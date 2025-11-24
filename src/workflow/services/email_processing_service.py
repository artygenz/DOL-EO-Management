"""
Email Processing Service

Extracts business logic from store_email task for better separation of concerns.
"""

from typing import Dict, Optional
from src.workflow.dto import EOIn
from src.workflow import repository as repo


class EmailProcessingService:
    """Service for processing EO emails - extracts business logic from tasks.py"""
    
    def __init__(self):
        # Keep existing external services as-is
        pass
    
    def process_eo_email(self, eo_payload: Dict) -> Dict:
        """
        Business logic extracted from store_email task
        
        Args:
            eo_payload: Email payload dictionary
            
        Returns:
            Dict containing eo_id, email_log_id, and processed_text
        """
        print(f"\n=== EO Processing Started ===")
        print(f"Subject: {eo_payload.get('subject', 'N/A')}")
        print(f"Sender: {eo_payload.get('sender', 'N/A')}")
        print(f"Message ID: {eo_payload.get('message_id', 'N/A')}")
        print(f"================================\n")
        
        eo = EOIn(**eo_payload)
        
        # 1. Log inbound email
        email_log_id = self._log_incoming_email(eo)
        
        # 2. Process S3 attachment if available
        eo_text = self._process_attachments(eo)
        
        # 3. Store EO and update status
        eo_row = repo.upsert_executive_order(eo)
        repo.update_eo_status(eo_row.id, "received")
        
        return {
            "eo_id": str(eo_row.id), 
            "email_log_id": email_log_id,
            "processed_text": eo_text,
            "next_step": "ai_extract_tasks"
        }
    
    def _log_incoming_email(self, eo: EOIn) -> Optional[str]:
        """Extract email logging logic"""
        try:
            email_log = repo.save_email_log(
                direction="incoming",
                subject=eo.subject,
                sender=eo.sender,
                recipients=eo.recipients,
                raw_content=eo.body_text,
                related_eo_id=None,
            )
            email_log_id = str(email_log.id)
            print(f"Email logged with ID: {email_log_id}")
            return email_log_id
        except Exception as e:
            print(f"Warning: Could not save email log: {e}")
            return None
    
    def _process_attachments(self, eo: EOIn) -> str:
        """Extract S3 attachment processing logic"""
        eo_text = eo.body_text
        if eo.raw_mime_s3_key:
            print(f"Processing S3 attachment: {eo.raw_mime_s3_key}")
            try:
                from src.email.s3_service import process_eo_attachment
                success, result = process_eo_attachment(eo.raw_mime_s3_key)
                
                if success:
                    eo_text = result
                    print(f"Successfully extracted text from S3 attachment: {len(eo_text)} characters")
                else:
                    print(f"Failed to process S3 attachment: {result}")
            except Exception as e:
                print(f"Error processing S3 attachment: {e}")
        
        return eo_text
