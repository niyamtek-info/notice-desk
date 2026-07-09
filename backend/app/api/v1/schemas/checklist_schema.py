from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class ApplicationChecklistBase(BaseModel):
    application_number: str
    pair_code: str
    document_a: str
    document_b: str
    attribute_code: str
    attribute_label: str
    document_a_value: Optional[str] = None
    document_b_value: Optional[str] = None
    match_status: Optional[str] = 'NOT_AVAILABLE'
    confidence: Optional[str] = 'LOW'
    remarks: Optional[str] = None
    is_match_overridden: Optional[bool] = False
    rerun_validation: Optional[int] = 0

class ApplicationChecklistCreate(ApplicationChecklistBase):
    pass

class ApplicationChecklistUpdate(BaseModel):
    document_a_value: Optional[str] = None
    document_b_value: Optional[str] = None
    match_status: Optional[str] = None
    confidence: Optional[str] = None
    remarks: Optional[str] = None
    is_match_overridden: Optional[bool] = None


class ApplicationChecklistBulkUpdateItem(BaseModel):
    attribute_code: str
    document_a_value: Optional[str] = None
    document_b_value: Optional[str] = None
    match_status: Optional[str] = None
    confidence: Optional[str] = None
    remarks: Optional[str] = None
    is_match_overridden: Optional[bool] = None

class ApplicationChecklistResponse(ApplicationChecklistBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ApplicationChecklistListResponse(BaseModel):
    items: List[ApplicationChecklistResponse]


class RunValidationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    application_number: str = Field(alias="Application_number")
