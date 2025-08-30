"""
Monitoring Routes

This module provides API endpoints for monitoring Celery tasks and email queue operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from src.core.dependencies import get_current_user, get_db
from src.models.user import User
from src.models.celery_task_log import CeleryTaskLog
from src.models.email_queue_log import EmailQueueLog
from src.email.queue_logger import EmailQueueLogger

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/celery/tasks", response_model=Dict[str, Any])
def get_celery_task_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    task_name: Optional[str] = Query(None),
    eo_id: Optional[str] = Query(None)
):
    """Get Celery task execution logs"""
    
    # Only admins can view monitoring logs
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = db.query(CeleryTaskLog)
    
    # Apply filters
    if status:
        query = query.filter(CeleryTaskLog.status == status)
    if task_name:
        query = query.filter(CeleryTaskLog.task_name.ilike(f"%{task_name}%"))
    if eo_id:
        query = query.filter(CeleryTaskLog.eo_id == eo_id)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    tasks = query.order_by(desc(CeleryTaskLog.created_at)).offset(offset).limit(limit).all()
    
    # Convert to dict for JSON response
    task_logs = []
    for task in tasks:
        task_logs.append({
            "id": str(task.id),
            "task_id": task.task_id,
            "task_name": task.task_name,
            "status": task.status,
            "worker_name": task.worker_name,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration_seconds": task.duration_seconds,
            "error_message": task.error_message,
            "retry_count": task.retry_count,
            "eo_id": task.eo_id,
            "email_log_id": task.email_log_id,
            "created_at": task.created_at.isoformat()
        })
    
    return {
        "tasks": task_logs,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/celery/stats", response_model=Dict[str, Any])
def get_celery_task_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get Celery task statistics"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get stats for last 24 hours
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    
    # Status counts
    status_counts = {}
    for status in ["started", "success", "failure", "retry"]:
        count = db.query(CeleryTaskLog).filter(
            CeleryTaskLog.status == status,
            CeleryTaskLog.created_at >= yesterday
        ).count()
        status_counts[status] = count
    
    # Task type counts
    task_counts = db.query(
        CeleryTaskLog.task_name,
        func.count(CeleryTaskLog.id).label('count')
    ).filter(
        CeleryTaskLog.created_at >= yesterday
    ).group_by(CeleryTaskLog.task_name).all()
    
    task_type_counts = {task_name: count for task_name, count in task_counts}
    
    # Average duration for successful tasks
    avg_duration = db.query(func.avg(CeleryTaskLog.duration_seconds)).filter(
        CeleryTaskLog.status == "success",
        CeleryTaskLog.duration_seconds.isnot(None),
        CeleryTaskLog.created_at >= yesterday
    ).scalar()
    
    return {
        "period": "last_24_hours",
        "status_counts": status_counts,
        "task_type_counts": task_type_counts,
        "average_duration_seconds": float(avg_duration) if avg_duration else None,
        "total_tasks": sum(status_counts.values())
    }

@router.get("/email/queue", response_model=Dict[str, Any])
def get_email_queue_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    email_type: Optional[str] = Query(None),
    is_rate_limited: Optional[bool] = Query(None)
):
    """Get email queue logs"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = db.query(EmailQueueLog)
    
    # Apply filters
    if status:
        query = query.filter(EmailQueueLog.status == status)
    if email_type:
        query = query.filter(EmailQueueLog.email_type == email_type)
    if is_rate_limited is not None:
        query = query.filter(EmailQueueLog.is_rate_limited == is_rate_limited)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    emails = query.order_by(desc(EmailQueueLog.created_at)).offset(offset).limit(limit).all()
    
    # Convert to dict for JSON response
    email_logs = []
    for email in emails:
        email_logs.append({
            "id": str(email.id),
            "email_id": email.email_id,
            "to_addresses": email.to_addresses,
            "subject": email.subject,
            "email_type": email.email_type,
            "priority": email.priority,
            "status": email.status,
            "queued_at": email.queued_at.isoformat(),
            "started_processing_at": email.started_processing_at.isoformat() if email.started_processing_at else None,
            "completed_at": email.completed_at.isoformat() if email.completed_at else None,
            "smtp_response_code": email.smtp_response_code,
            "retry_count": email.retry_count,
            "is_rate_limited": email.is_rate_limited,
            "error_message": email.error_message,
            "outbox_saved": email.outbox_saved,
            "eo_id": email.eo_id,
            "celery_task_id": email.celery_task_id
        })
    
    return {
        "emails": email_logs,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/email/stats", response_model=Dict[str, Any])
def get_email_queue_stats(
    current_user: User = Depends(get_current_user)
):
    """Get email queue statistics"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return EmailQueueLogger.get_queue_stats()

@router.get("/dashboard", response_model=Dict[str, Any])
def get_monitoring_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get monitoring dashboard data"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get recent activity (last hour)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    
    # Recent Celery tasks
    recent_tasks = db.query(CeleryTaskLog).filter(
        CeleryTaskLog.created_at >= one_hour_ago
    ).count()
    
    failed_tasks = db.query(CeleryTaskLog).filter(
        CeleryTaskLog.status == "failure",
        CeleryTaskLog.created_at >= one_hour_ago
    ).count()
    
    # Recent emails
    recent_emails = db.query(EmailQueueLog).filter(
        EmailQueueLog.created_at >= one_hour_ago
    ).count()
    
    failed_emails = db.query(EmailQueueLog).filter(
        EmailQueueLog.status.in_(["failed", "abandoned"]),
        EmailQueueLog.created_at >= one_hour_ago
    ).count()
    
    rate_limited_emails = db.query(EmailQueueLog).filter(
        EmailQueueLog.is_rate_limited == True,
        EmailQueueLog.created_at >= one_hour_ago
    ).count()
    
    # Current queue status
    email_stats = EmailQueueLogger.get_queue_stats()
    
    return {
        "period": "last_hour",
        "celery": {
            "recent_tasks": recent_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": ((recent_tasks - failed_tasks) / recent_tasks * 100) if recent_tasks > 0 else 100
        },
        "email": {
            "recent_emails": recent_emails,
            "failed_emails": failed_emails,
            "rate_limited_emails": rate_limited_emails,
            "success_rate": ((recent_emails - failed_emails) / recent_emails * 100) if recent_emails > 0 else 100,
            "current_queue": email_stats
        }
    }
