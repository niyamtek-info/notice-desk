from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ====================================================
# AO RESPONSE
# ====================================================
class AOResponse(BaseModel):
    id: int
    client_code: str
    ao_code: str
    ao_name: str
    ao_email: Optional[str]

    # Stored path (S3)
    signature_path: Optional[str]



    file_name: Optional[str] = None
    version: int
    is_active: bool

    class Config:
        from_attributes = True


# ====================================================
# CLIENT RESPONSE
# ====================================================
class ClientResponse(BaseModel):
    id: int
    client_code: str
    client_name: str
    client_type: str
    description: Optional[str]

    # Stored path (S3)
    logo_path: Optional[str]


    file_name: Optional[str] = None
    version: int
    is_active: bool
    created_at: datetime

    aos: List[AOResponse] = []

    class Config:
        from_attributes = True


# ====================================================
# AO CREATE REQUEST
# ====================================================
class AOCreateRequest(BaseModel):
    client_code: str
    ao_name: str
    ao_email: Optional[str] = None

    # ✅ base64 comes here
    signature_path: Optional[str] = None

    signature_file_name: Optional[str] = None


class AOBulkCreateRequest(BaseModel):
    aos: List[AOCreateRequest]


# ====================================================
# AO UPDATE REQUEST
# ====================================================
class AOUpdateRequest(BaseModel):
    ao_name: Optional[str] = None
    ao_email: Optional[str] = None
    is_active: Optional[bool] = None

    # ✅ base64 replace
    signature_path: Optional[str] = None

    signature_file_name: Optional[str] = None


# ====================================================
# CLIENT CREATE REQUEST
# ====================================================
class ClientCreateRequest(BaseModel):
    client_code: str
    client_name: str
    client_type: str
    description: Optional[str] = None

    # ✅ base64 comes here
    
    logo_path: Optional[str] = None

    logo_file_name: Optional[str] = None


# ====================================================
# CLIENT UPDATE REQUEST
# ====================================================
class ClientUpdateRequest(BaseModel):
    client_name: Optional[str] = None
    client_type: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    # ✅ base64 replace
    logo: Optional[str] = None   # 👈 ADD THIS
    logo_path: Optional[str] = None

    logo_file_name: Optional[str] = None