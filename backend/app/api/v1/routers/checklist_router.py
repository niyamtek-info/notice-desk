from fastapi import APIRouter, Depends, HTTPException
from typing import List, Union
from sqlalchemy.orm import Session
from celery.result import AsyncResult
from app.db.session import get_db
from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user
from app.api.v1.controllers.checklist_controller import ChecklistController
from app.api.v1.schemas.checklist_schema import (
    ApplicationChecklistCreate,
    ApplicationChecklistBulkUpdateItem,
    ApplicationChecklistResponse,
    RunValidationRequest,
)
from app.core.celery_app import celery_app
from app.core.async_task_store import (
    get_task,
    get_latest_for_application,
)
from app.core.background_store import (
    set_task_async,
    set_latest_for_application_async,
)
from app.workers.checklist_worker import (
    run_checklist_matching_worker,
    run_checklist_validation_worker,
)

router = APIRouter()


def _resolve_task_payload(task_id: str):
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
        payload["stage"] = payload.get("stage") or "Checklist completed"
    elif task_result.failed():
        payload["error"] = str(task_result.result)
        payload["status"] = "failed"
        payload["progress"] = 0
        payload["stage"] = payload.get("stage") or "Checklist failed"
    elif payload["status"] == "PENDING" and tracked.get("status"):
        payload["status"] = tracked.get("status")
    elif str(task_result.status).upper() in {"STARTED", "PROGRESS"}:
        info = task_result.info
        if isinstance(info, dict):
            payload.update({k: v for k, v in info.items() if v is not None})
        if "progress" not in payload:
            payload["progress"] = 10 if payload.get("status") == "processing" else 0
        if "stage" not in payload:
            payload["stage"] = "Checklist in progress"
    return payload


def _get_active_existing_task(task_type: str, application_number: str):
    existing = get_latest_for_application(task_type, application_number)
    if not existing or not existing.get("task_id"):
        return None
    resolved = _resolve_task_payload(existing["task_id"])
    normalized = str(resolved.get("status", "")).lower()
    if normalized in {"queued", "processing", "pending", "started"}:
        return resolved
    return None

@router.get("/{application_number}")
def get_checklist(
    application_number: str,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    controller = ChecklistController(db)
    return controller.get_checklist(application_number)


@router.post("/", response_model=ApplicationChecklistResponse)
def create_checklist(
    obj_in: ApplicationChecklistCreate,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    controller = ChecklistController(db)
    return controller.create_checklist(obj_in, audit_user=audit_user)

@router.put("/{application_number}",
            response_model=List[ApplicationChecklistResponse])
def update_checklist(
    application_number: str,
    obj_in: Union[ApplicationChecklistBulkUpdateItem, List[ApplicationChecklistBulkUpdateItem]],
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    controller = ChecklistController(db)
    return controller.update_checklist(application_number, obj_in, audit_user=audit_user)


@router.post("/{application_number}/match", response_model=dict)
def trigger_matching(
    application_number: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    existing = _get_active_existing_task("checklist_match", application_number)
    if existing:
        print(f"[ROUTER] Task already running for {application_number}")
        return {
            "status": "already_running",
            "task_id": existing.get("task_id"),
            "process_id": existing.get("task_id"),
            "application_number": application_number,
            "task_type": "checklist_match",
            "task_url": f"/api/v1/checklist/task/{existing.get('task_id')}",
            "progress_url": f"/api/v1/checklist/progress/{existing.get('task_id')}",
            "active_url": f"/api/v1/checklist/active/{application_number}?task_type=checklist_match",
            "error": existing.get("error"),
        }

    print(f"[ROUTER] Queuing checklist matching task for {application_number} to celery...")
    task = run_checklist_matching_worker.apply_async(
        queue="checklist_queue",
        kwargs={
            "application_number": application_number,
            "audit_user_payload": {
                "user_id": audit_user.user_id,
                "email": audit_user.email,
                "full_name": audit_user.full_name,
            },
        },
    )
    print(f"[ROUTER] Task queued with ID: {task.id}")
    
    # Async store operations (non-blocking)
    set_task_async(
        task.id,
        {
            "task_type": "checklist_match",
            "application_number": application_number,
            "status": "queued",
            "stage": "Checklist matching queued",
            "progress": 0,
        },
    )
    set_latest_for_application_async("checklist_match", application_number, task.id)
    
    # Return immediately without waiting for Redis
    return {
        "status": "queued",
        "task_id": task.id,
        "process_id": task.id,
        "application_number": application_number,
        "task_type": "checklist_match",
        "task_url": f"/api/v1/checklist/task/{task.id}",
        "progress_url": f"/api/v1/checklist/progress/{task.id}",
        "active_url": f"/api/v1/checklist/active/{application_number}?task_type=checklist_match",
    }


@router.post("/run_validation", response_model=dict)
def run_validation(
    payload: RunValidationRequest,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    existing = _get_active_existing_task("checklist_validation", payload.application_number)
    if existing:
        print(f"[ROUTER] Task already running for {payload.application_number}")
        return {
            "status": "already_running",
            "task_id": existing.get("task_id"),
            "process_id": existing.get("task_id"),
            "application_number": payload.application_number,
            "task_type": "checklist_validation",
            "task_url": f"/api/v1/checklist/task/{existing.get('task_id')}",
            "progress_url": f"/api/v1/checklist/progress/{existing.get('task_id')}",
            "active_url": f"/api/v1/checklist/active/{payload.application_number}?task_type=checklist_validation",
            "error": existing.get("error"),
        }

    print(f"[ROUTER] Queuing checklist validation task for {payload.application_number} to celery...")
    task = run_checklist_validation_worker.apply_async(
        queue="checklist_queue",
        kwargs={
            "application_number": payload.application_number,
            "audit_user_payload": {
                "user_id": audit_user.user_id,
                "email": audit_user.email,
                "full_name": audit_user.full_name,
            },
        },
    )
    print(f"[ROUTER] Task queued with ID: {task.id}")
    
    # Async store operations (non-blocking)
    set_task_async(
        task.id,
        {
            "task_type": "checklist_validation",
            "application_number": payload.application_number,
            "status": "queued",
            "stage": "Checklist validation queued",
            "progress": 0,
        },
    )
    set_latest_for_application_async("checklist_validation", payload.application_number, task.id)
    
    # Return immediately without waiting for Redis
    return {
        "status": "queued",
        "task_id": task.id,
        "process_id": task.id,
        "application_number": payload.application_number,
        "task_type": "checklist_validation",
        "task_url": f"/api/v1/checklist/task/{task.id}",
        "progress_url": f"/api/v1/checklist/progress/{task.id}",
        "active_url": f"/api/v1/checklist/active/{payload.application_number}?task_type=checklist_validation",
    }


@router.get("/task/{task_id}")
def get_checklist_task_status(
    task_id: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return _resolve_task_payload(task_id)


@router.get("/progress/{process_id}")
def get_checklist_progress(
    process_id: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return get_checklist_task_status(process_id)


@router.get("/active/{application_number}")
def get_active_checklist_task(
    application_number: str,
    task_type: str = "checklist_validation",
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    latest = get_latest_for_application(task_type, application_number)
    if not latest:
        return {
            "application_number": application_number,
            "task_type": task_type,
            "status": "not_found",
        }
    if latest.get("task_id"):
        return _resolve_task_payload(latest["task_id"])
    return latest
