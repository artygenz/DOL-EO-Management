"""
PMO Response Processing Chain

This module orchestrates the PMO response processing pipeline using
the refactored services from workflow/services/. It handles PMO decisions,
task updates, and follow-up actions.
"""

import logging
from typing import Dict, Any, List, Optional
from celery import chain, group

from src.workflow.celery_app import celery_app
from src.workflow.services.pmo_response_service import PMOResponseService
from src.workflow.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# Service instances
pmo_response_service = PMOResponseService()
notification_service = NotificationService()


@celery_app.task(bind=True, name="src.workflow.chains.pmo_response_chain.process_pmo_response_chain")
def process_pmo_response_chain(self, email_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrate the complete PMO response processing pipeline.
    
    Pipeline:
    1. Parse PMO response email
    2. Update task statuses (approve/reject)
    3. Handle rejected tasks (rewire if needed)
    4. Notify assignees of approved tasks
    5. Send improved tasks back to PMO (if any)
    
    Args:
        email_payload: PMO response email payload
        
    Returns:
        Dict with processing results and status
    """
    try:
        logger.info("PMO response chain start: message_id=%s", email_payload.get('message_id', 'unknown'))
        
        # Step 1: Process PMO response
        logger.debug("Step 1: Processing PMO response")
        pmo_result = pmo_response_service.process_pmo_response(email_payload)
        
        if not pmo_result.get("eo_id"):
            raise Exception(f"PMO response processing failed: {pmo_result}")
        
        eo_id = pmo_result["eo_id"]
        intent = pmo_result.get("intent")
        approved_count = pmo_result.get("approved", 0)
        rejected_count = pmo_result.get("rejected", 0)
        
        logger.info("PMO parsed: intent=%s approved=%d rejected=%d", intent, approved_count, rejected_count)
        
        # Step 2: Handle approved tasks (notify assignees)
        notification_result = None
        if approved_count > 0 or intent in ("APPROVE_ALL", "APPROVE_SOME"):
            logger.debug("Step 2: Notifying assignees of approved tasks")
            notification_result = notification_service.notify_assignees(eo_id)
            notified_count = notification_result.get("notified", 0)
            logger.info("Notified assignees: count=%d", notified_count)
        else:
            logger.info("Step 2 skipped: No approved tasks to notify")
        
        # Step 3: Handle rejected tasks (rewire if needed)
        rewire_result = None
        if rejected_count > 0:
            logger.debug("Step 3: Handling rejected tasks")
            
            # Get rejected task details from the PMO result
            rejected_ids = pmo_result.get("reject_task_ids", [])
            global_remarks = pmo_result.get("remarks")
            per_task_remarks = pmo_result.get("per_task_remarks", {})
            
            rewire_result = pmo_response_service.handle_rejected_tasks(
                eo_id, rejected_ids, global_remarks, per_task_remarks
            )
            
            if rewire_result.get("rewired") and rewire_result.get("updated_count", 0) > 0:
                logger.debug("Step 3a: Sending improved tasks to PMO")
                improved_result = pmo_response_service.send_improved_tasks_to_pmo(
                    eo_id,
                    rewire_result.get("improvement_summary", ""),
                    rewire_result.get("improved_task_ids", [])
                )
                rewire_result["improved_email_sent"] = improved_result.get("message_id")
                logger.info("Improved tasks email sent to PMO")
            else:
                logger.debug("No rewiring needed or possible")
        else:
            logger.info("Step 3 skipped: No rejected tasks to handle")
        
        # Pipeline completed successfully
        result = {
            "success": True,
            "eo_id": eo_id,
            "intent": intent,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "assignees_notified": notification_result.get("notified", 0) if notification_result else 0,
            "tasks_rewired": rewire_result.get("rewired", False) if rewire_result else False,
            "improved_tasks_sent": rewire_result.get("improved_email_sent") if rewire_result else None,
            "pipeline_status": "completed"
        }
        
        logger.info("PMO response chain done: eo_id=%s intent=%s approved=%d rejected=%d", eo_id, intent, approved_count, rejected_count)
        return result
        
    except Exception as e:
        logger.error("PMO response chain failed: %s", str(e))
        
        # Try to get eo_id for error reporting
        eo_id = None
        try:
            if 'pmo_result' in locals():
                eo_id = pmo_result.get("eo_id")
        except:
            pass
        
        error_result = {
            "success": False,
            "error": str(e),
            "eo_id": eo_id,
            "pipeline_status": "failed",
            "failed_step": "unknown"
        }
        
        logger.debug("PMO response chain error result: %s", error_result)
        return error_result


@celery_app.task(bind=True, name="src.workflow.chains.pmo_response_chain.handle_bulk_approval")
def handle_bulk_approval(self, eo_id: str, approval_type: str = "APPROVE_ALL") -> Dict[str, Any]:
    """
    Handle bulk approval of all tasks for an EO.
    
    Args:
        eo_id: ID of the EO
        approval_type: Type of approval (APPROVE_ALL, REJECT_ALL)
    """
    try:
        logger.info(f"Handling bulk {approval_type} for EO {eo_id}")
        
        # Create a mock PMO response payload for bulk approval
        mock_payload = {
            "message_id": f"bulk-{approval_type.lower()}-{eo_id}",
            "subject": f"Bulk {approval_type} for EO {eo_id}",
            "sender": "system@bulk-approval",
            "recipients": ["pmo@company.com"],
            "body_text": f"Bulk {approval_type} action",
            "related_eo_id": eo_id
        }
        
        # Process as regular PMO response
        result = process_pmo_response_chain(mock_payload)
        
        # Update result with bulk approval info
        result.update({
            "bulk_approval": True,
            "approval_type": approval_type,
            "pipeline_status": "bulk_approval_completed"
        })
        
        logger.info(f"Bulk approval completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Bulk approval failed for EO {eo_id}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "eo_id": eo_id,
            "approval_type": approval_type,
            "pipeline_status": "bulk_approval_failed"
        }


@celery_app.task(bind=True, name="src.workflow.chains.pmo_response_chain.retry_pmo_response")
def retry_pmo_response(self, email_payload: Dict[str, Any], retry_reason: str = None) -> Dict[str, Any]:
    """
    Retry processing a PMO response.
    
    Args:
        email_payload: Original PMO response email payload
        retry_reason: Reason for retry (optional)
    """
    try:
        logger.info(f"Retrying PMO response processing: {retry_reason}")
        
        # Process the PMO response again
        result = process_pmo_response_chain(email_payload)
        
        # Update result with retry info
        result.update({
            "retry_attempt": True,
            "retry_reason": retry_reason,
            "pipeline_status": "retry_completed" if result.get("success") else "retry_failed"
        })
        
        logger.info(f"PMO response retry completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"PMO response retry failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "retry_reason": retry_reason,
            "pipeline_status": "retry_failed"
        }
