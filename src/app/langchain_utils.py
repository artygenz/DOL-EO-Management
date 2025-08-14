"""
langchain_utils.py
LangChain orchestration for extracting structured tasks from an EO string.

This module encapsulates:
- Pydantic schemas (TaskModel, TasksModel) that define the strict output contract
- Prompt wiring (system + human) sourced from app.prompts
- ChatOpenAI configuration (model=gpt-4.1) with structured output
- Convenience functions to parse EO dates and invoke the chain

Environment:
- Reads OPENAI_API_KEY from .env or OS env using python-dotenv
- Optional: OPENAI_MODEL (defaults to gpt-4.1)

Notes:
- The LLM must return 'assignee' as an empty string. Assignment is done later by assign_tasks().
- Title is modeled as a string (despite an earlier typo in the informal spec).
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import List, Optional

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# Support running as a module or as a script from the 'app' directory
if __package__ is None or __package__ == "":
    import os
    import sys
    # Add project root to sys.path so 'import app.*' works when running 'python app/xyz.py'
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))


from .prompts import EO_EXTRACTION_SYSTEM_PROMPT, EO_EXTRACTION_HUMAN_TEMPLATE

# Load environment variables from .env if present
load_dotenv()

# -----------------------------
# Pydantic output data models
# -----------------------------


class TaskModel(BaseModel):
    """
    Single task item as produced by the LLM (with assignee intentionally empty).
    """

    id: int = Field(..., description="1-based sequential identifier for the task in the extracted list.")
    title: str = Field(..., description="Concise, informative title (6-12 words).")
    description: str = Field(..., description="1-3 sentence summary with expected outcome and EO section reference if obvious.")
    category_dept: str = Field(..., description="Mapped role/department label selected from the provided roles_text when possible.")
    assignee: str = Field(..., description='MUST be an empty string "". Assignment happens programmatically later.')
    status: str = Field(..., description='MUST be "Pending" at creation.')
    due_date: str = Field(..., description='YYYY-MM-DD if computable from EO relative deadlines, else "TBD".')
    created_at: str = Field(..., description="ISO 8601 datetime when the task list was generated (UTC).")


class TasksModel(BaseModel):
    """
    Top-level container returned by the LLM. Downstream systems expect this envelope.
    """

    tasks: List[TaskModel] = Field(default_factory=list, description="Ordered list of extracted tasks.")


# -----------------------------
# Helpers
# -----------------------------


def _parse_eo_date(eo_text: str) -> Optional[str]:
    """
    Attempt to parse the EO's official date from free-form text.

    Strategy:
    - Search for patterns like 'March 25, 2025' anywhere in the EO text.
    - If found, convert to 'YYYY-MM-DD' and return.
    - If multiple matches exist, return the first.

    Parameters
    ----------
    eo_text : str
        The full Executive Order text.

    Returns
    -------
    Optional[str]
        Parsed date in 'YYYY-MM-DD' or None if not found.
    """
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
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
    """
    Returns the current UTC time in ISO 8601 format.

    Returns
    -------
    str
        e.g., '2025-08-08T03:10:45.123456+00:00'
    """
    return datetime.now(timezone.utc).isoformat()


# -----------------------------
# Chain construction
# -----------------------------


def _build_chain(model_name: Optional[str] = None) -> ChatOpenAI:
    """
    Construct a ChatOpenAI model configured for structured output conforming to TasksModel.

    Parameters
    ----------
    model_name : Optional[str]
        The OpenAI chat model to use. Defaults to env OPENAI_MODEL or 'gpt-4.1'.

    Returns
    -------
    ChatOpenAI
        A model instance wrapped to emit TasksModel via with_structured_output.
    """
    resolved_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4.1")
    llm = ChatOpenAI(model=resolved_model, temperature=0)
    structured_llm = llm.with_structured_output(TasksModel)
    return structured_llm


def _build_prompt() -> ChatPromptTemplate:
    """
    Assemble the ChatPromptTemplate using centralized prompt strings.

    Returns
    -------
    ChatPromptTemplate
        The composed prompt (system + human) with required variables.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", EO_EXTRACTION_SYSTEM_PROMPT),
            ("human", EO_EXTRACTION_HUMAN_TEMPLATE),
        ]
    )
    return prompt


# -----------------------------
# Public API
# -----------------------------


def extract_tasks(
    eo_text: str,
    roles_text: str,
    eo_date: Optional[str] = None,
    now_utc: Optional[str] = None,
    model_name: Optional[str] = None,
) -> TasksModel:
    """
    Run the LangChain pipeline to extract structured tasks from an EO text.

    Parameters
    ----------
    eo_text : str
        Full Executive Order content (already converted to text).
        IMPORTANT: This function doesn't care where the string came from (Gmail, S3, DB).
    roles_text : str
        Roles catalog (newline-delimited). The LLM will map category_dept to these labels where possible.
    eo_date : Optional[str]
        EO official date (YYYY-MM-DD). If None, a best-effort parser will attempt to detect it from eo_text.
    now_utc : Optional[str]
        Current UTC timestamp (ISO 8601). If None, defaults to the current time.
    model_name : Optional[str]
        OpenAI chat model, defaults to env OPENAI_MODEL or 'gpt-4.1'.

    Returns
    -------
    TasksModel
        Parsed and validated container of tasks (with assignee intentionally empty).
    """
    # Resolve scheduling context
    eo_date_final = eo_date or _parse_eo_date(eo_text)
    now_utc_final = now_utc or _now_utc_iso()

    # Construct prompt and structured model
    prompt = _build_prompt()
    structured_llm = _build_chain(model_name=model_name)

    # Compose LCEL chain: prompt -> structured_llm (emits TasksModel)
    chain = prompt | structured_llm

    # Invoke with required variables
    result: TasksModel = chain.invoke(
        {
            "eo_text": eo_text,
            "roles_text": roles_text,
            "eo_date": eo_date_final or "",
            "now_utc": now_utc_final,
        }
    )

    # Ensure all assignees are empty per contract (defense-in-depth)
    for t in result.tasks:
        t.assignee = ""

    return result
