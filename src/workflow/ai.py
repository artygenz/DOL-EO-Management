from typing import List, Dict
from src.workflow.dto import LLMTask
from src.ai.extract_directives import extract_directives, assign_tasks
from src.ai.rewire_tasks import generate_task_update_from_update_email, generate_summary_from_list_of_task_updates
from src.workflow.mappers import llm_task_to_taskcreate  # you provide this
from src.db.users import build_roles_with_members_text

def clean_eo_text(body_text: str) -> str:
    """Remove any hardcoded role information from EO text that might confuse the LLM."""
    # Remove any ROLES_DEMO or similar hardcoded role sections
    lines = body_text.split('\n')
    cleaned_lines = []
    skip_mode = False
    
    for i, line in enumerate(lines):
        # Stop processing if we hit role-related markers
        if any(marker in line for marker in ['ROLES_DEMO =', 'ROLES_WITH_MEMBERS_DEMO =', 'ROLES_DEMO =']):
            skip_mode = True
            continue
        # Look for the specific pattern that indicates the start of hardcoded roles
        if 'Newline-delimited ROLES catalog used by the LLM' in line:
            skip_mode = True
            continue
        if skip_mode and line.strip() == '':
            skip_mode = False
            continue
        if not skip_mode:
            cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines)
    return result

def extract_tasks(body_text: str) -> List:
    """
    Wrap your existing AI function so the workflow code depends on a stable API.
    Expect extract_tasks_from_text() to return a list[dict] like:
      [{"title": "...", "description": "...", "assignee_email": "...", "due_date": "..."}]
    """
    
    try:
        # TEMPORARILY: Skip cleaning to see the raw EO text
        cleaned_body_text = body_text
        
        # Get real org roles from database instead of hardcoded demo
        roles_text = build_roles_with_members_text()
        
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
        
        # Step 1: Extract tasks with empty assignees
        data = extract_directives(cleaned_body_text, roles_text)
        
        # Step 2: Assign team members to tasks
        data = assign_tasks(data, roles_text)
        
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

def extract_daily_task_updates(email_body: str, user_tasks: List[Dict]) -> Dict:
    """
    Extract task updates from a daily update email using existing AI infrastructure.
    
    Args:
        email_body: The email body text
        user_tasks: List of user's active tasks with id and title
    
    Returns:
        Dict with case (C1/C2/C3) and extracted updates
    """
    try:
            # Debug logging removed for production
        
        # Handle edge cases first
        if not email_body or not email_body.strip():
            return {
                "case": "C1",
                "updates": [],
                "unmatched_mentions": []
            }
        
        if not user_tasks:
            return {
                "case": "C1",
                "updates": [],
                "unmatched_mentions": [email_body]
            }
        
        # Determine the case based on email structure
        case = _determine_email_case(email_body, user_tasks)
        
        updates = []
        unmatched_mentions = []
        
        if case == "C3":
            # Single task update - use existing AI function
            if len(user_tasks) == 1:
                task = user_tasks[0]
                # Check if the task is actually mentioned in the email
                task_title_lower = task['title'].lower()
                email_lower = email_body.lower()
                
                if task_title_lower in email_lower:
                    employee_role = "Employee"  # Default role, could be enhanced
                    
                    try:
                        # Use existing AI function for single task
                        structured_update = generate_task_update_from_update_email(
                            employee_role=employee_role,
                            raw_update=email_body,
                            task=task
                        )
                        
                        # Only add update if we got meaningful data
                        if structured_update and isinstance(structured_update, dict):
                            update = {
                                "task_id": task['id'],
                                "status": _map_status(structured_update.get('status_note', '')),
                                "progress_pct": structured_update.get('progress_pct'),
                                "notes": structured_update.get('status_note'),
                                "blockers": structured_update.get('blockers', []),
                                "risks": structured_update.get('risks', []),
                                "eta": None,  # Not in existing format
                                "spent_hours": structured_update.get('hours_spent'),
                                "ai_summary": structured_update.get('summary', '')  # Store AI-generated summary
                            }
                            updates.append(update)
                    except Exception as e:
                        print(f"[AI] Error processing single task update: {e}")
                        unmatched_mentions.append(email_body)
                else:
                    print(f"[AI] C3 case - task '{task['title']}' not mentioned in email, skipping extraction")
            
        elif case == "C2":
            # Multiple tasks with detailed breakdown - parse each task section
            updates = _extract_multiple_task_updates(email_body, user_tasks)
            
        elif case == "C1":
            # Consolidated update - for C1 case, always send all tasks to LLM
            # Let the LLM figure out what's relevant from the unstructured email
            print(f"[AI] C1 case - sending all {len(user_tasks)} user tasks to LLM for extraction")
            print(f"[AI] C1 case - email body: {email_body[:100]}...")
            
            # Always process all user tasks for C1 - let LLM decide what's relevant
            updates = _extract_consolidated_updates(email_body, user_tasks)
        
        # Check for unmatched mentions
        mentioned_tasks = [update.get('task_id') for update in updates]
        for task in user_tasks:
            if task['id'] not in mentioned_tasks and task['title'].lower() in email_body.lower():
                unmatched_mentions.append(f"Task: {task['title']}")
        
        return {
            "case": case,
            "updates": updates,
            "unmatched_mentions": unmatched_mentions
        }
        
    except Exception as e:
        print(f"[AI] daily update extraction failed: {e!r}")
        return {
            "case": "C1",
            "updates": [],
            "unmatched_mentions": [email_body]
        }

def _determine_email_case(email_body: str, user_tasks: List[Dict]) -> str:
    """Determine if email is C1, C2, or C3 format based on EMAIL STRUCTURE, not task count."""
    email_lower = email_body.lower()
    
    # Check for C2 indicators first (detailed structured breakdown)
    if "task:" in email_lower and "status:" in email_lower:
        task_count = email_lower.count("task:")
        if task_count > 1:
            return "C2"
    
    # Check for C3 indicators (structured single task format)
    # C3 should have clear structure like "Task: X, Status: Y, Progress: Z"
    if ("task:" in email_lower and "status:" in email_lower) or \
       ("progress:" in email_lower and "status:" in email_lower):
        return "C3"
    
    # Everything else is C1 (unstructured, casual email)
    # This includes casual updates, text-message style, or any unstructured format
    return "C1"

def _extract_multiple_task_updates(email_body: str, user_tasks: List[Dict]) -> List[Dict]:
    """Extract updates for multiple tasks in C2 format."""
    updates = []
    
    # Split email into sections by "Task:" headers
    sections = email_body.split("Task:")
    
    for section in sections[1:]:  # Skip first empty section
        lines = section.strip().split('\n')
        if not lines:
            continue
            
        # Extract task title from first line
        task_title = lines[0].strip()
        
        # Find matching task
        matching_task = None
        for task in user_tasks:
            if task['title'].lower() in task_title.lower():
                matching_task = task
                break
        
        if not matching_task:
            continue
        
        # Extract update information from section
        section_text = '\n'.join(lines)
        employee_role = "Employee"
        
        try:
            structured_update = generate_task_update_from_update_email(
                employee_role=employee_role,
                raw_update=section_text,
                task=matching_task
            )
            
            update = {
                "task_id": matching_task['id'],
                "status": _map_status(structured_update.get('status_note', '')),
                "progress_pct": structured_update.get('progress_pct'),
                "notes": structured_update.get('status_note'),
                "blockers": structured_update.get('blockers', []),
                "risks": structured_update.get('risks', []),
                "eta": None,
                "spent_hours": structured_update.get('hours_spent'),
                "ai_summary": structured_update.get('summary', '')  # Store AI-generated summary
            }
            updates.append(update)
            
        except Exception as e:
            print(f"[AI] Error processing task section: {e}")
            continue
    
    return updates

def _extract_consolidated_updates(email_body: str, user_tasks: List[Dict]) -> List[Dict]:
    """Extract updates for multiple tasks in C1 format."""
    updates = []
    
    
    # For consolidated updates, try to extract updates for each provided task
    # (The calling function has already filtered to relevant tasks)
    for task in user_tasks:
        employee_role = "Employee"
        
        try:
            structured_update = generate_task_update_from_update_email(
                employee_role=employee_role,
                raw_update=email_body,
                task=task
            )
            
            # Only add update if we got meaningful data and LLM is confident
            if structured_update and isinstance(structured_update, dict):
                confidence = structured_update.get('extraction_confidence', 0)
                
                # Only include updates where LLM is reasonably confident (>20%)
                if confidence > 20:
                    update = {
                        "task_id": task['id'],
                        "status": _map_status(structured_update.get('status_note', '')),
                        "progress_pct": structured_update.get('progress_pct'),
                        "notes": structured_update.get('status_note'),
                        "blockers": structured_update.get('blockers', []),
                        "risks": structured_update.get('risks', []),
                        "eta": None,
                        "spent_hours": structured_update.get('hours_spent'),
                        "ai_summary": structured_update.get('summary', ''),  # Store AI-generated summary
                        "extraction_confidence": confidence
                    }
                    updates.append(update)
                else:
                    pass
            else:
                pass
            
        except Exception as e:
            print(f"[AI] Error processing consolidated update for task {task['title']}: {e}")
            continue
    
    return updates

def _map_status(status_note: str) -> str:
    """Map status note to standardized status."""
    status_lower = status_note.lower()
    
    if 'not started' in status_lower or 'notstarted' in status_lower:
        return "NotStarted"
    elif 'in progress' in status_lower or 'inprogress' in status_lower:
        return "InProgress"
    elif 'blocked' in status_lower:
        return "Blocked"
    elif 'completed' in status_lower or 'done' in status_lower:
        return "Completed"
    else:
        return "InProgress"  # Default

def generate_daily_eo_summary(eo_id: str, task_updates: List[Dict], eo_context: str) -> Dict:
    """
    Generate a daily summary for an EO based on task updates using existing AI infrastructure.
    
    Args:
        eo_id: Executive Order ID
        task_updates: List of task updates for the day
        eo_context: EO title and description for context
    
    Returns:
        Dict with summary information
    """
    try:
        # Convert our format to the format expected by existing AI function
        task_update_list = []
        for update in task_updates:
            task_update_list.append({
                "task_title": update.get('task_title', 'Unknown Task'),
                "assignee": update.get('user_name', 'Unknown User'),
                "progress_pct": update.get('progress_pct', 0),
                "hours_spent": update.get('spent_hours', 0),
                "status_note": update.get('notes', ''),
                "blockers": update.get('blockers', []),
                "risks": update.get('risks', []),
                "next_actions": []
            })
        
        # Use existing AI function to generate summaries
        summarized_updates = generate_summary_from_list_of_task_updates(task_update_list, eo_context)
        
        # Count updates and calculate progress
        total_updates = len(task_updates)
        completed_tasks = sum(1 for update in task_updates if update.get('status') == 'Completed')
        in_progress_tasks = sum(1 for update in task_updates if update.get('status') == 'InProgress')
        blocked_tasks = sum(1 for update in task_updates if update.get('status') == 'Blocked')
        
        # Get the actual total number of tasks for this EO from the database
        from src.db.session import SessionLocal
        from src.models.task import Task
        with SessionLocal() as db:
            total_tasks_count = db.query(Task).filter(Task.eo_id == eo_id).count()
        
        # Collect blockers and risks
        all_blockers = []
        all_risks = []
        attention_items = []
        
        for update in task_updates:
            if update.get('blockers'):
                all_blockers.extend(update['blockers'])
            if update.get('risks'):
                all_risks.extend(update['risks'])
            if update.get('status') == 'Blocked':
                attention_items.append(f"Task {update.get('task_title', 'Unknown')} is blocked")
        
        # Generate summary text
        progress_summary = f"""
Daily Progress Summary for {eo_context}

Tasks Updated: {total_updates}
- Completed: {completed_tasks}
- In Progress: {in_progress_tasks}
- Blocked: {blocked_tasks}

Overall Progress: {completed_tasks}/{total_updates} tasks completed
        """.strip()
        
        return {
            "progress_summary": progress_summary,
            "key_blockers": list(set(all_blockers)) if all_blockers else None,
            "risks": list(set(all_risks)) if all_risks else None,
            "attention_items": attention_items if attention_items else None,
            "total_tasks": total_tasks_count,  # ✅ FIXED: Actual total tasks in EO
            "updated_tasks": total_updates     # ✅ CORRECT: Tasks that received updates today
        }
        
    except Exception as e:
        print(f"[AI] daily summary generation failed: {e!r}")
        return {
            "progress_summary": "Error generating summary",
            "key_blockers": None,
            "risks": None,
            "attention_items": None,
            "total_tasks": 0,  # Will be 0 on error
            "updated_tasks": 0  # Will be 0 on error
        }
