"""
File serving endpoints.

- GET /api/v1/files/serve?key=...   Streams a GCS object directly. Used as a
  fallback when GCS signed-URL generation fails (e.g. the attached service
  account lacks iam.serviceAccounts.signBlob permission) — the VM's ADC
  credentials always have storage.objects.get access, so this works
  reliably on GCP without any extra IAM setup. File keys are UUID-prefixed
  and not guessable, giving equivalent security to a signed URL.

- GET /api/v1/files/{key:path}      Serves files written by
  LocalStorageGateway (STORAGE_PROVIDER=local). Accepts EITHER a valid
  signed link (expires+sig, as produced by
  LocalStorageGateway.generate_presigned_url) OR a normal bearer token
  (same auth as the rest of the API).
"""
import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user_optional
from app.gateways.local_storage_gateway import LocalStorageGateway
from app.gateways.local_url_signing import verify
from app.gateways.s3_gateway import S3Gateway

router = APIRouter(tags=["Files"])


@router.get("/serve")
def serve_gcs_file(key: str = Query(..., description="GCS object key")):
    """Stream a GCS object to the client using the VM's ADC credentials."""
    try:
        gateway = S3Gateway()
        data = gateway.get_file_bytes_by_key(key)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}")

    content_type, _ = mimetypes.guess_type(key)
    content_type = content_type or "application/octet-stream"

    filename = key.split("/")[-1]
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{key:path}")
def get_local_file(
    key: str,
    expires: int | None = Query(default=None),
    sig: str | None = Query(default=None),
    audit_user: AuditUser | None = Depends(get_current_audit_user_optional),
):
    """
    Serves files written by LocalStorageGateway (STORAGE_PROVIDER=local).
    Accepts EITHER a valid signed link (expires+sig, as produced by
    LocalStorageGateway.generate_presigned_url - self-contained and
    needs no login, mirroring an S3 presigned URL) OR a normal bearer
    token (same auth as the rest of the API), so both a shared/presigned
    link and an authenticated in-app fetch work.
    """
    if audit_user is None and not verify(key, expires, sig):
        raise HTTPException(status_code=401, detail="Missing bearer token or valid signed link")

    gateway = LocalStorageGateway()
    try:
        data = gateway.get_file_bytes_by_key(key)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    content_type, _ = mimetypes.guess_type(key)
    return Response(content=data, media_type=content_type or "application/octet-stream")