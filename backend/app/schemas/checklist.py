from typing import Optional, List
from pydantic import BaseModel

class ChecklistItemBase(BaseModel):
    field_name: str
    document_type: str
    is_checked: bool
    remarks: Optional[str] = None

class ChecklistItemCreate(ChecklistItemBase):
    application_id: str

class ChecklistItemUpdate(BaseModel):
    is_checked: Optional[bool] = None
    remarks: Optional[str] = None

class ChecklistItemResponse(ChecklistItemBase):
    id: int
    application_id: str

    class Config:
        from_attributes = True

class ChecklistMatrixResponse(BaseModel):
    application_id: str
    items: List[ChecklistItemResponse]
