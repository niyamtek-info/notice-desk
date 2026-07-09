"""Move rerun_report from application_checklists to sarfaesi_master

Revision ID: 7f1c2d3e4b5a
Revises: e7f8a9b0c1d2
Create Date: 2026-04-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f1c2d3e4b5a"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("sarfaesi_master", "rerun_report"):
        op.add_column(
            "sarfaesi_master",
            sa.Column("rerun_report", sa.Integer(), nullable=False, server_default="1"),
        )

    if _has_column("application_checklists", "rerun_report"):
        op.drop_column("application_checklists", "rerun_report")


def downgrade() -> None:
    if not _has_column("application_checklists", "rerun_report"):
        op.add_column(
            "application_checklists",
            sa.Column("rerun_report", sa.Integer(), nullable=False, server_default="1"),
        )

    if _has_column("sarfaesi_master", "rerun_report"):
        op.drop_column("sarfaesi_master", "rerun_report")
