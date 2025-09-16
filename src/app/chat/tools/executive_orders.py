from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from src.app.chat.toolkit import register_tool
from src.db.chat.query.executive_orders import (
    search_eos as q_search_eos,
    get_eo_details as q_get_eo_details,
    get_eo_summary as q_get_eo_summary,
    aggregate_eos as q_aggregate_eos,
    timeseries_eos as q_timeseries_eos,
)
from src.db.chat.filters import EOFilters


class SearchEOArgs(BaseModel):
    title_contains: Optional[str] = None
    status: Optional[str] = None
    received_from: Optional[str] = None
    received_to: Optional[str] = None
    has_pmo: Optional[bool] = None
    has_primary_pmo: Optional[bool] = None
    has_overdue: Optional[bool] = None
    has_blockers: Optional[bool] = None
    has_risks: Optional[bool] = None
    sort: Optional[str] = Field(None, description="received_at_desc|title|open_tasks_desc|overdue_tasks_desc")
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


@register_tool(
    name="search_eos",
    description="Search executive orders with filters (role-scoped).",
    args_model=SearchEOArgs,
    entity="executive_orders",
    intent="search",
)
def tool_search_eos(db, current_user, args: SearchEOArgs):
    filt = EOFilters(
        title_contains=args.title_contains,
        status=args.status,
        has_pmo=args.has_pmo,
        has_primary_pmo=args.has_primary_pmo,
        has_overdue=args.has_overdue,
        has_blockers=args.has_blockers,
        has_risks=args.has_risks,
    )
    return q_search_eos(db, current_user, filters=filt, sort=args.sort, limit=args.limit, offset=args.offset)


class GetEOArgs(BaseModel):
    eo_id: str


@register_tool(
    name="get_eo_details",
    description="Get EO details if visible.",
    args_model=GetEOArgs,
    entity="executive_orders",
    intent="detail",
)
def tool_get_eo_details(db, current_user, args: GetEOArgs):
    return q_get_eo_details(db, current_user, eo_id=args.eo_id)


@register_tool(
    name="get_eo_summary",
    description="Get EO summary (task totals, overdue/open, last update, PMO assignments).",
    args_model=GetEOArgs,
    entity="executive_orders",
    intent="detail",
)
def tool_get_eo_summary(db, current_user, args: GetEOArgs):
    return q_get_eo_summary(db, current_user, eo_id=args.eo_id)


class AggregateEOArgs(BaseModel):
    metrics: list[str] = Field(default_factory=lambda: ["count"])  # currently only count
    group_by: str = Field(..., description="status|has_pmo|has_primary_pmo|has_overdue")


@register_tool(
    name="aggregate_eos",
    description="Aggregate EOs (count) grouped by status/has_pmo/has_primary_pmo/has_overdue.",
    args_model=AggregateEOArgs,
    entity="executive_orders",
    intent="aggregate",
)
def tool_aggregate_eos(db, current_user, args: AggregateEOArgs):
    return q_aggregate_eos(db, current_user, metrics=args.metrics, group_by=args.group_by, filters=EOFilters())


class TimeseriesEOArgs(BaseModel):
    metric: str = Field(..., description="received_count|with_overdue_count|with_blockers_count")
    bucket: str = Field("day", description="day|week")
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@register_tool(
    name="timeseries_eos",
    description="Timeseries on EOs: received_count / with_overdue_count / with_blockers_count.",
    args_model=TimeseriesEOArgs,
    entity="executive_orders",
    intent="timeseries",
)
def tool_timeseries_eos(db, current_user, args: TimeseriesEOArgs):
    return q_timeseries_eos(db, current_user, metric=args.metric, bucket=args.bucket, date_from=None, date_to=None, filters=EOFilters())


