from sqlalchemy.orm import Session
from app.db.models.communication import Communication

class CommunicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, obj_in: dict) -> Communication:
        db_obj = Communication(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
