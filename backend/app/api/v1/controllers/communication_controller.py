import os
import yaml
import asyncio
import base64
import mimetypes
import re
import html
import tempfile
import io
import zipfile
import copy
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from bs4 import BeautifulSoup
from jinja2 import Template

from docx import Document

from app.services.word_service import WordService
from app.services.communication_service import (
    CommunicationService,
    build_placeholder_map,
    cleanup_unresolved_brace_placeholders,
    normalize_placeholder_token,
    sanitize_placeholder_value,
)
from app.services.pdf_service import PDFService
from app.gateways.storage_gateway import get_storage_gateway
from app.api.v1.dependencies.auth import AuditUser
from app.schemas.communication_schema import (
    MailTemplateRequest,
    CommunicationCreate,
    BulkNoticeDownloadRequest,
)
from app.core.settings import settings
from app.services.placeholder_mapping_service import (
    get_notice_party_mappings,
    get_notice_template_aliases,
)

from app.db.models.client_models import MasterTemplate, Client, AOInformation
from app.db.models.application import Application


# --------------------------------------------------
# Load YAML Config (Header / Footer / Seal Only)
# --------------------------------------------------
config = {}
try:
    yaml_path = os.path.join(
        settings.BASE_DIR,
        "app",
        "metatable",
        "mail_templates.yaml"
    )
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
except Exception:
    config = {}

# Thread pool for Word/LibreOffice PDF generation (I/O + subprocess bound, not CPU bound)
pdf_executor = ThreadPoolExecutor(max_workers=8)


class CommunicationController:

    def __init__(self, db: Session):
        self.db = db
        self.service = CommunicationService(db)
        self.s3 = get_storage_gateway()

    def _extract_base_font_family(self, html_text: str) -> str | None:
        if not html_text:
            return None

        soup = BeautifulSoup(html_text, "html.parser")

        def _clean(value: str | None) -> str | None:
            if not value:
                return None
            cleaned = value.strip().rstrip(";")
            return cleaned or None

        for style_tag in soup.find_all("style"):
            style_text = style_tag.get_text(" ", strip=False) or ""
            match = re.search(r"body\s*\{[^}]*font-family\s*:\s*([^;}\n]+)", style_text, re.I | re.S)
            if match:
                font_family = _clean(match.group(1))
                if font_family:
                    return font_family

        for tag in soup.find_all(True):
            style_text = tag.get("style", "") or ""
            if not style_text:
                continue
            match = re.search(r"font-family\s*:\s*([^;]+)", style_text, re.I)
            if match:
                font_family = _clean(match.group(1))
                if font_family:
                    return font_family

        for selector in ("body", "html"):
            tag = soup.find(selector)
            if not tag:
                continue
            style_text = tag.get("style", "") or ""
            match = re.search(r"font-family\s*:\s*([^;]+)", style_text, re.I)
            if match:
                font_family = _clean(match.group(1))
                if font_family:
                    return font_family

        return None

    def _strip_font_related_styles(self, style_text: str | None) -> str:
        if not style_text:
            return ""

        cleaned = style_text
        for prop in (
            "font",
            "font-family",
            "font-size",
            "font-style",
            "font-weight",
            "font-variant",
            "font-stretch",
            "line-height",
            "letter-spacing",
            "text-transform",
        ):
            cleaned = re.sub(rf"(?i)\s*{prop}\s*:\s*[^;]+;?", "", cleaned)

        cleaned = cleaned.strip(" ;")
        return cleaned

    def _strip_font_related_styles_from_html(self, html_text: str) -> str:
        if not html_text:
            return html_text

        soup = BeautifulSoup(html_text, "html.parser")
        for node in soup.find_all(True):
            style_text = node.get("style")
            if not style_text:
                continue

            cleaned = self._strip_font_related_styles(style_text)
            if cleaned:
                node["style"] = cleaned
            else:
                node.attrs.pop("style", None)

        return str(soup)

    def _extract_font_family_from_node(self, node) -> str | None:
        if node is None:
            return None

        def _clean(value: str | None) -> str | None:
            if not value:
                return None
            cleaned = value.strip().rstrip(";")
            return cleaned or None

        search_roots = [node]
        if hasattr(node, "find_all"):
            search_roots.extend(list(node.find_all(True)))

        for current in search_roots:
            style_text = (current.get("style") or "") if hasattr(current, "get") else ""
            if not style_text:
                continue
            match = re.search(r"font-family\s*:\s*([^;]+)", style_text, re.I)
            if match:
                font_family = _clean(match.group(1))
                if font_family:
                    return font_family

        return None

    def _latest_template(self, query):
        return query.order_by(MasterTemplate.version.desc(), MasterTemplate.id.desc()).first()

    def _resolve_master_template(self, client_id: int, template_identifier: str):
        """
        Resolve a master template from any of the common identifiers the UI might send:
        - template_code
        - template_type_id
        - template_type name
        """
        query = self.db.query(MasterTemplate).filter(
            MasterTemplate.client_id == client_id,
            MasterTemplate.is_deleted == False,
            MasterTemplate.is_active == True,
        )

        template = self._latest_template(
            query.filter(MasterTemplate.template_code == template_identifier)
        )
        if template:
            return template

        if str(template_identifier).isdigit():
            template = self._latest_template(
                query.filter(MasterTemplate.template_type_id == int(template_identifier))
            )
            if template:
                return template

        return self._latest_template(
            query.filter(
                MasterTemplate.template_type_rel.has(template_type=template_identifier)
            )
        )

    def _resolve_master_template_any(self, template_identifier: str):
        query = self.db.query(MasterTemplate).filter(
            MasterTemplate.is_deleted == False,
            MasterTemplate.is_active == True,
        )

        template = self._latest_template(
            query.filter(MasterTemplate.template_code == template_identifier)
        )
        if template:
            return template

        if str(template_identifier).isdigit():
            template = self._latest_template(
                query.filter(MasterTemplate.template_type_id == int(template_identifier))
            )
            if template:
                return template

        return self._latest_template(
            query.filter(
                MasterTemplate.template_type_rel.has(template_type=template_identifier)
            )
        )

    def _resolve_master_template_by_id(self, template_id: int):
        return self._latest_template(
            self.db.query(MasterTemplate).filter(
                MasterTemplate.id == template_id,
                MasterTemplate.is_deleted == False,
                MasterTemplate.is_active == True,
            )
        )

    def _request_value(self, request, key: str, default=None):
        if isinstance(request, dict):
            return request.get(key, default)
        return getattr(request, key, default)

    @staticmethod
    def _normalize_client_code_token(value: str | None) -> str:
        token = "".join(
            ch if ch.isalnum() else "-"
            for ch in (value or "").strip().upper()
        )
        while "--" in token:
            token = token.replace("--", "-")
        return token.strip("-")

    def _resolve_client_for_application(self, application: Application):
        from sqlalchemy import func, or_
        from app.db.versioning import live_filter

        raw_client_value = str(getattr(application, "client_name", "") or "").strip()
        business_code = str(getattr(application, "business_code", "") or "").strip()

        candidates = []
        if raw_client_value:
            candidates.append(raw_client_value)
        if "-" in business_code:
            candidates.append(business_code.rsplit("-", 1)[0].strip())

        seen = set()
        normalized_candidates = []
        for candidate in candidates:
            key = candidate.lower()
            if candidate and key not in seen:
                seen.add(key)
                normalized_candidates.append(candidate)

        for candidate in normalized_candidates:
            lowered = candidate.lower()
            client = self.db.query(Client).filter(
                or_(
                    func.lower(Client.client_name) == lowered,
                    func.lower(Client.client_code) == lowered,
                ),
                *live_filter(Client),
            ).first()
            if client:
                return client

            client = self.db.query(Client).filter(
                or_(
                    func.lower(Client.client_name) == lowered,
                    func.lower(Client.client_code) == lowered,
                ),
                Client.is_deleted == False,
            ).order_by(Client.version.desc(), Client.id.desc()).first()
            if client:
                return client

        if business_code and "-" in business_code:
            business_prefix = self._normalize_client_code_token(
                business_code.rsplit("-", 1)[0]
            )
            clients = self.db.query(Client).filter(
                Client.is_deleted == False,
            ).order_by(Client.version.desc(), Client.id.desc()).all()
            for client in clients:
                if self._normalize_client_code_token(client.client_code) == business_prefix:
                    return client

        return None

    def _safe_filename_part(self, value: str | None, fallback: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
        cleaned = cleaned.strip("._-")
        return cleaned or fallback

    def _notice_download_filename(
        self,
        application: Application | None,
        notice_type: str | None,
        extension: str,
    ) -> str:
        loan_account_number = getattr(application, "loan_account_number", None)
        borrower_name = getattr(application, "loan_requester_name", None)
        application_number = getattr(application, "business_code", None)

        account_part = self._safe_filename_part(
            loan_account_number or application_number,
            "account",
        )
        borrower_part = self._safe_filename_part(borrower_name, "borrower")
        notice_part = self._safe_filename_part(notice_type, "notice")
        ext = self._safe_filename_part(extension, "pdf").lstrip(".")
        return f"{account_part}-{borrower_part}-{notice_part}.{ext}"

    def _template_bytes_from_storage_ref(self, storage_ref: str | None) -> bytes:
        if not storage_ref:
            raise HTTPException(status_code=500, detail="Template file missing")

        storage_ref = str(storage_ref).strip()
        if not storage_ref:
            raise HTTPException(status_code=500, detail="Template file missing")

        try:
            return self.s3.get_file_bytes_by_key(storage_ref)
        except Exception:
            local_path = os.path.join(settings.BASE_DIR, "app", storage_ref)
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    return f.read()
            raise HTTPException(status_code=500, detail="Template file missing on server")

    # Notice templates authored in the frontend editor (CreateNotice.tsx) bake
    # a hardcoded <footer><img style="width:69px; height:57px" /></footer>
    # into the saved template HTML - a leftover placeholder size, not a real
    # letterhead footer band. The header gets a proper full page-width box
    # (809px, matching the A4 print width) but the footer never did, so it
    # renders as a tiny crushed image on every notice. Normalize it here at
    # render time so already-saved templates are fixed too, not just ones
    # created after a frontend redeploy.
    _FOOTER_IMG_STYLE_RE = re.compile(
        r"(<footer\b[^>]*>.*?<img\b[^>]*\bstyle\s*=\s*\")width:\s*69px;\s*height:\s*57px(\")",
        re.IGNORECASE | re.DOTALL,
    )

    def _normalize_letterhead_footer_image(self, html_text: str) -> str:
        if not html_text or "<footer" not in html_text.lower():
            return html_text
        return self._FOOTER_IMG_STYLE_RE.sub(r"\1width:809px; height:57px\2", html_text)

    def _load_docx_template_from_storage(self, storage_ref: str | None) -> str:
        template_bytes = self._template_bytes_from_storage_ref(storage_ref)
        suffix = os.path.splitext(str(storage_ref or ""))[1] or ".docx"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            tmp.write(template_bytes)
            tmp.flush()
            return tmp.name
        finally:
            tmp.close()

    def _cleanup_temp_file(self, path: str | None) -> None:
        if not path:
            return
        try:
            os.remove(path)
        except Exception:
            pass

    async def _streaming_response_to_bytes(self, response: StreamingResponse) -> bytes:
        payload = bytearray()
        async for chunk in response.body_iterator:
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            payload.extend(chunk)
        return bytes(payload)

    async def _record_download_communication(
        self,
        *,
        application_number: str,
        template_name: str,
        subject: str,
        content: str = "",
        pdf_buffer=None,
        request: dict | None = None,
        structured_components: dict | None = None,
        output_format: str = "pdf",
        audit_user: AuditUser | None = None,
    ):
        payload = {
            "application_number": application_number,
            "type": "download",
            "status": "downloaded",
            "template_name": template_name,
            "subject": subject,
            "content": content,
            "recipient": (request or {}).get("recipient"),
            "sender": (request or {}).get("sender"),
            "meta_data": {
                "source": "download",
                "output_format": output_format,
            },
        }
        if audit_user is not None:
            payload["_audit_user"] = audit_user
        await self.service.save_communication(payload, pdf_bytes=pdf_buffer)

    def _resolve_ao_information(self, client_id: int, request):
        from sqlalchemy import func
        from app.db.versioning import OPEN_END_DATE

        query = self.db.query(AOInformation).filter(
            AOInformation.client_id == client_id,
            AOInformation.is_deleted == False,
            AOInformation.is_active == True,
            AOInformation.end_date == OPEN_END_DATE,
        )

        ao_code = str(self._request_value(request, "ao_code", "") or "").strip()
        if ao_code:
            ao = query.filter(func.lower(AOInformation.ao_code) == ao_code.lower()).first()
            if ao:
                return ao

            fallback = self.db.query(AOInformation).filter(
                AOInformation.ao_code == ao_code,
                AOInformation.is_deleted == False,
                AOInformation.is_active == True,
                AOInformation.end_date == OPEN_END_DATE,
            ).first()
            if fallback:
                return fallback

        ao_name = str(self._request_value(request, "ao_name", "") or "").strip()
        if ao_name:
            ao = query.filter(func.lower(AOInformation.ao_name) == ao_name.lower()).first()
            if ao:
                return ao

            fallback = self.db.query(AOInformation).filter(
                func.lower(AOInformation.ao_name) == ao_name.lower(),
                AOInformation.is_deleted == False,
                AOInformation.is_active == True,
                AOInformation.end_date == OPEN_END_DATE,
            ).first()
            if fallback:
                return fallback

        return query.first()

    def _extract_s3_key(self, file_url: str | None) -> str | None:
        if not file_url:
            return None

        value = str(file_url).strip()
        if not value:
            return None

        # Local-storage references (STORAGE_PROVIDER=local) point at our own
        # /files route rather than S3 - pull the key back out of that first.
        files_route_marker = "/api/v1/files/"
        if value.startswith("local://"):
            return value[len("local://"):].split("?", 1)[0]
        if files_route_marker in value:
            return value.split(files_route_marker, 1)[-1].split("?", 1)[0]

        base_url = (settings.S3_BASE_URL or "").rstrip("/")
        if base_url and value.startswith(base_url):
            return value[len(base_url):].lstrip("/").split("?", 1)[0]

        if value.startswith("s3://"):
            without_scheme = value[len("s3://"):]
            bucket_prefix = f"{settings.S3_BUCKET_NAME}/" if settings.S3_BUCKET_NAME else ""
            if bucket_prefix and without_scheme.startswith(bucket_prefix):
                return without_scheme[len(bucket_prefix):].split("?", 1)[0]
            return without_scheme.split("/", 1)[-1].split("?", 1)[0]

        if value.startswith("http://") or value.startswith("https://"):
            from urllib.parse import urlparse, unquote

            parsed = urlparse(value)
            path = unquote(parsed.path.lstrip("/"))
            bucket_prefix = f"{settings.S3_BUCKET_NAME}/" if settings.S3_BUCKET_NAME else ""
            if bucket_prefix and path.startswith(bucket_prefix):
                path = path[len(bucket_prefix):]
            return path.split("?", 1)[0]

        return value.split("?", 1)[0]

    def _looks_like_base64_image(self, value: str | None) -> bool:
        if not value:
            return False

        text = str(value).strip()
        if not text or text.startswith("data:"):
            return False

        # Legacy AO records may store the image payload directly instead of an
        # S3 path. Treat those as an inline PNG so bulk and single downloads
        # render the signature the same way.
        if any(sep in text for sep in ("/", "\\", "http://", "https://", "s3://")):
            return False

        if len(text) < 80:
            return False

        import re

        return bool(re.fullmatch(r"[A-Za-z0-9+/=\s]+", text))

    def _resolve_ao_signature(self, ao):
        signature_path = getattr(ao, "signature_path", None)
        if not signature_path:
            return None, None, None

        signature_path = str(signature_path).strip()
        if not signature_path:
            return None, None, None

        if signature_path.startswith("data:"):
            safe_signature_path = html.escape(signature_path, quote=True)
            signature_html = (
                f'<img src="{safe_signature_path}" '
                'alt="AO Signature" '
                'style="width:200px; height:auto; display:inline-block; vertical-align:middle;" />'
            )
            return signature_path, signature_html, signature_path

        if self._looks_like_base64_image(signature_path):
            data_uri = f"data:image/png;base64,{signature_path}"
            safe_data_uri = html.escape(data_uri, quote=True)
            signature_html = (
                f'<img src="{safe_data_uri}" '
                'alt="AO Signature" '
                'style="width:200px; height:auto; display:inline-block; vertical-align:middle;" />'
            )
            return data_uri, signature_html, data_uri

        s3_key = self._extract_s3_key(signature_path)
        if not s3_key:
            return None, None, signature_path

        try:
            file_bytes = self.s3.get_file_bytes_by_key(s3_key)
            encoded = base64.b64encode(file_bytes).decode("utf-8")
        except Exception:
            return None, None, signature_path

        content_type, _ = mimetypes.guess_type(s3_key)
        if not content_type:
            content_type = "image/png"

        data_uri = f"data:{content_type};base64,{encoded}"
        safe_data_uri = html.escape(data_uri, quote=True)
        signature_html = (
            f'<img src="{safe_data_uri}" '
            'alt="AO Signature" '
            'style="width:200px; height:auto; display:inline-block; vertical-align:middle;" />'
        )
        return data_uri, signature_html, signature_path

    def _apply_notice_layout_tweaks(self, html_text: str) -> str:
        if not html_text:
            return html_text

        notice_markers = (
            "NOTICE OF DEMAND UNDER SECTION 13(2)",
            "SUB:",
            "Yours faithfully",
            "Borrower",
        )
        if not any(marker in html_text for marker in notice_markers):
            return html_text

        soup = BeautifulSoup(html_text, "html.parser")
        wrapper = soup.select_one(".docx-root") or soup.body or soup

        wrapper_classes = list(wrapper.get("class") or [])
        if "notice-layout" not in wrapper_classes:
            wrapper_classes.append("notice-layout")
            wrapper["class"] = wrapper_classes

        style = soup.new_tag("style")
        style.string = """
/* Page-break behaviour is decided centrally in
   pdf_service._prevent_visible_table_page_breaks() / _inject_print_styles:
   a table with real visible cell borders is wrapped in
   <div class="js-avoid-split"> and kept whole, everything else breaks
   freely. This template no longer overrides that - it only carries the
   visual tweaks below. */
.notice-layout table.party-table,
.notice-layout table.notice-party-block,
.notice-layout table.notice-subject-block,
.notice-layout table.notice-signature-block {
  table-layout: fixed !important;
}

.notice-layout table.party-table td,
.notice-layout table.notice-party-block td,
.notice-layout table.notice-subject-block td,
.notice-layout table.notice-signature-block td {
  padding-top: 3px !important;
  padding-bottom: 3px !important;
}

.notice-layout table.party-table p,
.notice-layout table.notice-party-block p,
.notice-layout table.notice-subject-block p,
.notice-layout table.notice-signature-block p {
  margin: 0 !important;
  line-height: 1.05 !important;
}

.notice-layout table.notice-subject-block td:first-child {
  white-space: nowrap !important;
  width: 56px !important;
}

.notice-layout table.notice-signature-block img {
  margin-left: auto !important;
#   display: block !important;
}
""".strip()

        (soup.head or wrapper).append(style)

        for table in soup.find_all("table"):
            text = table.get_text(" ", strip=True)
            classes = list(table.get("class") or [])
            if "SUB:" in text and "notice-subject-block" not in classes:
                classes.append("notice-subject-block")
                table["class"] = classes
            elif "Yours faithfully" in text and "notice-signature-block" not in classes:
                classes.append("notice-signature-block")
                table["class"] = classes

        for node in soup.find_all(True):
            style = node.get("style")
            if not style:
                continue
            if (
                "break-after:page" in style
                or "page-break-after:always" in style
                or "break-before:page" in style
                or "page-break-before:always" in style
            ):
                cleaned = re.sub(r"(?i)\s*page-break-after\s*:\s*always\s*;?", "", style)
                cleaned = re.sub(r"(?i)\s*page-break-before\s*:\s*always\s*;?", "", cleaned)
                cleaned = re.sub(r"(?i)\s*break-after\s*:\s*page\s*;?", "", cleaned)
                cleaned = re.sub(r"(?i)\s*break-before\s*:\s*page\s*;?", "", cleaned)
                cleaned = cleaned.strip(" ;")
                if cleaned:
                    node["style"] = cleaned
                else:
                    node.attrs.pop("style", None)
                if node.name == "div" and not node.get_text(" ", strip=True) and not node.find(True):
                    node.decompose()
                continue

            if node.name in {"table", "tr", "td", "tbody"}:
                cleaned = style
                for prop in (
                    "page-break-inside",
                    "break-inside",
                    "page-break-after",
                    "break-after",
                    "page-break-before",
                    "break-before",
                ):
                    cleaned = re.sub(rf"(?i)\s*{prop}\s*:\s*[^;]+;?", "", cleaned)
                cleaned = cleaned.strip(" ;")
                if cleaned:
                    node["style"] = cleaned
                else:
                    node.attrs.pop("style", None)
            elif node.name in {"div", "p", "span"}:
                cleaned = style
                for prop in (
                    "page-break-inside",
                    "break-inside",
                    "page-break-after",
                    "break-after",
                    "page-break-before",
                    "break-before",
                ):
                    cleaned = re.sub(rf"(?i)\s*{prop}\s*:\s*[^;]+;?", "", cleaned)
                cleaned = cleaned.strip(" ;")
                if cleaned:
                    node["style"] = cleaned
                else:
                    node.attrs.pop("style", None)

        return str(soup)

    def _split_multi_value(self, value, *, split_commas: bool = False) -> list[str]:
        text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            return []

        if split_commas:
            parts = re.split(r"(?:\n+|\s*\|\s*|\s*;\s*|\s*,\s*)", text)
        else:
            parts = re.split(r"(?:\n+|\s*\|\s*|\s*;\s*)", text)

        cleaned = [part.strip() for part in parts if part and part.strip()]
        return cleaned or [text]

    def _address_lines_from_values(self, *values) -> list[str]:
        lines = []
        for value in values:
            if value is None:
                continue
            for chunk in self._split_multi_value(value, split_commas=False):
                formatted = self.service._format_address_value(chunk)
                if not formatted:
                    continue
                for line in formatted.split("\n"):
                    line = line.strip()
                    if line:
                        lines.append(line)
        return lines

    def _build_notice_parties(self, data: dict) -> list[dict]:
        parties = []
        for party_cfg in get_notice_party_mappings():
            name_key = str(party_cfg.get("name_placeholder") or "").strip().lower()
            address_key = str(party_cfg.get("address_placeholder") or "").strip().lower()
            role = str(party_cfg.get("role") or "").strip() or "Party"
            if not name_key or not address_key:
                continue

            names = self._split_multi_value(data.get(name_key, ""), split_commas=True)
            if not names:
                continue

            address_text = str(data.get(address_key, "") or "").strip()
            if not address_text:
                continue

            address_blocks = self._split_multi_value(address_text, split_commas=False)
            if len(address_blocks) == len(names) and len(address_blocks) > 1:
                paired_addresses = address_blocks
            elif len(address_blocks) == 1:
                paired_addresses = address_blocks * len(names)
            else:
                paired_addresses = []

            for idx, name in enumerate(names, start=1):
                address_source = paired_addresses[idx - 1] if paired_addresses else address_text
                address_lines = self._address_lines_from_values(address_source)
                parties.append(
                    {
                        "serial": str(len(parties) + 1),
                        "name": name,
                        "role": role if len(names) == 1 else f"{role} No. {idx}",
                        "address_lines": address_lines,
                        "address": "\n".join(address_lines),
                    }
                )

        return parties

    def _co_borrower_render_count(self, data: dict) -> int:
        indices = set()
        index_patterns = (
            re.compile(r"^co_borrower_(\d+)_(?:name|address)$", re.I),
            re.compile(r"^co_borrower_(?:name|address)_(\d+)$", re.I),
        )
        value_fields = ("name", "address")

        for key, value in data.items():
            if value in (None, ""):
                continue
            value_text = str(value).strip()
            if not value_text:
                continue

            key_text = str(key)
            for pattern in index_patterns:
                match = pattern.match(key_text)
                if match:
                    indices.add(int(match.group(1)))
                    break

        if not indices:
            for idx in range(1, 7):
                for field in value_fields:
                    for key in (
                        f"co_borrower_{idx}_{field}",
                        f"co_borrower_{field}_{idx}",
                    ):
                        value = data.get(key)
                        if value in (None, ""):
                            continue
                        if str(value).strip():
                            indices.add(idx)
                            break
                    if idx in indices:
                        break

        if indices:
            return max(indices)

        for fallback_key in (
            "co_borrower_name",
            "co_borrower_names",
            "CO_BORROWER_NAME",
            "CO_BORROWER_NAMES",
        ):
            values = self._split_multi_value(data.get(fallback_key, ""), split_commas=True)
            if values:
                return len(values)

        return 0

    def _expand_co_borrower_placeholder_block(self, html_text: str, data: dict) -> str:
        count = self._co_borrower_render_count(data)
        if count <= 0:
            return html_text

        soup = BeautifulSoup(html_text, "html.parser")
        target_block = None

        for candidate in soup.find_all("table"):
            candidate_text = str(candidate)
            if (
                "{{CO_BORROWER_NAME}}" in candidate_text
                or "{{CO_BORROWER_ADDRESS}}" in candidate_text
            ):
                target_block = candidate
                break

        if target_block is None:
            for candidate in soup.find_all("div"):
                candidate_text = str(candidate)
                if (
                    "{{CO_BORROWER_NAME}}" in candidate_text
                    or "{{CO_BORROWER_ADDRESS}}" in candidate_text
                ):
                    target_block = candidate
                    break

        if target_block is None:
            return html_text

        def _rewrite_token(text: str, index: int) -> str:
            updated = text.replace("{{CO_BORROWER_NAME}}", f"{{{{CO_BORROWER_NAME_{index}}}}}")
            updated = updated.replace(
                "{{CO_BORROWER_ADDRESS_ALSO_AT}}", f"{{{{CO_BORROWER_{index}_ADDRESS_ALSO_AT}}}}"
            )
            updated = updated.replace("{{CO_BORROWER_ADDRESS}}", f"{{{{CO_BORROWER_ADDRESS_{index}}}}}")
            updated = updated.replace("{{CO_BORROWER_NAMES}}", f"{{{{CO_BORROWER_NAME_{index}}}}}")
            updated = re.sub(
                r"Co-Borrower No\.?\s*\d*",
                f"Co-Borrower No. {index}",
                updated,
                flags=re.I,
            )
            if re.search(r"\bS\.?\s*No\.?\b", updated, re.I):
                # "(Co-Borrower - SNO)" labels use the co-borrower's own
                # ordinal (1, 2, 3...); the row's leading "SNO." column
                # instead needs the overall serial number, offset by 1 to
                # account for the borrower always occupying row 1. Both
                # reuse the same literal "SNO" placeholder text, so they
                # have to be told apart by whether "Co-Borrower" appears in
                # the same text node.
                replacement = index if "co-borrower" in updated.lower() else index + 1
                updated = re.sub(r"\bS\.?\s*No\.?\b", str(replacement), updated, flags=re.I)
            return updated

        for idx in range(1, count + 1):
            clone = copy.deepcopy(target_block)
            for text_node in clone.find_all(string=True):
                raw = str(text_node)
                updated = _rewrite_token(raw, idx)
                if updated != raw:
                    text_node.replace_with(updated)
            target_block.insert_before(clone)

        target_block.decompose()
        return str(soup)

    def _suppress_empty_name_address_blocks(
        self, html_source: str, placeholder_map: dict, alias_map: dict
    ) -> str:
        """
        A party's name/address block only makes sense when it actually has an
        address. If the address token in a block resolves to nothing, blank
        the paired name too - and for "Also At" blocks specifically (which
        exist only to show an alternate address) remove the whole block,
        since a bare "Also At" heading with no name or address under it would
        still show up as a half-empty section in the PDF.
        """
        name_token_re = re.compile(r"\{\{\s*([A-Za-z0-9_]*NAME[A-Za-z0-9_]*)\s*\}\}")
        address_token_re = re.compile(r"\{\{\s*([A-Za-z0-9_]*ADDRESS[A-Za-z0-9_]*)\s*\}\}")
        also_at_marker_re = re.compile(r"Also\s+[Aa]t\b")

        def _resolved(token_text: str) -> str:
            normalized = normalize_placeholder_token(token_text)
            candidates = [normalized]

            # Borrower/co-borrower fields are addressed with several
            # different index-placement conventions across this codebase -
            # "CO_BORROWER_ADDRESS_1", "CO_BORROWER_1_ADDRESS",
            # "CO_BORROWER_ADDRESS_1_ALSO_AT" (index sandwiched mid-word),
            # even a bare unindexed "CO_BORROWER_ADDRESS_ALSO_AT" that
            # report_fields aliases straight to co-borrower 1. Only one of
            # these is guaranteed to have an alias/data entry for any given
            # field, so rather than hardcode each shape, pull the index digit
            # out and try it at every position in the remaining words before
            # concluding a value is empty - getting this wrong means silently
            # deleting a real co-borrower's name from a legal notice, which
            # is worse than occasionally leaving a block that should've been
            # suppressed.
            parts = normalized.split("_")
            digit_positions = [i for i, part in enumerate(parts) if part.isdigit()]
            if len(digit_positions) == 1:
                pos = digit_positions[0]
                index = parts[pos]
                bare_parts = parts[:pos] + parts[pos + 1:]
                for insert_at in range(len(bare_parts) + 1):
                    candidate_parts = bare_parts[:insert_at] + [index] + bare_parts[insert_at:]
                    candidates.append("_".join(candidate_parts))
                if index == "1":
                    candidates.append("_".join(bare_parts))

            for candidate in candidates:
                # Check the candidate itself before following alias_map -
                # e.g. the unindexed "CO_BORROWER_ADDRESS_ALSO_AT" is aliased
                # to "CO_BORROWER_1_ADDRESS_ALSO_AT" for final token
                # substitution, but it's also a real field in its own right
                # (report_fields maps it straight to co-borrower 1's data),
                # so redirecting it through the alias here would skip past a
                # value that's actually sitting under the unindexed key.
                value = (placeholder_map.get(candidate) or "").strip()
                if value:
                    return value
                resolved_key = alias_map.get(candidate, candidate)
                value = (placeholder_map.get(resolved_key) or "").strip()
                if value:
                    return value
            return ""

        soup = BeautifulSoup(html_source, "html.parser")
        changed = False

        def _process(tag_name: str) -> bool:
            nonlocal changed
            found_any = False
            for block in list(soup.find_all(tag_name)):
                block_markup = str(block)
                name_tokens = name_token_re.findall(block_markup)
                address_tokens = address_token_re.findall(block_markup)
                if not name_tokens or not address_tokens:
                    continue

                found_any = True
                if any(_resolved(token) for token in address_tokens):
                    continue

                if also_at_marker_re.search(block.get_text(" ", strip=True)):
                    block.decompose()
                else:
                    for token in name_tokens:
                        normalized = normalize_placeholder_token(token)
                        resolved_key = alias_map.get(normalized, normalized)
                        if resolved_key in placeholder_map:
                            placeholder_map[resolved_key] = ""
                changed = True

            return found_any

        if not _process("table"):
            _process("div")

        # Some templates don't wrap "Also At"/"Also at" in a table or div at
        # all - it's just a bare run of sibling <p> tags (heading, name,
        # address, trailing blank line) dropped directly between two
        # tables. _process() above only looks inside table/div containers,
        # so this run is otherwise invisible to it. Treat the marker
        # paragraph plus its following <p> siblings as one block.
        for marker_p in list(soup.find_all("p")):
            if marker_p.decomposed:
                continue
            if not also_at_marker_re.search(marker_p.get_text(" ", strip=True)):
                continue
            group = [marker_p]
            sibling = marker_p.find_next_sibling()
            while sibling is not None and getattr(sibling, "name", None) == "p":
                group.append(sibling)
                sibling = sibling.find_next_sibling()

            group_markup = "".join(str(node) for node in group)
            address_tokens = address_token_re.findall(group_markup)
            if not address_tokens:
                continue
            if any(_resolved(token) for token in address_tokens):
                continue

            for node in group:
                node.decompose()
            changed = True

        return str(soup) if changed else html_source

    def _expand_standalone_co_borrower_placeholders(self, html_text: str, data: dict) -> str:
        count = self._co_borrower_render_count(data)
        if count <= 0:
            return html_text

        replacement_tokens = {
            "{{CO_BORROWER_NAME}}": ", ".join(f"{{{{CO_BORROWER_NAME_{idx}}}}}" for idx in range(1, count + 1)),
            "{{CO_BORROWER_ADDRESS}}": ", ".join(f"{{{{CO_BORROWER_ADDRESS_{idx}}}}}" for idx in range(1, count + 1)),
        }

        soup = BeautifulSoup(html_text, "html.parser")
        changed = False

        for text_node in soup.find_all(string=True):
            parent = getattr(text_node, "parent", None)
            if parent and parent.name in {"script", "style"}:
                continue

            raw = str(text_node)
            updated = raw
            for token, replacement in replacement_tokens.items():
                if token in updated:
                    updated = updated.replace(token, replacement)

            if updated != raw:
                text_node.replace_with(updated)
                changed = True

        return str(soup) if changed else html_text

    def _render_party_section(self, data: dict, base_font_family: str | None = None) -> str:
        def _render_party_table_block() -> str:
            parties = self._build_notice_parties(data)

            if not parties:
                return ""

            party_template = Template(
                """
{% for party in parties %}
<div class="docx-table hidden-table party-table" style="width:100%; display:grid; grid-template-columns:35px 1fr; column-gap:10px; row-gap:0; margin:10px 0; break-inside:avoid; page-break-inside:avoid; font-size: inherit; line-height: inherit; color: inherit;">
  <div style="padding:8px 10px 0 10px; text-align:right; line-height:1.2; font-size: inherit; color: inherit;">
    <p style="margin:0; white-space:pre-wrap; text-align:right; line-height:1.15; font-size: inherit; color: inherit;">{{ party.serial }}</p>
  </div>
  <div style="padding:8px 10px 0 10px; text-align:left; line-height:1.2; font-size: inherit; color: inherit;">
    <p style="margin:0; white-space:pre-wrap; text-align:left; line-height:1.15; font-size: inherit; color: inherit;"><strong>{{ party.name }} ({{ party.role }})</strong></p>
  </div>
  <div style="padding:8px 10px 0 10px; text-align:right; line-height:1.2; font-size: inherit; color: inherit;">&nbsp;</div>
  <div style="padding:8px 10px 0 10px; text-align:left; line-height:1.5; font-size: inherit; color: inherit;">
    <div class="address-block" style="white-space:normal; line-height:1.5; margin:0 0 8px 0; font-size: inherit; color: inherit;">
      {% for line in party.address_lines %}
      <span class="address-line" style="display:block; margin:0 0 3px 0; line-height:1.5; font-size: inherit; color: inherit;">{{ line }}</span>
      {% endfor %}
    </div>
  </div>
  <div style="padding:8px 10px 0 10px; text-align:right; line-height:1.2; font-size: inherit; color: inherit;">&nbsp;</div>
  <div style="padding:8px 10px 0 10px; text-align:left; line-height:1.2; font-size: inherit; color: inherit;">
    <p style="margin:0 0 10px 0; white-space:pre-wrap; text-align:justify; line-height:1.15; font-size: inherit; color: inherit;">{{ mortgaged_placeholder }}</p>
  </div>
</div>
{% endfor %}
                """
            )

            return party_template.render(
                parties=parties,
                mortgaged_placeholder="{{ADDRESS_OF_MORTGAGED_PROPERTY}}",
            ).strip()

        rendered_block = _render_party_table_block()
        if rendered_block:
            return rendered_block

        parties = self._build_notice_parties(data)

        if not parties:
            return ""

        party_template = Template(
            """
{% for party in parties %}
<div class="docx-table hidden-table party-table" style="width:100%; display:grid; grid-template-columns:35px 1fr; column-gap:10px; row-gap:0; margin:0 0 8px 0; break-inside:avoid; page-break-inside:avoid; font-size: inherit; line-height: inherit; color: inherit;">
  <div style="padding:8px 10px 0 10px; text-align:right; line-height:1.2; font-size: inherit; color: inherit;">
    <p style="margin:0; white-space:pre-wrap; text-align:left; line-height:1.15; font-size: inherit; color: inherit;">{{ party.serial }}</p>
  </div>
  <div style="padding:8px 10px 0 10px; text-align:left; line-height:1.2; font-size: inherit; color: inherit;">
    <p style="margin:0; white-space:pre-wrap; text-align:left; line-height:1.15; font-size: inherit; color: inherit;"><strong>{{ party.name }} ({{ party.role }})</strong></p>
  </div>
  <div style="padding:8px 10px 0 10px; text-align:right; line-height:1.2; font-size: inherit; color: inherit;">&nbsp;</div>
  <div style="padding:8px 10px 0 10px; text-align:left; line-height:1.5; font-size: inherit; color: inherit;">
    <div class="address-block" style="white-space:normal; line-height:1.5; margin:0 0 8px 0; font-size: inherit; color: inherit;">
      {% for line in party.address_lines %}
      <span class="address-line" style="display:block; margin:0 0 3px 0; line-height:1.5; font-size: inherit; color: inherit;">{{ line }}</span>
      {% endfor %}
    </div>
  </div>
  <div style="padding:8px 10px 0 10px; text-align:right; line-height:1.2; font-size: inherit; color: inherit;">&nbsp;</div>
  <div style="padding:8px 10px 0 10px; text-align:left; line-height:1.2; font-size: inherit; color: inherit;">
    <p style="margin:0 0 10px 0; white-space:pre-wrap; text-align:justify; line-height:1.15; font-size: inherit; color: inherit;">{{ mortgaged_placeholder }}</p>
  </div>
</div>
{% endfor %}
            """
        )

        return party_template.render(
            parties=parties,
            mortgaged_placeholder="{{ADDRESS_OF_MORTGAGED_PROPERTY}}",
        ).strip()

    def _normalize_notice_party_section(self, html_text: str, data: dict) -> str:
        soup = BeautifulSoup(html_text, "html.parser")
        body = soup.body or soup

        children = [child for child in body.contents if getattr(child, "name", None)]
        start_idx = next((i for i, child in enumerate(children) if child.name == "table" and "row-layout" in (child.get("class") or [])), None)
        end_idx = next((i for i, child in enumerate(children) if child.name == "p" and "Hereinafter collectively referred to as" in child.get_text(" ", strip=True)), None)

        if start_idx is None or end_idx is None or start_idx >= end_idx:
            return str(soup)

        rendered_parties = self._render_party_section(data)
        if not rendered_parties:
            return str(soup)

        for child in children[start_idx + 1:end_idx]:
            if getattr(child, "name", None):
                child.decompose()

        end_node = children[end_idx]
        fragment = BeautifulSoup(rendered_parties, "html.parser")
        for fragment_node in list(fragment.contents):
            end_node.insert_before(fragment_node)
        return str(soup)

    def _find_notice_recipient_block(self, body):
        if body is None:
            return None

        candidate_classes = {
            "row-layout",
            "party-table",
            "notice-party-block",
            "notice-recipient-block",
        }
        collective_marker = "Hereinafter collectively referred to as"

        for child in body.find_all(["table", "div"], recursive=False):
            classes = set(child.get("class") or [])
            text = child.get_text(" ", strip=True)
            if classes.intersection(candidate_classes):
                return child
            if child.name == "table" and (
                "s.no" in text.lower()
                or "co-borrower no" in text.lower()
                or "{{borrower_name}}" in text.lower()
                or "{{co_borrower_name}}" in text.lower()
            ):
                return child
            if child.name == "table" and collective_marker in text:
                # A table whose text is essentially just this closing note
                # (e.g. only "(Hereinafter collectively referred to as the
                # "Borrowers")") is the trailing marker itself, not the real
                # party/recipient table — matching it here would make the
                # caller delete everything from this marker to the next
                # occurrence of the same marker, i.e. the rest of the
                # document, since the real marker was already consumed.
                if len(text) > len(collective_marker) + 100:
                    return child

        return None

    def _replace_placeholders_in_html(
        self,
        html_text: str,
        data: dict,
        *,
        preserve_notice_party_layout: bool = True,
        rebuild_recipient_block: bool = True,
    ) -> str:
        rendered = html_text or ""
        if not rendered.strip():
            return rendered

        def _replace_with_minimal_table_logic(html_source: str) -> str:
            # Preserve the authored HTML when the caller asks for it. This keeps
            # inline styles, table structure, and loop formatting intact so the
            # PDF renderer sees the same markup that the frontend produced.
            effective_preserve = preserve_notice_party_layout
            expanded_html = self._expand_co_borrower_placeholder_block(html_source, data)
            expanded_html = self._expand_standalone_co_borrower_placeholders(expanded_html, data)
            co_borrower_expanded = expanded_html != html_source
            html_source = expanded_html

            placeholder_map = build_placeholder_map(data)
            for normalized_key, rendered_value in list(placeholder_map.items()):
                if normalized_key.endswith("_ADDRESS") or normalized_key in {
                    "MORTGAGED_PROPERTY_ADDRESS",
                    "ADDRESS_OF_MORTGAGED_PROPERTY",
                    "ADDRESS_OF_THE_MORTGAGED_PROPERTY",
                }:
                    rendered_value = self.service._format_address_value(rendered_value)
                # Preserve HTML fragments that already contain markup, but
                # turn plain multiline address text into <br/> separated
                # HTML so PDF rendering keeps each comma-separated part on
                # its own line.
                if "<" not in rendered_value and ">" not in rendered_value:
                    rendered_value = html.escape(rendered_value).replace("\n", "<br/>")
                placeholder_map[normalized_key] = rendered_value

            # Build alias_map: maps alias normalized keys to their target normalized keys.
            # This is used to resolve placeholders that are aliases for other fields.
            alias_map = {
                normalize_placeholder_token(str(item.get("alias") or "")):
                normalize_placeholder_token(str(item.get("target") or ""))
                for item in get_notice_template_aliases()
                if str(item.get("alias") or "").strip() and str(item.get("target") or "").strip()
            }

            known_tokens = set(placeholder_map.keys()) | set(alias_map.keys())

            html_source = self._suppress_empty_name_address_blocks(html_source, placeholder_map, alias_map)

            def replace_token(raw: str) -> str:
                normalized = normalize_placeholder_token(raw)
                resolved_key = alias_map.get(normalized, normalized)
                return placeholder_map.get(resolved_key, "")

            def replace_angle(match):
                token = match.group(1) or ""
                normalized = normalize_placeholder_token(token)
                if normalized not in known_tokens:
                    return match.group(0)
                return replace_token(token)

            # Use direct regex substitution on the raw HTML string instead of
            # iterating BeautifulSoup text nodes. This avoids the text-node
            # splitting / fragment re-parsing bug where placeholders inside
            # sentences could be missed when BeautifulSoup splits text nodes
            # or when fragment insertion mutates the soup during iteration.
            html_source = re.sub(
                r"\{\{\s*([^{}]+?)\s*\}\}",
                lambda m: replace_token(m.group(1)),
                html_source,
            )
            html_source = re.sub(
                r"&lt;\s*([^&]+?)\s*&gt;",
                replace_angle,
                html_source,
            )
            html_source = re.sub(
                r"<\s*([^<>]+?)\s*>",
                replace_angle,
                html_source,
            )

            soup_dedup = BeautifulSoup(html_source, "html.parser")
            collective_nodes = [
                node
                for node in soup_dedup.find_all("p")
                if "Hereinafter collectively referred to as" in node.get_text(" ", strip=True)
            ]
            for extra_node in collective_nodes[1:]:
                extra_node.decompose()
            html_source = str(soup_dedup)

            rendered_html = cleanup_unresolved_brace_placeholders(html_source)
            if effective_preserve or co_borrower_expanded or not rebuild_recipient_block:
                return self._apply_notice_layout_tweaks(rendered_html)

            return self._apply_notice_layout_tweaks(self._replace_notice_recipient_block(rendered_html, data))

        return _replace_with_minimal_table_logic(rendered)

    def _replace_notice_recipient_block(self, html_text: str, data: dict) -> str:
        parties = self._build_notice_parties(data)

        if not parties:
            return html_text

        soup = BeautifulSoup(html_text, "html.parser")
        body = (
            soup.select_one(".docx-content")
            or soup.select_one(".docx-page")
            or soup.body
            or soup
        )
        target_block = self._find_notice_recipient_block(body)
        if target_block is None:
            return html_text

        co_borrower_parties = [
            party for party in parties
            if "co-borrower" in str(party.get("role", "")).lower()
        ]
        render_parties = co_borrower_parties
        if not render_parties:
         return html_text

        raw_mortgaged_address = (
            data.get("MORTGAGED_PROPERTY_ADDRESS")
            or data.get("ADDRESS_OF_MORTGAGED_PROPERTY")
            or data.get("ADDRESS_OF_THE_MORTGAGED_PROPERTY")
            or data.get("mortgaged_property_address")
            or data.get("property_address")
            or ""
        )
        mortgaged_address = self.service._format_address_value(str(raw_mortgaged_address or ""))
        mortgaged_address_html = (
            html.escape(mortgaged_address).replace(chr(10), "<br/>")
            if mortgaged_address
            else ""
        )

        def _render_party_block(template_block, party, serial, co_borrower_number):
            block = copy.deepcopy(template_block)
            address_html = "\n".join(party.get("address_lines") or [])
            name_html = html.escape(str(party.get("name", "") or ""))
            replacement_map = {
                "{{CO_BORROWER_NAME}}": name_html,
                "{{CO_BORROWER_ADDRESS}}": html.escape(address_html).replace("\n", "<br/>"),
                "{{CO_BORROWER_ADDRESS_1}}": html.escape(address_html).replace("\n", "<br/>"),
                "{{CO_BORROWER_ADDRESS_2}}": html.escape(address_html).replace("\n", "<br/>"),
                "{{CO_BORROWER_ADDRESS_3}}": html.escape(address_html).replace("\n", "<br/>"),
                "{{CO_BORROWER_ADDRESS_4}}": html.escape(address_html).replace("\n", "<br/>"),
                "{{CO_BORROWER_ADDRESS_5}}": html.escape(address_html).replace("\n", "<br/>"),
                "{{CO_BORROWER_ADDRESS_6}}": html.escape(address_html).replace("\n", "<br/>"),
                "{{MORTAGE_PROPERTY_ADDRESS}}": mortgaged_address_html,
                "{{MORTGAGED_PROPERTY_ADDRESS}}": mortgaged_address_html,
                "{{ADDRESS_OF_MORTGAGED_PROPERTY}}": mortgaged_address_html,
                "{{ADDRESS_OF_THE_MORTGAGED_PROPERTY}}": mortgaged_address_html,
            }

            for text_node in block.find_all(string=True):
                parent = getattr(text_node, "parent", None)
                if parent and parent.name in {"script", "style"}:
                    continue

                raw = str(text_node)
                updated = raw
                if re.search(r"\bS\.?\s*No\.?\b", updated, re.I):
                    updated = re.sub(r"\bS\.?\s*No\.?\b", str(serial), updated, flags=re.I)
                # Co-Borrower No. is its own sequence (1, 2, 3... excluding the
                # borrower), independent of the overall S.No (which counts the
                # borrower as row 1). This used to just strip "No." down to a
                # bare "Co-Borrower" label, leaving the adjacent S.No cell's
                # value (the overall serial, e.g. 2) as the only visible
                # number - so the first co-borrower showed "Co-Borrower - 2"
                # instead of "Co-Borrower No. 1".
                updated = re.sub(
                    r"Co-Borrower No\.?\s*\d*",
                    f"Co-Borrower No. {co_borrower_number}",
                    updated,
                    flags=re.I,
                )
                for token, value in replacement_map.items():
                    if token in updated:
                        updated = updated.replace(token, value)

                if updated != raw:
                    fragment = BeautifulSoup(updated, "html.parser")
                    replacement_nodes = list(fragment.contents)
                    if not replacement_nodes:
                        text_node.replace_with(updated)
                        continue

                    last_node = text_node
                    for node in replacement_nodes:
                        last_node.insert_after(node)
                        last_node = node
                    text_node.extract()

            for anchor in list(block.find_all("a")):
                anchor_text = anchor.get_text(" ", strip=True).lower()
                anchor_href = str(anchor.get("href") or "").lower()
                if "s.no" in anchor_text or "s.no" in anchor_href:
                    anchor.unwrap()

            return block

        for co_borrower_number, party in enumerate(render_parties, start=1):
            # S.No (overall row count) counts the borrower as row 1, so
            # co-borrowers start at 2 - Co-Borrower No. is a separate count
            # that always starts at 1, independent of the borrower row.
            serial = co_borrower_number + 1
            cloned_block = _render_party_block(target_block, party, serial, co_borrower_number)
            target_block.insert_before(cloned_block)

        nodes_to_remove = [target_block]
        for sibling in list(target_block.next_siblings):
            if isinstance(sibling, str):
                if not sibling.strip():
                    nodes_to_remove.append(sibling)
                    continue
                nodes_to_remove.append(sibling)
                continue

            sibling_text = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else ""
            if "Hereinafter collectively referred to as" in sibling_text:
                break
            nodes_to_remove.append(sibling)

        for node in nodes_to_remove:
            if hasattr(node, "decompose"):
                node.decompose()
            elif hasattr(node, "extract"):
                node.extract()

        return str(soup)

    def _build_rendered_html(self, html_text: str, application_number: str) -> str:
        data = self.service._build_placeholder_data_from_report(application_number)
        return self._replace_placeholders_in_html(html_text, data)

    # ==========================================================
    # 🔹 WORD PREVIEW GENERATOR (OPTION B)
    # ==========================================================
    def _generate_word_preview(self, template_path, data):

        document = Document(template_path)

        token_pattern = re.compile(r"(\{\{\s*([^{}]+?)\s*\}\}|<\s*([^<>]+?)\s*>)")
        placeholder_map = build_placeholder_map(data)

        def replace_text(text: str) -> str:
            if not text:
                return text

            def replace_token(match):
                token = match.group(2) or match.group(3) or ""
                normalized = normalize_placeholder_token(token)
                return sanitize_placeholder_value(placeholder_map.get(normalized, ""))

            updated = token_pattern.sub(replace_token, text)
            return cleanup_unresolved_brace_placeholders(updated)

        for paragraph in document.paragraphs:
            paragraph.text = replace_text(paragraph.text)

        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        paragraph.text = replace_text(paragraph.text)

        # Extract body text and any table content for the editor preview
        lines = []
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                lines.append(text)

        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    lines.append(" | ".join(cells))
            if lines and lines[-1] != "":
                lines.append("")

        # Return plain text because the frontend loads word previews with
        # Draft.js text content, not HTML parsing.
        html_body = "\n".join(lines).strip()

        return html_body

    # ==========================================================
    # GENERATE MAIL TEMPLATE (PREVIEW)
    # ==========================================================
    def generate_mail_template(self, request: MailTemplateRequest):

        from app.db.versioning import live_filter
        application = self.db.query(Application).filter(
            Application.business_code == request.application_number,
            *live_filter(Application)
        ).first()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        client = self._resolve_client_for_application(application)

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Validate required fields for notice generation
        missing_fields = self.service.validate_required_notice_fields(request.application_number)
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot generate notice. Missing required fields: {', '.join(missing_fields)}",
            )

        template = self._resolve_master_template_any(request.template_name)

        if template:
            html_path = template.html_path
            if html_path:
                raw_html = self._template_bytes_from_storage_ref(html_path).decode("utf-8", errors="ignore")
                raw_html = self._normalize_letterhead_footer_image(raw_html)

                data = self.service._build_placeholder_data_from_report(
                    request.application_number
                )
                print("RAW TEMPLATE START")
                print(raw_html)
                print("RAW TEMPLATE END")
                # User-supplied date from frontend (for templates that have {{DATE}})
                if request.date:
                    data["CURRENT_DATE"] = datetime.strptime(
                        request.date,
                        "%Y-%m-%d"
                        ).strftime("%d-%m-%Y")
                    print("CURRENT_DATE VALUE =", data.get("CURRENT_DATE"))

                ao = self._resolve_ao_information(client.id, request)
                ao_signature_url, ao_signature_html, ao_signature_path = self._resolve_ao_signature(ao)
                if ao_signature_html:
                    data["ao_signature"] = ao_signature_html
                if ao_signature_url:
                    data["ao_signature_url"] = ao_signature_url
                if ao_signature_path:
                    data["ao_signature_path"] = ao_signature_path
                print(
                    "[MAIL_PREVIEW_MORTGAGED]",
                    {
                        "application_number": request.application_number,
                        "mortgaged_property_address": data.get("mortgaged_property_address", ""),
                        "address_of_mortgaged_property": data.get("ADDRESS_OF_MORTGAGED_PROPERTY", ""),
                        "address_of_the_mortgaged_property": data.get("ADDRESS_OF_THE_MORTGAGED_PROPERTY", ""),
                        "mortgaged_property_address_alias": data.get("MORTGAGED_PROPERTY_ADDRESS", ""),
                    },
                )
                print(
                    "[MAIL_PREVIEW_AO]",
                    {
                        "application_number": request.application_number,
                        "client_id": client.id,
                        "ao_code": self._request_value(request, "ao_code", None),
                        "ao_name": self._request_value(request, "ao_name", None),
                        "ao_found": bool(ao),
                        "ao_signature_path": getattr(ao, "signature_path", None),
                        "ao_signature_url": ao_signature_url,
                    },
                )
                # Keep the review body aligned with the original template layout.
                # Preserve the template HTML as authored by the editor so the
                # original inline styles remain the source of truth.
                preview_body = self._replace_placeholders_in_html(
                    raw_html,
                    data,
                    preserve_notice_party_layout=False,
                )
                # Safety net: inject AO signature if the placeholder survived BeautifulSoup
                # processing (e.g. the frontend already embedded the <img> so this is a no-op,
                # but handles the edge case where {{AO_SIGNATURE}} is still present).
                if ao_signature_html:
                    preview_body = re.sub(
                        r"\{\{\s*AO[_\s]?SIGNATURE(?:[_\s]?(?:PATH|URL))?\s*\}\}",
                        lambda _m: ao_signature_html,
                        preview_body,
                        flags=re.IGNORECASE,
                    )
                print(
                    "[MAIL_PREVIEW_HTML]",
                    {
                        "body_contains_img": "<img" in preview_body,
                    },
                )
                print(
                    "[MAIL_PREVIEW_BREAKCHECK]",
                    {
                        "has_page_break_before": "page-break-before" in preview_body.lower(),
                        "has_break_before": "break-before" in preview_body.lower(),
                        "has_page_break_after": "page-break-after" in preview_body.lower(),
                        "has_break_after": "break-after" in preview_body.lower(),
                        "has_page_break_inside": "page-break-inside" in preview_body.lower(),
                        "has_break_inside": "break-inside" in preview_body.lower(),
                    },
                )

                return {
                    "subject": template.template_code,
                    "body": preview_body,
                    "render_mode": "html",
                    "structuredComponents": {},
                    "signature_html": ao_signature_html,
                    "ao_signature_url": ao_signature_url,
                    "ao_signature_html": ao_signature_html,
                    "ao_signature_path": ao_signature_path,
                }

            template_storage_ref = template.file_path

            data = self.service._build_placeholder_data_from_report(
                request.application_number
            )

            temp_template_path = self._load_docx_template_from_storage(template_storage_ref)
            try:
                preview_body = self._generate_word_preview(
                    temp_template_path,
                    data
                )
            finally:
                self._cleanup_temp_file(temp_template_path)

            return {
                "subject": template.template_code,
                "body": preview_body,
                "signature_html": "",
                "render_mode": "word",
                "structuredComponents": {}
            }

        # YAML fallback is explicit and stays backend-driven.
        return self.service.generate_template_content(request)

    async def create_communication(self, comm_data: CommunicationCreate, audit_user: AuditUser | None = None):
        payload = comm_data.dict()
        if audit_user is not None:
            payload["_audit_user"] = audit_user
        return await self.service.save_communication(payload)

    async def bulk_download_notice(
        self,
        request: BulkNoticeDownloadRequest,
        audit_user: AuditUser | None = None,
    ):
        template = self._resolve_master_template_by_id(request.template_id)
        if not template:
            template = self._resolve_master_template_any(str(request.template_id))

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        if not request.ao_code or not str(request.ao_code).strip():
            raise HTTPException(status_code=400, detail="ao_code is required")

        application_numbers = []
        seen = set()
        for app_no in request.application_numbers or []:
            normalized = str(app_no).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            application_numbers.append(normalized)

        if not application_numbers:
            raise HTTPException(status_code=400, detail="application_numbers is required")

        from app.db.versioning import live_filter

        missing_applications = []
        for app_no in application_numbers:
            if not self.db.query(Application).filter(
                Application.business_code == app_no, *live_filter(Application)
            ).first():
                missing_applications.append(app_no)

        if missing_applications:
            raise HTTPException(
                status_code=404,
                detail="Application not found for application(s): " + ", ".join(missing_applications),
            )

        zip_buffer = io.BytesIO()
        ao_code = str(request.ao_code).strip()
        output_format = "pdf"

        request_content = None
        if template.html_path:
            request_content = self._template_bytes_from_storage_ref(template.html_path).decode(
                "utf-8",
                errors="ignore",
            )
            # Bulk always renders via the `content=` path in generate_pdf_response,
            # which (unlike the template-fetch path individual downloads use) never
            # normalizes the footer image, so it's saved crushed to 69x57px unless
            # fixed up here too.
            request_content = self._normalize_letterhead_footer_image(request_content)

        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for app_no in application_numbers:
                notice_request = {
                    "application_number": app_no,
                    "template_name": template.template_code,
                    "ao_code": ao_code,
                    "output_format": output_format,
                    "preserve_notice_party_layout": False,
                }
                if request_content:
                    notice_request["content"] = request_content
                    notice_request["subject"] = template.template_code

                rendered_response = await self.generate_pdf_response(
                    notice_request,
                    audit_user=audit_user,
                )
                file_bytes = await self._streaming_response_to_bytes(rendered_response)
                application = self.db.query(Application).filter(
                    Application.business_code == app_no
                ).order_by(Application.id.desc()).first()

                
                archive.writestr(
                    self._notice_download_filename(
                        application,
                        template.template_type_rel.template_type,
                        output_format,
                    ),
                    file_bytes,
                )

        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=bulk_notice_download.zip"
            },
        )

    # ==========================================================
    # MAIN PDF / WORD GENERATOR
    # ==========================================================
    async def generate_pdf_response(self, request: dict, audit_user: AuditUser | None = None):

        application_number = request.get("application_number")
        template_name = request.get("template_name")
        content = request.get("content")
        subject = request.get("subject", template_name or "")

        if not application_number or (not template_name and not content):
            raise HTTPException(status_code=400, detail="Missing required fields")

        # 0️⃣ Validate required fields for notice generation
        missing_fields = self.service.validate_required_notice_fields(application_number)
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot generate notice. Missing required fields: {', '.join(missing_fields)}",
            )

        # 1️⃣ Fetch Application
        from app.db.versioning import live_filter
        application = self.db.query(Application).filter(
            Application.business_code == application_number,
            *live_filter(Application)
        ).first()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        # 2️⃣ Fetch Client
        client = self._resolve_client_for_application(application)

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        pdf_filename = self._notice_download_filename(
            application,
            template_name or subject,
            "pdf",
        )
        docx_filename = self._notice_download_filename(
            application,
            template_name or subject,
            "docx",
        )

        data = self.service._build_placeholder_data_from_report(application_number)
        # User-supplied date from frontend (for templates that have {{DATE}}).
        # Matches generate_mail_template's key/format - the template's actual
        # placeholder resolves through CURRENT_DATE, not a lowercase "date".
        date_value = request.get("date")
        if date_value:
            data["CURRENT_DATE"] = datetime.strptime(date_value, "%Y-%m-%d").strftime("%d-%m-%Y")
        print(
            "[MAIL_PDF_MORTGAGED]",
            {
                "application_number": application_number,
                # "mortgaged_property_address": data.get("mortgaged_property_address", ""),
                # "address_of_mortgaged_property": data.get("ADDRESS_OF_MORTGAGED_PROPERTY", ""),
                # "address_of_the_mortgaged_property": data.get("ADDRESS_OF_THE_MORTGAGED_PROPERTY", ""),
                # "mortgaged_property_address_alias": data.get("MORTGAGED_PROPERTY_ADDRESS", ""),
            },
        )
        ao = self._resolve_ao_information(client.id, request)
        ao_signature_url, ao_signature_html, ao_signature_path = self._resolve_ao_signature(ao)
        if ao_signature_html:
            data["ao_signature"] = ao_signature_html
        if ao_signature_url:
            data["ao_signature_url"] = ao_signature_url
        if ao_signature_path:
            data["ao_signature_path"] = ao_signature_path
        print(
            "[MAIL_PDF_AO]",
            {
                "application_number": application_number,
                "client_id": client.id,
                "ao_code": self._request_value(request, "ao_code", None),
                "ao_name": self._request_value(request, "ao_name", None),
                "ao_found": bool(ao),
                "ao_signature_path": ao_signature_path,
                "ao_signature_resolved": bool(ao_signature_url),
            },
        )
        template = self._resolve_master_template_any(template_name)

        if content:
            # `content` is already-rendered HTML from the preview iframe - real
            # names/addresses, no more `{{TOKENS}}`. Don't let this second pass
            # rebuild the recipient block: that step is only correct against a
            # raw template, and against already-rendered text it mismatches on
            # the words "borrower"/"co-borrower" and duplicates/overwrites the
            # already-correct party rows with the wrong names.
            rendered_content = self._replace_placeholders_in_html(
                content,
                data,
                preserve_notice_party_layout=False,
                rebuild_recipient_block=False,
            )
            # Safety net: inject AO signature if the placeholder survived BeautifulSoup
            # processing (e.g. the frontend already embedded the <img> so this is a no-op,
            # but handles the edge case where {{AO_SIGNATURE}} is still present).
            if ao_signature_html:
                rendered_content = re.sub(
                    r"\{\{\s*AO[_\s]?SIGNATURE(?:[_\s]?(?:PATH|URL))?\s*\}\}",
                    lambda _m: ao_signature_html,
                    rendered_content,
                    flags=re.IGNORECASE,
                )
            print(
                "[MAIL_PDF_BREAKCHECK]",
                {
                    "has_page_break_before": "page-break-before" in rendered_content.lower(),
                    "has_break_before": "break-before" in rendered_content.lower(),
                    "has_page_break_after": "page-break-after" in rendered_content.lower(),
                    "has_break_after": "break-after" in rendered_content.lower(),
                    "has_page_break_inside": "page-break-inside" in rendered_content.lower(),
                    "has_break_inside": "break-inside" in rendered_content.lower(),
                },
            )
            pdf_service = PDFService()
            pdf_buffer = await pdf_service.generate_communication_pdf(
                subject=request.get("subject", template.template_code if template else ""),
                body_html=rendered_content,
                structured_components=request.get("structuredComponents") or {},
            )

            await self._record_download_communication(
                application_number=application_number,
                template_name=template_name or (template.template_code if template else ""),
                subject=request.get("subject", template.template_code if template else ""),
                content=rendered_content,
                pdf_buffer=pdf_buffer.getvalue(),
                request=request,
                structured_components=request.get("structuredComponents") or {},
                output_format=request.get("output_format", "pdf"),
                audit_user=audit_user,
            )

            return StreamingResponse(
                pdf_buffer,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'},
            )

        if template:
            if template.html_path:
                raw_html = self._template_bytes_from_storage_ref(template.html_path).decode("utf-8", errors="ignore")
                raw_html = self._normalize_letterhead_footer_image(raw_html)

                content = self._replace_placeholders_in_html(
                    raw_html,
                    data,
                    preserve_notice_party_layout=False,
                )

                # Direct signature injection — mirrors the frontend's injectSignatureHtml
                # which does a plain string replace after the preview call.
                # BeautifulSoup's text-node replacement can fail to properly insert the
                # <img> tag (the html.parser may wrap / escape it), so we do an explicit
                # regex sub here as a reliable fallback for all AO_SIGNATURE variants.
                if ao_signature_html:
                    content = re.sub(
                        r"\{\{\s*AO[_\s]?SIGNATURE(?:[_\s]?(?:PATH|URL))?\s*\}\}",
                        lambda _m: ao_signature_html,
                        content,
                        flags=re.IGNORECASE,
                    )

                print(
                    "[MAIL_PDF_BREAKCHECK]",
                    {
                        "has_page_break_before": "page-break-before" in content.lower(),
                        "has_break_before": "break-before" in content.lower(),
                        "has_page_break_after": "page-break-after" in content.lower(),
                        "has_break_after": "break-after" in content.lower(),
                        "has_page_break_inside": "page-break-inside" in content.lower(),
                        "has_break_inside": "break-inside" in content.lower(),
                    },
                )

                pdf_service = PDFService()
                pdf_buffer = await pdf_service.generate_communication_pdf(
                    subject=template.template_code,
                    body_html=content,
                    structured_components={},
                )

                await self._record_download_communication(
                    application_number=application_number,
                    template_name=template.template_code,
                    subject=template.template_code,
                    content=content,
                    pdf_buffer=pdf_buffer.getvalue(),
                    request=request,
                    structured_components={},
                    output_format=request.get("output_format", "pdf"),
                    audit_user=audit_user,
                )

                return StreamingResponse(
                    pdf_buffer,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'},
                )

            template_storage_ref = template.file_path

            word_service = WordService()
            loop = asyncio.get_running_loop()

            temp_template_path = self._load_docx_template_from_storage(template_storage_ref)
            try:
                buffer = await loop.run_in_executor(
                    pdf_executor,
                    word_service.generate_from_template,
                    temp_template_path,
                    data
                )
            finally:
                self._cleanup_temp_file(temp_template_path)

            if request.get("output_format") == "docx":
                await self._record_download_communication(
                    application_number=application_number,
                    template_name=template.template_code if template else template_name,
                    subject=template.template_code if template else template_name,
                    content="",
                    pdf_buffer=None,
                    request=request,
                    output_format="docx",
                    audit_user=audit_user,
                )
                return StreamingResponse(
                    buffer,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={
                        "Content-Disposition": f'attachment; filename="{docx_filename}"'
                    }
                )

            # This template has a raw .docx file_path but no html_path - the
            # pre-HTML-pipeline template shape. PDF output for that shape
            # depended on a LibreOffice conversion step that's been removed
            # (no template in current use is missing html_path); docx output
            # above still works since it never needed LibreOffice.
            raise HTTPException(
                status_code=400,
                detail="PDF output is not supported for templates without an HTML source. Use output_format=docx, or migrate this template to an HTML template.",
            )

        # ==========================================================
        # ✅ STEP 1: YAML WORD TEMPLATE CHECK (ADD HERE)
        # ==========================================================
        templates = self.service.load_templates()
        yaml_template = templates.get("templates", {}).get(template_name)

        if yaml_template and yaml_template.get("render_mode") == "word":

            template_path = os.path.join(
                settings.BASE_DIR,
                "app",
                yaml_template.get("word_template_path")
            )

            data = self.service._build_placeholder_data_from_report(application_number)

            word_service = WordService()
            loop = asyncio.get_running_loop()

            buffer = await loop.run_in_executor(
                pdf_executor,
                word_service.generate_from_template,
                template_path,
                data
            )

            if request.get("output_format") == "docx":
                await self._record_download_communication(
                    application_number=application_number,
                    template_name=template_name or yaml_template.get("template_name", ""),
                    subject=template_name or yaml_template.get("template_name", ""),
                    content="",
                    pdf_buffer=None,
                    request=request,
                    output_format="docx",
                    audit_user=audit_user,
                )
                return StreamingResponse(
                    buffer,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={
                        "Content-Disposition": f'attachment; filename="{docx_filename}"'
                    },
                )

            # PDF output for this legacy YAML "word" render mode depended on
            # a LibreOffice conversion step that's been removed (unused in
            # practice - zero communications on record for this template);
            # docx output above still works since it never needed LibreOffice.
            raise HTTPException(
                status_code=400,
                detail="PDF output is not supported for this template's render mode. Use output_format=docx.",
            )

        if not template:
            content = self.service.generate_template_content(
                MailTemplateRequest(
                    application_number=application_number,
                    template_name=template_name
                )
            )

            pdf_service = PDFService()

            pdf_buffer = await pdf_service.generate_communication_pdf(
                subject=content.get("subject", ""),
                body_html=content.get("body", ""),
                structured_components=content.get("structuredComponents"),
            )

            await self._record_download_communication(
                application_number=application_number,
                template_name=template_name or "",
                subject=content.get("subject", ""),
                content=content.get("body", ""),
                pdf_buffer=pdf_buffer.getvalue(),
                request=request,
                structured_components=content.get("structuredComponents"),
                output_format=request.get("output_format", "pdf"),
                audit_user=audit_user,
            )

            return StreamingResponse(
                pdf_buffer,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'}
            )

    # ==========================================================
    # NOTICE WORD GENERATOR (single backend call, no draft round-trip)
    # ==========================================================
    async def generate_docx_response(self, request: dict, audit_user: AuditUser | None = None):

        application_number = request.get("application_number")
        template_name = request.get("template_name")
        content = request.get("content")
        subject = request.get("subject", template_name or "")

        if not application_number or (not template_name and not content):
            raise HTTPException(status_code=400, detail="Missing required fields")

        missing_fields = self.service.validate_required_notice_fields(application_number)
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot generate notice. Missing required fields: {', '.join(missing_fields)}",
            )

        from app.db.versioning import live_filter
        application = self.db.query(Application).filter(
            Application.business_code == application_number,
            *live_filter(Application)
        ).first()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        client = self._resolve_client_for_application(application)

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        docx_filename = self._notice_download_filename(
            application,
            template_name or subject,
            "docx",
        )

        data = self.service._build_placeholder_data_from_report(application_number)
        # Matches generate_mail_template's key/format - the template's actual
        # placeholder resolves through CURRENT_DATE, not a lowercase "date".
        date_value = request.get("date")
        if date_value:
            data["CURRENT_DATE"] = datetime.strptime(date_value, "%Y-%m-%d").strftime("%d-%m-%Y")

        ao = self._resolve_ao_information(client.id, request)
        ao_signature_url, ao_signature_html, ao_signature_path = self._resolve_ao_signature(ao)
        if ao_signature_html:
            data["ao_signature"] = ao_signature_html
        if ao_signature_url:
            data["ao_signature_url"] = ao_signature_url
        if ao_signature_path:
            data["ao_signature_path"] = ao_signature_path

        template = self._resolve_master_template_any(template_name)

        word_service = WordService()
        loop = asyncio.get_running_loop()

        # Same HTML source the PDF path renders from - either the caller's
        # already-rendered content, or the raw uploaded MasterTemplate HTML.
        raw_html = content
        is_prerendered_content = bool(raw_html)
        if not raw_html and template and template.html_path:
            raw_html = self._template_bytes_from_storage_ref(template.html_path).decode(
                "utf-8", errors="ignore"
            )
            raw_html = self._normalize_letterhead_footer_image(raw_html)

        if raw_html:
            # When `raw_html` is the caller's already-rendered `content` (real
            # names, no more `{{TOKENS}}`), don't let this pass rebuild the
            # recipient block - see the matching comment in
            # generate_pdf_response for why that duplicates/overwrites the
            # already-correct party rows.
            rendered_content = self._replace_placeholders_in_html(
                raw_html,
                data,
                preserve_notice_party_layout=False,
                rebuild_recipient_block=not is_prerendered_content,
            )
            if ao_signature_html:
                rendered_content = re.sub(
                    r"\{\{\s*AO[_\s]?SIGNATURE(?:[_\s]?(?:PATH|URL))?\s*\}\}",
                    lambda _m: ao_signature_html,
                    rendered_content,
                    flags=re.IGNORECASE,
                )

            docx_buffer = await loop.run_in_executor(
                pdf_executor,
                word_service.generate_docx_from_html,
                rendered_content,
            )

            await self._record_download_communication(
                application_number=application_number,
                template_name=template_name or (template.template_code if template else ""),
                subject=request.get("subject", template.template_code if template else ""),
                content=rendered_content,
                pdf_buffer=None,
                request=request,
                structured_components=request.get("structuredComponents") or {},
                output_format="docx",
                audit_user=audit_user,
            )

            return StreamingResponse(
                docx_buffer,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f'attachment; filename="{docx_filename}"'},
            )

        if template and template.file_path:
            temp_template_path = self._load_docx_template_from_storage(template.file_path)
            try:
                buffer = await loop.run_in_executor(
                    pdf_executor,
                    word_service.generate_from_template,
                    temp_template_path,
                    data,
                )
            finally:
                self._cleanup_temp_file(temp_template_path)

            await self._record_download_communication(
                application_number=application_number,
                template_name=template.template_code,
                subject=template.template_code,
                content="",
                pdf_buffer=None,
                request=request,
                output_format="docx",
                audit_user=audit_user,
            )

            return StreamingResponse(
                buffer,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f'attachment; filename="{docx_filename}"'},
            )

        raise HTTPException(status_code=404, detail="Template not found")
