"""
Queued Email Service

This module provides an email service that uses the global email queue
instead of sending emails directly. This prevents rate limiting issues
by coordinating all email sending through a centralized queue.
"""

import logging
from typing import List, Optional, Dict, Any, Callable
from src.email.redis_email_queue import get_redis_email_queue

logger = logging.getLogger(__name__)

class QueuedEmailService:
    """
    Email service that uses the global email queue
    """
    
    def __init__(self):
        self.queue = get_redis_email_queue()
    
    def send(self,
             to: List[str],
             subject: str,
             body_text: str,
             body_html: Optional[str] = None,
             attachments: Optional[List] = None,
             headers: Optional[Dict[str, str]] = None,
             email_log_id: Optional[str] = None,
             email_type: str = "general",
             priority: int = 2,  # 0=urgent, 1=high, 2=normal, 3=low
             callback: Optional[Callable] = None,
             callback_args: Optional[tuple] = None,
             callback_kwargs: Optional[Dict[str, Any]] = None) -> str:
        """
        Queue an email for sending
        
        Args:
            to: List of recipient email addresses
            subject: Email subject
            body_text: Plain text email body
            body_html: HTML email body (optional)
            attachments: List of attachments (optional)
            headers: Additional email headers (optional)
            email_log_id: Email log ID for tracking (optional)
            email_type: Type of email for categorization (optional)
            priority: Email priority level (optional)
            callback: Callback function to call after sending (optional)
            callback_args: Arguments for callback function (optional)
            callback_kwargs: Keyword arguments for callback function (optional)
        
        Returns:
            Email request ID
        """
        # Convert attachments to the format expected by the Redis queue
        queue_attachments = None
        if attachments:
            queue_attachments = []
            for attachment in attachments:
                if hasattr(attachment, 'filename'):
                    # Attachment object - convert to dict for JSON serialization
                    queue_attachments.append({
                        'filename': attachment.filename,
                        'content_type': attachment.content_type,
                        'data': attachment.data.hex()  # Convert bytes to hex string for JSON
                    })
                else:
                    # Dictionary format
                    if 'data' in attachment and isinstance(attachment['data'], bytes):
                        attachment = attachment.copy()
                        attachment['data'] = attachment['data'].hex()
                    queue_attachments.append(attachment)
        
        # Enqueue the email in Redis
        email_id = self.queue.enqueue_email(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=queue_attachments,
            headers=headers,
            email_log_id=email_log_id,
            email_type=email_type,
            priority=priority
        )
        
        logger.info(f"Email queued for sending: {email_id} to {to}")
        return email_id
    
    def send_and_save(self,
                     to: List[str],
                     subject: str,
                     body_text: str,
                     body_html: Optional[str] = None,
                     attachments: Optional[List] = None,
                     headers: Optional[Dict[str, str]] = None,
                     email_log_id: Optional[str] = None,
                     email_type: str = "general") -> str:
        """
        Queue an email for sending (alias for send method)
        
        This method maintains compatibility with the existing EmailService interface
        """
        return self.send(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            headers=headers,
            email_log_id=email_log_id,
            email_type=email_type
        )
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get email queue statistics"""
        return self.queue.get_queue_stats()
    
    def clear_rate_limits(self, recipient: Optional[str] = None):
        """Clear rate limit information (not applicable for Redis queue)"""
        pass  # Redis queue doesn't have rate limits - handled by processor

# Convenience functions for backward compatibility
def send_email(to: List[str],
               subject: str,
               body_text: str,
               body_html: Optional[str] = None,
               attachments: Optional[List] = None,
               headers: Optional[Dict[str, str]] = None,
               email_log_id: Optional[str] = None,
               email_type: str = "general",
               priority: int = 2) -> str:
    """
    Convenience function to queue an email for sending
    """
    service = QueuedEmailService()
    return service.send(
        to=to,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        attachments=attachments,
        headers=headers,
        email_log_id=email_log_id,
        email_type=email_type,
        priority=priority
    )

def send_urgent_email(to: List[str],
                     subject: str,
                     body_text: str,
                     body_html: Optional[str] = None,
                     attachments: Optional[List] = None,
                     headers: Optional[Dict[str, str]] = None,
                     email_log_id: Optional[str] = None,
                     email_type: str = "urgent") -> str:
    """
    Convenience function to queue an urgent email for sending
    """
    return send_email(
        to=to,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        attachments=attachments,
        headers=headers,
        email_log_id=email_log_id,
        email_type=email_type,
        priority=0  # Urgent priority
    )
