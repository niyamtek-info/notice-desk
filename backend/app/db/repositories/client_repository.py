from sqlalchemy.orm import Session, joinedload
from app.db.models.client_models import Client, AOInformation
from sqlalchemy import func
from app.db.versioning import live_filter


class ClientRepository:

    def __init__(self, db: Session):
        self.db = db

    # ====================================================
    # CLIENT METHODS
    # ====================================================

    def create(self, client: Client):
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def get_all(self, skip: int | None = None, limit: int | None = None):
        # NOTE: can't apply .offset()/.limit() directly to a query using
        # joinedload() on a to-many relationship (all_aos) - that limits the
        # joined ROWS, not the number of clients. Page the client IDs first,
        # then eager-load AOs only for that page.
        if skip is None and limit is None:
            return (
                self.db.query(Client)
                .options(joinedload(Client.all_aos))
                .filter(*live_filter(Client))
                .order_by(Client.id.desc())
                .all()
            )

        id_query = (
            self.db.query(Client.id)
            .filter(*live_filter(Client))
            .order_by(Client.id.desc())
        )
        if skip is not None:
            id_query = id_query.offset(skip)
        if limit is not None:
            id_query = id_query.limit(limit)

        client_ids = [row[0] for row in id_query.all()]
        if not client_ids:
            return []

        return (
            self.db.query(Client)
            .options(joinedload(Client.all_aos))
            .filter(Client.id.in_(client_ids))
            .order_by(Client.id.desc())
            .all()
        )

    def get_by_id(self, client_id: int):
        return (
            self.db.query(Client)
            .options(joinedload(Client.all_aos))
            .filter(Client.id == client_id, *live_filter(Client))
            .first()
        )

    def get_by_code(self, client_code: str):
        return (
            self.db.query(Client)
            .options(joinedload(Client.all_aos))
            .filter(Client.client_code == client_code, *live_filter(Client))
            .first()
        )

    # ====================================================
    # AO METHODS
    # ====================================================

    def get_all_aos(self, client_name: str | None = None):
        query = self.db.query(AOInformation).filter(*live_filter(AOInformation))

        if client_name:
            query = query.join(
                Client,
                Client.client_code == AOInformation.client_code,
            ).filter(
                Client.client_name.ilike(f"%{client_name}%"),
                *live_filter(Client),
            )

        return query.order_by(AOInformation.id.desc()).all()

    def get_ao_by_id(self, ao_id: int):
        return (
            self.db.query(AOInformation)
            .filter(
                AOInformation.id == ao_id,
                *live_filter(AOInformation)
            )
            .first()
        )

    def get_aos_by_client_code(self, client_code: str):
        return (
            self.db.query(AOInformation)
            .filter(
                AOInformation.client_code == client_code,
                *live_filter(AOInformation)
            )
            .order_by(AOInformation.id.desc())
            .all()
        )

    def get_ao(self, client_code: str, ao_code: str):
        return (
            self.db.query(AOInformation)
            .filter(
                AOInformation.client_code == client_code,
                AOInformation.ao_code == ao_code,
                *live_filter(AOInformation)
            )
            .first()
        )

    def ao_exists(self, client_code: str, ao_code: str):
        return (
            self.db.query(AOInformation.id)
            .filter(
                AOInformation.client_code == client_code,
                AOInformation.ao_code == ao_code,
                *live_filter(AOInformation)
            )
            .first() is not None
        )
    
    # ====================================================
# INTERNAL METHODS (FOR DELETE / UPDATE ONLY)
# ====================================================

    def get_client_by_id_any(self, client_id: int):
        return (
            self.db.query(Client)
            .filter(Client.id == client_id)   # ✅ NO live_filter
            .order_by(Client.version.desc())
            .first()
        )


    def get_ao_by_id_any(self, ao_id: int):
        return (
            self.db.query(AOInformation)
            .filter(AOInformation.id == ao_id)   # ✅ NO live_filter
            .order_by(AOInformation.version.desc())
            .first()
        )
    
    def get_next_client_version(self, client_code: str):
        return (
            self.db.query(func.max(Client.version))
            .filter(Client.client_code == client_code)
            .scalar()
            or 0
        )

    def get_next_ao_version(self, client_code: str, ao_code: str):
        return (
            self.db.query(func.max(AOInformation.version))
            .filter(
                AOInformation.client_code == client_code,
                AOInformation.ao_code == ao_code
            )
            .scalar()
            or 0
        )

    # ====================================================
    # DELETE METHODS
    # ====================================================

    def soft_delete(self, client: Client):
        client.is_deleted = True
        client.is_active = False
        client.version += 1
        self.db.commit()
        return client

    def soft_delete_ao(self, ao: AOInformation):
        ao.is_deleted = True
        ao.is_active = False
        ao.version += 1
        self.db.commit()
        return ao