from __future__ import annotations

from typing import Any, Dict, Optional


FIELD_MAPPING = {
    # 🔥 APPLICATION
    "batch_code": {"source": "application.batch_code", "editable": True},
    "application_number": {"source": "application.business_code", "editable": True},
    "company_name": {"source": "application.client_name", "editable": True},
    "loan_account_no": {"source": "application.loan_account_number", "editable": True},
    "state": {"source": "application.state", "editable": True},

    # 🔥 CLIENT
    "client_code": {"source": "client.client_code", "editable": True},

    # 🔥 BORROWER
    "borrower_name": {"source": "application.loan_requester_name", "editable": True},
    "borrower_address": {"source": "document.borrower_address", "editable": True},
    "borrower_address_alt": {"source": "document.borrower_address_alt", "editable": True},
    "co_borrower_1_address_alt": {"source": "document.co_borrower_1_address_alt", "editable": True},
    "co_borrower_2_address_alt": {"source": "document.co_borrower_2_address_alt", "editable": True},
    "co_borrower_3_address_alt": {"source": "document.co_borrower_3_address_alt", "editable": True},
    "co_borrower_4_address_alt": {"source": "document.co_borrower_4_address_alt", "editable": True},
    "co_borrower_5_address_alt": {"source": "document.co_borrower_5_address_alt", "editable": True},
    "property_description": {
        "source": "document.description_of_schedule_property",
        "editable": True,
    },
    "property_address": {
        "source": "document.mortgaged_property_address",
        "editable": True,
    },
    "description_of_schedule_property": {
        "source": "document.description_of_schedule_property",
        "editable": True,
    },

    # 🔥 LOAN DETAILS
    "npa_date": {"source": "document.npa_date", "editable": True},
    "dpd": {"source": "document.dpd", "editable": True},
    "disbursal_date": {"source": "document.disbursal_date", "editable": True},
    "disbursal_amount": {"source": "document.disbursal_amount", "editable": True},
    "loan_agreement_date": {"source": "document.loan_agreement_date", "editable": True},
    "loan_amount": {"source": "document.loan_amount", "editable": True},
    "loan_amount_words": {
        "source": "extracted_loan_agreement.loan_amount_in_words",
        "editable": True,
    },
    "future_principal": {"source": "document.future_principal", "editable": True},
    "principal_outstanding": {"source": "document.principal_outstanding", "editable": True},
    "instalment_overdue": {"source": "document.instalment_overdue", "editable": True},
    "interest_on_termination": {"source": "document.interest_on_termination", "editable": True},
    "late_payment_penalty": {"source": "document.late_payment_penalty", "editable": True},
    "cheque_bounce_charges": {"source": "document.cheque_bounce_charges", "editable": True},
    "other_amount": {"source": "document.other_amount", "editable": True},
    "foreclosure_charges": {"source": "document.foreclosure_charges", "editable": True},
    "total_outstanding": {"source": "document.total_outstanding", "editable": True},
    "total_outstanding_words": {"source": "document.total_outstanding_words", "editable": True},

    # 🔥 NOTICE
    "notice_13_2_date": {"source": "document.notice_13_2_date", "editable": True},
    "notice_dispatch_date": {"source": "document.notice_dispatch_date", "editable": True},
    "notice_pasting_date": {"source": "document.notice_pasting_date", "editable": True},
    "delivery_status": {"source": "document.delivery_status", "editable": True},
    "delivered_address": {"source": "document.delivered_address", "editable": True},
    "undelivered_address": {"source": "document.undelivered_address", "editable": True},
    "total_address": {"source": "document.total_address", "editable": True},
    "publication_date_13_2": {"source": "document.publication_date_13_2", "editable": True},
    "publication_english_13_2": {"source": "document.publication_english_13_2", "editable": True},
    "publication_local_13_2": {"source": "document.publication_local_13_2", "editable": True},

    # 🔥 SYMBOLIC
    "symbolic_possession_date_13_4": {"source": "document.symbolic_possession_date", "editable": True},
    "symbolic_dispatch_date_13_4": {"source": "document.symbolic_dispatch_date", "editable": True},
    "symbolic_delivery_status_13_4": {"source": "document.symbolic_delivery_status", "editable": True},
    "symbolic_photo_13_4": {"source": "document.symbolic_photo", "editable": True},
    "symbolic_publication_date_13_4": {"source": "document.symbolic_publication_date", "editable": True},
    "symbolic_pub_english_13_4": {"source": "document.symbolic_pub_english", "editable": True},
    "symbolic_pub_local_13_4": {"source": "document.symbolic_pub_local", "editable": True},

    # 🔥 AUCTION
    "auction_date": {"source": "document.auction_date", "editable": True},
    "auction_publication_date": {"source": "document.auction_publication_date", "editable": True},
    "auction_pub_english": {"source": "document.auction_pub_english", "editable": True},
    "auction_pub_local": {"source": "document.auction_pub_local", "editable": True},
    "auction_status": {"source": "document.auction_status", "editable": True},
    "reserve_price": {"source": "document.reserve_price", "editable": True},
    "sold_price": {"source": "document.sold_price", "editable": True},

    # 🔥 AUCTION TIMINGS
    "inspection_start": {"source": "document.inspection_start", "editable": True},
    "inspection_end": {"source": "document.inspection_end", "editable": True},
    "emd_last_date": {"source": "document.emd_last_date", "editable": True},
    "auction_start": {"source": "document.auction_start", "editable": True},
    "auction_end": {"source": "document.auction_end", "editable": True},
    "bid_extension_time": {"source": "document.bid_extension_time", "editable": True},
    "total_extensions": {"source": "document.total_extensions", "editable": True},
    "emd_amount": {"source": "document.emd_amount", "editable": True},
    "bid_increment": {"source": "document.bid_increment", "editable": True},
    "total_bid_count": {"source": "document.total_bid_count", "editable": True},
    "authorised_officer": {"source": "document.authorised_officer", "editable": True},

    # 🔥 POST SALE
    "available_documents": {"source": "document.available_documents", "editable": True},
    "non_available_documents": {"source": "document.non_available_documents", "editable": True},
    "discrepancy_doc": {"source": "document.discrepancy_doc", "editable": True},
    "discrepancy_reason": {"source": "document.discrepancy_reason", "editable": True},
    "next_actionable_stage": {"source": "document.next_actionable_stage", "editable": True},
    "next_step_recommended": {"source": "document.next_step_recommended", "editable": True},
    "niyamtek_remarks": {"source": "document.niyamtek_remarks", "editable": True},
}


EDITABLE_FIELDS = set(FIELD_MAPPING.keys())

DOCUMENT_FIELDS = {
    key for key, value in FIELD_MAPPING.items()
    if value["source"].startswith("document.")
}

# Fields users are allowed to edit manually on the SARFAESI/report side.
# These are lifecycle/manual values, not application-master fields.
MANUAL_EDITABLE_FIELDS = {
    "discrepancy_doc",
    "date_of_npa",
    "dpd_as_on_notice",
    "disbursement_type",
    "disbursal_date",
    "disbursal_amount",
    "sec_13_2_notice_date",
    "notice_13_2_amount",
    "notice_dispatch_date",
    "notice_pasting_date",
    "delivery_status",
    "delivered_address",
    "undelivered_address",
    "total_address",
    "property_address",
    "property_description",
    "co_borrower_1_address_also_at",
    "co_borrower_2_address_also_at",
    "co_borrower_3_address_also_at",
    "co_borrower_4_address_also_at",
    "co_borrower_5_address_also_at",
    "publication_date_13_2",
    "publication_english_13_2",
    "publication_local_13_2",
    "physical_possession_date_13_4",
    "physical_dispatch_date_13_4",
    "physical_delivery_status_13_4",
    "physical_photo_13_4",
    "physical_publication_date_13_4",
    "physical_pub_english_13_4",
    "physical_pub_local_13_4",
    "cjm_filing_date",
    "court_name",
    "case_number",
    "crm_pl_date",
    "crm_pl_no",
    "next_hearing_date",
    "ov_date",
    "order_date",
    "court_ao_name",
    "advocate_details",
    "adv_com_name",
    "inventory_status",
    "auction_notice_date",
    "auction_date",
    "auction_publication_date",
    "auction_pub_english",
    "auction_pub_local",
    "reserve_price",
    "sold_price",
    "auction_status",
    "inspection_start",
    "inspection_end",
    "emd_last_date",
    "auction_start",
    "auction_end",
    "bid_extension_time",
    "total_extensions",
    "emd_amount",
    "bid_increment",
    "total_bid_count",
    "authorised_officer",
    "post_sale_notice",
    "sale_confirmation_date",
    "sale_certificate_date",
    "available_documents",
    "non_available_documents",
    "discrepancy_reason",
    "next_actionable_stage",
    "next_step_recommended",
    "niyamtek_remarks",
}


def get_source_value(sources: Dict[str, Any], path: str) -> Optional[Any]:
    if not path:
        return None

    for part in path.split("|"):
        current = sources
        for segment in part.strip().split("."):
            if current is None:
                break
            if isinstance(current, dict):
                current = current.get(segment)
            else:
                current = getattr(current, segment, None)
        if current is not None:
            return current

    return None


def get_audit_actor(current_user: Any) -> str:
    if not current_user:
        return "System"

    username = getattr(current_user, "username", None)
    if username:
        return username

    return "System"