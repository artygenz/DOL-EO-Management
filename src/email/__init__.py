"""
Email processing module for the Email Agent system.

This module provides comprehensive email processing capabilities including
connection management, real-time detection, security validation, and
intelligent polling for government-grade email systems.
"""

from .client import EmailClient
from .godaddy_client import GoDaddyEmailClient
from .enhanced_godaddy_client import EnhancedGoDaddyEmailClient
from .connection_pool import ConnectionPoolManager
from .reconnection_manager import IntelligentReconnectionManager as ReconnectionManager
from .idle_controller import IMAPIdleController
from .smart_polling_engine import SmartPollingEngine
from .uid_tracker import UIDTracker
from .redis_client import RedisClient
from .security_validator import (
    EmailSecurityValidator,
    SecurityValidatorFactory,
    SecurityValidationResult,
    AttachmentScanResult,
    ContentAnalysisResult,
    DigitalSignatureResult
)
from .content_extractor import (
    EnhancedContentExtractor,
    EmailHeaders,
    ThreadAnalysis,
    ValidatedAttachment,
    ExtractedContent,
    ContentExtractionError,
    AttachmentSecurityError
)

__all__ = [
    # Core email clients
    'EmailClient',
    'GoDaddyEmailClient', 
    'EnhancedGoDaddyEmailClient',
    
    # Connection management
    'ConnectionPoolManager',
    'ReconnectionManager',
    
    # Email detection and monitoring
    'IMAPIdleController',
    'SmartPollingEngine',
    'UIDTracker',
    'RedisClient',
    
    # Security validation
    'EmailSecurityValidator',
    'SecurityValidatorFactory',
    'SecurityValidationResult',
    'AttachmentScanResult',
    'ContentAnalysisResult',
    'DigitalSignatureResult',
    
    # Content extraction
    'EnhancedContentExtractor',
    'EmailHeaders',
    'ThreadAnalysis',
    'ValidatedAttachment',
    'ExtractedContent',
    'ContentExtractionError',
    'AttachmentSecurityError'
]