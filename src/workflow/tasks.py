from typing import Dict
from celery import states
from src.workflow.celery_app import celery_app
from src.workflow.dto import EOIn
from src.workflow import repository as repo
from src.workflow.ai import extract_tasks

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.store_email")
def store_email(eo_payload: Dict):
    """
    1) Upsert EO row (idempotent by message_id)
    2) Queue AI extraction
    """
    print("Recived EO", eo_payload)
    eo = EOIn(**eo_payload)
    eo_row = repo.upsert_executive_order(eo)
    repo.update_eo_status(eo_row.id, "received")
    # Chain to AI extraction
    ai_extract_tasks.delay(eo_row.id, eo.body_text if hasattr(eo, "body_text") else eo_payload.get("body_text", ""))
    return {"eo_id": str(eo_row.id)}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.ai_extract_tasks")
def ai_extract_tasks(eo_id: str, body_text: str):
    """
    1) Call AI to get task list
    2) Queue persistence
    """
    tasks = extract_tasks(body_text)
    # Convert to serializable dicts for the next task
    serializable = [t.model_dump() for t in tasks]
    persist_tasks.delay(eo_id, serializable)
    return {"eo_id": eo_id, "task_count": len(serializable)}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.persist_tasks")
def persist_tasks(eo_id: str, tasks_payload: list[dict]):
    """
    1) Persist tasks
    2) Mark EO status
    """
    from src.workflow.dto import TaskCreate
    to_create = []
    for d in tasks_payload or []:
        try:
            to_create.append(TaskCreate.model_validate(d))
        except Exception as e:
            print(f"[persist] drop malformed task: {e!r} :: {d!r}")
    count = repo.insert_tasks(eo_id, to_create)
    
    return {"eo_id": eo_id, "inserted": count}
    