"""
Tests for Email Template Engine

Tests government-compliant email template management and rendering functionality.
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.email.template_engine import (
    EmailTemplateEngine,
    EmailTemplate,
    EmailTemplateType,
    GovernmentComplianceLevel,
    TemplateContext,
    TaskAssignmentContext,
    PMOApprovalContext,
    ExecutiveSummaryContext,
    RenderedEmail,
    TemplateValidationError,
    TemplateRenderingError
)


class TestEmailTemplateEngine:
    """Test cases for EmailTemplateEngine"""
    
    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def template_engine(self, temp_templates_dir):
        """Create template engine with temporary directory"""
        return EmailTemplateEngine(temp_templates_dir)
    
    @pytest.fixture
    def sample_task_context(self):
        """Sample task assignment context"""
        return TaskAssignmentContext(
            recipient_name="John Developer",
            recipient_email="john.developer@dol.gov",
            sender_name="Jane Manager",
            sender_title="Project Manager",
            organization="U.S. Department of Labor",
            date=datetime(2024, 1, 15, 10, 30),
            correlation_id="test-correlation-123",
            additional_data={},
            task_id="TASK-2024-001",
            task_title="Implement Email Validation",
            task_description="Implement comprehensive email validation for the system",
            priority_level="HIGH",
            due_date=datetime(2024, 1, 22, 17, 0),
            project_name="Email Agent System",
            requirements=["Input validation", "Error handling", "Unit tests"],
            deliverables=["Validation module", "Test suite", "Documentation"]
        )
    
    @pytest.fixture
    def sample_pmo_context(self):
        """Sample PMO approval context"""
        return PMOApprovalContext(
            recipient_name="PMO Manager",
            recipient_email="pmo.manager@dol.gov",
            sender_name="System Architect",
            sender_title="Senior Architect",
            organization="U.S. Department of Labor",
            date=datetime(2024, 1, 15, 14, 0),
            correlation_id="pmo-approval-456",
            additional_data={},
            request_id="REQ-2024-001",
            request_type="System Enhancement",
            request_summary="Request approval for new email processing features",
            justification="Required for federal compliance and improved efficiency",
            estimated_cost=50000.0,
            estimated_timeline="3 months",
            risk_assessment="Low risk with proper testing",
            approval_deadline=datetime(2024, 1, 20, 17, 0),
            supporting_documents=["Technical specification", "Cost analysis", "Risk assessment"]
        )
    
    def test_initialization(self, temp_templates_dir):
        """Test template engine initialization"""
        engine = EmailTemplateEngine(temp_templates_dir)
        
        assert engine.templates_directory == temp_templates_dir
        assert isinstance(engine.templates, dict)
        assert len(engine.templates) >= 2  # Should have default templates
        
        # Check that default templates were created
        assert os.path.exists(os.path.join(temp_templates_dir, "templates.json"))
        assert os.path.exists(os.path.join(temp_templates_dir, "task_assignment"))
        assert os.path.exists(os.path.join(temp_templates_dir, "pmo_approval"))
    
    def test_default_templates_creation(self, template_engine):
        """Test that default templates are created correctly"""
        templates = template_engine.list_templates()
        
        # Should have at least task assignment and PMO approval templates
        template_types = [t.template_type for t in templates]
        assert EmailTemplateType.TASK_ASSIGNMENT in template_types
        assert EmailTemplateType.PMO_APPROVAL_REQUEST in template_types
        
        # Check template properties
        task_template = next(t for t in templates if t.template_type == EmailTemplateType.TASK_ASSIGNMENT)
        assert task_template.government_approved
        assert task_template.compliance_level == GovernmentComplianceLevel.UNCLASSIFIED
        assert "task_id" in task_template.required_fields
        assert "task_title" in task_template.required_fields
    
    def test_get_template(self, template_engine):
        """Test getting template by ID"""
        template = template_engine.get_template("task_assignment_v1")
        
        assert template is not None
        assert template.template_id == "task_assignment_v1"
        assert template.template_type == EmailTemplateType.TASK_ASSIGNMENT
        
        # Test non-existent template
        assert template_engine.get_template("non_existent") is None
    
    def test_list_templates(self, template_engine):
        """Test listing templates"""
        all_templates = template_engine.list_templates()
        assert len(all_templates) >= 2
        
        # Test filtering by type
        task_templates = template_engine.list_templates(EmailTemplateType.TASK_ASSIGNMENT)
        assert len(task_templates) >= 1
        assert all(t.template_type == EmailTemplateType.TASK_ASSIGNMENT for t in task_templates)
    
    def test_validate_template_context(self, template_engine):
        """Test template context validation"""
        template = template_engine.get_template("task_assignment_v1")
        
        # Valid context
        valid_context = {
            "task_id": "TASK-001",
            "task_title": "Test Task",
            "task_description": "Test description",
            "priority_level": "HIGH",
            "due_date": datetime.now(),
            "project_name": "Test Project"
        }
        
        assert template_engine.validate_template_context(template, valid_context)
        
        # Invalid context (missing required field)
        invalid_context = {
            "task_id": "TASK-001",
            "task_title": "Test Task"
            # Missing other required fields
        }
        
        with pytest.raises(TemplateValidationError):
            template_engine.validate_template_context(template, invalid_context)
    
    def test_render_task_assignment_email(self, template_engine, sample_task_context):
        """Test rendering task assignment email"""
        rendered_email = template_engine.render_task_assignment_email(sample_task_context)
        
        assert isinstance(rendered_email, RenderedEmail)
        assert rendered_email.template_id == "task_assignment_v1"
        assert "TASK-2024-001" in rendered_email.subject
        assert "HIGH" in rendered_email.subject
        assert "John Developer" in rendered_email.body_html
        assert "Implement Email Validation" in rendered_email.body_html
        assert "jane.manager@dol.gov" in rendered_email.sender_email
        assert rendered_email.correlation_id == "test-correlation-123"
        
        # Check that both HTML and text versions are generated
        assert rendered_email.body_html
        assert rendered_email.body_text
        assert len(rendered_email.body_text) > 0
    
    def test_render_pmo_approval_email(self, template_engine, sample_pmo_context):
        """Test rendering PMO approval email"""
        rendered_email = template_engine.render_pmo_approval_email(sample_pmo_context)
        
        assert isinstance(rendered_email, RenderedEmail)
        assert rendered_email.template_id == "pmo_approval_v1"
        assert "REQ-2024-001" in rendered_email.subject
        assert "PMO Manager" in rendered_email.body_html
        assert "System Enhancement" in rendered_email.body_html
        assert "$50,000.00" in rendered_email.body_html
        assert "system.architect@dol.gov" in rendered_email.sender_email
        assert rendered_email.correlation_id == "pmo-approval-456"
    
    def test_government_date_filter(self, template_engine):
        """Test government date formatting filter"""
        test_date = datetime(2024, 1, 15, 14, 30, 0)
        formatted = template_engine._format_government_date(test_date)
        
        assert "15 January 2024" in formatted
        assert "14:30" in formatted
    
    def test_classification_header_filter(self, template_engine):
        """Test classification header filter"""
        content = "Test Content"
        
        unclassified = template_engine._add_classification_header(
            content, GovernmentComplianceLevel.UNCLASSIFIED
        )
        assert unclassified == "[UNCLASSIFIED] Test Content"
        
        sensitive = template_engine._add_classification_header(
            content, GovernmentComplianceLevel.SENSITIVE
        )
        assert sensitive == "[SENSITIVE] Test Content"
    
    def test_content_sanitization_filter(self, template_engine):
        """Test content sanitization filter"""
        content = "Contact john.doe@example.com or call 555-123-4567 or use SSN 123-45-6789"
        sanitized = template_engine._sanitize_content(content)
        
        assert "[EMAIL_REDACTED]" in sanitized
        assert "[PHONE_REDACTED]" in sanitized
        assert "[SSN_REDACTED]" in sanitized
        assert "john.doe@example.com" not in sanitized
        assert "555-123-4567" not in sanitized
        assert "123-45-6789" not in sanitized
        
        # Government emails should not be redacted
        gov_content = "Contact official@dol.gov for more information"
        gov_sanitized = template_engine._sanitize_content(gov_content)
        assert "official@dol.gov" in gov_sanitized
    
    def test_government_compliance_validation(self, template_engine, sample_task_context):
        """Test government compliance validation"""
        rendered_email = template_engine.render_task_assignment_email(sample_task_context)
        
        # Should pass validation
        assert template_engine.validate_government_compliance(rendered_email)
        
        # Test missing correlation ID
        rendered_email.correlation_id = ""
        with pytest.raises(TemplateValidationError, match="Missing correlation ID"):
            template_engine.validate_government_compliance(rendered_email)
        
        # Test non-government sender
        rendered_email.correlation_id = "test-123"
        rendered_email.sender_email = "test@example.com"
        with pytest.raises(TemplateValidationError, match="government email domain"):
            template_engine.validate_government_compliance(rendered_email)
    
    def test_template_rendering_error_handling(self, template_engine):
        """Test error handling during template rendering"""
        # Test with invalid template ID
        with pytest.raises(TemplateValidationError, match="Template not found"):
            template_engine.render_email("invalid_template", TemplateContext(
                recipient_name="Test",
                recipient_email="test@dol.gov",
                sender_name="Sender",
                sender_title="Title",
                organization="DOL",
                date=datetime.now(),
                correlation_id="test-123",
                additional_data={}
            ))
    
    def test_template_metadata(self, template_engine, sample_task_context):
        """Test that rendered emails include proper metadata"""
        rendered_email = template_engine.render_task_assignment_email(sample_task_context)
        
        assert "template_version" in rendered_email.metadata
        assert "render_timestamp" in rendered_email.metadata
        assert "government_approved" in rendered_email.metadata
        assert rendered_email.metadata["government_approved"] is True
    
    def test_html_and_text_rendering(self, template_engine, sample_task_context):
        """Test that both HTML and text versions are properly rendered"""
        rendered_email = template_engine.render_task_assignment_email(sample_task_context)
        
        # HTML version should contain HTML tags
        assert "<html>" in rendered_email.body_html
        assert "<body" in rendered_email.body_html
        assert "U.S. Department of Labor" in rendered_email.body_html
        
        # Text version should not contain HTML tags
        assert "<html>" not in rendered_email.body_text
        assert "<body" not in rendered_email.body_text
        assert "U.S. Department of Labor" in rendered_email.body_text
        
        # Both should contain the core content
        assert "TASK-2024-001" in rendered_email.body_html
        assert "TASK-2024-001" in rendered_email.body_text
    
    def test_template_security_features(self, template_engine, sample_task_context):
        """Test security features in templates"""
        # Test with potentially malicious content
        sample_task_context.task_description = "<script>alert('xss')</script>Malicious content"
        
        rendered_email = template_engine.render_task_assignment_email(sample_task_context)
        
        # HTML should be escaped in the rendered content
        assert "<script>" not in rendered_email.body_html
        assert "alert('xss')" not in rendered_email.body_html
        
        # Content should still be present but sanitized
        assert "Malicious content" in rendered_email.body_html


class TestTemplateContextClasses:
    """Test template context data classes"""
    
    def test_template_context_creation(self):
        """Test basic template context creation"""
        context = TemplateContext(
            recipient_name="John Doe",
            recipient_email="john.doe@dol.gov",
            sender_name="Jane Smith",
            sender_title="Manager",
            organization="DOL",
            date=datetime.now(),
            correlation_id="test-123",
            additional_data={"key": "value"}
        )
        
        assert context.recipient_name == "John Doe"
        assert context.additional_data["key"] == "value"
    
    def test_task_assignment_context_creation(self):
        """Test task assignment context creation"""
        context = TaskAssignmentContext(
            recipient_name="Developer",
            recipient_email="dev@dol.gov",
            sender_name="Manager",
            sender_title="PM",
            organization="DOL",
            date=datetime.now(),
            correlation_id="task-123",
            additional_data={},
            task_id="TASK-001",
            task_title="Test Task",
            task_description="Description",
            priority_level="HIGH",
            due_date=datetime.now() + timedelta(days=7),
            project_name="Test Project",
            requirements=["Req1", "Req2"],
            deliverables=["Del1", "Del2"]
        )
        
        assert context.task_id == "TASK-001"
        assert len(context.requirements) == 2
        assert len(context.deliverables) == 2
    
    def test_pmo_approval_context_creation(self):
        """Test PMO approval context creation"""
        context = PMOApprovalContext(
            recipient_name="PMO",
            recipient_email="pmo@dol.gov",
            sender_name="Requester",
            sender_title="Architect",
            organization="DOL",
            date=datetime.now(),
            correlation_id="approval-123",
            additional_data={},
            request_id="REQ-001",
            request_type="Enhancement",
            request_summary="Summary",
            justification="Justification",
            estimated_cost=10000.0,
            estimated_timeline="2 months",
            risk_assessment="Low",
            approval_deadline=datetime.now() + timedelta(days=5),
            supporting_documents=["doc1.pdf", "doc2.pdf"]
        )
        
        assert context.request_id == "REQ-001"
        assert context.estimated_cost == 10000.0
        assert len(context.supporting_documents) == 2


if __name__ == "__main__":
    pytest.main([__file__])