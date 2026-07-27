from sqlalchemy.orm import Session
from decimal import Decimal
from app.db.models.application import Application
from app.db.models.safari_notice import SarfaesiMaster
from app.db.models.extracted_data import ApplicationChecklist
from app.db.models.document_extraction import Document
from app.db.models.extracted_data import (
    ExtractedSanctionLetter,
    ExtractedLoanAgreement,
    ExtractedMODT,
    ExtractedMODTProperty,
    ExtractedSalesDeed,
    ExtractedForeclosureStatement,
    ExtractedStatementOfAccount
)
from app.db.models.application import Application
from app.utils.date_utils import parse_datetime
from app.db.versioning import clone_version, close_version, live_filter, mark_created
from app.services.sarfaesi_mapper import MANUAL_EDITABLE_FIELDS

MASTER_FIELD_MAP = {
    "application_number": "application_number",
    "niyamtek_user": "niyamtek_user",
    "client_code": "client_code",
    "company_name": "company_name",
    "loan_account_number": "loan_account_no",
    "trust_number": "trust_number",
    "assignment_agreement_date": "assignment_agreement_date",
    "ao_name": "ao_name",
    "branch": "branch",
    "state": "state",
    "region": "region",
    "property_address": "property_address",
    "borrower_name": "borrower_name",
    "location": "state",
    "arc_name": "company_name",
    "borrower_address": "borrower_address",
    "borrower_address_also_at": "borrower_address_alt",
    "co_borrower_1_name": "co_borrower_1_name",
    "co_borrower_1_address": "co_borrower_1_address",
    "co_borrower_1_address_also_at": "co_borrower_1_address_alt",
    "co_borrower_2_name": "co_borrower_2_name",
    "co_borrower_2_address": "co_borrower_2_address",
    "co_borrower_2_address_also_at": "co_borrower_2_address_alt",
    "co_borrower_3_name": "co_borrower_3_name",
    "co_borrower_3_address": "co_borrower_3_address",
    "co_borrower_3_address_also_at": "co_borrower_3_address_alt",
    "co_borrower_4_name": "co_borrower_4_name",
    "co_borrower_4_address": "co_borrower_4_address",
    "co_borrower_4_address_also_at": "co_borrower_4_address_alt",
    "co_borrower_5_name": "co_borrower_5_name",
    "co_borrower_5_address": "co_borrower_5_address",
    "co_borrower_5_address_also_at": "co_borrower_5_address_alt",
    "co_borrower_6_name": "co_borrower_6_name",
    "co_borrower_6_address": "co_borrower_6_address",
    "property_description": "property_description",
    "guarantor_name_1": "guarantor_1_name",
    "guarantor_address_1": "guarantor_1_address",
    "guarantor_name_2": "guarantor_2_name",
    "guarantor_address_2": "guarantor_2_address",
    "date_of_npa": "npa_date",
    "dpd_as_on_notice": "dpd",
    "disbursement_type": "disbursement_type",
    "sec_13_2_notice_date": "notice_13_2_date",
    "notice_13_2_amount": "notice_13_2_amount",
    "notice_dispatch_date": "notice_dispatch_date",
    "notice_pasting_date": "notice_pasting_date",
    "delivery_status": "delivery_status",
    "delivered_address": "delivered_address",
    "undelivered_address": "undelivered_address",
    "total_address": "total_address",
    "publication_date_13_2": "publication_date_13_2",
    "publication_english_13_2": "publication_english_13_2",
    "publication_local_13_2": "publication_local_13_2",
    "disbursal_date": "disbursal_date",
    "disbursal_amount": "disbursal_amount",
    "loan_agreement_date": "loan_agreement_date",
    "loan_amount": "loan_amount",
    "loan_amount_words": "loan_amount_words",
    "future_principal": "future_principal",
    "principal_outstanding": "principal_outstanding",
    "instalment_overdue_amount": "instalment_overdue",
    "interest_on_termination": "interest_on_termination",
    "late_payment_penalty": "late_payment_penalty",
    "cheque_bounce_charges": "cheque_bounce_charges",
    "other_amount": "other_amount",
    "foreclosure_charges": "foreclosure_charges",
    "total_outstanding": "total_outstanding",
    "total_outstanding_words": "total_outstanding_words",
    "as_on_date": "updated_at",
}

MASTER_FIELD_TYPES = {
    column.name: column.type
    for column in SarfaesiMaster.__table__.columns
}



class ReportRepository:

    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # HELPER → SAFE INT CONVERSION
    # =====================================================
    def _to_int(self, value):
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return int(value)

        if isinstance(value, Decimal):
            return int(value)

        try:
            import re

            cleaned = str(value).strip().replace(",", "")
            cleaned = re.sub(r"(?i)rs\.?", "", cleaned)
            cleaned = re.sub(r"[^\d.\-]", "", cleaned)
            if cleaned in {"", "-", ".", "-."}:
                return None

            return int(float(cleaned))
        except Exception:
            return None

    def _to_decimal(self, value):
        if value is None:
            return None

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        try:
            import re

            cleaned = str(value).strip().replace(",", "")
            cleaned = re.sub(r"(?i)rs\.?", "", cleaned)
            cleaned = re.sub(r"[^\d.\-]", "", cleaned)
            if cleaned in {"", "-", ".", "-."}:
                return None
            return Decimal(cleaned)
        except Exception:
            return None

    def _first_non_empty(self, *values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            return value
        return None

    def _build_modt_property_description(self, modt: ExtractedMODT):
        if not modt:
            return None
        rows = (
            self.db.query(ExtractedMODTProperty)
            .filter(ExtractedMODTProperty.modt_id == modt.id)
            .order_by(ExtractedMODTProperty.property_index.asc(), ExtractedMODTProperty.id.asc())
            .all()
        )
        chunks = [r.property_description.strip() for r in rows if r.property_description and r.property_description.strip()]
        return " | ".join(chunks) if chunks else None

    def _extract_property_index(self, attribute_code: str):
        import re
        if attribute_code == "property_description":
            return 1
        m = re.match(r"^property_description_(\d+)$", attribute_code or "")
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    def _build_report_property_description_list(self, checklist_rows, sales_deed_rows):
        indexed = {}
        for row in checklist_rows:
            if row.pair_code != "MODT_SD":
                continue
            if not str(row.attribute_code or "").startswith("property_description"):
                continue
            idx = self._extract_property_index(row.attribute_code) or 1
            value = self._first_non_empty(row.document_b_value)
            if value is None:
                continue
            value = str(value).strip()
            if not value:
                continue
            indexed[idx] = value

        if indexed:
            return [indexed[k] for k in sorted(indexed.keys())]

        fallback_raw = []
        for sd in sales_deed_rows:
            txt = (sd.raw_description or "").strip()
            if txt:
                fallback_raw.append(txt)
        if fallback_raw:
            return fallback_raw

        fallback_addr = []
        for sd in sales_deed_rows:
            txt = (sd.property_address or "").strip()
            if txt:
                fallback_addr.append(txt)
        if fallback_addr:
            return fallback_addr
        return []

    def _format_report_property_descriptions(self, items):
        cleaned = [str(v).strip() for v in (items or []) if v is not None and str(v).strip()]
        if not cleaned:
            return None
        if len(cleaned) == 1:
            return cleaned[0]
        return "\n\n".join([f"Property {i + 1}: {v}" for i, v in enumerate(cleaned)])

    def _ensure_report_created(self, application_number: str, audit_user=None):
        report = self.get_report(application_number)
        if report:
            return report

        application = (
            self.db.query(Application)
            .filter(Application.business_code == application_number, *live_filter(Application))
            .first()
        )
        report = SarfaesiMaster(application_number=application_number)
        created_by = getattr(application, "created_by", None) or getattr(audit_user, "audit_actor", None)
        mark_created(report, audit_user)
        if created_by:
            report.created_by = created_by
            report.updated_by = created_by
        if application and getattr(application, "batch_code", None):
            report.batch_code = application.batch_code
        report.version = 1
        report.is_active = True
        report.is_deleted = False
        self.db.add(report)
        self.db.flush()
        return report

    # =====================================================
    # GET EXISTING REPORT (NO GENERATION)
    # =====================================================
    def get_report(self, application_number: str):
        live_report = self.db.query(SarfaesiMaster).filter(
            SarfaesiMaster.application_number == application_number,
            *live_filter(SarfaesiMaster)
        ).first()
        if live_report:
            return live_report

        # Fallback to the latest non-deleted version so bulk download can still
        # read the SARFAESI master row even if an older active flag was cleared.
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

    def mark_rerun_report(
        self,
        application_number: str,
        value: int = 1,
        audit_user=None,
        auto_commit: bool = True,
    ):
        report = self._ensure_report_created(application_number, audit_user=audit_user)
        report.updated_by = getattr(audit_user, "audit_actor", None) or report.updated_by
        if value is not None:
            # `rerun_report` is the flag consumed by the report workflow.
            # Keep the report row itself active; only toggle the rerun marker.
            report.rerun_report = int(value)

        desired_status = "Not_Available" if (value or 0) == 1 else "Available"
        application = (
            self.db.query(Application)
            .filter(
                Application.business_code == application_number,
                *live_filter(Application),
            )
            .first()
        )
        if application and getattr(application, "report_status", None) != desired_status:
            close_version(application, audit_user)
            self.db.flush()
            updated_application = clone_version(
                application,
                audit_user,
                report_status=desired_status,
            )
            self.db.add(updated_application)
        if auto_commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(report)
        return report

    # =====================================================
    # GENERATE REPORT (CHECKLIST FIRST, EXTRACTED FALLBACK)
    # =====================================================
    def generate_report(self, application_number: str):

        # --------------------------------------------------
        # STEP 1 → Reuse/Create live report row
        # --------------------------------------------------
        manual_entry_fields = MANUAL_EDITABLE_FIELDS

        report = self._ensure_report_created(application_number)

        preserved_manual_values = {}
        for field in manual_entry_fields:
            preserved_manual_values[field] = getattr(report, field, None)

        for field, value in preserved_manual_values.items():
            setattr(report, field, value)

        application = (
            self.db.query(Application)
            .filter(Application.business_code == application_number, *live_filter(Application))
            .first()
        )
        if application:
            report.record_id = application.record_id
            # Account number comes from the application's consolidated fields
            report.loan_account_number = application.loan_account_number
            if getattr(application, "batch_code", None) and not getattr(report, "batch_code", None):
                report.batch_code = application.batch_code

        # --------------------------------------------------
        # STEP 2 → FETCH LATEST EXTRACTED DOCUMENTS
        # --------------------------------------------------
        sanction = self.db.query(ExtractedSanctionLetter).filter(
            ExtractedSanctionLetter.application_number == application_number,
            *live_filter(ExtractedSanctionLetter),
        ).join(
            Document, Document.id == ExtractedSanctionLetter.document_id
        ).filter(
            *live_filter(Document)
        ).order_by(ExtractedSanctionLetter.created_at.desc()).first()

        loan = self.db.query(ExtractedLoanAgreement).filter(
            ExtractedLoanAgreement.application_number == application_number,
            *live_filter(ExtractedLoanAgreement),
        ).join(
            Document, Document.id == ExtractedLoanAgreement.document_id
        ).filter(
            *live_filter(Document)
        ).order_by(ExtractedLoanAgreement.created_at.desc()).first()

        modt = self.db.query(ExtractedMODT).filter(
            ExtractedMODT.application_number == application_number,
            *live_filter(ExtractedMODT),
        ).join(
            Document, Document.id == ExtractedMODT.document_id
        ).filter(
            *live_filter(Document)
        ).order_by(ExtractedMODT.created_at.desc()).first()

        sales_deed_rows = self.db.query(ExtractedSalesDeed).join(
            Document, Document.id == ExtractedSalesDeed.document_id
        ).filter(
            ExtractedSalesDeed.application_number == application_number,
            *live_filter(ExtractedSalesDeed),
            *live_filter(Document),
        ).order_by(ExtractedSalesDeed.created_at.asc(), ExtractedSalesDeed.id.asc()).all()
        sales_deed = sales_deed_rows[-1] if sales_deed_rows else None

        foreclosure = self.db.query(ExtractedForeclosureStatement).filter(
            ExtractedForeclosureStatement.application_number == application_number,
            *live_filter(ExtractedForeclosureStatement),
        ).join(
            Document, Document.id == ExtractedForeclosureStatement.document_id
        ).filter(
            *live_filter(Document)
        ).order_by(ExtractedForeclosureStatement.created_at.desc()).first()

        soa = self.db.query(ExtractedStatementOfAccount).filter(
            ExtractedStatementOfAccount.application_number == application_number,
            *live_filter(ExtractedStatementOfAccount),
        ).join(
            Document, Document.id == ExtractedStatementOfAccount.document_id
        ).filter(
            *live_filter(Document)
        ).order_by(ExtractedStatementOfAccount.created_at.desc()).first()

        has_extracted_document = any([sanction, loan, modt, sales_deed_rows, foreclosure, soa])
        if has_extracted_document:
            if getattr(report, "report_source", None) != "Manual Excel":
                report.report_source = "Extracted Document"
        elif not getattr(report, "report_source", None):
            report.report_source = "Application Creation"
        if has_extracted_document:
            report.has_document = True
        elif getattr(report, "has_document", None) is None:
            report.has_document = False

        # --------------------------------------------------
        # STEP 3 → CHECKLIST MAP (PRIORITY SOURCE)
        # --------------------------------------------------
        checklist_value_map = {}
        manual_fields = MANUAL_EDITABLE_FIELDS
        checklist_rows = self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.application_number == application_number,
            *live_filter(ApplicationChecklist)
        ).all()

        for row in checklist_rows:
            field = self._map_checklist_attribute_to_report_field(row.attribute_code)
            if field in manual_fields:
                continue
            if field == "property_description":
                # Handle property descriptions as a grouped list below so multiple
                # checklist rows are preserved in the final report text.
                continue
            if not hasattr(report, field):
                continue
            # For SL_LA date mismatch, prefer Loan Agreement date (document_b_value).
            if (
                row.pair_code == "SL_LA"
                and row.attribute_code == "date"
                and row.match_status == "MISMATCH"
            ):
                override_value = self._first_non_empty(row.document_b_value, row.document_a_value)
            elif (
                row.pair_code == "MODT_SD"
                and row.attribute_code.startswith("property_description")
            ):
                # For report description, prioritize Sale Deed side for MODT vs SD pair.
                override_value = self._first_non_empty(row.document_b_value, row.document_a_value)
            else:
                override_value = self._first_non_empty(row.document_a_value, row.document_b_value)
            if override_value is None:
                continue
            checklist_value_map[field] = override_value

        # --------------------------------------------------
        # STEP 4 → BASE EXTRACTOR MAPPING (FALLBACK SOURCE)
        # --------------------------------------------------

        # --- Sanction Letter ---
        if sanction:
            report.borrower_name = self._first_non_empty(
                checklist_value_map.get("borrower_name"),
                sanction.borrower_name,
                application.loan_requester_name if application else None,
                report.borrower_name,
            )
            report.borrower_address = self._first_non_empty(
                checklist_value_map.get("borrower_address"),
                sanction.borrower_address,
                report.borrower_address,
            )
            report.borrower_address_also_at = self._first_non_empty(
                checklist_value_map.get("borrower_address_also_at"),
                sanction.borrower_address_also_at,
                report.borrower_address_also_at,
            )

            for i in range(1, 6):
                name_field = f"co_borrower_{i}_name"
                addr_field = f"co_borrower_{i}_address"
                addr_also_at_field = f"co_borrower_{i}_address_also_at"

                setattr(
                    report,
                    name_field,
                    self._first_non_empty(
                        checklist_value_map.get(name_field),
                        getattr(sanction, name_field, None),
                        getattr(report, name_field, None),
                    ),
                )
                setattr(
                    report,
                    addr_field,
                    self._first_non_empty(
                        checklist_value_map.get(addr_field),
                        getattr(sanction, addr_field, None),
                        getattr(report, addr_field, None),
                    ),
                )
                setattr(
                    report,
                    addr_also_at_field,
                    self._first_non_empty(
                        checklist_value_map.get(addr_also_at_field),
                        getattr(sanction, addr_also_at_field, None),
                        getattr(report, addr_also_at_field, None),
                    ),
                )
        else:
            report.borrower_name = self._first_non_empty(
                checklist_value_map.get("borrower_name"),
                application.loan_requester_name if application else None,
                report.borrower_name,
            )

        # --- Loan Agreement ---
        if loan:
            report.loan_agreement_date = parse_datetime(
                self._first_non_empty(
                    checklist_value_map.get("loan_agreement_date"),
                    loan.loan_agreement_date,
                    report.loan_agreement_date,
                )
            )
            report.loan_amount = self._to_decimal(
                self._first_non_empty(
                    checklist_value_map.get("loan_amount"),
                    loan.loan_amount,
                    report.loan_amount,
                )
            )
        else:
            report.loan_amount = self._to_decimal(
                self._first_non_empty(
                    checklist_value_map.get("loan_amount"),
                    report.loan_amount,
                )
            )

        report.property_address = self._first_non_empty(
            checklist_value_map.get("property_address"),
            sanction.property_address if sanction else None,
            loan.property_address if loan else None,
            report.property_address,
        )

        # Map directly from the extracted loan agreement; fall back to any
        # checklist override or the report's existing value when there's no
        # extracted loan agreement to derive it from (e.g. Manual Excel reports).
        report.loan_amount_words = self._first_non_empty(
            checklist_value_map.get("loan_amount_words"),
            loan.loan_amount_in_words if loan else None,
            report.loan_amount_words,
        )

        # --- MODT ---
        property_description_items = self._build_report_property_description_list(checklist_rows, sales_deed_rows)
        if property_description_items:
            report.schedule_property_descriptions = property_description_items
            report.property_description = self._format_report_property_descriptions(property_description_items)

        # --- Foreclosure ---
        if foreclosure:
            report.future_principal = self._to_decimal(
                self._first_non_empty(
                    checklist_value_map.get("future_principal"),
                    report.future_principal,
                    foreclosure.outstanding_principal,
                )
            )
            report.principal_outstanding = self._to_decimal(
                self._first_non_empty(checklist_value_map.get("principal_outstanding"), foreclosure.principal_outstanding_overdue, report.principal_outstanding)
            )
            report.instalment_overdue_amount = self._to_decimal(
                self._first_non_empty(checklist_value_map.get("instalment_overdue_amount"), foreclosure.instalment_overdue_amount_interest_overview, report.instalment_overdue_amount)
            )
            report.interest_on_termination = self._to_decimal(
                self._first_non_empty(checklist_value_map.get("interest_on_termination"), foreclosure.interest_till_date, report.interest_on_termination)
            )
            report.late_payment_penalty = self._to_decimal(
                self._first_non_empty(checklist_value_map.get("late_payment_penalty"), foreclosure.late_payment_fee, report.late_payment_penalty)
            )
            report.cheque_bounce_charges = self._to_decimal(
                self._first_non_empty(checklist_value_map.get("cheque_bounce_charges"), foreclosure.cheque_bounce_charges, report.cheque_bounce_charges)
            )
            report.other_amount = self._to_decimal(
                self._first_non_empty(checklist_value_map.get("other_amount"), foreclosure.other_amount_charges, report.other_amount)
            )
            report.foreclosure_charges = self._to_decimal(
                self._first_non_empty(checklist_value_map.get("foreclosure_charges"), foreclosure.foreclosure_charges, report.foreclosure_charges)
            )
            report.total_outstanding = self._to_decimal(
                self._first_non_empty(checklist_value_map.get("total_outstanding"), foreclosure.total_amount_payable, report.total_outstanding)
            )
            report.as_on_date = parse_datetime(
                self._first_non_empty(checklist_value_map.get("as_on_date"), foreclosure.document_date, report.as_on_date)
            )
            report.fcl_as_on_date = parse_datetime(
                self._first_non_empty(
                    checklist_value_map.get("fcl_as_on_date"),
                    foreclosure.foreclosure_calculation_date,
                    report.fcl_as_on_date,
                )
            )

        # --- Application level fallback fields used in legacy export ---
        report.location = self._first_non_empty(
            checklist_value_map.get("location"),
            application.state if application else report.location,
        )
        report.arc_name = self._first_non_empty(
            checklist_value_map.get("arc_name"),
            application.client_name if application else report.arc_name,
        )

        # --------------------------------------------------
        # STEP 5 → APPLY REMAINING CHECKLIST OVERRIDES
        # --------------------------------------------------
        for field, raw_value in checklist_value_map.items():
            if field in manual_fields:
                continue
            if field == "loan_account_number":
                # Keep application loan account number as authoritative.
                continue
            master_field = MASTER_FIELD_MAP.get(field, field)
            if not hasattr(report, master_field):
                continue

            column_type = MASTER_FIELD_TYPES.get(master_field)
            if column_type is None:
                continue
            column_type_str = str(column_type).upper()
            value = raw_value

            if "BIGINT" in column_type_str or "INTEGER" in column_type_str:
                value = self._to_int(value)
            elif "DATETIME" in column_type_str or "DATE" in column_type_str:
                value = parse_datetime(value)

            setattr(report, master_field, value)

        # --------------------------------------------------
        # FINAL SAVE
        # --------------------------------------------------
        self.db.commit()
        self.db.refresh(report)

        return report

    def _map_checklist_attribute_to_report_field(self, attribute_code: str) -> str:
        mapping = {
            "address": "borrower_address",
            "date": "loan_agreement_date",
            "property_address": "property_address",
            "property_description": "property_description",
            "niyamtek_user": "niyamtek_user",
            "client_code": "client_code",
            "company_name": "company_name",
            "trust_number": "trust_number",
            "assignment_agreement_date": "assignment_agreement_date",
            "ao_name": "ao_name",
            "branch": "branch",
            "state": "state",
            "region": "region",
            "borrower_name": "borrower_name",
            "loan_account_number": "loan_account_number",
            "loan_amount": "loan_amount",
            "loan_amount_words": "loan_amount_words",
            "arc_name": "arc_name",
            "date_of_npa": "date_of_npa",
            "dpd_as_on_notice": "dpd_as_on_notice",
            "disbursal_date": "disbursal_date",
            "disbursal_amount": "disbursal_amount",
            "future_principal": "future_principal",
            "principal_outstanding": "principal_outstanding",
            "instalment_overdue_amount": "instalment_overdue_amount",
            "interest_on_termination": "interest_on_termination",
            "late_payment_penalty": "late_payment_penalty",
            "cheque_bounce_charges": "cheque_bounce_charges",
            "other_amount": "other_amount",
            "foreclosure_charges": "foreclosure_charges",
            "total_outstanding": "total_outstanding",
            "total_outstanding_words": "total_outstanding_words",
            "as_on_date": "as_on_date",
    "sec_13_2_notice_date": "notice_13_2_date",
            "location": "location",
            "borrower_address_also_at": "borrower_address_also_at",
            "co_borrower_1_address_also_at": "co_borrower_1_address_also_at",
            "co_borrower_2_address_also_at": "co_borrower_2_address_also_at",
            "co_borrower_3_address_also_at": "co_borrower_3_address_also_at",
            "co_borrower_4_address_also_at": "co_borrower_4_address_also_at",
            "co_borrower_5_address_also_at": "co_borrower_5_address_also_at",
            "co_borrower_name_1": "co_borrower_1_name",
            "co_borrower_address_1": "co_borrower_1_address",
            "co_borrower_name_2": "co_borrower_2_name",
            "co_borrower_address_2": "co_borrower_2_address",
            "co_borrower_name_3": "co_borrower_3_name",
            "co_borrower_address_3": "co_borrower_3_address",
            "co_borrower_name_4": "co_borrower_4_name",
            "co_borrower_address_4": "co_borrower_4_address",
            "co_borrower_name_5": "co_borrower_5_name",
            "co_borrower_address_5": "co_borrower_5_address",
    "co_borrower_name_6": "co_borrower_6_name",
    "co_borrower_address_6": "co_borrower_6_address",
    "property_description": "property_description",
    "guarantor_name_1": "guarantor_1_name",
            "guarantor_address_1": "guarantor_1_address",
            "guarantor_name_2": "guarantor_2_name",
            "guarantor_address_2": "guarantor_2_address",
            "disbursement_type": "disbursement_type",
            "notice_13_2_amount": "notice_13_2_amount",
            "notice_dispatch_date": "notice_dispatch_date",
            "notice_pasting_date": "notice_pasting_date",
            "delivery_status": "delivery_status",
            "delivered_address": "delivered_address",
            "undelivered_address": "undelivered_address",
            "total_address": "total_address",
            "publication_date_13_2": "publication_date_13_2",
            "publication_english_13_2": "publication_english_13_2",
            "publication_local_13_2": "publication_local_13_2",
        }
        return mapping.get(attribute_code, attribute_code)
    
    # =====================================================
# UPDATE REPORT (Manual Edit)
# =====================================================
    def update_report(self, application_number: str, update_data: dict, audit_user=None):

        report = self.db.query(SarfaesiMaster).filter(
            SarfaesiMaster.application_number == application_number,
            *live_filter(SarfaesiMaster)
        ).first()

        if not report:
            # If no report exists, create new
            report = self._ensure_report_created(application_number, audit_user=audit_user)

        manual_entry_fields = MANUAL_EDITABLE_FIELDS
        changed_any = False
        changed_non_manual = False
        schedule_list_updated = False
        updates = {}

        # Accept the legacy UI field name as an alias for the canonical column.
        normalized_update_data = dict(update_data)
        if "description_of_schedule_property" in normalized_update_data and "property_description" not in normalized_update_data:
            normalized_update_data["property_description"] = normalized_update_data["description_of_schedule_property"]

        for key, value in normalized_update_data.items():
            if key not in MANUAL_EDITABLE_FIELDS and key != "schedule_property_descriptions":
                continue

            master_field = MASTER_FIELD_MAP.get(key, key)
            if not hasattr(report, master_field):
                continue

            column_type = MASTER_FIELD_TYPES.get(master_field)
            if column_type is None:
                continue

            column_type_str = str(column_type).upper()
            current_value = getattr(report, master_field, None)
            is_date_column = "DATETIME" in column_type_str or "DATE" in column_type_str

            # Convert numeric safely
            if key == "schedule_property_descriptions":
                if value is None:
                    value = None
                elif isinstance(value, list):
                    value = [str(v).strip() for v in value if v is not None and str(v).strip()]
                else:
                    value = [str(value).strip()] if str(value).strip() else []
                schedule_list_updated = True
            elif "BIGINT" in column_type_str or "INTEGER" in column_type_str:
                value = self._to_int(value)
            elif "NUMERIC" in column_type_str or "DECIMAL" in column_type_str or "FLOAT" in column_type_str:
                value = self._to_decimal(value)
            elif is_date_column:
                value = parse_datetime(value) if value is not None else None

            if is_date_column:
                normalized_current_value = parse_datetime(current_value) if current_value is not None else None
                changed = normalized_current_value != value
            else:
                changed = current_value != value

            if changed:
                changed_any = True
                if key not in manual_entry_fields:
                    changed_non_manual = True
                updates[master_field] = value

        if schedule_list_updated:
            updates["discrepancy_doc"] = None

        if changed_any:
            close_version(report, audit_user)
            self.db.flush()
            report = clone_version(report, audit_user, **updates)
            self.db.add(report)

        self.db.commit()
        self.db.refresh(report)

        return report
