from typing import List
from src.workflow.dto import LLMTask
from src.app.extract_directives import extract_directives, assign_tasks
from src.workflow.mappers import llm_task_to_taskcreate  # you provide this
from src.db.users import build_roles_with_members_text

def clean_eo_text(body_text: str) -> str:
    """Remove any hardcoded role information from EO text that might confuse the LLM."""
    # Remove any ROLES_DEMO or similar hardcoded role sections
    lines = body_text.split('\n')
    cleaned_lines = []
    skip_mode = False
    
    for line in lines:
        # Stop processing if we hit role-related markers
        if any(marker in line for marker in ['ROLES_DEMO', 'ROLES_WITH_MEMBERS_DEMO', 'Newline-delimited ROLES']):
            skip_mode = True
            continue
        if skip_mode and line.strip() == '':
            skip_mode = False
            continue
        if not skip_mode:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def extract_tasks(body_text: str) -> List:
    """
    Wrap your existing AI function so the workflow code depends on a stable API.
    Expect extract_tasks_from_text() to return a list[dict] like:
      [{"title": "...", "description": "...", "assignee_email": "...", "due_date": "..."}]
    """
    
    try:
        # Clean the EO text to remove any hardcoded role information
        cleaned_body_text = clean_eo_text(body_text)
        
        # Get real org roles from database instead of hardcoded demo
        roles_text = build_roles_with_members_text()
        print(f"[DEBUG] Available roles from DB:\n{roles_text}")
        
        if not roles_text.strip():
            # Fallback to demo roles if no users in DB yet
            roles_text = """Secretary of the Treasury (in consultation with OMB Director)
All Agency Heads
Secretary of the Treasury
Agency Heads / Certifying Officers
Secretary of the Treasury & Agency Certifying Officers
OMB Director
OMB Director (in consultation with Secretary of the Treasury)
CFO Act Agency Heads
Heads of agencies with disbursing authority under 31 U.S.C. 3321(c) (e.g., DoD, DHS, DOJ) + Secretary of the Treasury
Secretary of the Treasury & NTDOs remaining after consolidation process
Secretary of the Treasury (in coordination with agency heads)
Agency Heads with authority under 31 U.S.C. 3321(b)"""
            print(f"[DEBUG] Using fallback roles:\n{roles_text}")
        
        # Step 1: Extract tasks with empty assignees
        data = extract_directives(cleaned_body_text, roles_text)
        print(f"[DEBUG] LLM extracted {len(data.get('tasks', []))} tasks")
        
        # Step 2: Assign team members to tasks
        data = assign_tasks(data, roles_text)
        
        # Debug: Check what assignees were assigned
        for i, task in enumerate(data.get('tasks', [])):
            print(f"[DEBUG] Task {i+1}: category='{task.get('category_dept')}' -> assignee='{task.get('assignee')}'")
        
    except Exception as e:
        # log and fail soft: return empty, let pipeline continue
        print(f"[AI] extractor failed: {e!r}")
        return []

    items = []

    for raw in data.get("tasks", []):
        if str(raw.get("due_date", "")).upper() == "TBD":
            raw["due_date"] = None
        try:
            llm = LLMTask.model_validate(raw)  # robust parse/validate
            items.append(llm)
        except Exception as e:
            print(f"[AI] skip malformed task item: {e!r} :: {raw!r}")
            continue
    return items
