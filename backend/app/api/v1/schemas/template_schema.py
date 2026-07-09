from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class MasterTemplateCreateRequest(BaseModel):
    client_code: str
    template_type: str
    batch_code: Optional[str] = None


class MasterTemplateResponse(BaseModel):
    id: int

    client_code: str
    client_name: str

    template_type: str
    service_code: str

    template_code: str
    file_path: str
    html_path: Optional[str] = None
    html_url: Optional[str] = None
    html_presigned_url: Optional[str] = None
    batch_code: Optional[str]
    header_image_name: Optional[str] = None
    footer_image_name: Optional[str] = None

    version: int
    is_active: bool

    created_at: datetime

    class Config:
        from_attributes = True


class MasterTemplateListResponse(BaseModel):
    templates: List[MasterTemplateResponse]
