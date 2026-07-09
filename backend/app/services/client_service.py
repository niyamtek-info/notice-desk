import uuid
import base64
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.client_models import Client, AOInformation
from app.api.v1.schemas.client_schema import AOResponse, ClientResponse
from app.db.repositories.client_repository import ClientRepository
from app.api.v1.dependencies.auth import AuditUser
from app.db.versioning import mark_created, close_version, clone_version, OPEN_END_DATE
from app.gateways.s3_gateway import S3Gateway


class ClientService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = ClientRepository(db)
        self.s3 = S3Gateway()

    # ====================================================
    # COMMON UTILS
    # ====================================================

    def _file_to_base64(self, file_url: str):
        try:
            if not file_url:
                return None
            file_bytes = self.s3.get_file_bytes(file_url)
            return base64.b64encode(file_bytes).decode("utf-8")
        except Exception:
            return None

    def _build_s3_filename(self, name: str) -> str:
        return f"{uuid.uuid4().hex[:8]}_{name}"

    def _decode_base64(self, data: str):
        try:
            return base64.b64decode(data.split(",")[-1])
        except Exception:
            raise HTTPException(400, "Invalid base64")

    # ====================================================
    # RESPONSE HELPERS
    # ====================================================

    def _attach_ao_base64(self, ao):
        if ao.signature_path and not ao.signature_path.startswith("data"):
            try:
                file_bytes = self.s3.get_file_bytes(ao.signature_path)
                base64_data = base64.b64encode(file_bytes).decode("utf-8")

                # ✅ DO NOT overwrite DB field
                setattr(ao, "signature_base64", f"data:image/png;base64,{base64_data}")

                file_name = ao.signature_path.split("/")[-1]
                setattr(ao, "file_name", file_name)

            except Exception as e:
                print("ERROR:", e)
                setattr(ao, "signature_base64", None)

        return ao

    

    def _attach_client_base64(self, client):
        if client.logo_path and not client.logo_path.startswith("data"):
            try:
                file_bytes = self.s3.get_file_bytes(client.logo_path)
                base64_data = base64.b64encode(file_bytes).decode("utf-8")

                # ✅ DO NOT overwrite original field
                setattr(client, "logo_base64", f"data:image/png;base64,{base64_data}")

                client.file_name = client.logo_path.split("/")[-1]

            except Exception:
                setattr(client, "logo_base64", None)
                client.file_name = None

        return client

    # ====================================================
    # CLIENT CRUD
    # ====================================================

    def create_client(self, client_code, client_name, client_type, description,
                      logo_path, logo_file_name, audit_user):

        if self.repo.get_by_code(client_code):
            raise HTTPException(400, "Client already exists (active)")

        s3_logo_path = None
        if logo_path:
            content = self._decode_base64(logo_path)
            file_name = self._build_s3_filename(logo_file_name or "logo.png")
            key = f"Client/{client_code}/logo/{file_name}"
            s3_logo_path = self.s3.upload_bytes(content, key, logo_file_name)

        max_version = self.repo.get_next_client_version(client_code)

        client = Client(
            client_code=client_code,
            client_name=client_name,
            client_type=client_type,
            description=description,
            logo_path=s3_logo_path,
            version=max_version + 1
        )

        mark_created(client, audit_user)
        self.db.add(client)
        self.db.commit()

        return self._attach_client_base64(client)

    def get_all_clients(self):
        clients = self.repo.get_all()

        result = []

        for client in clients:
            client = self._attach_client_base64(client)

            aos = self.repo.get_aos_by_client_code(client.client_code)

            ao_list = []
            for ao in aos:

                # ✅ FILTER AO (VERY IMPORTANT)
                if not (
                    ao.end_date == OPEN_END_DATE and
                    ao.is_active and
                    not ao.is_deleted
                ):
                    continue

                ao = self._attach_ao_base64(ao)

                ao_list.append(AOResponse(
                    id=ao.id,
                    client_code=ao.client_code,
                    ao_code=ao.ao_code,
                    ao_name=ao.ao_name,
                    ao_email=ao.ao_email,
                    signature_path=getattr(ao, "signature_base64", None),
                    file_name=getattr(ao, "file_name", None),
                    version=ao.version,
                    is_active=ao.is_active
                ))

            result.append(ClientResponse(
                id=client.id,
                client_code=client.client_code,
                client_name=client.client_name,
                client_type=client.client_type,
                description=client.description,
                logo_path=getattr(client, "logo_base64", None),
                file_name=getattr(client, "file_name", None),
                version=client.version,
                is_active=client.is_active,
                created_at=client.created_at,
                aos=ao_list
            ))

        return result

    def get_client(self, client_id):
        client = self.repo.get_by_id(client_id)
        if not client:
            raise HTTPException(404, "Client not found")
        return self._attach_client_base64(client)

    def update_client(self, client_id, payload, audit_user):
        client = self.repo.get_client_by_id_any(client_id)
        if not client:
            raise HTTPException(404, "Client not found")

        updates = {}

        for f in ["client_name", "client_type", "description", "is_active"]:
            if f in payload:
                updates[f] = payload[f]
        
        # ✅ HANDLE DELETE LOGO (even if logo not sent)
        if "logo" in payload and payload.get("logo") == "":
            updates["logo_path"] = None

        # ✅ logo update
        logo_data = payload.get("logo_path") or payload.get("logo")

        if logo_data:
            
            if logo_data.startswith("data"):
                content = self._decode_base64(logo_data)

                file_name = self._build_s3_filename(
                    payload.get("logo_file_name") or "logo.png"
                )

                key = f"Client/{client.client_code}/logo/{file_name}"

                updates["logo_path"] = self.s3.upload_bytes(
                    content, key, payload.get("logo_file_name")
                )
            else:
                updates["logo_path"] = logo_data

        if updates:
            max_version = self.repo.get_next_client_version(client.client_code)

            active = self.db.query(Client).filter(
                Client.client_code == client.client_code,
                Client.end_date == OPEN_END_DATE
            ).all()

            # 👉 get correct source BEFORE closing
            current_active = active[0] if active else client

            # 👉 close old versions
            for row in active:
                close_version(row, audit_user)

            # 👉 clone from correct version
            new_client = clone_version(current_active, audit_user, **updates)
            new_client.version = max_version + 1

            self.db.add(new_client)
            self.db.commit()

            return self._attach_client_base64(new_client)

        return self._attach_client_base64(client)

    def delete_client(self, client_id, audit_user):
        client = self.repo.get_client_by_id_any(client_id)
        if not client:
            raise HTTPException(404, "Client not found")

        if client.is_deleted:
            raise HTTPException(400, "Already deleted")

        max_version = self.repo.get_next_client_version(client.client_code)

        active = self.db.query(Client).filter(
            Client.client_code == client.client_code,
            Client.end_date == OPEN_END_DATE
        ).all()

        for row in active:
            close_version(row, audit_user)

        deleted = clone_version(client, audit_user, is_deleted=True, is_active=False)
        deleted.version = max_version + 1

        self.db.add(deleted)
        self.db.commit()

        return {"message": "Client deleted"}

    def _generate_ao_code(self, client_code: str) -> str:
        aos = self.repo.get_aos_by_client_code(client_code)

        aos = [
            ao for ao in aos
            if ao.is_active and not ao.is_deleted and ao.end_date == OPEN_END_DATE
        ]

        if not aos:
            return "AO-001"

        numbers = []
        for ao in aos:
            try:
                num = int(ao.ao_code.split("-")[-1])
                numbers.append(num)
            except:
                continue

        next_num = max(numbers) + 1 if numbers else 1

        return f"AO-{str(next_num).zfill(3)}"
    # ====================================================
    # AO CRUD
    # ====================================================

    def create_ao(self, client_code, ao_name, ao_email,
                  signature_path, signature_file_name, audit_user):

        client = self.repo.get_by_code(client_code)
        if not client:
            raise HTTPException(404, "Client not found")

        ao_code = self._generate_ao_code(client_code)

        s3_path = None
        if signature_path:
            content = self._decode_base64(signature_path)
            file_name = self._build_s3_filename(signature_file_name or "signature.png")
            key = f"Client/{client_code}/{ao_code}/signature/{file_name}"
            s3_path = self.s3.upload_bytes(content, key, signature_file_name)

        max_version = self.repo.get_next_ao_version(client_code, ao_code)

        ao = AOInformation(
            client_id=client.id,
            client_code=client_code,
            ao_code=ao_code,
            ao_name=ao_name,
            ao_email=ao_email,
            signature_path=s3_path,
            version=max_version + 1
        )

        mark_created(ao, audit_user)
        self.db.add(ao)
        self.db.commit()

        return self._attach_ao_base64(ao)

    def update_ao(self, ao_id, payload, audit_user):
        ao = self.repo.get_ao_by_id(ao_id)
        if not ao:
            raise HTTPException(404, "AO not found")

        updates = {}

        for f in ["ao_name", "ao_email", "is_active"]:
            if f in payload:
                updates[f] = payload[f]

        if payload.get("signature_path"):
            if payload["signature_path"].startswith("data"):
                content = self._decode_base64(payload["signature_path"])

                file_name = self._build_s3_filename(
                    payload.get("signature_file_name") or "signature.png"
                )

                key = f"Client/{ao.client_code}/{ao.ao_code}/signature/{file_name}"

                updates["signature_path"] = self.s3.upload_bytes(
                    content, key, payload.get("signature_file_name")
                )
            else:
                # already S3 path
                updates["signature_path"] = payload["signature_path"]
                content = self._decode_base64(payload["signature_path"])
                file_name = self._build_s3_filename(payload.get("signature_file_name") or "signature.png")
                key = f"Client/{ao.client_code}/{ao.ao_code}/signature/{file_name}"
                updates["signature_path"] = self.s3.upload_bytes(content, key, payload.get("signature_file_name"))

        if updates:
            max_version = self.repo.get_next_ao_version(ao.client_code, ao.ao_code)

            active = self.db.query(AOInformation).filter(
                AOInformation.client_code == ao.client_code,
                AOInformation.ao_code == ao.ao_code,
                AOInformation.end_date == OPEN_END_DATE
            ).all()

            for row in active:
                close_version(row, audit_user)

            updated = clone_version(ao, audit_user, **updates)
            updated.version = max_version + 1

            self.db.add(updated)
            self.db.commit()

            return self._attach_ao_base64(updated)

        return self._attach_ao_base64(ao)

    def delete_ao(self, ao_id, audit_user):
        ao = self.repo.get_ao_by_id_any(ao_id)
        if not ao:
            raise HTTPException(404, "AO not found")

        if ao.is_deleted:
            raise HTTPException(400, "Already deleted")

        max_version = self.repo.get_next_ao_version(ao.client_code, ao.ao_code)

        active = self.db.query(AOInformation).filter(
            AOInformation.client_code == ao.client_code,
            AOInformation.ao_code == ao.ao_code,
            AOInformation.end_date == OPEN_END_DATE
        ).all()

        for row in active:
            close_version(row, audit_user)

        deleted = clone_version(ao, audit_user, is_deleted=True, is_active=False)
        deleted.version = max_version + 1

        self.db.add(deleted)
        self.db.commit()

        return {"message": "AO deleted"}

    def get_all_aos(self):
        aos = self.repo.get_all_aos()
        for ao in aos:
            self._attach_ao_base64(ao)
        return aos

    def get_aos_by_client(self, client_code):
        aos = self.repo.get_aos_by_client_code(client_code)

        result = []
        for ao in aos:
            ao = self._attach_ao_base64(ao)

            result.append(AOResponse(
                id=ao.id,
                client_code=ao.client_code,
                ao_code=ao.ao_code,
                ao_name=ao.ao_name,
                ao_email=ao.ao_email,
                signature_path=ao.signature_path,
                file_name=getattr(ao, "file_name", None),
                version=ao.version,
                is_active=ao.is_active
            ))

        return result