from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from app.db.base_class import Base

class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(50), nullable=False, index=True)
    pair_code = Column(String(50), nullable=True, index=True)  # âœ… ADD THIS
    
    observation = Column(Text, nullable=False)  # The main text/title
    made_by = Column(String(50), default="AI")
    severity = Column(String(50), default="Medium")
    status = Column(String(50), default="Processing")
    comments = Column(Text, nullable=True)
    review_by = Column(String(100), default="System")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

