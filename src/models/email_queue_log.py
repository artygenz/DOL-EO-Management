"""
Email Queue Log Model

This model stores logs for email queue operations to help with debugging
email sending, rate limiting, and delivery issues.
"""

import uuid
import datetime as dt
from sqlalchemy import String, Text, DateTime, Integer, Boolean, JSON, func
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class EmailQueueLog(Base):
    __tablename__ = "email_queue_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # Email queue information
    email_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Redis email request ID
    queue_name: Mapped[str] = mapped_column(String(100), default="redis_email_queue", nullable=False)
    
    # Email details
    to_addresses: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500))
    email_type: Mapped[str] = mapped_column(String(100), index=True)  # pmo_review, employee_notification, etc.
    priority: Mapped[int] = mapped_column(Integer, default=2, nullable=False)  # 0=urgent, 1=high, 2=normal, 3=low
    
    # Processing status
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # queued, processing, sent, failed, abandoned
    processor_worker: Mapped[str | None] = mapped_column(String(255))  # Which worker processed it
    
    # Timing information
    queued_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_processing_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    
    # SMTP details
    smtp_host: Mapped[str | None] = mapped_column(String(255))
    smtp_response_code: Mapped[int | None] = mapped_column(Integer)  # SMTP response code (250 = success, 421 = rate limit)
    smtp_response_message: Mapped[str | None] = mapped_column(Text)  # SMTP server response
    
    # Retry and error handling
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)  # Error details if failed
    is_rate_limited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # If rate limited
    
    # Delivery confirmation
    outbox_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Saved to outbox
    outbox_path: Mapped[str | None] = mapped_column(String(1024))  # Path to outbox file
    
    # Related entities
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True)  # Celery task that queued this email
    email_log_id: Mapped[str | None] = mapped_column(String(36), index=True)  # Related email log if applicable
    eo_id: Mapped[str | None] = mapped_column(String(36), index=True)  # Related EO ID if applicable
    
    # Metadata
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<EmailQueueLog(email_id='{self.email_id}', status='{self.status}', to='{self.to_addresses}')>"
