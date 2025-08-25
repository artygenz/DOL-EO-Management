"""
Employee notification email template for notifying employees about their assigned tasks.
"""

from typing import Dict, List
from .base import BaseEmailTemplate, BuiltEmail


class EmployeeNotificationTemplate(BaseEmailTemplate):
    """Template for employee notification emails."""
    
    @staticmethod
    def build_employee_notification(eo, assignee_email: str, assignee_name: str, tasks: List[Dict]) -> BuiltEmail:
        """Build employee notification email with their assigned tasks."""
        subject = f"Task Assignment: {EmployeeNotificationTemplate._get_eo_property(eo, 'title') or 'Executive Order'}"
        
        # TEXT VERSION
        lines = [
            f"Dear {assignee_name},",
            "",
            f"You have been assigned {len(tasks)} task(s) from Executive Order: {EmployeeNotificationTemplate._get_eo_property(eo, 'title') or '(no subject)'}",
            f"EO ID: {EmployeeNotificationTemplate._get_eo_property(eo, 'id')}",
            f"EO Message-ID: {EmployeeNotificationTemplate._get_eo_property(eo, 'message_id')}",
            f"Received: {EmployeeNotificationTemplate._fmt_dt(EmployeeNotificationTemplate._get_eo_property(eo, 'received_at'))}",
            "",
            "Your assigned tasks are:",
            ""
        ]
        
        # Add task details
        for idx, task in enumerate(tasks, start=1):
            lines.extend([
                f"Task {idx}:",
                f"  Title: {task.get('title', '(untitled)')}",
                f"  Description: {task.get('description', '(no description)')}",
                f"  Due Date: {task.get('due_date', 'TBD')}",
                f"  Status: {task.get('status', 'Pending')}",
                ""
            ])
        
        lines.extend([
            "Please review these tasks and begin work as soon as possible.",
            "If you have any questions or need clarification, please contact your supervisor.",
            "",
            "Best regards,",
            "DOL EO Management System"
        ])
        
        body_text = "\n".join(lines)

        # HTML VERSION WITH ENHANCED CSS
        html_lines = [
            f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Task Assignment</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f9f9f9;
                    }}
                    .container {{
                        background-color: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 20px;
                        border-radius: 8px;
                        margin-bottom: 25px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 24px;
                        font-weight: 300;
                    }}
                    .greeting {{
                        font-size: 18px;
                        margin-bottom: 20px;
                        color: #2c3e50;
                    }}
                    .eo-info {{
                        background-color: #ecf0f1;
                        padding: 15px;
                        border-radius: 6px;
                        margin-bottom: 20px;
                        border-left: 4px solid #3498db;
                    }}
                    .task-list {{
                        margin: 20px 0;
                    }}
                    .task-item {{
                        background-color: #f8f9fa;
                        border: 1px solid #e9ecef;
                        border-radius: 8px;
                        padding: 20px;
                        margin-bottom: 15px;
                        border-left: 4px solid #28a745;
                    }}
                    .task-title {{
                        font-size: 18px;
                        font-weight: 600;
                        color: #2c3e50;
                        margin-bottom: 10px;
                    }}
                    .task-details {{
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 10px;
                        margin-top: 10px;
                    }}
                    .task-detail {{
                        background-color: white;
                        padding: 8px 12px;
                        border-radius: 4px;
                        border: 1px solid #dee2e6;
                    }}
                    .task-detail strong {{
                        color: #495057;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 2px solid #ecf0f1;
                        text-align: center;
                        color: #7f8c8d;
                    }}
                    .status-approved {{
                        color: #27ae60;
                        font-weight: 600;
                    }}
                    .status-pending {{
                        color: #f39c12;
                        font-weight: 600;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📋 Task Assignment</h1>
                    </div>
                    
                    <div class="greeting">
                        Dear <strong>{assignee_name}</strong>,
                    </div>
                    
                    <p>You have been assigned <strong>{len(tasks)} task(s)</strong> from the following Executive Order:</p>
                    
                    <div class="eo-info">
                        <strong>Executive Order:</strong> {EmployeeNotificationTemplate._get_eo_property(eo, 'title') or '(no subject)'}<br>
                        <strong>EO ID:</strong> {EmployeeNotificationTemplate._get_eo_property(eo, 'id')}<br>
                        <strong>Message ID:</strong> {EmployeeNotificationTemplate._get_eo_property(eo, 'message_id')}<br>
                        <strong>Received:</strong> {EmployeeNotificationTemplate._fmt_dt(EmployeeNotificationTemplate._get_eo_property(eo, 'received_at'))}
                    </div>
                    
                    <div class="task-list">
                        <h3>Your Assigned Tasks:</h3>
            """
        ]
        
        # Add task items
        for idx, task in enumerate(tasks, start=1):
            status_class = "status-approved" if task.get('status') == 'approved' else "status-pending"
            html_lines.append(f"""
                        <div class="task-item">
                            <div class="task-title">Task {idx}: {task.get('title', '(untitled)')}</div>
                            <p><strong>Description:</strong> {task.get('description', '(no description)')}</p>
                            <div class="task-details">
                                <div class="task-detail">
                                    <strong>Due Date:</strong> {task.get('due_date', 'TBD')}
                                </div>
                                <div class="task-detail">
                                    <strong>Status:</strong> <span class="{status_class}">{task.get('status', 'Pending')}</span>
                                </div>
                            </div>
                        </div>
            """)
        
        html_lines.append(f"""
                    </div>
                    
                    <div class="footer">
                        <p>Please review these tasks and begin work as soon as possible.</p>
                        <p>If you have any questions or need clarification, please contact your supervisor.</p>
                        <p><strong>Best regards,</strong><br>DOL EO Management System</p>
                    </div>
                </div>
            </body>
            </html>
            """)
        
        body_html = "\n".join(html_lines)
        
        # Create attachments (CSV and JSON)
        attachments = []
        
        # CSV attachment
        csv_data = EmployeeNotificationTemplate._build_csv_attachment(tasks, "assigned_tasks")
        attachments.append(("assigned_tasks.csv", "text/csv", csv_data))
        
        # JSON attachment
        json_data = EmployeeNotificationTemplate._build_json_attachment(eo, tasks, "assigned_tasks")
        attachments.append(("assigned_tasks.json", "application/json", json_data))
        
        # EO text attachment
        eo_text = EmployeeNotificationTemplate._build_eo_text_attachment(eo)
        attachments.append(("executive_order.txt", "text/plain", eo_text))
        
        return BuiltEmail(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            headers={}
        )
