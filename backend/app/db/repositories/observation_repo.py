from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.observation import Observation
from datetime import datetime

class ObservationRepository:
    def __init__(self):
        pass

    def get_db(self) -> Session:
        return SessionLocal()

    def get_observations(self, application_number: str) -> List[Dict[str, Any]]:
        db = self.get_db()
        try:
            obs_list = db.query(Observation).filter(Observation.application_number == application_number).all()
            return [
                {
                    "id": obs.id,
                    "title": obs.observation,       # Mapping to 'title' for backwards comaptibility if needed, or use 'observation'
                    "observation": obs.observation, # Using correct field name
                    "made_by": obs.made_by,
                    "severity": obs.severity,
                    "status": obs.status,
                    "comments": obs.comments,
                    "review_by": obs.review_by,
                    "explanation": obs.observation # Map observation to explanation too if UI expects it? 
                    # Actually, the 'load' method used to return {"recommended_documents": [...]}. 
                    # The Service expects that structure.
                }
                for obs in obs_list
            ]
        finally:
            db.close()

    # Legacy load support to match Service expectation
    def load(self, application_number: str) -> Optional[Dict[str, Any]]:
        obs_list = self.get_observations(application_number)
        if not obs_list:
            return None
        
        # Transform flat list to the structure expected by frontend/service
        # Service returns: {"application_id": app_num, "recommended_documents": [...]}
        # Frontend Observation.tsx maps: doc.title || doc.explanation -> observation
        
        # We need to return a dict that matches the JSON structure if we want minimal service changes.
        return {
            "application_id": application_number,
            "recommended_documents": obs_list
        }

    def save(self, application_number: str, data: Dict[str, Any]) -> bool:
        """
        Saves observations using Upsert strategy to preserve timestamps.
        """
        db = self.get_db()
        try:
            docs = data.get("recommended_documents", [])
            incoming_ids = [doc.get("id") for doc in docs if doc.get("id")]
            
            # 1. Delete removed observations
            # Delete any observation for this app that is NOT in the incoming IDs
            db.query(Observation).filter(
                Observation.application_number == application_number,
                Observation.id.notin_(incoming_ids)
            ).delete(synchronize_session=False)

            # 2. Upsert (Update existing or Insert new)
            for doc in docs:
                obs_id = doc.get("id")
                
                # Determine main text
                main_text = doc.get("title") or doc.get("observation") or doc.get("document_name") or "Unknown Observation"
                
                if obs_id:
                    # Update existing
                    existing_obs = db.query(Observation).filter(Observation.id == obs_id).first()
                    if existing_obs:
                        existing_obs.observation = main_text
                        existing_obs.made_by = doc.get("made_by", "AI")
                        existing_obs.severity = doc.get("severity", "Medium")
                        existing_obs.status = doc.get("status", "Processing")
                        existing_obs.comments = doc.get("comments", "")
                        existing_obs.review_by = doc.get("review_by", "System")
                        # updated_at is handled by onupdate=func.now() in model
                else:
                    # Insert new
                    new_obs = Observation(
                        application_number=application_number,
                        observation=main_text,
                        made_by=doc.get("made_by", "AI"),
                        severity=doc.get("severity", "Medium"),
                        status=doc.get("status", "Processing"),
                        comments=doc.get("comments", ""),
                        review_by=doc.get("review_by", "System")
                    )
                    db.add(new_obs)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error saving observations: {e}")
            return False
        finally:
            db.close()
