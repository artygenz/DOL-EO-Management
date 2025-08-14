import os
from celery import Celery

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
    },
)