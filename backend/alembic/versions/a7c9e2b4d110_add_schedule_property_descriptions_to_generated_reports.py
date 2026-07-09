"""add_schedule_property_descriptions_to_generated_reports

Revision ID: a7c9e2b4d110
Revises: f1a2c3d4e5f6
Create Date: 2026-03-09 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c9e2b4d110"
down_revision: Union[str, Sequence[str], None] = "f1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {col["name"] for col in inspector.get_columns(table_name)}
    return column_name in cols


def upgrade() -> None:
    if not _has_column("generated_reports", "schedule_property_descriptions"):
        op.add_column(
            "generated_reports",
            sa.Column("schedule_property_descriptions", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    if _has_column("generated_reports", "schedule_property_descriptions"):
        op.drop_column("generated_reports", "schedule_property_descriptions")
