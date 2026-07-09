from fastapi.encoders import jsonable_encoder

from app.api.v1.dependencies.auth import AuditUser
from app.core.async_task_store import set_task
from app.core.celery_app import celery_app
from app.db.repositories.checklist_repo import ChecklistRepository
from app.db.session import SessionLocal
from app.services.checklist_service import ChecklistService


def _deserialize_audit_user(audit_user_payload: dict | None) -> AuditUser | None:
    if not audit_user_payload:
        return None
    return AuditUser(
        user_id=audit_user_payload.get("user_id"),
        email=audit_user_payload.get("email") or "System",
        full_name=audit_user_payload.get("full_name"),
    )


def _update_task_state(task, *, task_type: str, application_number: str, status: str, stage: str, progress: int, result=None, error=None):
    payload = {
        "task_type": task_type,
        "application_number": application_number,
        "status": status,
        "stage": stage,
        "progress": progress,
    }
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error

    set_task(task.request.id, payload)

    try:
        if hasattr(task, "update_state"):
            task.update_state(
                state="PROGRESS" if status == "processing" else status.upper(),
                meta={
                    "task_id": task.request.id,
                    "process_id": task.request.id,
                    **payload,
                },
            )
    except Exception:
        pass


@celery_app.task(
    bind=True,
    name="app.workers.checklist_worker.run_checklist_matching_worker",
    queue="checklist_queue",
)
def run_checklist_matching_worker(self, *, application_number: str, audit_user_payload: dict | None = None):
    print(f"\n{'=' * 60}")
    print("[CELERY WORKER] Started checklist matching task")
    print(f"[CELERY WORKER] Task ID: {self.request.id}")
    print(f"[CELERY WORKER] Application: {application_number}")
    print("[CELERY WORKER] Queue: checklist_queue")
    print(f"{'=' * 60}\n")

    db = SessionLocal()
    audit_user = _deserialize_audit_user(audit_user_payload)
    try:
        ChecklistRepository(db).set_rerun_flag_without_versioning(application_number, 1, audit_user=audit_user)
        _update_task_state(
            self,
            task_type="checklist_match",
            application_number=application_number,
            status="processing",
            stage="Checklist matching in progress",
            progress=10,
        )
        _update_task_state(
            self,
            task_type="checklist_match",
            application_number=application_number,
            status="processing",
            stage="Comparing checklist fields",
            progress=60,
        )
        service = ChecklistService(db)
        result = service.trigger_matching(application_number, audit_user=audit_user)
        if result is None:
            raise ValueError("Checklist not found")
        payload = {
            "application_number": application_number,
            "items": jsonable_encoder(result),
        }
        _update_task_state(
            self,
            task_type="checklist_match",
            application_number=application_number,
            status="completed",
            stage="Checklist matching completed",
            progress=100,
            result=payload,
        )
        print(f"\n[CELERY WORKER] Completed checklist matching task for {application_number}\n")
        return payload
    except Exception as exc:
        ChecklistRepository(db).set_rerun_flag_without_versioning(application_number, 1, audit_user=audit_user)
        _update_task_state(
            self,
            task_type="checklist_match",
            application_number=application_number,
            status="failed",
            stage="Checklist matching failed",
            progress=0,
            error=str(exc),
        )
        raise
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.workers.checklist_worker.run_checklist_validation_worker",
    queue="checklist_queue",
)
def run_checklist_validation_worker(self, *, application_number: str, audit_user_payload: dict | None = None):
    print(f"\n{'=' * 60}")
    print("[CELERY WORKER] Started checklist validation task")
    print(f"[CELERY WORKER] Task ID: {self.request.id}")
    print(f"[CELERY WORKER] Application: {application_number}")
    print("[CELERY WORKER] Queue: checklist_queue")
    print(f"{'=' * 60}\n")

    db = SessionLocal()
    audit_user = _deserialize_audit_user(audit_user_payload)
    try:
        ChecklistRepository(db).set_rerun_flag_without_versioning(application_number, 1, audit_user=audit_user)
        _update_task_state(
            self,
            task_type="checklist_validation",
            application_number=application_number,
            status="processing",
            stage="Checklist validation in progress",
            progress=10,
        )
        _update_task_state(
            self,
            task_type="checklist_validation",
            application_number=application_number,
            status="processing",
            stage="Rebuilding checklist and matching fields",
            progress=60,
        )
        service = ChecklistService(db)
        result = service.run_validation(application_number, audit_user=audit_user)
        if result is None:
            raise ValueError("Checklist not found")
        payload = {
            "application_number": application_number,
            "items": jsonable_encoder(result),
        }
        _update_task_state(
            self,
            task_type="checklist_validation",
            application_number=application_number,
            status="completed",
            stage="Checklist validation completed",
            progress=100,
            result=payload,
        )
        print(f"\n[CELERY WORKER] Completed checklist validation task for {application_number}\n")
        return payload
    except Exception as exc:
        ChecklistRepository(db).set_rerun_flag_without_versioning(application_number, 1, audit_user=audit_user)
        _update_task_state(
            self,
            task_type="checklist_validation",
            application_number=application_number,
            status="failed",
            stage="Checklist validation failed",
            progress=0,
            error=str(exc),
        )
        raise
    finally:
        db.close()
