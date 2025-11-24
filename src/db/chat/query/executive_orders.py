from __future__ import annotations

"""Executive order chat queries (read-only)."""

from typing import Any, Dict
from datetime import date
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.executive_order import ExecutiveOrder
from src.models.task import Task
from src.models.task_update import TaskUpdate
from src.models.eo_pmo_assignment import EOPMOAssignment
from sqlalchemy import func, exists, and_
from src.db.chat.visibility import ChatVisibility
from src.db.chat.filters import EOFilters


def get_eo_details(db: Session, current_user: User, eo_id: str) -> Dict[str, Any]:
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


def get_cfo_overview(db: Session, current_user: User) -> Dict[str, Any]:
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


# ----------------------------- EO search/list -----------------------------

def search_eos(db: Session, current_user: User, filters: EOFilters, sort: str | None = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    q = db.query(ExecutiveOrder)
    q = ChatVisibility.apply_eo_visibility(q, current_user)

    if filters.title_contains:
        q = q.filter(ExecutiveOrder.title.ilike(f"%{filters.title_contains}%"))
    if filters.status:
        q = q.filter(ExecutiveOrder.status == filters.status)
    if filters.received_from:
        q = q.filter(ExecutiveOrder.received_at >= filters.received_from)
    if filters.received_to:
        q = q.filter(ExecutiveOrder.received_at <= filters.received_to)

    # has_pmo / has_primary_pmo via assignments
    if filters.has_pmo is True:
        sub = db.query(EOPMOAssignment.eo_id).filter(EOPMOAssignment.eo_id == ExecutiveOrder.id)
        q = q.filter(sub.exists())
    if filters.has_pmo is False:
        sub = db.query(EOPMOAssignment.eo_id).filter(EOPMOAssignment.eo_id == ExecutiveOrder.id)
        q = q.filter(~sub.exists())
    if filters.has_primary_pmo is True:
        sub = db.query(EOPMOAssignment.eo_id).filter(EOPMOAssignment.eo_id == ExecutiveOrder.id, EOPMOAssignment.is_primary == True)  # noqa: E712
        q = q.filter(sub.exists())
    if filters.has_primary_pmo is False:
        sub = db.query(EOPMOAssignment.eo_id).filter(EOPMOAssignment.eo_id == ExecutiveOrder.id, EOPMOAssignment.is_primary == True)  # noqa: E712
        q = q.filter(~sub.exists())

    # has_overdue via tasks
    if filters.has_overdue is not None:
        today = func.current_date()
        overdue_sub = (
            db.query(Task.id)
            .filter(Task.eo_id == ExecutiveOrder.id)
            .filter(Task.due_date != None, Task.due_date < today)  # noqa: E711
            .filter(Task.status.notin_(["completed", "rejected"]))
        )
        q = q.filter(overdue_sub.exists() if filters.has_overdue else ~overdue_sub.exists())

    # has_blockers / has_risks via updates
    if filters.has_blockers is not None:
        blk = db.query(TaskUpdate.id).filter(TaskUpdate.eo_id == ExecutiveOrder.id, TaskUpdate.blockers != None)  # noqa: E711
        q = q.filter(blk.exists() if filters.has_blockers else ~blk.exists())
    if filters.has_risks is not None:
        rsk = db.query(TaskUpdate.id).filter(TaskUpdate.eo_id == ExecutiveOrder.id, TaskUpdate.risks != None)  # noqa: E711
        q = q.filter(rsk.exists() if filters.has_risks else ~rsk.exists())

    # Sorting
    if sort == "title":
        q = q.order_by(ExecutiveOrder.title.asc())
    elif sort == "open_tasks_desc":
        # order by count of non-completed/rejected tasks desc
        sub = (
            db.query(func.count(Task.id))
            .filter(Task.eo_id == ExecutiveOrder.id)
            .filter(Task.status.notin_(["completed", "rejected"]))
            .correlate(ExecutiveOrder)
        )
        q = q.order_by(sub.desc())
    elif sort == "overdue_tasks_desc":
        today = func.current_date()
        sub = (
            db.query(func.count(Task.id))
            .filter(Task.eo_id == ExecutiveOrder.id)
            .filter(Task.due_date != None, Task.due_date < today)  # noqa: E711
            .filter(Task.status.notin_(["completed", "rejected"]))
            .correlate(ExecutiveOrder)
        )
        q = q.order_by(sub.desc())
    else:
        q = q.order_by(ExecutiveOrder.received_at.desc())

    total = q.count()
    rows = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        **({"rbac_blocked": True} if total == 0 else {}),
        "executive_orders": [
            {
                "id": str(e.id),
                "title": e.title,
                "status": e.status,
                "received_at": e.received_at.isoformat() if getattr(e, "received_at", None) else None,
            }
            for e in rows
        ],
    }


def get_eo_summary(db: Session, current_user: User, eo_id: str) -> Dict[str, Any]:
    """Return task status/category totals, open/overdue counts, last update date, and PMO assignments for an EO."""
    # Ensure EO is visible
    q = db.query(ExecutiveOrder.id).filter(ExecutiveOrder.id == eo_id)
    q = ChatVisibility.apply_eo_visibility(q, current_user)
    if not q.first():
        return {"error": "Not found or not visible"}

    # Totals by status
    rows_status = (
        db.query(Task.status, func.count())
        .filter(Task.eo_id == eo_id)
        .group_by(Task.status)
        .all()
    )
    by_status = {status: count for status, count in rows_status}

    # Totals by category
    rows_cat = (
        db.query(Task.category, func.count())
        .filter(Task.eo_id == eo_id)
        .group_by(Task.category)
        .all()
    )
    by_category = {str(cat): count for cat, count in rows_cat}

    # Open/overdue counts
    today = func.current_date()
    open_count = (
        db.query(func.count(Task.id))
        .filter(Task.eo_id == eo_id)
        .filter(Task.status.notin_(["completed", "rejected"]))
        .scalar()
    )
    overdue_count = (
        db.query(func.count(Task.id))
        .filter(Task.eo_id == eo_id)
        .filter(Task.due_date != None, Task.due_date < today)  # noqa: E711
        .filter(Task.status.notin_(["completed", "rejected"]))
        .scalar()
    )

    # Latest update date
    last_update = (
        db.query(func.max(TaskUpdate.date)).filter(TaskUpdate.eo_id == eo_id).scalar()
    )

    # PMO assignments (names not joined here; tool can enrich if needed)
    assignments = (
        db.query(EOPMOAssignment)
        .filter(EOPMOAssignment.eo_id == eo_id)
        .order_by(EOPMOAssignment.assigned_at.asc())
        .all()
    )
    pmos = [
        {
            "pmo_id": str(a.pmo_id),
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
            "is_primary": a.is_primary,
        }
        for a in assignments
    ]

    return {
        "by_status": by_status,
        "by_category": by_category,
        "open_tasks": int(open_count or 0),
        "overdue_tasks": int(overdue_count or 0),
        "last_update_date": last_update.isoformat() if hasattr(last_update, "isoformat") and last_update else None,
        "pmo_assignments": pmos,
    }


# ----------------------------- Aggregates & Timeseries -----------------------------

def _apply_eo_filters(db: Session, q, filters: EOFilters):
    """Apply EOFilters to a base EO query (helper, mutates query)."""
    if filters is None:
        return q
    if filters.title_contains:
        q = q.filter(ExecutiveOrder.title.ilike(f"%{filters.title_contains}%"))
    if filters.status:
        q = q.filter(ExecutiveOrder.status == filters.status)
    if filters.received_from:
        q = q.filter(ExecutiveOrder.received_at >= filters.received_from)
    if filters.received_to:
        q = q.filter(ExecutiveOrder.received_at <= filters.received_to)

    if filters.has_pmo is not None:
        sub = db.query(EOPMOAssignment.eo_id).filter(EOPMOAssignment.eo_id == ExecutiveOrder.id)
        q = q.filter(sub.exists() if filters.has_pmo else ~sub.exists())
    if filters.has_primary_pmo is not None:
        sub = db.query(EOPMOAssignment.eo_id).filter(
            EOPMOAssignment.eo_id == ExecutiveOrder.id,
            EOPMOAssignment.is_primary == True,  # noqa: E712
        )
        q = q.filter(sub.exists() if filters.has_primary_pmo else ~sub.exists())

    if filters.has_overdue is not None:
        today = func.current_date()
        overdue_sub = (
            db.query(Task.id)
            .filter(Task.eo_id == ExecutiveOrder.id)
            .filter(Task.due_date != None, Task.due_date < today)  # noqa: E711
            .filter(Task.status.notin_(["completed", "rejected"]))
        )
        q = q.filter(overdue_sub.exists() if filters.has_overdue else ~overdue_sub.exists())

    if filters.has_blockers is not None:
        blk = db.query(TaskUpdate.id).filter(TaskUpdate.eo_id == ExecutiveOrder.id, TaskUpdate.blockers != None)  # noqa: E711
        q = q.filter(blk.exists() if filters.has_blockers else ~blk.exists())
    if filters.has_risks is not None:
        rsk = db.query(TaskUpdate.id).filter(TaskUpdate.eo_id == ExecutiveOrder.id, TaskUpdate.risks != None)  # noqa: E711
        q = q.filter(rsk.exists() if filters.has_risks else ~rsk.exists())
    return q


def aggregate_eos(db: Session, current_user: User, metrics: list[str], group_by: str, filters: EOFilters | None = None) -> list[dict]:
    """
    Aggregations over visible EOs.
    - metrics: currently supports ["count"]. Additional metrics can be added later.
    - group_by: one of [status|has_pmo|has_primary_pmo|has_overdue]
    - filters: same shape as search_eos
    Returns: list of {group: value, metrics: {...}}
    """
    q = db.query(ExecutiveOrder)
    q = ChatVisibility.apply_eo_visibility(q, current_user)
    q = _apply_eo_filters(db, q, filters or EOFilters())

    rows: list[tuple] = []
    metric_count = func.count(ExecutiveOrder.id).label("count") if "count" in (metrics or ["count"]) else None

    if group_by == "status":
        sel = [ExecutiveOrder.status.label("group")]
        if metric_count is not None:
            sel.append(metric_count)
        rows = q.with_entities(*sel).group_by(ExecutiveOrder.status).all()
        return [{"group": g or "", "metrics": {"count": c}} for g, c in rows]

    if group_by in {"has_pmo", "has_primary_pmo", "has_overdue"}:
        if group_by == "has_pmo":
            expr = db.query(EOPMOAssignment.eo_id).filter(EOPMOAssignment.eo_id == ExecutiveOrder.id).exists()
        elif group_by == "has_primary_pmo":
            expr = db.query(EOPMOAssignment.eo_id).filter(EOPMOAssignment.eo_id == ExecutiveOrder.id, EOPMOAssignment.is_primary == True).exists()  # noqa: E712
        else:  # has_overdue
            today = func.current_date()
            expr = (
                db.query(Task.id)
                .filter(Task.eo_id == ExecutiveOrder.id)
                .filter(Task.due_date != None, Task.due_date < today)  # noqa: E711
                .filter(Task.status.notin_(["completed", "rejected"]))
            ).exists()
        rows = q.with_entities(expr.label("group"), metric_count).group_by(expr).all()
        return [{"group": bool(g), "metrics": {"count": c}} for g, c in rows]

    # Fallback: overall count only
    total = q.count()
    return [{"group": "all", "metrics": {"count": total}}]


def timeseries_eos(
    db: Session,
    current_user: User,
    metric: str,
    bucket: str = "day",
    date_from: date | None = None,
    date_to: date | None = None,
    filters: EOFilters | None = None,
) -> list[dict]:
    """Time-bucketed EO metrics over received_at or derived conditions."""
    q = db.query(ExecutiveOrder)
    q = ChatVisibility.apply_eo_visibility(q, current_user)
    q = _apply_eo_filters(db, q, filters or EOFilters())
    if date_from:
        q = q.filter(ExecutiveOrder.received_at >= date_from)
    if date_to:
        q = q.filter(ExecutiveOrder.received_at <= date_to)

    bucket_col = func.date_trunc("week" if bucket == "week" else "day", ExecutiveOrder.received_at)

    if metric == "received_count":
        rows = q.with_entities(bucket_col.label("bucket"), func.count(ExecutiveOrder.id)).group_by(bucket_col).order_by(bucket_col).all()
        return [{"bucket": b.isoformat(), "count": c} for b, c in rows]

    if metric in {"with_overdue_count", "with_blockers_count"}:
        # Apply existence predicate per EO, then bucket by received_at
        base = q
        if metric == "with_overdue_count":
            today = func.current_date()
            pred = (
                db.query(Task.id)
                .filter(Task.eo_id == ExecutiveOrder.id)
                .filter(Task.due_date != None, Task.due_date < today)  # noqa: E711
                .filter(Task.status.notin_(["completed", "rejected"]))
            ).exists()
        else:
            pred = db.query(TaskUpdate.id).filter(TaskUpdate.eo_id == ExecutiveOrder.id, TaskUpdate.blockers != None).exists()  # noqa: E711
        base = base.filter(pred)
        rows = base.with_entities(bucket_col.label("bucket"), func.count(ExecutiveOrder.id)).group_by(bucket_col).order_by(bucket_col).all()
        return [{"bucket": b.isoformat(), "count": c} for b, c in rows]

    # Unknown metric
    return []


