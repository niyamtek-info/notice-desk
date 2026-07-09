"""enable_same_table_versioning_keys

Revision ID: d91f0a7b22c4
Revises: c4f7a8b9d2e1
Create Date: 2026-03-09 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d91f0a7b22c4"
down_revision: Union[str, Sequence[str], None] = "c4f7a8b9d2e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_bank_loan_account", "loan_info", type_="unique")
    op.create_unique_constraint("uq_loan_info_record_version", "loan_info", ["record_id", "version"])

    op.drop_index("ix_applications_record_id", table_name="applications")
    op.drop_index("ix_applications_business_code", table_name="applications")
    op.create_index("ix_applications_record_id", "applications", ["record_id"], unique=False)
    op.create_index("ix_applications_business_code", "applications", ["business_code"], unique=False)

    op.drop_index("ix_banks_bank_code", table_name="banks")
    op.create_index("ix_banks_bank_code", "banks", ["bank_code"], unique=False)

    op.drop_index("ix_ao_info_ao_code", table_name="ao_info")
    op.create_index("ix_ao_info_ao_code", "ao_info", ["ao_code"], unique=False)

    op.drop_index("ix_notice_templates_template_code", table_name="notice_templates")
    op.create_index("ix_notice_templates_template_code", "notice_templates", ["template_code"], unique=False)

    op.drop_index("ix_documents_file_id", table_name="documents")
    op.create_index("ix_documents_file_id", "documents", ["file_id"], unique=False)


def downgrade() -> None:
    op.drop_constraint("uq_loan_info_record_version", "loan_info", type_="unique")
    op.create_unique_constraint("uq_bank_loan_account", "loan_info", ["bank_name", "loan_account_number"])
