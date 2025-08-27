"""
Email attachment processor for handling EO attachments and uploading to S3.
"""

import os
import uuid
from typing import List, Optional, Tuple
from email.message import EmailMessage
from src.email.s3_service import S3Service

def process_email_attachments(email_msg: EmailMessage, bucket_name: Optional[str] = None) -> List[dict]:
    """
    Process email attachments and upload PDFs to S3.
    
    Args:
        email_msg: EmailMessage object
        bucket_name: S3 bucket name (optional)
        
    Returns:
        List[dict]: List of attachment info with S3 keys
    """
    attachments = []
    s3_service = S3Service(bucket_name)
    
    for part in email_msg.walk():
        content_disposition = part.get("Content-Disposition", "")
        
        # Check if this is a PDF attachment
        if (part.get_content_maintype() == "application" and 
            "pdf" in part.get_content_subtype() and
            "attachment" in content_disposition):
            
            filename = part.get_filename()
            if filename and filename.lower().endswith('.pdf'):
                # Generate unique S3 key
                file_id = str(uuid.uuid4())
                s3_key = f"eo-attachments/{file_id}/{filename}"
                
                # Get attachment data
                attachment_data = part.get_payload(decode=True)
                
                # Upload to S3
                success = s3_service.upload_bytes(
                    attachment_data, 
                    s3_key, 
                    content_type="application/pdf"
                )
                
                if success:
                    attachments.append({
                        "filename": filename,
                        "s3_key": s3_key,
                        "content_type": "application/pdf",
                        "size": len(attachment_data)
                    })
                    print(f"Uploaded PDF attachment to S3: {s3_key}")
                else:
                    print(f"Failed to upload PDF attachment: {filename}")
    
    return attachments

def extract_eo_from_attachments(attachments: List[dict], bucket_name: Optional[str] = None) -> Tuple[bool, str]:
    """
    Extract EO text from the first PDF attachment.
    
    Args:
        attachments: List of attachment info from process_email_attachments
        bucket_name: S3 bucket name (optional)
        
    Returns:
        Tuple[bool, str]: (success, extracted_text_or_error_message)
    """
    if not attachments:
        return False, "No attachments found"
    
    # Use the first PDF attachment
    first_attachment = attachments[0]
    s3_key = first_attachment["s3_key"]
    
    try:
        from src.email.s3_service import process_eo_attachment
        return process_eo_attachment(s3_key, bucket_name)
    except Exception as e:
        return False, f"Error processing attachment: {str(e)}"

def create_eo_payload_from_email(
    email_msg: EmailMessage, 
    message_id: str,
    bucket_name: Optional[str] = None
) -> dict:
    """
    Create EO payload from email with attachment processing.
    
    Args:
        email_msg: EmailMessage object
        message_id: Email message ID
        bucket_name: S3 bucket name (optional)
        
    Returns:
        dict: EO payload for the workflow
    """
    from src.workflow.dto import EOIn
    
    # Extract basic email info
    subject = email_msg.get("Subject", "")
    sender = email_msg.get("From", "")
    recipients = email_msg.get("To", "")
    
    # Get email body
    body_text = ""
    if email_msg.is_multipart():
        for part in email_msg.walk():
            if part.get_content_type() == "text/plain":
                body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break
    else:
        body_text = email_msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    
    # Process attachments
    attachments = process_email_attachments(email_msg, bucket_name)
    raw_mime_s3_key = attachments[0]["s3_key"] if attachments else None
    
    # Create EO payload
    eo_payload = {
        "message_id": message_id,
        "subject": subject,
        "sender": sender,
        "recipients": [recipients] if recipients else [],
        "body_text": body_text,
        "raw_mime_s3_key": raw_mime_s3_key
    }
    
    return eo_payload 