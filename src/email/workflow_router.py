"""
Priority Assessment and Workflow Routing System

This module implements priority level assignment based on email type and content,
executive request escalation with high priority handling, workflow determination
and queue routing logic, and load balancing across processing queues.

Implements requirements:
- 2.5: Executive requests shall identify report requirements and assign high priority
- 6.5: System shall prioritize critical email types when resources are constrained
"""

import logging
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import threading

# Import types for type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .email_classifier import ClassificationResult, EmailType
    from .content_extractor import ExtractedContent

logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """Priority levels for email processing"""
    CRITICAL = "CRITICAL"  # Executive requests, urgent directives
    HIGH = "HIGH"         # New EOs, time-sensitive PMO responses
    MEDIUM = "MEDIUM"     # Regular PMO responses, developer updates
    LOW = "LOW"           # Routine communications


class WorkflowType(Enum):
    """Workflow types for email processing"""
    EXECUTIVE_ORDER_PROCESSING = "EXECUTIVE_ORDER_PROCESSING"
    PMO_APPROVAL_WORKFLOW = "PMO_APPROVAL_WORKFLOW"
    DEVELOPER_TASK_WORKFLOW = "DEVELOPER_TASK_WORKFLOW"
    EXECUTIVE_REPORTING_WORKFLOW = "EXECUTIVE_REPORTING_WORKFLOW"


class QueueName(Enum):
    """Processing queue names for load balancing"""
    EO_PROCESSING_QUEUE = "eo_processing_queue"
    PMO_WORKFLOW_QUEUE = "pmo_workflow_queue"
    DEVELOPER_QUEUE = "developer_queue"
    EXECUTIVE_PRIORITY_QUEUE = "executive_priority_queue"
    MANUAL_REVIEW_QUEUE = "manual_review_queue"


@dataclass
class QueueMetrics:
    """Metrics for queue load balancing"""
    queue_name: QueueName
    current_depth: int = 0
    processing_rate: float = 0.0  # emails per minute
    average_processing_time: float = 0.0  # seconds
    last_updated: datetime = field(default_factory=datetime.utcnow)
    error_rate: float = 0.0
    capacity_utilization: float = 0.0


@dataclass
class WorkflowAssignment:
    """Result of workflow routing decision"""
    workflow_type: WorkflowType
    priority_level: PriorityLevel
    assigned_queue: QueueName
    processing_requirements: Dict[str, Any]
    escalation_required: bool = False
    estimated_processing_time: float = 0.0
    routing_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EscalationRule:
    """Rules for executive request escalation"""
    trigger_keywords: List[str]
    sender_patterns: List[str]
    time_threshold_hours: int
    escalation_priority: PriorityLevel
    notification_recipients: List[str]


class WorkflowRouter:
    """
    Intelligent workflow determination and priority assignment system.
    
    Implements:
    - Priority level assignment based on email type and content
    - Executive request escalation with high priority handling
    - Workflow determination and queue routing logic
    - Load balancing across processing queues
    """
    
    # Executive escalation keywords for high priority detection
    EXECUTIVE_ESCALATION_KEYWORDS = [
        'urgent', 'immediate', 'asap', 'critical', 'emergency',
        'secretary request', 'director request', 'deputy request',
        'briefing request', 'report request', 'dashboard request',
        'strategic priority', 'presidential directive', 'white house',
        'congress', 'congressional', 'oversight', 'audit'
    ]
    
    # Executive sender patterns for automatic high priority
    EXECUTIVE_SENDER_PATTERNS = [
        'secretary@', 'deputy.secretary@', 'assistant.secretary@',
        'director@', 'deputy.director@', 'chief@', 'administrator@',
        'whitehouse.gov', 'omb.gov', 'gsa.gov'
    ]
    
    # Content analysis patterns for priority assessment
    PRIORITY_CONTENT_PATTERNS = {
        PriorityLevel.CRITICAL: [
            'executive order', 'presidential directive', 'immediate compliance',
            'national security', 'emergency response', 'critical infrastructure'
        ],
        PriorityLevel.HIGH: [
            'deadline', 'time sensitive', 'priority', 'urgent review',
            'approval required', 'budget impact', 'congressional inquiry'
        ],
        PriorityLevel.MEDIUM: [
            'status update', 'progress report', 'milestone', 'deliverable',
            'review requested', 'feedback needed'
        ]
    }
    
    # Default queue capacities and processing rates
    DEFAULT_QUEUE_CAPACITIES = {
        QueueName.EXECUTIVE_PRIORITY_QUEUE: 50,
        QueueName.EO_PROCESSING_QUEUE: 100,
        QueueName.PMO_WORKFLOW_QUEUE: 200,
        QueueName.DEVELOPER_QUEUE: 300,
        QueueName.MANUAL_REVIEW_QUEUE: 150
    }
    
    def __init__(self, enable_load_balancing: bool = True,
                 queue_capacity_limits: Optional[Dict[QueueName, int]] = None):
        """
        Initialize the workflow router.
        
        Args:
            enable_load_balancing: Whether to enable dynamic load balancing
            queue_capacity_limits: Custom queue capacity limits
        """
        self.enable_load_balancing = enable_load_balancing
        self.queue_capacities = queue_capacity_limits or self.DEFAULT_QUEUE_CAPACITIES
        
        # Queue metrics tracking
        self.queue_metrics: Dict[QueueName, QueueMetrics] = {
            queue: QueueMetrics(queue_name=queue)
            for queue in QueueName
        }
        
        # Load balancing state
        self._routing_history: deque = deque(maxlen=1000)  # Recent routing decisions
        self._queue_assignments: Dict[QueueName, List[str]] = defaultdict(list)
        self._lock = threading.RLock()
        
        # Escalation rules
        self.escalation_rules = self._initialize_escalation_rules()
        
        # Routing statistics
        self.routing_stats = {
            'total_routed': 0,
            'escalations_triggered': 0,
            'load_balancing_adjustments': 0,
            'priority_overrides': 0,
            'per_queue_assignments': {queue: 0 for queue in QueueName},
            'per_priority_assignments': {priority: 0 for priority in PriorityLevel}
        }
        
        logger.info(f"Workflow router initialized with load balancing: {enable_load_balancing}")
    
    def determine_workflow(self, classification: 'ClassificationResult') -> WorkflowType:
        """
        Determine workflow type based on email classification.
        
        Args:
            classification: Email classification result
            
        Returns:
            WorkflowType for the email
        """
        from .email_classifier import EmailType
        
        # Map email types to workflow types
        workflow_mapping = {
            EmailType.NEW_EO: WorkflowType.EXECUTIVE_ORDER_PROCESSING,
            EmailType.PMO_RESPONSE: WorkflowType.PMO_APPROVAL_WORKFLOW,
            EmailType.DEVELOPER_UPDATE: WorkflowType.DEVELOPER_TASK_WORKFLOW,
            EmailType.EXECUTIVE_REQUEST: WorkflowType.EXECUTIVE_REPORTING_WORKFLOW
        }
        
        workflow_type = workflow_mapping.get(
            classification.email_type,
            WorkflowType.DEVELOPER_TASK_WORKFLOW  # Default fallback
        )
        
        # Handle case where email_type might not be an enum
        email_type_str = getattr(classification.email_type, 'value', str(classification.email_type))
        logger.debug(f"Determined workflow {workflow_type.value} for email type {email_type_str}")
        return workflow_type
    
    def assign_priority_level(self, email: 'ExtractedContent',
                            classification: 'ClassificationResult') -> PriorityLevel:
        """
        Assign priority level based on email type and content analysis.
        
        Implements requirement 2.5: Executive requests shall assign high priority
        
        Args:
            email: Extracted email content
            classification: Email classification result
            
        Returns:
            PriorityLevel for the email
        """
        from .email_classifier import EmailType
        
        try:
            # Start with base priority based on email type
            base_priority = self._get_base_priority(classification.email_type)
            
            # Analyze content for priority escalation
            content_priority = self._analyze_content_priority(email)
            
            # Check sender for executive escalation
            sender_priority = self._analyze_sender_priority(email.headers.sender)
            
            # Apply escalation rules
            escalation_priority = self._check_escalation_rules(email, classification)
            
            # Determine final priority (highest wins)
            priorities = [base_priority, content_priority, sender_priority, escalation_priority]
            final_priority = max(priorities, key=lambda p: self._priority_weight(p))
            
            # Special handling for executive requests (requirement 2.5)
            if classification.email_type == EmailType.EXECUTIVE_REQUEST:
                if final_priority.value in ['LOW', 'MEDIUM']:
                    final_priority = PriorityLevel.HIGH
                    self.routing_stats['priority_overrides'] += 1
                    logger.info("Executive request priority elevated to HIGH per requirement 2.5")
            
            # Update statistics
            self.routing_stats['per_priority_assignments'][final_priority] += 1
            
            logger.debug(f"Assigned priority {final_priority.value} (base: {base_priority.value}, "
                        f"content: {content_priority.value}, sender: {sender_priority.value})")
            
            return final_priority
            
        except Exception as e:
            logger.error(f"Priority assignment failed: {e}")
            # Fallback to medium priority
            return PriorityLevel.MEDIUM
    
    def route_to_queue(self, workflow: WorkflowType, priority: PriorityLevel,
                      email_uid: str = None) -> QueueName:
        """
        Route workflow to appropriate queue with load balancing.
        
        Implements requirement 6.5: Prioritize critical email types when constrained
        
        Args:
            workflow: Workflow type to route
            priority: Priority level of the email
            email_uid: Unique identifier for the email (for load balancing)
            
        Returns:
            QueueName for processing
        """
        try:
            with self._lock:
                # Determine base queue for workflow
                base_queue = self._get_base_queue(workflow, priority)
                
                # Apply load balancing if enabled
                if self.enable_load_balancing:
                    final_queue = self._apply_load_balancing(base_queue, priority, email_uid)
                else:
                    final_queue = base_queue
                
                # Update routing statistics
                self.routing_stats['total_routed'] += 1
                self.routing_stats['per_queue_assignments'][final_queue] += 1
                
                # Record routing decision
                self._record_routing_decision(workflow, priority, final_queue, email_uid)
                
                logger.debug(f"Routed {workflow.value} with priority {priority.value} to {final_queue.value}")
                return final_queue
                
        except Exception as e:
            logger.error(f"Queue routing failed: {e}")
            # Fallback to developer queue
            return QueueName.DEVELOPER_QUEUE
    
    def handle_high_priority_escalation(self, email: 'ExtractedContent',
                                      classification: 'ClassificationResult') -> bool:
        """
        Handle high priority escalation for executive requests.
        
        Args:
            email: Extracted email content
            classification: Email classification result
            
        Returns:
            True if escalation was triggered
        """
        try:
            # Check if escalation is needed
            escalation_needed = self._should_escalate(email, classification)
            
            if escalation_needed:
                self._trigger_escalation(email, classification)
                self.routing_stats['escalations_triggered'] += 1
                logger.warning(f"High priority escalation triggered for email {email.headers.message_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Escalation handling failed: {e}")
            return False
    
    def create_workflow_assignment(self, email: 'ExtractedContent',
                                 classification: 'ClassificationResult') -> WorkflowAssignment:
        """
        Create complete workflow assignment with routing decision.
        
        Args:
            email: Extracted email content
            classification: Email classification result
            
        Returns:
            WorkflowAssignment with complete routing information
        """
        try:
            # Determine workflow and priority
            workflow_type = self.determine_workflow(classification)
            priority_level = self.assign_priority_level(email, classification)
            
            # Route to queue
            assigned_queue = self.route_to_queue(workflow_type, priority_level, email.headers.message_id)
            
            # Check for escalation
            escalation_required = self.handle_high_priority_escalation(email, classification)
            
            # Estimate processing time
            estimated_time = self._estimate_processing_time(workflow_type, priority_level)
            
            # Create processing requirements
            processing_requirements = self._create_processing_requirements(
                workflow_type, priority_level, classification
            )
            
            # Create routing metadata
            routing_metadata = {
                'routing_timestamp': datetime.utcnow().isoformat(),
                'router_version': '1.0.0',
                'load_balancing_applied': self.enable_load_balancing,
                'queue_metrics_at_routing': self._get_current_queue_metrics(assigned_queue)
            }
            
            return WorkflowAssignment(
                workflow_type=workflow_type,
                priority_level=priority_level,
                assigned_queue=assigned_queue,
                processing_requirements=processing_requirements,
                escalation_required=escalation_required,
                estimated_processing_time=estimated_time,
                routing_metadata=routing_metadata
            )
            
        except Exception as e:
            logger.error(f"Workflow assignment creation failed: {e}")
            # Return fallback assignment
            return self._create_fallback_assignment()
    
    def update_queue_metrics(self, queue_name: QueueName, depth: int,
                           processing_rate: float, avg_processing_time: float,
                           error_rate: float = 0.0) -> None:
        """
        Update queue metrics for load balancing decisions.
        
        Args:
            queue_name: Name of the queue
            depth: Current queue depth
            processing_rate: Processing rate (emails per minute)
            avg_processing_time: Average processing time in seconds
            error_rate: Error rate (0.0 to 1.0)
        """
        with self._lock:
            metrics = self.queue_metrics[queue_name]
            metrics.current_depth = depth
            metrics.processing_rate = processing_rate
            metrics.average_processing_time = avg_processing_time
            metrics.error_rate = error_rate
            metrics.last_updated = datetime.utcnow()
            
            # Calculate capacity utilization
            max_capacity = self.queue_capacities.get(queue_name, 100)
            metrics.capacity_utilization = depth / max_capacity
            
            logger.debug(f"Updated metrics for {queue_name.value}: depth={depth}, "
                        f"rate={processing_rate:.2f}, utilization={metrics.capacity_utilization:.2f}")
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive routing statistics"""
        with self._lock:
            # Convert enum keys to string values for JSON serialization
            routing_stats_copy = self.routing_stats.copy()
            routing_stats_copy['per_queue_assignments'] = {
                k.value if hasattr(k, 'value') else str(k): v 
                for k, v in self.routing_stats['per_queue_assignments'].items()
            }
            routing_stats_copy['per_priority_assignments'] = {
                k.value if hasattr(k, 'value') else str(k): v 
                for k, v in self.routing_stats['per_priority_assignments'].items()
            }
            
            return {
                'routing_stats': routing_stats_copy,
                'queue_metrics': {
                    queue.value: {
                        'current_depth': metrics.current_depth,
                        'processing_rate': metrics.processing_rate,
                        'capacity_utilization': metrics.capacity_utilization,
                        'error_rate': metrics.error_rate,
                        'last_updated': metrics.last_updated.isoformat()
                    }
                    for queue, metrics in self.queue_metrics.items()
                },
                'recent_routing_decisions': list(self._routing_history)[-10:]  # Last 10 decisions
            }
    
    # Private helper methods
    
    def _get_base_priority(self, email_type: 'EmailType') -> PriorityLevel:
        """Get base priority level for email type"""
        from .email_classifier import EmailType
        
        priority_mapping = {
            EmailType.EXECUTIVE_REQUEST: PriorityLevel.HIGH,
            EmailType.NEW_EO: PriorityLevel.HIGH,
            EmailType.PMO_RESPONSE: PriorityLevel.MEDIUM,
            EmailType.DEVELOPER_UPDATE: PriorityLevel.MEDIUM
        }
        
        return priority_mapping.get(email_type, PriorityLevel.MEDIUM)
    
    def _analyze_content_priority(self, email: 'ExtractedContent') -> PriorityLevel:
        """Analyze email content for priority indicators"""
        content = (email.headers.subject + " " + email.plain_text).lower()
        
        # Check for critical priority patterns
        for pattern in self.PRIORITY_CONTENT_PATTERNS[PriorityLevel.CRITICAL]:
            if pattern in content:
                return PriorityLevel.CRITICAL
        
        # Check for high priority patterns
        for pattern in self.PRIORITY_CONTENT_PATTERNS[PriorityLevel.HIGH]:
            if pattern in content:
                return PriorityLevel.HIGH
        
        # Check for medium priority patterns
        for pattern in self.PRIORITY_CONTENT_PATTERNS[PriorityLevel.MEDIUM]:
            if pattern in content:
                return PriorityLevel.MEDIUM
        
        return PriorityLevel.LOW
    
    def _analyze_sender_priority(self, sender: str) -> PriorityLevel:
        """Analyze sender for executive priority indicators"""
        sender_lower = sender.lower()
        
        # Check for executive sender patterns
        for pattern in self.EXECUTIVE_SENDER_PATTERNS:
            if pattern in sender_lower:
                return PriorityLevel.HIGH
        
        return PriorityLevel.LOW
    
    def _check_escalation_rules(self, email: 'ExtractedContent',
                              classification: 'ClassificationResult') -> PriorityLevel:
        """Check escalation rules for priority elevation"""
        content = (email.headers.subject + " " + email.plain_text).lower()
        sender = email.headers.sender.lower()
        
        for rule in self.escalation_rules:
            # Check keyword triggers
            keyword_match = any(keyword in content for keyword in rule.trigger_keywords)
            
            # Check sender patterns
            sender_match = any(pattern in sender for pattern in rule.sender_patterns)
            
            if keyword_match or sender_match:
                return rule.escalation_priority
        
        return PriorityLevel.LOW
    
    def _priority_weight(self, priority: PriorityLevel) -> int:
        """Get numeric weight for priority comparison"""
        weights = {
            PriorityLevel.CRITICAL: 4,
            PriorityLevel.HIGH: 3,
            PriorityLevel.MEDIUM: 2,
            PriorityLevel.LOW: 1
        }
        return weights.get(priority, 1)
    
    def _get_base_queue(self, workflow: WorkflowType, priority: PriorityLevel) -> QueueName:
        """Get base queue for workflow and priority"""
        # Executive priority queue for critical/high priority items
        if priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]:
            if workflow == WorkflowType.EXECUTIVE_REPORTING_WORKFLOW:
                return QueueName.EXECUTIVE_PRIORITY_QUEUE
        
        # Workflow-specific queues
        queue_mapping = {
            WorkflowType.EXECUTIVE_ORDER_PROCESSING: QueueName.EO_PROCESSING_QUEUE,
            WorkflowType.PMO_APPROVAL_WORKFLOW: QueueName.PMO_WORKFLOW_QUEUE,
            WorkflowType.DEVELOPER_TASK_WORKFLOW: QueueName.DEVELOPER_QUEUE,
            WorkflowType.EXECUTIVE_REPORTING_WORKFLOW: QueueName.EXECUTIVE_PRIORITY_QUEUE
        }
        
        return queue_mapping.get(workflow, QueueName.DEVELOPER_QUEUE)
    
    def _apply_load_balancing(self, base_queue: QueueName, priority: PriorityLevel,
                            email_uid: str = None) -> QueueName:
        """Apply load balancing logic to queue selection"""
        # Check if base queue is overloaded
        base_metrics = self.queue_metrics[base_queue]
        
        # If queue is not overloaded, use it
        if base_metrics.capacity_utilization < 0.8:
            return base_queue
        
        # Find alternative queues for load balancing
        alternative_queues = self._find_alternative_queues(base_queue, priority)
        
        if not alternative_queues:
            # No alternatives available, use base queue anyway
            logger.warning(f"No alternative queues available for {base_queue.value}, using overloaded queue")
            return base_queue
        
        # Select best alternative based on metrics
        best_queue = min(alternative_queues, 
                        key=lambda q: self.queue_metrics[q].capacity_utilization)
        
        self.routing_stats['load_balancing_adjustments'] += 1
        logger.info(f"Load balancing: redirected from {base_queue.value} to {best_queue.value}")
        
        return best_queue
    
    def _find_alternative_queues(self, base_queue: QueueName, 
                               priority: PriorityLevel) -> List[QueueName]:
        """Find alternative queues for load balancing"""
        alternatives = []
        
        # High priority items can use executive priority queue
        if priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]:
            if base_queue != QueueName.EXECUTIVE_PRIORITY_QUEUE:
                alternatives.append(QueueName.EXECUTIVE_PRIORITY_QUEUE)
        
        # Medium/low priority items can use developer queue as fallback
        if priority in [PriorityLevel.MEDIUM, PriorityLevel.LOW]:
            if base_queue != QueueName.DEVELOPER_QUEUE:
                alternatives.append(QueueName.DEVELOPER_QUEUE)
        
        # Filter out overloaded alternatives
        return [q for q in alternatives 
                if self.queue_metrics[q].capacity_utilization < 0.9]
    
    def _should_escalate(self, email: 'ExtractedContent',
                        classification: 'ClassificationResult') -> bool:
        """Determine if escalation is needed"""
        from .email_classifier import EmailType
        
        # Always escalate executive requests with high priority keywords
        if classification.email_type == EmailType.EXECUTIVE_REQUEST:
            content = (email.headers.subject + " " + email.plain_text).lower()
            if any(keyword in content for keyword in self.EXECUTIVE_ESCALATION_KEYWORDS):
                return True
        
        # Escalate if sender is high-level executive
        sender = email.headers.sender.lower()
        if any(pattern in sender for pattern in self.EXECUTIVE_SENDER_PATTERNS):
            return True
        
        return False
    
    def _trigger_escalation(self, email: 'ExtractedContent',
                          classification: 'ClassificationResult') -> None:
        """Trigger escalation procedures"""
        escalation_data = {
            'email_uid': email.headers.message_id,
            'sender': email.headers.sender,
            'subject': email.headers.subject,
            'classification': classification.email_type.value,
            'escalation_timestamp': datetime.utcnow().isoformat(),
            'escalation_reason': 'executive_priority_detected'
        }
        
        # Log escalation (in production, this would trigger notifications)
        logger.critical(f"ESCALATION TRIGGERED: {escalation_data}")
    
    def _estimate_processing_time(self, workflow: WorkflowType, 
                                priority: PriorityLevel) -> float:
        """Estimate processing time based on workflow and priority"""
        base_times = {
            WorkflowType.EXECUTIVE_ORDER_PROCESSING: 300.0,  # 5 minutes
            WorkflowType.PMO_APPROVAL_WORKFLOW: 180.0,       # 3 minutes
            WorkflowType.DEVELOPER_TASK_WORKFLOW: 120.0,     # 2 minutes
            WorkflowType.EXECUTIVE_REPORTING_WORKFLOW: 240.0  # 4 minutes
        }
        
        priority_multipliers = {
            PriorityLevel.CRITICAL: 0.5,  # Faster processing
            PriorityLevel.HIGH: 0.7,
            PriorityLevel.MEDIUM: 1.0,
            PriorityLevel.LOW: 1.5
        }
        
        base_time = base_times.get(workflow, 120.0)
        multiplier = priority_multipliers.get(priority, 1.0)
        
        return base_time * multiplier
    
    def _create_processing_requirements(self, workflow: WorkflowType,
                                      priority: PriorityLevel,
                                      classification: 'ClassificationResult') -> Dict[str, Any]:
        """Create processing requirements for the workflow"""
        requirements = {
            'workflow_type': workflow.value,
            'priority_level': priority.value,
            'requires_human_review': classification.requires_manual_review,
            'confidence_threshold': 0.8,
            'max_processing_time_seconds': self._estimate_processing_time(workflow, priority),
            'retry_attempts': 3 if priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH] else 1,
            'notification_required': priority == PriorityLevel.CRITICAL
        }
        
        # Workflow-specific requirements
        if workflow == WorkflowType.EXECUTIVE_ORDER_PROCESSING:
            requirements.update({
                'requires_pdf_extraction': True,
                'requires_compliance_check': True,
                'requires_audit_logging': True
            })
        elif workflow == WorkflowType.EXECUTIVE_REPORTING_WORKFLOW:
            requirements.update({
                'requires_dashboard_generation': True,
                'requires_executive_formatting': True,
                'requires_attachment_processing': True
            })
        
        return requirements
    
    def _get_current_queue_metrics(self, queue: QueueName) -> Dict[str, Any]:
        """Get current metrics for a queue"""
        metrics = self.queue_metrics[queue]
        return {
            'depth': metrics.current_depth,
            'utilization': metrics.capacity_utilization,
            'processing_rate': metrics.processing_rate,
            'error_rate': metrics.error_rate
        }
    
    def _record_routing_decision(self, workflow: WorkflowType, priority: PriorityLevel,
                               queue: QueueName, email_uid: str = None) -> None:
        """Record routing decision for analysis"""
        decision = {
            'timestamp': datetime.utcnow().isoformat(),
            'workflow': workflow.value,
            'priority': priority.value,
            'queue': queue.value,
            'email_uid': email_uid,
            'load_balancing_applied': self.enable_load_balancing
        }
        
        self._routing_history.append(decision)
    
    def _initialize_escalation_rules(self) -> List[EscalationRule]:
        """Initialize escalation rules for executive requests"""
        return [
            EscalationRule(
                trigger_keywords=['congressional inquiry', 'oversight', 'audit'],
                sender_patterns=['congress.gov', 'house.gov', 'senate.gov'],
                time_threshold_hours=1,
                escalation_priority=PriorityLevel.CRITICAL,
                notification_recipients=['security@dol.gov', 'compliance@dol.gov']
            ),
            EscalationRule(
                trigger_keywords=['white house', 'presidential', 'potus'],
                sender_patterns=['whitehouse.gov', 'eop.gov'],
                time_threshold_hours=2,
                escalation_priority=PriorityLevel.CRITICAL,
                notification_recipients=['secretary@dol.gov', 'deputy@dol.gov']
            ),
            EscalationRule(
                trigger_keywords=['emergency', 'critical', 'immediate action'],
                sender_patterns=['secretary@', 'deputy.secretary@'],
                time_threshold_hours=4,
                escalation_priority=PriorityLevel.HIGH,
                notification_recipients=['pmo@dol.gov', 'operations@dol.gov']
            )
        ]
    
    def _create_fallback_assignment(self) -> WorkflowAssignment:
        """Create fallback workflow assignment on error"""
        return WorkflowAssignment(
            workflow_type=WorkflowType.DEVELOPER_TASK_WORKFLOW,
            priority_level=PriorityLevel.MEDIUM,
            assigned_queue=QueueName.DEVELOPER_QUEUE,
            processing_requirements={'error': 'fallback_assignment'},
            escalation_required=False,
            estimated_processing_time=120.0,
            routing_metadata={'error': 'assignment_failed'}
        )