"""
Email templates package for DOL EO Management System.

This package contains modular email templates for different types of notifications:
- PMO review emails
- Employee notification emails
- Improved tasks review emails
"""

from .base import BaseEmailTemplate, BuiltEmail
from .pmo_review import PMOReviewTemplate
from .employee_notification import EmployeeNotificationTemplate
from .improved_tasks_review import ImprovedTasksReviewTemplate
from .daily_summary import DailySummaryTemplate

__all__ = [
    'BaseEmailTemplate',
    'BuiltEmail',
    'PMOReviewTemplate', 
    'EmployeeNotificationTemplate',
    'ImprovedTasksReviewTemplate',
    'DailySummaryTemplate'
]
