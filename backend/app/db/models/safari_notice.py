from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, Text, and_, event
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.models.application import Application
from app.db.base_class import Base
from app.db.models.client_models import Client
from app.db.versioning import OPEN_END_DATE
from app.utils.date_utils import parse_datetime


def _to_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    import re

    cleaned = str(value).strip().replace(",", "")
    cleaned = re.sub(r"(?i)rs\.?", "", cleaned)
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    if cleaned in {"", "-", ".", "-."}:
        return None
    try:
        return Decimal(cleaned)
    except Exception:
        return None


class SarfaesiMaster(Base):
    __tablename__ = "sarfaesi_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_number = Column(String(100), nullable=True, index=True)

    # =========================
    # BASIC DETAILS
    # =========================
    niyamtek_user = Column(String(50), nullable=True, index=True)
    client_code = Column(String(100), nullable=True, index=True)
    client = relationship(
        Client,
        primaryjoin=lambda: and_(
            SarfaesiMaster.client_code == Client.client_code,
            Client.is_deleted == False,
            Client.end_date == OPEN_END_DATE,
            Client.is_active == True,
        ),
        foreign_keys="[SarfaesiMaster.client_code]",
        viewonly=True,
        uselist=False,
    )
    application = relationship(
        Application,
        primaryjoin=lambda: and_(
            SarfaesiMaster.application_number == Application.business_code,
            Application.is_deleted == False,
            Application.end_date == OPEN_END_DATE,
            Application.is_active == True,
        ),
        foreign_keys="[SarfaesiMaster.application_number]",
        viewonly=True,
        uselist=False,
    )
    company_name = Column(String(255), nullable=True)
    loan_account_no = Column(String(100), nullable=True, index=True)
    borrower_name = Column(String(255), nullable=True)
    trust_number = Column(String(100), nullable=True)
    assignment_agreement_date = Column(Date, nullable=True)
    ao_name = Column(String(100), nullable=True)
    branch = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    property_address = Column(Text, nullable=True)
    borrower_address = Column(Text, nullable=True)
    borrower_address_alt = Column(Text, nullable=True)
    report_source = Column(String(50), nullable=True)
    has_document = Column(Boolean, nullable=False, default=False, server_default="0")
    # =========================
    # CO-BORROWERS (1–6)
    # =========================
    co_borrower_1_name = Column(String(255))
    co_borrower_1_address = Column(Text)
    co_borrower_1_address_alt = Column(Text)

    co_borrower_2_name = Column(String(255))
    co_borrower_2_address = Column(Text)
    co_borrower_2_address_alt = Column(Text)

    co_borrower_3_name = Column(String(255))
    co_borrower_3_address = Column(Text)
    co_borrower_3_address_alt = Column(Text)

    co_borrower_4_name = Column(String(255))
    co_borrower_4_address = Column(Text)
    co_borrower_4_address_alt = Column(Text)

    co_borrower_5_name = Column(String(255))
    co_borrower_5_address = Column(Text)
    co_borrower_5_address_alt = Column(Text)

    co_borrower_6_name = Column(String(255))
    co_borrower_6_address = Column(Text)

    property_description = Column(Text)

    # =========================
    # GUARANTORS
    # =========================
    guarantor_1_name = Column(String(255))
    guarantor_1_address = Column(Text)

    guarantor_2_name = Column(String(255))
    guarantor_2_address = Column(Text)
    # =========================
    # LOAN DETAILS
    # =========================
    npa_date = Column(Date)
    dpd = Column(Integer)

    disbursement_type = Column(String(100))
    disbursal_date = Column(Date)
    disbursal_amount = Column(Numeric(18, 2))

    loan_agreement_date = Column(Date)
    loan_amount = Column(Numeric(18, 2))
    loan_amount_words = Column(Text, nullable=True)
    future_principal = Column(Numeric(18, 2))
    principal_outstanding = Column(Numeric(18, 2))

    instalment_overdue = Column(Numeric(18, 2))
    interest_on_termination = Column(Numeric(18, 2))
    late_payment_penalty = Column(Numeric(18, 2))
    cheque_bounce_charges = Column(Numeric(18, 2))
    other_amount = Column(Numeric(18, 2))
    foreclosure_charges = Column(Numeric(18, 2))

    total_outstanding = Column(Numeric(18, 2))
    fcl_as_on_date = Column(Date, nullable=True)
    total_outstanding_words = Column(Text)

    # =========================
    # 13(2) DEMAND NOTICE
    # =========================
    notice_13_2_amount = Column(Numeric(18, 2))
    notice_13_2_date = Column(Date)
    notice_dispatch_date = Column(Date)
    notice_pasting_date = Column(Date)

    delivery_status = Column(String(100))
    delivery_status_date = Column(Date, nullable=True)
    delivered_address = Column(Text)
    undelivered_address = Column(Text)
    total_address = Column(Text)

    publication_date_13_2 = Column(Date)
    publication_english_13_2 = Column(Text)
    publication_local_13_2 = Column(Text)

    # =========================
    # 13(4) SYMBOLIC POSSESSION
    # =========================
    symbolic_possession_date_13_4 = Column(Date)
    symbolic_dispatch_date_13_4 = Column(Date)
    symbolic_delivery_status_13_4 = Column(String(100))
    symbolic_delivery_status_date_13_4 = Column(Date, nullable=True)
    symbolic_photo_13_4 = Column(String(100))

    symbolic_publication_date_13_4 = Column(Date)
    symbolic_pub_english_13_4 = Column(Text)
    symbolic_pub_local_13_4 = Column(Text)

    matured_date_13_4 = Column(Date, nullable=True)
    vacation_notice_moveable = Column(String(100), nullable=True)
    vacation_notice_immoveable = Column(String(100), nullable=True)

    # =========================
    # CJM / CMM
    # =========================
    cjm_filing_date = Column(Date)
    court_name = Column(String(255))
    case_number = Column(String(100))
    crm_pl_date = Column(Date)
    crm_pl_no = Column(String(100))
    next_hearing_date = Column(Date)

    ov_date = Column(Date)
    order_date = Column(Date)
    court_ao_name = Column(String(255))
    advocate_details = Column(Text)
    adv_com_name = Column(String(255), nullable=True)

    inventory_status = Column(String(100))

    # =========================
    # PHYSICAL POSSESSION
    # =========================
    physical_possession_date = Column(Date)
    physical_dispatch_date = Column(Date)
    physical_delivery_status = Column(String(100))
    physical_delivery_status_date = Column(Date, nullable=True)
    physical_photo = Column(String(100))

    physical_publication_date = Column(Date)
    physical_pub_english = Column(Text)
    physical_pub_local = Column(Text)

    physical_vacation_notice_moveable = Column(String(255), nullable=True)
    physical_vacation_notice_immoveable = Column(String(255), nullable=True)

    # =========================
    # AUCTION DETAILS
    # =========================
    auction_notice_date = Column(Date)
    auction_date = Column(Date)
    auction_publication_date = Column(Date)

    auction_pub_english = Column(Text)
    auction_pub_local = Column(Text)

    reserve_price = Column(Numeric(18, 2))
    sold_price = Column(Numeric(18, 2))
    auction_status = Column(String(100))

    inspection_start = Column(DateTime)
    inspection_end = Column(DateTime)

    emd_last_date = Column(DateTime)
    auction_start = Column(DateTime)
    auction_end = Column(DateTime)

    bid_extension_time = Column(String(100), nullable=True)
    total_extensions = Column(String(100), nullable=True)

    emd_amount = Column(Numeric(18, 2))
    bid_increment = Column(Numeric(18, 2))
    total_bid_count = Column(Integer)

    authorised_officer = Column(String(255))

    # =========================
    # POST SALE
    # =========================
    post_sale_notice = Column(Text)
    sale_confirmation_date = Column(Date)
    sale_certificate_date = Column(Date)

    available_documents = Column(Text)
    non_available_documents = Column(Text)

    discrepancy_doc = Column(Text)
    discrepancy_reason = Column(Text)

    next_actionable_stage = Column(String(255))
    next_step_recommended = Column(String(255))

    niyamtek_remarks = Column(Text)
    batch_code = Column(String(100), nullable=True, index=True)
    rerun_report = Column(Integer, default=1, server_default="1", nullable=False)

    # =========================
    # EXTRA FIELDS
    # =========================
    pos = Column(String(100), nullable=True)
    outstanding_amount = Column(Numeric(18, 2), nullable=True)
    sold_reg_date = Column(Date, nullable=True)
    sarfaesi_category = Column(String(255), nullable=True)
    case_status = Column(String(50), nullable=True)
    co_borrower_6_address_alt = Column(Text, nullable=True)

    # =========================
    # AUDIT
    # =========================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100))

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100))

    version = Column(Integer, nullable=False, default=1, server_default="1")
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=False, server_default="9999-12-12 00:00:00")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")

    @property
    def loan_account_number(self):
        return self.loan_account_no

    @loan_account_number.setter
    def loan_account_number(self, value):
        self.loan_account_no = value

    @property
    def borrower_address_also_at(self):
        return self.borrower_address_alt

    @borrower_address_also_at.setter
    def borrower_address_also_at(self, value):
        self.borrower_address_alt = value

    @property
    def co_borrower_1_address_also_at(self):
        return self.co_borrower_1_address_alt

    @co_borrower_1_address_also_at.setter
    def co_borrower_1_address_also_at(self, value):
        self.co_borrower_1_address_alt = value

    @property
    def co_borrower_2_address_also_at(self):
        return self.co_borrower_2_address_alt

    @co_borrower_2_address_also_at.setter
    def co_borrower_2_address_also_at(self, value):
        self.co_borrower_2_address_alt = value

    @property
    def co_borrower_3_address_also_at(self):
        return self.co_borrower_3_address_alt

    @co_borrower_3_address_also_at.setter
    def co_borrower_3_address_also_at(self, value):
        self.co_borrower_3_address_alt = value

    @property
    def co_borrower_4_address_also_at(self):
        return self.co_borrower_4_address_alt

    @co_borrower_4_address_also_at.setter
    def co_borrower_4_address_also_at(self, value):
        self.co_borrower_4_address_alt = value

    @property
    def co_borrower_5_address_also_at(self):
        return self.co_borrower_5_address_alt

    @co_borrower_5_address_also_at.setter
    def co_borrower_5_address_also_at(self, value):
        self.co_borrower_5_address_alt = value

    @property
    def date_of_npa(self):
        return self.npa_date

    @date_of_npa.setter
    def date_of_npa(self, value):
        self.npa_date = value

    @property
    def dpd_as_on_notice(self):
        return self.dpd

    @dpd_as_on_notice.setter
    def dpd_as_on_notice(self, value):
        self.dpd = value

    @property
    def sec_13_2_notice_date(self):
        return self.notice_13_2_date

    @sec_13_2_notice_date.setter
    def sec_13_2_notice_date(self, value):
        self.notice_13_2_date = value

    @property
    def instalment_overdue_amount(self):
        return self.instalment_overdue

    @instalment_overdue_amount.setter
    def instalment_overdue_amount(self, value):
        self.instalment_overdue = value

    @property
    def location(self):
        return self.state

    @location.setter
    def location(self, value):
        self.state = value

    @property
    def arc_name(self):
        return self.company_name

    @arc_name.setter
    def arc_name(self, value):
        self.company_name = value

    @property
    def description_of_schedule_property(self):
        return self.property_description

    @description_of_schedule_property.setter
    def description_of_schedule_property(self, value):
        self.property_description = value

    @property
    def schedule_property_descriptions(self):
        return getattr(self, "_schedule_property_descriptions", None) or []

    @schedule_property_descriptions.setter
    def schedule_property_descriptions(self, value):
        self._schedule_property_descriptions = value

    @property
    def as_on_date(self):
        return self.updated_at

    @as_on_date.setter
    def as_on_date(self, value):
        self.updated_at = value

    @property
    def status(self):
        return "Completed" if self.is_active else "In-Progress"

    @status.setter
    def status(self, value):
        return None

    @property
    def is_report_overridden(self):
        return 0

    @is_report_overridden.setter
    def is_report_overridden(self, value):
        return None


@event.listens_for(SarfaesiMaster, "before_insert")
@event.listens_for(SarfaesiMaster, "before_update")
def _normalize_sarfaesi_values(mapper, connection, target):
    numeric_fields = {
        "disbursal_amount",
        "loan_amount",
        "future_principal",
        "principal_outstanding",
        "instalment_overdue",
        "interest_on_termination",
        "late_payment_penalty",
        "cheque_bounce_charges",
        "other_amount",
        "foreclosure_charges",
        "total_outstanding",
        "notice_13_2_amount",
        "total_bid_count",
        "reserve_price",
        "sold_price",
        "emd_amount",
        "bid_increment",
        "outstanding_amount",
    }

    date_fields = {
        "assignment_agreement_date",
        "fcl_as_on_date",
        "delivery_status_date",
        "npa_date",
        "disbursal_date",
        "loan_agreement_date",
        "notice_13_2_date",
        "notice_dispatch_date",
        "notice_pasting_date",
        "publication_date_13_2",
        "symbolic_possession_date_13_4",
        "symbolic_dispatch_date_13_4",
        "symbolic_delivery_status_date_13_4",
        "symbolic_publication_date_13_4",
        "matured_date_13_4",
        "cjm_filing_date",
        "crm_pl_date",
        "next_hearing_date",
        "ov_date",
        "order_date",
        "physical_possession_date",
        "physical_dispatch_date",
        "physical_delivery_status_date",
        "physical_publication_date",
        "auction_notice_date",
        "auction_date",
        "auction_publication_date",
        "inspection_start",
        "inspection_end",
        "emd_last_date",
        "auction_start",
        "auction_end",
        "sale_confirmation_date",
        "sale_certificate_date",
        "sold_reg_date",
        "effective_date",
        "end_date",
    }

    datetime_fields = {
        "created_at",
        "updated_at",
        "inspection_start",
        "inspection_end",
        "emd_last_date",
        "auction_start",
        "auction_end",
        "effective_date",
        "end_date",
    }

    for field in numeric_fields:
        if hasattr(target, field):
            setattr(target, field, _to_decimal(getattr(target, field)))

    for field in date_fields | datetime_fields:
        if not hasattr(target, field):
            continue
        value = getattr(target, field)
        if value is None or isinstance(value, (int, float, Decimal)):
            continue
        if isinstance(value, str):
            parsed = parse_datetime(value)
            setattr(target, field, parsed)
