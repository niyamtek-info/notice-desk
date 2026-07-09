from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class CommunicationBase(BaseModel):
    application_number: str
    type: str
    status: str
    template_name: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    html_path: Optional[str] = None
    pdf_path: Optional[str] = None
    recipient: str
    sender: Optional[str] = None
    meta_data: Optional[dict] = None

class CommunicationCreate(CommunicationBase):
    pass

class CommunicationUpdate(BaseModel):
    status: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    meta_data: Optional[dict] = None

class CommunicationResponse(CommunicationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MailTemplateRequest(BaseModel):
    application_number: str
    template_name: str
    email: str
    contact: str
    sender: Optional[str] = None

    # 🔥 ADD THESE
    header_style: Optional[str] = None
    footer_style: Optional[str] = None
    seal_style: Optional[str] = None

    ao_code: Optional[str] = None
    ao_name: Optional[str] = None
    ao_designation: Optional[str] = None

    date: Optional[str] = None


class BulkNoticeDownloadRequest(BaseModel):
    template_id: int
    ao_code: str
    application_numbers: List[str]
    
