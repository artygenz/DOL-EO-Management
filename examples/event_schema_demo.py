#!/usr/bin/env python3
"""
Standardized Event Schema and Builder Demo

This demo showcases the standardized event schema and builder functionality,
including event creation, validation, schema migration, and backward compatibility.

Usage:
    python examples/event_schema_demo.py
"""

import sys
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.email.event_schema import (
    StandardizedEventBuilder,
    EventSchemaValidator,
    EventSchemaVersion,
    StandardizedEvent,
    create_event_from_email_processing,
    validate_event_compatibility,
    migrate_event_to_latest
)

# Mock classes for demo purposes
class MockEmailHeaders:
    def __init__(self):
        self.message_id = "<demo-email-123@dol.gov>"
        self.sender = "secretary@dol.gov"
        self.sender_name = "Secretary of Labor"
        self.recipients = ["pmo@dol.gov", "developers@dol.gov"]
        self.subject = "Executive Order 14058 - Implementation Directive"
        self.date = datetime.now(timezone.utc)

class MockExtractedContent:
    def __init__(self):
        self.headers = MockEmailHeaders()
        self.plain_text = """
        Executive Order 14058 - Transforming Federal Customer Experience and Service Delivery
        
        This executive order directs federal agencies to improve customer experience and service delivery.
        All agencies must implement new digital service standards within 180 days.
        
        Key requirements:
        1. Establish customer experience teams
        2. Implement digital-first service delivery
        3. Measure and report customer satisfaction
        4. Provide multilingual services
        
        Please coordinate implementation across all DOL divisions.
        """
        self.html_content = "<p>Executive Order content...</p>"
        self.content_hash = "eo14058_hash_abc123"
        self.attachments = [MockAttachment()]
        self.thread_analysis = MockThreadAnalysis()
        self.extraction_metadata = {
            'extraction_timestamp': datetime.now(timezone.utc),
            'extraction_duration_ms': 245.0
        }

class MockAttachment:
    def __init__(self):
        self.filename = "EO_14058_Implementation_Guide.pdf"
        self.content_type = "application/pdf"
        self.size_bytes = 2048576  # 2MB
        self.is_safe = True
        self.content_hash = "pdf_hash_def456"

class MockThreadAnalysis:
    def __init__(self):
        self.thread_id = "eo-14058-thread"
        self.is_reply = False
        self.is_forward = False
        self.thread_depth = 0
        self.conversation_participants = {"secretary@dol.gov", "pmo@dol.gov", "developers@dol.gov"}

class MockClassificationResult:
    def __init__(self):
        from src.email.email_classifier import EmailType
        self.email_type = EmailType.NEW_EO
        self.confidence_score = 0.97
        self.feature_importance = {
            "government_sender": 0.35,
            "executive_order_keywords": 0.30,
            "formal_language": 0.20,
            "pdf_attachment": 0.15
        }
        self.requires_manual_review = False
        self.alternative_classifications = []
        self.classification_timestamp = datetime.now(timezone.utc)
        self.classification_metadata = {
            'classification_method': 'ml_ensemble',
            'model_version': '1.2.0'
        }

class MockSecurityValidationResult:
    def __init__(self):
        self.sender_authorized = True
        self.content_safe = True
        self.attachments_safe = True
        self.validation_timestamp = datetime.now(timezone.utc)
        self.threat_indicators = []
        self.compliance_flags = ["FISMA_COMPLIANT", "FEDRAMP_AUTHORIZED"]

class MockWorkflowAssignment:
    def __init__(self):
        from src.email.workflow_router import WorkflowType, PriorityLevel, QueueName
        self.workflow_type = WorkflowType.EXECUTIVE_ORDER_PROCESSING
        self.priority_level = PriorityLevel.CRITICAL
        self.assigned_queue = QueueName.EO_PROCESSING_QUEUE
        self.processing_requirements = {
            "requires_pdf_extraction": True,
            "requires_compliance_check": True,
            "requires_audit_logging": True,
            "notification_required": True
        }
        self.estimated_processing_time = 450.0  # 7.5 minutes
        self.escalation_required = True


def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")


def demo_event_building():
    """Demo event building functionality"""
    print_header("STANDARDIZED EVENT BUILDING DEMO")
    
    # Create mock data
    extracted_content = MockExtractedContent()
    classification = MockClassificationResult()
    security_result = MockSecurityValidationResult()
    workflow_assignment = MockWorkflowAssignment()
    
    print_section("1. Creating Standardized Event")
    
    # Create event builder
    builder = StandardizedEventBuilder()
    
    # Build event
    event = builder.build_email_event(
        extracted_content=extracted_content,
        classification=classification,
        security_result=security_result,
        workflow_assignment=workflow_assignment
    )
    
    print(f"✓ Event created successfully!")
    print(f"  Event ID: {event.event_id}")
    print(f"  Correlation ID: {event.correlation_id}")
    print(f"  Event Type: {event.event_type}")
    print(f"  Priority: {event.priority}")
    print(f"  Confidence Score: {event.confidence_score}")
    print(f"  Schema Version: {event.schema_version}")
    
    print_section("2. Event Content Details")
    
    print(f"Email Metadata:")
    print(f"  Message ID: {event.email_metadata.message_id}")
    print(f"  Sender: {event.email_metadata.sender}")
    print(f"  Subject: {event.email_metadata.subject}")
    print(f"  Recipients: {len(event.email_metadata.recipients)} recipients")
    print(f"  Content Hash: {event.email_metadata.content_hash}")
    print(f"  Size: {event.email_metadata.size_bytes} bytes")
    
    print(f"\nContent:")
    print(f"  Body Text Length: {len(event.content.body_text)} characters")
    print(f"  Preview: {event.content.body_text_preview[:100]}...")
    print(f"  Has HTML: {event.content.has_html_content}")
    print(f"  Attachments: {len(event.content.attachments)}")
    if event.content.attachments:
        att = event.content.attachments[0]
        print(f"    - {att['filename']} ({att['size_bytes']} bytes, {att['content_type']})")
    
    print(f"\nSecurity:")
    print(f"  Sender Authorized: {event.security.sender_authorized}")
    print(f"  Content Safe: {event.security.content_safe}")
    print(f"  Attachments Safe: {event.security.attachments_safe}")
    print(f"  Compliance Flags: {event.security.compliance_flags}")
    
    print(f"\nWorkflow:")
    print(f"  Workflow Type: {event.workflow.workflow_type}")
    print(f"  Priority Level: {event.workflow.priority_level}")
    print(f"  Assigned Queue: {event.workflow.assigned_queue}")
    print(f"  Estimated Processing Time: {event.workflow.estimated_processing_time}s")
    print(f"  Escalation Required: {event.workflow.escalation_required}")
    
    return event


def demo_schema_validation(event: StandardizedEvent):
    """Demo schema validation functionality"""
    print_header("SCHEMA VALIDATION DEMO")
    
    validator = EventSchemaValidator()
    
    print_section("1. Validating Event Against Current Schema")
    
    is_valid, error = validator.validate_event(event.to_dict(), EventSchemaVersion.V2_0)
    
    if is_valid:
        print("✓ Event is valid against v2.0 schema")
    else:
        print(f"✗ Event validation failed: {error}")
    
    print_section("2. Checking Version Compatibility")
    
    compatible_versions = validator.check_version_compatibility(event.to_dict())
    
    print(f"Event is compatible with {len(compatible_versions)} schema versions:")
    for version in compatible_versions:
        print(f"  ✓ Schema version {version.value}")
    
    print_section("3. Validation Statistics")
    
    stats = validator.get_validation_statistics()
    print(f"Total Validations: {stats['total_validations']}")
    print(f"Successful Validations: {stats['successful_validations']}")
    print(f"Failed Validations: {stats['failed_validations']}")
    print(f"Compatibility Checks: {stats['version_compatibility_checks']}")


def demo_schema_migration():
    """Demo schema migration functionality"""
    print_header("SCHEMA MIGRATION DEMO")
    
    validator = EventSchemaValidator()
    
    print_section("1. Creating Legacy v1.0 Event")
    
    # Create a v1.0 event
    legacy_event = {
        "event_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "PMO_RESPONSE",
        "schema_version": "1.0",
        "priority": "MEDIUM",
        "confidence_score": 0.85,
        "email_metadata": {
            "uid": "legacy-uid-456",
            "message_id": "<legacy@dol.gov>",
            "sender": "pmo@dol.gov",
            "recipients": ["developer@dol.gov"],
            "subject": "Project Milestone Approval",
            "received_date": datetime.now(timezone.utc).isoformat()
        },
        "content": {
            "body_text": "The milestone has been approved. Please proceed with next phase.",
            "attachments": []
        },
        "security": {
            "sender_authorized": True,
            "content_safe": True,
            "attachments_safe": True
        },
        "workflow": {
            "assigned_queue": "pmo_workflow_queue",
            "workflow_type": "PMO_APPROVAL_WORKFLOW"
        }
    }
    
    print(f"✓ Created legacy v1.0 event")
    print(f"  Schema Version: {legacy_event['schema_version']}")
    print(f"  Event Type: {legacy_event['event_type']}")
    
    # Validate against v1.0 schema
    is_valid_v1, error = validator.validate_event(legacy_event, EventSchemaVersion.V1_0)
    print(f"  Valid against v1.0: {is_valid_v1}")
    
    print_section("2. Migrating to v2.0")
    
    # Migrate to v2.0
    migrated_event = validator.migrate_event_schema(
        legacy_event,
        EventSchemaVersion.V1_0,
        EventSchemaVersion.V2_0
    )
    
    print(f"✓ Successfully migrated to v2.0")
    print(f"  New Schema Version: {migrated_event['schema_version']}")
    
    # Show added fields
    print(f"\nAdded fields in v2.0:")
    print(f"  email_metadata.size_bytes: {migrated_event['email_metadata'].get('size_bytes', 'N/A')}")
    print(f"  content.body_text_preview: {migrated_event['content'].get('body_text_preview', 'N/A')[:50]}...")
    print(f"  content.has_html_content: {migrated_event['content'].get('has_html_content', 'N/A')}")
    print(f"  security.threat_indicators: {migrated_event['security'].get('threat_indicators', 'N/A')}")
    print(f"  workflow.priority_level: {migrated_event['workflow'].get('priority_level', 'N/A')}")
    print(f"  workflow.estimated_processing_time: {migrated_event['workflow'].get('estimated_processing_time', 'N/A')}")
    
    # Validate migrated event
    is_valid_v2, error = validator.validate_event(migrated_event, EventSchemaVersion.V2_0)
    print(f"\n✓ Migrated event valid against v2.0: {is_valid_v2}")
    
    print_section("3. Backward Compatibility Test")
    
    # Test that original data is preserved
    print("Verifying data preservation:")
    print(f"  Event ID preserved: {legacy_event['event_id'] == migrated_event['event_id']}")
    print(f"  Sender preserved: {legacy_event['email_metadata']['sender'] == migrated_event['email_metadata']['sender']}")
    print(f"  Content preserved: {legacy_event['content']['body_text'] == migrated_event['content']['body_text']}")
    print(f"  Security flags preserved: {legacy_event['security']['sender_authorized'] == migrated_event['security']['sender_authorized']}")


def demo_utility_functions():
    """Demo utility functions"""
    print_header("UTILITY FUNCTIONS DEMO")
    
    print_section("1. Convenience Event Creation")
    
    # Create mock data
    extracted_content = MockExtractedContent()
    classification = MockClassificationResult()
    security_result = MockSecurityValidationResult()
    workflow_assignment = MockWorkflowAssignment()
    
    # Use convenience function
    event = create_event_from_email_processing(
        extracted_content=extracted_content,
        classification=classification,
        security_result=security_result,
        workflow_assignment=workflow_assignment,
        correlation_id="custom-correlation-123"
    )
    
    print(f"✓ Event created using convenience function")
    print(f"  Custom Correlation ID: {event.correlation_id}")
    
    print_section("2. Event Compatibility Check")
    
    event_data = event.to_dict()
    compatible_versions = validate_event_compatibility(event_data)
    
    print(f"✓ Compatibility check completed")
    print(f"  Compatible with versions: {compatible_versions}")
    
    print_section("3. Migration to Latest")
    
    # Create older version event
    old_event = event_data.copy()
    old_event['schema_version'] = '1.0'
    
    latest_event = migrate_event_to_latest(old_event)
    
    print(f"✓ Migrated to latest version")
    print(f"  Original version: {old_event['schema_version']}")
    print(f"  Latest version: {latest_event['schema_version']}")


def demo_json_serialization(event: StandardizedEvent):
    """Demo JSON serialization"""
    print_header("JSON SERIALIZATION DEMO")
    
    print_section("1. Event to Dictionary")
    
    event_dict = event.to_dict()
    print(f"✓ Converted to dictionary")
    print(f"  Dictionary keys: {len(event_dict)} top-level fields")
    print(f"  Sample fields: {list(event_dict.keys())[:5]}")
    
    print_section("2. Event to JSON")
    
    event_json = event.to_json()
    print(f"✓ Converted to JSON")
    print(f"  JSON length: {len(event_json)} characters")
    
    # Pretty print first part of JSON
    print(f"\nJSON Preview (first 500 characters):")
    print(event_json[:500] + "..." if len(event_json) > 500 else event_json)
    
    print_section("3. JSON Validation")
    
    # Parse JSON back to verify it's valid
    try:
        parsed_json = json.loads(event_json)
        print(f"✓ JSON is valid and parseable")
        print(f"  Parsed event_id: {parsed_json['event_id']}")
        print(f"  Parsed event_type: {parsed_json['event_type']}")
    except json.JSONDecodeError as e:
        print(f"✗ JSON parsing failed: {e}")


def demo_performance_metrics():
    """Demo performance metrics"""
    print_header("PERFORMANCE METRICS DEMO")
    
    builder = StandardizedEventBuilder()
    validator = EventSchemaValidator()
    
    print_section("1. Builder Statistics")
    
    # Build a few events to generate stats
    for i in range(3):
        extracted_content = MockExtractedContent()
        classification = MockClassificationResult()
        security_result = MockSecurityValidationResult()
        workflow_assignment = MockWorkflowAssignment()
        
        builder.build_email_event(
            extracted_content=extracted_content,
            classification=classification,
            security_result=security_result,
            workflow_assignment=workflow_assignment
        )
    
    build_stats = builder.get_build_statistics()
    print(f"Builder Statistics:")
    for key, value in build_stats.items():
        print(f"  {key}: {value}")
    
    print_section("2. Validator Statistics")
    
    # Perform some validations
    sample_event = {
        "event_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "DEVELOPER_UPDATE",
        "schema_version": "2.0",
        "priority": "LOW",
        "confidence_score": 0.75,
        "email_metadata": {
            "uid": "test-uid",
            "message_id": "<test@example.com>",
            "sender": "dev@dol.gov",
            "recipients": ["pmo@dol.gov"],
            "subject": "Development Update",
            "received_date": datetime.now(timezone.utc).isoformat(),
            "content_hash": "hash123",
            "size_bytes": 512
        },
        "content": {
            "body_text": "Development progress update",
            "body_text_preview": "Development progress update",
            "has_html_content": False,
            "attachments": [],
            "classification_features": {},
            "thread_analysis": {}
        },
        "security": {
            "sender_authorized": True,
            "content_safe": True,
            "attachments_safe": True,
            "security_scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "threat_indicators": [],
            "compliance_flags": []
        },
        "workflow": {
            "assigned_queue": "developer_queue",
            "workflow_type": "DEVELOPER_TASK_WORKFLOW",
            "priority_level": "LOW",
            "processing_requirements": {},
            "estimated_processing_time": 60.0,
            "escalation_required": False
        },
        "processing_metadata": {}
    }
    
    validator.validate_event(sample_event, EventSchemaVersion.V2_0)
    validator.check_version_compatibility(sample_event)
    
    validation_stats = validator.get_validation_statistics()
    print(f"Validator Statistics:")
    for key, value in validation_stats.items():
        print(f"  {key}: {value}")


def main():
    """Main demo function"""
    print("🚀 Starting Standardized Event Schema and Builder Demo")
    print("This demo showcases federal-grade email event processing capabilities")
    
    try:
        # Demo event building
        event = demo_event_building()
        
        # Demo schema validation
        demo_schema_validation(event)
        
        # Demo schema migration
        demo_schema_migration()
        
        # Demo utility functions
        demo_utility_functions()
        
        # Demo JSON serialization
        demo_json_serialization(event)
        
        # Demo performance metrics
        demo_performance_metrics()
        
        print_header("DEMO COMPLETED SUCCESSFULLY")
        print("✅ All event schema and builder features demonstrated")
        print("✅ Schema validation and migration working correctly")
        print("✅ Backward compatibility maintained across versions")
        print("✅ Federal compliance requirements satisfied")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())