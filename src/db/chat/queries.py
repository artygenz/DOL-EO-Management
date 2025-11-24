from __future__ import annotations

"""
Chat read-only queries with role-scoped visibility.

LLD principles:
- SRP: This module only contains read-only query use-cases for chat.
- DIP: Depends on abstractions (Session-like), not concrete routers.
- ISP: Small, focused functions per use-case.
"""

from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.chat.visibility import ChatVisibility
from src.db.chat.filters import TaskFilters, TaskUpdateFilters
from src.models.user import User
from src.models.task import Task
from src.models.executive_order import ExecutiveOrder
from src.models.task_update import TaskUpdate


def get_my_tasks(db: Session, current_user: User, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Return a paginated list of tasks visible to the current user.

    Role behavior
    - Admin: all tasks.
    - Reviewer (PMO): tasks for EOs assigned to this PMO via `eo_pmo_assignments`.
    - Executor: only tasks where `Task.assignee_id == current_user.id`.

    Parameters
    - status: optional task status filter.
    - limit/offset: pagination controls.

    Response shape
    {
      "total": int,
      "tasks": [
        {"id": str, "title": str, "status": str, "eo_id": str, "due_date": iso|None, "category": str|None},
        ...
      ]
    }
    """
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
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


def search_tasks(db: Session, current_user: User, filters: TaskFilters, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Flexible task search with safe filters.

    Filters
    - status, category
    - due_before, due_after
    Response same as get_my_tasks.
    """
    q = db.query(Task)
    q = ChatVisibility.apply_task_visibility(q, current_user)
    if filters.status:
        q = q.filter(Task.status == filters.status)
    if filters.category:
        # Case-insensitive substring match for category (more forgiving than exact match)
        q = q.filter(Task.category.ilike(f"%{filters.category}%"))
    if filters.due_before:
        q = q.filter(Task.due_date != None, Task.due_date < filters.due_before)  # noqa: E711
    if filters.due_after:
        q = q.filter(Task.due_date != None, Task.due_date > filters.due_after)  # noqa: E711
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


def get_eo_details(db: Session, current_user: User, eo_id: str) -> Dict[str, Any]:
    """
    Return EO details if visible to the user; otherwise an error marker.

    Role behavior
    - Admin: can see any EO.
    - Reviewer: can see EOs assigned to them via `eo_pmo_assignments`.
    - Executor: can see EOs only through their assigned tasks (indirect visibility).

    Response shape
    {"id": str, "title": str, "status": str, "received_at": iso|None}
    or {"error": "Not found or not visible"}
    """
    q = db.query(ExecutiveOrder).filter(ExecutiveOrder.id == eo_id)
    q = ChatVisibility.apply_eo_visibility(q, current_user)
    eo = q.first()
    if not eo:
        return {"error": "Not found or not visible"}
    return {
        "id": str(eo.id),
        "title": eo.title,
        "status": eo.status,
        "received_at": eo.received_at.isoformat() if getattr(eo, "received_at", None) else None,
    }


def get_task_updates(db: Session, current_user: User, eo_id: Optional[str] = None, task_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Return task updates scoped to the user's visibility.

    Role behavior
    - Admin: unrestricted.
    - Reviewer: updates for tasks on EOs assigned to them.
    - Executor: updates for their own tasks only.

    Selection precedence
    - If task_id is provided: require visibility to that task.
    - Else if eo_id is provided: require visibility to that EO.
    - Else: restrict by visible task ids for the user.

    Response shape
    {
      "total": int,
      "updates": [
        {"id": str, "task_id": str, "eo_id": str, "user_id": str, "date": iso, "status": str|None,
         "progress_pct": int|None, "notes": str, "spent_hours": float|None}, ...
      ]
    }
    """
    q = db.query(TaskUpdate)
    # Restrict via Task visibility when filtering by task, else via EO visibility if eo_id provided, else via Task join for general visibility
    if task_id:
        # Ensure the task itself is visible
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if task_id not in {str(tid) for tid in visible_task_ids}:
            return {"total": 0, "updates": []}
        q = q.filter(TaskUpdate.task_id == task_id)
    elif eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return {"total": 0, "updates": []}
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        # Generic: restrict via tasks visible to the user
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return {"total": 0, "updates": []}
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))

    total = q.count()
    rows: Sequence[TaskUpdate] = q.order_by(TaskUpdate.date.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "updates": [
            {
                "id": str(u.id),
                "task_id": str(u.task_id),
                "eo_id": str(u.eo_id),
                "user_id": str(u.user_id),
                "date": u.date.isoformat(),
                "status": u.status,
                "progress_pct": u.progress_pct,
                "notes": u.notes or "",
                "spent_hours": float(u.spent_hours) if u.spent_hours is not None else None,
            }
            for u in rows
        ],
    }


def search_task_updates(db: Session, current_user: User, filters: TaskUpdateFilters, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Flexible task update search for role-visible data.

    Typical reviewer query: updates with blockers/risks between dates for my EOs.
    Filters
    - eo_id | task_id (optional scoping)
    - status
    - min_progress
    - has_blockers, has_risks
    - date_from, date_to
    Response same shape as get_task_updates.
    """
    q = db.query(TaskUpdate)

    # Scope by task/EO visibility
    if filters.task_id:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = {str(r[0]) for r in tq.all()}
        if filters.task_id not in visible_task_ids:
            return {"total": 0, "updates": []}
        q = q.filter(TaskUpdate.task_id == filters.task_id)
    elif filters.eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == filters.eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return {"total": 0, "updates": []}
        q = q.filter(TaskUpdate.eo_id == filters.eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return {"total": 0, "updates": []}
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))

    # Attribute filters
    if filters.status:
        q = q.filter(TaskUpdate.status == filters.status)
    if filters.min_progress is not None:
        q = q.filter(TaskUpdate.progress_pct != None, TaskUpdate.progress_pct >= filters.min_progress)  # noqa: E711
    if filters.has_blockers is True:
        q = q.filter(TaskUpdate.blockers != None)  # noqa: E711
    if filters.has_blockers is False:
        q = q.filter(TaskUpdate.blockers == None)  # noqa: E711
    if filters.has_risks is True:
        q = q.filter(TaskUpdate.risks != None)  # noqa: E711
    if filters.has_risks is False:
        q = q.filter(TaskUpdate.risks == None)  # noqa: E711
    if filters.date_from:
        q = q.filter(TaskUpdate.date >= filters.date_from)
    if filters.date_to:
        q = q.filter(TaskUpdate.date <= filters.date_to)

    total = q.count()
    rows: Sequence[TaskUpdate] = q.order_by(TaskUpdate.date.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "updates": [
            {
                "id": str(u.id),
                "task_id": str(u.task_id),
                "eo_id": str(u.eo_id),
                "user_id": str(u.user_id),
                "date": u.date.isoformat(),
                "status": u.status,
                "progress_pct": u.progress_pct,
                "notes": u.notes or "",
                "spent_hours": float(u.spent_hours) if u.spent_hours is not None else None,
            }
            for u in rows
        ],
    }


def get_cfo_overview(db: Session, current_user: User) -> Dict[str, Any]:
    """
    Portfolio-level aggregates for the currently logged-in user.

    Role behavior
    - Admin: global totals and breakdowns.
    - Reviewer: totals limited to EOs assigned to them and their tasks.
    - Executor: totals limited to their own tasks and the EOs implied by those tasks.

    Response shape
    {
      "executive_orders": {"total": int},
      "tasks": {"total": int, "by_status": {status: count}}
    }
    """
    # Even though admin is unrestricted, keep symmetry by applying EO visibility (no-op for admin)
    q = db.query(ExecutiveOrder)
    q = ChatVisibility.apply_eo_visibility(q, current_user)
    total_eos = q.count()

    tq = db.query(Task)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    total_tasks = tq.count()

    by_status = (
        tq.with_entities(Task.status, func.count())
        .group_by(Task.status)
        .all()
    )

    return {
        "executive_orders": {"total": total_eos},
        "tasks": {
            "total": total_tasks,
            "by_status": {status: count for status, count in by_status},
        },
    }


