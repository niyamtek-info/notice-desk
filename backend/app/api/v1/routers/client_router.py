import json
import base64  # ✅ ADDED
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user

from app.services.client_service import ClientService
from app.api.v1.schemas.client_schema import (
    ClientResponse,
    ClientCreateRequest,
    ClientUpdateRequest
)
from app.api.v1.schemas.client_schema import (
    AOResponse,
    AOBulkCreateRequest,
    AOUpdateRequest
)

router = APIRouter()

# ====================================================
# CREATE CLIENT
# ====================================================
@router.post("/", response_model=ClientResponse)
async def create_client(
    request: Request,
    client_code: Optional[str] = Form(None),
    client_name: Optional[str] = Form(None),
    client_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    content_type = request.headers.get("content-type", "").lower()

    logo_data = None
    logo_file_name = None

    # ✅ JSON handling
    if content_type.startswith("application/json"):
        payload = await request.json()
        client_code = payload.get("client_code")
        client_name = payload.get("client_name")
        client_type = payload.get("client_type")
        description = payload.get("description")
        logo_data = payload.get("logo") or payload.get("logo_path")
        logo_file_name = payload.get("logo_file_name") or "logo.png"

    # ✅ FILE → BASE64 (IMPORTANT FIX)
    if logo:
        file_bytes = await logo.read()
        logo_data = base64.b64encode(file_bytes).decode("utf-8")
        logo_file_name = logo.filename

    if not client_code or not client_name or not client_type:
        raise HTTPException(400, "client_code, client_name, client_type required")

    return ClientService(db).create_client(
        client_code=client_code,
        client_name=client_name,
        client_type=client_type,
        description=description,
        logo_path=logo_data,
        logo_file_name=logo_file_name,
        audit_user=audit_user,
    )


# ====================================================
# GET ALL CLIENTS
# ====================================================
@router.get("/", response_model=List[ClientResponse])
def get_all_clients(db: Session = Depends(get_db)):
    return ClientService(db).get_all_clients()


# ====================================================
# ---------------- AO ROUTES ----------------
# ====================================================

# CREATE AO
@router.post("/aos", response_model=List[AOResponse])
def create_aos(
    payload: AOBulkCreateRequest,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    results = []

    for ao_data in payload.aos:

        signature_data = (

         getattr(ao_data, "signature_path", None)
        )

        signature_file_name = ao_data.signature_file_name or "signature.png"

        ao = ClientService(db).create_ao(
            client_code=ao_data.client_code,
            ao_name=ao_data.ao_name,
            ao_email=ao_data.ao_email,
            signature_path=signature_data,
            signature_file_name=signature_file_name,
            audit_user=audit_user,
        )

        results.append(ao)

    return results

# GET ALL AOs
@router.get("/aos", response_model=List[AOResponse])
def get_all_aos(db: Session = Depends(get_db)):
    return ClientService(db).get_all_aos()


# GET AOs BY CLIENT
@router.get("/{client_code}", response_model=List[AOResponse])
def get_aos_by_client(client_code: str, db: Session = Depends(get_db)):
    return ClientService(db).get_aos_by_client(client_code)


# UPDATE AO
@router.put("/aos/{ao_id}", response_model=AOResponse)
def update_ao(
    ao_id: int,
    payload: AOUpdateRequest,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return ClientService(db).update_ao(
        ao_id, payload.dict(exclude_unset=True), audit_user
    )


# DELETE AO
@router.delete("/aos/{ao_id}")
def delete_ao(
    ao_id: int,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return ClientService(db).delete_ao(ao_id, audit_user)


# ====================================================
# CLIENT ID ROUTES
# ====================================================

@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    return ClientService(db).get_client(client_id)


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    payload: ClientUpdateRequest,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return ClientService(db).update_client(
        client_id, payload.dict(exclude_unset=True), audit_user
    )


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return ClientService(db).delete_client(client_id, audit_user)