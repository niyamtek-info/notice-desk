from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.safari_notice import SarfaesiMaster
from app.db.models.application import Application
from app.db.versioning import live_filter


class SarfaesiRepository:
    def __init__(self, db: Session):
        self.db = db

    def _to_decimal(self, value):
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        import re

        cleaned = str(value).strip().replace(",", "")
        cleaned = re.sub(r"(?i)rs\.?", "", cleaned)
        cleaned = re.sub(r"[^\d.\-]", "", cleaned)
        if cleaned in {"", "-", ".", "-."}:
            return None
        try:
            return Decimal(cleaned)
        except Exception:
            return None

    def _to_int(self, value):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        import re

        cleaned = str(value).strip().replace(",", "")
        cleaned = re.sub(r"(?i)rs\.?", "", cleaned)
        cleaned = re.sub(r"[^\d.\-]", "", cleaned)
        if cleaned in {"", "-", ".", "-."}:
            return None
        try:
            return int(float(cleaned))
        except Exception:
            return None

    def _normalize_value(self, field: str, value: Any):
        column = SarfaesiMaster.__table__.columns.get(field)
        if column is None or value is None:
            return value

        column_type = str(column.type).upper()
        if "NUMERIC" in column_type or "DECIMAL" in column_type or "FLOAT" in column_type:
            return self._to_decimal(value)
        if "INTEGER" in column_type and not isinstance(value, bool):
            return self._to_int(value)
        if "DATE" in column_type or "DATETIME" in column_type:
            if isinstance(value, datetime):
                return value
            try:
                from app.utils.date_utils import parse_datetime

                return parse_datetime(value)
            except Exception:
                return value
        return value

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        for field, value in list(normalized.items()):
            normalized[field] = self._normalize_value(field, value)
        return normalized

    _VALID_COLUMNS = set(SarfaesiMaster.__table__.columns.keys())

    def create(self, obj_in: Any, auto_commit: bool = True) -> SarfaesiMaster:
        payload = obj_in.dict(exclude_unset=True) if hasattr(obj_in, "dict") else dict(obj_in)
        payload = self._normalize_payload(payload)
        payload = {k: v for k, v in payload.items() if k in self._VALID_COLUMNS}
        sarfaesi = SarfaesiMaster(**payload)
        self.db.add(sarfaesi)
        if auto_commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(sarfaesi)
        return sarfaesi

    def get_all(self, skip: int = 0, limit: int = 100) -> list[SarfaesiMaster]:
        return (
            self.db.query(SarfaesiMaster)
            .filter(
                SarfaesiMaster.is_deleted == False,
                SarfaesiMaster.is_active == True,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_application_number(self, application_number):
        live_row = (
            self.db.query(SarfaesiMaster)
            .filter(
                SarfaesiMaster.application_number == application_number,
                SarfaesiMaster.is_deleted == False,
                *live_filter(SarfaesiMaster),
            )
            .order_by(SarfaesiMaster.updated_at.desc(), SarfaesiMaster.id.desc())  # 🔥 IMPORTANT
            .first()
        )
        if live_row:
            return live_row

        # Fallback to the latest non-deleted version so historical rows still
        # load in the UI even if the live/version flags were cleared earlier.
        return (
            self.db.query(SarfaesiMaster)
            .filter(
                SarfaesiMaster.application_number == application_number,
                SarfaesiMaster.is_deleted == False,
            )
            .order_by(
                SarfaesiMaster.version.desc(),
                SarfaesiMaster.updated_at.desc(),
                SarfaesiMaster.id.desc(),
            )
            .first()
        )

    def get_by_loan_account_no(self, loan_account_no, exclude_application_number: str | None = None):
        query = (
            self.db.query(SarfaesiMaster)
            .filter(
                SarfaesiMaster.loan_account_no == loan_account_no,
                SarfaesiMaster.is_deleted == False,
                SarfaesiMaster.is_active == True,
            )
        )
        if exclude_application_number:
            query = query.filter(SarfaesiMaster.application_number != exclude_application_number)
        return query.order_by(SarfaesiMaster.updated_at.desc(), SarfaesiMaster.id.desc()).first()

    def get_by_loan_account_no_including_deleted(self, loan_account_no, exclude_application_number: str | None = None):
        query = (
            self.db.query(SarfaesiMaster)
            .filter(SarfaesiMaster.loan_account_no == loan_account_no)
        )
        if exclude_application_number:
            query = query.filter(SarfaesiMaster.application_number != exclude_application_number)
        return query.order_by(SarfaesiMaster.updated_at.desc(), SarfaesiMaster.id.desc()).first()

    def is_loan_account_active(self, loan_account_no, exclude_application_number: str | None = None) -> bool:
        # Returns True if there's an ACTIVE SarfaesiMaster record with active Application
        # Returns False if SarfaesiMaster or its Application is soft-deleted (allow reuse)
        query = (
            self.db.query(SarfaesiMaster)
            .join(Application, SarfaesiMaster.application_number == Application.business_code)
            .filter(
                SarfaesiMaster.loan_account_no == loan_account_no,
                SarfaesiMaster.is_deleted == False,
                SarfaesiMaster.is_active == True,
                Application.is_deleted == False,
                Application.is_active == True,
            )
        )
        if exclude_application_number:
            query = query.filter(Application.business_code != exclude_application_number)
        return query.first() is not None

    def get_by_id(self, id: int):
        return (
            self.db.query(SarfaesiMaster)
            .filter(
                SarfaesiMaster.id == id,
                SarfaesiMaster.is_deleted == False,
                SarfaesiMaster.is_active == True,
            )
            .first()
        )

    def update(self, db_obj: SarfaesiMaster, obj_in: Any, auto_commit: bool = True) -> SarfaesiMaster:
        update_data = obj_in.dict(exclude_unset=True) if hasattr(obj_in, "dict") else dict(obj_in)
        update_data = self._normalize_payload(update_data)

        for field, value in update_data.items():
            if field not in self._VALID_COLUMNS:
                continue
            setattr(db_obj, field, value)

        self.db.add(db_obj)
        if auto_commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    def soft_delete(
        self,
        db_obj: SarfaesiMaster,
        deleted_by: str | None = None,
        auto_commit: bool = True,
    ) -> SarfaesiMaster:
        db_obj.is_deleted = True
        db_obj.is_active = False
        if deleted_by is not None:
            db_obj.updated_by = deleted_by
        self.db.add(db_obj)
        if auto_commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(db_obj)
        return db_obj
