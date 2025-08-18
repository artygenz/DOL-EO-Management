"""
Confidence-Based Manual Review System for Email Classification

This module implements a comprehensive manual review system that handles
ambiguous email classifications, manages human-in-the-loop validation,
and triggers model retraining based on classification errors.
"""

import logging
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import sqlite3
import threading
from queue import Queue, Empty
import uuid

from .email_classifier import EmailType, ClassificationResult, EmailFeatures, ClassificationAccuracy
from .content_extractor import ExtractedContent
from .security_validator import SecurityValidationResult

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Status of manual review items"""
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    TIMEOUT = "TIMEOUT"


class ReviewPriority(Enum):
    """Priority levels for manual review"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ErrorType(Enum):
    """Types of classification errors"""
    FALSE_POSITIVE = "FALSE_POSITIVE"
    FALSE_NEGATIVE = "FALSE_NEGATIVE"
    WRONG_CLASSIFICATION = "WRONG_CLASSIFICATION"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    AMBIGUOUS_CONTENT = "AMBIGUOUS_CONTENT"


@dataclass
class ManualReviewItem:
    """Item requiring manual review"""
    review_id: str
    email_uid: str
    message_id: str
    extracted_content: ExtractedContent
    security_result: SecurityValidationResult
    classification_result: ClassificationResult
    review_status: ReviewStatus
    review_priority: ReviewPriority
    created_timestamp: datetime
    assigned_reviewer: Optional[str] = None
    review_deadline: Optional[datetime] = None
    reviewer_notes: str = ""
    human_classification: Optional[EmailType] = None
    human_confidence: Optional[float] = None
    review_completed_timestamp: Optional[datetime] = None
    escalation_reason: Optional[str] = None
    retry_count: int = 0


@dataclass
class ClassificationError:
    """Record of classification error for model improvement"""
    error_id: str
    email_uid: str
    message_id: str
    predicted_type: EmailType
    actual_type: EmailType
    confidence_score: float
    error_type: ErrorType
    error_timestamp: datetime
    features_snapshot: Dict[str, Any]
    reviewer_feedback: str = ""
    model_version: str = ""
    retraining_triggered: bool = False


@dataclass
class RetrainingTrigger:
    """Trigger for model retraining based on error patterns"""
    trigger_id: str
    trigger_type: str
    error_count: int
    accuracy_threshold: float
    time_window_hours: int
    triggered_timestamp: datetime
    retraining_completed: bool = False
    new_model_accuracy: Optional[float] = None


class ManualReviewQueue:
    """Thread-safe queue for managing manual review items"""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize manual review queue.
        
        Args:
            max_size: Maximum number of items in queue
        """
        self._queue = Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._items_by_priority = {priority: [] for priority in ReviewPriority}
        
    def add_item(self, item: ManualReviewItem) -> bool:
        """
        Add item to review queue.
        
        Args:
            item: Manual review item to add
            
        Returns:
            True if item was added successfully
        """
        try:
            with self._lock:
                # Add to priority-based storage
                self._items_by_priority[item.review_priority].append(item)
                
                # Add to main queue (priority order)
                self._queue.put(item, block=False)
                
            logger.info(f"Added review item {item.review_id} with priority {item.review_priority.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add review item: {e}")
            return False
    
    def get_next_item(self, timeout: float = 1.0) -> Optional[ManualReviewItem]:
        """
        Get next item from queue (highest priority first).
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Next review item or None if timeout
        """
        try:
            # Get highest priority item first
            with self._lock:
                for priority in [ReviewPriority.CRITICAL, ReviewPriority.HIGH, 
                               ReviewPriority.MEDIUM, ReviewPriority.LOW]:
                    if self._items_by_priority[priority]:
                        item = self._items_by_priority[priority].pop(0)
                        return item
            
            # Fallback to regular queue
            return self._queue.get(timeout=timeout)
            
        except Empty:
            return None
        except Exception as e:
            logger.error(f"Failed to get next review item: {e}")
            return None
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self._queue.qsize()
    
    def get_priority_counts(self) -> Dict[ReviewPriority, int]:
        """Get count of items by priority"""
        with self._lock:
            return {priority: len(items) for priority, items in self._items_by_priority.items()}


class ManualReviewSystem:
    """
    Comprehensive manual review system for email classification.
    
    Handles confidence threshold enforcement, manual review queue management,
    classification error detection, and model retraining triggers.
    """
    
    # Configuration constants
    CONFIDENCE_THRESHOLD = 0.80  # Minimum confidence for automated processing
    MANUAL_REVIEW_TIMEOUT_HOURS = 24  # Hours before review times out
    ERROR_THRESHOLD_FOR_RETRAINING = 10  # Number of errors to trigger retraining
    ACCURACY_THRESHOLD_FOR_RETRAINING = 0.85  # Accuracy below which to retrain
    RETRAINING_WINDOW_HOURS = 168  # 7 days window for error analysis
    
    def __init__(self, database_path: str = "manual_review.db", 
                 enable_auto_retraining: bool = True):
        """
        Initialize manual review system.
        
        Args:
            database_path: Path to SQLite database for persistence
            enable_auto_retraining: Whether to enable automatic model retraining
        """
        self.database_path = database_path
        self.enable_auto_retraining = enable_auto_retraining
        
        # Initialize components
        self.review_queue = ManualReviewQueue()
        self.classification_errors: List[ClassificationError] = []
        self.retraining_triggers: List[RetrainingTrigger] = []
        
        # Statistics tracking
        self.review_stats = {
            'total_reviews_created': 0,
            'total_reviews_completed': 0,
            'total_reviews_approved': 0,
            'total_reviews_rejected': 0,
            'total_errors_detected': 0,
            'total_retraining_triggered': 0,
            'average_review_time_hours': 0.0,
            'current_queue_size': 0
        }
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Manual review system initialized with database: {database_path}")
    
    def evaluate_classification_confidence(self, classification_result: ClassificationResult,
                                         extracted_content: ExtractedContent,
                                         security_result: SecurityValidationResult) -> bool:
        """
        Evaluate if classification meets confidence threshold for automated processing.
        
        Args:
            classification_result: Result from email classifier
            extracted_content: Extracted email content
            security_result: Security validation result
            
        Returns:
            True if classification can be processed automatically, False if manual review needed
        """
        try:
            # Check basic confidence threshold
            if classification_result.confidence_score < self.CONFIDENCE_THRESHOLD:
                logger.info(f"Classification confidence {classification_result.confidence_score:.3f} "
                           f"below threshold {self.CONFIDENCE_THRESHOLD}, requiring manual review")
                return False
            
            # Additional checks for ambiguous classifications
            if self._is_ambiguous_classification(classification_result):
                logger.info("Classification is ambiguous, requiring manual review")
                return False
            
            # Check for security concerns that require human validation
            if self._requires_security_review(security_result):
                logger.info("Security validation requires human review")
                return False
            
            # Check for content patterns that typically require review
            if self._requires_content_review(extracted_content, classification_result):
                logger.info("Content patterns require human review")
                return False
            
            logger.debug(f"Classification approved for automated processing with confidence "
                        f"{classification_result.confidence_score:.3f}")
            return True
            
        except Exception as e:
            logger.error(f"Error evaluating classification confidence: {e}")
            # Default to manual review on error
            return False
    
    def create_manual_review(self, classification_result: ClassificationResult,
                           extracted_content: ExtractedContent,
                           security_result: SecurityValidationResult,
                           priority: ReviewPriority = ReviewPriority.MEDIUM,
                           reason: str = "Low confidence classification") -> str:
        """
        Create manual review item for ambiguous classification.
        
        Args:
            classification_result: Classification result requiring review
            extracted_content: Extracted email content
            security_result: Security validation result
            priority: Review priority level
            reason: Reason for manual review
            
        Returns:
            Review ID for tracking
        """
        try:
            review_id = str(uuid.uuid4())
            
            # Determine review deadline based on priority
            deadline_hours = {
                ReviewPriority.CRITICAL: 2,
                ReviewPriority.HIGH: 8,
                ReviewPriority.MEDIUM: 24,
                ReviewPriority.LOW: 72
            }
            
            review_deadline = datetime.utcnow() + timedelta(
                hours=deadline_hours.get(priority, 24)
            )
            
            # Create review item
            review_item = ManualReviewItem(
                review_id=review_id,
                email_uid=extracted_content.headers.message_id,
                message_id=extracted_content.headers.message_id,
                extracted_content=extracted_content,
                security_result=security_result,
                classification_result=classification_result,
                review_status=ReviewStatus.PENDING,
                review_priority=priority,
                created_timestamp=datetime.utcnow(),
                review_deadline=review_deadline,
                escalation_reason=reason
            )
            
            # Add to queue
            if self.review_queue.add_item(review_item):
                # Persist to database
                self._save_review_item(review_item)
                
                # Update statistics
                self.review_stats['total_reviews_created'] += 1
                self.review_stats['current_queue_size'] = self.review_queue.get_queue_size()
                
                logger.info(f"Created manual review {review_id} with priority {priority.value}")
                return review_id
            else:
                logger.error(f"Failed to add review item {review_id} to queue")
                return ""
                
        except Exception as e:
            logger.error(f"Failed to create manual review: {e}")
            return ""
    
    def get_next_review_item(self) -> Optional[ManualReviewItem]:
        """
        Get next item from manual review queue.
        
        Returns:
            Next review item or None if queue is empty
        """
        try:
            item = self.review_queue.get_next_item(timeout=1.0)
            
            if item:
                # Update status to in review
                item.review_status = ReviewStatus.IN_REVIEW
                self._update_review_item(item)
                
                logger.info(f"Retrieved review item {item.review_id} for processing")
            
            return item
            
        except Exception as e:
            logger.error(f"Failed to get next review item: {e}")
            return None
    
    def complete_manual_review(self, review_id: str, human_classification: EmailType,
                             human_confidence: float, reviewer_notes: str = "",
                             reviewer_id: str = "") -> bool:
        """
        Complete manual review with human classification.
        
        Args:
            review_id: ID of review item
            human_classification: Human-provided classification
            human_confidence: Human confidence in classification
            reviewer_notes: Optional reviewer notes
            reviewer_id: ID of reviewer
            
        Returns:
            True if review was completed successfully
        """
        try:
            # Load review item
            review_item = self._load_review_item(review_id)
            if not review_item:
                logger.error(f"Review item {review_id} not found")
                return False
            
            # Update review item
            review_item.human_classification = human_classification
            review_item.human_confidence = human_confidence
            review_item.reviewer_notes = reviewer_notes
            review_item.assigned_reviewer = reviewer_id
            review_item.review_completed_timestamp = datetime.utcnow()
            
            # Determine if original classification was correct
            original_classification = review_item.classification_result.email_type
            if human_classification == original_classification:
                review_item.review_status = ReviewStatus.APPROVED
                logger.info(f"Review {review_id} approved - classifications match")
            else:
                review_item.review_status = ReviewStatus.REJECTED
                logger.info(f"Review {review_id} rejected - classification error detected")
                
                # Record classification error
                self._record_classification_error(review_item, human_classification)
            
            # Update database
            self._update_review_item(review_item)
            
            # Update statistics
            self.review_stats['total_reviews_completed'] += 1
            if review_item.review_status == ReviewStatus.APPROVED:
                self.review_stats['total_reviews_approved'] += 1
            else:
                self.review_stats['total_reviews_rejected'] += 1
            
            # Calculate average review time
            review_time = (review_item.review_completed_timestamp - 
                          review_item.created_timestamp).total_seconds() / 3600
            self._update_average_review_time(review_time)
            
            logger.info(f"Manual review {review_id} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete manual review {review_id}: {e}")
            return False
    
    def detect_classification_errors(self, time_window_hours: int = 24) -> List[ClassificationError]:
        """
        Detect classification errors from recent manual reviews.
        
        Args:
            time_window_hours: Time window for error detection
            
        Returns:
            List of detected classification errors
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            recent_errors = []
            
            # Query database for recent rejected reviews
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM classification_errors 
                    WHERE error_timestamp > ? 
                    ORDER BY error_timestamp DESC
                """, (cutoff_time.isoformat(),))
                
                rows = cursor.fetchall()
                for row in rows:
                    error = self._row_to_classification_error(row)
                    recent_errors.append(error)
            
            logger.info(f"Detected {len(recent_errors)} classification errors in last {time_window_hours} hours")
            return recent_errors
            
        except Exception as e:
            logger.error(f"Failed to detect classification errors: {e}")
            return []
    
    def check_retraining_triggers(self) -> bool:
        """
        Check if model retraining should be triggered based on error patterns.
        
        Returns:
            True if retraining should be triggered
        """
        try:
            # Get recent errors
            recent_errors = self.detect_classification_errors(self.RETRAINING_WINDOW_HOURS)
            
            # Check error count threshold
            if len(recent_errors) >= self.ERROR_THRESHOLD_FOR_RETRAINING:
                logger.info(f"Error count {len(recent_errors)} exceeds threshold "
                           f"{self.ERROR_THRESHOLD_FOR_RETRAINING}, triggering retraining")
                
                self._create_retraining_trigger("error_count", len(recent_errors))
                return True
            
            # Check accuracy degradation
            if self._check_accuracy_degradation(recent_errors):
                logger.info("Accuracy degradation detected, triggering retraining")
                self._create_retraining_trigger("accuracy_degradation", len(recent_errors))
                return True
            
            # Check error patterns
            if self._check_error_patterns(recent_errors):
                logger.info("Systematic error patterns detected, triggering retraining")
                self._create_retraining_trigger("error_patterns", len(recent_errors))
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check retraining triggers: {e}")
            return False
    
    def get_review_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive review system statistics.
        
        Returns:
            Dictionary with review statistics
        """
        try:
            # Update current queue size
            self.review_stats['current_queue_size'] = self.review_queue.get_queue_size()
            
            # Get priority breakdown
            priority_counts = self.review_queue.get_priority_counts()
            
            # Get recent error statistics
            recent_errors = self.detect_classification_errors(24)
            error_by_type = {}
            for error in recent_errors:
                error_type = error.error_type.value
                error_by_type[error_type] = error_by_type.get(error_type, 0) + 1
            
            stats = self.review_stats.copy()
            stats.update({
                'priority_breakdown': {p.value: count for p, count in priority_counts.items()},
                'recent_errors_24h': len(recent_errors),
                'error_breakdown': error_by_type,
                'retraining_triggers_active': len(self.retraining_triggers)
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get review statistics: {e}")
            return self.review_stats.copy()
    
    def _is_ambiguous_classification(self, classification_result: ClassificationResult) -> bool:
        """Check if classification is ambiguous based on alternative classifications"""
        if not classification_result.alternative_classifications:
            return False
        
        # Check if top alternative is close to main classification
        top_alternative = classification_result.alternative_classifications[0]
        confidence_gap = classification_result.confidence_score - top_alternative[1]
        
        # If gap is small, classification is ambiguous
        return confidence_gap < 0.2
    
    def _requires_security_review(self, security_result: SecurityValidationResult) -> bool:
        """Check if security validation requires human review"""
        return (not security_result.sender_authorized or 
                not security_result.content_safe or 
                not security_result.attachments_safe or
                security_result.threat_level in ["MEDIUM", "HIGH", "CRITICAL"])
    
    def _requires_content_review(self, extracted_content: ExtractedContent,
                                classification_result: ClassificationResult) -> bool:
        """Check if content patterns require human review"""
        # Check for executive-level communications
        if any(exec_indicator in extracted_content.headers.sender.lower() 
               for exec_indicator in ['secretary', 'director', 'deputy', 'chief']):
            return True
        
        # Check for urgent/critical keywords
        urgent_keywords = ['urgent', 'critical', 'emergency', 'immediate']
        content_text = (extracted_content.headers.subject + " " + 
                       extracted_content.plain_text).lower()
        
        if any(keyword in content_text for keyword in urgent_keywords):
            return True
        
        return False
    
    def _record_classification_error(self, review_item: ManualReviewItem, 
                                   correct_classification: EmailType):
        """Record classification error for model improvement"""
        try:
            error_id = str(uuid.uuid4())
            
            # Determine error type
            original_type = review_item.classification_result.email_type
            if original_type != correct_classification:
                error_type = ErrorType.WRONG_CLASSIFICATION
            elif review_item.classification_result.confidence_score < 0.5:
                error_type = ErrorType.LOW_CONFIDENCE
            else:
                error_type = ErrorType.AMBIGUOUS_CONTENT
            
            # Create error record
            error = ClassificationError(
                error_id=error_id,
                email_uid=review_item.email_uid,
                message_id=review_item.message_id,
                predicted_type=original_type,
                actual_type=correct_classification,
                confidence_score=review_item.classification_result.confidence_score,
                error_type=error_type,
                error_timestamp=datetime.utcnow(),
                features_snapshot=review_item.classification_result.classification_metadata,
                reviewer_feedback=review_item.reviewer_notes,
                model_version=review_item.classification_result.classification_metadata.get('model_version', 'unknown')
            )
            
            # Save to database
            self._save_classification_error(error)
            
            # Update statistics
            self.review_stats['total_errors_detected'] += 1
            
            logger.info(f"Recorded classification error {error_id}")
            
        except Exception as e:
            logger.error(f"Failed to record classification error: {e}")
    
    def _create_retraining_trigger(self, trigger_type: str, error_count: int):
        """Create retraining trigger"""
        try:
            trigger_id = str(uuid.uuid4())
            
            trigger = RetrainingTrigger(
                trigger_id=trigger_id,
                trigger_type=trigger_type,
                error_count=error_count,
                accuracy_threshold=self.ACCURACY_THRESHOLD_FOR_RETRAINING,
                time_window_hours=self.RETRAINING_WINDOW_HOURS,
                triggered_timestamp=datetime.utcnow()
            )
            
            self.retraining_triggers.append(trigger)
            self._save_retraining_trigger(trigger)
            
            self.review_stats['total_retraining_triggered'] += 1
            
            logger.info(f"Created retraining trigger {trigger_id} for {trigger_type}")
            
        except Exception as e:
            logger.error(f"Failed to create retraining trigger: {e}")
    
    def _check_accuracy_degradation(self, recent_errors: List[ClassificationError]) -> bool:
        """Check if accuracy has degraded below threshold"""
        if len(recent_errors) < 5:  # Need minimum sample size
            return False
        
        # Calculate error rate by type
        error_by_type = {}
        for error in recent_errors:
            error_type = error.predicted_type
            if error_type not in error_by_type:
                error_by_type[error_type] = {'errors': 0, 'total': 0}
            error_by_type[error_type]['errors'] += 1
        
        # Check if any type has high error rate
        for email_type, stats in error_by_type.items():
            if stats['total'] > 0:
                error_rate = stats['errors'] / stats['total']
                if error_rate > (1 - self.ACCURACY_THRESHOLD_FOR_RETRAINING):
                    return True
        
        return False
    
    def _check_error_patterns(self, recent_errors: List[ClassificationError]) -> bool:
        """Check for systematic error patterns"""
        if len(recent_errors) < 3:
            return False
        
        # Check for repeated errors of same type
        error_type_counts = {}
        for error in recent_errors:
            key = f"{error.predicted_type.value}->{error.actual_type.value}"
            error_type_counts[key] = error_type_counts.get(key, 0) + 1
        
        # If any error pattern occurs frequently, trigger retraining
        max_pattern_count = max(error_type_counts.values()) if error_type_counts else 0
        return max_pattern_count >= 3
    
    def _update_average_review_time(self, new_review_time: float):
        """Update average review time with new data point"""
        current_avg = self.review_stats['average_review_time_hours']
        completed_reviews = self.review_stats['total_reviews_completed']
        
        if completed_reviews <= 1:
            self.review_stats['average_review_time_hours'] = new_review_time
        else:
            # Calculate running average
            self.review_stats['average_review_time_hours'] = (
                (current_avg * (completed_reviews - 1) + new_review_time) / completed_reviews
            )
    
    def _init_database(self):
        """Initialize SQLite database for persistence"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create review items table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS review_items (
                        review_id TEXT PRIMARY KEY,
                        email_uid TEXT NOT NULL,
                        message_id TEXT NOT NULL,
                        extracted_content TEXT NOT NULL,
                        security_result TEXT NOT NULL,
                        classification_result TEXT NOT NULL,
                        review_status TEXT NOT NULL,
                        review_priority TEXT NOT NULL,
                        created_timestamp TEXT NOT NULL,
                        assigned_reviewer TEXT,
                        review_deadline TEXT,
                        reviewer_notes TEXT,
                        human_classification TEXT,
                        human_confidence REAL,
                        review_completed_timestamp TEXT,
                        escalation_reason TEXT,
                        retry_count INTEGER DEFAULT 0
                    )
                """)
                
                # Create classification errors table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS classification_errors (
                        error_id TEXT PRIMARY KEY,
                        email_uid TEXT NOT NULL,
                        message_id TEXT NOT NULL,
                        predicted_type TEXT NOT NULL,
                        actual_type TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        error_type TEXT NOT NULL,
                        error_timestamp TEXT NOT NULL,
                        features_snapshot TEXT NOT NULL,
                        reviewer_feedback TEXT,
                        model_version TEXT,
                        retraining_triggered INTEGER DEFAULT 0
                    )
                """)
                
                # Create retraining triggers table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS retraining_triggers (
                        trigger_id TEXT PRIMARY KEY,
                        trigger_type TEXT NOT NULL,
                        error_count INTEGER NOT NULL,
                        accuracy_threshold REAL NOT NULL,
                        time_window_hours INTEGER NOT NULL,
                        triggered_timestamp TEXT NOT NULL,
                        retraining_completed INTEGER DEFAULT 0,
                        new_model_accuracy REAL
                    )
                """)
                
                conn.commit()
                
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _save_review_item(self, item: ManualReviewItem):
        """Save review item to database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO review_items VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    item.review_id,
                    item.email_uid,
                    item.message_id,
                    json.dumps(asdict(item.extracted_content), default=str),
                    json.dumps(asdict(item.security_result), default=str),
                    json.dumps(asdict(item.classification_result), default=str),
                    item.review_status.value,
                    item.review_priority.value,
                    item.created_timestamp.isoformat(),
                    item.assigned_reviewer,
                    item.review_deadline.isoformat() if item.review_deadline else None,
                    item.reviewer_notes,
                    item.human_classification.value if item.human_classification else None,
                    item.human_confidence,
                    item.review_completed_timestamp.isoformat() if item.review_completed_timestamp else None,
                    item.escalation_reason,
                    item.retry_count
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save review item: {e}")
    
    def _update_review_item(self, item: ManualReviewItem):
        """Update existing review item in database"""
        self._save_review_item(item)  # Same as save for SQLite
    
    def _load_review_item(self, review_id: str) -> Optional[ManualReviewItem]:
        """Load review item from database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM review_items WHERE review_id = ?", (review_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_review_item(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to load review item {review_id}: {e}")
            return None
    
    def _save_classification_error(self, error: ClassificationError):
        """Save classification error to database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO classification_errors VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    error.error_id,
                    error.email_uid,
                    error.message_id,
                    error.predicted_type.value,
                    error.actual_type.value,
                    error.confidence_score,
                    error.error_type.value,
                    error.error_timestamp.isoformat(),
                    json.dumps(error.features_snapshot),
                    error.reviewer_feedback,
                    error.model_version,
                    1 if error.retraining_triggered else 0
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save classification error: {e}")
    
    def _save_retraining_trigger(self, trigger: RetrainingTrigger):
        """Save retraining trigger to database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO retraining_triggers VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    trigger.trigger_id,
                    trigger.trigger_type,
                    trigger.error_count,
                    trigger.accuracy_threshold,
                    trigger.time_window_hours,
                    trigger.triggered_timestamp.isoformat(),
                    1 if trigger.retraining_completed else 0,
                    trigger.new_model_accuracy
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save retraining trigger: {e}")
    
    def _row_to_review_item(self, row) -> ManualReviewItem:
        """Convert database row to ManualReviewItem"""
        # For demo purposes, create mock objects for the complex fields
        from unittest.mock import Mock
        
        mock_extracted_content = Mock()
        mock_extracted_content.headers.message_id = row[2]
        mock_extracted_content.headers.subject = "Mock Subject"
        mock_extracted_content.headers.sender = "mock@example.com"
        mock_extracted_content.plain_text = "Mock content"
        
        mock_security_result = Mock()
        mock_security_result.sender_authorized = True
        mock_security_result.content_safe = True
        mock_security_result.attachments_safe = True
        
        mock_classification_result = Mock()
        mock_classification_result.email_type = EmailType.DEVELOPER_UPDATE
        mock_classification_result.confidence_score = 0.75
        
        return ManualReviewItem(
            review_id=row[0],
            email_uid=row[1],
            message_id=row[2],
            extracted_content=mock_extracted_content,
            security_result=mock_security_result,
            classification_result=mock_classification_result,
            review_status=ReviewStatus(row[6]),
            review_priority=ReviewPriority(row[7]),
            created_timestamp=datetime.fromisoformat(row[8]),
            assigned_reviewer=row[9],
            review_deadline=datetime.fromisoformat(row[10]) if row[10] else None,
            reviewer_notes=row[11] or "",
            human_classification=EmailType(row[12]) if row[12] else None,
            human_confidence=row[13],
            review_completed_timestamp=datetime.fromisoformat(row[14]) if row[14] else None,
            escalation_reason=row[15],
            retry_count=row[16] or 0
        )
    
    def _row_to_classification_error(self, row) -> ClassificationError:
        """Convert database row to ClassificationError"""
        return ClassificationError(
            error_id=row[0],
            email_uid=row[1],
            message_id=row[2],
            predicted_type=EmailType(row[3]),
            actual_type=EmailType(row[4]),
            confidence_score=row[5],
            error_type=ErrorType(row[6]),
            error_timestamp=datetime.fromisoformat(row[7]),
            features_snapshot=json.loads(row[8]) if row[8] else {},
            reviewer_feedback=row[9] or "",
            model_version=row[10] or "",
            retraining_triggered=bool(row[11])
        )


class HumanInTheLoopValidator:
    """
    Human-in-the-loop validation workflow for email classification.
    
    Provides interface for human reviewers to validate and correct
    email classifications with proper tracking and feedback loops.
    """
    
    def __init__(self, review_system: ManualReviewSystem):
        """
        Initialize validator with review system.
        
        Args:
            review_system: Manual review system instance
        """
        self.review_system = review_system
        self.active_reviews: Dict[str, ManualReviewItem] = {}
        
    def start_review_session(self, reviewer_id: str) -> Optional[ManualReviewItem]:
        """
        Start new review session for human reviewer.
        
        Args:
            reviewer_id: ID of human reviewer
            
        Returns:
            Review item to process or None if queue is empty
        """
        try:
            review_item = self.review_system.get_next_review_item()
            
            if review_item:
                review_item.assigned_reviewer = reviewer_id
                self.active_reviews[review_item.review_id] = review_item
                
                logger.info(f"Started review session for {reviewer_id} with item {review_item.review_id}")
            
            return review_item
            
        except Exception as e:
            logger.error(f"Failed to start review session: {e}")
            return None
    
    def submit_review_decision(self, review_id: str, human_classification: EmailType,
                             confidence: float, notes: str = "") -> bool:
        """
        Submit human review decision.
        
        Args:
            review_id: ID of review item
            human_classification: Human-provided classification
            confidence: Human confidence in decision (0.0-1.0)
            notes: Optional reviewer notes
            
        Returns:
            True if decision was submitted successfully
        """
        try:
            if review_id not in self.active_reviews:
                logger.error(f"Review {review_id} not found in active reviews")
                return False
            
            review_item = self.active_reviews[review_id]
            reviewer_id = review_item.assigned_reviewer or "unknown"
            
            # Complete the review
            success = self.review_system.complete_manual_review(
                review_id, human_classification, confidence, notes, reviewer_id
            )
            
            if success:
                # Remove from active reviews
                del self.active_reviews[review_id]
                logger.info(f"Review decision submitted for {review_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to submit review decision: {e}")
            return False
    
    def get_review_context(self, review_id: str) -> Optional[Dict[str, Any]]:
        """
        Get context information for review item.
        
        Args:
            review_id: ID of review item
            
        Returns:
            Context dictionary with email details and classification info
        """
        try:
            if review_id not in self.active_reviews:
                return None
            
            review_item = self.active_reviews[review_id]
            
            context = {
                'review_id': review_id,
                'email_subject': review_item.extracted_content.headers.subject,
                'email_sender': review_item.extracted_content.headers.sender,
                'email_content_preview': review_item.extracted_content.plain_text[:500],
                'original_classification': review_item.classification_result.email_type.value,
                'confidence_score': review_item.classification_result.confidence_score,
                'alternative_classifications': [
                    {'type': alt[0].value, 'confidence': alt[1]}
                    for alt in review_item.classification_result.alternative_classifications
                ],
                'security_status': {
                    'sender_authorized': review_item.security_result.sender_authorized,
                    'content_safe': review_item.security_result.content_safe,
                    'attachments_safe': review_item.security_result.attachments_safe
                },
                'review_priority': review_item.review_priority.value,
                'created_timestamp': review_item.created_timestamp.isoformat(),
                'deadline': review_item.review_deadline.isoformat() if review_item.review_deadline else None
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get review context: {e}")
            return None