from __future__ import annotations

"""
Role-scoped visibility helpers for Chat tools (read-only), implemented as a class
to align with Low-Level Design (LLD) principles:
- Single responsibility per method (compute clause vs apply clause)
- Explicit types and narrow interfaces (no global state)
- Encapsulation and discoverability via a cohesive class API
"""

from typing import TypeVar

from sqlalchemy import select, exists
from sqlalchemy.orm import Query

from src.models.user import User
from src.models.task import Task
from src.models.executive_order import ExecutiveOrder
from src.models.eo_pmo_assignment import EOPMOAssignment
from src.models.user import User as OrmUser
from src.db.dto.chat_user import ChatUser, make_chat_user


TQuery = TypeVar("TQuery", bound=Query)


class ChatVisibility:
    """Build and apply role-scoped visibility constraints for EO and Task queries."""

    @staticmethod
    def eo_visibility_clause(current_user: User):
        """Delegate to ChatUser DTO for building EO visibility clause."""
        dto: ChatUser = make_chat_user(current_user)
        return dto.eo_visibility_clause()

    @staticmethod
    def task_visibility_clause(current_user: User):
        """Delegate to ChatUser DTO for building Task visibility clause."""
        dto: ChatUser = make_chat_user(current_user)
        return dto.task_visibility_clause()

    @staticmethod
    def apply_eo_visibility(query: TQuery, current_user: User) -> TQuery:
        """Apply EO visibility restriction to an ExecutiveOrder query (no-op when unrestricted)."""
        clause = ChatVisibility.eo_visibility_clause(current_user)
        if clause is not None:
            query = query.filter(clause)
        return query

    @staticmethod
    def apply_task_visibility(query: TQuery, current_user: User) -> TQuery:
        """Apply Task visibility restriction to a Task query (no-op when unrestricted)."""
        clause = ChatVisibility.task_visibility_clause(current_user)
        if clause is not None:
            query = query.filter(clause)
        return query

    # ----------------------------- Users visibility -----------------------------

    @staticmethod
    def user_visibility_clause(current_user: User):
        """
        Build a SQLAlchemy filter clause limiting visible Users for the caller.
        Semantics:
        - admin: no restriction (None)
        - reviewer: only executor users who have tasks on EOs assigned to this PMO
        - executor: only self
        """
        if current_user.role == "admin":
            return None
        if current_user.role == "reviewer":
            pmo_scope_exists = exists(
                select(Task.id)
                .join(ExecutiveOrder, Task.eo_id == ExecutiveOrder.id)
                .join(EOPMOAssignment, EOPMOAssignment.eo_id == ExecutiveOrder.id)
                .where(
                    EOPMOAssignment.pmo_id == current_user.id,
                    Task.assignee_id == OrmUser.id,
                )
            )
            return (OrmUser.role == "executor") & pmo_scope_exists
        # executor
        return OrmUser.id == current_user.id

    @staticmethod
    def apply_user_visibility(query: TQuery, current_user: User) -> TQuery:
        """Apply Users visibility restriction to a User query (no-op when unrestricted)."""
        clause = ChatVisibility.user_visibility_clause(current_user)
        if clause is not None:
            query = query.filter(clause)
        return query


