"""
Daily Update Service

Extracts business logic from daily update tasks for better separation of concerns.
"""

import logging
from typing import Dict, Optional
from datetime import date, datetime, timezone
import hashlib
import pytz

logger = logging.getLogger(__name__)
from src.workflow.dto import DailyUpdateEmailPayload
from src.workflow.ai import extract_daily_task_updates
from src.workflow import repository as repo
from src.email.queued_email_service import QueuedEmailService
from src.db.session import SessionLocal
from src.models.executive_order import ExecutiveOrder
from src.models.task import Task
from src.models.eo_pmo_assignment import EOPMOAssignment
from src.models.user import User
from sqlalchemy import select


class DailyUpdateService:
    """Service for daily update processing - extracts business logic from daily update tasks"""
    
    def __init__(self):
        # Keep existing services as-is
        pass
    
    def process_daily_update_email(self, email_payload: Dict) -> Dict:
        """
        Business logic extracted from process_daily_update_email task
        
        Args:
            email_payload: Email payload dictionary
            
        Returns:
            Dict containing processing results
        """
        logger.info(f"Processing daily update from {email_payload.get('sender')}: {email_payload.get('subject', 'N/A')}")
        
        try:
            # Parse email payload
            email_data = DailyUpdateEmailPayload(**email_payload)
            
            # Resolve user by email
            user_id = repo.resolve_user_by_email(email_data.sender)
            if not user_id:
                logger.error(f"Could not resolve user for email: {email_data.sender}")
                return {"error": "User not found", "sender": email_data.sender}
            
            logger.info(f"User ID: {user_id}")
            
            # Get user's active tasks
            user_tasks = repo.get_user_active_tasks(user_id)
            if not user_tasks:
                logger.warning(f"No active tasks found for user: {email_data.sender}")
                return {"error": "No active tasks", "sender": email_data.sender}
            
            logger.info(f"Found {len(user_tasks)} active tasks for user")
            
            # Extract task updates using AI
            extraction_result = extract_daily_task_updates(email_data.body_text, user_tasks)
            
            # Process extracted updates
            updates_to_save = self._process_extracted_updates(extraction_result, user_tasks, user_id, email_data)
            
            # Save updates to database
            saved_count = repo.save_task_updates(updates_to_save)
            
            logger.info(f"Saved {saved_count} task updates for user {email_data.sender}")
            
            return {
                "success": True,
                "sender": email_data.sender,
                "user_id": user_id,
                "extraction_case": extraction_result.get('case'),
                "updates_saved": saved_count,
                "unmatched_mentions": extraction_result.get('unmatched_mentions', []),
                "is_late": self._check_if_late(email_data.received_at)
            }
            
        except Exception as e:
            logger.error(f"Error processing daily update email: {e}")
            return {"error": str(e), "sender": email_payload.get('sender')}
    
    def _process_extracted_updates(self, extraction_result: Dict, user_tasks: list, user_id: str, email_data: DailyUpdateEmailPayload) -> list:
        """Process extracted updates and prepare for database storage"""
        updates_to_save = []
        today = date.today()
        is_late = self._check_if_late(email_data.received_at)
        
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
        
        return updates_to_save
    
    def _check_if_late(self, email_time: datetime) -> bool:
        """Check if email is late (after 6pm ET)"""
        if email_time.tzinfo is None:
            email_time = email_time.replace(tzinfo=timezone.utc)
        
        # Convert to ET for deadline check
        et_tz = pytz.timezone('America/New_York')
        email_time_et = email_time.astimezone(et_tz)
        deadline_et = email_time_et.replace(hour=18, minute=0, second=0, microsecond=0)
        
        return email_time_et > deadline_et
    
    def aggregate_daily_updates(self, eo_id: str, target_date: Optional[str] = None) -> Dict:
        """
        Business logic extracted from aggregate_daily_updates task
        
        Args:
            eo_id: Executive Order ID
            target_date: Target date for aggregation (optional)
            
        Returns:
            Dict containing aggregation results
        """
        from src.workflow.ai import generate_daily_eo_summary
        
        logger.info(f"Aggregating daily updates for EO {eo_id} on {target_date}")
        
        try:
            # Parse target date
            if target_date:
                target_date = date.fromisoformat(target_date)
            else:
                target_date = date.today()
            
            # Get task updates for this EO and date
            task_updates = repo.get_task_updates_for_eo_date(eo_id, target_date)
            
            if not task_updates:
                logger.info(f"No task updates found for EO {eo_id} on {target_date}")
                return {"error": "No updates found", "eo_id": eo_id, "date": str(target_date)}
            
            # Get EO context for summary
            with SessionLocal() as db:
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
            
            # Note: Email sending orchestrated by chain layer
            
            logger.info(f"Generated and saved daily summary {summary_id} for EO {eo_id}")
            
            return {
                "success": True,
                "eo_id": eo_id,
                "date": str(target_date),
                "summary_id": summary_id,
                "updates_count": len(task_updates),
                "missing_updates_count": len(missing_updates)
            }
            
        except Exception as e:
            logger.error(f"Error aggregating daily updates: {e}")
            return {"error": str(e), "eo_id": eo_id, "date": target_date}
    
    # Note: Email orchestration handled by chain layer; this service is pure business logic
    
    def send_daily_summary_email(self, summary_id: str) -> Dict:
        """
        Business logic extracted from send_daily_summary_email task
        
        Args:
            summary_id: Daily summary ID
            
        Returns:
            Dict containing email sending results
        """
        logger.info(f"Sending daily summary email for summary {summary_id}")
        
        try:
            # Get summary data
            summary = repo.get_daily_eo_summary_by_id(summary_id)
            if not summary:
                logger.error(f"Summary not found: {summary_id}")
                return {"error": "Summary not found", "summary_id": summary_id}
            
            # Get EO details
            with SessionLocal() as db:
                eo = db.get(ExecutiveOrder, summary['eo_id'])
                if not eo:
                    logger.error(f"EO not found: {summary['eo_id']}")
                    return {"error": "EO not found", "summary_id": summary_id}
            
            # Get PMO assignments for this EO
            pmo_assignments = self._get_pmo_assignments(summary['eo_id'])
            if not pmo_assignments:
                logger.warning(f"No PMO assignments found for EO {summary['eo_id']}")
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
    
    def _get_pmo_assignments(self, eo_id: str) -> list:
        """Get PMO assignments for an EO"""
        with SessionLocal() as db:
            pmo_assignments = db.execute(
                select(EOPMOAssignment, User.email.label('pmo_email'), User.name.label('pmo_name'))
                .join(User, EOPMOAssignment.pmo_id == User.id)
                .where(EOPMOAssignment.eo_id == eo_id)
            ).all()
        
        return pmo_assignments
    
    def send_daily_reminders(self, target_date: Optional[str] = None) -> Dict:
        """
        Business logic extracted from send_daily_reminders task
        
        Args:
            target_date: Target date for reminders (optional)
            
        Returns:
            Dict containing reminder results
        """
        print(f"Sending daily reminders for {target_date}")
        
        try:
            # Parse target date
            if target_date:
                target_date = date.fromisoformat(target_date)
            else:
                target_date = date.today()
            
            # Get all EOs with active tasks
            eos_with_tasks = self._get_eos_with_active_tasks()
            
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
                    reminders_sent = self._send_reminder_emails(eo, missing_users, target_date)
                    total_reminders_sent += reminders_sent
            
            print(f"Sent {total_reminders_sent} reminder emails")
            
            return {
                "success": True,
                "date": str(target_date),
                "reminders_sent": total_reminders_sent
            }
            
        except Exception as e:
            print(f"Error sending daily reminders: {e}")
            return {"error": str(e), "date": target_date}
    
    def _get_eos_with_active_tasks(self) -> list:
        """Get EOs with active tasks"""
        with SessionLocal() as db:
            eos_with_tasks = db.execute(
                select(ExecutiveOrder)
                .join(Task, ExecutiveOrder.id == Task.eo_id)
                .where(Task.status.in_(["pending", "in_progress", "Pending PMO approval"]))
                .distinct()
            ).scalars().all()
        
        return eos_with_tasks
    
    def _send_reminder_emails(self, eo, missing_users: list, target_date: date) -> int:
        """Send reminder emails to missing users"""
        email_service = QueuedEmailService()
        reminders_sent = 0
        
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
            
            reminders_sent += 1
        
        return reminders_sent
