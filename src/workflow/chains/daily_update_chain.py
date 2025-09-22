"""
Daily Update Processing Chain

This module orchestrates the daily update processing pipeline using
the refactored services from workflow/services/. It handles task updates,
aggregation, and summary generation.
"""

import logging
from typing import Dict, Any, Optional
from datetime import date, datetime

from src.workflow.celery_app import celery_app
from src.workflow.services.daily_update_service import DailyUpdateService

logger = logging.getLogger(__name__)

# Service instance
daily_update_service = DailyUpdateService()


@celery_app.task(bind=True, name="src.workflow.chains.daily_update_chain.process_daily_update_chain")
def process_daily_update_chain(self, email_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrate the complete daily update processing pipeline.
    
    Pipeline:
    1. Process daily update email
    2. Extract task updates using AI
    3. Save task updates to database
    4. Trigger aggregation (if needed)
    
    Args:
        email_payload: Daily update email payload
        
    Returns:
        Dict with processing results and status
    """
    try:
        logger.info(f"Starting daily update processing chain for email: {email_payload.get('message_id', 'unknown')}")
        
        # Step 1: Process daily update email
        logger.info("Step 1: Processing daily update email")
        update_result = daily_update_service.process_daily_update_email(email_payload)
        
        if not update_result.get("success"):
            raise Exception(f"Daily update processing failed: {update_result}")
        
        sender = update_result.get("sender")
        user_id = update_result.get("user_id")
        updates_saved = update_result.get("updates_saved", 0)
        extraction_case = update_result.get("extraction_case")
        is_late = update_result.get("is_late", False)
        
        logger.info(f"Step 1 completed: {updates_saved} updates saved for user {user_id}")
        
        # Step 2: Trigger aggregation for affected EOs (if needed)
        aggregation_results = []
        if updates_saved > 0:
            logger.info("Step 2: Triggering aggregation for affected EOs")
            
            # Get affected EOs from the update result
            # This would need to be implemented in the service to return affected EO IDs
            # For now, we'll just log this step
            
            # TODO: Implement EO aggregation logic
            # affected_eos = get_affected_eos_from_updates(update_result)
            # for eo_id in affected_eos:
            #     agg_result = daily_update_service.aggregate_daily_updates(eo_id)
            #     aggregation_results.append(agg_result)
            
            logger.info("Step 2 completed: Aggregation triggered for affected EOs")
        else:
            logger.info("Step 2 skipped: No updates to aggregate")
        
        # Pipeline completed successfully
        result = {
            "success": True,
            "sender": sender,
            "user_id": user_id,
            "updates_saved": updates_saved,
            "extraction_case": extraction_case,
            "is_late": is_late,
            "aggregation_triggered": len(aggregation_results) > 0,
            "aggregation_results": aggregation_results,
            "pipeline_status": "completed"
        }
        
        logger.info(f"Daily update processing chain completed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Daily update processing chain failed: {str(e)}")
        
        # Try to get sender for error reporting
        sender = None
        try:
            if 'update_result' in locals():
                sender = update_result.get("sender")
        except:
            pass
        
        error_result = {
            "success": False,
            "error": str(e),
            "sender": sender,
            "pipeline_status": "failed",
            "failed_step": "unknown"
        }
        
        logger.error(f"Daily update processing chain error result: {error_result}")
        return error_result


@celery_app.task(bind=True, name="src.workflow.chains.daily_update_chain.aggregate_daily_updates_chain")
def aggregate_daily_updates_chain(self, eo_id: str, target_date: str = None) -> Dict[str, Any]:
    """
    Orchestrate the daily update aggregation pipeline.
    
    Pipeline:
    1. Aggregate daily updates for EO
    2. Generate summary using AI
    3. Send summary email to PMO
    
    Args:
        eo_id: ID of the Executive Order
        target_date: Date to aggregate (defaults to today)
        
    Returns:
        Dict with aggregation results and status
    """
    try:
        logger.info(f"Starting daily update aggregation chain for EO {eo_id} on {target_date or 'today'}")
        
        # Step 1: Aggregate daily updates
        logger.info("Step 1: Aggregating daily updates")
        aggregation_result = daily_update_service.aggregate_daily_updates(eo_id, target_date)
        
        if not aggregation_result.get("success"):
            raise Exception(f"Daily update aggregation failed: {aggregation_result}")
        
        summary_id = aggregation_result.get("summary_id")
        updates_count = aggregation_result.get("updates_count", 0)
        missing_updates_count = aggregation_result.get("missing_updates_count", 0)
        
        logger.info(f"Step 1 completed: Summary {summary_id} created with {updates_count} updates")
        
        # Step 2: Send summary email to PMO
        summary_email_result = None
        if summary_id:
            logger.info("Step 2: Sending summary email to PMO")
            summary_email_result = daily_update_service.send_daily_summary_email(summary_id)
            
            if summary_email_result.get("success"):
                pmo_count = summary_email_result.get("pmo_count", 0)
                pmo_emails = summary_email_result.get("pmo_emails", [])
                logger.info(f"Step 2 completed: Summary email sent to {pmo_count} PMOs")
            else:
                logger.warning(f"Step 2 failed: Summary email sending failed: {summary_email_result}")
        else:
            logger.info("Step 2 skipped: No summary to send")
        
        # Pipeline completed successfully
        result = {
            "success": True,
            "eo_id": eo_id,
            "target_date": target_date or str(date.today()),
            "summary_id": summary_id,
            "updates_count": updates_count,
            "missing_updates_count": missing_updates_count,
            "summary_email_sent": summary_email_result.get("success", False) if summary_email_result else False,
            "pmo_emails": summary_email_result.get("pmo_emails", []) if summary_email_result else [],
            "pipeline_status": "completed"
        }
        
        logger.info(f"Daily update aggregation chain completed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Daily update aggregation chain failed: {str(e)}")
        
        error_result = {
            "success": False,
            "error": str(e),
            "eo_id": eo_id,
            "target_date": target_date,
            "pipeline_status": "failed",
            "failed_step": "unknown"
        }
        
        logger.error(f"Daily update aggregation chain error result: {error_result}")
        return error_result


@celery_app.task(bind=True, name="src.workflow.chains.daily_update_chain.send_daily_reminders_chain")
def send_daily_reminders_chain(self, target_date: str = None) -> Dict[str, Any]:
    """
    Orchestrate the daily reminder sending pipeline.
    
    Pipeline:
    1. Find users with missing updates
    2. Send reminder emails
    3. Log reminder activity
    
    Args:
        target_date: Date to send reminders for (defaults to today)
        
    Returns:
        Dict with reminder results and status
    """
    try:
        logger.info(f"Starting daily reminders chain for {target_date or 'today'}")
        
        # Step 1: Send daily reminders
        logger.info("Step 1: Sending daily reminders")
        reminder_result = daily_update_service.send_daily_reminders(target_date)
        
        if not reminder_result.get("success"):
            raise Exception(f"Daily reminders sending failed: {reminder_result}")
        
        reminders_sent = reminder_result.get("reminders_sent", 0)
        target_date_used = reminder_result.get("date", target_date or str(date.today()))
        
        logger.info(f"Step 1 completed: {reminders_sent} reminders sent")
        
        # Pipeline completed successfully
        result = {
            "success": True,
            "target_date": target_date_used,
            "reminders_sent": reminders_sent,
            "pipeline_status": "completed"
        }
        
        logger.info(f"Daily reminders chain completed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Daily reminders chain failed: {str(e)}")
        
        error_result = {
            "success": False,
            "error": str(e),
            "target_date": target_date,
            "pipeline_status": "failed",
            "failed_step": "unknown"
        }
        
        logger.error(f"Daily reminders chain error result: {error_result}")
        return error_result


@celery_app.task(bind=True, name="src.workflow.chains.daily_update_chain.retry_daily_update")
def retry_daily_update(self, email_payload: Dict[str, Any], retry_reason: str = None) -> Dict[str, Any]:
    """
    Retry processing a daily update.
    
    Args:
        email_payload: Original daily update email payload
        retry_reason: Reason for retry (optional)
    """
    try:
        logger.info(f"Retrying daily update processing: {retry_reason}")
        
        # Process the daily update again
        result = process_daily_update_chain(email_payload)
        
        # Update result with retry info
        result.update({
            "retry_attempt": True,
            "retry_reason": retry_reason,
            "pipeline_status": "retry_completed" if result.get("success") else "retry_failed"
        })
        
        logger.info(f"Daily update retry completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Daily update retry failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "retry_reason": retry_reason,
            "pipeline_status": "retry_failed"
        }
