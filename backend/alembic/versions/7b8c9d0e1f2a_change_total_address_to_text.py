"""change total_address to text

Revision ID: 7b8c9d0e1f2a
Revises: 1a2b3c4d5e6f
Create Date: 2026-04-11 18:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7b8c9d0e1f2a"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "sarfaesi_master",
        "total_address",
        existing_type=sa.Integer(),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "sarfaesi_master",
        "total_address",
        existing_type=sa.Text(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
