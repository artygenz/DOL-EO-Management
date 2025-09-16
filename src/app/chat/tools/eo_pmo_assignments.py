from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from src.app.chat.toolkit import register_tool
from src.db.chat.query.eo_pmo_assignments import (
    search_assignments as q_search_assignments,
    get_eo_pmo_assignments as q_get_eo_pmo_assignments,
    aggregate_assignments as q_aggregate_assignments,
    timeseries_assignments as q_timeseries_assignments,
)


class SearchAssignmentsArgs(BaseModel):
    eo_id: Optional[str] = None
    pmo_id: Optional[str] = None
    is_primary: Optional[bool] = None
    assigned_from: Optional[str] = None
    assigned_to: Optional[str] = None
    sort: Optional[str] = Field(None, description="assigned_at_desc|is_primary_desc")
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


@register_tool(
    name="search_eo_pmo_assignments",
    description="Search EO↔PMO assignments within role visibility.",
    args_model=SearchAssignmentsArgs,
    entity="eo_pmo",
    intent="search",
)
def tool_search_assignments(db, current_user, args: SearchAssignmentsArgs):
    return q_search_assignments(
        db,
        current_user,
        eo_id=args.eo_id,
        pmo_id=args.pmo_id,
        is_primary=args.is_primary,
        assigned_from=None,
        assigned_to=None,
        sort=args.sort,
        limit=args.limit,
        offset=args.offset,
    )


class GetEOAssignmentsArgs(BaseModel):
    eo_id: str


@register_tool(
    name="get_eo_pmo_assignments",
    description="List PMO assignments for an EO.",
    args_model=GetEOAssignmentsArgs,
    entity="eo_pmo",
    intent="detail",
)
def tool_get_eo_pmo_assignments(db, current_user, args: GetEOAssignmentsArgs):
    return q_get_eo_pmo_assignments(db, current_user, eo_id=args.eo_id)


class AggregateAssignmentsArgs(BaseModel):
    group_by: str = Field(..., description="is_primary|pmo_id")


@register_tool(
    name="aggregate_eo_pmo_assignments",
    description="Aggregate assignments by is_primary or pmo_id.",
    args_model=AggregateAssignmentsArgs,
    entity="eo_pmo",
    intent="aggregate",
)
def tool_aggregate_assignments(db, current_user, args: AggregateAssignmentsArgs):
    return q_aggregate_assignments(db, current_user, group_by=args.group_by)


class TimeseriesAssignmentsArgs(BaseModel):
    bucket: str = Field("day", description="day|week")
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    eo_id: Optional[str] = None
    pmo_id: Optional[str] = None


@register_tool(
    name="timeseries_eo_pmo_assignments",
    description="Timeseries of assignment counts (assigned_at).",
    args_model=TimeseriesAssignmentsArgs,
    entity="eo_pmo",
    intent="timeseries",
)
def tool_timeseries_assignments(db, current_user, args: TimeseriesAssignmentsArgs):
    return q_timeseries_assignments(db, current_user, bucket=args.bucket, eo_id=args.eo_id, pmo_id=args.pmo_id)


