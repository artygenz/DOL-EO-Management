"""
Email Intent Detection Service

This service handles email intent detection based on sender role and subject patterns.
Business logic separated from HTTP concerns.
"""

import logging
import os
from typing import Optional
from sqlalchemy.orm import Session

from src.models.email_models import EmailWebhookPayload, EmailProcessingResult, EmailIntent

logger = logging.getLogger(__name__)


class EmailIntentService:
    """
    Service for detecting email intent based on sender role and subject patterns.
    
    Uses a simple and reliable approach:
    - CFO role + EO/Executive Order in subject = Executive Order
    - Reviewer role or PMO email + Re: in subject = PMO Response  
    - Executor role + Task Update/Daily Update in subject = Task Update
    - Everything else = Unknown
    """
    
    def __init__(self):
        self.pmo_email = os.getenv("PMO_EMAIL_ADDRESS", "").lower()
    
    async def detect_intent(self, payload: EmailWebhookPayload, db: Session = None) -> EmailProcessingResult:
        """
        Detect the intent of an incoming email based on sender role and subject patterns.
        
        Args:
            payload: The email webhook payload
            db: Database session for user lookup
            
        Returns:
            EmailProcessingResult with detected intent and confidence
        """
        try:
            # Initialize result
            result = EmailProcessingResult(
                email_id=payload.id,
                intent=EmailIntent.UNKNOWN,
                confidence=0.0,
                extracted_data={}
            )
            
            # Extract key information for analysis
            subject = payload.subject.lower() if payload.subject else ""
            sender = payload.sender.lower() if payload.sender else ""
            
            # Get sender's role from database
            sender_role = await self._get_sender_role(sender, db)
            
            # Check for Executive Order (CFO role + EO/Executive Order in subject)
            if sender_role == "admin" and self._has_eo_keywords(subject):
                return self._create_result(
                    EmailIntent.EXECUTIVE_ORDER, 0.95, sender_role, sender,
                    ["eo", "executive order"], "CFO role detected with EO/Executive Order in subject"
                )
            
            # Check for PMO Response (Reviewer role or PMO email + Re: in subject)
            if self._is_pmo_email(sender_role, sender) and self._has_pmo_patterns(subject):
                return self._create_result(
                    EmailIntent.PMO_RESPONSE, 0.90, sender_role, sender,
                    self._get_matching_patterns(subject, self._get_pmo_patterns()),
                    "PMO/Reviewer role detected with PMO-related patterns in subject"
                )
            
            # Check for Task Update (Executor role + Task Update/Daily Update in subject)
            if sender_role == "executor" and self._has_task_update_keywords(subject):
                return self._create_result(
                    EmailIntent.TASK_UPDATE, 0.85, sender_role, sender,
                    self._get_matching_patterns(subject, self._get_task_update_keywords()),
                    "Executor role detected with task update keywords in subject"
                )
            
            # Default to unknown with low confidence
            return self._create_unknown_result(sender_role, sender, subject)
            
        except Exception as e:
            logger.error(f"Error detecting email intent: {e}")
            return EmailProcessingResult(
                email_id=payload.id,
                intent=EmailIntent.UNKNOWN,
                confidence=0.0,
                extracted_data={"error": str(e)},
                processing_errors=[f"Intent detection failed: {str(e)}"]
            )
    
    async def _get_sender_role(self, sender: str, db: Session = None) -> Optional[str]:
        """Get sender's role from database"""
        if not db or not sender:
            return None
            
        try:
            from src.models.user import User
            from sqlalchemy import func
            sender_user = db.query(User).filter(func.lower(User.email) == sender.lower()).first()
            if sender_user:
                logger.info(f"Found sender role: {sender_user.role} for email: {sender}")
                return sender_user.role
            else:
                logger.warning(f"No user found for sender email: {sender}")
                return None
        except Exception as e:
            logger.error(f"Error looking up sender role: {e}")
            return None
    
    def _has_eo_keywords(self, subject: str) -> bool:
        """Check if subject contains EO keywords"""
        return "eo" in subject or "executive order" in subject
    
    def _is_pmo_email(self, sender_role: Optional[str], sender: str) -> bool:
        """Check if sender is a PMO email"""
        # Check if sender is a reviewer
        if sender_role == "reviewer":
            return True
        
        # Check if sender matches PMO email from environment
        if self.pmo_email and sender == self.pmo_email:
            logger.info(f"PMO email match found: {sender}")
            return True
        
        return False
    
    def _has_pmo_patterns(self, subject: str) -> bool:
        """Check if subject contains PMO patterns"""
        pmo_patterns = self._get_pmo_patterns()
        return any(pattern in subject for pattern in pmo_patterns)
    
    def _has_task_update_keywords(self, subject: str) -> bool:
        """Check if subject contains task update keywords"""
        task_update_keywords = self._get_task_update_keywords()
        return any(keyword in subject for keyword in task_update_keywords)
    
    def _get_pmo_patterns(self) -> list[str]:
        """Get PMO response patterns"""
        return ["re:", "reply:", "fw:", "forward:", "pmo review", "pmo response"]
    
    def _get_task_update_keywords(self) -> list[str]:
        """Get task update keywords"""
        return ["task update", "daily update", "daily task update", "progress update", "status update"]
    
    def _get_matching_patterns(self, subject: str, patterns: list[str]) -> list[str]:
        """Get patterns that match in the subject"""
        return [pattern for pattern in patterns if pattern in subject]
    
    def _create_result(self, intent: EmailIntent, confidence: float, sender_role: Optional[str], 
                       sender: str, patterns: list[str], analysis: str) -> EmailProcessingResult:
        """Create a processing result"""
        return EmailProcessingResult(
            email_id="",  # Will be set by caller
            intent=intent,
            confidence=confidence,
            extracted_data={
                "detection_method": "role_based",
                "sender_role": sender_role,
                "sender_email": sender,
                "subject_patterns": patterns,
                "analysis": analysis
            }
        )
    
    def _create_unknown_result(self, sender_role: Optional[str], sender: str, subject: str) -> EmailProcessingResult:
        """Create unknown result with low confidence"""
        return EmailProcessingResult(
            email_id="",  # Will be set by caller
            intent=EmailIntent.UNKNOWN,
            confidence=0.1,
            extracted_data={
                "detection_method": "fallback",
                "sender_role": sender_role,
                "sender_email": sender,
                "subject": subject,
                "analysis_notes": "No clear role-based intent indicators found",
                "possible_reasons": [
                    "Sender not found in database",
                    "Role doesn't match expected patterns",
                    "Subject doesn't contain expected keywords"
                ]
            }
        )
