# src/workflow/mappers.py
from datetime import date
from typing import Optional
from src.workflow.dto import LLMTask, TaskCreate

_STATUS_MAP = {
    None: "pending",
    "": "pending",
    "pending": "pending",
    "Pending": "pending",
    "in_progress": "in_progress",
    "In Progress": "in_progress",
    "completed": "completed",
    "Completed": "completed",
    "TBD": "pending",
}

def _norm_status(s: Optional[str]) -> str:
    return _STATUS_MAP.get(s, "pending")

def _parse_due_date(s: Optional[str]) -> Optional[date]:
    if not s or s.strip().upper() == "TBD":
        return None
    try:
        return date.fromisoformat(s.strip()[:10])
    except Exception:
        return None

def llm_task_to_taskcreate(x: LLMTask) -> TaskCreate:
    return TaskCreate(
        title=x.title,
        description=x.description,
        status=_norm_status(x.status),
        due_date=_parse_due_date(x.due_date),             # default for now; you can derive later
        assignee_name=(x.assignee or None),
        category=(x.category_dept or None),
    )