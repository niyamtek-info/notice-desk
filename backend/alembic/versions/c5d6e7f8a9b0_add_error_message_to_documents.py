"""Add error_message column to documents

Revision ID: c5d6e7f8a9b0
Revises: f4d5e6a7b8c9
Create Date: 2026-03-20 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c5d6e7f8a9b0"
down_revision = "f4d5e6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "error_message")
