import json
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.db.repositories.translation_repo import TranslationRepository
from app.db.repositories.extractor_repo import ExtractorRepository
from app.db.versioning import live_filter
from app.utils.gemini import call_gemini_ai, repair_json_with_llm

class TranslationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TranslationRepository(db)
        self.extractor_repo = ExtractorRepository(db)

    @staticmethod
    def _normalize_doc_type(doc_type: str) -> str:
        if not doc_type:
            return ""
        normalized = doc_type.strip().lower().replace(" ", "_")
        if normalized == "sales_deed":
            return "sale_deed"
        if normalized in {
            "memorandum_of_deposit_of_title_deed",
            "memorandum_of_deposit_of_title_deeds",
            "modt",
        }:
            return "memorandum_of_deposit_of_title_deeds"
        return normalized

    async def translate_document_extraction(self, record_id: str, target_language: str) -> Dict[str, Any]:
        """
        Translates the extracted JSON data of a document to the target language.
        Prioritizes database cache for speed and cost efficiency.
        """
        # 1. Get the extraction record
        record = self.extractor_repo.get_record(record_id)
        if not record:
            raise ValueError(f"Extraction record {record_id} not found.")

        # 2. Get document object for DB relations
        from app.db.models.document_extraction import Document
        doc_obj = self.db.query(Document).filter(
            Document.file_id == record_id, *live_filter(Document)
        ).first()
        if not doc_obj:
            raise ValueError(f"Document object for file_id {record_id} not found in DB.")

        doc_type = self._normalize_doc_type(record.get("doc_type") or "")
        raw_parsed = self.extractor_repo.get_raw_parsed_output(record_id)
        original_data = self._build_translation_source_payload(
            doc_type=doc_type,
            projected_data=record.get("ai_parsed_output"),
            raw_parsed_data=raw_parsed,
        )
        if not original_data:
            raise ValueError("No extracted data found to translate.")

        # 3. FAST PATH: Check if translation already exists in DB.
        existing = self.repo.get_translation(doc_obj.id, target_language)
        if existing and existing.original_content == original_data:
            print(f"DEBUG: Cache hit for translation ({target_language}) for {record_id}")
            return existing.translated_content

        # 4. Perform translation via Gemini
        translated_data = await self._perform_llm_translation(original_data, target_language)

        # 5. Save to cache
        self.repo.save_translation(
            document_id=doc_obj.id,
            language=target_language,
            original_content=original_data,
            translated_content=translated_data
        )

        return translated_data

    def get_cached_translation(self, record_id: str, target_language: str) -> Optional[Dict[str, Any]]:
        record = self.extractor_repo.get_record(record_id)
        if not record:
            raise ValueError(f"Extraction record {record_id} not found.")

        from app.db.models.document_extraction import Document

        doc_obj = self.db.query(Document).filter(
            Document.file_id == record_id, *live_filter(Document)
        ).first()
        if not doc_obj:
            raise ValueError(f"Document object for file_id {record_id} not found in DB.")

        existing = self.repo.get_translation(doc_obj.id, target_language)
        if not existing:
            return None

        doc_type = self._normalize_doc_type(record.get("doc_type") or "")
        raw_parsed = self.extractor_repo.get_raw_parsed_output(record_id)
        current_source = self._build_translation_source_payload(
            doc_type=doc_type,
            projected_data=record.get("ai_parsed_output"),
            raw_parsed_data=raw_parsed,
        )
        if existing.original_content == current_source:
            return existing.translated_content
        return None

    def translate_text(self, text: str, target_language: str = "English") -> str:
        """
        Translate plain text using the existing translation agent/service pathway.
        Returns original text if translation fails.
        """
        if not text or not str(text).strip():
            return text
        prompt = (
            f"Translate the following text to {target_language}. Return only translated text. "
            "Do not summarize, shorten, or paraphrase. Preserve all names, numbers, survey numbers, "
            "measurements, boundary directions, and legal/property terminology exactly in meaning.\n\n"
            f"{text}"
        )
        try:
            translated = call_gemini_ai(prompt)
            cleaned = str(translated).strip() if translated else ""
            # If model returns JSON-wrapped payload, extract translated string only.
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, str):
                    cleaned = parsed
                elif isinstance(parsed, dict):
                    for key in ("translated_text", "translation", "text", "value"):
                        val = parsed.get(key)
                        if isinstance(val, str) and val.strip():
                            cleaned = val
                            break
                    else:
                        cleaned = ""
                elif isinstance(parsed, list):
                    vals = [v for v in parsed if isinstance(v, str) and v.strip()]
                    cleaned = vals[0] if vals else ""
            except Exception:
                pass
            cleaned = cleaned.strip().strip('"')
            return cleaned or text
        except Exception:
            return text

    def _stringify_if_present(self, value: Any) -> Optional[str]:
        if value in (None, "", [], {}):
            return None
        if isinstance(value, (dict, list)):
            parts = self._collect_non_empty_strings(value)
            return " ".join(parts).strip() or None
        text = str(value).strip()
        return text or None

    def _collect_non_empty_strings(self, value: Any) -> list[str]:
        out: list[str] = []
        if isinstance(value, dict):
            for item in value.values():
                out.extend(self._collect_non_empty_strings(item))
            return out
        if isinstance(value, list):
            for item in value:
                out.extend(self._collect_non_empty_strings(item))
            return out
        if value is None:
            return out
        text = str(value).strip()
        if text:
            out.append(text)
        return out

    def _build_translation_source_payload(
        self,
        *,
        doc_type: str,
        projected_data: Optional[Dict[str, Any]],
        raw_parsed_data: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        # Default behavior for all non-Sale Deed docs: translate the full payload.
        if doc_type != "sale_deed":
            return projected_data

        # Sale Deed special handling: translate only raw data fields.
        source = raw_parsed_data if isinstance(raw_parsed_data, dict) else projected_data
        if not isinstance(source, dict):
            return None

        sales_deed = source.get("SalesDeed") if isinstance(source.get("SalesDeed"), dict) else {}
        projected_sales_deed = {}
        if isinstance(projected_data, dict):
            psd = projected_data.get("SalesDeed")
            if isinstance(psd, dict):
                projected_sales_deed = psd

        property_raw_text = self._stringify_if_present(
            sales_deed.get("Property_Raw_Text")
            if sales_deed.get("Property_Raw_Text") is not None
            else projected_sales_deed.get("Property_Raw_Text")
        )
        original_description = (
            self._stringify_if_present(sales_deed.get("description"))
            or self._stringify_if_present(projected_sales_deed.get("description"))
        )
        english_description = (
            self._stringify_if_present(sales_deed.get("raw_description"))
            or self._stringify_if_present(projected_sales_deed.get("raw_description"))
        )

        # Translate from the verbatim extracted description first.
        raw_description = original_description or english_description or property_raw_text

        out_sales_deed: Dict[str, Any] = {}
        if property_raw_text:
            out_sales_deed["Property_Raw_Text"] = property_raw_text
        if raw_description:
            out_sales_deed["raw_description"] = raw_description

        return {"SalesDeed": out_sales_deed} if out_sales_deed else None

    async def _perform_llm_translation(self, data: Dict, target_language: str) -> Dict:
        """
        Calls Gemini to translate JSON values while keeping keys intact.
        Uses a high-performance batching strategy to minimize LLM calls.
        """
        # Threshold for attempting a single-pass translation
        # Gemini-2.0-flash can handle large outputs, but 8k tokens is the safe limit.
        data_str = json.dumps(data)
        if len(data_str) < 15000: # ~4000-5000 tokens
            prompt = f"""
            TASK: Translate ALL string values in this JSON to {target_language}.
            Maintain structure and keys exactly. Return ONLY valid JSON.
            
            JSON:
            {data_str}
            """
            response = call_gemini_ai(prompt)
            try:
                clean_resp = self._clean_json(response)
                return json.loads(clean_resp)
            except Exception as e:
                print(f"DEBUG: Single-pass translation failed, falling back to batching: {e}")

        # --- BATCHING STRATEGY (High Efficiency) ---
        # 1. Flatten all string values into a list of (path, value) pairs
        strings_to_translate = []
        
        def collect_strings(node, path=""):
            if isinstance(node, str):
                if node.strip() and not node.isdigit(): # skip empty or pure numbers
                    strings_to_translate.append((path, node))
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    collect_strings(v, f"{path}[{i}]")
            elif isinstance(node, dict):
                for k, v in node.items():
                    collect_strings(v, f"{path}.{k}" if path else k)

        collect_strings(data)
        
        if not strings_to_translate:
            return data

        # 2. Translate strings in large batches (e.g. 30 per call)
        translated_map = {}
        batch_size = 30
        for i in range(0, len(strings_to_translate), batch_size):
            batch = strings_to_translate[i : i + batch_size]
            batch_values = [v for p, v in batch]
            
            prompt = f"""
            Translate this list of strings to {target_language}.
            Return a JSON array of the same length and in the same order. ONLY the array.
            Do not summarize, shorten, or omit details.
            Preserve the exact meaning of names, numbers, document references, survey numbers,
            measurements, boundary directions, and legal/property terminology.
            STRINGS: {json.dumps(batch_values, ensure_ascii=False)}
            """
            response = call_gemini_ai(prompt)
            try:
                clean_resp = self._clean_json(response)
                translated_batch = json.loads(clean_resp)
                if isinstance(translated_batch, list) and len(translated_batch) == len(batch):
                    for j, (path, orig) in enumerate(batch):
                        translated_map[path] = translated_batch[j]
                else:
                    raise ValueError("Batch size mismatch")
            except Exception as e:
                print(f"ERROR: Batch {i} failed: {e}. Retrying individually for this batch.")
                for path, orig in batch:
                    # Individual fallback for failed batch items
                    p_single = (
                        f"Translate the following text to {target_language}. Return only translated text. "
                        "Do not summarize, shorten, or paraphrase. Preserve all names, numbers, survey "
                        f"numbers, measurements, boundary directions, and legal/property meaning exactly.\n\n{orig}"
                    )
                    translated_map[path] = call_gemini_ai(p_single).strip().strip('"')

        # 3. Reconstruct the JSON with translated values
        import copy
        result = copy.deepcopy(data)
        
        def apply_translations(node, path=""):
            if isinstance(node, str):
                return translated_map.get(path, node)
            elif isinstance(node, list):
                return [apply_translations(v, f"{path}[{i}]") for i, v in enumerate(node)]
            elif isinstance(node, dict):
                return {k: apply_translations(v, f"{path}.{k}" if path else k) for k, v in node.items()}
            return node

        return apply_translations(result)

    def _clean_json(self, text: str) -> str:
        import re
        clean = text.strip()
        # Remove markdown markers
        if clean.startswith("```"):
            clean = re.sub(r"^```[a-zA-Z]*\n?", "", clean)
        if clean.endswith("```"):
            clean = re.sub(r"\n?```$", "", clean)
        # Sometimes LLM adds text before/after JSON
        if "{" in clean and "}" in clean:
            start = clean.find("{")
            end = clean.rfind("}") + 1
            clean = clean[start:end]
        elif "[" in clean and "]" in clean:
            start = clean.find("[")
            end = clean.rfind("]") + 1
            clean = clean[start:end]
        return clean.strip()

    def update_translation(self, record_id: str, language: str, translated_content: Dict) -> Dict:
        """
        Updates an existing translation or creates a new one if not exists (manual override).
        """
        # 1. Get document object
        from app.db.models.document_extraction import Document
        doc_obj = self.db.query(Document).filter(
            Document.file_id == record_id, *live_filter(Document)
        ).first()
        if not doc_obj:
            raise ValueError(f"Document object for file_id {record_id} not found in DB.")

        # 2. Get original data (optional, but good for completeness)
        record = self.extractor_repo.get_record(record_id)
        original_data = record.get("ai_parsed_output") if record else {}

        # 3. Save/Upsert
        self.repo.save_translation(
            document_id=doc_obj.id,
            language=language,
            original_content=original_data,
            translated_content=translated_content
        )
        
        return translated_content
