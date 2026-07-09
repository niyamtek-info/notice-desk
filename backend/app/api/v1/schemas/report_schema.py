from typing import Optional, List
from pydantic import BaseModel, field_serializer, field_validator
from datetime import datetime, date
from app.utils.date_utils import parse_datetime

class ReportBase(BaseModel):
    loan_account_number: Optional[str] = None
    borrower_name: Optional[str] = None
    location: Optional[str] = None
    arc_name: Optional[str] = None

    borrower_address: Optional[str] = None
    borrower_address_also_at: Optional[str] = None
    property_address: Optional[str] = None
    property_description: Optional[str] = None

    # Loan
    loan_amount: Optional[int] = None
    loan_amount_words: Optional[str] = None
    loan_agreement_date: Optional[datetime] = None

    date_of_npa: Optional[datetime] = None
    dpd_as_on_notice: Optional[int] = None
    sec_13_2_notice_date: Optional[datetime] = None

    disbursal_date: Optional[datetime] = None
    disbursal_amount: Optional[int] = None

    future_principal: Optional[int] = None

    # Financials
    principal_outstanding: Optional[int] = None
    instalment_overdue_amount: Optional[int] = None
    interest_on_termination: Optional[int] = None
    late_payment_penalty: Optional[int] = None
    cheque_bounce_charges: Optional[int] = None
    other_amount: Optional[int] = None
    foreclosure_charges: Optional[int] = None

    total_outstanding: Optional[int] = None
    as_on_date: Optional[datetime] = None

    total_outstanding_words: Optional[str] = None

    # SOA
    soa_bank_name: Optional[str] = None
    soa_interest_rate: Optional[str] = None
    soa_loan_status: Optional[str] = None

    # Foreclosure
    foreclosure_bank_name: Optional[str] = None
    foreclosure_loan_account_number: Optional[str] = None
    foreclosure_outstanding_principal: Optional[str] = None
    foreclosure_total_amount_payable: Optional[str] = None
    foreclosure_valid_upto_date: Optional[datetime] = None
    soa_sanction_date: Optional[datetime] = None

    
    borrower_name: Optional[str] = None
    borrower_address: Optional[str] = None
    borrower_address_also_at: Optional[str] = None
    property_address: Optional[str] = None
    description_of_schedule_property: Optional[str] = None
    property_description: Optional[str] = None
    schedule_property_descriptions: Optional[List[str]] = None
    
    co_borrower_1_name: Optional[str] = None
    co_borrower_1_address: Optional[str] = None
    co_borrower_1_address_also_at: Optional[str] = None
    
    co_borrower_2_name: Optional[str] = None
    co_borrower_2_address: Optional[str] = None
    co_borrower_2_address_also_at: Optional[str] = None
    
    co_borrower_3_name: Optional[str] = None
    co_borrower_3_address: Optional[str] = None
    co_borrower_3_address_also_at: Optional[str] = None
    
    co_borrower_4_name: Optional[str] = None
    co_borrower_4_address: Optional[str] = None
    co_borrower_4_address_also_at: Optional[str] = None
    
    co_borrower_5_name: Optional[str] = None
    co_borrower_5_address: Optional[str] = None
    co_borrower_5_address_also_at: Optional[str] = None
    total_address: Optional[str | int] = None
    is_report_overridden: Optional[int] = 0
    rerun_report: Optional[int] = 0
    status: Optional[str] = None

    @field_validator(
        "loan_agreement_date",
        "date_of_npa",
        "sec_13_2_notice_date",
        "disbursal_date",
        "as_on_date",
        "foreclosure_valid_upto_date",
        "soa_sanction_date",
        mode="before",
    )
    @classmethod
    def _parse_report_dates(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, (datetime, date)):
            if isinstance(value, datetime):
                return value
            return datetime.combine(value, datetime.min.time())
        parsed = parse_datetime(value)
        if parsed is None:
            return None
        if isinstance(parsed, datetime):
            return parsed
        return datetime.combine(parsed, datetime.min.time())

    @field_serializer(
        "loan_agreement_date",
        "date_of_npa",
        "sec_13_2_notice_date",
        "disbursal_date",
        "as_on_date",
        "foreclosure_valid_upto_date",
        "soa_sanction_date",
    )
    def _serialize_report_dates(self, value):
        if value is None:
            return None
        if hasattr(value, "strftime"):
            return value.strftime("%d-%m-%Y")
        return value

class ReportUpdateRequest(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: Optional[int] = None
    application_number: str
    status: Optional[str] = "In-Progress"
    # document_id removed because it is not part of the SARFAESI master table
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_serializer("created_at")
    def _serialize_created_at(self, value):
        if value is None:
            return None
        if hasattr(value, "strftime"):
            return value.strftime("%d-%m-%Y")
        return value


class ReportGenerateRequest(BaseModel):
    application_number: str


class BulkReportDownloadRequest(BaseModel):
    application_numbers: List[str]
