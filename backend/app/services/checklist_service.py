from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.repositories.checklist_repo import ChecklistRepository
from app.api.v1.schemas.checklist_schema import (
    ApplicationChecklistCreate,
    ApplicationChecklistUpdate,
    ApplicationChecklistBulkUpdateItem,
)
from app.db.models.extracted_data import (
    ExtractedSanctionLetter, 
    ExtractedLoanAgreement, 
    ExtractedMODT, 
    ExtractedMODTProperty,
    ExtractedSalesDeed,
    ExtractedSalesDeedSchedule,
    ApplicationChecklist,
)
from app.db.models.document_extraction import Document
from typing import Optional
from app.db.repositories.checklist_repo import ChecklistRepository, MasterChecklistRepository
from app.db.repositories.report_repo import ReportRepository
from app.db.repositories.observation_repo import ObservationRepository
from app.db.versioning import live_filter
from app.utils.gemini import call_gemini_ai
import json
import re

class ChecklistService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ChecklistRepository(db)

    def create_checklist(self, obj_in: ApplicationChecklistCreate, audit_user=None):
        payload = obj_in.model_dump()
        return self.repo.create(audit_user=audit_user, **payload)

    def get_checklist(self, application_number: str):
        return self.repo.get_by_application(application_number)

    def _get_latest_live_row(self, model, application_number: str):
        query = self.db.query(model)
        if hasattr(model, "document_id"):
            query = query.join(Document, Document.id == model.document_id).filter(*live_filter(Document))
        return query.filter(
            model.application_number == application_number,
            *live_filter(model),
        ).order_by(model.created_at.desc(), model.id.desc()).first()

    def _get_live_modt_properties(self, modt_id: int) -> list[ExtractedMODTProperty]:
        return (
            self.db.query(ExtractedMODTProperty)
            .filter(ExtractedMODTProperty.modt_id == modt_id, *live_filter(ExtractedMODTProperty))
            .order_by(ExtractedMODTProperty.property_index.asc(), ExtractedMODTProperty.id.asc())
            .all()
        )

    def _extract_sales_deed_plot_number(self, sales_deed_id: int) -> Optional[str]:
        row = (
            self.db.query(ExtractedSalesDeedSchedule)
            .filter(ExtractedSalesDeedSchedule.sales_deed_id == sales_deed_id, *live_filter(ExtractedSalesDeedSchedule))
            .order_by(ExtractedSalesDeedSchedule.id.asc())
            .first()
        )
        if not row or row.plot_number is None:
            return None
        return str(row.plot_number).strip() or None

    def _sales_deed_sort_key(self, sales_deed: ExtractedSalesDeed):
        plot_number = self._extract_sales_deed_plot_number(sales_deed.id)
        if plot_number and plot_number.isdigit():
            return (0, int(plot_number), plot_number, sales_deed.created_at, sales_deed.id)
        if plot_number:
            return (0, float("inf"), plot_number, sales_deed.created_at, sales_deed.id)
        return (1, float("inf"), "", sales_deed.created_at, sales_deed.id)

    def _get_sales_deed_rows_for_checklist(self, application_number: str) -> list[ExtractedSalesDeed]:
        rows = (
            self.db.query(ExtractedSalesDeed)
            .join(Document, Document.id == ExtractedSalesDeed.document_id)
            .filter(
                ExtractedSalesDeed.application_number == application_number,
                *live_filter(ExtractedSalesDeed),
                *live_filter(Document),
            )
            .order_by(ExtractedSalesDeed.created_at.desc(), ExtractedSalesDeed.id.desc())
            .all()
        )
        unique_rows: list[ExtractedSalesDeed] = []
        seen_keys: set[str] = set()
        for row in rows:
            plot_number = self._extract_sales_deed_plot_number(row.id)
            raw_description = (row.raw_description or "").strip().lower()
            dedupe_key = f"plot:{plot_number}" if plot_number else (f"desc:{raw_description}" if raw_description else f"id:{row.id}")
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            unique_rows.append(row)
        return sorted(unique_rows, key=self._sales_deed_sort_key)

    def _build_checklist_rows(self, application_number: str, audit_user=None, initial_version: int = 1):
        master_repo = MasterChecklistRepository(self.db)
        master_fields = master_repo.get_all()
        if not master_fields:
            master_repo.seed_default_fields()
            master_fields = master_repo.get_all()

        sanction = self._get_latest_live_row(ExtractedSanctionLetter, application_number)
        loan_agr = self._get_latest_live_row(ExtractedLoanAgreement, application_number)
        modt = self._get_latest_live_row(ExtractedMODT, application_number)
        modt_property_rows = self._get_live_modt_properties(modt.id) if modt else []
        sales_deed_rows = self._get_sales_deed_rows_for_checklist(application_number)

        co_borrower_master_fields = []
        for mf in master_fields:
            if mf.attribute_code in ["co_borrower_name", "co_borrower_address"]:
                co_borrower_master_fields.append(mf)
                continue

            if mf.pair_code == "MODT_SD" and mf.attribute_code == "property_description":
                row_count = max(len(modt_property_rows), len(sales_deed_rows), 1)
                for i in range(1, row_count + 1):
                    self.repo.create(
                        application_number=application_number,
                        pair_code=mf.pair_code,
                        document_a=mf.document_a,
                        document_b=mf.document_b,
                        attribute_code=(mf.attribute_code if row_count == 1 else f"property_description_{i}"),
                        attribute_label=(mf.attribute_label if row_count == 1 else f"{mf.attribute_label} {i}"),
                        match_status='NOT_AVAILABLE',
                        audit_user=audit_user,
                        initial_version=initial_version,
                    )
                continue

            self.repo.create(
                application_number=application_number,
                pair_code=mf.pair_code,
                document_a=mf.document_a,
                document_b=mf.document_b,
                attribute_code=mf.attribute_code,
                attribute_label=mf.attribute_label,
                match_status='NOT_AVAILABLE',
                audit_user=audit_user,
                initial_version=initial_version,
            )

        # Insert co-borrower fields grouped by co-borrower number: Name 1, Address 1, Name 2, Address 2, ...
        # Sort explicitly so output is stable even if DB returns fields in a different order.
        co_borrower_field_order = {"co_borrower_name": 0, "co_borrower_address": 1}
        co_borrower_master_fields.sort(
            key=lambda f: co_borrower_field_order.get(f.attribute_code, 99)
        )
        for i in range(1, 6):
            has_co_b = (
                (sanction and getattr(sanction, f"co_borrower_{i}_name", None)) or
                (loan_agr and getattr(loan_agr, f"co_borrower_{i}_name", None))
            )
            if not has_co_b:
                continue
            for mf in co_borrower_master_fields:
                attr_suffix = mf.attribute_code.replace("co_borrower_", "")
                new_attr_code = f"co_borrower_{i}_{attr_suffix}"
                self.repo.create(
                    application_number=application_number,
                    pair_code=mf.pair_code,
                    document_a=mf.document_a,
                    document_b=mf.document_b,
                    attribute_code=new_attr_code,
                    attribute_label=f"{mf.attribute_label} {i}",
                    match_status='NOT_AVAILABLE',
                    audit_user=audit_user,
                    initial_version=initial_version,
                )

        self.repo.set_rerun_flag_without_versioning(application_number, 0, audit_user=audit_user)
        return self.repo.get_by_application(application_number)

    def trigger_matching(self, application_number: str, audit_user=None):

        checklist_rows = self.get_checklist(application_number)
        if not checklist_rows:
            return None

        mismatches = []

        # ---------------------------------------------------
        # Fetch extracted docs
        # ---------------------------------------------------
        sanction = self._get_latest_live_row(ExtractedSanctionLetter, application_number)
        loan_agr = self._get_latest_live_row(ExtractedLoanAgreement, application_number)
        modt = self._get_latest_live_row(ExtractedMODT, application_number)
        sales_deed_rows = self._get_sales_deed_rows_for_checklist(application_number)

        pairs_to_compare = []
        checklist_rows_by_id = {r.id: r for r in checklist_rows}

        # ---------------------------------------------------
        # Prepare pairs
        # ---------------------------------------------------
        for row in checklist_rows:

            if row.is_match_overridden:
                continue

            doc_a_val = row.document_a_value
            doc_b_val = row.document_b_value

            pc = row.pair_code
            attr = row.attribute_code

            if not doc_a_val or not doc_b_val:

                if pc == "SL_LA":

                    if attr == "borrower_name":
                        doc_a_val = sanction.borrower_name if sanction else None
                        doc_b_val = loan_agr.borrower_name if loan_agr else None

                    elif attr == "address":
                        doc_a_val = sanction.borrower_address if sanction else None
                        doc_b_val = loan_agr.borrower_address if loan_agr else None

                    elif attr == "property_address":
                        doc_a_val = sanction.property_address if sanction else None
                        doc_b_val = loan_agr.property_address if loan_agr else None

                    elif attr == "loan_amount":
                        doc_a_val = (
                            sanction.sanction_amount
                            if sanction and sanction.sanction_amount
                            else (sanction.loan_amount if sanction else None)
                        )
                        doc_b_val = loan_agr.loan_amount if loan_agr else None

                    elif attr == "date":
                        doc_a_val = sanction.sanction_date if sanction else None
                        doc_b_val = loan_agr.loan_agreement_date if loan_agr else None

                    elif attr.startswith("co_borrower_"):
                        doc_a_val = getattr(sanction, attr, None) if sanction else None
                        doc_b_val = getattr(loan_agr, attr, None) if loan_agr else None

                elif pc == "MODT_SD":

                    if attr == "property_description" or attr.startswith("property_description_"):
                        idx = self._extract_property_index(attr)
                        mapped_sales_deed = self._get_sales_deed_for_row(
                            sales_deed_rows,
                            idx,
                        )

                        doc_a_val = self._get_modt_raw_property_description(modt, idx) if modt else None
                        doc_b_val = (
                            mapped_sales_deed.raw_description
                            or self._build_sales_deed_schedule_description(mapped_sales_deed.id, idx)
                        ) if mapped_sales_deed else None

            pairs_to_compare.append({
                "checklist_row_id": row.id,
                "attribute_code": attr,
                "attribute_label": row.attribute_label,
                "pair_code": pc,
                "doc_a": row.document_a,
                "doc_a_val": doc_a_val,
                "doc_b": row.document_b,
                "doc_b_val": doc_b_val
            })

        # ---------------------------------------------------
        # LLM Matching
        # ---------------------------------------------------
        results = self._batch_llm_matching(application_number, pairs_to_compare)

        # ---------------------------------------------------
        # Update Checklist + Collect mismatches
        # Update WITHOUT versioning - versions created once after all updates
        # ---------------------------------------------------
        for res in results:

            row_id = res.get("checklist_row_id")
            match_status = res["match_status"]
            doc_a_val = res.get("doc_a_val")
            doc_b_val = res.get("doc_b_val")

            row = checklist_rows_by_id.get(row_id)
            if not row:
                continue

            if row.is_match_overridden:
                continue

            update_payload = {
                "match_status": match_status,
                "document_a_value": doc_a_val,
                "document_b_value": doc_b_val,
            }

            self.repo.update_row_values_without_versioning_by_id(
                row.id,
                update_payload,
                audit_user=audit_user,
            )

            if match_status == "MISMATCH":
                mismatches.append({
                    "pair": row.pair_code,
                    "attribute": row.attribute_label,
                    "doc_a_value": doc_a_val,
                    "doc_b_value": doc_b_val,
                })

        # Refresh checklist rows
        checklist_rows = self.repo.get_by_application(application_number)

        # ---------------------------------------------------
        # GENERATE OBSERVATION PER PAIR (ONLY IF MISMATCH EXISTS)
        # ---------------------------------------------------
        from app.db.models.observation import Observation

        pair_codes = set(r.pair_code for r in checklist_rows)

        for pair in pair_codes:

            # 🔥 Fetch mismatched rows directly from DB
            pair_mismatch_rows = [
                r for r in checklist_rows
                if r.pair_code == pair and r.match_status == "MISMATCH"
            ]

            if not pair_mismatch_rows:
                continue

            # 🔥 Do not recreate if already exists
            existing_obs = self.db.query(Observation).filter(
                Observation.application_number == application_number,
                Observation.pair_code == pair
            ).first()

            if existing_obs:
                continue

            # 🔥 Convert DB rows into mismatch structure
            formatted_mismatches = []
            for r in pair_mismatch_rows:
                formatted_mismatches.append({
                    "attribute": r.attribute_label,
                    "doc_a": r.document_a,
                    "doc_b": r.document_b,
                    "doc_a_value": r.document_a_value,
                    "doc_b_value": r.document_b_value
                })

            self._generate_pair_observation(
                application_number,
                pair,
                formatted_mismatches
            )

        # Check if we've already validated and created versions before
        # Only snapshot if we have LIVE versions > 1 (meaning we've done this before)
        # First validation: all rows are version=1, so don't snapshot
        # Subsequent validations: max version > 1, so create snapshot
        # Reset rerun flag for all rows
        self.repo.set_rerun_flag_without_versioning(application_number, 0, audit_user=audit_user)
        
        return self.repo.get_by_application(application_number)

    def _build_sales_deed_schedule_description(self, sales_deed_id: int, property_index: Optional[int] = None) -> Optional[str]:
        rows = self.db.query(ExtractedSalesDeedSchedule).filter(
            ExtractedSalesDeedSchedule.sales_deed_id == sales_deed_id
        ).order_by(ExtractedSalesDeedSchedule.id.asc()).all()
        if property_index is not None and property_index > 0:
            if len(rows) >= property_index:
                rows = [rows[property_index - 1]]
            else:
                rows = []

        if not rows:
            return None

        chunks = []
        for r in rows:
            parts = []
            if r.property_extent:
                extent = r.property_extent
                if r.property_extent_unit:
                    extent = f"{extent} {r.property_extent_unit}"
                parts.append(f"Extent: {extent}")
            if r.plot_dimension:
                parts.append(f"Plot_Dimension: {r.plot_dimension}")
            if r.survey_number:
                parts.append(f"Survey_Number: {r.survey_number}")
            if r.old_survey_number:
                parts.append(f"Old_Survey_Number: {r.old_survey_number}")
            if r.ts_number:
                parts.append(f"TS_Number: {r.ts_number}")
            if r.plot_number:
                parts.append(f"Plot_Number: {r.plot_number}")
            if r.village_street_name:
                parts.append(f"Village_Street_Name: {r.village_street_name}")
            if r.jurisdiction:
                parts.append(f"Jurisdiction: {r.jurisdiction}")
            if r.address_remarks:
                parts.append(f"Address_Remarks: {r.address_remarks}")
            if r.boundary_east:
                parts.append(f"East: {r.boundary_east}")
            if r.boundary_west:
                parts.append(f"West: {r.boundary_west}")
            if r.boundary_north:
                parts.append(f"North: {r.boundary_north}")
            if r.boundary_south:
                parts.append(f"South: {r.boundary_south}")

            if not parts:
                continue

            schedule_type = r.schedule_type or "SCHEDULE"
            chunks.append(f"{schedule_type}: " + "; ".join(parts))

        return " | ".join(chunks) if chunks else None

    def _get_modt_raw_property_description(self, modt: ExtractedMODT, property_index: Optional[int] = None) -> Optional[str]:
        rows = (
            self.db.query(ExtractedMODTProperty)
            .filter(ExtractedMODTProperty.modt_id == modt.id)
            .order_by(ExtractedMODTProperty.property_index.asc(), ExtractedMODTProperty.id.asc())
            .all()
        )
        if property_index is not None and property_index > 0:
            rows = [r for r in rows if (r.property_index or 0) == property_index]
        texts = []
        for row in rows:
            raw_text = (row.raw_property_text or "").strip() if row.raw_property_text else ""
            if raw_text:
                texts.append(raw_text)
                continue
            fallback = (row.property_description or "").strip() if row.property_description else ""
            if fallback:
                texts.append(fallback)
        return " | ".join(texts) if texts else None

    def _extract_property_index(self, attribute_code: str) -> Optional[int]:
        if attribute_code == "property_description":
            return 1
        m = re.match(r"^property_description_(\d+)$", attribute_code or "")
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    def _get_sales_deed_for_index(self, sales_deed_rows: list, property_index: Optional[int]) -> Optional[ExtractedSalesDeed]:
        if not sales_deed_rows:
            return None
        idx = property_index or 1
        if idx <= 0:
            idx = 1
        if len(sales_deed_rows) >= idx:
            return sales_deed_rows[idx - 1]
        return None

    def _get_sales_deed_for_row(
        self,
        sales_deed_rows: list[ExtractedSalesDeed],
        property_index: Optional[int],
    ) -> Optional[ExtractedSalesDeed]:
        return self._get_sales_deed_for_index(sales_deed_rows, property_index)


    def run_validation(self, application_number: str, audit_user=None):
        existing_rows = self.repo.get_by_application(application_number)
        next_version = 1
        if existing_rows:
            next_version = max((row.version or 0) for row in existing_rows) + 1
            self.repo.delete_by_application(application_number, audit_user=audit_user)

        self._build_checklist_rows(application_number, audit_user=audit_user, initial_version=next_version)
        ReportRepository(self.db).mark_rerun_report(application_number, 1, audit_user=audit_user)
        return self.trigger_matching(application_number, audit_user=audit_user)


    def _normalize_value(self, value) -> Optional[str]:
        """Normalize a value for comparison: strip whitespace, lowercase, remove common punctuation."""
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        if not value:
            return None
        # Lowercase for case-insensitive comparison
        value = value.lower()
        # Strip common punctuation from start and end
        value = value.strip(".,;:!?\"'/- \t\n\r")
        if not value:
            return None
        return value

    def _extract_numeric_amount(self, value) -> Optional[float]:
        """
        If a value is purely a formatted number/currency amount (e.g. 'Rs. 7,19,578/-',
        '7,19,578.00'), return its numeric value. Returns None for anything that isn't
        entirely digits once currency symbols/commas/spaces are removed, so text like
        addresses or property descriptions (which merely contain digits) are left alone.
        """
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        stripped = re.sub(r"rs\.?|inr|₹|\$|/-|[,\s]", "", text, flags=re.IGNORECASE)
        # If any ASCII letter survives, this is descriptive text (an address / property
        # description that merely contains digits), not an amount — leave it alone.
        if re.search(r"[A-Za-z]", stripped):
            return None
        # Drop a SHORT non-digit prefix/suffix (<=3 chars) so a currency symbol carried
        # over from a translated document (e.g. Tamil "ரூ.", Hindi "रु.") does not defeat
        # the numeric comparison, while a longer word-run (e.g. a translated address that
        # opens with a door number) is left intact so it fails the fullmatch below.
        stripped = re.sub(r"^[^\d]{1,3}(?=\d)", "", stripped)
        stripped = re.sub(r"(?<=\d)[^\d.]{1,3}$", "", stripped)
        if not re.fullmatch(r"\d+(\.\d+)?", stripped):
            return None
        try:
            return float(stripped)
        except ValueError:
            return None

    def _tokenize_for_comparison(self, value: Optional[str]) -> Optional[frozenset]:
        """Word/number tokens (lowercased) for order- and punctuation-insensitive equality checks."""
        if not value:
            return None
        tokens = re.findall(r"[a-z0-9]+", value.lower())
        return frozenset(tokens) if tokens else None

    def _contains_non_latin_letters(self, value) -> bool:
        """True when the text carries alphabetic characters outside the Latin range —
        i.e. one side comes from a document translated into another script (Tamil,
        Devanagari, Telugu, ...). Digits and punctuation are ignored so a bare
        '51,78,288' is not flagged. Such pairs cannot be compared by the ASCII token
        test and are routed to the LLM for a meaning-based check instead."""
        if not value:
            return False
        for ch in str(value):
            if ch.isalpha() and ord(ch) > 0x24F:
                return True
        return False

    def _batch_llm_matching(self, application_number: str, pairs: list) -> list:
        """
        Uses LLM to compare pairs of extracted values.
        """
        if not pairs:
            return []

        processed_results = []
        to_llm = []

        for pair in pairs:

            doc_a = self._normalize_value(pair.get("doc_a_val"))
            doc_b = self._normalize_value(pair.get("doc_b_val"))

            # Missing value
            if not doc_a or not doc_b:
                processed_results.append({
                    **pair,
                    "match_status": "MISMATCH"
                })
                continue

            # Exact match after normalization
            if doc_a == doc_b:
                processed_results.append({
                    **pair,
                    "match_status": "MATCH"
                })
                continue

            # Deterministic numeric/currency comparison — do not let the LLM guess on amounts.
            # Only kicks in when BOTH sides are purely a formatted number (see _extract_numeric_amount),
            # so text fields like addresses/names/property_description are unaffected and still go to Gemini.
            num_a = self._extract_numeric_amount(pair.get("doc_a_val"))
            num_b = self._extract_numeric_amount(pair.get("doc_b_val"))
            if num_a is not None and num_b is not None:
                processed_results.append({
                    **pair,
                    "match_status": "MATCH" if num_a == num_b else "MISMATCH"
                })
                continue

            # Two kinds of pair need a semantic, meaning-based comparison rather than a
            # literal token match:
            #   1. property_description (MODT vs Sale Deed) — transliteration / verbosity
            #      differences are expected.
            #   2. Any pair where one side has been translated into another script/language
            #      (e.g. the Sanction Letter displayed in Tamil against an English Loan
            #      Agreement) — the ASCII token test cannot see through the translation.
            # Both are handed to Gemini.
            cross_language = (
                self._contains_non_latin_letters(pair.get("doc_a_val"))
                or self._contains_non_latin_letters(pair.get("doc_b_val"))
            )
            if pair.get("pair_code") == "MODT_SD" or cross_language:
                to_llm.append(pair)
                continue

            # Every other field (names, addresses, dates, ...) is decided deterministically —
            # order/punctuation/case-insensitive comparison — instead of relying on the
            # LLM's subjective judgment, which does not reliably enforce exact-value equality.
            # MATCH when EITHER holds:
            #   - word tokens are equal (order-insensitive), or
            #   - the alphanumeric-only strings are equal (space/punctuation-insensitive,
            #     so "Rama Krishna Gorada" == "Rama KrishnaGorada").
            # Both still require the exact same letters/digits, so a genuine spelling
            # difference stays a MISMATCH.
            tokens_a = self._tokenize_for_comparison(doc_a)
            tokens_b = self._tokenize_for_comparison(doc_b)
            collapsed_a = re.sub(r"[^a-z0-9]", "", doc_a.lower())
            collapsed_b = re.sub(r"[^a-z0-9]", "", doc_b.lower())
            is_match = (tokens_a and tokens_a == tokens_b) or (
                collapsed_a and collapsed_a == collapsed_b
            )
            processed_results.append({
                **pair,
                "match_status": "MATCH" if is_match else "MISMATCH"
            })

        if not to_llm:    
            return processed_results

        print(f"Calling LLM to match {len(to_llm)} pairs for {application_number}...")

        prompt = f"""
        You are an expert data validator. Your task is to compare pairs of extracted values from different documents for loan application {application_number}.
        Be careful and strict. Do not guess missing values. Do not mark values as MATCH just because they look similar unless they clearly refer to the same fact.
        Some values may contain OCR noise, punctuation differences, spacing differences, abbreviations, or uppercase/lowercase differences.
        
        PAIRS TO EVALUATE:
        {json.dumps(to_llm, default=str, indent=2)}
        
        INSTRUCTIONS:
        1. Compare 'doc_a_val' and 'doc_b_val' for each pair.
        2. Determine 'match_status':
           - 'MATCH': Only if both values clearly refer to the same entity/information.
           - 'MISMATCH': If both values are present and they clearly contradict each other or refer to different facts.
           - 'MISMATCH': If doc_a_val or doc_b_val is empty, null, whitespace, missing, or not extracted.
        3. If one side has no extracted value, do NOT infer it from context. Return 'MISMATCH' and explain that the value is missing on that side.
        4. Treat the following as the SAME value (return MATCH) when the meaning is clearly identical:
        - Case differences (uppercase/lowercase)
        - Punctuation differences (dots, slashes, hyphens)
        - Spacing differences
        - Common OCR noise:
            * Character substitutions: m↔n, mb↔nt, d↔cl, X↔V↔K, W↔VV, U↔H, rn↔m
            * Character merges or splits (e.g., "sh" read as "5h")
        - Abbreviations: M/s, Mr., Mrs., initials, dots in names
        - Currency: symbols, commas, trailing '/-'
        - Date formats: DD/MM/YYYY vs DD-MM-YYYY vs written form for the same date
        - Name with prefix/initial: if the initial + surname pattern is structurally consistent
            and differences are plausibly OCR, treat as MATCH

        4a. CROSS-LANGUAGE / TRANSLATED VALUES (very important):
        - One of the two documents may have been translated, so the two values can be
          written in different languages or scripts. This applies to ANY language, not
          a fixed list.
        - When the two sides are in different languages/scripts, compare by MEANING and
          PRONUNCIATION (transliteration), NOT by literal spelling.
        - Return MATCH when, once transliterated / translated to a common language, the
          two values clearly refer to the same person, organisation, place, amount or
          date — allowing for the usual currency-symbol, punctuation and date-format
          differences already covered above.
        - Still return MISMATCH when the underlying facts differ (a different name, a
          different number, a different date). Translation is not a reason to pass a
          genuine mismatch.

        5. For NAMES specifically:
        - Be extremely strict. Return MATCH only if the names have the identical spelling (ignoring case, punctuation, spaces, and common honorifics/prefixes).
        - EXCEPTION: if the two name values are in different scripts/languages (see rule 4a),
          judge them by transliteration and meaning rather than identical spelling.
        - If there is any spelling difference, missing or extra letters (e.g., 'milkd' vs 'milkdf'), you MUST return MISMATCH. Do not count trailing extra/missing letters as OCR noise.
        - Only match if the first, middle, and last names match. If one name has a different word or suffix, return MISMATCH.
        - When returning MISMATCH for a name, your "reason" field must state the spelling mismatch (e.g. 'milkd' vs 'milkdf').


        6. For 'property_description' pairs (pair_code = MODT_SD):
            - STEP 1 — HARD FIELD CHECK (do this first, before any other comparison):
              Extract and compare the following hard fields from both doc_a_val and doc_b_val:
                * Re-S.F. number range (e.g., 278/1 to 278/17)
                * Plot/Site number (e.g., Site No. 88)
                * Block number (e.g., Block B)
                * Total area/extent in square feet and/or square meters (e.g., 1080 sq ft / 100.38 sq mt)
                * All four plot-level boundaries (North, South, East, West site numbers or road names)
              If ALL of the above hard fields are present on both sides and match,
              return MATCH immediately. Do not penalize for name spelling differences,
              transliteration variations, or additional details present on one side only.

            - STEP 2 — SOFT FIELD EVALUATION (only if hard fields are incomplete or partially missing):
              Compare village, taluka, district, layout name, and S.F./Re-S.F. numbers.
              Apply the following tolerances:
                * Place names, layout names, and proper nouns may originate from regional
                  or local languages and be romanized differently across documents.
                  If two names are plausibly the same word rendered in different
                  romanization or transliteration styles, treat as MATCH.
                * If a layout or scheme name appears to be a translation or alternate
                  transliteration of the same underlying name, treat as MATCH.
                * Only return MISMATCH if the names are phonetically and semantically
                  unrelated — i.e., clearly refer to different places or entities.

            - MISMATCH TRIGGERS — always return MISMATCH if:
                * S.F. / Re-S.F. numbers differ (not explainable by OCR noise)
                * Plot/site number differs
                * Area/extent differs beyond rounding tolerance
                * All four plot-level boundaries differ with no phonetic/transliteration explanation

            - Additional details present in one document but absent in the other
              (e.g., pathway rights, valuation, patta numbers, verbose boundary descriptions)
              must NOT cause a MISMATCH. One document may simply be more detailed.
        7. Return the same 'checklist_row_id' from the input for each result.
        8. Output MUST be a valid JSON list of objects.
        
        OUTPUT FORMAT:
        [
            {{
                "checklist_row_id": 123,
                "attribute_code": "date",
                "match_status": "MATCH",
                "reason": "brief reason, mention missing value if MISMATCH due to empty side"
            }}
        ]
        """

        try:
            llm_response = call_gemini_ai(prompt)
            if not llm_response:
                for p in to_llm:
                    doc_a_text = self._normalize_value(p.get("doc_a_val"))
                    doc_b_text = self._normalize_value(p.get("doc_b_val"))

                    if not doc_a_text or not doc_b_text:
                        status = "MISMATCH"
                    elif doc_a_text == doc_b_text:
                        status = "MATCH"
                    else:
                        status = "MISMATCH"

                    processed_results.append({
                        **p,
                        "match_status": status
                    })

                return processed_results

            import re
            match = re.search(r"\[.*\]", llm_response, re.DOTALL)
            if match:
                results = json.loads(match.group(0))
                # Map results back to original pairs
                for p in to_llm:
                    llm_res = next(
                        (
                            r for r in results
                            if r.get("checklist_row_id") == p.get("checklist_row_id")
                        ),
                        None,
                    )
                    if not llm_res:
                        llm_res = next(
                            (
                                r for r in results
                                if r.get("attribute_code") == p.get("attribute_code")
                                and r.get("pair_code") == p.get("pair_code")
                            ),
                            None,
                        )
                    status = llm_res.get("match_status", "MISMATCH") if llm_res else "MISMATCH"
                    processed_results.append({**p, "match_status": status})
                return processed_results
            else:
                # Fallback — no valid JSON found in LLM response
                for p in to_llm:
                    doc_a_text = self._normalize_value(p.get("doc_a_val"))
                    doc_b_text = self._normalize_value(p.get("doc_b_val"))

                    if not doc_a_text or not doc_b_text:
                        status = "MISMATCH"
                    elif doc_a_text == doc_b_text:
                        status = "MATCH"
                    else:
                        status = "MISMATCH"

                    processed_results.append({
                        **p,
                        "match_status": status,
                    })

                return processed_results
        except Exception as e:
            
            print(f"Error in LLM matching: {e}")

            for p in to_llm:
                doc_a_text = self._normalize_value(p.get("doc_a_val"))
                doc_b_text = self._normalize_value(p.get("doc_b_val"))

                if not doc_a_text or not doc_b_text:
                    status = "MISMATCH"
                elif doc_a_text == doc_b_text:
                    status = "MATCH"
                else:
                    status = "MISMATCH"

                processed_results.append({
                    **p,
                    "match_status": status,
                })

            return processed_results

    def _generate_pair_observation(self, application_number: str, pair_code: str, mismatches: list):
        """
        Generates separate observation entries per mismatched attribute.
        """

        if not mismatches:
            return

        from app.db.models.observation import Observation

        for mismatch in mismatches:

            attribute = mismatch.get("attribute")
            doc_a = mismatch.get("doc_a")
            doc_b = mismatch.get("doc_b")
            doc_a_value = mismatch.get("doc_a_value")
            doc_b_value = mismatch.get("doc_b_value")

            # Simple professional observation text
            observation_text = (
                f"Mismatch observed in '{attribute}' between {doc_a} and {doc_b}. "
                f"{doc_a} value: '{doc_a_value}' | {doc_b} value: '{doc_b_value}'."
            )

            new_observation = Observation(
                application_number=application_number,
                pair_code=pair_code,
                observation=observation_text,
                severity="Medium",
                status="Processing",
                made_by="AI_CHECKLIST",
                review_by="System"
            )

            self.db.add(new_observation)

        self.db.commit()
        print(f"Separate observations created for pair {pair_code}")


    def update_checklist(self, application_number: str, attribute_code: str, obj_in, audit_user=None):

        """
        Manual checklist update for a single attribute row.
        """

        row = self.repo.get_single_row(
            application_number,
            attribute_code,
        )
        if not row:
            return None

        update_payload = {}
        changed_value_fields = False

        if obj_in.document_a_value is not None and obj_in.document_a_value != row.document_a_value:
            update_payload["document_a_value"] = obj_in.document_a_value
            changed_value_fields = True

        if obj_in.document_b_value is not None and obj_in.document_b_value != row.document_b_value:
            update_payload["document_b_value"] = obj_in.document_b_value
            changed_value_fields = True

        if obj_in.match_status is not None and obj_in.match_status != row.match_status:
            update_payload["match_status"] = obj_in.match_status

        if obj_in.confidence is not None and obj_in.confidence != row.confidence:
            update_payload["confidence"] = obj_in.confidence

        if obj_in.remarks is not None and obj_in.remarks != row.remarks:
            update_payload["remarks"] = obj_in.remarks

        value_or_status_changed = False
        if (
            ("document_a_value" in update_payload)
            or ("document_b_value" in update_payload)
            or ("match_status" in update_payload)
        ):
            value_or_status_changed = True

        explicit_override = getattr(obj_in, "is_match_overridden", None)
        if explicit_override is not None:
            update_payload["is_match_overridden"] = bool(explicit_override)
        elif value_or_status_changed:
            # Auto-mark override only when comparison values/status are manually changed.
            update_payload["is_match_overridden"] = True

        if update_payload:
            self.repo.update_row_values(
                application_number,
                attribute_code,
                update_payload,
                audit_user=audit_user,
            )
            ReportRepository(self.db).mark_rerun_report(application_number, 1, audit_user=audit_user)

        if changed_value_fields:
            updated_row = self.repo.get_single_row(
                application_number,
                attribute_code,
            )
            if updated_row:
                self._rematch_single_row(application_number, updated_row, audit_user=audit_user)

        return self.repo.get_by_application(application_number)

    def update_checklist_bulk(
        self,
        application_number: str,
        items: list[ApplicationChecklistBulkUpdateItem],
        audit_user=None,
    ):
        any_row_found = False
        updated_any = False
        rows_to_rematch = []

        for item in items:
            row = self.repo.get_single_row(
                application_number,
                item.attribute_code,
            )
            if not row:
                continue
            any_row_found = True

            # Only act on the fields the client actually sent. This lets a value
            # sent as null / "" be applied as an intentional clear instead of being
            # ignored as "unchanged" (previously `is not None` dropped every clear).
            fields_set = item.model_fields_set
            update_payload = {}
            changed_value_fields = False

            if "document_a_value" in fields_set and item.document_a_value != row.document_a_value:
                update_payload["document_a_value"] = item.document_a_value
                changed_value_fields = True
            if "document_b_value" in fields_set and item.document_b_value != row.document_b_value:
                update_payload["document_b_value"] = item.document_b_value
                changed_value_fields = True
            if "match_status" in fields_set and item.match_status != row.match_status:
                update_payload["match_status"] = item.match_status
            if "confidence" in fields_set and item.confidence != row.confidence:
                update_payload["confidence"] = item.confidence
            if "remarks" in fields_set and item.remarks != row.remarks:
                update_payload["remarks"] = item.remarks

            value_or_status_changed = (
                ("document_a_value" in update_payload)
                or ("document_b_value" in update_payload)
                or ("match_status" in update_payload)
            )

            if "is_match_overridden" in fields_set and item.is_match_overridden is not None:
                update_payload["is_match_overridden"] = bool(item.is_match_overridden)
            elif value_or_status_changed:
                # Auto-mark override only when comparison values/status are manually changed.
                update_payload["is_match_overridden"] = True

            if not update_payload:
                continue

            self.repo.update_row_values(
                application_number,
                item.attribute_code,
                update_payload,
                audit_user=audit_user,
            )

            if changed_value_fields:
                updated_row = self.repo.get_single_row(
                    application_number,
                    item.attribute_code,
                )
                if updated_row:
                    rows_to_rematch.append(updated_row)

            updated_any = True

        # None => no row matched any attribute_code (genuine 404).
        # If a row was found but nothing changed, fall through and return the
        # current checklist so a no-op edit is not reported as "not found".
        if not any_row_found:
            return None

        if rows_to_rematch:
            self._rematch_rows_bulk(application_number, rows_to_rematch, audit_user=audit_user)

        if updated_any:
            ReportRepository(self.db).mark_rerun_report(application_number, 1, audit_user=audit_user)

        return self.repo.get_by_application(application_number)

    def _rematch_single_row(self, application_number: str, row, audit_user=None):
        pair_input = [{
            "checklist_row_id": row.id,
            "attribute_code": row.attribute_code,
            "attribute_label": row.attribute_label,
            "pair_code": row.pair_code,
            "doc_a": row.document_a,
            "doc_a_val": row.document_a_value,
            "doc_b": row.document_b,
            "doc_b_val": row.document_b_value,
        }]

        results = self._batch_llm_matching(application_number, pair_input)
        if not results:
            return

        self.repo.update_row_values_without_versioning_by_id(
            row.id,
            {"match_status": results[0]["match_status"]},
            audit_user=audit_user,
        )

    def _rematch_rows_bulk(self, application_number: str, rows, audit_user=None):
        pair_input = []
        for row in rows:
            pair_input.append({
                "checklist_row_id": row.id,
                "attribute_code": row.attribute_code,
                "attribute_label": row.attribute_label,
                "pair_code": row.pair_code,
                "doc_a": row.document_a,
                "doc_a_val": row.document_a_value,
                "doc_b": row.document_b,
                "doc_b_val": row.document_b_value,
            })

        results = self._batch_llm_matching(application_number, pair_input)
        if not results:
            return

        for res in results:
            row_id = res.get("checklist_row_id")
            status = res.get("match_status")
            if not row_id or not status:
                continue
            self.repo.update_row_values_without_versioning_by_id(
                row_id,
                {"match_status": status},
                audit_user=audit_user,
            )
