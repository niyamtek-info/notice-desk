from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.db.models.user import User
from app.db.versioning import live_filter


security = HTTPBearer(auto_error=False)


@dataclass
class AuditUser:
    user_id: int | None
    email: str
    full_name: str | None

    @property
    def audit_actor(self) -> str:
        return self.email or self.full_name or "System"


def get_current_audit_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> AuditUser:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token subject",
        )

    user = db.query(User).filter(User.id == user_id, *live_filter(User)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return AuditUser(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )


def get_system_audit_user() -> AuditUser:
    return AuditUser(user_id=None, email="System", full_name="System")


def get_current_audit_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> AuditUser | None:
    """
    Same checks as get_current_audit_user, but returns None instead of
    raising when there's no/invalid token - for routes that also accept
    an alternative form of authorization (e.g. a signed URL).
    """
    if not credentials or not credentials.credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        return None

    user = db.query(User).filter(User.id == user_id, *live_filter(User)).first()
    if not user:
        return None

    return AuditUser(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )
