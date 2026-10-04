import os
from datetime import datetime, timedelta, timezone
import jwt
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def jwt_secret():
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters; no default is allowed")
    return secret

def create_access_token(subject, session_id, expires_delta=None):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(subject), "sid": session_id, "iat": now,
        "exp": now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))}, jwt_secret(), algorithm=ALGORITHM)
