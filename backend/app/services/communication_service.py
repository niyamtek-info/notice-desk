import yaml
import os
import base64
import mimetypes
import re
import json
import html
import uuid
from pathlib import Path
from fastapi import HTTPException
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.db.repositories.communication_repository import CommunicationRepository
from app.schemas.communication_schema import MailTemplateRequest
from typing import Optional
from app.db.models.safari_notice import SarfaesiMaster
from app.db.models.application import Application
from app.db.versioning import live_filter
from app.core.settings import settings
from app.gateways.storage_gateway import get_storage_gateway
from app.api.v1.dependencies.auth import AuditUser
from app.services.pdf_service import PDFService
from app.services.placeholder_mapping_service import get_placeholder_mapping_lookup
import datetime


_TOKEN_PATTERN = re.compile(r"(\{\{\s*([^{}]+?)\s*\}\}|<\s*([^<>]+?)\s*>)")
_UNRESOLVED_BRACE_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*[^{}]+?\s*\}\}")


def normalize_placeholder_token(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(raw or "")).strip("_").upper()


def sanitize_placeholder_value(value) -> str:
    if value is None:
        return ""

    text = str(value)
    if not text:
        return ""

    stripped = text.strip()
    if not stripped:
        return ""

    if stripped.lower() in {"null", "none", "undefined", "nan"}:
        return ""

    return text


def cleanup_unresolved_brace_placeholders(text: str) -> str:
    if not text:
        return text
    return _UNRESOLVED_BRACE_PLACEHOLDER_PATTERN.sub("", text)


def build_placeholder_map(data: dict) -> dict:
    return {
        normalize_placeholder_token(str(key)): sanitize_placeholder_value(value)
        for key, value in data.items()
        if not isinstance(value, list)
    }


class CommunicationService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = CommunicationRepository(db)
        self.s3 = get_storage_gateway()
        self.template_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "metatable",
            "mail_templates.yaml"
        )
        self.mapping = get_placeholder_mapping_lookup()
        self.report_fields = self.mapping.get("report_fields", [])
        self.notice_template_aliases = self.mapping.get("notice_template_aliases", [])

    # ==========================================================
    # LOAD YAML
    # ==========================================================

    def load_templates(self):
        with open(self.template_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_report_schema(self):
        return self.mapping if isinstance(self.mapping, dict) else {}

    # Same amount fields SarfaesiService._format_response() comma-formats for
    # the report edit form - kept in sync here so the generated notice shows
    # the same "19,55,60,000.00" grouping instead of the raw DB "195560000.00".
    _AMOUNT_FIELDS = {
        "dpd",
        "disbursal_amount",
        "loan_amount",
        "future_principal",
        "principal_outstanding",
        "instalment_overdue",
        "interest_on_termination",
        "late_payment_penalty",
        "cheque_bounce_charges",
        "other_amount",
        "foreclosure_charges",
        "total_outstanding",
        "notice_13_2_amount",
        "reserve_price",
        "sold_price",
        "outstanding_amount",
        "emd_amount",
        "bid_increment",
    }

    @staticmethod
    def _format_indian_amount(value) -> str | None:
        if value is None:
            return None

        raw = str(value).strip()
        if not raw:
            return None

        is_negative = raw.startswith("-")
        unsigned = raw.replace("-", "").replace(",", "")
        int_part, _, dec_part = unsigned.partition(".")
        int_part = "".join(ch for ch in int_part if ch.isdigit())
        if not int_part:
            return None

        last_three = int_part[-3:]
        rest = int_part[:-3]
        if rest:
            grouped_rest = []
            while len(rest) > 2:
                grouped_rest.insert(0, rest[-2:])
                rest = rest[:-2]
            grouped_rest.insert(0, rest)
            formatted_int = ",".join(grouped_rest) + "," + last_three
        else:
            formatted_int = last_three

        dec_part = "".join(ch for ch in dec_part if ch.isdigit())[:2].ljust(2, "0") or "00"
        result = f"{formatted_int}.{dec_part}"
        return f"-{result}" if is_negative else result

    def _format_report_value(self, value, field_name: str | None = None):
        if value is None:
            return ""

        if isinstance(value, (datetime.datetime, datetime.date)):
            return value.strftime("%d-%m-%Y")

        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)

        if field_name in self._AMOUNT_FIELDS:
            formatted = self._format_indian_amount(value)
            return formatted if formatted is not None else value

        return value

    def _format_address_value(self, value, max_lines=None):
        if value is None:
            return ""

        text = str(value).strip()
        if not text:
            return ""

        if "|" in text:
            parts = [part.strip() for part in text.split("|") if part.strip()]
        elif "," in text:
            parts = [part.strip() for part in text.split(",") if part.strip()]
        else:
            parts = [part.strip() for part in re.split(r"\n+", text) if part.strip()]

        # ──────────────────────────────────────────────────────────────────────
        # Indian address: intelligently combine comma-separated parts into
        # a clean 3-line format whenever possible.
        #   Line 1 : Door / house number + immediate area (e.g. HND:-1-8-74/21, Fire station)
        #   Line 2 : Locality / landmark  (e.g. TD gutta)
        #   Line 3 : City + pincode       (e.g. mahabub Nagar - 509001)
        # ──────────────────────────────────────────────────────────────────────
        if len(parts) > 3:
            # Keep first part as line 1 (door / identifier)
            # Keep last part as line 3 (city + state + pincode)
            # Merge everything in between into line 2
            first = parts[0]
            last = parts[-1]
            middle = [p for p in parts[1:-1] if p]
            line2 = ", ".join(middle) if middle else None
            lines = [first]
            if line2:
                lines.append(line2)
            lines.append(last)
            parts = lines

        if len(parts) <= 1:
            # Try a conservative split for long single-line addresses so
            # notice blocks render with readable line breaks instead of one
            # very long row.
            long_text = re.sub(r"\s+", " ", text).strip()
            if len(long_text) <= 70:
                result = long_text
                if max_lines is not None:
                    result = self._limit_address_lines(result, max_lines)
                return result

            separators = [
                r"\b(?=Opp\b)",
                r"\b(?=Near\b)",
                r"\b(?=Behind\b)",
                r"\b(?=Beside\b)",
                r"\b(?=Ward\b)",
                r"\b(?=Road\b)",
                r"\b(?=Street\b)",
                r"\b(?=Taluk\b)",
                r"\b(?=District\b)",
                r"\b(?=Pincode\b)",
                r"\b(?=PIN\b)",
                r"\b(?=Karnataka\b)",
                r"\b(?=Rajasthan\b)",
                r"\b(?=Kerala\b)",
                r"\b(?=Tamil\b)",
                r"\b(?=Andhra\b)",
                r"\b(?=Maharashtra\b)",
                r"\b(?=Telangana\b)",
                r"\b(?=Bangalore\b)",
                r"\b(?=Bengaluru\b)",
                r"\b(?=\d{6}\b)",
            ]
            formatted = long_text
            for pattern in separators:
                formatted = re.sub(pattern, "\n", formatted, flags=re.I)

            lines = [line.strip(" ,-/") for line in re.split(r"\n+", formatted) if line.strip(" ,-/")]
            if len(lines) > 1:
                if len(lines) > 3 and max_lines is None:
                    # Keep first as line1, last as line3, merge middle into line2
                    first = lines[0]
                    last = lines[-1]
                    middle = [l for l in lines[1:-1] if l]
                    line2 = ", ".join(middle) if middle else None
                    merged = [first]
                    if line2:
                        merged.append(line2)
                    merged.append(last)
                    result = "\n".join(merged)
                else:
                    result = "\n".join(lines)
                if max_lines is not None:
                    result = self._limit_address_lines(result, max_lines)
                return result

            # Final fallback: wrap by words at a reasonable width.
            words = long_text.split()
            wrapped = []
            current = []
            for word in words:
                candidate = " ".join(current + [word]).strip()
                if current and len(candidate) > 42:
                    wrapped.append(" ".join(current))
                    current = [word]
                else:
                    current.append(word)
            if current:
                wrapped.append(" ".join(current))
            result = "\n".join(wrapped) if len(wrapped) > 1 else long_text
            if max_lines is not None:
                result = self._limit_address_lines(result, max_lines)
            return result

        result = "\n".join(parts)
        if max_lines is not None:
            result = self._limit_address_lines(result, max_lines)
        return result

    def _limit_address_lines(self, address_text, max_lines):
        if not address_text:
            return address_text
        lines = [line.strip() for line in address_text.split("\n") if line.strip()]
        if len(lines) <= max_lines:
            return address_text
        # Take only the first max_lines lines, then join remaining content into the last line
        kept_lines = lines[:max_lines - 1]
        remaining_parts = lines[max_lines - 1:]
        if remaining_parts:
            last_line = ", ".join(remaining_parts)
            kept_lines.append(last_line)
        return "\n".join(kept_lines)

    def _merge_address_with_also_at(self, primary_address, also_at_address=None):
        """Merge primary address and also-at address into a single address block."""
        parts = []
        if primary_address:
            formatted = self._format_address_value(primary_address)
            if formatted:
                for line in formatted.split("\n"):
                    line = line.strip()
                    if line:
                        parts.append(line)
        if also_at_address:
            formatted = self._format_address_value(also_at_address)
            if formatted:
                for line in formatted.split("\n"):
                    line = line.strip()
                    if line:
                        parts.append(line)
        
        return "\n".join(parts) if parts else None

    def _build_borrower_section(self, data: dict) -> str:
        """
        Build the borrower section HTML for report_driven templates.
        Format: Name (no number prefix), then 3 lines of address max (combining primary + also_at).
        No "ALSO AT," label - just the address lines directly.
        """
        max_address_lines = 3
        parts = []

        # Borrower
        borrower_name = data.get("borrower_name", "")
        borrower_address = data.get("borrower_address", "")
        also_at = data.get("borrower_address_also_at", "")

        if borrower_name:
            # Name without "1." prefix - just the name
            parts.append(f'<strong>{html.escape(str(borrower_name))}</strong>')

        # Merge primary address and also_at, then cap at 3 lines
        merged_address = self._merge_address_with_also_at(borrower_address, also_at)
        if merged_address:
            limited = self._limit_address_lines(merged_address, max_address_lines)
            if limited:
                for line in limited.split("\n"):
                    line = line.strip()
                    if line:
                        parts.append(
                            f'<span style="display:block;">{html.escape(line)}</span>'
                        )

        # Co-borrowers
        for idx in range(1, 7):
            co_name = data.get(f"co_borrower_{idx}_name", "") or data.get(f"co_borrower_name_{idx}", "")
            co_address = data.get(f"co_borrower_{idx}_address", "") or data.get(f"co_borrower_address_{idx}", "")
            co_also_at = data.get(f"co_borrower_{idx}_address_also_at", "") or data.get(f"co_borrower_address_{idx}_also_at", "")

            if not co_name:
                continue

            # Name without serial number prefix
            parts.append(f'<strong>{html.escape(str(co_name))}</strong>')

            # Merge address + also_at, cap at 3 lines
            merged_address = self._merge_address_with_also_at(co_address, co_also_at)
            if merged_address:
                limited = self._limit_address_lines(merged_address, max_address_lines)
                if limited:
                    for line in limited.split("\n"):
                        line = line.strip()
                        if line:
                            parts.append(
                                f'<span style="display:block;">{html.escape(line)}</span>'
                            )

        if not parts:
            return ""

        joined = "".join(
            f'<span class="borrower-line" style="display:block; margin:0 0 2px 0; line-height:1.4;">{p}</span>'
            for p in parts
        )

        return (
            '<div class="borrower-section" '
            'style="margin:5px 0; white-space:normal; line-height:1.4;">'
            f"{joined}"
            "</div>"
        )

    def _compose_report_address(self, primary, also_at=None):
        parts = []

        def add_part(value):
            if value is None:
                return
            text = str(value).strip()
            if not text:
                return
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            for chunk in re.split(r"\n+", text):
                chunk = chunk.strip()
                if chunk:
                    parts.append(chunk)

        add_part(primary)
        add_part(also_at)
        return "\n".join(parts)

    def _build_mortgaged_property_address(self, report):
        if not report:
            return ""

        value = getattr(report, "property_address", None)
        if value is None:
            return ""

        return str(value).strip()

    def _report_value(self, report, *field_names, default=""):
        if not report:
            return default

        for field_name in field_names:
            value = getattr(report, field_name, None)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return default

    def _compose_co_borrower_address(self, report, index: int):
        primary = self._report_value(
            report,
            f"co_borrower_{index}_address",
            f"co_borrower_address_{index}",
        )
        also_at = self._report_value(
            report,
            f"co_borrower_{index}_address_also_at",
            f"co_borrower_address_{index}_also_at",
        )
        return self._compose_report_address(primary, also_at)

    def _format_address_block(self, value):
        formatted = self._format_address_value(value)
        if not formatted:
            return ""

        lines = [line.strip() for line in formatted.split("\n") if line.strip()]
        if not lines:
            return ""

        rendered_lines = []
        for line in lines:
            safe_line = html.escape(line)
            rendered_lines.append(
                f'<span class="address-line" style="display:block; margin:0 0 3px 0; line-height:1.5;">{safe_line}</span>'
            )

        joined = "".join(rendered_lines)
        if not joined:
            return ""

        return (
            '<span class="address-block" '
            'style="display:inline-block; white-space:normal; line-height:1.5; '
            'margin-top:2px; margin-bottom:2px;">'
            f"{joined}"
            "</span>"
        )

    def _safe_path_part(self, value: str, fallback: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
        cleaned = cleaned.strip("._-")
        return cleaned or fallback

    def _get_application(self, application_number: str):
        return self.db.query(Application).filter(
            Application.business_code == application_number,
            *live_filter(Application)
        ).first()

    def _get_master_report(self, application_number: str):
        # SARFAESI master report is the source of truth for notice rendering.
        return self.db.query(SarfaesiMaster).filter(
            SarfaesiMaster.application_number == application_number,
            *live_filter(SarfaesiMaster)
        ).first()

    def _loan_account_storage_root(self, application_number: str) -> str:
        application = self._get_application(application_number)
        loan_account_number = ""
        if application and getattr(application, "loan_account_number", None):
            loan_account_number = str(application.loan_account_number).strip()

        safe_loan_account = self._safe_path_part(loan_account_number or application_number, "application")
        return safe_loan_account

    def _section_type_from_template_name(self, template_name: str) -> str:
        value = str(template_name or "").strip()
        if not value:
            return "general"
        return self._safe_path_part(value.split("/", 1)[0], "general")

    def _communication_storage_prefix(self, application_number: str, template_name: str) -> str:
        loan_root = self._loan_account_storage_root(application_number)
        section_type = self._section_type_from_template_name(template_name)
        return f"{loan_root}/templates/{section_type}"

    def _communication_storage_context(self, application_number: str, template_name: str) -> dict:
        return {
            "loan_account_root": self._loan_account_storage_root(application_number),
            "section_type": self._section_type_from_template_name(template_name),
        }

    def _wrap_html_document(self, content: str) -> str:
        html_text = content or ""
        if "<html" in html_text.lower():
            return html_text
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
</head>
<body>{html_text}</body>
</html>"""

    async def _build_pdf_bytes(
        self,
        *,
        subject: str,
        body_html: str,
        structured_components: Optional[dict] = None,
    ) -> bytes:
        pdf_service = PDFService()
        pdf_buffer = await pdf_service.generate_communication_pdf(
            subject=subject or "",
            body_html=body_html or "",
            structured_components=structured_components or {},
        )
        return pdf_buffer.getvalue()

    # (primary address field, also-at field name variants that alias the
    # same underlying "_alt" DB column - see safari_notice.py's
    # borrower_address_also_at / co_borrower_N_address_also_at properties)
    _ADDRESS_ALSO_AT_PAIRS = [
        ("borrower_address", ("borrower_address_alt", "borrower_address_also_at")),
    ] + [
        (
            f"co_borrower_{i}_address",
            (f"co_borrower_{i}_address_alt", f"co_borrower_{i}_address_also_at"),
        )
        for i in range(1, 7)
    ]

    @staticmethod
    def _normalize_address_for_compare(value) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip().lower()

    def _suppress_duplicate_also_at_addresses(self, report, data: dict) -> None:
        """
        An "Also At" address is only meant to appear when it's genuinely
        different from the borrower's/co-borrower's primary address.
        Placeholder substitution just inserts whatever value is stored, so
        if both were saved identically the notice would show the same
        address twice under an "Also At" heading. Blank the also-at value
        here so any {{..._ALSO_AT}} / {{..._ALT}} placeholder resolves to
        empty instead of repeating the primary address.
        """
        for primary_field, alt_fields in self._ADDRESS_ALSO_AT_PAIRS:
            primary_norm = self._normalize_address_for_compare(
                getattr(report, primary_field, None)
            )
            if not primary_norm:
                continue
            for alt_field in alt_fields:
                alt_norm = self._normalize_address_for_compare(
                    getattr(report, alt_field, None)
                )
                if alt_norm and alt_norm == primary_norm and alt_field in data:
                    data[alt_field] = ""

    def _build_report_schema_data(self, report):
        data = {}
        for field_config in self.report_fields:
            field_name = field_config.get("field")
            if not field_name:
                continue
            model_field = field_config.get("model_field") or field_name
            value = self._format_report_value(getattr(report, model_field, None), field_name=field_name)
            if "address" in field_name:
                value = self._format_address_value(value)
            data[field_name] = value if value is not None else ""

        return data

    def _build_placeholder_data_from_report(self, application_number: str, report=None):
        report = report or self._get_generated_report(application_number)

        data = self._build_report_schema_data(report) if report else {}
        if report:
            self._suppress_duplicate_also_at_addresses(report, data)
            mortgaged_property_address = self._build_mortgaged_property_address(report)
            data["mortgaged_property_address"] = mortgaged_property_address
            data["ADDRESS_OF_MORTGAGED_PROPERTY"] = mortgaged_property_address
            data["ADDRESS_OF_THE_MORTGAGED_PROPERTY"] = mortgaged_property_address
            data["MORTGAGED_PROPERTY_ADDRESS"] = mortgaged_property_address
        data.update(self._build_report_placeholder_aliases(application_number, report=report))

        return data

    def validate_required_notice_fields(self, application_number: str) -> list[str]:
        """
        Validate that all required fields for notice generation are present.
        Returns a list of missing field display names. Empty list means all required fields are present.
        """
        report = self._get_generated_report(application_number)
        if not report:
            return ["Sarfaesi record not found for this application"]

        missing_fields = []

        # Mapping of model attribute -> display name for error messages
        required_fields = [
            ("loan_account_no", "LOAN ACCOUNT NO."),
            ("borrower_name", "Name of borrower"),
            ("borrower_address", "Borrower address"),
            ("property_address", "Property Address"),
            ("co_borrower_1_name", "Co-Borrower Name_1"),
            ("co_borrower_1_address", "Co-Borrower Address_1"),
            ("property_description", "Description of Schedule Property"),
            ("npa_date", "Date of NPA"),
            ("loan_agreement_date", "Loan Agreement Date"),
            ("loan_amount", "Loan amount"),
            ("loan_amount_words", "Loan amount in words"),
            ("future_principal", "Future principal"),
            ("principal_outstanding", "Principal Outstanding"),
            ("instalment_overdue", "Instalment overdue amount"),
            ("interest_on_termination", "Interest on Termination"),
            ("late_payment_penalty", "Late Payment Penalty"),
            ("cheque_bounce_charges", "Cheque Bounce Charges"),
            ("other_amount", "Other Amount"),
            ("foreclosure_charges", "Foreclosure charges"),
            ("total_outstanding", "Total Outstanding"),
            ("fcl_as_on_date", "FCL (As on Date)"),
            ("total_outstanding_words", "Total Outstanding in words"),
        ]

        for attr, display_name in required_fields:
            value = getattr(report, attr, None)
            if value is None:
                missing_fields.append(display_name)
            elif isinstance(value, str) and not value.strip():
                missing_fields.append(display_name)
            elif isinstance(value, (int, float)) and value == 0:
                # Zero is a valid value for numeric fields, only None is missing
                pass

        return missing_fields

    # ==========================================================
    # MAIN GENERATE METHOD
    # ==========================================================

    def generate_template_content(self, request: MailTemplateRequest) -> dict:

        templates = self.load_templates()
        template_group = templates.get("templates", {})
        template = template_group.get(request.template_name)

        if not template:
            return {
                "subject": f"Regarding Application {request.application_number}",
                "body": "Template not found.",
                "structuredComponents": {"IMAGE": [], "TABLE": []},
                "render_mode": "standard"
            }

        render_mode = template.get("render_mode", "standard")
        subject = template.get("subject", "")
        body = template.get("body", "")

        report = self._get_generated_report(request.application_number)
        if not report:
            raise HTTPException(
                status_code=404,
                detail="No report available for this application",
            )

        data = self._build_placeholder_data_from_report(
            request.application_number,
            report=report,
        )

        data["email"] = request.email or ""
        data["contact"] = request.contact or ""
        data["sender"] = request.sender or ""

        # Replace placeholders case-insensitively so both lowercase and CAPS
        # templates resolve to the same backend field names.
        placeholder_map = build_placeholder_map(data)
        print("===================================")
        print("INSIDE TEMPLATE GENERATION")
        print(
            "SYMBOLIC_PUB_ENGLISH_13_4 =>",
            placeholder_map.get("SYMBOLIC_PUB_ENGLISH_13_4")
        )
        print(
            "NOTICE_DISPATCH_DATE =>",
            placeholder_map.get("NOTICE_DISPATCH_DATE")
        )
        print("===================================")
        def _replace_token(match):
            token = match.group(2) or match.group(3) or ""
            normalized = normalize_placeholder_token(token)
            return placeholder_map.get(normalized, "")

        subject = _TOKEN_PATTERN.sub(_replace_token, subject)
        body = _TOKEN_PATTERN.sub(_replace_token, body)
        subject = cleanup_unresolved_brace_placeholders(subject)
        body = cleanup_unresolved_brace_placeholders(body)

        structured_components = {"IMAGE": [], "TABLE": []}

        # ==========================================================
        # MODE 1: STANDARD
        # ==========================================================
        if render_mode == "standard":
            pass

        # ==========================================================
        # MODE 2: ADVANCED (HTML parsing for ICC/ICICI)
        # ==========================================================
        elif render_mode == "advanced":
            processed = self._process_rendering(body)
            body = processed["body"]
            structured_components = processed["structuredComponents"]

        # ==========================================================
        # MODE 3: REPORT DRIVEN (Dynamic borrower + schedules)
        # ==========================================================
        elif render_mode == "report_driven":

            borrower_section = self._build_borrower_section(data)
            body = body.replace("{{borrower_section}}", borrower_section)

            schedule_tables = self._build_schedule_tables(template, data)

            structured_table_list = []
            table_index = 0

            # Get schedules defined in YAML dynamically
            schedules_defined = template.get("schedules", {}).keys()

            for schedule_key in schedules_defined:

                placeholder = f"{{{{{schedule_key}_table}}}}"

                if schedule_key in schedule_tables:

                    body = body.replace(
                        placeholder,
                        f"[STRUCTURED_COMPONENT:TABLE:{table_index}]"
                    )

                    structured_table_list.append(schedule_tables[schedule_key])
                    table_index += 1

                else:
                    # Remove placeholder if no data available
                    body = body.replace(placeholder, "")

            structured_components["TABLE"] = structured_table_list

        return {
            "subject": subject,
            "body": body,
            "structuredComponents": structured_components,
            "render_mode": render_mode
        }

    # ==========================================================
    # FETCH DATA FROM GENERATED REPORT
    # ==========================================================

    def _get_generated_report(self, application_number: str):
        # Explicit ordering matters here: if more than one row ever ends up
        # matching live_filter for the same application (e.g. a past race
        # between two concurrent saves each closing/cloning a version), an
        # unordered .first() can hand back a stale row - which is exactly
        # how a freshly-saved borrower/co-borrower address update failed to
        # show up in the generated notice. sarfaesi_repository.py's
        # get_by_application_number() already guards against this the same
        # way; mirror it here since this is the read path every notice/PDF/
        # Word generation goes through.
        return (
            self.db.query(SarfaesiMaster)
            .filter(
                SarfaesiMaster.application_number == application_number,
                *live_filter(SarfaesiMaster),
            )
            .order_by(SarfaesiMaster.updated_at.desc(), SarfaesiMaster.id.desc())
            .first()
        )

    def _build_report_placeholder_aliases(self, application_number: str, report=None):
        report = report or self._get_generated_report(application_number)

        aliases = {}
        for alias_config in self.notice_template_aliases:
            alias_name = alias_config.get("alias")
            if not alias_name:
                continue
            aliases[alias_name.lower()] = self._resolve_placeholder_alias(
                alias_config,
                application_number=application_number,
                report=report,
            )

        # Preserve a few convenience aliases used by the HTML renderer.
        aliases.setdefault("application_number", application_number)
        aliases.setdefault("email", "")
        aliases.setdefault("contact", "")
        aliases.setdefault("sender", "")
        return aliases

    def _resolve_placeholder_alias(self, alias_config: dict, *, application_number: str, report=None):
        report = report or self._get_generated_report(application_number)
        transform = str(alias_config.get("transform") or "first").strip().lower()

        if transform == "constant":
            return alias_config.get("constant", "")

        source_fields = alias_config.get("source_fields") or alias_config.get("source_field") or []
        if isinstance(source_fields, str):
            source_fields = [source_fields]
        if not isinstance(source_fields, list):
            source_fields = []

        # Fallback: if no source_fields specified, use the "target" field as the
        # source of truth so simple alias → target entries resolve correctly.
        if not source_fields:
            target = alias_config.get("target")
            if target:
                source_fields = [target.lower()]

        values = [self._report_value(report, field) for field in source_fields]

        if transform == "date_or_now":
            value = values[0] if values else None
            return self._format_report_value(value) or datetime.datetime.now().strftime("%d-%m-%Y")

        if transform == "date":
            value = values[0] if values else None
            return self._format_report_value(value)

        if transform == "join":
            separator = alias_config.get("separator", ", ")
            parts = [str(value).strip() for value in values if str(value).strip()]
            return separator.join(parts)

        if transform == "compose_address":
            parts = [self._format_report_value(value) for value in values if value not in (None, "")]
            cleaned_parts = [str(part).strip() for part in parts if str(part).strip()]
            if not cleaned_parts:
                return ""
            return self._format_address_block("\n".join(cleaned_parts))

        value = values[0] if values else ""
        if value is None:
            return ""
        return self._format_report_value(value)
    # ==========================================================
    # LEGACY HTML PARSER (DO NOT REMOVE)
    # ==========================================================

    def _process_rendering(self, html_content: str):

        soup = BeautifulSoup(html_content, "html.parser")

        structured_components = {
            "IMAGE": [],
            "TABLE": []
        }

        # Extract tables
        for table in soup.find_all("table"):

            headers = []
            rows = []

            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                cell_text = [c.get_text(strip=True) for c in cells]

                if tr.find("th"):
                    headers = cell_text
                else:
                    rows.append(cell_text)

            structured_components["TABLE"].append({
                "title": "",
                "headers": headers,
                "rows": rows
            })

            table.replace_with(
                soup.new_string(
                    f"[STRUCTURED_COMPONENT:TABLE:{len(structured_components['TABLE']) - 1}]"
                )
            )

        return {
            "body": str(soup),
            "structuredComponents": structured_components
        }

    def _amount_to_words(self, amount_str: str) -> str:
        """Simple utility to convert amount string (with currency) to words."""
        import re
        try:
            # Extract numbers only
            nums = re.findall(r'\d+', amount_str.replace(',', ''))
            if not nums: return "Zero"
            num = int(nums[0])
            
            # Basic conversion (Simplified for brevity, can be expanded)
            units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
            teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
            tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
            
            def convert_less_than_thousand(n):
                res = ""
                if n >= 100:
                    res += units[n // 100] + " Hundred "
                    n %= 100
                if n >= 20:
                    res += tens[n // 10] + " "
                    n %= 10
                if n >= 10:
                    res += teens[n - 10] + " "
                    n = 0
                if n > 0:
                    res += units[n] + " "
                return res.strip()

            if num == 0: return "Zero"
            
            # handle Lakhs/Crores (Indian System)
            res = ""
            if num >= 10000000:
                res += convert_less_than_thousand(num // 10000000) + " Crore "
                num %= 10000000
            if num >= 100000:
                res += convert_less_than_thousand(num // 100000) + " Lakh "
                num %= 100000
            if num >= 1000:
                res += convert_less_than_thousand(num // 1000) + " Thousand "
                num %= 1000
            res += convert_less_than_thousand(num)
            
            return res.strip() + " Only"
        except:
            return str(amount_str)


    async def save_communication(self, comm_data: dict, pdf_bytes: bytes | None = None):
        payload = dict(comm_data or {})
        payload.pop("structuredComponents", None)
        payload.pop("structured_components", None)
        application_number = payload.get("application_number")
        template_name = payload.get("template_name") or payload.get("subject") or "template"
        content = payload.get("content") or ""
        meta_data = dict(payload.get("meta_data") or {})
        db_content = content
        if db_content:
            try:
                db_content = BeautifulSoup(db_content, "html.parser").get_text(" ", strip=True)
            except Exception:
                db_content = str(db_content)
            if len(db_content) > 60000:
                db_content = db_content[:60000]

        html_path = payload.get("html_path")
        pdf_path = payload.get("pdf_path")
        audit_user = payload.pop("_audit_user", None)
        actor = None
        if isinstance(audit_user, AuditUser):
            actor = audit_user.audit_actor
        elif isinstance(audit_user, dict):
            actor = audit_user.get("audit_actor") or audit_user.get("email") or audit_user.get("full_name")
        if not actor:
            actor = payload.get("sender") or payload.get("recipient") or "System"

        if application_number and (content or pdf_bytes is not None):
            artifact_prefix = self._communication_storage_prefix(application_number, template_name)
            artifact_context = self._communication_storage_context(application_number, template_name)
            stamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            suffix = uuid.uuid4().hex[:8]
            stem = f"{stamp}_{suffix}"

            if content:
                normalized_html = self._wrap_html_document(content)
                html_filename = f"{stem}.html"
                html_key = f"{artifact_prefix}/{html_filename}"
                self.s3.upload_bytes(
                    normalized_html.encode("utf-8"),
                    html_key,
                    html_filename,
                )
                html_path = html_key

            if pdf_bytes is None:
                pdf_bytes = await self._build_pdf_bytes(
                    subject=payload.get("subject") or template_name,
                    body_html=content,
                    structured_components=meta_data.get("structuredComponents")
                    or meta_data.get("structured_components")
                    or {},
                )

            if pdf_bytes:
                pdf_filename = f"{stem}.pdf"
                pdf_key = f"{artifact_prefix}/{pdf_filename}"
                self.s3.upload_bytes(
                    pdf_bytes,
                    pdf_key,
                    pdf_filename,
                )
                pdf_path = pdf_key

            meta_data.update(
                {
                    "artifact_directory": artifact_prefix,
                    **artifact_context,
                    "html_path": html_path,
                    "pdf_path": pdf_path,
                }
            )
            payload["meta_data"] = meta_data

        payload["content"] = db_content
        payload["html_path"] = html_path
        payload["pdf_path"] = pdf_path
        payload["created_by"] = payload.get("created_by") or actor
        payload["updated_by"] = payload.get("updated_by") or actor
        return self.repo.create(payload)