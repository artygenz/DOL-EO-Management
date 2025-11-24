"""
Entity-scoped chat query facade.

For now, these delegate to implementations in `src.db.chat.queries` to avoid
duplicating logic. We can progressively move implementations here.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from src.models.user import User

# Re-export entity functions
from .tasks import get_my_tasks, search_tasks
from .task_updates import get_task_updates, search_task_updates
from .executive_orders import get_eo_details, get_cfo_overview
from .users import search_users
from .eo_pmo_assignments import get_eo_pmo_assignments

__all__ = [
    "get_my_tasks",
    "search_tasks",
    "get_task_updates",
    "search_task_updates",
    "get_eo_details",
    "get_cfo_overview",
    "search_users",
    "get_eo_pmo_assignments",
]


