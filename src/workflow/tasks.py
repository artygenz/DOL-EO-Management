from typing import Dict
from datetime import datetime
from celery import states
from src.workflow.celery_app import celery_app
from src.workflow.dto import EOIn, LLMTask
from src.workflow import repository as repo
from src.workflow.ai import extract_tasks
from src.email.email_template_builder import EmailTemplateBuilder
from src.email.queued_email_service import QueuedEmailService
# Use Attachment from redis_email_processor
from dataclasses import dataclass

@dataclass
class Attachment:
    filename: str
    content_type: str
    data: bytes
from src.db.session import SessionLocal
from src.models.task import Task
from src.models.user import User
from sqlalchemy import select

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.store_email")
def store_email(eo_payload: Dict):
    """
    1) Upsert EO row (idempotent by message_id)
    2) Process S3 attachment if available
    3) Queue AI extraction
    """

    print(f"\n=== EO Processing Started ===")
    print(f"Subject: {eo_payload.get('subject', 'N/A')}")
    print(f"Sender: {eo_payload.get('sender', 'N/A')}")
    print(f"Message ID: {eo_payload.get('message_id', 'N/A')}")
    print(f"================================\n")
    
    eo = EOIn(**eo_payload)
    
    # Log inbound EO email first to get email log ID for organized structure
    email_log_id = None
    try:
        email_log = repo.save_email_log(
            direction="incoming",
            subject=eo.subject,
            sender=eo.sender,
            recipients=eo.recipients,
            raw_content=eo.body_text,
            related_eo_id=None,
        )
        email_log_id = str(email_log.id)
        print(f"Email logged with ID: {email_log_id}")

    except Exception as e:
        print(f"Warning: Could not save email log: {e}")

    # Process S3 attachment if available
    eo_text = eo.body_text
    if eo.raw_mime_s3_key:
        print(f"Processing S3 attachment: {eo.raw_mime_s3_key}")
        try:
            from src.email.s3_service import process_eo_attachment
            success, result = process_eo_attachment(eo.raw_mime_s3_key)
            
            if success:
                eo_text = result
                print(f"Successfully extracted text from S3 attachment: {len(eo_text)} characters")
            else:
                print(f"Failed to process S3 attachment: {result}")
                # Continue with body_text as fallback
        except Exception as e:
            print(f"Error processing S3 attachment: {e}")
            # Continue with body_text as fallback

    eo_row = repo.upsert_executive_order(eo)
    repo.update_eo_status(eo_row.id, "received")
    
    # Chain to AI extraction with processed text
    ai_extract_tasks.delay(eo_row.id, eo_text)
    return {"eo_id": str(eo_row.id), "email_log_id": email_log_id}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.ai_extract_tasks")
def ai_extract_tasks(eo_id: str, body_text: str):
    """
    1) Call AI to get task list
    2) Queue persistence
    """
    print(f"\n=== AI Task Extraction Started ===")
    print(f"EO ID: {eo_id}")
    print(f"Body text length: {len(body_text)} characters")
    
    tasks = extract_tasks(body_text)
    
    print(f"Extracted {len(tasks)} tasks from EO")
    print(f"=====================================\n")
    
    # Convert to serializable dicts for the next task
    serializable = [t.model_dump() for t in tasks]
    persist_tasks.delay(eo_id, serializable)
    return {"eo_id": eo_id, "task_count": len(serializable)}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.persist_tasks")
def persist_tasks(eo_id: str, tasks_payload: list[dict]):
    """
    1) Persist tasks
    2) Mark EO status
    """
    print(f"\n=== Task Persistence Started ===")
    print(f"EO ID: {eo_id}")
    print(f"Tasks to persist: {len(tasks_payload or [])}")
    
    from src.workflow.dto import TaskCreate
    to_create = []
    for d in tasks_payload or []:
        try:
            to_create.append(LLMTask.model_validate(d))
        except Exception as e:
            print(f"Warning: Dropping malformed task: {e}")

    count = repo.insert_tasks(eo_id, to_create)
    
    print(f"Successfully persisted {count} tasks")
    print(f"====================================\n")

    # 2) prepare a JSON-safe snapshot for Celery (don’t send Pydantic objects!)
    safe_for_email = [
        t.model_dump(mode="json") if hasattr(t, "model_dump") else d
        for t, d in zip(to_create, tasks_payload[:len(to_create)])
    ]

    # 3) queue email build/send
    send_pmo_review_email.delay(eo_id, safe_for_email)

    return {"eo_id": eo_id, "inserted": count}


@celery_app.task(bind=True, acks_late=True, max_retries=3, name="src.workflow.tasks.send_pmo_review_email")
def send_pmo_review_email(self, eo_id: str, task_list: list):
    """
    1) Validate inputs
    2) Load EO by ID
    3) Build email via template service (subject/text/html/attachments)
    4) Send via email service (PMO recipient)
    """
    # --- checks ---
    if not eo_id:
        raise ValueError("eo_id is required")
    if task_list is None:
        task_list = []

    # --- load EO from DB ---
    eo = repo.get_executive_order(eo_id)
    if not eo:
        raise ValueError(f"ExecutiveOrder not found for id={eo_id}")
    
     # Resolve PMO recipient: DB role → env fallback
    import os
    pmo_email = os.getenv("PMO_EMAIL_ADDRESS", "kevin.brown@lumenlighthouse.ai")  # fallback for backward compatibility

   

    print(f"\n=== PMO Review Email Started ===")
    print(f"EO ID: {eo_id}")
    print(f"EO Title: {eo.title}")
    print(f"PMO Email: {pmo_email}")
    print(f"Tasks: {len(task_list)}")
    
    # --- build email via template service ---
    built = EmailTemplateBuilder.build_pmo_review(eo, task_list)

    # Save email log first to get the ID for organized file structure
    try:
        email_log = repo.save_email_log(
            direction="outgoing",
            subject=built.subject,
            sender=None,
            recipients=[pmo_email],
            raw_content=built.body_text,
            related_eo_id=eo.id,
        )
        email_log_id = str(email_log.id)
    except Exception as e:
        print(f"Warning: Could not save email log: {e}")
        email_log_id = None

    svc = QueuedEmailService()
    attachments = [Attachment(fn, ct, data) for (fn, ct, data) in built.attachments]

    message_id = svc.send_and_save(
        to=[pmo_email],
        subject=built.subject,
        body_text=built.body_text,
        body_html=built.body_html,
        attachments=attachments,
        headers=built.headers,
        email_log_id=email_log_id,
        email_type="eo_review"
    )

    print(f"PMO review email sent successfully")
    print(f"Message ID: {message_id}")
    print(f"================================\n")
    
    # (optional) persist outbound record here if you have a model/table
    return {"eo_id": eo_id, "sent_to": pmo_email, "message_id": message_id, "tasks": len(task_list)}

# --- NEW: PMO processing and follow-ups ---
from src.workflow.dto import PMOEmailIn, PMOReply
from src.workflow.parse_pmo import parse_pmo_email, extract_eo_id_from_subject

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.process_pmo_response")
def process_pmo_response(email_payload: Dict):
    # Basic association heuristics
    email = PMOEmailIn(**email_payload)
    related_eo_id = email.related_eo_id or extract_eo_id_from_subject(email.subject)
    email_log_id = email_payload.get("email_log_id")  # Get email log ID for organized structure

    # Validate that the EO exists
    if related_eo_id:
        eo = repo.get_executive_order(related_eo_id)
        if not eo:
            error_msg = f"EO with ID '{related_eo_id}' not found in database. Cannot process PMO response."
            print(f"ERROR: {error_msg}")
            return {
                "eo_id": related_eo_id, 
                "error": error_msg, 
                "intent": "ERROR", 
                "approved": 0, 
                "rejected": 0
            }
        print(f"Validated EO exists: {related_eo_id} - {eo.title}")
    else:
        error_msg = "No EO ID found in PMO email (neither in related_eo_id nor subject). Cannot process PMO response."
        print(f"ERROR: {error_msg}")
        return {
            "eo_id": None, 
            "error": error_msg, 
            "intent": "ERROR", 
            "approved": 0, 
            "rejected": 0
        }

    parsed = parse_pmo_email(email.body_text)
    intent = parsed.get("intent")
    approve_ids: list[str] = parsed.get("approve_task_ids") or []
    reject_ids: list[str] = parsed.get("reject_task_ids") or []
    global_remarks: str | None = parsed.get("remarks")
    per_task_remarks: dict[str, str] = parsed.get("per_task_remarks") or {}

    # Map simple task IDs to database UUIDs if needed
    if related_eo_id and (approve_ids or reject_ids):
        # Check if the IDs are simple numbers (1, 2, 3, etc.)
        if approve_ids and all(tid.isdigit() for tid in approve_ids):
            approve_ids = repo.map_simple_task_ids_to_uuids(related_eo_id, approve_ids)
            print(f"Mapped approved task IDs: {approve_ids}")
        
        if reject_ids and all(tid.isdigit() for tid in reject_ids):
            reject_ids = repo.map_simple_task_ids_to_uuids(related_eo_id, reject_ids)
            print(f"Mapped rejected task IDs: {reject_ids}")
        
        # Also map the per_task_remarks keys
        if per_task_remarks:
            mapped_per_task_remarks = {}
            all_simple_ids = list(per_task_remarks.keys())
            if all(tid.isdigit() for tid in all_simple_ids):
                mapped_ids = repo.map_simple_task_ids_to_uuids(related_eo_id, all_simple_ids)
                for simple_id, mapped_id in zip(all_simple_ids, mapped_ids):
                    if mapped_id:
                        mapped_per_task_remarks[mapped_id] = per_task_remarks[simple_id]
                per_task_remarks = mapped_per_task_remarks
                print(f"Mapped per-task remarks: {per_task_remarks}")

    # If intent is ALL variants, load task IDs by EO when possible
    if intent in ("APPROVE_ALL", "REJECT_ALL") and related_eo_id:
        if intent == "APPROVE_ALL":
            # For APPROVE_ALL, only approve tasks that are currently pending PMO approval
            pending_task_ids = repo.get_pending_task_ids_by_eo(related_eo_id)
            repo.update_tasks_status_and_remarks(pending_task_ids, status="approved", remarks="N/A")
            actual_approved_count = len(pending_task_ids)
        else:
            # For REJECT_ALL, reject all tasks for the EO
            task_ids = repo.get_task_ids_by_eo(related_eo_id)
            repo.update_tasks_status_and_remarks(task_ids, status="rejected", remarks=global_remarks or "")
            actual_rejected_count = len(task_ids)
    else:
        if approve_ids:
            repo.update_tasks_status_and_remarks(approve_ids, status="approved", remarks="N/A")
        if reject_ids:
            # First set global remarks on all
            repo.update_tasks_status_and_remarks(reject_ids, status="rejected", remarks=global_remarks or None)
            # Then overwrite per-task remarks if provided
            if per_task_remarks:
                repo.update_per_task_remarks(per_task_remarks)

    # Count actual approved/rejected tasks for return value
    actual_approved_count = len(approve_ids)
    actual_rejected_count = len(reject_ids)
    
    # Notify assignees if anything approved
    if intent in ("APPROVE_ALL", "APPROVE_SOME") and (approve_ids or intent == "APPROVE_ALL"):
        notify_assignees.delay(related_eo_id)

    # Handle rejected tasks remediation (later)
    if intent in ("REJECT_ALL", "APPROVE_SOME") and reject_ids:
        handle_rejected_tasks.delay(related_eo_id, reject_ids, global_remarks, per_task_remarks)

    return {"eo_id": related_eo_id, "intent": intent, "approved": actual_approved_count, "rejected": actual_rejected_count}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.notify_assignees")
def notify_assignees(eo_id: str | None):
    """
    Notify employees about their assigned tasks.
    1. Load EO and approved tasks
    2. Group tasks by assignee
    3. Send notification emails to each assignee
    """
    if not eo_id:
        return {"notified": 0}
    
    try:
        print(f"\n=== Employee Notification Started ===")
        print(f"EO ID: {eo_id}")
        
        # Load EO
        eo = repo.get_executive_order(eo_id)
        if not eo:
            return {"eo_id": eo_id, "error": "EO not found", "notified": 0}
        
        # Load all approved tasks for this EO
        with SessionLocal() as db:
            approved_tasks = db.execute(
                select(Task).where(
                    Task.eo_id == eo_id,
                    Task.status == "approved"
                ).order_by(Task.created_at)
            ).scalars().all()
        
        if not approved_tasks:
            print(f"No approved tasks found for EO {eo_id}")
            return {"eo_id": eo_id, "notified": 0}
        
        print(f"EO Title: {eo.title}")
        print(f"Total approved tasks: {len(approved_tasks)}")
        
        # Group tasks by assignee
        assignee_tasks = {}
        for task in approved_tasks:
            if task.assignee_id:
                assignee_id = str(task.assignee_id)
                if assignee_id not in assignee_tasks:
                    assignee_tasks[assignee_id] = []
                assignee_tasks[assignee_id].append(task)
        
        print(f"Found {len(assignee_tasks)} assignees to notify")
        
        # Send notification emails to each assignee
        notified_count = 0
        for assignee_id, tasks in assignee_tasks.items():
            try:
                # Get assignee details
                with SessionLocal() as db:
                    assignee = db.execute(
                        select(User).where(User.id == assignee_id)
                    ).scalar_one_or_none()
                
                if not assignee:
                    print(f"Assignee {assignee_id} not found, skipping")
                    continue
                
                # Convert tasks to dict format for email template
                task_dicts = []
                for task in tasks:
                    task_dict = {
                        "id": str(task.id),
                        "title": task.title,
                        "description": task.description,
                        "category": task.category,
                        "status": task.status,
                        "due_date": task.due_date.isoformat() if task.due_date else "TBD",
                        "remarks": task.remarks,
                        "assignee": assignee.name
                    }
                    task_dicts.append(task_dict)
                
                # Build email template
                built = EmailTemplateBuilder.build_employee_notification(
                    eo=eo,
                    assignee_email=assignee.email,
                    assignee_name=assignee.name,
                    tasks=task_dicts
                )
                
                # Save email log first to get the ID for organized structure
                email_log_id = None
                try:
                    email_log = repo.save_email_log(
                        direction="outgoing",
                        subject=built.subject,
                        sender=None,
                        recipients=[assignee.email],
                        raw_content=built.body_text,
                        related_eo_id=eo.id,
                    )
                    email_log_id = str(email_log.id)
                    print(f"Saved employee notification email log with ID: {email_log_id}")
                except Exception as e:
                    print(f"Warning: Could not save employee notification email log: {e}")
                
                # Send email
                svc = QueuedEmailService()
                attachments = [Attachment(fn, ct, data) for (fn, ct, data) in built.attachments]
                
                message_id = svc.send_and_save(
                    to=[assignee.email],
                    subject=built.subject,
                    body_text=built.body_text,
                    body_html=built.body_html,
                    attachments=attachments,
                    headers=built.headers,
                    email_log_id=email_log_id,
                    email_type="notify_employees"
                )
                
                print(f"✓ Notification sent to {assignee.name} ({assignee.email})")
                notified_count += 1
                
            except Exception as e:
                print(f"✗ Error sending notification to assignee {assignee_id}: {e}")
                continue
        
        print(f"Employee notification completed: {notified_count} emails sent")
        print(f"=====================================\n")
        
        return {"eo_id": eo_id, "notified": notified_count}
        
    except Exception as e:
        print(f"Error in notify_assignees: {e}")
        return {"eo_id": eo_id, "error": str(e), "notified": 0}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.handle_rejected_tasks")
def handle_rejected_tasks(eo_id: str | None, rejected_ids: list[str] | None, global_remarks: str | None, per_task_remarks: dict[str, str] | None):
    """
    Handle rejected tasks by:
    1. Loading rejected tasks from database
    2. Using LLM to rewire/improve tasks based on PMO remarks (global + per-task)
    3. Sending modified review email back to PMO
    """
    if not eo_id or not rejected_ids:
        return {"eo_id": eo_id, "rejected": len(rejected_ids or [])}
    
    try:
        # Load EO and rejected tasks
        eo = repo.get_executive_order(eo_id)
        if not eo:
            return {"eo_id": eo_id, "error": "EO not found"}
        
        # Load rejected tasks from database
        rejected_tasks = repo.get_tasks_by_ids(rejected_ids)
        if not rejected_tasks:
            return {"eo_id": eo_id, "error": "No rejected tasks found"}
        
        # Get all available roles for potential reassignment
        from src.db.users import build_roles_with_members_text
        roles_text = build_roles_with_members_text()
        
        # Build comprehensive remarks for each task
        per_task_remarks = per_task_remarks or {}
        task_remarks = {}
        
        for task in rejected_tasks:
            task_id_str = str(task.id)
            # Combine global remarks with per-task remarks
            task_remark_parts = []
            if global_remarks:
                task_remark_parts.append(f"Global feedback: {global_remarks}")
            if task_id_str in per_task_remarks:
                task_remark_parts.append(f"Task-specific feedback: {per_task_remarks[task_id_str]}")
            
            task_remarks[task_id_str] = " | ".join(task_remark_parts) if task_remark_parts else "Task needs improvement"
        
        # Convert tasks to dict format expected by rewire function
        tasks_dict = {
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "category_dept": task.category,
                    "assignee": "",  # Will be reassigned by assign_tasks
                    "status": "Pending",
                    "due_date": task.due_date.isoformat() if task.due_date else "TBD",
                    "created_at": task.created_at.isoformat(),
                    "remarks": task_remarks.get(str(task.id), "Task needs improvement"),  # Add remarks to each task
                }
                for task in rejected_tasks
            ]
        }
        
        # Use LLM to rewire tasks based on PMO remarks
        from src.app.rewire_tasks import rewire_tasks_with_remarks
        improved_result = rewire_tasks_with_remarks(
            eo=eo.description or "",
            remarks=global_remarks or "Tasks need improvement",
            tasks=tasks_dict,
            roles_text=roles_text
        )
        
        # Extract improved tasks and summary
        improved_tasks = improved_result.get("tasks", [])
        improvement_summary = improved_result.get("summary", "")
        
        print(f"LLM improved {len(improved_tasks)} tasks")
        print(f"Improvement summary: {improvement_summary}")
        
        # Update tasks in database with improved versions
        if improved_tasks:
            # Create a mapping from simple task ID to improved task data
            # The LLM returns simple IDs (1, 2, 3, 4, 5) but we need database UUIDs
            task_updates = {}
            for idx, improved_task in enumerate(improved_tasks):
                # Map simple ID to the corresponding rejected task UUID
                if idx < len(rejected_tasks):
                    task_uuid = str(rejected_tasks[idx].id)
                    # Create a copy and replace the LLM's simple ID with the database UUID
                    improved_task_copy = improved_task.copy()
                    improved_task_copy['id'] = task_uuid
                    task_updates[task_uuid] = improved_task_copy
                    print(f"Mapping improved task {improved_task.get('id')} to database UUID {task_uuid}")
            
            # Update tasks using repository method
            updated_count = repo.update_tasks_with_improved_data(task_updates)
            print(f"Updated {updated_count} tasks in database")
            
            # Send improved tasks back to PMO for review
            if updated_count > 0:
                # Pass the specific task IDs that were improved
                improved_task_ids = list(task_updates.keys())
                send_improved_tasks_to_pmo.delay(eo_id, improvement_summary, improved_task_ids)
            
            # TODO: Send modified review email back to PMO with improved tasks
        
        return {"eo_id": eo_id, "rejected": len(rejected_ids), "rewired": True}
        
    except Exception as e:
        print(f"[ERROR] handle_rejected_tasks failed: {e}")
        return {"eo_id": eo_id, "error": str(e)}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.send_improved_tasks_to_pmo")
def send_improved_tasks_to_pmo(eo_id: str, improvement_summary: str, improved_task_ids: list[str] = None):
    """
    Send improved tasks back to PMO for re-review after LLM improvements.
    Only sends the specific tasks that were just improved, not all tasks.
    
    Parameters
    ----------
    eo_id : str
        The Executive Order ID
    improvement_summary : str
        Summary of improvements made by LLM
    improved_task_ids : list[str], optional
        Specific task IDs that were improved. If not provided, falls back to looking for rejected tasks.
    """
    print(f"[DEBUG] send_improved_tasks_to_pmo started with eo_id: {eo_id}")
    
    if not eo_id:
        return {"error": "eo_id is required"}
    
    try:
        print(f"[DEBUG] Loading EO from database...")
        # Load EO from database
        eo = repo.get_executive_order(eo_id)
        if not eo:
            return {"error": f"ExecutiveOrder not found for id={eo_id}"}
        
        print(f"[DEBUG] EO loaded successfully: {eo.id}")
        print(f"[DEBUG] EO type: {type(eo)}")
        # Remove the problematic line that triggers lazy loading
        # print(f"[DEBUG] EO has relationships: {hasattr(eo, 'tasks')}")
        
        # Load specific improved task IDs, or fall back to rejected tasks
        if improved_task_ids:
            print(f"[DEBUG] Using provided improved task IDs: {len(improved_task_ids)} tasks")
            task_ids = improved_task_ids
        else:
            print(f"[DEBUG] No improved task IDs provided, falling back to rejected tasks...")
            task_ids = repo.get_task_ids_by_eo_and_status(eo_id, "rejected")
            
        if not task_ids:
            return {"error": "No tasks found to send for improved review"}
        
        print(f"[DEBUG] Found {len(task_ids)} improved task IDs: {task_ids[:3]}...")  # Show first 3
        
        # Convert tasks to format expected by email template
        print(f"[DEBUG] Converting tasks to dict format...")
        task_list = []
        with SessionLocal() as db:
            # Reload tasks in this session to avoid session issues
            for i, task_id in enumerate(task_ids):
                print(f"[DEBUG] Processing task {i+1}/{len(task_ids)}: {task_id}")
                task = db.get(Task, task_id)
                if task:
                    print(f"[DEBUG] Task {task_id} loaded, type: {type(task)}")
                    
                    # Get assignee name directly to avoid circular reference
                    assignee_name = "Unassigned"
                    if task.assignee_id:
                        print(f"[DEBUG] Task has assignee_id: {task.assignee_id}")
                        from src.models.user import User
                        assignee = db.get(User, task.assignee_id)
                        if assignee:
                            assignee_name = assignee.name
                            print(f"[DEBUG] Assignee name: {assignee_name}")
                    
                    task_dict = {
                        "id": str(task.id),  # Convert UUID to string
                        "title": task.title,
                        "description": task.description,
                        "category": task.category,
                        "status": task.status,
                        "due_date": task.due_date.isoformat() if task.due_date else "TBD",
                        "remarks": task.remarks,
                        "assignee": assignee_name
                    }
                    print(f"[DEBUG] Task dict created: {task_dict['id']} - {task_dict['title'][:50]}...")
                    task_list.append(task_dict)
                else:
                    print(f"[DEBUG] Task {task_id} not found in database")
        
        print(f"[DEBUG] Task list created with {len(task_list)} tasks")
        print(f"[DEBUG] First task dict: {task_list[0] if task_list else 'None'}")
        
        # Resolve PMO recipient
        import os
        pmo_email = os.getenv("PMO_EMAIL_ADDRESS", "kevin.brown@lumenlighthouse.ai")  # fallback for backward compatibility
        print(f"[DEBUG] PMO email: {pmo_email}")
        
        # Convert EO to simple dict to avoid circular reference issues
        print(f"[DEBUG] Converting EO to dict...")
        eo_dict = {
            "id": eo.id,
            "title": eo.title,
            "message_id": eo.message_id,
            "description": eo.description,
            "source_email": eo.source_email,
            "received_at": eo.received_at,
            "pdf_url": eo.pdf_url,
            "status": eo.status,
            "created_at": eo.created_at,
            "updated_at": eo.updated_at
        }
        print(f"[DEBUG] EO dict created: {eo_dict['id']} - {eo_dict['title']}")
        print(f"[DEBUG] EO dict type: {type(eo_dict)}")
        
        # Build email with improved tasks
        print(f"[DEBUG] Building email template...")
        try:
            built = EmailTemplateBuilder.build_improved_tasks_review(eo_dict, task_list, improvement_summary)
            print(f"[DEBUG] Email template built successfully")
            print(f"[DEBUG] Built object type: {type(built)}")
            print(f"[DEBUG] Built object attributes: {dir(built)}")
        except Exception as e:
            print(f"[ERROR] Failed to build email template: {e}")
            raise
        
        # Save email log first to get the ID for organized file structure
        print(f"[DEBUG] Saving email log...")
        try:
            email_log = repo.save_email_log(
                direction="outgoing",
                subject=built.subject,
                sender=None,
                recipients=[pmo_email],
                raw_content=built.body_text,
                related_eo_id=eo_dict["id"],
            )
            email_log_id = str(email_log.id)
            print(f"[DEBUG] Email log saved with ID: {email_log_id}")
        except Exception as e:
            print(f"Warning: Could not save email log: {e}")
            email_log_id = None
        
        # Send email
        print(f"[DEBUG] Creating EmailService...")
        svc = QueuedEmailService()
        
        print(f"[DEBUG] Creating attachments...")
        try:
            attachments = [Attachment(fn, ct, data) for (fn, ct, data) in built.attachments]
            print(f"[DEBUG] Created {len(attachments)} attachments")
        except Exception as e:
            print(f"[ERROR] Failed to create attachments: {e}")
            raise
        
        print(f"[DEBUG] Sending email...")
        try:
            message_id = svc.send_and_save(
                to=[pmo_email],
                subject=built.subject,
                body_text=built.body_text,
                body_html=built.body_html,
                attachments=attachments,
                headers=built.headers,
                email_log_id=email_log_id,
                email_type="improved_review"
            )
            print(f"[DEBUG] Email sent successfully with message_id: {message_id}")
        except Exception as e:
            print(f"[ERROR] Failed to send email: {e}")
            raise
        
        print(f"[DEBUG] Creating return dict...")
        result = {
            "eo_id": eo_id,
            "sent_to": pmo_email,
            "message_id": message_id,
            "tasks": len(task_list),
            "improvement_summary": improvement_summary
        }
        print(f"[DEBUG] Return dict created: {result}")
        
        print(f"[DEBUG] send_improved_tasks_to_pmo completed successfully")
        return result
        
    except Exception as e:
        print(f"[ERROR] send_improved_tasks_to_pmo failed: {e}")
        print(f"[ERROR] Exception type: {type(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return {"eo_id": eo_id, "error": str(e)}

# Daily Task Update Tasks
@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.process_daily_update_email")
def process_daily_update_email(email_payload: Dict):
    """
    Process a daily task update email from an employee.
    
    1. Resolve user_id from sender email
    2. Fetch user's active tasks
    3. Extract task updates using AI
    4. Save updates to database
    """
    from src.workflow.dto import DailyUpdateEmailPayload
    from src.workflow.ai import extract_daily_task_updates
    from src.workflow import repository as repo
    from datetime import date, datetime, timezone
    import hashlib
    
    print(f"\n=== Daily Update Processing Started ===")
    print(f"Sender: {email_payload.get('sender')}")
    print(f"Subject: {email_payload.get('subject', 'N/A')}")
    print(f"Body length: {len(email_payload.get('body_text', ''))} characters")
    
    try:
        # Parse email payload
        email_data = DailyUpdateEmailPayload(**email_payload)
        
        # Resolve user by email
        user_id = repo.resolve_user_by_email(email_data.sender)
        if not user_id:
            print(f"Error: Could not resolve user for email: {email_data.sender}")
            return {"error": "User not found", "sender": email_data.sender}
        
        print(f"User ID: {user_id}")
        
        # Get user's active tasks
        user_tasks = repo.get_user_active_tasks(user_id)
        if not user_tasks:
            print(f"Warning: No active tasks found for user: {email_data.sender}")
            return {"error": "No active tasks", "sender": email_data.sender}
        
        print(f"Found {len(user_tasks)} active tasks for user")
        
        # Extract task updates using AI
        extraction_result = extract_daily_task_updates(email_data.body_text, user_tasks)
        
        # Process extracted updates
        updates_to_save = []
        today = date.today()
        
        # Check if email is late (after 6pm ET)
        email_time = email_data.received_at
        if email_time.tzinfo is None:
            email_time = email_time.replace(tzinfo=timezone.utc)
        
        # Convert to ET for deadline check
        import pytz
        et_tz = pytz.timezone('America/New_York')
        email_time_et = email_time.astimezone(et_tz)
        deadline_et = email_time_et.replace(hour=18, minute=0, second=0, microsecond=0)
        is_late = email_time_et > deadline_et
        
        for update in extraction_result.get('updates', []):
            # Find the task details
            task_id = update.get('task_id')
            task_details = next((t for t in user_tasks if t['id'] == task_id), None)
            
            if task_details:
                # Create unique dedupe hash based on task, user, and date (not email content)
                dedupe_content = f"{task_id}_{user_id}_{today}"
                dedupe_hash = hashlib.sha256(dedupe_content.encode()).hexdigest()
                
                update_data = {
                    'task_id': task_id,
                    'user_id': user_id,
                    'eo_id': task_details['eo_id'],
                    'date': today,
                    'progress_pct': update.get('progress_pct'),
                    'status': update.get('status'),
                    'notes': update.get('notes'),
                    'blockers': update.get('blockers'),
                    'risks': update.get('risks'),
                    'eta': update.get('eta'),
                    'spent_hours': update.get('spent_hours'),
                    'ai_summary': update.get('ai_summary'),
                    'source_email_message_id': email_data.message_id,
                    'dedupe_hash': dedupe_hash,
                    'is_late': is_late
                }
                updates_to_save.append(update_data)
        
        # Save updates to database
        saved_count = repo.save_task_updates(updates_to_save)
        
        print(f"Saved {saved_count} task updates for user {email_data.sender}")
        print(f"=====================================\n")
        
        return {
            "success": True,
            "sender": email_data.sender,
            "user_id": user_id,
            "extraction_case": extraction_result.get('case'),
            "updates_saved": saved_count,
            "unmatched_mentions": extraction_result.get('unmatched_mentions', []),
            "is_late": is_late
        }
        
    except Exception as e:
        print(f"Error processing daily update email: {e}")
        return {"error": str(e), "sender": email_payload.get('sender')}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.aggregate_daily_updates")
def aggregate_daily_updates(eo_id: str, target_date: str = None):
    """
    Aggregate daily updates for an EO and generate summary.
    
    1. Get all task updates for the EO and date
    2. Generate summary using AI
    3. Save summary to database
    4. Send email to PMOs
    """
    from src.workflow.ai import generate_daily_eo_summary
    from src.workflow import repository as repo
    # EmailService removed - using Redis queue only
    from datetime import date
    import pytz
    
    print(f"Aggregating daily updates for EO {eo_id} on {target_date}")
    
    try:
        # Parse target date
        if target_date:
            target_date = date.fromisoformat(target_date)
        else:
            target_date = date.today()
        
        # Get task updates for this EO and date
        task_updates = repo.get_task_updates_for_eo_date(eo_id, target_date)
        
        if not task_updates:
            print(f"No task updates found for EO {eo_id} on {target_date}")
            return {"error": "No updates found", "eo_id": eo_id, "date": str(target_date)}
        
        # Get EO context for summary
        from src.models.executive_order import ExecutiveOrder
        with repo.SessionLocal() as db:
            eo = db.get(ExecutiveOrder, eo_id)
            eo_context = f"{eo.title}" if eo else f"EO {eo_id}"
        
        # Generate summary
        summary_data = generate_daily_eo_summary(eo_id, task_updates, eo_context)
        
        # Add missing updates information
        expected_users = repo.get_expected_updates_for_eo_date(eo_id, target_date)
        updated_user_emails = {update['user_email'] for update in task_updates if 'user_email' in update}
        missing_updates = [
            user['user_email'] for user in expected_users 
            if user['user_email'] not in updated_user_emails
        ]
        
        summary_data['missing_updates'] = missing_updates
        summary_data['eo_id'] = eo_id
        summary_data['date'] = target_date
        
        # Save summary to database
        summary_id = repo.save_daily_eo_summary(summary_data)
        
        # Send email to PMOs
        send_daily_summary_email.delay(summary_id)
        
        print(f"Generated and saved daily summary {summary_id} for EO {eo_id}")
        
        return {
            "success": True,
            "eo_id": eo_id,
            "date": str(target_date),
            "summary_id": summary_id,
            "updates_count": len(task_updates),
            "missing_updates_count": len(missing_updates)
        }
        
    except Exception as e:
        print(f"Error aggregating daily updates: {e}")
        return {"error": str(e), "eo_id": eo_id, "date": target_date}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.send_daily_summary_email")
def send_daily_summary_email(summary_id: str):
    """
    Send daily summary email to PMOs assigned to the EO.
    """
    from src.workflow import repository as repo
    # EmailService removed - using Redis queue only
    from src.email.email_template_builder import EmailTemplateBuilder
    
    print(f"Sending daily summary email for summary {summary_id}")
    
    try:
        # Get summary data
        summary = repo.get_daily_eo_summary_by_id(summary_id)
        if not summary:
            print(f"Summary not found: {summary_id}")
            return {"error": "Summary not found", "summary_id": summary_id}
        
        # Get EO details
        from src.models.executive_order import ExecutiveOrder
        with repo.SessionLocal() as db:
            eo = db.get(ExecutiveOrder, summary['eo_id'])
            if not eo:
                print(f"EO not found: {summary['eo_id']}")
                return {"error": "EO not found", "summary_id": summary_id}
        
        # Get PMO assignments for this EO
        from src.models.eo_pmo_assignment import EOPMOAssignment
        from src.models.user import User
        with repo.SessionLocal() as db:
            pmo_assignments = db.execute(
                select(EOPMOAssignment, User.email.label('pmo_email'), User.name.label('pmo_name'))
                .join(User, EOPMOAssignment.pmo_id == User.id)
                .where(EOPMOAssignment.eo_id == summary['eo_id'])
            ).all()
        
        if not pmo_assignments:
            print(f"No PMO assignments found for EO {summary['eo_id']}")
            return {"error": "No PMO assignments", "summary_id": summary_id}
        
        # Get individual task updates for detailed reporting
        task_updates = repo.get_task_updates_for_eo_date(summary['eo_id'], summary['date'])
        
        # Use the email template to build the email
        from src.email.email_templates import DailySummaryTemplate
        
        built_email = DailySummaryTemplate.build_daily_summary(
            eo=eo.__dict__ if hasattr(eo, '__dict__') else eo,
            summary=summary,
            task_updates=task_updates
        )
        
        # Send email to each PMO
        email_service = QueuedEmailService()
        pmo_emails = [assignment.pmo_email for assignment in pmo_assignments]
        
        email_service.send_and_save(
            to=pmo_emails,
            subject=built_email.subject,
            body_text=built_email.body_text,
            body_html=built_email.body_html,
            email_type="daily_summary"
        )
        
        # Mark summary as emailed
        repo.mark_summary_email_sent(summary_id)
        
        print(f"Sent daily summary email to {len(pmo_emails)} PMOs")
        
        return {
            "success": True,
            "summary_id": summary_id,
            "pmo_count": len(pmo_emails),
            "pmo_emails": pmo_emails
        }
        
    except Exception as e:
        print(f"Error sending daily summary email: {e}")
        return {"error": str(e), "summary_id": summary_id}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.send_daily_reminders")
def send_daily_reminders(target_date: str = None):
    """
    Send reminder emails to employees who haven't provided daily updates.
    Runs at 4pm ET daily.
    """
    from src.workflow import repository as repo
    from src.email.queued_email_service import QueuedEmailService
    from datetime import date
    
    print(f"Sending daily reminders for {target_date}")
    
    try:
        # Parse target date
        if target_date:
            target_date = date.fromisoformat(target_date)
        else:
            target_date = date.today()
        
        # Get all EOs with active tasks
        from src.models.executive_order import ExecutiveOrder
        from src.models.task import Task
        with repo.SessionLocal() as db:
            eos_with_tasks = db.execute(
                select(ExecutiveOrder)
                .join(Task, ExecutiveOrder.id == Task.eo_id)
                .where(Task.status.in_(["pending", "in_progress", "Pending PMO approval"]))
                .distinct()
            ).scalars().all()
        
        total_reminders_sent = 0
        
        for eo in eos_with_tasks:
            # Get expected updates for this EO
            expected_users = repo.get_expected_updates_for_eo_date(eo.id, target_date)
            
            # Get actual updates for this EO
            actual_updates = repo.get_task_updates_for_eo_date(eo.id, target_date)
            updated_user_emails = {update['user_email'] for update in actual_updates if 'user_email' in update}
            
            # Find users who haven't updated
            missing_users = [
                user for user in expected_users 
                if user['user_email'] not in updated_user_emails
            ]
            
            if missing_users:
                # Send reminder emails
                email_service = QueuedEmailService()
                
                for user in missing_users:
                    # Build task list separately to avoid nested f-string
                    task_list = chr(10).join(f"- {task['title']}" for task in user['tasks'])
                    
                    reminder_content = f"""
Hello {user['user_name']},

This is a friendly reminder that you have {user['task_count']} active task(s) assigned to you under Executive Order: {eo.title}

Please provide your daily update by 6:00 PM ET today.

Your tasks:
{task_list}

You can reply to this email with your update, or use the following template:

# Daily Update ({target_date})
- Task: [Task Title or ID]
  Status: [NotStarted/InProgress/Blocked/Completed]
  Progress: [0-100]%
  ETA: [YYYY-MM-DD]
  Spent: [X.X]h
  Blockers: [none or description]
  Notes: [brief update]

Thank you!
                    """.strip()
                    
                    email_service.send(
                        to=[user['user_email']],
                        subject=f"Daily Update Reminder - {eo.title}",
                        body_text=reminder_content,
                        body_html=reminder_content.replace('\n', '<br>')
                    )
                    
                    total_reminders_sent += 1
        
        print(f"Sent {total_reminders_sent} reminder emails")
        
        return {
            "success": True,
            "date": str(target_date),
            "reminders_sent": total_reminders_sent
        }
        
    except Exception as e:
        print(f"Error sending daily reminders: {e}")
        return {"error": str(e), "date": target_date}

    