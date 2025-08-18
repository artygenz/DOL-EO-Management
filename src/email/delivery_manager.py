"""
Delivery Manager with Comprehensive Tracking

This module provides SMTP delivery with confirmation tracking, delivery status monitoring,
automatic retry logic with exponential backoff, and bounce handling for the Email Agent.
Implements requirements 4.4 and 4.5 for reliable email delivery and failure escalation.
"""

import logging
import smtplib
import ssl
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import hashlib
import json
import threading
from queue import Queue, PriorityQueue, Empty
import re

from ..config.models import SMTPSettings
from ..database.manager import DatabaseManager
from ..database.models import AuditLogEntry, AuditAction

logger = logging.getLogger(__name__)


class DeliveryStatus(Enum):
    """Email delivery status enumeration."""
    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    RETRYING = "retrying"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"


class DeliveryPriority(Enum):
    """Email delivery priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class BounceType(Enum):
    """Email bounce classification types."""
    HARD_BOUNCE = "hard_bounce"  # Permanent failure
    SOFT_BOUNCE = "soft_bounce"  # Temporary failure
    BLOCK_BOUNCE = "block_bounce"  # Blocked by recipient server
    UNKNOWN = "unknown"


@dataclass
class DeliveryAttempt:
    """Individual delivery attempt record."""
    attempt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: DeliveryStatus = DeliveryStatus.PENDING
    smtp_response_code: Optional[int] = None
    smtp_response_message: Optional[str] = None
    error_message: Optional[str] = None
    delivery_time_ms: Optional[float] = None
    server_host: Optional[str] = None
    server_port: Optional[int] = None


@dataclass
class DeliveryRecord:
    """Comprehensive delivery tracking record."""
    delivery_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    recipient_email: str = ""
    sender_email: str = ""
    subject: str = ""
    message_id: str = ""
    priority: DeliveryPriority = DeliveryPriority.NORMAL
    status: DeliveryStatus = DeliveryStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None
    bounce_type: Optional[BounceType] = None
    bounce_reason: Optional[str] = None
    attempts: List[DeliveryAttempt] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate delivery record after initialization."""
        if not self.recipient_email:
            raise ValueError("Recipient email cannot be empty")
        if not self.sender_email:
            raise ValueError("Sender email cannot be empty")
        if not self.subject:
            raise ValueError("Subject cannot be empty")
    
    def add_attempt(self, attempt: DeliveryAttempt) -> None:
        """Add a delivery attempt to the record."""
        self.attempts.append(attempt)
        self.updated_at = datetime.utcnow()
        
        if attempt.status == DeliveryStatus.DELIVERED:
            self.status = DeliveryStatus.DELIVERED
            self.delivered_at = attempt.timestamp
        elif attempt.status == DeliveryStatus.FAILED:
            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                self.status = DeliveryStatus.ESCALATED
                self.failed_at = attempt.timestamp
            else:
                self.status = DeliveryStatus.RETRYING
                self._schedule_next_retry()
    
    def _schedule_next_retry(self) -> None:
        """Schedule next retry with exponential backoff."""
        # Exponential backoff: 2^retry_count minutes with jitter
        base_delay = 2 ** self.retry_count
        jitter = base_delay * 0.1  # 10% jitter
        delay_minutes = base_delay + (jitter * (2 * hash(self.delivery_id) % 100 - 100) / 100)
        
        self.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
        logger.info(f"Scheduled retry {self.retry_count + 1} for delivery {self.delivery_id} at {self.next_retry_at}")


@dataclass
class SMTPConnectionConfig:
    """SMTP connection configuration with security settings."""
    host: str
    port: int = 587
    use_tls: bool = True
    use_ssl: bool = False
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    local_hostname: Optional[str] = None
    source_address: Optional[Tuple[str, int]] = None
    
    def __post_init__(self):
        """Validate SMTP configuration."""
        if not self.host:
            raise ValueError("SMTP host cannot be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError("SMTP port must be between 1 and 65535")
        if self.timeout <= 0:
            raise ValueError("SMTP timeout must be positive")


class DeliveryManagerError(Exception):
    """Base exception for delivery manager errors."""
    pass


class SMTPConnectionError(DeliveryManagerError):
    """Raised when SMTP connection fails."""
    pass


class DeliveryFailureError(DeliveryManagerError):
    """Raised when email delivery fails permanently."""
    pass


class DeliveryManager:
    """
    Comprehensive email delivery manager with tracking, retry logic, and bounce handling.
    
    Implements requirements:
    - 4.4: Track delivery confirmation and handle failures
    - 4.5: Retry delivery and escalate persistent failures
    """
    
    def __init__(
        self,
        smtp_config: SMTPConnectionConfig,
        database_manager: Optional[DatabaseManager] = None,
        max_concurrent_deliveries: int = 10,
        delivery_timeout: int = 300,
        enable_bounce_detection: bool = True
    ):
        """
        Initialize the delivery manager.
        
        Args:
            smtp_config: SMTP server configuration
            database_manager: Database manager for persistence
            max_concurrent_deliveries: Maximum concurrent delivery threads
            delivery_timeout: Delivery timeout in seconds
            enable_bounce_detection: Enable bounce detection and handling
        """
        self.smtp_config = smtp_config
        self.database_manager = database_manager
        self.max_concurrent_deliveries = max_concurrent_deliveries
        self.delivery_timeout = delivery_timeout
        self.enable_bounce_detection = enable_bounce_detection
        
        # Delivery tracking
        self.delivery_records: Dict[str, DeliveryRecord] = {}
        self.delivery_queue = PriorityQueue()
        self.retry_queue = Queue()
        
        # Threading for concurrent deliveries
        self.delivery_threads: List[threading.Thread] = []
        self.retry_thread: Optional[threading.Thread] = None
        self.running = False
        self.thread_lock = threading.Lock()
        
        # Metrics
        self.delivery_metrics = {
            'total_sent': 0,
            'total_delivered': 0,
            'total_failed': 0,
            'total_bounced': 0,
            'total_retries': 0,
            'average_delivery_time': 0.0
        }
        
        logger.info("Initialized DeliveryManager with comprehensive tracking")
    
    def start(self) -> None:
        """Start the delivery manager background threads."""
        if self.running:
            logger.warning("DeliveryManager is already running")
            return
        
        self.running = True
        
        # Start delivery worker threads
        for i in range(self.max_concurrent_deliveries):
            thread = threading.Thread(
                target=self._delivery_worker,
                name=f"DeliveryWorker-{i}",
                daemon=True
            )
            thread.start()
            self.delivery_threads.append(thread)
        
        # Start retry worker thread
        self.retry_thread = threading.Thread(
            target=self._retry_worker,
            name="RetryWorker",
            daemon=True
        )
        self.retry_thread.start()
        
        logger.info(f"Started DeliveryManager with {self.max_concurrent_deliveries} delivery workers")
    
    def stop(self) -> None:
        """Stop the delivery manager and wait for threads to complete."""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for threads to complete
        for thread in self.delivery_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        if self.retry_thread and self.retry_thread.is_alive():
            self.retry_thread.join(timeout=5)
        
        logger.info("Stopped DeliveryManager")
    
    def send_email(
        self,
        recipient_email: str,
        sender_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        priority: DeliveryPriority = DeliveryPriority.NORMAL,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send an email with comprehensive tracking.
        
        Args:
            recipient_email: Recipient email address
            sender_email: Sender email address
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            attachments: List of attachments (optional)
            priority: Delivery priority
            correlation_id: Correlation ID for tracking
            metadata: Additional metadata
            
        Returns:
            Delivery ID for tracking
            
        Raises:
            DeliveryManagerError: If email preparation fails
        """
        try:
            # Create delivery record
            delivery_record = DeliveryRecord(
                recipient_email=recipient_email,
                sender_email=sender_email,
                subject=subject,
                message_id=f"<{uuid.uuid4()}@email-agent.dol.gov>",
                priority=priority,
                correlation_id=correlation_id,
                metadata=metadata or {}
            )
            
            # Prepare email message
            message = self._prepare_email_message(
                delivery_record,
                body_text,
                body_html,
                attachments
            )
            
            # Store delivery record
            with self.thread_lock:
                self.delivery_records[delivery_record.delivery_id] = delivery_record
            
            # Queue for delivery
            delivery_task = {
                'delivery_id': delivery_record.delivery_id,
                'message': message,
                'priority': priority.value,
                'timestamp': time.time()  # Add timestamp for ordering
            }
            
            # Use priority queue with lower numbers = higher priority
            priority_value = {
                DeliveryPriority.CRITICAL: 0,
                DeliveryPriority.HIGH: 1,
                DeliveryPriority.NORMAL: 2,
                DeliveryPriority.LOW: 3
            }.get(priority, 2)
            
            # Use tuple with priority, timestamp, and task for proper ordering
            self.delivery_queue.put((priority_value, time.time(), delivery_task))
            
            # Update metrics for sent email
            with self.thread_lock:
                self.delivery_metrics['total_sent'] += 1
            
            # Create audit log entry
            if self.database_manager:
                self._create_audit_entry(
                    AuditAction.EMAIL_DETECTED,  # Using existing action
                    delivery_record.delivery_id,
                    {
                        'action': 'email_queued_for_delivery',
                        'recipient': recipient_email,
                        'subject': subject,
                        'priority': priority.value,
                        'correlation_id': correlation_id
                    }
                )
            
            logger.info(f"Queued email for delivery: {delivery_record.delivery_id} (Priority: {priority.value})")
            return delivery_record.delivery_id
            
        except Exception as e:
            logger.error(f"Failed to queue email for delivery: {str(e)}")
            raise DeliveryManagerError(f"Email preparation failed: {str(e)}")
    
    def get_delivery_status(self, delivery_id: str) -> Optional[DeliveryRecord]:
        """
        Get delivery status for a specific email.
        
        Args:
            delivery_id: Delivery ID to check
            
        Returns:
            DeliveryRecord if found, None otherwise
        """
        with self.thread_lock:
            return self.delivery_records.get(delivery_id)
    
    def get_delivery_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive delivery metrics.
        
        Returns:
            Dictionary containing delivery metrics
        """
        with self.thread_lock:
            # Calculate current metrics
            pending_count = sum(1 for r in self.delivery_records.values() if r.status == DeliveryStatus.PENDING)
            retrying_count = sum(1 for r in self.delivery_records.values() if r.status == DeliveryStatus.RETRYING)
            
            return {
                **self.delivery_metrics,
                'pending_deliveries': pending_count,
                'retrying_deliveries': retrying_count,
                'total_records': len(self.delivery_records),
                'queue_size': self.delivery_queue.qsize(),
                'retry_queue_size': self.retry_queue.qsize()
            }
    
    def retry_failed_deliveries(self, max_age_hours: int = 24) -> List[str]:
        """
        Manually retry failed deliveries within the specified age.
        
        Args:
            max_age_hours: Maximum age of failed deliveries to retry
            
        Returns:
            List of delivery IDs that were queued for retry
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        retried_ids = []
        
        with self.thread_lock:
            for delivery_id, record in self.delivery_records.items():
                if (record.status == DeliveryStatus.FAILED and 
                    record.created_at >= cutoff_time and 
                    record.retry_count < record.max_retries):
                    
                    # Reset for retry
                    record.status = DeliveryStatus.RETRYING
                    record.next_retry_at = datetime.utcnow()
                    self.retry_queue.put(delivery_id)
                    retried_ids.append(delivery_id)
        
        logger.info(f"Queued {len(retried_ids)} failed deliveries for manual retry")
        return retried_ids
    
    def _prepare_email_message(
        self,
        delivery_record: DeliveryRecord,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> MIMEMultipart:
        """Prepare email message for delivery."""
        # Create message
        if body_html:
            message = MIMEMultipart('alternative')
        else:
            message = MIMEMultipart()
        
        # Set headers
        message['From'] = delivery_record.sender_email
        message['To'] = delivery_record.recipient_email
        message['Subject'] = delivery_record.subject
        message['Message-ID'] = delivery_record.message_id
        message['Date'] = delivery_record.created_at.strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # Add correlation ID if present
        if delivery_record.correlation_id:
            message['X-Correlation-ID'] = delivery_record.correlation_id
        
        # Add priority headers
        if delivery_record.priority in [DeliveryPriority.HIGH, DeliveryPriority.CRITICAL]:
            message['X-Priority'] = '1'
            message['Importance'] = 'high'
        
        # Add text body
        text_part = MIMEText(body_text, 'plain', 'utf-8')
        message.attach(text_part)
        
        # Add HTML body if provided
        if body_html:
            html_part = MIMEText(body_html, 'html', 'utf-8')
            message.attach(html_part)
        
        # Add attachments if provided
        if attachments:
            for attachment in attachments:
                self._add_attachment(message, attachment)
        
        return message
    
    def _add_attachment(self, message: MIMEMultipart, attachment: Dict[str, Any]) -> None:
        """Add attachment to email message."""
        try:
            filename = attachment.get('filename', 'attachment')
            content = attachment.get('content', b'')
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            # Create attachment part
            part = MIMEBase(*content_type.split('/', 1))
            part.set_payload(content)
            encoders.encode_base64(part)
            
            # Add headers
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )
            
            message.attach(part)
            
        except Exception as e:
            logger.error(f"Failed to add attachment {attachment.get('filename', 'unknown')}: {str(e)}")
            raise DeliveryManagerError(f"Attachment processing failed: {str(e)}")
    
    def _delivery_worker(self) -> None:
        """Background worker thread for processing delivery queue."""
        logger.info(f"Started delivery worker thread: {threading.current_thread().name}")
        
        while self.running:
            try:
                # Get delivery task with timeout
                try:
                    priority, timestamp, task = self.delivery_queue.get(timeout=1)
                except Empty:
                    continue
                
                delivery_id = task['delivery_id']
                message = task['message']
                
                # Get delivery record
                with self.thread_lock:
                    delivery_record = self.delivery_records.get(delivery_id)
                
                if not delivery_record:
                    logger.error(f"Delivery record not found: {delivery_id}")
                    continue
                
                # Attempt delivery
                self._attempt_delivery(delivery_record, message)
                
                # Mark task as done
                self.delivery_queue.task_done()
                
            except Exception as e:
                logger.error(f"Delivery worker error: {str(e)}")
                time.sleep(1)  # Brief pause on error
        
        logger.info(f"Stopped delivery worker thread: {threading.current_thread().name}")
    
    def _retry_worker(self) -> None:
        """Background worker thread for processing retry queue."""
        logger.info("Started retry worker thread")
        
        while self.running:
            try:
                # Check for deliveries ready for retry
                current_time = datetime.utcnow()
                retry_candidates = []
                
                with self.thread_lock:
                    for delivery_id, record in self.delivery_records.items():
                        if (record.status == DeliveryStatus.RETRYING and 
                            record.next_retry_at and 
                            record.next_retry_at <= current_time):
                            retry_candidates.append(delivery_id)
                
                # Process retry candidates
                for delivery_id in retry_candidates:
                    try:
                        delivery_record = self.delivery_records.get(delivery_id)
                        if delivery_record:
                            # Recreate message for retry
                            message = self._prepare_email_message(
                                delivery_record,
                                delivery_record.metadata.get('body_text', ''),
                                delivery_record.metadata.get('body_html'),
                                delivery_record.metadata.get('attachments')
                            )
                            
                            # Attempt delivery
                            self._attempt_delivery(delivery_record, message)
                    
                    except Exception as e:
                        logger.error(f"Retry attempt failed for {delivery_id}: {str(e)}")
                
                # Sleep before next check
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Retry worker error: {str(e)}")
                time.sleep(5)  # Brief pause on error
        
        logger.info("Stopped retry worker thread")
    
    def _attempt_delivery(self, delivery_record: DeliveryRecord, message: MIMEMultipart) -> None:
        """Attempt to deliver an email message."""
        attempt = DeliveryAttempt(
            server_host=self.smtp_config.host,
            server_port=self.smtp_config.port
        )
        
        start_time = time.time()
        
        try:
            # Update status to sending
            delivery_record.status = DeliveryStatus.SENDING
            attempt.status = DeliveryStatus.SENDING
            
            # Create SMTP connection
            smtp_server = self._create_smtp_connection()
            
            try:
                # Send message
                smtp_server.send_message(message)
                
                # Calculate delivery time
                delivery_time = (time.time() - start_time) * 1000
                attempt.delivery_time_ms = delivery_time
                attempt.status = DeliveryStatus.DELIVERED
                attempt.smtp_response_code = 250  # Standard success code
                attempt.smtp_response_message = "Message delivered successfully"
                
                # Update metrics
                with self.thread_lock:
                    self.delivery_metrics['total_delivered'] += 1
                    
                    # Update average delivery time
                    current_avg = self.delivery_metrics['average_delivery_time']
                    total_delivered = self.delivery_metrics['total_delivered']
                    self.delivery_metrics['average_delivery_time'] = (
                        (current_avg * (total_delivered - 1) + delivery_time) / total_delivered
                    )
                
                logger.info(f"Successfully delivered email {delivery_record.delivery_id} in {delivery_time:.2f}ms")
                
            finally:
                smtp_server.quit()
        
        except smtplib.SMTPRecipientsRefused as e:
            # Handle recipient-specific errors
            attempt.status = DeliveryStatus.FAILED
            attempt.error_message = f"Recipients refused: {str(e)}"
            
            # Analyze bounce type
            bounce_info = self._analyze_bounce(str(e))
            delivery_record.bounce_type = bounce_info['type']
            delivery_record.bounce_reason = bounce_info['reason']
            
            logger.warning(f"Recipients refused for {delivery_record.delivery_id}: {str(e)}")
        
        except smtplib.SMTPException as e:
            # Handle SMTP-specific errors
            attempt.status = DeliveryStatus.FAILED
            attempt.error_message = f"SMTP error: {str(e)}"
            
            # Extract response code if available
            if hasattr(e, 'smtp_code'):
                attempt.smtp_response_code = e.smtp_code
            if hasattr(e, 'smtp_error'):
                attempt.smtp_response_message = str(e.smtp_error)
            
            logger.error(f"SMTP error for {delivery_record.delivery_id}: {str(e)}")
        
        except Exception as e:
            # Handle general errors
            attempt.status = DeliveryStatus.FAILED
            attempt.error_message = f"Delivery error: {str(e)}"
            
            logger.error(f"Delivery error for {delivery_record.delivery_id}: {str(e)}")
        
        # Add attempt to record
        delivery_record.add_attempt(attempt)
        
        # Handle failure escalation
        if attempt.status == DeliveryStatus.FAILED:
            with self.thread_lock:
                self.delivery_metrics['total_failed'] += 1
                
                if delivery_record.status == DeliveryStatus.ESCALATED:
                    self.delivery_metrics['total_retries'] += delivery_record.retry_count
                    self._escalate_delivery_failure(delivery_record)
        
        # Create audit log entry
        if self.database_manager:
            self._create_audit_entry(
                AuditAction.EMAIL_PROCESSED,
                delivery_record.delivery_id,
                {
                    'action': 'delivery_attempt',
                    'status': attempt.status.value,
                    'delivery_time_ms': attempt.delivery_time_ms,
                    'smtp_response_code': attempt.smtp_response_code,
                    'error_message': attempt.error_message
                }
            )
    
    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and configure SMTP connection."""
        try:
            if self.smtp_config.use_ssl:
                # Use SSL connection
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(
                    self.smtp_config.host,
                    self.smtp_config.port,
                    context=context,
                    timeout=self.smtp_config.timeout,
                    source_address=self.smtp_config.source_address
                )
            else:
                # Use regular connection with optional TLS
                server = smtplib.SMTP(
                    self.smtp_config.host,
                    self.smtp_config.port,
                    timeout=self.smtp_config.timeout,
                    source_address=self.smtp_config.source_address
                )
                
                if self.smtp_config.use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
            
            # Authenticate if credentials provided
            if self.smtp_config.username and self.smtp_config.password:
                server.login(self.smtp_config.username, self.smtp_config.password)
            
            return server
            
        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {str(e)}")
            raise SMTPConnectionError(f"SMTP connection failed: {str(e)}")
    
    def _analyze_bounce(self, error_message: str) -> Dict[str, Any]:
        """Analyze bounce error message to determine bounce type."""
        error_lower = error_message.lower()
        
        # Hard bounce patterns
        hard_bounce_patterns = [
            r'user unknown',
            r'no such user',
            r'invalid recipient',
            r'recipient address rejected',
            r'mailbox unavailable',
            r'account disabled'
        ]
        
        # Soft bounce patterns
        soft_bounce_patterns = [
            r'mailbox full',
            r'quota exceeded',
            r'temporary failure',
            r'try again later',
            r'service unavailable'
        ]
        
        # Block bounce patterns
        block_bounce_patterns = [
            r'blocked',
            r'blacklisted',
            r'spam',
            r'policy violation',
            r'content rejected'
        ]
        
        # Check patterns
        for pattern in hard_bounce_patterns:
            if re.search(pattern, error_lower):
                return {'type': BounceType.HARD_BOUNCE, 'reason': error_message}
        
        for pattern in soft_bounce_patterns:
            if re.search(pattern, error_lower):
                return {'type': BounceType.SOFT_BOUNCE, 'reason': error_message}
        
        for pattern in block_bounce_patterns:
            if re.search(pattern, error_lower):
                return {'type': BounceType.BLOCK_BOUNCE, 'reason': error_message}
        
        return {'type': BounceType.UNKNOWN, 'reason': error_message}
    
    def _escalate_delivery_failure(self, delivery_record: DeliveryRecord) -> None:
        """Escalate persistent delivery failures."""
        logger.error(
            f"Escalating delivery failure for {delivery_record.delivery_id}: "
            f"{delivery_record.retry_count} attempts failed"
        )
        
        # Create escalation audit entry
        if self.database_manager:
            self._create_audit_entry(
                AuditAction.SYSTEM_ERROR,
                delivery_record.delivery_id,
                {
                    'action': 'delivery_escalated',
                    'recipient': delivery_record.recipient_email,
                    'subject': delivery_record.subject,
                    'retry_count': delivery_record.retry_count,
                    'bounce_type': delivery_record.bounce_type.value if delivery_record.bounce_type else None,
                    'bounce_reason': delivery_record.bounce_reason,
                    'last_error': delivery_record.attempts[-1].error_message if delivery_record.attempts else None
                }
            )
        
        # TODO: Implement additional escalation actions:
        # - Send alert to administrators
        # - Add to dead letter queue
        # - Trigger manual review process
        # - Update recipient blacklist for hard bounces
    
    def _create_audit_entry(self, action: AuditAction, delivery_id: str, details: Dict[str, Any]) -> None:
        """Create audit log entry for delivery events."""
        try:
            if self.database_manager:
                audit_entry = AuditLogEntry(
                    component="delivery_manager",
                    action=action,
                    email_uid=delivery_id,
                    details=details,
                    security_classification="UNCLASSIFIED"
                )
                self.database_manager.create_audit_entry(audit_entry)
        except Exception as e:
            logger.error(f"Failed to create audit entry: {str(e)}")