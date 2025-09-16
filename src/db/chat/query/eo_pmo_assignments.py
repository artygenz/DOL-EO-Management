from __future__ import annotations

"""EO ↔ PMO assignment queries (read-only)."""

from typing import Any, Dict, Optional, Sequence, List
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.user import User
from src.models.executive_order import ExecutiveOrder
from src.models.eo_pmo_assignment import EOPMOAssignment
from src.db.chat.visibility import ChatVisibility
from src.db.chat.enrichment import create_enrichment


def _apply_visibility(q, current_user: User):
    """Join EO and apply EO visibility constraints to the assignment query."""
    q = q.join(ExecutiveOrder, EOPMOAssignment.eo_id == ExecutiveOrder.id)
    q = ChatVisibility.apply_eo_visibility(q, current_user)
    return q


def search_assignments(
    db: Session,
    current_user: User,
    eo_id: Optional[str] = None,
    pmo_id: Optional[str] = None,
    is_primary: Optional[bool] = None,
    assigned_from: Optional[date] = None,
    assigned_to: Optional[date] = None,
    sort: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """List EO↔PMO assignments with filters; role-scoped via EO visibility."""
    q = db.query(EOPMOAssignment)
    q = _apply_visibility(q, current_user)
    if eo_id:
        q = q.filter(EOPMOAssignment.eo_id == eo_id)
    if pmo_id:
        q = q.filter(EOPMOAssignment.pmo_id == pmo_id)
    if is_primary is not None:
        q = q.filter(EOPMOAssignment.is_primary == is_primary)
    if assigned_from:
        q = q.filter(EOPMOAssignment.assigned_at >= assigned_from)
    if assigned_to:
        q = q.filter(EOPMOAssignment.assigned_at <= assigned_to)

    # Sorting
    if sort == "is_primary_desc":
        q = q.order_by(EOPMOAssignment.is_primary.desc(), EOPMOAssignment.assigned_at.desc())
    else:
        q = q.order_by(EOPMOAssignment.assigned_at.desc())

    total = q.count()
    rows: Sequence[EOPMOAssignment] = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        **({"rbac_blocked": True} if total == 0 else {}),
        "assignments": [
            {
                "eo_id": str(a.eo_id),
                "pmo_id": str(a.pmo_id),
                "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
                "is_primary": a.is_primary,
            }
            for a in rows
        ],
    }


def get_eo_pmo_assignments(db: Session, current_user: User, eo_id: str) -> Dict[str, Any]:
    """All PMO assignments for a visible EO (primary flag, assigned_at)."""
    q = db.query(EOPMOAssignment)
    q = _apply_visibility(q, current_user)
    q = q.filter(EOPMOAssignment.eo_id == eo_id)
    rows: Sequence[EOPMOAssignment] = q.order_by(EOPMOAssignment.is_primary.desc(), EOPMOAssignment.assigned_at.asc()).all()
    return {
        "eo_id": eo_id,
        "assignments": [
            {
                "pmo_id": str(a.pmo_id),
                "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
                "is_primary": a.is_primary,
            }
            for a in rows
        ],
    }


def aggregate_assignments(
    db: Session,
    current_user: User,
    group_by: str,
    eo_id: Optional[str] = None,
    pmo_id: Optional[str] = None,
    assigned_from: Optional[date] = None,
    assigned_to: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Counts of assignments grouped by is_primary or pmo_id."""
    q = db.query(EOPMOAssignment)
    q = _apply_visibility(q, current_user)
    if eo_id:
        q = q.filter(EOPMOAssignment.eo_id == eo_id)
    if pmo_id:
        q = q.filter(EOPMOAssignment.pmo_id == pmo_id)
    if assigned_from:
        q = q.filter(EOPMOAssignment.assigned_at >= assigned_from)
    if assigned_to:
        q = q.filter(EOPMOAssignment.assigned_at <= assigned_to)

    if group_by == "is_primary":
        rows = (
            q.with_entities(EOPMOAssignment.is_primary.label("group"), func.count())
            .group_by(EOPMOAssignment.is_primary)
            .all()
        )
        return [{"group": bool(g), "metrics": {"count": c}} for g, c in rows]

    if group_by == "pmo_id":
        rows = (
            q.with_entities(EOPMOAssignment.pmo_id.label("group"), func.count())
            .group_by(EOPMOAssignment.pmo_id)
            .all()
        )
        raw_aggregates = [{"group": str(g), "metrics": {"count": c}} for g, c in rows]
        
        # Enrich with human-readable PMO names
        enrichment = create_enrichment(db)
        return enrichment.enrich_pmo_aggregates(raw_aggregates)

    # Fallback: overall count
    return [{"group": "all", "metrics": {"count": q.count()}}]


def timeseries_assignments(
    db: Session,
    current_user: User,
    bucket: str = "day",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    eo_id: Optional[str] = None,
    pmo_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Counts of assignments over time (assigned_at), bucketed by day/week."""
    q = db.query(EOPMOAssignment)
    q = _apply_visibility(q, current_user)
    if eo_id:
        q = q.filter(EOPMOAssignment.eo_id == eo_id)
    if pmo_id:
        q = q.filter(EOPMOAssignment.pmo_id == pmo_id)
    if date_from:
        q = q.filter(EOPMOAssignment.assigned_at >= date_from)
    if date_to:
        q = q.filter(EOPMOAssignment.assigned_at <= date_to)

    bucket_col = func.date_trunc("week" if bucket == "week" else "day", EOPMOAssignment.assigned_at)
    rows = q.with_entities(bucket_col.label("bucket"), func.count()).group_by(bucket_col).order_by(bucket_col).all()
    return [{"bucket": b.isoformat(), "count": c} for b, c in rows]


