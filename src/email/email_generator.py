"""
Email Generator for Automated Email Generation

This module provides high-level email generation functionality for the Email Agent,
using the template engine to create government-compliant emails for various workflows.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid

from .template_engine import (
    EmailTemplateEngine, 
    TemplateContext, 
    TaskAssignmentContext, 
    PMOApprovalContext,
    ExecutiveSummaryContext,
    RenderedEmail,
    EmailTemplateType,
    GovernmentComplianceLevel
)

logger = logging.getLogger(__name__)


@dataclass
class TaskAssignmentData:
    """Data for task assignment email generation"""
    task_id: str
    task_title: str
    task_description: str
    priority_level: str  # HIGH, MEDIUM, LOW
    due_date: datetime
    project_name: str
    requirements: List[str]
    deliverables: List[str]
    assignee_name: str
    assignee_email: str


@dataclass
class PMOApprovalData:
    """Data for PMO approval request email generation"""
    request_id: str
    request_type: str
    request_summary: str
    justification: str
    estimated_cost: Optional[float]
    estimated_timeline: str
    risk_assessment: str
    approval_deadline: datetime
    supporting_documents: List[str]
    pmo_contact_name: str
    pmo_contact_email: str


@dataclass
class AttachmentInfo:
    """Information about an email attachment"""
    filename: str
    description: str
    file_type: str
    size_mb: Optional[float] = None
    is_dashboard_report: bool = False
    requires_executive_review: bool = True


@dataclass
class ExecutiveSummaryData:
    """Data for executive summary email generation with enhanced attachment support"""
    report_title: str
    reporting_period: str
    executive_name: str
    executive_email: str
    key_metrics: Optional[Dict[str, Any]] = None
    achievements: Optional[List[str]] = None
    challenges: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    attachments: Optional[List[str]] = None  # Simple string list for backward compatibility
    attachment_info: Optional[List[AttachmentInfo]] = None  # Enhanced attachment information
    next_steps: Optional[List[str]] = None
    priority_level: str = "HIGH"  # HIGH, CRITICAL, URGENT
    requires_acknowledgment: bool = True
    confidentiality_level: str = "SENSITIVE"  # UNCLASSIFIED, SENSITIVE, CONFIDENTIAL


class EmailGenerationError(Exception):
    """Raised when email generation fails"""
    pass


class EmailGenerator:
    """
    High-level email generator for automated workflow emails
    """
    
    def __init__(self, templates_directory: str = "templates/email"):
        """
        Initialize the email generator
        
        Args:
            templates_directory: Directory containing email templates
        """
        self.template_engine = EmailTemplateEngine(templates_directory)
        self.default_sender_name = "DOL Email Agent"
        self.default_sender_title = "Automated System"
        self.default_organization = "U.S. Department of Labor"
        
        logger.info("Initialized EmailGenerator")
    
    def generate_task_assignment_email(
        self, 
        task_data: TaskAssignmentData,
        sender_name: Optional[str] = None,
        sender_title: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> RenderedEmail:
        """
        Generate a task assignment email for developer workflows
        
        Args:
            task_data: Task assignment data
            sender_name: Name of the person assigning the task
            sender_title: Title of the person assigning the task
            correlation_id: Correlation ID for tracking
            
        Returns:
            RenderedEmail ready for delivery
            
        Raises:
            EmailGenerationError: If generation fails
        """
        try:
            # Create context
            context = TaskAssignmentContext(
                # Base context
                recipient_name=task_data.assignee_name,
                recipient_email=task_data.assignee_email,
                sender_name=sender_name or self.default_sender_name,
                sender_title=sender_title or self.default_sender_title,
                organization=self.default_organization,
                date=datetime.now(),
                correlation_id=correlation_id or str(uuid.uuid4()),
                additional_data={},
                
                # Task-specific context
                task_id=task_data.task_id,
                task_title=task_data.task_title,
                task_description=task_data.task_description,
                priority_level=task_data.priority_level,
                due_date=task_data.due_date,
                project_name=task_data.project_name,
                requirements=task_data.requirements,
                deliverables=task_data.deliverables
            )
            
            # Render email
            rendered_email = self.template_engine.render_task_assignment_email(context)
            
            # Validate compliance
            self.template_engine.validate_government_compliance(rendered_email)
            
            logger.info(f"Generated task assignment email for task {task_data.task_id}")
            return rendered_email
            
        except Exception as e:
            logger.error(f"Failed to generate task assignment email: {str(e)}")
            raise EmailGenerationError(f"Task assignment email generation failed: {str(e)}")
    
    def generate_pmo_approval_email(
        self,
        approval_data: PMOApprovalData,
        sender_name: Optional[str] = None,
        sender_title: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> RenderedEmail:
        """
        Generate a PMO approval request email with proper formatting
        
        Args:
            approval_data: PMO approval request data
            sender_name: Name of the person requesting approval
            sender_title: Title of the person requesting approval
            correlation_id: Correlation ID for tracking
            
        Returns:
            RenderedEmail ready for delivery
            
        Raises:
            EmailGenerationError: If generation fails
        """
        try:
            # Create context
            context = PMOApprovalContext(
                # Base context
                recipient_name=approval_data.pmo_contact_name,
                recipient_email=approval_data.pmo_contact_email,
                sender_name=sender_name or self.default_sender_name,
                sender_title=sender_title or self.default_sender_title,
                organization=self.default_organization,
                date=datetime.now(),
                correlation_id=correlation_id or str(uuid.uuid4()),
                additional_data={},
                
                # PMO-specific context
                request_id=approval_data.request_id,
                request_type=approval_data.request_type,
                request_summary=approval_data.request_summary,
                justification=approval_data.justification,
                estimated_cost=approval_data.estimated_cost,
                estimated_timeline=approval_data.estimated_timeline,
                risk_assessment=approval_data.risk_assessment,
                approval_deadline=approval_data.approval_deadline,
                supporting_documents=approval_data.supporting_documents
            )
            
            # Render email
            rendered_email = self.template_engine.render_pmo_approval_email(context)
            
            # Validate compliance
            self.template_engine.validate_government_compliance(rendered_email)
            
            logger.info(f"Generated PMO approval email for request {approval_data.request_id}")
            return rendered_email
            
        except Exception as e:
            logger.error(f"Failed to generate PMO approval email: {str(e)}")
            raise EmailGenerationError(f"PMO approval email generation failed: {str(e)}")
    
    def generate_executive_summary_email(
        self,
        summary_data: ExecutiveSummaryData,
        sender_name: Optional[str] = None,
        sender_title: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority_level: str = "HIGH"
    ) -> RenderedEmail:
        """
        Generate an executive summary email with professional formatting and priority handling
        
        Args:
            summary_data: Executive summary data
            sender_name: Name of the person sending the summary
            sender_title: Title of the person sending the summary
            correlation_id: Correlation ID for tracking
            priority_level: Priority level for executive communications (HIGH, CRITICAL, URGENT)
            
        Returns:
            RenderedEmail ready for delivery with executive-level formatting
            
        Raises:
            EmailGenerationError: If generation fails
        """
        try:
            # Validate executive summary data
            self._validate_executive_summary_data(summary_data)
            
            # Create context with executive-specific enhancements
            context = ExecutiveSummaryContext(
                # Base context
                recipient_name=summary_data.executive_name,
                recipient_email=summary_data.executive_email,
                sender_name=sender_name or self.default_sender_name,
                sender_title=sender_title or self.default_sender_title,
                organization=self.default_organization,
                date=datetime.now(),
                correlation_id=correlation_id or str(uuid.uuid4()),
                additional_data={
                    "priority_level": priority_level,
                    "executive_communication": True,
                    "requires_acknowledgment": True,
                    "attachment_count": len(summary_data.attachments) if summary_data.attachments else 0
                },
                
                # Executive summary context
                report_title=summary_data.report_title,
                reporting_period=summary_data.reporting_period,
                key_metrics=summary_data.key_metrics or {},
                achievements=summary_data.achievements or [],
                challenges=summary_data.challenges or [],
                recommendations=summary_data.recommendations or [],
                attachments=summary_data.attachments or [],
                next_steps=summary_data.next_steps or []
            )
            
            # Use the dedicated executive summary template
            rendered_email = self.template_engine.render_executive_summary_email(context)
            
            # Apply executive-level priority formatting
            rendered_email = self._apply_executive_priority_formatting(rendered_email, priority_level)
            
            # Add executive-specific metadata
            rendered_email.metadata.update({
                "attachment_count": len(summary_data.attachments) if summary_data.attachments else 0,
                "executive_communication": True,
                "requires_acknowledgment": True
            })
            
            # Validate compliance for executive communications
            self.template_engine.validate_government_compliance(rendered_email)
            
            # Additional validation for executive communications
            self._validate_executive_compliance(rendered_email, summary_data)
            
            logger.info(f"Generated executive summary email: {summary_data.report_title} (Priority: {priority_level})")
            return rendered_email
            
        except Exception as e:
            logger.error(f"Failed to generate executive summary email: {str(e)}")
            raise EmailGenerationError(f"Executive summary email generation failed: {str(e)}")
    
    def _validate_executive_summary_data(self, summary_data: ExecutiveSummaryData) -> None:
        """Validate executive summary data for completeness and quality"""
        if not summary_data.report_title or len(summary_data.report_title.strip()) < 5:
            raise EmailGenerationError("Executive summary requires a meaningful report title")
        
        if not summary_data.reporting_period:
            raise EmailGenerationError("Executive summary requires a reporting period")
        
        if not summary_data.executive_name:
            raise EmailGenerationError("Executive summary requires recipient executive name")
        
        if not summary_data.executive_email:
            raise EmailGenerationError("Executive summary requires recipient executive email")
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, summary_data.executive_email):
            raise EmailGenerationError("Invalid executive email format")
        
        # Ensure at least some content is provided
        has_content = any([
            summary_data.key_metrics,
            summary_data.achievements,
            summary_data.challenges,
            summary_data.recommendations,
            summary_data.next_steps
        ])
        
        if not has_content:
            raise EmailGenerationError("Executive summary requires at least one content section (metrics, achievements, challenges, recommendations, or next steps)")
    
    def _apply_executive_priority_formatting(self, rendered_email: RenderedEmail, priority_level: str) -> RenderedEmail:
        """Apply executive-level priority formatting to the email"""
        priority_prefixes = {
            "CRITICAL": "🔴 CRITICAL",
            "URGENT": "🟠 URGENT",
            "HIGH": "🔵 HIGH PRIORITY",
            "MEDIUM": "🟡 MEDIUM PRIORITY",
            "LOW": "⚪ LOW PRIORITY"
        }
        
        priority_prefix = priority_prefixes.get(priority_level.upper(), "🔵 HIGH PRIORITY")
        
        # Update subject with priority indicator
        original_subject = rendered_email.subject
        rendered_email.subject = f"{priority_prefix}: {original_subject}"
        
        # Add priority metadata (preserve existing metadata)
        priority_metadata = {
            "priority_level": priority_level.upper(),
            "executive_communication": True,
            "requires_acknowledgment": True,
            "delivery_priority": "high" if priority_level.upper() in ["CRITICAL", "URGENT", "HIGH"] else "normal"
        }
        rendered_email.metadata.update(priority_metadata)
        
        return rendered_email
    
    def _validate_executive_compliance(self, rendered_email: RenderedEmail, summary_data: ExecutiveSummaryData) -> None:
        """Additional compliance validation for executive communications"""
        # Ensure executive emails have proper classification
        if rendered_email.compliance_level.value == "unclassified":
            logger.warning("Executive summary using unclassified level - consider upgrading to sensitive")
        
        # Validate attachment handling
        if summary_data.attachments:
            if len(summary_data.attachments) > 10:
                raise EmailGenerationError("Executive summary cannot have more than 10 attachments")
            
            # Validate attachment names
            for attachment in summary_data.attachments:
                if not attachment or len(attachment.strip()) < 3:
                    raise EmailGenerationError("All attachment names must be meaningful and descriptive")
        
        # Ensure correlation ID is present for audit trail
        if not rendered_email.correlation_id:
            raise EmailGenerationError("Executive communications must have correlation ID for audit compliance")
        
        logger.info(f"Executive compliance validation passed for {rendered_email.correlation_id}")
    
    def generate_developer_notification_email(
        self,
        notification_type: str,
        message: str,
        recipient_name: str,
        recipient_email: str,
        additional_data: Optional[Dict[str, Any]] = None,
        sender_name: Optional[str] = None,
        sender_title: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> RenderedEmail:
        """
        Generate a general developer notification email
        
        Args:
            notification_type: Type of notification
            message: Notification message
            recipient_name: Name of the recipient
            recipient_email: Email of the recipient
            additional_data: Additional data for the notification
            sender_name: Name of the sender
            sender_title: Title of the sender
            correlation_id: Correlation ID for tracking
            
        Returns:
            RenderedEmail ready for delivery
        """
        try:
            # Create a simple task assignment context for notifications
            context = TaskAssignmentContext(
                # Base context
                recipient_name=recipient_name,
                recipient_email=recipient_email,
                sender_name=sender_name or self.default_sender_name,
                sender_title=sender_title or self.default_sender_title,
                organization=self.default_organization,
                date=datetime.now(),
                correlation_id=correlation_id or str(uuid.uuid4()),
                additional_data=additional_data or {},
                
                # Notification as task context
                task_id=f"NOTIFICATION-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                task_title=f"{notification_type} Notification",
                task_description=message,
                priority_level="MEDIUM",
                due_date=datetime.now() + timedelta(days=1),
                project_name="System Notification",
                requirements=[],
                deliverables=["Acknowledgment of notification"]
            )
            
            # Render using task assignment template
            rendered_email = self.template_engine.render_task_assignment_email(context)
            
            # Validate compliance
            self.template_engine.validate_government_compliance(rendered_email)
            
            logger.info(f"Generated developer notification email: {notification_type}")
            return rendered_email
            
        except Exception as e:
            logger.error(f"Failed to generate developer notification email: {str(e)}")
            raise EmailGenerationError(f"Developer notification email generation failed: {str(e)}")
    
    def validate_email_data(self, email_type: str, data: Dict[str, Any]) -> bool:
        """
        Validate email data before generation
        
        Args:
            email_type: Type of email to validate
            data: Email data to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        if email_type == "task_assignment":
            required_fields = ["task_id", "task_title", "task_description", "assignee_name", "assignee_email"]
            for field in required_fields:
                if field not in data or not data[field]:
                    raise EmailGenerationError(f"Missing required field for task assignment: {field}")
        
        elif email_type == "pmo_approval":
            required_fields = ["request_id", "request_type", "request_summary", "pmo_contact_name", "pmo_contact_email"]
            for field in required_fields:
                if field not in data or not data[field]:
                    raise EmailGenerationError(f"Missing required field for PMO approval: {field}")
        
        elif email_type == "executive_summary":
            required_fields = ["report_title", "executive_name", "executive_email"]
            for field in required_fields:
                if field not in data or not data[field]:
                    raise EmailGenerationError(f"Missing required field for executive summary: {field}")
        
        return True
    
    def get_available_templates(self) -> List[str]:
        """Get list of available email templates"""
        templates = self.template_engine.list_templates()
        return [t.template_id for t in templates]
    
    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific template"""
        template = self.template_engine.get_template(template_id)
        if not template:
            return None
        
        return {
            "template_id": template.template_id,
            "name": template.name,
            "type": template.template_type.value,
            "compliance_level": template.compliance_level.value,
            "required_fields": template.required_fields,
            "optional_fields": template.optional_fields,
            "government_approved": template.government_approved,
            "version": template.version
        }