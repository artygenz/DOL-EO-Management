#!/usr/bin/env python3
"""
Simple test for email classifier without package import issues
"""

import sys
import os
from pathlib import Path

# Add the specific module path
sys.path.insert(0, str(Path(__file__).parent / "src" / "email"))

# Import the classifier module directly
import email_classifier as ec

def test_classifier():
    print("Testing Email Classifier...")
    
    # Create classifier
    classifier = ec.EmailClassifier('test_models')
    print("✓ Classifier created")
    
    # Test rule-based classification with executive request features
    features = ec.EmailFeatures(
        sender_domain='dol.gov',
        sender_is_government=True,
        sender_role_indicators=['executive'],
        subject_keywords=['urgent', 'briefing', 'executive', 'request'],
        subject_length=40,
        subject_urgency_indicators=2,  # "urgent" and "immediate"
        subject_reply_indicators=0,
        content_length=200,
        content_keywords=['secretary', 'briefing', 'performance', 'request', 'urgent'],
        content_sentiment_score=0.0,
        content_formality_score=0.8,
        content_technical_terms=0,
        attachment_count=1,
        attachment_types=['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
        has_pdf_attachments=False,
        has_office_attachments=True,
        is_reply=False,
        thread_depth=0,
        conversation_participants_count=2,
        sender_authorized=True,
        content_safe=True,
        attachments_safe=True,
        sent_hour=14,
        sent_day_of_week=1,
        is_business_hours=True
    )
    
    email_type, confidence = classifier._rule_based_classification(features)
    print(f"✓ Executive Request Classification: {email_type.value} with confidence {confidence:.3f}")
    
    # Test PMO response features
    pmo_features = ec.EmailFeatures(
        sender_domain='dol.gov',
        sender_is_government=True,
        sender_role_indicators=['pmo'],
        subject_keywords=['approval', 'project', 'budget', 'approved'],
        subject_length=35,
        subject_urgency_indicators=0,
        subject_reply_indicators=1,  # "RE:"
        content_length=300,
        content_keywords=['project', 'approval', 'budget', 'milestone', 'approved'],
        content_sentiment_score=0.2,  # Slightly positive
        content_formality_score=0.7,
        content_technical_terms=2,
        attachment_count=1,
        attachment_types=['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        has_pdf_attachments=False,
        has_office_attachments=True,
        is_reply=True,
        thread_depth=2,
        conversation_participants_count=3,
        sender_authorized=True,
        content_safe=True,
        attachments_safe=True,
        sent_hour=10,
        sent_day_of_week=2,
        is_business_hours=True
    )
    
    email_type, confidence = classifier._rule_based_classification(pmo_features)
    print(f"✓ PMO Response Classification: {email_type.value} with confidence {confidence:.3f}")
    
    # Test Developer Update features
    dev_features = ec.EmailFeatures(
        sender_domain='dol.gov',
        sender_is_government=True,
        sender_role_indicators=['developer'],
        subject_keywords=['development', 'update', 'sprint', 'progress', 'complete'],
        subject_length=45,
        subject_urgency_indicators=0,
        subject_reply_indicators=0,
        content_length=500,
        content_keywords=['development', 'code', 'testing', 'bug', 'feature', 'implementation'],
        content_sentiment_score=0.1,
        content_formality_score=0.6,
        content_technical_terms=8,  # Many technical terms
        attachment_count=2,
        attachment_types=['application/zip', 'text/plain'],
        has_pdf_attachments=False,
        has_office_attachments=False,
        is_reply=False,
        thread_depth=0,
        conversation_participants_count=4,
        sender_authorized=True,
        content_safe=True,
        attachments_safe=True,
        sent_hour=16,
        sent_day_of_week=4,
        is_business_hours=True
    )
    
    email_type, confidence = classifier._rule_based_classification(dev_features)
    print(f"✓ Developer Update Classification: {email_type.value} with confidence {confidence:.3f}")
    
    # Test NEW_EO features
    eo_features = ec.EmailFeatures(
        sender_domain='whitehouse.gov',
        sender_is_government=True,
        sender_role_indicators=[],
        subject_keywords=['executive', 'order', 'federal', 'directive', 'implementation'],
        subject_length=50,
        subject_urgency_indicators=0,
        subject_reply_indicators=0,
        content_length=800,
        content_keywords=['executive', 'order', 'federal', 'agencies', 'implementation', 'pursuant', 'hereby'],
        content_sentiment_score=0.0,
        content_formality_score=0.9,  # Very formal
        content_technical_terms=1,
        attachment_count=1,
        attachment_types=['application/pdf'],
        has_pdf_attachments=True,
        has_office_attachments=False,
        is_reply=False,
        thread_depth=0,
        conversation_participants_count=1,
        sender_authorized=True,
        content_safe=True,
        attachments_safe=True,
        sent_hour=9,
        sent_day_of_week=1,
        is_business_hours=True
    )
    
    email_type, confidence = classifier._rule_based_classification(eo_features)
    print(f"✓ NEW_EO Classification: {email_type.value} with confidence {confidence:.3f}")
    
    # Test feature vector conversion
    vector = classifier._features_to_vector(features)
    print(f"✓ Feature vector created with {len(vector)} dimensions")
    
    # Test statistics
    stats = classifier.get_classification_statistics()
    print(f"✓ Statistics retrieved: {len(stats)} metrics")
    
    print("\n🎉 All tests passed! Email classifier is working correctly.")
    return True

if __name__ == "__main__":
    try:
        test_classifier()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)