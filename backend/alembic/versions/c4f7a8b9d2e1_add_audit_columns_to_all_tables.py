"""add_audit_columns_to_all_tables

Revision ID: c4f7a8b9d2e1
Revises: f1a2c3d4e5f6
Create Date: 2026-03-09 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.base import Base


# revision identifiers, used by Alembic.
revision: str = "c4f7a8b9d2e1"
down_revision: Union[str, Sequence[str], None] = "f1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AUDIT_COLUMNS = (
    ("created_at", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True)),
    ("created_by", sa.Column("created_by", sa.String(length=100), nullable=True)),
    ("updated_at", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True)),
    ("updated_by", sa.Column("updated_by", sa.String(length=100), nullable=True)),
    ("version", sa.Column("version", sa.Integer(), server_default="0", nullable=False)),
    ("effective_date", sa.Column("effective_date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True)),
    ("end_date", sa.Column("end_date", sa.DateTime(timezone=True), server_default=sa.text("'9999-12-12 00:00:00'"), nullable=False)),
    ("is_deleted", sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False)),
)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {col["name"] for col in inspector.get_columns(table_name)}
    return column_name in cols


def upgrade() -> None:
    for table_name in Base.metadata.tables:
        for column_name, column in AUDIT_COLUMNS:
            if not _has_column(table_name, column_name):
                op.add_column(table_name, column.copy())

    for table_name in Base.metadata.tables:
        op.execute(sa.text(f"""
            UPDATE {table_name}
            SET version = COALESCE(version, 0),
                is_deleted = COALESCE(is_deleted, 0),
                end_date = COALESCE(end_date, '9999-12-12 00:00:00')
        """))


def downgrade() -> None:
    for table_name in reversed(list(Base.metadata.tables)):
        for column_name, _ in reversed(AUDIT_COLUMNS):
            if _has_column(table_name, column_name):
                op.drop_column(table_name, column_name)
