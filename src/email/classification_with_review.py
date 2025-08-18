"""
Enhanced Email Classification with Manual Review Integration

This module integrates the email classifier with the manual review system
to provide confidence-based processing with human-in-the-loop validation.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .email_classifier import EmailClassifier, EmailType, ClassificationResult
from .manual_review_system import (
    ManualReviewSystem, HumanInTheLoopValidator, ReviewPriority,
    ManualReviewItem, ClassificationError
)
from .content_extractor import ExtractedContent
from .security_validator import SecurityValidationResult

logger = logging.getLogger(__name__)


class ProcessingDecision(Enum):
    """Decision on how to process email classification"""
    AUTOMATED_PROCESSING = "AUTOMATED_PROCESSING"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    SECURITY_REVIEW_REQUIRED = "SECURITY_REVIEW_REQUIRED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"


@dataclass
class EnhancedClassificationResult:
    """Enhanced classification result with processing decision"""
    classification_result: ClassificationResult
    processing_decision: ProcessingDecision
    review_id: Optional[str] = None
    decision_reason: str = ""
    confidence_meets_threshold: bool = False
    requires_human_validation: bool = False
    estimated_review_time_hours: float = 0.0


class ClassificationWithReview:
    """
    Enhanced email classification system with integrated manual review.
    
    Provides confidence-based processing decisions, automatic manual review
    creation, and human-in-the-loop validation workflow integration.
    """
    
    def __init__(self, classifier: EmailClassifier, 
                 review_system: ManualReviewSystem,
                 confidence_threshold: float = 0.80):
        """
        Initialize classification with review system.
        
        Args:
            classifier: Email classifier instance
            review_system: Manual review system instance
            confidence_threshold: Minimum confidence for automated processing
        """
        self.classifier = classifier
        self.review_system = review_system
        self.confidence_threshold = confidence_threshold
        
        # Processing statistics
        self.processing_stats = {
            'total_classifications': 0,
            'automated_processing': 0,
            'manual_reviews_created': 0,
            'security_reviews_created': 0,
            'escalations_created': 0,
            'average_confidence_score': 0.0,
            'accuracy_improvement_from_reviews': 0.0
        }
        
        logger.info("Classification with review system initialized")
    
    def classify_with_review_decision(self, extracted_content: ExtractedContent,
                                    security_result: SecurityValidationResult) -> EnhancedClassificationResult:
        """
        Classify email and make processing decision based on confidence and other factors.
        
        Args:
            extracted_content: Extracted email content
            security_result: Security validation result
            
        Returns:
            Enhanced classification result with processing decision
        """
        try:
            self.processing_stats['total_classifications'] += 1
            
            # Perform initial classification
            classification_result = self.classifier.classify_email(
                extracted_content, security_result
            )
            
            # Update average confidence score
            self._update_average_confidence(classification_result.confidence_score)
            
            # Evaluate processing decision
            processing_decision, decision_reason = self._evaluate_processing_decision(
                classification_result, extracted_content, security_result
            )
            
            # Create enhanced result
            enhanced_result = EnhancedClassificationResult(
                classification_result=classification_result,
                processing_decision=processing_decision,
                decision_reason=decision_reason,
                confidence_meets_threshold=classification_result.confidence_score >= self.confidence_threshold,
                requires_human_validation=processing_decision != ProcessingDecision.AUTOMATED_PROCESSING
            )
            
            # Handle processing decision
            if processing_decision == ProcessingDecision.AUTOMATED_PROCESSING:
                self.processing_stats['automated_processing'] += 1
                logger.info(f"Email classified for automated processing: {classification_result.email_type.value}")
                
            elif processing_decision == ProcessingDecision.MANUAL_REVIEW_REQUIRED:
                review_id = self._create_manual_review(
                    classification_result, extracted_content, security_result,
                    ReviewPriority.MEDIUM, decision_reason
                )
                enhanced_result.review_id = review_id
                enhanced_result.estimated_review_time_hours = 24.0
                self.processing_stats['manual_reviews_created'] += 1
                
            elif processing_decision == ProcessingDecision.SECURITY_REVIEW_REQUIRED:
                review_id = self._create_manual_review(
                    classification_result, extracted_content, security_result,
                    ReviewPriority.HIGH, decision_reason
                )
                enhanced_result.review_id = review_id
                enhanced_result.estimated_review_time_hours = 8.0
                self.processing_stats['security_reviews_created'] += 1
                
            elif processing_decision == ProcessingDecision.ESCALATION_REQUIRED:
                review_id = self._create_manual_review(
                    classification_result, extracted_content, security_result,
                    ReviewPriority.CRITICAL, decision_reason
                )
                enhanced_result.review_id = review_id
                enhanced_result.estimated_review_time_hours = 2.0
                self.processing_stats['escalations_created'] += 1
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Classification with review failed: {e}")
            # Return safe fallback
            return self._create_fallback_result(extracted_content)
    
    def process_review_feedback(self, review_id: str, human_classification: EmailType,
                              human_confidence: float, reviewer_notes: str = "") -> bool:
        """
        Process feedback from manual review to improve classification accuracy.
        
        Args:
            review_id: ID of completed review
            human_classification: Human-provided classification
            human_confidence: Human confidence in classification
            reviewer_notes: Optional reviewer notes
            
        Returns:
            True if feedback was processed successfully
        """
        try:
            # Complete the manual review
            success = self.review_system.complete_manual_review(
                review_id, human_classification, human_confidence, reviewer_notes
            )
            
            if success:
                # Check if this creates a classification error
                review_item = self.review_system._load_review_item(review_id)
                if review_item:
                    original_classification = review_item.classification_result.email_type
                    
                    if human_classification != original_classification:
                        # Classification error detected - could trigger retraining
                        logger.info(f"Classification error detected: {original_classification.value} -> {human_classification.value}")
                        
                        # Check if retraining should be triggered
                        if self.review_system.check_retraining_triggers():
                            logger.info("Retraining triggered due to classification errors")
                            self._trigger_model_retraining()
                    
                    # Update accuracy improvement statistics
                    self._update_accuracy_improvement_stats(review_item, human_classification)
                
                logger.info(f"Review feedback processed for {review_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to process review feedback: {e}")
            return False
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        try:
            # Get review system statistics
            review_stats = self.review_system.get_review_statistics()
            
            # Get classifier statistics
            classifier_stats = self.classifier.get_classification_statistics()
            
            # Combine statistics
            combined_stats = {
                'processing': self.processing_stats.copy(),
                'reviews': review_stats,
                'classification': classifier_stats,
                'overall_metrics': {
                    'total_emails_processed': self.processing_stats['total_classifications'],
                    'automation_rate': self._calculate_automation_rate(),
                    'review_queue_size': review_stats.get('current_queue_size', 0),
                    'average_confidence': self.processing_stats['average_confidence_score'],
                    'accuracy_improvement': self.processing_stats['accuracy_improvement_from_reviews']
                }
            }
            
            return combined_stats
            
        except Exception as e:
            logger.error(f"Failed to get processing statistics: {e}")
            return self.processing_stats.copy()
    
    def get_review_recommendations(self, time_window_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recommendations for improving classification accuracy based on recent reviews.
        
        Args:
            time_window_hours: Time window for analysis
            
        Returns:
            List of recommendations
        """
        try:
            recommendations = []
            
            # Get recent classification errors
            recent_errors = self.review_system.detect_classification_errors(time_window_hours)
            
            if not recent_errors:
                return recommendations
            
            # Analyze error patterns
            error_patterns = self._analyze_error_patterns(recent_errors)
            
            # Generate recommendations based on patterns
            for pattern, count in error_patterns.items():
                if count >= 3:  # Significant pattern
                    recommendations.append({
                        'type': 'classification_improvement',
                        'pattern': pattern,
                        'frequency': count,
                        'recommendation': self._generate_pattern_recommendation(pattern),
                        'priority': 'HIGH' if count >= 5 else 'MEDIUM'
                    })
            
            # Check if retraining is recommended
            if len(recent_errors) >= 5:
                recommendations.append({
                    'type': 'model_retraining',
                    'reason': f'{len(recent_errors)} errors in {time_window_hours} hours',
                    'recommendation': 'Consider retraining the classification model with recent feedback',
                    'priority': 'HIGH' if len(recent_errors) >= 10 else 'MEDIUM'
                })
            
            # Check confidence threshold adjustment
            avg_confidence = sum(error.confidence_score for error in recent_errors) / len(recent_errors)
            if avg_confidence > 0.75:  # High confidence but still errors
                recommendations.append({
                    'type': 'threshold_adjustment',
                    'current_threshold': self.confidence_threshold,
                    'suggested_threshold': min(0.85, self.confidence_threshold + 0.05),
                    'recommendation': 'Consider raising confidence threshold to reduce false positives',
                    'priority': 'MEDIUM'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get review recommendations: {e}")
            return []
    
    def _evaluate_processing_decision(self, classification_result: ClassificationResult,
                                    extracted_content: ExtractedContent,
                                    security_result: SecurityValidationResult) -> Tuple[ProcessingDecision, str]:
        """Evaluate what processing decision should be made"""
        
        # Check for critical security issues first
        if not security_result.sender_authorized:
            return ProcessingDecision.SECURITY_REVIEW_REQUIRED, "Sender not authorized"
        
        if security_result.threat_level in ["HIGH", "CRITICAL"]:
            return ProcessingDecision.ESCALATION_REQUIRED, f"High threat level: {security_result.threat_level}"
        
        if security_result.threat_level == "MEDIUM":
            return ProcessingDecision.SECURITY_REVIEW_REQUIRED, "Medium threat level detected"
        
        # Check for executive communications
        if self._is_executive_communication(extracted_content):
            return ProcessingDecision.ESCALATION_REQUIRED, "Executive-level communication"
        
        # Check for urgent content
        if self._is_urgent_content(extracted_content):
            return ProcessingDecision.MANUAL_REVIEW_REQUIRED, "Urgent content detected"
        
        # Check confidence threshold
        if classification_result.confidence_score < self.confidence_threshold:
            return ProcessingDecision.MANUAL_REVIEW_REQUIRED, f"Confidence {classification_result.confidence_score:.3f} below threshold {self.confidence_threshold}"
        
        # Check for ambiguous classification
        if self._is_ambiguous_classification(classification_result):
            return ProcessingDecision.MANUAL_REVIEW_REQUIRED, "Ambiguous classification with close alternatives"
        
        # All checks passed - can process automatically
        return ProcessingDecision.AUTOMATED_PROCESSING, "High confidence classification with no risk factors"
    
    def _create_manual_review(self, classification_result: ClassificationResult,
                            extracted_content: ExtractedContent,
                            security_result: SecurityValidationResult,
                            priority: ReviewPriority,
                            reason: str) -> str:
        """Create manual review item"""
        return self.review_system.create_manual_review(
            classification_result, extracted_content, security_result, priority, reason
        )
    
    def _is_executive_communication(self, extracted_content: ExtractedContent) -> bool:
        """Check if email is from executive-level sender"""
        executive_indicators = ['secretary', 'director', 'deputy', 'chief', 'administrator']
        sender_lower = extracted_content.headers.sender.lower()
        return any(indicator in sender_lower for indicator in executive_indicators)
    
    def _is_urgent_content(self, extracted_content: ExtractedContent) -> bool:
        """Check if email contains urgent content"""
        urgent_keywords = ['urgent', 'critical', 'emergency', 'immediate', 'asap']
        content_text = (extracted_content.headers.subject + " " + 
                       extracted_content.plain_text).lower()
        return any(keyword in content_text for keyword in urgent_keywords)
    
    def _is_ambiguous_classification(self, classification_result: ClassificationResult) -> bool:
        """Check if classification is ambiguous"""
        if not classification_result.alternative_classifications:
            return False
        
        top_alternative = classification_result.alternative_classifications[0]
        confidence_gap = classification_result.confidence_score - top_alternative[1]
        return confidence_gap < 0.2  # Small gap indicates ambiguity
    
    def _update_average_confidence(self, new_confidence: float):
        """Update running average confidence score"""
        current_avg = self.processing_stats['average_confidence_score']
        total_classifications = self.processing_stats['total_classifications']
        
        if total_classifications <= 1:
            self.processing_stats['average_confidence_score'] = new_confidence
        else:
            self.processing_stats['average_confidence_score'] = (
                (current_avg * (total_classifications - 1) + new_confidence) / total_classifications
            )
    
    def _calculate_automation_rate(self) -> float:
        """Calculate automation rate percentage"""
        total = self.processing_stats['total_classifications']
        automated = self.processing_stats['automated_processing']
        return (automated / total * 100) if total > 0 else 0.0
    
    def _trigger_model_retraining(self):
        """Trigger model retraining (placeholder for actual implementation)"""
        logger.info("Model retraining would be triggered here")
        # In a full implementation, this would:
        # 1. Collect recent classification errors
        # 2. Prepare training data with corrections
        # 3. Retrain the model
        # 4. Validate new model accuracy
        # 5. Deploy new model if accuracy improves
    
    def _update_accuracy_improvement_stats(self, review_item: ManualReviewItem, 
                                         human_classification: EmailType):
        """Update accuracy improvement statistics from review feedback"""
        original_classification = review_item.classification_result.email_type
        
        if human_classification != original_classification:
            # This was a classification error that human corrected
            # Update improvement statistics (simplified calculation)
            current_improvement = self.processing_stats['accuracy_improvement_from_reviews']
            self.processing_stats['accuracy_improvement_from_reviews'] = min(
                current_improvement + 0.01, 0.10  # Cap at 10% improvement
            )
    
    def _analyze_error_patterns(self, errors: List[ClassificationError]) -> Dict[str, int]:
        """Analyze patterns in classification errors"""
        patterns = {}
        
        for error in errors:
            # Pattern: predicted -> actual
            pattern = f"{error.predicted_type.value} -> {error.actual_type.value}"
            patterns[pattern] = patterns.get(pattern, 0) + 1
        
        return patterns
    
    def _generate_pattern_recommendation(self, pattern: str) -> str:
        """Generate recommendation based on error pattern"""
        if "DEVELOPER_UPDATE -> PMO_RESPONSE" in pattern:
            return "Consider improving detection of PMO-related keywords in developer communications"
        elif "NEW_EO -> EXECUTIVE_REQUEST" in pattern:
            return "Review executive order detection patterns to distinguish from general executive requests"
        elif "PMO_RESPONSE -> DEVELOPER_UPDATE" in pattern:
            return "Improve sender role detection for PMO vs developer communications"
        else:
            return f"Review classification features for pattern: {pattern}"
    
    def _create_fallback_result(self, extracted_content: ExtractedContent) -> EnhancedClassificationResult:
        """Create fallback result on error"""
        fallback_classification = ClassificationResult(
            email_type=EmailType.DEVELOPER_UPDATE,
            confidence_score=0.1,
            feature_importance={},
            classification_metadata={'error': 'classification_failed'},
            requires_manual_review=True,
            alternative_classifications=[],
            classification_timestamp=datetime.utcnow()
        )
        
        return EnhancedClassificationResult(
            classification_result=fallback_classification,
            processing_decision=ProcessingDecision.MANUAL_REVIEW_REQUIRED,
            decision_reason="Classification system error - requires manual review",
            confidence_meets_threshold=False,
            requires_human_validation=True,
            estimated_review_time_hours=24.0
        )


class ReviewWorkflowManager:
    """
    Manager for coordinating review workflows and human validator assignments.
    """
    
    def __init__(self, review_system: ManualReviewSystem):
        """
        Initialize workflow manager.
        
        Args:
            review_system: Manual review system instance
        """
        self.review_system = review_system
        self.validators: Dict[str, HumanInTheLoopValidator] = {}
        self.active_sessions: Dict[str, str] = {}  # validator_id -> review_id
        
    def register_validator(self, validator_id: str) -> HumanInTheLoopValidator:
        """
        Register human validator for review workflow.
        
        Args:
            validator_id: Unique identifier for validator
            
        Returns:
            HumanInTheLoopValidator instance
        """
        validator = HumanInTheLoopValidator(self.review_system)
        self.validators[validator_id] = validator
        
        logger.info(f"Registered validator: {validator_id}")
        return validator
    
    def assign_next_review(self, validator_id: str) -> Optional[Dict[str, Any]]:
        """
        Assign next review item to validator.
        
        Args:
            validator_id: ID of validator to assign review to
            
        Returns:
            Review context dictionary or None if no reviews available
        """
        try:
            if validator_id not in self.validators:
                logger.error(f"Validator {validator_id} not registered")
                return None
            
            validator = self.validators[validator_id]
            
            # Start review session
            review_item = validator.start_review_session(validator_id)
            
            if review_item:
                self.active_sessions[validator_id] = review_item.review_id
                
                # Get review context
                context = validator.get_review_context(review_item.review_id)
                
                logger.info(f"Assigned review {review_item.review_id} to validator {validator_id}")
                return context
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to assign review to {validator_id}: {e}")
            return None
    
    def submit_review_result(self, validator_id: str, human_classification: EmailType,
                           confidence: float, notes: str = "") -> bool:
        """
        Submit review result from validator.
        
        Args:
            validator_id: ID of validator submitting result
            human_classification: Human-provided classification
            confidence: Human confidence in classification
            notes: Optional reviewer notes
            
        Returns:
            True if result was submitted successfully
        """
        try:
            if validator_id not in self.validators:
                logger.error(f"Validator {validator_id} not registered")
                return False
            
            if validator_id not in self.active_sessions:
                logger.error(f"No active session for validator {validator_id}")
                return False
            
            validator = self.validators[validator_id]
            review_id = self.active_sessions[validator_id]
            
            # Submit decision
            success = validator.submit_review_decision(
                review_id, human_classification, confidence, notes
            )
            
            if success:
                # Remove from active sessions
                del self.active_sessions[validator_id]
                logger.info(f"Review result submitted by {validator_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to submit review result from {validator_id}: {e}")
            return False
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get current workflow status.
        
        Returns:
            Dictionary with workflow status information
        """
        try:
            queue_stats = self.review_system.get_review_statistics()
            
            status = {
                'total_validators': len(self.validators),
                'active_sessions': len(self.active_sessions),
                'pending_reviews': queue_stats.get('current_queue_size', 0),
                'priority_breakdown': queue_stats.get('priority_breakdown', {}),
                'validator_assignments': {
                    validator_id: self.active_sessions.get(validator_id, 'idle')
                    for validator_id in self.validators.keys()
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")
            return {}