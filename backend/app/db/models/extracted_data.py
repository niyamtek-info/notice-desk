from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, JSON, Boolean, Numeric, Date, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class ExtractedSanctionLetter(Base):
    __tablename__ = "extracted_sanction_letters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(50), index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    loan_account_number = Column(String(100))
    borrower_name = Column(String(255))
    borrower_address = Column(Text)
    borrower_address_also_at = Column(Text)
    borrower_pan = Column(String(50))
    
    # Co-borrowers (up to 5 as per user checklist)
    co_borrower_1_name = Column(String(255))
    co_borrower_1_address = Column(Text)
    co_borrower_1_address_also_at = Column(Text)
    co_borrower_1_pan = Column(String(50))
    
    co_borrower_2_name = Column(String(255))
    co_borrower_2_address = Column(Text)
    co_borrower_2_address_also_at = Column(Text)
    co_borrower_2_pan = Column(String(50))
    
    co_borrower_3_name = Column(String(255))
    co_borrower_3_address = Column(Text)
    co_borrower_3_address_also_at = Column(Text)
    co_borrower_3_pan = Column(String(50))
    
    co_borrower_4_name = Column(String(255))
    co_borrower_4_address = Column(Text)
    co_borrower_4_address_also_at = Column(Text)
    co_borrower_4_pan = Column(String(50))
    
    co_borrower_5_name = Column(String(255))
    co_borrower_5_address = Column(Text)
    co_borrower_5_address_also_at = Column(Text)
    co_borrower_5_pan = Column(String(50))

    sanction_date = Column(String(50))
    sanction_amount = Column(String(100))
    loan_amount = Column(String(100))
    loan_tenure = Column(String(50))
    interest_rate = Column(String(50))
    emi_amount = Column(String(100))
    repayment_frequency = Column(String(50))
    property_description = Column(Text)
    property_address = Column(Text)
    survey_number = Column(String(100))
    plot_number = Column(String(100))
    boundary_north = Column(String(255))
    boundary_south = Column(String(255))
    boundary_east = Column(String(255))
    boundary_west = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")
    

class ExtractedLoanAgreement(Base):
    __tablename__ = "extracted_loan_agreements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(50), index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    sanction_date = Column(String(50))
    loan_agreement_date = Column(String(50))
    loan_amount = Column(String(100))
    loan_amount_in_words = Column(Text)
    borrower_name = Column(String(255))
    borrower_address = Column(Text)
    borrower_address_also_at = Column(Text)
    borrower_pan = Column(String(50))
    borrower_pan = Column(String(50))
    
    # Co-borrowers (up to 5 as per user checklist)
    co_borrower_1_name = Column(String(255))
    co_borrower_1_address = Column(Text)
    co_borrower_1_address_also_at = Column(Text)
    co_borrower_1_pan = Column(String(50))
    co_borrower_1_pan = Column(String(50))
    
    co_borrower_2_name = Column(String(255))
    co_borrower_2_address = Column(Text)
    co_borrower_2_address_also_at = Column(Text)
    co_borrower_2_pan = Column(String(50))
    co_borrower_2_pan = Column(String(50))
    
    co_borrower_3_name = Column(String(255))
    co_borrower_3_address = Column(Text)
    co_borrower_3_address_also_at = Column(Text)
    co_borrower_3_pan = Column(String(50))
    co_borrower_3_pan = Column(String(50))
    
    co_borrower_4_name = Column(String(255))
    co_borrower_4_address = Column(Text)
    co_borrower_4_address_also_at = Column(Text)
    co_borrower_4_pan = Column(String(50))
    co_borrower_4_pan = Column(String(50))
    
    co_borrower_5_name = Column(String(255))
    co_borrower_5_address = Column(Text)
    co_borrower_5_address_also_at = Column(Text)
    co_borrower_5_pan = Column(String(50))
    co_borrower_5_pan = Column(String(50))
    property_address = Column(Text)
    property_description = Column(Text)
    survey_number = Column(String(100))
    plot_number = Column(String(100))
    boundary_north = Column(String(255))
    boundary_south = Column(String(255))
    boundary_east = Column(String(255))
    boundary_west = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")
    

class ExtractedMODT(Base):
    __tablename__ = "extracted_modts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(50), index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    document_type = Column(String(255))
    execution_date = Column(String(50))
    registration_date = Column(String(50))
    document_number = Column(String(100))
    book_number = Column(String(100))
    sub_registrar_office = Column(String(255))

    depositor_name = Column(String(255))
    depositor_address = Column(Text)
    depositor_address_also_at = Column(Text)
    depositee_name = Column(String(255))
    depositee_address = Column(Text)
    
    # Co-borrowers/Depositors (up to 5)
    co_borrower_1_name = Column(String(255))
    co_borrower_1_address = Column(Text)
    co_borrower_1_address_also_at = Column(Text)
    co_borrower_1_pan = Column(String(50))
    
    co_borrower_2_name = Column(String(255))
    co_borrower_2_address = Column(Text)
    co_borrower_2_address_also_at = Column(Text)
    co_borrower_2_pan = Column(String(50))
    
    co_borrower_3_name = Column(String(255))
    co_borrower_3_address = Column(Text)
    co_borrower_3_address_also_at = Column(Text)
    co_borrower_3_pan = Column(String(50))
    
    co_borrower_4_name = Column(String(255))
    co_borrower_4_address = Column(Text)
    co_borrower_4_address_also_at = Column(Text)
    co_borrower_4_pan = Column(String(50))
    
    co_borrower_5_name = Column(String(255))
    co_borrower_5_address = Column(Text)
    co_borrower_5_address_also_at = Column(Text)
    co_borrower_5_pan = Column(String(50))

    loan_amount = Column(String(100))
    loan_amount_in_words = Column(Text)
    loan_tenure = Column(String(100))

    stamp_duty = Column(String(100))
    registration_fee = Column(String(100))
    total_charges = Column(String(100))
    deposited_documents_json = Column(JSON)
    
    properties = relationship(
        "ExtractedMODTProperty",
        back_populates="modt",
        cascade="all, delete-orphan",
        order_by="ExtractedMODTProperty.property_index",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")


class ExtractedMODTProperty(Base):
    __tablename__ = "extracted_modt_properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    modt_id = Column(Integer, ForeignKey("extracted_modts.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_key = Column(String(100))
    property_index = Column(Integer, nullable=False, default=1, server_default="1")
    property_description = Column(Text)
    raw_property_text = Column(Text)
    survey_numbers = Column(String(255))
    plot_number = Column(String(100))
    extent = Column(String(100))
    extent_unit = Column(String(50))
    village = Column(String(255))
    taluka_or_mandal = Column(String(255))
    district = Column(String(255))
    state = Column(String(100))
    pincode = Column(String(20))
    boundary_north = Column(String(255))
    boundary_south = Column(String(255))
    boundary_east = Column(String(255))
    boundary_west = Column(String(255))
    address_remarks = Column(Text)
    confidence = Column(String(50))
    source_page_from = Column(Integer)
    source_page_to = Column(Integer)

    modt = relationship("ExtractedMODT", back_populates="properties")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

class ExtractedSalesDeed(Base):
    __tablename__ = "extracted_sales_deeds"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(50), index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Document Information
    document_category = Column(String(255))
    document_sub_category = Column(String(255))
    document_number = Column(String(100))
    book_number = Column(String(100))
    execution_date = Column(String(50))
    execution_location = Column(String(255))
    state = Column(String(100))
    number_of_pages = Column(String(50))
    sub_registrar_office = Column(String(255))
    document_remarks = Column(Text)
    
    # Property Info
    property_address = Column(Text)
    latitude = Column(String(50))
    longitude = Column(String(50))
    
    # Payment Summary
    market_value = Column(String(100))
    sale_transaction_value = Column(String(100))
    payment_remarks = Column(Text)
    raw_description = Column(Text)
    remarks = Column(Text)
    
    
    # Relationships
    from sqlalchemy.orm import relationship
    vendors = relationship("ExtractedSalesDeedVendor", back_populates="sales_deed", cascade="all, delete-orphan")
    purchasers = relationship("ExtractedSalesDeedPurchaser", back_populates="sales_deed", cascade="all, delete-orphan")
    witnesses = relationship("ExtractedSalesDeedWitness", back_populates="sales_deed", cascade="all, delete-orphan")
    schedules = relationship("ExtractedSalesDeedSchedule", back_populates="sales_deed", cascade="all, delete-orphan")
    payment_details = relationship("ExtractedSalesDeedPaymentDetail", back_populates="sales_deed", cascade="all, delete-orphan")
    parent_flows = relationship("ExtractedSalesDeedParentFlow", back_populates="sales_deed", cascade="all, delete-orphan")
    terms = relationship("ExtractedSalesDeedTerm", back_populates="sales_deed", cascade="all, delete-orphan")
    authority = relationship("ExtractedSalesDeedAuthority", back_populates="sales_deed", cascade="all, delete-orphan", uselist=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Vendor Table
class ExtractedSalesDeedVendor(Base):
    __tablename__ = "extracted_sales_deed_vendors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sales_deed_id = Column(Integer, ForeignKey("extracted_sales_deeds.id", ondelete="CASCADE"))
    
    name = Column(String(255))
    relationship_text = Column(String(100))
    relation_name = Column(String(255))
    pan = Column(String(50))
    aadhar = Column(String(50))
    date_of_birth_age = Column(String(100))
    gender = Column(String(50))
    address = Column(Text)
    signature_biometric_photo = Column(String(50))
    remarks = Column(Text)
    
    from sqlalchemy.orm import relationship
    sales_deed = relationship("ExtractedSalesDeed", back_populates="vendors")
    representative = relationship("ExtractedSalesDeedVendorRepresentative", back_populates="vendor", cascade="all, delete-orphan", uselist=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Vendor Representative Table
class ExtractedSalesDeedVendorRepresentative(Base):
    __tablename__ = "extracted_sales_deed_vendor_representatives"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("extracted_sales_deed_vendors.id", ondelete="CASCADE"))
    
    name = Column(String(255))
    relationship_text = Column(String(100))
    relations_name = Column(String(255))
    representation_capacity = Column(String(255))
    document_reference = Column(String(255))
    id_value = Column(String(100))
    date_of_birth_age = Column(String(100))
    gender = Column(String(50))
    address = Column(Text)
    signature_biometric_photo = Column(String(50))
    remarks = Column(Text)
    
    from sqlalchemy.orm import relationship
    vendor = relationship("ExtractedSalesDeedVendor", back_populates="representative")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Purchaser Table
class ExtractedSalesDeedPurchaser(Base):
    __tablename__ = "extracted_sales_deed_purchasers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sales_deed_id = Column(Integer, ForeignKey("extracted_sales_deeds.id", ondelete="CASCADE"))
    
    name = Column(String(255))
    relationship_text = Column(String(100))
    relations_name = Column(String(255))
    pan = Column(String(50))
    aadhar = Column(String(50))
    date_of_birth_age = Column(String(100))
    gender = Column(String(50))
    address = Column(Text)
    signature_biometric_photo = Column(String(50))
    remarks = Column(Text)
    
    from sqlalchemy.orm import relationship
    sales_deed = relationship("ExtractedSalesDeed", back_populates="purchasers")
    representative = relationship("ExtractedSalesDeedPurchaserRepresentative", back_populates="purchaser", cascade="all, delete-orphan", uselist=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Purchaser Representative Table
class ExtractedSalesDeedPurchaserRepresentative(Base):
    __tablename__ = "extracted_sales_deed_purchaser_representatives"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    purchaser_id = Column(Integer, ForeignKey("extracted_sales_deed_purchasers.id", ondelete="CASCADE"))
    
    name = Column(String(255))
    relationship_text = Column(String(100))
    relations_name = Column(String(255))
    representation_capacity = Column(String(255))
    document_reference = Column(String(255))
    id_value = Column(String(100))
    date_of_birth_age = Column(String(100))
    gender = Column(String(50))
    address = Column(Text)
    signature_biometric_photo = Column(String(50))
    remarks = Column(Text)
    
    from sqlalchemy.orm import relationship
    purchaser = relationship("ExtractedSalesDeedPurchaser", back_populates="representative")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Witness Table
class ExtractedSalesDeedWitness(Base):
    __tablename__ = "extracted_sales_deed_witnesses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sales_deed_id = Column(Integer, ForeignKey("extracted_sales_deeds.id", ondelete="CASCADE"))
    
    name = Column(String(255))
    relationship_text = Column(String(100))
    relations_name = Column(String(255))
    pan = Column(String(50))
    aadhar = Column(String(50))
    date_of_birth_age = Column(String(100))
    gender = Column(String(50))
    address = Column(Text)
    signature_biometric_photo = Column(String(50))
    remarks = Column(Text)
    
    from sqlalchemy.orm import relationship
    sales_deed = relationship("ExtractedSalesDeed", back_populates="witnesses")
    representative = relationship("ExtractedSalesDeedWitnessRepresentative", back_populates="witness", cascade="all, delete-orphan", uselist=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Witness Representative Table
class ExtractedSalesDeedWitnessRepresentative(Base):
    __tablename__ = "extracted_sales_deed_witness_representatives"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    witness_id = Column(Integer, ForeignKey("extracted_sales_deed_witnesses.id", ondelete="CASCADE"))
    
    name = Column(String(255))
    relationship_text = Column(String(100))
    relations_name = Column(String(255))
    representation_capacity = Column(String(255))
    document_reference = Column(String(255))
    id_value = Column(String(100))
    date_of_birth_age = Column(String(100))
    gender = Column(String(50))
    address = Column(Text)
    signature_biometric_photo = Column(String(50))
    remarks = Column(Text)
    
    from sqlalchemy.orm import relationship
    witness = relationship("ExtractedSalesDeedWitness", back_populates="representative")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Schedule Table (Schedule_A, Schedule_B, Schedule_C)
class ExtractedSalesDeedSchedule(Base):
    __tablename__ = "extracted_sales_deed_schedules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sales_deed_id = Column(Integer, ForeignKey("extracted_sales_deeds.id", ondelete="CASCADE"))
    
    schedule_type = Column(String(50))  # Schedule_A, Schedule_B, Schedule_C
    raw_text = Column(Text)
    property_extent = Column(String(100))
    property_extent_unit = Column(String(50))
    plot_dimension = Column(String(100))
    survey_number = Column(String(255))
    old_survey_number = Column(String(255))
    ts_number = Column(String(255))
    
    # Property Address (nested object)
    plot_number = Column(String(100))
    village_street_name = Column(String(255))
    jurisdiction = Column(String(255))
    address_remarks = Column(Text)
    
    # Boundaries (nested object)
    boundary_east = Column(String(255))
    boundary_west = Column(String(255))
    boundary_north = Column(String(255))
    boundary_south = Column(String(255))
    
    from sqlalchemy.orm import relationship
    sales_deed = relationship("ExtractedSalesDeed", back_populates="schedules")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Payment Details Table
class ExtractedSalesDeedPaymentDetail(Base):
    __tablename__ = "extracted_sales_deed_payment_details"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sales_deed_id = Column(Integer, ForeignKey("extracted_sales_deeds.id", ondelete="CASCADE"))
    
    payment_detail_key = Column(String(100))  # e.g., "Payment_Details_1"
    transaction_key = Column(String(100))     # e.g., "Transaction_1"
    transaction_value = Column(Text)
    
    from sqlalchemy.orm import relationship
    sales_deed = relationship("ExtractedSalesDeed", back_populates="payment_details")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Parent Document Flow Table
class ExtractedSalesDeedParentFlow(Base):
    __tablename__ = "extracted_sales_deed_parent_flows"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sales_deed_id = Column(Integer, ForeignKey("extracted_sales_deeds.id", ondelete="CASCADE"))
    
    flow_sequence = Column(Integer)  # 1, 2, 3, 4, 5, 6
    flow_value = Column(Text)
    
    from sqlalchemy.orm import relationship
    sales_deed = relationship("ExtractedSalesDeed", back_populates="parent_flows")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Terms and Conditions Table
class ExtractedSalesDeedTerm(Base):
    __tablename__ = "extracted_sales_deed_terms"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sales_deed_id = Column(Integer, ForeignKey("extracted_sales_deeds.id", ondelete="CASCADE"))
    
    term_sequence = Column(Integer)  # 1, 2, 3, 4, 5
    term_text = Column(Text)
    
    from sqlalchemy.orm import relationship
    sales_deed = relationship("ExtractedSalesDeed", back_populates="terms")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# Authority Table (single record per deed)
class ExtractedSalesDeedAuthority(Base):
    __tablename__ = "extracted_sales_deed_authority"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sales_deed_id = Column(Integer, ForeignKey("extracted_sales_deeds.id", ondelete="CASCADE"), unique=True)
    
    designation = Column(String(255))
    sub_registrar_name = Column(String(255))
    sub_registrar_signature = Column(String(255))
    sub_registrar_office = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    remarks = Column(Text)
    
    from sqlalchemy.orm import relationship
    sales_deed = relationship("ExtractedSalesDeed", back_populates="authority")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

class ExtractedLegalReport(Base):
    __tablename__ = "extracted_legal_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(50), index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    report_title = Column(String(255))
    law_firm_name = Column(String(255))
    advocate_name = Column(String(255))
    document_category = Column(String(255))
    document_sub_category = Column(String(255))
    reference_number = Column(String(100))
    report_date = Column(String(50))
    proposal_number = Column(String(100))
    document_state = Column(String(100))
    issuing_office_address = Column(Text)
    remarks = Column(Text)

    bank_or_nbfc_name = Column(String(255))
    branch_name = Column(String(255))
    addressed_to = Column(Text)

    primary_borrower_name = Column(String(255))
    co_borrowers_json = Column(JSON)
    borrower_full_name_and_address = Column(Text)
    borrower_constitution = Column(String(255))

    owner_name = Column(String(255))
    co_owners_json = Column(JSON)
    owner_address = Column(Text)
    owner_constitution = Column(String(255))

    loan_account_number = Column(String(100))
    loan_type = Column(String(100))
    product_type = Column(String(100))

    property_address = Column(Text)
    property_type = Column(String(100))
    village_or_town = Column(String(255))
    taluk_or_circle = Column(String(255))
    district = Column(String(255))
    property_state = Column(String(100))
    registration_district = Column(String(255))
    sub_registration_district = Column(String(255))
    survey_number = Column(String(255))
    re_survey_number = Column(String(255))
    plot_or_site_number = Column(String(100))
    block_number = Column(String(100))
    layout_name = Column(String(255))
    total_extent_hectares = Column(String(100))
    total_extent_acres = Column(String(100))
    total_extent_sqft = Column(String(100))
    total_extent_sqmeter = Column(String(100))
    land_use_type = Column(String(255))
    properties_list_json = Column(JSON)

    documents_scrutinized_json = Column(JSON)
    documents_to_be_obtained_json = Column(JSON)

    original_title_holder = Column(String(255))
    chain_of_title_summary = Column(Text)
    current_title_holder = Column(String(255))
    mode_of_acquisition = Column(String(255))
    title_tracing_period_from = Column(String(50))
    title_tracing_period_to = Column(String(50))

    encumbrance_certificate_number = Column(String(100))
    ec_period_from = Column(String(50))
    ec_period_to = Column(String(50))
    charges_registered = Column(Text)
    existing_mortgage_or_encumbrance = Column(Text)
    modt_details = Column(Text)

    is_title_clear_and_marketable = Column(String(50))
    is_property_free_of_encumbrance = Column(String(50))
    is_original_title_document_in_order = Column(String(50))
    is_property_within_municipal_limits = Column(String(50))
    is_property_agricultural_or_nonagricultural = Column(String(50))
    is_property_leasehold = Column(String(50))
    lis_pendens_status = Column(String(50))
    minors_interest = Column(String(255))
    power_of_attorney_status = Column(String(255))
    noc_from_society_or_builder = Column(String(255))
    sarfaesi_applicability = Column(String(255))
    urban_land_ceiling_act_applicable = Column(String(255))
    tenancy_laws_applicable = Column(String(255))
    site_inspection_done = Column(String(255))
    additional_document_required = Column(String(255))
    municipal_tax_paid_status = Column(String(255))
    municipal_tax_assessed_in_name_of = Column(String(255))
    construction_as_per_sanction_plan = Column(String(255))

    patta_number = Column(String(100))
    property_tax_receipt_number = Column(String(100))
    assessment_number = Column(String(100))
    tax_assessed_in_name_of = Column(String(255))
    tax_receipt_date = Column(String(50))

    title_certification_opinion = Column(Text)
    safeguards_to_be_observed = Column(Text)
    observation_remarks = Column(Text)
    certifying_advocate_name = Column(String(255))
    certification_date = Column(String(50))
    certification_place = Column(String(255))
    notes_and_conditions_json = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

class MasterChecklist(Base):
    __tablename__ = "master_checklists"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pair_code = Column(String(50), index=True)
    document_a = Column(String(50))
    document_b = Column(String(50))
    attribute_code = Column(String(100))
    attribute_label = Column(String(255))
    is_must = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

class ApplicationChecklist(Base):
    __tablename__ = "application_checklists"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(50), index=True)
    pair_code = Column(String(50), index=True)
    document_a = Column(String(50))
    document_b = Column(String(50))
    attribute_code = Column(String(100))
    attribute_label = Column(String(255))
    document_a_value = Column(Text)
    document_b_value = Column(Text)
    match_status = Column(Enum('MATCH','MISMATCH','NOT_AVAILABLE'), default='NOT_AVAILABLE')
    confidence = Column(Enum('HIGH','MEDIUM','LOW'), default='LOW')
    remarks = Column(Text)
    is_match_overridden = Column(Boolean, default=False)
    rerun_validation = Column(Integer, default=1, server_default="1", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")
    

# --- Foreclosure Statement Models ---

class ExtractedForeclosureStatement(Base):
    __tablename__ = "extracted_foreclosure_statements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(50), index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Document Information
    bank_name = Column(String(255))
    document_category = Column(String(100))
    document_sub_category = Column(String(100))
    document_date = Column(Date)
    loan_account_number = Column(String(100), index=True)
    loan_type = Column(String(100))
    issuing_branch = Column(String(255))
    state = Column(String(100))
    remarks = Column(Text)
    
    # Borrower Details
    borrower_name = Column(String(255))
    address = Column(Text)
    
    # Loan Details
    loan_sanction_date = Column(Date)
    foreclosure_request_date = Column(Date)
    foreclosure_calculation_date = Column(Date)
    outstanding_principal = Column(Numeric(18, 2))
    pending_installments = Column(Numeric(18, 2))
    principal_outstanding_overdue = Column(Numeric(18, 2))
    instalment_overdue_amount_interest_overview = Column(Numeric(18, 2))
    interest_till_date = Column(Numeric(18, 2))
    additional_interest = Column(Numeric(18, 2))
    per_day_interest = Column(Numeric(18, 2))
    
    # Charges Breakup
    foreclosure_charges = Column(Numeric(18, 2))
    prepayment_charges = Column(Numeric(18, 2))
    late_payment_fee = Column(Numeric(18, 2))
    late_payment_interest = Column(Numeric(18, 2))
    cheque_bounce_charges = Column(Numeric(18, 2))
    retrieval_other_charges = Column(Numeric(18, 2))
    other_amount_charges = Column(Numeric(18, 2))
    gst = Column(Numeric(18, 2))
    refund_if_any = Column(Numeric(18, 2))
    waiver_amount = Column(Numeric(18, 2))
    
    total_amount_payable = Column(Numeric(18, 2))
    valid_upto_date = Column(Date)
    
    
    # Relationships
    co_applicants = relationship("ExtractedForeclosureCoApplicant", back_populates="foreclosure", cascade="all, delete-orphan")
    notes = relationship("ExtractedForeclosureNote", back_populates="foreclosure", cascade="all, delete-orphan")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

class ExtractedForeclosureCoApplicant(Base):
    __tablename__ = "extracted_foreclosure_co_applicants"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    foreclosure_id = Column(Integer, ForeignKey("extracted_foreclosure_statements.id", ondelete="CASCADE"))
    name = Column(String(255))
    
    foreclosure = relationship("ExtractedForeclosureStatement", back_populates="co_applicants")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

class ExtractedForeclosureNote(Base):
    __tablename__ = "extracted_foreclosure_notes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    foreclosure_id = Column(Integer, ForeignKey("extracted_foreclosure_statements.id", ondelete="CASCADE"))
    note_text = Column(Text)
    
    foreclosure = relationship("ExtractedForeclosureStatement", back_populates="notes")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

# --- Statement of Accounts Models ---

class ExtractedStatementOfAccount(Base):
    __tablename__ = "extracted_statement_of_accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(50), index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Document Information
    bank_name = Column(String(255))
    document_category = Column(String(100))
    document_sub_category = Column(String(100))
    statement_as_on_date = Column(Date)
    loan_account_number = Column(String(100), index=True)
    branch = Column(String(255))
    currency = Column(String(20))
    
    # Borrower Details
    borrower_name = Column(String(255))
    co_applicant_name = Column(String(255))
    address = Column(Text)
    pan_number = Column(String(50))
    contact_details = Column(String(255))
    
    # Loan Details
    loan_type = Column(String(100))
    sanction_date = Column(Date)
    sanction_amount = Column(Numeric(18, 2))
    disbursed_amount = Column(Numeric(18, 2))
    tenure_months = Column(String(50))
    interest_rate = Column(String(50))
    interest_type = Column(String(50))
    emi_amount = Column(Numeric(18, 2))
    repayment_frequency = Column(String(100))
    repayment_mode = Column(String(100))
    loan_status = Column(String(100))
    
    
    # Relationships
    transactions = relationship("ExtractedSOATransaction", back_populates="soa", cascade="all, delete-orphan")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

class ExtractedSOATransaction(Base):
    __tablename__ = "extracted_soa_transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    soa_id = Column(Integer, ForeignKey("extracted_statement_of_accounts.id", ondelete="CASCADE"))
    
    transaction_date = Column(Date)
    value_date = Column(Date)
    transaction_type = Column(String(100))
    description = Column(Text)
    debit_amount = Column(Numeric(18, 2))
    credit_amount = Column(Numeric(18, 2))
    balance = Column(Numeric(18, 2))
    
    soa = relationship("ExtractedStatementOfAccount", back_populates="transactions")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

