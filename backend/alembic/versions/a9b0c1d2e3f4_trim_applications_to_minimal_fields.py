"""trim applications to minimal fields

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-03-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a9b0c1d2e3f4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


DROP_COLUMNS = [
    "status",
    "process_status",
    "report_status",
    "submitted_at",
    "approved_at",
    "rejected_at",
    "loan_request_amount",
    "loan_request_date",
    "pre_approval_amount",
    "pre_approval_status",
    "property_type",
    "survey_no",
    "subdivision",
    "plot_number",
    "door_number",
    "building_name",
    "floor",
    "appartment_size",
    "uds",
    "rera_no",
    "rera_status",
    "promotor",
    "name_of_the_project",
    "property_street",
    "property_locality",
    "property_town",
    "taluk",
    "village",
    "district",
    "pincode",
    "zone",
    "extent",
    "latitude",
    "longitude",
    "plan_approval_status",
    "plan_approval_number",
    "building_year",
    "building_value",
    "property_tax_number",
    "waterconnection_number",
    "electricity_connection_number",
    "sro_office",
    "patta_number",
]


def upgrade() -> None:
    for column_name in DROP_COLUMNS:
        op.drop_column("applications", column_name)


def downgrade() -> None:
    op.add_column("applications", sa.Column("status", sa.Enum("Draft", "Submitted", "In-Review", "Approved", "Rejected"), nullable=True))
    op.add_column("applications", sa.Column("process_status", sa.Enum("New", "In Progress", "Completed", "On Hold", "Rejected"), nullable=False, server_default="New"))
    op.add_column("applications", sa.Column("report_status", sa.String(length=50), nullable=False, server_default="Not_Available"))
    op.add_column("applications", sa.Column("submitted_at", sa.DateTime(), nullable=True))
    op.add_column("applications", sa.Column("approved_at", sa.DateTime(), nullable=True))
    op.add_column("applications", sa.Column("rejected_at", sa.DateTime(), nullable=True))
    op.add_column("applications", sa.Column("loan_request_amount", sa.BigInteger(), nullable=True))
    op.add_column("applications", sa.Column("loan_request_date", sa.DateTime(), nullable=True))
    op.add_column("applications", sa.Column("pre_approval_amount", sa.BigInteger(), nullable=True))
    op.add_column("applications", sa.Column("pre_approval_status", sa.String(length=20), nullable=True))
    op.add_column("applications", sa.Column("property_type", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("survey_no", sa.String(length=50), nullable=True))
    op.add_column("applications", sa.Column("subdivision", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("plot_number", sa.String(length=50), nullable=True))
    op.add_column("applications", sa.Column("door_number", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("building_name", sa.String(length=200), nullable=True))
    op.add_column("applications", sa.Column("floor", sa.String(length=50), nullable=True))
    op.add_column("applications", sa.Column("appartment_size", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("uds", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("rera_no", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("rera_status", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("promotor", sa.String(length=255), nullable=True))
    op.add_column("applications", sa.Column("name_of_the_project", sa.String(length=255), nullable=True))
    op.add_column("applications", sa.Column("property_street", sa.Text(), nullable=True))
    op.add_column("applications", sa.Column("property_locality", sa.String(length=255), nullable=True))
    op.add_column("applications", sa.Column("property_town", sa.String(length=255), nullable=True))
    op.add_column("applications", sa.Column("taluk", sa.String(length=255), nullable=True))
    op.add_column("applications", sa.Column("village", sa.String(length=255), nullable=True))
    op.add_column("applications", sa.Column("district", sa.String(length=255), nullable=True))
    op.add_column("applications", sa.Column("pincode", sa.String(length=20), nullable=True))
    op.add_column("applications", sa.Column("zone", sa.String(length=50), nullable=True))
    op.add_column("applications", sa.Column("extent", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("latitude", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("longitude", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("plan_approval_status", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("plan_approval_number", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("building_year", sa.String(length=20), nullable=True))
    op.add_column("applications", sa.Column("building_value", sa.BigInteger(), nullable=True))
    op.add_column("applications", sa.Column("property_tax_number", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("waterconnection_number", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("electricity_connection_number", sa.String(length=100), nullable=True))
    op.add_column("applications", sa.Column("sro_office", sa.String(length=200), nullable=True))
    op.add_column("applications", sa.Column("patta_number", sa.String(length=200), nullable=True))
