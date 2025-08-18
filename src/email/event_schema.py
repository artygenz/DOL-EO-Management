"""
Standardized Event Schema and Builder for Email Agent

This module implements the standardized JSON event schema with all required fields,
event builder with correlation ID generation and security metadata, event schema
validation and version compatibility checking, and backward compatibility for
at least 2 schema versions.

Implements requirements:
- 3.1: Standardized JSON event with defined schema including correlation ID, timestamp, email metadata, and classification confidence score
- 3.6: Include correlation IDs for end-to-end workflow tracking
- 3.7: Maintain backward compatibility for at least 2 schema versions
"""

import logging
import uuid
import json
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import jsonschema
from jsonschema import validate, ValidationError

# Import types for type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .content_extractor import ExtractedContent, EmailHeaders, ValidatedAttachment, ThreadAnalysis
    from .email_classifier import ClassificationResult, EmailType
    from .workflow_router import WorkflowAssignment, PriorityLevel, WorkflowType, QueueName
    from .security_validator import SecurityValidationResult

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for email processing"""
    NEW_EO = "NEW_EO"
    PMO_RESPONSE = "PMO_RESPONSE"
    DEVELOPER_UPDATE = "DEVELOPER_UPDATE"
    EXECUTIVE_REQUEST = "EXECUTIVE_REQUEST"


class EventPriority(Enum):
    """Event priority levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class EventEmailMetadata:
    """Email metadata for standardized events"""
    uid: str
    message_id: str
    sender: str
    sender_name: Optional[str]
    recipients: List[str]
    subject: str
    received_date: str  # ISO8601 format
    thread_id: Optional[str]
    content_hash: str
    size_bytes: int


@dataclass
class EventContent:
    """Event content structure"""
    body_text: str
    body_text_preview: str  # First 500 chars for preview
    has_html_content: bool
    attachments: List[Dict[str, Any]]
    classification_features: Dict[str, Any]
    thread_analysis: Dict[str, Any]


@dataclass
class EventSecurity:
    """Event security metadata"""
    sender_authorized: bool
    content_safe: bool
    attachments_safe: bool
    security_scan_timestamp: str  # ISO8601 format
    threat_indicators: List[str]
    compliance_flags: List[str]


@dataclass
class EventWorkflow:
    """Event workflow assignment"""
    assigned_queue: str
    workflow_type: str
    priority_level: str
    processing_requirements: Dict[str, Any]
    estimated_processing_time: float
    escalation_required: bool


@dataclass
class StandardizedEvent:
    """Complete standardized event structure"""
    # Core event fields
    event_id: str
    correlation_id: str
    timestamp: str  # ISO8601 format
    event_type: str
    schema_version: str
    
    # Priority and confidence
    priority: str
    confidence_score: float
    
    # Email data
    email_metadata: EventEmailMetadata
    content: EventContent
    security: EventSecurity
    workflow: EventWorkflow
    
    # Processing metadata
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class EventSchemaVersion(Enum):
    """Supported event schema versions"""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"  # Current version


class EventSchemaValidator:
    """Event schema validation with version compatibility"""
    
    # Schema definitions for different versions
    SCHEMAS = {
        EventSchemaVersion.V1_0: {
            "type": "object",
            "required": [
                "event_id", "correlation_id", "timestamp", "event_type",
                "schema_version", "priority", "confidence_score",
                "email_metadata", "content", "security", "workflow"
            ],
            "properties": {
                "event_id": {"type": "string", "format": "uuid"},
                "correlation_id": {"type": "string", "format": "uuid"},
                "timestamp": {"type": "string", "format": "date-time"},
                "event_type": {"type": "string", "enum": ["NEW_EO", "PMO_RESPONSE", "DEVELOPER_UPDATE", "EXECUTIVE_REQUEST"]},
                "schema_version": {"type": "string", "pattern": "^1\\.0$"},
                "priority": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "email_metadata": {
                    "type": "object",
                    "required": ["uid", "message_id", "sender", "subject", "received_date"],
                    "properties": {
                        "uid": {"type": "string"},
                        "message_id": {"type": "string"},
                        "sender": {"type": "string", "format": "email"},
                        "sender_name": {"type": ["string", "null"]},
                        "recipients": {"type": "array", "items": {"type": "string", "format": "email"}},
                        "subject": {"type": "string"},
                        "received_date": {"type": "string", "format": "date-time"},
                        "thread_id": {"type": ["string", "null"]},
                        "content_hash": {"type": "string"},
                        "size_bytes": {"type": "integer", "minimum": 0}
                    }
                },
                "content": {
                    "type": "object",
                    "required": ["body_text", "attachments"],
                    "properties": {
                        "body_text": {"type": "string"},
                        "body_text_preview": {"type": "string"},
                        "has_html_content": {"type": "boolean"},
                        "attachments": {"type": "array", "items": {"type": "object"}},
                        "classification_features": {"type": "object"}
                    }
                },
                "security": {
                    "type": "object",
                    "required": ["sender_authorized", "content_safe", "attachments_safe"],
                    "properties": {
                        "sender_authorized": {"type": "boolean"},
                        "content_safe": {"type": "boolean"},
                        "attachments_safe": {"type": "boolean"},
                        "security_scan_timestamp": {"type": "string", "format": "date-time"},
                        "threat_indicators": {"type": "array", "items": {"type": "string"}},
                        "compliance_flags": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "workflow": {
                    "type": "object",
                    "required": ["assigned_queue", "workflow_type"],
                    "properties": {
                        "assigned_queue": {"type": "string"},
                        "workflow_type": {"type": "string"},
                        "priority_level": {"type": "string"},
                        "processing_requirements": {"type": "object"},
                        "estimated_processing_time": {"type": "number", "minimum": 0},
                        "escalation_required": {"type": "boolean"}
                    }
                },
                "processing_metadata": {"type": "object"}
            }
        }
    }
    
    def __init__(self):
        """Initialize schema validator"""
        # Generate v1.1 schema (extends v1.0 with additional optional fields)
        self.SCHEMAS[EventSchemaVersion.V1_1] = self._create_v1_1_schema()
        
        # Generate v2.0 schema (current version with enhanced features)
        self.SCHEMAS[EventSchemaVersion.V2_0] = self._create_v2_0_schema()
        
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'version_compatibility_checks': 0,
            'schema_migrations': 0
        }
        
        logger.info("Event schema validator initialized with versions: " + 
                   ", ".join([v.value for v in EventSchemaVersion]))
    
    def validate_event(self, event_data: Dict[str, Any], 
                      target_version: EventSchemaVersion = EventSchemaVersion.V2_0) -> Tuple[bool, Optional[str]]:
        """
        Validate event against schema version
        
        Args:
            event_data: Event data to validate
            target_version: Target schema version
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self.validation_stats['total_validations'] += 1
            
            schema = self.SCHEMAS.get(target_version)
            if not schema:
                error_msg = f"Unsupported schema version: {target_version.value}"
                logger.error(error_msg)
                self.validation_stats['failed_validations'] += 1
                return False, error_msg
            
            # Validate against schema
            validate(instance=event_data, schema=schema)
            
            self.validation_stats['successful_validations'] += 1
            logger.debug(f"Event validation successful for schema version {target_version.value}")
            return True, None
            
        except ValidationError as e:
            error_msg = f"Schema validation failed: {e.message}"
            logger.warning(f"Event validation failed: {error_msg}")
            self.validation_stats['failed_validations'] += 1
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(f"Event validation error: {error_msg}")
            self.validation_stats['failed_validations'] += 1
            return False, error_msg
    
    def check_version_compatibility(self, event_data: Dict[str, Any]) -> List[EventSchemaVersion]:
        """
        Check which schema versions the event is compatible with
        
        Args:
            event_data: Event data to check
            
        Returns:
            List of compatible schema versions
        """
        self.validation_stats['version_compatibility_checks'] += 1
        compatible_versions = []
        
        for version in EventSchemaVersion:
            is_valid, _ = self.validate_event(event_data, version)
            if is_valid:
                compatible_versions.append(version)
        
        logger.debug(f"Event compatible with versions: {[v.value for v in compatible_versions]}")
        return compatible_versions
    
    def migrate_event_schema(self, event_data: Dict[str, Any], 
                           from_version: EventSchemaVersion,
                           to_version: EventSchemaVersion) -> Dict[str, Any]:
        """
        Migrate event from one schema version to another
        
        Args:
            event_data: Event data to migrate
            from_version: Source schema version
            to_version: Target schema version
            
        Returns:
            Migrated event data
        """
        try:
            self.validation_stats['schema_migrations'] += 1
            
            if from_version == to_version:
                return event_data.copy()
            
            migrated_data = event_data.copy()
            
            # Migration logic for different version combinations
            if from_version == EventSchemaVersion.V1_0 and to_version == EventSchemaVersion.V1_1:
                migrated_data = self._migrate_v1_0_to_v1_1(migrated_data)
            elif from_version == EventSchemaVersion.V1_1 and to_version == EventSchemaVersion.V2_0:
                migrated_data = self._migrate_v1_1_to_v2_0(migrated_data)
            elif from_version == EventSchemaVersion.V1_0 and to_version == EventSchemaVersion.V2_0:
                # Two-step migration
                migrated_data = self._migrate_v1_0_to_v1_1(migrated_data)
                migrated_data = self._migrate_v1_1_to_v2_0(migrated_data)
            else:
                logger.warning(f"No migration path from {from_version.value} to {to_version.value}")
                return migrated_data
            
            # Update schema version
            migrated_data['schema_version'] = to_version.value
            
            logger.info(f"Successfully migrated event from {from_version.value} to {to_version.value}")
            return migrated_data
            
        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            return event_data  # Return original on failure
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return self.validation_stats.copy()
    
    # Private helper methods for schema creation and migration
    
    def _create_v1_1_schema(self) -> Dict[str, Any]:
        """Create v1.1 schema (extends v1.0 with optional fields)"""
        import copy
        schema = copy.deepcopy(self.SCHEMAS[EventSchemaVersion.V1_0])
        schema['properties']['schema_version']['pattern'] = "^1\\.1$"
        
        # Add optional fields to v1.1
        schema['properties']['content']['properties']['thread_analysis'] = {"type": "object"}
        
        # Ensure processing_metadata has properties
        if 'properties' not in schema['properties']['processing_metadata']:
            schema['properties']['processing_metadata']['properties'] = {}
        
        schema['properties']['processing_metadata']['properties']['extraction_duration_ms'] = {"type": "number"}
        schema['properties']['processing_metadata']['properties']['classification_method'] = {"type": "string"}
        
        return schema
    
    def _create_v2_0_schema(self) -> Dict[str, Any]:
        """Create v2.0 schema (current version with enhanced features)"""
        import copy
        schema = copy.deepcopy(self.SCHEMAS[EventSchemaVersion.V1_1])
        schema['properties']['schema_version']['pattern'] = "^2\\.0$"
        
        # Enhanced fields in v2.0
        schema['properties']['email_metadata']['properties']['size_bytes'] = {"type": "integer", "minimum": 0}
        schema['properties']['content']['required'].append('body_text_preview')
        schema['properties']['content']['required'].append('has_html_content')
        schema['properties']['content']['required'].append('thread_analysis')
        
        # Enhanced security fields
        schema['properties']['security']['properties']['threat_indicators'] = {
            "type": "array", 
            "items": {"type": "string"}
        }
        schema['properties']['security']['properties']['compliance_flags'] = {
            "type": "array", 
            "items": {"type": "string"}
        }
        
        # Enhanced workflow fields
        schema['properties']['workflow']['required'].extend([
            'priority_level', 'estimated_processing_time', 'escalation_required'
        ])
        
        return schema
    
    def _migrate_v1_0_to_v1_1(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate event from v1.0 to v1.1"""
        migrated = event_data.copy()
        
        # Add optional fields with defaults
        if 'thread_analysis' not in migrated.get('content', {}):
            migrated.setdefault('content', {})['thread_analysis'] = {}
        
        if 'processing_metadata' not in migrated:
            migrated['processing_metadata'] = {}
        
        migrated['processing_metadata'].setdefault('extraction_duration_ms', 0.0)
        migrated['processing_metadata'].setdefault('classification_method', 'unknown')
        
        return migrated
    
    def _migrate_v1_1_to_v2_0(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate event from v1.1 to v2.0"""
        migrated = event_data.copy()
        
        # Add required fields for v2.0
        email_metadata = migrated.setdefault('email_metadata', {})
        email_metadata.setdefault('size_bytes', 0)
        
        content = migrated.setdefault('content', {})
        content.setdefault('body_text_preview', content.get('body_text', '')[:500])
        content.setdefault('has_html_content', False)
        content.setdefault('thread_analysis', {})
        
        security = migrated.setdefault('security', {})
        security.setdefault('threat_indicators', [])
        security.setdefault('compliance_flags', [])
        
        workflow = migrated.setdefault('workflow', {})
        workflow.setdefault('priority_level', 'MEDIUM')
        workflow.setdefault('estimated_processing_time', 120.0)
        workflow.setdefault('escalation_required', False)
        
        return migrated


class StandardizedEventBuilder:
    """
    Builder for creating standardized events with correlation ID generation
    and security metadata
    """
    
    def __init__(self, schema_validator: Optional[EventSchemaValidator] = None):
        """
        Initialize event builder
        
        Args:
            schema_validator: Optional schema validator instance
        """
        self.schema_validator = schema_validator or EventSchemaValidator()
        self.build_stats = {
            'total_events_built': 0,
            'successful_builds': 0,
            'failed_builds': 0,
            'correlation_ids_generated': 0
        }
        
        logger.info("Standardized event builder initialized")
    
    def build_email_event(self, 
                         extracted_content: 'ExtractedContent',
                         classification: 'ClassificationResult',
                         security_result: 'SecurityValidationResult',
                         workflow_assignment: 'WorkflowAssignment',
                         correlation_id: Optional[str] = None) -> StandardizedEvent:
        """
        Build standardized event from email processing components
        
        Args:
            extracted_content: Extracted email content
            classification: Email classification result
            security_result: Security validation result
            workflow_assignment: Workflow assignment
            correlation_id: Optional correlation ID (generated if not provided)
            
        Returns:
            StandardizedEvent instance
        """
        try:
            self.build_stats['total_events_built'] += 1
            build_start = datetime.now(timezone.utc)
            
            # Generate IDs
            event_id = str(uuid.uuid4())
            if not correlation_id:
                correlation_id = self.generate_correlation_id(extracted_content.headers.message_id)
                self.build_stats['correlation_ids_generated'] += 1
            
            # Build email metadata
            email_metadata = self._build_email_metadata(extracted_content)
            
            # Build content
            content = self._build_event_content(extracted_content, classification)
            
            # Build security metadata
            security = self._build_security_metadata(security_result)
            
            # Build workflow metadata
            workflow = self._build_workflow_metadata(workflow_assignment)
            
            # Build processing metadata
            processing_metadata = self._build_processing_metadata(
                extracted_content, classification, build_start
            )
            
            # Create standardized event
            event = StandardizedEvent(
                event_id=event_id,
                correlation_id=correlation_id,
                timestamp=build_start.isoformat(),
                event_type=self._map_email_type_to_event_type(classification.email_type),
                schema_version=EventSchemaVersion.V2_0.value,
                priority=self._map_priority_level(workflow_assignment.priority_level),
                confidence_score=classification.confidence_score,
                email_metadata=email_metadata,
                content=content,
                security=security,
                workflow=workflow,
                processing_metadata=processing_metadata
            )
            
            self.build_stats['successful_builds'] += 1
            logger.info(f"Successfully built standardized event {event_id} for email {extracted_content.headers.message_id}")
            
            return event
            
        except Exception as e:
            self.build_stats['failed_builds'] += 1
            logger.error(f"Failed to build standardized event: {e}")
            raise EventBuildError(f"Failed to build standardized event: {e}") from e
    
    def generate_correlation_id(self, message_id: str, context: Optional[str] = None) -> str:
        """
        Generate correlation ID for end-to-end workflow tracking
        
        Args:
            message_id: Email message ID
            context: Optional context for correlation
            
        Returns:
            Generated correlation ID
        """
        # Create deterministic correlation ID based on message ID and timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        correlation_data = f"{message_id}:{timestamp}"
        
        if context:
            correlation_data += f":{context}"
        
        # Generate UUID5 for deterministic but unique correlation ID
        correlation_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, correlation_data))
        
        logger.debug(f"Generated correlation ID {correlation_id} for message {message_id}")
        return correlation_id
    
    def validate_event_schema(self, event: StandardizedEvent, 
                            target_version: EventSchemaVersion = EventSchemaVersion.V2_0) -> Tuple[bool, Optional[str]]:
        """
        Validate event against schema
        
        Args:
            event: Event to validate
            target_version: Target schema version
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.schema_validator.validate_event(event.to_dict(), target_version)
    
    def add_security_metadata(self, event: StandardizedEvent, 
                            additional_security: Dict[str, Any]) -> StandardizedEvent:
        """
        Add additional security metadata to event
        
        Args:
            event: Event to enhance
            additional_security: Additional security metadata
            
        Returns:
            Enhanced event
        """
        try:
            # Update security metadata
            if 'threat_indicators' in additional_security:
                event.security.threat_indicators.extend(additional_security['threat_indicators'])
            
            if 'compliance_flags' in additional_security:
                event.security.compliance_flags.extend(additional_security['compliance_flags'])
            
            # Update processing metadata
            event.processing_metadata['security_enhancement_timestamp'] = datetime.now(timezone.utc).isoformat()
            event.processing_metadata['additional_security_checks'] = list(additional_security.keys())
            
            logger.debug(f"Added security metadata to event {event.event_id}")
            return event
            
        except Exception as e:
            logger.error(f"Failed to add security metadata: {e}")
            return event  # Return original event on failure
    
    def get_build_statistics(self) -> Dict[str, Any]:
        """Get event building statistics"""
        return self.build_stats.copy()
    
    # Private helper methods
    
    def _build_email_metadata(self, extracted_content: 'ExtractedContent') -> EventEmailMetadata:
        """Build email metadata from extracted content"""
        headers = extracted_content.headers
        
        return EventEmailMetadata(
            uid=headers.message_id,  # Using message_id as UID for now
            message_id=headers.message_id,
            sender=headers.sender,
            sender_name=headers.sender_name,
            recipients=headers.recipients,
            subject=headers.subject,
            received_date=headers.date.isoformat(),
            thread_id=extracted_content.thread_analysis.thread_id,
            content_hash=extracted_content.content_hash,
            size_bytes=len(extracted_content.plain_text.encode('utf-8'))
        )
    
    def _build_event_content(self, extracted_content: 'ExtractedContent', 
                           classification: 'ClassificationResult') -> EventContent:
        """Build event content from extracted content and classification"""
        # Create attachment summaries
        attachments = []
        for att in extracted_content.attachments:
            attachments.append({
                'filename': att.filename,
                'content_type': att.content_type,
                'size_bytes': att.size_bytes,
                'is_safe': att.is_safe,
                'content_hash': att.content_hash
            })
        
        # Create thread analysis summary
        thread_analysis = {
            'thread_id': extracted_content.thread_analysis.thread_id,
            'is_reply': extracted_content.thread_analysis.is_reply,
            'is_forward': extracted_content.thread_analysis.is_forward,
            'thread_depth': extracted_content.thread_analysis.thread_depth,
            'participants_count': len(extracted_content.thread_analysis.conversation_participants)
        }
        
        return EventContent(
            body_text=extracted_content.plain_text,
            body_text_preview=extracted_content.plain_text[:500],
            has_html_content=extracted_content.html_content is not None,
            attachments=attachments,
            classification_features=classification.feature_importance,
            thread_analysis=thread_analysis
        )
    
    def _build_security_metadata(self, security_result: 'SecurityValidationResult') -> EventSecurity:
        """Build security metadata from security validation result"""
        return EventSecurity(
            sender_authorized=security_result.sender_authorized,
            content_safe=security_result.content_safe,
            attachments_safe=security_result.attachments_safe,
            security_scan_timestamp=security_result.validation_timestamp.isoformat(),
            threat_indicators=security_result.threat_indicators,
            compliance_flags=security_result.compliance_flags
        )
    
    def _build_workflow_metadata(self, workflow_assignment: 'WorkflowAssignment') -> EventWorkflow:
        """Build workflow metadata from workflow assignment"""
        return EventWorkflow(
            assigned_queue=workflow_assignment.assigned_queue.value,
            workflow_type=workflow_assignment.workflow_type.value,
            priority_level=workflow_assignment.priority_level.value,
            processing_requirements=workflow_assignment.processing_requirements,
            estimated_processing_time=workflow_assignment.estimated_processing_time,
            escalation_required=workflow_assignment.escalation_required
        )
    
    def _build_processing_metadata(self, extracted_content: 'ExtractedContent',
                                 classification: 'ClassificationResult',
                                 build_start: datetime) -> Dict[str, Any]:
        """Build processing metadata"""
        build_duration = (datetime.now(timezone.utc) - build_start).total_seconds() * 1000
        
        return {
            'event_build_timestamp': build_start.isoformat(),
            'event_build_duration_ms': build_duration,
            'builder_version': '1.0.0',
            'extraction_timestamp': extracted_content.extraction_metadata.get('extraction_timestamp', '').isoformat() if hasattr(extracted_content.extraction_metadata.get('extraction_timestamp', ''), 'isoformat') else str(extracted_content.extraction_metadata.get('extraction_timestamp', '')),
            'classification_timestamp': classification.classification_timestamp.isoformat(),
            'classification_method': classification.classification_metadata.get('classification_method', 'unknown'),
            'requires_manual_review': classification.requires_manual_review,
            'alternative_classifications_count': len(classification.alternative_classifications)
        }
    
    def _map_email_type_to_event_type(self, email_type: 'EmailType') -> str:
        """Map email type to event type string"""
        # Import here to avoid circular imports
        from .email_classifier import EmailType
        
        mapping = {
            EmailType.NEW_EO: EventType.NEW_EO.value,
            EmailType.PMO_RESPONSE: EventType.PMO_RESPONSE.value,
            EmailType.DEVELOPER_UPDATE: EventType.DEVELOPER_UPDATE.value,
            EmailType.EXECUTIVE_REQUEST: EventType.EXECUTIVE_REQUEST.value
        }
        
        return mapping.get(email_type, EventType.DEVELOPER_UPDATE.value)
    
    def _map_priority_level(self, priority_level: 'PriorityLevel') -> str:
        """Map priority level to event priority string"""
        # Import here to avoid circular imports
        from .workflow_router import PriorityLevel
        
        mapping = {
            PriorityLevel.CRITICAL: EventPriority.CRITICAL.value,
            PriorityLevel.HIGH: EventPriority.HIGH.value,
            PriorityLevel.MEDIUM: EventPriority.MEDIUM.value,
            PriorityLevel.LOW: EventPriority.LOW.value
        }
        
        return mapping.get(priority_level, EventPriority.MEDIUM.value)


class EventBuildError(Exception):
    """Event building specific errors"""
    pass


# Utility functions for event handling

def create_event_from_email_processing(extracted_content: 'ExtractedContent',
                                     classification: 'ClassificationResult',
                                     security_result: 'SecurityValidationResult',
                                     workflow_assignment: 'WorkflowAssignment',
                                     correlation_id: Optional[str] = None) -> StandardizedEvent:
    """
    Convenience function to create standardized event from email processing components
    
    Args:
        extracted_content: Extracted email content
        classification: Email classification result
        security_result: Security validation result
        workflow_assignment: Workflow assignment
        correlation_id: Optional correlation ID
        
    Returns:
        StandardizedEvent instance
    """
    builder = StandardizedEventBuilder()
    return builder.build_email_event(
        extracted_content=extracted_content,
        classification=classification,
        security_result=security_result,
        workflow_assignment=workflow_assignment,
        correlation_id=correlation_id
    )


def validate_event_compatibility(event_data: Dict[str, Any]) -> List[str]:
    """
    Check event compatibility with all supported schema versions
    
    Args:
        event_data: Event data to check
        
    Returns:
        List of compatible schema version strings
    """
    validator = EventSchemaValidator()
    compatible_versions = validator.check_version_compatibility(event_data)
    return [version.value for version in compatible_versions]


def migrate_event_to_latest(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate event to latest schema version
    
    Args:
        event_data: Event data to migrate
        
    Returns:
        Migrated event data
    """
    validator = EventSchemaValidator()
    current_version = event_data.get('schema_version', '1.0')
    
    # Determine current version enum
    version_mapping = {v.value: v for v in EventSchemaVersion}
    from_version = version_mapping.get(current_version, EventSchemaVersion.V1_0)
    
    return validator.migrate_event_schema(
        event_data=event_data,
        from_version=from_version,
        to_version=EventSchemaVersion.V2_0
    )