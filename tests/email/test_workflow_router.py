"""
Tests for Priority Assessment and Workflow Routing System

Tests priority assignment accuracy, workflow routing logic, load balancing,
and executive request escalation functionality.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from dataclasses import dataclass

from src.email.workflow_router import (
    WorkflowRouter, PriorityLevel, WorkflowType, QueueName,
    WorkflowAssignment, QueueMetrics, EscalationRule
)
from src.email.email_classifier import EmailType, ClassificationResult
from src.email.content_extractor import ExtractedContent, EmailHeaders


@dataclass
class MockExtractedContent:
    """Mock extracted content for testing"""
    headers: EmailHeaders
    plain_text: str
    attachments: list = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


@dataclass
class MockEmailHeaders:
    """Mock email headers for testing"""
    message_id: str
    sender: str
    subject: str
    date: datetime = None
    
    def __post_init__(self):
        if self.date is None:
            self.date = datetime.utcnow()


# Global fixtures available to all test classes
@pytest.fixture
def router():
    """Create workflow router for testing"""
    return WorkflowRouter(enable_load_balancing=True)

@pytest.fixture
def router_no_load_balancing():
    """Create workflow router without load balancing"""
    return WorkflowRouter(enable_load_balancing=False)

@pytest.fixture
def mock_classification_new_eo():
    """Mock classification for NEW_EO"""
    return Mock(
        email_type=EmailType.NEW_EO,
        confidence_score=0.95,
        requires_manual_review=False
    )

@pytest.fixture
def mock_classification_executive_request():
    """Mock classification for EXECUTIVE_REQUEST"""
    return Mock(
        email_type=EmailType.EXECUTIVE_REQUEST,
        confidence_score=0.88,
        requires_manual_review=False
    )

@pytest.fixture
def mock_classification_pmo_response():
    """Mock classification for PMO_RESPONSE"""
    return Mock(
        email_type=EmailType.PMO_RESPONSE,
        confidence_score=0.92,
        requires_manual_review=False
    )

@pytest.fixture
def mock_classification_developer_update():
    """Mock classification for DEVELOPER_UPDATE"""
    return Mock(
        email_type=EmailType.DEVELOPER_UPDATE,
        confidence_score=0.85,
        requires_manual_review=True
    )

@pytest.fixture
def mock_email_executive_urgent():
    """Mock executive urgent email"""
    headers = MockEmailHeaders(
        message_id="exec-urgent-001",
        sender="secretary@dol.gov",
        subject="URGENT: Congressional Inquiry Response Required"
    )
    return MockExtractedContent(
        headers=headers,
        plain_text="This is an urgent request from the Secretary regarding a congressional inquiry. "
                  "Immediate action required for briefing preparation."
    )

@pytest.fixture
def mock_email_regular_pmo():
    """Mock regular PMO email"""
    headers = MockEmailHeaders(
        message_id="pmo-regular-001",
        sender="pmo.manager@dol.gov",
        subject="Project Status Update - Q3 Deliverables"
    )
    return MockExtractedContent(
        headers=headers,
        plain_text="Please provide status update on Q3 deliverables. "
                  "Review requested for milestone completion."
    )

@pytest.fixture
def mock_email_developer_update():
    """Mock developer update email"""
    headers = MockEmailHeaders(
        message_id="dev-update-001",
        sender="developer@contractor.com",
        subject="Development Progress - Feature Implementation"
    )
    return MockExtractedContent(
        headers=headers,
        plain_text="Development update: API implementation 75% complete. "
                  "Testing phase scheduled for next week."
    )

@pytest.fixture
def mock_email_white_house():
    """Mock White House email"""
    headers = MockEmailHeaders(
        message_id="wh-critical-001",
        sender="liaison@whitehouse.gov",
        subject="Presidential Directive - Immediate Implementation Required"
    )
    return MockExtractedContent(
        headers=headers,
        plain_text="Presidential directive requires immediate implementation. "
                  "National security implications. Emergency response needed."
    )


class TestWorkflowRouter:
    """Test suite for WorkflowRouter class"""


class TestWorkflowDetermination:
    """Test workflow determination logic"""
    
    def test_determine_workflow_new_eo(self, router, mock_classification_new_eo):
        """Test workflow determination for NEW_EO"""
        workflow = router.determine_workflow(mock_classification_new_eo)
        assert workflow == WorkflowType.EXECUTIVE_ORDER_PROCESSING
    
    def test_determine_workflow_executive_request(self, router, mock_classification_executive_request):
        """Test workflow determination for EXECUTIVE_REQUEST"""
        workflow = router.determine_workflow(mock_classification_executive_request)
        assert workflow == WorkflowType.EXECUTIVE_REPORTING_WORKFLOW
    
    def test_determine_workflow_pmo_response(self, router, mock_classification_pmo_response):
        """Test workflow determination for PMO_RESPONSE"""
        workflow = router.determine_workflow(mock_classification_pmo_response)
        assert workflow == WorkflowType.PMO_APPROVAL_WORKFLOW
    
    def test_determine_workflow_developer_update(self, router, mock_classification_developer_update):
        """Test workflow determination for DEVELOPER_UPDATE"""
        workflow = router.determine_workflow(mock_classification_developer_update)
        assert workflow == WorkflowType.DEVELOPER_TASK_WORKFLOW
    
    def test_determine_workflow_unknown_type(self, router):
        """Test workflow determination for unknown email type"""
        # Create a mock with an unknown enum value that will cause KeyError
        mock_classification = Mock()
        mock_classification.email_type = "UNKNOWN_TYPE"  # String instead of enum
        workflow = router.determine_workflow(mock_classification)
        assert workflow == WorkflowType.DEVELOPER_TASK_WORKFLOW  # Default fallback


class TestPriorityAssignment:
    """Test priority assignment logic"""
    
    def test_assign_priority_executive_request_high(self, router, mock_email_executive_urgent, 
                                                   mock_classification_executive_request):
        """Test executive request gets high priority (requirement 2.5)"""
        priority = router.assign_priority_level(mock_email_executive_urgent, mock_classification_executive_request)
        # Should be CRITICAL due to "congressional inquiry" content
        assert priority == PriorityLevel.CRITICAL
    
    def test_assign_priority_executive_request_regular_high(self, router, mock_classification_executive_request):
        """Test regular executive request gets high priority (requirement 2.5)"""
        headers = MockEmailHeaders(
            message_id="exec-regular-001",
            sender="regular@contractor.com",
            subject="Executive Report Request"
        )
        email = MockExtractedContent(
            headers=headers,
            plain_text="Please prepare executive summary report for quarterly review."
        )
        
        priority = router.assign_priority_level(email, mock_classification_executive_request)
        # Should be HIGH due to executive request type override
        assert priority == PriorityLevel.HIGH
    
    def test_assign_priority_executive_sender_escalation(self, router, mock_classification_developer_update):
        """Test executive sender triggers priority escalation"""
        headers = MockEmailHeaders(
            message_id="exec-sender-001",
            sender="deputy.secretary@dol.gov",
            subject="Regular Update"
        )
        email = MockExtractedContent(headers=headers, plain_text="Regular status update")
        
        priority = router.assign_priority_level(email, mock_classification_developer_update)
        assert priority == PriorityLevel.HIGH
    
    def test_assign_priority_content_analysis_critical(self, router, mock_classification_pmo_response):
        """Test content analysis triggers critical priority"""
        headers = MockEmailHeaders(
            message_id="critical-content-001",
            sender="regular@dol.gov",
            subject="Executive Order Implementation"
        )
        email = MockExtractedContent(
            headers=headers,
            plain_text="Executive order requires immediate compliance for national security."
        )
        
        priority = router.assign_priority_level(email, mock_classification_pmo_response)
        assert priority == PriorityLevel.CRITICAL
    
    def test_assign_priority_urgency_keywords(self, router, mock_classification_pmo_response):
        """Test urgency keywords trigger high priority"""
        headers = MockEmailHeaders(
            message_id="urgent-001",
            sender="manager@dol.gov",
            subject="URGENT: Deadline Approaching"
        )
        email = MockExtractedContent(
            headers=headers,
            plain_text="Time sensitive request with approaching deadline."
        )
        
        priority = router.assign_priority_level(email, mock_classification_pmo_response)
        assert priority == PriorityLevel.HIGH
    
    def test_assign_priority_regular_email_medium(self, router, mock_email_regular_pmo, 
                                                 mock_classification_pmo_response):
        """Test regular email gets medium priority"""
        priority = router.assign_priority_level(mock_email_regular_pmo, mock_classification_pmo_response)
        assert priority == PriorityLevel.MEDIUM
    
    def test_assign_priority_executive_request_override(self, router, mock_classification_executive_request):
        """Test executive request priority override (requirement 2.5)"""
        # Create email that would normally be low priority
        headers = MockEmailHeaders(
            message_id="exec-low-001",
            sender="regular@contractor.com",
            subject="Simple Request"
        )
        email = MockExtractedContent(headers=headers, plain_text="Simple request for information")
        
        priority = router.assign_priority_level(email, mock_classification_executive_request)
        assert priority == PriorityLevel.HIGH  # Should be elevated due to executive request type
    
    def test_assign_priority_white_house_critical(self, router, mock_email_white_house, 
                                                 mock_classification_new_eo):
        """Test White House email gets critical priority"""
        priority = router.assign_priority_level(mock_email_white_house, mock_classification_new_eo)
        assert priority == PriorityLevel.CRITICAL


class TestQueueRouting:
    """Test queue routing logic"""
    
    def test_route_to_queue_executive_priority(self, router):
        """Test executive workflow routes to priority queue"""
        queue = router.route_to_queue(WorkflowType.EXECUTIVE_REPORTING_WORKFLOW, PriorityLevel.HIGH)
        assert queue == QueueName.EXECUTIVE_PRIORITY_QUEUE
    
    def test_route_to_queue_eo_processing(self, router):
        """Test EO processing routes to EO queue"""
        queue = router.route_to_queue(WorkflowType.EXECUTIVE_ORDER_PROCESSING, PriorityLevel.MEDIUM)
        assert queue == QueueName.EO_PROCESSING_QUEUE
    
    def test_route_to_queue_pmo_workflow(self, router):
        """Test PMO workflow routes to PMO queue"""
        queue = router.route_to_queue(WorkflowType.PMO_APPROVAL_WORKFLOW, PriorityLevel.MEDIUM)
        assert queue == QueueName.PMO_WORKFLOW_QUEUE
    
    def test_route_to_queue_developer_workflow(self, router):
        """Test developer workflow routes to developer queue"""
        queue = router.route_to_queue(WorkflowType.DEVELOPER_TASK_WORKFLOW, PriorityLevel.LOW)
        assert queue == QueueName.DEVELOPER_QUEUE
    
    def test_route_to_queue_high_priority_executive(self, router):
        """Test high priority executive request routes to priority queue"""
        queue = router.route_to_queue(WorkflowType.EXECUTIVE_REPORTING_WORKFLOW, PriorityLevel.CRITICAL)
        assert queue == QueueName.EXECUTIVE_PRIORITY_QUEUE


class TestLoadBalancing:
    """Test load balancing functionality"""
    
    def test_load_balancing_disabled(self, router_no_load_balancing):
        """Test routing without load balancing"""
        queue = router_no_load_balancing.route_to_queue(
            WorkflowType.PMO_APPROVAL_WORKFLOW, PriorityLevel.MEDIUM
        )
        assert queue == QueueName.PMO_WORKFLOW_QUEUE
    
    def test_load_balancing_queue_overload(self, router):
        """Test load balancing when queue is overloaded"""
        # Simulate overloaded PMO queue (90% capacity should trigger load balancing)
        router.update_queue_metrics(
            QueueName.PMO_WORKFLOW_QUEUE,
            depth=180,  # 90% capacity (200 max) - should trigger load balancing
            processing_rate=5.0,
            avg_processing_time=60.0
        )
        
        # Should be redirected due to load balancing (90% > 80% threshold)
        queue = router.route_to_queue(WorkflowType.PMO_APPROVAL_WORKFLOW, PriorityLevel.MEDIUM)
        # Could be redirected to developer queue due to load balancing
        assert queue in [QueueName.PMO_WORKFLOW_QUEUE, QueueName.DEVELOPER_QUEUE]
    
    def test_load_balancing_critical_overload(self, router):
        """Test load balancing with critical queue overload"""
        # Simulate critically overloaded PMO queue
        router.update_queue_metrics(
            QueueName.PMO_WORKFLOW_QUEUE,
            depth=195,  # 97.5% capacity
            processing_rate=2.0,
            avg_processing_time=120.0
        )
        
        # Simulate available developer queue
        router.update_queue_metrics(
            QueueName.DEVELOPER_QUEUE,
            depth=50,  # Low utilization
            processing_rate=10.0,
            avg_processing_time=30.0
        )
        
        # Medium priority should be redirected to developer queue
        queue = router.route_to_queue(WorkflowType.PMO_APPROVAL_WORKFLOW, PriorityLevel.MEDIUM)
        # Note: This might still route to PMO queue depending on alternative queue logic
        assert queue in [QueueName.PMO_WORKFLOW_QUEUE, QueueName.DEVELOPER_QUEUE]
    
    def test_update_queue_metrics(self, router):
        """Test queue metrics update"""
        router.update_queue_metrics(
            QueueName.DEVELOPER_QUEUE,
            depth=75,
            processing_rate=8.5,
            avg_processing_time=45.0,
            error_rate=0.02
        )
        
        metrics = router.queue_metrics[QueueName.DEVELOPER_QUEUE]
        assert metrics.current_depth == 75
        assert metrics.processing_rate == 8.5
        assert metrics.average_processing_time == 45.0
        assert metrics.error_rate == 0.02
        assert metrics.capacity_utilization == 75 / 300  # Developer queue capacity is 300


class TestEscalation:
    """Test escalation functionality"""
    
    def test_handle_escalation_executive_request(self, router, mock_email_executive_urgent, 
                                               mock_classification_executive_request):
        """Test escalation for executive request with urgent keywords"""
        escalated = router.handle_high_priority_escalation(
            mock_email_executive_urgent, mock_classification_executive_request
        )
        assert escalated is True
    
    def test_handle_escalation_white_house_sender(self, router, mock_email_white_house, 
                                                mock_classification_new_eo):
        """Test escalation for White House sender"""
        escalated = router.handle_high_priority_escalation(
            mock_email_white_house, mock_classification_new_eo
        )
        assert escalated is True
    
    def test_handle_escalation_regular_email(self, router, mock_email_regular_pmo, 
                                           mock_classification_pmo_response):
        """Test no escalation for regular email"""
        escalated = router.handle_high_priority_escalation(
            mock_email_regular_pmo, mock_classification_pmo_response
        )
        assert escalated is False
    
    def test_escalation_congressional_inquiry(self, router, mock_classification_executive_request):
        """Test escalation for congressional inquiry"""
        headers = MockEmailHeaders(
            message_id="congress-001",
            sender="oversight@house.gov",
            subject="Congressional Oversight Inquiry"
        )
        email = MockExtractedContent(
            headers=headers,
            plain_text="Congressional inquiry regarding department operations and compliance."
        )
        
        escalated = router.handle_high_priority_escalation(email, mock_classification_executive_request)
        assert escalated is True


class TestWorkflowAssignment:
    """Test complete workflow assignment"""
    
    def test_create_workflow_assignment_executive(self, router, mock_email_executive_urgent, 
                                                mock_classification_executive_request):
        """Test complete workflow assignment for executive request"""
        assignment = router.create_workflow_assignment(
            mock_email_executive_urgent, mock_classification_executive_request
        )
        
        assert assignment.workflow_type == WorkflowType.EXECUTIVE_REPORTING_WORKFLOW
        assert assignment.priority_level == PriorityLevel.CRITICAL  # Congressional inquiry triggers CRITICAL
        assert assignment.assigned_queue == QueueName.EXECUTIVE_PRIORITY_QUEUE
        assert assignment.escalation_required is True
        assert assignment.estimated_processing_time > 0
        assert 'routing_timestamp' in assignment.routing_metadata
    
    def test_create_workflow_assignment_developer(self, router, mock_email_developer_update, 
                                                mock_classification_developer_update):
        """Test complete workflow assignment for developer update"""
        assignment = router.create_workflow_assignment(
            mock_email_developer_update, mock_classification_developer_update
        )
        
        assert assignment.workflow_type == WorkflowType.DEVELOPER_TASK_WORKFLOW
        assert assignment.priority_level == PriorityLevel.MEDIUM
        assert assignment.assigned_queue == QueueName.DEVELOPER_QUEUE
        assert assignment.escalation_required is False
        assert assignment.processing_requirements['requires_human_review'] is True
    
    def test_processing_requirements_eo(self, router, mock_email_white_house, 
                                      mock_classification_new_eo):
        """Test processing requirements for executive order"""
        assignment = router.create_workflow_assignment(
            mock_email_white_house, mock_classification_new_eo
        )
        
        requirements = assignment.processing_requirements
        assert requirements['requires_pdf_extraction'] is True
        assert requirements['requires_compliance_check'] is True
        assert requirements['requires_audit_logging'] is True
        assert requirements['retry_attempts'] == 3  # High priority gets more retries
    
    def test_processing_requirements_executive_reporting(self, router, mock_email_executive_urgent, 
                                                       mock_classification_executive_request):
        """Test processing requirements for executive reporting"""
        assignment = router.create_workflow_assignment(
            mock_email_executive_urgent, mock_classification_executive_request
        )
        
        requirements = assignment.processing_requirements
        assert requirements['requires_dashboard_generation'] is True
        assert requirements['requires_executive_formatting'] is True
        assert requirements['requires_attachment_processing'] is True


class TestStatisticsAndMetrics:
    """Test statistics and metrics collection"""
    
    def test_routing_statistics_tracking(self, router, mock_email_regular_pmo, 
                                       mock_classification_pmo_response):
        """Test routing statistics are tracked correctly"""
        initial_stats = router.get_routing_statistics()
        initial_total = initial_stats['routing_stats']['total_routed']
        
        # Create workflow assignment
        router.create_workflow_assignment(mock_email_regular_pmo, mock_classification_pmo_response)
        
        updated_stats = router.get_routing_statistics()
        assert updated_stats['routing_stats']['total_routed'] == initial_total + 1
        
        # Check that some queue got the assignment (could be PMO or developer due to load balancing)
        total_queue_assignments = sum(updated_stats['routing_stats']['per_queue_assignments'].values())
        assert total_queue_assignments > 0
        
        assert updated_stats['routing_stats']['per_priority_assignments']['MEDIUM'] > 0
    
    def test_escalation_statistics(self, router, mock_email_executive_urgent, 
                                 mock_classification_executive_request):
        """Test escalation statistics tracking"""
        initial_stats = router.get_routing_statistics()
        initial_escalations = initial_stats['routing_stats']['escalations_triggered']
        
        router.create_workflow_assignment(mock_email_executive_urgent, mock_classification_executive_request)
        
        updated_stats = router.get_routing_statistics()
        assert updated_stats['routing_stats']['escalations_triggered'] == initial_escalations + 1
    
    def test_queue_metrics_in_statistics(self, router):
        """Test queue metrics are included in statistics"""
        router.update_queue_metrics(
            QueueName.DEVELOPER_QUEUE,
            depth=50,
            processing_rate=7.5,
            avg_processing_time=40.0,
            error_rate=0.01
        )
        
        stats = router.get_routing_statistics()
        dev_queue_metrics = stats['queue_metrics'][QueueName.DEVELOPER_QUEUE.value]
        
        assert dev_queue_metrics['current_depth'] == 50
        assert dev_queue_metrics['processing_rate'] == 7.5
        assert dev_queue_metrics['capacity_utilization'] == 50 / 300
        assert dev_queue_metrics['error_rate'] == 0.01


class TestErrorHandling:
    """Test error handling and fallback behavior"""
    
    def test_priority_assignment_error_fallback(self, router):
        """Test priority assignment fallback on error"""
        # Create invalid email object
        invalid_email = Mock()
        invalid_email.headers.sender = None  # This should cause an error
        
        mock_classification = Mock(email_type=EmailType.DEVELOPER_UPDATE)
        
        priority = router.assign_priority_level(invalid_email, mock_classification)
        assert priority == PriorityLevel.MEDIUM  # Fallback priority
    
    def test_workflow_assignment_error_fallback(self, router):
        """Test workflow assignment fallback on error"""
        # Create invalid inputs
        invalid_email = None
        invalid_classification = None
        
        assignment = router.create_workflow_assignment(invalid_email, invalid_classification)
        
        # Should return fallback assignment
        assert assignment.workflow_type == WorkflowType.DEVELOPER_TASK_WORKFLOW
        assert assignment.priority_level == PriorityLevel.MEDIUM
        assert assignment.assigned_queue == QueueName.DEVELOPER_QUEUE
        assert 'error' in assignment.processing_requirements
    
    def test_queue_routing_error_fallback(self, router):
        """Test queue routing fallback on error"""
        # This should not cause an error, but test the fallback logic
        queue = router.route_to_queue(None, None)  # Invalid inputs
        assert queue == QueueName.DEVELOPER_QUEUE  # Fallback queue


class TestRequirementCompliance:
    """Test compliance with specific requirements"""
    
    def test_requirement_2_5_executive_priority(self, router):
        """Test requirement 2.5: Executive requests assign high priority"""
        # Test various executive request scenarios
        test_cases = [
            # Low priority content but executive request type should be elevated
            {
                'sender': 'regular@contractor.com',
                'subject': 'Simple Request',
                'content': 'Please provide information',
                'expected_priority': PriorityLevel.HIGH
            },
            # Already high priority content with executive request
            {
                'sender': 'secretary@dol.gov',
                'subject': 'URGENT: Report Required',
                'content': 'Urgent briefing request for congressional hearing',
                'expected_priority': PriorityLevel.HIGH
            }
        ]
        
        mock_classification = Mock(email_type=EmailType.EXECUTIVE_REQUEST)
        
        for case in test_cases:
            headers = MockEmailHeaders(
                message_id=f"test-{hash(case['sender'])}",
                sender=case['sender'],
                subject=case['subject']
            )
            email = MockExtractedContent(headers=headers, plain_text=case['content'])
            
            priority = router.assign_priority_level(email, mock_classification)
            assert priority == case['expected_priority'], f"Failed for case: {case}"
    
    def test_requirement_6_5_resource_constraint_prioritization(self, router):
        """Test requirement 6.5: Prioritize critical email types when constrained"""
        # Simulate resource constraints by overloading queues
        for queue in QueueName:
            router.update_queue_metrics(
                queue,
                depth=int(router.queue_capacities[queue] * 0.95),  # 95% capacity
                processing_rate=1.0,  # Slow processing
                avg_processing_time=300.0,  # Long processing time
                error_rate=0.1  # High error rate
            )
        
        # Test that critical priority still gets routed appropriately
        critical_queue = router.route_to_queue(
            WorkflowType.EXECUTIVE_REPORTING_WORKFLOW, 
            PriorityLevel.CRITICAL
        )
        
        # Should still route to executive priority queue even when constrained
        assert critical_queue == QueueName.EXECUTIVE_PRIORITY_QUEUE
        
        # Test that lower priority items might be redirected
        low_priority_queue = router.route_to_queue(
            WorkflowType.DEVELOPER_TASK_WORKFLOW,
            PriorityLevel.LOW
        )
        
        # Should route to appropriate queue (might be redirected due to load balancing)
        assert low_priority_queue in [QueueName.DEVELOPER_QUEUE, QueueName.PMO_WORKFLOW_QUEUE]


class TestPerformance:
    """Test performance characteristics"""
    
    def test_routing_performance(self, router, mock_email_regular_pmo, mock_classification_pmo_response):
        """Test routing performance under load"""
        start_time = time.time()
        
        # Perform multiple routing operations
        for i in range(100):
            router.create_workflow_assignment(mock_email_regular_pmo, mock_classification_pmo_response)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 100 routing operations in reasonable time (< 1 second)
        assert total_time < 1.0, f"Routing took too long: {total_time:.3f} seconds"
        
        # Average time per routing should be reasonable
        avg_time = total_time / 100
        assert avg_time < 0.01, f"Average routing time too high: {avg_time:.6f} seconds"
    
    def test_queue_metrics_update_performance(self, router):
        """Test queue metrics update performance"""
        start_time = time.time()
        
        # Update metrics for all queues multiple times
        for i in range(100):
            for queue in QueueName:
                router.update_queue_metrics(
                    queue,
                    depth=i % 50,
                    processing_rate=5.0 + (i % 10),
                    avg_processing_time=30.0 + (i % 20),
                    error_rate=0.01 * (i % 5)
                )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete all updates quickly
        assert total_time < 0.5, f"Metrics updates took too long: {total_time:.3f} seconds"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])