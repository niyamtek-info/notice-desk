"""Set version defaults to one across versioned tables

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-03-23 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e7f8a9b0c1d2"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


VERSIONED_TABLES = [
    "applications",
    "property_images",
    "banks",
    "ao_information",
    "notice_templates",
    "communications",
    "documents",
    "document_files",
    "document_ocr_text",
    "document_extracted_data",
    "application_context",
    "translations",
    "extracted_sanction_letters",
    "extracted_loan_agreements",
    "extracted_modts",
    "extracted_modt_properties",
    "extracted_sales_deeds",
    "extracted_sales_deed_vendors",
    "extracted_sales_deed_vendor_representatives",
    "extracted_sales_deed_purchasers",
    "extracted_sales_deed_purchaser_representatives",
    "extracted_sales_deed_witnesses",
    "extracted_sales_deed_witness_representatives",
    "extracted_sales_deed_schedules",
    "extracted_sales_deed_payment_details",
    "extracted_sales_deed_parent_flows",
    "extracted_sales_deed_terms",
    "extracted_sales_deed_authority",
    "master_checklists",
    "application_checklists",
    "extracted_foreclosure_statements",
    "extracted_foreclosure_co_applicants",
    "extracted_foreclosure_notes",
    "extracted_statement_of_accounts",
    "extracted_soa_transactions",
    "generated_reports",
    "logs",
    "observations",
    "reports",
    "users",
]


def upgrade() -> None:
    for table_name in VERSIONED_TABLES:
        op.execute(sa.text(f"UPDATE {table_name} SET version = 1 WHERE version IS NULL OR version < 1"))
        op.alter_column(
            table_name,
            "version",
            existing_type=sa.Integer(),
            server_default="1",
            existing_nullable=False,
        )


def downgrade() -> None:
    for table_name in VERSIONED_TABLES:
        op.alter_column(
            table_name,
            "version",
            existing_type=sa.Integer(),
            server_default="0",
            existing_nullable=False,
        )
