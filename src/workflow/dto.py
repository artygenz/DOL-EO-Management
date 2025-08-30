from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime

class EOIn(BaseModel):
    message_id: str = Field(..., description="Email Message-ID or unique key")
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipients: Optional[list[str]] = None
    received_at: Optional[datetime] = None
    body_text: str
    raw_mime_s3_key: Optional[str] = None

class LLMTask(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    category_dept: Optional[str] = None
    assignee: Optional[str] = None      # free‑text name from LLM
    status: Optional[str] = None        # "Pending"/"Completed"/etc (any casing)
    due_date: Optional[date | None] = None      # "YYYY-MM-DD" | "TBD" | None
    created_at: Optional[str] = None    # ISO string from LLM (ignore for D

#Need to add assignee details later
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Literal["pending", "in_progress", "completed"] = "pending"
    due_date: Optional[date] = None
    category: Optional[str] = None
    
class ExtractedTasks(BaseModel):
    eo_id: str
    tasks: List[LLMTask]

class PMOReply(BaseModel):
    intent: Literal["APPROVE_ALL", "APPROVE_SOME", "REJECT"]
    remarks: str | None                      # normalized combined remarks
    approve_task_ids: list[int] | None       # only when APPROVE_SOME
    reject_task_ids: list[int] | None        # optional if PMO named tasks to reject

class TaskUpdate(BaseModel):
    task_id: int
    updated_fields: dict[str, Any]           # e.g., {"title": "...", "due_date": "2025-09-01", "assignee_email": "..."}
    change_summary: str                      # short human-readable delta for email diffs

class PMOEmailIn(BaseModel):
    message_id: str = Field(..., description="Inbound email Message-ID")
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipients: Optional[list[str]] = None
    received_at: Optional[datetime] = None
    body_text: str
    related_eo_id: Optional[str] = Field(None, description="EO UUID if known from headers/subject")

class UserCreate(BaseModel):
    name: str
    email: str
    role: Literal["admin", "reviewer", "executor"] = "executor"
    org_role: Optional[str] = None

class UserLogin(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

# Dashboard DTOs
class DailyUpdateCreate(BaseModel):
    task_id: str
    update_text: str
    progress_pct: Optional[int] = Field(None, ge=0, le=100)
    hours_spent: Optional[float] = Field(None, ge=0)
    status_note: Optional[str] = None
    blockers: Optional[dict] = None
    risks: Optional[dict] = None
    next_actions: Optional[dict] = None

class DailyUpdateResponse(BaseModel):
    id: str
    task_id: str
    user_id: str
    update_text: str
    progress_pct: Optional[int]
    hours_spent: Optional[float]
    status_note: Optional[str]
    blockers: Optional[dict]
    risks: Optional[dict]
    next_actions: Optional[dict]
    created_at: datetime

class TaskAssigneeUpdate(BaseModel):
    assignee_id: str

class EOPMOUpdate(BaseModel):
    pmo_ids: list[str]
    primary_pmo_id: Optional[str] = None

class EOPMOAssignmentResponse(BaseModel):
    id: str
    eo_id: str
    pmo_id: str
    pmo_name: str
    pmo_email: str
    assigned_at: datetime
    assigned_by: Optional[str] = None
    is_primary: bool

# Task Update Schemas
class TaskUpdateCreate(BaseModel):
    task_id: str
    user_id: str
    eo_id: str
    date: date
    progress_pct: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    blockers: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    eta: Optional[date] = None
    spent_hours: Optional[float] = None
    ai_summary: Optional[str] = None  # AI-generated summary for this task update
    source_email_message_id: Optional[str] = None
    dedupe_hash: Optional[str] = None
    is_late: bool = False

class TaskUpdateOut(BaseModel):
    id: str
    task_id: str
    user_id: str
    eo_id: str
    date: date
    progress_pct: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    blockers: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    eta: Optional[date] = None
    spent_hours: Optional[float] = None
    ai_summary: Optional[str] = None  # AI-generated summary for this task update
    is_late: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

# Daily EO Summary Schemas
class DailyEOSummaryCreate(BaseModel):
    eo_id: str
    date: date
    progress_summary: Optional[str] = None
    key_blockers: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    attention_items: Optional[List[str]] = None
    missing_updates: Optional[List[str]] = None
    total_tasks: int = 0
    updated_tasks: int = 0

class DailyEOSummaryOut(BaseModel):
    id: str
    eo_id: str
    date: date
    progress_summary: Optional[str] = None
    key_blockers: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    attention_items: Optional[List[str]] = None
    missing_updates: Optional[List[str]] = None
    total_tasks: int
    updated_tasks: int
    summary_email_sent: bool
    summary_email_sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# LLM Extraction Schemas
class TaskUpdateExtraction(BaseModel):
    status: Optional[str] = None
    progress_pct: Optional[int] = None
    notes: Optional[str] = None
    blockers: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    eta: Optional[str] = None  # YYYY-MM-DD format
    spent_hours: Optional[float] = None
    ai_summary: Optional[str] = None  # AI-generated summary for this task update

class DailyUpdateExtraction(BaseModel):
    case: Literal["C1", "C2", "C3"]
    updates: List[TaskUpdateExtraction]
    unmatched_mentions: List[str] = []

# Email Processing Schemas
class DailyUpdateEmailPayload(BaseModel):
    message_id: str
    subject: str
    sender: str
    recipients: List[str]
    body_text: str
    body_html: Optional[str] = None
    received_at: datetime
    raw_mime_s3_key: Optional[str] = None