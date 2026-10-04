from datetime import datetime
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import jwt_secret, ALGORITHM
from db.database import get_db
from db.models import User, Session, Role

bearer = HTTPBearer(auto_error=False)

def unauthorized(detail: str = "Could not validate credentials"):
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})

def forbidden(detail: str = "Insufficient permissions"):
    return HTTPException(403, detail)

def oauth2_scheme(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise unauthorized()
    return credentials.credentials

def decode_token(token: str, verify_exp: bool = True):
    try:
        options = {"require": ["exp", "iat", "sub", "sid"], "verify_exp": verify_exp}
        payload = jwt.decode(token, jwt_secret(), algorithms=[ALGORITHM], options=options)
        if not isinstance(payload.get("sid"), str) or not str(payload["sub"]).isdigit():
            raise unauthorized()
        return payload
    except JWTError:
        raise unauthorized() from None

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_token(token)
    user = await db.scalar(
        select(User).join(Session, Session.user_id == User.id).where(
            User.telegram_id == payload["sub"],
            Session.id == payload["sid"],
            Session.expires_at > datetime.utcnow(),
            Session.is_revoked.is_(False)
        )
    )
    if user is None:
        raise unauthorized()
    return user

def require_role(*roles: Role):
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise forbidden()
        if not user.is_2fa_enabled:
            raise HTTPException(503, "Staff second-factor authentication is not active")
        return user
    return role_checker

get_current_staff_user = require_role(Role.MODERATOR, Role.SENIOR_MODERATOR, Role.ADMIN, Role.OWNER)
get_current_admin_user = require_role(Role.ADMIN, Role.OWNER)
