from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ApplicationCreate(BaseModel):
    """
    Incoming request schema.
    Accepts either:
    - {"data": {...}} (nested payload), or
    - a flat payload with application fields at the top level.
    """
    data: Dict[str, Any] = Field(..., description="Application form payload")

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return value

        if "data" in value and isinstance(value["data"], dict):
            return value

        return {"data": value}

class ApplicationData(BaseModel):
    record_id: str
    application_no: str
    batch_code: Optional[str] = None
    loan_account_number: Optional[str] = None
    borrower_name: Optional[str] = None
    client_name: Optional[str] = None
    location: Optional[str] = None
    assigned_date: Optional[str] = None
    report_status: Optional[str] = None
    type_of_work: Optional[str] = None
    source_type: Optional[str] = None
    report_source: Optional[str] = None
    has_document_for_report: Optional[bool] = None


class ApplicationListResponse(BaseModel):
    data: List[ApplicationData]

class ApplicationResponse(BaseModel):
    data: ApplicationData




class DeleteResponse(BaseModel):
    """
    Response for delete operation.
    """
    message: str = Field(..., example="Deleted successfully")
