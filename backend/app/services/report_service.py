from html.parser import HTMLParser
from io import BytesIO
import re
from datetime import date, datetime
from typing import List, Dict, Optional

import pandas as pd
from fastapi.responses import StreamingResponse
from num2words import num2words
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import AuditUser
from app.db.repositories.report_repo import ReportRepository
from app.db.models.client_models import Client
from app.db.models.safari_notice import SarfaesiMaster
from app.db.models.extracted_data import ApplicationChecklist
from app.db.versioning import live_filter
from app.utils.date_utils import parse_datetime


_HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")


class _ReportHtmlToExcelParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments: list[tuple[str, dict[str, bool]]] = []
        self._style_stack: list[dict[str, bool]] = [
            {"bold": False, "italic": False, "underline": False, "strike": False}
        ]

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in {"strong", "b", "em", "i", "ins", "u", "strike", "s", "del", "span"}:
            style = self._style_stack[-1].copy()
            if tag in {"strong", "b"}:
                style["bold"] = True
            if tag in {"em", "i"}:
                style["italic"] = True
            if tag in {"ins", "u"}:
                style["underline"] = True
            if tag in {"strike", "s", "del"}:
                style["strike"] = True
            attr_map = {str(k).lower(): v for k, v in attrs}
            style_attr = str(attr_map.get("style") or "").lower()
            if "font-weight:bold" in style_attr or "font-weight: bold" in style_attr:
                style["bold"] = True
            if "font-style:italic" in style_attr or "font-style: italic" in style_attr:
                style["italic"] = True
            if "text-decoration" in style_attr:
                if "underline" in style_attr:
                    style["underline"] = True
                if "line-through" in style_attr:
                    style["strike"] = True
            self._style_stack.append(style)
            return
        if tag == "br":
            self._append_text("\n")

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in {"strong", "b", "em", "i", "ins", "u", "strike", "s", "del", "span"}:
            if len(self._style_stack) > 1:
                self._style_stack.pop()
            return
        if tag == "p":
            self._append_paragraph_break()

    def handle_data(self, data: str):
        self._append_text(data)

    def _append_paragraph_break(self):
        current_text = self.get_text()
        if not current_text:
            return
        if current_text.endswith("\n\n"):
            return
        if current_text.endswith("\n"):
            self._append_text("\n")
        else:
            self._append_text("\n\n")

    def _append_text(self, text: str):
        if not text:
            return
        normalized = text.replace("\xa0", " ")
        if not normalized:
            return
        style = self._style_stack[-1].copy()
        if self.fragments and self.fragments[-1][1] == style:
            prev_text, prev_style = self.fragments[-1]
            self.fragments[-1] = (prev_text + normalized, prev_style)
            return
        self.fragments.append((normalized, style))

    def trim_trailing_breaks(self):
        while self.fragments:
            text, style = self.fragments[-1]
            trimmed = text.rstrip("\n")
            if trimmed == text:
                break
            if trimmed:
                self.fragments[-1] = (trimmed, style)
                break
            self.fragments.pop()

    def get_text(self) -> str:
        return "".join(text for text, _ in self.fragments)


# =====================================================
# FIXED REPORT TEMPLATE (LEGACY reports-table compatible)
# =====================================================
REPORT_TEMPLATE_COLUMNS = [
    "application_number",
    "batch_code",
    "niyamtek_user",
    "client_code",
    "company_name",
    "loan_account_number",
    "trust_number",
    "assignment_agreement_date",
    "ao_name",
    "branch",
    "state",
    "region",
    "property_address",
    "borrower_name",
    "borrower_address",
    "borrower_address_also_at",
    "co_borrower_name_1",
    "co_borrower_address_1",
    "co_borrower_address_1_also_at",
    "co_borrower_name_2",
    "co_borrower_address_2",
    "co_borrower_address_2_also_at",
    "co_borrower_name_3",
    "co_borrower_address_3",
    "co_borrower_address_3_also_at",
    "co_borrower_name_4",
    "co_borrower_address_4",
    "co_borrower_address_4_also_at",
    "co_borrower_name_5",
    "co_borrower_address_5",
    "co_borrower_address_5_also_at",
    "co_borrower_name_6",
    "co_borrower_address_6",
    "property_description",
    "guarantor_1_name",
    "guarantor_1_address",
    "guarantor_2_name",
    "guarantor_2_address",
    "date_of_npa",
    "dpd_as_on_notice",
    "disbursement_type",
    "disbursal_date",
    "disbursal_amount",
    "loan_agreement_date",
    "loan_amount",
    "loan_amount_words",
    "future_principal",
    "principal_outstanding",
    "instalment_overdue_amount",
    "interest_on_termination",
    "late_payment_penalty",
    "cheque_bounce_charges",
    "other_amount",
    "foreclosure_charges",
    "total_outstanding",
    "fcl_as_on_date",
    "total_outstanding_words",
    "sec_13_2_notice_date",   
    "notice_13_2_amount",
    "notice_dispatch_date",
    "notice_pasting_date",
    "delivery_status",
    "delivered_address",
    "undelivered_address",
    "total_address",
    "publication_date_13_2",
    "publication_english_13_2",
    "publication_local_13_2",
]

REPORT_EXPORT_HEADERS = {
    "application_number": "Application No.",
    "batch_code": "Batch Code",
    "niyamtek_user": "NIYAMTEK USER ID OR NAME",
    "client_code": "Client ID (CODE)",
    "company_name": "Company Name",
    "loan_account_number": "LOAN ACCOUNT NO.",
    "loan_amount_words": "Loan Amount in Words",
    "trust_number": "Trust Number",
    "assignment_agreement_date": "Assignment agreement Date",
    "ao_name": "AO NAME",
    "branch": "BRANCH",
    "state": "STATE",
    "region": "Region",
    "property_address": "Address of Mortgaged Property",
    "borrower_name": "NAME OF BORROWER",
    "borrower_address": "Borrower Address",
    "borrower_address_also_at": "Borrower Address_(Also At)",
    "co_borrower_name_1": "Co-Borrower Name_1",
    "co_borrower_address_1": "Co-Borrower Address_1",
    "co_borrower_address_1_also_at": "Co-Borrower Address_1 (Also At)",
    "co_borrower_name_2": "Co-Borrower Name_2",
    "co_borrower_address_2": "Co-Borrower Address_2",
    "co_borrower_address_2_also_at": "Co-Borrower Address_2 (Also At)",
    "co_borrower_name_3": "Co-Borrower Name_3",
    "co_borrower_address_3": "Co-Borrower Address_3",
    "co_borrower_address_3_also_at": "Co-Borrower Address_3 (Also At)",
    "co_borrower_name_4": "Co-Borrower Name_4",
    "co_borrower_address_4": "Co-Borrower Address_4",
    "co_borrower_address_4_also_at": "Co-Borrower Address_4 (Also At)",
    "co_borrower_name_5": "Co-Borrower Name_5",
    "co_borrower_address_5": "Co-Borrower Address_5",
    "co_borrower_address_5_also_at": "Co-Borrower Address_5 (Also At)",
    "co_borrower_name_6": "Co-Borrower Name_6",
    "co_borrower_address_6": "Co-Borrower Address_6",
    "property_description": "Property Description",
    "guarantor_1_name": "Guarantor Name_1",
    "guarantor_1_address": "Guarantor Address_1",
    "guarantor_2_name": "Guarantor Name_2",
    "guarantor_2_address": "Guarantor Address_2",
    "date_of_npa": "Date of NPA",
    "dpd_as_on_notice": "DPD as on Notice Issuance Date",
    "disbursement_type": "Disbursement Type (Loan / OD / CC / HL / BLG)",
    "disbursal_date": "Disbursal Date",
    "disbursal_amount": "Disbursal Amount",
    "loan_agreement_date": "Loan Agreement Date",
    "loan_amount": "Loan Amount",
    "future_principal": "Future Principle",
    "principal_outstanding": "Principal Outstanding",
    "instalment_overdue_amount": "Instalment_overdue_amount",
    "interest_on_termination": "Interest on Termination",
    "late_payment_penalty": "Late Payment Penalty",
    "cheque_bounce_charges": "Cheque Bounce Charges (Including Others)",
    "other_amount": "Other Amount",
    "foreclosure_charges": "Foreclosure Charges",
    "total_outstanding": "Total Outstanding",
    "fcl_as_on_date": "FCL (As on Date)",
    "total_outstanding_words": "Total Outstanding in words",
    "sec_13_2_notice_date": "13(2) Demand Notice (date)",
    "notice_13_2_amount": "13 (2) NOTICE AMT",
    "notice_dispatch_date": "Dispatch Date",
    "notice_pasting_date": "Pasting Date (optional)",
    "delivery_status": "Delivered /undelivered with Date",
    "delivered_address": "Delivered address",
    "undelivered_address": "Undelivered address",
    "total_address": "Total address",
    "publication_date_13_2": "13(2) Date of Publication",
    "publication_english_13_2": "Publication Details : (Names of News Papers) & Language Name : (English)",
    "publication_local_13_2": "Publication Details : (Names of News Papers) & Vernacular Language Name : (Tamil,Hindi,malayalam,etc...)",
}

LEGACY_TO_MODEL_FIELD = {
    "application_number": "application_number",
    "loan_account_number": "loan_account_number",
    "borrower_name": "borrower_name",
    "location": "location",
    "arc_name": "arc_name",
    "borrower_address": "borrower_address",
    "borrower_address_also_at": "borrower_address_also_at",
    "co_borrower_name_1": "co_borrower_1_name",
    "co_borrower_address_1": "co_borrower_1_address",
    "co_borrower_address_1_also_at": "co_borrower_1_address_also_at",
    "co_borrower_name_2": "co_borrower_2_name",
    "co_borrower_address_2": "co_borrower_2_address",
    "co_borrower_address_2_also_at": "co_borrower_2_address_also_at",
    "co_borrower_name_3": "co_borrower_3_name",
    "co_borrower_address_3": "co_borrower_3_address",
    "co_borrower_address_3_also_at": "co_borrower_3_address_also_at",
    "co_borrower_name_4": "co_borrower_4_name",
    "co_borrower_address_4": "co_borrower_4_address",
    "co_borrower_address_4_also_at": "co_borrower_4_address_also_at",
    "co_borrower_name_5": "co_borrower_5_name",
    "co_borrower_address_5": "co_borrower_5_address",
    "co_borrower_address_5_also_at": "co_borrower_5_address_also_at",
    "co_borrower_name_6": "co_borrower_6_name",
    "co_borrower_address_6": "co_borrower_6_address",
    "property_address": "property_address",
    "property_description": "property_description",
    "description_of_schedule_property": "property_description",
    "date_of_npa": "date_of_npa",
    "dpd_as_on_notice": "dpd_as_on_notice",
    "sec_13_2_notice_date": "sec_13_2_notice_date",
    "disbursal_date": "disbursal_date",
    "disbursal_amount": "disbursal_amount",
    "loan_agreement_date": "loan_agreement_date",
    "loan_amount": "loan_amount",
    "loan_amount_words": "loan_amount_words",
    "future_principal": "future_principal",
    "principal_outstanding": "principal_outstanding",
    "instalment_overdue_amount": "instalment_overdue_amount",
    "interest_on_termination": "interest_on_termination",
    "late_payment_penalty": "late_payment_penalty",
    "cheque_bounce_charges": "cheque_bounce_charges",
    "other_amount": "other_amount",
    "foreclosure_charges": "foreclosure_charges",
    "total_outstanding": "total_outstanding",
    "as_on_date": "as_on_date",
    "total_outstanding_words": "total_outstanding_words",
}


class ReportService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = ReportRepository(db)
        self.report_fields = [
            {
                "field": field_name,
                "model_field": LEGACY_TO_MODEL_FIELD.get(field_name, field_name),
                "excel_header": REPORT_EXPORT_HEADERS.get(field_name, field_name),
            }
            for field_name in REPORT_TEMPLATE_COLUMNS
        ]

    # =====================================================
    # HELPER → NUMBER TO WORDS
    # =====================================================
    def _number_to_words(self, amount: Optional[int]) -> Optional[str]:
        if not amount:
            return None
        try:
            return num2words(amount, lang="en_IN").title()
        except Exception:
            return None

    def _validate_checklist_before_report_generation(self, application_number: str):
        checklist_rows = (
            self.db.query(ApplicationChecklist)
            .filter(
                ApplicationChecklist.application_number == application_number,
                *live_filter(ApplicationChecklist),
            )
            .all()
        )
        if not checklist_rows:
            raise ValueError("Checklist not found for the application number")

        if any((row.rerun_validation or 0) == 1 for row in checklist_rows):
            raise ValueError("Rerun validation to generate report.")

        mismatch_count = sum(
            1
            for row in checklist_rows
            if row.match_status == "MISMATCH"
            and not (row.pair_code == "SL_LA" and row.attribute_code == "date")
        )
        if mismatch_count > 0:
            raise ValueError("Report generation blocked: checklist has mismatch.")

    # =====================================================
    # GET EXISTING REPORT (NO GENERATION)
    # =====================================================
    def get_report(self, application_number: str):

        report = self.repo.get_report(application_number)

        if not report:
            return None

        if report.total_outstanding and not report.total_outstanding_words:
            report.total_outstanding_words = self._number_to_words(report.total_outstanding)

        self.db.commit()
        self.db.refresh(report)

        return self._model_to_dict(report)

    # =====================================================
    # GENERATE REPORT (EXPLICIT CALL ONLY)
    # =====================================================
    def generate_report(self, application_number: str):
        self._validate_checklist_before_report_generation(application_number)
        report = self.repo.generate_report(application_number)
        if not report:
            return None

        # Once the report has been regenerated successfully, clear the rerun flag.
        self.repo.mark_rerun_report(application_number, 0)

        if report.total_outstanding and not report.total_outstanding_words:
            report.total_outstanding_words = self._number_to_words(report.total_outstanding)

        self.db.commit()
        self.db.refresh(report)
        return self._model_to_dict(report)

    # =====================================================
    # CREATE REPORT
    # =====================================================
    def create_report(self, application_number: str, data: Dict, audit_user: AuditUser | None = None):
        report = self.repo.create_report(application_number, data, audit_user=audit_user)
        return self._model_to_dict(report)

    # =====================================================
    # UPDATE REPORT (Manual Edit)
    # =====================================================
    def update_report(
        self,
        application_number: str,
        update_data: Dict,
        admin_overwrite: bool = False,
        audit_user: AuditUser | None = None,
    ):
        report = self.repo.update_report(application_number, update_data, audit_user=audit_user)
        return self._model_to_dict(report)

    # =====================================================
    # BULK DOWNLOAD
    # =====================================================
    def bulk_download_reports(self, application_numbers: List[str]):

        reports = []
        blocked_apps = []
        missing_apps = []

        for app_no in application_numbers:
            report = self.repo.get_report(app_no)
            if not report:
                missing_apps.append(app_no)
                continue
            if (report.rerun_report or 0) == 1:
                blocked_apps.append(app_no)
                continue
            reports.append(self._model_to_dict(report))

        if blocked_apps:
            raise ValueError(
                "Report download blocked. Report regeneration pending for application(s): "
                + ", ".join(blocked_apps)
            )
        if missing_apps:
            raise ValueError(
                "Report not found for application(s): " + ", ".join(missing_apps)
            )

        if not reports:
            raise Exception("No reports found")
            

        return self._export_to_excel(
            reports,
            "bulk_extracted_reports.xlsx"
        )

    # =====================================================
    # MODEL → SAFE DICT
    # =====================================================
    def _model_to_dict(self, report: SarfaesiMaster):

        data = {}
        resolved_client_code = None
        client_name = None
        report_application = getattr(report, "application", None)
        if report_application is not None:
            client_name = getattr(report_application, "client_name", None)
        if not client_name:
            client_name = getattr(report, "company_name", None) or getattr(report, "arc_name", None)
        if client_name:
            live_client = (
                self.db.query(Client)
                .filter(Client.client_name == client_name, *live_filter(Client))
                .first()
            )
            if live_client:
                resolved_client_code = live_client.client_code

        for field_config in self.report_fields:
            col = field_config.get("field")
            if not col:
                continue
            model_field = field_config.get("model_field") or col
            value = getattr(report, model_field, None)
            if col == "client_code" and resolved_client_code:
                value = resolved_client_code
            column = report.__table__.columns.get(model_field)
            column_type = str(column.type).upper() if column is not None else ""

            if col == "total_outstanding_words" and (value is None or value == ""):
                value = self._number_to_words(getattr(report, "total_outstanding", None))

            if value == "":
                value = None

            if value is None:
                data[col] = None
            elif "DATE" in column_type or "DATETIME" in column_type:
                if isinstance(value, str):
                    parsed = parse_datetime(value)
                    data[col] = parsed if parsed is not None else None
                else:
                    data[col] = value
            else:
                data[col] = value

        data["id"] = getattr(report, "id", None)
        data["status"] = getattr(report, "status", None) or "Completed"
        created_at = getattr(report, "created_at", None)
        if isinstance(created_at, str):
            parsed_created_at = parse_datetime(created_at)
            data["created_at"] = parsed_created_at
        else:
            data["created_at"] = created_at

        return data

    def _to_excel_fragments(self, value):
        if value is None:
            return [], ""

        if isinstance(value, datetime):
            return [(value.strftime("%d-%m-%Y"), {"bold": False, "italic": False, "underline": False, "strike": False})], value.strftime("%d-%m-%Y")

        if isinstance(value, date):
            text_value = value.strftime("%d-%m-%Y")
            return [(text_value, {"bold": False, "italic": False, "underline": False, "strike": False})], text_value

        if isinstance(value, str):
            parsed_value = parse_datetime(value)
            if parsed_value is not None:
                text_value = parsed_value.strftime("%d-%m-%Y")
                return [(text_value, {"bold": False, "italic": False, "underline": False, "strike": False})], text_value

        text_value = str(value)
        if not text_value:
            return [], ""
        if not _HTML_TAG_RE.search(text_value):
            return [(text_value, {"bold": False, "italic": False, "underline": False, "strike": False})], text_value

        parser = _ReportHtmlToExcelParser()
        parser.feed(text_value)
        parser.close()
        parser.trim_trailing_breaks()

        display_text = parser.get_text()
        if not display_text:
            return [], ""

        return parser.fragments, display_text

    def _get_xlsxwriter_format(self, workbook, cache: dict, *, bold=False, italic=False, underline=False, strike=False, wrap=False, valign=None):
        key = (bold, italic, underline, strike, wrap, valign)
        if key in cache:
            return cache[key]
        fmt = workbook.add_format({
            "bold": bold,
            "italic": italic,
            "underline": underline,
            "font_strikeout": strike,
            "text_wrap": wrap,
            **({"valign": valign} if valign else {}),
        })
        cache[key] = fmt
        return fmt

    # =====================================================
    # EXCEL EXPORT ENGINE (Template Enforced)
    # =====================================================
    def _export_to_excel(self, report_dicts: list[dict], filename: str):
        output = BytesIO()
        workbook = pd.ExcelWriter(output, engine="xlsxwriter")
        worksheet = workbook.book.add_worksheet("Report")
        workbook.sheets["Report"] = worksheet
        default_row_height = 15
        visible_fields = [
            field_config
            for field_config in self.report_fields
            if str(field_config.get("excel_header") or "").strip()
        ]

        format_cache = {}
        header_format = self._get_xlsxwriter_format(workbook.book, format_cache, bold=True)
        plain_top_format = self._get_xlsxwriter_format(workbook.book, format_cache, wrap=False, valign="top")
        worksheet.set_default_row(default_row_height)

        display_text_map: dict[tuple[int, int], str] = {}

        for col_idx, field_config in enumerate(visible_fields):
            col_name = field_config.get("field")
            header = field_config.get("excel_header", col_name)
            worksheet.write(0, col_idx, header, header_format)
            display_text_map[(0, col_idx)] = str(header)
        worksheet.set_row(0, default_row_height)

        for row_idx, report_dict in enumerate(report_dicts, start=1):
            worksheet.set_row(row_idx, default_row_height)
            for col_idx, field_config in enumerate(visible_fields):
                col_name = field_config.get("field")
                raw_value = report_dict.get(col_name, "")
                fragments, display_text = self._to_excel_fragments(raw_value)
                display_text_map[(row_idx, col_idx)] = display_text

                if not fragments:
                    worksheet.write(row_idx, col_idx, "")
                    continue

                has_style = any(
                    style["bold"] or style["italic"] or style["underline"] or style["strike"]
                    for _, style in fragments
                )
                if has_style:
                    rich_parts = []
                    for text, style in fragments:
                        if not text:
                            continue
                        if style["bold"] or style["italic"] or style["underline"] or style["strike"]:
                            rich_parts.append(
                                self._get_xlsxwriter_format(
                                    workbook.book,
                                    format_cache,
                                    bold=style["bold"],
                                    italic=style["italic"],
                                    underline=style["underline"],
                                    strike=style["strike"],
                                )
                            )
                        rich_parts.append(text)

                    if len(rich_parts) >= 3:
                        worksheet.write_rich_string(row_idx, col_idx, *rich_parts, plain_top_format)
                    else:
                        worksheet.write(row_idx, col_idx, display_text, plain_top_format)
                else:
                    worksheet.write(row_idx, col_idx, display_text, plain_top_format)

        for col_idx, _ in enumerate(visible_fields):
            max_length = max(
                len(display_text_map.get((row_idx, col_idx), ""))
                for row_idx in range(0, len(report_dicts) + 1)
            )
            worksheet.set_column(col_idx, col_idx, min(max_length + 3, 40))

        workbook.close()

        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    # =====================================================
    # SNAPSHOT
    # =====================================================
    def save_report_snapshot(self, application_number: str):
        report = self.repo.get_report(application_number)
        return self._model_to_dict(report) if report else None
