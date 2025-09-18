"""
Redis-backed Email Queue Service

This module provides a Redis-backed email queue that allows multiple worker processes
to queue emails, but only a single process (main worker process) handles SMTP sending.

This prevents concurrent SMTP connections that cause rate limiting.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import redis
from src.email.queue_logger import EmailQueueLogger

logger = logging.getLogger(__name__)

@dataclass
class RedisEmailRequest:
    """Email request for Redis queue"""
    id: str
    to: List[str]
    subject: str
    body_text: str
    body_html: Optional[str] = None
    attachments: Optional[List[Dict]] = None
    headers: Optional[Dict[str, str]] = None
    email_log_id: Optional[str] = None
    email_type: str = "general"
    priority: int = 2  # 0=urgent, 1=high, 2=normal, 3=low
    created_at: str = ""
    retry_count: int = 0
    max_retries: int = 3

class RedisEmailQueue:
    """
    Redis-backed email queue for distributed email sending
    """
    
    def __init__(self, redis_url: str = None):
        """Initialize Redis email queue"""
        if not redis_url:
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_url = f"redis://{redis_host}:6379/0"
        
        self.redis_client = redis.from_url(redis_url)
        self.queue_key = "email_queue"
        self.processing_key = "email_processing"
        
    def enqueue_email(self, 
                     to: List[str],
                     subject: str,
                     body_text: str,
                     body_html: Optional[str] = None,
                     attachments: Optional[List[Dict]] = None,
                     headers: Optional[Dict[str, str]] = None,
                     email_log_id: Optional[str] = None,
                     email_type: str = "general",
                     priority: int = 2) -> str:
        """
        Add an email to the Redis queue
        
        Returns:
            Email request ID
        """
        email_request = RedisEmailRequest(
            id=str(uuid.uuid4()),
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            headers=headers,
            email_log_id=email_log_id,
            email_type=email_type,
            priority=priority,
            created_at=datetime.utcnow().isoformat()
        )
        
        # Add to Redis queue with priority scoring
        priority_score = priority * 1000000 + int(time.time())
        
        try:
            self.redis_client.zadd(
                self.queue_key, 
                {json.dumps(asdict(email_request)): priority_score}
            )
            logger.info(f"Email queued in Redis: {email_request.id} to {to}")
            
            # Log to database
            EmailQueueLogger.log_email_queued(
                email_id=email_request.id,
                to_addresses=to,
                subject=email_request.subject,
                email_type=email_type,
                priority=priority,
                email_log_id=email_log_id
            )
            
            return email_request.id
            
        except Exception as e:
            logger.error(f"Failed to queue email in Redis: {e}")
            raise
    
    def get_next_email(self) -> Optional[RedisEmailRequest]:
        """
        Get the next email from the Redis queue
        
        Returns:
            Next email request or None if queue is empty
        """
        try:
            # Get the email with lowest priority score (highest priority)
            result = self.redis_client.zpopmin(self.queue_key, count=1)
            
            if not result:
                return None
            
            email_data, score = result[0]
            email_dict = json.loads(email_data)
            
            # Move to processing queue
            self.redis_client.hset(
                self.processing_key, 
                email_dict['id'], 
                email_data
            )
            
            return RedisEmailRequest(**email_dict)
            
        except Exception as e:
            logger.error(f"Failed to get next email from Redis queue: {e}")
            return None
    
    def mark_email_completed(self, email_id: str):
        """Mark an email as completed and remove from processing queue"""
        try:
            self.redis_client.hdel(self.processing_key, email_id)
            logger.debug(f"Email marked as completed: {email_id}")
        except Exception as e:
            logger.error(f"Failed to mark email as completed: {e}")
    
    def requeue_email(self, email_request: RedisEmailRequest):
        """Re-queue an email for retry"""
        try:
            email_request.retry_count += 1
            
            if email_request.retry_count > email_request.max_retries:
                logger.error(f"Email exceeded max retries: {email_request.id}")
                self.mark_email_completed(email_request.id)
                return
            
            # Re-add to queue with lower priority (higher score)
            priority_score = (email_request.priority + email_request.retry_count) * 1000000 + int(time.time())
            
            self.redis_client.zadd(
                self.queue_key,
                {json.dumps(asdict(email_request)): priority_score}
            )
            
            # Remove from processing
            self.redis_client.hdel(self.processing_key, email_request.id)
            
            logger.warning(f"Email re-queued for retry {email_request.retry_count}: {email_request.id}")
            
        except Exception as e:
            logger.error(f"Failed to re-queue email: {e}")
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        try:
            return {
                'queue_size': self.redis_client.zcard(self.queue_key),
                'processing_count': self.redis_client.hlen(self.processing_key)
            }
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {'queue_size': 0, 'processing_count': 0}


# Global Redis email queue instance
_redis_email_queue: Optional[RedisEmailQueue] = None

def get_redis_email_queue() -> RedisEmailQueue:
    """Get the global Redis email queue instance"""
    global _redis_email_queue
    if _redis_email_queue is None:
        _redis_email_queue = RedisEmailQueue()
    return _redis_email_queue
