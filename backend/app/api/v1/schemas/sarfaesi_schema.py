from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, AliasChoices


class SarfaesiBase(BaseModel):
    batch_code: Optional[str] = None
    niyamtek_user: Optional[str] = None
    client_code: Optional[str] = None
    application_number: Optional[str] = None
    company_name: Optional[str] = None
    loan_account_no: Optional[str] = None
    loan_amount_words: Optional[str] = None
    borrower_name: Optional[str] = None
    borrower_address: Optional[str] = None
    borrower_address_alt: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    branch: Optional[str] = None
    ao_name: Optional[str] = None
    trust_number: Optional[str] = None
    assignment_agreement_date: Optional[date | str] = None

    co_borrower_1_name: Optional[str] = None
    co_borrower_1_address: Optional[str] = None
    co_borrower_1_address_alt: Optional[str] = None
    co_borrower_2_name: Optional[str] = None
    co_borrower_2_address: Optional[str] = None
    co_borrower_2_address_alt: Optional[str] = None
    co_borrower_3_name: Optional[str] = None
    co_borrower_3_address: Optional[str] = None
    co_borrower_3_address_alt: Optional[str] = None
    co_borrower_4_name: Optional[str] = None
    co_borrower_4_address: Optional[str] = None
    co_borrower_4_address_alt: Optional[str] = None
    co_borrower_5_name: Optional[str] = None
    co_borrower_5_address: Optional[str] = None
    co_borrower_5_address_alt: Optional[str] = None
    co_borrower_6_name: Optional[str] = None
    co_borrower_6_address: Optional[str] = None
   

    guarantor_1_name: Optional[str] = None
    guarantor_1_address: Optional[str] = None
    guarantor_2_name: Optional[str] = None
    guarantor_2_address: Optional[str] = None

    property_description: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "property_description",
            "description_of_schedule_property",
            "descriptionOfScheduleProperty",
        ),
    )
    property_address: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "property_address",
            "mortgaged_property_address",
            "address_of_mortgaged_property",
        ),
    )
    npa_date: Optional[date | str] = None
    dpd: Optional[int] = None
    disbursement_type: Optional[str] = None
    disbursal_date: Optional[date | str] = None
    disbursal_amount: Optional[Decimal] = None
    loan_agreement_date: Optional[date | str] = None
    loan_amount: Optional[Decimal] = None
    future_principal: Optional[Decimal] = None
    principal_outstanding: Optional[Decimal] = None
    instalment_overdue: Optional[Decimal] = None
    interest_on_termination: Optional[Decimal] = None
    late_payment_penalty: Optional[Decimal] = None
    cheque_bounce_charges: Optional[Decimal] = None
    other_amount: Optional[Decimal] = None
    foreclosure_charges: Optional[Decimal] = None
    total_outstanding: Optional[Decimal] = None
    fcl_as_on_date: Optional[date | str] = None
    total_outstanding_words: Optional[str] = None

    notice_13_2_amount: Optional[Decimal] = None
    notice_13_2_date: Optional[date | str] = None
    notice_dispatch_date: Optional[date | str] = None
    notice_pasting_date: Optional[date | str] = None
    delivery_status: Optional[str] = None
    delivered_address: Optional[str] = None
    undelivered_address: Optional[str] = None
    total_address: Optional[str | int] = None
    publication_date_13_2: Optional[date | str] = None
    publication_english_13_2: Optional[str] = None
    publication_local_13_2: Optional[str] = None

    symbolic_possession_date: Optional[date | str] = None
    symbolic_dispatch_date: Optional[date | str] = None
    symbolic_delivery_status: Optional[str] = None
    symbolic_photo: Optional[str] = None
    symbolic_publication_date: Optional[date | str] = None
    symbolic_pub_english: Optional[str] = None
    symbolic_pub_local: Optional[str] = None

    cjm_filing_date: Optional[date | str] = None
    court_name: Optional[str] = None
    case_number: Optional[str] = None
    crm_pl_date: Optional[date | str] = None
    crm_pl_no: Optional[str] = None
    next_hearing_date: Optional[date | str] = None
    ov_date: Optional[date | str] = None
    order_date: Optional[date | str] = None
    court_ao_name: Optional[str] = None
    advocate_details: Optional[str] = None
    adv_com_name: Optional[str] = None
    inventory_status: Optional[str] = None

    physical_possession_date: Optional[date | str] = None
    physical_dispatch_date: Optional[date | str] = None
    physical_delivery_status: Optional[str] = None
    physical_photo: Optional[str] = None
    physical_publication_date: Optional[date | str] = None
    physical_pub_english: Optional[str] = None
    physical_pub_local: Optional[str] = None

    auction_notice_date: Optional[date | str] = None
    auction_date: Optional[date | str] = None
    auction_publication_date: Optional[date | str] = None
    auction_pub_english: Optional[str] = None
    auction_pub_local: Optional[str] = None
    reserve_price: Optional[Decimal] = None
    sold_price: Optional[Decimal] = None
    auction_status: Optional[str] = None
    inspection_start: Optional[datetime | str] = None
    inspection_end: Optional[datetime | str] = None
    emd_last_date: Optional[datetime | str] = None
    auction_start: Optional[datetime | str] = None
    auction_end: Optional[datetime | str] = None
    bid_extension_time: Optional[str] = None
    total_extensions: Optional[str] = None
    emd_amount: Optional[Decimal] = None
    bid_increment: Optional[Decimal] = None
    total_bid_count: Optional[int] = None
    authorised_officer: Optional[str] = None

    post_sale_notice: Optional[str] = None
    sale_confirmation_date: Optional[date | str] = None
    sale_certificate_date: Optional[date | str] = None
    available_documents: Optional[str] = None
    non_available_documents: Optional[str] = None
    discrepancy_doc: Optional[str] = None
    discrepancy_reason: Optional[str] = None
    next_actionable_stage: Optional[str] = None
    next_step_recommended: Optional[str] = None
    niyamtek_remarks: Optional[str] = None

    version: Optional[int] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None

    created_at: Optional[datetime | str] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime | str] = None
    updated_by: Optional[str] = None
    rerun_report: Optional[int] = None

    class Config:
        orm_mode = True


class SarfaesiCreate(SarfaesiBase):
    application_number: str


class SarfaesiUpdate(SarfaesiBase):
    pass


class LoanDetails(BaseModel):
    # BASIC
    application_number: Optional[str] = None
    batch_code: Optional[str] = None
    client_code: Optional[str] = None
    company_name: Optional[str] = None
    loan_account_no: Optional[str] = None
    loan_amount_words: Optional[str] = None
    borrower_name: Optional[str] = None
    borrower_address: Optional[str] = None
    borrower_address_alt: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    branch: Optional[str] = None
    ao_name: Optional[str] = None
    trust_number: Optional[str] = None
    assignment_agreement_date: Optional[date | str] = None
    report_source: Optional[str] = None
    has_document: Optional[bool] = None
    pos: Optional[str] = None
    sarfaesi_category: Optional[str] = None
    case_status: Optional[str] = None
    niyamtek_user: Optional[str] = None

    # CO-BORROWERS
    co_borrower_1_name: Optional[str] = None
    co_borrower_1_address: Optional[str] = None
    co_borrower_1_address_alt: Optional[str] = None
    co_borrower_2_name: Optional[str] = None
    co_borrower_2_address: Optional[str] = None
    co_borrower_2_address_alt: Optional[str] = None
    co_borrower_3_name: Optional[str] = None
    co_borrower_3_address: Optional[str] = None
    co_borrower_3_address_alt: Optional[str] = None
    co_borrower_4_name: Optional[str] = None
    co_borrower_4_address: Optional[str] = None
    co_borrower_4_address_alt: Optional[str] = None
    co_borrower_5_name: Optional[str] = None
    co_borrower_5_address: Optional[str] = None
    co_borrower_5_address_alt: Optional[str] = None
    co_borrower_6_name: Optional[str] = None
    co_borrower_6_address: Optional[str] = None

    # GUARANTORS
    guarantor_1_name: Optional[str] = None
    guarantor_1_address: Optional[str] = None
    guarantor_2_name: Optional[str] = None
    guarantor_2_address: Optional[str] = None

    property_description: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "property_description",
            "description_of_schedule_property",
            "descriptionOfScheduleProperty",
        ),
    )
    property_address: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "property_address",
            "mortgaged_property_address",
            "address_of_mortgaged_property",
        ),
    )

    # LOAN
    npa_date: Optional[date | str] = None
    # Treated as an amount field for display: comma-formatted by
    # SarfaesiService._format_response like the other amount fields.
    dpd: Optional[str] = None
    disbursement_type: Optional[str] = None
    disbursal_date: Optional[date | str] = None
    # Formatted as an Indian-grouped comma string (e.g. "19,55,60,000.00") by
    # SarfaesiService._format_response, not a raw Decimal - the DB column
    # holds no comma formatting, so the frontend edit form was redisplaying
    # saved amounts as "195560000.00" after every reload. report_repo.py
    # already strips commas back out on save, so round-tripping through
    # edit/save is unaffected by carrying the display string here instead.
    disbursal_amount: Optional[str] = None
    loan_agreement_date: Optional[date | str] = None
    loan_amount: Optional[str] = None
    future_principal: Optional[str] = None
    principal_outstanding: Optional[str] = None
    instalment_overdue: Optional[str] = None
    interest_on_termination: Optional[str] = None
    late_payment_penalty: Optional[str] = None
    cheque_bounce_charges: Optional[str] = None
    other_amount: Optional[str] = None
    foreclosure_charges: Optional[str] = None
    total_outstanding: Optional[str] = None
    fcl_as_on_date: Optional[date | str] = None
    total_outstanding_words: Optional[str] = None


class Thirteen2Details(BaseModel):
    notice_13_2_amount: Optional[str] = None
    notice_13_2_date: Optional[date | str] = None
    notice_dispatch_date: Optional[date | str] = None
    notice_pasting_date: Optional[date | str] = None
    delivery_status: Optional[str] = None
    delivery_status_date: Optional[date | str] = None
    delivered_address: Optional[str] = None
    undelivered_address: Optional[str] = None
    total_address: Optional[str | int] = None
    publication_date: Optional[date | str] = None
    publication_english: Optional[str] = None
    publication_local: Optional[str] = None


class Thirteen4Details(BaseModel):
    symbolic_possession_date: Optional[date | str] = None
    symbolic_dispatch_date: Optional[date | str] = None
    symbolic_delivery_status: Optional[str] = None
    symbolic_delivery_status_date: Optional[date | str] = None
    symbolic_photo: Optional[str] = None
    symbolic_publication_date: Optional[date | str] = None
    symbolic_pub_english: Optional[str] = None
    symbolic_pub_local: Optional[str] = None
    matured_date_13_4: Optional[date | str] = None


class SymbolicVacationNoticeDetails(BaseModel):
    vacation_notice_moveable: Optional[str] = None
    vacation_notice_immoveable: Optional[str] = None


class CjmDetails(BaseModel):
    cjm_filing_date: Optional[date | str] = None
    court_name: Optional[str] = None
    case_number: Optional[str] = None
    crm_pl_date: Optional[date | str] = None
    crm_pl_no: Optional[str] = None
    next_hearing_date: Optional[date | str] = None
    ov_date: Optional[date | str] = None
    order_date: Optional[date | str] = None
    court_ao_name: Optional[str] = None
    advocate_details: Optional[str] = None
    adv_com_name: Optional[str] = None
    inventory_status: Optional[str] = None


class PhysicalPossessionDetails(BaseModel):
    physical_possession_date: Optional[date | str] = None
    physical_dispatch_date: Optional[date | str] = None
    physical_delivery_status: Optional[str] = None
    physical_delivery_status_date: Optional[date | str] = None
    physical_photo: Optional[str] = None
    physical_publication_date: Optional[date | str] = None
    physical_pub_english: Optional[str] = None
    physical_pub_local: Optional[str] = None
    vacation_notice_moveable: Optional[date | str] = None
    vacation_notice_immoveable: Optional[date | str] = None


class AuctionNoticeDetails(BaseModel):
    auction_notice_date: Optional[date | str] = None
    auction_date: Optional[date | str] = None
    auction_publication_date: Optional[date | str] = None
    auction_pub_english: Optional[str] = None
    auction_pub_local: Optional[str] = None
    reserve_price: Optional[str] = None


class AuctionPortalDetails(BaseModel):
    auction_date: Optional[date | str] = None
    reserve_price: Optional[str] = None
    sold_price: Optional[str] = None
    auction_status: Optional[str] = None
    inspection_start: Optional[datetime | str] = None
    inspection_end: Optional[datetime | str] = None
    emd_last_date: Optional[datetime | str] = None
    auction_start: Optional[datetime | str] = None
    auction_end: Optional[datetime | str] = None
    bid_extension_time: Optional[str] = None
    total_extensions: Optional[str] = None
    outstanding_amount: Optional[str] = None
    emd_amount: Optional[str] = None
    bid_increment: Optional[str] = None
    total_bid_count: Optional[int] = None
    authorised_officer: Optional[str] = None


class PostSaleDetails(BaseModel):
    post_sale_notice: Optional[str] = None
    sold_price: Optional[str] = None
    sold_reg_date: Optional[date | str] = None


class SaleCertificateDetails(BaseModel):
    sale_confirmation_date: Optional[date | str] = None
    sale_certificate_date: Optional[date | str] = None


class NiyamtekRemarksDetails(BaseModel):
    available_documents: Optional[str] = None
    non_available_documents: Optional[str] = None
    discrepancy_doc: Optional[str] = None
    discrepancy_reason: Optional[str] = None
    next_actionable_stage: Optional[str] = None
    next_step_recommended: Optional[str] = None


class SarfaesiResponse(BaseModel):
    id: int
    rerun_report: Optional[int] = None
    loan_details: LoanDetails
    thirteen_two_details: Thirteen2Details = Field(alias="13_2_details")
    thirteen_four_details: Thirteen4Details = Field(alias="13_4_details")
    symbolic_vacation_notice_details: SymbolicVacationNoticeDetails
    cjm_details: CjmDetails
    physical_possession_details: PhysicalPossessionDetails
    auction_notice_details: AuctionNoticeDetails
    auction_portal_details: AuctionPortalDetails
    post_sale_details: PostSaleDetails
    sale_certificate_details: SaleCertificateDetails
    niyamtek_remarks_details: NiyamtekRemarksDetails

    model_config = {
        "populate_by_name": True
    }