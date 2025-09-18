"""
Celery Task Log Model

This model stores execution logs for Celery tasks to help with debugging
and monitoring task execution across the workflow.
"""

import uuid
import datetime as dt
from sqlalchemy import String, Text, DateTime, Integer, Boolean, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class CeleryTaskLog(Base):
    __tablename__ = "celery_task_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # Celery task information
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Celery task ID
    task_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # e.g., "src.workflow.tasks.store_email"
    
    # Task execution details
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # started, success, failure, retry
    worker_name: Mapped[str | None] = mapped_column(String(255))  # Which worker processed it
    
    # Timing information
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column()  # Execution time
    
    # Task data
    args: Mapped[dict | None] = mapped_column(JSON)  # Task arguments (sanitized)
    kwargs: Mapped[dict | None] = mapped_column(JSON)  # Task keyword arguments (sanitized)
    result: Mapped[dict | None] = mapped_column(JSON)  # Task result (if success)
    
    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)  # Error details if failed
    traceback: Mapped[str | None] = mapped_column(Text)  # Full traceback if failed
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Number of retries
    
    # Related entities
    eo_id: Mapped[str | None] = mapped_column(String(36), index=True)  # Related EO ID if applicable
    email_log_id: Mapped[str | None] = mapped_column(String(36), index=True)  # Related email log if applicable
    
    # Metadata
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<CeleryTaskLog(task_id='{self.task_id}', task_name='{self.task_name}', status='{self.status}')>"
