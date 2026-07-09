"""Expand application number columns for NYMTK identifiers

Revision ID: f4d5e6a7b8c9
Revises: f3c4b5d6e7f8
Create Date: 2026-03-13 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f4d5e6a7b8c9"
down_revision = "f3c4b5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("applications", "business_code", existing_type=sa.String(length=20), type_=sa.String(length=50), existing_nullable=True)
    op.alter_column("logs", "application_number", existing_type=sa.String(length=20), type_=sa.String(length=50), existing_nullable=False)
    op.alter_column("observations", "application_number", existing_type=sa.String(length=20), type_=sa.String(length=50), existing_nullable=False)
    op.alter_column("bulk_notices", "application_number", existing_type=sa.String(length=20), type_=sa.String(length=50), existing_nullable=False)


def downgrade() -> None:
    op.alter_column("bulk_notices", "application_number", existing_type=sa.String(length=50), type_=sa.String(length=20), existing_nullable=False)
    op.alter_column("observations", "application_number", existing_type=sa.String(length=50), type_=sa.String(length=20), existing_nullable=False)
    op.alter_column("logs", "application_number", existing_type=sa.String(length=50), type_=sa.String(length=20), existing_nullable=False)
    op.alter_column("applications", "business_code", existing_type=sa.String(length=50), type_=sa.String(length=20), existing_nullable=True)
