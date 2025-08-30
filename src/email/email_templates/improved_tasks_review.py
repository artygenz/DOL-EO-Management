"""
Improved tasks review email template for sending improved tasks back to PMO for re-review.
"""

from typing import Dict, List
from .base import BaseEmailTemplate, BuiltEmail


class ImprovedTasksReviewTemplate(BaseEmailTemplate):
    """Template for improved tasks review emails."""
    
    @staticmethod
    def build_improved_tasks_review(eo, rows: List[Dict], improvement_summary: str) -> BuiltEmail:
        """Build improved tasks review email."""
        subject = f"Improved Tasks Review: {ImprovedTasksReviewTemplate._get_eo_property(eo, 'title') or 'Executive Order'} [EO ID: {ImprovedTasksReviewTemplate._get_eo_property(eo, 'id')}]"
        
        # TEXT VERSION
        lines = [
            f"Subject EO: {ImprovedTasksReviewTemplate._get_eo_property(eo, 'title') or '(no subject)'}",
            f"EO ID: {ImprovedTasksReviewTemplate._get_eo_property(eo, 'id')}",
            f"EO Message-ID: {ImprovedTasksReviewTemplate._get_eo_property(eo, 'message_id')}",
            f"Received: {ImprovedTasksReviewTemplate._fmt_dt(ImprovedTasksReviewTemplate._get_eo_property(eo, 'received_at'))}",
            "",
            "=== IMPROVEMENT SUMMARY ===",
            improvement_summary,
            "",
            "Below are ALL tasks for this EO with their current status.",
            "Tasks marked as 'Approved' were previously approved and do not need action.",
            "Tasks marked as 'Pending PMO approval' are improved versions that need your review.",
            "",
            "INSTRUCTIONS:",
            "1. Copy the table below",
            "2. Paste it in your reply email", 
            "3. For 'Pending PMO approval' tasks: Fill in the 'Status' column with 'Approve' or 'Reject'",
            "4. For 'Pending PMO approval' tasks: Fill in the 'Remarks' column with your feedback",
            "5. Leave 'Approved' tasks as-is (no action needed)",
            "6. Send the email back",
            "",
            "NOTE: Please refer to the attached files for detailed information:",
            "- CSV file: Complete task details in spreadsheet format",
            "- JSON file: Structured task data",
            "- TXT file: Full Executive Order text",
            ""
        ]
        
        # Build table header
        table_lines = [
            "Task ID | Title | Owner | Assignee | Due | Status | Remarks",
            "--------|-------|-------|----------|-----|--------|--------"
        ]
        
        # Add task rows with sequential IDs (1, 2, 3, ...)
        for idx, r in enumerate(rows, start=1):
            title = r.get('title') or '(untitled)'
            current_status = r.get('status', 'Unknown')
            
            # Determine what to show in Status and Remarks columns
            if current_status == 'approved':
                status_display = "Approved"
                remarks_display = "N/A"
            else:
                status_display = "[Fill Here]"
                remarks_display = "[Fill Here]"
            
            table_lines.append(
                f"{idx} | {title} | {r.get('owner') or '—'} | {r.get('assignee') or '—'} | {r.get('due_date') or '—'} | {status_display} | {remarks_display}"
            )
        
        lines.extend(table_lines)
        body_text = "\n".join(lines)

        # HTML VERSION WITH ENHANCED CSS
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Improved Tasks Review</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .email-container {{
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 300;
                }}
                .content {{
                    padding: 30px;
                }}
                .eo-info {{
                    background-color: #e3f2fd;
                    border-left: 4px solid #2196f3;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .improvement-summary {{
                    background-color: #e8f5e8;
                    border-left: 4px solid #4caf50;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .improvement-summary h3 {{
                    margin-top: 0;
                    color: #2e7d32;
                }}
                .instructions {{
                    background-color: #fff3e0;
                    border-left: 4px solid #ff9800;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .instructions h3 {{
                    margin-top: 0;
                    color: #e65100;
                }}
                .instructions ol {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
                .instructions li {{
                    margin: 5px 0;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #e0e0e0;
                }}
                th {{
                    background-color: #f5f5f5;
                    font-weight: 600;
                    color: #333;
                }}
                tr:hover {{
                    background-color: #f8f9fa;
                }}
                .fill-here {{
                    color: #999;
                    font-style: italic;
                }}
                .status-approved {{
                    color: #27ae60;
                    font-weight: 600;
                }}
                .attachments {{
                    background-color: #f1f8e9;
                    border-left: 4px solid #4caf50;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .attachments h3 {{
                    margin-top: 0;
                    color: #2e7d32;
                }}
                .footer {{
                    background-color: #f5f5f5;
                    padding: 20px;
                    text-align: center;
                    color: #666;
                    border-top: 1px solid #e0e0e0;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>🔄 Improved Tasks Review</h1>
                </div>
                
                <div class="content">
                    <div class="eo-info">
                        <strong>Executive Order:</strong> {ImprovedTasksReviewTemplate._get_eo_property(eo, 'title') or '(no subject)'}<br>
                        <strong>EO ID:</strong> {ImprovedTasksReviewTemplate._get_eo_property(eo, 'id')}<br>
                        <strong>Message ID:</strong> {ImprovedTasksReviewTemplate._get_eo_property(eo, 'message_id')}<br>
                        <strong>Received:</strong> {ImprovedTasksReviewTemplate._fmt_dt(ImprovedTasksReviewTemplate._get_eo_property(eo, 'received_at'))}
                    </div>
                    
                    <div class="improvement-summary">
                        <h3>📈 Improvement Summary:</h3>
                        <p>{improvement_summary}</p>
                    </div>
                    
                    <p>Below are <strong>ALL tasks</strong> for this EO with their current status.</p>
                    <p><strong>Tasks marked as 'Approved'</strong> were previously approved and do not need action.</p>
                    <p><strong>Tasks marked as 'Pending PMO approval'</strong> are improved versions that need your review.</p>
                    
                    <div class="instructions">
                        <h3>📝 Instructions:</h3>
                        <ol>
                            <li>Copy the table below</li>
                            <li>Paste it in your reply email</li>
                            <li>For 'Pending PMO approval' tasks: Fill in the 'Status' column with 'Approve' or 'Reject'</li>
                            <li>For 'Pending PMO approval' tasks: Fill in the 'Remarks' column with your feedback</li>
                            <li>Leave 'Approved' tasks as-is (no action needed)</li>
                            <li>Send the email back</li>
                        </ol>
                    </div>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>Task ID</th>
                                <th>Title</th>
                                <th>Owner</th>
                                <th>Assignee</th>
                                <th>Due</th>
                                <th>Status</th>
                                <th>Remarks</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # Add task rows
        for idx, r in enumerate(rows, start=1):
            title = r.get('title') or '(untitled)'
            current_status = r.get('status', 'Unknown')
            
            # Determine what to show in Status and Remarks columns
            if current_status == 'approved':
                status_display = "Approved"
                remarks_display = "N/A"
                status_class = "status-approved"
            else:
                status_display = "[Fill Here]"
                remarks_display = "[Fill Here]"
                status_class = "fill-here"
            
            body_html += f"""
                            <tr>
                                <td>{idx}</td>
                                <td>{title}</td>
                                <td>{r.get('owner') or '—'}</td>
                                <td>{r.get('assignee') or '—'}</td>
                                <td>{r.get('due_date') or '—'}</td>
                                <td class="{status_class}">{status_display}</td>
                                <td class="{status_class}">{remarks_display}</td>
                            </tr>
            """
        
        body_html += f"""
                        </tbody>
                    </table>
                    
                    <div class="attachments">
                        <h3>📎 Attachments:</h3>
                        <p>Please refer to the attached files for detailed information:</p>
                        <ul>
                            <li><strong>CSV file:</strong> Complete task details in spreadsheet format</li>
                            <li><strong>JSON file:</strong> Structured task data</li>
                            <li><strong>TXT file:</strong> Full Executive Order text</li>
                        </ul>
                    </div>
                </div>
                
                <div class="footer">
                    <p>DOL EO Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create attachments
        attachments = []
        
        # CSV attachment
        csv_data = ImprovedTasksReviewTemplate._build_csv_attachment(rows, "improved_tasks")
        attachments.append(("improved_tasks.csv", "text/csv", csv_data))
        
        # JSON attachment
        json_data = ImprovedTasksReviewTemplate._build_json_attachment(eo, rows, "improved_tasks")
        attachments.append(("improved_tasks.json", "application/json", json_data))
        
        # EO text attachment
        eo_text = ImprovedTasksReviewTemplate._build_eo_text_attachment(eo)
        attachments.append(("executive_order.txt", "text/plain", eo_text))
        
        return BuiltEmail(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            headers={}
        )
