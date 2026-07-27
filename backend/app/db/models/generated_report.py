from sqlalchemy import Boolean, Column, String, DateTime, Integer, Date, Text, Enum, BigInteger, JSON, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.db.models.application import Application
from app.db.versioning import OPEN_END_DATE


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --------------------------------------------------
    # RELATION TO APPLICATION
    # --------------------------------------------------
    record_id = Column(
        String(36),
        nullable=True,
        index=True
    )

    application_number = Column(
        String(50),
        index=True,
        nullable=False
    )

    application = relationship(
        "Application",
        primaryjoin=lambda: and_(
            GeneratedReport.record_id == Application.record_id,
            Application.is_deleted == False,
            Application.end_date == OPEN_END_DATE,
            Application.is_active == True,
        ),
        foreign_keys="[GeneratedReport.record_id]",
        viewonly=True,
        uselist=False,
    )

    # --------------------------------------------------
    # STATUS
    # --------------------------------------------------
    status = Column(
        Enum("In-Progress", "Completed", name="report_status_enum"),
        default="In-Progress",
        nullable=False
    )
    is_report_overridden = Column(Integer, default=1, server_default="1", nullable=False)
    rerun_report = Column(Integer, default=1, server_default="1", nullable=False)

    # --------------------------------------------------
    # BASIC DETAILS
    # --------------------------------------------------
    loan_account_number = Column(String(100), nullable=True)
    borrower_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    arc_name = Column(String(255), nullable=True)

    borrower_address = Column(Text, nullable=True)
    borrower_address_also_at = Column(Text, nullable=True)

    # --------------------------------------------------
    # CO BORROWERS (1â€“6)
    # --------------------------------------------------
    co_borrower_1_name = Column(String(255), nullable=True)
    co_borrower_1_address = Column(Text, nullable=True)
    co_borrower_1_address_also_at = Column(Text, nullable=True)

    co_borrower_2_name = Column(String(255), nullable=True)
    co_borrower_2_address = Column(Text, nullable=True)
    co_borrower_2_address_also_at = Column(Text, nullable=True)

    co_borrower_3_name = Column(String(255), nullable=True)
    co_borrower_3_address = Column(Text, nullable=True)
    co_borrower_3_address_also_at = Column(Text, nullable=True)

    co_borrower_4_name = Column(String(255), nullable=True)
    co_borrower_4_address = Column(Text, nullable=True)
    co_borrower_4_address_also_at = Column(Text, nullable=True)

    co_borrower_5_name = Column(String(255), nullable=True)
    co_borrower_5_address = Column(Text, nullable=True)
    co_borrower_5_address_also_at = Column(Text, nullable=True)

    co_borrower_6_name = Column(String(255), nullable=True)
    co_borrower_6_address = Column(Text, nullable=True)
    co_borrower_6_address_also_at = Column(Text, nullable=True)  # added

    # --------------------------------------------------
    # PROPERTY
    # --------------------------------------------------
    description_of_schedule_property = Column(Text, nullable=True)
    schedule_property_descriptions = Column(JSON, nullable=True)
    survey_no = Column(String(100), nullable=True)
    plot_number = Column(String(100), nullable=True)
    door_number = Column(String(100), nullable=True)
    property_street = Column(Text, nullable=True)
    property_locality = Column(String(255), nullable=True)
    property_town = Column(String(255), nullable=True)
    taluk = Column(String(255), nullable=True)
    village = Column(String(255), nullable=True)
    district = Column(String(255), nullable=True)
    pincode = Column(String(20), nullable=True)

    # --------------------------------------------------
    # NPA / NOTICE
    # --------------------------------------------------
    date_of_npa = Column(DateTime, nullable=True)
    dpd_as_on_notice = Column(String(100), nullable=True)
    sec_13_2_notice_date = Column(DateTime, nullable=True)

    # --------------------------------------------------
    # LOAN DETAILS
    # --------------------------------------------------
    loan_amount = Column(BigInteger, nullable=True)
    loan_amount_words = Column(Text, nullable=True)
    loan_agreement_date = Column(DateTime, nullable=True)

    disbursal_date = Column(DateTime, nullable=True)
    disbursal_amount = Column(BigInteger, nullable=True)

    future_principal = Column(BigInteger, nullable=True)

    # --------------------------------------------------
    # FINANCIAL BREAKUP
    # --------------------------------------------------
    principal_outstanding = Column(BigInteger, nullable=True)
    instalment_overdue_amount = Column(BigInteger, nullable=True)
    interest_on_termination = Column(BigInteger, nullable=True)
    late_payment_penalty = Column(BigInteger, nullable=True)
    cheque_bounce_charges = Column(BigInteger, nullable=True)
    other_amount = Column(BigInteger, nullable=True)
    foreclosure_charges = Column(BigInteger, nullable=True)

    total_outstanding = Column(BigInteger, nullable=True)
    total_outstanding_words = Column(Text, nullable=True)
    as_on_date = Column(DateTime, nullable=True)

    # --------------------------------------------------
    # SOA
    # --------------------------------------------------
    soa_bank_name = Column(String(255), nullable=True)
    soa_loan_account_number = Column(String(100), nullable=True)
    soa_sanction_date = Column(Date, nullable=True)
    soa_sanction_amount = Column(String(50), nullable=True)
    soa_disbursed_amount = Column(String(50), nullable=True)
    soa_interest_rate = Column(String(50), nullable=True)
    soa_loan_status = Column(String(100), nullable=True)

    # --------------------------------------------------
    # FORECLOSURE
    # --------------------------------------------------
    foreclosure_bank_name = Column(String(255), nullable=True)
    foreclosure_loan_account_number = Column(String(100), nullable=True)
    foreclosure_outstanding_principal = Column(String(50), nullable=True)
    foreclosure_total_amount_payable = Column(String(50), nullable=True)
    foreclosure_valid_upto_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")


