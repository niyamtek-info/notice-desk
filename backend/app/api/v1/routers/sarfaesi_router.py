from typing import List
from fastapi import Request
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user
from app.api.v1.schemas.sarfaesi_schema import (
    SarfaesiCreate,
    SarfaesiResponse,
    SarfaesiUpdate,
)
from app.db.session import get_db
from app.services.sarfaesi_service import SarfaesiService

router = APIRouter(prefix="/sarfaesi", tags=["Sarfaesi"])


# 🔥 GENERATE FROM APPLICATION
@router.post("/generate/{application_number}", response_model=SarfaesiResponse)
def generate_sarfaesi_from_application(
    application_number: str,
    db: Session = Depends(get_db),
    current_user: AuditUser = Depends(get_current_audit_user),
):
    service = SarfaesiService(db)
    return service.generate_sarfaesi_from_application(application_number, current_user)


# 🔥 GET ALL
@router.get("/", response_model=List[SarfaesiResponse])
def list_sarfaesi(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: AuditUser = Depends(get_current_audit_user),
):
    service = SarfaesiService(db)
    return service.get_all_sarfaesi(skip=skip, limit=limit)


# 🔥 GET BY APPLICATION NUMBER
@router.get("/application/{application_number}", response_model=SarfaesiResponse)
def get_sarfaesi_by_application_number(
    application_number: str,
    db: Session = Depends(get_db),
    current_user: AuditUser = Depends(get_current_audit_user),
):
    service = SarfaesiService(db)
    return service.get_sarfaesi_by_application_number(application_number)


# 🔥 UPDATE + SYNC
@router.put("/application/{application_number}", response_model=SarfaesiResponse)
def update_sarfaesi_and_sync(
    application_number: str,
    obj_in: dict,  
    db: Session = Depends(get_db),
    current_user: AuditUser = Depends(get_current_audit_user),
):
    service = SarfaesiService(db)
    return service.update_sarfaesi_and_sync(application_number, obj_in, current_user)


# 🔥 DELETE (SOFT DELETE)
@router.delete("/application/{application_number}")
def delete_sarfaesi(
    application_number: str,
    db: Session = Depends(get_db),
    current_user: AuditUser = Depends(get_current_audit_user),
):
    service = SarfaesiService(db)
    service.delete_sarfaesi(application_number, current_user)
    return {"message": "Record deleted successfully"}


# # 🔥 DOCUMENT UPDATE
# @router.post("/document-update/{application_number}")
# def update_from_documents(
#     application_number: str,
#     extracted_data: dict,
#     db: Session = Depends(get_db),
#     current_user: AuditUser = Depends(get_current_audit_user),
# ):
#     service = SarfaesiService(db)
#     return service.update_sarfaesi_from_documents(
#         application_number,
#         extracted_data,
#         current_user
#     )


# # 🔥 VALIDATE CHECKLIST
# @router.get("/validate/{application_number}")
# def validate_checklist(
#     application_number: str,
#     db: Session = Depends(get_db),
#     current_user: AuditUser = Depends(get_current_audit_user),
# ):
#     service = SarfaesiService(db)
#     return service.validate_checklist(application_number)


# # 🔥 GENERATE REPORT
# @router.post("/report/{application_number}")
# def generate_report(
#     application_number: str,
#     db: Session = Depends(get_db),
#     current_user: AuditUser = Depends(get_current_audit_user),
# ):
#     service = SarfaesiService(db)
#     return service.generate_report(application_number)