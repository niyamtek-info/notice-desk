"""Add unique constraint to ao_information (bank_id, ao_code, ao_name)

Revision ID: f3c4b5d6e7f8
Revises: f2b3a5c6d7e8
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = 'f3c4b5d6e7f8'
down_revision = 'f2b3a5c6d7e8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unique constraint: ao_code + ao_name must be unique per bank at latest version
    op.create_unique_constraint('uq_ao_bank_code_name', 'ao_information', ['bank_id', 'ao_code', 'ao_name'])


def downgrade() -> None:
    # Remove unique constraint
    op.drop_constraint('uq_ao_bank_code_name', 'ao_information', type_='unique')
