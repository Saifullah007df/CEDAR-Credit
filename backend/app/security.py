"""Authentication and server-enforced role guards. Never trust client-supplied roles."""
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db import get_db
from app.models import User

password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)

def create_token(user: User) -> str:
    secret = get_settings().jwt_secret
    if len(secret) < 32:
        raise HTTPException(503, "Server JWT_SECRET must be configured (minimum 32 characters)")
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user.id), "iat": now, "exp": now + timedelta(hours=8)}, secret, algorithm="HS256")

def current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if auth is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    secret = get_settings().jwt_secret
    if len(secret) < 32:
        raise HTTPException(503, "Server JWT_SECRET not configured")
    try:
        payload = jwt.decode(auth.credentials, secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inactive user or invalid token")
    return user

def roles(*allowed: str):
    def guard(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user
    return guard

def audit(db: Session, user: User | None, event_type: str, object_type: str, object_id: int, **data):
    from app.models import AuditEvent
    db.add(AuditEvent(user_id=user.id if user else None, event_type=event_type, object_type=object_type, object_id=object_id, data=data))
