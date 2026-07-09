from sqlalchemy.orm import Session
from app.db.models.document_extraction import Document, DocumentFile, DocumentOCRText, DocumentExtractedData, ApplicationContext
from app.db.models.extracted_data import (
    ExtractedSanctionLetter, 
    ExtractedLoanAgreement, 
    ExtractedMODT, 
    ExtractedMODTProperty,
    ExtractedSalesDeed,
    ExtractedSalesDeedVendor,
    ExtractedSalesDeedVendorRepresentative,
    ExtractedSalesDeedPurchaser,
    ExtractedSalesDeedPurchaserRepresentative,
    ExtractedSalesDeedWitness,
    ExtractedSalesDeedWitnessRepresentative,
    ExtractedSalesDeedSchedule,
    ExtractedSalesDeedPaymentDetail,
    ExtractedSalesDeedParentFlow,
    ExtractedSalesDeedTerm,
    ExtractedSalesDeedAuthority,
    ExtractedForeclosureStatement,
    ExtractedForeclosureCoApplicant,
    ExtractedForeclosureNote,
    ExtractedStatementOfAccount,
    ExtractedSOATransaction,
    ExtractedLegalReport
)
from typing import Dict, List, Optional, Any
import uuid
from app.db.versioning import clone_version, close_version, current_actor, live_filter, mark_created, utcnow

class ExtractorRepository:

    def __init__(self, db: Session):
        self.db = db

    def save_record(self, record_id: str, record: Dict, audit_user=None) -> Document:
        db_doc = self.db.query(Document).filter(Document.file_id == record_id, *live_filter(Document)).first()
        if not db_doc:
            db_doc = Document(
                file_id=record_id,
                application_number=record.get("application_number"),
                doc_type=record.get("doc_type"),
                file_name=record.get("file_name"),
                document_name=record.get("document_name"),
                error_message=record.get("error_message"),
                client_type=record.get("client_type") or "UNKNOWN",
            )
            mark_created(db_doc, audit_user)
            self.db.add(db_doc)
            self.db.flush()
        else:
            db_doc.application_number = record.get("application_number", db_doc.application_number)
            db_doc.doc_type = record.get("doc_type", db_doc.doc_type)
            db_doc.file_name = record.get("file_name", db_doc.file_name)
            db_doc.document_name = record.get("document_name", db_doc.document_name)
            db_doc.error_message = record.get("error_message")
            db_doc.client_type = record.get("client_type") or db_doc.client_type or "UNKNOWN"
            db_doc.updated_at = utcnow()
            db_doc.updated_by = current_actor(audit_user)

        # Upsert document_files
        s3_paths = record.get("s3_paths", {}) or {}
        db_files = self.db.query(DocumentFile).filter(DocumentFile.document_id == db_doc.id, *live_filter(DocumentFile)).first()
        if not db_files:
            db_files = DocumentFile(document_id=db_doc.id)
            mark_created(db_files, audit_user)
            self.db.add(db_files)
        db_files.original_path = record.get("s3_original", db_files.original_path)
        db_files.original_pdf_path = record.get("original_pdf_path", db_files.original_pdf_path)
        db_files.selected_page_range = record.get("selected_page_range", db_files.selected_page_range)
        db_files.ocr_json_path = s3_paths.get("ocr", db_files.ocr_json_path)
        db_files.original_llm_path = s3_paths.get("original_llm", db_files.original_llm_path)
        db_files.parsed_llm_path = s3_paths.get("parsed_llm", db_files.parsed_llm_path)

        # Upsert OCR text
        if "ocr_text" in record and record.get("ocr_text") is not None:
            db_ocr = self.db.query(DocumentOCRText).filter(DocumentOCRText.document_id == db_doc.id, *live_filter(DocumentOCRText)).first()
            if not db_ocr:
                db_ocr = DocumentOCRText(document_id=db_doc.id)
                mark_created(db_ocr, audit_user)
                self.db.add(db_ocr)
            db_ocr.ocr_text = record.get("ocr_text")

        # Upsert document_extracted_data (secondary store)
        parsed_data = record.get("ai_parsed_output")
        if parsed_data is not None:
            db_data = self.db.query(DocumentExtractedData).filter(DocumentExtractedData.document_id == db_doc.id, *live_filter(DocumentExtractedData)).first()
            if not db_data:
                db_data = DocumentExtractedData(document_id=db_doc.id)
                mark_created(db_data, audit_user)
                self.db.add(db_data)
            elif db_data.ai_parsed_output != parsed_data:
                close_version(db_data, audit_user)
                db_data = clone_version(db_data, audit_user, document_id=db_doc.id)
                self.db.add(db_data)
            db_data.ai_parsed_output = parsed_data

        # Upsert extracted_* tables (primary store for GET) + context
        doc_type = record.get("doc_type") or db_doc.doc_type
        app_number = record.get("application_number") or db_doc.application_number
        extracted_upsert_payload = record.get("upsert_parsed_output")
        if extracted_upsert_payload is None:
            extracted_upsert_payload = parsed_data

        if extracted_upsert_payload is not None and doc_type:
            for row in self.db.query(ApplicationContext).filter(ApplicationContext.document_id == db_doc.id, *live_filter(ApplicationContext)).all():
                close_version(row, audit_user, deleted=True)
            self._extract_and_save_context(db_doc, extracted_upsert_payload, doc_type, audit_user=audit_user)
            self._save_to_specific_extracted_table(
                app_number,
                db_doc.id,
                extracted_upsert_payload,
                doc_type,
                audit_user=audit_user,
            )

        self.db.commit()
        self.db.refresh(db_doc)
        return db_doc

    def ensure_placeholder_record(
        self,
        *,
        record_id: str,
        application_number: str,
        doc_type: Optional[str] = None,
        file_name: Optional[str] = None,
        document_name: Optional[str] = None,
        audit_user=None,
        client_type: Optional[str] = None,
    ) -> Document:
        db_doc = self.db.query(Document).filter(Document.file_id == record_id, *live_filter(Document)).first()
        if not db_doc:
            db_doc = Document(
                file_id=record_id,
                application_number=application_number,
                doc_type=doc_type,
                file_name=file_name,
                document_name=document_name,
                error_message=None,
                client_type=client_type or "UNKNOWN",
            )
            mark_created(db_doc, audit_user)
            self.db.add(db_doc)
        else:
            db_doc.application_number = application_number or db_doc.application_number
            db_doc.doc_type = doc_type or db_doc.doc_type
            db_doc.file_name = file_name or db_doc.file_name
            db_doc.document_name = document_name or db_doc.document_name
            if client_type:
                db_doc.client_type = client_type
            elif not db_doc.client_type:
                db_doc.client_type = "UNKNOWN"
            db_doc.updated_at = utcnow()
            db_doc.updated_by = current_actor(audit_user)

        self.db.commit()
        self.db.refresh(db_doc)
        return db_doc

    def save_processing_error(
        self,
        *,
        record_id: str,
        application_number: str,
        doc_type: Optional[str] = None,
        file_name: Optional[str] = None,
        document_name: Optional[str] = None,
        s3_original: Optional[str] = None,
        error_message: Optional[str] = None,
        audit_user=None,
    ) -> Optional[Document]:
        error_text = self._fit_str(error_message, max_len=16000)
        db_doc = self.db.query(Document).filter(Document.file_id == record_id, *live_filter(Document)).first()

        if not db_doc:
            db_doc = Document(
                file_id=record_id,
                application_number=application_number,
                doc_type=doc_type,
                file_name=file_name,
                document_name=document_name,
                error_message=error_text,
                client_type="UNKNOWN",
            )
            mark_created(db_doc, audit_user)
            self.db.add(db_doc)
            self.db.flush()
        else:
            db_doc.application_number = application_number or db_doc.application_number
            db_doc.doc_type = doc_type or db_doc.doc_type
            db_doc.file_name = file_name or db_doc.file_name
            db_doc.document_name = document_name or db_doc.document_name
            db_doc.error_message = error_text
            db_doc.client_type = db_doc.client_type or "UNKNOWN"

        if s3_original:
            db_files = self.db.query(DocumentFile).filter(DocumentFile.document_id == db_doc.id, *live_filter(DocumentFile)).first()
            if not db_files:
                db_files = DocumentFile(document_id=db_doc.id)
                mark_created(db_files, audit_user)
                self.db.add(db_files)
            db_files.original_path = s3_original

        self.db.commit()
        self.db.refresh(db_doc)
        return db_doc

    def _normalize_doc_type(self, doc_type: str) -> str:
        if not doc_type:
            return ""
        normalized = doc_type.strip().lower().replace(" ", "_")
        if normalized == "sales_deed":
            return "sale_deed"
        if normalized in {"legalreport", "legal_report"}:
            return "legal_report"
        if normalized in {
            "memorandum_of_deposit_of_title_deed",
            "memorandum_of_deposit_of_title_deeds",
            "modt",
        }:
            return "memorandum_of_deposit_of_title_deeds"
        return normalized

    def _parse_date(self, date_str: Optional[str]):
        if not date_str or not isinstance(date_str, str):
            return None
        import datetime as dt
        date_str = date_str.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y"):
            try:
                return dt.datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_numeric(self, val: Any) -> Optional[float]:
        if val is None or val == "":
            return None
        if isinstance(val, (int, float)):
            return float(val)
        import re
        # Remove currency symbols and commas, keep decimal point and minus sign
        clean_val = re.sub(r'[^-0-9.]', '', str(val))
        try:
            return float(clean_val)
        except ValueError:
            return None

    def _date_to_str(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    def _fit_str(self, value: Any, max_len: Optional[int] = None) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if max_len is not None and len(text) > max_len:
            return text[:max_len]
        return text

    def _as_list(self, value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]
        return []

    def _collect_non_empty_strings(self, value: Any) -> List[str]:
        values: List[str] = []
        if isinstance(value, dict):
            for v in value.values():
                values.extend(self._collect_non_empty_strings(v))
        elif isinstance(value, list):
            for item in value:
                values.extend(self._collect_non_empty_strings(item))
        else:
            if value is None:
                return values
            text = str(value).strip()
            if text:
                values.append(text)
        return values

    def _normalize_text_value(self, value: Any, max_len: Optional[int] = None) -> Optional[str]:
        if isinstance(value, (dict, list)):
            value = " ".join(self._collect_non_empty_strings(value))
        return self._fit_str(value, max_len=max_len)

    def _has_meaningful_content(self, value: Any) -> bool:
        return bool(self._collect_non_empty_strings(value))

    def _normalize_dict(self, value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _normalize_list_of_dicts(self, value: Any) -> List[Dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict) and self._has_meaningful_content(item)]
        if isinstance(value, dict):
            if any(isinstance(v, dict) for v in value.values()):
                return [v for v in value.values() if isinstance(v, dict) and self._has_meaningful_content(v)]
            return [value] if self._has_meaningful_content(value) else []
        return []

    def _extract_schedule_property(self, dom: Dict[str, Any]) -> Dict[str, Any]:
        prop = dom.get("scheduleProperty")
        if not isinstance(prop, dict) or not prop:
            prop = dom.get("schedule_property")
        if not isinstance(prop, dict):
            prop = {}

        boundaries = prop.get("boundaries")
        if not isinstance(boundaries, dict):
            boundaries = {}

        return {
            "description": self._normalize_text_value(prop.get("description") or prop.get("propertyDescription")),
            "surveyNumber": self._normalize_text_value(
                prop.get("surveyNumber") or prop.get("survey_number") or prop.get("surveyNo")
            ),
            "plotNumber": self._normalize_text_value(
                prop.get("plotNumber") or prop.get("plot_number") or prop.get("plotNo")
            ),
            "propertyAddress": self._normalize_text_value(
                prop.get("propertyAddress") or prop.get("property_address") or prop.get("address")
            ),
            "boundaries": {
                "north": self._normalize_text_value(boundaries.get("north") or prop.get("boundaryNorth")),
                "south": self._normalize_text_value(boundaries.get("south") or prop.get("boundarySouth")),
                "east": self._normalize_text_value(boundaries.get("east") or prop.get("boundaryEast")),
                "west": self._normalize_text_value(boundaries.get("west") or prop.get("boundaryWest")),
            },
        }

    def _normalize_identifier_dict(self, value: Any) -> Dict[str, Optional[str]]:
        if isinstance(value, dict):
            return {
                "PAN": self._normalize_text_value(value.get("PAN"), 50),
                "AADHAR": self._normalize_text_value(value.get("AADHAR"), 50),
            }
        if value is None:
            return {"PAN": None, "AADHAR": None}
        text = self._normalize_text_value(value, 100)
        return {"PAN": text, "AADHAR": None}

    def _normalize_identifier_value(self, value: Any) -> Optional[str]:
        if isinstance(value, dict):
            parts = []
            pan = self._normalize_text_value(value.get("PAN"), 50)
            aadhar = self._normalize_text_value(value.get("AADHAR"), 50)
            if pan:
                parts.append(f"PAN:{pan}")
            if aadhar:
                parts.append(f"AADHAR:{aadhar}")
            return self._normalize_text_value(" ".join(parts), 100)
        return self._normalize_text_value(value, 100)

    def _normalize_sales_deed_schedule_map(self, value: Any) -> Dict[str, Dict[str, Any]]:
        if isinstance(value, dict):
            out: Dict[str, Dict[str, Any]] = {}
            for key, item in value.items():
                if isinstance(item, dict) and self._has_meaningful_content(item):
                    out[str(key)] = item
            return out
        if isinstance(value, list):
            out: Dict[str, Dict[str, Any]] = {}
            for idx, item in enumerate(value, start=1):
                if isinstance(item, dict) and self._has_meaningful_content(item):
                    out[f"SCHEDULE_{idx}"] = item
            return out
        return {}

    def _normalize_sales_deed_payment_details(self, value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict) and self._has_meaningful_content(item)]
        if isinstance(value, dict):
            if not self._has_meaningful_content(value):
                return []
            if any(isinstance(v, dict) for v in value.values()):
                return [{k: v} for k, v in value.items() if isinstance(v, dict) and self._has_meaningful_content(v)]
            return [value]
        return []

    def _normalize_sales_deed_text_list(self, value: Any) -> List[Any]:
        if isinstance(value, list):
            return [item for item in value if self._has_meaningful_content(item)]
        if self._has_meaningful_content(value):
            return [value]
        return []

    def _normalize_modt_properties(self, value: Any) -> List[Dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
        if isinstance(value, dict):
            # Accept keyed objects like {"Schedule_A": {...}, "Schedule_B": {...}}
            dict_values = [v for v in value.values() if isinstance(v, dict)]
            if dict_values and all(not isinstance(v, (str, int, float, bool, type(None))) for v in value.values()):
                out: List[Dict[str, Any]] = []
                for k, v in value.items():
                    if not isinstance(v, dict):
                        continue
                    payload = dict(v)
                    payload.setdefault("scheduleKey", k)
                    out.append(payload)
                return out
            return [value]
        return []


    def _extract_and_save_context(self, doc: Document, data: Dict, doc_type: str, audit_user=None):
        """
        Extracts application context information based on document type patterns 
        and saves them to application_context table.
        Refined for Sale Deed, EC, and Patta.
        """
        contexts = []
        norm_type = self._normalize_doc_type(doc_type)

        # 1. Sale Deed (Vendor & Purchaser)
        if norm_type == "sale_deed":
            sales_deed = data.get("SalesDeed", {})
            if not isinstance(sales_deed, dict):
                sales_deed = {}
            
            # Vendor
            vendor = sales_deed.get("Vendor", {})
            if isinstance(vendor, list): 
                # Handle case where Vendor is a list (as per YAML schema hint) 
                vendors = vendor
            elif isinstance(vendor, dict):
                vendors = [vendor]
            else:
                vendors = []

            for v in vendors:
                if not isinstance(v, dict):
                    continue
                v_ids = v.get("ID") or {}
                if not isinstance(v_ids, dict):
                    v_ids = {}
                # Extract PAN
                if v_ids.get("PAN"):
                     contexts.append({
                        "name": v.get("Vendor_name") or v.get("Name"),
                        "father_name": v.get("Relation_Name"),
                        "identity_number": v_ids.get("PAN"),
                        "identity_type": "PAN",
                        "gender": v.get("Gender"),
                        "address": v.get("Address")
                    })
                # Extract AADHAR
                if v_ids.get("AADHAR"):
                     contexts.append({
                        "name": v.get("Vendor_name") or v.get("Name"),
                        "father_name": v.get("Relation_Name"),
                        "identity_number": v_ids.get("AADHAR"),
                        "identity_type": "AADHAR",
                        "gender": v.get("Gender"),
                        "address": v.get("Address")
                    })
                # If IDs missing but name exists, add generic
                if not v_ids.get("PAN") and not v_ids.get("AADHAR") and (v.get("Vendor_name") or v.get("Name")):
                    contexts.append({
                        "name": v.get("Vendor_name") or v.get("Name"),
                        "father_name": v.get("Relation_Name"),
                        "identity_type": "VENDOR",
                        "gender": v.get("Gender"),
                        "address": v.get("Address")
                    })

            # Purchaser
            purchaser = sales_deed.get("Purchaser", {})
            if isinstance(purchaser, list):
                purchasers = purchaser
            elif isinstance(purchaser, dict):
                purchasers = [purchaser]
            else:
                purchasers = []

            for p in purchasers:
                if not isinstance(p, dict):
                    continue
                p_ids = p.get("ID", {})
                if not isinstance(p_ids, dict):
                    p_ids = {}
                if p_ids.get("PAN"):
                     contexts.append({
                        "name": p.get("Purchaser_name") or p.get("Name"),
                        "father_name": p.get("Relation_Name"),
                        "identity_number": p_ids.get("PAN"),
                        "identity_type": "PAN",
                        "gender": p.get("Gender"),
                        "address": p.get("Address")
                    })
                if p_ids.get("AADHAR"):
                     contexts.append({
                        "name": p.get("Purchaser_name") or p.get("Name"),
                        "father_name": p.get("Relation_Name"),
                        "identity_number": p_ids.get("AADHAR"),
                        "identity_type": "AADHAR",
                        "gender": p.get("Gender"),
                        "address": p.get("Address")
                    })
                if not p_ids.get("PAN") and not p_ids.get("AADHAR") and (p.get("Purchaser_name") or p.get("Name")):
                    contexts.append({
                        "name": p.get("Purchaser_name") or p.get("Name"),
                        "father_name": p.get("Relation_Name"),
                        "identity_type": "PURCHASER",
                        "gender": p.get("Gender"),
                        "address": p.get("Address")
                    })

        # 2. Encumbrance Certificate (EC)
        elif norm_type == "encumbrance_certificate":
            ec_dom = data.get("EC_DocumentDOM", {})
            ec_info = ec_dom.get("EC_DocumentInfo", {})
            prop_info = ec_dom.get("propertyInfo", {})
            
            # Applicant
            if ec_info.get("applicantName"):
                contexts.append({
                    "name": ec_info.get("applicantName"),
                    "identity_type": "APPLICANT"
                })
            
            # Owner
            if prop_info.get("ownerName"):
                contexts.append({
                    "name": prop_info.get("ownerName"),
                    "identity_type": "OWNER"
                })

            # Transactions (Executant / Claimant)
            conversations = ec_dom.get("transactionDetails", [])
            for txn in conversations:
                if txn.get("executant"):
                    contexts.append({
                        "name": txn.get("executant"),
                        "identity_type": "EXECUTANT"
                    })
                if txn.get("claimant"):
                    contexts.append({
                        "name": txn.get("claimant"),
                        "identity_type": "CLAIMANT"
                    })

        # 3. Patta Document
        elif norm_type == "patta_document":
             # Based on schema: name_in_adangal seems to be the primary person name field
             name = data.get("name_in_adangal")
             if name:
                 contexts.append({
                     "name": name,
                     "identity_type": "PATTA_HOLDER",
                     "identity_number": data.get("PattaNumber") # Linking Patta No as ID? Optional.
                 })

        # 4. Loan Agreement
        elif norm_type == "loan_agreement":
            la_dom = data.get("LoanAgreementDOM", {})
            borrower_name = la_dom.get("borrowerName") or la_dom.get("borrowersName")
            borrower_address = la_dom.get("borrowerAddress") or la_dom.get("borrowersAddress")
            if borrower_name:
                contexts.append({
                    "name": borrower_name,
                    "address": borrower_address,
                    "identity_type": "BORROWER"
                })
            
            # Co-Borrowers
            co_borrowers = la_dom.get("coBorrowers", [])
            for cb in co_borrowers:
                name = cb.get("coBorrowerName")
                address = cb.get("coBorrowerAddress")
                if name:
                    contexts.append({
                        "name": name,
                        "address": address,
                        "identity_type": "CO_BORROWER"
                    })

        # 5. Sanction Letter
        elif norm_type == "sanction_letter":
            sl_dom = data.get("SanctionLetterDOM", {})
            borrower_name = sl_dom.get("borrowerName") or sl_dom.get("borrowersName")
            borrower_address = sl_dom.get("borrowerAddress") or sl_dom.get("borrowersAddress")
            if borrower_name:
                contexts.append({
                    "name": borrower_name,
                    "address": borrower_address,
                    "identity_type": "BORROWER",
                    "identity_number": sl_dom.get("loanAccountNumber")
                })

        # 6. MODT
        elif norm_type == "memorandum_of_deposit_of_title_deeds":
            modt_dom = data.get("MODT_DocumentDOM", {})
            parties = modt_dom.get("parties", {})
            depositor_name = parties.get("depositorName")
            if depositor_name:
                contexts.append({
                    "name": depositor_name,
                    "address": parties.get("depositorAddress"),
                    "identity_type": "DEPOSITOR"
                })

        # 7. Foreclosure Statement
        elif norm_type == "foreclosure_statement":
            fs_keys = ["ForeclosureStatement", "Foreclosure_Statement", "ForeclosureStatemen"]
            fs = {}
            for k in fs_keys:
                if k in data:
                    fs = data[k]
                    break
            
            borrower = fs.get("Borrower_Details", {})
            if borrower.get("Borrower_Name"):
                contexts.append({
                    "name": borrower.get("Borrower_Name"),
                    "address": borrower.get("Address"),
                    "identity_type": "BORROWER"
                })
            
            # Co-Applicants
            for co in borrower.get("Co_Applicants", []):
                if co:
                    contexts.append({
                        "name": co,
                        "identity_type": "CO_BORROWER"
                    })

        # 8. Statement of Accounts
        elif norm_type == "statement_of_accounts":
            soa_keys = ["StatementOfAccounts", "Statement_of_Accounts", "StatementOfAccount"]
            soa = {}
            for k in soa_keys:
                if k in data:
                    soa = data[k]
                    break
            
            borrower = soa.get("Borrower_Details", {})
            if borrower.get("Borrower_Name"):
                contexts.append({
                    "name": borrower.get("Borrower_Name"),
                    "address": borrower.get("Address"),
                    "identity_type": "BORROWER",
                    "identity_number": borrower.get("PAN_Number")
                })
            if borrower.get("Co_Applicant_Name"):
                contexts.append({
                    "name": borrower.get("Co_Applicant_Name"),
                    "identity_type": "CO_BORROWER"
                })

        # Save to DB
        unique_contexts = []
        seen = set()
        
        # Deduplicate local list based on name+id
        for i in contexts:
            key = (i.get("name"), i.get("identity_number"), i.get("identity_type"))
            if key not in seen and i.get("name"): # Ensure name exists
                seen.add(key)
                unique_contexts.append(i)

        for ctx in unique_contexts:
            db_context = ApplicationContext(
                document_id=doc.id,
                name=self._normalize_text_value(ctx.get("name"), 255),
                father_name=self._normalize_text_value(ctx.get("father_name"), 255),
                dob_year=self._normalize_text_value(ctx.get("dob_year"), 4),
                gender=self._normalize_text_value(ctx.get("gender"), 50),
                address=self._normalize_text_value(ctx.get("address")),
                identity_number=self._normalize_text_value(ctx.get("identity_number"), 100),
                identity_type=self._normalize_text_value(ctx.get("identity_type"), 50)
            )
            mark_created(db_context, audit_user)
            self.db.add(db_context)

    def _save_sales_deed(self, application_number: str, document_id: int, data: Dict, audit_user=None) -> None:
        try:
            sd_dom = data.get("SalesDeed", {})
            if not sd_dom and (data.get("Document_Information") or data.get("Document_Number")):
                sd_dom = data
            sd_dom = self._normalize_dict(sd_dom)

            doc_info = self._normalize_dict(sd_dom.get("Document_Information") or sd_dom.get("document_information") or {})
            prop_info = self._normalize_dict(sd_dom.get("Property_Info") or sd_dom.get("property_info") or {})
            pay_info = self._normalize_dict(
                sd_dom.get("Payment_Information")
                or sd_dom.get("payment_Information")
                or sd_dom.get("payment_information")
                or {}
            )
            schedules = self._normalize_sales_deed_schedule_map(
                sd_dom.get("Schedule_Information")
                or sd_dom.get("schedule_information")
                or sd_dom.get("ScheduleInformation")
                or sd_dom.get("Schedules")
                or {}
            )

            db_sd = self.db.query(ExtractedSalesDeed).filter(
                ExtractedSalesDeed.document_id == document_id,
                *live_filter(ExtractedSalesDeed)
            ).first()
            if not db_sd:
                db_sd = ExtractedSalesDeed(application_number=application_number, document_id=document_id)
                mark_created(db_sd, audit_user)
                self.db.add(db_sd)
                self.db.flush()
            else:
                close_version(db_sd, audit_user)
                db_sd = clone_version(db_sd, audit_user)
                self.db.add(db_sd)
                self.db.flush()

            db_sd.application_number = application_number
            db_sd.document_category = self._normalize_text_value(doc_info.get("Document_Category"), 255)
            db_sd.document_sub_category = self._normalize_text_value(doc_info.get("Document_Sub_Category"), 255)
            db_sd.document_number = self._normalize_text_value(doc_info.get("Document_Number"), 100)
            db_sd.book_number = self._normalize_text_value(doc_info.get("Book_Number"), 100)
            db_sd.execution_date = self._normalize_text_value(doc_info.get("Document_Execution_Date"), 50)
            db_sd.execution_location = self._normalize_text_value(doc_info.get("Document_Execution_Location"), 255)
            db_sd.state = self._normalize_text_value(doc_info.get("State"), 100)
            db_sd.number_of_pages = self._normalize_text_value(doc_info.get("Number_of_Pages"), 50)
            db_sd.sub_registrar_office = self._normalize_text_value(doc_info.get("Sub_Registrar_Office"), 255)
            db_sd.document_remarks = self._normalize_text_value(doc_info.get("Remarks"))
            db_sd.property_address = self._normalize_text_value(prop_info.get("Property_Address"))
            geo = self._normalize_dict(prop_info.get("Geographic_Coordinates") or {})
            db_sd.latitude = self._normalize_text_value(geo.get("Latitude"), 50)
            db_sd.longitude = self._normalize_text_value(geo.get("Longitude"), 50)
            db_sd.market_value = self._normalize_text_value(pay_info.get("Market_Value"), 100)
            db_sd.sale_transaction_value = self._normalize_text_value(pay_info.get("Sale_Transaction_Value"), 100)
            db_sd.payment_remarks = self._normalize_text_value(pay_info.get("Remarks"))
            db_sd.remarks = self._normalize_text_value(sd_dom.get("Remarks"))
            db_sd.raw_description = (
                self._normalize_text_value(sd_dom.get("raw_description"))
                or self._normalize_text_value(sd_dom.get("description"))
                or self._normalize_text_value(sd_dom.get("Property_Raw_Text"))
            )
            self.db.flush()

            for model in (
                ExtractedSalesDeedVendor,
                ExtractedSalesDeedPurchaser,
                ExtractedSalesDeedWitness,
                ExtractedSalesDeedAuthority,
                ExtractedSalesDeedPaymentDetail,
            ):
                for row in self.db.query(model).filter(model.sales_deed_id == db_sd.id, *live_filter(model)).all():
                    close_version(row, audit_user, deleted=True)

            for party_value, party_model, rep_model in (
                (sd_dom.get("Vendor"), ExtractedSalesDeedVendor, ExtractedSalesDeedVendorRepresentative),
                (sd_dom.get("Purchaser"), ExtractedSalesDeedPurchaser, ExtractedSalesDeedPurchaserRepresentative),
                (sd_dom.get("Witness"), ExtractedSalesDeedWitness, ExtractedSalesDeedWitnessRepresentative),
            ):
                for party in self._normalize_list_of_dicts(party_value):
                    ids = self._normalize_identifier_dict(party.get("ID"))
                    party_kwargs = {
                        "sales_deed_id": db_sd.id,
                        "name": self._normalize_text_value(party.get("Name"), 255),
                        "relationship_text": self._normalize_text_value(party.get("Relationship"), 100),
                        "pan": ids.get("PAN"),
                        "aadhar": ids.get("AADHAR"),
                        "date_of_birth_age": self._normalize_text_value(party.get("Date_of_Birth_Age"), 100),
                        "gender": self._normalize_text_value(party.get("Gender"), 50),
                        "address": self._normalize_text_value(party.get("Address")),
                        "signature_biometric_photo": self._normalize_text_value(party.get("Signature_Biometric_Photo"), 50),
                        "remarks": self._normalize_text_value(party.get("Remarks")),
                    }
                    relation_value = self._normalize_text_value(party.get("Relation_Name") or party.get("Relations_Name"), 255)
                    if party_model is ExtractedSalesDeedVendor:
                        party_kwargs["relation_name"] = relation_value
                    else:
                        party_kwargs["relations_name"] = relation_value
                    db_party = party_model(**party_kwargs)
                    mark_created(db_party, audit_user)
                    self.db.add(db_party)
                    self.db.flush()

                    rep = self._normalize_dict(party.get("Representative_Details"))
                    if self._has_meaningful_content(rep):
                        db_rep = rep_model(
                            **{
                                "vendor_id" if rep_model is ExtractedSalesDeedVendorRepresentative else "purchaser_id" if rep_model is ExtractedSalesDeedPurchaserRepresentative else "witness_id": db_party.id,
                                "name": self._normalize_text_value(rep.get("Name"), 255),
                                "relationship_text": self._normalize_text_value(rep.get("Relationship"), 100),
                                "relations_name": self._normalize_text_value(rep.get("Relations_Name"), 255),
                                "representation_capacity": self._normalize_text_value(rep.get("Representation_Capacity"), 255),
                                "document_reference": self._normalize_text_value(rep.get("Document_Reference"), 255),
                                "id_value": self._normalize_identifier_value(rep.get("ID")),
                                "date_of_birth_age": self._normalize_text_value(rep.get("Date_of_Birth_Age"), 100),
                                "gender": self._normalize_text_value(rep.get("Gender"), 50),
                                "address": self._normalize_text_value(rep.get("Address")),
                                "signature_biometric_photo": self._normalize_text_value(rep.get("Signature_Biometric_Photo"), 50),
                                "remarks": self._normalize_text_value(rep.get("Remarks")),
                            }
                        )
                        mark_created(db_rep, audit_user)
                        self.db.add(db_rep)

            auth = self._normalize_dict(sd_dom.get("Authority"))
            if self._has_meaningful_content(auth):
                db_auth = ExtractedSalesDeedAuthority(
                    sales_deed_id=db_sd.id,
                    designation=self._normalize_text_value(auth.get("Designation"), 255),
                    sub_registrar_name=self._normalize_text_value(auth.get("Sub_Registrar_Name"), 255),
                    sub_registrar_signature=self._normalize_text_value(auth.get("Sub_Registrar_Signature"), 255),
                    sub_registrar_office=self._normalize_text_value(auth.get("Sub_Registrar_Office"), 255),
                    city=self._normalize_text_value(auth.get("City"), 100),
                    state=self._normalize_text_value(auth.get("State"), 100),
                    remarks=self._normalize_text_value(auth.get("Remarks"))
                )
                mark_created(db_auth, audit_user)
                self.db.add(db_auth)

            for pd in self._normalize_sales_deed_payment_details(pay_info.get("Payment_Details")):
                for key, val in pd.items():
                    key_text = self._normalize_text_value(key, 100)
                    if isinstance(val, dict):
                        items = list(val.items())
                    else:
                        items = [("VALUE", val)]
                    for t_key, t_val in items:
                        value_text = self._normalize_text_value(t_val)
                        if not value_text:
                            continue
                        db_pay = ExtractedSalesDeedPaymentDetail(
                            sales_deed_id=db_sd.id,
                            payment_detail_key=key_text,
                            transaction_key=self._normalize_text_value(t_key, 100),
                            transaction_value=value_text
                        )
                        mark_created(db_pay, audit_user)
                        self.db.add(db_pay)

            existing_schedules = {
                (r.schedule_type or "").strip().upper(): r
                for r in self.db.query(ExtractedSalesDeedSchedule).filter(
                    ExtractedSalesDeedSchedule.sales_deed_id == db_sd.id,
                    *live_filter(ExtractedSalesDeedSchedule)
                ).all()
            }
            seen_schedule_types = set()
            meaningful_schedule_found = False
            for raw_key, val in schedules.items():
                if not isinstance(val, dict) or not self._has_meaningful_content(val):
                    continue
                schedule_type = self._fit_str((str(raw_key or "").strip() or "UNSPECIFIED").upper(), 50) or "UNSPECIFIED"
                seen_schedule_types.add(schedule_type)
                meaningful_schedule_found = True
                prop_addr = self._normalize_dict(val.get("Property_Address") or {})
                bounds = self._normalize_dict(val.get("Property_Boundary_Definition") or {})
                existing_schedule = existing_schedules.get(schedule_type)
                if not existing_schedule:
                    db_sched = ExtractedSalesDeedSchedule(sales_deed_id=db_sd.id, schedule_type=schedule_type)
                    mark_created(db_sched, audit_user)
                    self.db.add(db_sched)
                else:
                    close_version(existing_schedule, audit_user)
                    db_sched = clone_version(existing_schedule, audit_user, sales_deed_id=db_sd.id, schedule_type=schedule_type)
                    self.db.add(db_sched)
                db_sched.property_extent = self._normalize_text_value(val.get("Property_Extent"), 100)
                db_sched.property_extent_unit = self._normalize_text_value(val.get("Property_Extent_Unit"), 50)
                db_sched.plot_dimension = self._normalize_text_value(val.get("Plot_Dimension"), 100)
                db_sched.survey_number = self._normalize_text_value(val.get("Survey_Number"), 255)
                db_sched.old_survey_number = self._normalize_text_value(val.get("Old_Survey_Number"), 255)
                db_sched.ts_number = self._normalize_text_value(val.get("TS_Number"), 255)
                db_sched.plot_number = self._normalize_text_value(prop_addr.get("Plot_Number"), 100)
                db_sched.village_street_name = self._normalize_text_value(prop_addr.get("Village_Street_Name"), 255)
                db_sched.jurisdiction = self._normalize_text_value(prop_addr.get("Jurisdiction"), 255)
                db_sched.address_remarks = self._normalize_text_value(prop_addr.get("Remarks"))
                db_sched.boundary_east = self._normalize_text_value(bounds.get("East"), 255)
                db_sched.boundary_west = self._normalize_text_value(bounds.get("West"), 255)
                db_sched.boundary_north = self._normalize_text_value(bounds.get("North"), 255)
                db_sched.boundary_south = self._normalize_text_value(bounds.get("South"), 255)
                db_sched.raw_text = self._normalize_text_value(val.get("raw_text") or val.get("Raw_Text") or val.get("Property_Raw_Text") or val.get("Description") or val.get("description"))
            if meaningful_schedule_found:
                for schedule_type, row in existing_schedules.items():
                    if schedule_type not in seen_schedule_types:
                        close_version(row, audit_user, deleted=True)

            parent_doc_details = self._normalize_dict(sd_dom.get("Parent_Document_Details") or {})
            parent_flows = self._normalize_sales_deed_text_list(parent_doc_details.get("Flow"))
            existing_flows = {
                r.flow_sequence: r
                for r in self.db.query(ExtractedSalesDeedParentFlow).filter(
                    ExtractedSalesDeedParentFlow.sales_deed_id == db_sd.id,
                    *live_filter(ExtractedSalesDeedParentFlow)
                ).all()
            }
            seen_flow_seq = set()
            for i, flow in enumerate(parent_flows):
                seq = i + 1
                seen_flow_seq.add(seq)
                existing_flow = existing_flows.get(seq)
                if not existing_flow:
                    db_flow = ExtractedSalesDeedParentFlow(sales_deed_id=db_sd.id, flow_sequence=seq)
                    mark_created(db_flow, audit_user)
                    self.db.add(db_flow)
                else:
                    close_version(existing_flow, audit_user)
                    db_flow = clone_version(existing_flow, audit_user, sales_deed_id=db_sd.id, flow_sequence=seq)
                    self.db.add(db_flow)
                db_flow.flow_value = self._normalize_text_value(flow)
            for seq, row in existing_flows.items():
                if seq not in seen_flow_seq:
                    close_version(row, audit_user, deleted=True)

            terms_block = self._normalize_dict(sd_dom.get("Terms_and_Conditions") or {})
            terms = self._normalize_sales_deed_text_list(terms_block.get("Text"))
            existing_terms = {
                r.term_sequence: r
                for r in self.db.query(ExtractedSalesDeedTerm).filter(
                    ExtractedSalesDeedTerm.sales_deed_id == db_sd.id,
                    *live_filter(ExtractedSalesDeedTerm)
                ).all()
            }
            seen_term_seq = set()
            for i, term in enumerate(terms):
                seq = i + 1
                seen_term_seq.add(seq)
                existing_term = existing_terms.get(seq)
                if not existing_term:
                    db_term = ExtractedSalesDeedTerm(sales_deed_id=db_sd.id, term_sequence=seq)
                    mark_created(db_term, audit_user)
                    self.db.add(db_term)
                else:
                    close_version(existing_term, audit_user)
                    db_term = clone_version(existing_term, audit_user, sales_deed_id=db_sd.id, term_sequence=seq)
                    self.db.add(db_term)
                db_term.term_text = self._normalize_text_value(term)
            for seq, row in existing_terms.items():
                if seq not in seen_term_seq:
                    close_version(row, audit_user, deleted=True)
        except Exception as exc:
            self.db.rollback()
            raise ValueError(f"Sale Deed DB projection failed: {exc}") from exc

    def _save_to_specific_extracted_table(self, application_number: str, document_id: int, data: Dict, doc_type: str, audit_user=None):
        """
        Saves extracted data to document-specific tables.
        Handles UPSERT by deleting existing record for this document_id first.
        """
        norm_type = self._normalize_doc_type(doc_type)

        if norm_type == "sanction_letter":
            sl_dom = data.get("SanctionLetterDOM", {})
            co_borrowers = self._as_list(sl_dom.get("coBorrowers"))
            schedule_property = self._extract_schedule_property(sl_dom)

            db_sl = self.db.query(ExtractedSanctionLetter).filter(
                ExtractedSanctionLetter.document_id == document_id,
                *live_filter(ExtractedSanctionLetter)
            ).first()
            if not db_sl:
                db_sl = ExtractedSanctionLetter(
                    application_number=application_number,
                    document_id=document_id,
                )
                mark_created(db_sl, audit_user)
                self.db.add(db_sl)
            else:
                close_version(db_sl, audit_user)
                db_sl = clone_version(db_sl, audit_user)
                self.db.add(db_sl)

            db_sl.application_number = application_number
            db_sl.loan_account_number = sl_dom.get("loanAccountNumber")
            db_sl.borrower_name = sl_dom.get("borrowerName")
            db_sl.borrower_address = sl_dom.get("borrowerAddress")
            db_sl.borrower_pan = sl_dom.get("borrowerPan")
            db_sl.co_borrower_1_name = co_borrowers[0].get("coBorrowerName") if len(co_borrowers) > 0 else None
            db_sl.co_borrower_1_address = co_borrowers[0].get("coBorrowerAddress") if len(co_borrowers) > 0 else None
            db_sl.co_borrower_1_pan = co_borrowers[0].get("coBorrowerPan") if len(co_borrowers) > 0 else None
            db_sl.co_borrower_2_name = co_borrowers[1].get("coBorrowerName") if len(co_borrowers) > 1 else None
            db_sl.co_borrower_2_address = co_borrowers[1].get("coBorrowerAddress") if len(co_borrowers) > 1 else None
            db_sl.co_borrower_2_pan = co_borrowers[1].get("coBorrowerPan") if len(co_borrowers) > 1 else None
            db_sl.co_borrower_3_name = co_borrowers[2].get("coBorrowerName") if len(co_borrowers) > 2 else None
            db_sl.co_borrower_3_address = co_borrowers[2].get("coBorrowerAddress") if len(co_borrowers) > 2 else None
            db_sl.co_borrower_3_pan = co_borrowers[2].get("coBorrowerPan") if len(co_borrowers) > 2 else None
            db_sl.co_borrower_4_name = co_borrowers[3].get("coBorrowerName") if len(co_borrowers) > 3 else None
            db_sl.co_borrower_4_address = co_borrowers[3].get("coBorrowerAddress") if len(co_borrowers) > 3 else None
            db_sl.co_borrower_4_pan = co_borrowers[3].get("coBorrowerPan") if len(co_borrowers) > 3 else None
            db_sl.co_borrower_5_name = co_borrowers[4].get("coBorrowerName") if len(co_borrowers) > 4 else None
            db_sl.co_borrower_5_address = co_borrowers[4].get("coBorrowerAddress") if len(co_borrowers) > 4 else None
            db_sl.co_borrower_5_pan = co_borrowers[4].get("coBorrowerPan") if len(co_borrowers) > 4 else None
            db_sl.sanction_date = sl_dom.get("sanctionDate")
            db_sl.sanction_amount = sl_dom.get("sanctionAmount")
            db_sl.loan_amount = sl_dom.get("loanAmount")
            db_sl.loan_tenure = sl_dom.get("loanTenure")
            db_sl.interest_rate = sl_dom.get("interestRate")
            db_sl.emi_amount = sl_dom.get("emiAmount")
            db_sl.repayment_frequency = sl_dom.get("repaymentFrequency")
            db_sl.property_description = schedule_property.get("description")
            db_sl.property_address = schedule_property.get("propertyAddress")
            db_sl.survey_number = schedule_property.get("surveyNumber")
            db_sl.plot_number = schedule_property.get("plotNumber")
            db_sl.boundary_north = schedule_property.get("boundaries", {}).get("north")
            db_sl.boundary_south = schedule_property.get("boundaries", {}).get("south")
            db_sl.boundary_east = schedule_property.get("boundaries", {}).get("east")
            db_sl.boundary_west = schedule_property.get("boundaries", {}).get("west")
        
        elif norm_type == "loan_agreement":
            la_dom = data.get("LoanAgreementDOM", {})
            co_borrowers = self._as_list(la_dom.get("coBorrowers"))
            prop = self._extract_schedule_property(la_dom)

            db_la = self.db.query(ExtractedLoanAgreement).filter(
                ExtractedLoanAgreement.document_id == document_id,
                *live_filter(ExtractedLoanAgreement)
            ).first()
            if not db_la:
                db_la = ExtractedLoanAgreement(
                    application_number=application_number,
                    document_id=document_id,
                )
                mark_created(db_la, audit_user)
                self.db.add(db_la)
            else:
                close_version(db_la, audit_user)
                db_la = clone_version(db_la, audit_user)
                self.db.add(db_la)

            db_la.application_number = application_number
            db_la.sanction_date = la_dom.get("sanctionDate")
            db_la.loan_agreement_date = la_dom.get("loanAgreementDate")
            db_la.loan_amount = la_dom.get("loanAmount")
            db_la.loan_amount_in_words = self._fit_str(la_dom.get("loanAmountInWords"))
            db_la.borrower_name = la_dom.get("borrowerName")
            db_la.borrower_address = la_dom.get("borrowerAddress")
            db_la.borrower_pan = la_dom.get("borrowerPan")
            db_la.co_borrower_1_name = co_borrowers[0].get("name") if len(co_borrowers) > 0 else None
            db_la.co_borrower_1_address = co_borrowers[0].get("address") if len(co_borrowers) > 0 else None
            db_la.co_borrower_1_pan = co_borrowers[0].get("pan") if len(co_borrowers) > 0 else None
            db_la.co_borrower_2_name = co_borrowers[1].get("name") if len(co_borrowers) > 1 else None
            db_la.co_borrower_2_address = co_borrowers[1].get("address") if len(co_borrowers) > 1 else None
            db_la.co_borrower_2_pan = co_borrowers[1].get("pan") if len(co_borrowers) > 1 else None
            db_la.co_borrower_3_name = co_borrowers[2].get("name") if len(co_borrowers) > 2 else None
            db_la.co_borrower_3_address = co_borrowers[2].get("address") if len(co_borrowers) > 2 else None
            db_la.co_borrower_3_pan = co_borrowers[2].get("pan") if len(co_borrowers) > 2 else None
            db_la.co_borrower_4_name = co_borrowers[3].get("name") if len(co_borrowers) > 3 else None
            db_la.co_borrower_4_address = co_borrowers[3].get("address") if len(co_borrowers) > 3 else None
            db_la.co_borrower_4_pan = co_borrowers[3].get("pan") if len(co_borrowers) > 3 else None
            db_la.co_borrower_5_name = co_borrowers[4].get("name") if len(co_borrowers) > 4 else None
            db_la.co_borrower_5_address = co_borrowers[4].get("address") if len(co_borrowers) > 4 else None
            db_la.co_borrower_5_pan = co_borrowers[4].get("pan") if len(co_borrowers) > 4 else None
            db_la.property_address = prop.get("propertyAddress")
            db_la.property_description = prop.get("description")
            db_la.survey_number = prop.get("surveyNumber")
            db_la.plot_number = prop.get("plotNumber")
            db_la.boundary_north = prop.get("boundaries", {}).get("north")
            db_la.boundary_south = prop.get("boundaries", {}).get("south")
            db_la.boundary_east = prop.get("boundaries", {}).get("east")
            db_la.boundary_west = prop.get("boundaries", {}).get("west")

        elif norm_type == "legal_report":
            legal_dom = data.get("LegalReport", {})
            if not isinstance(legal_dom, dict) or not legal_dom:
                legal_dom = data.get("Legal_Report", {})
            if not isinstance(legal_dom, dict) or not legal_dom:
                legal_dom = data

            doc_info = legal_dom.get("Document_Information") or {}
            lender = legal_dom.get("Lender_Details") or {}
            borrower = legal_dom.get("Borrower_Details") or {}
            owner = legal_dom.get("Property_Owner_Details") or {}
            loan = legal_dom.get("Loan_Details") or {}
            prop = legal_dom.get("Property_Details") or {}
            title_tracing = legal_dom.get("Title_Tracing") or {}
            encumbrance = legal_dom.get("Encumbrance_Details") or {}
            verification = legal_dom.get("Legal_Verification_Checklist") or {}
            tax = legal_dom.get("Tax_And_Revenue_Details") or {}
            certification = legal_dom.get("Title_Certification") or {}

            db_lr = self.db.query(ExtractedLegalReport).filter(
                ExtractedLegalReport.document_id == document_id,
                *live_filter(ExtractedLegalReport)
            ).first()
            if not db_lr:
                db_lr = ExtractedLegalReport(
                    application_number=application_number,
                    document_id=document_id,
                )
                mark_created(db_lr, audit_user)
                self.db.add(db_lr)
            else:
                close_version(db_lr, audit_user)
                db_lr = clone_version(db_lr, audit_user)
                self.db.add(db_lr)

            db_lr.application_number = application_number
            db_lr.report_title = self._fit_str(doc_info.get("Report_Title"), 255)
            db_lr.law_firm_name = self._fit_str(doc_info.get("Law_Firm_Name"), 255)
            db_lr.advocate_name = self._fit_str(doc_info.get("Advocate_Name"), 255)
            db_lr.document_category = self._fit_str(doc_info.get("Document_Category"), 255)
            db_lr.document_sub_category = self._fit_str(doc_info.get("Document_Sub_Category"), 255)
            db_lr.reference_number = self._fit_str(doc_info.get("Reference_Number"), 100)
            db_lr.report_date = self._fit_str(doc_info.get("Report_Date"), 50)
            db_lr.proposal_number = self._fit_str(doc_info.get("Proposal_Number"), 100)
            db_lr.document_state = self._fit_str(doc_info.get("State"), 100)
            db_lr.issuing_office_address = self._normalize_text_value(doc_info.get("Issuing_Office_Address"))
            db_lr.remarks = self._normalize_text_value(doc_info.get("Remarks"))

            db_lr.bank_or_nbfc_name = self._fit_str(lender.get("Bank_Or_NBFC_Name"), 255)
            db_lr.branch_name = self._fit_str(lender.get("Branch_Name"), 255)
            db_lr.addressed_to = self._normalize_text_value(lender.get("Addressed_To"))

            db_lr.primary_borrower_name = self._fit_str(borrower.get("Primary_Borrower_Name"), 255)
            db_lr.co_borrowers_json = self._normalize_list_of_dicts(borrower.get("Co_Borrowers"))
            db_lr.borrower_full_name_and_address = self._normalize_text_value(borrower.get("Borrower_Full_Name_And_Address"))
            db_lr.borrower_constitution = self._fit_str(borrower.get("Constitution_Of_Owner"), 255)

            db_lr.owner_name = self._fit_str(owner.get("Owner_Name"), 255)
            db_lr.co_owners_json = self._normalize_list_of_dicts(owner.get("Co_Owners"))
            db_lr.owner_address = self._normalize_text_value(owner.get("Owner_Address"))
            db_lr.owner_constitution = self._fit_str(owner.get("Owner_Constitution"), 255)

            db_lr.loan_account_number = self._fit_str(loan.get("Loan_Account_Number"), 100)
            db_lr.loan_type = self._fit_str(loan.get("Loan_Type"), 100)
            db_lr.product_type = self._fit_str(loan.get("Product_Type"), 100)

            db_lr.property_address = self._normalize_text_value(prop.get("Property_Address"))
            db_lr.property_type = self._fit_str(prop.get("Property_Type"), 100)
            db_lr.village_or_town = self._fit_str(prop.get("Village_Or_Town"), 255)
            db_lr.taluk_or_circle = self._fit_str(prop.get("Taluk_Or_Circle"), 255)
            db_lr.district = self._fit_str(prop.get("District"), 255)
            db_lr.property_state = self._fit_str(prop.get("State"), 100)
            db_lr.registration_district = self._fit_str(prop.get("Registration_District"), 255)
            db_lr.sub_registration_district = self._fit_str(prop.get("Sub_Registration_District"), 255)
            db_lr.survey_number = self._fit_str(prop.get("Survey_Number"), 255)
            db_lr.re_survey_number = self._fit_str(prop.get("Re_Survey_Number"), 255)
            db_lr.plot_or_site_number = self._fit_str(prop.get("Plot_Or_Site_Number"), 100)
            db_lr.block_number = self._fit_str(prop.get("Block_Number"), 100)
            db_lr.layout_name = self._fit_str(prop.get("Layout_Name"), 255)
            db_lr.total_extent_hectares = self._fit_str(prop.get("Total_Extent_Hectares"), 100)
            db_lr.total_extent_acres = self._fit_str(prop.get("Total_Extent_Acres"), 100)
            db_lr.total_extent_sqft = self._fit_str(prop.get("Total_Extent_Sqft"), 100)
            db_lr.total_extent_sqmeter = self._fit_str(prop.get("Total_Extent_SqMeter"), 100)
            db_lr.land_use_type = self._fit_str(prop.get("Land_Use_Type"), 255)
            db_lr.properties_list_json = self._normalize_list_of_dicts(prop.get("Properties_List"))

            db_lr.documents_scrutinized_json = self._normalize_list_of_dicts(legal_dom.get("Documents_Scrutinized"))
            db_lr.documents_to_be_obtained_json = self._normalize_list_of_dicts(legal_dom.get("Documents_To_Be_Obtained"))

            db_lr.original_title_holder = self._fit_str(title_tracing.get("Original_Title_Holder"), 255)
            db_lr.chain_of_title_summary = self._normalize_text_value(title_tracing.get("Chain_Of_Title_Summary"))
            db_lr.current_title_holder = self._fit_str(title_tracing.get("Current_Title_Holder"), 255)
            db_lr.mode_of_acquisition = self._fit_str(title_tracing.get("Mode_Of_Acquisition"), 255)
            db_lr.title_tracing_period_from = self._fit_str(title_tracing.get("Title_Tracing_Period_From"), 50)
            db_lr.title_tracing_period_to = self._fit_str(title_tracing.get("Title_Tracing_Period_To"), 50)

            db_lr.encumbrance_certificate_number = self._fit_str(encumbrance.get("Encumbrance_Certificate_Number"), 100)
            db_lr.ec_period_from = self._fit_str(encumbrance.get("EC_Period_From"), 50)
            db_lr.ec_period_to = self._fit_str(encumbrance.get("EC_Period_To"), 50)
            db_lr.charges_registered = self._normalize_text_value(encumbrance.get("Charges_Registered"))
            db_lr.existing_mortgage_or_encumbrance = self._normalize_text_value(encumbrance.get("Existing_Mortgage_Or_Encumbrance"))
            db_lr.modt_details = self._normalize_text_value(encumbrance.get("MODT_Details"))

            db_lr.is_title_clear_and_marketable = self._fit_str(verification.get("Is_Title_Clear_And_Marketable"), 50)
            db_lr.is_property_free_of_encumbrance = self._fit_str(verification.get("Is_Property_Free_Of_Encumbrance"), 50)
            db_lr.is_original_title_document_in_order = self._fit_str(verification.get("Is_Original_Title_Document_In_Order"), 50)
            db_lr.is_property_within_municipal_limits = self._fit_str(verification.get("Is_Property_Within_Municipal_Limits"), 50)
            db_lr.is_property_agricultural_or_nonagricultural = self._fit_str(verification.get("Is_Property_Agricultural_Or_NonAgricultural"), 50)
            db_lr.is_property_leasehold = self._fit_str(verification.get("Is_Property_Leasehold"), 50)
            db_lr.lis_pendens_status = self._fit_str(verification.get("Lis_Pendens_Status"), 50)
            db_lr.minors_interest = self._normalize_text_value(verification.get("Minors_Interest"))
            db_lr.power_of_attorney_status = self._normalize_text_value(verification.get("Power_Of_Attorney_Status"))
            db_lr.noc_from_society_or_builder = self._normalize_text_value(verification.get("NOC_From_Society_Or_Builder"))
            db_lr.sarfaesi_applicability = self._normalize_text_value(verification.get("SARFAESI_Applicability"))
            db_lr.urban_land_ceiling_act_applicable = self._normalize_text_value(verification.get("Urban_Land_Ceiling_Act_Applicable"))
            db_lr.tenancy_laws_applicable = self._normalize_text_value(verification.get("Tenancy_Laws_Applicable"))
            db_lr.site_inspection_done = self._normalize_text_value(verification.get("Site_Inspection_Done"))
            db_lr.additional_document_required = self._normalize_text_value(verification.get("Additional_Document_Required"))
            db_lr.municipal_tax_paid_status = self._normalize_text_value(verification.get("Municipal_Tax_Paid_Status"))
            db_lr.municipal_tax_assessed_in_name_of = self._normalize_text_value(verification.get("Municipal_Tax_Assessed_In_Name_Of"))
            db_lr.construction_as_per_sanction_plan = self._normalize_text_value(verification.get("Construction_As_Per_Sanction_Plan"))

            db_lr.patta_number = self._fit_str(tax.get("Patta_Number"), 100)
            db_lr.property_tax_receipt_number = self._fit_str(tax.get("Property_Tax_Receipt_Number"), 100)
            db_lr.assessment_number = self._fit_str(tax.get("Assessment_Number"), 100)
            db_lr.tax_assessed_in_name_of = self._normalize_text_value(tax.get("Tax_Assessed_In_Name_Of"))
            db_lr.tax_receipt_date = self._fit_str(tax.get("Tax_Receipt_Date"), 50)

            db_lr.title_certification_opinion = self._normalize_text_value(certification.get("Title_Certification_Opinion"))
            db_lr.safeguards_to_be_observed = self._normalize_text_value(certification.get("Safeguards_To_Be_Observed"))
            db_lr.observation_remarks = self._normalize_text_value(certification.get("Observation_Remarks"))
            db_lr.certifying_advocate_name = self._fit_str(certification.get("Certifying_Advocate_Name"), 255)
            db_lr.certification_date = self._fit_str(certification.get("Certification_Date"), 50)
            db_lr.certification_place = self._fit_str(certification.get("Certification_Place"), 255)
            notes = certification.get("Notes_And_Conditions")
            if isinstance(notes, list):
                db_lr.notes_and_conditions_json = [
                    item for item in (self._fit_str(note, 4000) for note in notes) if item
                ]
            elif self._has_meaningful_content(notes):
                db_lr.notes_and_conditions_json = [self._fit_str(notes, 4000)]
            else:
                db_lr.notes_and_conditions_json = []

        elif norm_type == "memorandum_of_deposit_of_title_deeds":
            modt_dom = data.get("MODT_DocumentDOM", {})
            info = modt_dom.get("documentInfo", {})
            parties = modt_dom.get("parties", {})
            loan = modt_dom.get("loanDetails", {})
            raw_props = modt_dom.get("scheduleProperties")
            if raw_props is None:
                raw_props = modt_dom.get("scheduleProperty")
            properties = self._normalize_modt_properties(raw_props)
            stamp = modt_dom.get("stampAndFees", {})

            db_modt = self.db.query(ExtractedMODT).filter(
                ExtractedMODT.document_id == document_id,
                *live_filter(ExtractedMODT)
            ).first()
            if not db_modt:
                db_modt = ExtractedMODT(
                    application_number=application_number,
                    document_id=document_id,
                )
                mark_created(db_modt, audit_user)
                self.db.add(db_modt)
            else:
                close_version(db_modt, audit_user)
                db_modt = clone_version(db_modt, audit_user)
                self.db.add(db_modt)

            db_modt.application_number = application_number
            db_modt.document_type = self._fit_str(info.get("documentType"), 255)
            db_modt.execution_date = info.get("executionDate")
            db_modt.registration_date = info.get("registrationDate")
            db_modt.document_number = self._fit_str(info.get("documentNumber"), 100)
            db_modt.book_number = self._fit_str(info.get("bookNumber"), 100)
            db_modt.sub_registrar_office = self._fit_str(info.get("subRegistrarOffice"), 255)
            db_modt.depositor_name = self._fit_str(parties.get("depositorName"), 255)
            db_modt.depositor_address = parties.get("depositorAddress")
            db_modt.depositee_name = self._fit_str(parties.get("depositeeName"), 255)
            db_modt.depositee_address = parties.get("depositeeAddress")
            db_modt.loan_amount = self._fit_str(loan.get("loanAmount"), 100)
            db_modt.loan_amount_in_words = loan.get("loanAmountInWords")
            db_modt.loan_tenure = self._fit_str(loan.get("loanTenure"), 100)
            db_modt.stamp_duty = self._fit_str(stamp.get("stampDuty"), 100)
            db_modt.registration_fee = self._fit_str(stamp.get("registrationFee"), 100)
            db_modt.total_charges = self._fit_str(stamp.get("totalCharges"), 100)
            db_modt.deposited_documents_json = modt_dom.get("depositedDocuments", [])
            self.db.flush()
            for row in self.db.query(ExtractedMODTProperty).filter(
                ExtractedMODTProperty.modt_id == db_modt.id,
                *live_filter(ExtractedMODTProperty)
            ).all():
                close_version(row, audit_user, deleted=True)

            for idx, prop in enumerate(properties, start=1):
                if not isinstance(prop, dict):
                    continue
                boundaries = prop.get("boundaries") or {}
                if not isinstance(boundaries, dict):
                    boundaries = {}
                survey_numbers = prop.get("surveyNumbers")
                if isinstance(survey_numbers, (list, dict)):
                    survey_numbers = ", ".join(self._collect_non_empty_strings(survey_numbers))
                raw_property_text = prop.get("rawPropertyText")
                if raw_property_text is None:
                    raw_property_text = prop.get("raw_text")
                src_from = self._parse_numeric(prop.get("sourcePageFrom"))
                src_to = self._parse_numeric(prop.get("sourcePageTo"))
                child = ExtractedMODTProperty(
                        modt_id=db_modt.id,
                        schedule_key=self._fit_str(prop.get("scheduleKey"), 100),
                        property_index=idx,
                        property_description=prop.get("propertyDescription"),
                        raw_property_text=raw_property_text,
                        survey_numbers=self._fit_str(survey_numbers, 255),
                        plot_number=self._fit_str(prop.get("plotNumber"), 100),
                        extent=self._fit_str(prop.get("extent"), 100),
                        extent_unit=self._fit_str(prop.get("extentUnit"), 50),
                        village=self._fit_str(prop.get("village"), 255),
                        taluka_or_mandal=self._fit_str(prop.get("talukaOrMandal") or prop.get("mandal"), 255),
                        district=self._fit_str(prop.get("district"), 255),
                        state=self._fit_str(prop.get("state"), 100),
                        pincode=self._fit_str(prop.get("pincode"), 20),
                        boundary_north=self._fit_str(prop.get("boundaryNorth") or boundaries.get("north"), 255),
                        boundary_south=self._fit_str(prop.get("boundarySouth") or boundaries.get("south"), 255),
                        boundary_east=self._fit_str(prop.get("boundaryEast") or boundaries.get("east"), 255),
                        boundary_west=self._fit_str(prop.get("boundaryWest") or boundaries.get("west"), 255),
                        address_remarks=prop.get("addressRemarks"),
                        confidence=self._fit_str(prop.get("confidence"), 50),
                        source_page_from=int(src_from) if src_from is not None else None,
                        source_page_to=int(src_to) if src_to is not None else None,
                    )
                mark_created(child, audit_user)
                self.db.add(child)
            
        elif norm_type == "sale_deed":
            self._save_sales_deed(
                application_number=application_number,
                document_id=document_id,
                data=data,
                audit_user=audit_user,
            )
            return
            # Robust JSON access
            sd_dom = data.get("SalesDeed", {})
            if not sd_dom:
                # Fallback: if data itself looks like the sale deed object
                if data.get("Document_Information") or data.get("Document_Number"):
                    sd_dom = data

            doc_info = (
                sd_dom.get("Document_Information")
                or sd_dom.get("document_information")
                or {}
            )
            prop_info = (
                sd_dom.get("Property_Info")
                or sd_dom.get("property_info")
                or {}
            )
            pay_info = (
                sd_dom.get("Payment_Information")
                or sd_dom.get("payment_Information")
                or sd_dom.get("payment_information")
                or {}
            )
            schedules = (
                sd_dom.get("Schedule_Information")
                or sd_dom.get("schedule_information")
                or sd_dom.get("ScheduleInformation")
                or sd_dom.get("Schedules")
                or {}
            )

            db_sd = self.db.query(ExtractedSalesDeed).filter(
                ExtractedSalesDeed.document_id == document_id,
                *live_filter(ExtractedSalesDeed)
            ).first()
            if not db_sd:
                db_sd = ExtractedSalesDeed(
                    application_number=application_number,
                    document_id=document_id,
                )
                mark_created(db_sd, audit_user)
                self.db.add(db_sd)
                self.db.flush()
            else:
                close_version(db_sd, audit_user)
                db_sd = clone_version(db_sd, audit_user)
                self.db.add(db_sd)
                self.db.flush()

            db_sd.application_number = application_number
            db_sd.document_category = self._fit_str(doc_info.get("Document_Category"), 255)
            db_sd.document_sub_category = self._fit_str(doc_info.get("Document_Sub_Category"), 255)
            db_sd.document_number = self._fit_str(doc_info.get("Document_Number"), 100)
            db_sd.book_number = self._fit_str(doc_info.get("Book_Number"), 100)
            db_sd.execution_date = self._normalize_text_value(doc_info.get("Document_Execution_Date"), 50)
            db_sd.execution_location = self._normalize_text_value(doc_info.get("Document_Execution_Location"), 255)
            db_sd.state = self._fit_str(doc_info.get("State"), 100)
            db_sd.number_of_pages = self._fit_str(doc_info.get("Number_of_Pages"), 50)
            db_sd.sub_registrar_office = self._normalize_text_value(doc_info.get("Sub_Registrar_Office"), 255)
            db_sd.document_remarks = self._normalize_text_value(doc_info.get("Remarks"))
            db_sd.property_address = self._normalize_text_value(prop_info.get("Property_Address"))
            geo = prop_info.get("Geographic_Coordinates") or {}
            if not isinstance(geo, dict):
                geo = {}
            db_sd.latitude = self._fit_str(geo.get("Latitude"), 50)
            db_sd.longitude = self._fit_str(geo.get("Longitude"), 50)
            db_sd.market_value = self._fit_str(pay_info.get("Market_Value"), 100)
            db_sd.sale_transaction_value = self._fit_str(pay_info.get("Sale_Transaction_Value"), 100)
            db_sd.payment_remarks = self._normalize_text_value(pay_info.get("Remarks"))
            property_raw_text = sd_dom.get("Property_Raw_Text")
            if isinstance(property_raw_text, (dict, list)):
                property_raw_text = " ".join(self._collect_non_empty_strings(property_raw_text))

            description_payload = sd_dom.get("description")
            if isinstance(description_payload, (dict, list)):
                description_payload = " ".join(self._collect_non_empty_strings(description_payload))
            raw_description_payload = sd_dom.get("raw_description")
            if isinstance(raw_description_payload, (dict, list)):
                raw_description_payload = " ".join(self._collect_non_empty_strings(raw_description_payload))

            db_sd.remarks = self._normalize_text_value(sd_dom.get("Remarks"))
            db_sd.raw_description = (
                self._fit_str(raw_description_payload)
                or self._fit_str(description_payload)
                or self._fit_str(property_raw_text)
            )
            self.db.flush()

            # Refresh child rows under same parent id to avoid duplicates.
            for model in (
                ExtractedSalesDeedVendor,
                ExtractedSalesDeedPurchaser,
                ExtractedSalesDeedWitness,
                ExtractedSalesDeedAuthority,
                ExtractedSalesDeedPaymentDetail,
            ):
                for row in self.db.query(model).filter(model.sales_deed_id == db_sd.id, *live_filter(model)).all():
                    close_version(row, audit_user, deleted=True)

            # 1. Vendors
            vendors = self._as_list(sd_dom.get("Vendor"))
            for v in vendors:
                if not isinstance(v, dict):
                    continue
                v_ids = v.get("ID") or {}
                if not isinstance(v_ids, dict):
                    v_ids = {}
                db_vendor = ExtractedSalesDeedVendor(
                    sales_deed_id=db_sd.id,
                    name=self._normalize_text_value(v.get("Name"), 255),
                    relationship_text=self._normalize_text_value(v.get("Relationship"), 100),
                    relation_name=self._normalize_text_value(v.get("Relation_Name") or v.get("Relations_Name"), 255),
                    pan=self._normalize_text_value(v_ids.get("PAN"), 50),
                    aadhar=self._normalize_text_value(v_ids.get("AADHAR"), 50),
                    date_of_birth_age=self._normalize_text_value(v.get("Date_of_Birth_Age"), 100),
                    gender=self._normalize_text_value(v.get("Gender"), 50),
                    address=self._normalize_text_value(v.get("Address")),
                    signature_biometric_photo=self._normalize_text_value(v.get("Signature_Biometric_Photo"), 50),
                    remarks=self._normalize_text_value(v.get("Remarks"))
                )
                mark_created(db_vendor, audit_user)
                self.db.add(db_vendor)
                self.db.flush()
                
                # Vendor Representative
                rep = v.get("Representative_Details", {})
                if rep and isinstance(rep, dict) and rep.get("Name"):
                    r_ids = rep.get("ID")
                    if isinstance(r_ids, dict): # Handle if ID is dict
                        r_id_val = f"PAN:{r_ids.get('PAN')} AADHAR:{r_ids.get('AADHAR')}"
                    else:
                        r_id_val = str(r_ids)
                        
                    db_rep = ExtractedSalesDeedVendorRepresentative(
                        vendor_id=db_vendor.id,
                        name=self._normalize_text_value(rep.get("Name"), 255),
                        relationship_text=self._normalize_text_value(rep.get("Relationship"), 100),
                        relations_name=self._normalize_text_value(rep.get("Relations_Name"), 255),
                        representation_capacity=self._normalize_text_value(rep.get("Representation_Capacity"), 255),
                        document_reference=self._normalize_text_value(rep.get("Document_Reference"), 255),
                        id_value=self._normalize_text_value(r_id_val, 100),
                        date_of_birth_age=self._normalize_text_value(rep.get("Date_of_Birth_Age"), 100),
                        gender=self._normalize_text_value(rep.get("Gender"), 50),
                        address=self._normalize_text_value(rep.get("Address")),
                        signature_biometric_photo=self._normalize_text_value(rep.get("Signature_Biometric_Photo"), 50),
                        remarks=self._normalize_text_value(rep.get("Remarks"))
                    )
                    mark_created(db_rep, audit_user)
                    self.db.add(db_rep)

            # 2. Purchasers
            purchasers = self._as_list(sd_dom.get("Purchaser"))
            for p in purchasers:
                if not isinstance(p, dict):
                    continue
                p_ids = p.get("ID") or {}
                if not isinstance(p_ids, dict):
                    p_ids = {}
                db_purchaser = ExtractedSalesDeedPurchaser(
                    sales_deed_id=db_sd.id,
                    name=self._normalize_text_value(p.get("Name"), 255),
                    relationship_text=self._normalize_text_value(p.get("Relationship"), 100),
                    relations_name=self._normalize_text_value(p.get("Relations_Name"), 255),
                    pan=self._normalize_text_value(p_ids.get("PAN"), 50),
                    aadhar=self._normalize_text_value(p_ids.get("AADHAR") if isinstance(p_ids, dict) else None, 50),
                    date_of_birth_age=self._normalize_text_value(p.get("Date_of_Birth_Age"), 100),
                    gender=self._normalize_text_value(p.get("Gender"), 50),
                    address=self._normalize_text_value(p.get("Address")),
                    signature_biometric_photo=self._normalize_text_value(p.get("Signature_Biometric_Photo"), 50),
                    remarks=self._normalize_text_value(p.get("Remarks"))
                )
                mark_created(db_purchaser, audit_user)
                self.db.add(db_purchaser)
                self.db.flush()
                
                # Purchaser Representative
                rep = p.get("Representative_Details", {})
                if rep and isinstance(rep, dict) and rep.get("Name"):
                    r_ids = rep.get("ID")
                    r_id_val = str(r_ids)
                        
                    db_rep = ExtractedSalesDeedPurchaserRepresentative(
                        purchaser_id=db_purchaser.id,
                        name=self._normalize_text_value(rep.get("Name"), 255),
                        relationship_text=self._normalize_text_value(rep.get("Relationship"), 100),
                        relations_name=self._normalize_text_value(rep.get("Relations_Name"), 255),
                        representation_capacity=self._normalize_text_value(rep.get("Representation_Capacity"), 255),
                        document_reference=self._normalize_text_value(rep.get("Document_Reference"), 255),
                        id_value=self._normalize_text_value(r_id_val, 100),
                        date_of_birth_age=self._normalize_text_value(rep.get("Date_of_Birth_Age"), 100),
                        gender=self._normalize_text_value(rep.get("Gender"), 50),
                        address=self._normalize_text_value(rep.get("Address")),
                        signature_biometric_photo=self._normalize_text_value(rep.get("Signature_Biometric_Photo"), 50),
                        remarks=self._normalize_text_value(rep.get("Remarks"))
                    )
                    mark_created(db_rep, audit_user)
                    self.db.add(db_rep)

            # 3. Witnesses
            witnesses = self._as_list(sd_dom.get("Witness"))
            for w in witnesses:
                if not isinstance(w, dict):
                    continue
                w_ids = w.get("ID") or {}
                if not isinstance(w_ids, dict):
                    w_ids = {}
                db_witness = ExtractedSalesDeedWitness(
                    sales_deed_id=db_sd.id,
                    name=self._normalize_text_value(w.get("Name"), 255),
                    relationship_text=self._normalize_text_value(w.get("Relationship"), 100),
                    relations_name=self._normalize_text_value(w.get("Relations_Name"), 255),
                    pan=self._normalize_text_value(w_ids.get("PAN"), 50),
                    aadhar=self._normalize_text_value(w_ids.get("AADHAR"), 50),
                    date_of_birth_age=self._normalize_text_value(w.get("Date_of_Birth_Age"), 100),
                    gender=self._normalize_text_value(w.get("Gender"), 50),
                    address=self._normalize_text_value(w.get("Address")),
                    signature_biometric_photo=self._normalize_text_value(w.get("Signature_Biometric_Photo"), 50),
                    remarks=self._normalize_text_value(w.get("Remarks"))
                )
                mark_created(db_witness, audit_user)
                self.db.add(db_witness)
                self.db.flush()
                
                # Witness Representative
                rep = w.get("Representative_Details", {})
                if rep and isinstance(rep, dict) and rep.get("Name"):
                    r_ids = rep.get("ID")
                    r_id_val = str(r_ids)
                        
                    db_rep = ExtractedSalesDeedWitnessRepresentative(
                        witness_id=db_witness.id,
                        name=self._normalize_text_value(rep.get("Name"), 255),
                        relationship_text=self._normalize_text_value(rep.get("Relationship"), 100),
                        relations_name=self._normalize_text_value(rep.get("Relations_Name"), 255),
                        representation_capacity=self._normalize_text_value(rep.get("Representation_Capacity"), 255),
                        document_reference=self._normalize_text_value(rep.get("Document_Reference"), 255),
                        id_value=self._normalize_text_value(r_id_val, 100),
                        date_of_birth_age=self._normalize_text_value(rep.get("Date_of_Birth_Age"), 100),
                        gender=self._normalize_text_value(rep.get("Gender"), 50),
                        address=self._normalize_text_value(rep.get("Address")),
                        signature_biometric_photo=self._normalize_text_value(rep.get("Signature_Biometric_Photo"), 50),
                        remarks=self._normalize_text_value(rep.get("Remarks"))
                    )
                    mark_created(db_rep, audit_user)
                    self.db.add(db_rep)

            # 4. Authority
            auth = sd_dom.get("Authority", {})
            if auth:
                db_auth = ExtractedSalesDeedAuthority(
                    sales_deed_id=db_sd.id,
                    designation=self._normalize_text_value(auth.get("Designation"), 255),
                    sub_registrar_name=self._normalize_text_value(auth.get("Sub_Registrar_Name"), 255),
                    sub_registrar_signature=self._normalize_text_value(auth.get("Sub_Registrar_Signature"), 255),
                    sub_registrar_office=self._normalize_text_value(auth.get("Sub_Registrar_Office"), 255),
                    city=self._normalize_text_value(auth.get("City"), 100),
                    state=self._normalize_text_value(auth.get("State"), 100),
                    remarks=self._normalize_text_value(auth.get("Remarks"))
                )
                mark_created(db_auth, audit_user)
                self.db.add(db_auth)

            # 5. Payment Details
            payment_details = self._as_list(pay_info.get("Payment_Details"))
            for pd in payment_details:
                if not isinstance(pd, dict):
                    continue
                # pd is simpler dict like {"Payment_Details_1": {"Transaction_1": "..."}}
                for key, val in pd.items():
                    if isinstance(val, dict):
                        for t_key, t_val in val.items():
                            db_pay = ExtractedSalesDeedPaymentDetail(
                                sales_deed_id=db_sd.id,
                                payment_detail_key=key,
                                transaction_key=t_key,
                                transaction_value=self._normalize_text_value(t_val)
                            )
                            mark_created(db_pay, audit_user)
                            self.db.add(db_pay)

            # 6. Schedules (row-wise insert/update from LLM output)
            # Reuse the normalized schedule block resolved earlier with key fallbacks.
            if not isinstance(schedules, dict):
                schedules = {}

            # Keep one current row per explicit schedule key from extraction output.
            existing_schedules = {
                (r.schedule_type or "").strip().upper(): r
                for r in self.db.query(ExtractedSalesDeedSchedule).filter(
                    ExtractedSalesDeedSchedule.sales_deed_id == db_sd.id,
                    *live_filter(ExtractedSalesDeedSchedule)
                ).all()
            }

            seen_schedule_types = set()
            meaningful_schedule_found = False
            for raw_key, val in schedules.items():
                if not isinstance(val, dict):
                    continue
                # Ignore empty/null-only placeholder schedules from model output.
                if not self._collect_non_empty_strings(val):
                    continue

                schedule_type = self._fit_str((str(raw_key or "").strip() or "UNSPECIFIED").upper(), 50) or "UNSPECIFIED"
                seen_schedule_types.add(schedule_type)
                meaningful_schedule_found = True

                prop_addr = val.get("Property_Address") or {}  # nested
                if not isinstance(prop_addr, dict):
                    prop_addr = {}
                bounds = val.get("Property_Boundary_Definition") or {}  # nested
                if not isinstance(bounds, dict):
                    bounds = {}

                existing_schedule = existing_schedules.get(schedule_type)
                if not existing_schedule:
                    db_sched = ExtractedSalesDeedSchedule(
                        sales_deed_id=db_sd.id,
                        schedule_type=schedule_type,
                    )
                    mark_created(db_sched, audit_user)
                    self.db.add(db_sched)
                else:
                    close_version(existing_schedule, audit_user)
                    db_sched = clone_version(
                        existing_schedule,
                        audit_user,
                        sales_deed_id=db_sd.id,
                        schedule_type=schedule_type,
                    )
                    self.db.add(db_sched)

                db_sched.property_extent = self._normalize_text_value(val.get("Property_Extent"), 100)
                db_sched.property_extent_unit = self._normalize_text_value(val.get("Property_Extent_Unit"), 50)
                db_sched.plot_dimension = self._normalize_text_value(val.get("Plot_Dimension"), 100)
                db_sched.survey_number = self._normalize_text_value(val.get("Survey_Number"), 255)
                db_sched.old_survey_number = self._normalize_text_value(val.get("Old_Survey_Number"), 255)
                db_sched.ts_number = self._normalize_text_value(val.get("TS_Number"), 255)
                db_sched.plot_number = self._normalize_text_value(prop_addr.get("Plot_Number"), 100)
                db_sched.village_street_name = self._normalize_text_value(prop_addr.get("Village_Street_Name"), 255)
                db_sched.jurisdiction = self._normalize_text_value(prop_addr.get("Jurisdiction"), 255)
                db_sched.address_remarks = self._normalize_text_value(prop_addr.get("Remarks"))
                db_sched.boundary_east = self._normalize_text_value(bounds.get("East"), 255)
                db_sched.boundary_west = self._normalize_text_value(bounds.get("West"), 255)
                db_sched.boundary_north = self._normalize_text_value(bounds.get("North"), 255)
                db_sched.boundary_south = self._normalize_text_value(bounds.get("South"), 255)
                sched_raw_text = (
                    val.get("raw_text")
                    or val.get("Raw_Text")
                    or val.get("Property_Raw_Text")
                    or val.get("Description")
                    or val.get("description")
                )
                if isinstance(sched_raw_text, (dict, list)):
                    sched_raw_text = " ".join(self._collect_non_empty_strings(sched_raw_text))
                db_sched.raw_text = self._normalize_text_value(sched_raw_text)

            # Only prune prior schedules when this run produced meaningful schedule content.
            # Prevents accidental data loss if model returns null-only placeholders.
            if meaningful_schedule_found:
                for schedule_type, row in existing_schedules.items():
                    if schedule_type not in seen_schedule_types:
                        close_version(row, audit_user, deleted=True)

            # 7. Parent Document Flows
            parent_doc_details = sd_dom.get("Parent_Document_Details") or {}
            if not isinstance(parent_doc_details, dict):
                parent_doc_details = {}
            parent_flows = self._as_list(parent_doc_details.get("Flow"))
            existing_flows = {
                r.flow_sequence: r
                for r in self.db.query(ExtractedSalesDeedParentFlow).filter(
                    ExtractedSalesDeedParentFlow.sales_deed_id == db_sd.id,
                    *live_filter(ExtractedSalesDeedParentFlow)
                ).all()
            }
            seen_flow_seq = set()
            for i, flow in enumerate(parent_flows):
                seq = i + 1
                seen_flow_seq.add(seq)
                existing_flow = existing_flows.get(seq)
                if not existing_flow:
                    db_flow = ExtractedSalesDeedParentFlow(
                        sales_deed_id=db_sd.id,
                        flow_sequence=seq,
                    )
                    mark_created(db_flow, audit_user)
                    self.db.add(db_flow)
                else:
                    close_version(existing_flow, audit_user)
                    db_flow = clone_version(
                        existing_flow,
                        audit_user,
                        sales_deed_id=db_sd.id,
                        flow_sequence=seq,
                    )
                    self.db.add(db_flow)
                db_flow.flow_value = self._normalize_text_value(flow)
            for seq, row in existing_flows.items():
                if seq not in seen_flow_seq:
                    close_version(row, audit_user, deleted=True)

            # 8. Terms and Conditions
            terms_block = sd_dom.get("Terms_and_Conditions") or {}
            if not isinstance(terms_block, dict):
                terms_block = {}
            terms = self._as_list(terms_block.get("Text"))
            existing_terms = {
                r.term_sequence: r
                for r in self.db.query(ExtractedSalesDeedTerm).filter(
                    ExtractedSalesDeedTerm.sales_deed_id == db_sd.id,
                    *live_filter(ExtractedSalesDeedTerm)
                ).all()
            }
            seen_term_seq = set()
            for i, term in enumerate(terms):
                seq = i + 1
                seen_term_seq.add(seq)
                existing_term = existing_terms.get(seq)
                if not existing_term:
                    db_term = ExtractedSalesDeedTerm(
                        sales_deed_id=db_sd.id,
                        term_sequence=seq,
                    )
                    mark_created(db_term, audit_user)
                    self.db.add(db_term)
                else:
                    close_version(existing_term, audit_user)
                    db_term = clone_version(
                        existing_term,
                        audit_user,
                        sales_deed_id=db_sd.id,
                        term_sequence=seq,
                    )
                    self.db.add(db_term)
                db_term.term_text = self._normalize_text_value(term)
            for seq, row in existing_terms.items():
                if seq not in seen_term_seq:
                    close_version(row, audit_user, deleted=True)

        elif norm_type == "foreclosure_statement":
            fs_keys = ["ForeclosureStatement", "Foreclosure_Statement", "ForeclosureStatemen"]
            fs = {}
            for k in fs_keys:
                if k in data:
                    fs = data[k]
                    break

            doc_info = fs.get("Document_Information", {})
            borrower = fs.get("Borrower_Details", {})
            loan = fs.get("Loan_Details", {})
            charges = fs.get("Charges_Breakup", {})
            validity = fs.get("Validity_And_Conditions", {})

            db_fs = self.db.query(ExtractedForeclosureStatement).filter(
                ExtractedForeclosureStatement.document_id == document_id,
                *live_filter(ExtractedForeclosureStatement)
            ).first()
            if not db_fs:
                db_fs = ExtractedForeclosureStatement(
                    application_number=application_number,
                    document_id=document_id,
                )
                mark_created(db_fs, audit_user)
                self.db.add(db_fs)
                self.db.flush()
            else:
                close_version(db_fs, audit_user)
                db_fs = clone_version(db_fs, audit_user)
                self.db.add(db_fs)
                self.db.flush()

            db_fs.application_number = application_number
            db_fs.bank_name = doc_info.get("Bank_Name")
            db_fs.document_category = doc_info.get("Document_Category")
            db_fs.document_sub_category = doc_info.get("Document_Sub_Category")
            db_fs.document_date = self._parse_date(doc_info.get("Document_Date"))
            db_fs.loan_account_number = doc_info.get("Loan_Account_Number")
            db_fs.loan_type = doc_info.get("Loan_Type")
            db_fs.issuing_branch = doc_info.get("Issuing_Branch")
            db_fs.state = doc_info.get("State")
            db_fs.remarks = doc_info.get("Remarks")

            db_fs.borrower_name = borrower.get("Borrower_Name")
            db_fs.address = borrower.get("Address")

            db_fs.loan_sanction_date = self._parse_date(loan.get("Loan_Sanction_Date"))
            db_fs.foreclosure_request_date = self._parse_date(loan.get("Foreclosure_Request_Date"))
            db_fs.foreclosure_calculation_date = self._parse_date(loan.get("Foreclosure_Calculation_Date"))
            db_fs.outstanding_principal = self._parse_numeric(
                loan.get("Outstanding_Principal") or loan.get("Principal_Outstanding_Overdue")
            )
            db_fs.pending_installments = self._parse_numeric(
                loan.get("Pending_Installments") or loan.get("instalment_overdue_amount_interest_overview")
            )
            db_fs.principal_outstanding_overdue = self._parse_numeric(
                loan.get("Principal_Outstanding_Overdue") or loan.get("Outstanding_Principal")
            )
            db_fs.instalment_overdue_amount_interest_overview = self._parse_numeric(
                loan.get("instalment_overdue_amount_interest_overview") or loan.get("Pending_Installments")
            )
            db_fs.interest_till_date = self._parse_numeric(loan.get("Interest_Till_Date"))
            db_fs.additional_interest = self._parse_numeric(loan.get("Additional_Interest"))
            db_fs.per_day_interest = self._parse_numeric(loan.get("Per_Day_Interest"))

            db_fs.foreclosure_charges = self._parse_numeric(charges.get("Foreclosure_Charges"))
            db_fs.prepayment_charges = self._parse_numeric(charges.get("Prepayment_Charges"))
            db_fs.late_payment_fee = self._parse_numeric(charges.get("Late_Payment_Fee"))
            db_fs.late_payment_interest = self._parse_numeric(charges.get("Late_Payment_Interest"))
            db_fs.cheque_bounce_charges = self._parse_numeric(
                charges.get("Cheque_Bounce_Charges") or charges.get("Check_Bounce_Charges")
            )
            db_fs.retrieval_other_charges = self._parse_numeric(
                charges.get("Retrieval_Other_Charges") or charges.get("Other_Amount_Charges")
            )
            db_fs.other_amount_charges = self._parse_numeric(
                charges.get("Other_Amount_Charges") or charges.get("Retrieval_Other_Charges")
            )
            db_fs.gst = self._parse_numeric(charges.get("GST"))
            db_fs.refund_if_any = self._parse_numeric(charges.get("Refund_If_Any"))
            db_fs.waiver_amount = self._parse_numeric(charges.get("Waiver_Amount"))
            db_fs.total_amount_payable = self._parse_numeric(
                fs.get("Total_Amount_Payable")
            )
            db_fs.valid_upto_date = self._parse_date(validity.get("Valid_Upto_Date"))

            # Replace child rows while preserving parent id
            for row in self.db.query(ExtractedForeclosureCoApplicant).filter(
                ExtractedForeclosureCoApplicant.foreclosure_id == db_fs.id,
                *live_filter(ExtractedForeclosureCoApplicant)
            ).all():
                close_version(row, audit_user, deleted=True)
            for row in self.db.query(ExtractedForeclosureNote).filter(
                ExtractedForeclosureNote.foreclosure_id == db_fs.id,
                *live_filter(ExtractedForeclosureNote)
            ).all():
                close_version(row, audit_user, deleted=True)
            
            # Co-Applicants
            for co in self._as_list(borrower.get("Co_Applicants")):
                if co:
                    db_co = ExtractedForeclosureCoApplicant(foreclosure_id=db_fs.id, name=co)
                    mark_created(db_co, audit_user)
                    self.db.add(db_co)
            
            # Notes
            for note in self._as_list(validity.get("Notes")):
                if note:
                    db_note = ExtractedForeclosureNote(foreclosure_id=db_fs.id, note_text=note)
                    mark_created(db_note, audit_user)
                    self.db.add(db_note)

        elif norm_type == "statement_of_accounts":
            soa_keys = ["StatementOfAccounts", "Statement_of_Accounts", "StatementOfAccount"]
            soa = {}
            for k in soa_keys:
                if k in data:
                    soa = data[k]
                    break
            
            doc_info = soa.get("Document_Information", {})
            borrower = soa.get("Borrower_Details", {})
            loan = soa.get("Loan_Details", {})
            transactions = self._as_list(soa.get("Transaction_Details"))
            
            db_soa = self.db.query(ExtractedStatementOfAccount).filter(
                ExtractedStatementOfAccount.document_id == document_id,
                *live_filter(ExtractedStatementOfAccount)
            ).first()
            if not db_soa:
                db_soa = ExtractedStatementOfAccount(
                    application_number=application_number,
                    document_id=document_id,
                )
                mark_created(db_soa, audit_user)
                self.db.add(db_soa)
                self.db.flush()
            else:
                close_version(db_soa, audit_user)
                db_soa = clone_version(db_soa, audit_user)
                self.db.add(db_soa)
                self.db.flush()

            db_soa.application_number = application_number
            db_soa.bank_name = doc_info.get("Bank_Name")
            db_soa.document_category = doc_info.get("Document_Category")
            db_soa.document_sub_category = doc_info.get("Document_Sub_Category")
            db_soa.statement_as_on_date = self._parse_date(doc_info.get("Statement_As_On_Date"))
            db_soa.loan_account_number = doc_info.get("Loan_Account_Number")
            db_soa.branch = doc_info.get("Branch")
            db_soa.currency = doc_info.get("Currency")
            db_soa.borrower_name = borrower.get("Borrower_Name")
            db_soa.co_applicant_name = borrower.get("Co_Applicant_Name")
            db_soa.address = borrower.get("Address")
            db_soa.pan_number = borrower.get("PAN_Number")
            db_soa.contact_details = borrower.get("Contact_Details")
            db_soa.loan_type = loan.get("Loan_Type")
            db_soa.sanction_date = self._parse_date(loan.get("Sanction_Date"))
            db_soa.sanction_amount = self._parse_numeric(loan.get("Sanction_Amount"))
            db_soa.disbursed_amount = self._parse_numeric(loan.get("Disbursed_Amount"))
            db_soa.tenure_months = loan.get("Tenure_Months")
            db_soa.interest_rate = loan.get("Interest_Rate")
            db_soa.interest_type = loan.get("Interest_Type")
            db_soa.emi_amount = self._parse_numeric(loan.get("EMI_Amount"))
            db_soa.repayment_frequency = loan.get("Repayment_Frequency")
            db_soa.repayment_mode = loan.get("Repayment_Mode")
            db_soa.loan_status = loan.get("Loan_Status")

            for row in self.db.query(ExtractedSOATransaction).filter(
                ExtractedSOATransaction.soa_id == db_soa.id,
                *live_filter(ExtractedSOATransaction)
            ).all():
                close_version(row, audit_user, deleted=True)
            
            # Transactions
            for txn in transactions:
                if not isinstance(txn, dict):
                    continue
                db_txn = ExtractedSOATransaction(
                    soa_id=db_soa.id,
                    transaction_date=self._parse_date(txn.get("Transaction_Date")),
                    value_date=self._parse_date(txn.get("Value_Date")),
                    transaction_type=txn.get("Transaction_Type"),
                    description=txn.get("Description"),
                    debit_amount=self._parse_numeric(txn.get("Debit_Amount")),
                    credit_amount=self._parse_numeric(txn.get("Credit_Amount")),
                    balance=self._parse_numeric(txn.get("Balance"))
                )
                mark_created(db_txn, audit_user)
                self.db.add(db_txn)

    def get_record(self, file_id: str) -> Optional[Dict]:
        doc = self.db.query(Document).filter(Document.file_id == file_id, *live_filter(Document)).first()
        if not doc:
            return None
        return self._to_dict(doc)

    def get_raw_parsed_output(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns the raw ai_parsed_output JSON from document_extracted_data.
        This is the legacy/UI payload store and can differ from extracted_* projection.
        """
        doc = self.db.query(Document).filter(Document.file_id == file_id, *live_filter(Document)).first()
        if not doc:
            return None
        row = self.db.query(DocumentExtractedData).filter(DocumentExtractedData.document_id == doc.id, *live_filter(DocumentExtractedData)).first()
        return row.ai_parsed_output if row else None
    def list_records(self, application_number: Optional[str] = None) -> List[Dict]:
        query = self.db.query(Document).filter(*live_filter(Document))
        if application_number:
            query = query.filter(Document.application_number == application_number)
        docs = query.order_by(Document.uploaded_at.desc()).all()
        return [self._to_dict(doc) for doc in docs]

    def list_doc_types(self, application_number: str) -> List[str]:
        rows = (
            self.db.query(Document.doc_type)
            .filter(Document.application_number == application_number, *live_filter(Document))
            .all()
        )
        return [r[0] for r in rows if r and r[0]]

    def delete_record(self, file_id: str, audit_user=None) -> bool:
        doc = self.db.query(Document).filter(Document.file_id == file_id, *live_filter(Document)).first()
        if doc:
            self._soft_delete_extracted_rows_for_document(doc.id, doc.doc_type, audit_user=audit_user)
            close_version(doc, audit_user, deleted=True)
            file_row = self.db.query(DocumentFile).filter(DocumentFile.document_id == doc.id, *live_filter(DocumentFile)).first()
            if file_row:
                close_version(file_row, audit_user, deleted=True)
            ocr_row = self.db.query(DocumentOCRText).filter(DocumentOCRText.document_id == doc.id, *live_filter(DocumentOCRText)).first()
            if ocr_row:
                close_version(ocr_row, audit_user, deleted=True)
            data_row = self.db.query(DocumentExtractedData).filter(DocumentExtractedData.document_id == doc.id, *live_filter(DocumentExtractedData)).first()
            if data_row:
                close_version(data_row, audit_user, deleted=True)
            for row in self.db.query(ApplicationContext).filter(ApplicationContext.document_id == doc.id, *live_filter(ApplicationContext)).all():
                close_version(row, audit_user, deleted=True)
            self.db.commit()
            return True
        return False

    def _soft_delete_extracted_rows_for_document(self, document_id: int, doc_type: str, audit_user=None) -> None:
        norm_type = self._normalize_doc_type(doc_type)

        if norm_type == "sanction_letter":
            row = self.db.query(ExtractedSanctionLetter).filter(
                ExtractedSanctionLetter.document_id == document_id,
                *live_filter(ExtractedSanctionLetter),
            ).first()
            if row:
                close_version(row, audit_user, deleted=True)
            return

        if norm_type == "loan_agreement":
            row = self.db.query(ExtractedLoanAgreement).filter(
                ExtractedLoanAgreement.document_id == document_id,
                *live_filter(ExtractedLoanAgreement),
            ).first()
            if row:
                close_version(row, audit_user, deleted=True)
            return

        if norm_type == "legal_report":
            row = self.db.query(ExtractedLegalReport).filter(
                ExtractedLegalReport.document_id == document_id,
                *live_filter(ExtractedLegalReport),
            ).first()
            if row:
                close_version(row, audit_user, deleted=True)
            return

        if norm_type in {"memorandum_of_deposit_of_title_deeds", "modt"}:
            row = self.db.query(ExtractedMODT).filter(
                ExtractedMODT.document_id == document_id,
                *live_filter(ExtractedMODT),
            ).first()
            if not row:
                return
            for child in self.db.query(ExtractedMODTProperty).filter(
                ExtractedMODTProperty.modt_id == row.id,
                *live_filter(ExtractedMODTProperty),
            ).all():
                close_version(child, audit_user, deleted=True)
            close_version(row, audit_user, deleted=True)
            return

        if norm_type == "sale_deed":
            row = self.db.query(ExtractedSalesDeed).filter(
                ExtractedSalesDeed.document_id == document_id,
                *live_filter(ExtractedSalesDeed),
            ).first()
            if not row:
                return

            vendors = self.db.query(ExtractedSalesDeedVendor).filter(
                ExtractedSalesDeedVendor.sales_deed_id == row.id,
                *live_filter(ExtractedSalesDeedVendor),
            ).all()
            for vendor in vendors:
                rep = self.db.query(ExtractedSalesDeedVendorRepresentative).filter(
                    ExtractedSalesDeedVendorRepresentative.vendor_id == vendor.id,
                    *live_filter(ExtractedSalesDeedVendorRepresentative),
                ).first()
                if rep:
                    close_version(rep, audit_user, deleted=True)
                close_version(vendor, audit_user, deleted=True)

            purchasers = self.db.query(ExtractedSalesDeedPurchaser).filter(
                ExtractedSalesDeedPurchaser.sales_deed_id == row.id,
                *live_filter(ExtractedSalesDeedPurchaser),
            ).all()
            for purchaser in purchasers:
                rep = self.db.query(ExtractedSalesDeedPurchaserRepresentative).filter(
                    ExtractedSalesDeedPurchaserRepresentative.purchaser_id == purchaser.id,
                    *live_filter(ExtractedSalesDeedPurchaserRepresentative),
                ).first()
                if rep:
                    close_version(rep, audit_user, deleted=True)
                close_version(purchaser, audit_user, deleted=True)

            witnesses = self.db.query(ExtractedSalesDeedWitness).filter(
                ExtractedSalesDeedWitness.sales_deed_id == row.id,
                *live_filter(ExtractedSalesDeedWitness),
            ).all()
            for witness in witnesses:
                rep = self.db.query(ExtractedSalesDeedWitnessRepresentative).filter(
                    ExtractedSalesDeedWitnessRepresentative.witness_id == witness.id,
                    *live_filter(ExtractedSalesDeedWitnessRepresentative),
                ).first()
                if rep:
                    close_version(rep, audit_user, deleted=True)
                close_version(witness, audit_user, deleted=True)

            child_models = (
                (ExtractedSalesDeedSchedule, ExtractedSalesDeedSchedule.sales_deed_id),
                (ExtractedSalesDeedPaymentDetail, ExtractedSalesDeedPaymentDetail.sales_deed_id),
                (ExtractedSalesDeedParentFlow, ExtractedSalesDeedParentFlow.sales_deed_id),
                (ExtractedSalesDeedTerm, ExtractedSalesDeedTerm.sales_deed_id),
            )
            for model, fk in child_models:
                for child in self.db.query(model).filter(fk == row.id, *live_filter(model)).all():
                    close_version(child, audit_user, deleted=True)

            authority = self.db.query(ExtractedSalesDeedAuthority).filter(
                ExtractedSalesDeedAuthority.sales_deed_id == row.id,
                *live_filter(ExtractedSalesDeedAuthority),
            ).first()
            if authority:
                close_version(authority, audit_user, deleted=True)

            close_version(row, audit_user, deleted=True)
            return

        if norm_type == "foreclosure_statement":
            row = self.db.query(ExtractedForeclosureStatement).filter(
                ExtractedForeclosureStatement.document_id == document_id,
                *live_filter(ExtractedForeclosureStatement),
            ).first()
            if not row:
                return
            for child in self.db.query(ExtractedForeclosureCoApplicant).filter(
                ExtractedForeclosureCoApplicant.foreclosure_id == row.id,
                *live_filter(ExtractedForeclosureCoApplicant),
            ).all():
                close_version(child, audit_user, deleted=True)
            for child in self.db.query(ExtractedForeclosureNote).filter(
                ExtractedForeclosureNote.foreclosure_id == row.id,
                *live_filter(ExtractedForeclosureNote),
            ).all():
                close_version(child, audit_user, deleted=True)
            close_version(row, audit_user, deleted=True)
            return

        if norm_type == "statement_of_account":
            row = self.db.query(ExtractedStatementOfAccount).filter(
                ExtractedStatementOfAccount.document_id == document_id,
                *live_filter(ExtractedStatementOfAccount),
            ).first()
            if not row:
                return
            for child in self.db.query(ExtractedSOATransaction).filter(
                ExtractedSOATransaction.soa_id == row.id,
                *live_filter(ExtractedSOATransaction),
            ).all():
                close_version(child, audit_user, deleted=True)
            close_version(row, audit_user, deleted=True)

    def _build_primary_extracted_output(self, document_id: int, doc_type: str) -> Optional[Dict[str, Any]]:
        norm_type = self._normalize_doc_type(doc_type)

        if norm_type == "sanction_letter":
            row = self.db.query(ExtractedSanctionLetter).filter(
                ExtractedSanctionLetter.document_id == document_id,
                *live_filter(ExtractedSanctionLetter),
            ).first()
            if not row:
                return None
            co_borrowers = []
            for i in range(1, 6):
                name = getattr(row, f"co_borrower_{i}_name")
                address = getattr(row, f"co_borrower_{i}_address")
                pan = getattr(row, f"co_borrower_{i}_pan")
                if name or address or pan:
                    co_borrowers.append(
                        {
                            "coBorrowerName": name,
                            "coBorrowerAddress": address,
                            "coBorrowerPan": pan,
                        }
                    )
            return {
                "SanctionLetterDOM": {
                    "loanAccountNumber": row.loan_account_number,
                    "borrowerName": row.borrower_name,
                    "borrowerAddress": row.borrower_address,
                    "borrowerPan": row.borrower_pan,
                    "coBorrowers": co_borrowers,
                    "sanctionDate": row.sanction_date,
                    "sanctionAmount": row.sanction_amount,
                    "loanAmount": row.loan_amount,
                    "loanTenure": row.loan_tenure,
                    "interestRate": row.interest_rate,
                    "emiAmount": row.emi_amount,
                    "repaymentFrequency": row.repayment_frequency,
                    "scheduleProperty": {
                        "description": row.property_description,
                        "surveyNumber": row.survey_number,
                        "plotNumber": row.plot_number,
                        "propertyAddress": row.property_address,
                        "boundaries": {
                            "north": row.boundary_north,
                            "south": row.boundary_south,
                            "east": row.boundary_east,
                            "west": row.boundary_west,
                        },
                    },
                }
            }

        if norm_type == "loan_agreement":
            row = self.db.query(ExtractedLoanAgreement).filter(
                ExtractedLoanAgreement.document_id == document_id,
                *live_filter(ExtractedLoanAgreement),
            ).first()
            if not row:
                return None
            co_borrowers = []
            for i in range(1, 6):
                name = getattr(row, f"co_borrower_{i}_name")
                address = getattr(row, f"co_borrower_{i}_address")
                pan = getattr(row, f"co_borrower_{i}_pan")
                if name or address or pan:
                    co_borrowers.append({"name": name, "address": address, "pan": pan})
            return {
                "LoanAgreementDOM": {
                    "sanctionDate": row.sanction_date,
                    "loanAgreementDate": row.loan_agreement_date,
                    "loanAmount": row.loan_amount,
                    "loanAmountInWords": row.loan_amount_in_words,
                    "borrowerName": row.borrower_name,
                    "borrowerAddress": row.borrower_address,
                    "borrowerPan": row.borrower_pan,
                    "coBorrowers": co_borrowers,
                    "scheduleProperty": {
                        "description": row.property_description,
                        "propertyAddress": row.property_address,
                        "surveyNumber": row.survey_number,
                        "plotNumber": row.plot_number,
                        "boundaries": {
                            "north": row.boundary_north,
                            "south": row.boundary_south,
                            "east": row.boundary_east,
                            "west": row.boundary_west,
                        },
                    },
                }
            }

        if norm_type == "legal_report":
            row = self.db.query(ExtractedLegalReport).filter(
                ExtractedLegalReport.document_id == document_id,
                *live_filter(ExtractedLegalReport),
            ).first()
            if not row:
                return None

            return {
                "LegalReport": {
                    "Document_Information": {
                        "Report_Title": row.report_title,
                        "Law_Firm_Name": row.law_firm_name,
                        "Advocate_Name": row.advocate_name,
                        "Document_Category": row.document_category,
                        "Document_Sub_Category": row.document_sub_category,
                        "Reference_Number": row.reference_number,
                        "Report_Date": row.report_date,
                        "Proposal_Number": row.proposal_number,
                        "State": row.document_state,
                        "Issuing_Office_Address": row.issuing_office_address,
                        "Remarks": row.remarks,
                    },
                    "Lender_Details": {
                        "Bank_Or_NBFC_Name": row.bank_or_nbfc_name,
                        "Branch_Name": row.branch_name,
                        "Addressed_To": row.addressed_to,
                    },
                    "Borrower_Details": {
                        "Primary_Borrower_Name": row.primary_borrower_name,
                        "Co_Borrowers": row.co_borrowers_json or [],
                        "Borrower_Full_Name_And_Address": row.borrower_full_name_and_address,
                        "Constitution_Of_Owner": row.borrower_constitution,
                    },
                    "Property_Owner_Details": {
                        "Owner_Name": row.owner_name,
                        "Co_Owners": row.co_owners_json or [],
                        "Owner_Address": row.owner_address,
                        "Owner_Constitution": row.owner_constitution,
                    },
                    "Loan_Details": {
                        "Loan_Account_Number": row.loan_account_number,
                        "Loan_Type": row.loan_type,
                        "Product_Type": row.product_type,
                    },
                    "Property_Details": {
                        "Property_Address": row.property_address,
                        "Property_Type": row.property_type,
                        "Village_Or_Town": row.village_or_town,
                        "Taluk_Or_Circle": row.taluk_or_circle,
                        "District": row.district,
                        "State": row.property_state,
                        "Registration_District": row.registration_district,
                        "Sub_Registration_District": row.sub_registration_district,
                        "Survey_Number": row.survey_number,
                        "Re_Survey_Number": row.re_survey_number,
                        "Plot_Or_Site_Number": row.plot_or_site_number,
                        "Block_Number": row.block_number,
                        "Layout_Name": row.layout_name,
                        "Total_Extent_Hectares": row.total_extent_hectares,
                        "Total_Extent_Acres": row.total_extent_acres,
                        "Total_Extent_Sqft": row.total_extent_sqft,
                        "Total_Extent_SqMeter": row.total_extent_sqmeter,
                        "Land_Use_Type": row.land_use_type,
                        "Properties_List": row.properties_list_json or [],
                    },
                    "Documents_Scrutinized": row.documents_scrutinized_json or [],
                    "Documents_To_Be_Obtained": row.documents_to_be_obtained_json or [],
                    "Title_Tracing": {
                        "Original_Title_Holder": row.original_title_holder,
                        "Chain_Of_Title_Summary": row.chain_of_title_summary,
                        "Current_Title_Holder": row.current_title_holder,
                        "Mode_Of_Acquisition": row.mode_of_acquisition,
                        "Title_Tracing_Period_From": row.title_tracing_period_from,
                        "Title_Tracing_Period_To": row.title_tracing_period_to,
                    },
                    "Encumbrance_Details": {
                        "Encumbrance_Certificate_Number": row.encumbrance_certificate_number,
                        "EC_Period_From": row.ec_period_from,
                        "EC_Period_To": row.ec_period_to,
                        "Charges_Registered": row.charges_registered,
                        "Existing_Mortgage_Or_Encumbrance": row.existing_mortgage_or_encumbrance,
                        "MODT_Details": row.modt_details,
                    },
                    "Legal_Verification_Checklist": {
                        "Is_Title_Clear_And_Marketable": row.is_title_clear_and_marketable,
                        "Is_Property_Free_Of_Encumbrance": row.is_property_free_of_encumbrance,
                        "Is_Original_Title_Document_In_Order": row.is_original_title_document_in_order,
                        "Is_Property_Within_Municipal_Limits": row.is_property_within_municipal_limits,
                        "Is_Property_Agricultural_Or_NonAgricultural": row.is_property_agricultural_or_nonagricultural,
                        "Is_Property_Leasehold": row.is_property_leasehold,
                        "Lis_Pendens_Status": row.lis_pendens_status,
                        "Minors_Interest": row.minors_interest,
                        "Power_Of_Attorney_Status": row.power_of_attorney_status,
                        "NOC_From_Society_Or_Builder": row.noc_from_society_or_builder,
                        "SARFAESI_Applicability": row.sarfaesi_applicability,
                        "Urban_Land_Ceiling_Act_Applicable": row.urban_land_ceiling_act_applicable,
                        "Tenancy_Laws_Applicable": row.tenancy_laws_applicable,
                        "Site_Inspection_Done": row.site_inspection_done,
                        "Additional_Document_Required": row.additional_document_required,
                        "Municipal_Tax_Paid_Status": row.municipal_tax_paid_status,
                        "Municipal_Tax_Assessed_In_Name_Of": row.municipal_tax_assessed_in_name_of,
                        "Construction_As_Per_Sanction_Plan": row.construction_as_per_sanction_plan,
                    },
                    "Tax_And_Revenue_Details": {
                        "Patta_Number": row.patta_number,
                        "Property_Tax_Receipt_Number": row.property_tax_receipt_number,
                        "Assessment_Number": row.assessment_number,
                        "Tax_Assessed_In_Name_Of": row.tax_assessed_in_name_of,
                        "Tax_Receipt_Date": row.tax_receipt_date,
                    },
                    "Title_Certification": {
                        "Title_Certification_Opinion": row.title_certification_opinion,
                        "Safeguards_To_Be_Observed": row.safeguards_to_be_observed,
                        "Observation_Remarks": row.observation_remarks,
                        "Certifying_Advocate_Name": row.certifying_advocate_name,
                        "Certification_Date": row.certification_date,
                        "Certification_Place": row.certification_place,
                        "Notes_And_Conditions": row.notes_and_conditions_json or [],
                    },
                }
            }

        if norm_type == "memorandum_of_deposit_of_title_deeds":
            row = self.db.query(ExtractedMODT).filter(
                ExtractedMODT.document_id == document_id,
                *live_filter(ExtractedMODT),
            ).first()
            if not row:
                return None
            prop_rows = (
                self.db.query(ExtractedMODTProperty)
                .filter(
                    ExtractedMODTProperty.modt_id == row.id,
                    *live_filter(ExtractedMODTProperty),
                )
                .order_by(ExtractedMODTProperty.property_index.asc(), ExtractedMODTProperty.id.asc())
                .all()
            )
            schedule_properties = []
            for p in prop_rows:
                schedule_properties.append(
                    {
                        "scheduleKey": p.schedule_key,
                        "propertyDescription": p.property_description,
                        "rawPropertyText": p.raw_property_text,
                        "surveyNumbers": p.survey_numbers,
                        "plotNumber": p.plot_number,
                        "extent": p.extent,
                        "extentUnit": p.extent_unit,
                        "village": p.village,
                        "talukaOrMandal": p.taluka_or_mandal,
                        "district": p.district,
                        "state": p.state,
                        "pincode": p.pincode,
                        "boundaryNorth": p.boundary_north,
                        "boundarySouth": p.boundary_south,
                        "boundaryEast": p.boundary_east,
                        "boundaryWest": p.boundary_west,
                        "addressRemarks": p.address_remarks,
                        "confidence": p.confidence,
                        "sourcePageFrom": p.source_page_from,
                        "sourcePageTo": p.source_page_to,
                    }
                )
            return {
                "MODT_DocumentDOM": {
                    "documentInfo": {
                        "documentType": row.document_type,
                        "executionDate": row.execution_date,
                        "registrationDate": row.registration_date,
                        "documentNumber": row.document_number,
                        "bookNumber": row.book_number,
                        "subRegistrarOffice": row.sub_registrar_office,
                    },
                    "parties": {
                        "depositorName": row.depositor_name,
                        "depositorAddress": row.depositor_address,
                        "depositeeName": row.depositee_name,
                        "depositeeAddress": row.depositee_address,
                    },
                    "loanDetails": {
                        "loanAmount": row.loan_amount,
                        "loanAmountInWords": row.loan_amount_in_words,
                        "loanTenure": row.loan_tenure,
                    },
                    "scheduleProperties": schedule_properties,
                    "depositedDocuments": row.deposited_documents_json or [],
                    "stampAndFees": {
                        "stampDuty": row.stamp_duty,
                        "registrationFee": row.registration_fee,
                        "totalCharges": row.total_charges,
                    }
                }
            }

        if norm_type == "sale_deed":
            sd = self.db.query(ExtractedSalesDeed).filter(
                ExtractedSalesDeed.document_id == document_id,
                *live_filter(ExtractedSalesDeed),
            ).first()
            if not sd:
                return None
            original_description = None
            raw_row = self.db.query(DocumentExtractedData).filter(
                DocumentExtractedData.document_id == document_id,
                *live_filter(DocumentExtractedData),
            ).first()
            if raw_row and isinstance(raw_row.ai_parsed_output, dict):
                raw_sd = raw_row.ai_parsed_output.get("SalesDeed")
                if isinstance(raw_sd, dict):
                    original_description = self._fit_str(raw_sd.get("description"))
            vendors = self.db.query(ExtractedSalesDeedVendor).filter(
                ExtractedSalesDeedVendor.sales_deed_id == sd.id,
                *live_filter(ExtractedSalesDeedVendor),
            ).all()
            purchasers = self.db.query(ExtractedSalesDeedPurchaser).filter(
                ExtractedSalesDeedPurchaser.sales_deed_id == sd.id,
                *live_filter(ExtractedSalesDeedPurchaser),
            ).all()
            witnesses = self.db.query(ExtractedSalesDeedWitness).filter(
                ExtractedSalesDeedWitness.sales_deed_id == sd.id,
                *live_filter(ExtractedSalesDeedWitness),
            ).all()
            schedules = self.db.query(ExtractedSalesDeedSchedule).filter(
                ExtractedSalesDeedSchedule.sales_deed_id == sd.id,
                *live_filter(ExtractedSalesDeedSchedule),
            ).all()
            payment_rows = self.db.query(ExtractedSalesDeedPaymentDetail).filter(
                ExtractedSalesDeedPaymentDetail.sales_deed_id == sd.id,
                *live_filter(ExtractedSalesDeedPaymentDetail),
            ).all()
            flow_rows = self.db.query(ExtractedSalesDeedParentFlow).filter(
                ExtractedSalesDeedParentFlow.sales_deed_id == sd.id,
                *live_filter(ExtractedSalesDeedParentFlow),
            ).order_by(ExtractedSalesDeedParentFlow.flow_sequence).all()
            term_rows = self.db.query(ExtractedSalesDeedTerm).filter(
                ExtractedSalesDeedTerm.sales_deed_id == sd.id,
                *live_filter(ExtractedSalesDeedTerm),
            ).order_by(ExtractedSalesDeedTerm.term_sequence).all()
            authority = self.db.query(ExtractedSalesDeedAuthority).filter(
                ExtractedSalesDeedAuthority.sales_deed_id == sd.id,
                *live_filter(ExtractedSalesDeedAuthority),
            ).first()

            def _rep_payload(rep):
                if not rep:
                    return None
                return {
                    "Name": rep.name,
                    "Relationship": rep.relationship_text,
                    "Relations_Name": rep.relations_name,
                    "Representation_Capacity": rep.representation_capacity,
                    "Document_Reference": rep.document_reference,
                    "ID": rep.id_value,
                    "Date_of_Birth_Age": rep.date_of_birth_age,
                    "Gender": rep.gender,
                    "Address": rep.address,
                    "Signature_Biometric_Photo": rep.signature_biometric_photo,
                    "Remarks": rep.remarks,
                }

            def vendor_obj(v):
                rep = self.db.query(ExtractedSalesDeedVendorRepresentative).filter(
                    ExtractedSalesDeedVendorRepresentative.vendor_id == v.id,
                    *live_filter(ExtractedSalesDeedVendorRepresentative),
                ).first()
                out = {
                    "Name": v.name,
                    "Relationship": v.relationship_text,
                    "Relation_Name": v.relation_name,
                    "ID": {"PAN": v.pan, "AADHAR": v.aadhar},
                    "Date_of_Birth_Age": v.date_of_birth_age,
                    "Gender": v.gender,
                    "Address": v.address,
                    "Signature_Biometric_Photo": v.signature_biometric_photo,
                    "Remarks": v.remarks,
                }
                rep_payload = _rep_payload(rep)
                if rep_payload:
                    out["Representative_Details"] = rep_payload
                return out

            def purchaser_obj(v):
                rep = self.db.query(ExtractedSalesDeedPurchaserRepresentative).filter(
                    ExtractedSalesDeedPurchaserRepresentative.purchaser_id == v.id,
                    *live_filter(ExtractedSalesDeedPurchaserRepresentative),
                ).first()
                out = {
                    "Name": v.name,
                    "Relationship": v.relationship_text,
                    "Relations_Name": v.relations_name,
                    "ID": {"PAN": v.pan, "AADHAR": v.aadhar},
                    "Date_of_Birth_Age": v.date_of_birth_age,
                    "Gender": v.gender,
                    "Address": v.address,
                    "Signature_Biometric_Photo": v.signature_biometric_photo,
                    "Remarks": v.remarks,
                }
                rep_payload = _rep_payload(rep)
                if rep_payload:
                    out["Representative_Details"] = rep_payload
                return out

            def witness_obj(v):
                rep = self.db.query(ExtractedSalesDeedWitnessRepresentative).filter(
                    ExtractedSalesDeedWitnessRepresentative.witness_id == v.id,
                    *live_filter(ExtractedSalesDeedWitnessRepresentative),
                ).first()
                out = {
                    "Name": v.name,
                    "Relationship": v.relationship_text,
                    "Relations_Name": v.relations_name,
                    "ID": {"PAN": v.pan, "AADHAR": v.aadhar},
                    "Date_of_Birth_Age": v.date_of_birth_age,
                    "Gender": v.gender,
                    "Address": v.address,
                    "Signature_Biometric_Photo": v.signature_biometric_photo,
                    "Remarks": v.remarks,
                }
                rep_payload = _rep_payload(rep)
                if rep_payload:
                    out["Representative_Details"] = rep_payload
                return out

            payment_map = {}
            for r in payment_rows:
                payment_map.setdefault(r.payment_detail_key, {})[r.transaction_key] = r.transaction_value
            payment_details = [{k: v} for k, v in payment_map.items()]

            schedule_rows = []
            schedule_info = {}
            for s in schedules:
                schedule_payload = {
                    "raw_text": s.raw_text,
                    "Property_Extent": s.property_extent,
                    "Property_Extent_Unit": s.property_extent_unit,
                    "Plot_Dimension": s.plot_dimension,
                    "Survey_Number": s.survey_number,
                    "Old_Survey_Number": s.old_survey_number,
                    "TS_Number": s.ts_number,
                    "Property_Address": {
                        "Plot_Number": s.plot_number,
                        "Village_Street_Name": s.village_street_name,
                        "Jurisdiction": s.jurisdiction,
                        "Remarks": s.address_remarks,
                    },
                    "Property_Boundary_Definition": {
                        "East": s.boundary_east,
                        "West": s.boundary_west,
                        "North": s.boundary_north,
                        "South": s.boundary_south,
                    },
                }
                schedule_rows.append({
                    "id": s.id,
                    "sales_deed_id": s.sales_deed_id,
                    "document_id": sd.document_id,
                    "application_number": sd.application_number,
                    "schedule_type": s.schedule_type,
                    **schedule_payload,
                })
                schedule_info[s.schedule_type] = schedule_payload

            return {
                "SalesDeed": {
                    "Document_Information": {
                        "Document_Category": sd.document_category,
                        "Document_Sub_Category": sd.document_sub_category,
                        "Document_Number": sd.document_number,
                        "Book_Number": sd.book_number,
                        "Document_Execution_Date": sd.execution_date,
                        "Document_Execution_Location": sd.execution_location,
                        "State": sd.state,
                        "Number_of_Pages": sd.number_of_pages,
                        "Sub_Registrar_Office": sd.sub_registrar_office,
                        "Remarks": sd.document_remarks,
                    },
                    "Property_Info": {
                        "Property_Address": sd.property_address,
                        "Geographic_Coordinates": {"Latitude": sd.latitude, "Longitude": sd.longitude},
                    },
                    "Payment_Information": {
                        "Market_Value": sd.market_value,
                        "Sale_Transaction_Value": sd.sale_transaction_value,
                        "Remarks": sd.payment_remarks,
                        "Payment_Details": payment_details,
                    },
                    "Remarks": sd.remarks,
                    "Vendor": [vendor_obj(v) for v in vendors],
                    "Purchaser": [purchaser_obj(v) for v in purchasers],
                    "Witness": [witness_obj(v) for v in witnesses],
                    "Schedule_Rows": schedule_rows,
                    "Schedule_Information": schedule_info,
                    "description": original_description,
                    "raw_description": sd.raw_description,
                    "Parent_Document_Details": {"Flow": [f.flow_value for f in flow_rows]},
                    "Terms_and_Conditions": {"Text": [t.term_text for t in term_rows]},
                    "Authority": {
                        "Designation": authority.designation if authority else None,
                        "Sub_Registrar_Name": authority.sub_registrar_name if authority else None,
                        "Sub_Registrar_Signature": authority.sub_registrar_signature if authority else None,
                        "Sub_Registrar_Office": authority.sub_registrar_office if authority else None,
                        "City": authority.city if authority else None,
                        "State": authority.state if authority else None,
                        "Remarks": authority.remarks if authority else None,
                    },
                }
            }

        if norm_type == "foreclosure_statement":
            fs = self.db.query(ExtractedForeclosureStatement).filter(
                ExtractedForeclosureStatement.document_id == document_id,
                *live_filter(ExtractedForeclosureStatement),
            ).first()
            if not fs:
                return None
            co_rows = self.db.query(ExtractedForeclosureCoApplicant).filter(
                ExtractedForeclosureCoApplicant.foreclosure_id == fs.id,
                *live_filter(ExtractedForeclosureCoApplicant),
            ).all()
            note_rows = self.db.query(ExtractedForeclosureNote).filter(
                ExtractedForeclosureNote.foreclosure_id == fs.id,
                *live_filter(ExtractedForeclosureNote),
            ).all()
            return {
                "ForeclosureStatement": {
                    "Document_Information": {
                        "Bank_Name": fs.bank_name,
                        "Document_Category": fs.document_category,
                        "Document_Sub_Category": fs.document_sub_category,
                        "Document_Date": self._date_to_str(fs.document_date),
                        "Loan_Account_Number": fs.loan_account_number,
                        "Loan_Type": fs.loan_type,
                        "Issuing_Branch": fs.issuing_branch,
                        "State": fs.state,
                        "Remarks": fs.remarks,
                    },
                    "Borrower_Details": {
                        "Borrower_Name": fs.borrower_name,
                        "Address": fs.address,
                        "Co_Applicants": [x.name for x in co_rows],
                    },
                    "Loan_Details": {
                        "Loan_Sanction_Date": self._date_to_str(fs.loan_sanction_date),
                        "Foreclosure_Request_Date": self._date_to_str(fs.foreclosure_request_date),
                        "Foreclosure_Calculation_Date": self._date_to_str(fs.foreclosure_calculation_date),
                        "Outstanding_Principal": str(fs.outstanding_principal) if fs.outstanding_principal is not None else None,
                        "Pending_Installments": str(fs.pending_installments) if fs.pending_installments is not None else None,
                        "Principal_Outstanding_Overdue": str(fs.principal_outstanding_overdue) if fs.principal_outstanding_overdue is not None else None,
                        "instalment_overdue_amount_interest_overview": str(fs.instalment_overdue_amount_interest_overview) if fs.instalment_overdue_amount_interest_overview is not None else None,
                        "Interest_Till_Date": str(fs.interest_till_date) if fs.interest_till_date is not None else None,
                        "Additional_Interest": str(fs.additional_interest) if fs.additional_interest is not None else None,
                        "Per_Day_Interest": str(fs.per_day_interest) if fs.per_day_interest is not None else None,
                    },
                    "Charges_Breakup": {
                        "Foreclosure_Charges": str(fs.foreclosure_charges) if fs.foreclosure_charges is not None else None,
                        "Prepayment_Charges": str(fs.prepayment_charges) if fs.prepayment_charges is not None else None,
                        "Late_Payment_Fee": str(fs.late_payment_fee) if fs.late_payment_fee is not None else None,
                        "Late_Payment_Interest": str(fs.late_payment_interest) if fs.late_payment_interest is not None else None,
                        "Cheque_Bounce_Charges": str(fs.cheque_bounce_charges) if fs.cheque_bounce_charges is not None else None,
                        "Retrieval_Other_Charges": str(fs.retrieval_other_charges) if fs.retrieval_other_charges is not None else None,
                        "Other_Amount_Charges": str(fs.other_amount_charges) if fs.other_amount_charges is not None else None,
                        "GST": str(fs.gst) if fs.gst is not None else None,
                        "Refund_If_Any": str(fs.refund_if_any) if fs.refund_if_any is not None else None,
                        "Waiver_Amount": str(fs.waiver_amount) if fs.waiver_amount is not None else None,
                    },
                    "Total_Amount_Payable": str(fs.total_amount_payable) if fs.total_amount_payable is not None else None,
                    "Validity_And_Conditions": {
                        "Valid_Upto_Date": self._date_to_str(fs.valid_upto_date),
                        "Notes": [n.note_text for n in note_rows],
                    },
                }
            }

        if norm_type == "statement_of_accounts":
            soa = self.db.query(ExtractedStatementOfAccount).filter(
                ExtractedStatementOfAccount.document_id == document_id,
                *live_filter(ExtractedStatementOfAccount),
            ).first()
            if not soa:
                return None
            txn_rows = self.db.query(ExtractedSOATransaction).filter(
                ExtractedSOATransaction.soa_id == soa.id,
                *live_filter(ExtractedSOATransaction),
            ).all()
            return {
                "StatementOfAccounts": {
                    "Document_Information": {
                        "Bank_Name": soa.bank_name,
                        "Document_Category": soa.document_category,
                        "Document_Sub_Category": soa.document_sub_category,
                        "Statement_As_On_Date": self._date_to_str(soa.statement_as_on_date),
                        "Loan_Account_Number": soa.loan_account_number,
                        "Branch": soa.branch,
                        "Currency": soa.currency,
                    },
                    "Borrower_Details": {
                        "Borrower_Name": soa.borrower_name,
                        "Co_Applicant_Name": soa.co_applicant_name,
                        "Address": soa.address,
                        "PAN_Number": soa.pan_number,
                        "Contact_Details": soa.contact_details,
                    },
                    "Loan_Details": {
                        "Loan_Type": soa.loan_type,
                        "Sanction_Date": self._date_to_str(soa.sanction_date),
                        "Sanction_Amount": str(soa.sanction_amount) if soa.sanction_amount is not None else None,
                        "Disbursed_Amount": str(soa.disbursed_amount) if soa.disbursed_amount is not None else None,
                        "Tenure_Months": soa.tenure_months,
                        "Interest_Rate": soa.interest_rate,
                        "Interest_Type": soa.interest_type,
                        "EMI_Amount": str(soa.emi_amount) if soa.emi_amount is not None else None,
                        "Repayment_Frequency": soa.repayment_frequency,
                        "Repayment_Mode": soa.repayment_mode,
                        "Loan_Status": soa.loan_status,
                    },
                    "Transaction_Details": [
                        {
                            "Transaction_Date": self._date_to_str(t.transaction_date),
                            "Value_Date": self._date_to_str(t.value_date),
                            "Transaction_Type": t.transaction_type,
                            "Description": t.description,
                            "Debit_Amount": str(t.debit_amount) if t.debit_amount is not None else None,
                            "Credit_Amount": str(t.credit_amount) if t.credit_amount is not None else None,
                            "Balance": str(t.balance) if t.balance is not None else None,
                        } for t in txn_rows
                    ],
                }
            }

        return None
        
    def _to_dict(self, doc: Document) -> Dict:
        # Reconstruct the dict format expected by the service
        # This ensures backward compatibility with the rest of the app
        primary_parsed_output = self._build_primary_extracted_output(doc.id, doc.doc_type)
        record = {
            "application_number": doc.application_number,
            "file_id": doc.file_id,
            "doc_type": doc.doc_type,
            "file_name": doc.file_name,
            "document_name": doc.document_name,
            "error_message": doc.error_message,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "s3_original": doc.files.original_path if doc.files else None,
            "original_pdf_path": doc.files.original_pdf_path if doc.files else None,
            "selected_page_range": doc.files.selected_page_range if doc.files else None,
            "ocr_text": doc.ocr_text.ocr_text if doc.ocr_text else None,
            "ai_parsed_output": primary_parsed_output,
            "application_context": [
                {
                    "name": ctx.name,
                    "father_name": ctx.father_name,
                    "dob_year": ctx.dob_year,
                    "gender": ctx.gender,
                    "address": ctx.address,
                    "identity_number": ctx.identity_number,
                    "identity_type": ctx.identity_type
                } for ctx in doc.application_context
            ],
             # Reconstruct paths dict
            "s3_paths": {
                "original": doc.files.original_path if doc.files else None,
                "ocr": doc.files.ocr_json_path if doc.files else None,
                "original_llm": doc.files.original_llm_path if doc.files else None,
                # We keep parsed_llm path hidden when extracted_* table has data,
                # so GET consumers use DB payload as source of truth.
                "parsed_llm": None if primary_parsed_output else (doc.files.parsed_llm_path if doc.files else None)
            }
        }
        return record
