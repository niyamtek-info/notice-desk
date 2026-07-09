"""add_modt_properties_child_table

Revision ID: f1a2c3d4e5f6
Revises: d0b1f7c2a001
Create Date: 2026-03-08 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d0b1f7c2a001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {col["name"] for col in inspector.get_columns(table_name)}
    return column_name in cols


def upgrade() -> None:
    if not _has_table("extracted_modt_properties"):
        op.create_table(
            "extracted_modt_properties",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("modt_id", sa.Integer(), nullable=False),
            sa.Column("schedule_key", sa.String(length=100), nullable=True),
            sa.Column("property_index", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("property_description", sa.Text(), nullable=True),
            sa.Column("raw_property_text", sa.Text(), nullable=True),
            sa.Column("survey_numbers", sa.String(length=255), nullable=True),
            sa.Column("plot_number", sa.String(length=100), nullable=True),
            sa.Column("extent", sa.String(length=100), nullable=True),
            sa.Column("extent_unit", sa.String(length=50), nullable=True),
            sa.Column("village", sa.String(length=255), nullable=True),
            sa.Column("taluka_or_mandal", sa.String(length=255), nullable=True),
            sa.Column("district", sa.String(length=255), nullable=True),
            sa.Column("state", sa.String(length=100), nullable=True),
            sa.Column("pincode", sa.String(length=20), nullable=True),
            sa.Column("boundary_north", sa.String(length=255), nullable=True),
            sa.Column("boundary_south", sa.String(length=255), nullable=True),
            sa.Column("boundary_east", sa.String(length=255), nullable=True),
            sa.Column("boundary_west", sa.String(length=255), nullable=True),
            sa.Column("address_remarks", sa.Text(), nullable=True),
            sa.Column("confidence", sa.String(length=50), nullable=True),
            sa.Column("source_page_from", sa.Integer(), nullable=True),
            sa.Column("source_page_to", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["modt_id"], ["extracted_modts.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("modt_id", "property_index", name="uq_extracted_modt_properties_modt_idx"),
        )
        op.create_index(
            "ix_extracted_modt_properties_modt_id",
            "extracted_modt_properties",
            ["modt_id"],
            unique=False,
        )

    # Backfill one row per existing MODT where legacy property columns are populated.
    if _has_column("extracted_modts", "property_description"):
        op.execute(
            sa.text(
                """
                INSERT INTO extracted_modt_properties (
                    modt_id, schedule_key, property_index, property_description,
                    survey_numbers, plot_number, extent, village, taluka_or_mandal, district,
                    boundary_north, boundary_south, boundary_east, boundary_west, created_at, updated_at
                )
                SELECT
                    m.id, NULL, 1, m.property_description,
                    m.survey_numbers, m.plot_number, m.extent, m.village, m.mandal, m.district,
                    m.boundary_north, m.boundary_south, m.boundary_east, m.boundary_west,
                    COALESCE(m.created_at, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP
                FROM extracted_modts m
                WHERE m.property_description IS NOT NULL
                  AND TRIM(m.property_description) <> ''
                  AND NOT EXISTS (
                      SELECT 1 FROM extracted_modt_properties p WHERE p.modt_id = m.id
                  )
                """
            )
        )
        op.drop_column("extracted_modts", "property_description")


def downgrade() -> None:
    if not _has_column("extracted_modts", "property_description"):
        op.add_column("extracted_modts", sa.Column("property_description", sa.Text(), nullable=True))

    if _has_table("extracted_modt_properties"):
        # Restore parent description from first property row if missing.
        op.execute(
            sa.text(
                """
                UPDATE extracted_modts m
                JOIN (
                    SELECT p.modt_id, p.property_description
                    FROM extracted_modt_properties p
                    JOIN (
                        SELECT modt_id, MIN(property_index) AS min_idx
                        FROM extracted_modt_properties
                        GROUP BY modt_id
                    ) first_row
                      ON p.modt_id = first_row.modt_id
                     AND p.property_index = first_row.min_idx
                ) x ON x.modt_id = m.id
                SET m.property_description = x.property_description
                WHERE m.property_description IS NULL
                """
            )
        )
        op.drop_index("ix_extracted_modt_properties_modt_id", table_name="extracted_modt_properties")
        op.drop_table("extracted_modt_properties")
