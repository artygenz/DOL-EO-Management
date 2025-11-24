from __future__ import annotations

"""
chat_tools.py

Purpose
-------
Expose a small, safe set of callable "tools" that the chatbot can use to
answer questions. Each tool is a thin adapter around role-scoped, read-only
query functions implemented in `src/db/chat/queries.py`.

Design choices (LLD / SOLID)
----------------------------
- Single Responsibility: This module only defines tool argument schemas and
  binds DB + user context into callables for the agent. No business logic.
- Interface Segregation: Tools have narrow, task-focused parameters. No free
  form SQL, no arbitrary code; just structured inputs with validation.
- Dependency Inversion: The tools depend on abstractions (Pydantic DTOs and
  query functions) rather than building queries inline. Swapping the underlying
  query implementations doesn't change the tool interfaces.

Safety
------
All tools call query functions that already apply `ChatVisibility`, ensuring
role-based access control (admin/reviewer/executor) is enforced before any data
leaves the server. This prevents the model from bypassing visibility.

What returns from make_tools
----------------------------
- tool_fns: Mapping[name -> callable(dto_or_dict) -> dict]. The agent calls
  these functions directly when it decides which tool to use.
- tool_specs: JSON schemas for function-calling capable LLMs. Even if you are
  not using an LLM yet, keeping these specs makes the contract explicit and
  future-proofs the agent.
"""

from typing import Any, Dict, Optional, Tuple, Callable

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.models.user import User
from src.db.chat.queries import (
    get_my_tasks,
    get_eo_details,
    get_task_updates,
    get_cfo_overview,
    search_task_updates,
    search_tasks,
)
from src.db.chat.filters import TaskUpdateFilters, TaskFilters


# ----------------------- Pydantic arg schemas -----------------------

class GetMyTasksArgs(BaseModel):
    """Input for listing tasks visible to the current user.

    Notes
    - The visibility scope depends on role:
      - admin: all tasks
      - reviewer: tasks for EOs assigned to the PMO
      - executor: only tasks assigned to the user
    """

    status: Optional[str] = Field(None, description="Optional task status filter")
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


class GetEODetailsArgs(BaseModel):
    """Input for fetching EO details if visible to the user."""

    eo_id: str


class GetTaskUpdatesArgs(BaseModel):
    """Input for fetching updates by eo_id or task_id within user's scope."""

    eo_id: Optional[str] = None
    task_id: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


class SearchTaskUpdatesArgs(BaseModel):
    """Input for flexible search over task updates.

    Common usage: reviewers searching for updates with blockers/risks or minimum
    progress within a time window. All results are still role-scoped.
    """

    eo_id: Optional[str] = None
    task_id: Optional[str] = None
    status: Optional[str] = None
    min_progress: Optional[int] = Field(None, ge=0, le=100)
    has_blockers: Optional[bool] = None
    has_risks: Optional[bool] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


class SearchTasksArgs(BaseModel):
    """Input for flexible task search (status/category) within role scope."""

    status: Optional[str] = None
    category: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


# ----------------------- Tool factory -----------------------

def make_tools(db: Session, current_user: User) -> Tuple[Dict[str, Callable[[Any], Dict[str, Any]]], list[dict]]:
    """Create role-safe tool callables and corresponding JSON specs.

    Parameters
    - db: SQLAlchemy Session bound to the current request.
    - current_user: ORM `User` of the caller; used by query functions to apply
      `ChatVisibility` so role-based scoping is always enforced.

    Returns
    - tool_fns: mapping[name -> callable(dto_or_dict) -> dict]
    - tool_specs: list of JSON schemas compatible with function-calling LLMs

    Notes
    - Each closure captures `db` and `current_user` ensuring the model cannot
      opt-out of visibility rules.
    - Inputs are validated by Pydantic before hitting the DB layer.
    """

    def _get_my_tasks(args: GetMyTasksArgs) -> Dict[str, Any]:
        return get_my_tasks(db, current_user, status=args.status, limit=args.limit, offset=args.offset)

    def _get_eo_details(args: GetEODetailsArgs) -> Dict[str, Any]:
        return get_eo_details(db, current_user, eo_id=args.eo_id)

    def _get_task_updates(args: GetTaskUpdatesArgs) -> Dict[str, Any]:
        return get_task_updates(db, current_user, eo_id=args.eo_id, task_id=args.task_id, limit=args.limit, offset=args.offset)

    def _search_task_updates(args: SearchTaskUpdatesArgs) -> Dict[str, Any]:
        filt = TaskUpdateFilters(
            eo_id=args.eo_id,
            task_id=args.task_id,
            status=args.status,
            min_progress=args.min_progress,
            has_blockers=args.has_blockers,
            has_risks=args.has_risks,
        )
        return search_task_updates(db, current_user, filt, limit=args.limit, offset=args.offset)

    def _search_tasks(args: SearchTasksArgs) -> Dict[str, Any]:
        filt = TaskFilters(status=args.status, category=args.category)
        return search_tasks(db, current_user, filt, limit=args.limit, offset=args.offset)

    def _get_cfo_overview(_: dict | None = None) -> Dict[str, Any]:
        return get_cfo_overview(db, current_user)

    tool_fns: Dict[str, Callable[[Any], Dict[str, Any]]] = {
        "get_my_tasks": _get_my_tasks,
        "get_eo_details": _get_eo_details,
        "get_task_updates": _get_task_updates,
        "search_task_updates": _search_task_updates,
        "search_tasks": _search_tasks,
        "get_cfo_overview": _get_cfo_overview,
    }

    tool_specs = [
        {
            "type": "function",
            "function": {
                "name": "get_my_tasks",
                "description": "List tasks visible to the user, optionally filtered by status.",
                "parameters": GetMyTasksArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_eo_details",
                "description": "Get EO details if visible to the user.",
                "parameters": GetEODetailsArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_task_updates",
                "description": "Get task updates by eo_id or task_id within user's visibility.",
                "parameters": GetTaskUpdatesArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_task_updates",
                "description": "Search task updates with filters (status, min_progress, blockers/risks).",
                "parameters": SearchTaskUpdatesArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_tasks",
                "description": "Search tasks with filters (status, category).",
                "parameters": SearchTasksArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_cfo_overview",
                "description": "Portfolio overview for the current user (admin global).",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
    ]

    return tool_fns, tool_specs


