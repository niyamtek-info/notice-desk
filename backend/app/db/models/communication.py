from sqlalchemy import Boolean, Column, DateTime, String, Integer, Text, JSON
from sqlalchemy.sql import func
from app.db.base_class import Base

class Communication(Base):
    __tablename__ = "communications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(50), index=True)
    type = Column(String(20))  # email, whatsapp, etc.
    status = Column(String(20))  # draft, sent, failed
    template_name = Column(String(100))
    subject = Column(String(255))
    content = Column(Text)
    html_path = Column(String(500), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    recipient = Column(String(255))
    sender = Column(String(255))
    meta_data = Column(JSON, nullable=True)  # Using meta_data to avoid collision with metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

