"""
Email Webhook Routes

This module handles HTTP concerns only - request/response, validation, and routing.
All business logic is delegated to services.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from src.models.email_models import EmailWebhookPayload, EmailWebhookResponse
from src.services.email_intent_service import EmailIntentService
from src.services.email_processing_service import EmailProcessingService

# Optional imports for authenticated endpoints
try:
    from src.db.session import get_db
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["email"])

# Initialize services
intent_service = EmailIntentService()
processing_service = EmailProcessingService()


@router.post("/webhook", response_model=EmailWebhookResponse)
async def receive_email_webhook(
    payload: EmailWebhookPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db) if DB_AVAILABLE else None
):
    """
    Receive email webhook from IMAP IDLE listener
    
    This endpoint handles HTTP concerns only:
    - Request validation
    - Response formatting
    - Error handling
    - Delegation to business services
    """
    try:
        logger.info(f"=== EMAIL WEBHOOK RECEIVED ===")
        logger.info(f"Email ID: {payload.id}")
        logger.info(f"Subject: {payload.subject}")
        logger.info(f"Sender: {payload.sender}")
        logger.info(f"Recipients: {payload.recipients}")
        logger.info(f"Timestamp: {payload.timestamp}")
        logger.info(f"===============================")
        
        # Step 1: Detect email intent (delegate to service)
        intent_result = await intent_service.detect_intent(payload, db)
        logger.info(f"Detected intent: {intent_result.intent} (confidence: {intent_result.confidence})")
        
        # Step 2: Process email based on intent (delegate to service)
        await processing_service.process_email(payload, intent_result, db)
        
        logger.info(f"Successfully processed email {payload.id}")
        
        return EmailWebhookResponse(
            success=True,
            message=f"Email processed successfully with intent: {intent_result.intent}",
            email_id=payload.id,
            processing_status="completed",
            detected_intent=intent_result.intent.value,
            routing_info={
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "extracted_data": intent_result.extracted_data
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing email {payload.id}: {e}")
        return EmailWebhookResponse(
            success=False,
            message=f"Error processing email: {str(e)}",
            email_id=payload.id,
            processing_status="error",
            detected_intent="unknown"
        )


@router.get("/webhook/health")
async def webhook_health_check():
    """
    Health check endpoint for email webhook service
    """
    return {
        "status": "healthy",
        "service": "email_webhook",
        "message": "Email webhook service is running"
    }


@router.get("/webhook/stats")
async def webhook_stats():
    """
    Get webhook processing statistics
    """
    return {
        "service": "email_webhook",
        "status": "operational",
        "services": {
            "intent_detection": "EmailIntentService",
            "email_processing": "EmailProcessingService"
        },
        "message": "All email processing services are available"
    }