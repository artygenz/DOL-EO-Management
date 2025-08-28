"""
Email Webhook Routes

This module handles incoming email webhooks from the IMAP IDLE listener service.
It processes normalized email payloads and triggers appropriate business logic.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json
import base64
from pathlib import Path

# Optional imports for authenticated endpoints
try:
    from src.core.dependencies import get_current_user
    from src.models.user import User
    from src.db.session import get_db
    from sqlalchemy.orm import Session
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["email"])

class EmailAttachmentModel(BaseModel):
    """Email attachment model"""
    filename: str
    content_type: str
    size: int
    data: str  # Base64 encoded
    content_id: Optional[str] = None

class EmailMetadataModel(BaseModel):
    """Email metadata model"""
    message_id: str
    subject: str
    from_email: str
    to_emails: List[str]
    cc_emails: List[str]
    bcc_emails: List[str]
    date: datetime
    received_date: datetime
    size: int
    flags: List[str]
    headers: Dict[str, str]

class EmailWebhookPayload(BaseModel):
    """Complete email webhook payload"""
    id: str
    direction: str
    subject: str
    sender: str
    recipients: List[str]
    body: str
    raw_content: str
    attachments: List[Dict] = Field(default_factory=list)
    timestamp: str
    uid: Optional[int] = None
    message_num: Optional[str] = None

class EmailWebhookResponse(BaseModel):
    """Response model for email webhook"""
    success: bool
    message: str
    email_id: Optional[str] = None
    processing_status: str = "received"

@router.post("/webhook", response_model=EmailWebhookResponse)
async def receive_email_webhook(
    payload: EmailWebhookPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db) if DB_AVAILABLE else None
):
    """
    Receive email webhook from IMAP IDLE listener
    
    This endpoint receives normalized email payloads from the IMAP IDLE listener
    and processes them asynchronously. It handles:
    - Email metadata extraction
    - Attachment processing
    - Business logic routing
    - Database storage
    """
    try:
        print(f"=== WEBHOOK DEBUG: Received email webhook: {payload.subject} ===")
        logger.info(f"Received email webhook: {payload.subject}")
        
        # Use the provided email ID
        email_id = payload.id
        
        # Log the incoming email
        logger.info(f"Processing email ID: {email_id}")
        logger.info(f"From: {payload.sender}")
        logger.info(f"Subject: {payload.subject}")
        logger.info(f"Attachments: {len(payload.attachments)}")
        
        # Add immediate logging
        logger.info(f"=== WEBHOOK RECEIVED ===")
        logger.info(f"Email ID: {email_id}")
        logger.info(f"Subject: {payload.subject}")
        logger.info(f"From: {payload.sender}")
        logger.info(f"To: {payload.recipients}")
        logger.info(f"Attachments: {len(payload.attachments)}")
        logger.info(f"Raw content length: {len(payload.raw_content)}")
        logger.info(f"=== END WEBHOOK DATA ===")
        
        # Add background task for processing
        background_tasks.add_task(
            process_email_async,
            email_id,
            payload,
            db
        )
        
        return EmailWebhookResponse(
            success=True,
            message="Email received and queued for processing",
            email_id=email_id,
            processing_status="queued"
        )
        
    except Exception as e:
        logger.error(f"Error processing email webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process email webhook: {str(e)}"
        )

@router.get("/webhook/health")
async def webhook_health_check():
    """Health check endpoint for the email webhook service"""
    return {
        "status": "healthy",
        "service": "email_webhook",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/webhook/stats")
async def webhook_stats(
    current_user: User = Depends(get_current_user) if DB_AVAILABLE else None,
    db: Session = Depends(get_db) if DB_AVAILABLE else None
):
    """
    Get email webhook processing statistics
    
    Requires authentication and admin privileges
    """
    if not DB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available"
        )
    
    if current_user and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    # TODO: Implement statistics collection
    # This could include:
    # - Total emails processed
    # - Processing success/failure rates
    # - Average processing time
    # - Recent email activity
    
    return {
        "total_emails_processed": 0,
        "success_rate": 0.0,
        "average_processing_time": 0.0,
        "last_email_processed": None,
        "service_status": "active"
    }

async def process_email_async(
    email_id: str,
    payload: EmailWebhookPayload,
    db: Session = None
):
    """
    Asynchronously process email webhook payload
    
    This function handles the actual email processing logic:
    1. Save email to database
    2. Log email details
    """
    try:
        logger.info(f"Starting async processing for email ID: {email_id}")
        
        # Step 1: Save email to database (if available)
        if db:
            await save_email_to_database(email_id, payload, db)
        
        # Step 2: Log email details
        logger.info(f"Email saved successfully: {email_id}")
        logger.info(f"Subject: {payload.subject}")
        logger.info(f"From: {payload.sender}")
        logger.info(f"To: {payload.recipients}")
        logger.info(f"Attachments: {len(payload.attachments)}")
        logger.info(f"Direction: {payload.direction}")
        logger.info(f"Parsed: False (will be processed later)")
        
        logger.info(f"Successfully processed email ID: {email_id}")
        
    except Exception as e:
        logger.error(f"Error in async email processing for {email_id}: {e}")
        # TODO: Implement error handling and retry logic

async def save_email_to_database(
    email_id: str,
    payload: EmailWebhookPayload,
    db: Session = None
):
    """Save email metadata to database"""
    try:
        from src.models.email_log import EmailLog
        from datetime import datetime, timezone
        
        # Create email log entry
        email_log = EmailLog(
            direction=payload.direction,
            subject=payload.subject,
            sender=payload.sender,
            recipients=payload.recipients,
            raw_content=payload.raw_content,
            parsed=False,  # Will be parsed later when we add business logic
            related_eo_id=None  # Will be linked later when we add EO detection
        )
        
        # Add to database
        db.add(email_log)
        db.commit()
        
        logger.info(f"Saved email {email_id} to database")
        
    except Exception as e:
        logger.error(f"Error saving email to database: {e}")
        db.rollback()
        raise

# TODO: Add attachment processing and content routing later
# For now, we just log and save emails to the database
