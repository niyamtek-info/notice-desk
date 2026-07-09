from typing import Optional

from app.api.v1.dependencies.auth import AuditUser
from app.core.celery_app import celery_app
from app.core.progress_store import set_progress
from app.db.session import SessionLocal
from app.services.extractor_service import ExtractorService


def _deserialize_audit_user(audit_user_payload: dict | None) -> AuditUser | None:
    if not audit_user_payload:
        return None
    return AuditUser(
        user_id=audit_user_payload.get("user_id"),
        email=audit_user_payload.get("email") or "System",
        full_name=audit_user_payload.get("full_name"),
    )


@celery_app.task(
    bind=True,
    name="app.workers.extraction_worker.run_extraction_worker",
    queue="extraction_queue",
)
def run_extraction_worker(
    self,
    *,
    file_id: str,
    doc_type: str,
    application_number: str,
    filename: str,
    file_path: str,
    document_name: Optional[str] = None,
    username: Optional[str] = None,
    audit_user_payload: dict | None = None,
    language: Optional[str] = None,
    original_file_path: Optional[str] = None,
    selected_page_range: Optional[str] = None,
):
    db = SessionLocal()
    audit_user = _deserialize_audit_user(audit_user_payload)
    service = ExtractorService(db)
    try:
        set_progress(
            file_id,
            {
                "status": "processing",
                "stage": "Extraction started",
                "progress": 5,
                "doc_type": doc_type,
                "application_number": application_number,
                "document_name": document_name,
                "filename": filename,
                "task_id": self.request.id,
            },
        )

        result = service.process_document(
            file=None,
            doc_type=doc_type,
            application_number=application_number,
            audit_user=audit_user,
            language=language,
            file_id=file_id,
            filename=filename,
            file_path=file_path,
            document_name=document_name,
            original_file_path=original_file_path,
            selected_page_range=selected_page_range,
        )

        set_progress(
            file_id,
            {
                "status": "completed",
                "progress": 100,
                "stage": "Completed",
                "task_id": self.request.id,
                "result": result,
            },
        )
        return result
    except Exception as exc:
        service._persist_processing_error(
            record_id=file_id,
            application_number=application_number,
            doc_type=doc_type,
            file_name=filename,
            document_name=document_name,
            s3_original=None,
            error_message=str(exc),
            audit_user=audit_user,
        )
        # Clean up original temp file on error
        if original_file_path:
            import os
            try:
                if os.path.exists(original_file_path):
                    os.remove(original_file_path)
            except Exception as cleanup_err:
                print(f"Cleanup error: {cleanup_err}")
        set_progress(
            file_id,
            {
                "status": "failed",
                "stage": "Extraction failed",
                "progress": 0,
                "doc_type": doc_type,
                "application_number": application_number,
                "document_name": document_name,
                "error": str(exc),
                "task_id": self.request.id,
            },
        )
        raise
    finally:
        db.close()