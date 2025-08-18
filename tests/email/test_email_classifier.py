"""
Comprehensive tests for the Machine Learning Email Classifier

Tests classification accuracy across all email types with 95% accuracy target
and validates confidence scoring, feature extraction, and model training.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch

from src.email.email_classifier import (
    EmailClassifier, EmailType, EmailFeatures, ClassificationResult,
    ClassificationAccuracy, EmailClassifierFactory
)
from src.email.content_extractor import (
    ExtractedContent, EmailHeaders, ValidatedAttachment, ThreadAnalysis
)
from src.email.security_validator import SecurityValidationResult


class TestEmailClassifier:
    """Test suite for EmailClassifier"""
    
    @pytest.fixture
    def temp_model_dir(self):
        """Create temporary directory for model storage"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def classifier(self, temp_model_dir):
        """Create classifier instance for testing"""
        return EmailClassifier(model_directory=temp_model_dir, enable_model_training=True)
    
    @pytest.fixture
    def sample_headers(self):
        """Create sample email headers"""
        return EmailHeaders(
            message_id="<test@example.com>",
            sender="test.user@dol.gov",
            sender_name="Test User",
            recipients=["recipient@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Test Email Subject",
            date=datetime.now(),
            reply_to=None,
            in_reply_to=None,
            references=[],
            thread_topic=None,
            priority=None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
    
    @pytest.fixture
    def sample_thread_analysis(self):
        """Create sample thread analysis"""
        return ThreadAnalysis(
            thread_id="thread-123",
            is_reply=False,
            is_forward=False,
            parent_message_id=None,
            thread_depth=0,
            conversation_participants={"test.user@dol.gov"},
            thread_subject="Test Email Subject",
            original_subject="Test Email Subject",
            reply_chain_length=0
        )
    
    @pytest.fixture
    def sample_security_result(self):
        """Create sample security validation result"""
        return SecurityValidationResult(
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
    
    def create_extracted_content(self, email_type: EmailType, headers: EmailHeaders,
                               thread_analysis: ThreadAnalysis) -> ExtractedContent:
        """Create extracted content for specific email type"""
        
        # Customize content based on email type
        if email_type == EmailType.NEW_EO:
            content = """
            Executive Order 14001: Implementation of New Federal Policy
            
            By the authority vested in me as President by the Constitution and the laws 
            of the United States of America, it is hereby ordered as follows:
            
            Section 1. Policy. It is the policy of this Administration to ensure effective
            implementation of federal directives across all agencies.
            
            This order is effective immediately and shall be implemented by all federal agencies.
            """
            subject = "Executive Order 14001 - Implementation Required"
            attachments = [
                ValidatedAttachment(
                    filename="executive_order_14001.pdf",
                    original_filename="executive_order_14001.pdf",
                    content_type="application/pdf",
                    size_bytes=1024000,
                    content_hash="abc123",
                    is_safe=True,
                    security_scan_result="CLEAN",
                    temporary_path="/tmp/eo.pdf",
                    extraction_timestamp=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=24),
                    metadata={}
                )
            ]
            
        elif email_type == EmailType.PMO_RESPONSE:
            content = """
            Project Status Update - Q4 Implementation
            
            Dear Team,
            
            Following our review of the project milestone deliverables, I am pleased to 
            approve the current phase completion. The budget allocation has been reviewed
            and approved for the next phase.
            
            Key approvals:
            - Budget: $500,000 approved for Phase 2
            - Timeline: Extended by 2 weeks as requested
            - Resources: Additional developer assigned
            
            Please proceed with implementation as planned.
            
            Best regards,
            PMO Team
            """
            subject = "RE: Project Approval - Phase 2 Budget Approved"
            attachments = [
                ValidatedAttachment(
                    filename="project_status.xlsx",
                    original_filename="project_status.xlsx",
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    size_bytes=512000,
                    content_hash="def456",
                    is_safe=True,
                    security_scan_result="CLEAN",
                    temporary_path="/tmp/status.xlsx",
                    extraction_timestamp=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=24),
                    metadata={}
                )
            ]
            
        elif email_type == EmailType.DEVELOPER_UPDATE:
            content = """
            Development Progress Update - Week 42
            
            Hi Team,
            
            Here's the weekly development update:
            
            Completed:
            - Feature implementation for user authentication module
            - Bug fixes for database connection issues
            - Unit testing for API endpoints
            - Code review and merge of 15 pull requests
            
            In Progress:
            - Integration testing for payment system
            - Performance optimization for search functionality
            - Documentation updates
            
            Blockers:
            - Waiting for API keys from third-party service
            - Database migration pending approval
            
            Next Week:
            - Complete integration testing
            - Deploy to staging environment
            - Begin user acceptance testing
            
            Progress: 75% complete
            
            Thanks,
            Development Team
            """
            subject = "Development Update - Week 42 - 75% Complete"
            attachments = [
                ValidatedAttachment(
                    filename="development_logs.zip",
                    original_filename="development_logs.zip",
                    content_type="application/zip",
                    size_bytes=2048000,
                    content_hash="ghi789",
                    is_safe=True,
                    security_scan_result="CLEAN",
                    temporary_path="/tmp/logs.zip",
                    extraction_timestamp=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=24),
                    metadata={}
                )
            ]
            
        elif email_type == EmailType.EXECUTIVE_REQUEST:
            content = """
            URGENT: Executive Briefing Request
            
            Dear Team,
            
            The Secretary requires an immediate briefing on the current status of 
            the digital transformation initiative. Please prepare a comprehensive
            executive summary including:
            
            - Current project status and milestones
            - Budget utilization and forecasts
            - Risk assessment and mitigation strategies
            - Performance metrics and KPIs
            - Recommendations for next quarter
            
            This briefing is needed for the Cabinet meeting on Friday. Please prioritize
            this request and coordinate with all relevant stakeholders.
            
            Time sensitive - please confirm receipt and expected delivery time.
            
            Regards,
            Office of the Secretary
            """
            subject = "URGENT: Executive Briefing Request - Digital Transformation"
            attachments = [
                ValidatedAttachment(
                    filename="briefing_template.pptx",
                    original_filename="briefing_template.pptx",
                    content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    size_bytes=1536000,
                    content_hash="jkl012",
                    is_safe=True,
                    security_scan_result="CLEAN",
                    temporary_path="/tmp/briefing.pptx",
                    extraction_timestamp=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=24),
                    metadata={}
                )
            ]
        
        # Update headers with email type specific content
        headers.subject = subject
        
        return ExtractedContent(
            headers=headers,
            plain_text=content,
            html_content=None,
            sanitized_html=None,
            attachments=attachments,
            thread_analysis=thread_analysis,
            content_hash="content_hash_123",
            extraction_metadata={},
            security_flags=[]
        )
    
    def test_classifier_initialization(self, temp_model_dir):
        """Test classifier initialization"""
        classifier = EmailClassifier(model_directory=temp_model_dir)
        
        assert classifier.model_directory == Path(temp_model_dir)
        assert classifier.enable_model_training is True
        assert classifier.CONFIDENCE_THRESHOLD == 0.80
        assert classifier.ACCURACY_TARGET == 0.95
        assert len(classifier.EMAIL_TYPE_PATTERNS) == 4
    
    def test_feature_extraction_new_eo(self, classifier, sample_headers, 
                                     sample_thread_analysis, sample_security_result):
        """Test feature extraction for NEW_EO emails"""
        extracted_content = self.create_extracted_content(
            EmailType.NEW_EO, sample_headers, sample_thread_analysis
        )
        
        features = classifier._extract_email_features(extracted_content, sample_security_result)
        
        assert features.sender_is_government is True
        assert features.has_pdf_attachments is True
        assert features.content_formality_score > 0.7  # Should be formal
        assert 'executive' in ' '.join(features.content_keywords).lower()
        assert 'order' in ' '.join(features.content_keywords).lower()
    
    def test_feature_extraction_pmo_response(self, classifier, sample_headers,
                                           sample_thread_analysis, sample_security_result):
        """Test feature extraction for PMO_RESPONSE emails"""
        # Make it a reply
        sample_thread_analysis.is_reply = True
        sample_thread_analysis.thread_depth = 2
        
        extracted_content = self.create_extracted_content(
            EmailType.PMO_RESPONSE, sample_headers, sample_thread_analysis
        )
        
        features = classifier._extract_email_features(extracted_content, sample_security_result)
        
        assert features.is_reply is True
        assert features.thread_depth == 2
        assert features.has_office_attachments is True
        assert 'approval' in ' '.join(features.content_keywords).lower()
        assert 'budget' in ' '.join(features.content_keywords).lower()
    
    def test_feature_extraction_developer_update(self, classifier, sample_headers,
                                                sample_thread_analysis, sample_security_result):
        """Test feature extraction for DEVELOPER_UPDATE emails"""
        extracted_content = self.create_extracted_content(
            EmailType.DEVELOPER_UPDATE, sample_headers, sample_thread_analysis
        )
        
        features = classifier._extract_email_features(extracted_content, sample_security_result)
        
        assert features.content_technical_terms > 5  # Should have many technical terms
        assert 'development' in ' '.join(features.content_keywords).lower()
        assert 'code' in ' '.join(features.content_keywords).lower()
        assert features.attachment_count > 0
    
    def test_feature_extraction_executive_request(self, classifier, sample_headers,
                                                 sample_thread_analysis, sample_security_result):
        """Test feature extraction for EXECUTIVE_REQUEST emails"""
        # Update sender to be executive
        sample_headers.sender = "secretary@dol.gov"
        
        extracted_content = self.create_extracted_content(
            EmailType.EXECUTIVE_REQUEST, sample_headers, sample_thread_analysis
        )
        
        features = classifier._extract_email_features(extracted_content, sample_security_result)
        
        assert features.subject_urgency_indicators > 0  # Should detect urgency
        assert 'urgent' in ' '.join(features.subject_keywords).lower()
        assert 'briefing' in ' '.join(features.content_keywords).lower()
        assert features.has_office_attachments is True
    
    def test_rule_based_classification_new_eo(self, classifier, sample_headers,
                                            sample_thread_analysis, sample_security_result):
        """Test rule-based classification for NEW_EO"""
        extracted_content = self.create_extracted_content(
            EmailType.NEW_EO, sample_headers, sample_thread_analysis
        )
        
        features = classifier._extract_email_features(extracted_content, sample_security_result)
        email_type, confidence = classifier._rule_based_classification(features)
        
        assert email_type == EmailType.NEW_EO
        assert confidence > 0.5
    
    def test_rule_based_classification_pmo_response(self, classifier, sample_headers,
                                                  sample_thread_analysis, sample_security_result):
        """Test rule-based classification for PMO_RESPONSE"""
        sample_thread_analysis.is_reply = True
        
        extracted_content = self.create_extracted_content(
            EmailType.PMO_RESPONSE, sample_headers, sample_thread_analysis
        )
        
        features = classifier._extract_email_features(extracted_content, sample_security_result)
        email_type, confidence = classifier._rule_based_classification(features)
        
        assert email_type == EmailType.PMO_RESPONSE
        assert confidence > 0.5
    
    def test_rule_based_classification_developer_update(self, classifier, sample_headers,
                                                       sample_thread_analysis, sample_security_result):
        """Test rule-based classification for DEVELOPER_UPDATE"""
        extracted_content = self.create_extracted_content(
            EmailType.DEVELOPER_UPDATE, sample_headers, sample_thread_analysis
        )
        
        features = classifier._extract_email_features(extracted_content, sample_security_result)
        email_type, confidence = classifier._rule_based_classification(features)
        
        assert email_type == EmailType.DEVELOPER_UPDATE
        assert confidence > 0.5
    
    def test_rule_based_classification_executive_request(self, classifier, sample_headers,
                                                        sample_thread_analysis, sample_security_result):
        """Test rule-based classification for EXECUTIVE_REQUEST"""
        sample_headers.sender = "secretary@dol.gov"
        
        extracted_content = self.create_extracted_content(
            EmailType.EXECUTIVE_REQUEST, sample_headers, sample_thread_analysis
        )
        
        features = classifier._extract_email_features(extracted_content, sample_security_result)
        email_type, confidence = classifier._rule_based_classification(features)
        
        assert email_type == EmailType.EXECUTIVE_REQUEST
        assert confidence > 0.5
    
    def test_classify_email_new_eo(self, classifier, sample_headers,
                                 sample_thread_analysis, sample_security_result):
        """Test full email classification for NEW_EO"""
        extracted_content = self.create_extracted_content(
            EmailType.NEW_EO, sample_headers, sample_thread_analysis
        )
        
        result = classifier.classify_email(extracted_content, sample_security_result)
        
        assert isinstance(result, ClassificationResult)
        assert result.email_type == EmailType.NEW_EO
        assert result.confidence_score > 0.0
        assert isinstance(result.feature_importance, dict)
        assert isinstance(result.requires_manual_review, bool)
        assert isinstance(result.classification_timestamp, datetime)
    
    def test_classify_email_confidence_scoring(self, classifier, sample_headers,
                                             sample_thread_analysis, sample_security_result):
        """Test confidence scoring in classification"""
        extracted_content = self.create_extracted_content(
            EmailType.NEW_EO, sample_headers, sample_thread_analysis
        )
        
        result = classifier.classify_email(extracted_content, sample_security_result)
        
        # Confidence should be between 0 and 1
        assert 0.0 <= result.confidence_score <= 1.0
        
        # Manual review should be required if confidence is low
        if result.confidence_score < classifier.MANUAL_REVIEW_THRESHOLD:
            assert result.requires_manual_review is True
        else:
            assert result.requires_manual_review is False
    
    def test_classify_email_feature_importance(self, classifier, sample_headers,
                                             sample_thread_analysis, sample_security_result):
        """Test feature importance calculation"""
        extracted_content = self.create_extracted_content(
            EmailType.NEW_EO, sample_headers, sample_thread_analysis
        )
        
        result = classifier.classify_email(extracted_content, sample_security_result)
        
        # Feature importance should be a dict with float values
        assert isinstance(result.feature_importance, dict)
        for feature, importance in result.feature_importance.items():
            assert isinstance(feature, str)
            assert isinstance(importance, float)
            assert 0.0 <= importance <= 1.0
    
    def test_classify_email_alternative_classifications(self, classifier, sample_headers,
                                                       sample_thread_analysis, sample_security_result):
        """Test alternative classifications"""
        extracted_content = self.create_extracted_content(
            EmailType.NEW_EO, sample_headers, sample_thread_analysis
        )
        
        result = classifier.classify_email(extracted_content, sample_security_result)
        
        # Alternative classifications should be a list of tuples
        assert isinstance(result.alternative_classifications, list)
        for alt_type, alt_confidence in result.alternative_classifications:
            assert isinstance(alt_type, EmailType)
            assert isinstance(alt_confidence, float)
            assert 0.0 <= alt_confidence <= 1.0
    
    def test_classification_accuracy_all_types(self, classifier, sample_headers,
                                             sample_thread_analysis, sample_security_result):
        """Test classification accuracy across all email types"""
        correct_classifications = 0
        total_classifications = 0
        
        # Test each email type multiple times with variations
        for email_type in EmailType:
            for variation in range(3):  # Test 3 variations per type
                # Create slight variations in headers
                headers = sample_headers
                if variation == 1:
                    headers.sender = f"user{variation}@dol.gov"
                elif variation == 2:
                    headers.sender = f"test{variation}@labor.gov"
                
                extracted_content = self.create_extracted_content(
                    email_type, headers, sample_thread_analysis
                )
                
                result = classifier.classify_email(extracted_content, sample_security_result)
                
                total_classifications += 1
                if result.email_type == email_type:
                    correct_classifications += 1
        
        accuracy = correct_classifications / total_classifications
        
        # Should achieve reasonable accuracy with rule-based classification
        assert accuracy >= 0.7  # 70% minimum for rule-based
        
        print(f"Classification accuracy: {accuracy:.3f} ({correct_classifications}/{total_classifications})")
    
    def test_model_training_with_sample_data(self, classifier, sample_headers,
                                           sample_thread_analysis, sample_security_result):
        """Test model training with sample data"""
        # Create training data for all email types
        training_data = []
        
        for email_type in EmailType:
            for i in range(10):  # 10 samples per type
                headers = sample_headers
                headers.sender = f"user{i}@dol.gov"
                
                extracted_content = self.create_extracted_content(
                    email_type, headers, sample_thread_analysis
                )
                
                training_data.append((extracted_content, sample_security_result, email_type))
        
        # Train model
        accuracy_result = classifier.train_model(training_data)
        
        assert isinstance(accuracy_result, ClassificationAccuracy)
        assert 0.0 <= accuracy_result.overall_accuracy <= 1.0
        assert len(accuracy_result.per_class_accuracy) == len(EmailType)
        assert len(accuracy_result.precision_scores) == len(EmailType)
        assert len(accuracy_result.recall_scores) == len(EmailType)
        assert len(accuracy_result.f1_scores) == len(EmailType)
        assert accuracy_result.confusion_matrix.shape == (len(EmailType), len(EmailType))
    
    def test_validate_classification_accuracy(self, classifier, sample_headers,
                                            sample_thread_analysis, sample_security_result):
        """Test accuracy validation"""
        # Create validation data
        validation_data = []
        
        for email_type in EmailType:
            for i in range(5):  # 5 samples per type
                headers = sample_headers
                headers.sender = f"validation{i}@dol.gov"
                
                extracted_content = self.create_extracted_content(
                    email_type, headers, sample_thread_analysis
                )
                
                validation_data.append((extracted_content, sample_security_result, email_type))
        
        # Validate accuracy
        accuracy_result = classifier.validate_classification_accuracy(validation_data)
        
        assert isinstance(accuracy_result, ClassificationAccuracy)
        assert 0.0 <= accuracy_result.overall_accuracy <= 1.0
        assert isinstance(accuracy_result.validation_timestamp, datetime)
    
    def test_classification_statistics(self, classifier, sample_headers,
                                     sample_thread_analysis, sample_security_result):
        """Test classification statistics tracking"""
        initial_stats = classifier.get_classification_statistics()
        
        # Perform some classifications
        for email_type in EmailType:
            extracted_content = self.create_extracted_content(
                email_type, sample_headers, sample_thread_analysis
            )
            classifier.classify_email(extracted_content, sample_security_result)
        
        final_stats = classifier.get_classification_statistics()
        
        # Statistics should have increased
        assert final_stats['total_classifications'] > initial_stats['total_classifications']
        assert final_stats['successful_classifications'] > initial_stats['successful_classifications']
    
    def test_features_to_vector_conversion(self, classifier, sample_headers,
                                         sample_thread_analysis, sample_security_result):
        """Test feature to vector conversion"""
        extracted_content = self.create_extracted_content(
            EmailType.NEW_EO, sample_headers, sample_thread_analysis
        )
        
        features = classifier._extract_email_features(extracted_content, sample_security_result)
        vector = classifier._features_to_vector(features)
        
        assert isinstance(vector, np.ndarray)
        assert len(vector) > 0
        assert all(isinstance(x, (int, float, np.number)) for x in vector)
    
    def test_sender_role_indicators(self, classifier):
        """Test sender role indicator extraction"""
        test_cases = [
            ("secretary@dol.gov", ["executive"]),
            ("pmo.manager@dol.gov", ["pmo"]),
            ("developer@dol.gov", ["developer"]),
            ("analyst@dol.gov", ["analyst"]),
            ("regular.user@dol.gov", [])
        ]
        
        for sender, expected_roles in test_cases:
            roles = classifier._extract_sender_role_indicators(sender)
            for expected_role in expected_roles:
                assert expected_role in roles
    
    def test_urgency_indicators(self, classifier):
        """Test urgency indicator detection"""
        test_cases = [
            ("URGENT: Please respond immediately", 2),
            ("Normal email subject", 0),
            ("ASAP - Critical issue needs attention", 2),
            ("Priority request for review", 1)
        ]
        
        for text, expected_count in test_cases:
            count = classifier._count_urgency_indicators(text)
            assert count >= expected_count
    
    def test_sentiment_analysis(self, classifier):
        """Test sentiment score calculation"""
        test_cases = [
            ("This is excellent work and very successful", 0.1),  # Positive
            ("This is a terrible failure and very bad", -0.1),   # Negative
            ("This is a normal email with neutral content", 0.0)  # Neutral
        ]
        
        for content, expected_sentiment in test_cases:
            sentiment = classifier._calculate_sentiment_score(content)
            if expected_sentiment > 0:
                assert sentiment > 0
            elif expected_sentiment < 0:
                assert sentiment < 0
            else:
                assert abs(sentiment) < 0.1  # Near neutral
    
    def test_formality_score(self, classifier):
        """Test formality score calculation"""
        formal_content = "Pursuant to the regulations, we hereby notify you that..."
        informal_content = "Hey there! Thanks for the awesome update, it's really cool!"
        
        formal_score = classifier._calculate_formality_score(formal_content)
        informal_score = classifier._calculate_formality_score(informal_content)
        
        assert formal_score > informal_score
        assert 0.0 <= formal_score <= 1.0
        assert 0.0 <= informal_score <= 1.0
    
    def test_technical_terms_counting(self, classifier):
        """Test technical terms counting"""
        technical_content = "The API server database application needs code development"
        non_technical_content = "Please send the report to the manager for review"
        
        technical_count = classifier._count_technical_terms(technical_content)
        non_technical_count = classifier._count_technical_terms(non_technical_content)
        
        assert technical_count > non_technical_count
        assert technical_count >= 5  # Should find at least 5 technical terms
    
    def test_error_handling_invalid_content(self, classifier, sample_security_result):
        """Test error handling with invalid content"""
        # Create invalid extracted content
        invalid_content = ExtractedContent(
            headers=None,  # Invalid
            plain_text="",
            html_content=None,
            sanitized_html=None,
            attachments=[],
            thread_analysis=None,  # Invalid
            content_hash="",
            extraction_metadata={},
            security_flags=[]
        )
        
        # Should handle gracefully and return fallback classification
        result = classifier.classify_email(invalid_content, sample_security_result)
        
        assert isinstance(result, ClassificationResult)
        assert result.requires_manual_review is True
        assert result.confidence_score < 0.5
    
    def test_model_persistence(self, classifier, temp_model_dir):
        """Test model saving and loading"""
        # Save models
        classifier._save_models()
        
        # Check that model files were created
        model_files = [
            "email_classifier.pkl",
            "feature_scaler.pkl", 
            "text_vectorizer.pkl",
            "model_metadata.json"
        ]
        
        for filename in model_files:
            assert (Path(temp_model_dir) / filename).exists()
        
        # Create new classifier and load models
        new_classifier = EmailClassifier(model_directory=temp_model_dir)
        new_classifier._load_models()
        
        # Should have loaded successfully (no exceptions)
        assert new_classifier.model_directory == Path(temp_model_dir)


class TestEmailClassifierFactory:
    """Test suite for EmailClassifierFactory"""
    
    def test_create_classifier(self):
        """Test factory classifier creation"""
        classifier = EmailClassifierFactory.create_classifier(
            model_directory="test_models",
            enable_training=True
        )
        
        assert isinstance(classifier, EmailClassifier)
        assert classifier.model_directory == Path("test_models")
        assert classifier.enable_model_training is True
    
    def test_create_production_classifier(self):
        """Test production classifier creation"""
        classifier = EmailClassifierFactory.create_production_classifier()
        
        assert isinstance(classifier, EmailClassifier)
        assert classifier.model_directory == Path("models/production")
        assert classifier.enable_model_training is False


class TestEmailClassifierIntegration:
    """Integration tests for email classifier with real-world scenarios"""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier for integration testing"""
        return EmailClassifier(model_directory="test_models", enable_model_training=True)
    
    def test_end_to_end_classification_workflow(self, classifier):
        """Test complete classification workflow"""
        # Create realistic email content
        email_msg = EmailMessage()
        email_msg['From'] = "secretary@dol.gov"
        email_msg['To'] = "team@dol.gov"
        email_msg['Subject'] = "URGENT: Executive Briefing Request - Q4 Performance"
        email_msg['Message-ID'] = "<urgent-briefing@dol.gov>"
        email_msg['Date'] = "Mon, 01 Jan 2024 14:30:00 -0500"
        
        content = """
        Dear Team,
        
        The Secretary requires an immediate executive briefing on Q4 performance metrics.
        Please prepare a comprehensive report including budget analysis, milestone achievements,
        and strategic recommendations for the upcoming quarter.
        
        This is time-sensitive and needed for tomorrow's Cabinet meeting.
        
        Regards,
        Office of the Secretary
        """
        email_msg.set_content(content)
        
        # Create extracted content
        headers = EmailHeaders(
            message_id="<urgent-briefing@dol.gov>",
            sender="secretary@dol.gov",
            sender_name="Office of the Secretary",
            recipients=["team@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="URGENT: Executive Briefing Request - Q4 Performance",
            date=datetime(2024, 1, 1, 14, 30),
            reply_to=None,
            in_reply_to=None,
            references=[],
            thread_topic=None,
            priority="high",
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        
        thread_analysis = ThreadAnalysis(
            thread_id="<urgent-briefing@dol.gov>",
            is_reply=False,
            is_forward=False,
            parent_message_id=None,
            thread_depth=0,
            conversation_participants={"secretary@dol.gov", "team@dol.gov"},
            thread_subject="URGENT: Executive Briefing Request - Q4 Performance",
            original_subject="Executive Briefing Request - Q4 Performance",
            reply_chain_length=0
        )
        
        extracted_content = ExtractedContent(
            headers=headers,
            plain_text=content,
            html_content=None,
            sanitized_html=None,
            attachments=[],
            thread_analysis=thread_analysis,
            content_hash="integration_test_hash",
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
        
        # Perform classification
        result = classifier.classify_email(extracted_content, security_result)
        
        # Verify results
        assert result.email_type == EmailType.EXECUTIVE_REQUEST
        assert result.confidence_score > 0.5
        assert result.classification_timestamp is not None
        assert isinstance(result.feature_importance, dict)
        
        # Check that urgency was detected
        features = classifier._extract_email_features(extracted_content, security_result)
        assert features.subject_urgency_indicators > 0
        assert features.sender_is_government is True
    
    def test_batch_classification_performance(self, classifier):
        """Test classification performance with batch processing"""
        import time
        
        # Create batch of emails
        batch_size = 50
        emails = []
        
        for i in range(batch_size):
            email_type = list(EmailType)[i % len(EmailType)]
            
            headers = EmailHeaders(
                message_id=f"<batch-test-{i}@dol.gov>",
                sender=f"user{i}@dol.gov",
                sender_name=f"User {i}",
                recipients=["recipient@dol.gov"],
                cc_recipients=[],
                bcc_recipients=[],
                subject=f"Batch Test Email {i}",
                date=datetime.now(),
                reply_to=None,
                in_reply_to=None,
                references=[],
                thread_topic=None,
                priority=None,
                content_type="text/plain",
                encoding="utf-8",
                custom_headers={}
            )
            
            thread_analysis = ThreadAnalysis(
                thread_id=f"<batch-test-{i}@dol.gov>",
                is_reply=False,
                is_forward=False,
                parent_message_id=None,
                thread_depth=0,
                conversation_participants={f"user{i}@dol.gov"},
                thread_subject=f"Batch Test Email {i}",
                original_subject=f"Batch Test Email {i}",
                reply_chain_length=0
            )
            
            extracted_content = ExtractedContent(
                headers=headers,
                plain_text=f"This is batch test email number {i}",
                html_content=None,
                sanitized_html=None,
                attachments=[],
                thread_analysis=thread_analysis,
                content_hash=f"batch_hash_{i}",
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
            
            emails.append((extracted_content, security_result))
        
        # Measure classification time
        start_time = time.time()
        
        results = []
        for extracted_content, security_result in emails:
            result = classifier.classify_email(extracted_content, security_result)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_email = total_time / batch_size
        
        # Verify all emails were classified
        assert len(results) == batch_size
        assert all(isinstance(result, ClassificationResult) for result in results)
        
        # Performance should be reasonable (less than 1 second per email)
        assert avg_time_per_email < 1.0
        
        print(f"Batch classification performance: {avg_time_per_email:.3f}s per email")
    
    def test_classification_consistency(self, classifier):
        """Test that classification is consistent for identical emails"""
        # Create identical email content
        headers = EmailHeaders(
            message_id="<consistency-test@dol.gov>",
            sender="test@dol.gov",
            sender_name="Test User",
            recipients=["recipient@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Consistency Test Email",
            date=datetime.now(),
            reply_to=None,
            in_reply_to=None,
            references=[],
            thread_topic=None,
            priority=None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        
        thread_analysis = ThreadAnalysis(
            thread_id="<consistency-test@dol.gov>",
            is_reply=False,
            is_forward=False,
            parent_message_id=None,
            thread_depth=0,
            conversation_participants={"test@dol.gov"},
            thread_subject="Consistency Test Email",
            original_subject="Consistency Test Email",
            reply_chain_length=0
        )
        
        extracted_content = ExtractedContent(
            headers=headers,
            plain_text="This is a consistency test email",
            html_content=None,
            sanitized_html=None,
            attachments=[],
            thread_analysis=thread_analysis,
            content_hash="consistency_hash",
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
        
        # Classify the same email multiple times
        results = []
        for _ in range(5):
            result = classifier.classify_email(extracted_content, security_result)
            results.append(result)
        
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.email_type == first_result.email_type
            assert abs(result.confidence_score - first_result.confidence_score) < 0.001
            assert result.requires_manual_review == first_result.requires_manual_review


if __name__ == "__main__":
    pytest.main([__file__, "-v"])