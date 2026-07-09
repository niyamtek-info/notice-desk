"""add template artifact paths to communications

Revision ID: 0f1e2d3c4b5a
Revises: a9b0c1d2e3f4
Create Date: 2026-04-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0f1e2d3c4b5a"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("communications", sa.Column("html_path", sa.String(length=500), nullable=True))
    op.add_column("communications", sa.Column("pdf_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("communications", "pdf_path")
    op.drop_column("communications", "html_path")
