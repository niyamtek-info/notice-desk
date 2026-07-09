"""Expand application_context gender column

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-03-20 16:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d6e7f8a9b0c1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "application_context",
        "gender",
        existing_type=sa.String(length=10),
        type_=sa.String(length=50),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "application_context",
        "gender",
        existing_type=sa.String(length=50),
        type_=sa.String(length=10),
        existing_nullable=True,
    )
