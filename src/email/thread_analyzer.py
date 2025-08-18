"""
Email Thread Analysis and Correlation System

This module provides comprehensive email threading analysis for PMO response correlation,
conversation context tracking, and workflow correlation as specified in requirements 2.3 and 3.9.
"""

import re
import hashlib
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import parseaddr
from enum import Enum
import uuid

from .content_extractor import EmailHeaders, ThreadAnalysis

logger = logging.getLogger(__name__)


class ThreadType(Enum):
    """Email thread types for workflow correlation"""
    NEW_CONVERSATION = "new_conversation"
    PMO_RESPONSE_CHAIN = "pmo_response_chain"
    DEVELOPER_UPDATE_CHAIN = "developer_update_chain"
    EXECUTIVE_REQUEST_CHAIN = "executive_request_chain"
    MIXED_WORKFLOW_CHAIN = "mixed_workflow_chain"


class ConversationRole(Enum):
    """Participant roles in email conversations"""
    INITIATOR = "initiator"
    PMO_RESPONDER = "pmo_responder"
    DEVELOPER = "developer"
    EXECUTIVE = "executive"
    EXTERNAL_PARTICIPANT = "external_participant"


@dataclass
class ConversationParticipant:
    """Email conversation participant with role analysis"""
    email_address: str
    display_name: Optional[str]
    role: ConversationRole
    first_seen: datetime
    last_seen: datetime
    message_count: int = 0
    is_internal: bool = True
    domain: Optional[str] = None
    
    def __post_init__(self):
        """Extract domain from email address"""
        if '@' in self.email_address:
            self.domain = self.email_address.split('@')[1].lower()


@dataclass
class ThreadCorrelation:
    """Thread correlation data for workflow analysis"""
    original_request_id: Optional[str]
    workflow_type: ThreadType
    correlation_confidence: float
    related_task_ids: List[str] = field(default_factory=list)
    approval_request_ids: List[str] = field(default_factory=list)
    status_update_ids: List[str] = field(default_factory=list)
    correlation_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Complete conversation context across email chains"""
    thread_id: str
    conversation_id: str
    thread_type: ThreadType
    participants: List[ConversationParticipant]
    message_timeline: List[Dict[str, Any]]
    subject_evolution: List[str]
    workflow_correlation: ThreadCorrelation
    conversation_summary: str
    key_decisions: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ThreadDuplicateCheck:
    """Thread-based duplicate detection result"""
    is_duplicate: bool
    duplicate_type: str  # 'exact', 'thread_continuation', 'content_similar'
    original_message_id: Optional[str]
    confidence_score: float
    detection_method: str
    duplicate_metadata: Dict[str, Any] = field(default_factory=dict)


class EmailThreadAnalyzer:
    """Advanced email thread analysis and correlation system"""
    
    # Government domain patterns for role detection
    GOVERNMENT_DOMAINS = {
        'dol.gov', 'labor.gov', 'osha.gov', 'bls.gov', 'dol.state.gov'
    }
    
    # PMO-related keywords for workflow correlation
    PMO_KEYWORDS = {
        'approval', 'approved', 'reject', 'rejected', 'review', 'reviewed',
        'pmo', 'project management', 'status', 'milestone', 'deliverable',
        'budget', 'timeline', 'resource', 'risk', 'issue', 'escalation'
    }
    
    # Developer-related keywords
    DEVELOPER_KEYWORDS = {
        'development', 'code', 'coding', 'programming', 'bug', 'fix',
        'feature', 'implementation', 'testing', 'deployment', 'release',
        'commit', 'pull request', 'merge', 'branch', 'repository'
    }
    
    # Executive-related keywords
    EXECUTIVE_KEYWORDS = {
        'executive', 'director', 'secretary', 'assistant secretary',
        'report', 'summary', 'briefing', 'dashboard', 'metrics',
        'performance', 'strategic', 'policy', 'decision', 'priority'
    }
    
    def __init__(self, conversation_cache_size: int = 1000):
        """
        Initialize the thread analyzer
        
        Args:
            conversation_cache_size: Maximum number of conversations to cache
        """
        self.conversation_cache: Dict[str, ConversationContext] = {}
        self.thread_cache: Dict[str, ThreadAnalysis] = {}
        self.cache_size = conversation_cache_size
        self.analysis_stats = {
            'threads_analyzed': 0,
            'conversations_tracked': 0,
            'pmo_correlations_found': 0,
            'duplicates_detected': 0,
            'workflow_correlations': 0
        }
        
        logger.info(f"Email thread analyzer initialized with cache size: {conversation_cache_size}")
    
    def analyze_email_thread(self, email_msg: EmailMessage, headers: EmailHeaders) -> ThreadAnalysis:
        """
        Perform comprehensive thread analysis for an email
        
        Args:
            email_msg: Email message to analyze
            headers: Extracted email headers
            
        Returns:
            ThreadAnalysis: Complete thread analysis result
        """
        try:
            self.analysis_stats['threads_analyzed'] += 1
            
            # Check cache first
            cache_key = f"{headers.message_id}_{headers.thread_topic or headers.subject}"
            if cache_key in self.thread_cache:
                logger.debug(f"Using cached thread analysis for {headers.message_id}")
                return self.thread_cache[cache_key]
            
            # Perform comprehensive thread analysis
            thread_analysis = self._perform_thread_analysis(email_msg, headers)
            
            # Cache the result
            if len(self.thread_cache) >= self.cache_size:
                # Remove oldest entry
                oldest_key = next(iter(self.thread_cache))
                del self.thread_cache[oldest_key]
            
            self.thread_cache[cache_key] = thread_analysis
            
            logger.debug(f"Thread analysis completed for {headers.message_id}")
            return thread_analysis
            
        except Exception as e:
            logger.error(f"Thread analysis failed for {headers.message_id}: {e}")
            # Return basic thread analysis on failure
            return self._create_fallback_thread_analysis(headers)
    
    def track_conversation_context(self, email_msg: EmailMessage, headers: EmailHeaders, 
                                 thread_analysis: ThreadAnalysis) -> ConversationContext:
        """
        Track and update conversation context across email chains
        
        Args:
            email_msg: Email message
            headers: Email headers
            thread_analysis: Thread analysis result
            
        Returns:
            ConversationContext: Updated conversation context
        """
        try:
            conversation_id = self._generate_conversation_id(thread_analysis.thread_id, headers)
            
            # Get or create conversation context
            if conversation_id in self.conversation_cache:
                context = self.conversation_cache[conversation_id]
                context = self._update_conversation_context(context, email_msg, headers, thread_analysis)
            else:
                context = self._create_conversation_context(email_msg, headers, thread_analysis)
                self.analysis_stats['conversations_tracked'] += 1
            
            # Update cache
            if len(self.conversation_cache) >= self.cache_size:
                # Remove oldest conversation
                oldest_key = min(self.conversation_cache.keys(), 
                               key=lambda k: self.conversation_cache[k].created_at)
                del self.conversation_cache[oldest_key]
            
            self.conversation_cache[conversation_id] = context
            
            logger.debug(f"Conversation context updated for {conversation_id}")
            return context
            
        except Exception as e:
            logger.error(f"Conversation tracking failed: {e}")
            # Return minimal context on failure
            return self._create_minimal_conversation_context(headers, thread_analysis)
    
    def detect_pmo_response_correlation(self, headers: EmailHeaders, content: str, 
                                      thread_analysis: ThreadAnalysis) -> ThreadCorrelation:
        """
        Detect PMO response correlation for workflow processing
        
        Args:
            headers: Email headers
            content: Email content
            thread_analysis: Thread analysis
            
        Returns:
            ThreadCorrelation: PMO correlation result
        """
        try:
            # Analyze content for PMO-related patterns
            pmo_score = self._calculate_pmo_correlation_score(headers, content)
            
            # Check for approval/rejection patterns
            approval_patterns = self._detect_approval_patterns(content)
            
            # Look for task/request references
            task_references = self._extract_task_references(content)
            
            # Determine workflow type
            workflow_type = self._determine_workflow_type(headers, content, thread_analysis)
            
            # Calculate correlation confidence
            confidence = self._calculate_correlation_confidence(
                pmo_score, approval_patterns, task_references, workflow_type
            )
            
            correlation = ThreadCorrelation(
                original_request_id=thread_analysis.parent_message_id,
                workflow_type=workflow_type,
                correlation_confidence=confidence,
                related_task_ids=task_references.get('task_ids', []),
                approval_request_ids=task_references.get('approval_ids', []),
                status_update_ids=task_references.get('status_ids', []),
                correlation_metadata={
                    'pmo_score': pmo_score,
                    'approval_patterns': approval_patterns,
                    'detection_timestamp': datetime.utcnow().isoformat(),
                    'thread_depth': thread_analysis.thread_depth
                }
            )
            
            if workflow_type == ThreadType.PMO_RESPONSE_CHAIN:
                self.analysis_stats['pmo_correlations_found'] += 1
            
            self.analysis_stats['workflow_correlations'] += 1
            
            logger.debug(f"PMO correlation analysis completed with confidence: {confidence}")
            return correlation
            
        except Exception as e:
            logger.error(f"PMO correlation detection failed: {e}")
            return self._create_fallback_correlation(thread_analysis)
    
    def detect_thread_based_duplicates(self, headers: EmailHeaders, content: str,
                                     thread_analysis: ThreadAnalysis) -> ThreadDuplicateCheck:
        """
        Detect duplicates based on thread analysis and content similarity
        
        Args:
            headers: Email headers
            content: Email content
            thread_analysis: Thread analysis
            
        Returns:
            ThreadDuplicateCheck: Duplicate detection result
        """
        try:
            # Check for exact message ID duplicates
            exact_duplicate = self._check_exact_duplicate(headers.message_id)
            if exact_duplicate:
                self.analysis_stats['duplicates_detected'] += 1
                return ThreadDuplicateCheck(
                    is_duplicate=True,
                    duplicate_type='exact',
                    original_message_id=headers.message_id,
                    confidence_score=1.0,
                    detection_method='message_id_match'
                )
            
            # Check for thread continuation duplicates
            thread_duplicate = self._check_thread_continuation_duplicate(thread_analysis, content)
            if thread_duplicate['is_duplicate']:
                self.analysis_stats['duplicates_detected'] += 1
                return ThreadDuplicateCheck(
                    is_duplicate=True,
                    duplicate_type='thread_continuation',
                    original_message_id=thread_duplicate['original_id'],
                    confidence_score=thread_duplicate['confidence'],
                    detection_method='thread_analysis',
                    duplicate_metadata=thread_duplicate['metadata']
                )
            
            # Check for content similarity duplicates
            content_duplicate = self._check_content_similarity_duplicate(content, headers)
            if content_duplicate['is_duplicate']:
                self.analysis_stats['duplicates_detected'] += 1
                return ThreadDuplicateCheck(
                    is_duplicate=True,
                    duplicate_type='content_similar',
                    original_message_id=content_duplicate['original_id'],
                    confidence_score=content_duplicate['confidence'],
                    detection_method='content_similarity',
                    duplicate_metadata=content_duplicate['metadata']
                )
            
            # No duplicate detected
            return ThreadDuplicateCheck(
                is_duplicate=False,
                duplicate_type='none',
                original_message_id=None,
                confidence_score=0.0,
                detection_method='comprehensive_analysis'
            )
            
        except Exception as e:
            logger.error(f"Thread-based duplicate detection failed: {e}")
            return ThreadDuplicateCheck(
                is_duplicate=False,
                duplicate_type='error',
                original_message_id=None,
                confidence_score=0.0,
                detection_method='error_fallback'
            )
    
    def _perform_thread_analysis(self, email_msg: EmailMessage, headers: EmailHeaders) -> ThreadAnalysis:
        """Perform comprehensive thread analysis"""
        # Enhanced thread analysis building on existing logic
        is_reply = bool(headers.in_reply_to or headers.references)
        is_forward = self._detect_forward_patterns(headers.subject, email_msg)
        
        # Generate thread ID with improved logic
        thread_id = self._generate_thread_id(headers)
        
        # Calculate enhanced thread depth
        thread_depth = self._calculate_thread_depth(headers, email_msg)
        
        # Extract conversation participants with role analysis
        participants = self._extract_conversation_participants(email_msg, headers)
        
        # Determine original subject with better pattern matching
        original_subject = self._extract_enhanced_original_subject(headers.subject)
        
        # Calculate reply chain length with pattern analysis
        reply_chain_length = self._calculate_reply_chain_length(headers.subject, headers.references)
        
        # Determine parent message ID with fallback logic
        parent_message_id = self._determine_parent_message_id(headers)
        
        return ThreadAnalysis(
            thread_id=thread_id,
            is_reply=is_reply,
            is_forward=is_forward,
            parent_message_id=parent_message_id,
            thread_depth=thread_depth,
            conversation_participants=participants,
            thread_subject=original_subject,
            original_subject=original_subject,
            reply_chain_length=reply_chain_length
        )
    
    def _generate_thread_id(self, headers: EmailHeaders) -> str:
        """Generate consistent thread ID"""
        if headers.references:
            # Use first reference as thread root for consistency
            thread_id = headers.references[0]
            # Remove angle brackets if present for consistency
            return thread_id.strip('<>')
        elif headers.in_reply_to:
            # For replies without references, use in_reply_to
            thread_id = headers.in_reply_to
            # Remove angle brackets if present for consistency
            return thread_id.strip('<>')
        else:
            # New thread - use message ID
            thread_id = headers.message_id
            # Remove angle brackets if present for consistency
            return thread_id.strip('<>')
    
    def _calculate_thread_depth(self, headers: EmailHeaders, email_msg: EmailMessage) -> int:
        """Calculate thread depth with enhanced logic"""
        depth = 0
        
        # Count references
        if headers.references:
            depth = len(headers.references)
        elif headers.in_reply_to:
            depth = 1
        
        # Additional depth indicators from subject
        subject_lower = headers.subject.lower()
        re_count = subject_lower.count('re:')
        fwd_count = subject_lower.count('fwd:') + subject_lower.count('fw:')
        
        # Use maximum of reference depth and subject indicators
        subject_depth = re_count + fwd_count
        return max(depth, subject_depth)
    
    def _extract_conversation_participants(self, email_msg: EmailMessage, headers: EmailHeaders) -> Set[str]:
        """Extract conversation participants with enhanced analysis"""
        participants = set()
        
        # Add sender
        participants.add(headers.sender)
        
        # Add recipients
        participants.update(headers.recipients)
        participants.update(headers.cc_recipients)
        participants.update(headers.bcc_recipients)
        
        # Extract participants from references and forwarded content
        try:
            content = str(email_msg.get_content() or "")
            
            # Look for forwarded email headers in content
            forwarded_emails = re.findall(r'From:\s*([^\r\n]+)', content, re.IGNORECASE)
            for email_line in forwarded_emails:
                _, email = parseaddr(email_line)
                if email and '@' in email:
                    participants.add(email)
            
            # Look for "To:" lines in forwarded content
            to_emails = re.findall(r'To:\s*([^\r\n]+)', content, re.IGNORECASE)
            for email_line in to_emails:
                for addr in email_line.split(','):
                    _, email = parseaddr(addr.strip())
                    if email and '@' in email:
                        participants.add(email)
                        
        except Exception as e:
            logger.debug(f"Could not extract forwarded participants: {e}")
        
        return participants
    
    def _detect_forward_patterns(self, subject: str, email_msg: EmailMessage) -> bool:
        """Detect if email is forwarded with enhanced patterns"""
        subject_lower = subject.lower()
        
        # Check subject patterns
        forward_patterns = ['fwd:', 'fw:', 'forward:', 'forwarded:']
        if any(pattern in subject_lower for pattern in forward_patterns):
            return True
        
        # Check content for forwarded message indicators
        try:
            content = str(email_msg.get_content() or "").lower()
            forward_indicators = [
                '---------- forwarded message',
                'begin forwarded message',
                'forwarded by',
                'original message',
                'from:',  # Often indicates forwarded content
            ]
            
            return any(indicator in content for indicator in forward_indicators)
            
        except Exception:
            return False
    
    def _extract_enhanced_original_subject(self, subject: str) -> str:
        """Extract original subject with enhanced pattern matching"""
        if not subject:
            return ""
        
        original = subject
        
        # Enhanced prefix patterns
        patterns = [
            r'^\[.*?\]\s*',  # [EXTERNAL], [SPAM], etc.
            r'^re:\s*',      # Re:
            r'^fwd?:\s*',    # Fwd:, Fw:
            r'^fw:\s*',      # FW:
            r'^forward:\s*', # Forward:
            r'^automatic reply:\s*',  # Automatic reply:
            r'^out of office:\s*',    # Out of office:
        ]
        
        # Apply patterns iteratively
        changed = True
        iterations = 0
        max_iterations = 10  # Prevent infinite loops
        
        while changed and iterations < max_iterations:
            old_original = original
            for pattern in patterns:
                original = re.sub(pattern, '', original, flags=re.IGNORECASE)
            changed = (original != old_original)
            iterations += 1
        
        return original.strip()
    
    def _calculate_reply_chain_length(self, subject: str, references: List[str]) -> int:
        """Calculate reply chain length with enhanced logic"""
        # Count from subject
        subject_lower = subject.lower()
        subject_count = (subject_lower.count('re:') + 
                        subject_lower.count('fwd:') + 
                        subject_lower.count('fw:'))
        
        # Count from references
        reference_count = len(references) if references else 0
        
        # Use maximum as chain length
        return max(subject_count, reference_count)
    
    def _determine_parent_message_id(self, headers: EmailHeaders) -> Optional[str]:
        """Determine parent message ID with fallback logic"""
        # Prefer In-Reply-To
        if headers.in_reply_to:
            return headers.in_reply_to
        
        # Use last reference as immediate parent
        if headers.references:
            return headers.references[-1]
        
        return None
    
    def _generate_conversation_id(self, thread_id: str, headers: EmailHeaders) -> str:
        """Generate consistent conversation ID for thread continuity"""
        # Use thread ID as the primary key for conversation grouping
        # This ensures all messages in the same thread get the same conversation ID
        conversation_key = thread_id
        return hashlib.sha256(conversation_key.encode()).hexdigest()[:16]
    
    def _create_conversation_context(self, email_msg: EmailMessage, headers: EmailHeaders,
                                   thread_analysis: ThreadAnalysis) -> ConversationContext:
        """Create new conversation context"""
        conversation_id = self._generate_conversation_id(thread_analysis.thread_id, headers)
        
        # Analyze participants
        participants = []
        for email_addr in thread_analysis.conversation_participants:
            participant = ConversationParticipant(
                email_address=email_addr,
                display_name=self._extract_display_name(email_addr, email_msg),
                role=self._determine_participant_role(email_addr),
                first_seen=headers.date,
                last_seen=headers.date,
                message_count=1,
                is_internal=self._is_internal_email(email_addr)
            )
            participants.append(participant)
        
        # Create initial message timeline entry
        timeline_entry = {
            'message_id': headers.message_id,
            'sender': headers.sender,
            'timestamp': headers.date,
            'subject': headers.subject,
            'is_reply': thread_analysis.is_reply,
            'is_forward': thread_analysis.is_forward
        }
        
        # Determine thread type
        thread_type = self._determine_thread_type_from_analysis(thread_analysis, headers)
        
        # Create workflow correlation
        content = str(email_msg.get_content() or "")
        workflow_correlation = self.detect_pmo_response_correlation(headers, content, thread_analysis)
        
        return ConversationContext(
            thread_id=thread_analysis.thread_id,
            conversation_id=conversation_id,
            thread_type=thread_type,
            participants=participants,
            message_timeline=[timeline_entry],
            subject_evolution=[headers.subject],
            workflow_correlation=workflow_correlation,
            conversation_summary=self._generate_conversation_summary(headers, content)
        )
    
    def _update_conversation_context(self, context: ConversationContext, email_msg: EmailMessage,
                                   headers: EmailHeaders, thread_analysis: ThreadAnalysis) -> ConversationContext:
        """Update existing conversation context"""
        # Update participants
        for email_addr in thread_analysis.conversation_participants:
            existing_participant = next(
                (p for p in context.participants if p.email_address == email_addr), None
            )
            
            if existing_participant:
                existing_participant.last_seen = headers.date
                existing_participant.message_count += 1
            else:
                new_participant = ConversationParticipant(
                    email_address=email_addr,
                    display_name=self._extract_display_name(email_addr, email_msg),
                    role=self._determine_participant_role(email_addr),
                    first_seen=headers.date,
                    last_seen=headers.date,
                    message_count=1,
                    is_internal=self._is_internal_email(email_addr)
                )
                context.participants.append(new_participant)
        
        # Add to message timeline
        timeline_entry = {
            'message_id': headers.message_id,
            'sender': headers.sender,
            'timestamp': headers.date,
            'subject': headers.subject,
            'is_reply': thread_analysis.is_reply,
            'is_forward': thread_analysis.is_forward
        }
        context.message_timeline.append(timeline_entry)
        
        # Update subject evolution
        if headers.subject not in context.subject_evolution:
            context.subject_evolution.append(headers.subject)
        
        # Update workflow correlation
        content = str(email_msg.get_content() or "")
        updated_correlation = self.detect_pmo_response_correlation(headers, content, thread_analysis)
        
        # Merge correlation data intelligently
        if updated_correlation.correlation_confidence > context.workflow_correlation.correlation_confidence:
            context.workflow_correlation.workflow_type = updated_correlation.workflow_type
            context.workflow_correlation.correlation_confidence = updated_correlation.correlation_confidence
        
        # Merge task IDs without duplicates
        existing_task_ids = set(context.workflow_correlation.related_task_ids)
        new_task_ids = set(updated_correlation.related_task_ids)
        context.workflow_correlation.related_task_ids = list(existing_task_ids | new_task_ids)
        
        # Merge approval IDs without duplicates
        existing_approval_ids = set(context.workflow_correlation.approval_request_ids)
        new_approval_ids = set(updated_correlation.approval_request_ids)
        context.workflow_correlation.approval_request_ids = list(existing_approval_ids | new_approval_ids)
        
        # Update thread type based on conversation evolution
        if len(context.message_timeline) > 1:
            context.thread_type = self._determine_evolved_thread_type(context)
        
        context.updated_at = datetime.utcnow()
        
        return context
    
    def _determine_evolved_thread_type(self, context: ConversationContext) -> ThreadType:
        """Determine thread type based on conversation evolution"""
        # Count different workflow indicators across all messages
        pmo_indicators = 0
        dev_indicators = 0
        exec_indicators = 0
        
        for entry in context.message_timeline:
            subject_lower = entry['subject'].lower()
            
            # Check for PMO indicators
            if any(keyword in subject_lower for keyword in ['pmo', 'approval', 'budget']):
                pmo_indicators += 1
            
            # Check for dev indicators  
            if any(keyword in subject_lower for keyword in ['development', 'progress', 'update', 'code']):
                dev_indicators += 1
                
            # Check for exec indicators
            if any(keyword in subject_lower for keyword in ['executive', 'summary', 'director', 'secretary']):
                exec_indicators += 1
        
        # Count unique workflow types present
        workflow_types_present = 0
        if pmo_indicators > 0:
            workflow_types_present += 1
        if dev_indicators > 0:
            workflow_types_present += 1
        if exec_indicators > 0:
            workflow_types_present += 1
        
        # If multiple workflow types are present, it's a mixed workflow
        if workflow_types_present >= 2:
            return ThreadType.MIXED_WORKFLOW_CHAIN
        elif pmo_indicators > 0:
            return ThreadType.PMO_RESPONSE_CHAIN
        elif dev_indicators > 0:
            return ThreadType.DEVELOPER_UPDATE_CHAIN
        elif exec_indicators > 0:
            return ThreadType.EXECUTIVE_REQUEST_CHAIN
        else:
            return context.thread_type  # Keep existing type
    
    def _calculate_pmo_correlation_score(self, headers: EmailHeaders, content: str) -> float:
        """Calculate PMO correlation score based on content analysis"""
        score = 0.0
        content_lower = content.lower()
        
        # Check for PMO keywords
        pmo_matches = sum(1 for keyword in self.PMO_KEYWORDS if keyword in content_lower)
        score += min(pmo_matches * 0.1, 0.5)  # Max 0.5 from keywords
        
        # Check sender domain
        if any(domain in headers.sender for domain in self.GOVERNMENT_DOMAINS):
            score += 0.2
        
        # Check for approval/rejection language
        approval_patterns = [
            'approved', 'approve', 'rejected', 'reject', 'denied', 'deny',
            'authorized', 'authorize', 'confirmed', 'confirm'
        ]
        if any(pattern in content_lower for pattern in approval_patterns):
            score += 0.3
        
        return min(score, 1.0)
    
    def _detect_approval_patterns(self, content: str) -> Dict[str, Any]:
        """Detect approval/rejection patterns in content"""
        content_lower = content.lower()
        
        patterns = {
            'approval_found': False,
            'rejection_found': False,
            'approval_type': None,
            'decision_confidence': 0.0
        }
        
        # Approval patterns
        approval_indicators = [
            'approved', 'approve', 'authorization granted', 'authorized',
            'confirmed', 'confirm', 'accepted', 'accept', 'go ahead',
            'proceed', 'green light'
        ]
        
        # Rejection patterns
        rejection_indicators = [
            'rejected', 'reject', 'denied', 'deny', 'declined', 'decline',
            'not approved', 'not authorized', 'cannot approve', 'refused'
        ]
        
        approval_count = sum(1 for indicator in approval_indicators if indicator in content_lower)
        rejection_count = sum(1 for indicator in rejection_indicators if indicator in content_lower)
        
        if approval_count > rejection_count and approval_count > 0:
            patterns['approval_found'] = True
            patterns['approval_type'] = 'approved'
            patterns['decision_confidence'] = min(approval_count * 0.3, 1.0)
        elif rejection_count > approval_count and rejection_count > 0:
            patterns['rejection_found'] = True
            patterns['approval_type'] = 'rejected'
            patterns['decision_confidence'] = min(rejection_count * 0.3, 1.0)
        
        return patterns
    
    def _extract_task_references(self, content: str) -> Dict[str, List[str]]:
        """Extract task and request references from content"""
        references = {
            'task_ids': [],
            'approval_ids': [],
            'status_ids': []
        }
        
        # Look for specific task ID patterns with better matching
        task_patterns = [
            r'task\s+id[:\s]*([a-zA-Z0-9-]+)',
            r'task[:\s#-]+([a-zA-Z0-9-]{3,})',  # At least 3 chars
            r'ticket[:\s#-]+([a-zA-Z0-9-]{3,})',
            r'project[:\s#-]+([a-zA-Z0-9-]{3,})',
            r'([a-zA-Z]+-\d{4}-\d{3})',  # Pattern like PROJ-2024-001
            r'([a-zA-Z]+[-_]\d+)',  # Pattern like EO-2024-001
        ]
        
        for pattern in task_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            # Filter out single characters and common words
            valid_matches = [m for m in matches if len(m) >= 3 and not m.lower() in ['the', 'and', 'for', 'you', 'are']]
            references['task_ids'].extend(valid_matches)
        
        # Look for approval ID patterns
        approval_patterns = [
            r'approval\s+id[:\s]*([a-zA-Z0-9-]+)',
            r'approval[:\s#-]+([a-zA-Z0-9-]{3,})',
            r'auth[:\s#-]+([a-zA-Z0-9-]{3,})',
            r'(PMO-[a-zA-Z0-9-]+)',
        ]
        
        for pattern in approval_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            valid_matches = [m for m in matches if len(m) >= 3]
            references['approval_ids'].extend(valid_matches)
        
        # Remove duplicates
        references['task_ids'] = list(set(references['task_ids']))
        references['approval_ids'] = list(set(references['approval_ids']))
        
        return references
    
    def _determine_workflow_type(self, headers: EmailHeaders, content: str, 
                                thread_analysis: ThreadAnalysis) -> ThreadType:
        """Determine workflow type based on analysis"""
        content_lower = content.lower()
        
        # Calculate scores for different workflow types
        pmo_score = sum(1 for keyword in self.PMO_KEYWORDS if keyword in content_lower)
        dev_score = sum(1 for keyword in self.DEVELOPER_KEYWORDS if keyword in content_lower)
        exec_score = sum(1 for keyword in self.EXECUTIVE_KEYWORDS if keyword in content_lower)
        
        # Determine primary workflow type
        if pmo_score > dev_score and pmo_score > exec_score:
            return ThreadType.PMO_RESPONSE_CHAIN
        elif dev_score > pmo_score and dev_score > exec_score:
            return ThreadType.DEVELOPER_UPDATE_CHAIN
        elif exec_score > pmo_score and exec_score > dev_score:
            return ThreadType.EXECUTIVE_REQUEST_CHAIN
        elif pmo_score > 0 or dev_score > 0 or exec_score > 0:
            return ThreadType.MIXED_WORKFLOW_CHAIN
        else:
            return ThreadType.NEW_CONVERSATION
    
    def _calculate_correlation_confidence(self, pmo_score: float, approval_patterns: Dict[str, Any],
                                        task_references: Dict[str, List[str]], 
                                        workflow_type: ThreadType) -> float:
        """Calculate overall correlation confidence"""
        confidence = 0.0
        
        # PMO score contribution
        confidence += pmo_score * 0.3
        
        # Approval patterns contribution
        if approval_patterns['approval_found'] or approval_patterns['rejection_found']:
            confidence += approval_patterns['decision_confidence'] * 0.3
        
        # Task references contribution
        total_refs = (len(task_references['task_ids']) + 
                     len(task_references['approval_ids']) + 
                     len(task_references['status_ids']))
        confidence += min(total_refs * 0.1, 0.2)
        
        # Workflow type contribution (increased for executive requests)
        if workflow_type == ThreadType.PMO_RESPONSE_CHAIN:
            confidence += 0.2
        elif workflow_type == ThreadType.EXECUTIVE_REQUEST_CHAIN:
            confidence += 0.25  # Higher confidence for executive requests
        elif workflow_type == ThreadType.DEVELOPER_UPDATE_CHAIN:
            confidence += 0.15
        elif workflow_type == ThreadType.MIXED_WORKFLOW_CHAIN:
            confidence += 0.3  # High confidence for mixed workflows
        
        return min(confidence, 1.0)
    
    def _check_exact_duplicate(self, message_id: str) -> bool:
        """Check for exact message ID duplicates"""
        # This would typically check against a database or cache
        # For now, return False as this is a placeholder
        return False
    
    def _check_thread_continuation_duplicate(self, thread_analysis: ThreadAnalysis, 
                                           content: str) -> Dict[str, Any]:
        """Check for thread continuation duplicates"""
        # Placeholder implementation - would check against stored thread data
        return {
            'is_duplicate': False,
            'original_id': None,
            'confidence': 0.0,
            'metadata': {}
        }
    
    def _check_content_similarity_duplicate(self, content: str, 
                                          headers: EmailHeaders) -> Dict[str, Any]:
        """Check for content similarity duplicates"""
        # Placeholder implementation - would use content hashing and similarity algorithms
        return {
            'is_duplicate': False,
            'original_id': None,
            'confidence': 0.0,
            'metadata': {}
        }
    
    def _extract_display_name(self, email_addr: str, email_msg: EmailMessage) -> Optional[str]:
        """Extract display name for email address"""
        # Try to find display name in headers
        for header in ['From', 'To', 'Cc']:
            header_value = email_msg.get(header, '')
            if email_addr in header_value:
                name, addr = parseaddr(header_value)
                if name and name != addr:
                    return name
        return None
    
    def _determine_participant_role(self, email_addr: str) -> ConversationRole:
        """Determine participant role based on email address"""
        domain = email_addr.split('@')[1].lower() if '@' in email_addr else ''
        
        if domain in self.GOVERNMENT_DOMAINS:
            # Could be refined based on specific subdomain or email patterns
            if 'pmo' in email_addr.lower():
                return ConversationRole.PMO_RESPONDER
            elif any(keyword in email_addr.lower() for keyword in ['dev', 'engineer', 'tech']):
                return ConversationRole.DEVELOPER
            elif any(keyword in email_addr.lower() for keyword in ['director', 'exec', 'secretary']):
                return ConversationRole.EXECUTIVE
            else:
                return ConversationRole.INITIATOR
        else:
            return ConversationRole.EXTERNAL_PARTICIPANT
    
    def _is_internal_email(self, email_addr: str) -> bool:
        """Check if email address is internal"""
        domain = email_addr.split('@')[1].lower() if '@' in email_addr else ''
        return domain in self.GOVERNMENT_DOMAINS
    
    def _determine_thread_type_from_analysis(self, thread_analysis: ThreadAnalysis, 
                                           headers: EmailHeaders) -> ThreadType:
        """Determine thread type from analysis"""
        # Simple heuristic based on participants and subject
        gov_participants = sum(1 for p in thread_analysis.conversation_participants 
                              if any(domain in p for domain in self.GOVERNMENT_DOMAINS))
        
        if gov_participants > 1:
            return ThreadType.PMO_RESPONSE_CHAIN
        else:
            return ThreadType.NEW_CONVERSATION
    
    def _generate_conversation_summary(self, headers: EmailHeaders, content: str) -> str:
        """Generate conversation summary"""
        # Simple summary based on subject and first few lines of content
        summary = f"Conversation: {headers.subject}"
        
        # Add first sentence of content if available
        sentences = content.split('.')[:2]
        if sentences:
            first_sentence = sentences[0].strip()[:100]
            if first_sentence:
                summary += f" - {first_sentence}..."
        
        return summary
    
    def _create_fallback_thread_analysis(self, headers: EmailHeaders) -> ThreadAnalysis:
        """Create fallback thread analysis on error"""
        return ThreadAnalysis(
            thread_id=headers.message_id,
            is_reply=bool(headers.in_reply_to),
            is_forward=False,
            parent_message_id=headers.in_reply_to,
            thread_depth=0,
            conversation_participants={headers.sender},
            thread_subject=headers.subject,
            original_subject=headers.subject,
            reply_chain_length=0
        )
    
    def _create_fallback_correlation(self, thread_analysis: ThreadAnalysis) -> ThreadCorrelation:
        """Create fallback correlation on error"""
        return ThreadCorrelation(
            original_request_id=thread_analysis.parent_message_id,
            workflow_type=ThreadType.NEW_CONVERSATION,
            correlation_confidence=0.0
        )
    
    def _create_minimal_conversation_context(self, headers: EmailHeaders, 
                                           thread_analysis: ThreadAnalysis) -> ConversationContext:
        """Create minimal conversation context on error"""
        return ConversationContext(
            thread_id=thread_analysis.thread_id,
            conversation_id=headers.message_id,
            thread_type=ThreadType.NEW_CONVERSATION,
            participants=[],
            message_timeline=[],
            subject_evolution=[headers.subject],
            workflow_correlation=self._create_fallback_correlation(thread_analysis),
            conversation_summary=f"Error processing: {headers.subject}"
        )
    
    def get_conversation_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation context by ID"""
        return self.conversation_cache.get(conversation_id)
    
    def get_thread_analysis_stats(self) -> Dict[str, Any]:
        """Get thread analysis statistics"""
        return {
            **self.analysis_stats,
            'cache_size': len(self.thread_cache),
            'conversation_cache_size': len(self.conversation_cache)
        }
    
    def clear_caches(self) -> None:
        """Clear all caches"""
        self.thread_cache.clear()
        self.conversation_cache.clear()
        logger.info("Thread analyzer caches cleared")