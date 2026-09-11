from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user
from app.api.v1.schemas.report_schema import (
    BulkReportDownloadRequest,
    ReportResponse,
    ReportUpdateRequest,
    ReportGenerateRequest,
)
from app.services.report_service import ReportService


router = APIRouter(
    prefix="/report",
    tags=["Report"]
)


# =========================================================
# BULK DOWNLOAD
# =========================================================
@router.post("/bulk-download")
def bulk_download_reports(
    payload: BulkReportDownloadRequest,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    service = ReportService(db)
    try:
        return service.bulk_download_reports(payload.application_numbers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/generate", response_model=ReportResponse)
def generate_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    service = ReportService(db)
    try:
        report = service.generate_report(payload.application_number, audit_user=audit_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not report:
        raise HTTPException(status_code=404, detail="Report generation failed")
    return report


# =========================================================
# GET REPORT (VIEW / EDIT SCREEN LOAD)
# =========================================================
@router.get("/{application_number}", response_model=ReportResponse)
def get_report(
    application_number: str,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    service = ReportService(db)
    report = service.get_report(application_number)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return report


# =========================================================
# CREATE REPORT (First Save)
# =========================================================
@router.post("/{application_number}", response_model=ReportResponse)
def create_report(
    application_number: str,
    report_data: ReportUpdateRequest,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    service = ReportService(db)
    return service.create_report(
        application_number,
        report_data.model_dump(exclude_unset=True),
        audit_user=audit_user,
    )


# =========================================================
# UPDATE REPORT (Normal / Admin Overwrite)
# =========================================================
@router.put("/{application_number}", response_model=ReportResponse)
def update_report(
    application_number: str,
    update_data: ReportUpdateRequest,
    admin_overwrite: bool = Query(False),
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    service = ReportService(db)

    updated_report = service.update_report(
        application_number,
        update_data.model_dump(exclude_unset=True),
        admin_overwrite=admin_overwrite,
        audit_user=audit_user,
    )

    if not updated_report:
        raise HTTPException(status_code=404, detail="Report not found")

    return updated_report


# =========================================================
# SNAPSHOT (Optional Versioning Ready)
# =========================================================
@router.post("/{application_number}/snapshot")
def create_report_snapshot(
    application_number: str,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    service = ReportService(db)
    snapshot = service.save_report_snapshot(application_number)

    if not snapshot:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "message": "Snapshot saved",
        "created_at": snapshot.created_at
    }
