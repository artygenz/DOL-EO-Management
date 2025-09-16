from __future__ import annotations

"""Query runner: one LLM function-calling step over a minimal tool subset.

Responsibilities
- Build a concise, role-aware system prompt with guardrails and defaults
- Optionally include user/context metadata and pre-router hints
- Execute at most one tool via native function-calling and return JSON
"""

import json
import os
from typing import Any, Dict, Optional, Callable
from .logger import log_call
from .openai_client import get_openai_client
from .config import BrainConfig
from .natural_language_generator import NaturalLanguageGenerator, NLGContext


def _build_system_prompt(context: Optional[Dict[str, Any]] = None, hints: Optional[Dict[str, Any]] = None) -> str:
    role = (context or {}).get("role", "").lower()
    user_id = str((context or {}).get("user_id", ""))
    hints_str = "{}" if not hints else __safe_json(hints)
    return (
        "You are a role-aware data assistant for an operations dashboard.\n"
        f"Current user: role={role}, id={user_id}.\n"
        "You may call at most ONE tool to answer the user's question.\n"
        "Always respect role visibility implicitly; never request data outside the user's scope.\n\n"
        "Tool usage rules:\n"
        "- Use ONLY the provided tools via function calling.\n"
        "- Choose the single most relevant tool for the request.\n"
        "- If the user asks for both list and aggregate, prefer the one that best answers their question directly.\n"
        "- If a required identifier is missing (e.g., task_id), ask briefly for clarification instead of guessing.\n\n"
        "Argument rules:\n"
        "- Include only fields defined in the tool's JSON schema.\n"
        "- Use sensible defaults when omitted: limit=20, offset=0.\n"
        "- Do not fabricate UUIDs, statuses, or dates.\n"
        "- When dates are vague ('this week', 'last 7 days'), it's okay to proceed without dates; the tool may still return useful defaults.\n\n"
        "Hints (optional defaults; do not overfit):\n"
        f"- {hints_str}\n"
    )


def __safe_json(obj: Dict[str, Any]) -> str:
    try:
        import json as _json
        return _json.dumps(obj, ensure_ascii=False)[:800]
    except Exception:
        return "{}"


class DefaultQueryExecutor:
    """QueryExecutor implementation with injectable LLM client and config."""

    def __init__(self, client: Any, config: BrainConfig | None = None):
        self._client = client
        cfg = config or BrainConfig.from_env()
        self._model = cfg.openai_model
        self._temperature = cfg.llm_temperature

    @log_call("brain.query_runner")
    def execute(
        self,
        message: str,
        tool_fns: Dict[str, Any],
        tool_specs: list[dict],
        *,
        context: Optional[Dict[str, Any]] = None,
        hints: Optional[Dict[str, Any]] = None,
        entity: Optional[str] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        processing: list[str] = []
        role = (context or {}).get("role", "").lower()
        if role:
            processing.append(f"Signed in as {role}.")
            if progress_cb:
                progress_cb(processing[-1])
        if entity:
            human_entity = {
                "tasks": "tasks",
                "task_updates": "task updates",
                "executive_orders": "executive orders",
                "users": "users",
                "eo_pmo": "EO↔PMO assignments",
            }.get((entity or "").lower(), (entity or ""))
            processing.append(f"Understanding your question as about {human_entity}.")
            if progress_cb:
                progress_cb(processing[-1])
        if hints:
            processing.append("Extracted a few helpful filters from your question.")
            if progress_cb:
                progress_cb(processing[-1])
        client = self._client
        if not client:
            return {"final": "LLM unavailable. Please try again later."}

        system = _build_system_prompt(context=context, hints=hints)
        resp = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": message}],
            tools=tool_specs,
            tool_choice="auto",
            temperature=self._temperature,
        )
        msg = resp.choices[0].message
        if not getattr(msg, "tool_calls", None):
            return {"final": (msg.content or "").strip(), "processing": processing}
        tc = msg.tool_calls[0]
        name = tc.function.name
        raw_args = tc.function.arguments
        try:
            parsed = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        except Exception:
            parsed = {}
        if name not in tool_fns:
            processing.append("I couldn't determine a safe tool to answer this.")
            if progress_cb:
                progress_cb(processing[-1])
            return {"final": "Sorry, I couldn't determine a valid tool.", "processing": processing}

        friendly_tool = {
            "get_my_tasks": "listing your tasks",
            "search_tasks": "searching tasks",
            "aggregate_tasks": "counting tasks",
            "search_task_updates": "searching task updates",
            "get_nearest_due_task": "finding the nearest-due task",
            "search_eos": "searching executive orders",
        }.get(name, f"running {name}")
        processing.append(f"Plan: {friendly_tool} with safe parameters.")
        if progress_cb:
            progress_cb(processing[-1])

        # Basic argument validation/guardrails for ID fields to avoid name→UUID crashes
        def _is_uuid_like(val: Any) -> bool:
            try:
                import uuid
                uuid.UUID(str(val))
                return True
            except Exception:
                return False

        def _friendly_invalid_id_message(field: str, value: Any, role: str) -> str:
            role_note = "As an admin, you have broad access." if role == "admin" else (
                "As a reviewer, I can only access data under your assigned Executive Orders."
                if role == "reviewer" else "As an executor, I can only access your own tasks and related updates."
            )
            base = f"I couldn't use '{value}' as a valid identifier. "
            if field == "user_id":
                tip = ("If you meant a person, please provide their name or email (e.g., 'updates from Jane Doe' or 'updates from jane@org.com'), "
                       "or ask me to look them up (e.g., 'find Jane Doe'). ")
            elif field == "eo_id":
                tip = ("If you meant an Executive Order, please provide its title or keywords (e.g., 'EO about digital payments') "
                       "or ask me to search (e.g., 'list executive orders about payments'). ")
            else:  # task_id
                tip = ("If you meant a specific task, please provide part of the task title (e.g., 'find tasks with "
                       "\"Compliance Plan\" in the title') or ask me to list tasks you can see. ")
            return base + tip + role_note

        def _nlg_finalize(user_role: str, user_question: str, message_text: str, tag: str = "notice") -> str:
            try:
                nlg = NaturalLanguageGenerator()
                ctx = NLGContext(
                    user_role=user_role,
                    user_question=user_question,
                    tool_name=tag,
                    tool_args={"reason": tag},
                    data_summary={"total": 0, "key_stats": {"note": message_text}},
                )
                text = nlg.generate_response(ctx)
                return text or message_text
            except Exception:
                return message_text

        if isinstance(parsed, dict):
            for key in ("task_id", "eo_id", "user_id"):
                if key in parsed and parsed[key] and not _is_uuid_like(parsed[key]):
                    role = (context or {}).get("role", "").lower()
                    msg_text = _friendly_invalid_id_message(key, parsed[key], role)
                    processing.append("I couldn't use the provided identifier; asking you to use names/titles or let me search.")
                    if progress_cb:
                        progress_cb(processing[-1])
                    return {
                        "final": _nlg_finalize(role, message, msg_text, tag="invalid_id"),
                        "invalid_arg": {key: parsed[key]},
                        "processing": processing,
                    }

        # Minimal misattribution guard: if the message targets a specific subject but
        # tool args lack the corresponding identifier, block for non-admins.
        current_role = (context or {}).get("role", "").lower()
        if isinstance(hints, dict) and current_role != "admin":
            entity_lower = (entity or "").lower()
            tool_lacks_user = isinstance(parsed, dict) and ("assignee_id" not in parsed and "user_id" not in parsed)
            tool_lacks_eo = isinstance(parsed, dict) and ("eo_id" not in parsed)
            tool_lacks_task = isinstance(parsed, dict) and ("task_id" not in parsed)

            # Targets from hints
            target_user = hints.get("users") or hints.get("user_id")
            target_eo = hints.get("eo_id")
            target_task = hints.get("task_id")

            is_tasks = entity_lower == "tasks"
            is_updates = entity_lower == "task_updates"
            tool_is_tasks_query = name in {"search_tasks", "get_my_tasks"}
            tool_is_updates_query = name in {"search_task_updates"}

            if target_user and (is_tasks or is_updates):
                # Only block if target_user looks like a UUID (specific user ID)
                # Allow name-based searches to proceed and let database RBAC handle restrictions
                import re
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                is_uuid = re.match(uuid_pattern, str(target_user).lower())
                
                if is_uuid and ((tool_is_tasks_query and tool_lacks_user) or (tool_is_updates_query and tool_lacks_user)):
                    role = (context or {}).get("role", "").lower()
                    msg_text = (f"Your question targets a specific user ID, but no user identifier was provided. "
                               "Due to role-based access controls, I can only show data within your scope.")
                    processing.append("Blocking access to another user's data without a specific identifier.")
                    if progress_cb:
                        progress_cb(processing[-1])
                    return {
                        "final": _nlg_finalize(role, message, msg_text, tag="rbac_target_user"),
                        "rbac_target_mismatch": True,
                        "tool_considered": name,
                        "args": parsed,
                        "processing": processing,
                    }

            if target_eo and (is_tasks or is_updates):
                if (tool_is_tasks_query and tool_lacks_eo) or (tool_is_updates_query and tool_lacks_eo):
                    role = (context or {}).get("role", "").lower()
                    msg_text = ("Your question targets a specific Executive Order, but no EO identifier was included. "
                               "Please specify the EO by title or ask me to search for it.")
                    processing.append("Needs a specific executive order identifier (title/ID) to proceed.")
                    if progress_cb:
                        progress_cb(processing[-1])
                    return {
                        "final": _nlg_finalize(role, message, msg_text, tag="rbac_target_eo"),
                        "rbac_target_mismatch": True,
                        "tool_considered": name,
                        "args": parsed,
                        "processing": processing,
                    }

            if target_task and (is_tasks or is_updates):
                if (tool_is_tasks_query and tool_lacks_task) or (tool_is_updates_query and tool_lacks_task):
                    role = (context or {}).get("role", "").lower()
                    msg_text = ("Your question targets a specific task, but no task identifier was included. "
                               "Please reference the task by part of its title or ask me to list tasks you can see.")
                    processing.append("Needs a specific task identifier (title/ID) to proceed.")
                    if progress_cb:
                        progress_cb(processing[-1])
                    return {
                        "final": _nlg_finalize(role, message, msg_text, tag="rbac_target_task"),
                        "rbac_target_mismatch": True,
                        "tool_considered": name,
                        "args": parsed,
                        "processing": processing,
                    }

        result = tool_fns[name](parsed)
        processing.append("Queried the database via a safe, role-scoped tool.")
        if progress_cb:
            progress_cb(processing[-1])

        # Post-query visibility summary
        try:
            if isinstance(result, dict):
                total = int(result.get("total", 0))
                rbac_blocked = bool(result.get("rbac_blocked", False))
                if rbac_blocked:
                    processing.append("Request is outside your visibility; results are restricted by your role.")
                    if progress_cb:
                        progress_cb(processing[-1])
                else:
                    processing.append(f"Found {total} result{'s' if total != 1 else ''} within your visibility.")
                    if progress_cb:
                        progress_cb(processing[-1])
        except Exception:
            pass

        # Format the response for user consumption
        user_role = (context or {}).get("role", "")
        
        # Use unified NLG approach - send raw data to LLM with comprehensive prompt
        final_response = self._generate_unified_response(
            user_question=message,
            user_role=user_role,
            tool_name=name,
            tool_args=parsed,
            tool_result=result,
            entity=entity
        )

        return {
            "tool": name,
            "args": parsed,
            "data": result,
            "final": final_response,
            "processing": processing,
        }
    
    @log_call("brain.query_runner")
    def execute_streaming(
        self,
        message: str,
        tool_fns: Dict[str, Any],
        tool_specs: list[dict],
        *,
        context: Optional[Dict[str, Any]] = None,
        hints: Optional[Dict[str, Any]] = None,
        entity: Optional[str] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
    ):
        """Execute query with streaming response support."""
        processing: list[str] = []
        role = (context or {}).get("role", "").lower()
        if role:
            processing.append(f"Signed in as {role}.")
            if progress_cb:
                progress_cb(processing[-1])
        if entity:
            human_entity = {
                "tasks": "tasks",
                "task_updates": "task updates",
                "executive_orders": "executive orders",
                "users": "users",
                "eo_pmo": "EO↔PMO assignments",
            }.get((entity or "").lower(), (entity or ""))
            processing.append(f"Understanding your question as about {human_entity}.")
            if progress_cb:
                progress_cb(processing[-1])
        if hints:
            processing.append("Extracted a few helpful filters from your question.")
            if progress_cb:
                progress_cb(processing[-1])
        client = self._client
        if not client:
            yield {"final_stream": iter(["LLM unavailable. Please try again later."]), "processing": processing}
            return

        system = _build_system_prompt(context=context, hints=hints)
        resp = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": message}],
            tools=tool_specs,
            tool_choice="auto",
            temperature=self._temperature,
        )
        msg = resp.choices[0].message
        if not getattr(msg, "tool_calls", None):
            # No tool call - stream the direct response
            direct_response = (msg.content or "").strip()
            yield {"final_stream": iter([direct_response]), "processing": processing}
            return
            
        tc = msg.tool_calls[0]
        name = tc.function.name
        raw_args = tc.function.arguments
        try:
            parsed = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        except Exception:
            parsed = {}
        if name not in tool_fns:
            processing.append("I couldn't determine a safe tool to answer this.")
            if progress_cb:
                progress_cb(processing[-1])
            yield {"final_stream": iter(["Sorry, I couldn't determine a valid tool."]), "processing": processing}
            return

        friendly_tool = {
            "get_my_tasks": "listing your tasks",
            "search_tasks": "searching tasks",
            "aggregate_tasks": "counting tasks",
            "search_task_updates": "searching task updates",
            "get_nearest_due_task": "finding the nearest-due task",
            "search_eos": "searching executive orders",
        }.get(name, f"running {name}")
        processing.append(f"Plan: {friendly_tool} with safe parameters.")
        if progress_cb:
            progress_cb(processing[-1])

        # Basic argument validation/guardrails for ID fields to avoid name→UUID crashes
        def _is_uuid_like(val: Any) -> bool:
            try:
                import uuid
                uuid.UUID(str(val))
                return True
            except Exception:
                return False

        def _friendly_invalid_id_message(field: str, value: Any, role: str) -> str:
            role_note = "As an admin, you have broad access." if role == "admin" else (
                "As a reviewer, I can only access data under your assigned Executive Orders."
                if role == "reviewer" else "As an executor, I can only access your own tasks and related updates."
            )
            base = f"I couldn't use '{value}' as a valid identifier. "
            if field == "user_id":
                tip = ("If you meant a person, please provide their name or email (e.g., 'updates from Jane Doe' or 'updates from jane@org.com'), "
                       "or ask me to look them up (e.g., 'find Jane Doe'). ")
            elif field == "eo_id":
                tip = ("If you meant an Executive Order, please provide its title or keywords (e.g., 'EO about digital payments') "
                       "or ask me to search (e.g., 'list executive orders about payments'). ")
            else:  # task_id
                tip = ("If you meant a specific task, please provide part of the task title (e.g., 'find tasks with "
                       "\"Compliance Plan\" in the title') or ask me to list tasks you can see. ")
            return base + tip + role_note

        def _nlg_finalize_streaming(user_role: str, user_question: str, message_text: str, tag: str = "notice"):
            try:
                nlg = NaturalLanguageGenerator()
                ctx = NLGContext(
                    user_role=user_role,
                    user_question=user_question,
                    tool_name=tag,
                    tool_args={"reason": tag},
                    data_summary={"total": 0, "key_stats": {"note": message_text}},
                )
                return nlg.generate_unified_response_streaming(ctx)
            except Exception:
                return iter([message_text])
        

        if isinstance(parsed, dict):
            for key in ("task_id", "eo_id", "user_id"):
                if key in parsed and parsed[key] and not _is_uuid_like(parsed[key]):
                    role = (context or {}).get("role", "").lower()
                    msg_text = _friendly_invalid_id_message(key, parsed[key], role)
                    processing.append("I couldn't use the provided identifier; asking you to use names/titles or let me search.")
                    if progress_cb:
                        progress_cb(processing[-1])
                    yield {
                        "final_stream": _nlg_finalize_streaming(role, message, msg_text, tag="invalid_id"),
                        "invalid_arg": {key: parsed[key]},
                        "processing": processing,
                    }
                    return

        # Minimal misattribution guard: if the message targets a specific subject but
        # tool args lack the corresponding identifier, block for non-admins.
        current_role = (context or {}).get("role", "").lower()
        if isinstance(hints, dict) and current_role != "admin":
            entity_lower = (entity or "").lower()
            tool_lacks_user = isinstance(parsed, dict) and ("assignee_id" not in parsed and "user_id" not in parsed)
            tool_lacks_eo = isinstance(parsed, dict) and ("eo_id" not in parsed)
            tool_lacks_task = isinstance(parsed, dict) and ("task_id" not in parsed)

            # Targets from hints
            target_user = hints.get("users") or hints.get("user_id")
            target_eo = hints.get("eo_id")
            target_task = hints.get("task_id")

            is_tasks = entity_lower == "tasks"
            is_updates = entity_lower == "task_updates"
            tool_is_tasks_query = name in {"search_tasks", "get_my_tasks"}
            tool_is_updates_query = name in {"search_task_updates"}

            if target_user and (is_tasks or is_updates):
                # Only block if target_user looks like a UUID (specific user ID)
                # Allow name-based searches to proceed and let database RBAC handle restrictions
                import re
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                is_uuid = re.match(uuid_pattern, str(target_user).lower())
                
                if is_uuid and ((tool_is_tasks_query and tool_lacks_user) or (tool_is_updates_query and tool_lacks_user)):
                    role = (context or {}).get("role", "").lower()
                    msg_text = (f"Your question targets a specific user ID, but no user identifier was provided. "
                               "Due to role-based access controls, I can only show data within your scope.")
                    processing.append("Blocking access to another user's data without a specific identifier.")
                    if progress_cb:
                        progress_cb(processing[-1])
                    yield {
                        "final_stream": _nlg_finalize_streaming(role, message, msg_text, tag="rbac_target_user"),
                        "rbac_target_mismatch": True,
                        "tool_considered": name,
                        "args": parsed,
                        "processing": processing,
                    }
                    return

            if target_eo and (is_tasks or is_updates):
                if (tool_is_tasks_query and tool_lacks_eo) or (tool_is_updates_query and tool_lacks_eo):
                    role = (context or {}).get("role", "").lower()
                    msg_text = ("Your question targets a specific Executive Order, but no EO identifier was included. "
                               "Please specify the EO by title or ask me to search for it.")
                    processing.append("Needs a specific executive order identifier (title/ID) to proceed.")
                    if progress_cb:
                        progress_cb(processing[-1])
                    yield {
                        "final_stream": _nlg_finalize_streaming(role, message, msg_text, tag="rbac_target_eo"),
                        "rbac_target_mismatch": True,
                        "tool_considered": name,
                        "args": parsed,
                        "processing": processing,
                    }
                    return

            if target_task and (is_tasks or is_updates):
                if (tool_is_tasks_query and tool_lacks_task) or (tool_is_updates_query and tool_lacks_task):
                    role = (context or {}).get("role", "").lower()
                    msg_text = ("Your question targets a specific task, but no task identifier was included. "
                               "Please reference the task by part of its title or ask me to list tasks you can see.")
                    processing.append("Needs a specific task identifier (title/ID) to proceed.")
                    if progress_cb:
                        progress_cb(processing[-1])
                    yield {
                        "final_stream": _nlg_finalize_streaming(role, message, msg_text, tag="rbac_target_task"),
                        "rbac_target_mismatch": True,
                        "tool_considered": name,
                        "args": parsed,
                        "processing": processing,
                    }
                    return

        result = tool_fns[name](parsed)
        processing.append("Queried the database via a safe, role-scoped tool.")
        if progress_cb:
            progress_cb(processing[-1])

        # Post-query visibility summary
        try:
            if isinstance(result, dict):
                total = int(result.get("total", 0))
                rbac_blocked = bool(result.get("rbac_blocked", False))
                if rbac_blocked:
                    processing.append("Request is outside your visibility; results are restricted by your role.")
                    if progress_cb:
                        progress_cb(processing[-1])
                else:
                    processing.append(f"Found {total} result{'s' if total != 1 else ''} within your visibility.")
                    if progress_cb:
                        progress_cb(processing[-1])
        except Exception:
            pass

        # Format the response for user consumption with streaming
        user_role = (context or {}).get("role", "")
        
        # Use streaming NLG approach
        final_response_stream = self._generate_unified_response_streaming(
            user_question=message,
            user_role=user_role,
            tool_name=name,
            tool_args=parsed,
            tool_result=result,
            entity=entity
        )

        yield {
            "tool": name,
            "args": parsed,
            "data": result,
            "final_stream": final_response_stream,
            "processing": processing,
        }
    
    def _generate_unified_response(
        self,
        user_question: str,
        user_role: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        entity: Optional[str] = None
    ) -> str:
        """Generate unified response using NLG with comprehensive prompt."""
        try:
            # Create a comprehensive context for the LLM
            context = NLGContext(
                user_role=user_role,
                user_question=user_question,
                tool_name=tool_name,
                tool_args=tool_args,
                data_summary=self._summarize_any_data(tool_result, tool_args)
            )
            
            # Use the existing NLG but with a unified prompt
            nlg = NaturalLanguageGenerator()
            response = nlg.generate_unified_response(context)
            return response or "I couldn't generate a response for your query."
            
        except Exception as e:
            return f"I encountered an issue while processing your request: {str(e)}"
    
    def _generate_unified_response_streaming(
        self,
        user_question: str,
        user_role: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        entity: Optional[str] = None
    ):
        """Generate streaming response using NLG."""
        try:
            context = NLGContext(
                user_role=user_role,
                user_question=user_question,
                tool_name=tool_name,
                tool_args=tool_args,
                data_summary=self._summarize_any_data(tool_result, tool_args)
            )
            
            nlg = NaturalLanguageGenerator()
            for chunk in nlg.generate_unified_response_streaming(context):
                yield chunk
                
        except Exception as e:
            yield f"I encountered an issue while processing your request: {str(e)}"
    
    def _summarize_any_data(self, tool_result: Any, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize any type of data for NLG context."""
        summary = {}
        
        # Include RBAC context if available
        if isinstance(tool_result, dict) and "rbac_blocked" in tool_result:
            summary["rbac_blocked"] = tool_result["rbac_blocked"]
        
        if isinstance(tool_result, dict):
            # Handle dict results (most common)
            if "tasks" in tool_result:
                tasks = tool_result.get("tasks", [])
                summary["total"] = len(tasks)
                summary["data_type"] = "tasks"
                summary["items"] = tasks[:5]  # First 5 items for context
                if len(tasks) > 5:
                    summary["has_more"] = True
                    
            elif "updates" in tool_result:
                updates = tool_result.get("updates", [])
                summary["total"] = len(updates)
                summary["data_type"] = "task_updates"
                summary["items"] = updates[:5]
                if len(updates) > 5:
                    summary["has_more"] = True
                    
            elif "executive_orders" in tool_result:
                eos = tool_result.get("executive_orders", [])
                summary["total"] = len(eos)
                summary["data_type"] = "executive_orders"
                summary["items"] = eos[:5]
                if len(eos) > 5:
                    summary["has_more"] = True
                    
            else:
                # Generic dict handling
                summary["total"] = len(tool_result)
                summary["data_type"] = "data"
                summary["items"] = list(tool_result.items())[:5]
                
        elif isinstance(tool_result, list):
            # Handle list results
            summary["total"] = len(tool_result)
            summary["data_type"] = "list"
            summary["items"] = tool_result[:5]
            if len(tool_result) > 5:
                summary["has_more"] = True
                
        else:
            # Handle primitive results
            summary["total"] = 1
            summary["data_type"] = "value"
            summary["value"] = str(tool_result)
        
        # Add tool args context
        if tool_args:
            summary["filters"] = {k: v for k, v in tool_args.items() if k not in ["limit", "offset"]}
        
        return summary

@log_call("brain.query_runner")
def run_query_with_tools(
    message: str,
    tool_fns: Dict[str, Any],
    tool_specs: list[dict],
    *,
    context: Optional[Dict[str, Any]] = None,
    hints: Optional[Dict[str, Any]] = None,
    entity: Optional[str] = None,
) -> Dict[str, Any]:
    """Backward-compatible function adapter that uses DefaultQueryExecutor."""
    client = get_openai_client()
    executor = DefaultQueryExecutor(client=client, config=BrainConfig.from_env())
    return executor.execute(
        message,
        tool_fns,
        tool_specs,
        context=context,
        hints=hints,
        entity=entity,
    )

@log_call("brain.query_runner")
def run_query_with_tools_streaming(
    message: str,
    tool_fns: Dict[str, Any],
    tool_specs: list[dict],
    *,
    context: Optional[Dict[str, Any]] = None,
    hints: Optional[Dict[str, Any]] = None,
    entity: Optional[str] = None,
):
    """Streaming version of run_query_with_tools."""
    client = get_openai_client()
    executor = DefaultQueryExecutor(client=client, config=BrainConfig.from_env())
    for result in executor.execute_streaming(
        message,
        tool_fns,
        tool_specs,
        context=context,
        hints=hints,
        entity=entity,
    ):
        yield result


