from celery import Celery

from app.core.settings import settings


celery_app = Celery(
    "matex",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.extraction_worker",
        "app.workers.translation_worker",
        "app.workers.checklist_worker",
    ],
)

celery_app.conf.update(
    # Task tracking & serialization
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600,  # Reduced from 86400: expire results after 1 hour
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # Worker pool configuration - use prefork for better stability with I/O operations
    worker_pool="prefork",
    worker_concurrency=4,  # Optimized for I/O-bound operations
    worker_prefetch_multiplier=2,  # Reduce prefetching for even load distribution
    worker_max_tasks_per_child=1000,  # Recycle workers to prevent memory leaks
    worker_disable_rate_limits=False,
    task_acks_late=True,  # Acknowledge task only after completion
    task_reject_on_worker_lost=True,  # Requeue lost tasks
    
    # Broker connection optimization
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_pool_limit=10,
    broker_transport_options={
        "socket_connect_timeout": 5,
        "socket_timeout": 10,
        "retry_on_timeout": True,
        "visibility_timeout": 3600,  # Task visibility timeout (seconds)
        "max_retries": 3,
    },
    
    # Task execution settings
    task_default_queue="celery",
    task_default_exchange="celery",
    task_default_routing_key="celery",
    task_soft_time_limit=1800,  # 30 minutes soft limit
    task_time_limit=1900,  # 31.66 minutes hard limit
    task_default_retry_delay=60,
    task_max_retries=3,
    task_compression="gzip",
    
    # Task routes for specialized queues
    task_routes={
        "app.workers.extraction_worker.run_extraction_worker": {
            "queue": "extraction_queue",
            "routing_key": "extraction_queue",
            "priority": 10,
        },
        "app.workers.translation_worker.run_translation_worker": {
            "queue": "translation_queue",
            "routing_key": "translation_queue",
            "priority": 5,
        },
        "app.workers.checklist_worker.run_checklist_matching_worker": {
            "queue": "checklist_queue",
            "routing_key": "checklist_queue",
            "priority": 5,
        },
        "app.workers.checklist_worker.run_checklist_validation_worker": {
            "queue": "checklist_queue",
            "routing_key": "checklist_queue",
            "priority": 5,
        },
    },
    
    # Queue definitions
    task_queues={
        "celery": {
            "exchange": "celery",
            "binding_key": "celery",
            "queue_arguments": {"x-max-priority": 10},
        },
        "extraction_queue": {
            "exchange": "extraction",
            "binding_key": "extraction_queue",
            "queue_arguments": {"x-max-priority": 10},
        },
        "translation_queue": {
            "exchange": "translation",
            "binding_key": "translation_queue",
            "queue_arguments": {"x-max-priority": 5},
        },
        "checklist_queue": {
            "exchange": "checklist",
            "binding_key": "checklist_queue",
            "queue_arguments": {"x-max-priority": 5},
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])

# Compatibility with -A app.core.celery_app (without :celery_app)
app = celery_app
celery = celery_app