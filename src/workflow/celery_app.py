import os
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready, worker_shutdown, worker_process_init

# Import task logger to register signal handlers
import src.workflow.task_logger  # This ensures signal handlers are registered

BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)

celery_app = Celery(
    "dol_eo_workflow",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["src.workflow.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=300,
    task_soft_time_limit=280,
    broker_connection_retry_on_startup=True,
    task_routes={
        "src.workflow.tasks.store_email": {"queue": "ingest"},
        "src.workflow.tasks.ai_extract_tasks": {"queue": "ai"},
        "src.workflow.tasks.persist_tasks": {"queue": "db"},
        "src.workflow.tasks.send_pmo_review_email": {"queue": "email"},
        "src.workflow.tasks.process_pmo_response": {"queue": "review"},
        "src.workflow.tasks.notify_assignees": {"queue": "email"},
        "src.workflow.tasks.handle_rejected_tasks": {"queue": "ai"},
        "src.workflow.tasks.send_improved_tasks_to_pmo": {"queue": "email"},
        "src.workflow.tasks.process_daily_update_email": {"queue": "ai"},
        "src.workflow.tasks.aggregate_daily_updates": {"queue": "ai"},
        "src.workflow.tasks.send_daily_summary_email": {"queue": "email"},
        "src.workflow.tasks.send_daily_reminders": {"queue": "email"},
    },
    # Celery Beat Schedule for periodic tasks
    beat_schedule={
        'send-daily-reminders': {
            'task': 'src.workflow.tasks.send_daily_reminders',
            'schedule': 60 * 60 * 24,  # Daily at 4pm ET (configured via crontab)
            'args': (),
        },
        'aggregate-daily-updates': {
            'task': 'src.workflow.tasks.aggregate_daily_updates',
            'schedule': crontab(minute=45, hour=17),  # Testing at 01:42 UTC
            'args': ('e06b798b-2972-456b-8e76-459ebf751cf6',),  # EO ID for EO 14249
        },
    },
    # Timezone configuration for ET-based scheduling
    # timezone='America/New_York',
    enable_utc=True,
)

# Email queue signals for Celery workers
@worker_ready.connect
def start_redis_email_processor_worker(sender, **kwargs):
    """Start the Redis email processor in the main worker process only"""
    try:
        import threading
        from src.email.redis_email_processor import start_redis_email_processor
        
        # Start the Redis email processor in a background thread
        processor_thread = threading.Thread(target=start_redis_email_processor, daemon=True)
        processor_thread.start()
        
        print("Redis email processor started in main worker process")
    except Exception as e:
        print(f"Failed to start Redis email processor: {e}")

# Disable email queue in worker subprocesses to prevent concurrent SMTP connections
# @worker_process_init.connect
# def init_email_queue_worker_process(sender, **kwargs):
#     """Initialize email queue in each worker subprocess"""
#     try:
#         from src.email.email_queue import start_global_email_queue
#         import os
#         start_global_email_queue()
#         print(f"Global email queue started in worker subprocess {os.getpid()}")
#     except Exception as e:
#         print(f"Failed to start email queue in worker subprocess: {e}")

@worker_shutdown.connect
def stop_redis_email_processor_worker(sender, **kwargs):
    """Stop the Redis email processor when Celery worker shuts down"""
    try:
        from src.email.redis_email_processor import stop_redis_email_processor
        stop_redis_email_processor()
        print("Redis email processor stopped in Celery worker")
    except Exception as e:
        print(f"Failed to stop Redis email processor in worker: {e}")