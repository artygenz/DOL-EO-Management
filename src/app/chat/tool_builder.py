from __future__ import annotations

"""
Factory to build tool callables and JSON schemas from the registry, bound to (db, current_user).
"""

from typing import Any, Dict, Tuple
from pydantic import BaseModel
import importlib

from src.app.chat.toolkit import list_tools, ToolSpec


def build_tools(db, current_user, entity: str | None = None, intents: list[str] | None = None) -> Tuple[Dict[str, Any], list[dict]]:
    # Lazy-load tool modules if registry is empty
    if not list_tools():
        importlib.import_module("src.app.chat.tools")
    tool_fns: Dict[str, Any] = {}
    tool_specs_json: list[dict] = []
    for spec in list_tools(entity, intents):
        tool_fns[spec.name] = _bind_callable(spec, db, current_user)
        tool_specs_json.append(_to_openai_tool_spec(spec))
    return tool_fns, tool_specs_json


def _bind_callable(spec: ToolSpec, db, current_user):
    def _call(payload):
        if spec.args_model is dict:
            parsed = payload or {}
        else:
            parsed = spec.args_model.model_validate(payload or {})
        return spec.func(db, current_user, parsed)

    return _call


def _to_openai_tool_spec(spec: ToolSpec) -> dict:
    params = {} if spec.args_model is dict else spec.args_model.model_json_schema()
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": params,
        },
    }


