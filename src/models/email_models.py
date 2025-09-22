"""
Email Models

This module contains all Pydantic models and data structures used for email webhook processing.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EmailIntent(str, Enum):
    """Email intent types for classification"""
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
    routing_suggestions: List[str] = Field(default_factory=list)
