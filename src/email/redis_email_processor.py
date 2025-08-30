"""
Redis Email Processor

This module processes emails from the Redis queue and sends them via SMTP.
Only runs in the main worker process to prevent concurrent SMTP connections.
"""

import logging
import os
import time
import threading
from typing import Optional
from src.email.redis_email_queue import get_redis_email_queue, RedisEmailRequest
from src.email.queue_logger import EmailQueueLogger
# EmailService removed - using Redis queue only
from dataclasses import dataclass

@dataclass
class Attachment:
    filename: str
    content_type: str
    data: bytes

logger = logging.getLogger(__name__)

class RedisEmailProcessor:
    """
    Processes emails from Redis queue with single SMTP connection
    """
    
    def __init__(self):
        self.queue = get_redis_email_queue()
        self.running = False
        self.base_delay = 10.0  # 10 seconds between emails (increased for GoDaddy)
        self.max_delay = 300.0  # 5 minutes max delay
        self.smtp_retry_delay = 60.0  # 1 minute delay after SMTP rate limit
    
    def start(self):
        """Start the email processor"""
        if self.running:
            logger.warning("Redis email processor is already running")
            return
        
        self.running = True
        logger.info("Redis email processor started")
        
        while self.running:
            try:
                # Get next email from Redis queue
                email_request = self.queue.get_next_email()
                
                if email_request is None:
                    # No emails in queue, wait a bit
                    time.sleep(1)
                    continue
                
                # Log processing start
                EmailQueueLogger.log_email_processing_start(
                    email_id=email_request.id,
                    processor_worker="redis_email_processor"
                )
                
                # Process the email
                success = self._process_email(email_request)
                
                if success:
                    # Mark as completed
                    self.queue.mark_email_completed(email_request.id)
                    logger.info(f"Email processed successfully: {email_request.id}")
                else:
                    # Re-queue for retry
                    self.queue.requeue_email(email_request)
                    logger.warning(f"Email processing failed, re-queued: {email_request.id}")
                    
                    # Log retry
                    EmailQueueLogger.log_email_retry(
                        email_id=email_request.id,
                        retry_count=email_request.retry_count + 1,
                        error_message="Processing failed, retrying"
                    )
                
                # Add delay between emails to prevent rate limiting
                delay = self.base_delay + (email_request.retry_count * 2)  # Increase delay with retries
                delay = min(delay, self.max_delay)
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error in Redis email processor: {e}")
                time.sleep(5)  # Wait before retrying
    
    def stop(self):
        """Stop the email processor"""
        self.running = False
        logger.info("Redis email processor stopped")
    
    def _process_email(self, email_request: RedisEmailRequest) -> bool:
        """
        Process a single email request
        
        Returns:
            True if successful, False if should be retried
        """
        try:
            # Convert hex-encoded attachment data back to bytes
            attachments = None
            if email_request.attachments:
                attachments = []
                for att in email_request.attachments:
                    if 'data' in att and isinstance(att['data'], str):
                        # Convert hex string back to bytes
                        att_data = bytes.fromhex(att['data'])
                    else:
                        att_data = att.get('data', b'')
                    
                    attachments.append(Attachment(
                        filename=att['filename'],
                        content_type=att['content_type'],
                        data=att_data
                    ))
            
            # Save to outbox first (always succeeds)
            message_id = self._save_to_outbox(
                to=email_request.to,
                subject=email_request.subject,
                body_text=email_request.body_text,
                body_html=email_request.body_html,
                attachments=attachments,
                headers=email_request.headers,
                email_log_id=email_request.email_log_id,
                email_type=email_request.email_type
            )
            
            # Then try SMTP with single attempt
            try:
                self._send_via_smtp_single(
                    to=email_request.to,
                    subject=email_request.subject,
                    body_text=email_request.body_text,
                    body_html=email_request.body_html,
                    attachments=attachments,
                    headers=email_request.headers
                )
                logger.info(f"Email sent via SMTP and saved to outbox: {message_id}")
                
                # Log success
                EmailQueueLogger.log_email_sent_success(
                    email_id=email_request.id,
                    smtp_host=os.getenv('SMTP_HOST', 'lumenlighthouse.ai'),
                    smtp_response_code=250,
                    smtp_response_message="OK",
                    outbox_saved=True,
                    outbox_path=f"outbox/{email_request.email_type}/{message_id}"
                )
                
                return True
                
            except Exception as smtp_e:
                # Check if it's a rate limiting error
                error_str = str(smtp_e)
                is_rate_limited = '421' in error_str or 'rate limit' in error_str.lower() or 'too many' in error_str.lower()
                
                # Log failure
                EmailQueueLogger.log_email_failed(
                    email_id=email_request.id,
                    error_message=str(smtp_e),
                    smtp_host=os.getenv('SMTP_HOST', 'lumenlighthouse.ai'),
                    smtp_response_code=421 if is_rate_limited else None,
                    smtp_response_message=str(smtp_e),
                    is_rate_limited=is_rate_limited,
                    retry_count=email_request.retry_count,
                    outbox_saved=True,
                    outbox_path=f"outbox/{email_request.email_type}/{message_id}"
                )
                
                if is_rate_limited:
                    logger.warning(f"SMTP rate limited for {email_request.id}: {smtp_e}")
                    logger.info(f"Applying SMTP retry delay of {self.smtp_retry_delay} seconds")
                    time.sleep(self.smtp_retry_delay)  # Wait before allowing retry
                    return False  # Retry
                else:
                    # Other SMTP errors - consider success since saved to outbox
                    logger.warning(f"SMTP failed for {email_request.id}, but saved to outbox: {smtp_e}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error processing email {email_request.id}: {e}")
            return False
    
    def _send_via_smtp_single(self, to, subject, body_text, body_html=None, attachments=None, headers=None):
        """Send email via SMTP with single attempt"""
        import smtplib
        import ssl
        import os
        from email.message import EmailMessage
        
        # Get SMTP settings
        smtp_host = os.getenv('SMTP_HOST', 'lumenlighthouse.ai')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        username = os.getenv('EMAIL_USER')
        password = os.getenv('EMAIL_PASS')
        
        # Create email message
        msg = EmailMessage()
        msg['From'] = username
        msg['To'] = ', '.join(to)
        msg['Subject'] = subject
        
        # Set content
        if body_html:
            msg.set_content(body_text)
            msg.add_alternative(body_html, subtype='html')
        else:
            msg.set_content(body_text)
        
        # Add attachments
        if attachments:
            for attachment in attachments:
                filename = attachment.filename
                content_type = attachment.content_type
                data = attachment.data
                
                # Parse content type
                if '/' in content_type:
                    maintype, subtype = content_type.split('/', 1)
                else:
                    maintype, subtype = 'application', 'octet-stream'
                
                msg.add_attachment(
                    data, 
                    maintype=maintype, 
                    subtype=subtype, 
                    filename=filename
                )
        
        # Send email (single attempt)
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.starttls(context=context)
            smtp.login(username, password)
            smtp.send_message(msg)
        
        logger.info(f"SMTP send successful to: {', '.join(to)}")
    
    def _save_to_outbox(self, to, subject, body_text, body_html=None, attachments=None, headers=None, email_log_id=None, email_type="general"):
        """Save email to outbox directory for backup"""
        import json
        import pathlib
        import uuid
        from datetime import datetime, timezone
        
        out_dir = os.getenv("OUTBOX_DIR", "/tmp/outbox")
        pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate unique message ID
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Create outbox subdirectory for this email type
        type_dir = pathlib.Path(out_dir) / email_type
        type_dir.mkdir(exist_ok=True)
        
        # Create email-specific directory
        email_dir = type_dir / message_id
        email_dir.mkdir(exist_ok=True)
        
        # Save email metadata and content
        email_data = {
            "message_id": message_id,
            "timestamp": timestamp,
            "to": to,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "headers": headers or {},
            "email_log_id": email_log_id,
            "email_type": email_type,
            "attachments": []
        }
        
        # Save email content
        (email_dir / "email.json").write_text(json.dumps(email_data, indent=2))
        (email_dir / "body.txt").write_text(body_text)
        if body_html:
            (email_dir / "body.html").write_text(body_html)
        
        # Save attachments
        if attachments:
            att_dir = email_dir / "attachments"
            att_dir.mkdir(exist_ok=True)
            
            for i, attachment in enumerate(attachments):
                filename = attachment.filename
                att_path = att_dir / filename
                att_path.write_bytes(attachment.data)
                
                email_data["attachments"].append({
                    "filename": filename,
                    "content_type": attachment.content_type,
                    "path": str(att_path.relative_to(email_dir))
                })
        
        # Update email.json with attachment info
        (email_dir / "email.json").write_text(json.dumps(email_data, indent=2))
        
        logger.info(f"Email saved to outbox: {message_id}")
        return message_id


# Global processor instance
_email_processor: Optional[RedisEmailProcessor] = None

def start_redis_email_processor():
    """Start the Redis email processor"""
    global _email_processor
    
    if _email_processor and _email_processor.running:
        logger.warning("Redis email processor is already running")
        return
    
    _email_processor = RedisEmailProcessor()
    _email_processor.start()

def stop_redis_email_processor():
    """Stop the Redis email processor"""
    global _email_processor
    
    if _email_processor:
        _email_processor.stop()
        _email_processor = None
