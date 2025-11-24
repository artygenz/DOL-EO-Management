"""
Email Processing Service

This service handles email processing for different email types.
Business logic separated from HTTP concerns.
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from src.models.email_models import EmailWebhookPayload, EmailProcessingResult, EmailIntent

logger = logging.getLogger(__name__)


class EmailProcessingService:
    """Main service for processing emails based on intent"""
    
    def __init__(self):
        self.processors = {
            EmailIntent.EXECUTIVE_ORDER: ExecutiveOrderProcessor(),
            EmailIntent.PMO_RESPONSE: PMOResponseProcessor(),
            EmailIntent.TASK_UPDATE: TaskUpdateProcessor(),
            EmailIntent.UNKNOWN: UnknownEmailProcessor(),
        }
    
    async def process_email(self, payload: EmailWebhookPayload, intent_result: EmailProcessingResult, db: Session = None):
        """
        Process email based on detected intent using appropriate processor
        
        Args:
            payload: The email webhook payload
            intent_result: The detected intent and confidence
            db: Database session
        """
        try:
            # Get the appropriate processor for the detected intent
            processor = self.processors.get(intent_result.intent, self.processors[EmailIntent.UNKNOWN])
            
            # Process the email using the selected processor
            await processor.process(payload, intent_result, db)
            
            logger.info(f"Email processed successfully with intent: {intent_result.intent}")
            
        except Exception as e:
            logger.error(f"Error processing email with intent {intent_result.intent}: {e}")
            raise


class ExecutiveOrderProcessor:
    """Handles Executive Order email processing"""
    
    async def process(self, payload: EmailWebhookPayload, intent_result: EmailProcessingResult, db: Session = None):
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
            
            # Queue EO for processing using the new orchestrated chain
            from src.workflow.chains.eo_processing_chain import process_eo_chain
            
            try:
                # Use the new orchestrated chain instead of individual tasks
                process_eo_chain.delay(eo_data.model_dump())
                logger.info(f"Executive Order queued for orchestrated processing: {eo_data.message_id}")
            except Exception as e:
                logger.error(f"Failed to queue EO for orchestrated processing: {e}")
                raise Exception(f"Failed to queue EO for orchestrated processing: {e}")
            
            logger.info(f"Executive Order queued successfully: {eo_data.message_id}")
            
        except Exception as e:
            logger.error(f"Error processing Executive Order: {e}")
            raise


class PMOResponseProcessor:
    """Handles PMO response email processing"""
    
    async def process(self, payload: EmailWebhookPayload, intent_result: EmailProcessingResult, db: Session = None):
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
                    raise Exception(f"EO not found: {error_msg}")
                logger.info(f"Validated EO exists: {related_eo_id} - {eo.title}")
            else:
                error_msg = "No EO ID found in PMO email subject. Cannot process PMO response."
                logger.error(f"ERROR: {error_msg}")
                raise Exception(f"Missing EO ID: {error_msg}")
            
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
                logger.info(f"PMO email logged with ID: {email_log_id}")
            except Exception as e:
                logger.warning(f"Could not save PMO email log: {e}")
            
            # Convert to PMOEmailIn format
            pmo_email_data = PMOEmailIn(
                message_id=payload.message_id or payload.id,
                subject=payload.subject,
                sender=payload.sender,
                recipients=payload.recipients,
                body_text=payload.raw_content,
                received_at=datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00')) if payload.timestamp else None,
                related_eo_id=related_eo_id
            )
            
            # Queue PMO response for processing using the new orchestrated chain
            from src.workflow.chains.pmo_response_chain import process_pmo_response_chain
            
            # Prepare email payload for Celery task
            email_payload = pmo_email_data.model_dump()
            email_payload["email_log_id"] = email_log_id  # Add email log ID
            
            try:
                # Use the new orchestrated chain instead of individual tasks
                process_pmo_response_chain.delay(email_payload)
                logger.info(f"PMO response queued for orchestrated processing: {pmo_email_data.message_id}")
            except Exception as e:
                logger.error(f"Failed to queue PMO email for orchestrated processing: {e}")
                raise Exception(f"Failed to queue PMO email for orchestrated processing: {e}")
            
            logger.info(f"PMO response queued successfully: {pmo_email_data.message_id}")
            
        except Exception as e:
            logger.error(f"Error processing PMO response: {e}")
            raise


class TaskUpdateProcessor:
    """Handles task update email processing"""
    
    async def process(self, payload: EmailWebhookPayload, intent_result: EmailProcessingResult, db: Session = None):
        """Process task update email - uses AI to extract updates for all user's tasks"""
        try:
            logger.info(f"Processing task update: {payload.subject}")
            
            # Convert to DailyUpdateEmailPayload format for Celery task
            from src.workflow.dto import DailyUpdateEmailPayload
            
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
            
            # Queue daily update for processing using the new orchestrated chain
            from src.workflow.chains.daily_update_chain import process_daily_update_chain
            
            try:
                # Use the new orchestrated chain instead of individual tasks
                process_daily_update_chain.delay(daily_update_data.model_dump())
                logger.info(f"Daily task update queued for orchestrated processing: {daily_update_data.message_id}")
            except Exception as e:
                logger.error(f"Failed to queue daily update for orchestrated processing: {e}")
                raise Exception(f"Failed to queue daily update for orchestrated processing: {e}")
            
            logger.info(f"Daily task update queued successfully: {daily_update_data.message_id}")
            
        except Exception as e:
            logger.error(f"Error processing task update: {e}")
            raise


class UnknownEmailProcessor:
    """Handles unknown email processing"""
    
    async def process(self, payload: EmailWebhookPayload, intent_result: EmailProcessingResult, db: Session = None):
        """Process unknown email - log and store for manual review"""
        try:
            logger.info(f"Processing unknown email: {payload.subject}")
            
            # Log unknown email for manual review
            logger.warning(f"Unknown email received from {payload.sender}: {payload.subject}")
            
            # Store email in database for manual review
            if db:
                await self._save_unknown_email(payload, db)
            
            logger.info(f"Unknown email processed: {payload.id}")
            
        except Exception as e:
            logger.error(f"Error processing unknown email: {e}")
            raise
    
    async def _save_unknown_email(self, payload: EmailWebhookPayload, db: Session):
        """Save unknown email to database for manual review"""
        try:
            from src.workflow import repository as repo
            email_log = repo.save_email_log(
                direction="incoming",
                subject=payload.subject,
                sender=payload.sender,
                recipients=payload.recipients,
                raw_content=payload.raw_content,
                related_eo_id=None,
            )
            logger.info(f"Unknown email logged with ID: {email_log.id}")
        except Exception as e:
            logger.error(f"Could not save unknown email log: {e}")
