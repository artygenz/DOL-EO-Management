"""
Tests for Email Generator

Tests high-level email generation functionality for automated workflow emails.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.email.email_generator import (
    EmailGenerator,
    TaskAssignmentData,
    PMOApprovalData,
    ExecutiveSummaryData,
    EmailGenerationError
)
from src.email.template_engine import RenderedEmail, GovernmentComplianceLevel


class TestEmailGenerator:
    """Test cases for EmailGenerator"""
    
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
    
    @pytest.fixture
    def sample_task_data(self):
        """Sample task assignment data"""
        return TaskAssignmentData(
            task_id="TASK-2024-001",
            task_title="Implement User Authentication",
            task_description="Implement secure user authentication system with multi-factor support",
            priority_level="HIGH",
            due_date=datetime(2024, 2, 1, 17, 0),
            project_name="Security Enhancement Project",
            requirements=[
                "Multi-factor authentication support",
                "Password complexity validation",
                "Session management",
                "Audit logging"
            ],
            deliverables=[
                "Authentication module",
                "Unit test suite",
                "Integration tests",
                "Security documentation"
            ],
            assignee_name="John Developer",
            assignee_email="john.developer@dol.gov"
        )
    
    @pytest.fixture
    def sample_pmo_data(self):
        """Sample PMO approval data"""
        return PMOApprovalData(
            request_id="REQ-2024-005",
            request_type="Infrastructure Upgrade",
            request_summary="Request approval for upgrading email processing infrastructure to handle increased load",
            justification="Current system is approaching capacity limits and requires scaling to meet federal requirements",
            estimated_cost=75000.0,
            estimated_timeline="4 months",
            risk_assessment="Medium risk - requires careful migration planning and testing",
            approval_deadline=datetime(2024, 1, 25, 17, 0),
            supporting_documents=[
                "Infrastructure Assessment Report",
                "Cost-Benefit Analysis",
                "Migration Plan",
                "Risk Mitigation Strategy"
            ],
            pmo_contact_name="Sarah PMO Manager",
            pmo_contact_email="sarah.pmo@dol.gov"
        )
    
    @pytest.fixture
    def sample_executive_data(self):
        """Sample executive summary data"""
        return ExecutiveSummaryData(
            report_title="Q1 2024 Email System Performance Report",
            reporting_period="January - March 2024",
            key_metrics={
                "emails_processed": 125000,
                "average_processing_time": "2.3 seconds",
                "system_uptime": "99.8%",
                "security_incidents": 0,
                "compliance_score": "100%"
            },
            achievements=[
                "Processed 125,000 emails with 99.8% uptime",
                "Zero security incidents reported",
                "Achieved 100% compliance with federal standards",
                "Reduced average processing time by 15%"
            ],
            challenges=[
                "Increased email volume during peak periods",
                "Need for additional server capacity",
                "Staff training on new security protocols"
            ],
            recommendations=[
                "Implement horizontal scaling for peak load handling",
                "Invest in additional server infrastructure",
                "Conduct quarterly security training sessions"
            ],
            attachments=[
                "Q1_Performance_Metrics.pdf",
                "Security_Audit_Report.pdf",
                "Compliance_Certificate.pdf"
            ],
            next_steps=[
                "Prepare Q2 capacity planning",
                "Schedule infrastructure upgrades",
                "Implement monitoring improvements"
            ],
            executive_name="Director Johnson",
            executive_email="director.johnson@dol.gov"
        )
    
    def test_initialization(self, temp_templates_dir):
        """Test email generator initialization"""
        generator = EmailGenerator(temp_templates_dir)
        
        assert generator.template_engine is not None
        assert generator.default_sender_name == "DOL Email Agent"
        assert generator.default_sender_title == "Automated System"
        assert generator.default_organization == "U.S. Department of Labor"
    
    def test_generate_task_assignment_email(self, email_generator, sample_task_data):
        """Test generating task assignment email"""
        rendered_email = email_generator.generate_task_assignment_email(
            sample_task_data,
            sender_name="Project Manager Smith",
            sender_title="Senior Project Manager",
            correlation_id="task-assignment-123"
        )
        
        assert isinstance(rendered_email, RenderedEmail)
        assert "TASK-2024-001" in rendered_email.subject
        assert "HIGH" in rendered_email.subject
        assert "John Developer" in rendered_email.body_html
        assert "Implement User Authentication" in rendered_email.body_html
        assert "Multi-factor authentication support" in rendered_email.body_html
        assert "Authentication module" in rendered_email.body_html
        assert rendered_email.recipient_email == "john.developer@dol.gov"
        assert rendered_email.correlation_id == "task-assignment-123"
        assert "project.manager.smith@dol.gov" in rendered_email.sender_email
    
    def test_generate_task_assignment_email_with_defaults(self, email_generator, sample_task_data):
        """Test generating task assignment email with default sender"""
        rendered_email = email_generator.generate_task_assignment_email(sample_task_data)
        
        assert isinstance(rendered_email, RenderedEmail)
        assert "DOL Email Agent" in rendered_email.body_html
        assert "Automated System" in rendered_email.body_html
        assert rendered_email.correlation_id  # Should generate UUID
        assert "dol.email.agent@dol.gov" in rendered_email.sender_email
    
    def test_generate_pmo_approval_email(self, email_generator, sample_pmo_data):
        """Test generating PMO approval email"""
        rendered_email = email_generator.generate_pmo_approval_email(
            sample_pmo_data,
            sender_name="System Architect",
            sender_title="Senior Architect",
            correlation_id="pmo-approval-456"
        )
        
        assert isinstance(rendered_email, RenderedEmail)
        assert "REQ-2024-005" in rendered_email.subject
        assert "Infrastructure Upgrade" in rendered_email.subject
        assert "Sarah PMO Manager" in rendered_email.body_html
        assert "Infrastructure Upgrade" in rendered_email.body_html
        assert "$75,000.00" in rendered_email.body_html
        assert "4 months" in rendered_email.body_html
        assert "Infrastructure Assessment Report" in rendered_email.body_html
        assert rendered_email.recipient_email == "sarah.pmo@dol.gov"
        assert rendered_email.correlation_id == "pmo-approval-456"
        assert rendered_email.compliance_level == GovernmentComplianceLevel.SENSITIVE
    
    def test_generate_developer_notification_email(self, email_generator):
        """Test generating developer notification email"""
        rendered_email = email_generator.generate_developer_notification_email(
            notification_type="System Maintenance",
            message="Scheduled maintenance will occur this weekend. Please plan accordingly.",
            recipient_name="Jane Developer",
            recipient_email="jane.developer@dol.gov",
            additional_data={"maintenance_window": "Saturday 2-6 AM"},
            correlation_id="notification-789"
        )
        
        assert isinstance(rendered_email, RenderedEmail)
        assert "System Maintenance" in rendered_email.subject
        assert "Jane Developer" in rendered_email.body_html
        assert "Scheduled maintenance will occur" in rendered_email.body_html
        assert rendered_email.recipient_email == "jane.developer@dol.gov"
        assert rendered_email.correlation_id == "notification-789"
    
    def test_validate_email_data_task_assignment(self, email_generator):
        """Test email data validation for task assignment"""
        # Valid data
        valid_data = {
            "task_id": "TASK-001",
            "task_title": "Test Task",
            "task_description": "Description",
            "assignee_name": "John Doe",
            "assignee_email": "john@dol.gov"
        }
        
        assert email_generator.validate_email_data("task_assignment", valid_data)
        
        # Invalid data - missing required field
        invalid_data = {
            "task_id": "TASK-001",
            "task_title": "Test Task"
            # Missing other required fields
        }
        
        with pytest.raises(EmailGenerationError, match="Missing required field"):
            email_generator.validate_email_data("task_assignment", invalid_data)
    
    def test_validate_email_data_pmo_approval(self, email_generator):
        """Test email data validation for PMO approval"""
        # Valid data
        valid_data = {
            "request_id": "REQ-001",
            "request_type": "Enhancement",
            "request_summary": "Summary",
            "pmo_contact_name": "PMO Manager",
            "pmo_contact_email": "pmo@dol.gov"
        }
        
        assert email_generator.validate_email_data("pmo_approval", valid_data)
        
        # Invalid data - missing required field
        invalid_data = {
            "request_id": "REQ-001"
            # Missing other required fields
        }
        
        with pytest.raises(EmailGenerationError, match="Missing required field"):
            email_generator.validate_email_data("pmo_approval", invalid_data)
    
    def test_validate_email_data_executive_summary(self, email_generator):
        """Test email data validation for executive summary"""
        # Valid data
        valid_data = {
            "report_title": "Q1 Report",
            "executive_name": "Director",
            "executive_email": "director@dol.gov"
        }
        
        assert email_generator.validate_email_data("executive_summary", valid_data)
        
        # Invalid data - missing required field
        invalid_data = {
            "report_title": "Q1 Report"
            # Missing other required fields
        }
        
        with pytest.raises(EmailGenerationError, match="Missing required field"):
            email_generator.validate_email_data("executive_summary", invalid_data)
    
    def test_get_available_templates(self, email_generator):
        """Test getting available templates"""
        templates = email_generator.get_available_templates()
        
        assert isinstance(templates, list)
        assert len(templates) >= 2
        assert "task_assignment_v1" in templates
        assert "pmo_approval_v1" in templates
    
    def test_get_template_info(self, email_generator):
        """Test getting template information"""
        info = email_generator.get_template_info("task_assignment_v1")
        
        assert info is not None
        assert info["template_id"] == "task_assignment_v1"
        assert info["type"] == "task_assignment"
        assert info["government_approved"] is True
        assert "required_fields" in info
        assert "optional_fields" in info
        
        # Test non-existent template
        assert email_generator.get_template_info("non_existent") is None
    
    def test_error_handling_invalid_task_data(self, email_generator):
        """Test error handling with invalid task data"""
        invalid_task_data = TaskAssignmentData(
            task_id="",  # Empty task ID
            task_title="Test Task",
            task_description="Description",
            priority_level="HIGH",
            due_date=datetime.now(),
            project_name="Project",
            requirements=[],
            deliverables=[],
            assignee_name="John Doe",
            assignee_email="john@dol.gov"
        )
        
        # This should still work as the template engine will handle validation
        # But if we add validation to the generator, it would catch this
        rendered_email = email_generator.generate_task_assignment_email(invalid_task_data)
        assert isinstance(rendered_email, RenderedEmail)
    
    @patch('src.email.email_generator.EmailTemplateEngine')
    def test_error_handling_template_engine_failure(self, mock_template_engine, temp_templates_dir):
        """Test error handling when template engine fails"""
        # Mock template engine to raise exception
        mock_engine_instance = MagicMock()
        mock_engine_instance.render_task_assignment_email.side_effect = Exception("Template error")
        mock_template_engine.return_value = mock_engine_instance
        
        generator = EmailGenerator(temp_templates_dir)
        
        task_data = TaskAssignmentData(
            task_id="TASK-001",
            task_title="Test",
            task_description="Description",
            priority_level="HIGH",
            due_date=datetime.now(),
            project_name="Project",
            requirements=[],
            deliverables=[],
            assignee_name="John",
            assignee_email="john@dol.gov"
        )
        
        with pytest.raises(EmailGenerationError, match="Template error"):
            generator.generate_task_assignment_email(task_data)
    
    def test_correlation_id_generation(self, email_generator, sample_task_data):
        """Test automatic correlation ID generation"""
        rendered_email = email_generator.generate_task_assignment_email(sample_task_data)
        
        # Should generate a UUID if not provided
        assert rendered_email.correlation_id
        assert len(rendered_email.correlation_id) > 10  # UUID should be longer
        
        # Should use provided correlation ID
        custom_id = "custom-correlation-123"
        rendered_email_custom = email_generator.generate_task_assignment_email(
            sample_task_data, 
            correlation_id=custom_id
        )
        assert rendered_email_custom.correlation_id == custom_id
    
    def test_government_compliance_validation(self, email_generator, sample_task_data):
        """Test that generated emails pass government compliance validation"""
        rendered_email = email_generator.generate_task_assignment_email(sample_task_data)
        
        # Should pass compliance validation (tested in template engine)
        assert rendered_email.sender_email.endswith('.gov')
        assert rendered_email.correlation_id
        assert "U.S. Department of Labor" in rendered_email.body_html
    
    def test_priority_level_handling(self, email_generator, sample_task_data):
        """Test handling of different priority levels"""
        # Test HIGH priority
        sample_task_data.priority_level = "HIGH"
        high_email = email_generator.generate_task_assignment_email(sample_task_data)
        assert "HIGH" in high_email.subject
        
        # Test MEDIUM priority
        sample_task_data.priority_level = "MEDIUM"
        medium_email = email_generator.generate_task_assignment_email(sample_task_data)
        assert "MEDIUM" in medium_email.subject
        
        # Test LOW priority
        sample_task_data.priority_level = "LOW"
        low_email = email_generator.generate_task_assignment_email(sample_task_data)
        assert "LOW" in low_email.subject
    
    def test_cost_formatting_in_pmo_approval(self, email_generator, sample_pmo_data):
        """Test proper cost formatting in PMO approval emails"""
        # Test with cost
        rendered_email = email_generator.generate_pmo_approval_email(sample_pmo_data)
        assert "$75,000.00" in rendered_email.body_html
        
        # Test without cost
        sample_pmo_data.estimated_cost = None
        rendered_email_no_cost = email_generator.generate_pmo_approval_email(sample_pmo_data)
        assert "$" not in rendered_email_no_cost.body_html or "Estimated Cost" not in rendered_email_no_cost.body_html


class TestEmailDataClasses:
    """Test email data classes"""
    
    def test_task_assignment_data_creation(self):
        """Test TaskAssignmentData creation"""
        data = TaskAssignmentData(
            task_id="TASK-001",
            task_title="Test Task",
            task_description="Description",
            priority_level="HIGH",
            due_date=datetime.now(),
            project_name="Project",
            requirements=["Req1"],
            deliverables=["Del1"],
            assignee_name="John",
            assignee_email="john@dol.gov"
        )
        
        assert data.task_id == "TASK-001"
        assert data.priority_level == "HIGH"
        assert len(data.requirements) == 1
        assert len(data.deliverables) == 1
    
    def test_pmo_approval_data_creation(self):
        """Test PMOApprovalData creation"""
        data = PMOApprovalData(
            request_id="REQ-001",
            request_type="Enhancement",
            request_summary="Summary",
            justification="Justification",
            estimated_cost=10000.0,
            estimated_timeline="2 months",
            risk_assessment="Low",
            approval_deadline=datetime.now(),
            supporting_documents=["doc1.pdf"],
            pmo_contact_name="PMO",
            pmo_contact_email="pmo@dol.gov"
        )
        
        assert data.request_id == "REQ-001"
        assert data.estimated_cost == 10000.0
        assert len(data.supporting_documents) == 1
    
    def test_executive_summary_data_creation(self):
        """Test ExecutiveSummaryData creation"""
        data = ExecutiveSummaryData(
            report_title="Q1 Report",
            reporting_period="Q1 2024",
            key_metrics={"metric1": "value1"},
            achievements=["Achievement1"],
            challenges=["Challenge1"],
            recommendations=["Recommendation1"],
            attachments=["report.pdf"],
            next_steps=["Step1"],
            executive_name="Director",
            executive_email="director@dol.gov"
        )
        
        assert data.report_title == "Q1 Report"
        assert len(data.key_metrics) == 1
        assert len(data.achievements) == 1


if __name__ == "__main__":
    pytest.main([__file__])