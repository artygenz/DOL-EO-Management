"""
Manual Review System Demo

Demonstrates the confidence-based manual review system with human-in-the-loop
validation workflow for email classification.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import tempfile
from datetime import datetime
from pathlib import Path

from src.email.email_classifier import EmailClassifier, EmailType
from src.email.manual_review_system import (
    ManualReviewSystem, HumanInTheLoopValidator, ReviewPriority
)
from src.email.classification_with_review import (
    ClassificationWithReview, ReviewWorkflowManager
)
from src.email.content_extractor import ExtractedContent, EmailHeaders, ThreadAnalysis
from src.email.security_validator import SecurityValidationResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_email(email_type: EmailType, confidence_level: str = "high") -> tuple:
    """Create sample email data for testing"""
    
    # Create headers based on email type
    if email_type == EmailType.NEW_EO:
        sender = "policy.director@whitehouse.gov"
        subject = "Executive Order 14001 - Implementation Guidance"
        content = """
        Pursuant to Executive Order 14001, all federal agencies shall implement
        the following requirements effective immediately. This directive establishes
        new compliance standards for government operations.
        """
    elif email_type == EmailType.PMO_RESPONSE:
        sender = "pmo.manager@dol.gov"
        subject = "Re: Project Milestone Approval Request"
        content = """
        The project milestone has been reviewed and approved. Budget allocation
        is confirmed and resources are available for the next phase.
        """
    elif email_type == EmailType.DEVELOPER_UPDATE:
        sender = "dev.engineer@dol.gov"
        subject = "Development Progress Update - 75% Complete"
        content = """
        Development progress update: API implementation is 75% complete.
        Testing framework is in place and unit tests are passing.
        No blockers at this time.
        """
    elif email_type == EmailType.EXECUTIVE_REQUEST:
        sender = "secretary@dol.gov"
        subject = "Urgent: Dashboard Report Request"
        content = """
        I need the quarterly performance dashboard report prepared for
        tomorrow's executive briefing. Please prioritize this request.
        """
    else:
        sender = "unknown@example.com"
        subject = "Unclear email type"
        content = "This email is ambiguous and hard to classify."
    
    # Adjust content for confidence level
    if confidence_level == "low":
        # Make content more ambiguous
        content = "Please review the attached document and provide feedback."
        subject = "Document Review"
    elif confidence_level == "medium":
        # Mix characteristics from different types
        content += " Please review and provide development feedback on the implementation."
    
    # Create email headers
    headers = EmailHeaders(
        message_id=f"<{email_type.value.lower()}@example.com>",
        sender=sender,
        sender_name="Test User",
        recipients=["recipient@dol.gov"],
        cc_recipients=[],
        bcc_recipients=[],
        subject=subject,
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
    
    # Create thread analysis
    thread_analysis = ThreadAnalysis(
        thread_id=f"thread-{email_type.value}",
        is_reply=email_type == EmailType.PMO_RESPONSE,
        is_forward=False,
        parent_message_id=None,
        thread_depth=1 if email_type == EmailType.PMO_RESPONSE else 0,
        conversation_participants={sender},
        thread_subject=subject,
        original_subject=subject,
        reply_chain_length=0
    )
    
    # Create extracted content
    extracted_content = ExtractedContent(
        headers=headers,
        plain_text=content,
        html_content=f"<p>{content}</p>",
        sanitized_html=f"<p>{content}</p>",
        attachments=[],
        thread_analysis=thread_analysis,
        content_hash=f"hash-{email_type.value}",
        extraction_metadata={},
        security_flags=[]
    )
    
    # Create security result
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
    
    return extracted_content, security_result


def demonstrate_confidence_threshold_enforcement():
    """Demonstrate confidence threshold enforcement"""
    print("\n" + "="*60)
    print("CONFIDENCE THRESHOLD ENFORCEMENT DEMO")
    print("="*60)
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        # Initialize systems
        classifier = EmailClassifier(enable_model_training=False)
        review_system = ManualReviewSystem(database_path=temp_db.name)
        classification_with_review = ClassificationWithReview(
            classifier, review_system, confidence_threshold=0.80
        )
        
        # Test different confidence scenarios
        test_cases = [
            ("High confidence NEW_EO", EmailType.NEW_EO, "high"),
            ("Low confidence DEVELOPER_UPDATE", EmailType.DEVELOPER_UPDATE, "low"),
            ("Medium confidence PMO_RESPONSE", EmailType.PMO_RESPONSE, "medium"),
            ("Executive request (always reviewed)", EmailType.EXECUTIVE_REQUEST, "high")
        ]
        
        for case_name, email_type, confidence_level in test_cases:
            print(f"\nTesting: {case_name}")
            print("-" * 40)
            
            # Create sample email
            extracted_content, security_result = create_sample_email(email_type, confidence_level)
            
            # Classify with review decision
            result = classification_with_review.classify_with_review_decision(
                extracted_content, security_result
            )
            
            print(f"Classification: {result.classification_result.email_type.value}")
            print(f"Confidence: {result.classification_result.confidence_score:.3f}")
            print(f"Processing Decision: {result.processing_decision.value}")
            print(f"Reason: {result.decision_reason}")
            
            if result.review_id:
                print(f"Review ID: {result.review_id}")
                print(f"Estimated Review Time: {result.estimated_review_time_hours} hours")
        
        # Show processing statistics
        print(f"\nProcessing Statistics:")
        stats = classification_with_review.get_processing_statistics()
        processing_stats = stats['processing']
        print(f"Total Classifications: {processing_stats['total_classifications']}")
        print(f"Automated Processing: {processing_stats['automated_processing']}")
        print(f"Manual Reviews Created: {processing_stats['manual_reviews_created']}")
        print(f"Automation Rate: {stats['overall_metrics']['automation_rate']:.1f}%")
        
    finally:
        # Cleanup
        Path(temp_db.name).unlink(missing_ok=True)


def demonstrate_manual_review_workflow():
    """Demonstrate manual review workflow with human validator"""
    print("\n" + "="*60)
    print("MANUAL REVIEW WORKFLOW DEMO")
    print("="*60)
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        # Initialize systems
        classifier = EmailClassifier(enable_model_training=False)
        review_system = ManualReviewSystem(database_path=temp_db.name)
        workflow_manager = ReviewWorkflowManager(review_system)
        
        # Register human validator
        validator_id = "human-reviewer-001"
        validator = workflow_manager.register_validator(validator_id)
        
        print(f"Registered validator: {validator_id}")
        
        # Create some emails that need review
        emails_for_review = [
            ("Ambiguous email 1", EmailType.DEVELOPER_UPDATE, "low"),
            ("Ambiguous email 2", EmailType.PMO_RESPONSE, "low"),
            ("Executive communication", EmailType.EXECUTIVE_REQUEST, "high")
        ]
        
        review_ids = []
        
        for case_name, email_type, confidence_level in emails_for_review:
            print(f"\nCreating review for: {case_name}")
            
            # Create sample email
            extracted_content, security_result = create_sample_email(email_type, confidence_level)
            
            # Create classification result with low confidence
            from src.email.email_classifier import ClassificationResult
            classification_result = ClassificationResult(
                email_type=email_type,
                confidence_score=0.65,  # Below threshold
                feature_importance={'content': 0.5},
                classification_metadata={'model_version': 'v1.0.0'},
                requires_manual_review=True,
                alternative_classifications=[(EmailType.DEVELOPER_UPDATE, 0.60)],
                classification_timestamp=datetime.utcnow()
            )
            
            # Create manual review
            priority = ReviewPriority.CRITICAL if "Executive" in case_name else ReviewPriority.MEDIUM
            review_id = review_system.create_manual_review(
                classification_result, extracted_content, security_result,
                priority, f"Low confidence: {case_name}"
            )
            
            review_ids.append(review_id)
            print(f"Created review: {review_id}")
        
        # Show queue status
        print(f"\nReview Queue Status:")
        queue_stats = review_system.get_review_statistics()
        print(f"Total items in queue: {queue_stats['current_queue_size']}")
        print(f"Priority breakdown: {queue_stats['priority_breakdown']}")
        
        # Simulate human reviewer workflow
        print(f"\n" + "-"*40)
        print("HUMAN REVIEWER WORKFLOW")
        print("-"*40)
        
        # Process reviews one by one
        for i in range(len(review_ids)):
            print(f"\nReviewer session {i+1}:")
            
            # Assign next review
            review_context = workflow_manager.assign_next_review(validator_id)
            
            if review_context:
                print(f"Assigned review: {review_context['review_id']}")
                print(f"Email subject: {review_context['email_subject']}")
                print(f"Original classification: {review_context['original_classification']}")
                print(f"Confidence: {review_context['confidence_score']:.3f}")
                print(f"Priority: {review_context['review_priority']}")
                
                # Simulate human decision
                original_type = EmailType(review_context['original_classification'])
                
                # Simulate human correcting some classifications
                if i == 0:  # First review - human agrees
                    human_classification = original_type
                    human_confidence = 0.90
                    notes = "Classification looks correct"
                elif i == 1:  # Second review - human corrects
                    human_classification = EmailType.DEVELOPER_UPDATE
                    human_confidence = 0.85
                    notes = "This is actually a developer update, not PMO response"
                else:  # Third review - human agrees
                    human_classification = original_type
                    human_confidence = 0.95
                    notes = "Executive request confirmed"
                
                print(f"Human decision: {human_classification.value} (confidence: {human_confidence:.2f})")
                print(f"Notes: {notes}")
                
                # Submit review result
                success = workflow_manager.submit_review_result(
                    validator_id, human_classification, human_confidence, notes
                )
                
                if success:
                    print("Review submitted successfully")
                else:
                    print("Failed to submit review")
            else:
                print("No more reviews available")
                break
        
        # Show final statistics
        print(f"\nFinal Statistics:")
        final_stats = review_system.get_review_statistics()
        print(f"Total reviews created: {final_stats['total_reviews_created']}")
        print(f"Total reviews completed: {final_stats['total_reviews_completed']}")
        print(f"Reviews approved: {final_stats['total_reviews_approved']}")
        print(f"Reviews rejected: {final_stats['total_reviews_rejected']}")
        print(f"Classification errors detected: {final_stats['total_errors_detected']}")
        
        # Check if retraining would be triggered
        should_retrain = review_system.check_retraining_triggers()
        print(f"Retraining triggered: {should_retrain}")
        
    finally:
        # Cleanup
        Path(temp_db.name).unlink(missing_ok=True)


def demonstrate_error_detection_and_retraining():
    """Demonstrate classification error detection and retraining triggers"""
    print("\n" + "="*60)
    print("ERROR DETECTION AND RETRAINING DEMO")
    print("="*60)
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        # Initialize systems
        review_system = ManualReviewSystem(database_path=temp_db.name)
        
        # Simulate multiple classification errors
        print("Simulating classification errors...")
        
        error_scenarios = [
            (EmailType.DEVELOPER_UPDATE, EmailType.PMO_RESPONSE, 0.75),
            (EmailType.NEW_EO, EmailType.EXECUTIVE_REQUEST, 0.80),
            (EmailType.PMO_RESPONSE, EmailType.DEVELOPER_UPDATE, 0.70),
            (EmailType.DEVELOPER_UPDATE, EmailType.PMO_RESPONSE, 0.85),
            (EmailType.NEW_EO, EmailType.EXECUTIVE_REQUEST, 0.78),
        ]
        
        for i, (predicted, actual, confidence) in enumerate(error_scenarios):
            # Create sample email and classification
            extracted_content, security_result = create_sample_email(predicted, "medium")
            
            from src.email.email_classifier import ClassificationResult
            classification_result = ClassificationResult(
                email_type=predicted,
                confidence_score=confidence,
                feature_importance={'content': 0.5},
                classification_metadata={'model_version': 'v1.0.0'},
                requires_manual_review=True,
                alternative_classifications=[(actual, confidence - 0.10)],
                classification_timestamp=datetime.utcnow()
            )
            
            # Create review and complete with correction
            review_id = review_system.create_manual_review(
                classification_result, extracted_content, security_result,
                ReviewPriority.MEDIUM, f"Error simulation {i+1}"
            )
            
            # Complete review with human correction
            review_system.complete_manual_review(
                review_id, actual, 0.90, f"Corrected classification {i+1}"
            )
            
            print(f"Error {i+1}: {predicted.value} -> {actual.value} (confidence: {confidence:.2f})")
        
        # Detect classification errors
        print(f"\nDetecting classification errors...")
        recent_errors = review_system.detect_classification_errors(24)
        print(f"Found {len(recent_errors)} classification errors")
        
        # Analyze error patterns
        error_patterns = {}
        for error in recent_errors:
            pattern = f"{error.predicted_type.value} -> {error.actual_type.value}"
            error_patterns[pattern] = error_patterns.get(pattern, 0) + 1
        
        print(f"\nError patterns:")
        for pattern, count in error_patterns.items():
            print(f"  {pattern}: {count} occurrences")
        
        # Check retraining triggers
        print(f"\nChecking retraining triggers...")
        should_retrain = review_system.check_retraining_triggers()
        print(f"Retraining should be triggered: {should_retrain}")
        
        if should_retrain:
            print("Retraining would be initiated due to:")
            print(f"  - {len(recent_errors)} errors detected")
            print(f"  - Error patterns indicate systematic issues")
            print(f"  - Accuracy may have degraded below threshold")
        
        # Show recommendations
        classifier = EmailClassifier(enable_model_training=False)
        classification_with_review = ClassificationWithReview(classifier, review_system)
        
        recommendations = classification_with_review.get_review_recommendations(24)
        
        if recommendations:
            print(f"\nRecommendations for improvement:")
            for rec in recommendations:
                print(f"  - {rec['type']}: {rec['recommendation']} (Priority: {rec['priority']})")
        
    finally:
        # Cleanup
        Path(temp_db.name).unlink(missing_ok=True)


def main():
    """Run all manual review system demonstrations"""
    print("MANUAL REVIEW SYSTEM DEMONSTRATION")
    print("="*60)
    print("This demo shows the confidence-based manual review system")
    print("with human-in-the-loop validation for email classification.")
    
    try:
        # Run demonstrations
        demonstrate_confidence_threshold_enforcement()
        demonstrate_manual_review_workflow()
        demonstrate_error_detection_and_retraining()
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nKey features demonstrated:")
        print("✓ Confidence threshold enforcement (80% minimum)")
        print("✓ Manual review queue with priority handling")
        print("✓ Human-in-the-loop validation workflow")
        print("✓ Classification error detection and tracking")
        print("✓ Model retraining triggers based on error patterns")
        print("✓ Comprehensive statistics and recommendations")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\nDemo failed with error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())