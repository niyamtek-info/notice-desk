from app.db.base_class import Base
from app.db.models.application import Application
from app.db.models.document_extraction import Document, DocumentFile, DocumentOCRText, DocumentExtractedData, ApplicationContext
from app.db.models.observation import Observation
from app.db.models.user import User
from app.db.models.extracted_data import (
    ExtractedSanctionLetter, 
    ExtractedLoanAgreement, 
    ExtractedMODT, 
    ExtractedMODTProperty,
    ExtractedSalesDeed, 
    ExtractedForeclosureStatement,
    ExtractedForeclosureCoApplicant,
    ExtractedForeclosureNote,
    ExtractedStatementOfAccount,
    ExtractedSOATransaction,
    ExtractedLegalReport,
    MasterChecklist,
    ApplicationChecklist
)
from app.db.models.communication import Communication
from app.db.models.client_models import (
    Client,
    AOInformation,
    MasterTemplate,
    TemplateType

)
from app.db.models.safari_notice import SarfaesiMaster
# from app.db.models.bulk_notice import BulkNotice, BulkNoticeBatch
# Import all models here for Alembic
# Base classes for ORM models
