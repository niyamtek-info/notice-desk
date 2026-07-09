from fastapi import HTTPException
from typing import Dict, Any
from app.services.observation_service import ObservationService

class ObservationController:
    def __init__(self, service: ObservationService):
        self.service = service

    def get_observations(self, application_number: str):
        return self.service.get_by_application(application_number)

    def update_observations(self, application_number: str, payload: Dict[str, Any]):
        success = self.service.update(application_number, payload)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update observations")
        return {"status": "success", "message": "Observations updated"}
