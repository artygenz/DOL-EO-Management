"""
Celery Task Logger

This module provides logging utilities for Celery tasks to help with
debugging and monitoring task execution.
"""

import uuid
import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from celery import Task
from celery.signals import task_prerun, task_postrun, task_failure, task_retry
from src.db.session import SessionLocal
from src.models.celery_task_log import CeleryTaskLog

logger = logging.getLogger(__name__)

# Debug: Log when this module is imported
logger.warning("TaskLogger module imported - signal handlers registering...")

class TaskLogger:
    """Utility class for logging Celery task execution"""
    
    @staticmethod
    def sanitize_args(args: tuple, kwargs: dict) -> tuple[dict, dict]:
        """Sanitize task arguments to remove sensitive data and make JSON serializable"""
        
        def clean_value(value):
            """Clean individual values for JSON serialization"""
            if isinstance(value, (str, int, float, bool, type(None))):
                return value
            elif isinstance(value, (list, tuple)):
                return [clean_value(item) for item in value[:10]]  # Limit to first 10 items
            elif isinstance(value, dict):
                return {str(k): clean_value(v) for k, v in list(value.items())[:10]}  # Limit to first 10 items
            elif hasattr(value, '__dict__'):
                return str(type(value).__name__)  # Just the class name for objects
            else:
                return str(value)[:500]  # Truncate long strings
        
        try:
            cleaned_args = {f"arg_{i}": clean_value(arg) for i, arg in enumerate(args)}
            cleaned_kwargs = {str(k): clean_value(v) for k, v in kwargs.items()}
            
            # Remove sensitive fields
            sensitive_fields = ['password', 'token', 'secret', 'key', 'auth']
            for field in sensitive_fields:
                if field in cleaned_kwargs:
                    cleaned_kwargs[field] = "[REDACTED]"
                    
            return cleaned_args, cleaned_kwargs
            
        except Exception as e:
            logger.warning(f"Failed to sanitize task arguments: {e}")
            return {"args_error": str(e)}, {"kwargs_error": str(e)}
    
    @staticmethod
    def log_task_start(task_id: str, task_name: str, args: tuple, kwargs: dict, 
                      worker_name: str = None, eo_id: str = None, email_log_id: str = None):
        """Log when a task starts execution"""
        try:
            with SessionLocal() as db:
                cleaned_args, cleaned_kwargs = TaskLogger.sanitize_args(args, kwargs)
                
                task_log = CeleryTaskLog(
                    task_id=task_id,
                    task_name=task_name,
                    status="started",
                    worker_name=worker_name,
                    started_at=datetime.now(timezone.utc),
                    args=cleaned_args,
                    kwargs=cleaned_kwargs,
                    eo_id=eo_id,
                    email_log_id=email_log_id
                )
                
                db.add(task_log)
                db.commit()
                logger.info(f"Logged task start: {task_id} ({task_name})")
                
        except Exception as e:
            logger.error(f"Failed to log task start for {task_id}: {e}")
    
    @staticmethod
    def log_task_success(task_id: str, result: Any, duration_seconds: float = None):
        """Log when a task completes successfully"""
        try:
            with SessionLocal() as db:
                task_log = db.query(CeleryTaskLog).filter(CeleryTaskLog.task_id == task_id).first()
                
                if task_log:
                    # Clean result for JSON serialization
                    try:
                        if isinstance(result, dict):
                            clean_result = {str(k): str(v)[:500] if isinstance(v, str) else v 
                                          for k, v in result.items()}
                        else:
                            clean_result = {"result": str(result)[:500]}
                    except:
                        clean_result = {"result": str(type(result).__name__)}
                    
                    task_log.status = "success"
                    task_log.completed_at = datetime.now(timezone.utc)
                    task_log.result = clean_result
                    
                    if duration_seconds is not None:
                        task_log.duration_seconds = duration_seconds
                    elif task_log.started_at:
                        duration = datetime.now(timezone.utc) - task_log.started_at
                        task_log.duration_seconds = duration.total_seconds()
                    
                    db.commit()
                    logger.info(f"Logged task success: {task_id}")
                else:
                    logger.warning(f"Task log not found for success: {task_id}")
                    
        except Exception as e:
            logger.error(f"Failed to log task success for {task_id}: {e}")
    
    @staticmethod
    def log_task_failure(task_id: str, error: Exception, tb: str = None):
        """Log when a task fails"""
        try:
            with SessionLocal() as db:
                task_log = db.query(CeleryTaskLog).filter(CeleryTaskLog.task_id == task_id).first()
                
                if task_log:
                    task_log.status = "failure"
                    task_log.completed_at = datetime.now(timezone.utc)
                    task_log.error_message = str(error)[:1000]  # Truncate long errors
                    task_log.traceback = tb[:5000] if tb else None  # Truncate long tracebacks
                    
                    if task_log.started_at:
                        duration = datetime.now(timezone.utc) - task_log.started_at
                        task_log.duration_seconds = duration.total_seconds()
                    
                    db.commit()
                    logger.info(f"Logged task failure: {task_id}")
                else:
                    logger.warning(f"Task log not found for failure: {task_id}")
                    
        except Exception as e:
            logger.error(f"Failed to log task failure for {task_id}: {e}")
    
    @staticmethod
    def log_task_retry(task_id: str, retry_count: int, error: Exception = None):
        """Log when a task is retried"""
        try:
            with SessionLocal() as db:
                task_log = db.query(CeleryTaskLog).filter(CeleryTaskLog.task_id == task_id).first()
                
                if task_log:
                    task_log.status = "retry"
                    task_log.retry_count = retry_count
                    if error:
                        task_log.error_message = str(error)[:1000]
                    
                    db.commit()
                    logger.info(f"Logged task retry: {task_id} (attempt {retry_count})")
                else:
                    logger.warning(f"Task log not found for retry: {task_id}")
                    
        except Exception as e:
            logger.error(f"Failed to log task retry for {task_id}: {e}")

# Celery signal handlers
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task prerun signal"""
    logger.warning(f"TASK_PRERUN: {task_id} ({sender})")
    try:
        # Extract additional context from kwargs if available
        eo_id = None
        email_log_id = None
        
        if kwargs:
            eo_id = kwargs.get('eo_id') or (args[0] if args and isinstance(args[0], str) else None)
            email_log_id = kwargs.get('email_log_id')
        
        worker_name = getattr(task, 'request', {}).get('hostname', 'unknown')
        
        # Extract task name from Celery task object
        task_name = "unknown"
        if sender:
            if hasattr(sender, 'name'):
                task_name = sender.name
            else:
                task_name = str(sender)
        
        TaskLogger.log_task_start(
            task_id=task_id,
            task_name=task_name,
            args=args or (),
            kwargs=kwargs or {},
            worker_name=worker_name,
            eo_id=eo_id,
            email_log_id=email_log_id
        )
    except Exception as e:
        logger.error(f"Error in task_prerun_handler: {e}")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """Handle task postrun signal"""
    try:
        if state == 'SUCCESS':
            TaskLogger.log_task_success(task_id=task_id, result=retval)
    except Exception as e:
        logger.error(f"Error in task_postrun_handler: {e}")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failure signal"""
    try:
        tb_str = traceback if isinstance(traceback, str) else str(traceback) if traceback else None
        TaskLogger.log_task_failure(task_id=task_id, error=exception, tb=tb_str)
    except Exception as e:
        logger.error(f"Error in task_failure_handler: {e}")

@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """Handle task retry signal"""
    try:
        # Get retry count from the task
        retry_count = getattr(sender, 'request', {}).get('retries', 0) + 1
        TaskLogger.log_task_retry(task_id=task_id, retry_count=retry_count, error=reason)
    except Exception as e:
        logger.error(f"Error in task_retry_handler: {e}")
