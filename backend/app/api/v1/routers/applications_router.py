from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Form, File, UploadFile
from typing import Optional, List
from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user
from app.api.v1.controllers.applications_controller import ApplicationsController
from app.api.v1.schemas.applications_schema import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationListResponse,
    DeleteResponse,
)

router = APIRouter(tags=["Applications"])
controller = ApplicationsController()


@router.post("/manual", response_model=ApplicationResponse)
def create_record(
    payload: ApplicationCreate,
    audit_user: AuditUser = Depends(get_current_audit_user),
):

    result = controller.create_record(payload.data, audit_user=audit_user)

    return {
        "message": "Success",
        "data": result
    }


@router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return controller.upload_file(file, audit_user=audit_user)




@router.get("", response_model=ApplicationListResponse)
def list_records(
    client_name: Optional[str] = None,
    client_code: Optional[str] = None,
    batch_code: Optional[str] = None, 
    loan_account_number: Optional[str] = None,
    borrower_name: Optional[str] = None,
    location: Optional[str] = None,
    type_of_work: Optional[str] = None,  # ✅ ADD
    assigned_from: Optional[datetime] = Query(None),
    assigned_to: Optional[datetime] = Query(None),
    audit_user: AuditUser = Depends(get_current_audit_user),
):

    records = controller.list_records(
        client_name=client_name,
        client_code=client_code,
        loan_account_number=loan_account_number,
        batch_code = batch_code,
        borrower_name=borrower_name,
        location=location,
        type_of_work=type_of_work,
        assigned_from=assigned_from,
        assigned_to=assigned_to
    )

    return {
        "message": "Success",
        "data": records
    }


@router.get("/download-template")
def download_bulk_template(
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return controller.download_template()



@router.get("/{record_id}", response_model=ApplicationResponse)
def get_record(
    record_id: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    record = controller.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return {
        "data": record
    }


@router.get("/{record_id}/documents/view")
def get_document_view_url(
    record_id: str,
    filename: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    url = controller.get_document_url(record_id, filename)
    if not url:
        raise HTTPException(status_code=404, detail="Document or Application not found")
    return {"url": url}


@router.get("/search/query", response_model=ApplicationListResponse)
def search_records(
    q: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    results = controller.search_records(q)
    return {"items": results}


@router.put("/{record_id}", response_model=ApplicationResponse)
def update_record(
    record_id: str,
    payload: ApplicationCreate,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    result = controller.update_record(record_id, payload.data, audit_user=audit_user)
    return {
        "message": "Success",
        "data": result
    }


@router.delete("/{record_id}", response_model=DeleteResponse)
def delete_record(
    record_id: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    success = controller.delete_record(record_id, audit_user=audit_user)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")

    return {"message": "Record deleted successfully"}



