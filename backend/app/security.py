"""Authentication: bearer API compatibility plus HttpOnly cookie sessions with CSRF protection."""
from datetime import datetime, timedelta, timezone
import secrets
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db import get_db
from app.models import User

password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
SESSION_COOKIE = "cedar_session"

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)

def create_token(user: User) -> str:
    secret = get_settings().jwt_secret
    if len(secret) < 32:
        raise HTTPException(503, "Server JWT_SECRET must be configured (minimum 32 characters)")
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": str(user.id), "iat": now, "exp": now + timedelta(hours=8),
        "csrf": secrets.token_urlsafe(32),
    }, secret, algorithm="HS256")

def current_user(
    request: Request,
    auth: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """Bearer tokens remain supported; browser cookie auth requires X-CSRF-Token for writes."""
    token = auth.credentials if auth else request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    secret = get_settings().jwt_secret
    if len(secret) < 32:
        raise HTTPException(503, "Server JWT_SECRET not configured")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    if not auth and request.method not in ("GET", "HEAD", "OPTIONS"):
        csrf = payload.get("csrf", "")
        supplied = request.headers.get("x-csrf-token", "")
        if not csrf or not secrets.compare_digest(supplied, csrf):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token")
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inactive user or invalid token")
    request.state.auth_payload = payload
    return user

def roles(*allowed: str):
    def guard(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user
    return guard

def audit(db: Session, user: User | None, event_type: str, object_type: str, object_id: int, **data):
    from app.models import AuditEvent
    db.add(AuditEvent(user_id=user.id if user else None, event_type=event_type,
                      object_type=object_type, object_id=object_id, data=data))
