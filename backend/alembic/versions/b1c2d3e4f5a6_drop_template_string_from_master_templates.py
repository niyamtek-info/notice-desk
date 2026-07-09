"""restore template_string in master_templates

Revision ID: b1c2d3e4f5a6
Revises: 8c9d0e1f2a3b
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa


revision = "b1c2d3e4f5a6"
down_revision = "8c9d0e1f2a3b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "master_templates",
        sa.Column("template_string", sa.String(length=99999999), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("master_templates", "template_string")
