import re

from sqlalchemy import and_
from sqlalchemy import func
from app.db.models.client_models import (
    Client,
    AOInformation,
    MasterTemplate,
    TemplateType
)
from app.db.versioning import OPEN_END_DATE


class MasterTemplateRepository:

    def __init__(self, db):
        self.db = db

    # ====================================================
    # CLIENT
    # ====================================================
    def get_client_by_code(self, client_code: str):
        return (
            self.db.query(Client)
            .filter(
                Client.client_code == client_code,
                Client.end_date == OPEN_END_DATE,
                Client.is_deleted == False,
                Client.is_active == True,
            )
            .first()
        )

    # ====================================================
    # AO (FIXED 🔥)
    # ====================================================
    def get_ao(self, client_id: int, ao_code: str):
        return (
            self.db.query(AOInformation)
            .filter(
                AOInformation.client_id == client_id,
                AOInformation.ao_code == ao_code,
                AOInformation.end_date == OPEN_END_DATE,
                AOInformation.is_deleted == False,
                AOInformation.is_active == True,
            )
            .first()
        )

    # ====================================================
    # TEMPLATE TYPE
    # ====================================================
    def get_template_type(self, template_type: str):
        return (
            self.db.query(TemplateType)
            .filter(
                TemplateType.template_type == template_type,
                TemplateType.end_date == OPEN_END_DATE,
                TemplateType.is_deleted == False,
                TemplateType.is_active == True,
            )
            .first()
        )

    # ====================================================
    # SEED
    # ====================================================
    def seed_template_types_if_empty(self):
        if self.db.query(TemplateType).first():
            return

        data = [
            ("Section 13(2)", "S132"),
            ("Section 13(4)", "S134"),
            ("Section 14", "S14"),
            ("Publication", "PUBL"),
            ("Auction", "AUCT"),
        ]

        for name, code in data:
            self.db.add(
                TemplateType(template_type=name, service_code=code)
            )

        self.db.commit()

    # ====================================================
    # LAST SEQUENCE (MISSING FIX 🔥)
    # ====================================================
    def get_last_sequence(self, template_type_id: int):
        # Use the maximum numeric suffix from template_code values for this template type.
        # Ordering by latest row id can reuse an already-assigned code when historical inserts
        # arrive out of sequence, which causes duplicate (template_code, version) on upload.
        rows = (
            self.db.query(MasterTemplate.template_code)
            .filter(MasterTemplate.template_type_id == template_type_id)
            .all()
        )

        max_seq = 0
        for (template_code,) in rows:
            if not template_code:
                continue
            match = re.search(r"/T/(\d+)$", str(template_code).strip())
            if not match:
                continue
            seq = int(match.group(1))
            if seq > max_seq:
                max_seq = seq

        return max_seq

    # ====================================================
    # ACTIVE TEMPLATE (FIXED 🔥)
    # ====================================================
    def get_active_template(self, client_id, template_type_id):

        query = self.db.query(MasterTemplate).filter(
            MasterTemplate.client_id == client_id,
            MasterTemplate.template_type_id == template_type_id,
            MasterTemplate.end_date == OPEN_END_DATE,
            MasterTemplate.is_deleted == False,
            MasterTemplate.is_active == True,
        )

        return query.first()

    # ====================================================
    # GET ALL
    # ====================================================
    def get_all_active_templates(self):
        latest = (
            self.db.query(
                MasterTemplate.template_code,
                func.max(MasterTemplate.version).label("max_version"),
            )
            .filter(
                MasterTemplate.is_deleted == False,
                MasterTemplate.is_active == True,
            )
            .group_by(MasterTemplate.template_code)
            .subquery()
        )
        return (
            self.db.query(MasterTemplate)
            .join(
                latest,
                and_(
                    MasterTemplate.template_code == latest.c.template_code,
                    MasterTemplate.version == latest.c.max_version,
                ),
            )
            .filter(
                MasterTemplate.is_deleted == False,
                MasterTemplate.is_active == True,
            )
            .all()
        )

    # ====================================================
    # FILTER CLIENT
    # ====================================================
    def get_templates_by_client(self, client_code: str):
        latest = (
            self.db.query(
                MasterTemplate.template_code,
                func.max(MasterTemplate.version).label("max_version"),
            )
            .join(Client, MasterTemplate.client_id == Client.id)
            .filter(
                Client.client_code == client_code,
                MasterTemplate.is_deleted == False,
                MasterTemplate.is_active == True,
            )
            .group_by(MasterTemplate.template_code)
            .subquery()
        )
        return (
            self.db.query(MasterTemplate)
            .join(Client, MasterTemplate.client_id == Client.id)
            .join(
                latest,
                and_(
                    MasterTemplate.template_code == latest.c.template_code,
                    MasterTemplate.version == latest.c.max_version,
                ),
            )
            .filter(
                Client.client_code == client_code,
                MasterTemplate.is_deleted == False,
                MasterTemplate.is_active == True,
            )
            .all()
        )

    # ====================================================
    # FILTER TYPE
    # ====================================================
    def get_templates_by_type(self, template_type_id: int):
        latest = (
            self.db.query(
                MasterTemplate.template_code,
                func.max(MasterTemplate.version).label("max_version"),
            )
            .filter(
                MasterTemplate.template_type_id == template_type_id,
                MasterTemplate.is_deleted == False,
                MasterTemplate.is_active == True,
            )
            .group_by(MasterTemplate.template_code)
            .subquery()
        )
        return (
            self.db.query(MasterTemplate)
            .join(
                latest,
                and_(
                    MasterTemplate.template_code == latest.c.template_code,
                    MasterTemplate.version == latest.c.max_version,
                ),
            )
            .filter(
                MasterTemplate.template_type_id == template_type_id,
                MasterTemplate.is_deleted == False,
                MasterTemplate.is_active == True,
            )
            .all()
        )

    # ====================================================
    # DROPDOWN
    # ====================================================
    def get_all_template_types(self):
        return (
            self.db.query(TemplateType)
            .filter(
                TemplateType.is_active == True,
                TemplateType.is_deleted == False,
                TemplateType.end_date == OPEN_END_DATE,
            )
            .all()
        )

    # ====================================================
    # INTERNAL METHODS
    # ====================================================
    def get_template_by_id_any(self, template_id: int):
        return (
            self.db.query(MasterTemplate)
            .filter(MasterTemplate.id == template_id)
            .order_by(MasterTemplate.version.desc())
            .first()
        )

    def get_template_by_id_active(self, template_id: int):
        return (
            self.db.query(MasterTemplate)
            .filter(
                MasterTemplate.id == template_id,
                MasterTemplate.end_date == OPEN_END_DATE,
                MasterTemplate.is_deleted == False,
                MasterTemplate.is_active == True,
            )
            .first()
        )

    def get_latest_active_template_by_any_id(self, template_id: int):
        any_row = self.get_template_by_id_any(template_id)
        if not any_row:
            return None

        return (
            self.db.query(MasterTemplate)
            .filter(
                MasterTemplate.template_code == any_row.template_code,
                MasterTemplate.end_date == OPEN_END_DATE,
                MasterTemplate.is_deleted == False,
                MasterTemplate.is_active == True,
            )
            .order_by(MasterTemplate.version.desc(), MasterTemplate.id.desc())
            .first()
        )

    def get_next_template_version(self, template_code: str):
        return (
            self.db.query(func.max(MasterTemplate.version))
            .filter(MasterTemplate.template_code == template_code)
            .scalar()
            or 0
        )
