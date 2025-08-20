# src/workflow/repository.py
import uuid
from sqlalchemy.inspection import inspect
from sqlalchemy import select, update
from datetime import datetime, timezone
from src.db.session import get_engine, get_session_maker
from src.models.executive_order import ExecutiveOrder
from src.models.task import Task
from src.models.email_log import EmailLog
from src.workflow.dto import EOIn, LLMTask
from src.db.users import resolve_assignee_name_to_id

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
            "description": eo.body_text,
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

def insert_tasks(eo_id: str | uuid.UUID, tasks: list[LLMTask]) -> int:
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

            # Resolve assignee name to user ID
            assignee_id = resolve_assignee_name_to_id(t.assignee)
            print(f"[DEBUG] Resolving assignee: '{t.assignee}' -> {assignee_id}")

            payload = {
                "eo_id": eo_uuid,
                "title": t.title,
                "description": t.description,
                "status": "Pending PMO approval",
                "due_date": t.due_date,
                "category": t.category_dept,
                "assignee_id": assignee_id,
                "remarks": None,
                "created_at": now,
                "updated_at": now,
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

def get_executive_order(eo_id: str) -> ExecutiveOrder | None:
    """Fetch an ExecutiveOrder by primary key."""
    with SessionLocal() as db:
        return db.get(ExecutiveOrder, eo_id)

# --- new helpers ---

def save_email_log(direction: str, subject: str | None, sender: str | None, recipients: list[str] | None, raw_content: str | None, related_eo_id: str | uuid.UUID | None) -> EmailLog:
    with SessionLocal() as db:
        eo_uuid = None
        if related_eo_id:
            try:
                eo_uuid = uuid.UUID(str(related_eo_id))
            except Exception:
                eo_uuid = None
        log = EmailLog(
            direction=direction,
            subject=subject,
            sender=sender,
            recipients=recipients,
            raw_content=raw_content,
            parsed=False,
            related_eo_id=eo_uuid,
        )
        db.add(log)
        db.commit(); db.refresh(log)
        return log

def update_tasks_status_and_remarks(task_ids: list[str | uuid.UUID], status: str, remarks: str | None) -> int:
    if not task_ids:
        return 0
    uuids: list[uuid.UUID] = []
    for tid in task_ids:
        try:
            uuids.append(uuid.UUID(str(tid)))
        except Exception:
            continue
    if not uuids:
        return 0
    with SessionLocal() as db:
        res = db.execute(
            update(Task)
            .where(Task.id.in_(uuids))
            .values(status=status, remarks=remarks, updated_at=datetime.now(timezone.utc))
        )
        db.commit()
        return res.rowcount or 0


def get_task_ids_by_eo(eo_id: str | uuid.UUID) -> list[str]:
    try:
        eo_uuid = uuid.UUID(str(eo_id))
    except Exception:
        eo_uuid = eo_id
    with SessionLocal() as db:
        rows = db.execute(select(Task.id).where(Task.eo_id == eo_uuid)).all()
        return [str(r[0]) for r in rows]


def update_per_task_remarks(remarks_map: dict[str, str]) -> int:
    if not remarks_map:
        return 0
    updated = 0
    with SessionLocal() as db:
        for tid, rem in remarks_map.items():
            try:
                t_uuid = uuid.UUID(str(tid))
            except Exception:
                continue
            res = db.execute(
                update(Task)
                .where(Task.id == t_uuid)
                .values(remarks=rem, updated_at=datetime.now(timezone.utc))
            )
            updated += res.rowcount or 0
        db.commit()
    return updated