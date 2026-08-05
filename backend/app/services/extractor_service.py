# app/services/extractor_service.py
import uuid
import json
import os
import re
import copy
from datetime import datetime
from typing import Any, Dict, Optional

from celery import current_task
from app.db.models.application import Application
from app.db.models.extracted_data import (
    ExtractedForeclosureStatement,
    ExtractedSanctionLetter,
    ExtractedStatementOfAccount,
)
from app.api.v1.dependencies.auth import AuditUser
from app.db.repositories.extractor_repo import ExtractorRepository
from app.utils.gemini import call_gemini_ai, repair_json_with_llm
from app.db.repositories.checklist_repo import ChecklistRepository
from app.db.repositories.report_repo import ReportRepository
from app.db.versioning import live_filter
from app.utils.ocr_utils import extract_text_with_docai
from app.utils.prompt_utils import load_prompt_and_schema, load_prompt
from app.services.translation_service import TranslationService

from app.gateways.storage_gateway import get_storage_gateway, resolve_any_reference_url
from app.core.settings import settings
from app.core.progress_store import set_progress, delete_progress

def update_progress(file_id: str, progress: int, stage: str):
    status = "processing"
    stage_lower = str(stage or "").lower()
    if progress >= 100 or stage_lower == "completed":
        status = "completed"
    elif "failed" in stage_lower:
        status = "failed"

    payload = {
        "progress": progress,
        "stage": stage,
        "status": status,
    }
    set_progress(file_id, payload)

    # Mirror the same progress into Celery state so the API can resolve it
    # even when Redis is temporarily unavailable or multiple workers are active.
    task = current_task
    if task and getattr(task, "update_state", None):
        try:
            task.update_state(
                state="PROGRESS" if status == "processing" else status.upper(),
                meta={
                    "file_id": file_id,
                    **payload,
                },
            )
        except Exception:
            pass
    print(f"Extraction Progress [{file_id}]: {stage} ({progress}%)")


class ExtractorService:
    """
    Industrial service layer for the extraction pipeline.
    Handles:
    - File upload → S3
    - OCR extraction
    - Prompt building
    - Gemini LLM call
    - JSON parsing & validation
    - Local JSON DB persistence
    """

    def __init__(self, db: Any):
        self.db = db
        self.repo = ExtractorRepository(db)
        self.s3 = get_storage_gateway()

    _INVALID_DOCUMENT_PROMPT_RULES = """
        CRITICAL INVALID-DOCUMENT CHECK:
        - If the document is unreadable, blank, or has zero relevant content, return:
        {
        "document_invalid": true,
        "error_message": "Reason why this document is invalid."
        }
        - If the document is a RELATED or SUPPORTING document (not the exact type 
        requested but contains some relevant fields), extract whatever fields 
        are available and add:
        {
        "document_warning": true,
        "warning_message": "This is a supporting document (e.g., heirship affidavit), 
        not a Sale Deed. Partial extraction performed."
        }
        - Only reject if the document has NO extractable relevant information at all.
        """

    def _sanitize_s3_prefix_part(self, value: Optional[str]) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
        text = re.sub(r"\s+", "_", text)
        text = re.sub(r"_+", "_", text)
        return text.strip("._")

    def _get_latest_non_empty_value(self, model: Any, field_name: str, application_number: str) -> str:
        value = (
            self.db.query(getattr(model, field_name))
            .filter(
                model.application_number == application_number,
                *live_filter(model),
            )
            .order_by(model.id.desc())
            .limit(1)
            .scalar()
        )
        return str(value or "").strip()

    def _resolve_loan_account_number(self, application_number: str) -> str:
        app = (
            self.db.query(Application)
            .filter(
                *live_filter(Application),
            )
            .filter(
                (Application.business_code == application_number)
                | (Application.record_id == application_number)
            )
            .order_by(Application.id.desc())
            .first()
        )
        candidates = [
            getattr(app, "loan_account_number", None) if app else None,
            self._get_latest_non_empty_value(
                ExtractedSanctionLetter,
                "loan_account_number",
                application_number,
            ),
            self._get_latest_non_empty_value(
                ExtractedForeclosureStatement,
                "loan_account_number",
                application_number,
            ),
            self._get_latest_non_empty_value(
                ExtractedStatementOfAccount,
                "loan_account_number",
                application_number,
            ),
        ]
        for candidate in candidates:
            storage_key = self._sanitize_s3_prefix_part(candidate)
            if storage_key:
                return storage_key
        return ""

    def _get_storage_prefix(self, application_number: str) -> str:
        storage_key = self._resolve_loan_account_number(application_number)
        if storage_key:
            return storage_key
        fallback = self._sanitize_s3_prefix_part(application_number)
        return fallback or application_number

    # -----------------------------------------------------------
    # 1. PROCESS DOCUMENT
    # -----------------------------------------------------------
    def process_document(
        self,
        file,
        doc_type: str,
        application_number: str,
        audit_user: AuditUser | None = None,
        language: Optional[str] = None,
        file_id: Optional[str] = None,
        filename: Optional[str] = None,
        file_path: Optional[str] = None,
        document_name: Optional[str] = None,
        original_file_path: Optional[str] = None,
        selected_page_range: Optional[str] = None,
    ):
        if file_id is None:
            file_id = str(uuid.uuid4())
        if filename is None:
            # If file is UploadFile, use its filename; else fallback
            if hasattr(file, 'filename'):
                filename = f"{file_id}_{file.filename}"
            else:
                filename = f"{file_id}_uploaded_file"
        if document_name is None:
            if hasattr(file, "filename") and getattr(file, "filename", None):
                document_name = file.filename
            else:
                document_name = filename

        # ---------------------------------
        # INITIAL PROGRESS
        # ---------------------------------
        update_progress(file_id, 5, "Starting extraction")

        temp_path: Optional[str] = None
        s3_original_url: Optional[str] = None

        try:
            # TEMP SAVE
            if file_path:
                temp_path = file_path
            else:
                temp_path = os.path.join(settings.TMP_DIR, filename)
                # Handle sync read (file object)
                content = file.read() if hasattr(file, 'read') else file
                with open(temp_path, "wb") as f:
                    f.write(content)

            # Validate file is not empty and is likely a PDF
            if os.path.getsize(temp_path) == 0:
                update_progress(file_id, 0, "Failed: Uploaded file is empty.")
                raise ValueError("Uploaded file is empty.")
            with open(temp_path, "rb") as f:
                header = f.read(5)
                if header != b'%PDF-':
                    update_progress(file_id, 0, "Failed: Uploaded file is not a valid PDF.")
                    raise ValueError("Uploaded file is not a valid PDF.")

            storage_prefix = self._get_storage_prefix(application_number)

            original_key = f"{storage_prefix}/original-document/{filename}"
            s3_original_url = self.s3.upload_file(temp_path, original_key)

            update_progress(file_id, 20, "OCR extraction in progress")

            ocr_text = extract_text_with_docai(temp_path, language=language)

            ocr_json_key = f"{storage_prefix}/ocr-output/{file_id}.json"
            self.s3.save_json({"ocr_text": ocr_text}, ocr_json_key)

            update_progress(file_id, 40, "OCR completed")

            doc_type = doc_type.strip()
            prompt_template, schema = load_prompt_and_schema(doc_type, return_fields=True)
            if not prompt_template:
                prompt_template = load_prompt(doc_type)

            if not prompt_template:
                raise ValueError(f"Prompt template for document type '{doc_type}' not found in YAML or prompts directory.")

            final_prompt = self._build_extraction_prompt(prompt_template, ocr_text or "")
            llm_output = call_gemini_ai(final_prompt, ocr_text)

            update_progress(file_id, 65, "AI extraction completed")

            extracted_json = self._safe_json_parse(llm_output)
            invalid_document_error = self._extract_document_error(extracted_json)
            if invalid_document_error:
                update_progress(file_id, 0, f"Failed: {invalid_document_error}")
                raise ValueError(invalid_document_error)

            if extracted_json is None:
                raise ValueError("LLM returned an invalid or unreadable response for this document.")
            mapped_json = self._map_output_to_schema(extracted_json, schema, doc_type)
            self._normalize_sales_deed_descriptions(mapped_json, doc_type)

            original_llm_key = f"{storage_prefix}/original-llm-output/{file_id}.json"
            self.s3.save_json({"raw_llm_output": llm_output}, original_llm_key)

            llm_key = f"{storage_prefix}/llm-output/{file_id}.json"
            self.s3.save_json(mapped_json, llm_key)

            record = {
                "application_number": application_number,
                "file_id": file_id,
                "doc_type": doc_type,
                "file_name": filename,
                "document_name": document_name,
                "error_message": None,
                "uploaded_at": datetime.utcnow().isoformat(),
                "s3_original": s3_original_url,
                "original_pdf_path": None,
                "selected_page_range": selected_page_range,
                "ocr_text": ocr_text,
                "schema": schema,
                "ai_raw_output": llm_output,
                "ai_parsed_output": mapped_json,
                "s3_paths": {
                    "original": original_key,
                    "ocr": ocr_json_key,
                    "original_llm": original_llm_key,
                    "parsed_llm": llm_key
                }
            }
            
            # Upload original PDF if provided
            s3_original_pdf_url = None
            if original_file_path:
                try:
                    # Use 'full' suffix to distinguish from processed file
                    original_pdf_key = f"{storage_prefix}/original-document/{file_id}_original.pdf"
                    s3_original_pdf_url = self.s3.upload_file(original_file_path, original_pdf_key)
                    record["original_pdf_path"] = s3_original_pdf_url
                    print(f"DEBUG: Uploaded original PDF to {original_pdf_key}")
                except Exception as org_err:
                    print(f"Warning: Failed to upload original PDF: {org_err}")

            self.repo.save_record(file_id, record, audit_user=audit_user)
            if application_number and self._should_mark_rerun_validation(doc_type):
                try:
                    self._set_checklist_rerun_validation(application_number, 1)
                except Exception as flag_exc:
                    print(f"Checklist rerun validation update skipped for {application_number}: {flag_exc}")
            if application_number and self._should_mark_rerun_report(doc_type):
                try:
                    ReportRepository(self.db).mark_rerun_report(application_number, 1)
                except Exception as flag_exc:
                    print(f"Report rerun flag update skipped for {application_number}: {flag_exc}")

            update_progress(file_id, 85, "Saved to database")
            update_progress(file_id, 100, "Completed")

            return {
                "application_number": application_number,
                "file_id": file_id,
                "doc_type": doc_type,
                "json": mapped_json,
                "document_url": s3_original_url,
                "original_document_url": record.get("original_pdf_path"),
                "document_name": document_name
            }
        except Exception as exc:
            self._persist_processing_error(
                record_id=file_id,
                application_number=application_number,
                doc_type=doc_type,
                file_name=filename,
                document_name=document_name,
                s3_original=s3_original_url,
                error_message=str(exc),
                audit_user=audit_user,
            )
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            if original_file_path and os.path.exists(original_file_path):
                os.remove(original_file_path)

    def _map_output_to_schema(self, data: Any, schema_fields: list, doc_type: str) -> Any:
        """
        Translates raw LLM output into a dictionary that strictly follows the schema names.
        Handles cases where Gemini might use 'llm_key' or 'name' or variations.
        """
        if not data or not isinstance(data, dict):
            return data

        # Usually the schema has a root object like {'SanctionLetterDOM': {...}}
        # If the schema fields define a root object, we map recursively.
        return self._map_item_to_schema(data, schema_fields)

    def _build_extraction_prompt(self, prompt_template: str, ocr_text: str) -> str:
        base_prompt = prompt_template.replace("{{ocr_text}}", ocr_text)
        if "document_invalid" in base_prompt and "error_message" in base_prompt:
            return base_prompt
        return f"{base_prompt.rstrip()}\n{self._INVALID_DOCUMENT_PROMPT_RULES}"

    def _extract_document_error(self, extracted_json: Any) -> Optional[str]:
        if not isinstance(extracted_json, dict):
            return None

        invalid_flag = extracted_json.get("document_invalid")
        if isinstance(invalid_flag, str):
            invalid_flag = invalid_flag.strip().lower() in {"true", "yes", "1"}

        if not invalid_flag:
            return None

        error_message = extracted_json.get("error_message") or extracted_json.get("message")
        if isinstance(error_message, (dict, list)):
            error_message = " ".join(self._collect_non_empty_strings(error_message))
        error_text = str(error_message).strip() if error_message is not None else ""
        return error_text or "Uploaded document is invalid for the requested document type."

    def _persist_processing_error(
        self,
        *,
        record_id: str,
        application_number: str,
        doc_type: Optional[str],
        file_name: Optional[str],
        document_name: Optional[str],
        s3_original: Optional[str],
        error_message: str,
        audit_user: Optional[str] = None,
    ) -> None:
        try:
            self.db.rollback()
            self.repo.save_processing_error(
                record_id=record_id,
                application_number=application_number,
                doc_type=doc_type,
                file_name=file_name,
                document_name=document_name,
                s3_original=s3_original,
                error_message=error_message,
                audit_user=audit_user,
            )
        except Exception as persist_exc:
            print(f"Failed to persist document error for {record_id}: {persist_exc}")

    def ensure_processing_record(
        self,
        *,
        record_id: str,
        application_number: str,
        doc_type: Optional[str],
        file_name: Optional[str],
        document_name: Optional[str],
        audit_user: Optional[AuditUser] = None,
    ) -> None:
        self.repo.ensure_placeholder_record(
            record_id=record_id,
            application_number=application_number,
            doc_type=doc_type,
            file_name=file_name,
            document_name=document_name,
            audit_user=audit_user,
        )

    def _map_item_to_schema(self, data: Any, fields: list) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return data
            
        mapped = {}
        matched_input_keys = set()
        for field in fields:
            name = field.get("name")
            llm_key = field.get("llm_key")
            field_type = field.get("type")
            
            # Find the best match for this field in 'data'
            val = None
            
            # 1. Direct matches
            if llm_key and llm_key in data:
                val = data[llm_key]
                matched_input_keys.add(llm_key)
            elif name in data:
                val = data[name]
                matched_input_keys.add(name)
            else:
                # 2. Heuristic match (normalized keys)
                norm_llm = llm_key.lower().replace("_", "").replace(" ", "") if llm_key else None
                norm_name = name.lower().replace("_", "").replace(" ", "")
                for k, v in data.items():
                    norm_k = k.lower().replace("_", "").replace(" ", "")
                    if norm_k == norm_llm or norm_k == norm_name:
                        val = v
                        matched_input_keys.add(k)
                        break
            
            if val is not None:
                # Recursive mapping
                if field_type == "object" and "properties" in field:
                    mapped[name] = self._map_item_to_schema(val, field["properties"])
                elif field_type == "array" and "items" in field:
                    item_schema = field["items"]
                    if isinstance(val, list):
                        if item_schema.get("type") == "object" and "properties" in item_schema:
                            mapped[name] = [self._map_item_to_schema(v, item_schema["properties"]) for v in val]
                        else:
                            mapped[name] = val
                    else:
                        # Wrap single item in list if expected array
                        if item_schema.get("type") == "object" and "properties" in item_schema:
                             mapped[name] = [self._map_item_to_schema(val, item_schema["properties"])]
                        else:
                             mapped[name] = [val]
                else:
                    mapped[name] = val
            else:
                # Initialize missing fields if they are required or just to maintain structure
                mapped[name] = [] if field_type == "array" else ({} if field_type == "object" else None)

        # Preserve any extra LLM keys that are not represented in schema fields.
        # This prevents accidental data loss for evolving prompts (e.g. sale deed schedules).
        for k, v in data.items():
            if k not in matched_input_keys and k not in mapped:
                mapped[k] = v

        return mapped

    # -----------------------------------------------------------
    # 2. GET RECORD BY ID
    # -----------------------------------------------------------
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        record = self.repo.get_record(record_id)
        if record:
            return self._transform_record(record)
        return None

    # -----------------------------------------------------------
    # 3. GET ALL RECORDS (FILTERED BY APP NO)
    # -----------------------------------------------------------
    def list_records(self, application_number: Optional[str] = None):
        records = self.repo.list_records(application_number)
        return [self._transform_record(r) for r in records]

    # -----------------------------------------------------------
    # 3.1 GET RECOMMENDATIONS
    # -----------------------------------------------------------
    def get_recommendations(self, application_number: str) -> Dict[str, Any]:
        """
        Returns recommendations for the 4 core documents.
        """
        required_docs = [
            {"document_name": "Sanction_Letter", "reason": "Mandatory for loan processing", "explanation": "Required to verify loan terms and approval."},
            {"document_name": "Loan_Agreement", "reason": "Legal requirement", "explanation": "The primary legal contract for the loan."},
            {"document_name": "Memorandum_of_Deposit_of_Title_Deeds", "reason": "Collateral security", "explanation": "Required for property-backed loans."},
            {"document_name": "Sale Deed", "reason": "Proof of ownership", "explanation": "Verify the property ownership history."}
        ]
        
        # Fast path: fetch only doc types, avoid full payload transforms.
        existing_types = {
            doc_type for doc_type in self.repo.list_doc_types(application_number) if doc_type
        }
        
        pending_docs = []
        for doc in required_docs:
            status = "completed" if doc["document_name"] in existing_types else "pending"
            pending_docs.append({
                **doc,
                "status": status
            })
            
        return {
            "application_number": application_number,
            "pending_documents": pending_docs,
            "status": "completed"
        }

    # -----------------------------------------------------------
    # 4. UPDATE RECORD
    # -----------------------------------------------------------
    def update_record(self, record_id: str, update_data: Dict[str, Any], audit_user=None):
        current = self.repo.get_record(record_id)
        if not current:
            return None

        # HANDLE FLATTENED / DOT-NOTATION UPDATES
        # If the update_data contains keys with dots (e.g. "SanctionLetterDOM.borrowerName"),
        # we assume these are updates to ai_parsed_output.
        
        # 1. Identify extraction updates
        extraction_updates = {}
        extraction_paths: Dict[str, str] = {}
        standard_updates = {}

        current_parsed = current.get("ai_parsed_output") or {}
        current_doc_type = current.get("doc_type") or update_data.get("doc_type") or update_data.get("Document Type")
        
        for k, v in update_data.items():
            if k == "ai_parsed_output":
                # If explicit ai_parsed_output is sent, we take it.
                extraction_updates[k] = v
                extraction_paths[k] = k
                continue

            if "." in k or "[" in k:
                # Frontend edit forms often send human-readable dotted labels
                # such as "Loan Agreement DOM.Borrower Name". Normalize them
                # back to canonical extraction paths before merging.
                resolved_path = self._normalize_extraction_key(k, current_parsed)
                if not resolved_path or resolved_path == k:
                    resolved_path = self._resolve_human_readable_extraction_path(
                        key=k,
                        parsed=current_parsed,
                        doc_type=current_doc_type,
                    ) or resolved_path or k
                extraction_updates[k] = v
                extraction_paths[k] = resolved_path
                continue

            resolved_path = self._resolve_human_readable_extraction_path(
                key=k,
                parsed=current_parsed,
                doc_type=current_doc_type,
            )
            if resolved_path:
                extraction_updates[k] = v
                extraction_paths[k] = resolved_path
            else:
                standard_updates[k] = v
        had_extraction_updates = bool(extraction_updates)
        had_any_updates = bool(standard_updates) or had_extraction_updates
        
        # 2. Apply Standard Updates
        current.update(standard_updates)
        
        # 3. Apply Extraction Updates (Unflatten & Merge)
        if extraction_updates:
            # Keep two variants:
            # 1) legacy payload as provided by UI (for document_extracted_data JSON)
            # 2) normalized payload (for extracted_* table upsert mapping)
            # GET remains table-first; raw JSON is used only as update merge base.
            raw_parsed = self.repo.get_raw_parsed_output(record_id)
            existing_parsed_legacy = copy.deepcopy(raw_parsed or current.get("ai_parsed_output") or {})
            existing_parsed_normalized = copy.deepcopy(current.get("ai_parsed_output") or {})
            
            # If specifically "ai_parsed_output" key is present, start with that
            if "ai_parsed_output" in extraction_updates:
                 new_parsed = extraction_updates.pop("ai_parsed_output")
                 # Check if this new_parsed is ALSO flattened (partial update wrapper)
                 if isinstance(new_parsed, dict):
                      self._deep_merge(existing_parsed_legacy, new_parsed)
                      self._deep_merge(existing_parsed_normalized, new_parsed)
            
            # Process strictly flattened keys "A.B.C"
            for key, value in extraction_updates.items():
                resolved_key = extraction_paths.get(key) or self._normalize_extraction_key(key, existing_parsed_normalized)
                self._unflatten_and_set(existing_parsed_legacy, resolved_key, value)
                self._unflatten_and_set(existing_parsed_normalized, resolved_key, value)
            
            current["ai_parsed_output"] = existing_parsed_legacy
            current["upsert_parsed_output"] = existing_parsed_normalized

            doc_type = current.get("doc_type") or update_data.get("doc_type")
            self._normalize_sales_deed_descriptions(current["ai_parsed_output"], doc_type)
            self._normalize_sales_deed_descriptions(current["upsert_parsed_output"], doc_type)

        self.repo.save_record(record_id, current, audit_user=audit_user)

        if had_any_updates and self._should_mark_rerun_validation(current.get("doc_type")) and current.get("application_number"):
            try:
                self._set_checklist_rerun_validation(current.get("application_number"), 1)
            except Exception as flag_exc:
                print(f"Checklist rerun validation update skipped for {current.get('application_number')}: {flag_exc}")
        if had_any_updates and self._should_mark_rerun_report(current.get("doc_type")) and current.get("application_number"):
            try:
                ReportRepository(self.db).mark_rerun_report(current.get("application_number"), 1)
            except Exception as flag_exc:
                print(f"Report rerun flag update skipped for {current.get('application_number')}: {flag_exc}")

        return current

    def _is_probably_english(self, text: Optional[str]) -> bool:
        if not text:
            return True
        latin = re.findall(r"[A-Za-z]", text)
        non_ascii = re.findall(r"[^\x00-\x7F]", text)
        if not latin and non_ascii:
            return False
        if non_ascii and len(non_ascii) > max(10, len(latin) // 2):
            return False
        return True

    def _normalize_doc_type(self, doc_type: str) -> str:
        if not doc_type:
            return ""
        normalized = str(doc_type).strip().lower().replace(" ", "_")
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

    def _collect_non_empty_strings(self, value: Any) -> list[str]:
        out: list[str] = []
        if isinstance(value, dict):
            for v in value.values():
                out.extend(self._collect_non_empty_strings(v))
            return out
        if isinstance(value, list):
            for v in value:
                out.extend(self._collect_non_empty_strings(v))
            return out
        if value is None:
            return out
        s = str(value).strip()
        if s:
            out.append(s)
        return out

    def _normalize_sales_deed_descriptions(self, parsed: Any, doc_type: Optional[str]) -> None:
        norm = (doc_type or "").strip().lower().replace(" ", "_")
        if norm not in {"sale_deed", "sales_deed"} or not isinstance(parsed, dict):
            return
        sales_deed = parsed.get("SalesDeed")
        if not isinstance(sales_deed, dict):
            return

        description = sales_deed.get("description")
        raw_description = sales_deed.get("raw_description")
        property_raw_text = sales_deed.get("Property_Raw_Text")
        # 1) Preserve original description value as-is for `description`.
        source_description = description or raw_description
        if not source_description and isinstance(property_raw_text, (list, dict)):
            source_description = " ".join(self._collect_non_empty_strings(property_raw_text)) or None
        if not source_description and property_raw_text is not None:
            source_description = str(property_raw_text).strip() or None
        if source_description:
            sales_deed["description"] = str(source_description).strip()

        # 2) raw_description must contain English value only.
        base_for_english = raw_description or source_description
        if not base_for_english:
            return
        english_text = str(base_for_english).strip()
        if english_text and not self._is_probably_english(english_text):
            english_text = TranslationService(self.db).translate_text(english_text, "English")
        sales_deed["raw_description"] = english_text

    def _should_mark_rerun_validation(self, doc_type: Optional[str]) -> bool:
        if not doc_type:
            return False
        normalized = doc_type.strip().lower().replace(" ", "_")
        target_doc_types = {
            "sale_deed",
            "sales_deed",
            "memorandum_of_deposit_of_title_deed",
            "memorandum_of_deposit_of_title_deeds",
            "modt",
            "sanction_letter",
            "loan_agreement",
            "loan_agrement",
            "legal_report",
        }
        return normalized in target_doc_types

    def _should_mark_rerun_validation_on_delete(self, doc_type: Optional[str]) -> bool:
        if not doc_type:
            return False
        normalized = doc_type.strip().lower().replace(" ", "_")
        # Explicitly exclude Sanction Letter for delete flow.
        target_doc_types = {
            "sale_deed",
            "sales_deed",
            "memorandum_of_deposit_of_title_deed",
            "memorandum_of_deposit_of_title_deeds",
            "modt",
            "loan_agreement",
            "loan_agrement",
            "legal_report",
        }
        return normalized in target_doc_types

    def _set_checklist_rerun_validation(self, application_number: str, flag: int, initialize_if_missing: bool = True):
        """
        Set rerun_validation flag on checklist WITHOUT creating new versions.
        New versions (snapshots) are only created when user explicitly clicks "Run Validation" from UI.
        If checklist rows do not exist yet, do not auto-create placeholder rows.
        """
        checklist_repo = ChecklistRepository(self.db)
        rows = checklist_repo.set_rerun_flag_without_versioning(application_number, flag)
        if rows or not initialize_if_missing:
            return

        return

    def _should_mark_rerun_report(self, doc_type: Optional[str]) -> bool:
        # Rerun report should be raised for any extracted document mutation.
        return bool(doc_type and str(doc_type).strip())

    def _normalize_extraction_key(self, key: str, existing_parsed: Dict[str, Any]) -> str:
        """
        Converts UI labels like:
        - "Sanction Letter DOM.Loan Account Number"
        into schema keys like:
        - "SanctionLetterDOM.loanAccountNumber"
        by fuzzy-matching each segment against existing parsed JSON keys.
        """
        parts = [p.strip() for p in key.split(".") if p.strip()]
        if not parts:
            return key

        resolved_parts = []
        cursor: Any = existing_parsed if isinstance(existing_parsed, dict) else {}

        for i, part in enumerate(parts):
            if part.isdigit():
                resolved_parts.append(f"[{part}]")
                if isinstance(cursor, list):
                    idx = int(part)
                    cursor = cursor[idx] if 0 <= idx < len(cursor) else None
                else:
                    cursor = None
                continue

            base_part, bracket_suffix = self._split_bracket_suffix(part)
            array_index_suffix = ""
            trailing_index = re.match(r"^(.*?)(\d+)$", base_part)
            if trailing_index:
                base_candidate = trailing_index.group(1).strip()
                index_value = int(trailing_index.group(2))
                matched_key = None
                if isinstance(cursor, dict) and cursor:
                    matched_key = self._match_existing_key(base_candidate, list(cursor.keys()))
                if matched_key is not None and isinstance(cursor.get(matched_key), list):
                    base_part = base_candidate
                    array_index_suffix = f"[{max(0, index_value - 1)}]"
            resolved = None
            if isinstance(cursor, dict) and cursor:
                resolved = self._match_existing_key(base_part, list(cursor.keys()))

            if resolved is None:
                # Fallback: derive a reasonable key shape
                resolved = self._to_pascal(base_part) if i == 0 else self._to_camel(base_part)

            resolved = f"{resolved}{array_index_suffix}{bracket_suffix}"
            resolved_parts.append(resolved)
            next_cursor = cursor.get(resolved.split("[", 1)[0]) if isinstance(cursor, dict) else None
            if isinstance(next_cursor, list):
                cursor = next_cursor[0] if next_cursor else None
            else:
                cursor = next_cursor

        return ".".join(resolved_parts)

    def _match_existing_key(self, raw: str, candidates: list[str]) -> Optional[str]:
        raw_norm = self._norm_token(raw)
        for c in candidates:
            if self._norm_token(c) == raw_norm:
                return c
        return None

    def _norm_token(self, token: str) -> str:
        return re.sub(r"[^a-z0-9]", "", token.lower())

    def _to_camel(self, token: str) -> str:
        words = [w for w in re.split(r"[^A-Za-z0-9]+", token) if w]
        if not words:
            return token
        return words[0].lower() + "".join(w[:1].upper() + w[1:] for w in words[1:])

    def _to_pascal(self, token: str) -> str:
        words = [w for w in re.split(r"[^A-Za-z0-9]+", token) if w]
        if not words:
            return token
        out = "".join(w[:1].upper() + w[1:] for w in words)
        # Preserve DOM suffix casing for common root keys
        if out.lower().endswith("dom"):
            out = out[:-3] + "DOM"
        return out

    def _split_bracket_suffix(self, part: str) -> tuple[str, str]:
        m = re.match(r"^([^\[]+)(\[\d+\])$", part)
        if not m:
            return part, ""
        return m.group(1), m.group(2)

    def _unflatten_and_set(self, target: Dict, key: str, value: Any):
        """
        Parses keys like:
        - "A.B.C"
        - "A.list[0].name"
        and sets values, creating dict/list containers as needed.
        """
        tokens = []
        for part in key.split("."):
            if part.isdigit():
                tokens.append(int(part))
                continue
            for name, idx in re.findall(r"([^\[\]]+)|\[(\d+)\]", part):
                if name:
                    if name.isdigit():
                        tokens.append(int(name))
                    else:
                        tokens.append(name)
                else:
                    tokens.append(int(idx))

        if not tokens:
            return

        current_level: Any = target
        for i, token in enumerate(tokens):
            is_last = i == len(tokens) - 1
            next_token = None if is_last else tokens[i + 1]

            if isinstance(token, str):
                if not isinstance(current_level, dict):
                    return
                if is_last:
                    current_level[token] = value
                    return
                want_list = isinstance(next_token, int)
                child = current_level.get(token)
                if want_list:
                    if not isinstance(child, list):
                        current_level[token] = []
                else:
                    if not isinstance(child, dict):
                        current_level[token] = {}
                current_level = current_level[token]
                continue

            if not isinstance(current_level, list):
                return
            want_list = isinstance(next_token, int)
            while len(current_level) <= token:
                current_level.append([] if want_list else {})
            if is_last:
                current_level[token] = value
                return
            child = current_level[token]
            if want_list:
                if not isinstance(child, list):
                    current_level[token] = []
            else:
                if not isinstance(child, dict):
                    current_level[token] = {}
            current_level = current_level[token]

    def _deep_merge(self, target: Dict, source: Dict):
        """
        Recursive deep merge of source into target.
        """
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                self._deep_merge(target[k], v)
            else:
                target[k] = v

    def _normalize_label(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value or "").lower())

    def _resolve_human_readable_extraction_path(
        self,
        *,
        key: str,
        parsed: Any,
        doc_type: Optional[str] = None,
    ) -> Optional[str]:
        normalized_key = self._normalize_label(key)
        if not normalized_key or not isinstance(parsed, dict):
            return None

        canonical_doc_type = self._normalize_doc_type(doc_type or "")
        modt_path_map = {
            "documenttype": "MODT_DocumentDOM.documentInfo.documentType",
            "executiondate": "MODT_DocumentDOM.documentInfo.executionDate",
            "registrationdate": "MODT_DocumentDOM.documentInfo.registrationDate",
            "documentnumber": "MODT_DocumentDOM.documentInfo.documentNumber",
            "booknumber": "MODT_DocumentDOM.documentInfo.bookNumber",
            "subregistraroffice": "MODT_DocumentDOM.documentInfo.subRegistrarOffice",
            "depositorname": "MODT_DocumentDOM.parties.depositorName",
            "depositoraddress": "MODT_DocumentDOM.parties.depositorAddress",
            "depositeename": "MODT_DocumentDOM.parties.depositeeName",
            "depositeeaddress": "MODT_DocumentDOM.parties.depositeeAddress",
            "loanamount": "MODT_DocumentDOM.loanDetails.loanAmount",
            "loanamountinwords": "MODT_DocumentDOM.loanDetails.loanAmountInWords",
            "loantenure": "MODT_DocumentDOM.loanDetails.loanTenure",
            "stampduty": "MODT_DocumentDOM.stampAndFees.stampDuty",
            "registrationfee": "MODT_DocumentDOM.stampAndFees.registrationFee",
            "totalcharges": "MODT_DocumentDOM.stampAndFees.totalCharges",
        }

        legal_report_path_map = {
            "reporttitle": "LegalReport.Document_Information.Report_Title",
            "lawfirmname": "LegalReport.Document_Information.Law_Firm_Name",
            "advocatename": "LegalReport.Document_Information.Advocate_Name",
            "documentcategory": "LegalReport.Document_Information.Document_Category",
            "documentsubcategory": "LegalReport.Document_Information.Document_Sub_Category",
            "referencenumber": "LegalReport.Document_Information.Reference_Number",
            "reportdate": "LegalReport.Document_Information.Report_Date",
            "proposalnumber": "LegalReport.Document_Information.Proposal_Number",
            "state": "LegalReport.Document_Information.State",
            "issuingofficeaddress": "LegalReport.Document_Information.Issuing_Office_Address",
            "remarks": "LegalReport.Document_Information.Remarks",
            "bankornbfcname": "LegalReport.Lender_Details.Bank_Or_NBFC_Name",
            "branchname": "LegalReport.Lender_Details.Branch_Name",
            "addressedto": "LegalReport.Lender_Details.Addressed_To",
            "primaryborrowername": "LegalReport.Borrower_Details.Primary_Borrower_Name",
            "borrowerfullnameandaddress": "LegalReport.Borrower_Details.Borrower_Full_Name_And_Address",
            "constitutionofowner": "LegalReport.Borrower_Details.Constitution_Of_Owner",
            "ownername": "LegalReport.Property_Owner_Details.Owner_Name",
            "owneraddress": "LegalReport.Property_Owner_Details.Owner_Address",
            "ownerconstitution": "LegalReport.Property_Owner_Details.Owner_Constitution",
            "loanaccountnumber": "LegalReport.Loan_Details.Loan_Account_Number",
            "loantype": "LegalReport.Loan_Details.Loan_Type",
            "producttype": "LegalReport.Loan_Details.Product_Type",
            "propertyaddress": "LegalReport.Property_Details.Property_Address",
            "propertytype": "LegalReport.Property_Details.Property_Type",
            "villageortown": "LegalReport.Property_Details.Village_Or_Town",
            "talukorcircle": "LegalReport.Property_Details.Taluk_Or_Circle",
            "district": "LegalReport.Property_Details.District",
            "registrationdistrict": "LegalReport.Property_Details.Registration_District",
            "subregistrationdistrict": "LegalReport.Property_Details.Sub_Registration_District",
            "surveynumber": "LegalReport.Property_Details.Survey_Number",
            "resurveynumber": "LegalReport.Property_Details.Re_Survey_Number",
            "plotorsitenumber": "LegalReport.Property_Details.Plot_Or_Site_Number",
            "blocknumber": "LegalReport.Property_Details.Block_Number",
            "layoutname": "LegalReport.Property_Details.Layout_Name",
            "totalextenthectares": "LegalReport.Property_Details.Total_Extent_Hectares",
            "totalextentacres": "LegalReport.Property_Details.Total_Extent_Acres",
            "totalextentsqft": "LegalReport.Property_Details.Total_Extent_Sqft",
            "totalextentsqmeter": "LegalReport.Property_Details.Total_Extent_SqMeter",
            "landusetype": "LegalReport.Property_Details.Land_Use_Type",
            "originaltitleholder": "LegalReport.Title_Tracing.Original_Title_Holder",
            "chainoftitlesummary": "LegalReport.Title_Tracing.Chain_Of_Title_Summary",
            "currenttitleholder": "LegalReport.Title_Tracing.Current_Title_Holder",
            "modeofacquisition": "LegalReport.Title_Tracing.Mode_Of_Acquisition",
            "titletracingperiodfrom": "LegalReport.Title_Tracing.Title_Tracing_Period_From",
            "titletracingperiodto": "LegalReport.Title_Tracing.Title_Tracing_Period_To",
            "encumbrancecertificatenumber": "LegalReport.Encumbrance_Details.Encumbrance_Certificate_Number",
            "ecperiodfrom": "LegalReport.Encumbrance_Details.EC_Period_From",
            "ecperiodto": "LegalReport.Encumbrance_Details.EC_Period_To",
            "chargesregistered": "LegalReport.Encumbrance_Details.Charges_Registered",
            "existingmortgageorencumbrance": "LegalReport.Encumbrance_Details.Existing_Mortgage_Or_Encumbrance",
            "modtdetails": "LegalReport.Encumbrance_Details.MODT_Details",
            "istitleclearandmarketable": "LegalReport.Legal_Verification_Checklist.Is_Title_Clear_And_Marketable",
            "ispropertyfreeofencumbrance": "LegalReport.Legal_Verification_Checklist.Is_Property_Free_Of_Encumbrance",
            "isoriginaltitledocumentinorder": "LegalReport.Legal_Verification_Checklist.Is_Original_Title_Document_In_Order",
            "ispropertywithinmunicipallimits": "LegalReport.Legal_Verification_Checklist.Is_Property_Within_Municipal_Limits",
            "ispropertyagriculturalornonagricultural": "LegalReport.Legal_Verification_Checklist.Is_Property_Agricultural_Or_NonAgricultural",
            "ispropertyleasehold": "LegalReport.Legal_Verification_Checklist.Is_Property_Leasehold",
            "lispendensstatus": "LegalReport.Legal_Verification_Checklist.Lis_Pendens_Status",
            "minorsinterest": "LegalReport.Legal_Verification_Checklist.Minors_Interest",
            "powerofattorneystatus": "LegalReport.Legal_Verification_Checklist.Power_Of_Attorney_Status",
            "nocfromsocietyorbuilder": "LegalReport.Legal_Verification_Checklist.NOC_From_Society_Or_Builder",
            "sarfaesiapplicability": "LegalReport.Legal_Verification_Checklist.SARFAESI_Applicability",
            "urbanlandceilingactapplicable": "LegalReport.Legal_Verification_Checklist.Urban_Land_Ceiling_Act_Applicable",
            "tenancylawsapplicable": "LegalReport.Legal_Verification_Checklist.Tenancy_Laws_Applicable",
            "siteinspectiondone": "LegalReport.Legal_Verification_Checklist.Site_Inspection_Done",
            "additionaldocumentrequired": "LegalReport.Legal_Verification_Checklist.Additional_Document_Required",
            "municipaltaxpaidstatus": "LegalReport.Legal_Verification_Checklist.Municipal_Tax_Paid_Status",
            "municipaltaxassessedinnameof": "LegalReport.Legal_Verification_Checklist.Municipal_Tax_Assessed_In_Name_Of",
            "constructionaspersanctionplan": "LegalReport.Legal_Verification_Checklist.Construction_As_Per_Sanction_Plan",
            "pattanumber": "LegalReport.Tax_And_Revenue_Details.Patta_Number",
            "propertytaxreceiptnumber": "LegalReport.Tax_And_Revenue_Details.Property_Tax_Receipt_Number",
            "assessmentnumber": "LegalReport.Tax_And_Revenue_Details.Assessment_Number",
            "taxassessedinnameof": "LegalReport.Tax_And_Revenue_Details.Tax_Assessed_In_Name_Of",
            "taxreceiptdate": "LegalReport.Tax_And_Revenue_Details.Tax_Receipt_Date",
            "titlecertificationopinion": "LegalReport.Title_Certification.Title_Certification_Opinion",
            "safeguardstobeobserved": "LegalReport.Title_Certification.Safeguards_To_Be_Observed",
            "observationremarks": "LegalReport.Title_Certification.Observation_Remarks",
            "certifyingadvocatename": "LegalReport.Title_Certification.Certifying_Advocate_Name",
            "certificationdate": "LegalReport.Title_Certification.Certification_Date",
            "certificationplace": "LegalReport.Title_Certification.Certification_Place",
        }

        sanction_letter_path_map = {
            "loanaccountnumber": "SanctionLetterDOM.loanAccountNumber",
            "borrowername": "SanctionLetterDOM.borrowerName",
            "borroweraddress": "SanctionLetterDOM.borrowerAddress",
            "borrowerpan": "SanctionLetterDOM.borrowerPan",
            "sanctiondate": "SanctionLetterDOM.sanctionDate",
            "sanctionamount": "SanctionLetterDOM.sanctionAmount",
            "loanamount": "SanctionLetterDOM.loanAmount",
            "loantenure": "SanctionLetterDOM.loanTenure",
            "interestrate": "SanctionLetterDOM.interestRate",
            "emiamount": "SanctionLetterDOM.emiAmount",
            "repaymentfrequency": "SanctionLetterDOM.repaymentFrequency",
            "propertydescription": "SanctionLetterDOM.scheduleProperty.description",
            "descriptionofproperty": "SanctionLetterDOM.scheduleProperty.description",
            "schedulepropertydescription": "SanctionLetterDOM.scheduleProperty.description",
            "propertyaddress": "SanctionLetterDOM.scheduleProperty.propertyAddress",
            "addressofproperty": "SanctionLetterDOM.scheduleProperty.propertyAddress",
            "surveynumber": "SanctionLetterDOM.scheduleProperty.surveyNumber",
            "plotnumber": "SanctionLetterDOM.scheduleProperty.plotNumber",
            "north": "SanctionLetterDOM.scheduleProperty.boundaries.north",
            "south": "SanctionLetterDOM.scheduleProperty.boundaries.south",
            "east": "SanctionLetterDOM.scheduleProperty.boundaries.east",
            "west": "SanctionLetterDOM.scheduleProperty.boundaries.west",
        }

        loan_agreement_path_map = {
            "loanagreementdate": "LoanAgreementDOM.loanAgreementDate",
            "sanctiondate": "LoanAgreementDOM.sanctionDate",
            "loanamount": "LoanAgreementDOM.loanAmount",
            "loanamountinwords": "LoanAgreementDOM.loanAmountInWords",
            "borrowername": "LoanAgreementDOM.borrowerName",
            "borroweraddress": "LoanAgreementDOM.borrowerAddress",
            "borrowerpan": "LoanAgreementDOM.borrowerPan",
            "propertydescription": "LoanAgreementDOM.scheduleProperty.description",
            "descriptionofproperty": "LoanAgreementDOM.scheduleProperty.description",
            "schedulepropertydescription": "LoanAgreementDOM.scheduleProperty.description",
            "propertyaddress": "LoanAgreementDOM.scheduleProperty.propertyAddress",
            "addressofproperty": "LoanAgreementDOM.scheduleProperty.propertyAddress",
            "surveynumber": "LoanAgreementDOM.scheduleProperty.surveyNumber",
            "plotnumber": "LoanAgreementDOM.scheduleProperty.plotNumber",
            "north": "LoanAgreementDOM.scheduleProperty.boundaries.north",
            "south": "LoanAgreementDOM.scheduleProperty.boundaries.south",
            "east": "LoanAgreementDOM.scheduleProperty.boundaries.east",
            "west": "LoanAgreementDOM.scheduleProperty.boundaries.west",
        }

        if canonical_doc_type in {
            "memorandum_of_deposit_of_title_deeds",
            "memorandum_of_deposit_of_title_deed",
            "modt",
        } and normalized_key in modt_path_map:
            return modt_path_map[normalized_key]

        if canonical_doc_type == "legal_report" and normalized_key in legal_report_path_map:
            return legal_report_path_map[normalized_key]

        if canonical_doc_type == "sanction_letter" and normalized_key in sanction_letter_path_map:
            return sanction_letter_path_map[normalized_key]

        if canonical_doc_type == "loan_agreement" and normalized_key in loan_agreement_path_map:
            return loan_agreement_path_map[normalized_key]

        found = self._find_label_path(parsed, normalized_key)
        return found

    def _find_label_path(self, node: Any, normalized_label: str, prefix: str = "") -> Optional[str]:
        if isinstance(node, dict):
            for key, value in node.items():
                current_path = f"{prefix}.{key}" if prefix else key
                if self._normalize_label(key) == normalized_label and not isinstance(value, (dict, list)):
                    return current_path
                found = self._find_label_path(value, normalized_label, current_path)
                if found:
                    return found
        elif isinstance(node, list):
            for index, item in enumerate(node):
                current_path = f"{prefix}[{index}]"
                found = self._find_label_path(item, normalized_label, current_path)
                if found:
                    return found
        return None

    # -----------------------------------------------------------
    # 5. DELETE RECORD
    # -----------------------------------------------------------
    def delete_record(self, record_id: str, audit_user=None) -> bool:
        current = self.repo.get_record(record_id)
        if not current:
            delete_progress(record_id)
            return True

        application_number = current.get("application_number")
        doc_type = current.get("doc_type")

        deleted = self.repo.delete_record(record_id, audit_user=audit_user)
        if not deleted:
            return False

        delete_progress(record_id)

        if application_number and self._should_mark_rerun_validation_on_delete(doc_type):
            try:
                self._set_checklist_rerun_validation(application_number, 1, initialize_if_missing=False)
            except Exception as flag_exc:
                print(f"Checklist rerun validation update skipped for {application_number}: {flag_exc}")
        if application_number and self._should_mark_rerun_report(doc_type):
            try:
                ReportRepository(self.db).mark_rerun_report(application_number, 1)
            except Exception as flag_exc:
                print(f"Report rerun flag update skipped for {application_number}: {flag_exc}")

        return True

    # -----------------------------------------------------------
    # HELPER: SAFE JSON PARSER
    # -----------------------------------------------------------
    def _safe_json_parse(self, text: str):
        if not text:
            return None
        
        # 1. Strip Markdown Code Blocks (```json ... ```)
        import re
        text = text.strip()
        # Remove opening ```json (or just ```)
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        # Remove closing ```
        if text.endswith("```"):
            text = re.sub(r"\n?```$", "", text)
        text = text.strip()

        # 2. Try Raw Parse
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"DEBUG: Initial JSON parse failed: {str(e)}")

        # 3. Stepwise Cleaning
        # A. Remove trailing commas before closing braces/brackets
        # This fixes errors like {"key": "value", }
        text = re.sub(r',\s*([\]\}])', r'\1', text)
        
        # B. Regex Extraction (Find outermost {} or [])
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        extracted = match.group(0) if match else text
        
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass

        # 4. Local Repair: Balance Braces/Quotes (Simple attempt for truncation)
        def balance_json(s):
            stack = []
            in_string = False
            escape = False
            for char in s:
                if in_string:
                    if char == '"' and not escape:
                        in_string = False
                    elif char == '\\':
                        escape = not escape
                    else:
                        escape = False
                else:
                    if char == '"':
                        in_string = True
                    elif char in '{[':
                        stack.append('}' if char == '{' else ']')
                    elif char in '}]':
                        if stack and stack[-1] == char:
                            stack.pop()
            
            # If still in string, close it
            if in_string:
                s += '"'
            
            # Close remaining braces
            while stack:
                s += stack.pop()
            return s

        try:
            balanced = balance_json(extracted)
            # Apply trailing comma fix again after balancing just in case
            balanced = re.sub(r',\s*([\]\}])', r'\1', balanced)
            return json.loads(balanced)
        except json.JSONDecodeError:
            # 5. LLM Repair (Last Resort)
            print(f"DEBUG: Local repair failed. Attempting LLM repair on len={len(extracted)}")
            try:
                repaired = repair_json_with_llm(extracted)
                return json.loads(repaired)
            except Exception as e3:
                print(f"DEBUG: LLM repair failed: {str(e3)}")
                return None

    # -----------------------------------------------------------
    # HELPER: TRANSFORM S3 URLs TO HTTPS
    # -----------------------------------------------------------
    # -----------------------------------------------------------
    # HELPER: TRANSFORM S3 URLs TO HTTPS (PRE-SIGNED)
    # -----------------------------------------------------------
    def _transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Converts s3:// URLs to temporary pre-signed HTTPS URLs for the frontend."""
        if not record:
            return record

        s3_url = record.get("s3_original")
        if s3_url:
            # resolve_any_reference_url figures out which backend a stored
            # reference (gs:// / s3:// URI, https URL, local /files URL, or
            # a bare key) actually belongs to and presigns it from there -
            # so documents uploaded under a previous STORAGE_PROVIDER stay
            # viewable after switching, as long as that backend is still
            # configured.
            try:
                url = resolve_any_reference_url(s3_url)
                if url:
                    record["document_url"] = url
                # We typically keep s3_original as the source of truth
            except Exception as e:
                print(f"Error generating pre-signed URL for {s3_url}: {e}")

        # Generate Pre-signed URL for original PDF (complete uploaded file)
        original_pdf_url = record.get("original_pdf_path")
        if original_pdf_url:
            try:
                url = resolve_any_reference_url(original_pdf_url)
                if url:
                    record["original_document_url"] = url
            except Exception as e:
                print(f"Error generating pre-signed URL for original PDF: {e}")
        elif record.get("document_url"):
            # No separate original PDF stored — reuse the extraction document URL
            # so the "Original Doc" tab shows the uploaded file instead of being blank.
            record["original_document_url"] = record["document_url"]

        return record

