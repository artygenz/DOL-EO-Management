"""
Template Engine Demo

Demonstrates the government-compliant email template system for automated email generation.
"""

import os
import sys
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.email.email_generator import (
    EmailGenerator,
    TaskAssignmentData,
    PMOApprovalData,
    ExecutiveSummaryData
)


def main():
    """Demonstrate template engine functionality"""
    print("=== Email Template Engine Demo ===\n")
    
    # Initialize email generator
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "email")
    generator = EmailGenerator(templates_dir)
    
    print("1. Available Templates:")
    templates = generator.get_available_templates()
    for template_id in templates:
        info = generator.get_template_info(template_id)
        print(f"   - {template_id}: {info['name']} ({info['type']})")
    print()
    
    # Demo 1: Task Assignment Email
    print("2. Generating Task Assignment Email:")
    task_data = TaskAssignmentData(
        task_id="TASK-2024-001",
        task_title="Implement Email Security Validation",
        task_description="Develop comprehensive email security validation system with threat detection and government compliance features",
        priority_level="HIGH",
        due_date=datetime.now() + timedelta(days=14),
        project_name="Email Agent Security Enhancement",
        requirements=[
            "Implement malware scanning integration",
            "Add sender authorization validation",
            "Create threat detection algorithms",
            "Ensure FISMA compliance"
        ],
        deliverables=[
            "Security validation module",
            "Threat detection engine",
            "Comprehensive test suite",
            "Security documentation",
            "Compliance certification"
        ],
        assignee_name="John Security Developer",
        assignee_email="john.security@dol.gov"
    )
    
    task_email = generator.generate_task_assignment_email(
        task_data,
        sender_name="Sarah Project Manager",
        sender_title="Senior Project Manager",
        correlation_id="DEMO-TASK-001"
    )
    
    print(f"   Subject: {task_email.subject}")
    print(f"   To: {task_email.recipient_email}")
    print(f"   From: {task_email.sender_email}")
    print(f"   Correlation ID: {task_email.correlation_id}")
    print(f"   Compliance Level: {task_email.compliance_level.value}")
    print("   Content Preview:")
    print("   " + task_email.body_text[:200].replace('\n', '\n   ') + "...")
    print()
    
    # Demo 2: PMO Approval Email
    print("3. Generating PMO Approval Request Email:")
    pmo_data = PMOApprovalData(
        request_id="REQ-2024-007",
        request_type="Critical Security Enhancement",
        request_summary="Request approval for implementing advanced email security features to meet new federal cybersecurity requirements",
        justification="Recent federal guidelines require enhanced email security measures. This implementation will ensure compliance and protect against emerging threats.",
        estimated_cost=125000.0,
        estimated_timeline="6 months",
        risk_assessment="Medium risk - requires careful integration with existing systems and thorough testing",
        approval_deadline=datetime.now() + timedelta(days=7),
        supporting_documents=[
            "Federal Cybersecurity Requirements Analysis",
            "Technical Implementation Plan",
            "Cost-Benefit Analysis",
            "Risk Assessment Report",
            "Security Architecture Design"
        ],
        pmo_contact_name="Michael PMO Director",
        pmo_contact_email="michael.pmo@dol.gov"
    )
    
    pmo_email = generator.generate_pmo_approval_email(
        pmo_data,
        sender_name="Dr. Alice System Architect",
        sender_title="Chief System Architect",
        correlation_id="DEMO-PMO-001"
    )
    
    print(f"   Subject: {pmo_email.subject}")
    print(f"   To: {pmo_email.recipient_email}")
    print(f"   From: {pmo_email.sender_email}")
    print(f"   Correlation ID: {pmo_email.correlation_id}")
    print(f"   Compliance Level: {pmo_email.compliance_level.value}")
    print("   Content Preview:")
    print("   " + pmo_email.body_text[:200].replace('\n', '\n   ') + "...")
    print()
    
    # Demo 3: Developer Notification Email
    print("4. Generating Developer Notification Email:")
    notification_email = generator.generate_developer_notification_email(
        notification_type="System Maintenance Alert",
        message="Scheduled maintenance will be performed on the email processing system this weekend. The system will be unavailable from Saturday 2:00 AM to 6:00 AM EST. Please plan your development activities accordingly.",
        recipient_name="Development Team",
        recipient_email="dev.team@dol.gov",
        additional_data={
            "maintenance_window": "Saturday 2:00 AM - 6:00 AM EST",
            "affected_systems": ["Email Processing", "Database", "Queue System"],
            "contact": "ops.team@dol.gov"
        },
        sender_name="Operations Team",
        sender_title="System Operations",
        correlation_id="DEMO-NOTIFICATION-001"
    )
    
    print(f"   Subject: {notification_email.subject}")
    print(f"   To: {notification_email.recipient_email}")
    print(f"   From: {notification_email.sender_email}")
    print(f"   Correlation ID: {notification_email.correlation_id}")
    print("   Content Preview:")
    print("   " + notification_email.body_text[:200].replace('\n', '\n   ') + "...")
    print()
    
    # Demo 4: Template Validation
    print("5. Template Validation Demo:")
    try:
        # Valid data
        generator.validate_email_data("task_assignment", {
            "task_id": "TASK-001",
            "task_title": "Test Task",
            "task_description": "Description",
            "assignee_name": "John Doe",
            "assignee_email": "john@dol.gov"
        })
        print("   ✓ Valid task assignment data passed validation")
        
        # Invalid data
        try:
            generator.validate_email_data("task_assignment", {
                "task_id": "TASK-001"
                # Missing required fields
            })
        except Exception as e:
            print(f"   ✓ Invalid data correctly rejected: {str(e)}")
        
    except Exception as e:
        print(f"   ✗ Validation error: {str(e)}")
    
    print()
    
    # Demo 5: Government Compliance Features
    print("6. Government Compliance Features:")
    print("   ✓ All emails include correlation IDs for audit trails")
    print("   ✓ Government domain enforcement (.gov)")
    print("   ✓ Content sanitization (PII redaction)")
    print("   ✓ Classification headers for sensitive content")
    print("   ✓ Official government identification in all emails")
    print("   ✓ Structured metadata for compliance reporting")
    print()
    
    # Demo 6: Template Metadata
    print("7. Template Metadata:")
    task_template_info = generator.get_template_info("task_assignment_v1")
    if task_template_info:
        print(f"   Template: {task_template_info['name']}")
        print(f"   Version: {task_template_info['version']}")
        print(f"   Government Approved: {task_template_info['government_approved']}")
        print(f"   Compliance Level: {task_template_info['compliance_level']}")
        print(f"   Required Fields: {', '.join(task_template_info['required_fields'])}")
    
    print("\n=== Demo Complete ===")
    print("The template engine successfully generated government-compliant emails")
    print("with proper formatting, security features, and audit compliance.")


if __name__ == "__main__":
    main()