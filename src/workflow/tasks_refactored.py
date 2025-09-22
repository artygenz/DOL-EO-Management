"""
Refactored Celery Tasks

Thin orchestration layer that delegates to business logic services.
This replaces the monolithic tasks.py with clean, maintainable task wrappers.
"""

from typing import Dict
from celery import states
from src.workflow.celery_app import celery_app

# Import services
from src.workflow.services import (
    EmailProcessingService,
    AITaskExtractionService,
    TaskPersistenceService,
    PMOReviewService,
    PMOResponseService,
    NotificationService,
    DailyUpdateService
)

# Service instances (could be dependency injected later)
email_processing_service = EmailProcessingService()
ai_extraction_service = AITaskExtractionService()
task_persistence_service = TaskPersistenceService()
pmo_review_service = PMOReviewService()
pmo_response_service = PMOResponseService()
notification_service = NotificationService()
daily_update_service = DailyUpdateService()

# ============================================================================
# EO PROCESSING TASKS
# ============================================================================

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.store_email")
def store_email(eo_payload: Dict):
    """
    Thin wrapper - delegates to EmailProcessingService
    
    Args:
        eo_payload: Email payload dictionary
        
    Returns:
        Dict containing processing results
    """
    return email_processing_service.process_eo_email(eo_payload)

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.ai_extract_tasks")
def ai_extract_tasks(eo_id: str, body_text: str):
    """
    Thin wrapper - delegates to AITaskExtractionService
    
    Args:
        eo_id: Executive Order ID
        body_text: Text content to extract tasks from
        
    Returns:
        Dict containing extraction results
    """
    result = ai_extraction_service.extract_tasks_from_eo(eo_id, body_text)
    
    # Chain to next task
    persist_tasks.delay(eo_id, result["tasks"])
    return {"eo_id": eo_id, "task_count": result["task_count"]}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.persist_tasks")
def persist_tasks(eo_id: str, tasks_payload: list[dict]):
    """
    Thin wrapper - delegates to TaskPersistenceService
    
    Args:
        eo_id: Executive Order ID
        tasks_payload: List of task dictionaries to persist
        
    Returns:
        Dict containing persistence results
    """
    result = task_persistence_service.persist_tasks_for_eo(eo_id, tasks_payload)
    
    # Chain to next task
    send_pmo_review_email.delay(eo_id, result["tasks_for_email"])
    return {"eo_id": eo_id, "inserted": result["inserted"]}

@celery_app.task(bind=True, acks_late=True, max_retries=3, name="src.workflow.tasks.send_pmo_review_email")
def send_pmo_review_email(self, eo_id: str, task_list: list):
    """
    Thin wrapper - delegates to PMOReviewService
    
    Args:
        eo_id: Executive Order ID
        task_list: List of tasks to include in review email
        
    Returns:
        Dict containing email sending results
    """
    return pmo_review_service.send_pmo_review_email(eo_id, task_list)

# ============================================================================
# PMO RESPONSE TASKS
# ============================================================================

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.process_pmo_response")
def process_pmo_response(email_payload: Dict):
    """
    Thin wrapper - delegates to PMOResponseService
    
    Args:
        email_payload: Email payload dictionary
        
    Returns:
        Dict containing processing results
    """
    return pmo_response_service.process_pmo_response(email_payload)

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.notify_assignees")
def notify_assignees(eo_id: str | None):
    """
    Thin wrapper - delegates to NotificationService
    
    Args:
        eo_id: Executive Order ID
        
    Returns:
        Dict containing notification results
    """
    return notification_service.notify_assignees(eo_id)

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.handle_rejected_tasks")
def handle_rejected_tasks(eo_id: str | None, rejected_ids: list[str] | None, global_remarks: str | None, per_task_remarks: dict[str, str] | None):
    """
    Thin wrapper - delegates to PMOResponseService
    
    Args:
        eo_id: Executive Order ID
        rejected_ids: List of rejected task IDs
        global_remarks: Global remarks from PMO
        per_task_remarks: Per-task remarks from PMO
        
    Returns:
        Dict containing processing results
    """
    return pmo_response_service.handle_rejected_tasks(eo_id, rejected_ids, global_remarks, per_task_remarks)

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.send_improved_tasks_to_pmo")
def send_improved_tasks_to_pmo(eo_id: str, improvement_summary: str, improved_task_ids: list[str] = None):
    """
    Thin wrapper - delegates to PMOResponseService
    
    Args:
        eo_id: Executive Order ID
        improvement_summary: Summary of improvements made by LLM
        improved_task_ids: Specific task IDs that were improved
        
    Returns:
        Dict containing email sending results
    """
    return pmo_response_service.send_improved_tasks_to_pmo(eo_id, improvement_summary, improved_task_ids)

# ============================================================================
# DAILY UPDATE TASKS
# ============================================================================

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.process_daily_update_email")
def process_daily_update_email(email_payload: Dict):
    """
    Thin wrapper - delegates to DailyUpdateService
    
    Args:
        email_payload: Email payload dictionary
        
    Returns:
        Dict containing processing results
    """
    return daily_update_service.process_daily_update_email(email_payload)

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.aggregate_daily_updates")
def aggregate_daily_updates(eo_id: str, target_date: str = None):
    """
    Thin wrapper - delegates to DailyUpdateService
    
    Args:
        eo_id: Executive Order ID
        target_date: Target date for aggregation (optional)
        
    Returns:
        Dict containing aggregation results
    """
    return daily_update_service.aggregate_daily_updates(eo_id, target_date)

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.send_daily_summary_email")
def send_daily_summary_email(summary_id: str):
    """
    Thin wrapper - delegates to DailyUpdateService
    
    Args:
        summary_id: Daily summary ID
        
    Returns:
        Dict containing email sending results
    """
    return daily_update_service.send_daily_summary_email(summary_id)

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.send_daily_reminders")
def send_daily_reminders(target_date: str = None):
    """
    Thin wrapper - delegates to DailyUpdateService
    
    Args:
        target_date: Target date for reminders (optional)
        
    Returns:
        Dict containing reminder results
    """
    return daily_update_service.send_daily_reminders(target_date)
