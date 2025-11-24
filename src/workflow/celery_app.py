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
    include=[
        "src.workflow.chains",  # Orchestrated chains
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=300,
    task_soft_time_limit=280,
    broker_connection_retry_on_startup=True,
    task_routes={
        # Orchestrated chains
        "src.workflow.chains.eo_processing_chain.process_eo_chain": {"queue": "ingest"},
        "src.workflow.chains.eo_processing_chain.process_eo_with_auto_approval": {"queue": "ingest"},
        "src.workflow.chains.eo_processing_chain.retry_failed_eo": {"queue": "ingest"},
        "src.workflow.chains.pmo_response_chain.process_pmo_response_chain": {"queue": "review"},
        "src.workflow.chains.pmo_response_chain.handle_bulk_approval": {"queue": "review"},
        "src.workflow.chains.pmo_response_chain.retry_pmo_response": {"queue": "review"},
        "src.workflow.chains.daily_update_chain.process_daily_update_chain": {"queue": "ai"},
        "src.workflow.chains.daily_update_chain.aggregate_daily_updates_chain": {"queue": "ai"},
        "src.workflow.chains.daily_update_chain.send_daily_reminders_chain": {"queue": "email"},
        "src.workflow.chains.daily_update_chain.retry_daily_update": {"queue": "ai"},
    },
    # Celery Beat Schedule for periodic tasks
    beat_schedule={
        # Use new orchestrated chains for scheduled tasks
        'send-daily-reminders': {
            'task': 'src.workflow.chains.daily_update_chain.send_daily_reminders_chain',
            'schedule': 60 * 60 * 24,  # Daily at 4pm ET (configured via crontab)
            'args': (),
        },
        'aggregate-daily-updates': {
            'task': 'src.workflow.chains.daily_update_chain.aggregate_daily_updates_chain',
            'schedule': crontab(minute=44, hour=21),  # Testing at 01:42 UTC
            'args': ('c54091da-e0ee-4157-8de7-678594be0098',),  # EO ID for EO 14249
        },
        
        # Keep original tasks as backup (commented out)
        # 'send-daily-reminders-original': {
        #     'task': 'src.workflow.chains.daily_update_chain.send_daily_reminders_chain',
        #     'schedule': 60 * 60 * 24,
        #     'args': (),
        # },
        # 'aggregate-daily-updates-original': {
        #     'task': 'src.workflow.chains.daily_update_chain.aggregate_daily_updates_chain',
        #     'schedule': crontab(minute=44, hour=21),
        #     'args': ('c54091da-e0ee-4157-8de7-678594be0098',),
        # },
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