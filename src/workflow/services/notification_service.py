"""
Notification Service

Extracts business logic from notify_assignees task for better separation of concerns.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)
from src.workflow import repository as repo
from src.email.email_template_builder import EmailTemplateBuilder
from src.email.queued_email_service import QueuedEmailService
from src.db.session import SessionLocal
from src.models.task import Task
from src.models.user import User
from sqlalchemy import select
from dataclasses import dataclass


@dataclass
class Attachment:
    """Attachment data class for email service"""
    filename: str
    content_type: str
    data: bytes


class NotificationService:
    """Service for employee notifications - extracts business logic from notify_assignees task"""
    
    def __init__(self):
        # Keep existing services as-is
        pass
    
    def notify_assignees(self, eo_id: Optional[str]) -> Dict:
        """
        Business logic extracted from notify_assignees task
        
        Args:
            eo_id: Executive Order ID
            
        Returns:
            Dict containing notification results
        """
        if not eo_id:
            return {"notified": 0}
        
        try:
            logger.info(f"Starting employee notification for EO: {eo_id}")
            
            # Load EO
            eo = repo.get_executive_order(eo_id)
            if not eo:
                return {"eo_id": eo_id, "error": "EO not found", "notified": 0}
            
            # Load all approved tasks for this EO
            approved_tasks = self._get_approved_tasks(eo_id)
            if not approved_tasks:
                logger.info(f"No approved tasks found for EO {eo_id}")
                return {"eo_id": eo_id, "notified": 0}
            
            logger.info(f"EO Title: {eo.title}, Total approved tasks: {len(approved_tasks)}")
            
            # Group tasks by assignee
            assignee_tasks = self._group_tasks_by_assignee(approved_tasks)
            logger.info(f"Found {len(assignee_tasks)} assignees to notify")
            
            # Send notification emails to each assignee
            notified_count = self._send_notification_emails(eo, assignee_tasks)
            
            logger.info(f"Employee notification completed: {notified_count} emails sent")
            
            return {"eo_id": eo_id, "notified": notified_count}
            
        except Exception as e:
            logger.error(f"Error in notify_assignees: {e}")
            return {"eo_id": eo_id, "error": str(e), "notified": 0}
    
    def _get_approved_tasks(self, eo_id: str) -> list:
        """Get all approved tasks for an EO"""
        with SessionLocal() as db:
            approved_tasks = db.execute(
                select(Task).where(
                    Task.eo_id == eo_id,
                    Task.status == "approved"
                ).order_by(Task.created_at)
            ).scalars().all()
        
        return approved_tasks
    
    def _group_tasks_by_assignee(self, approved_tasks: list) -> Dict[str, list]:
        """Group tasks by assignee ID"""
        assignee_tasks = {}
        for task in approved_tasks:
            if task.assignee_id:
                assignee_id = str(task.assignee_id)
                if assignee_id not in assignee_tasks:
                    assignee_tasks[assignee_id] = []
                assignee_tasks[assignee_id].append(task)
        
        return assignee_tasks
    
    def _send_notification_emails(self, eo, assignee_tasks: Dict[str, list]) -> int:
        """Send notification emails to each assignee"""
        notified_count = 0
        
        for assignee_id, tasks in assignee_tasks.items():
            try:
                # Get assignee details
                assignee = self._get_assignee_details(assignee_id)
                if not assignee:
                    logger.warning(f"Assignee {assignee_id} not found, skipping")
                    continue
                
                # Convert tasks to dict format for email template
                task_dicts = self._convert_tasks_to_dicts(tasks, assignee)
                
                # Build email template
                built = EmailTemplateBuilder.build_employee_notification(
                    eo=eo,
                    assignee_email=assignee.email,
                    assignee_name=assignee.name,
                    tasks=task_dicts
                )
                
                # Save email log
                email_log_id = self._log_employee_notification(built, assignee.email, eo.id)
                
                # Send email
                message_id = self._send_employee_notification_email(built, assignee.email, email_log_id)
                
                logger.info(f"✓ Notification sent to {assignee.name} ({assignee.email})")
                notified_count += 1
                
            except Exception as e:
                logger.error(f"✗ Error sending notification to assignee {assignee_id}: {e}")
                continue
        
        return notified_count
    
    def _get_assignee_details(self, assignee_id: str) -> Optional[User]:
        """Get assignee details from database"""
        with SessionLocal() as db:
            assignee = db.execute(
                select(User).where(User.id == assignee_id)
            ).scalar_one_or_none()
        
        return assignee
    
    def _convert_tasks_to_dicts(self, tasks: list, assignee: User) -> list:
        """Convert tasks to dictionary format for email template"""
        task_dicts = []
        for task in tasks:
            task_dict = {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "category": task.category,
                "status": task.status,
                "due_date": task.due_date.isoformat() if task.due_date else "TBD",
                "remarks": task.remarks,
                "assignee": assignee.name
            }
            task_dicts.append(task_dict)
        
        return task_dicts
    
    def _log_employee_notification(self, built_email, assignee_email: str, eo_id: str) -> Optional[str]:
        """Log employee notification email"""
        try:
            email_log = repo.save_email_log(
                direction="outgoing",
                subject=built_email.subject,
                sender=None,
                recipients=[assignee_email],
                raw_content=built_email.body_text,
                related_eo_id=eo_id,
            )
            email_log_id = str(email_log.id)
            logger.info(f"Saved employee notification email log with ID: {email_log_id}")
            return email_log_id
        except Exception as e:
            logger.warning(f"Could not save employee notification email log: {e}")
            return None
    
    def _send_employee_notification_email(self, built_email, assignee_email: str, email_log_id: Optional[str]) -> str:
        """Send employee notification email"""
        svc = QueuedEmailService()
        attachments = [Attachment(fn, ct, data) for (fn, ct, data) in built_email.attachments]
        
        message_id = svc.send_and_save(
            to=[assignee_email],
            subject=built_email.subject,
            body_text=built_email.body_text,
            body_html=built_email.body_html,
            attachments=attachments,
            headers=built_email.headers,
            email_log_id=email_log_id,
            email_type="notify_employees"
        )
        
        return message_id
