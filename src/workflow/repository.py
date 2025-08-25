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
    """Upsert EO by message_id, return EO row."""
    with SessionLocal() as db:
        existing = db.execute(
            select(ExecutiveOrder).where(ExecutiveOrder.message_id == eo.message_id)
        ).scalar_one_or_none()
        
        if existing:
            # Update existing EO
            existing.title = eo.subject
            existing.source_email = eo.sender
            existing.received_at = eo.received_at
            existing.description = eo.body_text
            # Update pdf_url if S3 attachment is available
            if eo.raw_mime_s3_key:
                # Generate a presigned URL for the S3 object
                try:
                    from src.email.s3_service import S3Service
                    s3_service = S3Service()
                    pdf_url = s3_service.get_file_url(eo.raw_mime_s3_key)
                    if pdf_url:
                        existing.pdf_url = pdf_url
                except Exception as e:
                    print(f"Error generating PDF URL: {e}")
            db.commit(); db.refresh(existing)
            return existing
        
        # Create new EO
        pdf_url = None
        if eo.raw_mime_s3_key:
            # Generate a presigned URL for the S3 object
            try:
                from src.email.s3_service import S3Service
                s3_service = S3Service()
                pdf_url = s3_service.get_file_url(eo.raw_mime_s3_key)
            except Exception as e:
                print(f"Error generating PDF URL: {e}")
        
        new_eo = ExecutiveOrder(
            message_id=eo.message_id,
            title=eo.subject,
            source_email=eo.sender,
            received_at=eo.received_at,
            description=eo.body_text,
            pdf_url=pdf_url,
            status="received",
        )
        db.add(new_eo)
        db.commit(); db.refresh(new_eo)
        return new_eo

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
        tasks = db.execute(
            select(Task.id).where(Task.eo_id == eo_uuid).order_by(Task.created_at)
        ).scalars().all()
        return [str(task_id) for task_id in tasks]

def get_pending_task_ids_by_eo(eo_id: str | uuid.UUID) -> list[str]:
    """
    Get task IDs for an EO that are currently in 'Pending PMO approval' status.
    This is used when PMO says 'approve all' - we only approve the pending tasks.
    """
    try:
        eo_uuid = uuid.UUID(str(eo_id))
    except Exception:
        eo_uuid = eo_id
    
    with SessionLocal() as db:
        # First verify the EO exists
        eo = db.execute(select(ExecutiveOrder).where(ExecutiveOrder.id == eo_uuid)).scalar_one_or_none()
        if not eo:
            print(f"ERROR: EO with ID '{eo_id}' not found in database")
            return []
        
        tasks = db.execute(
            select(Task.id).where(
                Task.eo_id == eo_uuid,
                Task.status == "Pending PMO approval"
            ).order_by(Task.created_at)
        ).scalars().all()
        
        task_ids = [str(task_id) for task_id in tasks]
        print(f"Found {len(task_ids)} pending tasks for EO {eo_id}: {task_ids}")
        return task_ids

def map_simple_task_ids_to_uuids(eo_id: str | uuid.UUID, simple_task_ids: list[str]) -> list[str]:
    """
    Map simple task IDs (1, 2, 3, etc.) to actual database UUIDs.
    This assumes tasks are ordered by creation time within an EO.
    """
    try:
        eo_uuid = uuid.UUID(str(eo_id))
    except Exception:
        eo_uuid = eo_id
    
    with SessionLocal() as db:
        # Get all tasks for this EO, ordered by creation time
        tasks = db.execute(
            select(Task.id).where(Task.eo_id == eo_uuid).order_by(Task.created_at)
        ).scalars().all()
        
        task_list = list(tasks)
        print(f"DEBUG: EO {eo_id} has {len(task_list)} tasks in database")
        print(f"DEBUG: Task IDs in database: {[str(t) for t in task_list]}")
        print(f"DEBUG: Trying to map simple IDs: {simple_task_ids}")
        
        mapped_ids = []
        
        for simple_id in simple_task_ids:
            try:
                # Convert simple ID to 0-based index
                index = int(simple_id) - 1
                if 0 <= index < len(task_list):
                    mapped_ids.append(str(task_list[index]))
                    print(f"DEBUG: Mapped {simple_id} -> {task_list[index]}")
                else:
                    print(f"Warning: Task ID {simple_id} out of range for EO {eo_id} (max: {len(task_list)})")
            except ValueError:
                print(f"Warning: Invalid task ID format: {simple_id}")
                continue
        
        print(f"DEBUG: Final mapped IDs: {mapped_ids}")
        return mapped_ids


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

def get_tasks_by_ids(task_ids: list[str | uuid.UUID]) -> list[Task]:
    """Get tasks by their IDs."""
    if not task_ids:
        return []
    uuids: list[uuid.UUID] = []
    for tid in task_ids:
        try:
            uuids.append(uuid.UUID(str(tid)))
        except Exception:
            continue
    if not uuids:
        return []
    with SessionLocal() as db:
        tasks = db.execute(select(Task).where(Task.id.in_(uuids))).scalars().all()
        return list(tasks)

def update_tasks_with_improved_data(task_updates: dict[str, dict]) -> int:
    """
    Update tasks in database with improved data from LLM rewiring.
    
    Parameters
    ----------
    task_updates : dict[str, dict]
        Mapping of task ID (string) to improved task data dict
        
    Returns
    -------
    int
        Number of tasks successfully updated
    """
    if not task_updates:
        return 0
        
    updated_count = 0
    with SessionLocal() as db:
        for task_id_str, improved_data in task_updates.items():
            try:
                task_uuid = uuid.UUID(task_id_str)
                db_task = db.get(Task, task_uuid)
                
                if db_task:
                    # Update task fields with improved data
                    db_task.title = improved_data.get("title", db_task.title)
                    db_task.description = improved_data.get("description", db_task.description)
                    db_task.category = improved_data.get("category_dept", db_task.category)
                    db_task.status = "Pending PMO approval"  # Reset to pending for re-review
                    db_task.remarks = improved_data.get("remarks", db_task.remarks)
                    db_task.updated_at = datetime.now(timezone.utc)
                    updated_count += 1
                    
            except (ValueError, TypeError) as e:
                print(f"Error updating task {task_id_str}: {e}")
                continue
        
        db.commit()
    
    return updated_count