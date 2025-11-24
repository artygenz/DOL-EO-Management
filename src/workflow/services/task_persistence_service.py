"""
Task Persistence Service

Extracts business logic from persist_tasks task for better separation of concerns.
"""

from typing import Dict, List
from src.workflow.dto import LLMTask
from src.workflow import repository as repo


class TaskPersistenceService:
    """Service for task persistence - extracts business logic from persist_tasks task"""
    
    def __init__(self):
        # Keep existing repository as-is
        pass
    
    def persist_tasks_for_eo(self, eo_id: str, tasks_payload: List[dict]) -> Dict:
        """
        Business logic extracted from persist_tasks task
        
        Args:
            eo_id: Executive Order ID
            tasks_payload: List of task dictionaries to persist
            
        Returns:
            Dict containing eo_id, inserted count, and tasks_for_email
        """
        print(f"\n=== Task Persistence Started ===")
        print(f"EO ID: {eo_id}")
        print(f"Tasks to persist: {len(tasks_payload or [])}")
        
        # Validate and convert tasks
        to_create = []
        for d in tasks_payload or []:
            try:
                to_create.append(LLMTask.model_validate(d))
            except Exception as e:
                print(f"Warning: Dropping malformed task: {e}")

        # Use existing repository as-is
        count = repo.insert_tasks(eo_id, to_create)
        
        print(f"Successfully persisted {count} tasks")
        print(f"====================================\n")

        # Prepare for email - JSON-safe snapshot for Celery
        safe_for_email = [
            t.model_dump(mode="json") if hasattr(t, "model_dump") else d
            for t, d in zip(to_create, tasks_payload[:len(to_create)])
        ]

        return {
            "eo_id": eo_id,
            "inserted": count,
            "tasks_for_email": safe_for_email,
            "next_step": "send_pmo_review_email"
        }
