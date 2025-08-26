from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.models.eo_pmo_assignment import EOPMOAssignment
from src.models.executive_order import ExecutiveOrder
from src.models.user import User
from typing import List, Optional
import uuid

def assign_pmos_to_eo(
    db: Session,
    eo_id: str,
    pmo_ids: List[str],
    assigned_by: str,
    primary_pmo_id: Optional[str] = None
) -> List[EOPMOAssignment]:
    """
    Assign PMOs to an Executive Order.
    
    Args:
        db: Database session
        eo_id: Executive Order ID
        pmo_ids: List of PMO user IDs to assign
        assigned_by: User ID who is making the assignment
        primary_pmo_id: Optional primary PMO ID (for initial approval emails)
    
    Returns:
        List of created assignments
    """
    # Verify EO exists
    eo = db.query(ExecutiveOrder).filter(ExecutiveOrder.id == eo_id).first()
    if not eo:
        raise ValueError(f"Executive Order with ID {eo_id} not found")
    
    # Verify all PMOs exist and are reviewers
    pmos = db.query(User).filter(
        and_(
            User.id.in_(pmo_ids),
            User.role == "reviewer"
        )
    ).all()
    
    if len(pmos) != len(pmo_ids):
        raise ValueError("Some PMO users not found or not reviewers")
    
    # Remove existing assignments for this EO
    db.query(EOPMOAssignment).filter(EOPMOAssignment.eo_id == eo_id).delete()
    
    # Create new assignments
    assignments = []
    for pmo_id in pmo_ids:
        assignment = EOPMOAssignment(
            eo_id=eo_id,
            pmo_id=pmo_id,
            assigned_by=assigned_by,
            is_primary=(pmo_id == primary_pmo_id) if primary_pmo_id else False
        )
        db.add(assignment)
        assignments.append(assignment)
    
    db.commit()
    
    # Refresh assignments to get IDs
    for assignment in assignments:
        db.refresh(assignment)
    
    return assignments

def get_pmos_for_eo(db: Session, eo_id: str) -> List[EOPMOAssignment]:
    """Get all PMO assignments for an EO."""
    return db.query(EOPMOAssignment).filter(EOPMOAssignment.eo_id == eo_id).all()

def get_primary_pmo_for_eo(db: Session, eo_id: str) -> Optional[EOPMOAssignment]:
    """Get the primary PMO assignment for an EO."""
    return db.query(EOPMOAssignment).filter(
        and_(
            EOPMOAssignment.eo_id == eo_id,
            EOPMOAssignment.is_primary == True
        )
    ).first()

def get_eos_for_pmo(db: Session, pmo_id: str) -> List[EOPMOAssignment]:
    """Get all EO assignments for a PMO."""
    return db.query(EOPMOAssignment).filter(EOPMOAssignment.pmo_id == pmo_id).all()

def remove_pmo_from_eo(db: Session, eo_id: str, pmo_id: str) -> bool:
    """Remove a specific PMO assignment from an EO."""
    assignment = db.query(EOPMOAssignment).filter(
        and_(
            EOPMOAssignment.eo_id == eo_id,
            EOPMOAssignment.pmo_id == pmo_id
        )
    ).first()
    
    if assignment:
        db.delete(assignment)
        db.commit()
        return True
    return False

def get_pmo_emails_for_eo(db: Session, eo_id: str) -> List[str]:
    """Get all PMO email addresses for an EO."""
    assignments = db.query(EOPMOAssignment).join(User).filter(
        EOPMOAssignment.eo_id == eo_id
    ).all()
    
    return [assignment.pmo.email for assignment in assignments]

def get_primary_pmo_email_for_eo(db: Session, eo_id: str) -> Optional[str]:
    """Get the primary PMO email address for an EO."""
    assignment = get_primary_pmo_for_eo(db, eo_id)
    return assignment.pmo.email if assignment else None
