from __future__ import annotations

"""Task update chat queries (read-only)."""

from typing import Any, Dict, Optional, Sequence, List, Tuple
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, DateTime, exists, and_

from src.models.user import User
from src.models.task import Task
from src.models.task_update import TaskUpdate
from src.models.executive_order import ExecutiveOrder
from src.db.chat.visibility import ChatVisibility
from src.db.chat.filters import TaskUpdateFilters


def get_task_updates(db: Session, current_user: User, eo_id: str | None = None, task_id: str | None = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Task updates within user's visibility; can scope by eo_id or task_id."""
    q = db.query(TaskUpdate)
    if task_id:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = {str(r[0]) for r in tq.all()}
        if task_id not in visible_task_ids:
            return {"total": 0, "updates": [], "rbac_blocked": True}
        q = q.filter(TaskUpdate.task_id == task_id)
    elif eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return {"total": 0, "updates": [], "rbac_blocked": True}
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return {"total": 0, "updates": [], "rbac_blocked": True}
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
    """Flexible task update search (status, min_progress, blockers/risks, dates)."""
    q = db.query(TaskUpdate)

    if filters.task_id:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = {str(r[0]) for r in tq.all()}
        if filters.task_id not in visible_task_ids:
            return {"total": 0, "updates": [], "rbac_blocked": True}
        q = q.filter(TaskUpdate.task_id == filters.task_id)
    elif filters.eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == filters.eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return {"total": 0, "updates": [], "rbac_blocked": True}
        q = q.filter(TaskUpdate.eo_id == filters.eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return {"total": 0, "updates": [], "rbac_blocked": True}
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))

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


# ----------------------------- Additional list/search helpers -----------------------------

def latest_updates_per_task(db: Session, current_user: User, eo_id: str | None = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Return the most recent update per visible task (optionally for a single EO)."""
    # Visible task ids
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    if eo_id:
        tq = tq.filter(Task.eo_id == eo_id)
    visible_task_ids = [r[0] for r in tq.all()]
    if not visible_task_ids:
        return {"total": 0, "updates": []}

    # Subquery: latest date per task
    sub = (
        db.query(TaskUpdate.task_id, func.max(TaskUpdate.date).label("max_date"))
        .filter(TaskUpdate.task_id.in_(visible_task_ids))
        .group_by(TaskUpdate.task_id)
        .subquery()
    )

    q = (
        db.query(TaskUpdate)
        .join(sub, and_(TaskUpdate.task_id == sub.c.task_id, TaskUpdate.date == sub.c.max_date))
        .order_by(TaskUpdate.date.desc())
    )
    total = q.count()
    rows: Sequence[TaskUpdate] = q.offset(offset).limit(limit).all()
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
            }
            for u in rows
        ],
    }


def updates_in_last_days(db: Session, current_user: User, days: int = 7, eo_id: str | None = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Updates within the last N days (default 7), optionally scoped to one EO."""
    cutoff = date.today() - timedelta(days=days)
    q = db.query(TaskUpdate)
    if eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return {"total": 0, "updates": []}
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return {"total": 0, "updates": []}
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    q = q.filter(TaskUpdate.date >= cutoff)
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
            }
            for u in rows
        ],
    }


def updates_for_overdue_tasks(db: Session, current_user: User, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Updates for tasks that are currently overdue within the user's visibility."""
    today = date.today()
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    tq = tq.filter(Task.due_date != None, Task.due_date < today)  # noqa: E711
    tq = tq.filter(Task.status.notin_(["completed", "rejected"]))
    task_ids = [r[0] for r in tq.all()]
    if not task_ids:
        return {"total": 0, "updates": []}
    q = db.query(TaskUpdate).filter(TaskUpdate.task_id.in_(task_ids))
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
            }
            for u in rows
        ],
    }


def search_updates_notes(db: Session, current_user: User, term: str, eo_id: str | None = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Search updates by substring in notes (case-insensitive), respecting visibility."""
    q = db.query(TaskUpdate)
    if eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return {"total": 0, "updates": []}
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return {"total": 0, "updates": []}
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    q = q.filter(TaskUpdate.notes.ilike(f"%{term}%"))
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
            }
            for u in rows
        ],
    }


# ----------------------------- Detail -----------------------------

def get_update_by_id(db: Session, current_user: User, update_id: str) -> Dict[str, Any]:
    """Return a single TaskUpdate if the underlying task is visible to the user."""
    upd = db.query(TaskUpdate).filter(TaskUpdate.id == update_id).first()
    if not upd:
        return {"error": "Not found"}
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    tq = tq.filter(Task.id == upd.task_id)
    if not tq.first():
        return {"error": "Not found or not visible"}
    return {
        "id": str(upd.id),
        "task_id": str(upd.task_id),
        "eo_id": str(upd.eo_id),
        "user_id": str(upd.user_id),
        "date": upd.date.isoformat(),
        "status": upd.status,
        "progress_pct": upd.progress_pct,
        "notes": upd.notes or "",
        "spent_hours": float(upd.spent_hours) if upd.spent_hours is not None else None,
    }


def get_task_update_history(db: Session, current_user: User, task_id: str, limit: int = 200, offset: int = 0) -> Dict[str, Any]:
    """All updates for a given task (chronological), if task is visible."""
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    tq = tq.filter(Task.id == task_id)
    if not tq.first():
        return {"total": 0, "updates": []}
    q = db.query(TaskUpdate).filter(TaskUpdate.task_id == task_id).order_by(TaskUpdate.date.asc())
    total = q.count()
    rows: Sequence[TaskUpdate] = q.offset(offset).limit(limit).all()
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
            }
            for u in rows
        ],
    }


# ----------------------------- Aggregates -----------------------------

def aggregate_updates_by_status(db: Session, current_user: User, eo_id: str | None = None, task_id: str | None = None) -> Dict[str, int]:
    q = db.query(TaskUpdate)
    if task_id:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = {str(r[0]) for r in tq.all()}
        if task_id not in visible_task_ids:
            return {}
        q = q.filter(TaskUpdate.task_id == task_id)
    elif eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return {}
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return {}
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    rows = q.with_entities(TaskUpdate.status, func.count()).group_by(TaskUpdate.status).all()
    return {status: count for status, count in rows}


def average_progress(db: Session, current_user: User, eo_id: str | None = None, task_id: str | None = None) -> float:
    q = db.query(func.avg(TaskUpdate.progress_pct))
    if task_id:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = {str(r[0]) for r in tq.all()}
        if task_id not in visible_task_ids:
            return 0.0
        q = q.filter(TaskUpdate.task_id == task_id)
    elif eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return 0.0
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return 0.0
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    val = q.scalar() or 0
    try:
        return float(val)
    except Exception:
        return 0.0


def blockers_and_risks_counts(db: Session, current_user: User, eo_id: str | None = None) -> Dict[str, int]:
    q = db.query(TaskUpdate)
    if eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return {"blockers": 0, "risks": 0}
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return {"blockers": 0, "risks": 0}
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    blockers = q.filter(TaskUpdate.blockers != None).count()  # noqa: E711
    risks = q.filter(TaskUpdate.risks != None).count()  # noqa: E711
    return {"blockers": blockers, "risks": risks}


def updates_per_user(db: Session, current_user: User, eo_id: str | None = None) -> Dict[str, int]:
    q = db.query(TaskUpdate)
    if eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return {}
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return {}
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    rows = q.with_entities(TaskUpdate.user_id, func.count()).group_by(TaskUpdate.user_id).all()
    return {str(uid): count for uid, count in rows}


def updates_per_user_ranked(
    db: Session,
    current_user: User,
    eo_id: str | None = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Ranked counts of updates per executor within the caller's visibility.

    - Optional eo_id to scope portfolio
    - Optional date window [date_from, date_to]
    - Sorted by count desc, limited
    """
    q = db.query(TaskUpdate)
    if eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return []
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return []
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    if date_from:
        q = q.filter(TaskUpdate.date >= date_from)
    if date_to:
        q = q.filter(TaskUpdate.date <= date_to)
    rows = (
        q.with_entities(TaskUpdate.user_id, func.count().label("count"))
        .group_by(TaskUpdate.user_id)
        .order_by(func.count().desc())
        .limit(limit)
        .all()
    )
    return [{"user_id": str(uid), "count": cnt} for uid, cnt in rows]


def updates_per_eo(db: Session, current_user: User) -> Dict[str, int]:
    tq = db.query(Task.id, Task.eo_id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    visible_task_ids = [r[0] for r in tq.all()]
    eo_ids = [r[1] for r in tq.all()]
    if not visible_task_ids:
        return {}
    q = db.query(TaskUpdate.eo_id, func.count()).filter(TaskUpdate.task_id.in_(visible_task_ids)).group_by(TaskUpdate.eo_id)
    return {str(eo): cnt for eo, cnt in q.all()}


def updates_per_task(db: Session, current_user: User) -> Dict[str, int]:
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    visible_task_ids = [r[0] for r in tq.all()]
    if not visible_task_ids:
        return {}
    q = db.query(TaskUpdate.task_id, func.count()).filter(TaskUpdate.task_id.in_(visible_task_ids)).group_by(TaskUpdate.task_id)
    return {str(tid): cnt for tid, cnt in q.all()}


# ----------------------------- Timeseries -----------------------------

def timeseries_updates_count(
    db: Session,
    current_user: User,
    bucket: str = "day",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    eo_id: str | None = None,
    task_id: str | None = None,
) -> List[Dict[str, Any]]:
    q = db.query(TaskUpdate)
    if task_id:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = {str(r[0]) for r in tq.all()}
        if task_id not in visible_task_ids:
            return []
        q = q.filter(TaskUpdate.task_id == task_id)
    elif eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return []
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return []
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    if date_from:
        q = q.filter(TaskUpdate.date >= date_from)
    if date_to:
        q = q.filter(TaskUpdate.date <= date_to)
    bucket_col = func.date_trunc("week" if bucket == "week" else "day", TaskUpdate.date)
    rows = q.with_entities(bucket_col.label("bucket"), func.count().label("count")).group_by(bucket_col).order_by(bucket_col).all()
    return [{"bucket": b.isoformat(), "count": c} for b, c in rows]


def timeseries_average_progress(
    db: Session,
    current_user: User,
    bucket: str = "day",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    eo_id: str | None = None,
) -> List[Dict[str, Any]]:
    q = db.query(TaskUpdate)
    if eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return []
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return []
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    if date_from:
        q = q.filter(TaskUpdate.date >= date_from)
    if date_to:
        q = q.filter(TaskUpdate.date <= date_to)
    bucket_col = func.date_trunc("week" if bucket == "week" else "day", TaskUpdate.date)
    rows = q.with_entities(bucket_col.label("bucket"), func.avg(TaskUpdate.progress_pct).label("avg")).group_by(bucket_col).order_by(bucket_col).all()
    return [{"bucket": b.isoformat(), "avg_progress": float(a) if a is not None else 0.0} for b, a in rows]


def timeseries_blockers_count(db: Session, current_user: User, bucket: str = "day", date_from: Optional[date] = None, date_to: Optional[date] = None, eo_id: str | None = None) -> List[Dict[str, Any]]:
    q = db.query(TaskUpdate)
    if eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return []
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return []
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    if date_from:
        q = q.filter(TaskUpdate.date >= date_from)
    if date_to:
        q = q.filter(TaskUpdate.date <= date_to)
    q = q.filter(TaskUpdate.blockers != None)  # noqa: E711
    bucket_col = func.date_trunc("week" if bucket == "week" else "day", TaskUpdate.date)
    rows = q.with_entities(bucket_col.label("bucket"), func.count()).group_by(bucket_col).order_by(bucket_col).all()
    return [{"bucket": b.isoformat(), "blockers": c} for b, c in rows]


def timeseries_risks_count(db: Session, current_user: User, bucket: str = "day", date_from: Optional[date] = None, date_to: Optional[date] = None, eo_id: str | None = None) -> List[Dict[str, Any]]:
    q = db.query(TaskUpdate)
    if eo_id:
        eq = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
        eq = ChatVisibility.apply_eo_visibility(eq, current_user)
        if not eq.first():
            return []
        q = q.filter(TaskUpdate.eo_id == eo_id)
    else:
        tq = db.query(Task.id)
        tq = ChatVisibility.apply_task_visibility(tq, current_user)
        visible_task_ids = [r[0] for r in tq.all()]
        if not visible_task_ids:
            return []
        q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    if date_from:
        q = q.filter(TaskUpdate.date >= date_from)
    if date_to:
        q = q.filter(TaskUpdate.date <= date_to)
    q = q.filter(TaskUpdate.risks != None)  # noqa: E711
    bucket_col = func.date_trunc("week" if bucket == "week" else "day", TaskUpdate.date)
    rows = q.with_entities(bucket_col.label("bucket"), func.count()).group_by(bucket_col).order_by(bucket_col).all()
    return [{"bucket": b.isoformat(), "risks": c} for b, c in rows]


def velocity_updates_per_executor_per_week(db: Session, current_user: User, date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[Dict[str, Any]]:
    """Counts of updates per executor per week within visibility."""
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    visible_task_ids = [r[0] for r in tq.all()]
    if not visible_task_ids:
        return []
    q = db.query(TaskUpdate)
    q = q.filter(TaskUpdate.task_id.in_(visible_task_ids))
    if date_from:
        q = q.filter(TaskUpdate.date >= date_from)
    if date_to:
        q = q.filter(TaskUpdate.date <= date_to)
    week_col = func.date_trunc("week", TaskUpdate.date)
    rows = q.with_entities(TaskUpdate.user_id, week_col.label("week"), func.count().label("count")).group_by(TaskUpdate.user_id, week_col).order_by(week_col).all()
    return [{"user_id": str(uid), "week": wk.isoformat(), "count": cnt} for uid, wk, cnt in rows]


# ----------------------------- Cross-entity helpers -----------------------------

def updates_for_tasks_due_this_week(db: Session, current_user: User, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    today = date.today()
    end = today + timedelta(days=7)
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    tq = tq.filter(Task.due_date != None, Task.due_date >= today, Task.due_date <= end)  # noqa: E711
    task_ids = [r[0] for r in tq.all()]
    if not task_ids:
        return {"total": 0, "updates": []}
    q = db.query(TaskUpdate).filter(TaskUpdate.task_id.in_(task_ids)).order_by(TaskUpdate.date.desc())
    total = q.count()
    rows: Sequence[TaskUpdate] = q.offset(offset).limit(limit).all()
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
            }
            for u in rows
        ],
    }


def updates_for_tasks_in_category(db: Session, current_user: User, category_term: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    tq = tq.filter(Task.category.ilike(f"%{category_term}%"))
    task_ids = [r[0] for r in tq.all()]
    if not task_ids:
        return {"total": 0, "updates": []}
    q = db.query(TaskUpdate).filter(TaskUpdate.task_id.in_(task_ids)).order_by(TaskUpdate.date.desc())
    total = q.count()
    rows: Sequence[TaskUpdate] = q.offset(offset).limit(limit).all()
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
            }
            for u in rows
        ],
    }


def updates_for_tasks_assigned_to(db: Session, current_user: User, assignee_id: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    tq = tq.filter(Task.assignee_id == assignee_id)
    task_ids = [r[0] for r in tq.all()]
    if not task_ids:
        return {"total": 0, "updates": []}
    q = db.query(TaskUpdate).filter(TaskUpdate.task_id.in_(task_ids)).order_by(TaskUpdate.date.desc())
    total = q.count()
    rows: Sequence[TaskUpdate] = q.offset(offset).limit(limit).all()
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
            }
            for u in rows
        ],
    }


# ----------------------------- Coverage / Quality helpers -----------------------------

def first_vs_recent_update_per_task(db: Session, current_user: User, eo_id: str | None = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """For each visible task, return first and most recent update summaries and progress delta."""
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    if eo_id:
        tq = tq.filter(Task.eo_id == eo_id)
    task_ids = [r[0] for r in tq.all()]
    if not task_ids:
        return []

    first_sub = (
        db.query(TaskUpdate.task_id, func.min(TaskUpdate.date).label("min_date"))
        .filter(TaskUpdate.task_id.in_(task_ids))
        .group_by(TaskUpdate.task_id)
        .subquery()
    )
    recent_sub = (
        db.query(TaskUpdate.task_id, func.max(TaskUpdate.date).label("max_date"))
        .filter(TaskUpdate.task_id.in_(task_ids))
        .group_by(TaskUpdate.task_id)
        .subquery()
    )
    first_rows = (
        db.query(TaskUpdate)
        .join(first_sub, and_(TaskUpdate.task_id == first_sub.c.task_id, TaskUpdate.date == first_sub.c.min_date))
        .all()
    )
    recent_rows = (
        db.query(TaskUpdate)
        .join(recent_sub, and_(TaskUpdate.task_id == recent_sub.c.task_id, TaskUpdate.date == recent_sub.c.max_date))
        .order_by(TaskUpdate.date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    # Build maps
    first_by_task: Dict[str, TaskUpdate] = {str(u.task_id): u for u in first_rows}
    out: List[Dict[str, Any]] = []
    for u in recent_rows:
        first = first_by_task.get(str(u.task_id))
        delta = None
        if first and first.progress_pct is not None and u.progress_pct is not None:
            delta = u.progress_pct - first.progress_pct
        out.append({
            "task_id": str(u.task_id),
            "first": {
                "date": first.date.isoformat() if first else None,
                "progress_pct": first.progress_pct if first else None,
            },
            "recent": {
                "date": u.date.isoformat(),
                "progress_pct": u.progress_pct,
            },
            "delta_progress": delta,
        })
    return out


def tasks_without_recent_updates(db: Session, current_user: User, days: int = 7, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Visible tasks with no updates in the last N days."""
    cutoff = date.today() - timedelta(days=days)
    tq = db.query(Task)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    # NOT EXISTS update newer than cutoff
    sub = db.query(TaskUpdate.id).filter(TaskUpdate.task_id == Task.id, TaskUpdate.date >= cutoff)
    tq = tq.filter(~exists(sub))
    total = tq.count()
    rows: Sequence[Task] = tq.order_by(Task.due_date.nulls_last()).offset(offset).limit(limit).all()
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


def tasks_with_consecutive_blockers(
    db: Session,
    current_user: User,
    min_days: int = 2,
    window_days: int = 7,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Heuristic detection of tasks with blockers on >= min_days within the last window_days.
    This approximates consecutive days by requiring count>=min_days and the span between
    min(date) and max(date) <= (count-1) days.
    """
    cutoff = date.today() - timedelta(days=window_days)
    tq = db.query(Task.id)
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    visible_task_ids = [r[0] for r in tq.all()]
    if not visible_task_ids:
        return {"total": 0, "tasks": []}

    sub = (
        db.query(
            TaskUpdate.task_id.label("task_id"),
            func.count().label("cnt"),
            func.min(TaskUpdate.date).label("min_d"),
            func.max(TaskUpdate.date).label("max_d"),
        )
        .filter(
            TaskUpdate.task_id.in_(visible_task_ids),
            TaskUpdate.blockers != None,  # noqa: E711
            TaskUpdate.date >= cutoff,
        )
        .group_by(TaskUpdate.task_id)
        .subquery()
    )
    # cnt >= min_days and span <= (cnt-1)
    q = db.query(Task).join(sub, Task.id == sub.c.task_id).filter(
        and_(sub.c.cnt >= min_days, func.extract('epoch', sub.c.max_d - sub.c.min_d) <= (sub.c.cnt - 1) * 24 * 3600)
    )
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


