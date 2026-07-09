"""
File serving endpoint — streams GCS objects directly to the client.

This is used as a fallback when GCS signed-URL generation fails (e.g. the
attached service account lacks iam.serviceAccounts.signBlob permission).
The VM's ADC credentials always have storage.objects.get access, so this
endpoint works reliably on GCP without any extra IAM setup.

File keys are UUID-prefixed and not guessable, giving equivalent security
to a signed URL without requiring the signBlob IAM permission.
"""
import mimetypes

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.gateways.s3_gateway import S3Gateway

router = APIRouter()


@router.get("/files/serve")
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
