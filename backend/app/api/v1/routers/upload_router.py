from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from starlette.concurrency import run_in_threadpool
from app.core.settings import settings
import shutil
import os
import uuid
from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user

router = APIRouter(
    tags=["Uploads"]
)


def _write_upload_to_disk(upload_file, dest_path: str):
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """
    Upload a file to the server.
    Returns the URL to access the file.
    """
    try:
        # Generate a unique filename to avoid collisions
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.TMP_DIR, unique_filename)

        await run_in_threadpool(_write_upload_to_disk, file, file_path)

        # Construct the URL (assuming standard deployment, adjusting as needed)
        # Using a relative URL or absolute depends on frontend needs. 
        # Returning a relative URL starting with /uploads/ is usually safest for proxying.
        url = f"/uploads/{unique_filename}"
        
        return {"url": url, "filename": unique_filename, "original_name": file.filename}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not upload file: {str(e)}")
