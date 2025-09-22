# src/workflow/repository.py
import uuid
from sqlalchemy.inspection import inspect
from sqlalchemy import select, update
from datetime import datetime, timezone, date
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
    if status not in {"processed", "pending", "received"}:
        status = "pending"  # Default to pending instead of error
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

def get_task_ids_by_eo_and_status(eo_id: str | uuid.UUID, status: str) -> list[str]:
    """
    Get task IDs for an EO that have a specific status.
    This is used when sending improved tasks to PMO - we only send rejected tasks that have been improved.
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
                Task.status == status
            ).order_by(Task.created_at)
        ).scalars().all()
        
        task_ids = [str(task_id) for task_id in tasks]
        print(f"Found {len(task_ids)} {status} tasks for EO {eo_id}: {task_ids}")
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
        # Mapping simple task IDs to UUIDs
        
        mapped_ids = []
        
        for simple_id in simple_task_ids:
            try:
                # Convert simple ID to 0-based index
                index = int(simple_id) - 1
                if 0 <= index < len(task_list):
                    mapped_ids.append(str(task_list[index]))
                    # Mapped simple ID to UUID
                else:
                    print(f"Warning: Task ID {simple_id} out of range for EO {eo_id} (max: {len(task_list)})")
            except ValueError:
                print(f"Warning: Invalid task ID format: {simple_id}")
                continue
        
        # Final mapped IDs
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
                    
                    # Handle assignee updates from LLM rewiring
                    if "assignee" in improved_data and improved_data["assignee"]:
                        assignee_name = improved_data["assignee"]
                        assignee_id = resolve_assignee_name_to_id(assignee_name)
                        if assignee_id:
                            db_task.assignee_id = assignee_id
                        else:
                            print(f"[WARNING] Could not resolve assignee '{assignee_name}' for task {task_id_str}")
                    
                    db_task.updated_at = datetime.now(timezone.utc)
                    updated_count += 1
                    
            except (ValueError, TypeError) as e:
                print(f"Error updating task {task_id_str}: {e}")
                continue
        
        db.commit()
    
    return updated_count

# Task Updates Repository Functions
def get_user_active_tasks(user_id: str | uuid.UUID) -> list[dict]:
    """Get all active tasks assigned to a user."""
    try:
        user_uuid = uuid.UUID(str(user_id))
    except Exception:
        return []
    
    with SessionLocal() as db:
        tasks = db.execute(
            select(Task)
            .where(Task.assignee_id == user_uuid)
        ).scalars().all()
        
        return [
            {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "eo_id": str(task.eo_id),
                "status": task.status
            }
            for task in tasks
        ]

def resolve_user_by_email(email: str) -> str | None:
    """Resolve user ID by email address."""
    with SessionLocal() as db:
        from src.models.user import User
        from sqlalchemy import func
        
        # Case-insensitive email lookup
        user = db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        ).scalar_one_or_none()
        
        return str(user.id) if user else None

def save_task_updates(updates: list[dict]) -> int:
    """Save multiple task updates to database with proper deduplication."""
    if not updates:
        return 0
    
    saved_count = 0
    replaced_count = 0
    with SessionLocal() as db:
        from src.models.task_update import TaskUpdate
        from datetime import date
        
        for update_data in updates:
            try:
                # Convert date string to date object if needed
                update_date = update_data['date']
                if isinstance(update_date, str):
                    update_date = date.fromisoformat(update_date)
                
                # Convert ETA string to date object if needed
                eta = update_data.get('eta')
                if eta and isinstance(eta, str):
                    eta = date.fromisoformat(eta)
                
                # Check for existing updates for the same task, user, and date
                existing_updates = db.execute(
                    select(TaskUpdate)
                    .where(TaskUpdate.task_id == uuid.UUID(update_data['task_id']))
                    .where(TaskUpdate.user_id == uuid.UUID(update_data['user_id']))
                    .where(TaskUpdate.date == update_date)
                ).scalars().all()
                
                if existing_updates:
                    # Delete all existing records for this task, user, and date
                    for existing_update in existing_updates:
                        db.delete(existing_update)
                    
                    replaced_count += len(existing_updates)
                
                # Always create a new task update (either replacing old ones or creating first one)
                # Create new task update
                task_update = TaskUpdate(
                    eo_id=uuid.UUID(update_data['eo_id']),
                    task_id=uuid.UUID(update_data['task_id']),
                    user_id=uuid.UUID(update_data['user_id']),
                    date=update_date,
                    progress_pct=update_data.get('progress_pct'),
                    status=update_data.get('status'),
                    notes=update_data.get('notes'),
                    blockers=update_data.get('blockers'),
                    risks=update_data.get('risks'),
                    eta=eta,
                    spent_hours=update_data.get('spent_hours'),
                    source_email_message_id=update_data.get('source_email_message_id'),
                    dedupe_hash=update_data.get('dedupe_hash'),
                    is_late=update_data.get('is_late', False),
                    ai_summary=update_data.get('ai_summary')
                )
                
                db.add(task_update)
                saved_count += 1
                
            except Exception as e:
                print(f"Error saving task update: {e}")
                continue
        
        db.commit()
    
    return saved_count + replaced_count

def get_task_updates_for_eo_date(eo_id: str | uuid.UUID, target_date: date) -> list[dict]:
    """Get all task updates for a specific EO and date."""
    try:
        eo_uuid = uuid.UUID(str(eo_id))
    except Exception:
        return []
    
    with SessionLocal() as db:
        from src.models.task_update import TaskUpdate
        from src.models.task import Task
        from src.models.user import User
        
        updates = db.execute(
            select(TaskUpdate, Task.title.label('task_title'), User.name.label('user_name'))
            .join(Task, TaskUpdate.task_id == Task.id)
            .join(User, TaskUpdate.user_id == User.id)
            .where(TaskUpdate.eo_id == eo_uuid)
            .where(TaskUpdate.date == target_date)
        ).all()
        
        return [
            {
                "id": str(update.TaskUpdate.id),
                "task_id": str(update.TaskUpdate.task_id),
                "task_title": update.task_title,
                "user_id": str(update.TaskUpdate.user_id),
                "user_name": update.user_name,
                "progress_pct": update.TaskUpdate.progress_pct,
                "status": update.TaskUpdate.status,
                "notes": update.TaskUpdate.notes,
                "blockers": update.TaskUpdate.blockers,
                "risks": update.TaskUpdate.risks,
                "eta": update.TaskUpdate.eta,
                "spent_hours": update.TaskUpdate.spent_hours,
                "is_late": update.TaskUpdate.is_late,
                "ai_summary": update.TaskUpdate.ai_summary
            }
            for update in updates
        ]

def get_expected_updates_for_eo_date(eo_id: str | uuid.UUID, target_date: date) -> list[dict]:
    """Get list of users who should provide updates for an EO on a given date."""
    try:
        eo_uuid = uuid.UUID(str(eo_id))
    except Exception:
        return []
    
    with SessionLocal() as db:
        from src.models.task import Task
        from src.models.user import User
        
        # Get all active tasks for this EO with assignees
        tasks = db.execute(
            select(Task, User.email.label('user_email'), User.name.label('user_name'))
            .join(User, Task.assignee_id == User.id)
            .where(Task.eo_id == eo_uuid)
            .where(Task.status.in_(["pending", "in_progress", "Pending PMO approval"]))
        ).all()
        
        # Group by user
        user_tasks = {}
        for task in tasks:
            user_email = task.user_email
            if user_email not in user_tasks:
                user_tasks[user_email] = {
                    "user_email": user_email,
                    "user_name": task.user_name,
                    "task_count": 0,
                    "tasks": []
                }
            user_tasks[user_email]["task_count"] += 1
            user_tasks[user_email]["tasks"].append({
                "id": str(task.Task.id),
                "title": task.Task.title
            })
        
        return list(user_tasks.values())

def save_daily_eo_summary(summary_data: dict) -> str:
    """Save a daily EO summary to database."""
    with SessionLocal() as db:
        from src.models.daily_eo_summary import DailyEOSummary
        from datetime import date
        
        # Convert date string to date object if needed
        summary_date = summary_data['date']
        if isinstance(summary_date, str):
            summary_date = date.fromisoformat(summary_date)
        
        summary = DailyEOSummary(
            eo_id=uuid.UUID(summary_data['eo_id']),
            date=summary_date,
            progress_summary=summary_data.get('progress_summary'),
            key_blockers=summary_data.get('key_blockers'),
            risks=summary_data.get('risks'),
            attention_items=summary_data.get('attention_items'),
            missing_updates=summary_data.get('missing_updates'),
            total_tasks=summary_data.get('total_tasks', 0),
            updated_tasks=summary_data.get('updated_tasks', 0)
        )
        
        db.add(summary)
        db.commit()
        db.refresh(summary)
        
        return str(summary.id)

def get_daily_eo_summary(eo_id: str | uuid.UUID, target_date: date) -> dict | None:
    """Get daily EO summary for a specific date."""
    try:
        eo_uuid = uuid.UUID(str(eo_id))
    except Exception:
        return None
    
    with SessionLocal() as db:
        from src.models.daily_eo_summary import DailyEOSummary
        
        summary = db.execute(
            select(DailyEOSummary)
            .where(DailyEOSummary.eo_id == eo_uuid)
            .where(DailyEOSummary.date == target_date)
        ).scalar_one_or_none()
        
        if summary:
            return {
                "id": str(summary.id),
                "eo_id": str(summary.eo_id),
                "date": summary.date,
                "progress_summary": summary.progress_summary,
                "key_blockers": summary.key_blockers,
                "risks": summary.risks,
                "attention_items": summary.attention_items,
                "missing_updates": summary.missing_updates,
                "total_tasks": summary.total_tasks,
                "updated_tasks": summary.updated_tasks,
                "summary_email_sent": summary.summary_email_sent,
                "summary_email_sent_at": summary.summary_email_sent_at
            }
        
        return None

def get_daily_eo_summary_by_id(summary_id: str | uuid.UUID) -> dict | None:
    """Get daily EO summary by its ID."""
    try:
        summary_uuid = uuid.UUID(str(summary_id))
    except Exception:
        return None
    
    with SessionLocal() as db:
        from src.models.daily_eo_summary import DailyEOSummary
        
        summary = db.get(DailyEOSummary, summary_uuid)
        
        if summary:
            return {
                "id": str(summary.id),
                "eo_id": str(summary.eo_id),
                "date": summary.date,
                "progress_summary": summary.progress_summary,
                "key_blockers": summary.key_blockers,
                "risks": summary.risks,
                "attention_items": summary.attention_items,
                "missing_updates": summary.missing_updates,
                "total_tasks": summary.total_tasks,
                "updated_tasks": summary.updated_tasks,
                "summary_email_sent": summary.summary_email_sent,
                "summary_email_sent_at": summary.summary_email_sent_at
            }
        
        return None

def mark_summary_email_sent(summary_id: str | uuid.UUID) -> bool:
    """Mark a daily summary as having been emailed."""
    try:
        summary_uuid = uuid.UUID(str(summary_id))
    except Exception:
        return False
    
    with SessionLocal() as db:
        from src.models.daily_eo_summary import DailyEOSummary
        
        summary = db.get(DailyEOSummary, summary_uuid)
        if summary:
            summary.summary_email_sent = True
            summary.summary_email_sent_at = datetime.now(timezone.utc)
            db.commit()
            return True
        
        return False