from __future__ import annotations

"""
Filter DTOs for flexible chat queries (read-only).

LLD:
- SRP: DTOs only describe filters; they do not execute queries.
- OCP: Add new filters via new fields without changing query core.
"""

from dataclasses import dataclass
from typing import Optional, Sequence
from datetime import date


@dataclass(frozen=True)
class TaskFilters:
    status: Optional[str] = None
    category: Optional[str] = None
    due_before: Optional[date] = None
    due_after: Optional[date] = None
    assignee_name: Optional[str] = None


@dataclass(frozen=True)
class TaskUpdateFilters:
    eo_id: Optional[str] = None
    task_id: Optional[str] = None
    status: Optional[str] = None
    min_progress: Optional[int] = None
    has_blockers: Optional[bool] = None
    has_risks: Optional[bool] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


@dataclass(frozen=True)
class EOFilters:
    title_contains: Optional[str] = None
    status: Optional[str] = None
    received_from: Optional[date] = None
    received_to: Optional[date] = None
    has_pmo: Optional[bool] = None
    has_primary_pmo: Optional[bool] = None
    has_overdue: Optional[bool] = None
    has_blockers: Optional[bool] = None
    has_risks: Optional[bool] = None


