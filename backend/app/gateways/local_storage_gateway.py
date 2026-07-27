import json
import logging
import shutil
from pathlib import Path

from app.core.settings import settings
from app.gateways.local_url_signing import sign

logger = logging.getLogger(__name__)

_FILES_ROUTE_PREFIX = "/api/v1/files/"


class LocalStorageGateway:
    """
    Disk-backed storage gateway with the same method surface as S3Gateway,
    so callers can switch backends via STORAGE_PROVIDER without code changes.
    Files are written under LOCAL_STORAGE_ROOT using the same key structure
    S3 keys already use, and served back over HTTP via the authenticated
    /api/v1/files/{key} route (see app/api/v1/routers/files_router.py).
    """

    def _path_for_key(self, key: str) -> Path:
        return Path(settings.LOCAL_STORAGE_ROOT).joinpath(*key.split("/"))

    def _url_for_key(self, key: str) -> str:
        base_url = settings.LOCAL_STORAGE_BASE_URL.rstrip("/")
        return f"{base_url}{_FILES_ROUTE_PREFIX}{key}"

    def key_from_reference(self, file_url: str) -> str:
        value = file_url.split("?", 1)[0]
        if value.startswith("local://"):
            return value[len("local://"):]
        if _FILES_ROUTE_PREFIX in value:
            return value.split(_FILES_ROUTE_PREFIX, 1)[-1]
        # Bare key (no scheme/prefix) - already what we need.
        return value

    # -----------------------------------------------------------
    # Upload File
    # -----------------------------------------------------------
    def upload_file(self, local_path: str, key: str) -> str:
        dest = self._path_for_key(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, dest)
        return self._url_for_key(key)

    # -----------------------------------------------------------
    # Upload Raw Bytes
    # -----------------------------------------------------------
    def upload_bytes(self, data: bytes, key: str, filename: str = "") -> str:
        dest = self._path_for_key(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return self._url_for_key(key)

    # -----------------------------------------------------------
    # Save / Overwrite JSON
    # -----------------------------------------------------------
    def save_json(self, data: dict, key: str) -> str:
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        return self.upload_bytes(payload.encode("utf-8"), key)

    def overwrite_json(self, data: dict, key: str) -> str:
        return self.save_json(data, key)

    # -----------------------------------------------------------
    # Load / Download JSON
    # -----------------------------------------------------------
    def load_json(self, key: str) -> dict:
        dest = self._path_for_key(self.key_from_reference(key))
        return json.loads(dest.read_text(encoding="utf-8"))

    def download_json(self, key: str) -> dict:
        try:
            return self.load_json(key)
        except Exception as e:
            raise RuntimeError(f"Failed to load local JSON ({key}): {e}")

    # -----------------------------------------------------------
    # Presigned URL - mirrors an S3 presigned URL: self-contained and
    # fetchable without a login token, valid for `expiration` seconds.
    # The /files route also accepts a normal bearer token as an
    # alternative, for authenticated in-app fetches.
    # -----------------------------------------------------------
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        resolved_key = self.key_from_reference(key)
        expires, signature = sign(resolved_key, expiration)
        base = self._url_for_key(resolved_key)
        return f"{base}?expires={expires}&sig={signature}"

    # -----------------------------------------------------------
    # Fetch bytes
    # -----------------------------------------------------------
    def get_file_bytes(self, file_url: str) -> bytes:
        return self.get_file_bytes_by_key(self.key_from_reference(file_url))

    def get_file_bytes_by_key(self, key: str) -> bytes:
        dest = self._path_for_key(key)
        try:
            return dest.read_bytes()
        except FileNotFoundError as e:
            raise Exception(f"Failed to fetch local file for key ({key}): {e}")

    # -----------------------------------------------------------
    # Cheap existence check
    # -----------------------------------------------------------
    def exists(self, key: str) -> bool:
        return self._path_for_key(key).is_file()
