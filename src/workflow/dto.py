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