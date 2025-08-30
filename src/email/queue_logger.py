"""
Email Queue Logger

This module provides logging utilities for email queue operations to help with
debugging email sending, rate limiting, and delivery issues.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from src.db.session import SessionLocal
from src.models.email_queue_log import EmailQueueLog

logger = logging.getLogger(__name__)

class EmailQueueLogger:
    """Utility class for logging email queue operations"""
    
    @staticmethod
    def log_email_queued(email_id: str, to_addresses: List[str], subject: str = None,
                        email_type: str = "general", priority: int = 2,
                        celery_task_id: str = None, eo_id: str = None, 
                        email_log_id: str = None) -> Optional[str]:
        """Log when an email is queued for sending"""
        try:
            with SessionLocal() as db:
                queue_log = EmailQueueLog(
                    email_id=email_id,
                    to_addresses=to_addresses,
                    subject=subject[:500] if subject else None,  # Truncate long subjects
                    email_type=email_type,
                    priority=priority,
                    status="queued",
                    celery_task_id=celery_task_id,
                    eo_id=eo_id,
                    email_log_id=email_log_id,
                    queued_at=datetime.now(timezone.utc)
                )
                
                db.add(queue_log)
                db.commit()
                
                logger.info(f"Logged email queued: {email_id} to {to_addresses}")
                return str(queue_log.id)
                
        except Exception as e:
            logger.error(f"Failed to log email queued for {email_id}: {e}")
            return None
    
    @staticmethod
    def log_email_processing_start(email_id: str, processor_worker: str = None):
        """Log when email processing starts"""
        try:
            with SessionLocal() as db:
                queue_log = db.query(EmailQueueLog).filter(EmailQueueLog.email_id == email_id).first()
                
                if queue_log:
                    queue_log.status = "processing"
                    queue_log.started_processing_at = datetime.now(timezone.utc)
                    queue_log.processor_worker = processor_worker
                    
                    db.commit()
                    logger.info(f"Logged email processing start: {email_id}")
                else:
                    logger.warning(f"Email queue log not found for processing start: {email_id}")
                    
        except Exception as e:
            logger.error(f"Failed to log email processing start for {email_id}: {e}")
    
    @staticmethod
    def log_email_sent_success(email_id: str, smtp_host: str = None, 
                              smtp_response_code: int = None, smtp_response_message: str = None,
                              outbox_saved: bool = False, outbox_path: str = None):
        """Log when email is sent successfully"""
        try:
            with SessionLocal() as db:
                queue_log = db.query(EmailQueueLog).filter(EmailQueueLog.email_id == email_id).first()
                
                if queue_log:
                    queue_log.status = "sent"
                    queue_log.completed_at = datetime.now(timezone.utc)
                    queue_log.smtp_host = smtp_host
                    queue_log.smtp_response_code = smtp_response_code or 250
                    queue_log.smtp_response_message = smtp_response_message[:1000] if smtp_response_message else None
                    queue_log.outbox_saved = outbox_saved
                    queue_log.outbox_path = outbox_path
                    queue_log.is_rate_limited = False
                    
                    db.commit()
                    logger.info(f"Logged email sent successfully: {email_id}")
                else:
                    logger.warning(f"Email queue log not found for success: {email_id}")
                    
        except Exception as e:
            logger.error(f"Failed to log email success for {email_id}: {e}")
    
    @staticmethod
    def log_email_failed(email_id: str, error_message: str, smtp_host: str = None,
                        smtp_response_code: int = None, smtp_response_message: str = None,
                        is_rate_limited: bool = False, retry_count: int = 0, 
                        outbox_saved: bool = False, outbox_path: str = None):
        """Log when email sending fails"""
        try:
            with SessionLocal() as db:
                queue_log = db.query(EmailQueueLog).filter(EmailQueueLog.email_id == email_id).first()
                
                if queue_log:
                    # Determine final status
                    if retry_count >= queue_log.max_retries:
                        queue_log.status = "abandoned"
                        queue_log.completed_at = datetime.now(timezone.utc)
                    else:
                        queue_log.status = "failed"
                    
                    queue_log.error_message = error_message[:1000] if error_message else None
                    queue_log.smtp_host = smtp_host
                    queue_log.smtp_response_code = smtp_response_code
                    queue_log.smtp_response_message = smtp_response_message[:1000] if smtp_response_message else None
                    queue_log.is_rate_limited = is_rate_limited
                    queue_log.retry_count = retry_count
                    queue_log.outbox_saved = outbox_saved
                    queue_log.outbox_path = outbox_path
                    
                    db.commit()
                    logger.info(f"Logged email failure: {email_id} (attempt {retry_count + 1})")
                else:
                    logger.warning(f"Email queue log not found for failure: {email_id}")
                    
        except Exception as e:
            logger.error(f"Failed to log email failure for {email_id}: {e}")
    
    @staticmethod
    def log_email_retry(email_id: str, retry_count: int, error_message: str = None):
        """Log when email is being retried"""
        try:
            with SessionLocal() as db:
                queue_log = db.query(EmailQueueLog).filter(EmailQueueLog.email_id == email_id).first()
                
                if queue_log:
                    queue_log.status = "queued"  # Back to queued for retry
                    queue_log.retry_count = retry_count
                    if error_message:
                        queue_log.error_message = error_message[:1000]
                    
                    db.commit()
                    logger.info(f"Logged email retry: {email_id} (attempt {retry_count})")
                else:
                    logger.warning(f"Email queue log not found for retry: {email_id}")
                    
        except Exception as e:
            logger.error(f"Failed to log email retry for {email_id}: {e}")
    
    @staticmethod
    def get_queue_stats() -> Dict[str, Any]:
        """Get email queue statistics from the database"""
        try:
            with SessionLocal() as db:
                # Get counts by status
                status_counts = {}
                for status in ["queued", "processing", "sent", "failed", "abandoned"]:
                    count = db.query(EmailQueueLog).filter(EmailQueueLog.status == status).count()
                    status_counts[status] = count
                
                # Get recent failures (last hour)
                one_hour_ago = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                recent_failures = db.query(EmailQueueLog).filter(
                    EmailQueueLog.status.in_(["failed", "abandoned"]),
                    EmailQueueLog.updated_at >= one_hour_ago
                ).count()
                
                # Get rate limited emails (last hour)
                rate_limited = db.query(EmailQueueLog).filter(
                    EmailQueueLog.is_rate_limited == True,
                    EmailQueueLog.updated_at >= one_hour_ago
                ).count()
                
                return {
                    **status_counts,
                    "recent_failures": recent_failures,
                    "recent_rate_limited": rate_limited,
                    "total": sum(status_counts.values())
                }
                
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def cleanup_old_logs(days_to_keep: int = 30):
        """Clean up old email queue logs to prevent database bloat"""
        try:
            with SessionLocal() as db:
                cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)
                
                deleted_count = db.query(EmailQueueLog).filter(
                    EmailQueueLog.created_at < cutoff_date
                ).delete()
                
                db.commit()
                logger.info(f"Cleaned up {deleted_count} old email queue logs")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return 0
