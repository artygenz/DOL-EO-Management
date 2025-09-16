from __future__ import annotations

"""Task-related chat queries (read-only)."""

from typing import Any, Dict, Optional, Sequence, List
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, DateTime, and_, exists

from src.models.user import User
from src.models.task import Task
from src.models.task_update import TaskUpdate
from src.db.chat.visibility import ChatVisibility
from src.db.chat.filters import TaskFilters


def get_my_tasks(db: Session, current_user: User, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Paginated list of tasks within user's visibility (admin/reviewer/executor)."""
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    if status:
        q = q.filter(Task.status == status)
    total = q.count()
    rows: Sequence[Task] = q.order_by(Task.due_date.nulls_last()).offset(offset).limit(limit).all()
    return {
        "total": total,
        **({"rbac_blocked": True} if total == 0 else {}),
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
            }
            for t in rows
        ],
    }


def search_tasks(db: Session, current_user: User, filters: TaskFilters, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Flexible task search with safe filters (status, category ilike, due ranges)."""
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    if filters.status:
        q = q.filter(Task.status == filters.status)
    if filters.category:
        q = q.filter(Task.category.ilike(f"%{filters.category}%"))
    if filters.due_before:
        q = q.filter(Task.due_date != None, Task.due_date < filters.due_before)  # noqa: E711
    if filters.due_after:
        q = q.filter(Task.due_date != None, Task.due_date > filters.due_after)  # noqa: E711
    total = q.count()
    rows: Sequence[Task] = q.order_by(Task.due_date.nulls_last()).offset(offset).limit(limit).all()
    return {
        "total": total,
        **({"rbac_blocked": True} if total == 0 else {}),
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
            }
            for t in rows
        ],
    }


def search_tasks_by_assignee_name(db: Session, current_user: User, assignee_name: str, filters: TaskFilters, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Search tasks by assignee name with additional filters.
    
    This function will:
    1. Find users matching the assignee_name (case-insensitive partial match)
    2. Search for tasks assigned to those users
    3. Apply role-based visibility restrictions
    4. Apply additional filters (status, category, due dates)
    
    Returns tasks with RBAC context if the user cannot see the requested assignee's tasks.
    """
    # First, find users matching the assignee name
    matching_users = db.query(User).filter(
        User.name.ilike(f"%{assignee_name}%")
    ).all()
    
    if not matching_users:
        # No users found with that name
        return {
            "total": 0,
            "rbac_blocked": True,
            "rbac_reason": f"No user found with name containing '{assignee_name}'",
            "tasks": []
        }
    
    # Get user IDs for the query
    user_ids = [user.id for user in matching_users]
    
    # Build the base query with assignee filter
    q = db.query(Task).filter(Task.assignee_id.in_(user_ids))
    
    # Apply role-based visibility
    q = ChatVisibility.apply_task_visibility(q, current_user)
    
    # Apply additional filters
    if filters.status:
        q = q.filter(Task.status == filters.status)
    if filters.category:
        q = q.filter(Task.category.ilike(f"%{filters.category}%"))
    if filters.due_before:
        q = q.filter(Task.due_date != None, Task.due_date < filters.due_before)  # noqa: E711
    if filters.due_after:
        q = q.filter(Task.due_date != None, Task.due_date > filters.due_after)  # noqa: E711
    
    total = q.count()
    
    # Get results
    rows: Sequence[Task] = q.order_by(Task.due_date.nulls_last()).offset(offset).limit(limit).all()
    
    # Determine RBAC context
    rbac_blocked = False
    rbac_reason = None
    
    if total == 0:
        # Check if this is due to RBAC restrictions
        # Count tasks for these users without visibility restrictions
        unrestricted_count = db.query(Task).filter(Task.assignee_id.in_(user_ids)).count()
        if unrestricted_count > 0:
            rbac_blocked = True
            rbac_reason = f"Tasks for '{assignee_name}' exist but are not visible due to role-based access controls"
        else:
            rbac_reason = f"No tasks found for user(s) matching '{assignee_name}'"
    elif len(matching_users) > 1:
        # Multiple users found - this might be a partial match scenario
        rbac_reason = f"Found tasks for {len(matching_users)} users matching '{assignee_name}'"
    
    result = {
        "total": total,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
                "assignee_id": str(t.assignee_id) if t.assignee_id else None,
                "assignee_name": t.assignee.name if t.assignee else None,
            }
            for t in rows
        ],
    }
    
    if rbac_blocked:
        result["rbac_blocked"] = True
    if rbac_reason:
        result["rbac_reason"] = rbac_reason
        
    return result


# ----------------------------- Additional list/search helpers -----------------------------

def get_tasks_by_eo(db: Session, current_user: User, eo_id: str, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    List tasks for a specific Executive Order within the caller's visibility.

    Role behavior
    - Admin: all tasks for the EO
    - Reviewer: only if the EO is assigned to the PMO (via visibility)
    - Executor: only their own tasks on that EO

    Parameters
    - eo_id: EO UUID to scope tasks
    - status: optional status filter
    - limit/offset: pagination
    """
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    q = q.filter(Task.eo_id == eo_id)
    if status:
        q = q.filter(Task.status == status)
    total = q.count()
    rows: Sequence[Task] = q.order_by(Task.due_date.nulls_last()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
            }
            for t in rows
        ],
    }


def get_unassigned_tasks(db: Session, current_user: User, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    List unassigned tasks (assignee_id is NULL) within caller's visibility.
    Useful for PMOs/Admins to triage.
    """
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    q = q.filter(Task.assignee_id == None)  # noqa: E711
    if status:
        q = q.filter(Task.status == status)
    total = q.count()
    rows: Sequence[Task] = q.order_by(Task.due_date.nulls_last()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
            }
            for t in rows
        ],
    }


def get_tasks_by_assignee(db: Session, current_user: User, assignee_id: str, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    List tasks for a given assignee.
    Visibility still applies; PMOs see only tasks from their EOs.
    Admin can see any.
    """
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    q = q.filter(Task.assignee_id == assignee_id)
    if status:
        q = q.filter(Task.status == status)
    total = q.count()
    rows: Sequence[Task] = q.order_by(Task.due_date.nulls_last()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
            }
            for t in rows
        ],
    }


def get_tasks_due_this_week(db: Session, current_user: User, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Convenience: tasks with due_date in the next 7 days (inclusive)."""
    today = date.today()
    return list_tasks_due_between(db, current_user, start=today, end=today + timedelta(days=7), limit=limit, offset=offset)


def list_tasks_due_between(db: Session, current_user: User, start: date, end: date, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    List tasks whose due_date falls in [start, end], respecting visibility.
    Dates are interpreted in server timezone; inclusive boundaries.
    """
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    q = q.filter(Task.due_date != None, Task.due_date >= start, Task.due_date <= end)  # noqa: E711
    total = q.count()
    rows: Sequence[Task] = q.order_by(Task.due_date).offset(offset).limit(limit).all()
    return {
        "total": total,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
            }
            for t in rows
        ],
    }


def get_overdue_tasks(db: Session, current_user: User, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Tasks with due_date < today and status not in {completed, rejected}.
    Results are role-scoped.
    """
    today = date.today()
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    q = q.filter(Task.due_date != None, Task.due_date < today)  # noqa: E711
    q = q.filter(Task.status.notin_(["completed", "rejected"]))
    total = q.count()
    rows: Sequence[Task] = q.order_by(Task.due_date).offset(offset).limit(limit).all()
    return {
        "total": total,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
            }
            for t in rows
        ],
    }


def get_upcoming_tasks(db: Session, current_user: User, days: int = 14, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Tasks due within the next 'days' days (default 14)."""
    today = date.today()
    return list_tasks_due_between(db, current_user, start=today, end=today + timedelta(days=days), limit=limit, offset=offset)


def get_recently_completed_tasks(db: Session, current_user: User, days: int = 7, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Tasks with status=completed and updated_at within the last 'days'.
    Note: relies on Task.updated_at; if completion timestamp is tracked elsewhere,
    switch to that source.
    """
    cutoff = date.today() - timedelta(days=days)
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    q = q.filter(Task.status == "completed")
    q = q.filter(Task.updated_at >= cast(cutoff, DateTime))
    total = q.count()
    rows: Sequence[Task] = q.order_by(Task.updated_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
            }
            for t in rows
        ],
    }


# ----------------------------- Aggregates -----------------------------

def aggregate_tasks_by_status(db: Session, current_user: User, eo_id: Optional[str] = None) -> Dict[str, int]:
    """Counts of tasks grouped by status, optionally scoped to an EO."""
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    if eo_id:
        q = q.filter(Task.eo_id == eo_id)
    rows = q.with_entities(Task.status, func.count()).group_by(Task.status).all()
    return {status: count for status, count in rows}


def aggregate_tasks_by_category(db: Session, current_user: User, eo_id: Optional[str] = None) -> Dict[str, int]:
    """Counts of tasks grouped by category, optionally scoped to an EO."""
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    if eo_id:
        q = q.filter(Task.eo_id == eo_id)
    rows = q.with_entities(Task.category, func.count()).group_by(Task.category).all()
    return {str(category): count for category, count in rows}


def total_tasks(db: Session, current_user: User, eo_id: Optional[str] = None) -> int:
    """Total number of visible tasks, optionally scoped to an EO."""
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    if eo_id:
        q = q.filter(Task.eo_id == eo_id)
    return q.count()


# ----------------------------- Timeseries -----------------------------

def timeseries_tasks_due(db: Session, current_user: User, bucket: str = "day", date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[Dict[str, Any]]:
    """
    Time-bucketed counts of tasks by due_date.
    - bucket: 'day' or 'week' (default day)
    - date_from/date_to: optional bounds on due_date
    """
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    if date_from:
        q = q.filter(Task.due_date != None, Task.due_date >= date_from)  # noqa: E711
    if date_to:
        q = q.filter(Task.due_date != None, Task.due_date <= date_to)  # noqa: E711
    if bucket == "week":
        bucket_col = func.date_trunc("week", cast(Task.due_date, DateTime))
    else:
        bucket_col = Task.due_date
    rows = q.with_entities(bucket_col.label("bucket"), func.count().label("count")).group_by(bucket_col).order_by(bucket_col).all()
    return [{"bucket": (b.isoformat() if hasattr(b, "isoformat") else str(b)), "count": c} for b, c in rows]


def timeseries_tasks_completed(db: Session, current_user: User, bucket: str = "day", date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[Dict[str, Any]]:
    """
    Time-bucketed counts of tasks marked completed using Task.updated_at.
    - bucket: 'day' or 'week'
    - date_from/date_to: optional bounds on updated_at
    """
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    q = q.filter(Task.status == "completed")
    if date_from:
        q = q.filter(Task.updated_at >= cast(date_from, DateTime))
    if date_to:
        q = q.filter(Task.updated_at <= cast(date_to, DateTime))
    bucket_col = func.date_trunc("week" if bucket == "week" else "day", Task.updated_at)
    rows = q.with_entities(bucket_col.label("bucket"), func.count().label("count")).group_by(bucket_col).order_by(bucket_col).all()
    return [{"bucket": b.isoformat(), "count": c} for b, c in rows]


# ----------------------------- Cross-entity (updates) -----------------------------

def list_tasks_with_update_flags(
    db: Session,
    current_user: User,
    has_blockers: Optional[bool] = None,
    has_risks: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List tasks that have at least one TaskUpdate matching the specified flags.

    Filters
    - has_blockers / has_risks: True (must have), False (must not), None (ignore)
    - date_from/date_to: constrain the TaskUpdate.date window
    """
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)

    # Build an EXISTS subquery on TaskUpdate
    upd = db.query(TaskUpdate.id).filter(TaskUpdate.task_id == Task.id)
    if has_blockers is True:
        upd = upd.filter(TaskUpdate.blockers != None)  # noqa: E711
    if has_blockers is False:
        upd = upd.filter(TaskUpdate.blockers == None)  # noqa: E711
    if has_risks is True:
        upd = upd.filter(TaskUpdate.risks != None)  # noqa: E711
    if has_risks is False:
        upd = upd.filter(TaskUpdate.risks == None)  # noqa: E711
    if date_from:
        upd = upd.filter(TaskUpdate.date >= date_from)
    if date_to:
        upd = upd.filter(TaskUpdate.date <= date_to)

    q = q.filter(exists(upd))
    total = q.count()
    rows: Sequence[Task] = q.order_by(Task.due_date.nulls_last()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
            }
            for t in rows
        ],
    }


# ----------------------------- Details -----------------------------

def get_task_details(db: Session, current_user: User, task_id: str) -> Dict[str, Any]:
    """Return a single task row if visible; otherwise an error marker."""
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    q = q.filter(Task.id == task_id)
    task = q.first()
    if not task:
        return {"error": "Not found or not visible"}
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "eo_id": str(task.eo_id),
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "category": task.category,
        "assignee_id": str(task.assignee_id) if task.assignee_id else None,
        "updated_at": task.updated_at.isoformat() if getattr(task, "updated_at", None) else None,
    }


def get_nearest_due_task(db: Session, current_user: User, limit: int = 1) -> Dict[str, Any]:
    """
    Return the nearest upcoming tasks by due_date within user's visibility.
    Tasks without due_date are excluded; ordered ascending by due_date.
    """
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    q = q.filter(Task.due_date != None)  # noqa: E711
    rows: Sequence[Task] = q.order_by(Task.due_date.asc()).limit(limit).all()
    return {
        "total": len(rows),
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "eo_id": str(t.eo_id),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "category": t.category,
            }
            for t in rows
        ],
    }

