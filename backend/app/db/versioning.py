from __future__ import annotations

from datetime import datetime
from typing import Any


OPEN_END_DATE = datetime(9999, 12, 12, 0, 0, 0)
SYSTEM_ACTOR = "System"


def utcnow() -> datetime:
    return datetime.utcnow()


def current_actor(audit_user: Any | None) -> str:
    if audit_user is None:
        return SYSTEM_ACTOR
    actor = getattr(audit_user, "audit_actor", None)
    return actor or SYSTEM_ACTOR


def mark_created(row: Any, audit_user: Any | None) -> Any:
    actor = current_actor(audit_user)
    now = utcnow()
    row.created_at = row.created_at or now
    row.created_by = row.created_by or actor
    row.updated_at = now
    row.updated_by = actor
    if hasattr(row, "niyamtek_user") and getattr(row, "niyamtek_user") is None:
        row.niyamtek_user = actor
    row.version = 1 if row.version is None or row.version < 1 else row.version
    row.effective_date = row.effective_date or now
    row.end_date = OPEN_END_DATE
    row.is_deleted = False
    return row


def close_version(row: Any, audit_user: Any | None, *, deleted: bool = False) -> Any:
    actor = current_actor(audit_user)
    now = utcnow()
    row.updated_at = now
    row.updated_by = actor
    row.end_date = now
    row.is_active = False
    if deleted:
        row.is_deleted = True
    return row


def clone_version(row: Any, audit_user: Any | None, **overrides: Any) -> Any:
    cls = type(row)
    data = {}
    now = utcnow()
    actor = current_actor(audit_user)

    for column in cls.__table__.columns:
        if column.name in [
            "id",
            "version",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "effective_date",
            "end_date",
            "is_active",
        ]:
            continue

        data[column.name] = getattr(row, column.name)

    data.update(overrides)
    if "niyamtek_user" in cls.__table__.columns and "niyamtek_user" not in overrides:
        data["niyamtek_user"] = actor
    current_version = row.version or 1
    if current_version < 1:
        current_version = 1
    data["version"] = current_version + 1
    data["created_at"] = row.created_at
    data["created_by"] = row.created_by
    data["updated_at"] = now
    data["updated_by"] = current_actor(audit_user)
    data["effective_date"] = now
    data["end_date"] = OPEN_END_DATE
    data.setdefault("is_active", True)
    data.setdefault("is_deleted", False)

    return cls(**data)


def live_filter(model: Any):
    return (
        model.is_deleted == False,
        model.end_date == OPEN_END_DATE,
        model.is_active == True,
    )