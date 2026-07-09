import asyncio

from app.core.celery_app import celery_app
from app.core.async_task_store import set_task
from app.db.session import SessionLocal
from app.services.translation_service import TranslationService


@celery_app.task(
    bind=True,
    name="app.workers.translation_worker.run_translation_worker",
    queue="translation_queue",
)
def run_translation_worker(self, *, record_id: str, target_language: str):
    db = SessionLocal()
    try:
        task_type = f"translation:{target_language.lower()}"
        set_task(
            self.request.id,
            {
                "task_type": task_type,
                "record_id": record_id,
                "target_language": target_language,
                "status": "processing",
                "stage": "Translation in progress",
                "progress": 15,
            },
        )
        set_task(
            self.request.id,
            {
                "task_type": task_type,
                "record_id": record_id,
                "target_language": target_language,
                "status": "processing",
                "stage": "Translating content",
                "progress": 65,
            },
        )
        service = TranslationService(db)
        translated_data = asyncio.run(
            service.translate_document_extraction(
                record_id=record_id,
                target_language=target_language,
            )
        )
        payload = {
            "record_id": record_id,
            "language": target_language,
            "translated_data": translated_data,
        }
        set_task(
            self.request.id,
            {
                "task_type": task_type,
                "record_id": record_id,
                "target_language": target_language,
                "status": "completed",
                "stage": "Translation completed",
                "progress": 100,
                "result": payload,
            },
        )
        return payload
    except Exception as exc:
        set_task(
            self.request.id,
            {
                "task_type": f"translation:{target_language.lower()}",
                "record_id": record_id,
                "target_language": target_language,
                "status": "failed",
                "stage": "Translation failed",
                "progress": 0,
                "error": str(exc),
            },
        )
        raise
    finally:
        db.close()
