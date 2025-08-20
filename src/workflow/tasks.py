from typing import Dict
from celery import states
from src.workflow.celery_app import celery_app
from src.workflow.dto import EOIn, LLMTask
from src.workflow import repository as repo
from src.workflow.ai import extract_tasks
from src.email.email_template_builder import EmailTemplateBuilder
from src.email.email_service import EmailService, Attachment

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.store_email")
def store_email(eo_payload: Dict):
    """
    1) Upsert EO row (idempotent by message_id)
    2) Queue AI extraction
    """

    print("Recived EO", eo_payload)
    eo = EOIn(**eo_payload)
    # Log inbound EO email
    try:
        repo.save_email_log(
            direction="incoming",
            subject=eo.subject,
            sender=eo.sender,
            recipients=eo.recipients,
            raw_content=eo.body_text,
            related_eo_id=None,
        )
    except Exception as _:
        pass

    eo_row = repo.upsert_executive_order(eo)
    repo.update_eo_status(eo_row.id, "received")
    # Chain to AI extraction
    ai_extract_tasks.delay(eo_row.id, eo.body_text if hasattr(eo, "body_text") else eo_payload.get("body_text", ""))
    return {"eo_id": str(eo_row.id)}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.ai_extract_tasks")
def ai_extract_tasks(eo_id: str, body_text: str):
    """
    1) Call AI to get task list
    2) Queue persistence
    """
    tasks = extract_tasks(body_text)
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
    from src.workflow.dto import TaskCreate
    to_create = []
    for d in tasks_payload or []:
        try:
            to_create.append(LLMTask.model_validate(d))
        except Exception as e:
            print(f"[persist] drop malformed task: {e!r} :: {d!r}")

    # print("\n\n Tasks that are sent to db handler to add in the table",to_create,"\n\n")

    count = repo.insert_tasks(eo_id, to_create)

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
    
     # Resolve PMO recipient: DB role → env fallback, hardcoded for now
    pmo_email = "abbuabhinav.1502@gmail.com"         ### repo.get_user_email_by_role("PMO") , once we have user data

   

    # --- build email via template service ---
    built = EmailTemplateBuilder.build_pmo_review(eo, task_list)

    svc = EmailService()
    attachments = [Attachment(fn, ct, data) for (fn, ct, data) in built.attachments]

    message_id = svc.send(
        to=[pmo_email],
        subject=built.subject,
        body_text=built.body_text,
        body_html=built.body_html,
        attachments=attachments,
        headers=built.headers,
    )

    try:
        repo.save_email_log(
            direction="outgoing",
            subject=built.subject,
            sender=None,
            recipients=[pmo_email],
            raw_content=built.body_text,
            related_eo_id=eo.id,
        )
    except Exception as _:
        pass

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

    parsed = parse_pmo_email(email.body_text)
    intent = parsed.get("intent")
    approve_ids: list[str] = parsed.get("approve_task_ids") or []
    reject_ids: list[str] = parsed.get("reject_task_ids") or []
    global_remarks: str | None = parsed.get("remarks")
    per_task_remarks: dict[str, str] = parsed.get("per_task_remarks") or {}

    # If intent is ALL variants, load all task IDs by EO when possible
    if intent in ("APPROVE_ALL", "REJECT_ALL") and related_eo_id:
        task_ids = repo.get_task_ids_by_eo(related_eo_id)
        if intent == "APPROVE_ALL":
            repo.update_tasks_status_and_remarks(task_ids, status="approved", remarks="N/A")
        else:
            repo.update_tasks_status_and_remarks(task_ids, status="rejected", remarks=global_remarks or "")
    else:
        if approve_ids:
            repo.update_tasks_status_and_remarks(approve_ids, status="approved", remarks="N/A")
        if reject_ids:
            # First set global remarks on all
            repo.update_tasks_status_and_remarks(reject_ids, status="rejected", remarks=global_remarks or None)
            # Then overwrite per-task remarks if provided
            if per_task_remarks:
                repo.update_per_task_remarks(per_task_remarks)

    # Notify assignees if anything approved
    if intent in ("APPROVE_ALL", "APPROVE_SOME") and (approve_ids or intent == "APPROVE_ALL"):
        notify_assignees.delay(related_eo_id)

    # Handle rejected tasks remediation (later)
    if intent in ("REJECT_ALL", "APPROVE_SOME") and reject_ids:
        handle_rejected_tasks.delay(related_eo_id, reject_ids, global_remarks)

    return {"eo_id": related_eo_id, "intent": intent, "approved": len(approve_ids), "rejected": len(reject_ids)}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.notify_assignees")
def notify_assignees(eo_id: str | None):
    # Stub: will load approved tasks grouped by assignee and email
    if not eo_id:
        return {"notified": 0}
    # TODO: implement grouping and templating
    return {"eo_id": eo_id, "notified": 0}

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5, name="src.workflow.tasks.handle_rejected_tasks")
def handle_rejected_tasks(eo_id: str | None, rejected_ids: list[str] | None, remarks: str | None):
    # Stub: will call LLM refine and send modified review email
    return {"eo_id": eo_id, "rejected": len(rejected_ids or [])}

    