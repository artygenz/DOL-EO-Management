from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional

from src.app.chat.toolkit import register_tool
from src.db.chat.query.tasks import (
    get_my_tasks as q_get_my_tasks,
    search_tasks as q_search_tasks,
    search_tasks_by_assignee_name as q_search_tasks_by_assignee_name,
    get_task_details as q_get_task_details,
    get_nearest_due_task as q_get_nearest_due,
    aggregate_tasks_by_status as q_agg_by_status,
    aggregate_tasks_by_category as q_agg_by_category,
    timeseries_tasks_due as q_ts_due,
    timeseries_tasks_completed as q_ts_completed,
)
from src.db.chat.filters import TaskFilters


class GetMyTasksArgs(BaseModel):
    status: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


@register_tool(
    name="get_my_tasks",
    description="List tasks visible to the user (respects role). Optional status filter.",
    args_model=GetMyTasksArgs,
    entity="tasks",
    intent="search",
)
def tool_get_my_tasks(db, current_user, args: GetMyTasksArgs):
    return q_get_my_tasks(db, current_user, status=args.status, limit=args.limit, offset=args.offset)


class SearchTasksArgs(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    due_from: Optional[str] = None  # ISO date; parsed in query via DTO if needed
    due_to: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


@register_tool(
    name="search_tasks",
    description="Search tasks by status/category/due window within role visibility.",
    args_model=SearchTasksArgs,
    entity="tasks",
    intent="search",
)
def tool_search_tasks(db, current_user, args: SearchTasksArgs):
    filt = TaskFilters(status=args.status, category=args.category)
    # due_from/due_to not modeled in TaskFilters as str; leave for future parsing if needed
    return q_search_tasks(db, current_user, filters=filt, limit=args.limit, offset=args.offset)


class GetTaskArgs(BaseModel):
    task_id: str


@register_tool(
    name="get_task_details",
    description="Fetch a single task if visible to the user.",
    args_model=GetTaskArgs,
    entity="tasks",
    intent="detail",
)
def tool_get_task_details(db, current_user, args: GetTaskArgs):
    return q_get_task_details(db, current_user, task_id=args.task_id)


class AggregateTasksArgs(BaseModel):
    group_by: str = Field(..., description="status|category")


@register_tool(
    name="aggregate_tasks",
    description="Aggregate visible tasks by group (status/category).",
    args_model=AggregateTasksArgs,
    entity="tasks",
    intent="aggregate",
)
def tool_aggregate_tasks(db, current_user, args: AggregateTasksArgs):
    if args.group_by == "status":
        return q_agg_by_status(db, current_user)
    if args.group_by == "category":
        return q_agg_by_category(db, current_user)
    return {"error": "Unsupported group_by"}


class TimeseriesTasksArgs(BaseModel):
    metric: str = Field(..., description="due_count|completed_count")
    bucket: str = Field("day", description="day|week")
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@register_tool(
    name="timeseries_tasks",
    description="Timeseries metrics for tasks (due/completed).",
    args_model=TimeseriesTasksArgs,
    entity="tasks",
    intent="timeseries",
)
def tool_timeseries_tasks(db, current_user, args: TimeseriesTasksArgs):
    if args.metric == "due_count":
        return q_ts_due(db, current_user, bucket=args.bucket)
    if args.metric == "completed_count":
        return q_ts_completed(db, current_user, bucket=args.bucket)
    return {"error": "Unsupported metric"}


class GetNearestDueArgs(BaseModel):
    limit: int = Field(1, ge=1, le=10)


@register_tool(
    name="get_nearest_due_task",
    description="Return the nearest upcoming tasks by due_date within role visibility.",
    args_model=GetNearestDueArgs,
    entity="tasks",
    intent="search",
)
def tool_get_nearest_due_task(db, current_user, args: GetNearestDueArgs):
    return q_get_nearest_due(db, current_user, limit=args.limit)


class SearchTasksByAssigneeArgs(BaseModel):
    assignee_name: str = Field(..., description="Name of the assignee to search for (partial match supported)")
    status: Optional[str] = None
    category: Optional[str] = None
    due_from: Optional[str] = None  # ISO date; parsed in query via DTO if needed
    due_to: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


@register_tool(
    name="search_tasks_by_assignee_name",
    description="Search tasks by assignee name with additional filters. Respects role-based access controls.",
    args_model=SearchTasksByAssigneeArgs,
    entity="tasks",
    intent="search",
)
def tool_search_tasks_by_assignee_name(db, current_user, args: SearchTasksByAssigneeArgs):
    """Search tasks by assignee name with proper RBAC handling."""
    filt = TaskFilters(
        status=args.status, 
        category=args.category,
        assignee_name=args.assignee_name
    )
    return q_search_tasks_by_assignee_name(
        db, 
        current_user, 
        assignee_name=args.assignee_name,
        filters=filt, 
        limit=args.limit, 
        offset=args.offset
    )


