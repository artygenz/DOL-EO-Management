from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from src.app.chat.toolkit import register_tool
from src.db.chat.query.users import (
    search_users as q_search_users,
    get_user_details as q_get_user_details,
    aggregate_users as q_aggregate_users,
    pmo_visible_executors as q_pmo_visible_executors,
    user_summary as q_user_summary,
    timeseries_user_updates as q_timeseries_user_updates,
    leaderboard_users as q_leaderboard_users,
)


class SearchUsersArgs(BaseModel):
    role: Optional[str] = None
    org_role_contains: Optional[str] = None
    is_active: Optional[bool] = None
    name_or_email_contains: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


@register_tool(
    name="search_users",
    description="Search users by role/org_role/name/email within role visibility.",
    args_model=SearchUsersArgs,
    entity="users",
    intent="search",
)
def tool_search_users(db, current_user, args: SearchUsersArgs):
    return q_search_users(
        db,
        current_user,
        role=args.role,
        org_role_contains=args.org_role_contains,
        is_active=args.is_active,
        name_or_email_contains=args.name_or_email_contains,
        limit=args.limit,
        offset=args.offset,
    )


class GetUserArgs(BaseModel):
    user_id: str


@register_tool(
    name="get_user_details",
    description="Get a user's basic profile if visible.",
    args_model=GetUserArgs,
    entity="users",
    intent="detail",
)
def tool_get_user_details(db, current_user, args: GetUserArgs):
    return q_get_user_details(db, current_user, user_id=args.user_id)


class AggregateUsersArgs(BaseModel):
    group_by: str = Field("role", description="role|org_role")
    role: Optional[str] = None
    org_role_contains: Optional[str] = None
    is_active: Optional[bool] = None


@register_tool(
    name="aggregate_users",
    description="Aggregate users by role/org_role (counts).",
    args_model=AggregateUsersArgs,
    entity="users",
    intent="aggregate",
)
def tool_aggregate_users(db, current_user, args: AggregateUsersArgs):
    return q_aggregate_users(
        db,
        current_user,
        group_by=args.group_by,
        role=args.role,
        org_role_contains=args.org_role_contains,
        is_active=args.is_active,
    )


class PMOExecutorsArgs(BaseModel):
    name_or_email_contains: Optional[str] = None
    org_role_contains: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


@register_tool(
    name="pmo_visible_executors",
    description="For reviewers: list executors who have tasks on PMO-assigned EOs.",
    args_model=PMOExecutorsArgs,
    entity="users",
    intent="search",
)
def tool_pmo_visible_executors(db, current_user, args: PMOExecutorsArgs):
    return q_pmo_visible_executors(
        db,
        current_user,
        name_or_email_contains=args.name_or_email_contains,
        org_role_contains=args.org_role_contains,
        limit=args.limit,
        offset=args.offset,
    )


class UserSummaryArgs(BaseModel):
    user_id: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@register_tool(
    name="user_summary",
    description="User summary: task status totals, overdue count, updates/blockers/risks in window.",
    args_model=UserSummaryArgs,
    entity="users",
    intent="detail",
)
def tool_user_summary(db, current_user, args: UserSummaryArgs):
    return q_user_summary(db, current_user, user_id=args.user_id)


class TimeseriesUserUpdatesArgs(BaseModel):
    user_id: Optional[str] = None
    bucket: str = Field("day", description="day|week")
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@register_tool(
    name="timeseries_user_updates",
    description="Timeseries of user update activity.",
    args_model=TimeseriesUserUpdatesArgs,
    entity="users",
    intent="timeseries",
)
def tool_timeseries_user_updates(db, current_user, args: TimeseriesUserUpdatesArgs):
    return q_timeseries_user_updates(db, current_user, user_id=args.user_id, bucket=args.bucket)


class LeaderboardUsersArgs(BaseModel):
    metric: str = Field("updates_count", description="updates_count|blockers_count|risks_count|overdue_tasks")
    limit: int = Field(10, ge=1, le=100)
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@register_tool(
    name="leaderboard_users",
    description="Top users by metric within role visibility.",
    args_model=LeaderboardUsersArgs,
    entity="users",
    intent="aggregate",
)
def tool_leaderboard_users(db, current_user, args: LeaderboardUsersArgs):
    return q_leaderboard_users(db, current_user, metric=args.metric, limit=args.limit)


