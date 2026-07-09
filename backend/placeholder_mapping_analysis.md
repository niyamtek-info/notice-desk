# Placeholder Mapping Analysis Report

## Issues Found

### 1. INVALID/INCORRECT MAPPINGS (Model field doesn't exist)

| Field in Mapping | Model Field | Issue |
|-----------------|-------------|-------|
| `fcl_amount` | `fcl_as_on_date` | **WRONG MAPPING** - Maps to date field instead of amount field. Should map to `total_outstanding` or create separate field |

### 2. MISSING PLACEHOLDER MAPPINGS (Fields in model but not in mapping)

These fields exist in SarfaesiMaster model but are NOT in placeholder_mapping.json:

| Model Column | Type | Suggested Placeholder |
|-------------|------|----------------------|
| `co_borrower_6_address_alt` | Text | CO_BORROWER_6_ADDRESS_ALT |
| `co_borrower_5_address_alt` | Text | CO_BORROWER_5_ADDRESS_ALT |
| `co_borrower_4_address_alt` | Text | CO_BORROWER_4_ADDRESS_ALT |
| `co_borrower_3_address_alt` | Text | CO_BORROWER_3_ADDRESS_ALT |
| `co_borrower_2_address_alt` | Text | CO_BORROWER_2_ADDRESS_ALT |
| `co_borrower_1_address_alt` | Text | CO_BORROWER_1_ADDRESS_ALT |
| `borrower_address_alt` | Text | BORROWER_ADDRESS_ALT |
| `batch_code` | String | BATCH_CODE |
| `rerun_report` | Integer | RERUN_REPORT |
| `created_at` | DateTime | CREATED_AT |
| `created_by` | String | CREATED_BY |
| `updated_at` | DateTime | UPDATED_AT |
| `updated_by` | String | UPDATED_BY |
| `version` | Integer | VERSION |
| `effective_date` | DateTime | EFFECTIVE_DATE |
| `end_date` | DateTime | END_DATE |
| `is_active` | Boolean | IS_ACTIVE |
| `is_deleted` | Boolean | IS_DELETED |

### 3. FIELDS IN USER LIST BUT NOT IN MODEL OR MAPPING

These fields were mentioned by user but don't exist in current model:

| Field Name | Action Required |
|-----------|----------------|
| `matured_date_13_4` | **ADD TO MODEL** + Add to mapping |
| `vacation_notice_moveable` | **ADD TO MODEL** + Add to mapping |
| `vacation_notice_immoveable` | **ADD TO MODEL** + Add to mapping |
| `physical_vacation_notice_moveable` | **ADD TO MODEL** + Add to mapping |
| `physical_vacation_notice_immoveable` | **ADD TO MODEL** + Add to mapping |
| `status` | **ADD TO MODEL** (computed property exists but not as column) + Add to mapping |
| `outstanding_amount` | **ADD TO MODEL** + Add to mapping |
| `sold_reg_date` | **ADD TO MODEL** + Add to mapping |
| `sarfaesi_category` | **ADD TO MODEL** + Add to mapping |
| `case_status` | **ADD TO MODEL** + Add to mapping |

### 4. PLACEHOLDER ↔ COLUMN NAME MISMATCHES

| Placeholder | Current Model Field | Issue |
|------------|---------------------|-------|
| `LOAN_ACCOUNT_NUMBER` | `loan_account_no` | ✅ OK (has property alias) |
| `LOAN_ACCOUNT_NO` | `loan_account_no` | ✅ OK |
| `INSTALMENT_OVERDUE_AMOUNT` | `instalment_overdue` | ✅ OK (has property alias) |
| `INSTALMENT_OVERDUE` | `instalment_overdue` | ✅ OK |
| `DATE_OF_NPA` | `npa_date` | ✅ OK (has property alias) |
| `DPD_AS_ON_NOTICE` | `dpd` | ✅ OK (has property alias) |
| `DPD` | `dpd` | ✅ OK |
| `FCL_AMOUNT` | `fcl_as_on_date` | ❌ **WRONG** - Should be amount, not date |

### 5. EXAMPLE: {{SYMBOLIC_PUBLICATION_DATE_13_4}} USAGE

This placeholder IS properly mapped:
- Placeholder: `SYMBOLIC_PUBLICATION_DATE_13_4`
- Model Field: `symbolic_publication_date_13_4`
- Status: ✅ CORRECTLY MAPPED

When you add `{{SYMBOLIC_PUBLICATION_DATE_13_4}}` in a template, it will automatically fetch value from `symbolic_publication_date_13_4` column.

## REQUIRED FIXES

### Fix 1: Correct FCL_AMOUNT mapping
```json
{
  "field": "total_outstanding",
  "model_field": "total_outstanding",
  "excel_header": "FCL (As on Date) - Amount",
  "placeholder": "FCL_AMOUNT"
}
```

### Fix 2: Add missing co_borrower address_alt fields
Add these entries to report_fields:
- CO_BORROWER_1_ADDRESS_ALT → co_borrower_1_address_alt
- CO_BORROWER_2_ADDRESS_ALT → co_borrower_2_address_alt
- CO_BORROWER_3_ADDRESS_ALT → co_borrower_3_address_alt
- CO_BORROWER_4_ADDRESS_ALT → co_borrower_4_address_alt
- CO_BORROWER_5_ADDRESS_ALT → co_borrower_5_address_alt
- CO_BORROWER_6_ADDRESS_ALT → co_borrower_6_address_alt
- BORROWER_ADDRESS_ALT → borrower_address_alt

### Fix 3: Add new model columns to mapping
Add placeholders for:
- BATCH_CODE → batch_code
- RERUN_REPORT → rerun_report
- CREATED_AT → created_at
- CREATED_BY → created_by
- UPDATED_AT → updated_at
- UPDATED_BY → updated_by
- VERSION → version
- EFFECTIVE_DATE → effective_date
- END_DATE → end_date
- IS_ACTIVE → is_active
- IS_DELETED → is_deleted

### Fix 4: Add new model columns (requires migration)
If you need these fields, add them to SarfaesiMaster model:
- matured_date_13_4
- vacation_notice_moveable
- vacation_notice_immoveable
- physical_vacation_notice_moveable
- physical_vacation_notice_immoveable
- outstanding_amount
- sold_reg_date
- sarfaesi_category
- case_status

## SUMMARY

✅ **Working correctly:** 100+ placeholder mappings
❌ **Needs fix:** 1 incorrect mapping (FCL_AMOUNT)
⚠️ **Missing:** 17 existing model fields not in mapping
➕ **To add:** 9 new fields need to be added to model + mapping