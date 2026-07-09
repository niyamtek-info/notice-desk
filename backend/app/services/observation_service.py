from typing import Dict, Any, Optional
from app.db.repositories.observation_repo import ObservationRepository

class ObservationService:
    def __init__(self):
        self.repo = ObservationRepository()

    def get_by_application(self, application_number: str) -> Dict[str, Any]:
        """Fetches observations for a given application."""
        data = self.repo.load(application_number)
        if data is None:
            return {"application_id": application_number, "recommended_documents": []}
        return data

    def update(self, application_number: str, payload: Dict[str, Any]) -> bool:
        """Manually updates observations."""
        return self.repo.save(application_number, payload)
