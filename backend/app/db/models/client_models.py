from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from sqlalchemy import and_
from app.db.versioning import OPEN_END_DATE

class Client(Base):
    __tablename__ = "clients"


    id = Column(Integer, primary_key=True, index=True)
    client_code  = Column(String(50), nullable=False, index=True)
    client_name = Column(String(255), nullable=False)
    client_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    logo_path = Column(String(500), nullable=True)

    # Versioning
    version = Column(Integer, nullable=False, default=1, server_default="1")
    
    # Soft Delete
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")
    
    # Audit (with timezone)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")

    __table_args__ = (
        UniqueConstraint("client_code", "version", name="uq_client_code_version"),
        Index("idx_client_code_active", "client_code", "is_deleted", "end_date"),
    )

    # -------------------------------------------------
    # Active AO (latest versions only)
    # -------------------------------------------------
    aos = relationship(
        "AOInformation",
        primaryjoin=lambda: and_(
            Client.id == AOInformation.client_id,
            AOInformation.end_date == OPEN_END_DATE,
            AOInformation.is_deleted == False,
            AOInformation.is_active == True, 
        ),
        back_populates="client",
    )

    # -------------------------------------------------
    # All AO history (no filter)
    # -------------------------------------------------
    all_aos = relationship(
        "AOInformation",
        primaryjoin="Client.id == AOInformation.client_id",

        viewonly=True
    )

    templates = relationship("MasterTemplate", back_populates="client")

   

class AOInformation(Base):
    __tablename__ = "ao_information"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    ao_code = Column(String(100), nullable=False, index=True)
    client_code = Column(String(50), nullable=False, index=True)
    ao_name = Column(String(255), nullable=False)
    ao_email = Column(String(255), nullable=True)
    signature_path = Column(String(500), nullable=True)

    # Versioning
    version = Column(Integer, nullable=False, default=1, server_default="1")
    
    # Soft Delete
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")
    
    # Audit (with timezone)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")

    # Unique constraint: ao_code per client (versioned)
    __table_args__ = (
    UniqueConstraint(
        "client_code",
        "ao_code",
        "version",
        name="uq_ao_client_code_version"
    ),
    Index(
        "idx_ao_client_code_active",
        "client_code",
        "is_deleted",
        "end_date"
    ),
    Index(
        "idx_ao_code_client",
        "ao_code",
        "client_code"
    )
    
    )

    # Relationship
    client = relationship("Client", back_populates="aos")

class TemplateType(Base):
    __tablename__ = "template_types"

    id = Column(Integer, primary_key=True, index=True)

    template_type = Column(String(100), nullable=False, unique=True)
    service_code = Column(String(50), nullable=False, unique=True)

    # 🔥 Versioning (optional but keep consistent)
    version = Column(Integer, nullable=False, default=1, server_default="1")

    # 🔥 Soft delete
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

    # 🔥 FULL AUDIT (same as your system)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)
    effective_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")

    # 🔥 Relationship
    templates = relationship("MasterTemplate", back_populates="template_type_rel")

class MasterTemplate(Base):
    __tablename__ = "master_templates"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    client_name = Column(String(255), nullable=False, index=True)
    batch_code = Column(String(100), nullable=True, index=True)
    header_image_name = Column(String(255), nullable=True)
    footer_image_name = Column(String(255), nullable=True)

    # 🔥 NEW FK
    template_type_id = Column(Integer, ForeignKey("template_types.id"), nullable=False)

    template_code = Column(String(100), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    html_path = Column(String(500), nullable=True)

    # Versioning
    version = Column(Integer, nullable=False, default=1, server_default="1")

    # Soft Delete
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)
    effective_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")

    # Relationships
    client = relationship("Client", back_populates="templates")
    template_type_rel = relationship(
    "TemplateType",
    back_populates="templates",
    lazy="joined"
    )

    __table_args__ = (
    UniqueConstraint("template_code", "version", name="uq_master_templates_template_code_version"),
    Index("idx_master_template_client_active", "client_id", "is_deleted", "end_date"),
    Index("idx_template_type_fk", "template_type_id"),
)
