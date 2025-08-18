"""
Unit tests for Standardized Event Schema and Builder

Tests event schema validation, version compatibility checking, backward compatibility,
correlation ID generation, and security metadata handling.
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from typing import Dict, Any

from src.email.event_schema import (
    StandardizedEventBuilder,
    EventSchemaValidator,
    EventSchemaVersion,
    StandardizedEvent,
    EventEmailMetadata,
    EventContent,
    EventSecurity,
    EventWorkflow,
    EventType,
    EventPriority,
    EventBuildError,
    create_event_from_email_processing,
    validate_event_compatibility,
    migrate_event_to_latest
)


class TestEventSchemaValidator:
    """Test event schema validation functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = EventSchemaValidator()
        self.sample_event_v1_0 = {
            "event_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "NEW_EO",
            "schema_version": "1.0",
            "priority": "HIGH",
            "confidence_score": 0.95,
            "email_metadata": {
                "uid": "test-uid-123",
                "message_id": "<test@example.com>",
                "sender": "sender@dol.gov",
                "sender_name": "Test Sender",
                "recipients": ["recipient@dol.gov"],
                "subject": "Test Executive Order",
                "received_date": datetime.now(timezone.utc).isoformat(),
                "thread_id": "thread-123",
                "content_hash": "abc123",
                "size_bytes": 1024
            },
            "content": {
                "body_text": "This is a test executive order email.",
                "body_text_preview": "This is a test executive order email.",
                "has_html_content": False,
                "attachments": [],
                "classification_features": {"formality_score": 0.8},
                "thread_analysis": {"thread_depth": 0}
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
                "assigned_queue": "eo_processing_queue",
                "workflow_type": "EXECUTIVE_ORDER_PROCESSING",
                "priority_level": "HIGH",
                "processing_requirements": {"requires_pdf_extraction": True},
                "estimated_processing_time": 300.0,
                "escalation_required": False
            },
            "processing_metadata": {}
        }
    
    def test_validate_valid_event_v1_0(self):
        """Test validation of valid v1.0 event"""
        is_valid, error = self.validator.validate_event(
            self.sample_event_v1_0, EventSchemaVersion.V1_0
        )
        
        assert is_valid is True
        assert error is None
        assert self.validator.validation_stats['successful_validations'] > 0
    
    def test_validate_valid_event_v2_0(self):
        """Test validation of valid v2.0 event"""
        # Convert v1.0 event to v2.0 format
        event_v2_0 = self.sample_event_v1_0.copy()
        event_v2_0['schema_version'] = '2.0'
        
        is_valid, error = self.validator.validate_event(
            event_v2_0, EventSchemaVersion.V2_0
        )
        
        assert is_valid is True
        assert error is None
    
    def test_validate_invalid_event_missing_required_field(self):
        """Test validation failure for missing required field"""
        invalid_event = self.sample_event_v1_0.copy()
        del invalid_event['event_id']  # Remove required field
        
        is_valid, error = self.validator.validate_event(
            invalid_event, EventSchemaVersion.V1_0
        )
        
        assert is_valid is False
        assert error is not None
        assert "'event_id' is a required property" in error
        assert self.validator.validation_stats['failed_validations'] > 0
    
    def test_validate_invalid_event_wrong_type(self):
        """Test validation failure for wrong field type"""
        invalid_event = self.sample_event_v1_0.copy()
        invalid_event['confidence_score'] = "invalid"  # Should be number
        
        is_valid, error = self.validator.validate_event(
            invalid_event, EventSchemaVersion.V1_0
        )
        
        assert is_valid is False
        assert error is not None
        assert "is not of type 'number'" in error
    
    def test_validate_invalid_event_out_of_range(self):
        """Test validation failure for out of range value"""
        invalid_event = self.sample_event_v1_0.copy()
        invalid_event['confidence_score'] = 1.5  # Should be <= 1.0
        
        is_valid, error = self.validator.validate_event(
            invalid_event, EventSchemaVersion.V1_0
        )
        
        assert is_valid is False
        assert error is not None
        assert "1.5 is greater than the maximum of 1.0" in error
    
    def test_check_version_compatibility(self):
        """Test version compatibility checking"""
        compatible_versions = self.validator.check_version_compatibility(
            self.sample_event_v1_0
        )
        
        # Should be compatible with multiple versions
        assert len(compatible_versions) >= 1
        assert EventSchemaVersion.V1_0 in compatible_versions
        assert self.validator.validation_stats['version_compatibility_checks'] > 0
    
    def test_migrate_v1_0_to_v1_1(self):
        """Test migration from v1.0 to v1.1"""
        migrated = self.validator.migrate_event_schema(
            self.sample_event_v1_0,
            EventSchemaVersion.V1_0,
            EventSchemaVersion.V1_1
        )
        
        assert migrated['schema_version'] == '1.1'
        assert 'thread_analysis' in migrated['content']
        assert 'processing_metadata' in migrated
        assert 'extraction_duration_ms' in migrated['processing_metadata']
        assert self.validator.validation_stats['schema_migrations'] > 0
    
    def test_migrate_v1_0_to_v2_0(self):
        """Test migration from v1.0 to v2.0"""
        migrated = self.validator.migrate_event_schema(
            self.sample_event_v1_0,
            EventSchemaVersion.V1_0,
            EventSchemaVersion.V2_0
        )
        
        assert migrated['schema_version'] == '2.0'
        assert 'size_bytes' in migrated['email_metadata']
        assert 'body_text_preview' in migrated['content']
        assert 'has_html_content' in migrated['content']
        assert 'threat_indicators' in migrated['security']
        assert 'compliance_flags' in migrated['security']
        assert 'priority_level' in migrated['workflow']
        assert 'estimated_processing_time' in migrated['workflow']
        assert 'escalation_required' in migrated['workflow']
    
    def test_migrate_same_version(self):
        """Test migration with same source and target version"""
        migrated = self.validator.migrate_event_schema(
            self.sample_event_v1_0,
            EventSchemaVersion.V1_0,
            EventSchemaVersion.V1_0
        )
        
        assert migrated == self.sample_event_v1_0
    
    def test_get_validation_statistics(self):
        """Test getting validation statistics"""
        # Perform some validations
        self.validator.validate_event(self.sample_event_v1_0, EventSchemaVersion.V1_0)
        self.validator.check_version_compatibility(self.sample_event_v1_0)
        
        stats = self.validator.get_validation_statistics()
        
        assert 'total_validations' in stats
        assert 'successful_validations' in stats
        assert 'failed_validations' in stats
        assert 'version_compatibility_checks' in stats
        assert 'schema_migrations' in stats
        assert stats['total_validations'] > 0


class TestStandardizedEventBuilder:
    """Test standardized event builder functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.builder = StandardizedEventBuilder()
        
        # Create mock objects for dependencies
        self.mock_extracted_content = self._create_mock_extracted_content()
        self.mock_classification = self._create_mock_classification()
        self.mock_security_result = self._create_mock_security_result()
        self.mock_workflow_assignment = self._create_mock_workflow_assignment()
    
    def _create_mock_extracted_content(self):
        """Create mock extracted content"""
        mock_content = Mock()
        
        # Mock headers
        mock_headers = Mock()
        mock_headers.message_id = "<test@example.com>"
        mock_headers.sender = "sender@dol.gov"
        mock_headers.sender_name = "Test Sender"
        mock_headers.recipients = ["recipient@dol.gov"]
        mock_headers.subject = "Test Executive Order"
        mock_headers.date = datetime.now(timezone.utc)
        mock_content.headers = mock_headers
        
        # Mock content
        mock_content.plain_text = "This is a test executive order email content."
        mock_content.html_content = "<p>This is a test executive order email content.</p>"
        mock_content.content_hash = "abc123hash"
        
        # Mock attachments
        mock_attachment = Mock()
        mock_attachment.filename = "executive_order.pdf"
        mock_attachment.content_type = "application/pdf"
        mock_attachment.size_bytes = 1024
        mock_attachment.is_safe = True
        mock_attachment.content_hash = "attachment_hash"
        mock_content.attachments = [mock_attachment]
        
        # Mock thread analysis
        mock_thread = Mock()
        mock_thread.thread_id = "thread-123"
        mock_thread.is_reply = False
        mock_thread.is_forward = False
        mock_thread.thread_depth = 0
        mock_thread.conversation_participants = {"sender@dol.gov", "recipient@dol.gov"}
        mock_content.thread_analysis = mock_thread
        
        # Mock extraction metadata
        mock_content.extraction_metadata = {
            'extraction_timestamp': datetime.now(timezone.utc),
            'extraction_duration_ms': 150.0
        }
        
        return mock_content
    
    def _create_mock_classification(self):
        """Create mock classification result"""
        from src.email.email_classifier import EmailType, ClassificationResult
        
        mock_classification = Mock(spec=ClassificationResult)
        mock_classification.email_type = EmailType.NEW_EO
        mock_classification.confidence_score = 0.95
        mock_classification.feature_importance = {"formality_score": 0.8, "government_sender": 0.9}
        mock_classification.requires_manual_review = False
        mock_classification.alternative_classifications = []
        mock_classification.classification_timestamp = datetime.now(timezone.utc)
        mock_classification.classification_metadata = {
            'classification_method': 'ml_ensemble',
            'model_version': '1.0.0'
        }
        
        return mock_classification
    
    def _create_mock_security_result(self):
        """Create mock security validation result"""
        mock_security = Mock()
        mock_security.sender_authorized = True
        mock_security.content_safe = True
        mock_security.attachments_safe = True
        mock_security.validation_timestamp = datetime.now(timezone.utc)
        mock_security.threat_indicators = []
        mock_security.compliance_flags = ["FISMA_COMPLIANT"]
        
        return mock_security
    
    def _create_mock_workflow_assignment(self):
        """Create mock workflow assignment"""
        from src.email.workflow_router import WorkflowType, PriorityLevel, QueueName
        
        mock_workflow = Mock()
        mock_workflow.workflow_type = WorkflowType.EXECUTIVE_ORDER_PROCESSING
        mock_workflow.priority_level = PriorityLevel.HIGH
        mock_workflow.assigned_queue = QueueName.EO_PROCESSING_QUEUE
        mock_workflow.processing_requirements = {"requires_pdf_extraction": True}
        mock_workflow.estimated_processing_time = 300.0
        mock_workflow.escalation_required = False
        
        return mock_workflow
    
    def test_build_email_event_success(self):
        """Test successful event building"""
        event = self.builder.build_email_event(
            extracted_content=self.mock_extracted_content,
            classification=self.mock_classification,
            security_result=self.mock_security_result,
            workflow_assignment=self.mock_workflow_assignment
        )
        
        assert isinstance(event, StandardizedEvent)
        assert event.event_id is not None
        assert event.correlation_id is not None
        assert event.event_type == EventType.NEW_EO.value
        assert event.priority == EventPriority.HIGH.value
        assert event.confidence_score == 0.95
        assert event.schema_version == EventSchemaVersion.V2_0.value
        
        # Check email metadata
        assert event.email_metadata.message_id == "<test@example.com>"
        assert event.email_metadata.sender == "sender@dol.gov"
        assert event.email_metadata.subject == "Test Executive Order"
        
        # Check content
        assert "This is a test executive order email content." in event.content.body_text
        assert len(event.content.attachments) == 1
        assert event.content.attachments[0]['filename'] == "executive_order.pdf"
        
        # Check security
        assert event.security.sender_authorized is True
        assert event.security.content_safe is True
        assert event.security.attachments_safe is True
        
        # Check workflow
        assert event.workflow.workflow_type == "EXECUTIVE_ORDER_PROCESSING"
        assert event.workflow.priority_level == "HIGH"
        assert event.workflow.assigned_queue == "eo_processing_queue"
        
        assert self.builder.build_stats['successful_builds'] > 0
    
    def test_build_email_event_with_custom_correlation_id(self):
        """Test event building with custom correlation ID"""
        custom_correlation_id = str(uuid.uuid4())
        
        event = self.builder.build_email_event(
            extracted_content=self.mock_extracted_content,
            classification=self.mock_classification,
            security_result=self.mock_security_result,
            workflow_assignment=self.mock_workflow_assignment,
            correlation_id=custom_correlation_id
        )
        
        assert event.correlation_id == custom_correlation_id
        # Should not increment generated correlation IDs counter
        assert self.builder.build_stats['correlation_ids_generated'] == 0
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation"""
        message_id = "<test@example.com>"
        correlation_id = self.builder.generate_correlation_id(message_id)
        
        assert correlation_id is not None
        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 36  # UUID format
        
        # Test with context
        correlation_id_with_context = self.builder.generate_correlation_id(
            message_id, context="test_context"
        )
        assert correlation_id_with_context != correlation_id
    
    def test_validate_event_schema(self):
        """Test event schema validation"""
        event = self.builder.build_email_event(
            extracted_content=self.mock_extracted_content,
            classification=self.mock_classification,
            security_result=self.mock_security_result,
            workflow_assignment=self.mock_workflow_assignment
        )
        
        is_valid, error = self.builder.validate_event_schema(event)
        
        assert is_valid is True
        assert error is None
    
    def test_add_security_metadata(self):
        """Test adding additional security metadata"""
        event = self.builder.build_email_event(
            extracted_content=self.mock_extracted_content,
            classification=self.mock_classification,
            security_result=self.mock_security_result,
            workflow_assignment=self.mock_workflow_assignment
        )
        
        additional_security = {
            'threat_indicators': ['suspicious_attachment'],
            'compliance_flags': ['NIST_REVIEWED']
        }
        
        enhanced_event = self.builder.add_security_metadata(event, additional_security)
        
        assert 'suspicious_attachment' in enhanced_event.security.threat_indicators
        assert 'NIST_REVIEWED' in enhanced_event.security.compliance_flags
        assert 'security_enhancement_timestamp' in enhanced_event.processing_metadata
    
    def test_build_event_failure_handling(self):
        """Test event building failure handling"""
        # Create invalid mock that will cause failure
        invalid_mock = Mock()
        invalid_mock.headers = None  # This should cause an error
        
        with pytest.raises(EventBuildError):
            self.builder.build_email_event(
                extracted_content=invalid_mock,
                classification=self.mock_classification,
                security_result=self.mock_security_result,
                workflow_assignment=self.mock_workflow_assignment
            )
        
        assert self.builder.build_stats['failed_builds'] > 0
    
    def test_get_build_statistics(self):
        """Test getting build statistics"""
        # Build an event
        self.builder.build_email_event(
            extracted_content=self.mock_extracted_content,
            classification=self.mock_classification,
            security_result=self.mock_security_result,
            workflow_assignment=self.mock_workflow_assignment
        )
        
        stats = self.builder.get_build_statistics()
        
        assert 'total_events_built' in stats
        assert 'successful_builds' in stats
        assert 'failed_builds' in stats
        assert 'correlation_ids_generated' in stats
        assert stats['total_events_built'] > 0
    
    def test_event_to_dict_and_json(self):
        """Test event serialization to dict and JSON"""
        event = self.builder.build_email_event(
            extracted_content=self.mock_extracted_content,
            classification=self.mock_classification,
            security_result=self.mock_security_result,
            workflow_assignment=self.mock_workflow_assignment
        )
        
        # Test to_dict
        event_dict = event.to_dict()
        assert isinstance(event_dict, dict)
        assert 'event_id' in event_dict
        assert 'correlation_id' in event_dict
        assert 'email_metadata' in event_dict
        
        # Test to_json
        event_json = event.to_json()
        assert isinstance(event_json, str)
        
        # Verify JSON is valid
        parsed_json = json.loads(event_json)
        assert parsed_json['event_id'] == event.event_id


class TestUtilityFunctions:
    """Test utility functions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.sample_event_data = {
            "event_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "NEW_EO",
            "schema_version": "1.0",
            "priority": "HIGH",
            "confidence_score": 0.95,
            "email_metadata": {
                "uid": "test-uid-123",
                "message_id": "<test@example.com>",
                "sender": "sender@dol.gov",
                "recipients": ["recipient@dol.gov"],
                "subject": "Test Executive Order",
                "received_date": datetime.now(timezone.utc).isoformat()
            },
            "content": {
                "body_text": "Test content",
                "attachments": []
            },
            "security": {
                "sender_authorized": True,
                "content_safe": True,
                "attachments_safe": True
            },
            "workflow": {
                "assigned_queue": "eo_processing_queue",
                "workflow_type": "EXECUTIVE_ORDER_PROCESSING"
            }
        }
    
    def test_validate_event_compatibility(self):
        """Test event compatibility validation utility"""
        compatible_versions = validate_event_compatibility(self.sample_event_data)
        
        assert isinstance(compatible_versions, list)
        assert len(compatible_versions) >= 1
        assert '1.0' in compatible_versions
    
    def test_migrate_event_to_latest(self):
        """Test event migration to latest version utility"""
        migrated = migrate_event_to_latest(self.sample_event_data)
        
        assert migrated['schema_version'] == '2.0'
        assert 'size_bytes' in migrated['email_metadata']
        assert 'body_text_preview' in migrated['content']
    
    @patch('src.email.event_schema.StandardizedEventBuilder')
    def test_create_event_from_email_processing(self, mock_builder_class):
        """Test convenience function for creating events"""
        mock_builder = Mock()
        mock_event = Mock()
        mock_builder.build_email_event.return_value = mock_event
        mock_builder_class.return_value = mock_builder
        
        # Create mock inputs
        mock_extracted_content = Mock()
        mock_classification = Mock()
        mock_security_result = Mock()
        mock_workflow_assignment = Mock()
        
        result = create_event_from_email_processing(
            extracted_content=mock_extracted_content,
            classification=mock_classification,
            security_result=mock_security_result,
            workflow_assignment=mock_workflow_assignment
        )
        
        assert result == mock_event
        mock_builder.build_email_event.assert_called_once_with(
            extracted_content=mock_extracted_content,
            classification=mock_classification,
            security_result=mock_security_result,
            workflow_assignment=mock_workflow_assignment,
            correlation_id=None
        )


class TestBackwardCompatibility:
    """Test backward compatibility features"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = EventSchemaValidator()
    
    def test_v1_0_event_compatibility(self):
        """Test that v1.0 events remain compatible"""
        v1_0_event = {
            "event_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "NEW_EO",
            "schema_version": "1.0",
            "priority": "HIGH",
            "confidence_score": 0.95,
            "email_metadata": {
                "uid": "test-uid",
                "message_id": "<test@example.com>",
                "sender": "sender@dol.gov",
                "recipients": ["recipient@dol.gov"],
                "subject": "Test",
                "received_date": datetime.now(timezone.utc).isoformat()
            },
            "content": {
                "body_text": "Test content",
                "attachments": []
            },
            "security": {
                "sender_authorized": True,
                "content_safe": True,
                "attachments_safe": True
            },
            "workflow": {
                "assigned_queue": "test_queue",
                "workflow_type": "TEST_WORKFLOW"
            }
        }
        
        # Should validate against v1.0 schema
        is_valid, error = self.validator.validate_event(v1_0_event, EventSchemaVersion.V1_0)
        assert is_valid is True
        assert error is None
    
    def test_migration_preserves_data(self):
        """Test that migration preserves original data"""
        original_event = {
            "event_id": "test-event-id",
            "correlation_id": "test-correlation-id",
            "timestamp": "2024-01-01T00:00:00Z",
            "event_type": "NEW_EO",
            "schema_version": "1.0",
            "priority": "HIGH",
            "confidence_score": 0.95,
            "email_metadata": {
                "uid": "test-uid",
                "message_id": "<test@example.com>",
                "sender": "sender@dol.gov",
                "recipients": ["recipient@dol.gov"],
                "subject": "Test Subject",
                "received_date": "2024-01-01T00:00:00Z"
            },
            "content": {
                "body_text": "Original content",
                "attachments": [{"filename": "test.pdf"}]
            },
            "security": {
                "sender_authorized": True,
                "content_safe": True,
                "attachments_safe": True
            },
            "workflow": {
                "assigned_queue": "test_queue",
                "workflow_type": "TEST_WORKFLOW"
            }
        }
        
        migrated = self.validator.migrate_event_schema(
            original_event,
            EventSchemaVersion.V1_0,
            EventSchemaVersion.V2_0
        )
        
        # Check that original data is preserved
        assert migrated['event_id'] == original_event['event_id']
        assert migrated['correlation_id'] == original_event['correlation_id']
        assert migrated['timestamp'] == original_event['timestamp']
        assert migrated['event_type'] == original_event['event_type']
        assert migrated['priority'] == original_event['priority']
        assert migrated['confidence_score'] == original_event['confidence_score']
        
        # Check that nested data is preserved
        assert migrated['email_metadata']['sender'] == original_event['email_metadata']['sender']
        assert migrated['content']['body_text'] == original_event['content']['body_text']
        assert migrated['security']['sender_authorized'] == original_event['security']['sender_authorized']
        assert migrated['workflow']['assigned_queue'] == original_event['workflow']['assigned_queue']
        
        # Check that new fields are added with defaults
        assert migrated['schema_version'] == '2.0'
        assert 'size_bytes' in migrated['email_metadata']
        assert 'body_text_preview' in migrated['content']
    
    def test_multiple_version_support(self):
        """Test that multiple schema versions are supported simultaneously"""
        # Create events for different versions
        base_event = {
            "event_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "NEW_EO",
            "priority": "HIGH",
            "confidence_score": 0.95,
            "email_metadata": {
                "uid": "test-uid",
                "message_id": "<test@example.com>",
                "sender": "sender@dol.gov",
                "recipients": ["recipient@dol.gov"],
                "subject": "Test",
                "received_date": datetime.now(timezone.utc).isoformat(),
                "content_hash": "hash123",
                "size_bytes": 1024
            },
            "content": {
                "body_text": "Test content",
                "body_text_preview": "Test content",
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
                "assigned_queue": "test_queue",
                "workflow_type": "TEST_WORKFLOW",
                "priority_level": "HIGH",
                "processing_requirements": {},
                "estimated_processing_time": 120.0,
                "escalation_required": False
            },
            "processing_metadata": {}
        }
        
        # Test v1.0
        v1_0_event = base_event.copy()
        v1_0_event['schema_version'] = '1.0'
        is_valid_v1_0, _ = self.validator.validate_event(v1_0_event, EventSchemaVersion.V1_0)
        
        # Test v1.1
        v1_1_event = base_event.copy()
        v1_1_event['schema_version'] = '1.1'
        is_valid_v1_1, _ = self.validator.validate_event(v1_1_event, EventSchemaVersion.V1_1)
        
        # Test v2.0
        v2_0_event = base_event.copy()
        v2_0_event['schema_version'] = '2.0'
        is_valid_v2_0, _ = self.validator.validate_event(v2_0_event, EventSchemaVersion.V2_0)
        
        # All should be valid for their respective versions
        assert is_valid_v1_0 is True
        assert is_valid_v1_1 is True
        assert is_valid_v2_0 is True


if __name__ == '__main__':
    pytest.main([__file__])