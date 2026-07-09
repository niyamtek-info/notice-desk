from sqlalchemy import Boolean, Column, String, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(36), index=True, nullable=False) # Maps to internal UUID
    application_number = Column(String(50), index=True, nullable=False)
    doc_type = Column(String(100), index=True)
    file_name = Column(String(255))
    document_name = Column(String(255))
    error_message = Column(Text, nullable=True)
    client_type = Column(String(50), nullable=False, default="UNKNOWN", server_default="UNKNOWN")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    files = relationship("DocumentFile", back_populates="document", uselist=False, cascade="all, delete-orphan")
    ocr_text = relationship("DocumentOCRText", back_populates="document", uselist=False, cascade="all, delete-orphan")
    extracted_data = relationship("DocumentExtractedData", back_populates="document", uselist=False, cascade="all, delete-orphan")
    application_context = relationship("ApplicationContext", back_populates="document", cascade="all, delete-orphan")
    translations = relationship("Translation", back_populates="document", cascade="all, delete-orphan")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")


class DocumentFile(Base):
    __tablename__ = "document_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    original_path = Column(String(500)) # S3 Path (processed PDF or extracted pages)
    original_pdf_path = Column(String(500)) # S3 Path (complete uploaded PDF)
    selected_page_range = Column(String(255)) # Page range string (e.g., "1-3,5,7-9")
    ocr_json_path = Column(String(500))
    original_llm_path = Column(String(500))
    parsed_llm_path = Column(String(500))

    document = relationship("Document", back_populates="files")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")


class DocumentOCRText(Base):
    __tablename__ = "document_ocr_text"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    ocr_text = Column(Text(length=16000000)) # LONGTEXT support for heavy documents

    document = relationship("Document", back_populates="ocr_text")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")


class DocumentExtractedData(Base):
    __tablename__ = "document_extracted_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    ai_parsed_output = Column(JSON) # Stores the flexible JSON output

    document = relationship("Document", back_populates="extracted_data")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")


class ApplicationContext(Base):
    __tablename__ = "application_context"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), index=True)
    father_name = Column(String(255))
    dob_year = Column(String(4))
    gender = Column(String(50))
    address = Column(Text)
    identity_number = Column(String(100), index=True) # PAN, Aadhar, etc.
    identity_type = Column(String(50)) # e.g. "PAN", "AADHAR", "VENDOR", etc.

    document = relationship("Document", back_populates="application_context")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")


class Translation(Base):
    __tablename__ = "translations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    language = Column(String(50), nullable=False) # e.g. "Tamil", "Hindi"
    
    original_content = Column(JSON) # Snapshot of what was translated
    translated_content = Column(JSON)
    
    document = relationship("Document", back_populates="translations")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

