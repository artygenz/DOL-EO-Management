"""
Email Webhook Routes

This module handles incoming email webhooks from the IMAP IDLE listener service.
It processes normalized email payloads, detects email intent, and routes to appropriate
business logic handlers for Executive Orders, PMO responses, and task updates.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import logging
import json
import base64
import re
from pathlib import Path
from enum import Enum

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

# Email Intent Types
class EmailIntent(str, Enum):
    EXECUTIVE_ORDER = "executive_order"
    PMO_RESPONSE = "pmo_response"
    TASK_UPDATE = "task_update"
    UNKNOWN = "unknown"

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
    """Complete email webhook payload from IMAP IDLE listener"""
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
    # Enhanced fields from IMAP listener
    message_id: Optional[str] = None
    email_date: Optional[str] = None
    received_date: Optional[str] = None
    content_type: Optional[str] = None
    email_size: Optional[int] = None
    structured_metadata: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None

class EmailWebhookResponse(BaseModel):
    """Response model for email webhook"""
    success: bool
    message: str
    email_id: Optional[str] = None
    processing_status: str = "received"
    detected_intent: Optional[str] = None
    routing_info: Optional[Dict[str, Any]] = None

class EmailProcessingResult(BaseModel):
    """Result of email processing"""
    email_id: str
    intent: EmailIntent
    confidence: float
    extracted_data: Dict[str, Any]
    processing_errors: List[str] = Field(default_factory=list)

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
    - Email intent detection (EO, PMO response, task update, unknown)
    - Email metadata extraction and storage
    - Attachment processing
    - Business logic routing based on intent
    - Database storage with proper relationships
    """
    try:
        logger.info(f"=== EMAIL WEBHOOK RECEIVED ===")
        logger.info(f"Email ID: {payload.id}")
        logger.info(f"Subject: {payload.subject}")
        logger.info(f"From: {payload.sender}")
        logger.info(f"To: {payload.recipients}")
        logger.info(f"Attachments: {len(payload.attachments)}")
        logger.info(f"Raw content length: {len(payload.raw_content)}")
        logger.info(f"Message ID: {payload.message_id}")
        logger.info(f"=== END EMAIL DATA ===")
        
        # Step 1: Detect email intent
        intent_result = await detect_email_intent(payload, db)
        logger.info(f"Detected intent: {intent_result.intent} (confidence: {intent_result.confidence})")
        
        # Step 2: Add background task for comprehensive processing
        background_tasks.add_task(
            process_email_with_intent,
            payload,
            intent_result,
            db
        )
        
        # Step 3: Return immediate response with intent information
        return EmailWebhookResponse(
            success=True,
            message="Email received and queued for processing",
            email_id=payload.id,
            processing_status="queued",
            detected_intent=intent_result.intent.value,
            routing_info={
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "extracted_data": intent_result.extracted_data
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing email webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process email webhook: {str(e)}"
        )

async def detect_email_intent(payload: EmailWebhookPayload, db: Session = None) -> EmailProcessingResult:
    """
    Detect the intent of an incoming email based on sender role and subject patterns.
    
    This function uses a simple and reliable approach:
    - CFO role + EO/Executive Order in subject = Executive Order
    - Reviewer role or PMO email + Re: in subject = PMO Response  
    - Executor role + Task Update/Daily Update in subject = Task Update
    - Everything else = Unknown
    
    Args:
        payload: The email webhook payload
        db: Database session for user lookup
        
    Returns:
        EmailProcessingResult with detected intent and confidence
    """
    try:
        # Initialize result
        result = EmailProcessingResult(
            email_id=payload.id,
            intent=EmailIntent.UNKNOWN,
            confidence=0.0,
            extracted_data={}
        )
        
        # Extract key information for analysis
        subject = payload.subject.lower() if payload.subject else ""
        sender = payload.sender.lower() if payload.sender else ""
        
        # Step 1: Get sender's role from database
        sender_role = None
        sender_user = None
        
        if db and sender:
            try:
                from src.models.user import User
                from sqlalchemy import func
                sender_user = db.query(User).filter(func.lower(User.email) == sender.lower()).first()
                if sender_user:
                    sender_role = sender_user.role
                    logger.info(f"Found sender role: {sender_role} for email: {sender}")
                else:
                    logger.warning(f"No user found for sender email: {sender}")
            except Exception as e:
                logger.error(f"Error looking up sender role: {e}")
        
        # Step 2: Check for Executive Order (CFO role + EO/Executive Order in subject)
        if sender_role == "admin" and ("eo" in subject or "executive order" in subject):
            result.intent = EmailIntent.EXECUTIVE_ORDER
            result.confidence = 0.95
            result.extracted_data = {
                "detection_method": "role_based",
                "sender_role": sender_role,
                "sender_email": sender,
                "subject_patterns": ["eo", "executive order"],
                "analysis": "CFO role detected with EO/Executive Order in subject"
            }
            return result
        
        # Step 3: Check for PMO Response (Reviewer role or PMO email + Re: in subject)
        is_pmo_email = False
        
        # Check if sender is a reviewer
        if sender_role == "reviewer":
            is_pmo_email = True
        
        # Check if sender matches PMO email from environment
        if not is_pmo_email:
            try:
                import os
                pmo_email = os.getenv("PMO_EMAIL_ADDRESS", "").lower()
                if pmo_email and sender == pmo_email:
                    is_pmo_email = True
                    logger.info(f"PMO email match found: {sender}")
            except Exception as e:
                logger.error(f"Error checking PMO email from env: {e}")
        
        # Check for PMO Response patterns: reply, forward, or PMO-related keywords
        pmo_patterns = ["re:", "reply:", "fw:", "forward:", "pmo review", "pmo response"]
        has_pmo_pattern = any(pattern in subject for pattern in pmo_patterns)
        
        if is_pmo_email and has_pmo_pattern:
            result.intent = EmailIntent.PMO_RESPONSE
            result.confidence = 0.90
            result.extracted_data = {
                "detection_method": "role_based",
                "sender_role": sender_role,
                "sender_email": sender,
                "subject_patterns": [pattern for pattern in pmo_patterns if pattern in subject],
                "analysis": "PMO/Reviewer role detected with PMO-related patterns in subject"
            }
            return result
        
        # Step 4: Check for Task Update (Executor role + Task Update/Daily Update in subject)
        task_update_keywords = ["task update", "daily update", "daily task update", "progress update", "status update"]
        has_task_update_keyword = any(keyword in subject for keyword in task_update_keywords)
        
        if sender_role == "executor" and has_task_update_keyword:
            result.intent = EmailIntent.TASK_UPDATE
            result.confidence = 0.85
            result.extracted_data = {
                "detection_method": "role_based",
                "sender_role": sender_role,
                "sender_email": sender,
                "subject_patterns": [kw for kw in task_update_keywords if kw in subject],
                "analysis": "Executor role detected with task update keywords in subject"
            }
            return result
        
        # Step 5: Default to unknown with low confidence
        result.confidence = 0.1
        result.extracted_data = {
            "detection_method": "fallback",
            "sender_role": sender_role,
            "sender_email": sender,
            "subject": subject,
            "analysis_notes": "No clear role-based intent indicators found",
            "possible_reasons": [
                "Sender not found in database",
                "Role doesn't match expected patterns",
                "Subject doesn't contain expected keywords"
            ]
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error detecting email intent: {e}")
        return EmailProcessingResult(
            email_id=payload.id,
            intent=EmailIntent.UNKNOWN,
            confidence=0.0,
            extracted_data={"error": str(e)},
            processing_errors=[f"Intent detection failed: {str(e)}"]
        )

# REMOVED: Old complex intent detection functions - replaced with simple role-based approach

async def process_email_with_intent(
    payload: EmailWebhookPayload,
    intent_result: EmailProcessingResult,
    db: Session = None
):
    """
    Process email based on detected intent.
    
    This function routes the email to appropriate business logic handlers
    based on the detected intent (EO, PMO response, task update, unknown).
    """
    try:
        logger.info(f"Processing email {payload.id} with intent: {intent_result.intent}")
        
        # Step 1: Save email to database
        if db:
            email_log_id = await save_email_to_database(payload, intent_result, db)
            logger.info(f"Saved email to database with ID: {email_log_id}")
        
        # Step 2: Route to appropriate processor based on intent
        if intent_result.intent == EmailIntent.EXECUTIVE_ORDER:
            await process_executive_order(payload, intent_result, db)
        elif intent_result.intent == EmailIntent.PMO_RESPONSE:
            await process_pmo_response(payload, intent_result, db)
        elif intent_result.intent == EmailIntent.TASK_UPDATE:
            # Check if this is a daily update (multiple tasks) or specific task update
            subject = payload.subject.lower() if payload.subject else ""
            
            # Check for specific task update patterns (EO/Task IDs in subject)
            import re
            has_specific_task_pattern = (
                re.search(r'\[EO-[a-f0-9-]+\]', subject) or 
                re.search(r'\[TASK-[a-f0-9-]+\]', subject) or
                re.search(r'EO-[a-f0-9-]+', subject) or
                re.search(r'TASK-[a-f0-9-]+', subject)
            )
            
            # Check for daily update patterns
            has_daily_pattern = any(keyword in subject for keyword in ["daily update", "daily task update"])
            
            if has_specific_task_pattern:
                # Specific task update with EO/Task IDs
                await process_task_update(payload, intent_result, db)
            elif has_daily_pattern or "task update" in subject:
                # Daily task update (general update about multiple tasks)
                await process_daily_task_update(payload, intent_result, db)
            else:
                # Default to daily task update for executor role
                await process_daily_task_update(payload, intent_result, db)
        else:
            await process_unknown_email(payload, intent_result, db)
        
        logger.info(f"Successfully processed email {payload.id}")
        
    except Exception as e:
        logger.error(f"Error processing email {payload.id}: {e}")
        # TODO: Implement error handling and retry logic

async def process_executive_order(
    payload: EmailWebhookPayload,
    intent_result: EmailProcessingResult,
    db: Session = None
):
    """Process Executive Order email - works exactly like /app/workflow/eo endpoint"""
    try:
        logger.info(f"Processing Executive Order: {payload.subject}")
        
        # Convert to EOIn format for existing workflow (exactly like /app/workflow/eo)
        from src.workflow.dto import EOIn
        
        eo_data = EOIn(
            message_id=payload.message_id or payload.id,
            subject=payload.subject,
            sender=payload.sender,
            recipients=payload.recipients,
            received_at=datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00')) if payload.timestamp else None,
            body_text=payload.raw_content,
            raw_mime_s3_key=None  # TODO: Implement S3 storage if needed
        )
        
        # Queue EO for processing using the same Celery task as /app/workflow/eo
        from src.workflow.tasks import store_email
        
        try:
            # This is exactly what /app/workflow/eo does
            store_email.delay(eo_data.model_dump())
            logger.info(f"Executive Order queued for processing: {eo_data.message_id}")
        except Exception as e:
            logger.error(f"Failed to queue EO for processing: {e}")
            raise HTTPException(status_code=500, detail="Failed to queue EO for processing")
        
        logger.info(f"Executive Order queued successfully: {eo_data.message_id}")
        
    except Exception as e:
        logger.error(f"Error processing Executive Order: {e}")
        raise

async def process_pmo_response(
    payload: EmailWebhookPayload,
    intent_result: EmailProcessingResult,
    db: Session = None
):
    """Process PMO response email - works exactly like /app/webhook/pmo_email endpoint"""
    try:
        logger.info(f"Processing PMO response: {payload.subject}")
        
        # Convert to PMOEmailIn format for existing workflow (exactly like /app/webhook/pmo_email)
        from src.workflow.dto import PMOEmailIn
        from src.workflow.parse_pmo import extract_eo_id_from_subject
        
        # Extract EO ID from subject if not provided (same logic as /app/webhook/pmo_email)
        related_eo_id = extract_eo_id_from_subject(payload.subject)
        
        # Validate EO exists before processing (same validation as /app/webhook/pmo_email)
        if related_eo_id:
            from src.workflow import repository as repo
            eo = repo.get_executive_order(related_eo_id)
            if not eo:
                error_msg = f"EO with ID '{related_eo_id}' not found in database. Please check the EO ID and try again."
                logger.error(f"ERROR: {error_msg}")
                raise HTTPException(
                    status_code=404, 
                    detail={
                        "error": "EO not found",
                        "message": error_msg,
                        "eo_id": related_eo_id
                    }
                )
            logger.info(f"Validated EO exists: {related_eo_id} - {eo.title}")
        else:
            error_msg = "No EO ID found in PMO email subject. Cannot process PMO response."
            logger.error(f"ERROR: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Missing EO ID",
                    "message": error_msg
                }
            )
        
        # Persist inbound PMO email for audit (same as /app/webhook/pmo_email)
        email_log_id = None
        try:
            from src.workflow import repository as repo
            email_log = repo.save_email_log(
                direction="incoming",
                subject=payload.subject,
                sender=payload.sender,
                recipients=payload.recipients,
                raw_content=payload.raw_content,
                related_eo_id=related_eo_id,
            )
            email_log_id = str(email_log.id)
            logger.info(f"Saved PMO email log with ID: {email_log_id}")
        except Exception as e:
            logger.warning(f"Could not save PMO email log: {e}")
            # Non-fatal: still try to process
        
        # Create PMOEmailIn payload (same format as /app/webhook/pmo_email)
        pmo_email_data = PMOEmailIn(
            message_id=payload.message_id or payload.id,
            subject=payload.subject,
            sender=payload.sender,
            recipients=payload.recipients,
            received_at=datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00')) if payload.timestamp else None,
            body_text=payload.raw_content,
            related_eo_id=related_eo_id
        )
        
        # Add email log ID to the payload for organized file structure (same as /app/webhook/pmo_email)
        email_payload = pmo_email_data.model_dump()
        email_payload["email_log_id"] = email_log_id
        email_payload["related_eo_id"] = related_eo_id  # Ensure EO ID is set
        
        # Queue PMO response for processing using the same Celery task as /app/webhook/pmo_email
        from src.workflow.tasks import process_pmo_response
        
        try:
            # This is exactly what /app/webhook/pmo_email does
            process_pmo_response.delay(email_payload)
            logger.info(f"PMO response queued for processing: {pmo_email_data.message_id}")
        except Exception as e:
            logger.error(f"Failed to queue PMO email for processing: {e}")
            raise HTTPException(status_code=500, detail="Failed to queue PMO email for processing")
        
        logger.info(f"PMO response queued successfully: {pmo_email_data.message_id}")
        
    except Exception as e:
        logger.error(f"Error processing PMO response: {e}")
        raise

async def process_task_update(
    payload: EmailWebhookPayload,
    intent_result: EmailProcessingResult,
    db: Session = None
):
    """Process task update email - uses AI to extract structured updates and create daily updates"""
    try:
        logger.info(f"Processing task update: {payload.subject}")
        
        # Step 1: Extract task information from subject (e.g., [EO-xxx][TASK-yyy])
        from src.workflow.parse_pmo import extract_eo_id_from_subject
        import re
        
        # Extract EO ID and Task ID from subject
        eo_id = extract_eo_id_from_subject(payload.subject)
        task_id_match = re.search(r'\[TASK-([a-f0-9-]+)\]', payload.subject)
        task_id = task_id_match.group(1) if task_id_match else None
        
        if not eo_id or not task_id:
            error_msg = f"Could not extract EO ID or Task ID from subject: {payload.subject}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Missing EO/Task ID",
                    "message": error_msg
                }
            )
        
        # Step 2: Validate EO and Task exist
        from src.workflow import repository as repo
        eo = repo.get_executive_order(eo_id)
        if not eo:
            error_msg = f"EO with ID '{eo_id}' not found in database."
            logger.error(error_msg)
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "EO not found",
                    "message": error_msg,
                    "eo_id": eo_id
                }
            )
        
        # Get task details
        from src.models.task import Task
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            error_msg = f"Task with ID '{task_id}' not found in database."
            logger.error(error_msg)
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Task not found",
                    "message": error_msg,
                    "task_id": task_id
                }
            )
        
        logger.info(f"Validated EO: {eo_id} and Task: {task_id}")
        
        # Step 3: Save email log
        email_log_id = None
        try:
            email_log = repo.save_email_log(
                direction="incoming",
                subject=payload.subject,
                sender=payload.sender,
                recipients=payload.recipients,
                raw_content=payload.raw_content,
                related_eo_id=eo_id,
            )
            email_log_id = str(email_log.id)
            logger.info(f"Saved task update email log with ID: {email_log_id}")
        except Exception as e:
            logger.warning(f"Could not save task update email log: {e}")
        
        # Step 4: Use AI to extract structured task update from email
        from src.app.rewire_tasks import generate_task_update_from_update_email
        
        # Get employee role (for now, use a default or extract from sender)
        employee_role = "Employee"  # TODO: Extract from user database based on sender email
        
        # Convert task to dict format expected by AI function
        task_dict = {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "category": task.category
        }
        
        try:
            # Extract structured task update using AI
            structured_update = generate_task_update_from_update_email(
                employee_role=employee_role,
                raw_update=payload.raw_content,
                task=task_dict
            )
            
            logger.info(f"AI extracted structured update: {structured_update}")
            
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            # Fallback: create basic update from raw content
            structured_update = {
                "update_text": payload.raw_content,
                "progress_pct": None,
                "hours_spent": None,
                "status_note": "Update received via email",
                "blockers": None,
                "risks": None,
                "next_actions": None
            }
        
        # Step 5: Create daily update using existing logic
        from src.models.daily_update import DailyUpdate
        from src.models.user import User
        
        # Find user by email (sender)
        from sqlalchemy import func
        user = db.query(User).filter(func.lower(User.email) == payload.sender.lower()).first()
        if not user:
            logger.warning(f"User not found for email: {payload.sender}")
            # For now, skip creating daily update if user not found
            # TODO: Create user or use default user
            return
        
        # Create daily update
        daily_update = DailyUpdate(
            task_id=task_id,
            user_id=str(user.id),
            update_text=structured_update.get("update_text", payload.raw_content),
            progress_pct=structured_update.get("progress_pct"),
            hours_spent=structured_update.get("hours_spent"),
            status_note=structured_update.get("status_note"),
            blockers=structured_update.get("blockers"),
            risks=structured_update.get("risks"),
            next_actions=structured_update.get("next_actions")
        )
        
        db.add(daily_update)
        db.commit()
        db.refresh(daily_update)
        
        logger.info(f"Created daily update with ID: {daily_update.id}")
        
        # Step 6: Update task status if provided in structured update
        if structured_update.get("status"):
            task.status = structured_update["status"]
            db.commit()
            logger.info(f"Updated task status to: {structured_update['status']}")
        
        logger.info(f"Task update processed successfully: EO={eo_id}, Task={task_id}, Update={daily_update.id}")
        
    except Exception as e:
        logger.error(f"Error processing task update: {e}")
        if db:
            db.rollback()
        raise

async def process_daily_task_update(
    payload: EmailWebhookPayload,
    intent_result: EmailProcessingResult,
    db: Session = None
):
    """Process daily task update email - uses AI to extract updates for all user's tasks"""
    try:
        logger.info(f"Processing daily task update: {payload.subject}")
        
        # Convert to DailyUpdateEmailPayload format for Celery task
        from src.workflow.dto import DailyUpdateEmailPayload
        from datetime import datetime
        
        daily_update_data = DailyUpdateEmailPayload(
            message_id=payload.message_id or payload.id,
            subject=payload.subject,
            sender=payload.sender,
            recipients=payload.recipients,
            body_text=payload.raw_content,
            body_html=payload.raw_content,  # For now, use same as text
            received_at=datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00')) if payload.timestamp else datetime.now(),
            raw_mime_s3_key=None
        )
        
        # Queue daily update for processing using Celery task
        from src.workflow.tasks import process_daily_update_email
        
        try:
            process_daily_update_email.delay(daily_update_data.model_dump())
            logger.info(f"Daily task update queued for processing: {daily_update_data.message_id}")
        except Exception as e:
            logger.error(f"Failed to queue daily update for processing: {e}")
            raise HTTPException(status_code=500, detail="Failed to queue daily update for processing")
        
        logger.info(f"Daily task update queued successfully: {daily_update_data.message_id}")
        
    except Exception as e:
        logger.error(f"Error processing daily task update: {e}")
        raise

async def process_unknown_email(
    payload: EmailWebhookPayload,
    intent_result: EmailProcessingResult,
    db: Session = None
):
    """Process unknown email type"""
    try:
        logger.info(f"Processing unknown email type: {payload.subject}")
        
        # For unknown emails, we just log them and store in database
        # They can be manually reviewed later
        
        logger.info(f"Unknown email logged for manual review")
        
    except Exception as e:
        logger.error(f"Error processing unknown email: {e}")
        raise

async def save_email_to_database(
    payload: EmailWebhookPayload,
    intent_result: EmailProcessingResult,
    db: Session = None
) -> str:
    """Save email metadata to database with intent information"""
    try:
        from src.models.email_log import EmailLog
        from datetime import datetime, timezone
        import uuid
        
        # Create email log entry with enhanced information
        email_log = EmailLog(
            direction=payload.direction,
            subject=payload.subject,
            sender=payload.sender,
            recipients=payload.recipients,
            raw_content=payload.raw_content,
            parsed=True,  # Mark as parsed since we detected intent
            related_eo_id=None  # Will be linked later if it's an EO
        )
        
        # Add to database
        db.add(email_log)
        db.commit()
        db.refresh(email_log)
        
        logger.info(f"Saved email {payload.id} to database with ID: {email_log.id}")
        return str(email_log.id)
        
    except Exception as e:
        logger.error(f"Error saving email to database: {e}")
        if db:
            db.rollback()
        raise

@router.get("/webhook/health")
async def webhook_health_check():
    """Health check endpoint for the email webhook service"""
    return {
        "status": "healthy",
        "service": "email_webhook",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "intent_detection",
            "email_processing",
            "business_logic_routing"
        ]
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
    # - Intent detection accuracy
    # - Processing success/failure rates
    # - Average processing time
    # - Recent email activity by intent type
    
    return {
        "total_emails_processed": 0,
        "intent_distribution": {
            "executive_order": 0,
            "pmo_response": 0,
            "task_update": 0,
            "unknown": 0
        },
        "success_rate": 0.0,
        "average_processing_time": 0.0,
        "last_email_processed": None,
        "service_status": "active"
    }
