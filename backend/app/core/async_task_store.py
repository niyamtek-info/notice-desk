import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis

from app.core.settings import settings


ASYNC_TASKS: Dict[str, Dict[str, Any]] = {}
ASYNC_TASK_INDEX: Dict[str, str] = {}
_redis_client = None


def _get_redis_client():
    global _redis_client
    if _redis_client is not None:
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
    except Exception:
        # Silently fail - in-memory fallback is acceptable
        _redis_client = False
        return None


def _task_key(task_id: str) -> str:
    return f"async_task:{task_id}"


def _task_index_key(task_type: str, application_number: str) -> str:
    return f"async_task_idx:{task_type}:{application_number}"


def set_task(task_id: str, payload: Dict[str, Any], ttl_seconds: int = 86400):
    current = ASYNC_TASKS.get(task_id, {})
    if "created_at" not in current:
        current["created_at"] = datetime.now(timezone.utc).isoformat()
    current.update(payload or {})
    current["task_id"] = task_id
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    ASYNC_TASKS[task_id] = current

    client = _get_redis_client()
    if not client:
        return
    try:
        # Fast-path write: avoid extra Redis GET round-trip in request path.
        client.setex(_task_key(task_id), ttl_seconds, json.dumps(current))
    except Exception:
        pass


def get_task(task_id: str) -> Dict[str, Any]:
    client = _get_redis_client()
    if client:
        try:
            raw = client.get(_task_key(task_id))
            if raw:
                try:
                    return json.loads(raw)
                except Exception:
                    pass
        except Exception:
            pass
    return ASYNC_TASKS.get(task_id, {"task_id": task_id, "status": "not_found"})


def set_latest_for_application(task_type: str, application_number: str, task_id: str, ttl_seconds: int = 86400):
    idx = _task_index_key(task_type, application_number)
    ASYNC_TASK_INDEX[idx] = task_id
    client = _get_redis_client()
    if not client:
        return
    try:
        client.setex(idx, ttl_seconds, task_id)
    except Exception:
        pass


def get_latest_for_application(task_type: str, application_number: str) -> Optional[Dict[str, Any]]:
    idx = _task_index_key(task_type, application_number)
    task_id = None

    client = _get_redis_client()
    if client:
        try:
            task_id = client.get(idx)
        except Exception:
            task_id = None
    else:
        task_id = ASYNC_TASK_INDEX.get(idx)

    if not task_id:
        return None
    return get_task(task_id)
