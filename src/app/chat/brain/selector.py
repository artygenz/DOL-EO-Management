from __future__ import annotations

"""Selector: build minimal tool set for entity/intents from the registry.

Now provides a ToolSelector interface-compatible class, with the legacy
function preserved as a thin adapter for backward compatibility.
"""

from typing import Any, Dict, List, Tuple
from src.app.chat.tool_builder import build_tools
from .logger import log_call
from .interfaces import ToolSelector as ToolSelectorProtocol


class DefaultToolSelector(ToolSelectorProtocol):
    """Default implementation of ToolSelector.

    Responsibility: choose a minimal set of tools for an entity+intents.
    Keep pure and side-effect free for easy testing.
    """

    def __init__(self) -> None:
        # Placeholder for future preferences/strategies if needed
        pass

    @log_call("brain.selector")
    def select_tools(self, db, user, entity: str, intents: List[str]) -> Tuple[Dict[str, Any], List[Dict], str]:
        tool_fns, tool_specs = build_tools(db, user, entity=entity, intents=intents)
        return tool_fns, tool_specs, entity


# Backward-compatible function adapter
@log_call("brain.selector")
def select_tools(db, current_user, entity: str, intents: List[str]) -> Tuple[Dict[str, Any], List[Dict], str]:
    selector = DefaultToolSelector()
    return selector.select_tools(db, current_user, entity, intents)
