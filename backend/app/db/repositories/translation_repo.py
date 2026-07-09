from sqlalchemy.orm import Session
from app.db.models.document_extraction import Translation
from typing import List, Optional

class TranslationRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_translation(self, document_id: int, language: str, original_content: dict, translated_content: dict) -> Translation:
        # Check if a translation for this language already exists for this document
        existing = self.db.query(Translation).filter(
            Translation.document_id == document_id,
            Translation.language == language
        ).first()

        if existing:
            existing.original_content = original_content
            existing.translated_content = translated_content
            self.db.add(existing)
        else:
            db_translation = Translation(
                document_id=document_id,
                language=language,
                original_content=original_content,
                translated_content=translated_content
            )
            self.db.add(db_translation)
        
        self.db.commit()
        if existing:
            self.db.refresh(existing)
            return existing
        else:
            self.db.refresh(db_translation)
            return db_translation

    def get_translation(self, document_id: int, language: str) -> Optional[Translation]:
        return self.db.query(Translation).filter(
            Translation.document_id == document_id,
            Translation.language == language
        ).first()

    def list_translations(self, document_id: int) -> List[Translation]:
        return self.db.query(Translation).filter(
            Translation.document_id == document_id
        ).all()
