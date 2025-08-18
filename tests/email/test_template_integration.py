"""
Integration Tests for Template-Based Email Generation System

Tests the complete template system integration with government compliance requirements.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta

from src.email.email_generator import (
    EmailGenerator,
    TaskAssignmentData,
    PMOApprovalData,
    EmailGenerationError
)
from src.email.template_engine import (
    EmailTemplateEngine,
    GovernmentComplianceLevel,
    TemplateValidationError
)


class TestTemplateSystemIntegration:
    """Integration tests for the complete template system"""
    
    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def email_generator(self, temp_templates_dir):
        """Create email generator with temporary directory"""
        return EmailGenerator(temp_templates_dir)
    
    def test_complete_task_assignment_workflow(self, email_generator):
        """Test complete task assignment email generation workflow"""
        # Create task assignment data
        task_data = TaskAssignmentData(
            task_id="INTEGRATION-TASK-001",
            task_title="Implement Federal Compliance Module",
            task_description="Develop comprehensive federal compliance validation module with FISMA requirements",
            priority_level="CRITICAL",
            due_date=datetime.now() + timedelta(days=10),
            project_name="Federal Compliance Initiative",
            requirements=[
                "FISMA compliance validation",
                "NIST framework implementation",
                "Audit trail generation",
                "Security control testing"
            ],
            deliverables=[
                "Compliance validation module",
                "NIST framework adapter",
                "Audit logging system",
                "Security test suite",
                "Compliance documentation"
            ],
            assignee_name="Senior Developer Johnson",
            assignee_email="senior.developer.johnson@dol.gov"
        )
        
        # Generate email
        rendered_email = email_generator.generate_task_assignment_email(
            task_data,
            sender_name="Chief Technology Officer",
            sender_title="CTO",
            correlation_id="INTEGRATION-TEST-001"
        )
        
        # Verify email structure
        assert rendered_email.template_id == "task_assignment_v1"
        assert "INTEGRATION-TASK-001" in rendered_email.subject
        assert "CRITICAL" in rendered_email.subject
        assert rendered_email.recipient_email == "senior.developer.johnson@dol.gov"
        assert rendered_email.correlation_id == "INTEGRATION-TEST-001"
        
        # Verify government compliance
        assert rendered_email.sender_email.endswith('.gov')
        assert rendered_email.compliance_level == GovernmentComplianceLevel.UNCLASSIFIED
        assert "U.S. Department of Labor" in rendered_email.body_html
        assert "U.S. Department of Labor" in rendered_email.body_text
        
        # Verify content includes all requirements and deliverables
        for requirement in task_data.requirements:
            assert requirement in rendered_email.body_html
            assert requirement in rendered_email.body_text
        
        for deliverable in task_data.deliverables:
            assert deliverable in rendered_email.body_html
            assert deliverable in rendered_email.body_text
        
        # Verify metadata
        assert rendered_email.metadata["government_approved"] is True
        assert "render_timestamp" in rendered_email.metadata
        assert "template_version" in rendered_email.metadata
    
    def test_complete_pmo_approval_workflow(self, email_generator):
        """Test complete PMO approval email generation workflow"""
        # Create PMO approval data
        pmo_data = PMOApprovalData(
            request_id="INTEGRATION-REQ-001",
            request_type="Critical Infrastructure Upgrade",
            request_summary="Request approval for upgrading email processing infrastructure to meet new federal cybersecurity requirements",
            justification="New federal mandates require enhanced security measures and improved audit capabilities",
            estimated_cost=250000.0,
            estimated_timeline="8 months",
            risk_assessment="Medium-High risk due to system complexity, but essential for federal compliance",
            approval_deadline=datetime.now() + timedelta(days=5),
            supporting_documents=[
                "Federal Cybersecurity Requirements Analysis.pdf",
                "Infrastructure Upgrade Technical Specification.pdf",
                "Cost-Benefit Analysis Report.pdf",
                "Risk Assessment and Mitigation Plan.pdf",
                "Compliance Gap Analysis.pdf"
            ],
            pmo_contact_name="Director of Program Management",
            pmo_contact_email="director.pmo@dol.gov"
        )
        
        # Generate email
        rendered_email = email_generator.generate_pmo_approval_email(
            pmo_data,
            sender_name="Chief Information Security Officer",
            sender_title="CISO",
            correlation_id="INTEGRATION-PMO-001"
        )
        
        # Verify email structure
        assert rendered_email.template_id == "pmo_approval_v1"
        assert "INTEGRATION-REQ-001" in rendered_email.subject
        assert "Critical Infrastructure Upgrade" in rendered_email.subject
        assert rendered_email.recipient_email == "director.pmo@dol.gov"
        assert rendered_email.correlation_id == "INTEGRATION-PMO-001"
        
        # Verify government compliance
        assert rendered_email.sender_email.endswith('.gov')
        assert rendered_email.compliance_level == GovernmentComplianceLevel.SENSITIVE
        assert "U.S. Department of Labor" in rendered_email.body_html
        assert "U.S. Department of Labor" in rendered_email.body_text
        
        # Verify cost formatting
        assert "$250,000.00" in rendered_email.body_html
        
        # Verify supporting documents are listed
        for document in pmo_data.supporting_documents:
            assert document in rendered_email.body_html
            assert document in rendered_email.body_text
        
        # Verify approval urgency indicators
        assert "APPROVAL REQUIRED" in rendered_email.body_html
        assert "APPROVAL REQUIRED" in rendered_email.body_text
    
    def test_government_compliance_validation_integration(self, email_generator):
        """Test government compliance validation across the system"""
        task_data = TaskAssignmentData(
            task_id="COMPLIANCE-TEST-001",
            task_title="Security Compliance Validation",
            task_description="Test government compliance features",
            priority_level="HIGH",
            due_date=datetime.now() + timedelta(days=7),
            project_name="Compliance Testing",
            requirements=["Government compliance"],
            deliverables=["Compliance report"],
            assignee_name="Compliance Officer",
            assignee_email="compliance.officer@dol.gov"
        )
        
        rendered_email = email_generator.generate_task_assignment_email(task_data)
        
        # Test compliance validation
        template_engine = email_generator.template_engine
        assert template_engine.validate_government_compliance(rendered_email)
        
        # Test that non-compliant emails are rejected
        rendered_email.correlation_id = ""
        with pytest.raises(TemplateValidationError, match="Missing correlation ID"):
            template_engine.validate_government_compliance(rendered_email)
        
        # Test non-government email domain
        rendered_email.correlation_id = "test-123"
        rendered_email.sender_email = "test@example.com"
        with pytest.raises(TemplateValidationError, match="government email domain"):
            template_engine.validate_government_compliance(rendered_email)
    
    def test_content_sanitization_integration(self, email_generator):
        """Test content sanitization across the system"""
        task_data = TaskAssignmentData(
            task_id="SANITIZATION-TEST-001",
            task_title="Content Sanitization Test",
            task_description="Test with PII: contact john.doe@example.com or call 555-123-4567 or SSN 123-45-6789",
            priority_level="MEDIUM",
            due_date=datetime.now() + timedelta(days=5),
            project_name="Security Testing",
            requirements=["Contact admin@dol.gov for government info"],
            deliverables=["Sanitized output"],
            assignee_name="Security Tester",
            assignee_email="security.tester@dol.gov"
        )
        
        rendered_email = email_generator.generate_task_assignment_email(task_data)
        
        # Verify PII is redacted
        assert "[EMAIL_REDACTED]" in rendered_email.body_html
        assert "[PHONE_REDACTED]" in rendered_email.body_html
        assert "[SSN_REDACTED]" in rendered_email.body_html
        
        # Verify government emails are preserved
        assert "admin@dol.gov" in rendered_email.body_html
        
        # Verify original PII is not present
        assert "john.doe@example.com" not in rendered_email.body_html
        assert "555-123-4567" not in rendered_email.body_html
        assert "123-45-6789" not in rendered_email.body_html
    
    def test_template_versioning_and_metadata(self, email_generator):
        """Test template versioning and metadata handling"""
        task_data = TaskAssignmentData(
            task_id="VERSION-TEST-001",
            task_title="Template Versioning Test",
            task_description="Test template versioning",
            priority_level="LOW",
            due_date=datetime.now() + timedelta(days=3),
            project_name="Template Testing",
            requirements=["Version tracking"],
            deliverables=["Version report"],
            assignee_name="Template Tester",
            assignee_email="template.tester@dol.gov"
        )
        
        rendered_email = email_generator.generate_task_assignment_email(task_data)
        
        # Verify metadata
        assert "template_version" in rendered_email.metadata
        assert "render_timestamp" in rendered_email.metadata
        assert "government_approved" in rendered_email.metadata
        assert rendered_email.metadata["government_approved"] is True
        
        # Verify template version is tracked
        template_info = email_generator.get_template_info("task_assignment_v1")
        assert template_info["version"] == "1.0"
        assert template_info["government_approved"] is True
    
    def test_error_handling_integration(self, email_generator):
        """Test error handling across the system"""
        # Test with missing required data
        incomplete_task_data = TaskAssignmentData(
            task_id="",  # Empty task ID
            task_title="",  # Empty title
            task_description="Test description",
            priority_level="HIGH",
            due_date=datetime.now(),
            project_name="Test Project",
            requirements=[],
            deliverables=[],
            assignee_name="Test User",
            assignee_email="test@dol.gov"
        )
        
        # Should still work but with empty fields
        rendered_email = email_generator.generate_task_assignment_email(incomplete_task_data)
        assert isinstance(rendered_email, object)
        
        # Test validation with invalid data types
        with pytest.raises(EmailGenerationError):
            email_generator.validate_email_data("task_assignment", {
                "task_id": None,
                "task_title": None
            })
    
    def test_multiple_template_types_integration(self, email_generator):
        """Test integration with multiple template types"""
        # Get available templates
        templates = email_generator.get_available_templates()
        assert "task_assignment_v1" in templates
        assert "pmo_approval_v1" in templates
        
        # Test template info for each type
        for template_id in templates:
            info = email_generator.get_template_info(template_id)
            assert info is not None
            assert "template_id" in info
            assert "name" in info
            assert "government_approved" in info
            assert info["government_approved"] is True
    
    def test_date_formatting_integration(self, email_generator):
        """Test government date formatting integration"""
        specific_date = datetime(2024, 12, 25, 14, 30, 0)
        
        task_data = TaskAssignmentData(
            task_id="DATE-TEST-001",
            task_title="Date Formatting Test",
            task_description="Test date formatting",
            priority_level="MEDIUM",
            due_date=specific_date,
            project_name="Date Testing",
            requirements=["Date formatting"],
            deliverables=["Formatted dates"],
            assignee_name="Date Tester",
            assignee_email="date.tester@dol.gov"
        )
        
        rendered_email = email_generator.generate_task_assignment_email(task_data)
        
        # Verify government date format is used
        assert "25 December 2024" in rendered_email.body_html
        assert "14:30" in rendered_email.body_html
    
    def test_classification_levels_integration(self, email_generator):
        """Test different classification levels"""
        # Task assignment should be UNCLASSIFIED
        task_data = TaskAssignmentData(
            task_id="CLASS-TEST-001",
            task_title="Classification Test",
            task_description="Test classification",
            priority_level="MEDIUM",
            due_date=datetime.now() + timedelta(days=5),
            project_name="Classification Testing",
            requirements=["Classification handling"],
            deliverables=["Classification report"],
            assignee_name="Classification Tester",
            assignee_email="classification.tester@dol.gov"
        )
        
        task_email = email_generator.generate_task_assignment_email(task_data)
        assert task_email.compliance_level == GovernmentComplianceLevel.UNCLASSIFIED
        
        # PMO approval should be SENSITIVE
        pmo_data = PMOApprovalData(
            request_id="CLASS-REQ-001",
            request_type="Classification Test",
            request_summary="Test classification levels",
            justification="Testing purposes",
            estimated_cost=1000.0,
            estimated_timeline="1 week",
            risk_assessment="Low",
            approval_deadline=datetime.now() + timedelta(days=3),
            supporting_documents=["test.pdf"],
            pmo_contact_name="PMO Tester",
            pmo_contact_email="pmo.tester@dol.gov"
        )
        
        pmo_email = email_generator.generate_pmo_approval_email(pmo_data)
        assert pmo_email.compliance_level == GovernmentComplianceLevel.SENSITIVE


if __name__ == "__main__":
    pytest.main([__file__])