import uuid
import io
from fastapi.responses import StreamingResponse
from datetime import datetime
from fastapi import HTTPException, UploadFile 
import pandas as pd
from typing import Any, Dict, Optional, List
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill

from app.db.repositories.applications_repo import ApplicationsRepository
from app.db.repositories.report_repo import ReportRepository
from app.db.models.client_models import Client
from app.db.session import SessionLocal
from app.db.versioning import live_filter
from app.api.v1.dependencies.auth import AuditUser
from app.utils.date_utils import parse_datetime
from app.services.sarfaesi_service import SarfaesiService
import traceback

DISPLAY_COLUMN_MAP = {
    "TYPE_OF_WORK": "TYPE OF SERVICE",
    "LOAN_ACCOUNT_NUMBER": "LOAN ACCOUNT NO",
    "LOAN_REQUESTER_NAME": "BORROWER NAME",
    "STATE": "LOCATION",
    "ASSIGNED_DATE": "DATE OF ASSIGN",
    "client_name": "CLIENT NAME"
}

BULK_SARFAESI_FIELD_MAP = {
    "NIYAMTEK_USER": "niyamtek_user",
    "BATCH_CODE": "batch_code",
    "CLIENT_CODE": "client_code",
    "COMPANY_NAME": "client_name",
    "CLIENT_NAME": "client_name",
    "LOAN_REQUESTER_NAME": "borrower_name",
    "ASSIGNED_DATE": "assignment_agreement_date",
    "LOAN_ACCOUNT_NUMBER": "loan_account_no",
    "BORROWER_NAME": "borrower_name",
    "TRUST_NUMBER": "trust_number",
    "AO_NAME": "ao_name",
    "BRANCH": "branch",
    "STATE": "state",
    "REGION": "region",
    "PROPERTY_ADDRESS": "property_address",
    "BORROWER_ADDRESS": "borrower_address",
    "BORROWER_ADDRESS_ALSO_AT": "borrower_address_alt",
    "CO_BORROWER_NAME_1": "co_borrower_1_name",
    "CO_BORROWER_ADDRESS_1": "co_borrower_1_address",
    "CO_BORROWER_ADDRESS_1_ALSO_AT": "co_borrower_1_address_alt",
    "CO_BORROWER_NAME_2": "co_borrower_2_name",
    "CO_BORROWER_ADDRESS_2": "co_borrower_2_address",
    "CO_BORROWER_ADDRESS_2_ALSO_AT": "co_borrower_2_address_alt",
    "CO_BORROWER_NAME_3": "co_borrower_3_name",
    "CO_BORROWER_ADDRESS_3": "co_borrower_3_address",
    "CO_BORROWER_ADDRESS_3_ALSO_AT": "co_borrower_3_address_alt",
    "CO_BORROWER_NAME_4": "co_borrower_4_name",
    "CO_BORROWER_ADDRESS_4": "co_borrower_4_address",
    "CO_BORROWER_ADDRESS_4_ALSO_AT": "co_borrower_4_address_alt",
    "CO_BORROWER_NAME_5": "co_borrower_5_name",
    "CO_BORROWER_ADDRESS_5": "co_borrower_5_address",
    "CO_BORROWER_ADDRESS_5_ALSO_AT": "co_borrower_5_address_alt",
    "CO_BORROWER_NAME_6": "co_borrower_6_name",
    "CO_BORROWER_ADDRESS_6": "co_borrower_6_address",
    "CO_BORROWER_ADDRESS_6_ALSO_AT": "co_borrower_6_address_alt",
    "GUARANTOR_NAME_1": "guarantor_1_name",
    "GUARANTOR_ADDRESS_1": "guarantor_1_address",
    "GUARANTOR_NAME_2": "guarantor_2_name",
    "GUARANTOR_ADDRESS_2": "guarantor_2_address",
    "PROPERTY_DESCRIPTION": "property_description",
    "DATE_OF_NPA": "npa_date",
    "DPD_AS_ON_NOTICE_ISSUANCE_DATE": "dpd",
    "DISBURSEMENT_TYPE": "disbursement_type",
    "DISBURSAL_DATE": "disbursal_date",
    "DISBURSAL_AMOUNT": "disbursal_amount",
    "LOAN_AGREEMENT_DATE": "loan_agreement_date",
    "LOAN_AMOUNT": "loan_amount",
    "LOAN_AMOUNT_IN_WORDS": "loan_amount_words",
    "FUTURE_PRINCIPAL": "future_principal",
    "PRINCIPAL_OUTSTANDING": "principal_outstanding",
    "INSTALMENT_OVERDUE_AMOUNT": "instalment_overdue",
    "INTEREST_ON_TERMINATION": "interest_on_termination",
    "LATE_PAYMENT_PENALTY": "late_payment_penalty",
    "CHEQUE_BOUNCE_CHARGES_INCLUDING_OTHERS": "cheque_bounce_charges",
    "OTHER_AMOUNT": "other_amount",
    "FORECLOSURE_CHARGES": "foreclosure_charges",
    "TOTAL_OUTSTANDING": "total_outstanding",
    "FCL_AS_ON_DATE": "fcl_as_on_date",
    "TOTAL_OUTSTANDING_IN_WORDS": "total_outstanding_words",
    "13_2_NOTICE_AMT": "notice_13_2_amount",
    "13_2_DEMAND_NOTICE_DATE": "notice_13_2_date",
    "DISPATCH_DATE": "notice_dispatch_date",
    "PASTING_DATE_OPTIONAL": "notice_pasting_date",
    "DELIVERED_ADDRESS": "delivered_address",
    "UNDELIVERED_ADDRESS": "undelivered_address",
    "TOTAL_ADDRESS": "total_address",
    "13_2_DATE_OF_PUBLICATION": "publication_date_13_2",
    "PUBLICATION_DETAILS_NAMES_OF_NEWS_PAPERS_LANGUAGE_NAME_ENGLISH": "publication_english_13_2",
    "PUBLICATION_DETAILS_NAMES_OF_NEWS_PAPERS_VERNACULAR_LANGUAGE_NAME_TAMIL_HINDI_MALAYALAM_ETC": "publication_local_13_2",
}


class ApplicationsService:
    def __init__(self):
        self.repo = ApplicationsRepository()

    def _get_client_name(self, data: Dict) -> str:
        client_name = (
            data.get("LOAN_INFO", {}).get("CLIENT_NAME")
            or data.get("LOAN_INFO", {}).get("client_name")
            or data.get("loan_info", {}).get("client_name")
            or data.get("client_name")
        )
        if not client_name or not str(client_name).strip():
            raise HTTPException(status_code=400, detail="client_name is required to create an application")
        return str(client_name).strip()

    def _get_client_code(self, data: Dict, required: bool = False) -> Optional[str]:
        client_code = (
            data.get("LOAN_INFO", {}).get("CLIENT_CODE")
            or data.get("LOAN_INFO", {}).get("client_code")
            or data.get("loan_info", {}).get("client_code")
            or data.get("client_code")
        )
        if client_code is not None:
            client_code = str(client_code).strip()
        if not client_code:
            client_name = self._get_client_name(data)
            db = SessionLocal()
            try:
                client = (
                    db.query(Client)
                    .filter(Client.client_name == client_name, *live_filter(Client))
                    .first()
                )
                if client:
                    client_code = client.client_code
            finally:
                db.close()
        if required and not client_code:
            raise HTTPException(status_code=400, detail="client_code is required to create an application")
        return client_code or None

    def _generate_business_code(self, client_code: str) -> str:
        return self.repo.get_next_business_code(client_code)

    def _validate_client_code_exists(self, db, client_code: str) -> None:
        if not client_code:
            raise HTTPException(status_code=400, detail="client_code is required to create an application")
        client = (
            db.query(Client)
            .filter(Client.client_code == client_code, *live_filter(Client))
            .first()
        )
        if not client:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid client_code: {client_code}. Client does not exist.",
            )

    def _ensure_business_code_is_unique(self, business_code: str, record_id: Optional[str] = None) -> None:
        if self.repo.active_business_code_exists(business_code, exclude_record_id=record_id):
            raise HTTPException(
                status_code=409,
                detail=f"Active application number already exists: {business_code}",
            )

    def _normalize_application_payload(self, data: Dict) -> Dict:
        """
        Accept either a flat payload or the existing nested payload shape and
        return the canonical nested structure used by the repository layer.
        """
        if not isinstance(data, dict):
            return {}

        batch_code = (
            data.get("batch_code")
            or data.get("BATCH_CODE")
            or data.get("batchCode")
        )

        if any(key in data for key in ("APPLICATION", "LOAN_INFO", "PROPERTY_INFO")):
            normalized = {
                "APPLICATION": dict(data.get("APPLICATION", {})),
                "LOAN_INFO": dict(data.get("LOAN_INFO", {})),
                "PROPERTY_INFO": dict(data.get("PROPERTY_INFO", {})),
            }
            if batch_code is not None:
                normalized["batch_code"] = batch_code
            return normalized

        return {
            "APPLICATION": {
                "ASSIGNED_AT": data.get("ASSIGNED_AT") or data.get("ASSIGNED_DATE"),
                "TYPE_OF_WORK": data.get("TYPE_OF_WORK"),
            },
            "LOAN_INFO": {
                "CLIENT_NAME": data.get("CLIENT_NAME") or data.get("client_name"),
                "client_code": data.get("client_code") or data.get("CLIENT_CODE"),
                "LOAN_ACCOUNT_NUMBER": data.get("LOAN_ACCOUNT_NUMBER"),
                "LOAN_REQUESTER_NAME": data.get("LOAN_REQUESTER_NAME"),
            },
            "PROPERTY_INFO": {
                "STATE": data.get("STATE"),
            },
            "batch_code": batch_code,
        }

    def _has_complete_13_2_details(self, data: Dict[str, Any]) -> bool:
        required_fields = (
            "notice_13_2_amount",
            "notice_13_2_date",
            "notice_dispatch_date",
            "notice_pasting_date",
            "delivery_status",
            "delivered_address",
            "undelivered_address",
            "total_address",
            "publication_date_13_2",
            "publication_english_13_2",
            "publication_local_13_2",
        )

        for field in required_fields:
            if self._is_blank_value(data.get(field)):
                return False
        return True

    # -------------------------------------------------
    # INTERNAL SINGLE INSERT
    # -------------------------------------------------
    def _create_single(self, data: dict, source_type: str, audit_user: AuditUser | None = None):
        data = self._normalize_application_payload(data)
        record_id = str(uuid.uuid4())
        client_code = self._get_client_code(data, required=True)
        business_code = self._generate_business_code(client_code)
        self._ensure_business_code_is_unique(business_code)
        batch_code = data.get("batch_code")
        loan_account_number = (
            data.get("LOAN_INFO", {}).get("LOAN_ACCOUNT_NUMBER")
            or data.get("LOAN_INFO", {}).get("loan_account_number")
        )
        if loan_account_number and self.repo.loan_account_exists(str(loan_account_number).strip()):
            raise HTTPException(
                status_code=409,
                detail="Loan account already exists",
            )

        record = {
            "record_id": record_id,
            "business_code": business_code,
            "data": data,
            "source_type": source_type,
            "batch_code": batch_code
        }

        db = SessionLocal()
        try:
            self._validate_client_code_exists(db, client_code)
            self.repo.save_record(
                record_id,
                record,
                audit_user=audit_user,
                db=db,
                auto_commit=False,
            )

            # Keep application + SARFAESI generation in one transaction.
            sarfaesi_service = SarfaesiService(db)
            sarfaesi_service.generate_sarfaesi_from_application(
                business_code,
                audit_user,
                auto_commit=False,
            )
            if not self._has_complete_13_2_details(data):
                ReportRepository(db).mark_rerun_report(
                    business_code,
                    1,
                    audit_user=audit_user,
                    auto_commit=False,
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        return self.repo.get_record(record_id)

    # -------------------------------------------------
    # MANUAL CREATE (JSON)
    # -------------------------------------------------
    def create_record(self, data: Dict, source_type: str = "Manual", audit_user: AuditUser | None = None):
        return self._create_single(data, source_type, audit_user=audit_user)

    def _is_blank_value(self, value: Any) -> bool:
        if isinstance(value, pd.Series):
            return all(self._is_blank_value(item) for item in value.tolist())
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, str) and value.strip().upper() == "NONE":
            return True
        try:
            return bool(pd.isna(value))
        except Exception:
            return False

    def _normalize_date(self, value: Any) -> str:
        """Normalize date values to YYYY-MM-DD format for comparison"""
        if value is None:
            return ""
        
        # If it's a date/datetime object, convert to string
        if hasattr(value, 'strftime'):
            return value.strftime('%Y-%m-%d')
        
        value_str = str(value).strip()
        if not value_str:
            return ""
        
        # Try to parse and normalize to YYYY-MM-DD
        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%m-%d-%Y", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                from datetime import datetime
                dt = datetime.strptime(value_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If can't parse, return original
        return value_str

    def _values_match(self, db_value: Any, uploaded_value: Any) -> bool:
        if db_value is None and uploaded_value is None:
            return True
        if db_value is None or uploaded_value is None:
            return False
        
        # Normalize both values for comparison
        db_normalized = self._normalize_date(db_value)
        uploaded_normalized = self._normalize_date(uploaded_value)
        
        # Compare normalized values
        if db_normalized == uploaded_normalized:
            return True
        
        # If not dates, try string comparison
        db_str = str(db_value).strip().upper()
        uploaded_str = str(uploaded_value).strip().upper()
        if db_str == uploaded_str:
            return True
        
        # Try HTML-stripped comparison BEFORE numeric comparison (for fields like property_description)
        try:
            import re
            # Remove HTML tags from both values and clean up
            db_clean = re.sub(r'<[^>]+>', '', str(db_value)).strip().upper()
            uploaded_clean = re.sub(r'<[^>]+>', '', str(uploaded_value)).strip().upper()
            
            # Normalize whitespace (replace multiple spaces with single space)
            db_clean = re.sub(r'\s+', ' ', db_clean)
            uploaded_clean = re.sub(r'\s+', ' ', uploaded_clean)
            
            # Remove ALL trailing periods (handles <p>text.</p> vs text.)
            db_clean = re.sub(r'\.+$', '', db_clean)
            uploaded_clean = re.sub(r'\.+$', '', uploaded_clean)
            
            # Remove trailing/leading spaces
            db_clean = db_clean.strip()
            uploaded_clean = uploaded_clean.strip()
            
            if db_clean and uploaded_clean and db_clean == uploaded_clean:
                return True
        except Exception:
            pass
        
        # Try numeric comparison
        try:
            db_num = float(db_str.replace(",", ""))
            uploaded_num = float(uploaded_str.replace(",", ""))
            return db_num == uploaded_num
        except (ValueError, AttributeError):
            pass
        
        return False

    def _build_sarfaesi_payload_from_row(self, row: pd.Series) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        for column_name, value in row.items():
            if self._is_blank_value(value):
                continue
            target_field = BULK_SARFAESI_FIELD_MAP.get(column_name)
            if not target_field:
                continue
            current_value = payload.get(target_field)
            if self._is_blank_value(current_value):
                payload[target_field] = self._first_non_blank_value(value)
        return payload

    def upload_file(self, file: UploadFile, audit_user: AuditUser):
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter

        file_content = file.file.read()
        rich_text_map: Dict[int, str] = {}

        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_content))
        elif file.filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            raise Exception("Unsupported file format")

        df = self._normalize_columns(df)
        df = self._map_columns(df)

        required_columns = [
            "CLIENT_CODE",
            "CLIENT_NAME",
            "LOAN_ACCOUNT_NUMBER",
            "LOAN_REQUESTER_NAME",
            "STATE",
            "ASSIGNED_DATE",
        ]

        for col in required_columns:
            if col not in df.columns:
                raise Exception(f"Missing required column in file: {col}")

        result_rows = []

        for index, row in df.iterrows():
            row_data = row.to_dict()
            error_reason = None

            missing_fields = []
            for col in required_columns:
                value = row.get(col)
                if self._is_blank_value(value):
                    missing_fields.append(col)
            if missing_fields:
                error_reason = f"Missing fields: {', '.join(missing_fields)}"

            client_code = str(self._first_non_blank_value(row.get("CLIENT_CODE")) or "").strip()
            client_name = str(self._first_non_blank_value(row.get("CLIENT_NAME")) or "").strip()
            loan_account = str(self._first_non_blank_value(row.get("LOAN_ACCOUNT_NUMBER")) or "").strip()

            # VALIDATION: Check if client exists in database
            if client_name and not error_reason:
                db = SessionLocal()
                try:
                    client = (
                        db.query(Client)
                        .filter(Client.client_name == client_name, Client.is_deleted == False)
                        .order_by(Client.version.desc(), Client.id.desc())
                        .first()
                    )
                    if not client:
                        error_reason = f"Client '{client_name}' not found in database"
                finally:
                    db.close()

            # VALIDATION: Check if this is an update scenario
            is_update_scenario = False
            existing_app = None

            if loan_account and error_reason is None:
                deleted_status = self.repo.get_loan_account_status(loan_account)
                if deleted_status and deleted_status.get("is_deleted"):
                    # Soft-deleted record exists - not an update scenario, new record can be created
                    pass
                elif self.repo.loan_account_exists(loan_account):
                    existing_app = self.repo.get_record_by_loan_account(loan_account)
                if existing_app:
                    # Fetch the SarfaesiMaster record to check field values
                    application_no = existing_app.get("application_no")
                    db = SessionLocal()
                    try:
                        sarfaesi_service = SarfaesiService(db)
                        existing_report = sarfaesi_service.repo.get_by_application_number(application_no)
                        
                        if existing_report:
                            # Check if any populated fields are being modified
                            modified_fields = []
                            for col in df.columns:
                                if col in required_columns:
                                    continue
                                
                                uploaded_value = row.get(col)
                                if self._is_blank_value(uploaded_value):
                                    continue
                                
                                db_field = BULK_SARFAESI_FIELD_MAP.get(col)
                                if not db_field:
                                    continue
                                
                                # Get DB value using getattr
                                db_value = getattr(existing_report, db_field, None)
                                
                                # Convert date objects to string for comparison
                                if hasattr(db_value, 'strftime'):
                                    db_value = db_value.strftime('%Y-%m-%d')
                                
                                # If DB has a value and uploaded is different, it's a modification
                                if not self._is_blank_value(db_value):
                                    if not self._values_match(db_value, uploaded_value):
                                        modified_fields.append({
                                            "field": col,
                                            "db_value": db_value,
                                            "uploaded_value": uploaded_value
                                        })
                            
                            if modified_fields:
                                # Reject - trying to modify populated fields
                                error_parts = []
                                for field_info in modified_fields:
                                    field_name = field_info["field"]
                                    db_val = field_info["db_value"]
                                    uploaded_val = field_info["uploaded_value"]
                                    error_parts.append(
                                        f"{field_name} cannot be edited. Existing value: '{db_val}'. "
                                        f"Uploaded value: '{uploaded_val}'. Only empty fields can be filled."
                                    )
                                error_reason = " | ".join(error_parts)
                            else:
                                # All good - only empty fields being filled
                                is_update_scenario = True
                    finally:
                        db.close()

            if not error_reason:
                try:
                    record_id = None  # Initialize for both paths
                    if is_update_scenario and existing_app:
                        # UPDATE existing record - only empty fields
                        application_no = existing_app.get("application_no")
                        report_payload = self._build_sarfaesi_payload_from_row(row)
                        report_payload["report_source"] = "Manual Excel"
                        report_payload["has_document"] = False
                        
                        db = SessionLocal()
                        try:
                            sarfaesi_service = SarfaesiService(db)
                            
                            # Group fields by section
                            nested_payload = {
                                "loan_details": {},
                                "13_2_details": {},
                                "13_4_details": {},
                                "cjm_details": {},
                                "physical_possession_details": {},
                                "auction_notice_details": {},
                                "auction_portal_details": {},
                                "post_sale_details": {},
                                "sale_certificate_details": {},
                                "niyamtek_remarks_details": {},
                            }
                            
                            field_to_section_map = {
                                "borrower_name": "loan_details",
                                "loan_account_no": "loan_details",
                                "borrower_address": "loan_details",
                                "state": "loan_details",
                                "region": "loan_details",
                                "branch": "loan_details",
                                "ao_name": "loan_details",
                                "trust_number": "loan_details",
                                "assignment_agreement_date": "loan_details",
                                "property_address": "loan_details",
                                "property_description": "loan_details",
                                "npa_date": "loan_details",
                                "dpd": "loan_details",
                                "disbursement_type": "loan_details",
                                "disbursal_date": "loan_details",
                                "disbursal_amount": "loan_details",
                                "loan_agreement_date": "loan_details",
                                "loan_amount": "loan_details",
                                "loan_amount_words": "loan_details",
                                "future_principal": "loan_details",
                                "principal_outstanding": "loan_details",
                                "instalment_overdue": "loan_details",
                                "interest_on_termination": "loan_details",
                                "late_payment_penalty": "loan_details",
                                "cheque_bounce_charges": "loan_details",
                                "other_amount": "loan_details",
                                "foreclosure_charges": "loan_details",
                                "total_outstanding": "loan_details",
                                "fcl_as_on_date": "loan_details",
                                "total_outstanding_words": "loan_details",
                                "co_borrower_1_name": "loan_details",
                                "co_borrower_1_address": "loan_details",
                                "co_borrower_2_name": "loan_details",
                                "co_borrower_2_address": "loan_details",
                                "co_borrower_3_name": "loan_details",
                                "co_borrower_3_address": "loan_details",
                                "co_borrower_4_name": "loan_details",
                                "co_borrower_4_address": "loan_details",
                                "co_borrower_5_name": "loan_details",
                                "co_borrower_5_address": "loan_details",
                                "co_borrower_6_name": "loan_details",
                                "co_borrower_6_address": "loan_details",
                                "guarantor_1_name": "loan_details",
                                "guarantor_1_address": "loan_details",
                                "guarantor_2_name": "loan_details",
                                "guarantor_2_address": "loan_details",
                                "notice_13_2_amount": "13_2_details",
                                "notice_13_2_date": "13_2_details",
                                "notice_dispatch_date": "13_2_details",
                                "notice_pasting_date": "13_2_details",
                                "delivered_address": "13_2_details",
                                "undelivered_address": "13_2_details",
                                "total_address": "13_2_details",
                                "publication_date_13_2": "13_2_details",
                                "publication_english_13_2": "13_2_details",
                                "publication_local_13_2": "13_2_details",
                            }
                            
                            for field_name, value in report_payload.items():
                                section = field_to_section_map.get(field_name)
                                if section and section in nested_payload:
                                    nested_payload[section][field_name] = value
                            
                            nested_payload = {k: v for k, v in nested_payload.items() if v}
                            
                            updated_report = sarfaesi_service.update_sarfaesi_and_sync(
                                application_no,
                                nested_payload,
                                audit_user,
                            )
                            
                            # Preserve rerun_report
                            existing_rerun_report = getattr(sarfaesi_service.repo.get_by_application_number(application_no), 'rerun_report', 0)
                            if hasattr(updated_report, 'rerun_report'):
                                updated_report.rerun_report = existing_rerun_report
                            db.commit()
                        finally:
                            db.close()
                        
                        row_data["APPLICATION_NUMBER"] = application_no
                        row_data["ERROR_REASON"] = "SUCCESS (updated)"
                    else:
                        # INSERT new record
                        record_id = str(uuid.uuid4())
                        type_of_work = self._first_non_blank_value(row.get("TYPE_OF_WORK"))
                        batch_code = self._first_non_blank_value(row.get("BATCH_CODE"))

                        if self._is_blank_value(type_of_work):
                            type_of_work = None
                        else:
                            type_of_work = str(type_of_work).strip()

                        if self._is_blank_value(batch_code):
                            batch_code = None
                        else:
                            batch_code = str(batch_code).strip()

                        record_data = {
                            "APPLICATION": {
                                "ASSIGNED_DATE": parse_datetime(self._first_non_blank_value(row.get("ASSIGNED_DATE"))),
                                "TYPE_OF_WORK": type_of_work,
                            },
                            "LOAN_INFO": {
                                "client_code": client_code,
                                "client_name": client_name,
                                "LOAN_ACCOUNT_NUMBER": loan_account,
                                "LOAN_REQUESTER_NAME": self._first_non_blank_value(row.get("LOAN_REQUESTER_NAME"))
                            },
                            "PROPERTY_INFO": {
                                "STATE": self._first_non_blank_value(row.get("STATE"))
                            }
                        }
                        report_payload = self._build_sarfaesi_payload_from_row(row)
                        assigned_date = self._first_non_blank_value(row.get("ASSIGNED_DATE"))
                        if "assignment_agreement_date" not in report_payload and not self._is_blank_value(assigned_date):
                            report_payload["assignment_agreement_date"] = parse_datetime(assigned_date)
                        report_payload["report_source"] = "Manual Excel"
                        report_payload["has_document"] = False

                        business_code = self.repo.get_next_business_code(client_code)
                        
                        record = {
                            "business_code": business_code,
                            "data": record_data,
                            "source_type": "Bulk Upload",
                            "batch_code": batch_code,
                        }

                        db = SessionLocal()
                        try:
                            self.repo.save_record(
                                record_id,
                                record,
                                audit_user=audit_user,
                                db=db,
                                auto_commit=False,
                            )

                            sarfaesi_service = SarfaesiService(db)
                            sarfaesi_service.generate_sarfaesi_from_application(
                                business_code,
                                audit_user,
                                manual_payload=report_payload,
                                report_source="Manual Excel",
                                has_document=False,
                                auto_commit=False,
                            )
                            db.commit()
                        except Exception:
                            db.rollback()
                            raise
                        finally:
                            db.close()

                        row_data["APPLICATION_NUMBER"] = business_code
                        row_data["ERROR_REASON"] = "SUCCESS"
                        

                except Exception as e:
                    traceback.print_exc()
                    print("SAVE ERROR:", str(e))
                    row_data["ERROR_REASON"] = f"Unable to save record: {str(e)}"
            else:
                row_data["ERROR_REASON"] = error_reason

            result_rows.append(row_data)

        result_df = pd.DataFrame(result_rows)
        result_df.rename(columns=DISPLAY_COLUMN_MAP, inplace=True)
        result_df.columns = [col.upper() for col in result_df.columns]

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            result_df.to_excel(writer, index=False, sheet_name="UPLOAD_RESULT")
            worksheet = writer.sheets["UPLOAD_RESULT"]

            max_row = worksheet.max_row
            max_col = worksheet.max_column

            for cell in worksheet[1]:
                cell.font = Font(bold=True)
            worksheet.freeze_panes = worksheet["A2"]
            worksheet.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"

            success_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
            error_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

            for row in worksheet.iter_rows(min_row=2, max_row=max_row):
                for cell in row:
                    if cell.column == max_col:
                        if cell.value == "SUCCESS":
                            cell.fill = success_fill
                        elif cell.value:
                            cell.fill = error_fill

            for column_cells in worksheet.columns:
                max_length = max(
                    len(str(cell.value)) if cell.value else 0
                    for cell in column_cells
                )
                worksheet.column_dimensions[
                    get_column_letter(column_cells[0].column)
                ].width = min(max_length + 3, 40)

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=bulk_upload_result.xlsx"
            }
        )

    def get_record(self, record_id: str) -> Optional[Dict]:
        return self.repo.get_record(record_id)

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
        assigned_to: Optional[datetime] = None
    ) -> List[Dict]:
        return self.repo.list_records(
            client_name=client_name,
            client_code=client_code,
            loan_account_number=loan_account_number,
            batch_code=batch_code,
            borrower_name=borrower_name,
            location=location,
            type_of_work=type_of_work,
            assigned_from=assigned_from,
            assigned_to=assigned_to,
        )

    def search_records(self, query: str) -> List[Dict]:
        return self.repo.search_records(query)

    def update_record(self, record_id: str, data: Dict, audit_user: AuditUser | None = None) -> Dict:
        normalized = data
        loan_account_number = (
            normalized.get("LOAN_INFO", {}).get("LOAN_ACCOUNT_NUMBER")
            or normalized.get("LOAN_INFO", {}).get("loan_account_number")
        )
        if loan_account_number:
            existing = self.repo.get_record(record_id)
            existing_loan = existing.get("loan_account_number") if existing else None
            if existing_loan:
                if str(loan_account_number).strip() != str(existing_loan).strip():
                    raise HTTPException(
                        status_code=422,
                        detail="Loan account number cannot be changed once it has been set.",
                    )
            elif self.repo.loan_account_exists(
                str(loan_account_number).strip(),
                exclude_record_id=record_id,
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Loan account already exists",
                )
        return self.repo.update_record(
            record_id,
            normalized,
            audit_user=audit_user,
        )

    def delete_record(self, record_id: str, audit_user: AuditUser | None = None) -> bool:
        return self.repo.delete_record(record_id, audit_user=audit_user)

    def get_document_url(self, record_id: str, filename: str) -> Optional[str]:
        record = self.get_record(record_id)
        if not record:
            return None
        business_code = record.get("business_code")
        if not business_code:
            return None
        s3_key = f"{business_code}/original-document/{filename}"
        from app.gateways.s3_gateway import S3Gateway
        gateway = S3Gateway()
        return gateway.generate_presigned_url(s3_key)

    def download_template(self):
        columns = [
            "BATCH CODE",
            "TYPE OF SERVICE",
            "DATE OF ASSIGN",
            "NIYAMTEK USER ID OR NAME",
            "CLIENT ID (CODE)",
            "Company Name",
            "LOAN ACCOUNT NO.",
            "NAME OF BORROWER",
            "Trust Number",
            "Assignment agreement Date",
            "AO NAME",
            "BRANCH",
            "STATE",
            "Region",
            "Property Address",
            "Property Description",
            "Borrower Address",
            "Borrower Address_(Also At)",
            "Co-Borrower Name_1",
            "Co-Borrower Address_1",
            "Co-Borrower Address_1 (Also At)",
            "Co-Borrower Name_2",
            "Co-Borrower Address_2",
            "Co-Borrower Address_2 (Also At)",
            "Co-Borrower Name_3",
            "Co-Borrower Address_3",
            "Co-Borrower Address_3 (Also At)",
            "Co-Borrower Name_4",
            "Co-Borrower Address_4",
            "Co-Borrower Address_4 (Also At)",
            "Co-Borrower Name_5",
            "Co-Borrower Address_5",
            "Co-Borrower Address_5 (Also At)",
            "Co-Borrower Name_6",
            "Co-Borrower Address_6",
            "Guarantor Name_1",
            "Guarantor Address_1",
            "Guarantor Name_2",
            "Guarantor Address_2",
            "Date of NPA",
            "DPD as on Notice Issuance Date",
            "Disbursement Type (Loan / OD / CC / HL / BLG)",
            "Disbursal Date",
            "Disbursal Amount",
            "Loan Agreement Date",
            "Loan Amount",
            "Loan Amount in Words",
            "Future Principle",
            "Principal Outstanding",
            "Instalment_overdue_amount",
            "Interest on Termination",
            "Late Payment Penalty",
            "Cheque Bounce Charges (Including Others)",
            "Other Amount",
            "Foreclosure Charges",
            "Total Outstanding",
            "FCL (As on Date)",
            "Total Outstanding in words",
            "13 (2) NOTICE AMT",
            "13(2) Demand Notice (date)",
            "Dispatch Date",
            "Pasting Date (optional)",
            "Delivered address",
            "Undelivered address",
            "Total address",
            "13(2) Date of Publication",
            "Publication Details : (Names of News Papers) & Language Name : (English)",
            "Publication Details : (Names of News Papers) & Vernacular Language Name : (Tamil,Hindi,malayalam,etc...)",
        ]

        df = pd.DataFrame(columns=columns)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="BULK_UPLOAD_TEMPLATE")
            worksheet = writer.sheets["BULK_UPLOAD_TEMPLATE"]
            for cell in worksheet[1]:
                cell.font = Font(bold=True)
            worksheet.freeze_panes = "A2"
            for column_cells in worksheet.columns:
                max_length = max(
                    len(str(cell.value)) if cell.value else 0
                    for cell in column_cells
                )
                worksheet.column_dimensions[
                    get_column_letter(column_cells[0].column)
                ].width = max_length + 5

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=BULK_UPLOAD_TEMPLATE.xlsx"
            }
        )

    def _first_non_blank_value(self, value: Any) -> Any:
        if isinstance(value, pd.Series):
            for item in value.tolist():
                if not self._is_blank_value(item):
                    return item
            return None
        return value

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace(r"[^A-Z0-9]+", "_", regex=True)
            .str.replace(r"_+", "_", regex=True)
            .str.strip("_")
        )
        return df

    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        column_map = {}
        for col in df.columns:
            if "CLIENT" in col and "CODE" in col:
                column_map[col] = "CLIENT_CODE"
            elif "CLIENT" in col:
                column_map[col] = "CLIENT_NAME"
            elif "ACCOUNT" in col:
                column_map[col] = "LOAN_ACCOUNT_NUMBER"
            elif col in {"NAME_OF_BORROWER", "BORROWER_NAME"}:
                column_map[col] = "LOAN_REQUESTER_NAME"
            elif col == "BORROWER_ADDRESS":
                column_map[col] = "BORROWER_ADDRESS"
            elif col == "BORROWER_ADDRESS_ALSO_AT":
                column_map[col] = "BORROWER_ADDRESS_ALSO_AT"
            elif "CO_BORROWER_NAME_" in col:
                column_map[col] = col
            elif "CO_BORROWER_ADDRESS_" in col:
                column_map[col] = col
            elif "BORROWER" in col:
                column_map[col] = "LOAN_REQUESTER_NAME"
            elif "LOCATION" in col or "STATE" in col:
                column_map[col] = "STATE"
            elif "TYPE" in col and ("WORK" in col or "SERVICE" in col):
                column_map[col] = "TYPE_OF_WORK"
            elif "DISBURSEMENT" in col:
                column_map[col] = "DISBURSEMENT_TYPE"
            elif "BATCH" in col and "CODE" in col:
                column_map[col] = "BATCH_CODE"
            elif "ASSIGN" in col:
                column_map[col] = "ASSIGNED_DATE"
            elif "COMPANY_NAME" in col:
                column_map[col] = "CLIENT_NAME"
            elif col in {"LOAN_ACCOUNT_NO", "LOAN_ACCOUNT_NUMBER"}:
                column_map[col] = "LOAN_ACCOUNT_NUMBER"
            elif "CLIENT_ID" in col or col == "CLIENT_CODE":
                column_map[col] = "CLIENT_CODE"
            elif "NIYAMTEK_USER" in col:
                column_map[col] = "NIYAMTEK_USER"
        df.rename(columns=column_map, inplace=True)
        return df