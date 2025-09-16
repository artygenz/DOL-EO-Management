from __future__ import annotations

"""User chat queries (read-only)."""

from typing import Any, Dict, Optional, Sequence, List
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, exists

from src.models.user import User as OrmUser
from src.models.task import Task
from src.models.task_update import TaskUpdate
from src.models.executive_order import ExecutiveOrder
from src.models.eo_pmo_assignment import EOPMOAssignment
from src.db.chat.visibility import ChatVisibility
from src.db.chat.enrichment import create_enrichment


def search_users(
    db: Session,
    current_user: OrmUser,
    role: Optional[str] = None,
    org_role_contains: Optional[str] = None,
    is_active: Optional[bool] = None,
    name_or_email_contains: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    q = db.query(OrmUser)
    q = ChatVisibility.apply_user_visibility(q, current_user)
    if role:
        q = q.filter(OrmUser.role == role)
    if org_role_contains:
        q = q.filter(OrmUser.org_role.ilike(f"%{org_role_contains}%"))
    if is_active is not None:
        q = q.filter(OrmUser.is_active == is_active)
    if name_or_email_contains:
        term = f"%{name_or_email_contains}%"
        q = q.filter((OrmUser.name.ilike(term)) | (OrmUser.email.ilike(term)))
    total = q.count()
    rows: Sequence[OrmUser] = q.order_by(OrmUser.name.asc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        **({"rbac_blocked": True} if total == 0 else {}),
        "users": [
            {
                "id": str(u.id),
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "org_role": u.org_role,
                "is_active": bool(u.is_active),
            }
            for u in rows
        ],
    }


def get_user_details(db: Session, current_user: OrmUser, user_id: str) -> Dict[str, Any]:
    q = db.query(OrmUser).filter(OrmUser.id == user_id)
    q = ChatVisibility.apply_user_visibility(q, current_user)
    u = q.first()
    if not u:
        return {"error": "Not found or not visible"}
    return {
        "id": str(u.id),
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "org_role": u.org_role,
        "is_active": bool(u.is_active),
    }


def aggregate_users(db: Session, current_user: OrmUser, group_by: str = "role", role: Optional[str] = None, org_role_contains: Optional[str] = None, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
    q = db.query(OrmUser)
    q = ChatVisibility.apply_user_visibility(q, current_user)
    if role:
        q = q.filter(OrmUser.role == role)
    if org_role_contains:
        q = q.filter(OrmUser.org_role.ilike(f"%{org_role_contains}%"))
    if is_active is not None:
        q = q.filter(OrmUser.is_active == is_active)
    if group_by == "org_role":
        rows = q.with_entities(OrmUser.org_role.label("group"), func.count()).group_by(OrmUser.org_role).all()
        return [{"group": g or "", "metrics": {"count": c}} for g, c in rows]
    # role
    rows = q.with_entities(OrmUser.role.label("group"), func.count()).group_by(OrmUser.role).all()
    return [{"group": g or "", "metrics": {"count": c}} for g, c in rows]


def pmo_visible_executors(db: Session, current_user: OrmUser, name_or_email_contains: Optional[str] = None, org_role_contains: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Reviewers: list executors who have tasks on PMO-assigned EOs. Admin sees all executors; executor sees self only."""
    q = db.query(OrmUser)
    q = ChatVisibility.apply_user_visibility(q, current_user)
    if name_or_email_contains:
        term = f"%{name_or_email_contains}%"
        q = q.filter((OrmUser.name.ilike(term)) | (OrmUser.email.ilike(term)))
    if org_role_contains:
        q = q.filter(OrmUser.org_role.ilike(f"%{org_role_contains}%"))
    total = q.count()
    rows: Sequence[OrmUser] = q.order_by(OrmUser.name.asc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "users": [
            {
                "id": str(u.id),
                "name": u.name,
                "email": u.email,
                "org_role": u.org_role,
            }
            for u in rows
        ],
    }


def user_summary(db: Session, current_user: OrmUser, user_id: str, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Dict[str, Any]:
    """Summary for a user: task status totals, overdue count, updates/blockers/risks counts in window."""
    # Visibility: user must be visible
    uq = db.query(OrmUser).filter(OrmUser.id == user_id)
    uq = ChatVisibility.apply_user_visibility(uq, current_user)
    if not uq.first():
        return {"error": "Not found or not visible"}

    # Tasks assigned to the user (within PMO visibility if reviewer)
    tq = db.query(Task).filter(Task.assignee_id == user_id)
    if current_user.role != "admin":
        # Apply PMO/executor scope via EO visibility by joining EO and assignments
        if current_user.role == "reviewer":
            tq = (
                tq.join(ExecutiveOrder, Task.eo_id == ExecutiveOrder.id)
                .join(EOPMOAssignment, EOPMOAssignment.eo_id == ExecutiveOrder.id)
                .filter(EOPMOAssignment.pmo_id == current_user.id)
            )
        else:  # executor
            tq = tq.filter(Task.assignee_id == current_user.id)

    # Status totals
    by_status_rows = tq.with_entities(Task.status, func.count()).group_by(Task.status).all()
    by_status = {s: c for s, c in by_status_rows}

    # Overdue tasks count
    today = func.current_date()
    overdue_count = (
        tq.session.query(func.count(Task.id))
        .filter(Task.due_date != None, Task.due_date < today)  # noqa: E711
        .filter(Task.status.notin_(["completed", "rejected"]))
        .scalar()
    )

    # Updates window
    uqry = db.query(TaskUpdate).filter(TaskUpdate.user_id == user_id)
    if date_from:
        uqry = uqry.filter(TaskUpdate.date >= date_from)
    if date_to:
        uqry = uqry.filter(TaskUpdate.date <= date_to)
    updates_count = uqry.count()
    blockers_count = uqry.filter(TaskUpdate.blockers != None).count()  # noqa: E711
    risks_count = uqry.filter(TaskUpdate.risks != None).count()  # noqa: E711

    return {
        "by_status": by_status,
        "overdue_tasks": int(overdue_count or 0),
        "updates_count": int(updates_count or 0),
        "blockers_count": int(blockers_count or 0),
        "risks_count": int(risks_count or 0),
    }


def timeseries_user_updates(db: Session, current_user: OrmUser, user_id: Optional[str] = None, bucket: str = "day", date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[Dict[str, Any]]:
    """Trend of update activity; if user_id omitted, scope to visible executors (reviewer) or self (executor), global for admin."""
    q = db.query(TaskUpdate)
    if user_id:
        # Ensure target user is visible
        uq = db.query(OrmUser).filter(OrmUser.id == user_id)
        uq = _apply_user_visibility(db, uq, current_user)
        if not uq.first():
            return []
        q = q.filter(TaskUpdate.user_id == user_id)
    else:
        if current_user.role == "executor":
            q = q.filter(TaskUpdate.user_id == current_user.id)
        elif current_user.role == "reviewer":
            # Limit to executors visible to this PMO via tasks on assigned EOs
            tq = (
                db.query(Task.assignee_id)
                .join(ExecutiveOrder, Task.eo_id == ExecutiveOrder.id)
                .join(EOPMOAssignment, EOPMOAssignment.eo_id == ExecutiveOrder.id)
                .filter(EOPMOAssignment.pmo_id == current_user.id)
                .distinct()
            )
            q = q.filter(TaskUpdate.user_id.in_([r[0] for r in tq.all()]))
        # admin: no restriction

    if date_from:
        q = q.filter(TaskUpdate.date >= date_from)
    if date_to:
        q = q.filter(TaskUpdate.date <= date_to)
    bucket_col = func.date_trunc("week" if bucket == "week" else "day", TaskUpdate.date)
    rows = q.with_entities(bucket_col.label("bucket"), func.count()).group_by(bucket_col).order_by(bucket_col).all()
    return [{"bucket": b.isoformat(), "count": c} for b, c in rows]


def leaderboard_users(db: Session, current_user: OrmUser, metric: str = "updates_count", limit: int = 10, date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[Dict[str, Any]]:
    """Top users by metric within visibility: updates_count | blockers_count | risks_count | overdue_tasks."""
    if metric in {"updates_count", "blockers_count", "risks_count"}:
        q = db.query(TaskUpdate.user_id)
        # Scope to visible executors for reviewer; self for executor
        if current_user.role == "executor":
            q = q.filter(TaskUpdate.user_id == current_user.id)
        elif current_user.role == "reviewer":
            tq = (
                db.query(Task.assignee_id)
                .join(ExecutiveOrder, Task.eo_id == ExecutiveOrder.id)
                .join(EOPMOAssignment, EOPMOAssignment.eo_id == ExecutiveOrder.id)
                .filter(EOPMOAssignment.pmo_id == current_user.id)
                .distinct()
            )
            q = q.filter(TaskUpdate.user_id.in_([r[0] for r in tq.all()]))
        if date_from:
            q = q.filter(TaskUpdate.date >= date_from)
        if date_to:
            q = q.filter(TaskUpdate.date <= date_to)
        if metric == "updates_count":
            rows = db.query(TaskUpdate.user_id, func.count().label("score")).select_from(q.subquery()).group_by(TaskUpdate.user_id).order_by(func.count().desc()).limit(limit).all()
        elif metric == "blockers_count":
            rows = db.query(TaskUpdate.user_id, func.count().label("score")).filter(TaskUpdate.blockers != None).group_by(TaskUpdate.user_id).order_by(func.count().desc()).limit(limit).all()  # noqa: E711
        else:  # risks_count
            rows = db.query(TaskUpdate.user_id, func.count().label("score")).filter(TaskUpdate.risks != None).group_by(TaskUpdate.user_id).order_by(func.count().desc()).limit(limit).all()  # noqa: E711
        
        raw_aggregates = [{"user_id": str(uid), "score": int(score)} for uid, score in rows]
        
        # Enrich with human-readable user names
        enrichment = create_enrichment(db)
        return enrichment.enrich_executor_aggregates(raw_aggregates)

    # overdue_tasks per user (assignee)
    today = func.current_date()
    tq = db.query(Task.assignee_id, func.count().label("score"))
    tq = ChatVisibility.apply_task_visibility(tq, current_user)
    tq = tq.filter(Task.due_date != None, Task.due_date < today)  # noqa: E711
    tq = tq.filter(Task.status.notin_(["completed", "rejected"]))
    rows = tq.group_by(Task.assignee_id).order_by(func.count().desc()).limit(limit).all()
    
    raw_aggregates = [{"user_id": str(uid), "score": int(score)} for uid, score in rows]
    
    # Enrich with human-readable user names
    enrichment = create_enrichment(db)
    return enrichment.enrich_executor_aggregates(raw_aggregates)