import asyncio
from app.db.base import Base
from app.db.session import engine

# Import all models so they are registered with Base.metadata
# These imports match app.db.base.py
from app.db.models.application import Application
from app.db.models.document_extraction import Document, DocumentFile, DocumentOCRText, DocumentExtractedData, ApplicationContext
from app.db.models.log import Log
from app.db.models.observation import Observation
from app.db.models.user import User
from app.db.models.extracted_data import (
    ExtractedSanctionLetter, 
    ExtractedLoanAgreement, 
    ExtractedMODT, 
    ExtractedSalesDeed, 
    MasterChecklist,
    ApplicationChecklist
)
from app.db.models.generated_report import GeneratedReport

from app.db.repositories.checklist_repo import MasterChecklistRepository
from app.db.repositories.template_repository import MasterTemplateRepository
from app.db.session import SessionLocal

def init_db():
    print("Checking database tables...")
    
    # Base.metadata.create_all checks for existence of tables and only creates if missing.
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables checked/created successfully!")
        
        # Seed Master Checklist
        print("Seeding Master Checklist...")
        db = SessionLocal()
        try:
            repo = MasterChecklistRepository(db)
            repo.seed_default_fields()
            print("Master Checklist seeded successfully!")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == "__main__":
    init_db()
