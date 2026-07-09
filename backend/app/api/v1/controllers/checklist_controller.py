from sqlalchemy.orm import Session
from app.services.checklist_service import ChecklistService
from app.api.v1.schemas.checklist_schema import (
    ApplicationChecklistCreate,
    ApplicationChecklistBulkUpdateItem,
)
from app.db.models.document_extraction import Document
from app.db.versioning import live_filter
from app.api.v1.dependencies.auth import AuditUser
from fastapi import HTTPException
from typing import Union

class ChecklistController:
    def __init__(self, db: Session):
        self.db = db
        self.service = ChecklistService(db)

    def get_checklist(self, application_number: str):
        checklist = self.service.get_checklist(application_number)
        if not checklist:
            has_documents = self.db.query(Document).filter(
                Document.application_number == application_number,
                *live_filter(Document),
            ).first()
            if has_documents:
                return {
                    "status": "not_initialized",
                    "message": "No Data found Please Run Validation",
                "application_number": application_number,
                "documents_uploaded": True,
                "rerun_validation": 1,
                "items": [],
            }
            raise HTTPException(status_code=404, detail="Checklist not found")
        return checklist

    def create_checklist(self, obj_in: ApplicationChecklistCreate, audit_user: AuditUser | None = None):
        existing = self.service.get_checklist(obj_in.application_number)
        if existing:
            raise HTTPException(status_code=400, detail="Checklist already exists")
        return self.service.create_checklist(obj_in, audit_user=audit_user)

    def update_checklist(
        self,
        application_number: str,
        obj_in: Union[ApplicationChecklistBulkUpdateItem, list[ApplicationChecklistBulkUpdateItem]],
        audit_user: AuditUser | None = None,
    ):
        items = obj_in if isinstance(obj_in, list) else [obj_in]
        updated = self.service.update_checklist_bulk(application_number, items, audit_user=audit_user)
        if not updated:
            raise HTTPException(status_code=404, detail="Checklist row(s) not found")
        return updated
