from __future__ import annotations

"""
agent.py

Purpose
-------
Minimal bootstrap agent that routes a user message to one tool. This keeps the
first version dependency-free (no LLM needed) while exercising the tool layer
end-to-end. Later, swap the heuristic router with an LLM function-calling agent
without changing tool contracts.

Design
------
- SRP: This class only decides which tool to call and returns its result.
- Open/Closed: Add new routes/keywords without altering tool implementations.
- DIP: Depends on `make_tools` (abstraction) rather than building queries.

Notes
-----
- All tools invoked here already enforce role-based visibility.
- The keyword matching is intentionally simple; upgrading to an LLM is a drop-in
  replacement once the tool set is stable.
"""

import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.models.user import User
from src.app.chat.chat_tools import make_tools
from src.app.chat.chat_tools import (
    GetMyTasksArgs,
    GetEODetailsArgs,
    GetTaskUpdatesArgs,
    SearchTaskUpdatesArgs,
    SearchTasksArgs,
)

import os
from openai import OpenAI


class ChatAgent:
    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.current_user = current_user
        self.tool_fns, self.tool_specs = make_tools(db, current_user)

    def answer(self, message: str) -> Dict[str, Any]:
        """Route the message to a single tool and return its JSON result."""
        text = (message or "").lower().strip()

        # Naive routing; extend later or swap with LLM function-calling
        if any(k in text for k in ["my tasks", "my task", "tasks for me", "executor tasks"]):
            return self.tool_fns["get_my_tasks"]({})

        if "eo details" in text or text.startswith("eo "):
            # Expect format: "eo details <eo_id>"
            parts = text.split()
            eo_id = parts[-1] if len(parts) > 2 else ""
            return self.tool_fns["get_eo_details"]({"eo_id": eo_id})

        if "updates with blockers" in text:
            return self.tool_fns["search_task_updates"]({"has_blockers": True})

        if "updates with risks" in text:
            return self.tool_fns["search_task_updates"]({"has_risks": True})

        if "task updates" in text:
            return self.tool_fns["get_task_updates"]({})

        if "cfo overview" in text or "portfolio" in text:
            return self.tool_fns["get_cfo_overview"](None)

        if "search tasks" in text:
            return self.tool_fns["search_tasks"]({})

        # Default: try my tasks
        return self.tool_fns["get_my_tasks"]({})

    # --------------------- LLM-backed routing (function-calling lite) ---------------------

    def answer_llm(self, message: str) -> Dict[str, Any]:
        """
        Use an LLM to choose a tool and arguments. The LLM outputs STRICT JSON:
          {"call": {"tool": "<name>", "args": {...}}}
        or a final text answer:
          {"final": "..."}
        We then execute the chosen tool with validated Pydantic args.
        """

        tool_catalog = {
            name: spec["function"]["parameters"] for name, spec in (
                (spec["function"]["name"], spec) for spec in self.tool_specs
            )
        }

        system = self._build_system_prompt(tool_catalog)

        client = OpenAI()
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            tools=self.tool_specs,
            tool_choice="auto",
            temperature=0,
        )

        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            return {"final": (msg.content or "").strip()}

        # Execute the first requested tool (keep it simple for now)
        tc = tool_calls[0]
        name: str = tc.function.name
        raw_args = tc.function.arguments
        print("\n\n DEBUG: raw_args \n\n", raw_args)
        if isinstance(raw_args, str):
            try:
                raw_args = json.loads(raw_args)
            except Exception:
                raw_args = {}
        if not isinstance(raw_args, dict):
            raw_args = {}

        if not name or name not in self.tool_fns:
            return {"final": "Sorry, I couldn't determine the right tool."}

        # Validate args via Pydantic for each tool
        def parse_args(tool_name: str, raw: dict):
            mapping = {
                "get_my_tasks": GetMyTasksArgs,
                "get_eo_details": GetEODetailsArgs,
                "get_task_updates": GetTaskUpdatesArgs,
                "search_task_updates": SearchTaskUpdatesArgs,
                "search_tasks": SearchTasksArgs,
                "get_cfo_overview": dict,  # no args
            }
            cls = mapping.get(tool_name)
            if cls is dict:
                return {}
            if cls is None:
                return raw
            return cls.model_validate(raw)

        try:
            parsed = parse_args(name, raw_args)
        except Exception as e:
            return {"final": f"Invalid arguments for {name}: {e}"}

        result = self.tool_fns[name](parsed if isinstance(parsed, dict) else parsed)
        # Optionally, we could add a second LLM pass to verbalize the JSON result.
        return {"tool": name, "data": result}

    def _build_system_prompt(self, tool_catalog: dict) -> str:
        """Construct a strict, role-aware system prompt for tool selection."""
        role = (getattr(self.current_user, "role", "") or "").lower()
        user_id = str(getattr(self.current_user, "id", ""))
        return (
            "You are a role-aware data assistant for an operations dashboard.\n"
            f"Current user: role={role}, id={user_id}.\n"
            "Your job is to pick ONE tool and valid arguments to answer the user's question, "
            "or reply with a short clarification. You MUST enforce role visibility implicitly; "
            "never propose accessing data outside the user's scope.\n\n"
            "You have access to tools via function calling; tool names and JSON arg schemas are provided out-of-band.\n"
            "Choose the single most relevant tool based on the user's request. If a required identifier is missing, ask briefly.\n"
            "ARG RULES:\n"
            "- Default limit=20, offset=0 when not specified.\n"
            "- Only include fields defined in the tool schema.\n"
            "- If a required identifier (e.g., eo_id) is missing, reply briefly asking for it.\n"
            "- Never fabricate UUIDs or statuses.\n"
        )


