from sqlalchemy import Boolean, Column, String, DateTime, Integer, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("business_code", "version", name="uq_applications_business_code_version"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(String(36), index=True, nullable=False)
    batch_code = Column(String(100), nullable=True, index=True)
    business_code = Column(String(50), index=True, nullable=False)
    type_of_work = Column(String(100), nullable=True)
    assigned_date = Column(DateTime, nullable=True)
    source_type = Column(Enum("Manual", "Upload", "Bulk Upload"), nullable=True)

    client_name = Column(String(255), nullable=True)
    loan_account_number = Column(String(100), nullable=True)
    loan_requester_name = Column(String(200), nullable=True)
    state = Column(String(255), nullable=True)
    report_status = Column(String(50), nullable=False, default="Not_Available", server_default="Not_Available")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")
