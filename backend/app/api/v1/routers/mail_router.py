from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.v1.controllers.communication_controller import CommunicationController
from app.schemas.communication_schema import (
    MailTemplateRequest,
    CommunicationCreate,
    CommunicationResponse,
    BulkNoticeDownloadRequest,
)
from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user

router = APIRouter()

@router.post("/generate")
async def generate_mail_template(
    request: MailTemplateRequest,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """
    Generate a mail template based on the request.
    """
    controller = CommunicationController(db)
    return controller.generate_mail_template(request)

@router.post("/", response_model=CommunicationResponse)
async def create_communication(
    request: CommunicationCreate,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """
    Save a communication record.
    """
    controller = CommunicationController(db)
    return await controller.create_communication(request, audit_user=audit_user)

@router.post("/generate-pdf")
async def generate_pdf(
    request: dict,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """
    Generate and download a PDF version of the communication.
    """
    controller = CommunicationController(db)
    return await controller.generate_pdf_response(request, audit_user=audit_user)


@router.post("/bulk-notice-download")
async def bulk_notice_download(
    request: BulkNoticeDownloadRequest,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """
    Download notices for multiple applications as a ZIP archive.
    """
    controller = CommunicationController(db)
    return await controller.bulk_download_notice(request, audit_user=audit_user)
