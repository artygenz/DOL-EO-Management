"""
Email template builder for DOL EO Management System.

This module now serves as a compatibility layer for the new modular email templates.
All templates have been moved to src/email/email_templates/ for better organization.
"""

from typing import List, Dict, Tuple

# Import the new modular templates
from .email_templates import (
    PMOReviewTemplate,
    EmployeeNotificationTemplate, 
    ImprovedTasksReviewTemplate,
    BuiltEmail
)

class EmailTemplateBuilder:
    """
    Compatibility layer for the new modular email templates.
    All template methods now delegate to the appropriate template class.
    """

    @staticmethod
    def _get_eo_property(eo, prop_name: str, default=None):
        """Safely get EO property whether it's a dict or object."""
        if isinstance(eo, dict):
            return eo.get(prop_name, default)
        else:
            return getattr(eo, prop_name, default)

    @staticmethod
    def build_pmo_review(eo, rows: List[Dict]) -> BuiltEmail:
        """Build PMO review email with tasks table."""
        return PMOReviewTemplate.build_pmo_review(eo, rows)

    @staticmethod
    def build_employee_notification(eo, assignee_email: str, assignee_name: str, tasks: List[Dict]) -> BuiltEmail:
        """Build employee notification email with their assigned tasks."""
        return EmployeeNotificationTemplate.build_employee_notification(eo, assignee_email, assignee_name, tasks)

    @staticmethod
    def build_improved_tasks_review(eo, rows: List[Dict], improvement_summary: str) -> BuiltEmail:
        """Build improved tasks review email."""
        return ImprovedTasksReviewTemplate.build_improved_tasks_review(eo, rows, improvement_summary)