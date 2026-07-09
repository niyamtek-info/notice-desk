"""add_raw_text_to_extracted_sales_deed_schedules

Revision ID: d0b1f7c2a001
Revises: 9b2626b50695
Create Date: 2026-03-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0b1f7c2a001'
down_revision: Union[str, Sequence[str], None] = '9b2626b50695'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {col['name'] for col in inspector.get_columns(table_name)}
    return column_name in cols


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_column('extracted_sales_deed_schedules', 'raw_text'):
        op.add_column(
            'extracted_sales_deed_schedules',
            sa.Column('raw_text', sa.Text(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _has_column('extracted_sales_deed_schedules', 'raw_text'):
        op.drop_column('extracted_sales_deed_schedules', 'raw_text')
