"""
langchain_utils.py
LangChain orchestration for extracting structured tasks from an EO string and related task management workflows.

This module encapsulates:
- Pydantic schemas (TaskModel, TasksModel) that define the strict output contract
- Prompt wiring (system + human) sourced from app.prompts
- ChatOpenAI configuration (model=gpt-4.1) with structured output
- Convenience functions to parse EO dates and invoke the chain
- New: Utility functions for task rewiring, update extraction, summaries, and weekly reports

Environment:
- Reads OPENAI_API_KEY from .env or OS env using python-dotenv
- Optional: OPENAI_MODEL (defaults to gpt-4.1)
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# Support running as a module or as a script from the 'app' directory
if __package__ is None or __package__ == "":
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from .prompts import (
        EO_EXTRACTION_SYSTEM_PROMPT, EO_EXTRACTION_HUMAN_TEMPLATE,
        REWIRE_TASKS_SYSTEM_PROMPT, REWIRE_TASKS_HUMAN_TEMPLATE,
        REWIRE_TASKS_CHECK_SYSTEM_PROMPT, REWIRE_TASKS_CHECK_HUMAN_TEMPLATE,
        TASK_UPDATE_SYSTEM_PROMPT, TASK_UPDATE_HUMAN_TEMPLATE,
        TASK_SUMMARY_SYSTEM_PROMPT, TASK_SUMMARY_HUMAN_TEMPLATE,
        EO_WEEKLY_SUMMARY_SYSTEM_PROMPT, EO_WEEKLY_SUMMARY_HUMAN_TEMPLATE
    )
except ImportError:
    from prompts import (
        EO_EXTRACTION_SYSTEM_PROMPT, EO_EXTRACTION_HUMAN_TEMPLATE,
        REWIRE_TASKS_SYSTEM_PROMPT, REWIRE_TASKS_HUMAN_TEMPLATE,
        REWIRE_TASKS_CHECK_SYSTEM_PROMPT, REWIRE_TASKS_CHECK_HUMAN_TEMPLATE,
        TASK_UPDATE_SYSTEM_PROMPT, TASK_UPDATE_HUMAN_TEMPLATE,
        TASK_SUMMARY_SYSTEM_PROMPT, TASK_SUMMARY_HUMAN_TEMPLATE,
        EO_WEEKLY_SUMMARY_SYSTEM_PROMPT, EO_WEEKLY_SUMMARY_HUMAN_TEMPLATE
    )

# Load environment variables from .env if present
load_dotenv()

# ----------------------------- Pydantic output data models -----------------------------

class TaskModel(BaseModel):
    id: int
    title: str
    description: str
    category_dept: str
    assignee: str
    status: str
    due_date: str
    created_at: str

class TasksModel(BaseModel):
    tasks: List[TaskModel] = Field(default_factory=list)

# ----------------------------- Helpers -----------------------------

def _parse_eo_date(eo_text: str) -> Optional[str]:
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    }
    pattern = re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})\b",
        re.IGNORECASE,
    )
    match = pattern.search(eo_text or "")
    if not match:
        return None
    month_name, day_str, year_str = match.groups()
    month_num = months[month_name.lower()]
    day = int(day_str)
    year = int(year_str)
    return f"{year:04d}-{month_num:02d}-{day:02d}"

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _build_llm(model_name: Optional[str] = None, temperature: float = 0):
    resolved_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4.1")
    return ChatOpenAI(model=resolved_model, temperature=temperature)

# ----------------------------- Chain construction -----------------------------

def _build_prompt(system_prompt: str, human_template: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_template),
    ])

# ----------------------------- Public API: EO Extraction (existing) -----------------------------

def extract_tasks(
    eo_text: str,
    roles_text: str,
    eo_date: Optional[str] = None,
    now_utc: Optional[str] = None,
    model_name: Optional[str] = None,
) -> TasksModel:
    eo_date_final = eo_date or _parse_eo_date(eo_text)
    now_utc_final = now_utc or _now_utc_iso()
    prompt = _build_prompt(EO_EXTRACTION_SYSTEM_PROMPT, EO_EXTRACTION_HUMAN_TEMPLATE)
    structured_llm = _build_llm(model_name=model_name).with_structured_output(TasksModel)
    chain = prompt | structured_llm
    result: TasksModel = chain.invoke({
        "eo_text": eo_text,
        "roles_text": roles_text,
        "eo_date": eo_date_final or "",
        "now_utc": now_utc_final,
    })
    for t in result.tasks:
        t.assignee = ""
    return result

# ----------------------------- New Utilities for Task Rewiring & Summaries -----------------------------

def rewire_tasks_llm(
    eo: str,
    remarks: str,
    tasks: dict,
    roles_text: str,
    model_name: Optional[str] = None,
) -> dict:
    """
    Calls LLM to rewrite tasks based on remarks and EO, and summarize changes.
    Returns: dict with keys 'tasks' (list) and 'summary' (str)
    """
    prompt = _build_prompt(REWIRE_TASKS_SYSTEM_PROMPT, REWIRE_TASKS_HUMAN_TEMPLATE)
    llm = _build_llm(model_name=model_name)
    chain = prompt | llm
    result = chain.invoke({
        "eo": eo,
        "remarks": remarks,
        "tasks": tasks,
        "roles_text": roles_text,
    })
    # Ensure result is a dict, not AIMessage
    if hasattr(result, "content"):
        content = result.content
        if isinstance(content, str):
            import json
            try:
                return json.loads(content)
            except Exception:
                return {"content": content}
        return content
    return result

def rewire_tasks_conscience_check_llm(
    eo: str,
    remarks: str,
    original_tasks: dict,
    summary: str,
    revised_tasks: dict,
    model_name: Optional[str] = None,
) -> dict:
    """
    Calls LLM to check if revised tasks match remarks/EO, returns score and corrections if needed.
    Returns: dict with keys 'score', 'verdict', and optionally 'tasks', 'summary'
    """
    prompt = _build_prompt(REWIRE_TASKS_CHECK_SYSTEM_PROMPT, REWIRE_TASKS_CHECK_HUMAN_TEMPLATE)
    llm = _build_llm(model_name=model_name)
    chain = prompt | llm
    result = chain.invoke({
        "eo": eo,
        "remarks": remarks,
        "original_tasks": original_tasks,
        "summary": summary,
        "revised_tasks": revised_tasks,
    })
    if hasattr(result, "content"):
        content = result.content
        if isinstance(content, str):
            import json
            try:
                return json.loads(content)
            except Exception:
                return {"content": content}
        return content
    return result

def generate_task_update_llm(
    employee_role: str,
    raw_update: str,
    task: dict,
    model_name: Optional[str] = None,
) -> dict:
    """
    Calls LLM to extract a structured task update from an employee's email update.
    Returns: dict with required fields.
    """
    prompt = _build_prompt(TASK_UPDATE_SYSTEM_PROMPT, TASK_UPDATE_HUMAN_TEMPLATE)
    llm = _build_llm(model_name=model_name)
    chain = prompt | llm
    result = chain.invoke({
        "employee_role": employee_role,
        "raw_update": raw_update,
        "task": task,
    })
    if hasattr(result, "content"):
        content = result.content
        if isinstance(content, str):
            import json
            try:
                return json.loads(content)
            except Exception:
                return {"content": content}
        return content
    return result

def generate_task_summaries_llm(
    task_update_list: list,
    EO: str,
    model_name: Optional[str] = None,
) -> list:
    """
    Calls LLM to add a 'summary' field to each task update in the list.
    Returns: list of dicts, each with a 'summary' field added.
    """
    prompt = _build_prompt(TASK_SUMMARY_SYSTEM_PROMPT, TASK_SUMMARY_HUMAN_TEMPLATE)
    llm = _build_llm(model_name=model_name)
    chain = prompt | llm
    result = chain.invoke({
        "task_update_list": task_update_list,
        "EO": EO,
    })
    if hasattr(result, "content"):
        content = result.content
        if isinstance(content, str):
            import json
            try:
                return json.loads(content)
            except Exception:
                return {"content": content}
        return content
    return result

def generate_eo_weekly_summary_llm(
    six_day_summary: list,
    EO: str,
    tasks: list,
    model_name: Optional[str] = None,
) -> dict:
    """
    Calls LLM to generate a comprehensive weekly summary report for a single EO.
    Returns: dict with the required summary fields.
    """
    prompt = _build_prompt(EO_WEEKLY_SUMMARY_SYSTEM_PROMPT, EO_WEEKLY_SUMMARY_HUMAN_TEMPLATE)
    llm = _build_llm(model_name=model_name)
    chain = prompt | llm
    result = chain.invoke({
        "six_day_summary": six_day_summary,
        "EO": EO,
        "tasks": tasks,
    })
    if hasattr(result, "content"):
        content = result.content
        if isinstance(content, str):
            import json
            try:
                return json.loads(content)
            except Exception:
                return {"content": content}
        return content
    return result
