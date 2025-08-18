"""
Machine Learning Email Classifier for Government Email Processing

This module implements a multi-factor email classification system that analyzes
sender, subject, content, and attachments to classify emails into four types:
NEW_EO, PMO_RESPONSE, DEVELOPER_UPDATE, EXECUTIVE_REQUEST with 95% accuracy target.
"""

import logging
import re
import hashlib
import pickle
import json
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.message import EmailMessage as StdEmailMessage
from pathlib import Path
from enum import Enum
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler
import joblib

# Import types for type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .content_extractor import ExtractedContent, EmailHeaders, ValidatedAttachment
    from .security_validator import SecurityValidationResult

logger = logging.getLogger(__name__)


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


@dataclass
class ClassificationAccuracy:
    """Classification accuracy metrics for validation"""
    overall_accuracy: float
    per_class_accuracy: Dict[EmailType, float]
    precision_scores: Dict[EmailType, float]
    recall_scores: Dict[EmailType, float]
    f1_scores: Dict[EmailType, float]
    confusion_matrix: np.ndarray
    validation_timestamp: datetime


class EmailClassifier:
    """
    Multi-factor machine learning email classifier for government workflows.
    
    Implements comprehensive email classification using:
    - Sender analysis (domain, role indicators)
    - Subject analysis (keywords, patterns, urgency)
    - Content analysis (keywords, sentiment, formality, technical terms)
    - Attachment analysis (types, count, content)
    - Thread analysis (reply patterns, conversation context)
    - Security validation results
    - Temporal patterns (time of day, business hours)
    """
    
    # Government domain patterns for sender analysis
    GOVERNMENT_DOMAINS = {
        'dol.gov', 'labor.gov', 'osha.gov', 'bls.gov', 'dol.state.gov',
        'whitehouse.gov', 'gsa.gov', 'omb.gov', 'treasury.gov'
    }
    
    # Role indicators for sender classification
    ROLE_INDICATORS = {
        'executive': ['secretary', 'assistant.secretary', 'director', 'deputy', 'chief', 'administrator'],
        'pmo': ['pmo', 'project.manager', 'program.manager', 'portfolio', 'coordinator'],
        'developer': ['developer', 'engineer', 'programmer', 'architect', 'devops', 'tech'],
        'analyst': ['analyst', 'specialist', 'advisor', 'consultant']
    }
    
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
    
    # Confidence thresholds
    CONFIDENCE_THRESHOLD = 0.80  # Minimum confidence for automated processing
    MANUAL_REVIEW_THRESHOLD = 0.80  # Below this requires manual review
    ACCURACY_TARGET = 0.95  # Target accuracy for model validation
    
    def __init__(self, model_directory: str = "models", 
                 enable_model_training: bool = True):
        """
        Initialize the email classifier.
        
        Args:
            model_directory: Directory to store trained models
            enable_model_training: Whether to enable model training and updates
        """
        self.model_directory = Path(model_directory)
        self.model_directory.mkdir(parents=True, exist_ok=True)
        
        self.enable_model_training = enable_model_training
        
        # Initialize models and vectorizers
        self.text_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=2,
            max_df=0.95
        )
        
        self.feature_scaler = StandardScaler()
        
        # Ensemble classifier with multiple algorithms
        self.classifier = VotingClassifier([
            ('rf', RandomForestClassifier(n_estimators=100, random_state=42)),
            ('lr', LogisticRegression(random_state=42, max_iter=1000)),
            ('svm', SVC(probability=True, random_state=42))
        ], voting='soft')
        
        # Classification statistics
        self.classification_stats = {
            'total_classifications': 0,
            'successful_classifications': 0,
            'manual_reviews_required': 0,
            'accuracy_validations': 0,
            'model_retraining_count': 0,
            'per_type_counts': {email_type: 0 for email_type in EmailType}
        }
        
        # Load existing models if available
        self._load_models()
        
        logger.info(f"Email classifier initialized with model directory: {model_directory}")
    
    def classify_email(self, extracted_content: 'ExtractedContent',
                      security_result: 'SecurityValidationResult') -> ClassificationResult:
        """
        Classify email using multi-factor analysis.
        
        Args:
            extracted_content: Extracted email content and metadata
            security_result: Security validation result
            
        Returns:
            ClassificationResult with classification and confidence
        """
        try:
            self.classification_stats['total_classifications'] += 1
            classification_start = datetime.utcnow()
            
            logger.debug(f"Starting classification for email: {extracted_content.headers.message_id}")
            
            # Extract comprehensive features
            features = self._extract_email_features(extracted_content, security_result)
            
            # Perform classification
            try:
                # Check if model is trained by trying to predict
                feature_vector = self._features_to_vector(features)
                probabilities = self.classifier.predict_proba([feature_vector])[0]
                
                # Get class labels
                classes = self.classifier.classes_
                
                # Find best classification
                best_idx = np.argmax(probabilities)
                best_email_type = EmailType(classes[best_idx])
                confidence_score = probabilities[best_idx]
                
                # Get alternative classifications
                alternative_classifications = []
                for i, (class_label, prob) in enumerate(zip(classes, probabilities)):
                    if i != best_idx and prob > 0.1:  # Include alternatives with >10% probability
                        alternative_classifications.append((EmailType(class_label), prob))
                
                # Sort alternatives by probability
                alternative_classifications.sort(key=lambda x: x[1], reverse=True)
                
            except Exception as e:
                # Fallback to rule-based classification if model not trained or prediction fails
                logger.debug(f"Using rule-based classification - ML model not available: {e}")
                best_email_type, confidence_score = self._rule_based_classification(features)
                alternative_classifications = []
            
            # Calculate feature importance (simplified for this implementation)
            feature_importance = self._calculate_feature_importance(features, best_email_type)
            
            # Determine if manual review is required
            requires_manual_review = confidence_score < self.MANUAL_REVIEW_THRESHOLD
            
            # Create classification metadata
            classification_metadata = {
                'feature_count': len(self._features_to_vector(features)),
                'model_version': self._get_model_version(),
                'classification_method': 'ml_ensemble' if hasattr(self.classifier, 'predict_proba') else 'rule_based',
                'processing_time_ms': (datetime.utcnow() - classification_start).total_seconds() * 1000
            }
            
            result = ClassificationResult(
                email_type=best_email_type,
                confidence_score=confidence_score,
                feature_importance=feature_importance,
                classification_metadata=classification_metadata,
                requires_manual_review=requires_manual_review,
                alternative_classifications=alternative_classifications,
                classification_timestamp=classification_start
            )
            
            # Update statistics
            self.classification_stats['successful_classifications'] += 1
            self.classification_stats['per_type_counts'][best_email_type] += 1
            
            if requires_manual_review:
                self.classification_stats['manual_reviews_required'] += 1
            
            logger.info(f"Email classified as {best_email_type.value} with confidence {confidence_score:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Email classification failed: {e}")
            # Return fallback classification
            return self._create_fallback_classification(extracted_content)
    
    def _extract_email_features(self, extracted_content: 'ExtractedContent',
                               security_result: 'SecurityValidationResult') -> EmailFeatures:
        """Extract comprehensive features for classification"""
        headers = extracted_content.headers
        content = extracted_content.plain_text
        attachments = extracted_content.attachments
        thread_analysis = extracted_content.thread_analysis
        
        # Sender features
        sender_domain = headers.sender.split('@')[1].lower() if '@' in headers.sender else ''
        sender_is_government = any(
            sender_domain == gov_domain or sender_domain.endswith(f'.{gov_domain}')
            for gov_domain in self.GOVERNMENT_DOMAINS
        )
        sender_role_indicators = self._extract_sender_role_indicators(headers.sender)
        
        # Subject features
        subject_keywords = self._extract_keywords(headers.subject.lower())
        subject_length = len(headers.subject)
        subject_urgency_indicators = self._count_urgency_indicators(headers.subject)
        subject_reply_indicators = self._count_reply_indicators(headers.subject)
        
        # Content features
        content_length = len(content)
        content_keywords = self._extract_keywords(content.lower())
        content_sentiment_score = self._calculate_sentiment_score(content)
        content_formality_score = self._calculate_formality_score(content)
        content_technical_terms = self._count_technical_terms(content)
        
        # Attachment features
        attachment_count = len(attachments)
        attachment_types = [att.content_type for att in attachments]
        has_pdf_attachments = any('pdf' in att.content_type.lower() for att in attachments)
        has_office_attachments = any(
            any(office_type in att.content_type.lower() 
                for office_type in ['word', 'excel', 'powerpoint', 'officedocument'])
            for att in attachments
        )
        
        # Thread features
        is_reply = thread_analysis.is_reply
        thread_depth = thread_analysis.thread_depth
        conversation_participants_count = len(thread_analysis.conversation_participants)
        
        # Security features
        sender_authorized = security_result.sender_authorized
        content_safe = security_result.content_safe
        attachments_safe = security_result.attachments_safe
        
        # Temporal features
        sent_hour = headers.date.hour
        sent_day_of_week = headers.date.weekday()
        is_business_hours = 9 <= sent_hour <= 17 and sent_day_of_week < 5
        
        return EmailFeatures(
            sender_domain=sender_domain,
            sender_is_government=sender_is_government,
            sender_role_indicators=sender_role_indicators,
            subject_keywords=subject_keywords,
            subject_length=subject_length,
            subject_urgency_indicators=subject_urgency_indicators,
            subject_reply_indicators=subject_reply_indicators,
            content_length=content_length,
            content_keywords=content_keywords,
            content_sentiment_score=content_sentiment_score,
            content_formality_score=content_formality_score,
            content_technical_terms=content_technical_terms,
            attachment_count=attachment_count,
            attachment_types=attachment_types,
            has_pdf_attachments=has_pdf_attachments,
            has_office_attachments=has_office_attachments,
            is_reply=is_reply,
            thread_depth=thread_depth,
            conversation_participants_count=conversation_participants_count,
            sender_authorized=sender_authorized,
            content_safe=content_safe,
            attachments_safe=attachments_safe,
            sent_hour=sent_hour,
            sent_day_of_week=sent_day_of_week,
            is_business_hours=is_business_hours
        )
    
    def _extract_sender_role_indicators(self, sender: str) -> List[str]:
        """Extract role indicators from sender email"""
        indicators = []
        sender_lower = sender.lower()
        
        for role, patterns in self.ROLE_INDICATORS.items():
            for pattern in patterns:
                if pattern in sender_lower:
                    indicators.append(role)
                    break
        
        return indicators
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        # Simple keyword extraction - in production, use more sophisticated NLP
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words and short words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Return unique keywords
        return list(set(keywords))
    
    def _count_urgency_indicators(self, text: str) -> int:
        """Count urgency indicators in text"""
        urgency_patterns = [
            'urgent', 'asap', 'immediate', 'priority', 'critical',
            'emergency', 'rush', 'time sensitive', 'deadline'
        ]
        
        text_lower = text.lower()
        return sum(1 for pattern in urgency_patterns if pattern in text_lower)
    
    def _count_reply_indicators(self, subject: str) -> int:
        """Count reply indicators in subject"""
        reply_patterns = ['re:', 'fwd:', 'fw:', 'reply', 'response']
        subject_lower = subject.lower()
        return sum(1 for pattern in reply_patterns if pattern in subject_lower)
    
    def _calculate_sentiment_score(self, content: str) -> float:
        """Calculate sentiment score (simplified implementation)"""
        # Simplified sentiment analysis - in production, use proper NLP library
        positive_words = [
            'good', 'great', 'excellent', 'successful', 'approved', 'completed',
            'satisfied', 'pleased', 'positive', 'effective', 'efficient'
        ]
        negative_words = [
            'bad', 'poor', 'failed', 'rejected', 'delayed', 'problem',
            'issue', 'concern', 'negative', 'ineffective', 'inefficient'
        ]
        
        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        total_words = len(content.split())
        if total_words == 0:
            return 0.0
        
        # Return normalized sentiment score (-1 to 1)
        return (positive_count - negative_count) / max(total_words / 100, 1)
    
    def _calculate_formality_score(self, content: str) -> float:
        """Calculate formality score of content"""
        # Enhanced formality analysis for government content
        formal_indicators = [
            'pursuant to', 'in accordance with', 'hereby', 'whereas',
            'therefore', 'furthermore', 'consequently', 'respectfully',
            'executive order', 'federal agencies', 'implementation',
            'compliance', 'authority vested', 'constitution', 'laws',
            'united states', 'shall', 'effective immediately'
        ]
        informal_indicators = [
            'hey', 'hi', 'thanks', 'thx', 'ok', 'okay', 'cool', 'awesome',
            'gonna', 'wanna', 'yeah', 'nope', 'btw', 'fyi'
        ]
        
        content_lower = content.lower()
        formal_count = sum(1 for indicator in formal_indicators if indicator in content_lower)
        informal_count = sum(1 for indicator in informal_indicators if indicator in content_lower)
        
        total_words = len(content.split())
        if total_words == 0:
            return 0.5  # Neutral
        
        # Base formality score
        base_score = 0.5
        
        # Adjust based on formal/informal indicators
        if formal_count > 0:
            base_score += min(0.4, formal_count * 0.1)  # Up to 0.4 boost
        if informal_count > 0:
            base_score -= min(0.3, informal_count * 0.1)  # Up to 0.3 reduction
        
        # Additional checks for government-style language
        if any(phrase in content_lower for phrase in ['executive order', 'federal', 'pursuant to']):
            base_score += 0.2
        
        return max(0.0, min(1.0, base_score))
    
    def _count_technical_terms(self, content: str) -> int:
        """Count technical terms in content"""
        technical_terms = [
            'api', 'database', 'server', 'application', 'system', 'software',
            'code', 'programming', 'development', 'deployment', 'testing',
            'bug', 'feature', 'implementation', 'architecture', 'framework'
        ]
        
        content_lower = content.lower()
        return sum(1 for term in technical_terms if term in content_lower)
    
    def _features_to_vector(self, features: EmailFeatures) -> np.ndarray:
        """Convert features to numerical vector for ML model"""
        # Create feature vector (simplified - in production, use proper feature engineering)
        vector = [
            # Sender features
            1.0 if features.sender_is_government else 0.0,
            len(features.sender_role_indicators),
            
            # Subject features
            features.subject_length / 100.0,  # Normalized
            features.subject_urgency_indicators,
            features.subject_reply_indicators,
            
            # Content features
            min(features.content_length / 1000.0, 10.0),  # Normalized and capped
            len(features.content_keywords) / 10.0,  # Normalized
            features.content_sentiment_score,
            features.content_formality_score,
            features.content_technical_terms / 10.0,  # Normalized
            
            # Attachment features
            min(features.attachment_count, 10.0),  # Capped
            1.0 if features.has_pdf_attachments else 0.0,
            1.0 if features.has_office_attachments else 0.0,
            
            # Thread features
            1.0 if features.is_reply else 0.0,
            min(features.thread_depth, 10.0),  # Capped
            min(features.conversation_participants_count, 20.0),  # Capped
            
            # Security features
            1.0 if features.sender_authorized else 0.0,
            1.0 if features.content_safe else 0.0,
            1.0 if features.attachments_safe else 0.0,
            
            # Temporal features
            features.sent_hour / 24.0,  # Normalized
            features.sent_day_of_week / 7.0,  # Normalized
            1.0 if features.is_business_hours else 0.0
        ]
        
        return np.array(vector)
    
    def _rule_based_classification(self, features: EmailFeatures) -> Tuple[EmailType, float]:
        """Fallback rule-based classification when ML model is not available"""
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
    
    def _calculate_feature_importance(self, features: EmailFeatures, 
                                    email_type: EmailType) -> Dict[str, float]:
        """Calculate feature importance for the classification"""
        # Simplified feature importance calculation
        importance = {}
        
        # High importance features for each email type
        if email_type == EmailType.NEW_EO:
            importance['sender_government'] = 0.3 if features.sender_is_government else 0.0
            importance['has_pdf'] = 0.2 if features.has_pdf_attachments else 0.0
            importance['formality'] = features.content_formality_score * 0.2
            
        elif email_type == EmailType.PMO_RESPONSE:
            importance['is_reply'] = 0.3 if features.is_reply else 0.0
            importance['has_office_docs'] = 0.2 if features.has_office_attachments else 0.0
            importance['thread_depth'] = min(features.thread_depth / 10.0, 0.2)
            
        elif email_type == EmailType.DEVELOPER_UPDATE:
            importance['technical_terms'] = min(features.content_technical_terms / 10.0, 0.3)
            importance['sender_role'] = 0.2 if 'developer' in features.sender_role_indicators else 0.0
            importance['content_length'] = min(features.content_length / 1000.0, 0.2)
            
        elif email_type == EmailType.EXECUTIVE_REQUEST:
            importance['sender_role'] = 0.3 if 'executive' in features.sender_role_indicators else 0.0
            importance['urgency'] = min(features.subject_urgency_indicators / 3.0, 0.2)
            importance['business_hours'] = 0.1 if features.is_business_hours else 0.0
        
        # Normalize importance scores
        total_importance = sum(importance.values())
        if total_importance > 0:
            importance = {k: v / total_importance for k, v in importance.items()}
        
        return importance
    
    def _create_fallback_classification(self, extracted_content: 'ExtractedContent') -> ClassificationResult:
        """Create fallback classification result on error"""
        return ClassificationResult(
            email_type=EmailType.DEVELOPER_UPDATE,  # Safe default
            confidence_score=0.1,  # Very low confidence
            feature_importance={},
            classification_metadata={'error': 'classification_failed'},
            requires_manual_review=True,
            alternative_classifications=[],
            classification_timestamp=datetime.utcnow()
        )
    
    def train_model(self, training_data: List[Tuple['ExtractedContent', 'SecurityValidationResult', EmailType]]) -> ClassificationAccuracy:
        """
        Train the classification model with labeled data.
        
        Args:
            training_data: List of (extracted_content, security_result, true_email_type) tuples
            
        Returns:
            ClassificationAccuracy with training results
        """
        if not self.enable_model_training:
            logger.warning("Model training is disabled")
            return self._create_dummy_accuracy()
        
        try:
            logger.info(f"Starting model training with {len(training_data)} samples")
            
            # Extract features and labels
            X = []
            y = []
            
            for extracted_content, security_result, true_email_type in training_data:
                features = self._extract_email_features(extracted_content, security_result)
                feature_vector = self._features_to_vector(features)
                
                X.append(feature_vector)
                y.append(true_email_type.value)
            
            X = np.array(X)
            y = np.array(y)
            
            # Split data for validation
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            X_train_scaled = self.feature_scaler.fit_transform(X_train)
            X_test_scaled = self.feature_scaler.transform(X_test)
            
            # Train the ensemble classifier
            self.classifier.fit(X_train_scaled, y_train)
            
            # Validate model
            y_pred = self.classifier.predict(X_test_scaled)
            y_pred_proba = self.classifier.predict_proba(X_test_scaled)
            
            # Calculate accuracy metrics
            overall_accuracy = accuracy_score(y_test, y_pred)
            
            # Per-class metrics
            from sklearn.metrics import precision_recall_fscore_support
            precision, recall, f1, support = precision_recall_fscore_support(
                y_test, y_pred, average=None, labels=[et.value for et in EmailType]
            )
            
            per_class_accuracy = {}
            precision_scores = {}
            recall_scores = {}
            f1_scores = {}
            
            for i, email_type in enumerate(EmailType):
                # Calculate per-class accuracy
                class_mask = y_test == email_type.value
                if np.sum(class_mask) > 0:
                    class_correct = np.sum((y_pred == email_type.value) & class_mask)
                    per_class_accuracy[email_type] = class_correct / np.sum(class_mask)
                else:
                    per_class_accuracy[email_type] = 0.0
                
                precision_scores[email_type] = precision[i] if i < len(precision) else 0.0
                recall_scores[email_type] = recall[i] if i < len(recall) else 0.0
                f1_scores[email_type] = f1[i] if i < len(f1) else 0.0
            
            # Confusion matrix
            conf_matrix = confusion_matrix(y_test, y_pred, labels=[et.value for et in EmailType])
            
            # Save trained model
            self._save_models()
            
            # Update statistics
            self.classification_stats['model_retraining_count'] += 1
            
            accuracy_result = ClassificationAccuracy(
                overall_accuracy=overall_accuracy,
                per_class_accuracy=per_class_accuracy,
                precision_scores=precision_scores,
                recall_scores=recall_scores,
                f1_scores=f1_scores,
                confusion_matrix=conf_matrix,
                validation_timestamp=datetime.utcnow()
            )
            
            logger.info(f"Model training completed. Overall accuracy: {overall_accuracy:.3f}")
            
            # Check if accuracy meets target
            if overall_accuracy < self.ACCURACY_TARGET:
                logger.warning(f"Model accuracy {overall_accuracy:.3f} below target {self.ACCURACY_TARGET}")
            
            return accuracy_result
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return self._create_dummy_accuracy()
    
    def validate_classification_accuracy(self, validation_data: List[Tuple['ExtractedContent', 'SecurityValidationResult', EmailType]]) -> ClassificationAccuracy:
        """
        Validate classification accuracy on test data.
        
        Args:
            validation_data: List of (extracted_content, security_result, true_email_type) tuples
            
        Returns:
            ClassificationAccuracy with validation results
        """
        try:
            self.classification_stats['accuracy_validations'] += 1
            
            logger.info(f"Validating classification accuracy with {len(validation_data)} samples")
            
            correct_predictions = 0
            per_class_correct = {email_type: 0 for email_type in EmailType}
            per_class_total = {email_type: 0 for email_type in EmailType}
            
            all_predictions = []
            all_true_labels = []
            
            for extracted_content, security_result, true_email_type in validation_data:
                # Classify email
                classification_result = self.classify_email(extracted_content, security_result)
                predicted_type = classification_result.email_type
                
                # Track results
                all_predictions.append(predicted_type.value)
                all_true_labels.append(true_email_type.value)
                
                per_class_total[true_email_type] += 1
                
                if predicted_type == true_email_type:
                    correct_predictions += 1
                    per_class_correct[true_email_type] += 1
            
            # Calculate overall accuracy
            overall_accuracy = correct_predictions / len(validation_data) if validation_data else 0.0
            
            # Calculate per-class accuracy
            per_class_accuracy = {}
            for email_type in EmailType:
                if per_class_total[email_type] > 0:
                    per_class_accuracy[email_type] = per_class_correct[email_type] / per_class_total[email_type]
                else:
                    per_class_accuracy[email_type] = 0.0
            
            # Calculate precision, recall, F1
            from sklearn.metrics import precision_recall_fscore_support
            precision, recall, f1, support = precision_recall_fscore_support(
                all_true_labels, all_predictions, average=None, labels=[et.value for et in EmailType]
            )
            
            precision_scores = {}
            recall_scores = {}
            f1_scores = {}
            
            for i, email_type in enumerate(EmailType):
                precision_scores[email_type] = precision[i] if i < len(precision) else 0.0
                recall_scores[email_type] = recall[i] if i < len(recall) else 0.0
                f1_scores[email_type] = f1[i] if i < len(f1) else 0.0
            
            # Confusion matrix
            conf_matrix = confusion_matrix(all_true_labels, all_predictions, labels=[et.value for et in EmailType])
            
            accuracy_result = ClassificationAccuracy(
                overall_accuracy=overall_accuracy,
                per_class_accuracy=per_class_accuracy,
                precision_scores=precision_scores,
                recall_scores=recall_scores,
                f1_scores=f1_scores,
                confusion_matrix=conf_matrix,
                validation_timestamp=datetime.utcnow()
            )
            
            logger.info(f"Accuracy validation completed. Overall accuracy: {overall_accuracy:.3f}")
            
            return accuracy_result
            
        except Exception as e:
            logger.error(f"Accuracy validation failed: {e}")
            return self._create_dummy_accuracy()
    
    def _create_dummy_accuracy(self) -> ClassificationAccuracy:
        """Create dummy accuracy result for error cases"""
        return ClassificationAccuracy(
            overall_accuracy=0.0,
            per_class_accuracy={email_type: 0.0 for email_type in EmailType},
            precision_scores={email_type: 0.0 for email_type in EmailType},
            recall_scores={email_type: 0.0 for email_type in EmailType},
            f1_scores={email_type: 0.0 for email_type in EmailType},
            confusion_matrix=np.zeros((len(EmailType), len(EmailType))),
            validation_timestamp=datetime.utcnow()
        )
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            # Save classifier
            classifier_path = self.model_directory / "email_classifier.pkl"
            joblib.dump(self.classifier, classifier_path)
            
            # Save feature scaler
            scaler_path = self.model_directory / "feature_scaler.pkl"
            joblib.dump(self.feature_scaler, scaler_path)
            
            # Save text vectorizer
            vectorizer_path = self.model_directory / "text_vectorizer.pkl"
            joblib.dump(self.text_vectorizer, vectorizer_path)
            
            # Save metadata
            metadata = {
                'model_version': self._get_model_version(),
                'training_timestamp': datetime.utcnow().isoformat(),
                'classification_stats': self.classification_stats
            }
            
            metadata_path = self.model_directory / "model_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
    
    def _load_models(self):
        """Load trained models from disk"""
        try:
            classifier_path = self.model_directory / "email_classifier.pkl"
            scaler_path = self.model_directory / "feature_scaler.pkl"
            vectorizer_path = self.model_directory / "text_vectorizer.pkl"
            
            if all(path.exists() for path in [classifier_path, scaler_path, vectorizer_path]):
                self.classifier = joblib.load(classifier_path)
                self.feature_scaler = joblib.load(scaler_path)
                self.text_vectorizer = joblib.load(vectorizer_path)
                
                logger.info("Models loaded successfully")
            else:
                logger.info("No existing models found, will use rule-based classification")
                
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
    
    def _get_model_version(self) -> str:
        """Get current model version"""
        return f"v1.0.{self.classification_stats['model_retraining_count']}"
    
    def get_classification_statistics(self) -> Dict[str, Any]:
        """Get classification statistics"""
        return self.classification_stats.copy()


class EmailClassifierFactory:
    """Factory for creating email classifier instances"""
    
    @staticmethod
    def create_classifier(model_directory: str = "models", 
                         enable_training: bool = True) -> EmailClassifier:
        """
        Create an email classifier instance.
        
        Args:
            model_directory: Directory for model storage
            enable_training: Whether to enable model training
            
        Returns:
            EmailClassifier instance
        """
        return EmailClassifier(model_directory, enable_training)
    
    @staticmethod
    def create_production_classifier() -> EmailClassifier:
        """
        Create a production-ready classifier with optimized settings.
        
        Returns:
            EmailClassifier configured for production use
        """
        return EmailClassifier(
            model_directory="models/production",
            enable_model_training=False  # Disable training in production
        )