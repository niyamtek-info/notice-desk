import json

data = json.load(open('app/metatable/placeholder_mapping.json'))
fields = data['report_fields']

# Actual column names from SarfaesiMaster model (safari_notice.py)
model_cols = {
    'id', 'application_number', 'niyamtek_user', 'client_code', 'company_name',
    'loan_account_no', 'borrower_name', 'trust_number', 'assignment_agreement_date',
    'ao_name', 'branch', 'state', 'region', 'property_address', 'borrower_address',
    'borrower_address_alt', 'report_source', 'has_document',
    'co_borrower_1_name', 'co_borrower_1_address', 'co_borrower_1_address_alt',
    'co_borrower_2_name', 'co_borrower_2_address', 'co_borrower_2_address_alt',
    'co_borrower_3_name', 'co_borrower_3_address', 'co_borrower_3_address_alt',
    'co_borrower_4_name', 'co_borrower_4_address', 'co_borrower_4_address_alt',
    'co_borrower_5_name', 'co_borrower_5_address', 'co_borrower_5_address_alt',
    'co_borrower_6_name', 'co_borrower_6_address',
    'property_description',
    'guarantor_1_name', 'guarantor_1_address', 'guarantor_2_name', 'guarantor_2_address',
    'npa_date', 'dpd', 'disbursement_type', 'disbursal_date', 'disbursal_amount',
    'loan_agreement_date', 'loan_amount', 'loan_amount_words',
    'future_principal', 'principal_outstanding', 'instalment_overdue',
    'interest_on_termination', 'late_payment_penalty', 'cheque_bounce_charges',
    'other_amount', 'foreclosure_charges', 'total_outstanding', 'fcl_as_on_date',
    'total_outstanding_words',
    'notice_13_2_amount', 'notice_13_2_date', 'notice_dispatch_date', 'notice_pasting_date',
    'delivery_status', 'delivered_address', 'undelivered_address', 'total_address',
    'publication_date_13_2', 'publication_english_13_2', 'publication_local_13_2',
    'symbolic_possession_date_13_4', 'symbolic_dispatch_date_13_4',
    'symbolic_delivery_status_13_4', 'symbolic_photo_13_4',
    'symbolic_publication_date_13_4', 'symbolic_pub_english_13_4', 'symbolic_pub_local_13_4',
    'cjm_filing_date', 'court_name', 'case_number', 'crm_pl_date', 'crm_pl_no',
    'next_hearing_date', 'ov_date', 'order_date', 'court_ao_name',
    'advocate_details', 'adv_com_name', 'inventory_status',
    'physical_possession_date', 'physical_dispatch_date', 'physical_delivery_status',
    'physical_photo', 'physical_publication_date', 'physical_pub_english', 'physical_pub_local',
    'auction_notice_date', 'auction_date', 'auction_publication_date',
    'auction_pub_english', 'auction_pub_local', 'reserve_price', 'sold_price', 'auction_status',
    'inspection_start', 'inspection_end', 'emd_last_date', 'auction_start', 'auction_end',
    'bid_extension_time', 'total_extensions', 'emd_amount', 'bid_increment', 'total_bid_count',
    'authorised_officer', 'post_sale_notice', 'sale_confirmation_date', 'sale_certificate_date',
    'available_documents', 'non_available_documents', 'discrepancy_doc', 'discrepancy_reason',
    'next_actionable_stage', 'next_step_recommended', 'niyamtek_remarks',
    'batch_code', 'rerun_report',
    'created_at', 'created_by', 'updated_at', 'updated_by', 'version',
    'effective_date', 'end_date', 'is_active', 'is_deleted'
}

# Python properties on the model
properties = {
    'loan_account_number',
    'borrower_address_also_at',
    'co_borrower_1_address_also_at',
    'co_borrower_2_address_also_at',
    'co_borrower_3_address_also_at',
    'co_borrower_4_address_also_at',
    'co_borrower_5_address_also_at',
    'date_of_npa',
    'dpd_as_on_notice',
    'sec_13_2_notice_date',
    'instalment_overdue_amount',
    'location',
    'arc_name',
    'description_of_schedule_property',
    'schedule_property_descriptions',
    'as_on_date',
    'status',
    'is_report_overridden'
}

valid = model_cols | properties

print("=== BROKEN model_field references (doesn't exist in model) ===")
for f in fields:
    mf = f.get('model_field')
    ph = f.get('placeholder')
    if mf and mf not in valid:
        print(f'  {ph:40s} model_field="{mf}"')

print()
print("=== model_field vs field mismatch ===")
for f in fields:
    fld = f.get('field')
    mf = f.get('model_field')
    if fld != mf:
        print(f'  placeholder={f.get("placeholder"):40s} field="{fld}" model_field="{mf}"')