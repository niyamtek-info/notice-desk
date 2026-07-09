"""Fix generated_reports unique constraints for versioning

Revision ID: a7c9e2b4d110_fix
Revises: a7c9e2b4d110
Create Date: 2026-03-10 09:46:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a7c9e2b4d110_fix"
down_revision: Union[str, Sequence[str], None] = "a7c9e2b4d110"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the conflicting unique constraints
    # These prevent versioning since we need multiple records per application_number
    try:
        op.drop_constraint("ix_generated_reports_application_number", "generated_reports", type_="unique")
    except:
        pass
    
    try:
        op.drop_constraint("ix_generated_reports_record_id", "generated_reports", type_="unique")
    except:
        pass
    
    # Recreate as non-unique indexes for query performance
    op.create_index("ix_generated_reports_application_number", "generated_reports", ["application_number"], unique=False, if_not_exists=True)
    op.create_index("ix_generated_reports_record_id", "generated_reports", ["record_id"], unique=False, if_not_exists=True)


def downgrade() -> None:
    try:
        op.drop_index("ix_generated_reports_application_number", table_name="generated_reports")
    except:
        pass
    
    try:
        op.drop_index("ix_generated_reports_record_id", table_name="generated_reports")
    except:
        pass
