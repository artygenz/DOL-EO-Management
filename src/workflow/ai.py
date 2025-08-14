from typing import List
from src.workflow.dto import LLMTask
from src.app.extract_directives import extract_directives
from src.workflow.mappers import llm_task_to_taskcreate  # you provide this

def extract_tasks(body_text: str) -> List:
    """
    Wrap your existing AI function so the workflow code depends on a stable API.
    Expect extract_tasks_from_text() to return a list[dict] like:
      [{"title": "...", "description": "...", "assignee_email": "...", "due_date": "..."}]
    """
    
    try:
        data = extract_directives(body_text)
    except Exception as e:
        # log and fail soft: return empty, let pipeline continue
        print(f"[AI] extractor failed: {e!r}")
        return []

    items = []

    for raw in data.get("tasks", []):
        try:
            llm = LLMTask.model_validate(raw)  # robust parse/validate
            items.append(llm_task_to_taskcreate(llm))
        except Exception as e:
            print(f"[AI] skip malformed task item: {e!r} :: {raw!r}")
            continue
    return items

    