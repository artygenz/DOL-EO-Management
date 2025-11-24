"""
PMO Response Service

Extracts business logic from process_pmo_response and related tasks for better separation of concerns.
Minimizes noisy logging; uses appropriate levels (info for milestones, debug for details).
"""

import logging
from typing import Dict, List, Optional
from src.workflow.dto import PMOEmailIn
from src.workflow.parse_pmo import parse_pmo_email, extract_eo_id_from_subject
from src.workflow import repository as repo


logger = logging.getLogger(__name__)


class PMOResponseService:
    """Service for PMO response processing - extracts business logic from process_pmo_response task"""
    
    def __init__(self):
        # Keep existing services as-is
        pass
    
    def process_pmo_response(self, email_payload: Dict) -> Dict:
        """
        Business logic extracted from process_pmo_response task
        
        Args:
            email_payload: Email payload dictionary
            
        Returns:
            Dict containing eo_id, intent, approved count, and rejected count
        """
        # Basic association heuristics
        email = PMOEmailIn(**email_payload)
        related_eo_id = email.related_eo_id or extract_eo_id_from_subject(email.subject)
        email_log_id = email_payload.get("email_log_id")

        # Validate that the EO exists
        if related_eo_id:
            eo = repo.get_executive_order(related_eo_id)
            if not eo:
                error_msg = f"EO with ID '{related_eo_id}' not found in database. Cannot process PMO response."
                logger.error(error_msg)
                return {
                    "eo_id": related_eo_id, 
                    "error": error_msg, 
                    "intent": "ERROR", 
                    "approved": 0, 
                    "rejected": 0
                }
        else:
            error_msg = "No EO ID found in PMO email (neither in related_eo_id nor subject). Cannot process PMO response."
            logger.error(error_msg)
            return {
                "eo_id": None, 
                "error": error_msg, 
                "intent": "ERROR", 
                "approved": 0, 
                "rejected": 0
            }

        # Parse PMO email
        parsed = parse_pmo_email(email.body_text)
        intent = parsed.get("intent")
        approve_ids: List[str] = parsed.get("approve_task_ids") or []
        reject_ids: List[str] = parsed.get("reject_task_ids") or []
        global_remarks: Optional[str] = parsed.get("remarks")
        per_task_remarks: Dict[str, str] = parsed.get("per_task_remarks") or {}

        # Map simple task IDs to database UUIDs if needed
        if related_eo_id and (approve_ids or reject_ids):
            approve_ids, reject_ids, per_task_remarks = self._map_task_ids(
                related_eo_id, approve_ids, reject_ids, per_task_remarks
            )

        # Process task updates based on intent
        actual_approved_count, actual_rejected_count = self._process_task_updates(
            related_eo_id, intent, approve_ids, reject_ids, global_remarks, per_task_remarks
        )

        # Return data only; orchestration (notify/rewire/email) handled by chain layer
        result = {
            "eo_id": related_eo_id,
            "intent": intent,
            "approved": actual_approved_count,
            "rejected": actual_rejected_count,
            "reject_task_ids": reject_ids,
            "remarks": global_remarks,
            "per_task_remarks": per_task_remarks,
        }
        return result
    
    def _map_task_ids(self, eo_id: str, approve_ids: List[str], reject_ids: List[str], per_task_remarks: Dict[str, str]) -> tuple:
        """Map simple task IDs to database UUIDs"""
        # Check if the IDs are simple numbers (1, 2, 3, etc.)
        if approve_ids and all(tid.isdigit() for tid in approve_ids):
            approve_ids = repo.map_simple_task_ids_to_uuids(eo_id, approve_ids)
        
        if reject_ids and all(tid.isdigit() for tid in reject_ids):
            reject_ids = repo.map_simple_task_ids_to_uuids(eo_id, reject_ids)
        
        # Also map the per_task_remarks keys
        if per_task_remarks:
            mapped_per_task_remarks = {}
            all_simple_ids = list(per_task_remarks.keys())
            if all(tid.isdigit() for tid in all_simple_ids):
                mapped_ids = repo.map_simple_task_ids_to_uuids(eo_id, all_simple_ids)
                for simple_id, mapped_id in zip(all_simple_ids, mapped_ids):
                    if mapped_id:
                        mapped_per_task_remarks[mapped_id] = per_task_remarks[simple_id]
                per_task_remarks = mapped_per_task_remarks
        
        return approve_ids, reject_ids, per_task_remarks
    
    def _process_task_updates(self, eo_id: str, intent: str, approve_ids: List[str], reject_ids: List[str], 
                            global_remarks: Optional[str], per_task_remarks: Dict[str, str]) -> tuple:
        """Process task status updates based on PMO intent"""
        # If intent is ALL variants, load task IDs by EO when possible
        if intent in ("APPROVE_ALL", "REJECT_ALL") and eo_id:
            if intent == "APPROVE_ALL":
                # For APPROVE_ALL, only approve tasks that are currently pending PMO approval
                pending_task_ids = repo.get_pending_task_ids_by_eo(eo_id)
                repo.update_tasks_status_and_remarks(pending_task_ids, status="approved", remarks="N/A")
                actual_approved_count = len(pending_task_ids)
                actual_rejected_count = 0
            else:
                # For REJECT_ALL, reject all tasks for the EO
                task_ids = repo.get_task_ids_by_eo(eo_id)
                repo.update_tasks_status_and_remarks(task_ids, status="rejected", remarks=global_remarks or "")
                actual_approved_count = 0
                actual_rejected_count = len(task_ids)
        else:
            # Process individual task updates
            if approve_ids:
                repo.update_tasks_status_and_remarks(approve_ids, status="approved", remarks="N/A")
            if reject_ids:
                # First set global remarks on all
                repo.update_tasks_status_and_remarks(reject_ids, status="rejected", remarks=global_remarks or None)
                # Then overwrite per-task remarks if provided
                if per_task_remarks:
                    repo.update_per_task_remarks(per_task_remarks)
            
            actual_approved_count = len(approve_ids)
            actual_rejected_count = len(reject_ids)
        
        return actual_approved_count, actual_rejected_count
    
    # Note: follow-up orchestration is handled at the chain layer; this service is pure business logic.
    
    def handle_rejected_tasks(self, eo_id: Optional[str], rejected_ids: Optional[List[str]], 
                            global_remarks: Optional[str], per_task_remarks: Optional[Dict[str, str]]) -> Dict:
        """
        Business logic extracted from handle_rejected_tasks task
        
        Args:
            eo_id: Executive Order ID
            rejected_ids: List of rejected task IDs
            global_remarks: Global remarks from PMO
            per_task_remarks: Per-task remarks from PMO
            
        Returns:
            Dict containing processing results
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
            task_remarks = self._build_task_remarks(rejected_tasks, global_remarks, per_task_remarks)
            
            # Convert tasks to dict format expected by rewire function
            tasks_dict = self._prepare_tasks_for_rewiring(rejected_tasks, task_remarks)
            
            # Use LLM to rewire tasks based on PMO remarks
            improved_result = self._rewire_tasks_with_llm(eo.description or "", global_remarks or "Tasks need improvement", 
                                                        tasks_dict, roles_text)
            
            # Process improved tasks
            if improved_result.get("tasks"):
                updated_count = self._update_tasks_with_improvements(eo_id, improved_result, rejected_tasks)
                
                if updated_count > 0:
                    # Send improved tasks back to PMO for review
                    improved_task_ids = list(improved_result.get("task_updates", {}).keys())
                    self._send_improved_tasks_to_pmo(eo_id, improved_result.get("summary", ""), improved_task_ids)
            
            return {"eo_id": eo_id, "rejected": len(rejected_ids), "rewired": True}
            
        except Exception as e:
            logger.error("handle_rejected_tasks failed: %s", e)
            return {"eo_id": eo_id, "error": str(e)}
    
    def _build_task_remarks(self, rejected_tasks, global_remarks: Optional[str], per_task_remarks: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Build comprehensive remarks for each task"""
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
        
        return task_remarks
    
    def _prepare_tasks_for_rewiring(self, rejected_tasks, task_remarks: Dict[str, str]) -> Dict:
        """Prepare tasks in format expected by rewire function"""
        return {
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
                    "remarks": task_remarks.get(str(task.id), "Task needs improvement"),
                }
                for task in rejected_tasks
            ]
        }
    
    def _rewire_tasks_with_llm(self, eo_description: str, remarks: str, tasks_dict: Dict, roles_text: str) -> Dict:
        """Use LLM to rewire tasks based on PMO remarks"""
        from src.ai.rewire_tasks import rewire_tasks_with_remarks
        return rewire_tasks_with_remarks(
            eo=eo_description,
            remarks=remarks,
            tasks=tasks_dict,
            roles_text=roles_text
        )
    
    def _update_tasks_with_improvements(self, eo_id: str, improved_result: Dict, rejected_tasks) -> int:
        """Update tasks in database with improved versions"""
        improved_tasks = improved_result.get("tasks", [])
        if not improved_tasks:
            return 0
        
        # Assign tasks based on category_dept
        if improved_tasks:
            from src.ai.extract_directives import assign_tasks
            improved_result_with_assignments = assign_tasks(improved_result, improved_result.get("roles_text", ""))
            improved_tasks = improved_result_with_assignments.get("tasks", improved_tasks)
        
        # Create a mapping from simple task ID to improved task data
        task_updates = {}
        for idx, improved_task in enumerate(improved_tasks):
            # Map simple ID to the corresponding rejected task UUID
            if idx < len(rejected_tasks):
                task_uuid = str(rejected_tasks[idx].id)
                # Create a copy and replace the LLM's simple ID with the database UUID
                improved_task_copy = improved_task.copy()
                improved_task_copy['id'] = task_uuid
                task_updates[task_uuid] = improved_task_copy
        
        # Update tasks using repository method
        updated_count = repo.update_tasks_with_improved_data(task_updates)
        logger.info("Updated %d tasks in database", updated_count)
        
        return updated_count
    
    def _send_improved_tasks_to_pmo(self, eo_id: str, improvement_summary: str, improved_task_ids: List[str]):
        """Send improved tasks back to PMO for review"""
        # Call the service method directly instead of queuing a task
        return self.send_improved_tasks_to_pmo(eo_id, improvement_summary, improved_task_ids)
    
    def send_improved_tasks_to_pmo(self, eo_id: str, improvement_summary: str, improved_task_ids: Optional[List[str]] = None) -> Dict:
        """
        Business logic extracted from send_improved_tasks_to_pmo task
        
        Args:
            eo_id: Executive Order ID
            improvement_summary: Summary of improvements made by LLM
            improved_task_ids: Specific task IDs that were improved
            
        Returns:
            Dict containing processing results
        """
        
        if not eo_id:
            return {"error": "eo_id is required"}
        
        try:
            # Load EO from database
            eo = repo.get_executive_order(eo_id)
            if not eo:
                return {"error": f"ExecutiveOrder not found for id={eo_id}"}
            
            # Load specific improved task IDs, or fall back to improved tasks
            if improved_task_ids:
                task_ids = improved_task_ids
            else:
                task_ids = repo.get_task_ids_by_eo_and_status(eo_id, "Pending PMO approval")
                
            if not task_ids:
                return {"error": "No tasks found to send for improved review"}
            
            # Convert tasks to format expected by email template
            task_list = self._prepare_tasks_for_email(eo_id, task_ids)
            
            # Resolve PMO recipient
            import os
            pmo_email = os.getenv("PMO_EMAIL_ADDRESS", "kevin.brown@lumenlighthouse.ai")
            
            # Convert EO to simple dict to avoid circular reference issues
            eo_dict = self._convert_eo_to_dict(eo)
            
            # Build email with improved tasks
            built = self._build_improved_tasks_email(eo_dict, task_list, improvement_summary)
            
            # Save email log
            email_log_id = self._log_improved_tasks_email(built, pmo_email, eo_dict["id"])
            
            # Send email
            message_id = self._send_improved_tasks_email(built, pmo_email, email_log_id)
            
            result = {
                "eo_id": eo_id,
                "sent_to": pmo_email,
                "message_id": message_id,
                "tasks": len(task_list),
                "improvement_summary": improvement_summary
            }
            
            return result
            
        except Exception as e:
            logger.error("send_improved_tasks_to_pmo failed: %s", e)
            return {"eo_id": eo_id, "error": str(e)}
    
    def _prepare_tasks_for_email(self, eo_id: str, task_ids: List[str]) -> List[Dict]:
        """Prepare tasks for email template"""
        task_list = []
        from src.db.session import SessionLocal
        from src.models.task import Task
        from src.models.user import User
        
        with SessionLocal() as db:
            for i, task_id in enumerate(task_ids):
                task = db.get(Task, task_id)
                if task:
                    # Get assignee name directly to avoid circular reference
                    assignee_name = "Unassigned"
                    if task.assignee_id:
                        assignee = db.get(User, task.assignee_id)
                        if assignee:
                            assignee_name = assignee.name
                    
                    task_dict = {
                        "id": str(task.id),
                        "title": task.title,
                        "description": task.description,
                        "category": task.category,
                        "status": task.status,
                        "due_date": task.due_date.isoformat() if task.due_date else "TBD",
                        "remarks": task.remarks,
                        "assignee": assignee_name
                    }
                    task_list.append(task_dict)
        
        return task_list
    
    def _convert_eo_to_dict(self, eo) -> Dict:
        """Convert EO to dictionary to avoid circular references"""
        return {
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
    
    def _build_improved_tasks_email(self, eo_dict: Dict, task_list: List[Dict], improvement_summary: str):
        """Build email template for improved tasks"""
        from src.email.email_template_builder import EmailTemplateBuilder
        return EmailTemplateBuilder.build_improved_tasks_review(eo_dict, task_list, improvement_summary)
    
    def _log_improved_tasks_email(self, built_email, pmo_email: str, eo_id: str) -> Optional[str]:
        """Log improved tasks email"""
        try:
            email_log = repo.save_email_log(
                direction="outgoing",
                subject=built_email.subject,
                sender=None,
                recipients=[pmo_email],
                raw_content=built_email.body_text,
                related_eo_id=eo_id,
            )
            email_log_id = str(email_log.id)
            return email_log_id
        except Exception as e:
            logger.warning("Could not save email log: %s", e)
            return None
    
    def _send_improved_tasks_email(self, built_email, pmo_email: str, email_log_id: Optional[str]) -> str:
        """Send improved tasks email"""
        from src.email.queued_email_service import QueuedEmailService
        from dataclasses import dataclass
        
        @dataclass
        class Attachment:
            filename: str
            content_type: str
            data: bytes
        
        svc = QueuedEmailService()
        attachments = [Attachment(fn, ct, data) for (fn, ct, data) in built_email.attachments]
        
        message_id = svc.send_and_save(
            to=[pmo_email],
            subject=built_email.subject,
            body_text=built_email.body_text,
            body_html=built_email.body_html,
            attachments=attachments,
            headers=built_email.headers,
            email_log_id=email_log_id,
            email_type="improved_review"
        )
        
        return message_id
