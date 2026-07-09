"""align versioned uniqueness for applications and sarfaesi

Revision ID: 1a2b3c4d5e6f
Revises: 0f1e2d3c4b5a
Create Date: 2026-04-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1a2b3c4d5e6f"
down_revision = "0f1e2d3c4b5a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_applications_business_code_version",
        "applications",
        ["business_code", "version"],
    )
    op.drop_index("uq_sarfaesi_master_active_loan_account_no", table_name="sarfaesi_master")
    op.drop_column("sarfaesi_master", "active_loan_account_no")


def downgrade() -> None:
    op.add_column(
        "sarfaesi_master",
        sa.Column(
            "active_loan_account_no",
            sa.String(length=100),
            sa.Computed(
                "((case when (`end_date` = '9999-12-12 00:00:00') then `loan_account_no` else NULL end))",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "uq_sarfaesi_master_active_loan_account_no",
        "sarfaesi_master",
        ["active_loan_account_no"],
        unique=True,
    )
    op.drop_constraint("uq_applications_business_code_version", "applications", type_="unique")
