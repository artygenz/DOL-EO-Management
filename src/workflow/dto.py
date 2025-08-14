from typing import List, Literal, Optional
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
    due_date: Optional[str] = None      # "YYYY-MM-DD" | "TBD" | None
    created_at: Optional[str] = None    # ISO string from LLM (ignore for D

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Literal["pending", "in_progress", "completed"] = "pending"
    due_date: Optional[date] = None
    category: Optional[str] = None
    
class ExtractedTasks(BaseModel):
    eo_id: str
    tasks: List[LLMTask]