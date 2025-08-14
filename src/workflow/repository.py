# src/workflow/repository.py
import uuid
from sqlalchemy.inspection import inspect
from sqlalchemy import select
from datetime import datetime, timezone
from src.db.session import get_engine, get_session_maker
from src.models.executive_order import ExecutiveOrder
from src.models.task import Task
from src.workflow.dto import EOIn, TaskCreate

SessionLocal = get_session_maker(get_engine())

def _eo_columns() -> set[str]:
    return {c.key for c in inspect(ExecutiveOrder).mapper.column_attrs}

def upsert_executive_order(eo: EOIn) -> ExecutiveOrder:
    cols = _eo_columns()
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        existing = db.execute(
            select(ExecutiveOrder).where(ExecutiveOrder.message_id == eo.message_id)
        ).scalar_one_or_none()

        if existing:
            # map EOIn → model fields
            if eo.subject:
                existing.title = eo.subject
            if eo.received_at:
                existing.received_at = eo.received_at
            if eo.sender:
                existing.source_email = eo.sender
            existing.updated_at = now
            db.commit(); db.refresh(existing)
            return existing

        # prepare only valid kwargs for the model
        data = {
            "message_id": eo.message_id,
            "title": eo.subject or "Untitled EO",
            "description": None,
            "source_email": eo.sender,
            "received_at": eo.received_at or now,
            "pdf_url": None,
            "status": "pending",   # enum allows: processed|error|pending
            "created_at": now,
            "updated_at": now,
        }
        # keep only columns the model actually has
        data = {k: v for k, v in data.items() if k in cols}

        obj = ExecutiveOrder(**data)
        db.add(obj)
        db.commit(); db.refresh(obj)
        return obj

def _task_columns() -> set[str]:
    return {c.key for c in inspect(Task).mapper.column_attrs}

def insert_tasks(eo_id: str | uuid.UUID, tasks: list[TaskCreate]) -> int:
    cols = _task_columns()
    now = datetime.now(timezone.utc)

    # eo_id is UUID in DB; coerce if we got a string
    try:
        eo_uuid = uuid.UUID(str(eo_id))
    except Exception:
        eo_uuid = eo_id

    inserted = 0
    with SessionLocal() as db:
        for t in tasks or []:
            # dedupe by (eo_id, title)
            exists = db.execute(
                select(Task).where(Task.eo_id == eo_uuid, Task.title == t.title)
            ).scalar_one_or_none()
            if exists:
                continue

            payload = {
                "eo_id": eo_uuid,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "due_date": t.due_date,
                "category": t.category,
                "created_at": now,
                "updated_at": now,
                # DO NOT pass assignee_email / assignee_name here (no column yet)
                # DO NOT pass category_dept here (no column yet)
            }
            payload = {k: v for k, v in payload.items() if k in cols}
            db.add(Task(**payload))
            inserted += 1

        db.commit()
    return inserted

def update_eo_status(eo_id: str, status: str, error: str | None = None) -> None:
    if status not in {"processed", "error", "pending"}:
        status = "error"
    with SessionLocal() as db:
        eo = db.get(ExecutiveOrder, eo_id)
        if not eo:
            return
        eo.status = status
        eo.updated_at = datetime.now(timezone.utc)
        # only set error_reason if you add that column later
        db.commit()