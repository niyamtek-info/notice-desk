import json
import os
import re
import uuid
import tempfile
from urllib.parse import urlparse

from fastapi import HTTPException

from app.core.settings import settings
from app.db.models.client_models import MasterTemplate
from app.db.repositories.template_repository import MasterTemplateRepository
from app.db.versioning import (
    OPEN_END_DATE,
    close_version,
    clone_version,
    current_actor,
    mark_created,
    utcnow,
)
from app.gateways.storage_gateway import get_storage_gateway
from app.services.html_normalizer import normalize_docx_html
from app.services.light_docx_html_renderer import docx_to_html


class MasterTemplateService:
    def __init__(self, db):
        self.db = db
        self.repo = MasterTemplateRepository(db)
        self.repo.seed_template_types_if_empty()
        self.s3 = get_storage_gateway()

    def _safe_path_part(self, value: str, fallback: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in str(value or "").strip())
        cleaned = cleaned.strip("._-")
        return cleaned or fallback

    def _template_key_prefix(self, client_code: str, template_code: str) -> str:
        return f"templates/{self._safe_path_part(client_code, 'client')}/{template_code}"

    def _upload_text(self, key: str, text: str, filename: str) -> str:
        self.s3.upload_bytes(text.encode("utf-8"), key, filename)
        return key

    def _upload_bytes(self, key: str, data: bytes, filename: str) -> str:
        self.s3.upload_bytes(data, key, filename)
        return key

    def _store_asset_name(self, upload_file, template_key_prefix: str, slot: str) -> str | None:
        if not upload_file:
            return None

        original_name = getattr(upload_file, "filename", None) or f"{slot}.bin"
        safe_name = self._safe_path_part(original_name, f"{slot}.bin")
        key = f"{template_key_prefix}/assets/{uuid.uuid4().hex}_{safe_name}"
        data = upload_file.file.read()
        upload_file.file.seek(0)
        self._upload_bytes(key, data, safe_name)
        return original_name

    def _is_html_upload(self, file_name: str | None, content_type: str | None) -> bool:
        name = (file_name or "").lower()
        mime = (content_type or "").lower()
        return name.endswith((".html", ".htm")) or mime in {"text/html", "application/xhtml+xml"}

    def _extract_html_revision(self, html_path: str | None, safe_template_code: str) -> int:
        if not html_path:
            return 0

        file_name = os.path.basename(str(html_path))
        base_name = f"{safe_template_code}.html"
        if file_name == base_name:
            return 0

        match = re.match(rf"^{re.escape(safe_template_code)}\((\d+)\)\.html$", file_name)
        if match:
            return int(match.group(1))

        return 0

    def _next_html_filename(self, existing_template, safe_template_code: str) -> str:
        current_rev = self._extract_html_revision(
            getattr(existing_template, "html_path", None),
            safe_template_code,
        )
        next_rev = current_rev + 1
        return f"{safe_template_code}({next_rev}).html"

    def _build_public_s3_url(self, s3_key: str | None) -> str | None:
        if not s3_key:
            return None

        key = str(s3_key).strip()
        if not key:
            return None

        if key.startswith(("http://", "https://", "s3://")):
            return key

        base_url = (settings.S3_BASE_URL or "").strip().rstrip("/")
        if not base_url:
            return None

        return f"{base_url}/{key.lstrip('/')}"

    def _build_presigned_s3_url(self, s3_key: str | None) -> str | None:
        if not s3_key:
            return None

        key = str(s3_key).strip()
        if not key:
            return None

        bucket_name = (settings.S3_BUCKET_NAME or "").strip()
        base_url = (settings.S3_BASE_URL or "").strip().rstrip("/")

        if key.startswith("gs://"):
            gcs_bucket = (settings.GCS_BUCKET_NAME or "").strip()
            key = key.split(f"gs://{gcs_bucket}/", 1)[-1]
        elif key.startswith("s3://"):
            s3_prefix = f"s3://{bucket_name}/"
            if bucket_name and key.startswith(s3_prefix):
                key = key[len(s3_prefix):]
            else:
                parsed = urlparse(key)
                key = parsed.path.lstrip("/")
        elif key.startswith(("http://", "https://")):
            if base_url and key.startswith(f"{base_url}/"):
                key = key[len(base_url) + 1:]
            else:
                parsed = urlparse(key)
                path_key = parsed.path.lstrip("/")
                host = (parsed.netloc or "").lower()
                bucket_lower = bucket_name.lower()

                # Handle both path-style and virtual-hosted-style S3 URLs.
                if bucket_name and path_key.startswith(f"{bucket_name}/"):
                    key = path_key[len(bucket_name) + 1:]
                elif bucket_name and (host == bucket_lower or host.startswith(f"{bucket_lower}.")):
                    key = path_key
                else:
                    key = path_key

        key = key.lstrip("/")
        if not key:
            return None

        try:
            expiry = max(1, int(settings.TEMPLATE_PRESIGNED_EXPIRY_SECONDS or 3600))
            return self.s3.generate_presigned_url(key, expiration=expiry)
        except Exception:
            return None

    def _generate_html_from_docx(
        self,
        docx_bytes: bytes,
        template_key_prefix: str,
        base_name: str,
        html_filename: str | None = None,
    ) -> tuple[str | None, str | None]:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_docx_path = os.path.join(tmpdir, os.path.basename(base_name))
            with open(temp_docx_path, "wb") as f:
                f.write(docx_bytes)

            html_content = normalize_docx_html(docx_to_html(temp_docx_path))
        if not html_content.strip():
            return None, None

        html_filename = html_filename or f"{os.path.splitext(base_name)[0]}.html"
        html_key = f"{template_key_prefix}/{html_filename}"
        self._upload_text(html_key, html_content, html_filename)
        return html_key, html_filename

    def _resolve_template_context(self, client_code, client_name, template_type):
        client = self.repo.get_client_by_code(client_code)
        if not client:
            raise HTTPException(400, "Invalid client_code")

        if client.client_name != client_name:
            raise HTTPException(400, "Client name mismatch")

        template_type_obj = self.repo.get_template_type(template_type)
        if not template_type_obj:
            raise HTTPException(400, "Invalid template_type")

        return client, template_type_obj

    def _process_template_content(
        self,
        client_code,
        template_code,
        file,
        file_path,
        template_string,
        existing_template=None,
        is_update: bool = False,
    ):
        template_key_prefix = self._template_key_prefix(client_code, template_code)
        safe_template_code = template_code.replace("/", "_")
        upload_file = file or file_path
        raw_html_text = (template_string or "").strip()
        has_new_content = bool(raw_html_text or upload_file)

        if not has_new_content:
            if existing_template is None:
                raise HTTPException(400, "Template file or template_string is required")

            return {
                "file_path": existing_template.file_path,
                "html_path": existing_template.html_path,
                "template_string": None,
                "template_format": "html"
                if existing_template.html_path and existing_template.file_path == existing_template.html_path
                else "docx",
                "original_file_name": os.path.basename(existing_template.file_path or f"{safe_template_code}.html"),
                "html_filename": os.path.basename(existing_template.html_path) if existing_template.html_path else None,
                "manifest_path": f"{template_key_prefix}/template-manifest.json",
            }

        original_file_name = getattr(upload_file, "filename", None) or f"{uuid.uuid4().hex}"
        is_html_upload = bool(raw_html_text) or self._is_html_upload(
            getattr(upload_file, "filename", None),
            getattr(upload_file, "content_type", None),
        )

        docx_relative_path = None
        html_relative_path = None
        html_filename = None
        stored_template_string = None

        if raw_html_text:
            html_filename = (
                self._next_html_filename(existing_template, safe_template_code)
                if is_update and existing_template
                else f"{safe_template_code}.html"
            )
            html_relative_path = self._upload_text(
                f"{template_key_prefix}/{html_filename}",
                raw_html_text,
                html_filename,
            )
            docx_relative_path = html_relative_path
            stored_template_string = None
        elif upload_file:
            file_bytes = upload_file.file.read()
            upload_file.file.seek(0)

            if is_html_upload:
                html_filename = (
                    self._next_html_filename(existing_template, safe_template_code)
                    if is_update and existing_template
                    else f"{safe_template_code}.html"
                )
                html_text = file_bytes.decode("utf-8-sig", errors="ignore")
                html_relative_path = self._upload_text(
                    f"{template_key_prefix}/{html_filename}",
                    html_text,
                    html_filename,
                )
                docx_relative_path = html_relative_path
                stored_template_string = None
            else:
                original_docx_name = (
                    original_file_name
                    if original_file_name.lower().endswith(".docx")
                    else f"{original_file_name}.docx"
                )
                docx_filename = f"{uuid.uuid4().hex}_{original_docx_name}"
                docx_relative_path = self._upload_bytes(
                    f"{template_key_prefix}/{docx_filename}",
                    file_bytes,
                    docx_filename,
                )

                html_relative_path, html_filename = self._generate_html_from_docx(
                    file_bytes,
                    template_key_prefix,
                    f"{safe_template_code}.docx",
                    html_filename=(
                        self._next_html_filename(existing_template, safe_template_code)
                        if is_update and existing_template
                        else None
                    ),
                )
                stored_template_string = None

        return {
            "file_path": docx_relative_path or html_relative_path,
            "html_path": html_relative_path,
            "template_string": stored_template_string,
            "template_format": "html" if (is_html_upload or raw_html_text) else "docx",
            "original_file_name": original_file_name,
            "html_filename": html_filename,
            "manifest_path": f"{template_key_prefix}/template-manifest.json",
        }

    def _write_manifest(
        self,
        client_code,
        client_name,
        template_type,
        service_code,
        template_code,
        content_result,
    ):
        template_key_prefix = self._template_key_prefix(client_code, template_code)
        manifest = {
            "template_code": template_code,
            "client_code": client_code,
            "client_name": client_name,
            "template_type": template_type,
            "service_code": service_code,
            "original_file_name": content_result["original_file_name"],
            "template_format": content_result["template_format"],
            "docx_file": content_result["file_path"],
            "html_file": content_result["html_path"],
            "html_filename": content_result["html_filename"],
            "placeholders": [],
        }
        return self._upload_text(
            f"{template_key_prefix}/template-manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
            "template-manifest.json",
        )

    def upload_template(
        self,
        client_code,
        client_name,
        template_type,
        file,
        file_path,
        template_string,
        batch_code,
        header_image=None,
        footer_image=None,
        header_image_name=None,
        footer_image_name=None,
        audit_user=None,
    ):
        client, template_type_obj = self._resolve_template_context(
            client_code,
            client_name,
            template_type,
        )
        template_type_id = template_type_obj.id
        service_code = template_type_obj.service_code

        last_seq = self.repo.get_last_sequence(template_type_id)
        next_seq = last_seq + 1
        template_code = f"{service_code}/T/{str(next_seq).zfill(3)}"
        template_key_prefix = self._template_key_prefix(client_code, template_code)

        file_header_image_name = self._store_asset_name(
            header_image,
            template_key_prefix,
            "header",
        )
        file_footer_image_name = self._store_asset_name(
            footer_image,
            template_key_prefix,
            "footer",
        )
        manual_header_image_name = (
            str(header_image_name).strip() if header_image_name is not None else None
        )
        manual_footer_image_name = (
            str(footer_image_name).strip() if footer_image_name is not None else None
        )
        resolved_header_image_name = file_header_image_name or manual_header_image_name or None
        resolved_footer_image_name = file_footer_image_name or manual_footer_image_name or None

        content_result = self._process_template_content(
            client_code=client_code,
            template_code=template_code,
            file=file,
            file_path=file_path,
            template_string=template_string,
            is_update=False,
        )
        manifest_relative_path = self._write_manifest(
            client_code=client_code,
            client_name=client_name,
            template_type=template_type,
            service_code=service_code,
            template_code=template_code,
            content_result=content_result,
        )

        new_template = MasterTemplate(
            client_id=client.id,
            client_name=client.client_name,
            template_type_id=template_type_id,
            template_code=template_code,
            file_path=content_result["file_path"],
            html_path=content_result["html_path"],
            batch_code=batch_code,
            header_image_name=resolved_header_image_name,
            footer_image_name=resolved_footer_image_name,
        )
        mark_created(new_template, audit_user)
        self.db.add(new_template)

        self.db.commit()
        self.db.refresh(new_template)

        print(
            "[TEMPLATE_UPLOAD]",
            {
                "template_code": template_code,
                "client_code": client_code,
                "template_type": template_type,
                "template_format": content_result["template_format"],
                "file_path": content_result["file_path"],
                "html_path": content_result["html_path"],
                "used_template_string_input": bool((template_string or "").strip()),
            },
        )

        return {
            "template_code": template_code,
            "file_path": content_result["file_path"],
            "html_path": content_result["html_path"],
            "template_format": content_result["template_format"],
            "manifest_path": manifest_relative_path,
            "placeholders": [],
            "header_image_name": resolved_header_image_name,
            "footer_image_name": resolved_footer_image_name,
            "message": "Template uploaded successfully",
        }

    def update_template(
        self,
        template_id,
        client_code=None,
        client_name=None,
        template_type=None,
        file=None,
        file_path=None,
        template_string=None,
        batch_code=None,
        header_image=None,
        footer_image=None,
        header_image_name=None,
        footer_image_name=None,
        audit_user=None,
    ):
        template = self.repo.get_template_by_id_active(template_id)
        if not template:
            template = self.repo.get_latest_active_template_by_any_id(template_id)
        if not template:
            raise HTTPException(404, "Template not found")

        resolved_client_code = client_code or template.client.client_code
        resolved_client_name = client_name or template.client_name
        resolved_template_type = template_type or template.template_type_rel.template_type
        client, template_type_obj = self._resolve_template_context(
            resolved_client_code,
            resolved_client_name,
            resolved_template_type,
        )

        template_key_prefix = self._template_key_prefix(
            resolved_client_code,
            template.template_code,
        )
        new_header_name = self._store_asset_name(
            header_image,
            template_key_prefix,
            "header",
        )
        new_footer_name = self._store_asset_name(
            footer_image,
            template_key_prefix,
            "footer",
        )
        manual_header_name = (
            str(header_image_name).strip() if header_image_name is not None else None
        )
        manual_footer_name = (
            str(footer_image_name).strip() if footer_image_name is not None else None
        )

        content_result = self._process_template_content(
            client_code=resolved_client_code,
            template_code=template.template_code,
            file=file,
            file_path=file_path,
            template_string=template_string,
            existing_template=template,
            is_update=True,
        )
        manifest_relative_path = self._write_manifest(
            client_code=resolved_client_code,
            client_name=resolved_client_name,
            template_type=resolved_template_type,
            service_code=template_type_obj.service_code,
            template_code=template.template_code,
            content_result=content_result,
        )

        resolved_batch_code = template.batch_code if batch_code is None else batch_code
        resolved_header_image_name = template.header_image_name
        if new_header_name is not None:
            resolved_header_image_name = new_header_name
        elif header_image_name is not None:
            resolved_header_image_name = manual_header_name

        resolved_footer_image_name = template.footer_image_name
        if new_footer_name is not None:
            resolved_footer_image_name = new_footer_name
        elif footer_image_name is not None:
            resolved_footer_image_name = manual_footer_name

        max_version = self.repo.get_next_template_version(template.template_code)
        active_rows = self.db.query(MasterTemplate).filter(
            MasterTemplate.template_code == template.template_code,
            MasterTemplate.end_date == OPEN_END_DATE,
            MasterTemplate.is_deleted == False,
            MasterTemplate.is_active == True,
        ).all()

        current_active = active_rows[0] if active_rows else template
        old_html_path = current_active.html_path
        new_html_path = content_result["html_path"]
        new_html_filename = os.path.basename(new_html_path) if new_html_path else None
        content_changed = bool(file or file_path or (template_string or "").strip())
        print(
            "[TEMPLATE_UPDATE_PLAN]",
            {
                "template_id": template_id,
                "template_code": template.template_code,
                "old_id": current_active.id,
                "old_version": current_active.version,
                "next_version": max_version + 1,
                "content_changed": content_changed,
                "old_html_path": old_html_path,
                "new_html_path": new_html_path,
                "new_html_filename": new_html_filename,
            },
        )

        for row in active_rows:
            close_version(row, audit_user)

        new_template = clone_version(
            current_active,
            audit_user,
            client_id=client.id,
            client_name=client.client_name,
            template_type_id=template_type_obj.id,
            batch_code=resolved_batch_code,
            header_image_name=resolved_header_image_name,
            footer_image_name=resolved_footer_image_name,
            file_path=content_result["file_path"],
            html_path=content_result["html_path"],
            is_deleted=False,
            is_active=True,
        )
        new_template.version = max_version + 1

        self.db.add(new_template)
        self.db.commit()
        self.db.refresh(new_template)

        print(
            "[TEMPLATE_UPDATE_APPLIED]",
            {
                "template_code": new_template.template_code,
                "new_id": new_template.id,
                "new_version": new_template.version,
                "new_html_path": new_template.html_path,
                "new_html_filename": os.path.basename(new_template.html_path) if new_template.html_path else None,
                "header_image_name": new_template.header_image_name,
                "footer_image_name": new_template.footer_image_name,
            },
        )

        return {
            "message": "Template updated successfully",
            "manifest_path": manifest_relative_path,
            "template": self._build_response(new_template),
        }

    def _build_response(self, template):
        html_path = template.html_path
        if not html_path and template.file_path:
            root, _ = os.path.splitext(template.file_path)
            html_path = f"{root}.html"

        html_presigned_url = self._build_presigned_s3_url(html_path)
        html_url = html_presigned_url or self._build_public_s3_url(html_path)

        # Last-resort fallback: when V4 signing and GCS_BASE_URL both fail, return the raw
        # gs:// URI.  The frontend template fetcher detects this pattern and routes the
        # request through /api/v1/files/serve instead of the proxy.
        if not html_presigned_url and html_path:
            if html_path.startswith("gs://"):
                html_presigned_url = html_path
            else:
                clean_key = html_path.lstrip("/")
                html_presigned_url = f"gs://{settings.GCS_BUCKET_NAME}/{clean_key}"

        return {
            "id": template.id,
            "client_code": template.client.client_code,
            "client_name": template.client_name,
            "template_type": template.template_type_rel.template_type,
            "service_code": template.template_type_rel.service_code,
            "template_code": template.template_code,
            "file_path": template.file_path,
            "html_path": html_path,
            "html_url": html_url,
            "html_presigned_url": html_presigned_url,
            "batch_code": template.batch_code,
            "version": template.version,
            "is_active": template.is_active,
            "created_at": template.created_at,
            "header_image_name": template.header_image_name,
            "footer_image_name": template.footer_image_name,
        }

    def get_all_templates(self, skip: int | None = None, limit: int | None = None):
        templates = self.repo.get_all_active_templates(skip=skip, limit=limit)
        return {"templates": [self._build_response(t) for t in templates]}

    def get_templates_by_client(self, client_code):
        templates = self.repo.get_templates_by_client(client_code)
        return {"templates": [self._build_response(t) for t in templates]}

    def get_templates_by_type(self, template_type):
        template_type_obj = self.repo.get_template_type(template_type)
        if not template_type_obj:
            raise HTTPException(400, "Invalid template_type")

        templates = self.repo.get_templates_by_type(template_type_obj.id)
        return {"templates": [self._build_response(t) for t in templates]}

    def get_template_types(self):
        types = self.repo.get_all_template_types()
        return [
            {
                "id": t.id,
                "template_type": t.template_type,
                "service_code": t.service_code,
            }
            for t in types
        ]

    def delete_template(self, template_id: int, audit_user=None):
        template = self.repo.get_template_by_id_any(template_id)
        if not template:
            raise HTTPException(404, "Template not found")

        if template.is_deleted:
            raise HTTPException(400, "Template already deleted")

        active_rows = self.db.query(MasterTemplate).filter(
            MasterTemplate.template_code == template.template_code,
            MasterTemplate.end_date == OPEN_END_DATE,
        ).all()

        if not active_rows:
            active_rows = [template]

        for row in active_rows:
            row.updated_at = utcnow()
            row.updated_by = current_actor(audit_user)
            row.end_date = utcnow()
            row.is_deleted = True
            row.is_active = False
            row.version = (row.version or 1) + 1

        self.db.commit()
        self.db.refresh(template)

        return {
            "message": "Template deleted successfully",
            "template": self._build_response(template),
        }


