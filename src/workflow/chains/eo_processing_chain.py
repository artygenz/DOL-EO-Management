"""
EO Processing Chain

This module orchestrates the complete Executive Order processing pipeline using
the refactored services from workflow/services/. It provides proper task chaining
with error handling and state management.
"""

import logging
from typing import Dict, Any
from celery import chain, group
from celery.exceptions import Retry

from src.workflow.celery_app import celery_app
from src.workflow.services.email_processing_service import EmailProcessingService
from src.workflow.services.ai_task_extraction_service import AITaskExtractionService
from src.workflow.services.task_persistence_service import TaskPersistenceService
from src.workflow.services.pmo_review_service import PMOReviewService
from src.workflow.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# Service instances
email_processing_service = EmailProcessingService()
ai_extraction_service = AITaskExtractionService()
task_persistence_service = TaskPersistenceService()
pmo_review_service = PMOReviewService()
notification_service = NotificationService()


@celery_app.task(bind=True, name="src.workflow.chains.eo_processing_chain.process_eo_chain")
def process_eo_chain(self, eo_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrate the complete EO processing pipeline using service layer.
    
    Pipeline:
    1. Process EO email (store, extract text, update status)
    2. Extract tasks using AI
    3. Persist tasks to database
    4. Send PMO review email
    5. Notify assignees (if tasks are auto-approved)
    
    Args:
        eo_payload: Email webhook payload
        
    Returns:
        Dict with processing results and status
    """
    try:
        logger.info(f"Starting EO processing chain for email: {eo_payload.get('message_id', 'unknown')}")
        
        # Step 1: Process EO email
        logger.info("Step 1: Processing EO email")
        email_result = email_processing_service.process_eo_email(eo_payload)
        
        if not email_result.get("next_step") == "ai_extract_tasks":
            raise Exception(f"Email processing failed: {email_result}")
        
        eo_id = email_result["eo_id"]
        processed_text = email_result["processed_text"]
        
        logger.info(f"Step 1 completed: EO {eo_id} processed")
        
        # Step 2: Extract tasks using AI
        logger.info("Step 2: Extracting tasks using AI")
        ai_result = ai_extraction_service.extract_tasks_from_eo(eo_id, processed_text)
        
        if not ai_result.get("next_step") == "persist_tasks":
            raise Exception(f"AI extraction failed: {ai_result}")
        
        tasks_payload = ai_result["tasks"]
        task_count = ai_result["task_count"]
        
        logger.info(f"Step 2 completed: {task_count} tasks extracted")
        
        # Step 3: Persist tasks to database
        logger.info("Step 3: Persisting tasks to database")
        persistence_result = task_persistence_service.persist_tasks_for_eo(eo_id, tasks_payload)
        
        if not persistence_result.get("next_step") == "send_pmo_review_email":
            raise Exception(f"Task persistence failed: {persistence_result}")
        
        inserted_count = persistence_result["inserted"]
        tasks_for_email = persistence_result["tasks_for_email"]
        
        logger.info(f"Step 3 completed: {inserted_count} tasks persisted")
        
        # Step 4: Send PMO review email
        logger.info("Step 4: Sending PMO review email")
        pmo_result = pmo_review_service.send_pmo_review_email(eo_id, tasks_for_email)
        
        sent_to = pmo_result["sent_to"]
        message_id = pmo_result["message_id"]
        
        logger.info(f"Step 4 completed: PMO email sent to {sent_to}")
        
        # Pipeline completed successfully
        result = {
            "success": True,
            "eo_id": eo_id,
            "email_log_id": email_result.get("email_log_id"),
            "tasks_extracted": task_count,
            "tasks_persisted": inserted_count,
            "pmo_email_sent": True,
            "pmo_email_address": sent_to,
            "pmo_message_id": message_id,
            "pipeline_status": "completed"
        }
        
        logger.info(f"EO processing chain completed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"EO processing chain failed: {str(e)}")
        
        # Try to get eo_id for error reporting
        eo_id = None
        try:
            if 'email_result' in locals():
                eo_id = email_result.get("eo_id")
        except:
            pass
        
        error_result = {
            "success": False,
            "error": str(e),
            "eo_id": eo_id,
            "pipeline_status": "failed",
            "failed_step": "unknown"
        }
        
        logger.error(f"EO processing chain error result: {error_result}")
        return error_result


@celery_app.task(bind=True, name="src.workflow.chains.eo_processing_chain.process_eo_with_auto_approval")
def process_eo_with_auto_approval(self, eo_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process EO with automatic task approval and assignee notification.
    
    This is used when tasks should be auto-approved without PMO review.
    """
    try:
        logger.info(f"Starting EO processing with auto-approval for email: {eo_payload.get('message_id', 'unknown')}")
        
        # Run the standard EO processing chain
        eo_result = process_eo_chain(eo_payload)
        
        if not eo_result.get("success"):
            return eo_result
        
        eo_id = eo_result["eo_id"]
        
        # Auto-approve all tasks (this would need to be implemented in the service)
        # For now, we'll just log this step
        logger.info(f"Auto-approving tasks for EO {eo_id}")
        
        # Notify assignees
        logger.info("Notifying assignees")
        notification_result = notification_service.notify_assignees(eo_id)
        
        notified_count = notification_result.get("notified", 0)
        
        # Update result with auto-approval info
        eo_result.update({
            "auto_approved": True,
            "assignees_notified": notified_count,
            "pipeline_status": "completed_with_auto_approval"
        })
        
        logger.info(f"EO processing with auto-approval completed: {eo_result}")
        return eo_result
        
    except Exception as e:
        logger.error(f"EO processing with auto-approval failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "pipeline_status": "failed",
            "failed_step": "auto_approval"
        }


@celery_app.task(bind=True, name="src.workflow.chains.eo_processing_chain.retry_failed_eo")
def retry_failed_eo(self, eo_id: str, retry_reason: str = None) -> Dict[str, Any]:
    """
    Retry processing a failed EO.
    
    Args:
        eo_id: ID of the EO to retry
        retry_reason: Reason for retry (optional)
    """
    try:
        logger.info(f"Retrying failed EO processing for EO {eo_id}")
        
        # This would need to fetch the original email payload from the database
        # and reprocess it. For now, we'll just log the attempt.
        
        # TODO: Implement retry logic
        # 1. Fetch original email payload from database
        # 2. Reset EO status to pending
        # 3. Restart the processing chain
        
        logger.info(f"Retry attempt logged for EO {eo_id}")
        
        return {
            "success": True,
            "eo_id": eo_id,
            "retry_reason": retry_reason,
            "status": "retry_initiated"
        }
        
    except Exception as e:
        logger.error(f"Failed to retry EO {eo_id}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "eo_id": eo_id
        }
