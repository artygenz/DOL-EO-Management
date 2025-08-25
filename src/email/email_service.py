# src/services/email_service.py
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