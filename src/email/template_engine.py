"""
Template-Based Email Generation System

This module provides government-compliant email template management and rendering
for automated email generation in the Email Agent system.
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
import logging

logger = logging.getLogger(__name__)


class EmailTemplateType(Enum):
    """Supported email template types"""
    TASK_ASSIGNMENT = "task_assignment"
    PMO_APPROVAL_REQUEST = "pmo_approval_request"
    EXECUTIVE_SUMMARY = "executive_summary"
    DEVELOPER_NOTIFICATION = "developer_notification"


class GovernmentComplianceLevel(Enum):
    """Government compliance levels for email templates"""
    UNCLASSIFIED = "unclassified"
    SENSITIVE = "sensitive"
    CONFIDENTIAL = "confidential"


@dataclass
class EmailTemplate:
    """Email template configuration"""
    template_id: str
    template_type: EmailTemplateType
    name: str
    subject_template: str
    body_template: str
    compliance_level: GovernmentComplianceLevel
    required_fields: List[str]
    optional_fields: List[str]
    government_approved: bool
    version: str
    created_date: datetime
    last_modified: datetime


@dataclass
class TemplateContext:
    """Context data for template rendering"""
    recipient_name: str
    recipient_email: str
    sender_name: str
    sender_title: str
    organization: str
    date: datetime
    correlation_id: str
    additional_data: Dict[str, Any]


@dataclass
class TaskAssignmentContext(TemplateContext):
    """Context for task assignment emails"""
    task_id: str
    task_title: str
    task_description: str
    priority_level: str
    due_date: datetime
    project_name: str
    requirements: List[str]
    deliverables: List[str]


@dataclass
class PMOApprovalContext(TemplateContext):
    """Context for PMO approval request emails"""
    request_id: str
    request_type: str
    request_summary: str
    justification: str
    estimated_cost: Optional[float]
    estimated_timeline: str
    risk_assessment: str
    approval_deadline: datetime
    supporting_documents: List[str]


@dataclass
class ExecutiveSummaryContext(TemplateContext):
    """Context for executive summary emails"""
    report_title: str
    reporting_period: str
    key_metrics: Dict[str, Any]
    achievements: List[str]
    challenges: List[str]
    recommendations: List[str]
    attachments: List[str]
    next_steps: List[str]


@dataclass
class RenderedEmail:
    """Rendered email ready for delivery"""
    template_id: str
    subject: str
    body_html: str
    body_text: str
    recipient_email: str
    sender_email: str
    compliance_level: GovernmentComplianceLevel
    correlation_id: str
    metadata: Dict[str, Any]


class TemplateValidationError(Exception):
    """Raised when template validation fails"""
    pass


class TemplateRenderingError(Exception):
    """Raised when template rendering fails"""
    pass


class EmailTemplateEngine:
    """
    Government-compliant email template engine for automated email generation
    """
    
    def __init__(self, templates_directory: str = "templates/email"):
        """
        Initialize the template engine
        
        Args:
            templates_directory: Directory containing email templates
        """
        self.templates_directory = templates_directory
        self.templates: Dict[str, EmailTemplate] = {}
        self.jinja_env = Environment(
            loader=FileSystemLoader(templates_directory),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters for government compliance
        self.jinja_env.filters['government_date'] = self._format_government_date
        self.jinja_env.filters['classification_header'] = self._add_classification_header
        self.jinja_env.filters['sanitize_content'] = self._sanitize_content
        
        self._load_templates()
        logger.info(f"Initialized EmailTemplateEngine with {len(self.templates)} templates")
    
    def _load_templates(self) -> None:
        """Load all email templates from the templates directory"""
        if not os.path.exists(self.templates_directory):
            os.makedirs(self.templates_directory, exist_ok=True)
            self._create_default_templates()
        
        # Load template configurations
        config_file = os.path.join(self.templates_directory, "templates.json")
        if not os.path.exists(config_file):
            # Create default templates if config doesn't exist
            self._create_default_templates()
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                template_configs = json.load(f)
                
            for config in template_configs:
                template = EmailTemplate(
                    template_id=config['template_id'],
                    template_type=EmailTemplateType(config['template_type']),
                    name=config['name'],
                    subject_template=config['subject_template'],
                    body_template=config['body_template'],
                    compliance_level=GovernmentComplianceLevel(config['compliance_level']),
                    required_fields=config['required_fields'],
                    optional_fields=config['optional_fields'],
                    government_approved=config['government_approved'],
                    version=config['version'],
                    created_date=datetime.fromisoformat(config['created_date']),
                    last_modified=datetime.fromisoformat(config['last_modified'])
                )
                self.templates[template.template_id] = template
    
    def _create_default_templates(self) -> None:
        """Create default government-compliant email templates"""
        # Create templates directory structure
        os.makedirs(os.path.join(self.templates_directory, "task_assignment"), exist_ok=True)
        os.makedirs(os.path.join(self.templates_directory, "pmo_approval"), exist_ok=True)
        os.makedirs(os.path.join(self.templates_directory, "executive_summary"), exist_ok=True)
        
        # Task Assignment Template
        task_assignment_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ task_title | classification_header(compliance_level) }}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
        <header style="border-bottom: 2px solid #0066cc; padding-bottom: 10px; margin-bottom: 20px;">
            <h1 style="color: #0066cc; margin: 0;">U.S. Department of Labor</h1>
            <p style="margin: 5px 0 0 0; color: #666;">Task Assignment Notification</p>
        </header>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #0066cc; margin-bottom: 20px;">
            <h2 style="margin-top: 0; color: #0066cc;">Task Assignment: {{ task_title }}</h2>
            <p><strong>Task ID:</strong> {{ task_id }}</p>
            <p><strong>Priority:</strong> {{ priority_level }}</p>
            <p><strong>Due Date:</strong> {{ due_date | government_date }}</p>
            <p><strong>Project:</strong> {{ project_name }}</p>
        </div>
        
        <section style="margin-bottom: 20px;">
            <h3 style="color: #0066cc;">Task Description</h3>
            <p>{{ task_description | sanitize_content }}</p>
        </section>
        
        {% if requirements %}
        <section style="margin-bottom: 20px;">
            <h3 style="color: #0066cc;">Requirements</h3>
            <ul>
            {% for requirement in requirements %}
                <li>{{ requirement | sanitize_content }}</li>
            {% endfor %}
            </ul>
        </section>
        {% endif %}
        
        {% if deliverables %}
        <section style="margin-bottom: 20px;">
            <h3 style="color: #0066cc;">Expected Deliverables</h3>
            <ul>
            {% for deliverable in deliverables %}
                <li>{{ deliverable | sanitize_content }}</li>
            {% endfor %}
            </ul>
        </section>
        {% endif %}
        
        <section style="margin-bottom: 20px;">
            <h3 style="color: #0066cc;">Assignment Details</h3>
            <p><strong>Assigned to:</strong> {{ recipient_name }}</p>
            <p><strong>Assigned by:</strong> {{ sender_name }}, {{ sender_title }}</p>
            <p><strong>Organization:</strong> {{ organization }}</p>
            <p><strong>Assignment Date:</strong> {{ date | government_date }}</p>
        </section>
        
        <footer style="border-top: 1px solid #ddd; padding-top: 15px; margin-top: 30px; font-size: 12px; color: #666;">
            <p><strong>Correlation ID:</strong> {{ correlation_id }}</p>
            <p>This is an official communication from the U.S. Department of Labor. Please respond within 24 hours to confirm receipt.</p>
            <p>For questions or concerns, please contact your supervisor or the PMO.</p>
        </footer>
    </div>
</body>
</html>
        """
        
        task_assignment_text = """
U.S. DEPARTMENT OF LABOR
Task Assignment Notification

TASK ASSIGNMENT: {{ task_title | upper }}

Task ID: {{ task_id }}
Priority: {{ priority_level }}
Due Date: {{ due_date | government_date }}
Project: {{ project_name }}

TASK DESCRIPTION:
{{ task_description | sanitize_content }}

{% if requirements %}
REQUIREMENTS:
{% for requirement in requirements %}
- {{ requirement | sanitize_content }}
{% endfor %}
{% endif %}

{% if deliverables %}
EXPECTED DELIVERABLES:
{% for deliverable in deliverables %}
- {{ deliverable | sanitize_content }}
{% endfor %}
{% endif %}

ASSIGNMENT DETAILS:
Assigned to: {{ recipient_name }}
Assigned by: {{ sender_name }}, {{ sender_title }}
Organization: {{ organization }}
Assignment Date: {{ date | government_date }}

Correlation ID: {{ correlation_id }}

This is an official communication from the U.S. Department of Labor.
Please respond within 24 hours to confirm receipt.
For questions or concerns, please contact your supervisor or the PMO.
        """
        
        # PMO Approval Request Template
        pmo_approval_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ request_type | classification_header(compliance_level) }} - Approval Request</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
        <header style="border-bottom: 2px solid #dc3545; padding-bottom: 10px; margin-bottom: 20px;">
            <h1 style="color: #dc3545; margin: 0;">U.S. Department of Labor</h1>
            <p style="margin: 5px 0 0 0; color: #666;">PMO Approval Request</p>
        </header>
        
        <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin-bottom: 20px;">
            <h2 style="margin-top: 0; color: #856404;">APPROVAL REQUIRED</h2>
            <p><strong>Request ID:</strong> {{ request_id }}</p>
            <p><strong>Request Type:</strong> {{ request_type }}</p>
            <p><strong>Approval Deadline:</strong> {{ approval_deadline | government_date }}</p>
        </div>
        
        <section style="margin-bottom: 20px;">
            <h3 style="color: #dc3545;">Request Summary</h3>
            <p>{{ request_summary | sanitize_content }}</p>
        </section>
        
        <section style="margin-bottom: 20px;">
            <h3 style="color: #dc3545;">Justification</h3>
            <p>{{ justification | sanitize_content }}</p>
        </section>
        
        <section style="margin-bottom: 20px;">
            <h3 style="color: #dc3545;">Impact Assessment</h3>
            {% if estimated_cost %}
            <p><strong>Estimated Cost:</strong> ${{ "{:,.2f}".format(estimated_cost) }}</p>
            {% endif %}
            <p><strong>Estimated Timeline:</strong> {{ estimated_timeline }}</p>
            <p><strong>Risk Assessment:</strong> {{ risk_assessment | sanitize_content }}</p>
        </section>
        
        {% if supporting_documents %}
        <section style="margin-bottom: 20px;">
            <h3 style="color: #dc3545;">Supporting Documents</h3>
            <ul>
            {% for document in supporting_documents %}
                <li>{{ document | sanitize_content }}</li>
            {% endfor %}
            </ul>
        </section>
        {% endif %}
        
        <section style="margin-bottom: 20px;">
            <h3 style="color: #dc3545;">Request Details</h3>
            <p><strong>Requested by:</strong> {{ sender_name }}, {{ sender_title }}</p>
            <p><strong>Organization:</strong> {{ organization }}</p>
            <p><strong>Request Date:</strong> {{ date | government_date }}</p>
            <p><strong>PMO Contact:</strong> {{ recipient_name }}</p>
        </section>
        
        <div style="background-color: #f8d7da; padding: 15px; border-left: 4px solid #dc3545; margin-bottom: 20px;">
            <h3 style="margin-top: 0; color: #721c24;">Action Required</h3>
            <p>This request requires PMO approval before proceeding. Please review all documentation and provide approval or rejection with comments.</p>
            <p><strong>Response required by:</strong> {{ approval_deadline | government_date }}</p>
        </div>
        
        <footer style="border-top: 1px solid #ddd; padding-top: 15px; margin-top: 30px; font-size: 12px; color: #666;">
            <p><strong>Correlation ID:</strong> {{ correlation_id }}</p>
            <p>This is an official PMO approval request from the U.S. Department of Labor.</p>
            <p>All approvals must be documented and tracked for audit compliance.</p>
        </footer>
    </div>
</body>
</html>
        """
        
        pmo_approval_text = """
U.S. DEPARTMENT OF LABOR
PMO Approval Request

*** APPROVAL REQUIRED ***

Request ID: {{ request_id }}
Request Type: {{ request_type }}
Approval Deadline: {{ approval_deadline | government_date }}

REQUEST SUMMARY:
{{ request_summary | sanitize_content }}

JUSTIFICATION:
{{ justification | sanitize_content }}

IMPACT ASSESSMENT:
{% if estimated_cost %}
Estimated Cost: ${{ "{:,.2f}".format(estimated_cost) }}
{% endif %}
Estimated Timeline: {{ estimated_timeline }}
Risk Assessment: {{ risk_assessment | sanitize_content }}

{% if supporting_documents %}
SUPPORTING DOCUMENTS:
{% for document in supporting_documents %}
- {{ document | sanitize_content }}
{% endfor %}
{% endif %}

REQUEST DETAILS:
Requested by: {{ sender_name }}, {{ sender_title }}
Organization: {{ organization }}
Request Date: {{ date | government_date }}
PMO Contact: {{ recipient_name }}

ACTION REQUIRED:
This request requires PMO approval before proceeding. Please review all 
documentation and provide approval or rejection with comments.
Response required by: {{ approval_deadline | government_date }}

Correlation ID: {{ correlation_id }}

This is an official PMO approval request from the U.S. Department of Labor.
All approvals must be documented and tracked for audit compliance.
        """
        
        # Write template files
        with open(os.path.join(self.templates_directory, "task_assignment", "template.html"), 'w') as f:
            f.write(task_assignment_html.strip())
        
        with open(os.path.join(self.templates_directory, "task_assignment", "template.txt"), 'w') as f:
            f.write(task_assignment_text.strip())
        
        with open(os.path.join(self.templates_directory, "pmo_approval", "template.html"), 'w') as f:
            f.write(pmo_approval_html.strip())
        
        with open(os.path.join(self.templates_directory, "pmo_approval", "template.txt"), 'w') as f:
            f.write(pmo_approval_text.strip())
        
        # Create template configuration
        templates_config = [
            {
                "template_id": "task_assignment_v1",
                "template_type": "task_assignment",
                "name": "Developer Task Assignment",
                "subject_template": "Task Assignment: {{ task_title }} - {{ task_id }} ({{ priority_level }} Priority)",
                "body_template": "task_assignment/template.html",
                "compliance_level": "unclassified",
                "required_fields": ["task_id", "task_title", "task_description", "priority_level", "due_date", "project_name"],
                "optional_fields": ["requirements", "deliverables"],
                "government_approved": True,
                "version": "1.0",
                "created_date": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat()
            },
            {
                "template_id": "pmo_approval_v1",
                "template_type": "pmo_approval_request",
                "name": "PMO Approval Request",
                "subject_template": "PMO Approval Required: {{ request_type }} ({{ request_id }})",
                "body_template": "pmo_approval/template.html",
                "compliance_level": "sensitive",
                "required_fields": ["request_id", "request_type", "request_summary", "justification", "estimated_timeline", "risk_assessment", "approval_deadline"],
                "optional_fields": ["estimated_cost", "supporting_documents"],
                "government_approved": True,
                "version": "1.0",
                "created_date": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat()
            }
        ]
        
        with open(os.path.join(self.templates_directory, "templates.json"), 'w') as f:
            json.dump(templates_config, f, indent=2)
    
    def _format_government_date(self, date_value: datetime) -> str:
        """Format date according to government standards"""
        return date_value.strftime("%d %B %Y at %H:%M %Z")
    
    def _add_classification_header(self, content: str, compliance_level: GovernmentComplianceLevel) -> str:
        """Add classification header to content"""
        classification_map = {
            GovernmentComplianceLevel.UNCLASSIFIED: "UNCLASSIFIED",
            GovernmentComplianceLevel.SENSITIVE: "SENSITIVE",
            GovernmentComplianceLevel.CONFIDENTIAL: "CONFIDENTIAL"
        }
        classification = classification_map.get(compliance_level, "UNCLASSIFIED")
        return f"[{classification}] {content}"
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content for government compliance"""
        if not content:
            return ""
        
        # Remove potentially sensitive patterns
        import re
        
        # Remove email addresses except government domains
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@(?!.*\.gov\b)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', content)
        
        # Remove phone numbers
        content = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', content)
        
        # Remove SSNs
        content = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', content)
        
        return content
    
    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self, template_type: Optional[EmailTemplateType] = None) -> List[EmailTemplate]:
        """List available templates, optionally filtered by type"""
        templates = list(self.templates.values())
        if template_type:
            templates = [t for t in templates if t.template_type == template_type]
        return templates
    
    def validate_template_context(self, template: EmailTemplate, context: Dict[str, Any]) -> bool:
        """Validate that context contains all required fields"""
        missing_fields = []
        for field in template.required_fields:
            if field not in context:
                missing_fields.append(field)
        
        if missing_fields:
            raise TemplateValidationError(f"Missing required fields: {missing_fields}")
        
        return True
    
    def render_email(self, template_id: str, context: TemplateContext) -> RenderedEmail:
        """
        Render an email using the specified template and context
        
        Args:
            template_id: ID of the template to use
            context: Context data for rendering
            
        Returns:
            RenderedEmail object with rendered content
            
        Raises:
            TemplateValidationError: If template validation fails
            TemplateRenderingError: If rendering fails
        """
        template = self.get_template(template_id)
        if not template:
            raise TemplateValidationError(f"Template not found: {template_id}")
        
        # Convert context to dictionary
        context_dict = asdict(context)
        
        # Validate context
        self.validate_template_context(template, context_dict)
        
        try:
            # Render subject
            subject_template = Template(template.subject_template)
            subject = subject_template.render(**context_dict, compliance_level=template.compliance_level)
            
            # Render HTML body
            html_template = self.jinja_env.get_template(template.body_template)
            body_html = html_template.render(**context_dict, compliance_level=template.compliance_level)
            
            # Render text body (try to find .txt version)
            text_template_path = template.body_template.replace('.html', '.txt')
            try:
                text_template = self.jinja_env.get_template(text_template_path)
                body_text = text_template.render(**context_dict, compliance_level=template.compliance_level)
            except:
                # Fallback to HTML content stripped of tags
                import re
                body_text = re.sub('<[^<]+?>', '', body_html)
                body_text = re.sub(r'\n\s*\n', '\n\n', body_text)
            
            return RenderedEmail(
                template_id=template_id,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                recipient_email=context.recipient_email,
                sender_email=f"{context.sender_name.lower().replace(' ', '.')}@dol.gov",
                compliance_level=template.compliance_level,
                correlation_id=context.correlation_id,
                metadata={
                    "template_version": template.version,
                    "render_timestamp": datetime.now().isoformat(),
                    "government_approved": template.government_approved
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to render template {template_id}: {str(e)}")
            raise TemplateRenderingError(f"Template rendering failed: {str(e)}")
    
    def render_task_assignment_email(self, context: TaskAssignmentContext) -> RenderedEmail:
        """Render a task assignment email"""
        return self.render_email("task_assignment_v1", context)
    
    def render_pmo_approval_email(self, context: PMOApprovalContext) -> RenderedEmail:
        """Render a PMO approval request email"""
        return self.render_email("pmo_approval_v1", context)
    
    def render_executive_summary_email(self, context: ExecutiveSummaryContext) -> RenderedEmail:
        """Render an executive summary email with professional formatting"""
        return self.render_email("executive_summary_v1", context)
    
    def validate_government_compliance(self, rendered_email: RenderedEmail) -> bool:
        """
        Validate that rendered email meets government compliance requirements
        
        Args:
            rendered_email: The rendered email to validate
            
        Returns:
            True if compliant, raises exception otherwise
        """
        # Check for required government headers
        if not rendered_email.correlation_id:
            raise TemplateValidationError("Missing correlation ID for audit trail")
        
        # Check for proper classification
        if rendered_email.compliance_level == GovernmentComplianceLevel.CONFIDENTIAL:
            if "CONFIDENTIAL" not in rendered_email.subject:
                raise TemplateValidationError("Confidential emails must have classification in subject")
        
        # Check for government domain
        if not rendered_email.sender_email.endswith('.gov'):
            raise TemplateValidationError("Sender must use government email domain")
        
        # Check for required footer information
        if "U.S. Department of Labor" not in rendered_email.body_html:
            raise TemplateValidationError("Missing official government identification")
        
        logger.info(f"Email {rendered_email.correlation_id} passed government compliance validation")
        return True