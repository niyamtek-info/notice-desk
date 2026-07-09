"""
Background task store writer - Non-blocking Redis operations.
Prevents API response delays caused by Redis round-trips.
"""
import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from queue import Queue
import redis

from app.core.settings import settings


# Global background writer thread
_bg_queue: Optional[Queue] = None
_bg_thread: Optional[threading.Thread] = None
_redis_pool: Optional[redis.ConnectionPool] = None
_started = False


def _get_redis_connection():
    """Get a redis connection from the pool."""
    global _redis_pool
    if _redis_pool is None:
        try:
            _redis_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.1,
                socket_timeout=0.2,
                retry_on_timeout=False,
                max_connections=10,
            )
        except Exception as e:
            print(f"WARNING: Cannot create Redis pool: {e}")
            return None
    
    try:
        client = redis.Redis(connection_pool=_redis_pool)
        return client
    except Exception as e:
        print(f"WARNING: Cannot get Redis connection: {e}")
        return None


def _background_writer_worker():
    """Background thread that writes to Redis without blocking API responses."""
    while True:
        try:
            item = _bg_queue.get(timeout=1)
            if item is None:  # Shutdown signal
                break
            
            operation_type, key, value, ttl = item
            client = _get_redis_connection()
            if not client:
                continue
            
            try:
                if operation_type == "setex":
                    client.setex(key, ttl, value)
                elif operation_type == "delete":
                    client.delete(key)
            except Exception as e:
                # Silently fail - this is best-effort background operation
                pass
        except Exception:
            pass


def start_background_writer():
    """Initialize the background writer thread."""
    global _bg_queue, _bg_thread, _started
    
    if _started:
        return
    
    _bg_queue = Queue(maxsize=1000)
    _bg_thread = threading.Thread(target=_background_writer_worker, daemon=True)
    _bg_thread.start()
    _started = True


def enqueue_store_operation(operation_type: str, key: str, value: str, ttl: int = 86400):
    """
    Enqueue a background store operation.
    Non-blocking: returns immediately.
    """
    if not _started:
        start_background_writer()
    
    try:
        _bg_queue.put_nowait((operation_type, key, value, ttl))
    except Exception:
        # Queue full - discard silently (Redis operation is non-critical)
        pass


def set_progress_async(file_id: str, payload: Dict[str, Any], ttl_seconds: int = 86400):
    """
    Set extraction progress asynchronously (non-blocking).
    Returns immediately without waiting for Redis.
    """
    # Keep the progress payload shape identical to Celery updates.
    # This updates local fallback memory and Redis using the same merge logic
    # that the worker uses for subsequent progress transitions.
    from app.core.progress_store import set_progress

    set_progress(file_id, payload or {}, ttl_seconds=ttl_seconds)


def set_task_async(task_id: str, payload: Dict[str, Any], ttl_seconds: int = 86400):
    """
    Set task status asynchronously (non-blocking).
    Returns immediately without waiting for Redis.
    """
    current = {
        "task_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    current.update(payload or {})
    
    value_json = json.dumps(current)
    key = f"async_task:{task_id}"
    enqueue_store_operation("setex", key, value_json, ttl_seconds)


def set_latest_for_application_async(task_type: str, application_number: str, task_id: str, ttl_seconds: int = 86400):
    """
    Set latest task for application asynchronously (non-blocking).
    """
    key = f"async_task_idx:{task_type}:{application_number}"
    enqueue_store_operation("setex", key, task_id, ttl_seconds)


def delete_progress_async(file_id: str):
    """Delete progress asynchronously."""
    key = f"extraction_progress:{file_id}"
    enqueue_store_operation("delete", key, "", 0)
