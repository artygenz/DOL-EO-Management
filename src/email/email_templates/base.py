"""
Base email template class with common functionality for all email templates.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class BuiltEmail:
    """Data class for built email content."""
    subject: str
    body_text: str
    body_html: str
    attachments: List[tuple]  # (filename, content_type, data)
    headers: Dict[str, str]


class BaseEmailTemplate(ABC):
    """Base class for all email templates."""
    
    @staticmethod
    def _get_eo_property(eo, prop_name: str, default=None):
        """Safely get EO property whether it's a dict or object."""
        if isinstance(eo, dict):
            return eo.get(prop_name, default)
        else:
            return getattr(eo, prop_name, default)
    
    @staticmethod
    def _fmt_dt(dt) -> str:
        """Format datetime for display."""
        if not dt:
            return "Unknown"
        if isinstance(dt, str):
            return dt
        if hasattr(dt, 'strftime'):
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        return str(dt)
    
    @staticmethod
    def _build_csv_attachment(tasks: List[Dict], prefix: str) -> bytes:
        """Build CSV attachment from tasks."""
        import csv
        import io
        
        if not tasks:
            return b""
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        headers = ['ID', 'Title', 'Description', 'Category', 'Status', 'Due Date', 'Assignee', 'Remarks']
        writer.writerow(headers)
        
        # Write data
        for task in tasks:
            writer.writerow([
                task.get('id', ''),
                task.get('title', ''),
                task.get('description', ''),
                task.get('category', ''),
                task.get('status', ''),
                task.get('due_date', ''),
                task.get('assignee', ''),
                task.get('remarks', '')
            ])
        
        return output.getvalue().encode('utf-8')
    
    @staticmethod
    def _build_json_attachment(eo: Any, tasks: List[Dict], prefix: str) -> bytes:
        """Build JSON attachment from EO and tasks."""
        import json
        
        data = {
            "eo": {
                "id": BaseEmailTemplate._get_eo_property(eo, 'id'),
                "title": BaseEmailTemplate._get_eo_property(eo, 'title'),
                "message_id": BaseEmailTemplate._get_eo_property(eo, 'message_id'),
                "received_at": BaseEmailTemplate._get_eo_property(eo, 'received_at'),
                "description": BaseEmailTemplate._get_eo_property(eo, 'description')
            },
            "tasks": tasks,
            "generated_at": datetime.now().isoformat()
        }
        
        return json.dumps(data, indent=2, default=str).encode('utf-8')
    
    @staticmethod
    def _build_eo_text_attachment(eo: Any) -> bytes:
        """Build text attachment with EO content."""
        eo_text = BaseEmailTemplate._get_eo_property(eo, 'description', '')
        if not eo_text:
            eo_text = "Executive Order content not available."
        
        return eo_text.encode('utf-8')
    
    @staticmethod
    def _to_primitive(obj):
        """Convert objects to JSON-serializable primitives."""
        import uuid
        
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return obj
