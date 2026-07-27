
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.services.extractor_service import ExtractorService
from app.db.session import get_db
from typing import Optional
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
import asyncio
import os
import uuid
import json
import shutil
from celery.result import AsyncResult

from app.core.progress_store import (
    get_progress as get_extraction_progress,
    get_active_for_application,
    get_latest_for_application,
)
from app.core.background_store import set_progress_async
from app.core.celery_app import celery_app
from app.workers.extraction_worker import run_extraction_worker
from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user

router = APIRouter(
    tags=["Extractor"]
)


def _resolve_progress_payload(file_id: str):
    progress_data = get_extraction_progress(file_id)
    task_id = progress_data.get("task_id")
    if not task_id:
        return progress_data

    task_result = AsyncResult(task_id, app=celery_app)
    payload = dict(progress_data)
    payload["task_id"] = task_id

    if task_result.successful():
        payload["status"] = "completed"
        payload["progress"] = 100
        payload["stage"] = payload.get("stage") or "Completed"
        if task_result.result is not None:
            payload["result"] = task_result.result
    elif task_result.failed():
        payload["status"] = "failed"
        payload["progress"] = 0
        payload["stage"] = payload.get("stage") or "Extraction failed"
        payload["error"] = str(task_result.result)
    elif str(task_result.status).upper() in {"STARTED", "PROGRESS"}:
        info = task_result.info
        if isinstance(info, dict):
            payload.update({k: v for k, v in info.items() if v is not None})
        if "status" not in payload or not payload.get("status"):
            payload["status"] = "processing"
        if "progress" not in payload:
            payload["progress"] = 5 if payload["status"] == "processing" else 0
        if "stage" not in payload:
            payload["stage"] = "Extraction in progress"
    elif payload.get("status") == "not_found" and task_result.status != "PENDING":
        payload["status"] = str(task_result.status).lower()

    return payload

@router.get("/progress/stream/{file_id}")
async def stream_progress(
    request: Request,
    file_id: str,
):
    """
    SSE endpoint to stream extraction progress for a given file_id.
    The client should listen for 'progress' events.
    """
    async def event_generator():
        last_progress = None
        while True:
            if await request.is_disconnected():
                break
            progress_data = _resolve_progress_payload(file_id)
            if progress_data != last_progress:
                yield f"data: {json.dumps(progress_data)}\n\n"
                last_progress = progress_data.copy()
                if progress_data.get("status") in {"completed", "failed", "not_found"}:
                    break
            await asyncio.sleep(0.5)
    return StreamingResponse(event_generator(), media_type="text/event-stream")



def _write_upload_to_disk(upload_file, dest_path: str):
    with open(dest_path, "wb") as f_out:
        shutil.copyfileobj(upload_file.file, f_out)


@router.post("/process")
async def process_document(
    file: UploadFile = File(...),
    orginal_file: UploadFile = File(None),
    doc_type: str = Form(...),
    application_number: str = Form(...),
    document_name: str = Form(None),
    username: str = Form(None),
    language: str = Form(None),
    pages: str = Form(None),
    page_range: str = Form(None),
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """
    Start extraction and return file_id immediately.
    Progress is written asynchronously without blocking response.
    """
    # Generate file_id and filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    original_filename = f"{file_id}_original_{orginal_file.filename}" if orginal_file else filename
    
    # Save file temporarily
    from app.core.settings import settings
    temp_path = os.path.join(settings.TMP_DIR, filename)
    await run_in_threadpool(_write_upload_to_disk, file, temp_path)

    # Save original file if provided
    original_temp_path = None
    if orginal_file:
        original_temp_path = os.path.join(settings.TMP_DIR, f"original_{filename}")
        await run_in_threadpool(_write_upload_to_disk, orginal_file, original_temp_path)

    await run_in_threadpool(
        ExtractorService(db).ensure_processing_record,
        record_id=file_id,
        application_number=application_number,
        doc_type=doc_type,
        file_name=filename,
        document_name=document_name or file.filename,
        audit_user=audit_user,
    )

    # Enqueue task immediately
    task = run_extraction_worker.apply_async(
        queue="extraction_queue",
        kwargs={
            "file_id": file_id,
            "doc_type": doc_type,
            "application_number": application_number,
            "document_name": document_name,
            "username": username,
            "audit_user_payload": jsonable_encoder(audit_user),
            "language": language,
            "filename": filename,
            "file_path": temp_path,
            "original_file_path": original_temp_path,
            "selected_page_range": page_range or pages,
        },
    )

    # Write progress asynchronously (non-blocking) - returns immediately
    set_progress_async(file_id, {
        "progress": 0,
        "status": "queued",
        "stage": "Queued for extraction",
        "doc_type": doc_type,
        "application_number": application_number,
        "document_name": document_name,
        "filename": filename,
        "task_id": task.id,
    })

    # Return file_id immediately without waiting for Redis
    return {
        "file_id": file_id,
        "task_id": task.id,
        "status": "queued",
        "progress_url": f"/api/v1/extract/progress/{file_id}",
        "progress_stream_url": f"/api/v1/extract/progress/stream/{file_id}",
        "latest_progress_url": f"/api/v1/extract/progress/latest/{application_number}",
        "task_url": f"/api/v1/extract/task/{task.id}",
    }

@router.get("/progress/{file_id}")
def get_progress(
    file_id: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return _resolve_progress_payload(file_id)

@router.get("/active/{application_number}")
def get_active_extractions(
    application_number: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """Return extractions currently in progress or failed for the given application."""
    return get_active_for_application(application_number)


@router.get("/progress/latest/{application_number}")
def get_latest_progress(
    application_number: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return get_latest_for_application(application_number)


@router.get("/task/{task_id}")
def get_task_status(
    task_id: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    task_result = AsyncResult(task_id, app=celery_app)
    payload = {
        "task_id": task_id,
        "status": task_result.status,
    }
    if task_result.successful():
        payload["result"] = task_result.result
    elif task_result.failed():
        payload["error"] = str(task_result.result)
    return payload



@router.get("/{record_id}")
def get_record(
    record_id: str,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """Fetch a single extraction record."""
    service = ExtractorService(db)
    return service.get_record(record_id)


@router.get("/")
def list_records(
    application_number: Optional[str] = None,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """List all extraction records, optionally filtered by application number."""
    service = ExtractorService(db)
    return service.list_records(application_number)


@router.get("/recommendations/{application_number}")
def get_recommendations(
    application_number: str,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """Fetch recommendations for an application."""
    service = ExtractorService(db)
    return service.get_recommendations(application_number)


@router.put("/{record_id}")
def update_record(
    record_id: str,
    update_data: dict,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """Update an extraction record."""
    service = ExtractorService(db)
    return service.update_record(record_id, update_data, audit_user=audit_user)


@router.delete("/{record_id}")
def delete_record(
    record_id: str,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """Delete an extraction record."""
    service = ExtractorService(db)
    return service.delete_record(record_id, audit_user=audit_user)
