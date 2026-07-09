import json
from datetime import datetime, timezone
from typing import Any, Dict

import redis

from app.core.settings import settings


EXTRACTION_PROGRESS: Dict[str, Dict[str, Any]] = {}
DELETED_PROGRESS_IDS: set[str] = set()


_redis_client = None


def _get_redis_client():
    global _redis_client
    if _redis_client not in (None, False):
        return _redis_client
    try:
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.1,
            socket_timeout=0.2,
            retry_on_timeout=False,
            max_connections=5,
        )
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        # Do not permanently negative-cache transient connection failures.
        _redis_client = None
        return None


def _progress_key(file_id: str) -> str:
    return f"extraction_progress:{file_id}"


def _deleted_key(file_id: str) -> str:
    return f"extraction_progress_deleted:{file_id}"


def _is_deleted(file_id: str) -> bool:
    if file_id in DELETED_PROGRESS_IDS:
        return True
    client = _get_redis_client()
    if not client:
        return False
    try:
        return bool(client.get(_deleted_key(file_id)))
    except Exception:
        return False


def set_progress(file_id: str, payload: Dict[str, Any], ttl_seconds: int = 86400):
    DELETED_PROGRESS_IDS.discard(file_id)
    # Always keep local fallback updated.
    current = EXTRACTION_PROGRESS.get(file_id, {})
    if "created_at" not in current:
        current["created_at"] = datetime.now(timezone.utc).isoformat()
    current.update(payload or {})
    current["file_id"] = file_id
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    EXTRACTION_PROGRESS[file_id] = current

    client = _get_redis_client()
    if not client:
        return

    key = _progress_key(file_id)
    client.delete(_deleted_key(file_id))
    existing_raw = client.get(key)
    existing = {}
    if existing_raw:
        try:
            existing = json.loads(existing_raw)
        except Exception:
            existing = {}
    if "created_at" not in existing:
        existing["created_at"] = current.get("created_at")
    existing.update(payload or {})
    existing["file_id"] = file_id
    existing["updated_at"] = current["updated_at"]
    client.setex(key, ttl_seconds, json.dumps(existing))


def get_progress(file_id: str) -> Dict[str, Any]:
    if _is_deleted(file_id):
        return {
            "file_id": file_id,
            "progress": 0,
            "status": "not_found",
            "stage": "No extraction found for this file_id",
        }
    client = _get_redis_client()
    if client:
        raw = client.get(_progress_key(file_id))
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
    return EXTRACTION_PROGRESS.get(
        file_id,
        {
            "file_id": file_id,
            "progress": 0,
            "status": "not_found",
            "stage": "No extraction found for this file_id",
        },
    )


def get_active_for_application(application_number: str) -> Dict[str, Dict[str, Any]]:
    active: Dict[str, Dict[str, Any]] = {}

    def _should_include(data: Dict[str, Any]) -> bool:
        if data.get("application_number") != application_number:
            return False
        status = str(data.get("status") or "").lower()
        progress = data.get("progress", 0)
        if status in {"queued", "processing", "started", "failed"}:
            return True
        try:
            return float(progress or 0) < 100
        except Exception:
            return False

    client = _get_redis_client()
    if client:
        for key in client.scan_iter(match="extraction_progress:*", count=500):
            raw = client.get(key)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if _should_include(data):
                fid = key.split(":", 1)[1]
                if _is_deleted(fid):
                    continue
                active[fid] = data
        return active

    for fid, data in EXTRACTION_PROGRESS.items():
        if _is_deleted(fid):
            continue
        if _should_include(data):
            active[fid] = data
    return active


def get_latest_for_application(application_number: str) -> Dict[str, Any]:
    candidates = []
    client = _get_redis_client()

    if client:
        for key in client.scan_iter(match="extraction_progress:*", count=500):
            raw = client.get(key)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if data.get("application_number") == application_number:
                if _is_deleted(str(data.get("file_id") or key.split(":", 1)[1])):
                    continue
                candidates.append(data)
    else:
        for _, data in EXTRACTION_PROGRESS.items():
            if _is_deleted(str(data.get("file_id") or "")):
                continue
            if data.get("application_number") == application_number:
                candidates.append(data)

    if not candidates:
        return {
            "application_number": application_number,
            "status": "not_found",
            "stage": "No extraction found for this application",
        }

    def _sort_key(item: Dict[str, Any]) -> str:
        return str(item.get("updated_at") or item.get("created_at") or "")

    return sorted(candidates, key=_sort_key, reverse=True)[0]


def delete_progress(file_id: str):
    DELETED_PROGRESS_IDS.add(file_id)
    EXTRACTION_PROGRESS.pop(file_id, None)
    client = _get_redis_client()
    if not client:
        return
    client.setex(_deleted_key(file_id), 86400, "1")
    client.delete(_progress_key(file_id))
