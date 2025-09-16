from __future__ import annotations

"""
Chat user DTOs using LLD and polymorphism to encapsulate role behavior.

Each role implements methods to build SQLAlchemy visibility clauses for
Executive Orders and Tasks. Admin returns no clause (unrestricted view).
"""

from dataclasses import dataclass
from typing import Optional, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.sql.elements import ClauseElement

from src.models.task import Task
from src.models.executive_order import ExecutiveOrder
from src.models.eo_pmo_assignment import EOPMOAssignment
from src.models.user import User as OrmUser


class ChatUser(Protocol):
    id: UUID

    def eo_visibility_clause(self) -> Optional[ClauseElement]:
        ...

    def task_visibility_clause(self) -> Optional[ClauseElement]:
        ...

    def user_visibility_clause(self) -> Optional[ClauseElement]:
        ...


@dataclass(frozen=True)
class AdminUser:
    id: UUID

    def eo_visibility_clause(self) -> Optional[ClauseElement]:
        return None

    def task_visibility_clause(self) -> Optional[ClauseElement]:
        return None

    def user_visibility_clause(self) -> Optional[ClauseElement]:
        return None


@dataclass(frozen=True)
class ReviewerUser:
    id: UUID

    def eo_visibility_clause(self) -> Optional[ClauseElement]:
        return ExecutiveOrder.id.in_(
            select(EOPMOAssignment.eo_id).where(EOPMOAssignment.pmo_id == self.id)
        )

    def task_visibility_clause(self) -> Optional[ClauseElement]:
        return Task.eo_id.in_(
            select(EOPMOAssignment.eo_id).where(EOPMOAssignment.pmo_id == self.id)
        )

    def user_visibility_clause(self) -> Optional[ClauseElement]:
        # Only executor users with tasks on the PMO's EOs
        from sqlalchemy import exists
        exists_tasks = exists(
            select(Task.id)
            .select_from(Task)
            .join(ExecutiveOrder, Task.eo_id == ExecutiveOrder.id)
            .join(EOPMOAssignment, EOPMOAssignment.eo_id == ExecutiveOrder.id)
            .where(EOPMOAssignment.pmo_id == self.id, Task.assignee_id == OrmUser.id)
        )
        return (OrmUser.role == "executor") & exists_tasks


@dataclass(frozen=True)
class ExecutorUser:
    id: UUID

    def eo_visibility_clause(self) -> Optional[ClauseElement]:
        return ExecutiveOrder.id.in_(select(Task.eo_id).where(Task.assignee_id == self.id))

    def task_visibility_clause(self) -> Optional[ClauseElement]:
        return Task.assignee_id == self.id

    def user_visibility_clause(self) -> Optional[ClauseElement]:
        return OrmUser.id == self.id


def make_chat_user(user: OrmUser) -> ChatUser:
    """Factory: Map ORM user to a role-specific ChatUser DTO."""
    role = (user.role or "").strip().lower()
    if role == "admin":
        return AdminUser(id=user.id)
    if role == "reviewer":
        return ReviewerUser(id=user.id)
    # default to executor
    return ExecutorUser(id=user.id)


