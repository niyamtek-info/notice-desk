from datetime import datetime
import re
from typing import Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.application import (
    Application
)
from app.db.models.client_models import Client
from app.db.models.document_extraction import Document
from app.db.models.safari_notice import SarfaesiMaster
from app.db.session import SessionLocal
from app.db.versioning import OPEN_END_DATE, clone_version, close_version, live_filter, mark_created
from app.utils.date_utils import parse_datetime


class ApplicationsRepository:

    def get_db(self) -> Session:
        return SessionLocal()

    

    def _to_dict(self, app: Application, db: Session | None = None) -> Optional[Dict]:
        if not app:
            return None

        owns_db = db is None
        db = db or self.get_db()
        try:
            report_row = (
                db.query(SarfaesiMaster)
                .filter(
                    SarfaesiMaster.application_number == app.business_code,
                    SarfaesiMaster.is_deleted == False,
                    SarfaesiMaster.is_active == True,
                )
                .order_by(SarfaesiMaster.updated_at.desc(), SarfaesiMaster.id.desc())
                .first()
            )
            has_document = (
                db.query(Document.id)
                .filter(
                    Document.application_number == app.business_code,
                    Document.is_deleted == False,
                )
                .first()
                is not None
            )
            report_source = getattr(report_row, "report_source", None) if report_row else None
            if not report_source:
                report_source = "Extracted Document" if has_document else "Application Creation"

            return {
                "record_id": app.record_id,
                "application_no": app.business_code,
                "batch_code": app.batch_code,
                "loan_account_number": app.loan_account_number,
                "borrower_name": app.loan_requester_name,
                "client_name": app.client_name,
                "location": app.state,
                "assigned_date": app.assigned_date.isoformat() if app.assigned_date else None,
                "report_status": getattr(app, "report_status", None),
                "type_of_work": app.type_of_work,
                "source_type": app.source_type,
                "report_source": report_source,
                "has_document_for_report": has_document,

            }
        finally:
            if owns_db:
                db.close()

    def _sync_report_status_for_apps(self, db: Session, apps: List[Application]) -> None:
        if not apps:
            return

        app_numbers = [a.business_code for a in apps if a.business_code]
        if not app_numbers:
            return

        checklist_rows = (
            db.query(
                SarfaesiMaster.application_number,
                SarfaesiMaster.rerun_report,
            )
            .filter(
                SarfaesiMaster.application_number.in_(app_numbers),
                SarfaesiMaster.is_deleted == False,
                SarfaesiMaster.is_active == True,
            )
            .all()
        )

        unavailable_by_app = {
            row.application_number
            for row in checklist_rows
            if (row.rerun_report or 0) == 1
        }
        available_by_app = {
            row.application_number
            for row in checklist_rows
            if (row.rerun_report or 0) == 0
        }

        for app in apps:
            if app.business_code in unavailable_by_app:
                app.report_status = "Not_Available"
            elif app.business_code in available_by_app:
                app.report_status = "Available"
            else:
                app.report_status = "Not_Available"

    def save_record(
        self,
        record_id: str,
        record: Dict,
        audit_user=None,
        db: Session | None = None,
        auto_commit: bool = True,
    ):
        owns_db = db is None
        db = db or self.get_db()
        try:
            data = record.get("data", {})
            app_data = data.get("APPLICATION", {})
            loan_data = data.get("LOAN_INFO", {})
            prop_data = data.get("PROPERTY_INFO", {})
            batch_code = record.get("batch_code")
            loan_account_number = loan_data.get("LOAN_ACCOUNT_NUMBER")

            if loan_account_number:
                loan_account = str(loan_account_number).strip()
                # Check if active record exists - block duplicate
                if self.loan_account_exists(loan_account):
                    raise Exception("Loan account already exists")
                # Check if soft-deleted record exists - allow new record creation
                deleted_status = self.get_loan_account_status(loan_account)
                if deleted_status and deleted_status.get("is_deleted"):
                    pass  # Allow creation - soft-deleted record can be replaced

            app = Application(
                record_id=record_id,
                business_code=record.get("business_code"),
                batch_code=batch_code,
                source_type=record.get("source_type"),
                assigned_date=parse_datetime(
                    app_data.get("ASSIGNED_AT") or app_data.get("ASSIGNED_DATE")
                ),
                type_of_work=app_data.get("TYPE_OF_WORK"),
                client_name=loan_data.get("CLIENT_NAME") or loan_data.get("client_name"),
                loan_account_number=loan_account_number,
                loan_requester_name=loan_data.get("LOAN_REQUESTER_NAME"),
                state=prop_data.get("STATE"),
                report_status="Not_Available",
            )
            mark_created(app, audit_user)
            db.add(app)
            db.flush()

            if auto_commit:
                db.commit()
            db.refresh(app)
        except IntegrityError as e:
            db.rollback()
            detail = getattr(e, "orig", e)
            raise Exception(f"Database integrity error: {detail}")
        except Exception as e:
            db.rollback()
            raise Exception(f"Database error: {str(e)}")
        finally:
            if owns_db:
                db.close()

    def get_next_business_code(self, client_code: str) -> str:
        db = self.get_db()
        try:
            client_token = self._normalize_client_code_token(client_code)
            prefix = f"{client_token}-"
            existing_codes = (
                db.query(Application.business_code)
                .filter(
                    Application.business_code.isnot(None),
                    Application.business_code.ilike(f"{prefix}%"),
                )
                .all()
            )

            max_number = 0
            for (business_code,) in existing_codes:
                if not business_code:
                    continue
                match = re.fullmatch(
                    rf"{re.escape(client_token)}-(\d+)",
                    business_code.strip(),
                    flags=re.IGNORECASE,
                )
                if match:
                    max_number = max(max_number, int(match.group(1)))

            return f"{prefix}{max_number + 1}"
        finally:
            db.close()

    def active_business_code_exists(self, business_code: str, exclude_record_id: Optional[str] = None) -> bool:
        db = self.get_db()
        try:
            query = db.query(Application).filter(
                Application.business_code == business_code,
                *live_filter(Application),
            )
            if exclude_record_id:
                query = query.filter(Application.record_id != exclude_record_id)
            return query.first() is not None
        finally:
            db.close()

    def update_record(self, record_id: str, data: Dict, audit_user=None) -> Dict:
        db = self.get_db()
        try:
            app = (
                db.query(Application)
                .filter(Application.record_id == record_id, *live_filter(Application))
                .first()
            )
            if not app:
                raise Exception("Application not found")

            app_data = data.get("APPLICATION", {})
            loan_data = data.get("LOAN_INFO", {})
            prop_data = data.get("PROPERTY_INFO", {})
            batch_code = data.get("batch_code")
            
            app_updates = {}
            if "ASSIGNED_AT" in app_data or "ASSIGNED_DATE" in app_data:
                value = app_data.get("ASSIGNED_AT") or app_data.get("ASSIGNED_DATE")
                if value is not None:
                    app_updates["assigned_date"] = parse_datetime(value)
            if "TYPE_OF_WORK" in app_data:
                value = app_data.get("TYPE_OF_WORK")
                if value is not None:
                    app_updates["type_of_work"] = value
            # ═══ LOAN INFO FIELDS ═══
            # LOAN INFO SAFE UPDATE
            if loan_data:

                if "client_name" in loan_data or "CLIENT_NAME" in loan_data:
                    value = loan_data.get("client_name") or loan_data.get("CLIENT_NAME")
                    if value is not None:
                        app_updates["client_name"] = value

            if "LOAN_ACCOUNT_NUMBER" in loan_data:
                value = loan_data.get("LOAN_ACCOUNT_NUMBER")
                if value is not None:
                    loan_account = str(value).strip()
                    if self.loan_account_exists(loan_account, exclude_record_id=record_id):
                        raise Exception("Loan account already exists")
                    deleted_status = self.get_loan_account_status(loan_account)
                    if deleted_status and deleted_status.get("is_deleted"):
                        pass  # Allow - replacing soft-deleted record
                    app_updates["loan_account_number"] = value

                if "LOAN_REQUESTER_NAME" in loan_data:
                    value = loan_data.get("LOAN_REQUESTER_NAME")
                    if value is not None:
                        app_updates["loan_requester_name"] = value
            # ═══ PROPERTY INFO FIELDS ═══
            if prop_data and "STATE" in prop_data:
                value = prop_data.get("STATE")
                if value is not None:
                    app_updates["state"] = value

            if batch_code is not None:
                app_updates["batch_code"] = batch_code

            if app_updates:
                close_version(app, audit_user)
                app = clone_version(app, audit_user, **app_updates)
                db.add(app)
                db.flush()

        

            db.commit()
            current_app = (
                db.query(Application)
                .filter(Application.record_id == record_id, *live_filter(Application))
                .first()
            )
            return self._to_dict(current_app)
        except IntegrityError:
            db.rollback()
            raise Exception("Loan account already exists for this bank")
        except Exception as e:
            db.rollback()
            raise Exception(f"Database error: {str(e)}")
        finally:
            db.close()

    def get_record(self, record_id: str) -> Optional[Dict]:
        db = self.get_db()
        try:
            app = (
                db.query(Application)
                .filter(Application.record_id == record_id, *live_filter(Application))
                .first()
            )
            if app:
                self._sync_report_status_for_apps(db, [app])
            return self._to_dict(app)
        finally:
            db.close()

    def list_records(
        self,
        client_name: Optional[str] = None,
        client_code: Optional[str] = None,
        batch_code: Optional[str] = None,
        loan_account_number: Optional[str] = None,
        borrower_name: Optional[str] = None,
        location: Optional[str] = None,
        type_of_work: Optional[str] = None,
        assigned_from: Optional[datetime] = None,
        assigned_to: Optional[datetime] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        db = self.get_db()
        try:
            query = (
                db.query(Application)
                .filter(*live_filter(Application))
            )

            if client_code:
                resolved_client_code = str(client_code).strip()
                client_token = self._normalize_client_code_token(resolved_client_code)
                client_row = (
                    db.query(Client)
                    .filter(Client.client_code == resolved_client_code, *live_filter(Client))
                    .first()
                )
                if not client_row:
                    client_row = (
                        db.query(Client)
                        .filter(Client.client_code == resolved_client_code, Client.is_deleted == False)
                        .order_by(Client.version.desc(), Client.id.desc())
                        .first()
                    )
                resolved_client_name = client_row.client_name if client_row else resolved_client_code
                query = query.filter(
                    or_(
                        Application.business_code.ilike(f"{client_token}-%"),
                        Application.client_name == resolved_client_name,
                    )
                )
            elif client_name:
                resolved_client_name = client_name
                resolved_client_code = None

                # Try resolving client_code to client_name using live_filter first.
                client_row = (
                    db.query(Client)
                    .filter(Client.client_code == client_name, *live_filter(Client))
                    .first()
                )
                if not client_row:
                    # Some clients may have incorrect SCD2 flags (end_date, is_active).
                    # Use a more permissive query as fallback.
                    client_row = (
                        db.query(Client)
                        .filter(Client.client_code == client_name, Client.is_deleted == False)
                        .order_by(Client.version.desc(), Client.id.desc())
                        .first()
                    )

                if client_row:
                    resolved_client_name = client_row.client_name
                    resolved_client_code = client_row.client_code
                else:
                    # If client_code lookup failed entirely, the value might already be a client_name.
                    # Try looking up by name with permissive query.
                    client_by_name = (
                        db.query(Client)
                        .filter(Client.client_name == client_name, Client.is_deleted == False)
                        .order_by(Client.version.desc(), Client.id.desc())
                        .first()
                    )
                    if client_by_name:
                        resolved_client_name = client_by_name.client_name
                        resolved_client_code = client_by_name.client_code

                # Always apply the filter; if we could not resolve, filter by the raw value.
                if resolved_client_code:
                    client_token = self._normalize_client_code_token(resolved_client_code)
                    query = query.filter(
                        or_(
                            Application.business_code.ilike(f"{client_token}-%"),
                            Application.client_name == resolved_client_name,
                        )
                    )
                else:
                    query = query.filter(Application.client_name == resolved_client_name)
            if batch_code:
                query = query.filter(Application.batch_code==batch_code)
            if loan_account_number:
                query = query.filter(Application.loan_account_number == loan_account_number)
            if borrower_name:
                query = query.filter(Application.loan_requester_name.ilike(f"%{borrower_name}%"))
            if location:
                query = query.filter(Application.state.ilike(f"%{location}%"))

            if type_of_work:
                query = query.filter(Application.type_of_work == type_of_work)

            if assigned_from and assigned_to:
                query = query.filter(
                    func.date(Application.assigned_date).between(
                        assigned_from.date(),
                        assigned_to.date(),
                    )
                )
            elif assigned_from:
                query = query.filter(func.date(Application.assigned_date) == assigned_from.date())
            elif assigned_to:
                query = query.filter(func.date(Application.assigned_date) == assigned_to.date())

            query = query.order_by(Application.created_at.desc(), Application.id.desc())
            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)

            apps = query.all()
            self._sync_report_status_for_apps(db, apps)
            return [self._to_dict(a) for a in apps]
        finally:
            db.close()

    def search_records(self, q: str) -> List[Dict]:
        db = self.get_db()
        try:
            query = (
                db.query(Application)
                .filter(
                    *live_filter(Application),
                    (
                        Application.loan_requester_name.ilike(f"%{q}%")
                    )
                    | (Application.business_code.ilike(f"%{q}%"))
                    | (Application.client_name.ilike(f"%{q}%"))
                )
            )
            query = query.order_by(Application.created_at.desc())
            apps = query.all()
            self._sync_report_status_for_apps(db, apps)
            return [self._to_dict(a) for a in apps]
        finally:
            db.close()

    def delete_record(self, record_id: str, audit_user=None) -> bool:
        db = self.get_db()
        try:
            app = (
                db.query(Application)
                .filter(Application.record_id == record_id, *live_filter(Application))
                .first()
            )
            if not app:
                return False

            close_version(app, audit_user, deleted=True)

            # Also soft-delete associated SarfaesiMaster record
            sarfaesi = (
                db.query(SarfaesiMaster)
                .filter(
                    SarfaesiMaster.application_number == app.business_code,
                    SarfaesiMaster.is_deleted == False,
                )
                .order_by(SarfaesiMaster.updated_at.desc(), SarfaesiMaster.id.desc())
                .first()
            )
            if sarfaesi:
                sarfaesi.is_deleted = True
                sarfaesi.is_active = False
                sarfaesi.updated_by = getattr(audit_user, "audit_actor", "System") if audit_user else "System"
                sarfaesi.version = (sarfaesi.version or 0) + 1

            db.commit()
            return True
        finally:
            db.close()

    def loan_exists(self, client_name: str, loan_account_number: str) -> bool:
        db = self.get_db()
        try:
            return (
                db.query(Application)
                .filter(
                    Application.client_name == client_name,
                    Application.loan_account_number == loan_account_number,
                    *live_filter(Application),
                )
                .first()
                is not None
            )
        finally:
            db.close()

    def loan_account_exists(self, loan_account_number: str, exclude_record_id: Optional[str] = None, allow_if_deleted: bool = False) -> bool:
        db = self.get_db()
        try:
            query = db.query(Application).filter(
                Application.loan_account_number == loan_account_number,
                Application.is_deleted == False,
            )
            if exclude_record_id:
                query = query.filter(Application.record_id != exclude_record_id)
            active_exists = query.first() is not None

            if not active_exists and allow_if_deleted:
                deleted_query = db.query(Application).filter(
                    Application.loan_account_number == loan_account_number,
                    Application.is_deleted == True,
                )
                if exclude_record_id:
                    deleted_query = deleted_query.filter(Application.record_id != exclude_record_id)
                return deleted_query.first() is None

            return active_exists
        finally:
            db.close()

    def get_loan_account_status(self, loan_account_number: str) -> Optional[Dict]:
        db = self.get_db()
        try:
            app = (
                db.query(Application)
                .filter(Application.loan_account_number == loan_account_number)
                .order_by(Application.updated_at.desc(), Application.id.desc())
                .first()
            )
            if app:
                return {
                    "record_id": app.record_id,
                    "is_deleted": app.is_deleted,
                    "is_active": app.is_active,
                }
            return None
        finally:
            db.close()

    def get_record_by_loan_account(self, loan_account_number: str) -> Optional[Dict]:
        db = self.get_db()
        try:
            app = (
                db.query(Application)
                .filter(Application.loan_account_number == loan_account_number, *live_filter(Application))
                .first()
            )
            if app:
                return {
                    "record_id": app.record_id,
                    "business_code": app.business_code,
                    "application_no": app.business_code,
                }
            return None
        finally:
            db.close()

    @staticmethod
    def _normalize_client_code_token(client_code: str) -> str:
        token = "".join(
            ch if ch.isalnum() else "-"
            for ch in (client_code or "").strip().upper()
        )
        while "--" in token:
            token = token.replace("--", "-")
        return token.strip("-")
