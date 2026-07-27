from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Dict, Any
from celery.result import AsyncResult

from app.db.session import get_db
from app.services.translation_service import TranslationService
from app.core.celery_app import celery_app
from app.core.async_task_store import (
    get_latest_for_application,
    get_task,
    set_task,
    set_latest_for_application,
)
from app.workers.translation_worker import run_translation_worker
from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user

router = APIRouter()

class TranslationRequest(BaseModel):
    record_id: str
    target_language: str

@router.post("/")
async def translate_document(
    request: TranslationRequest,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """
    Translate document extraction data.
    Returns immediately with task_id without waiting for Redis.
    """
    service = TranslationService(db)
    cached_translation = await run_in_threadpool(
        service.get_cached_translation,
        request.record_id,
        request.target_language,
    )
    if cached_translation is not None:
        return {
            "status": "completed",
            "source": "cache",
            "record_id": request.record_id,
            "language": request.target_language,
            "translated_data": cached_translation,
        }

    task_type = f"translation:{request.target_language.lower()}"
    latest = get_latest_for_application(task_type, request.record_id)
    if latest:
        latest_status = str(latest.get("status", "")).lower()
        if latest_status in {"queued", "processing"} and latest.get("task_id"):
            return {
                "status": latest_status,
                "task_id": latest.get("task_id"),
                "process_id": latest.get("task_id"),
                "record_id": request.record_id,
                "language": request.target_language,
                "task_url": f"/api/v1/translate/task/{latest.get('task_id')}",
                "progress_url": f"/api/v1/translate/progress/{latest.get('task_id')}",
                "active_url": (
                    f"/api/v1/translate/active/{request.record_id}"
                    f"?target_language={request.target_language}"
                ),
            }

    task = run_translation_worker.apply_async(
        queue="translation_queue",
        kwargs={
            "record_id": request.record_id,
            "target_language": request.target_language,
        },
    )

    # Register immediately so the UI can resolve process_id right away.
    set_task(
        task.id,
        {
            "task_type": task_type,
            "record_id": request.record_id,
            "target_language": request.target_language,
            "status": "queued",
            "stage": "Translation queued",
            "progress": 0,
        },
    )
    set_latest_for_application(
        task_type,
        request.record_id,
        task.id,
    )
    
    # Return immediately without waiting for Redis
    return {
        "status": "queued",
        "task_id": task.id,
        "process_id": task.id,
        "record_id": request.record_id,
        "language": request.target_language,
        "task_url": f"/api/v1/translate/task/{task.id}",
        "progress_url": f"/api/v1/translate/progress/{task.id}",
        "active_url": (
            f"/api/v1/translate/active/{request.record_id}"
            f"?target_language={request.target_language}"
        ),
    }


@router.get("/task/{task_id}")
def get_translation_task_status(
    task_id: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    tracked = get_task(task_id)
    task_result = AsyncResult(task_id, app=celery_app)
    payload = {
        "task_id": task_id,
        "process_id": task_id,
        "status": task_result.status,
    }
    payload.update({k: v for k, v in tracked.items() if k not in {"status", "task_id"}})
    if task_result.successful():
        payload["result"] = task_result.result
        payload["status"] = "completed"
        payload["progress"] = 100
        payload["stage"] = payload.get("stage") or "Translation completed"
    elif task_result.failed():
        payload["error"] = str(task_result.result)
        payload["status"] = "failed"
        payload["progress"] = 0
        payload["stage"] = payload.get("stage") or "Translation failed"
    elif payload["status"] == "PENDING" and tracked.get("status"):
        payload["status"] = tracked.get("status")
    if "progress" not in payload:
        if str(payload.get("status", "")).lower() in {"queued"}:
            payload["progress"] = 0
        elif str(payload.get("status", "")).lower() in {"processing", "started"}:
            payload["progress"] = 15
    if "stage" not in payload:
        if str(payload.get("status", "")).lower() in {"queued"}:
            payload["stage"] = "Translation queued"
        elif str(payload.get("status", "")).lower() in {"processing", "started"}:
            payload["stage"] = "Translation in progress"
    return payload


@router.get("/progress/{process_id}")
def get_translation_progress(
    process_id: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return get_translation_task_status(process_id)


@router.get("/active/{record_id}")
def get_active_translation_task(
    record_id: str,
    target_language: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    task_type = f"translation:{target_language.lower()}"
    latest = get_latest_for_application(task_type, record_id)
    if not latest:
        return {
            "record_id": record_id,
            "target_language": target_language,
            "task_type": task_type,
            "status": "not_found",
        }
    if latest.get("task_id") and not latest.get("process_id"):
        latest["process_id"] = latest.get("task_id")
    return latest

class TranslationUpdateRequest(BaseModel):
    record_id: str
    target_language: str
    translated_data: Dict[str, Any]

@router.put("/")
def update_translation(
    request: TranslationUpdateRequest,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """
    Update/Save manually edited translation.
    """
    service = TranslationService(db)
    try:
        updated_data = service.update_translation(
            record_id=request.record_id,
            language=request.target_language,
            translated_content=request.translated_data
        )
        return {
            "record_id": request.record_id,
            "language": request.target_language,
            "status": "updated",
            "translated_data": updated_data
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
