#!/usr/bin/env python3
"""
Workflow Router Demo

Demonstrates the Priority Assessment and Workflow Routing System functionality
including priority assignment, workflow determination, queue routing, and
executive request escalation.
"""

import sys
import os
from datetime import datetime
from dataclasses import dataclass

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.email.workflow_router import (
    WorkflowRouter, PriorityLevel, WorkflowType, QueueName
)
from src.email.email_classifier import EmailType


@dataclass
class MockEmailHeaders:
    """Mock email headers for demo"""
    message_id: str
    sender: str
    subject: str
    date: datetime = None
    
    def __post_init__(self):
        if self.date is None:
            self.date = datetime.utcnow()


@dataclass
class MockExtractedContent:
    """Mock extracted content for demo"""
    headers: MockEmailHeaders
    plain_text: str
    attachments: list = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


@dataclass
class MockClassification:
    """Mock classification result for demo"""
    email_type: EmailType
    confidence_score: float
    requires_manual_review: bool = False


def create_demo_emails():
    """Create demo emails for testing"""
    return [
        {
            'name': 'Executive Order from White House',
            'email': MockExtractedContent(
                headers=MockEmailHeaders(
                    message_id='eo-001',
                    sender='directive@whitehouse.gov',
                    subject='Executive Order 14001 - Implementation Required'
                ),
                plain_text='Executive order requires immediate implementation across all federal agencies. '
                          'Compliance deadline is 30 days from effective date.'
            ),
            'classification': MockClassification(
                email_type=EmailType.NEW_EO,
                confidence_score=0.98
            )
        },
        {
            'name': 'Urgent Executive Request',
            'email': MockExtractedContent(
                headers=MockEmailHeaders(
                    message_id='exec-urgent-001',
                    sender='secretary@dol.gov',
                    subject='URGENT: Congressional Inquiry Response Required'
                ),
                plain_text='Congressional inquiry requires immediate response. '
                          'Briefing materials needed for oversight hearing.'
            ),
            'classification': MockClassification(
                email_type=EmailType.EXECUTIVE_REQUEST,
                confidence_score=0.95
            )
        },
        {
            'name': 'PMO Status Update',
            'email': MockExtractedContent(
                headers=MockEmailHeaders(
                    message_id='pmo-001',
                    sender='pmo.manager@dol.gov',
                    subject='Project Milestone Review - Q3 Deliverables'
                ),
                plain_text='Please provide status update on Q3 project deliverables. '
                          'Review meeting scheduled for next week.'
            ),
            'classification': MockClassification(
                email_type=EmailType.PMO_RESPONSE,
                confidence_score=0.92
            )
        },
        {
            'name': 'Developer Progress Update',
            'email': MockExtractedContent(
                headers=MockEmailHeaders(
                    message_id='dev-001',
                    sender='developer@contractor.com',
                    subject='Development Progress - API Implementation'
                ),
                plain_text='API development is 80% complete. Testing phase will begin next week. '
                          'No blockers identified at this time.'
            ),
            'classification': MockClassification(
                email_type=EmailType.DEVELOPER_UPDATE,
                confidence_score=0.88,
                requires_manual_review=True
            )
        },
        {
            'name': 'Regular Executive Report Request',
            'email': MockExtractedContent(
                headers=MockEmailHeaders(
                    message_id='exec-regular-001',
                    sender='deputy.director@dol.gov',
                    subject='Monthly Dashboard Report Request'
                ),
                plain_text='Please prepare monthly dashboard report for executive review. '
                          'Include performance metrics and key achievements.'
            ),
            'classification': MockClassification(
                email_type=EmailType.EXECUTIVE_REQUEST,
                confidence_score=0.85
            )
        }
    ]


def demonstrate_workflow_routing():
    """Demonstrate workflow routing functionality"""
    print("=" * 80)
    print("WORKFLOW ROUTER DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Initialize workflow router
    print("1. Initializing Workflow Router...")
    router = WorkflowRouter(enable_load_balancing=True)
    print("   ✓ Router initialized with load balancing enabled")
    print()
    
    # Create demo emails
    demo_emails = create_demo_emails()
    
    print("2. Processing Demo Emails...")
    print("-" * 50)
    
    for i, demo in enumerate(demo_emails, 1):
        print(f"\n📧 Email {i}: {demo['name']}")
        print(f"   From: {demo['email'].headers.sender}")
        print(f"   Subject: {demo['email'].headers.subject}")
        print(f"   Classification: {demo['classification'].email_type.value}")
        print(f"   Confidence: {demo['classification'].confidence_score:.2f}")
        
        # Create workflow assignment
        assignment = router.create_workflow_assignment(
            demo['email'], demo['classification']
        )
        
        print(f"   → Workflow: {assignment.workflow_type.value}")
        print(f"   → Priority: {assignment.priority_level.value}")
        print(f"   → Queue: {assignment.assigned_queue.value}")
        print(f"   → Escalation Required: {assignment.escalation_required}")
        print(f"   → Estimated Processing Time: {assignment.estimated_processing_time:.0f}s")
        
        if assignment.escalation_required:
            print("   ⚠️  HIGH PRIORITY ESCALATION TRIGGERED!")
    
    print("\n" + "=" * 50)
    print("3. Router Statistics")
    print("=" * 50)
    
    stats = router.get_routing_statistics()
    routing_stats = stats['routing_stats']
    
    print(f"Total Emails Routed: {routing_stats['total_routed']}")
    print(f"Escalations Triggered: {routing_stats['escalations_triggered']}")
    print(f"Load Balancing Adjustments: {routing_stats['load_balancing_adjustments']}")
    
    print("\nQueue Assignments:")
    for queue, count in routing_stats['per_queue_assignments'].items():
        if count > 0:
            print(f"  {queue}: {count} emails")
    
    print("\nPriority Distribution:")
    for priority, count in routing_stats['per_priority_assignments'].items():
        if count > 0:
            print(f"  {priority}: {count} emails")
    
    print("\n" + "=" * 50)
    print("4. Load Balancing Demonstration")
    print("=" * 50)
    
    # Simulate queue overload
    print("\nSimulating queue overload scenarios...")
    
    # Overload PMO queue
    router.update_queue_metrics(
        QueueName.PMO_WORKFLOW_QUEUE,
        depth=180,  # Near capacity
        processing_rate=2.0,  # Slow processing
        avg_processing_time=120.0,
        error_rate=0.05
    )
    
    print("PMO Queue overloaded (90% capacity)")
    
    # Route a PMO workflow
    queue = router.route_to_queue(
        WorkflowType.PMO_APPROVAL_WORKFLOW,
        PriorityLevel.MEDIUM,
        "test-email-001"
    )
    
    print(f"PMO workflow routed to: {queue.value}")
    
    # Test high priority routing under load
    queue = router.route_to_queue(
        WorkflowType.EXECUTIVE_REPORTING_WORKFLOW,
        PriorityLevel.CRITICAL,
        "test-email-002"
    )
    
    print(f"Critical executive workflow routed to: {queue.value}")
    
    print("\n" + "=" * 50)
    print("5. Priority Assessment Examples")
    print("=" * 50)
    
    # Test different priority scenarios
    priority_test_cases = [
        {
            'name': 'Congressional Inquiry',
            'email': MockExtractedContent(
                headers=MockEmailHeaders(
                    message_id='congress-001',
                    sender='oversight@house.gov',
                    subject='Congressional Oversight Request'
                ),
                plain_text='Congressional inquiry regarding department compliance with federal regulations.'
            ),
            'classification': MockClassification(EmailType.EXECUTIVE_REQUEST, 0.90)
        },
        {
            'name': 'Regular Developer Update',
            'email': MockExtractedContent(
                headers=MockEmailHeaders(
                    message_id='dev-regular-001',
                    sender='dev@contractor.com',
                    subject='Weekly Progress Report'
                ),
                plain_text='Weekly development progress report. All tasks on schedule.'
            ),
            'classification': MockClassification(EmailType.DEVELOPER_UPDATE, 0.85)
        },
        {
            'name': 'Emergency Response',
            'email': MockExtractedContent(
                headers=MockEmailHeaders(
                    message_id='emergency-001',
                    sender='director@dol.gov',
                    subject='EMERGENCY: System Outage Response'
                ),
                plain_text='Critical system outage affecting national security operations. Immediate response required.'
            ),
            'classification': MockClassification(EmailType.EXECUTIVE_REQUEST, 0.95)
        }
    ]
    
    for test_case in priority_test_cases:
        priority = router.assign_priority_level(
            test_case['email'], test_case['classification']
        )
        print(f"\n{test_case['name']}: {priority.value}")
        print(f"  Reason: Content analysis and sender patterns")
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("✓ Priority assessment based on email type and content")
    print("✓ Executive request escalation with high priority handling")
    print("✓ Workflow determination and queue routing logic")
    print("✓ Load balancing across processing queues")
    print("✓ Comprehensive statistics and metrics tracking")
    print("✓ Requirement 2.5: Executive requests assign high priority")
    print("✓ Requirement 6.5: Critical email prioritization under resource constraints")


if __name__ == "__main__":
    try:
        demonstrate_workflow_routing()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()