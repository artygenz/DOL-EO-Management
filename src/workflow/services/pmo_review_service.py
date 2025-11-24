"""
PMO Review Service

Extracts business logic from send_pmo_review_email task for better separation of concerns.
"""

from typing import Dict, List, Optional
import os
from dataclasses import dataclass
from src.workflow import repository as repo
from src.email.email_template_builder import EmailTemplateBuilder
from src.email.queued_email_service import QueuedEmailService


@dataclass
class Attachment:
    """Attachment data class for email service"""
    filename: str
    content_type: str
    data: bytes


class PMOReviewService:
    """Service for PMO review emails - extracts business logic from send_pmo_review_email task"""
    
    def __init__(self):
        # Keep existing services as-is
        pass
    
    def send_pmo_review_email(self, eo_id: str, task_list: List) -> Dict:
        """
        Business logic extracted from send_pmo_review_email task
        
        Args:
            eo_id: Executive Order ID
            task_list: List of tasks to include in review email
            
        Returns:
            Dict containing eo_id, sent_to, message_id, and tasks count
        """
        # Validation
        if not eo_id:
            raise ValueError("eo_id is required")
        if task_list is None:
            task_list = []

        # Load EO using existing repository
        eo = repo.get_executive_order(eo_id)
        if not eo:
            raise ValueError(f"ExecutiveOrder not found for id={eo_id}")
        
        # Get PMO email
        pmo_email = os.getenv("PMO_EMAIL_ADDRESS", "kevin.brown@lumenlighthouse.ai")

        print(f"\n=== PMO Review Email Started ===")
        print(f"EO ID: {eo_id}")
        print(f"EO Title: {eo.title}")
        print(f"PMO Email: {pmo_email}")
        print(f"Tasks: {len(task_list)}")
        
        # Build email using existing template builder
        built = EmailTemplateBuilder.build_pmo_review(eo, task_list)

        # Log email
        email_log_id = self._log_outgoing_email(built, pmo_email, eo.id)

        # Send email using existing service
        svc = QueuedEmailService()
        attachments = [Attachment(fn, ct, data) for (fn, ct, data) in built.attachments]

        message_id = svc.send_and_save(
            to=[pmo_email],
            subject=built.subject,
            body_text=built.body_text,
            body_html=built.body_html,
            attachments=attachments,
            headers=built.headers,
            email_log_id=email_log_id,
            email_type="eo_review"
        )

        print(f"PMO review email sent successfully")
        print(f"Message ID: {message_id}")
        print(f"================================\n")
        
        return {
            "eo_id": eo_id,
            "sent_to": pmo_email,
            "message_id": message_id,
            "tasks": len(task_list)
        }
    
    def _log_outgoing_email(self, built_email, pmo_email: str, eo_id: str) -> Optional[str]:
        """Extract email logging logic"""
        try:
            email_log = repo.save_email_log(
                direction="outgoing",
                subject=built_email.subject,
                sender=None,
                recipients=[pmo_email],
                raw_content=built_email.body_text,
                related_eo_id=eo_id,
            )
            email_log_id = str(email_log.id)
            return email_log_id
        except Exception as e:
            print(f"Warning: Could not save email log: {e}")
            return None
