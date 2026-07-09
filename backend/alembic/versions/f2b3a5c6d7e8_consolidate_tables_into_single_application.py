"""Consolidate LoanInfo and PropertyInfo into Application table

Revision ID: f2b3a5c6d7e8
Revises: c4f7a8b9d2e1
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = 'f2b3a5c6d7e8'
down_revision = 'c4f7a8b9d2e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ══════════════════════════════════════════════════════════════
    # STEP 1: ADD LOAN_INFO COLUMNS TO APPLICATIONS TABLE
    # ══════════════════════════════════════════════════════════════
    op.add_column('applications', sa.Column('bank_name', sa.String(255), nullable=True))
    op.add_column('applications', sa.Column('loan_account_number', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('loan_requester_name', sa.String(200), nullable=True))
    op.add_column('applications', sa.Column('loan_request_amount', sa.BigInteger(), nullable=True))
    op.add_column('applications', sa.Column('loan_request_date', sa.DateTime(), nullable=True))
    op.add_column('applications', sa.Column('pre_approval_amount', sa.BigInteger(), nullable=True))
    op.add_column('applications', sa.Column('pre_approval_status', sa.String(20), nullable=True))

    # ══════════════════════════════════════════════════════════════
    # STEP 2: ADD PROPERTY_INFO COLUMNS TO APPLICATIONS TABLE
    # ══════════════════════════════════════════════════════════════
    op.add_column('applications', sa.Column('property_type', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('state', sa.String(255), nullable=True))
    op.add_column('applications', sa.Column('survey_no', sa.String(50), nullable=True))
    op.add_column('applications', sa.Column('subdivision', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('plot_number', sa.String(50), nullable=True))
    
    op.add_column('applications', sa.Column('door_number', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('building_name', sa.String(200), nullable=True))
    op.add_column('applications', sa.Column('floor', sa.String(50), nullable=True))
    op.add_column('applications', sa.Column('appartment_size', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('uds', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('rera_no', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('rera_status', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('promotor', sa.String(255), nullable=True))
    op.add_column('applications', sa.Column('name_of_the_project', sa.String(255), nullable=True))
    
    op.add_column('applications', sa.Column('property_street', sa.Text(), nullable=True))
    op.add_column('applications', sa.Column('property_locality', sa.String(255), nullable=True))
    op.add_column('applications', sa.Column('property_town', sa.String(255), nullable=True))
    op.add_column('applications', sa.Column('taluk', sa.String(255), nullable=True))
    op.add_column('applications', sa.Column('village', sa.String(255), nullable=True))
    op.add_column('applications', sa.Column('district', sa.String(255), nullable=True))
    op.add_column('applications', sa.Column('pincode', sa.String(20), nullable=True))
    op.add_column('applications', sa.Column('zone', sa.String(50), nullable=True))
    
    op.add_column('applications', sa.Column('extent', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('latitude', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('longitude', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('plan_approval_status', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('plan_approval_number', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('building_year', sa.String(20), nullable=True))
    op.add_column('applications', sa.Column('building_value', sa.BigInteger(), nullable=True))
    op.add_column('applications', sa.Column('property_tax_number', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('waterconnection_number', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('electricity_connection_number', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('sro_office', sa.String(200), nullable=True))
    op.add_column('applications', sa.Column('patta_number', sa.String(200), nullable=True))

    # ══════════════════════════════════════════════════════════════
    # STEP 3: MIGRATE DATA FROM LOAN_INFO TO APPLICATIONS
    # ══════════════════════════════════════════════════════════════
    op.execute("""
        UPDATE applications a
        JOIN (
            SELECT record_id, bank_name, loan_account_number, loan_requester_name,
                   loan_request_amount, loan_request_date, pre_approval_amount, pre_approval_status
            FROM loan_info
            WHERE is_deleted = FALSE AND end_date = '9999-12-12 00:00:00'
        ) li ON a.record_id = li.record_id AND a.is_deleted = FALSE AND a.end_date = '9999-12-12 00:00:00'
        SET a.bank_name = li.bank_name,
            a.loan_account_number = li.loan_account_number,
            a.loan_requester_name = li.loan_requester_name,
            a.loan_request_amount = li.loan_request_amount,
            a.loan_request_date = li.loan_request_date,
            a.pre_approval_amount = li.pre_approval_amount,
            a.pre_approval_status = li.pre_approval_status
    """)

    # ══════════════════════════════════════════════════════════════
    # STEP 4: MIGRATE DATA FROM PROPERTY_INFO TO APPLICATIONS
    # ══════════════════════════════════════════════════════════════
    op.execute("""
        UPDATE applications a
        JOIN (
            SELECT record_id, property_type, state, survey_no, subdivision, plot_number,
                   door_number, building_name, floor, appartment_size, uds, rera_no, rera_status, promotor,
                   name_of_the_project, property_street, property_locality, property_town, taluk, village,
                   district, pincode, zone, extent, latitude, longitude, plan_approval_status,
                   plan_approval_number, building_year, building_value, property_tax_number,
                   waterconnection_number, electricity_connection_number, sro_office, patta_number
            FROM property_info
            WHERE is_deleted = FALSE AND end_date = '9999-12-12 00:00:00'
        ) pi ON a.record_id = pi.record_id AND a.is_deleted = FALSE AND a.end_date = '9999-12-12 00:00:00'
        SET a.property_type = pi.property_type,
            a.state = pi.state,
            a.survey_no = pi.survey_no,
            a.subdivision = pi.subdivision,
            a.plot_number = pi.plot_number,
            a.door_number = pi.door_number,
            a.building_name = pi.building_name,
            a.floor = pi.floor,
            a.appartment_size = pi.appartment_size,
            a.uds = pi.uds,
            a.rera_no = pi.rera_no,
            a.rera_status = pi.rera_status,
            a.promotor = pi.promotor,
            a.name_of_the_project = pi.name_of_the_project,
            a.property_street = pi.property_street,
            a.property_locality = pi.property_locality,
            a.property_town = pi.property_town,
            a.taluk = pi.taluk,
            a.village = pi.village,
            a.district = pi.district,
            a.pincode = pi.pincode,
            a.zone = pi.zone,
            a.extent = pi.extent,
            a.latitude = pi.latitude,
            a.longitude = pi.longitude,
            a.plan_approval_status = pi.plan_approval_status,
            a.plan_approval_number = pi.plan_approval_number,
            a.building_year = pi.building_year,
            a.building_value = pi.building_value,
            a.property_tax_number = pi.property_tax_number,
            a.waterconnection_number = pi.waterconnection_number,
            a.electricity_connection_number = pi.electricity_connection_number,
            a.sro_office = pi.sro_office,
            a.patta_number = pi.patta_number
    """)

    # ══════════════════════════════════════════════════════════════
    # STEP 5: DROP FOREIGN KEY CONSTRAINTS FROM PROPERTY_IMAGES
    # ══════════════════════════════════════════════════════════════
    # Note: property_images.record_id FK to applications still works as-is

    # ══════════════════════════════════════════════════════════════
    # STEP 6: DROP OLD TABLES
    # ══════════════════════════════════════════════════════════════
    op.drop_table('loan_info')
    op.drop_table('property_info')


def downgrade() -> None:
    # ══════════════════════════════════════════════════════════════
    # RECREATE LOAN_INFO TABLE
    # ══════════════════════════════════════════════════════════════
    op.create_table('loan_info',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.String(36), nullable=False),
        sa.Column('bank_name', sa.String(255), nullable=False),
        sa.Column('loan_account_number', sa.String(100), nullable=False),
        sa.Column('loan_requester_name', sa.String(200), nullable=True),
        sa.Column('loan_request_amount', sa.BigInteger(), nullable=True),
        sa.Column('loan_request_date', sa.DateTime(), nullable=True),
        sa.Column('pre_approval_amount', sa.BigInteger(), nullable=True),
        sa.Column('pre_approval_status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False, server_default='9999-12-12 00:00:00'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['record_id'], ['applications.record_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_id', 'version', name='uq_loan_info_record_version')
    )

    # ══════════════════════════════════════════════════════════════
    # RECREATE PROPERTY_INFO TABLE
    # ══════════════════════════════════════════════════════════════
    op.create_table('property_info',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.String(36), nullable=True),
        sa.Column('property_type', sa.String(100), nullable=True),
        sa.Column('state', sa.String(255), nullable=True),
        sa.Column('survey_no', sa.String(50), nullable=True),
        sa.Column('subdivision', sa.String(100), nullable=True),
        sa.Column('plot_number', sa.String(50), nullable=True),
        sa.Column('door_number', sa.String(100), nullable=True),
        sa.Column('building_name', sa.String(200), nullable=True),
        sa.Column('floor', sa.String(50), nullable=True),
        sa.Column('appartment_size', sa.String(100), nullable=True),
        sa.Column('uds', sa.String(100), nullable=True),
        sa.Column('rera_no', sa.String(100), nullable=True),
        sa.Column('rera_status', sa.String(100), nullable=True),
        sa.Column('promotor', sa.String(255), nullable=True),
        sa.Column('name_of_the_project', sa.String(255), nullable=True),
        sa.Column('property_street', sa.Text(), nullable=True),
        sa.Column('property_locality', sa.String(255), nullable=True),
        sa.Column('property_town', sa.String(255), nullable=True),
        sa.Column('taluk', sa.String(255), nullable=True),
        sa.Column('village', sa.String(255), nullable=True),
        sa.Column('district', sa.String(255), nullable=True),
        sa.Column('pincode', sa.String(20), nullable=True),
        sa.Column('zone', sa.String(50), nullable=True),
        sa.Column('extent', sa.String(100), nullable=True),
        sa.Column('latitude', sa.String(100), nullable=True),
        sa.Column('longitude', sa.String(100), nullable=True),
        sa.Column('plan_approval_status', sa.String(100), nullable=True),
        sa.Column('plan_approval_number', sa.String(100), nullable=True),
        sa.Column('building_year', sa.String(20), nullable=True),
        sa.Column('building_value', sa.BigInteger(), nullable=True),
        sa.Column('property_tax_number', sa.String(100), nullable=True),
        sa.Column('waterconnection_number', sa.String(100), nullable=True),
        sa.Column('electricity_connection_number', sa.String(100), nullable=True),
        sa.Column('sro_office', sa.String(200), nullable=True),
        sa.Column('patta_number', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False, server_default='9999-12-12 00:00:00'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['record_id'], ['applications.record_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # ══════════════════════════════════════════════════════════════
    # REMOVE MIGRATED COLUMNS FROM APPLICATIONS TABLE
    # ══════════════════════════════════════════════════════════════
    # Loan info columns
    op.drop_column('applications', 'bank_name')
    op.drop_column('applications', 'loan_account_number')
    op.drop_column('applications', 'loan_requester_name')
    op.drop_column('applications', 'loan_request_amount')
    op.drop_column('applications', 'loan_request_date')
    op.drop_column('applications', 'pre_approval_amount')
    op.drop_column('applications', 'pre_approval_status')
    
    # Property info columns
    op.drop_column('applications', 'property_type')
    op.drop_column('applications', 'state')
    op.drop_column('applications', 'survey_no')
    op.drop_column('applications', 'subdivision')
    op.drop_column('applications', 'plot_number')
    op.drop_column('applications', 'door_number')
    op.drop_column('applications', 'building_name')
    op.drop_column('applications', 'floor')
    op.drop_column('applications', 'appartment_size')
    op.drop_column('applications', 'uds')
    op.drop_column('applications', 'rera_no')
    op.drop_column('applications', 'rera_status')
    op.drop_column('applications', 'promotor')
    op.drop_column('applications', 'name_of_the_project')
    op.drop_column('applications', 'property_street')
    op.drop_column('applications', 'property_locality')
    op.drop_column('applications', 'property_town')
    op.drop_column('applications', 'taluk')
    op.drop_column('applications', 'village')
    op.drop_column('applications', 'district')
    op.drop_column('applications', 'pincode')
    op.drop_column('applications', 'zone')
    op.drop_column('applications', 'extent')
    op.drop_column('applications', 'latitude')
    op.drop_column('applications', 'longitude')
    op.drop_column('applications', 'plan_approval_status')
    op.drop_column('applications', 'plan_approval_number')
    op.drop_column('applications', 'building_year')
    op.drop_column('applications', 'building_value')
    op.drop_column('applications', 'property_tax_number')
    op.drop_column('applications', 'waterconnection_number')
    op.drop_column('applications', 'electricity_connection_number')
    op.drop_column('applications', 'sro_office')
    op.drop_column('applications', 'patta_number')
