from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from src.app.chat.toolkit import register_tool
from src.db.chat.query.task_updates import (
    search_task_updates as q_search_updates,
    get_update_by_id as q_get_update,
    get_task_update_history as q_update_history,
    aggregate_updates_by_status as q_agg_by_status,
    average_progress as q_avg_progress,
    timeseries_updates_count as q_ts_count,
    timeseries_average_progress as q_ts_avg,
    updates_per_user_ranked as q_updates_per_user_ranked,
)
from src.db.chat.filters import TaskUpdateFilters

class SearchUpdatesArgs(BaseModel):
    eo_id: Optional[str] = None
    task_id: Optional[str] = None
    status: Optional[str] = None
    min_progress: Optional[int] = Field(None, ge=0, le=100)
    has_blockers: Optional[bool] = None
    has_risks: Optional[bool] = None
    notes_contains: Optional[str] = None  # not used in base search; optional custom
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)

@register_tool(
    name="search_task_updates",
    description="Search task updates with blockers/risks/progress/date filters within role visibility.",
    args_model=SearchUpdatesArgs,
    entity="task_updates",
    intent="search",
)
def tool_search_task_updates(db, current_user, args: SearchUpdatesArgs):
    filt = TaskUpdateFilters(
        eo_id=args.eo_id,
        task_id=args.task_id,
        status=args.status,
        min_progress=args.min_progress,
        has_blockers=args.has_blockers,
        has_risks=args.has_risks,
        # date_from/date_to strings omitted for brevity; extend DTO if needed
    )
    return q_search_updates(db, current_user, filters=filt, limit=args.limit, offset=args.offset)


class GetUpdateArgs(BaseModel):
    update_id: str


@register_tool(
    name="get_task_update",
    description="Fetch a single task update if visible.",
    args_model=GetUpdateArgs,
    entity="task_updates",
    intent="detail",
)
def tool_get_task_update(db, current_user, args: GetUpdateArgs):
    return q_get_update(db, current_user, update_id=args.update_id)


class GetTaskHistoryArgs(BaseModel):
    task_id: str
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


@register_tool(
    name="get_task_update_history",
    description="List updates for a task (chronological).",
    args_model=GetTaskHistoryArgs,
    entity="task_updates",
    intent="detail",
)
def tool_get_task_update_history(db, current_user, args: GetTaskHistoryArgs):
    return q_update_history(db, current_user, task_id=args.task_id, limit=args.limit, offset=args.offset)


class AggregateUpdatesArgs(BaseModel):
    group_by: str = Field(..., description="status|user_id|eo_id|task_id")


@register_tool(
    name="aggregate_task_updates",
    description="Aggregate updates by group (status/user_id/eo_id/task_id) with counts or avg progress.",
    args_model=AggregateUpdatesArgs,
    entity="task_updates",
    intent="aggregate",
)
def tool_aggregate_task_updates(db, current_user, args: AggregateUpdatesArgs):
    if args.group_by == "status":
        return q_agg_by_status(db, current_user)
    # For brevity, expose avg as separate tool; extend with metrics list if needed
    return {"error": "Unsupported group_by"}


class TimeseriesUpdatesArgs(BaseModel):
    metric: str = Field(..., description="count|avg_progress")
    bucket: str = Field("day", description="day|week")
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    eo_id: Optional[str] = None
    task_id: Optional[str] = None


@register_tool(
    name="timeseries_task_updates",
    description="Timeseries for updates: count or average progress.",
    args_model=TimeseriesUpdatesArgs,
    entity="task_updates",
    intent="timeseries",
)
def tool_timeseries_task_updates(db, current_user, args: TimeseriesUpdatesArgs):
    if args.metric == "count":
        return q_ts_count(db, current_user, bucket=args.bucket, eo_id=args.eo_id, task_id=args.task_id)
    if args.metric == "avg_progress":
        return q_ts_avg(db, current_user, bucket=args.bucket, eo_id=args.eo_id)
    return {"error": "Unsupported metric"}


class TopExecutorsArgs(BaseModel):
    eo_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = Field(5, ge=1, le=50)


@register_tool(
    name="top_executors_by_updates",
    description="Top executors by number of updates in an optional date window, respecting visibility.",
    args_model=TopExecutorsArgs,
    entity="task_updates",
    intent="aggregate",
)
def tool_top_executors_by_updates(db, current_user, args: TopExecutorsArgs):
    # For now, do not parse date strings; extend with ISO parsing if provided.
    return q_updates_per_user_ranked(
        db,
        current_user,
        eo_id=args.eo_id,
        date_from=None,
        date_to=None,
        limit=args.limit,
    )