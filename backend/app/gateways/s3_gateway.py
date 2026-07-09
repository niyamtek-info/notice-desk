"""
GCS gateway — drop-in replacement for the previous S3Gateway.
Keeps the same class name and method signatures so all calling code
(services, controllers) works without modification.
"""
import json
import mimetypes
import datetime
from urllib.parse import urlparse

import google.auth
from google.auth.transport import requests as google_auth_requests
from google.cloud import storage

from app.core.settings import settings


def _get_signing_credentials():
    """
    Return (credentials, service_account_email) suitable for signed-URL
    generation.  Works both with an explicit service-account JSON file
    (GOOGLE_APPLICATION_CREDENTIALS) and with the VM's attached service
    account via ADC.
    """
    creds_file = settings.GOOGLE_APPLICATION_CREDENTIALS
    if creds_file:
        from google.oauth2 import service_account as sa_module
        creds = sa_module.Credentials.from_service_account_file(
            creds_file,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return creds, creds.service_account_email

    # ADC path — works on GCE VMs with an attached service account
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    request = google_auth_requests.Request()
    creds.refresh(request)
    email = getattr(creds, "service_account_email", None)
    return creds, email


class S3Gateway:
    """
    GCS-backed storage gateway.  All method signatures are identical to the
    previous boto3/S3 implementation so that callers need no changes.
    """

    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _blob(self, key: str) -> storage.Blob:
        return self.bucket.blob(key)

    # ------------------------------------------------------------------ #
    #  Upload                                                              #
    # ------------------------------------------------------------------ #

    def upload_file(self, local_path: str, s3_key: str) -> str:
        content_type, _ = mimetypes.guess_type(local_path)
        if not content_type:
            content_type = "application/octet-stream"

        blob = self._blob(s3_key)
        blob.content_disposition = "inline"
        blob.upload_from_filename(local_path, content_type=content_type)

        if settings.GCS_BASE_URL:
            return f"{settings.GCS_BASE_URL}/{s3_key}"
        return f"gs://{settings.GCS_BUCKET_NAME}/{s3_key}"

    def upload_bytes(self, data: bytes, s3_key: str, filename: str = "") -> str:
        content_type, _ = mimetypes.guess_type(filename or s3_key)
        if not content_type:
            content_type = "application/octet-stream"

        blob = self._blob(s3_key)
        blob.content_disposition = "inline"
        blob.upload_from_string(data, content_type=content_type)

        if settings.GCS_BASE_URL:
            return f"{settings.GCS_BASE_URL}/{s3_key}"
        return f"gs://{settings.GCS_BUCKET_NAME}/{s3_key}"

    # ------------------------------------------------------------------ #
    #  JSON helpers                                                        #
    # ------------------------------------------------------------------ #

    def save_json(self, data: dict, s3_key: str) -> str:
        blob = self._blob(s3_key)
        blob.upload_from_string(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
        if settings.GCS_BASE_URL:
            return f"{settings.GCS_BASE_URL}/{s3_key}"
        return f"gs://{settings.GCS_BUCKET_NAME}/{s3_key}"

    def overwrite_json(self, data: dict, s3_key: str) -> str:
        return self.save_json(data, s3_key)

    def load_json(self, s3_key: str) -> dict:
        return json.loads(self._blob(s3_key).download_as_bytes())

    def download_json(self, s3_key: str) -> dict:
        try:
            return self.load_json(s3_key)
        except Exception as e:
            raise RuntimeError(f"Failed to download JSON from GCS ({s3_key}): {e}")

    # ------------------------------------------------------------------ #
    #  Signed / presigned URLs                                            #
    # ------------------------------------------------------------------ #

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Return a URL the browser can use to fetch the GCS object.

        Strategy (in order):
        1. V4 signed URL — produces a real https://storage.googleapis.com/BUCKET/key?X-Goog-…
           URL the browser can load directly, exactly like AWS pre-signed URLs.
           Requires the service account to have iam.serviceAccounts.signBlob permission.
        2. Backend file-serve endpoint (BACKEND_BASE_URL fallback) — used when signing
           is unavailable. BACKEND_BASE_URL must be the externally reachable URL of the
           backend (e.g. http://35.200.x.x:8000), NOT localhost, because the browser
           resolves the URL, not the server.
        3. If neither works, raise a clear error.
        """
        from urllib.parse import quote

        # Strip gs://bucket-name/ prefix if the full URI was stored in the DB
        if s3_key.startswith("gs://"):
            s3_key = s3_key.split(f"gs://{settings.GCS_BUCKET_NAME}/", 1)[-1]
        s3_key = s3_key.lstrip("/")

        # ── Path 1: V4 signed URL (proper https://storage.googleapis.com/… URL) ─
        blob = self._blob(s3_key)
        sign_exc = None
        try:
            creds, email = _get_signing_credentials()
            token = getattr(creds, "token", None)
            if email and token:
                # IAM-based signing — works on GCE without a JSON key file
                return blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.timedelta(seconds=expiration),
                    method="GET",
                    service_account_email=email,
                    access_token=token,
                )
            # Service-account JSON key available — sign directly
            return blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(seconds=expiration),
                method="GET",
                credentials=creds,
            )
        except Exception as exc:
            sign_exc = exc
            print(f"GCS V4 signing failed for '{s3_key}': {exc}")

        # ── Path 2: backend file-serve endpoint (fallback) ───────────────────
        # BACKEND_BASE_URL must be the URL the browser can reach, e.g. http://35.x.x.x:8000
        # Setting it to http://localhost:8000 on the server won't work from the browser.
        backend_base = (settings.BACKEND_BASE_URL or "").strip().rstrip("/")
        if backend_base:
            return f"{backend_base}/api/v1/files/serve?key={quote(s3_key, safe='')}"

        raise RuntimeError(
            f"Cannot produce an accessible URL for GCS object '{s3_key}'. "
            "Either grant iam.serviceAccounts.signBlob to the service account for V4 signed URLs, "
            "or set BACKEND_BASE_URL in your .env to the externally reachable backend URL "
            "(e.g. http://35.200.x.x:8000) to enable the file-serve fallback. "
            f"Signing error: {sign_exc}"
        ) from sign_exc

    # ------------------------------------------------------------------ #
    #  Download                                                           #
    # ------------------------------------------------------------------ #

    def get_file_bytes(self, file_url: str) -> bytes:
        try:
            if file_url.startswith("gs://"):
                key = file_url.split(f"gs://{settings.GCS_BUCKET_NAME}/", 1)[-1]
            elif file_url.startswith(("http://", "https://")):
                parsed = urlparse(file_url)
                key = parsed.path.lstrip("/")
                # Strip bucket-name prefix for storage.googleapis.com path-style URLs
                bucket_prefix = f"{settings.GCS_BUCKET_NAME}/"
                if key.startswith(bucket_prefix):
                    key = key[len(bucket_prefix):]
            else:
                key = file_url
            return self._blob(key).download_as_bytes()
        except Exception as e:
            raise Exception(f"Failed to fetch file from GCS: {e}")

    def get_file_bytes_by_key(self, s3_key: str) -> bytes:
        try:
            # Strip gs://bucket/ prefix if callers accidentally pass a full URI
            if s3_key.startswith("gs://"):
                s3_key = s3_key.split(f"gs://{settings.GCS_BUCKET_NAME}/", 1)[-1]
            return self._blob(s3_key).download_as_bytes()
        except Exception as e:
            raise Exception(f"Failed to fetch file from GCS key ({s3_key}): {e}")
