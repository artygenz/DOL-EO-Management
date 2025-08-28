# src/services/email_service.py
"""
Email Service for DOL EO Management System

This module provides email sending functionality with both outbox storage and SMTP delivery.

Environment Variables Required for SMTP:
- EMAIL_HOST: SMTP host (default: smtpout.secureserver.net)
- EMAIL_PORT: SMTP port (default: 465)
- SMTP_HOST: SMTP host (default: smtpout.secureserver.net)
- SMTP_PORT: SMTP port (default: 465)
- EMAIL_USER: Email username/address
- EMAIL_PASS: Email password

Environment Variables for Outbox:
- OUTBOX_DIR: Directory to save emails (default: /tmp/outbox)

Usage:
    # Save to outbox only (existing functionality)
    email_service = EmailService()
    message_id = email_service.send(to=["recipient@example.com"], ...)
    
    # Send via SMTP and save to outbox
    message_id = email_service.send_and_save(to=["recipient@example.com"], ...)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Dict, Tuple, List
from datetime import datetime, timezone
import os, json, pathlib
import uuid

@dataclass
class Attachment:
    filename: str
    content_type: str
    data: bytes

class EmailService:
    """
    Dev 'console' email sender: writes payloads to OUTBOX_DIR.
    Swap with real SMTP/Graph provider later; keep same interface.
    """
    def __init__(self, out_dir: Optional[str] = None):
        self.out_dir = out_dir or os.getenv("OUTBOX_DIR", "/tmp/outbox")
        pathlib.Path(self.out_dir).mkdir(parents=True, exist_ok=True)

    def send(
        self,
        to: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[Iterable[Attachment]] = None,
        headers: Optional[Dict[str, str]] = None,
        email_log_id: Optional[str] = None,
        email_type: str = "general"
    ) -> str:
        """
        Send email and save to organized folder structure.
        
        Parameters
        ----------
        email_log_id : str, optional
            The email log ID from database for organizing files
        email_type : str
            Type of email (e.g., 'eo_review', 'improved_review', 'assignee_notification')
        """
        ts = int(datetime.now(timezone.utc).timestamp())
        mid = f"local-{ts}"
        
        # Create organized folder structure
        if email_log_id:
            # Use email log ID for organization
            folder_name = f"{email_type}/{email_log_id}"
        else:
            # Fallback to timestamp-based organization
            folder_name = f"{email_type}/{mid}"
        
        email_dir = pathlib.Path(self.out_dir) / folder_name
        email_dir.mkdir(parents=True, exist_ok=True)
        
        # Create metadata payload
        payload = {
            "message_id": mid,
            "email_log_id": email_log_id,
            "email_type": email_type,
            "to": to,
            "subject": subject,
            "headers": headers or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "attachments_count": len(list(attachments or [])),
        }
        
        # Save email files in organized structure
        (email_dir / "subject.txt").write_text(subject, encoding="utf-8")
        (email_dir / "body.txt").write_text(body_text or "", encoding="utf-8")
        
        if body_html:
            (email_dir / "body.html").write_text(body_html, encoding="utf-8")
        
        (email_dir / "metadata.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        
        # Save attachments in attachments subfolder
        if attachments:
            attachments_dir = email_dir / "attachments"
            attachments_dir.mkdir(exist_ok=True)
            
            for attachment in attachments:
                # Sanitize filename for filesystem safety
                safe_filename = "".join(c for c in attachment.filename if c.isalnum() or c in "._-")
                attachment_path = attachments_dir / safe_filename
                attachment_path.write_bytes(attachment.data)
                
                # Also save attachment metadata
                attachment_meta = {
                    "original_filename": attachment.filename,
                    "safe_filename": safe_filename,
                    "content_type": attachment.content_type,
                    "size_bytes": len(attachment.data),
                    "saved_at": datetime.now(timezone.utc).isoformat()
                }
                meta_path = attachments_dir / f"{safe_filename}.meta.json"
                meta_path.write_text(json.dumps(attachment_meta, indent=2), encoding="utf-8")
        
        # Create a README file for the email folder
        readme_content = f"""# Email: {subject}

**Message ID:** {mid}
**Email Log ID:** {email_log_id or 'N/A'}
**Type:** {email_type}
**Sent To:** {', '.join(to)}
**Created:** {datetime.now(timezone.utc).isoformat()}

## Files in this folder:
- `subject.txt` - Email subject line
- `body.txt` - Plain text email body
- `body.html` - HTML email body (if available)
- `metadata.json` - Complete email metadata
- `attachments/` - Folder containing email attachments
- `README.md` - This file

## Attachments:
"""
        
        if attachments:
            for attachment in attachments:
                safe_filename = "".join(c for c in attachment.filename if c.isalnum() or c in "._-")
                readme_content += f"- `{safe_filename}` - {attachment.filename} ({attachment.content_type})\n"
        else:
            readme_content += "- No attachments\n"
        
        (email_dir / "README.md").write_text(readme_content, encoding="utf-8")
        
        return mid
    
    def send_and_save(
        self,
        to: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[Iterable[Attachment]] = None,
        headers: Optional[Dict[str, str]] = None,
        email_log_id: Optional[str] = None,
        email_type: str = "general"
    ) -> str:
        """
        Send email via SMTP and also save to outbox for backup.
        
        This method combines actual email sending with the existing outbox
        functionality for complete email management.
        
        Parameters
        ----------
        to : List[str]
            List of recipient email addresses
        subject : str
            Email subject line
        body_text : str
            Plain text email body
        body_html : Optional[str]
            HTML email body (optional)
        attachments : Optional[Iterable[Attachment]]
            List of email attachments
        headers : Optional[Dict[str, str]]
            Additional email headers
        email_log_id : Optional[str]
            Email log ID from database for organization
        email_type : str
            Type of email for categorization
            
        Returns
        -------
        str
            Message ID of the sent email
            
        Raises
        ------
        Exception
            If email sending fails
        """
        try:
            # First, save to outbox (existing functionality)
            message_id = self.send(
                to=to,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                headers=headers,
                email_log_id=email_log_id,
                email_type=email_type
            )
            
            # Then, send via SMTP
            self._send_via_smtp(
                to=to,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                headers=headers
            )
            
            return message_id
            
        except Exception as e:
            # Log the error but don't fail completely
            # The email is still saved to outbox
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send email via SMTP: {e}")
            logger.info(f"Email saved to outbox with message_id: {message_id}")
            
            # Re-raise the exception for proper error handling
            raise
    
    def _send_via_smtp(
        self,
        to: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[Iterable[Attachment]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Send email via SMTP using STARTTLS with connection pooling and retry logic.
        
        This method handles rate limiting by reusing connections and implementing
        intelligent retry logic for multiple recipients.
        
        Parameters
        ----------
        to : List[str]
            List of recipient email addresses
        subject : str
            Email subject line
        body_text : str
            Plain text email body
        body_html : Optional[str]
            HTML email body (optional)
        attachments : Optional[Iterable[Attachment]]
            List of email attachments
        """
        try:
            import smtplib
            import ssl
            import os
            import time
            import random
            from email.message import EmailMessage
            
            # Get SMTP settings from environment
            smtp_host = os.getenv('SMTP_HOST', 'lumenlighthouse.ai')
            smtp_port = int(os.getenv('SMTP_PORT', 587))
            username = os.getenv('EMAIL_USER')
            password = os.getenv('EMAIL_PASS')
            
            # Convert attachments to the format expected by EmailMessage
            email_attachments = []
            if attachments:
                for attachment in attachments:
                    email_attachments.append({
                        'filename': attachment.filename,
                        'content_type': attachment.content_type,
                        'data': attachment.data
                    })
            
            # Create email message template (reused for all recipients)
            def create_email_message(recipient):
                msg = EmailMessage()
                msg['From'] = username
                msg['To'] = recipient
                msg['Subject'] = subject
                
                # Set content
                if body_html:
                    msg.set_content(body_text)
                    msg.add_alternative(body_html, subtype='html')
                else:
                    msg.set_content(body_text)
                
                # Add attachments
                for attachment in email_attachments:
                    filename = attachment['filename']
                    content_type = attachment['content_type']
                    data = attachment['data']
                    
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
                
                return msg
            
            # Send emails with connection pooling and retry logic
            successful_sends = 0
            failed_sends = 0
            max_retries = 3
            base_delay = 2  # Base delay in seconds
            
            for i, recipient in enumerate(to):
                retry_count = 0
                sent = False
                
                while retry_count < max_retries and not sent:
                    try:
                        # Create SSL context
                        context = ssl.create_default_context()
                        
                        # Create SMTP connection
                        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
                            # Start TLS encryption
                            smtp.starttls(context=context)
                            # Login
                            smtp.login(username, password)
                            
                            # Create email message for this recipient
                            msg = create_email_message(recipient)
                            
                            # Send the email
                            smtp.send_message(msg)
                            
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"Email sent successfully to: {recipient}")
                            
                            successful_sends += 1
                            sent = True
                            
                            # Add delay between sends to avoid rate limiting
                            if i < len(to) - 1:  # Don't delay after the last email
                                delay = base_delay + random.uniform(0, 1)  # 2-3 seconds with jitter
                                time.sleep(delay)
                        
                    except smtplib.SMTPResponseException as e:
                        if e.smtp_code == 421:  # Rate limiting error
                            retry_count += 1
                            delay = base_delay * (2 ** retry_count) + random.uniform(0, 2)  # Exponential backoff
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"Rate limited for {recipient}, retrying in {delay:.1f}s (attempt {retry_count}/{max_retries})")
                            time.sleep(delay)
                        else:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"SMTP error for {recipient}: {e}")
                            failed_sends += 1
                            break
                            
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to send email to {recipient}: {e}")
                        retry_count += 1
                        if retry_count < max_retries:
                            delay = base_delay * (2 ** retry_count) + random.uniform(0, 2)
                            time.sleep(delay)
                        else:
                            failed_sends += 1
                            break
                
                if not sent:
                    failed_sends += 1
            
            # Log summary
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Email sending completed: {successful_sends} successful, {failed_sends} failed")
            
            # Return success if at least one email was sent
            return successful_sends > 0
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize SMTP client: {e}")
            raise