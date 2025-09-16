from __future__ import annotations

"""
Response formatter: converts tool results into user-friendly chat responses.

Follows LLD principles:
- Single Responsibility: formats tool results into structured responses
- Open/Closed: extensible via strategy pattern for different data types
- Dependency Inversion: depends on abstractions (ResponseFormatter protocol)
- Interface Segregation: focused on formatting concerns only
"""

from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .natural_language_generator import NaturalLanguageGenerator, DataSummarizer, NLGContext


@dataclass(frozen=True)
class ChatResponse:
    """Structured response payload for the frontend."""
    text: str
    data_preview: Optional[Dict[str, Any]] = None
    chart: Optional[Dict[str, Any]] = None
    tool_info: Optional[Dict[str, Any]] = None
    visibility: Optional[str] = None
    suggested_followups: Optional[List[str]] = None


class ResponseFormatter(Protocol):
    """Protocol for formatting tool results into chat responses."""
    
    def format_response(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        user_role: str,
        user_question: str,
    ) -> ChatResponse:
        """Convert tool result into a structured chat response."""
        ...


class BaseResponseFormatter(ABC):
    """Base formatter with common utilities."""
    
    def __init__(self):
        self.nlg = NaturalLanguageGenerator()
    
    @abstractmethod
    def format_response(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        user_role: str,
        user_question: str,
    ) -> ChatResponse:
        pass
    
    def _get_visibility_note(self, user_role: str) -> str:
        """Generate role-aware visibility disclaimer using LLM."""
        # Create simple context for visibility note
        context = NLGContext(
            user_role=user_role,
            user_question="What is my data access scope?",
            tool_name="visibility_note",
            tool_args={"user_role": user_role},
            data_summary={"user_role": user_role},
            raw_data_available=True
        )
        
        # Generate LLM response
        text = self.nlg.generate_unified_response(context)
        
        # Fallback to simple template if LLM fails
        if not text:
            if user_role == "admin":
                return "Results include all data across the organization."
            elif user_role == "reviewer":
                return "Results limited to EOs assigned to your PMO."
            else:  # executor
                return "Results limited to your assigned tasks and EOs."
        
        return text
    
    def _normalize_envelope(self, tool_name: str, entity: str, tool_result: Any, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Return a predictable envelope from heterogeneous tool results."""
        limit = tool_args.get("limit", 20)
        offset = tool_args.get("offset", 0)
        applied_filters: Dict[str, Any] = {k: v for k, v in tool_args.items() if k not in ("limit", "offset")}

        items_key_order = ["tasks", "updates", "executive_orders", "users", "assignments", "items"]
        items: List[Dict[str, Any]] = []
        total = 0
        rbac_blocked = False
        aggregates = None
        kv_aggregates = None

        if isinstance(tool_result, dict):
            for key in items_key_order:
                if key in tool_result and isinstance(tool_result[key], list):
                    items = tool_result[key]  # type: ignore
                    break
            total = int(tool_result.get("total", len(items)))
            rbac_blocked = bool(tool_result.get("rbac_blocked", False))
            # detect kv aggregates like {status: count}
            if not items and tool_result and all(isinstance(v, (int, float)) for v in tool_result.values()):
                kv_aggregates = tool_result
        elif isinstance(tool_result, list):
            # list aggregates like [{group, metrics}]
            aggregates = tool_result
            total = len(tool_result)

        return {
            "meta": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": total > (offset + limit),
                "rbac_blocked": rbac_blocked,
                "applied_filters": applied_filters,
            },
            "data": {
                "items": items,
                "aggregates": aggregates,
                "kv_aggregates": kv_aggregates,
            },
        }
    
    def _extract_pagination_info(self, tool_result: Dict[str, Any], tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pagination metadata from tool result and args."""
        total = tool_result.get("total", 0)
        limit = tool_args.get("limit", 20)
        offset = tool_args.get("offset", 0)
        has_more = total > (offset + limit)
        
        return {
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    
    def _generate_rbac_message(self, user_role: str, user_question: str, tool_name: str) -> str:
        """Generate RBAC message using LLM."""
        try:
            context = NLGContext(
                user_role=user_role,
                user_question=user_question,
                tool_name="rbac_blocked",
                tool_args={"reason": "access_denied"},
                data_summary={"total": 0, "key_stats": {"note": "User attempted to access data outside their role scope"}}
            )
            text = self.nlg.generate_response(context)
            return text or "You're requesting data outside your visibility. Your results are limited by your role."
        except Exception:
            return "You're requesting data outside your visibility. Your results are limited by your role."
    
    def _generate_error_message(self, user_role: str, user_question: str, error: str) -> str:
        """Generate error message using LLM."""
        try:
            context = NLGContext(
                user_role=user_role,
                user_question=user_question,
                tool_name="error",
                tool_args={"error": error},
                data_summary={"total": 0, "key_stats": {"note": f"Error occurred: {error}"}}
            )
            text = self.nlg.generate_response(context)
            return text or f"Sorry, {error}"
        except Exception:
            return f"Sorry, {error}"
    
    def _generate_no_data_message(self, user_role: str, user_question: str, data_type: str) -> str:
        """Generate no data found message using LLM."""
        try:
            context = NLGContext(
                user_role=user_role,
                user_question=user_question,
                tool_name="no_data",
                tool_args={"data_type": data_type},
                data_summary={"total": 0, "key_stats": {"note": f"No {data_type} data found"}}
            )
            text = self.nlg.generate_response(context)
            return text or f"No {data_type} data found."
        except Exception:
            return f"No {data_type} data found."


class TaskResponseFormatter(BaseResponseFormatter):
    """Formatter for task-related tool results."""
    
    def format_response(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        user_role: str,
        user_question: str,
    ) -> ChatResponse:
        if isinstance(tool_result, dict) and "error" in tool_result:
            return ChatResponse(
                text=self._generate_error_message(user_role, user_question, tool_result['error']),
                tool_info={"name": tool_name, "args": tool_args}
            )
        
        if not isinstance(tool_result, dict) or "tasks" not in tool_result:
            # Use LLM to generate no data message
            no_data_text = self._generate_no_data_message(user_role, user_question, "tasks")
            return ChatResponse(
                text=no_data_text,
                tool_info={"name": tool_name, "args": tool_args}
            )
        
        env = self._normalize_envelope(tool_name, "tasks", tool_result, tool_args)
        tasks = env["data"]["items"]
        total = env["meta"]["total"]
        rbac_blocked = env["meta"]["rbac_blocked"]

        # RBAC notice when visibility blocked (empty due to scope)
        if total == 0 and rbac_blocked:
            # Use LLM to generate RBAC message
            rbac_text = self._generate_rbac_message(user_role, user_question, tool_name)
            return ChatResponse(
                text=rbac_text,
                tool_info={"name": tool_name, "args": tool_args},
                visibility=self._get_visibility_note(user_role),
                suggested_followups=["Narrow the scope", "Try 'my tasks'", "Filter differently"],
            )
        
        # RBAC soft notice if hints imply other-subject access
        ql = (user_question or "").lower()
        if any(w in ql for w in ["someone else's", "kevin", "sophia", "dylan"]) and user_role != "admin":
            text = "This answer reflects data you are authorized to view. I can’t show other users’ private tasks."
        else:
            text = None

        # Generate text summary - try natural language first when not preset above
        if not text:
            text = self._generate_enhanced_task_summary(tool_name, tool_args, tool_result, user_role, user_question)
        if not text:
            text = self._generate_task_summary(tool_name, tasks, total, user_role, user_question)
        
        # Build data preview
        data_preview = None
        if tasks:
            data_preview = {
                "columns": ["id", "title", "status", "due_date", "category"],
                "rows": [
                    [
                        t.get("id", ""),
                        t.get("title", ""),
                        t.get("status", ""),
                        t.get("due_date", ""),
                        t.get("category", "")
                    ]
                    for t in tasks[:5]  # Show first 5 rows
                ],
                "total": total,
                "page": self._extract_pagination_info(tool_result, tool_args)
            }
        
        # Generate follow-ups
        followups = self._generate_task_followups(tool_name, total, user_role)
        
        return ChatResponse(
            text=text,
            data_preview=data_preview,
            tool_info={"name": tool_name, "args": tool_args},
            visibility=self._get_visibility_note(user_role),
            suggested_followups=followups
        )
    
    def _generate_task_summary(
        self,
        tool_name: str,
        tasks: List[Dict],
        total: int,
        user_role: str,
        user_question: str,
    ) -> str:
        """Generate contextual text summary for tasks using LLM."""
        # Create data summary for LLM
        data_summary = DataSummarizer.summarize_task_data({"tasks": tasks, "total": total}, {"tool_name": tool_name})
        
        # Create NLG context
        context = NLGContext(
            user_role=user_role,
            user_question=user_question,
            tool_name=tool_name,
            tool_args={"tool_name": tool_name, "total": total},
            data_summary=data_summary,
            raw_data_available=len(tasks) > 0
        )
        
        # Generate LLM response
        text = self.nlg.generate_unified_response(context)
        
        # Fallback to simple template if LLM fails
        if not text:
            if total == 0:
                if "overdue" in user_question.lower():
                    return "No overdue tasks found in your scope."
                elif "my tasks" in user_question.lower():
                    scope = "your PMO scope" if user_role == "reviewer" else "assigned to you"
                    return f"No tasks found in {scope}."
                else:
                    return "No tasks match your criteria."
            
            if tool_name == "get_my_tasks":
                scope = "your PMO scope" if user_role == "reviewer" else "assigned to you"
                return f"You have {total} task{'s' if total != 1 else ''} in {scope}."
            elif "overdue" in tool_name:
                return f"Found {total} overdue task{'s' if total != 1 else ''}."
            elif "upcoming" in tool_name or "due" in tool_name:
                return f"Found {total} upcoming task{'s' if total != 1 else ''}."
            else:
                return f"Found {total} task{'s' if total != 1 else ''} matching your criteria."
        
        return text
    
    def _generate_task_followups(self, tool_name: str, total: int, user_role: str) -> List[str]:
        """Generate contextual follow-up suggestions."""
        followups = []
        
        if total > 5:
            followups.append("Show next page")
        
        if tool_name == "get_my_tasks":
            followups.extend([
                "Show only overdue tasks",
                "Filter by status",
                "Group by category"
            ])
        elif "overdue" not in tool_name:
            followups.append("Show overdue tasks")
        
        if user_role in ("admin", "reviewer"):
            followups.append("Show task breakdown by assignee")
        
        return followups[:3]  # Limit to 3 suggestions
    
    def _generate_enhanced_task_summary(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Dict[str, Any],
        user_role: str,
        user_question: str,
    ) -> Optional[str]:
        """Generate enhanced summary using NLG when appropriate."""
        tasks = tool_result.get("tasks", [])
        total = tool_result.get("total", len(tasks))
        
        # Check if this query would benefit from natural language
        if not self.nlg.should_use_nlg(tool_name, user_question, total):
            return None
        
        # Create data summary for LLM
        data_summary = DataSummarizer.summarize_task_data(tool_result, tool_args)
        
        context = NLGContext(
            user_role=user_role,
            user_question=user_question,
            tool_name=tool_name,
            tool_args=tool_args,
            data_summary=data_summary
        )
        
        return self.nlg.generate_response(context)


class TaskUpdateResponseFormatter(BaseResponseFormatter):
    """Formatter for task update tool results."""
    
    def format_response(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        user_role: str,
        user_question: str,
    ) -> ChatResponse:
        if isinstance(tool_result, dict) and "error" in tool_result:
            return ChatResponse(
                text=self._generate_error_message(user_role, user_question, tool_result['error']),
                tool_info={"name": tool_name, "args": tool_args}
            )
        
        # Handle ranking results (list of dicts with user_id/count)
        if isinstance(tool_result, list) and tool_result and "user_id" in tool_result[0]:
            return self._format_ranking_response(tool_name, tool_args, tool_result, user_role, user_question)
        
        if not isinstance(tool_result, dict) or "updates" not in tool_result:
            # Use LLM to generate no data message
            no_data_text = self._generate_no_data_message(user_role, user_question, "task updates")
            return ChatResponse(
                text=no_data_text,
                tool_info={"name": tool_name, "args": tool_args}
            )
        
        env = self._normalize_envelope(tool_name, "task_updates", tool_result, tool_args)
        updates = env["data"]["items"]
        total = env["meta"]["total"]
        rbac_blocked = env["meta"]["rbac_blocked"]

        if total == 0 and rbac_blocked:
            # Use LLM to generate RBAC message
            rbac_text = self._generate_rbac_message(user_role, user_question, tool_name)
            return ChatResponse(
                text=rbac_text,
                tool_info={"name": tool_name, "args": tool_args},
                visibility=self._get_visibility_note(user_role),
                suggested_followups=["Use 'my EOs' scope", "Filter differently"],
            )
        
        # RBAC soft notice if hints imply other-subject access
        ql = (user_question or "").lower()
        if any(w in ql for w in ["someone else's", "kevin", "sophia", "dylan"]) and user_role != "admin":
            text = "This answer reflects updates you are authorized to view. I can’t show other users’ private updates."
        else:
            text = None

        # Generate text summary - try natural language first when not preset above
        if not text:
            text = self._generate_enhanced_update_summary(tool_name, tool_args, tool_result, user_role, user_question)
        if not text:
            text = self._generate_update_summary(tool_name, tool_args, updates, total, user_question)
        
        # Build data preview
        data_preview = None
        if updates:
            data_preview = {
                "columns": ["date", "task_id", "status", "progress_pct", "notes"],
                "rows": [
                    [
                        u.get("date", ""),
                        u.get("task_id", "")[:8] + "...",  # Truncate ID
                        u.get("status", ""),
                        f"{u.get('progress_pct', 0)}%" if u.get('progress_pct') is not None else "",
                        (u.get("notes", "") or "")[:50] + ("..." if len(u.get("notes", "") or "") > 50 else "")
                    ]
                    for u in updates[:5]
                ],
                "total": total,
                "page": self._extract_pagination_info(tool_result, tool_args)
            }
        
        return ChatResponse(
            text=text,
            data_preview=data_preview,
            tool_info={"name": tool_name, "args": tool_args},
            visibility=self._get_visibility_note(user_role),
            suggested_followups=self._generate_update_followups(tool_name, total)
        )
    
    def _format_ranking_response(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: List[Dict],
        user_role: str,
        user_question: str,
    ) -> ChatResponse:
        """Format ranking/leaderboard responses."""
        if not tool_result:
            return ChatResponse(
                text="No activity found for the specified period.",
                tool_info={"name": tool_name, "args": tool_args}
            )
        
        total_people = len(tool_result)
        top_count = tool_result[0].get("count", 0)
        
        text = f"Top {total_people} executor{'s' if total_people != 1 else ''} by updates. Leading with {top_count} update{'s' if top_count != 1 else ''}."
        
        data_preview = {
            "columns": ["rank", "user_id", "updates"],
            "rows": [
                [i + 1, r["user_id"][:8] + "...", r["count"]]
                for i, r in enumerate(tool_result[:5])
            ],
            "total": total_people,
            "page": {"limit": len(tool_result), "offset": 0, "has_more": False}
        }
        
        return ChatResponse(
            text=text,
            data_preview=data_preview,
            tool_info={"name": tool_name, "args": tool_args},
            visibility=self._get_visibility_note(user_role),
            suggested_followups=["Show updates for top performer", "Filter by date range"]
        )
    
    def _generate_update_summary(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        updates: List[Dict],
        total: int,
        user_question: str,
    ) -> str:
        """Generate contextual summary for updates using LLM."""
        # Create data summary for LLM
        data_summary = DataSummarizer.summarize_update_data({"updates": updates, "total": total}, tool_args)
        
        # Create NLG context
        context = NLGContext(
            user_role="user",  # Will be overridden by caller if needed
            user_question=user_question,
            tool_name=tool_name,
            tool_args=tool_args,
            data_summary=data_summary,
            raw_data_available=len(updates) > 0
        )
        
        # Generate LLM response
        text = self.nlg.generate_unified_response(context)
        
        # Fallback to simple template if LLM fails
        if not text:
            if total == 0:
                if tool_args.get("has_blockers") or tool_args.get("has_risks"):
                    return "No updates with blockers or risks found in your scope."
                return "No updates found matching your criteria."
            
            has_blockers = tool_args.get("has_blockers")
            has_risks = tool_args.get("has_risks")
            
            if has_blockers and has_risks:
                return f"Found {total} update{'s' if total != 1 else ''} reporting both blockers and risks."
            elif has_blockers:
                return f"Found {total} update{'s' if total != 1 else ''} reporting blockers."
            elif has_risks:
                return f"Found {total} update{'s' if total != 1 else ''} reporting risks."
            else:
                return f"Found {total} task update{'s' if total != 1 else ''}."
        
        return text
    
    def _generate_update_followups(self, tool_name: str, total: int) -> List[str]:
        """Generate follow-up suggestions for updates."""
        followups = []
        
        if total > 5:
            followups.append("Show next page")
        
        followups.extend([
            "Filter by recent updates only",
            "Show updates with blockers",
            "Group by executor"
        ])
        
        return followups[:3]
    
    def _generate_enhanced_update_summary(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        user_role: str,
        user_question: str,
    ) -> Optional[str]:
        """Generate enhanced summary using NLG when appropriate."""
        # Handle both dict results and ranking list results
        if isinstance(tool_result, list):
            total = len(tool_result)
        elif isinstance(tool_result, dict):
            total = tool_result.get("total", 0)
        else:
            return None
        
        # Check if this query would benefit from natural language
        if not self.nlg.should_use_nlg(tool_name, user_question, total):
            return None
        
        # Create data summary for LLM
        data_summary = DataSummarizer.summarize_update_data(tool_result, tool_args)
        
        context = NLGContext(
            user_role=user_role,
            user_question=user_question,
            tool_name=tool_name,
            tool_args=tool_args,
            data_summary=data_summary
        )
        
        return self.nlg.generate_response(context)


class AggregateResponseFormatter(BaseResponseFormatter):
    """Formatter for aggregate/summary tool results."""
    
    def format_response(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        user_role: str,
        user_question: str,
    ) -> ChatResponse:
        if isinstance(tool_result, dict) and "error" in tool_result:
            return ChatResponse(
                text=self._generate_error_message(user_role, user_question, tool_result['error']),
                tool_info={"name": tool_name, "args": tool_args}
            )
        
        # Handle list-based aggregates: [{"group": X, "metrics": {"count": N}}, ...]
        if isinstance(tool_result, list):
            groups: List[str] = []
            counts: List[int] = []
            for item in tool_result:
                try:
                    label = item.get("group", "")
                    metrics = item.get("metrics", {}) or {}
                    count = int(metrics.get("count", 0))
                    groups.append(str(label))
                    counts.append(count)
                except Exception:
                    continue

            total_count = sum(counts)

            # All responses now go through LLM - no hardcoded count logic

            # Generate LLM response for list-based aggregates
            text = self._generate_enhanced_aggregate_summary(tool_name, tool_args, tool_result, user_role, user_question)
            if not text:
                # Fallback to simple template if LLM fails
                text = f"Portfolio breakdown: {total_count} total items across {len(groups)} categories."
            
            data_preview = {
                "columns": ["group", "count"],
                "rows": [[g, c] for g, c in list(zip(groups, counts))[:10]],
                "total": len(groups),
                "page": {"limit": len(groups), "offset": 0, "has_more": False},
            }
            chart = {"type": "bar", "data": {"labels": groups, "values": counts}}
            return ChatResponse(
                text=text,
                data_preview=data_preview,
                chart=chart,
                tool_info={"name": tool_name, "args": tool_args},
                visibility=self._get_visibility_note(user_role),
            )

        if isinstance(tool_result, dict):
            # Key-value aggregates (e.g., {"pending": 5, "completed": 10})
            total_count = sum(tool_result.values()) if isinstance(list(tool_result.values())[0], (int, float)) else 0
            
            # Try natural language first
            text = self._generate_enhanced_aggregate_summary(tool_name, tool_args, tool_result, user_role, user_question)
            if not text:
                text = f"Portfolio breakdown: {total_count} total items across {len(tool_result)} categories."
            
            data_preview = {
                "columns": ["category", "count"],
                "rows": [[k, v] for k, v in tool_result.items()],
                "total": len(tool_result),
                "page": {"limit": len(tool_result), "offset": 0, "has_more": False}
            }
            
            # Simple chart payload for bar chart
            chart = {
                "type": "bar",
                "data": {
                    "labels": list(tool_result.keys()),
                    "values": list(tool_result.values())
                }
            }
            
            return ChatResponse(
                text=text,
                data_preview=data_preview,
                chart=chart,
                tool_info={"name": tool_name, "args": tool_args},
                visibility=self._get_visibility_note(user_role)
            )
        
        return ChatResponse(
            text="Aggregate data processed.",
            tool_info={"name": tool_name, "args": tool_args}
        )
    
    def _generate_enhanced_aggregate_summary(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        user_role: str,
        user_question: str,
    ) -> Optional[str]:
        """Generate enhanced summary using NLG when appropriate."""
        # Handle both dict and list results
        if isinstance(tool_result, dict):
            total_count = sum(v for v in tool_result.values() if isinstance(v, (int, float)))
        elif isinstance(tool_result, list):
            total_count = len(tool_result)
        else:
            total_count = 0

        # All responses now go through LLM - no hardcoded count logic
        
        # Check if this query would benefit from natural language
        if not self.nlg.should_use_nlg(tool_name, user_question, total_count):
            return None
        
        # Create data summary for LLM
        data_summary = DataSummarizer.summarize_aggregate_data(tool_result, tool_args)
        
        context = NLGContext(
            user_role=user_role,
            user_question=user_question,
            tool_name=tool_name,
            tool_args=tool_args,
            data_summary=data_summary
        )
        
        return self.nlg.generate_response(context)


class ResponseFormatterFactory:
    """Factory to select appropriate formatter based on tool name/entity."""
    
    _REGISTRY: Dict[str, ResponseFormatter] = {
        "tasks": TaskResponseFormatter(),
        "task_updates": TaskUpdateResponseFormatter(),
        "aggregate": AggregateResponseFormatter(),
    }

    @classmethod
    def register_formatter(cls, key: str, formatter: ResponseFormatter) -> None:
        cls._REGISTRY[key] = formatter

    @classmethod
    def get_formatter(cls, tool_name: str, entity: str) -> ResponseFormatter:
        # Exact entity mapping
        if entity in cls._REGISTRY:
            return cls._REGISTRY[entity]
        # Aggregate/time-series
        if "aggregate" in tool_name or "timeseries" in tool_name:
            return cls._REGISTRY.get("aggregate", AggregateResponseFormatter())
        # Heuristic fallbacks
        if entity == "task_updates" or "update" in tool_name:
            return TaskUpdateResponseFormatter()
        if entity == "tasks" or "task" in tool_name:
            return TaskResponseFormatter()
        # Default
        return TaskResponseFormatter()
