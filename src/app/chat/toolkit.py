from __future__ import annotations

"""
Tool registry and decorator for chat tools.

LLD:
- Registry pattern to avoid hardcoding tools in factories/agents
- Decorator for declarative registration near tool implementations
- Factory (in tool_builder.py) binds DB + current_user to callables and JSON specs
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Type
from pydantic import BaseModel


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_model: Type[BaseModel] | type[dict]
    entity: str  # "tasks" | "task_updates" | "executive_orders" | "users" | "eo_pmo"
    intent: str  # "search" | "detail" | "aggregate" | "timeseries"
    func: Callable  # signature (db, current_user, args_model_instance) -> dict


_REGISTRY: list[ToolSpec] = []


def register_tool(*, name: str, description: str, args_model: Type[BaseModel] | type[dict], entity: str, intent: str):
    """Decorator to register a chat tool with metadata."""

    def _decorator(func: Callable):
        _REGISTRY.append(ToolSpec(name=name, description=description, args_model=args_model, entity=entity, intent=intent, func=func))
        return func

    return _decorator

def list_tools(entity: Optional[str] = None, intents: Optional[list[str]] = None) -> list[ToolSpec]:
    tools = _REGISTRY
    if entity:
        tools = [t for t in tools if t.entity == entity]
    if intents:
        tools = [t for t in tools if t.intent in intents]
    return tools


