"""
AI Task Extraction Service

Extracts business logic from ai_extract_tasks task for better separation of concerns.
"""

from typing import Dict, List
from src.workflow.ai import extract_tasks


class AITaskExtractionService:
    """Service for AI task extraction - extracts business logic from ai_extract_tasks task"""
    
    def __init__(self):
        # Keep existing AI service as-is
        pass
    
    def extract_tasks_from_eo(self, eo_id: str, body_text: str) -> Dict:
        """
        Business logic extracted from ai_extract_tasks task
        
        Args:
            eo_id: Executive Order ID
            body_text: Text content to extract tasks from
            
        Returns:
            Dict containing eo_id, task_count, tasks, and next_step
        """
        print(f"\n=== AI Task Extraction Started ===")
        print(f"EO ID: {eo_id}")
        print(f"Body text length: {len(body_text)} characters")
        
        # Use existing AI service as-is
        tasks = extract_tasks(body_text)
        
        print(f"Extracted {len(tasks)} tasks from EO")
        print(f"=====================================\n")
        
        # Convert to serializable dicts
        serializable = [t.model_dump() for t in tasks]
        
        return {
            "eo_id": eo_id,
            "task_count": len(serializable),
            "tasks": serializable,
            "next_step": "persist_tasks"
        }
