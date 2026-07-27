import threading
from typing import Protocol, runtime_checkable

from app.core.settings import settings

# Cached gateway instances, keyed by provider. STORAGE_PROVIDER doesn't
# change at runtime, so constructing a fresh storage.Client() (and, for
# S3Gateway, redoing credential discovery) on every call is pure overhead —
# reuse one instance per process instead.
_gateway_cache: dict[str, object] = {}
_gateway_cache_lock = threading.Lock()


@runtime_checkable
class StorageGateway(Protocol):
    """
    Shared interface implemented by S3Gateway and LocalStorageGateway.
    Callers should obtain an instance via get_storage_gateway() rather than
    importing a concrete gateway directly, so STORAGE_PROVIDER controls
    where files actually end up.
    """

    def upload_file(self, local_path: str, key: str) -> str: ...

    def upload_bytes(self, data: bytes, key: str, filename: str = "") -> str: ...

    def save_json(self, data: dict, key: str) -> str: ...

    def overwrite_json(self, data: dict, key: str) -> str: ...

    def load_json(self, key: str) -> dict: ...

    def download_json(self, key: str) -> dict: ...

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str: ...

    def get_file_bytes(self, file_url: str) -> bytes: ...

    def get_file_bytes_by_key(self, key: str) -> bytes: ...

    def key_from_reference(self, value: str) -> str: ...

    def exists(self, key: str) -> bool: ...


def get_storage_gateway() -> StorageGateway:
    """
    Return the storage gateway selected by settings.STORAGE_PROVIDER.
    "cloud" is backed by Google Cloud Storage (S3Gateway - name kept for
    compatibility with existing calling code). The gateway is a cached
    singleton per provider, reused across requests.
    """
    return _gateway_for_provider(settings.STORAGE_PROVIDER)


def _gateway_for_provider(provider: str) -> StorageGateway | None:
    if provider == "local":
        return _cached_gateway("local")

    if not settings.GCS_BUCKET_NAME:
        return None

    return _cached_gateway("cloud")


def _cached_gateway(provider: str) -> StorageGateway:
    gateway = _gateway_cache.get(provider)
    if gateway is not None:
        return gateway

    with _gateway_cache_lock:
        gateway = _gateway_cache.get(provider)
        if gateway is not None:
            return gateway

        if provider == "local":
            from app.gateways.local_storage_gateway import LocalStorageGateway

            gateway = LocalStorageGateway()
        else:
            from app.gateways.s3_gateway import S3Gateway

            gateway = S3Gateway()

        _gateway_cache[provider] = gateway
        return gateway


def resolve_any_reference_url(reference: str | None, expiration: int = 3600) -> str | None:
    """
    Build a fetchable URL for a stored reference (GCS URL/key, local
    URL/key, whatever was saved) regardless of which STORAGE_PROVIDER
    is active right now. Documents written under a previous backend
    stay viewable after switching STORAGE_PROVIDER, as long as that
    backend is still configured (e.g. GCS_BUCKET_NAME left in place
    even though STORAGE_PROVIDER=local) - no manual migration needed.
    """
    if not reference:
        return None

    if reference.startswith("local://") or "/api/v1/files/" in reference:
        provider_order = ["local", "cloud"]
    elif reference.startswith(("gs://", "s3://", "http")):
        provider_order = ["cloud", "local"]
    else:
        # Bare key - ambiguous by itself. Try whichever backend is
        # active today first, then the other as a fallback.
        provider_order = (
            ["cloud", "local"] if settings.STORAGE_PROVIDER == "cloud" else ["local", "cloud"]
        )

    for provider in provider_order:
        gateway = _gateway_for_provider(provider)
        if gateway is None:
            continue
        key = gateway.key_from_reference(reference)
        if gateway.exists(key):
            return gateway.generate_presigned_url(key, expiration=expiration)

    return None
