from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool
from typing import Dict, Any
from app.services.observation_service import ObservationService
from app.api.v1.controllers.observation_controller import ObservationController
from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user

router = APIRouter(tags=["Observations"])

service = ObservationService()
controller = ObservationController(service)

@router.get("/{application_number}")
async def get_observations(
    application_number: str,
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """
    Fetches the generated observations from the filesystem.
    """
    return await run_in_threadpool(controller.get_observations, application_number)

@router.put("/{application_number}")
async def update_observations(
    application_number: str,
    payload: Dict[str, Any],
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    """
    Updates the observations manually.
    """
    return await run_in_threadpool(controller.update_observations, application_number, payload)
