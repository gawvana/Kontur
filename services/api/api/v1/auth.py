import base64
import hashlib
import hmac
import json
import os
import struct
import time
import uuid
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, quote
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import User, Role, Session, AdminRecoveryCode
from core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from core.rate_limit import RateLimiter
from api.deps import get_current_user, oauth2_scheme, decode_token, unauthorized, forbidden
from schemas.models import (
    UserResponse, SessionResponse, TwoFactorSetupResponse, TwoFactorVerifyRequest
)

router = APIRouter()
auth_limiter = RateLimiter(requests_per_minute=30)

class TelegramAuthData(BaseModel):
    initData: str = Field(max_length=16384)


def verify_telegram_data(init_data: str, bot_token: str) -> dict:
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
        data = dict(pairs)
        if len(data) != len(pairs) or not bot_token:
            raise ValueError()
        received = data.pop("hash")
        check = "\n".join(f"{key}={data[key]}" for key in sorted(data))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(received, expected):
            raise ValueError()
        age = time.time() - int(data["auth_date"])
        if age < -30 or age > 300:
            raise ValueError()
        user = json.loads(data["user"])
        if type(user.get("id")) is not int or not 0 < user["id"] < 2**63:
            raise ValueError()
        return user
    except (ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(401, "Invalid or expired Telegram data") from None


# --- RFC 6238 TOTP Helpers ---

def generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("utf-8").replace("=", "")

def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    try:
        code_int = int(code.strip())
    except (ValueError, AttributeError):
        return False
    # Pad base32 string if needed
    padded = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    try:
        key = base64.b32decode(padded)
    except Exception:
        return False
    t = int(time.time() // 30)
    for i in range(-window, window + 1):
        msg = struct.pack(">Q", t + i)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        o = h[19] & 15
        val = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
        if val == code_int:
            return True
    return False


@router.post("/telegram")
async def telegram_auth(
    auth_data: TelegramAuthData,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(auth_limiter)
):
    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        raise HTTPException(503, "Telegram authentication is not configured")
    user_data = verify_telegram_data(auth_data.initData, bot_token)
    telegram_id = str(user_data["id"])
    username = user_data.get("username")
    first_name = user_data.get("first_name")
    last_name = user_data.get("last_name")

    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=Role.USER
        )
        db.add(user)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                raise
    else:
        # Update names if changed
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if last_name and user.last_name != last_name:
            user.last_name = last_name

    session_id = uuid.uuid4().hex
    user_agent = request.headers.get("User-Agent")
    client_ip = request.client.host if request.client else None

    db.add(Session(
        id=session_id,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        user_agent=user_agent[:255] if user_agent else None,
        ip_address=client_ip
    ))
    await db.commit()
    token = create_access_token(telegram_id, session_id)
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "telegram_id": telegram_id, "role": user.role}}


@router.post("/refresh")
async def refresh_session(
    response: Response,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    F04: Safe session renewal without requiring re-exchange of Telegram initData
    if the session is still active and valid.
    """
    payload = decode_token(token, verify_exp=False)
    session = await db.scalar(
        select(Session).where(
            Session.id == payload["sid"],
            Session.is_revoked.is_(False)
        )
    )
    if not session or session.expires_at < datetime.utcnow():
        raise unauthorized("Session expired or revoked")

    user = await db.scalar(select(User).where(User.id == session.user_id))
    if not user:
        raise unauthorized()

    # Extend session expiry
    session.expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    await db.commit()

    new_token = create_access_token(user.telegram_id, session.id)
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": new_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=204)
async def logout(
    user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    payload = decode_token(token)
    await db.execute(
        update(Session).where(Session.id == payload["sid"], Session.user_id == user.id).values(is_revoked=True)
    )
    await db.commit()


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    sessions = await db.scalars(
        select(Session).where(Session.user_id == user.id, Session.is_revoked.is_(False)).order_by(Session.created_at.desc())
    )
    return list(sessions.all())


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    session = await db.scalar(select(Session).where(Session.id == session_id, Session.user_id == user.id))
    if not session:
        raise HTTPException(404, "Session not found")
    session.is_revoked = True
    await db.commit()


# --- 2FA for Staff / Admins ---

@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    secret = generate_totp_secret()
    user.totp_secret = secret
    
    # Generate 8 recovery codes
    recovery_codes = [uuid.uuid4().hex[:8] for _ in range(8)]
    # Clear old codes
    await db.execute(delete(AdminRecoveryCode).where(AdminRecoveryCode.user_id == user.id))
    for code in recovery_codes:
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        db.add(AdminRecoveryCode(user_id=user.id, code_hash=code_hash))
    await db.commit()

    uri = f"otpauth://totp/Kontur:{quote(user.username or user.telegram_id)}?secret={secret}&issuer=Kontur"
    return {
        "secret": secret,
        "provisioning_uri": uri,
        "recovery_codes": recovery_codes
    }


@router.post("/2fa/verify")
async def verify_2fa(
    body: TwoFactorVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    code = body.code.strip()
    if user.totp_secret and verify_totp(user.totp_secret, code):
        user.is_2fa_enabled = True
        await db.commit()
        return {"status": "verified"}

    # Check recovery code
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    rec = await db.scalar(
        select(AdminRecoveryCode).where(
            AdminRecoveryCode.user_id == user.id,
            AdminRecoveryCode.code_hash == code_hash,
            AdminRecoveryCode.is_used.is_(False)
        )
    )
    if rec:
        rec.is_used = True
        user.is_2fa_enabled = True
        await db.commit()
        return {"status": "verified_by_recovery_code"}

    raise HTTPException(400, "Invalid 2FA code or recovery code")
