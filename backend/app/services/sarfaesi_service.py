from typing import Any, Dict
from urllib import request
from sqlalchemy.exc import SQLAlchemyError

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from sympy import limit
from app.api.v1.dependencies.auth import AuditUser
from app.api.v1.schemas.sarfaesi_schema import (
    AuctionNoticeDetails,
    AuctionPortalDetails,
    CjmDetails,
    LoanDetails,
    NiyamtekRemarksDetails,
    PhysicalPossessionDetails,
    PostSaleDetails,
    SaleCertificateDetails,
    SarfaesiUpdate,
    SymbolicVacationNoticeDetails,
    Thirteen2Details,
    Thirteen4Details,
)
from app.db.models.application import Application
from app.db.models.client_models import Client
from app.db.models.extracted_data import ExtractedLoanAgreement
from app.db.models.document_extraction import Document
from app.db.models.safari_notice import SarfaesiMaster
from app.db.versioning import close_version, clone_version, live_filter
from app.db.repositories.sarfaesi_repository import SarfaesiRepository
from app.services.sarfaesi_mapper import (
    DOCUMENT_FIELDS,
    EDITABLE_FIELDS,
    FIELD_MAPPING,
    get_source_value,
)


class SarfaesiService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SarfaesiRepository(db)

    _MASTER_COLUMNS = set(SarfaesiMaster.__table__.columns.keys())
    _BLOCKED_UPDATE_FIELDS = {
        "id",
        "application_number",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by",
        "version",
        "is_active",
        "is_deleted",
        "report_source",
        "has_document",
        "rerun_report",
    }
    _SECTION_FIELD_ALIASES = {
        "loan_details": {
            "descriptionOfScheduleProperty": "property_description",
            "description_of_schedule_property": "property_description",
            "property_description": "property_description",
            "propertyAddress": "property_address",
            "mortgaged_property_address": "property_address",
            "address_of_mortgaged_property": "property_address",
            "loan_amount_in_words": "loan_amount_words",
        },
        "13_2_details": {
            "publication_date": "publication_date_13_2",
            "publication_english": "publication_english_13_2",
            "publication_local": "publication_local_13_2",
        },
        "13_4_details": {
            "symbolic_possession_date": "symbolic_possession_date_13_4",
            "symbolic_dispatch_date": "symbolic_dispatch_date_13_4",
            "symbolic_delivery_status": "symbolic_delivery_status_13_4",
            "symbolic_photo": "symbolic_photo_13_4",
            "symbolic_publication_date": "symbolic_publication_date_13_4",
            "symbolic_pub_english": "symbolic_pub_english_13_4",
            "symbolic_pub_local": "symbolic_pub_local_13_4",
        },
        "physical_possession_details": {
            "physical_possession_date": "physical_possession_date",
            "physical_dispatch_date": "physical_dispatch_date",
            "physical_delivery_status": "physical_delivery_status",
            "vacation_notice_moveable": "physical_vacation_notice_moveable",
            "vacation_notice_immoveable": "physical_vacation_notice_immoveable",
        }
    }

    # 🔥 LOAD ALL SOURCES
    def _load_sources(self, application_number: str) -> Dict[str, Any]:
        application = (
            self.db.query(Application)
            .filter(Application.business_code == application_number, *live_filter(Application))
            .first()
        )

        client = None
        document_payload = {}
        extracted_loan_agreement = None

        if application:
            client = (
                self.db.query(Client)
                .filter(Client.client_name == application.client_name, *live_filter(Client))
                .first()
            )
            if not client:
                # Fallback: some clients may have incorrect SCD2 flags (end_date, is_active).
                # Try a more permissive query to ensure we always find the client.
                client = (
                    self.db.query(Client)
                    .filter(Client.client_name == application.client_name, Client.is_deleted == False)
                    .order_by(Client.version.desc(), Client.id.desc())
                    .first()
                )

            document = (
                self.db.query(Document)
                .filter(Document.application_number == application_number, Document.is_deleted == False)
                .order_by(Document.created_at.desc())
                .first()
            )

            if document and document.extracted_data:
                document_payload = document.extracted_data.ai_parsed_output or {}

            extracted_loan_agreement = (
                self.db.query(ExtractedLoanAgreement)
                .filter(
                    ExtractedLoanAgreement.application_number == application_number,
                    ExtractedLoanAgreement.is_deleted == False,
                )
                .order_by(ExtractedLoanAgreement.created_at.desc())
                .first()
            )

        return {
            "application": application,
            "client": client,
            "document": document_payload,
            "extracted_loan_agreement": extracted_loan_agreement,
        }
    
    def _format_response(self, s):
        resolved_client_code = None
        application_rel = getattr(s, "application", None)
        client_name = getattr(application_rel, "client_name", None)
        if not client_name:
            client_name = getattr(s, "company_name", None)
        if not client_name:
            # Fallback: query application directly if SQLAlchemy relationship is None
            app_direct = (
                self.db.query(Application)
                .filter(Application.business_code == s.application_number, *live_filter(Application))
                .first()
            )
            if app_direct:
                client_name = app_direct.client_name
        if client_name:
            live_client = (
                self.db.query(Client)
                .filter(Client.client_name == client_name, *live_filter(Client))
                .first()
            )
            if not live_client:
                # printFallback for clients with incorrect SCD2 flags
                live_client = (
                    self.db.query(Client)
                    .filter(Client.client_name == client_name, Client.is_deleted == False)
                    .order_by(Client.version.desc(), Client.id.desc())
                    .first()
                )
            if live_client:
                resolved_client_code = live_client.client_code

        return {
            "id": s.id,
            "rerun_report": s.rerun_report,

            "loan_details": {
                "application_number": s.application_number,
                "batch_code": s.batch_code,
                "niyamtek_user": s.niyamtek_user,
                "client_code": resolved_client_code or s.client_code,
                "company_name": s.company_name,
                "loan_account_no": s.loan_account_no,
                "loan_amount_words": s.loan_amount_words,
                "borrower_name": s.borrower_name,
                "borrower_address": s.borrower_address,
                "borrower_address_alt": s.borrower_address_alt,
                "state": s.state,
                "region": s.region,
                "branch": s.branch,
                "ao_name": s.ao_name,
                "trust_number": s.trust_number,
                "assignment_agreement_date": s.assignment_agreement_date,

                # CO-BORROWERS
                "co_borrower_1_name": s.co_borrower_1_name,
                "co_borrower_1_address": s.co_borrower_1_address,
                "co_borrower_1_address_alt": s.co_borrower_1_address_alt,
                "co_borrower_2_name": s.co_borrower_2_name,
                "co_borrower_2_address": s.co_borrower_2_address,
                "co_borrower_2_address_alt": s.co_borrower_2_address_alt,
                "co_borrower_3_name": s.co_borrower_3_name,
                "co_borrower_3_address": s.co_borrower_3_address,
                "co_borrower_3_address_alt": s.co_borrower_3_address_alt,
                "co_borrower_4_name": s.co_borrower_4_name,
                "co_borrower_4_address": s.co_borrower_4_address,
                "co_borrower_4_address_alt": s.co_borrower_4_address_alt,
                "co_borrower_5_name": s.co_borrower_5_name,
                "co_borrower_5_address": s.co_borrower_5_address,
                "co_borrower_5_address_alt": s.co_borrower_5_address_alt,
                "co_borrower_6_name": s.co_borrower_6_name,
                "co_borrower_6_address": s.co_borrower_6_address,
                "co_borrower_6_address_alt": s.co_borrower_6_address_alt,

                # GUARANTORS
                "guarantor_1_name": s.guarantor_1_name,
                "guarantor_1_address": s.guarantor_1_address,
                "guarantor_2_name": s.guarantor_2_name,
                "guarantor_2_address": s.guarantor_2_address,

                # PROPERTY
                "property_address": s.property_address,
                "property_description": s.property_description or s.description_of_schedule_property,

                # LOAN
                "npa_date": s.npa_date,
                "dpd": s.dpd,
                "disbursement_type": s.disbursement_type,
                "disbursal_date": s.disbursal_date,
                "disbursal_amount": s.disbursal_amount,
                "loan_agreement_date": s.loan_agreement_date,
                "loan_amount": s.loan_amount,
                "future_principal": s.future_principal,
                "principal_outstanding": s.principal_outstanding,
                "instalment_overdue": s.instalment_overdue,
                "interest_on_termination": s.interest_on_termination,
                "late_payment_penalty": s.late_payment_penalty,
                "cheque_bounce_charges": s.cheque_bounce_charges,
                "other_amount": s.other_amount,
                "foreclosure_charges": s.foreclosure_charges,
                "total_outstanding": s.total_outstanding,
                "fcl_as_on_date": s.fcl_as_on_date,
                "total_outstanding_words": s.total_outstanding_words,
            },

            "13_2_details": {
                "notice_13_2_amount": s.notice_13_2_amount,
                "notice_13_2_date": s.notice_13_2_date,
                "notice_dispatch_date": s.notice_dispatch_date,
                "notice_pasting_date": s.notice_pasting_date,
                "delivery_status": s.delivery_status,
                "delivery_status_date": s.delivery_status_date,
                "delivered_address": s.delivered_address,
                "undelivered_address": s.undelivered_address,
                "total_address": s.total_address,
                "publication_date": s.publication_date_13_2,
                "publication_english": s.publication_english_13_2,
                "publication_local": s.publication_local_13_2,
            },

            "13_4_details": {
                "symbolic_possession_date": s.symbolic_possession_date_13_4,
                "symbolic_dispatch_date": s.symbolic_dispatch_date_13_4,
                "symbolic_delivery_status": s.symbolic_delivery_status_13_4,
                "symbolic_delivery_status_date": s.symbolic_delivery_status_date_13_4,
                "symbolic_photo": s.symbolic_photo_13_4,
                "symbolic_publication_date": s.symbolic_publication_date_13_4,
                "symbolic_pub_english": s.symbolic_pub_english_13_4,
                "symbolic_pub_local": s.symbolic_pub_local_13_4,
                "matured_date_13_4": s.matured_date_13_4,
            },

            "symbolic_vacation_notice_details": {
                "vacation_notice_moveable": s.vacation_notice_moveable,
                "vacation_notice_immoveable": s.vacation_notice_immoveable,
            },

            "cjm_details": {
                "cjm_filing_date": s.cjm_filing_date,
                "court_name": s.court_name,
                "case_number": s.case_number,
                "crm_pl_date": s.crm_pl_date,
                "crm_pl_no": s.crm_pl_no,
                "next_hearing_date": s.next_hearing_date,
                "ov_date": s.ov_date,
                "order_date": s.order_date,
                "court_ao_name": s.court_ao_name,
                "advocate_details": s.advocate_details,
                "adv_com_name": s.adv_com_name,
                "inventory_status": s.inventory_status,
            },

            "physical_possession_details": {
                "physical_possession_date": s.physical_possession_date,
                "physical_dispatch_date": s.physical_dispatch_date,
                "physical_delivery_status": s.physical_delivery_status,
                "physical_delivery_status_date": s.physical_delivery_status_date,
                "physical_photo": s.physical_photo,
                "physical_publication_date": s.physical_publication_date,
                "physical_pub_english": s.physical_pub_english,
                "physical_pub_local": s.physical_pub_local,
                "vacation_notice_moveable": s.physical_vacation_notice_moveable,
                "vacation_notice_immoveable": s.physical_vacation_notice_immoveable,
            },

            "auction_notice_details": {
                "auction_notice_date": s.auction_notice_date,
                "auction_date": s.auction_date,
                "auction_publication_date": s.auction_publication_date,
                "auction_pub_english": s.auction_pub_english,
                "auction_pub_local": s.auction_pub_local,
                "reserve_price": s.reserve_price,
            },

            "auction_portal_details": {
                "auction_date": s.auction_date,
                "reserve_price": s.reserve_price,
                "sold_price": s.sold_price,
                "auction_status": s.auction_status,
                "inspection_start": s.inspection_start,
                "inspection_end": s.inspection_end,
                "emd_last_date": s.emd_last_date,
                "auction_start": s.auction_start,
                "auction_end": s.auction_end,
                "bid_extension_time": s.bid_extension_time,
                "total_extensions": s.total_extensions,
                "outstanding_amount": s.outstanding_amount,
                "emd_amount": s.emd_amount,
                "bid_increment": s.bid_increment,
                "total_bid_count": s.total_bid_count,
                "authorised_officer": s.authorised_officer,
            },

            "post_sale_details": {
                "post_sale_notice": s.post_sale_notice,
                "sold_price": s.sold_price,
                "sold_reg_date": s.sold_reg_date,
            },

            "sale_certificate_details": {
                "sale_confirmation_date": s.sale_confirmation_date,
                "sale_certificate_date": s.sale_certificate_date,
            },

            "niyamtek_remarks_details": {
                "available_documents": s.available_documents,
                "non_available_documents": s.non_available_documents,
                "discrepancy_doc": s.discrepancy_doc,
                "discrepancy_reason": s.discrepancy_reason,
                "next_actionable_stage": s.next_actionable_stage,
                "next_step_recommended": s.next_step_recommended,
            },
        }

    def _empty_response(self) -> Dict[str, Any]:
        return {
            "id": 0,
            "rerun_report": None,
            "loan_details": {field: None for field in LoanDetails.model_fields.keys()},
            "13_2_details": {field: None for field in Thirteen2Details.model_fields.keys()},
            "13_4_details": {field: None for field in Thirteen4Details.model_fields.keys()},
            "symbolic_vacation_notice_details": {field: None for field in SymbolicVacationNoticeDetails.model_fields.keys()},
            "cjm_details": {field: None for field in CjmDetails.model_fields.keys()},
            "physical_possession_details": {field: None for field in PhysicalPossessionDetails.model_fields.keys()},
            "auction_notice_details": {field: None for field in AuctionNoticeDetails.model_fields.keys()},
            "auction_portal_details": {field: None for field in AuctionPortalDetails.model_fields.keys()},
            "post_sale_details": {field: None for field in PostSaleDetails.model_fields.keys()},
            "sale_certificate_details": {field: None for field in SaleCertificateDetails.model_fields.keys()},
            "niyamtek_remarks_details": {field: None for field in NiyamtekRemarksDetails.model_fields.keys()},
        }

    # 🔥 BUILD MASTER PAYLOAD
    def _build_payload(self, sources: Dict[str, Any]) -> Dict[str, Any]:
        payload = {}
        for field, mapping in FIELD_MAPPING.items():
            value = get_source_value(sources, mapping["source"])
            payload[field] = value
        return payload

    # 🔥 GENERATE MASTER (MAIN ENTRY)
    def generate_sarfaesi_from_application(
        self,
        application_number: str,
        current_user: AuditUser,
        manual_payload: Dict[str, Any] | None = None,
        report_source: str | None = None,
        has_document: bool | None = None,
        auto_commit: bool = True,
    ):
        sources = self._load_sources(application_number)

        if not sources["application"]:
            raise HTTPException(status_code=404, detail="Application not found")

        application = sources.get("application")
        payload = self._build_payload(sources)
        payload["application_number"] = application_number
        if manual_payload:
            for field, value in manual_payload.items():
                if value is None:
                    continue
                if isinstance(value, str) and value.strip() == "":
                    continue
                payload[field] = value

        resolved_has_document = bool(sources.get("document")) if has_document is None else bool(has_document)
        if report_source:
            payload["report_source"] = report_source
        elif payload.get("report_source") is None:
            payload["report_source"] = "Extracted Document" if resolved_has_document else "Application Creation"
        payload["has_document"] = resolved_has_document
        payload["rerun_report"] = 1 if payload.get("report_source") == "Extracted Document" else 0

        actor = current_user.audit_actor

        existing = self.repo.get_by_application_number(application_number)
        loan_account_no = payload.get("loan_account_no")
        if loan_account_no:
            # Check if loan account exists for an ACTIVE Application - block duplicate
            if self.repo.is_loan_account_active(
                loan_account_no,
                exclude_application_number=application_number if existing else None,
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Loan account number already exists in SARFAESI report",
                )

        if existing:
            # 🔥 deactivate old active version explicitly before creating a new one
            close_version(existing, current_user)
            self.db.flush()

            # 🔥 create new version
            payload["version"] = (existing.version or 0) + 1
            payload["created_by"] = getattr(application, "created_by", None) or actor
            payload["updated_by"] = actor
            payload.setdefault("niyamtek_user", actor)
            payload["is_active"] = True

            created = self.repo.create(payload, auto_commit=auto_commit)
            return self._format_response(created)

        payload["created_by"] = getattr(application, "created_by", None) or actor
        payload["updated_by"] = actor
        payload.setdefault("niyamtek_user", actor)

        created = self.repo.create(payload, auto_commit=auto_commit)
        return self._format_response(created)

    # 🔥 UPDATE + SYNC BACK
    def update_sarfaesi_and_sync(self, application_number: str, obj_in: SarfaesiUpdate, current_user: AuditUser):

        sarfaesi = self.repo.get_by_application_number(application_number)

        if not sarfaesi:
            raise HTTPException(status_code=404, detail="Record not found")

        raw_data = obj_in
        print("RAW DATA:", raw_data)

        update_data = {}

        # ==============================
        # 🔥 CLEAN + MAP INPUT
        # ==============================
        for section, values in raw_data.items():
            if not isinstance(values, dict) or not values:
                continue

            for key, value in values.items():
                normalized_key = self._SECTION_FIELD_ALIASES.get(section, {}).get(key, key)

                if normalized_key in self._BLOCKED_UPDATE_FIELDS:
                    continue

                if normalized_key in self._MASTER_COLUMNS:
                    # Allow blank strings through so users can clear a field in the UI.
                    # The repository will preserve string blanks and normalize numeric/date
                    # blanks to None where appropriate.
                    if isinstance(value, str):
                        value = value.strip()
                    update_data[normalized_key] = value

        print("UPDATE DATA:", update_data)

        actor = current_user.audit_actor
        update_data["updated_by"] = actor

        # Block loan_account_no from being changed once it has been set
        if sarfaesi.loan_account_no and "loan_account_no" in update_data:
            incoming = str(update_data["loan_account_no"]).strip() if update_data["loan_account_no"] else None
            if incoming and incoming != str(sarfaesi.loan_account_no).strip():
                raise HTTPException(
                    status_code=422,
                    detail="Loan account number cannot be changed once it has been set.",
                )
            update_data.pop("loan_account_no")

        new_loan_account = update_data.get("loan_account_no") or update_data.get("loan_account_number")
        if new_loan_account:
            # Check if loan account exists for an ACTIVE Application - block duplicate
            if self.repo.is_loan_account_active(
                new_loan_account,
                exclude_application_number=application_number,
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Loan account number already exists in SARFAESI report",
                )

        changed_any = False
        normalized_updates = {}
        for field, value in update_data.items():
            if field == "updated_by":
                continue
            if getattr(sarfaesi, field, None) != value:
                changed_any = True
            normalized_updates[field] = value

        if not changed_any:
            return self._format_response(sarfaesi)

        # ==============================
        # 🔥 VERSIONED SARFAESI UPDATE
        # ==============================
        try:
            close_version(sarfaesi, current_user)
            self.db.flush()
            new_sarfaesi = clone_version(sarfaesi, current_user, **normalized_updates)  
            self.db.add(new_sarfaesi)
            self.db.flush()

        except SQLAlchemyError as e:
            import traceback
            print("DB ERROR:", str(e))
            traceback.print_exc()
            self.db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Database error: {str(e)}"
            )

        # ==============================
        # 🔥 APPLICATION SCD2
        # ==============================
        application = (
            self.db.query(Application)
            .filter(Application.business_code == application_number, *live_filter(Application))
            .first()
        )

        app_update_data = {}
        if application:
            for field, value in update_data.items():
                mapping = FIELD_MAPPING.get(field)
                if not mapping:
                    continue

                source = mapping["source"]
                if not source.startswith("application."):
                    continue

                app_field = source.split(".")[1]
                current_value = getattr(application, app_field, None)
                if current_value != value:
                    app_update_data[app_field] = value

        if application and app_update_data:
            close_version(application, current_user)
            self.db.flush()
            new_app = clone_version(application, current_user, **app_update_data)
            self.db.add(new_app)
            self.db.flush()

        self.db.commit()
        self.db.refresh(new_sarfaesi)

        return self._format_response(new_sarfaesi)

    # 🔥 SYNC TO SOURCE TABLES
    def _sync_to_sources(self, application_number: str, data: Dict[str, Any]):
        sources = self._load_sources(application_number)

        for field, value in data.items():
            mapping = FIELD_MAPPING.get(field)
            if not mapping:
                continue

            source_path = mapping["source"].split("|")[0]
            source_name, attr = source_path.split(".")

            target = sources.get(source_name)

            if not target:
                continue

            if isinstance(target, dict):
                target[attr] = value
            elif hasattr(target, attr):
                setattr(target, attr, value)

        self.db.flush()
        self.db.commit()

    # 🔥 DOCUMENT UPDATE → MASTER
    def update_sarfaesi_from_documents(self, application_number: str, extracted_data: Dict[str, Any], current_user: AuditUser):
        sarfaesi = self.repo.get_by_application_number(application_number)

        if not sarfaesi:
            raise HTTPException(status_code=404, detail="Record not found")

        document_source = {"document": extracted_data}
        payload = {}

        for field in DOCUMENT_FIELDS:
            value = get_source_value(document_source, FIELD_MAPPING[field]["source"])
            if value is not None:
                payload[field] = value

        if not payload:
            return sarfaesi

        payload["updated_by"] = current_user.audit_actor

        return self.repo.update(sarfaesi, payload)

    # 🔥 REPORT FINAL SYNC
    def generate_report(self, application_number: str, current_user: AuditUser):
        sarfaesi = self.repo.get_by_application_number(application_number)

        if not sarfaesi:
            raise HTTPException(status_code=404, detail="Record not found")

        # 👉 Report already validated elsewhere
        # 👉 Just mark/update snapshot

        update_data = {
            "updated_by": current_user.audit_actor
        }

        return self.repo.update(sarfaesi, update_data)
    
    def get_all_sarfaesi(self, skip: int = 0, limit: int = 100):
        sarfaesi_list = self.repo.get_all(skip=skip, limit=limit)
        return [self._format_response(item) for item in sarfaesi_list]
    
    def get_sarfaesi_by_application_number(self, application_number: str):
        sarfaesi = self.repo.get_by_application_number(application_number)

        if not sarfaesi:
            return self._empty_response()

        return self._format_response(sarfaesi)
    
    def delete_sarfaesi(self, application_number: str, current_user: AuditUser):
        sarfaesi = self.repo.get_by_application_number(application_number)

        if not sarfaesi:
            raise HTTPException(status_code=404, detail="Record not found")

        sarfaesi.is_active = False
        sarfaesi.is_deleted = True
        sarfaesi.updated_by = current_user.audit_actor
        if hasattr(sarfaesi, "deleted_by"):
            setattr(sarfaesi, "deleted_by", current_user.audit_actor)
        sarfaesi.version = (sarfaesi.version or 0) + 1

        return self.repo.update(sarfaesi, {})
