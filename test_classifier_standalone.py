#!/usr/bin/env python3
"""
Standalone test for email classifier functionality
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set
try:
    import numpy as np
except ImportError:
    # Mock numpy for basic functionality
    class MockNumpy:
        def array(self, data):
            return data
    np = MockNumpy()

# Mock the dependencies for testing
@dataclass
class EmailHeaders:
    message_id: str
    sender: str
    sender_name: Optional[str]
    recipients: List[str]
    cc_recipients: List[str]
    bcc_recipients: List[str]
    subject: str
    date: datetime
    reply_to: Optional[str]
    in_reply_to: Optional[str]
    references: List[str]
    thread_topic: Optional[str]
    priority: Optional[str]
    content_type: str
    encoding: Optional[str]
    custom_headers: Dict[str, str]

@dataclass
class ValidatedAttachment:
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    content_hash: str
    is_safe: bool
    security_scan_result: Optional[str]
    temporary_path: Optional[str]
    extraction_timestamp: datetime
    expires_at: datetime
    metadata: Dict[str, Any]

@dataclass
class ThreadAnalysis:
    thread_id: str
    is_reply: bool
    is_forward: bool
    parent_message_id: Optional[str]
    thread_depth: int
    conversation_participants: Set[str]
    thread_subject: str
    original_subject: str
    reply_chain_length: int

@dataclass
class ExtractedContent:
    headers: EmailHeaders
    plain_text: str
    html_content: Optional[str]
    sanitized_html: Optional[str]
    attachments: List[ValidatedAttachment]
    thread_analysis: ThreadAnalysis
    content_hash: str
    extraction_metadata: Dict[str, Any]
    security_flags: List[str]

@dataclass
class SecurityValidationResult:
    is_valid: bool
    sender_authorized: bool
    content_safe: bool
    attachments_safe: bool
    digital_signature_valid: bool
    threat_level: str
    security_issues: List[str]
    quarantine_required: bool
    validation_timestamp: datetime

# Now import the core classifier logic
class EmailType(Enum):
    """Email classification types for government workflow processing"""
    NEW_EO = "NEW_EO"
    PMO_RESPONSE = "PMO_RESPONSE"
    DEVELOPER_UPDATE = "DEVELOPER_UPDATE"
    EXECUTIVE_REQUEST = "EXECUTIVE_REQUEST"

@dataclass
class EmailFeatures:
    """Extracted features for email classification"""
    # Sender features
    sender_domain: str
    sender_is_government: bool
    sender_role_indicators: List[str]
    
    # Subject features
    subject_keywords: List[str]
    subject_length: int
    subject_urgency_indicators: int
    subject_reply_indicators: int
    
    # Content features
    content_length: int
    content_keywords: List[str]
    content_sentiment_score: float
    content_formality_score: float
    content_technical_terms: int
    
    # Attachment features
    attachment_count: int
    attachment_types: List[str]
    has_pdf_attachments: bool
    has_office_attachments: bool
    
    # Thread features
    is_reply: bool
    thread_depth: int
    conversation_participants_count: int
    
    # Security features
    sender_authorized: bool
    content_safe: bool
    attachments_safe: bool
    
    # Temporal features
    sent_hour: int
    sent_day_of_week: int
    is_business_hours: bool

@dataclass
class ClassificationResult:
    """Result of email classification with confidence scoring"""
    email_type: EmailType
    confidence_score: float
    feature_importance: Dict[str, float]
    classification_metadata: Dict[str, Any]
    requires_manual_review: bool
    alternative_classifications: List[Tuple[EmailType, float]]
    classification_timestamp: datetime

class SimpleEmailClassifier:
    """Simplified email classifier for testing"""
    
    # Email type specific keywords and patterns
    EMAIL_TYPE_PATTERNS = {
        EmailType.NEW_EO: {
            'subject_keywords': [
                'executive order', 'eo', 'presidential directive', 'new directive',
                'policy directive', 'federal directive', 'implementation guidance'
            ],
            'content_keywords': [
                'executive order', 'presidential', 'directive', 'federal agencies',
                'implementation', 'compliance', 'effective date', 'requirements'
            ],
            'sender_patterns': ['whitehouse.gov', 'omb.gov', 'gsa.gov'],
            'attachment_patterns': ['pdf', 'executive_order', 'directive']
        },
        EmailType.PMO_RESPONSE: {
            'subject_keywords': [
                'approval', 'approved', 'rejected', 'review', 'status update',
                'milestone', 'deliverable', 'budget', 'timeline', 'resource'
            ],
            'content_keywords': [
                'project', 'milestone', 'deliverable', 'budget', 'timeline',
                'resource', 'risk', 'issue', 'approval', 'status', 'progress'
            ],
            'sender_patterns': ['pmo', 'project', 'program'],
            'attachment_patterns': ['xlsx', 'pptx', 'docx', 'project', 'status']
        },
        EmailType.DEVELOPER_UPDATE: {
            'subject_keywords': [
                'development update', 'progress update', 'code review',
                'deployment', 'release', 'bug fix', 'feature complete'
            ],
            'content_keywords': [
                'development', 'code', 'programming', 'bug', 'fix', 'feature',
                'implementation', 'testing', 'deployment', 'release', 'commit'
            ],
            'sender_patterns': ['developer', 'engineer', 'tech', 'dev'],
            'attachment_patterns': ['zip', 'tar', 'log', 'code', 'patch']
        },
        EmailType.EXECUTIVE_REQUEST: {
            'subject_keywords': [
                'executive request', 'urgent request', 'director request',
                'secretary request', 'briefing request', 'report request'
            ],
            'content_keywords': [
                'request', 'briefing', 'report', 'summary', 'dashboard',
                'metrics', 'performance', 'strategic', 'priority', 'urgent'
            ],
            'sender_patterns': ['secretary', 'director', 'deputy', 'chief'],
            'attachment_patterns': ['pdf', 'pptx', 'docx', 'report', 'briefing']
        }
    }
    
    CONFIDENCE_THRESHOLD = 0.80
    MANUAL_REVIEW_THRESHOLD = 0.80
    
    def __init__(self):
        self.classification_stats = {
            'total_classifications': 0,
            'successful_classifications': 0,
            'manual_reviews_required': 0,
            'per_type_counts': {email_type: 0 for email_type in EmailType}
        }
    
    def rule_based_classification(self, features: EmailFeatures) -> Tuple[EmailType, float]:
        """Rule-based classification implementation"""
        scores = {email_type: 0.0 for email_type in EmailType}
        
        # Analyze each email type based on patterns
        for email_type, patterns in self.EMAIL_TYPE_PATTERNS.items():
            score = 0.0
            
            # Subject keyword matching
            subject_keywords_lower = [kw.lower() for kw in features.subject_keywords]
            subject_matches = sum(
                1 for pattern_kw in patterns['subject_keywords']
                if any(pattern_kw in subj_kw for subj_kw in subject_keywords_lower)
            )
            score += subject_matches * 0.3
            
            # Content keyword matching
            content_keywords_lower = [kw.lower() for kw in features.content_keywords]
            content_matches = sum(
                1 for pattern_kw in patterns['content_keywords']
                if any(pattern_kw in cont_kw for cont_kw in content_keywords_lower)
            )
            score += content_matches * 0.2
            
            # Sender pattern matching
            sender_matches = sum(
                1 for pattern in patterns['sender_patterns']
                if pattern in features.sender_domain or 
                   any(pattern in role for role in features.sender_role_indicators)
            )
            score += sender_matches * 0.3
            
            # Attachment pattern matching
            attachment_matches = sum(
                1 for pattern in patterns['attachment_patterns']
                if any(pattern in att_type.lower() for att_type in features.attachment_types)
            )
            score += attachment_matches * 0.2
            
            scores[email_type] = score
        
        # Find best match
        best_type = max(scores, key=scores.get)
        max_score = scores[best_type]
        
        # Calculate confidence based on score separation
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) > 1 and sorted_scores[0] > 0:
            confidence = min(0.9, sorted_scores[0] / (sorted_scores[0] + sorted_scores[1]))
        else:
            confidence = 0.5  # Low confidence for rule-based
        
        return best_type, confidence
    
    def classify_email(self, extracted_content: ExtractedContent,
                      security_result: SecurityValidationResult) -> ClassificationResult:
        """Classify email using rule-based approach"""
        try:
            self.classification_stats['total_classifications'] += 1
            
            # Extract features (simplified)
            features = self._extract_features(extracted_content, security_result)
            
            # Perform classification
            email_type, confidence = self.rule_based_classification(features)
            
            # Create result
            result = ClassificationResult(
                email_type=email_type,
                confidence_score=confidence,
                feature_importance=self._calculate_feature_importance(features, email_type),
                classification_metadata={'method': 'rule_based'},
                requires_manual_review=confidence < self.MANUAL_REVIEW_THRESHOLD,
                alternative_classifications=[],
                classification_timestamp=datetime.utcnow()
            )
            
            self.classification_stats['successful_classifications'] += 1
            self.classification_stats['per_type_counts'][email_type] += 1
            
            if result.requires_manual_review:
                self.classification_stats['manual_reviews_required'] += 1
            
            return result
            
        except Exception as e:
            print(f"Classification failed: {e}")
            return ClassificationResult(
                email_type=EmailType.DEVELOPER_UPDATE,
                confidence_score=0.1,
                feature_importance={},
                classification_metadata={'error': 'classification_failed'},
                requires_manual_review=True,
                alternative_classifications=[],
                classification_timestamp=datetime.utcnow()
            )
    
    def _extract_features(self, extracted_content: ExtractedContent,
                         security_result: SecurityValidationResult) -> EmailFeatures:
        """Extract features from email content"""
        headers = extracted_content.headers
        content = extracted_content.plain_text
        
        # Simple feature extraction
        sender_domain = headers.sender.split('@')[1].lower() if '@' in headers.sender else ''
        sender_is_government = any(
            domain in sender_domain for domain in ['dol.gov', 'labor.gov', 'whitehouse.gov']
        )
        
        return EmailFeatures(
            sender_domain=sender_domain,
            sender_is_government=sender_is_government,
            sender_role_indicators=self._extract_role_indicators(headers.sender),
            subject_keywords=headers.subject.lower().split(),
            subject_length=len(headers.subject),
            subject_urgency_indicators=headers.subject.lower().count('urgent'),
            subject_reply_indicators=headers.subject.lower().count('re:'),
            content_length=len(content),
            content_keywords=content.lower().split()[:20],  # First 20 words
            content_sentiment_score=0.0,
            content_formality_score=0.7 if any(word in content.lower() for word in ['pursuant', 'hereby']) else 0.5,
            content_technical_terms=sum(1 for word in ['code', 'api', 'database'] if word in content.lower()),
            attachment_count=len(extracted_content.attachments),
            attachment_types=[att.content_type for att in extracted_content.attachments],
            has_pdf_attachments=any('pdf' in att.content_type for att in extracted_content.attachments),
            has_office_attachments=any('office' in att.content_type for att in extracted_content.attachments),
            is_reply=extracted_content.thread_analysis.is_reply,
            thread_depth=extracted_content.thread_analysis.thread_depth,
            conversation_participants_count=len(extracted_content.thread_analysis.conversation_participants),
            sender_authorized=security_result.sender_authorized,
            content_safe=security_result.content_safe,
            attachments_safe=security_result.attachments_safe,
            sent_hour=headers.date.hour,
            sent_day_of_week=headers.date.weekday(),
            is_business_hours=9 <= headers.date.hour <= 17 and headers.date.weekday() < 5
        )
    
    def _extract_role_indicators(self, sender: str) -> List[str]:
        """Extract role indicators from sender"""
        indicators = []
        sender_lower = sender.lower()
        
        role_patterns = {
            'executive': ['secretary', 'director', 'deputy', 'chief'],
            'pmo': ['pmo', 'project', 'program'],
            'developer': ['dev', 'engineer', 'tech']
        }
        
        for role, patterns in role_patterns.items():
            if any(pattern in sender_lower for pattern in patterns):
                indicators.append(role)
        
        return indicators
    
    def _calculate_feature_importance(self, features: EmailFeatures, email_type: EmailType) -> Dict[str, float]:
        """Calculate simple feature importance"""
        importance = {}
        
        if email_type == EmailType.EXECUTIVE_REQUEST:
            importance['urgency'] = min(features.subject_urgency_indicators / 2.0, 0.3)
            importance['sender_role'] = 0.2 if 'executive' in features.sender_role_indicators else 0.0
        elif email_type == EmailType.PMO_RESPONSE:
            importance['is_reply'] = 0.3 if features.is_reply else 0.0
            importance['office_attachments'] = 0.2 if features.has_office_attachments else 0.0
        elif email_type == EmailType.DEVELOPER_UPDATE:
            importance['technical_terms'] = min(features.content_technical_terms / 5.0, 0.3)
        elif email_type == EmailType.NEW_EO:
            importance['formality'] = features.content_formality_score * 0.3
            importance['pdf_attachments'] = 0.2 if features.has_pdf_attachments else 0.0
        
        return importance
    
    def get_classification_statistics(self) -> Dict[str, Any]:
        """Get classification statistics"""
        return self.classification_stats.copy()


def test_classifier():
    """Test the email classifier"""
    print("🧪 Testing Email Classifier...")
    
    classifier = SimpleEmailClassifier()
    print("✓ Classifier created")
    
    # Test cases for each email type
    test_cases = [
        # Executive Request
        {
            'type': EmailType.EXECUTIVE_REQUEST,
            'sender': 'secretary@dol.gov',
            'subject': 'URGENT: Executive Briefing Required - Q4 Performance',
            'content': 'The Secretary requires an immediate briefing on performance metrics for the Cabinet meeting.',
            'attachments': [('briefing_template.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation')],
            'is_reply': False
        },
        # PMO Response
        {
            'type': EmailType.PMO_RESPONSE,
            'sender': 'pmo.manager@dol.gov',
            'subject': 'RE: Project Alpha - Budget Approval Decision',
            'content': 'Following our review of the project deliverables, the budget has been approved for Phase 2.',
            'attachments': [('approval.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')],
            'is_reply': True
        },
        # Developer Update
        {
            'type': EmailType.DEVELOPER_UPDATE,
            'sender': 'dev.team@dol.gov',
            'subject': 'Development Update - Sprint 23 - 85% Complete',
            'content': 'Sprint progress: API development complete, database optimization in progress, code review finished.',
            'attachments': [('logs.zip', 'application/zip')],
            'is_reply': False
        },
        # NEW_EO
        {
            'type': EmailType.NEW_EO,
            'sender': 'whitehouse@whitehouse.gov',
            'subject': 'Executive Order 14001: Federal IT Modernization',
            'content': 'Executive Order 14001 hereby directs all federal agencies to implement modernization requirements pursuant to this directive.',
            'attachments': [('executive_order.pdf', 'application/pdf')],
            'is_reply': False
        }
    ]
    
    correct_classifications = 0
    total_classifications = len(test_cases)
    
    for i, test_case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1}: {test_case['type'].value} ---")
        
        # Create test data
        headers = EmailHeaders(
            message_id=f"<test-{i}@dol.gov>",
            sender=test_case['sender'],
            sender_name="Test User",
            recipients=['recipient@dol.gov'],
            cc_recipients=[],
            bcc_recipients=[],
            subject=test_case['subject'],
            date=datetime.now(),
            reply_to=None,
            in_reply_to="<parent@dol.gov>" if test_case['is_reply'] else None,
            references=["<ref@dol.gov>"] if test_case['is_reply'] else [],
            thread_topic=None,
            priority='high' if 'URGENT' in test_case['subject'] else None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        
        thread_analysis = ThreadAnalysis(
            thread_id=f"<thread-{i}@dol.gov>",
            is_reply=test_case['is_reply'],
            is_forward=False,
            parent_message_id="<parent@dol.gov>" if test_case['is_reply'] else None,
            thread_depth=1 if test_case['is_reply'] else 0,
            conversation_participants={test_case['sender']},
            thread_subject=test_case['subject'],
            original_subject=test_case['subject'],
            reply_chain_length=1 if test_case['is_reply'] else 0
        )
        
        attachments = []
        for filename, content_type in test_case['attachments']:
            attachment = ValidatedAttachment(
                filename=filename,
                original_filename=filename,
                content_type=content_type,
                size_bytes=1024000,
                content_hash=f"hash_{filename}",
                is_safe=True,
                security_scan_result="CLEAN",
                temporary_path=f"/tmp/{filename}",
                extraction_timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
                metadata={}
            )
            attachments.append(attachment)
        
        extracted_content = ExtractedContent(
            headers=headers,
            plain_text=test_case['content'],
            html_content=None,
            sanitized_html=None,
            attachments=attachments,
            thread_analysis=thread_analysis,
            content_hash=f"hash_{i}",
            extraction_metadata={},
            security_flags=[]
        )
        
        security_result = SecurityValidationResult(
            is_valid=True,
            sender_authorized=True,
            content_safe=True,
            attachments_safe=True,
            digital_signature_valid=True,
            threat_level="LOW",
            security_issues=[],
            quarantine_required=False,
            validation_timestamp=datetime.now()
        )
        
        # Classify
        result = classifier.classify_email(extracted_content, security_result)
        
        # Check result
        is_correct = result.email_type == test_case['type']
        if is_correct:
            correct_classifications += 1
            print(f"✅ CORRECT: {result.email_type.value} (confidence: {result.confidence_score:.3f})")
        else:
            print(f"❌ INCORRECT: Expected {test_case['type'].value}, got {result.email_type.value} (confidence: {result.confidence_score:.3f})")
        
        print(f"   Manual Review Required: {result.requires_manual_review}")
        if result.feature_importance:
            print(f"   Top Features: {list(result.feature_importance.keys())[:3]}")
    
    # Summary
    accuracy = correct_classifications / total_classifications
    print(f"\n📊 RESULTS SUMMARY:")
    print(f"   Overall Accuracy: {accuracy:.3f} ({correct_classifications}/{total_classifications})")
    print(f"   Target Accuracy: ≥0.70 for rule-based classification")
    
    # Statistics
    stats = classifier.get_classification_statistics()
    print(f"\n📈 CLASSIFICATION STATISTICS:")
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for sub_key, sub_value in value.items():
                print(f"     {sub_key}: {sub_value}")
        else:
            print(f"   {key}: {value}")
    
    # Test passed if accuracy is reasonable
    if accuracy >= 0.70:
        print(f"\n🎉 TEST PASSED! Accuracy {accuracy:.3f} meets minimum threshold of 0.70")
        return True
    else:
        print(f"\n❌ TEST FAILED! Accuracy {accuracy:.3f} below minimum threshold of 0.70")
        return False


if __name__ == "__main__":
    try:
        success = test_classifier()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)