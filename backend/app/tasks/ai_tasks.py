import asyncio

from fastapi.encoders import jsonable_encoder

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.translation_service import TranslationService


@celery_app.task(name="app.tasks.ai_tasks.run_translation_task", bind=True)
def run_translation_task(self, *, record_id: str, target_language: str):
    db = SessionLocal()
    try:
        service = TranslationService(db)
        translated_data = asyncio.run(
            service.translate_document_extraction(
                record_id=record_id,
                target_language=target_language,
            )
        )
        return {
            "record_id": record_id,
            "language": target_language,
            "translated_data": translated_data,
        }
    finally:
        db.close()
