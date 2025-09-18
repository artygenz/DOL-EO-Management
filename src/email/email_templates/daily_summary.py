"""
Daily Summary email template for sending daily task update summaries to PMOs.
"""

from typing import Dict, List
from datetime import datetime
from .base import BaseEmailTemplate, BuiltEmail


class DailySummaryTemplate(BaseEmailTemplate):
    """Template for daily summary emails."""
    
    @staticmethod
    def build_daily_summary(eo: Dict, summary: Dict, task_updates: List[Dict]) -> BuiltEmail:
        """Build daily summary email with comprehensive task updates."""
        subject = f"Daily Summary - {DailySummaryTemplate._get_eo_property(eo, 'title')} - {summary.get('date', 'Unknown Date')}"
        
        # Group updates by status
        completed_updates = [u for u in task_updates if u.get('status') == 'Completed']
        in_progress_updates = [u for u in task_updates if u.get('status') == 'InProgress']
        blocked_updates = [u for u in task_updates if u.get('status') == 'Blocked']
        
        # TEXT VERSION
        lines = [
            f"Daily Summary Report - {DailySummaryTemplate._get_eo_property(eo, 'title')}",
            f"Date: {summary.get('date', 'Unknown')}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "EXECUTIVE SUMMARY",
            "=" * 50,
            summary.get('progress_summary', 'No summary available'),
            "",
            f"Key Metrics:",
            f"- Total Tasks: {summary.get('total_tasks', 0)}",
            f"- Updated Tasks: {summary.get('updated_tasks', 0)}",
            f"- Missing Updates: {len(summary.get('missing_updates', []))}",
            ""
        ]
        
        # Add blockers section
        if summary.get('key_blockers'):
            lines.extend([
                "KEY BLOCKERS & ISSUES",
                "=" * 50,
            ])
            for blocker in summary['key_blockers']:
                lines.append(f"• {blocker}")
            lines.append("")
        
        # Add risks section
        if summary.get('risks'):
            lines.extend([
                "RISK ASSESSMENT",
                "=" * 50,
            ])
            for risk in summary['risks']:
                lines.append(f"• {risk}")
            lines.append("")
        
        # Add attention items section
        if summary.get('attention_items'):
            lines.extend([
                "ATTENTION ITEMS",
                "=" * 50,
            ])
            for item in summary['attention_items']:
                lines.append(f"• {item}")
            lines.append("")
        
        # Add individual task updates
        lines.extend([
            "INDIVIDUAL TASK UPDATES",
            "=" * 50,
        ])
        
        # Completed tasks
        lines.extend([
            f"✅ COMPLETED TASKS ({len(completed_updates)})",
            "-" * 30,
        ])
        if completed_updates:
            for update in completed_updates:
                lines.extend([
                    f"Task: {update.get('task_title', 'Unknown Task')}",
                    f"Assignee: {update.get('user_name', 'Unknown')}",
                    f"Progress: {update.get('progress_pct', 0)}%",
                    f"Hours Spent: {update.get('spent_hours', 0)}h",
                    f"Notes: {update.get('notes', 'No notes provided')}",
                ])
                if update.get('ai_summary'):
                    lines.append(f"AI Summary: {update.get('ai_summary')}")
                lines.append("")
        else:
            lines.append("• No tasks completed today")
            lines.append("")
        
        # In Progress tasks
        lines.extend([
            f"🔄 IN PROGRESS TASKS ({len(in_progress_updates)})",
            "-" * 30,
        ])
        if in_progress_updates:
            for update in in_progress_updates:
                lines.extend([
                    f"Task: {update.get('task_title', 'Unknown Task')}",
                    f"Assignee: {update.get('user_name', 'Unknown')}",
                    f"Progress: {update.get('progress_pct', 0)}%",
                    f"Hours Spent: {update.get('spent_hours', 0)}h",
                    f"Notes: {update.get('notes', 'No notes provided')}",
                ])
                if update.get('ai_summary'):
                    lines.append(f"AI Summary: {update.get('ai_summary')}")
                if update.get('blockers'):
                    lines.append(f"Blockers: {', '.join(update['blockers'])}")
                if update.get('risks'):
                    lines.append(f"Risks: {', '.join(update['risks'])}")
                lines.append("")
        else:
            lines.append("• No tasks in progress")
            lines.append("")
        
        # Blocked tasks
        lines.extend([
            f"BLOCKED TASKS ({len(blocked_updates)})",
            "-" * 30,
        ])
        if blocked_updates:
            for update in blocked_updates:
                lines.extend([
                    f"Task: {update.get('task_title', 'Unknown Task')}",
                    f"Assignee: {update.get('user_name', 'Unknown')}",
                    f"Progress: {update.get('progress_pct', 0)}%",
                    f"Hours Spent: {update.get('spent_hours', 0)}h",
                    f"Notes: {update.get('notes', 'No notes provided')}",
                ])
                if update.get('ai_summary'):
                    lines.append(f"AI Summary: {update.get('ai_summary')}")
                if update.get('blockers'):
                    lines.append(f"Blockers: {', '.join(update['blockers'])}")
                if update.get('risks'):
                    lines.append(f"Risks: {', '.join(update['risks'])}")
                lines.append("")
        else:
            lines.append("• No tasks currently blocked")
            lines.append("")
        
        # Missing updates
        lines.extend([
            "MISSING UPDATES",
            "=" * 50,
        ])
        if summary.get('missing_updates'):
            lines.append("Employees who haven't provided updates:")
            for email in summary['missing_updates']:
                lines.append(f"• {email}")
        else:
            lines.append("• All expected updates received")
        
        lines.extend([
            "",
            "=" * 50,
            "This report was automatically generated by the DOL EO Management System.",
            "For questions or issues, please contact the system administrator."
        ])
        
        body_text = "\n".join(lines)

        # HTML VERSION WITH ENHANCED CSS
        body_html = DailySummaryTemplate._build_html_content(eo, summary, completed_updates, in_progress_updates, blocked_updates)
        
        return BuiltEmail(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=[],
            headers={}
        )
    
    @staticmethod
    def _build_html_content(eo: Dict, summary: Dict, completed_updates: List[Dict], 
                           in_progress_updates: List[Dict], blocked_updates: List[Dict]) -> str:
        """Build the HTML content with CSS styling."""
        
        def format_task_update(update, status_class):
            blockers_str = ', '.join(update.get('blockers', [])) if update.get('blockers') else 'None'
            risks_str = ', '.join(update.get('risks', [])) if update.get('risks') else 'None'
            
            blockers_html = f'''
            <div class="blockers-list">
                <h4>BLOCKERS</h4>
                <ul><li>{blockers_str}</li></ul>
            </div>
            ''' if update.get('blockers') else ''
            
            risks_html = f'''
            <div class="risks-list">
                <h4>⚠️ Risks</h4>
                <ul><li>{risks_str}</li></ul>
            </div>
            ''' if update.get('risks') else ''
            
            return f'''
            <div class="task-item {status_class}">
                <div class="task-title">{update.get('task_title', 'Unknown Task')}</div>
                <div class="task-details">
                    <div class="task-detail">
                    
                        <span class="label">Assignee</span>
                        <span class="value">{update.get('user_name', 'Unknown')}</span>
                    </div>
                    <div class="task-detail">
                        <span class="label">Progress</span>
                        <span class="value">{update.get('progress_pct', 0)}%</span>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {update.get('progress_pct', 0)}%"></div>
                        </div>
                    </div>
                    <div class="task-detail">
                        <span class="label">Hours Spent</span>
                        <span class="value">{update.get('spent_hours', 0)}h</span>
                    </div>
                    <div class="task-detail">
                        <span class="label">Status</span>
                        <span class="value"><span class="status-badge status-{status_class}">{status_class.title()}</span></span>
                    </div>
                </div>
                <div class="task-detail" style="margin-top: 10px;">
                    <span class="label">Notes</span>
                    <span class="value">{update.get('notes', 'No notes provided')}</span>
                </div>
                {f'<div class="task-detail" style="margin-top: 10px;"><span class="label">AI Summary</span><span class="value">{update.get("ai_summary", "No AI summary available")}</span></div>' if update.get('ai_summary') else ''}
                {blockers_html}
                {risks_html}
            </div>
            '''
        
        def format_simple_task_update(update):
            return f'''
            <div class="task-item completed">
                <div class="task-title">{update.get('task_title', 'Unknown Task')}</div>
                <div class="task-details">
                    <div class="task-detail">
                        <span class="label">Assignee</span>
                        <span class="value">{update.get('user_name', 'Unknown')}</span>
                    </div>
                    <div class="task-detail">
                        <span class="label">Progress</span>
                        <span class="value">{update.get('progress_pct', 0)}%</span>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {update.get('progress_pct', 0)}%"></div>
                        </div>
                    </div>
                    <div class="task-detail">
                        <span class="label">Hours Spent</span>
                        <span class="value">{update.get('spent_hours', 0)}h</span>
                    </div>
                    <div class="task-detail">
                        <span class="label">Status</span>
                        <span class="value"><span class="status-badge status-completed">Completed</span></span>
                    </div>
                </div>
                <div class="task-detail" style="margin-top: 10px;">
                    <span class="label">Notes</span>
                    <span class="value">{update.get('notes', 'No notes provided')}</span>
                </div>
                {f'<div class="task-detail" style="margin-top: 10px;"><span class="label">AI Summary</span><span class="value">{update.get("ai_summary", "No AI summary available")}</span></div>' if update.get('ai_summary') else ''}
            </div>
            '''
        
        # Build sections
        blockers_section = ''.join(f'<li><strong>{blocker}</strong></li>' for blocker in (summary.get('key_blockers') or []))
        blockers_html = f'<ul>{blockers_section}</ul>' if blockers_section else '<p><em>• No major blockers identified</em></p>'
        
        risks_section = ''.join(f'<li><strong>{risk}</strong></li>' for risk in (summary.get('risks') or []))
        risks_html = f'<ul>{risks_section}</ul>' if risks_section else '<p><em>• No significant risks identified</em></p>'
        
        attention_section = ''.join(f'<li><strong>{item}</strong></li>' for item in (summary.get('attention_items') or []))
        attention_html = f'<ul>{attention_section}</ul>' if attention_section else '<p><em>• No items requiring immediate attention</em></p>'
        
        missing_section = ''.join(f'<li><strong>{email}</strong></li>' for email in (summary.get('missing_updates') or []))
        missing_html = f'''
        <div class="missing-updates">
            <h4>Employees who haven't provided updates:</h4>
            <ul>{missing_section}</ul>
        </div>
        ''' if missing_section else '<p><em>• All expected updates received</em></p>'
        
        completed_section = ''.join(format_simple_task_update(update) for update in completed_updates) if completed_updates else '<p><em>• No tasks completed today</em></p>'
        in_progress_section = ''.join(format_task_update(update, 'in-progress') for update in in_progress_updates) if in_progress_updates else '<p><em>• No tasks in progress</em></p>'
        blocked_section = ''.join(format_task_update(update, 'blocked') for update in blocked_updates) if blocked_updates else '<p><em>• No tasks currently blocked</em></p>'
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Summary - {DailySummaryTemplate._get_eo_property(eo, 'title')}</title>
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
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
            margin: 20px 0;
        }}
        .header {{
            border-bottom: 3px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #007bff;
            margin: 0 0 10px 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .header .meta {{
            color: #666;
            font-size: 14px;
            margin: 0;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #495057;
            border-left: 4px solid #007bff;
            padding-left: 15px;
            margin: 25px 0 15px 0;
            font-size: 20px;
            font-weight: 600;
        }}
        .section h3 {{
            color: #6c757d;
            margin: 20px 0 10px 0;
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .metric-card .number {{
            font-size: 24px;
            font-weight: bold;
            display: block;
        }}
        .metric-card .label {{
            font-size: 12px;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .task-list {{
            margin: 15px 0;
        }}
        .task-item {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #28a745;
        }}
        .task-item.blocked {{
            border-left-color: #dc3545;
            background-color: #fff5f5;
        }}
        .task-item.in-progress {{
            border-left-color: #ffc107;
            background-color: #fffbf0;
        }}
        .task-item.completed {{
            border-left-color: #28a745;
            background-color: #f0fff4;
        }}
        .task-title {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 8px;
            font-size: 16px;
        }}
        .task-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            font-size: 14px;
        }}
        .task-detail {{
            display: flex;
            flex-direction: column;
        }}
        .task-detail .label {{
            font-weight: 600;
            color: #6c757d;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .task-detail .value {{
            color: #495057;
            margin-top: 2px;
        }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background-color: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        .blockers-list, .risks-list {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 10px;
            margin: 10px 0;
        }}
        .blockers-list h4, .risks-list h4 {{
            color: #856404;
            margin: 0 0 8px 0;
            font-size: 14px;
            font-weight: 600;
        }}
        .blockers-list ul, .risks-list ul {{
            margin: 0;
            padding-left: 20px;
            color: #856404;
        }}
        .missing-updates {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            padding: 15px;
            margin: 15px 0;
        }}
        .missing-updates h4 {{
            color: #721c24;
            margin: 0 0 10px 0;
            font-size: 14px;
            font-weight: 600;
        }}
        .missing-updates ul {{
            margin: 0;
            padding-left: 20px;
            color: #721c24;
        }}
        .footer {{
            border-top: 1px solid #e9ecef;
            padding-top: 20px;
            margin-top: 30px;
            text-align: center;
            color: #6c757d;
            font-size: 12px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .status-completed {{
            background-color: #d4edda;
            color: #155724;
        }}
        .status-in-progress {{
            background-color: #fff3cd;
            color: #856404;
        }}
        .status-blocked {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        @media (max-width: 600px) {{
            body {{
                padding: 10px;
            }}
            .email-container {{
                padding: 20px;
            }}
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            .task-details {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>📊 Daily Summary Report</h1>
            <p class="meta">
                <strong>EO:</strong> {DailySummaryTemplate._get_eo_property(eo, 'title')}<br>
                <strong>Date:</strong> {summary.get('date', 'Unknown')}<br>
                <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </p>
        </div>

        <div class="section">
            <h2>📈 Executive Summary</h2>
            <p>{summary.get('progress_summary', 'No summary available').replace(chr(10), '<br>')}</p>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <span class="number">{summary.get('total_tasks', 0)}</span>
                    <span class="label">Total Tasks</span>
                </div>
                <div class="metric-card">
                    <span class="number">{summary.get('updated_tasks', 0)}</span>
                    <span class="label">Updated Tasks</span>
                </div>
                <div class="metric-card">
                    <span class="number">{len(summary.get('missing_updates', []))}</span>
                    <span class="label">Missing Updates</span>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🚧 Key Blockers & Issues</h2>
            {blockers_html}
        </div>

        <div class="section">
            <h2>⚠️ Risk Assessment</h2>
            {risks_html}
        </div>

        <div class="section">
            <h2>🔍 Attention Items</h2>
            {attention_html}
        </div>

        <div class="section">
            <h2>📋 Individual Task Updates</h2>
            
            <h3>✅ Completed Tasks ({len(completed_updates)})</h3>
            <div class="task-list">
                {completed_section}
            </div>

            <h3>🔄 In Progress Tasks ({len(in_progress_updates)})</h3>
            <div class="task-list">
                {in_progress_section}
            </div>

            <h3>BLOCKED TASKS ({len(blocked_updates)})</h3>
            <div class="task-list">
                {blocked_section}
            </div>
        </div>

        <div class="section">
            <h2>📧 Missing Updates</h2>
            {missing_html}
        </div>

        <div class="footer">
            <p><strong>This report was automatically generated by the DOL EO Management System.</strong><br>
            For questions or issues, please contact the system administrator.</p>
        </div>
    </div>
</body>
</html>
        """
