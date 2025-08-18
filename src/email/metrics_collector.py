"""
Comprehensive Metrics Collection System for Email Agent

This module implements federal-grade metrics collection for monitoring
email processing performance, classification accuracy, connection health,
and security incidents in real-time.

Requirements: 7.1, 7.2
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected by the system"""
    PROCESSING_LATENCY = "processing_latency"
    THROUGHPUT = "throughput"
    CLASSIFICATION_ACCURACY = "classification_accuracy"
    CONNECTION_HEALTH = "connection_health"
    SECURITY_INCIDENT = "security_incident"
    UPTIME = "uptime"


class SecurityIncidentType(Enum):
    """Types of security incidents tracked"""
    MALWARE_DETECTED = "malware_detected"
    PHISHING_ATTEMPT = "phishing_attempt"
    UNAUTHORIZED_SENDER = "unauthorized_sender"
    SUSPICIOUS_CONTENT = "suspicious_content"
    ATTACHMENT_THREAT = "attachment_threat"
    AUTHENTICATION_FAILURE = "authentication_failure"


@dataclass
class ProcessingMetric:
    """Metrics for email processing performance"""
    timestamp: datetime
    email_uid: str
    processing_start_time: float
    processing_end_time: float
    latency_ms: float
    classification_type: str
    confidence_score: float
    success: bool
    error_type: Optional[str] = None


@dataclass
class ThroughputMetric:
    """Metrics for email processing throughput"""
    timestamp: datetime
    emails_processed: int
    time_window_minutes: int
    emails_per_hour: float
    peak_processing_time_ms: float
    average_processing_time_ms: float


@dataclass
class ClassificationAccuracyMetric:
    """Metrics for email classification accuracy"""
    timestamp: datetime
    email_type: str
    predicted_classification: str
    actual_classification: Optional[str]
    confidence_score: float
    correct_prediction: Optional[bool]
    manual_review_required: bool


@dataclass
class ConnectionHealthMetric:
    """Metrics for connection health and uptime"""
    timestamp: datetime
    connection_id: str
    connection_type: str  # IMAP, SMTP
    status: str  # HEALTHY, DEGRADED, FAILED
    response_time_ms: float
    error_count: int
    uptime_percentage: float
    last_successful_operation: datetime


@dataclass
class SecurityIncidentMetric:
    """Metrics for security incidents"""
    timestamp: datetime
    incident_id: str
    incident_type: SecurityIncidentType
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    email_uid: Optional[str]
    sender: Optional[str]
    description: str
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class SystemHealthSnapshot:
    """Complete system health snapshot"""
    timestamp: datetime
    overall_health: str  # HEALTHY, DEGRADED, CRITICAL
    processing_metrics: ProcessingMetric
    throughput_metrics: ThroughputMetric
    classification_accuracy: float
    connection_health: Dict[str, ConnectionHealthMetric]
    security_incidents_count: int
    uptime_percentage: float


class MetricsCollector:
    """
    Comprehensive metrics collection system for Email Agent
    
    Collects and aggregates metrics for:
    - Email processing latency and throughput
    - Classification accuracy rates
    - Connection health and uptime
    - Security incident counting and categorization
    """
    
    def __init__(self, retention_hours: int = 24):
        """
        Initialize metrics collector
        
        Args:
            retention_hours: How long to retain metrics in memory
        """
        self.retention_hours = retention_hours
        self._lock = threading.RLock()
        
        # Metric storage
        self._processing_metrics: deque = deque(maxlen=10000)
        self._throughput_metrics: deque = deque(maxlen=1000)
        self._classification_metrics: deque = deque(maxlen=10000)
        self._connection_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._security_incidents: deque = deque(maxlen=5000)
        
        # Real-time tracking
        self._active_processing: Dict[str, float] = {}
        self._system_start_time = time.time()
        self._connection_status: Dict[str, ConnectionHealthMetric] = {}
        
        # Accuracy tracking
        self._classification_results: Dict[str, List[bool]] = defaultdict(list)
        
        # Background cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_old_metrics, daemon=True)
        self._cleanup_thread.start()
        
        logger.info("MetricsCollector initialized with %d hour retention", retention_hours)
    
    def start_processing_timer(self, email_uid: str) -> None:
        """Start timing email processing"""
        with self._lock:
            self._active_processing[email_uid] = time.time()
    
    def end_processing_timer(self, email_uid: str, classification_type: str, 
                           confidence_score: float, success: bool = True, 
                           error_type: Optional[str] = None) -> None:
        """End timing email processing and record metrics"""
        with self._lock:
            if email_uid not in self._active_processing:
                logger.warning("No start time found for email %s", email_uid)
                return
            
            start_time = self._active_processing.pop(email_uid)
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            metric = ProcessingMetric(
                timestamp=datetime.now(),
                email_uid=email_uid,
                processing_start_time=start_time,
                processing_end_time=end_time,
                latency_ms=latency_ms,
                classification_type=classification_type,
                confidence_score=confidence_score,
                success=success,
                error_type=error_type
            )
            
            self._processing_metrics.append(metric)
            logger.debug("Recorded processing metric for %s: %.2fms", email_uid, latency_ms)
    
    def record_classification_accuracy(self, email_type: str, predicted: str, 
                                     actual: Optional[str], confidence: float,
                                     manual_review: bool = False) -> None:
        """Record classification accuracy metrics"""
        with self._lock:
            correct = None
            if actual is not None:
                correct = predicted == actual
                self._classification_results[email_type].append(correct)
            
            metric = ClassificationAccuracyMetric(
                timestamp=datetime.now(),
                email_type=email_type,
                predicted_classification=predicted,
                actual_classification=actual,
                confidence_score=confidence,
                correct_prediction=correct,
                manual_review_required=manual_review
            )
            
            self._classification_metrics.append(metric)
            logger.debug("Recorded classification accuracy for %s: %s->%s (%.2f)", 
                        email_type, predicted, actual, confidence)
    
    def record_connection_health(self, connection_id: str, connection_type: str,
                               status: str, response_time_ms: float, 
                               error_count: int = 0) -> None:
        """Record connection health metrics"""
        with self._lock:
            # Calculate uptime percentage
            if connection_id in self._connection_status:
                previous = self._connection_status[connection_id]
                time_diff = (datetime.now() - previous.timestamp).total_seconds()
                if status == "HEALTHY":
                    uptime_percentage = min(100.0, previous.uptime_percentage + 
                                          (time_diff / 3600) * 100)
                else:
                    uptime_percentage = max(0.0, previous.uptime_percentage - 
                                          (time_diff / 3600) * 10)
            else:
                uptime_percentage = 100.0 if status == "HEALTHY" else 0.0
            
            # Get previous last successful operation time
            if status == "HEALTHY":
                last_successful_operation = datetime.now()
            else:
                previous_metric = self._connection_status.get(connection_id)
                last_successful_operation = (previous_metric.last_successful_operation 
                                            if previous_metric else datetime.now())
            
            metric = ConnectionHealthMetric(
                timestamp=datetime.now(),
                connection_id=connection_id,
                connection_type=connection_type,
                status=status,
                response_time_ms=response_time_ms,
                error_count=error_count,
                uptime_percentage=uptime_percentage,
                last_successful_operation=last_successful_operation
            )
            
            self._connection_metrics[connection_id].append(metric)
            self._connection_status[connection_id] = metric
            
            logger.debug("Recorded connection health for %s: %s (%.2fms)", 
                        connection_id, status, response_time_ms)
    
    def record_security_incident(self, incident_type: SecurityIncidentType,
                               severity: str, description: str,
                               email_uid: Optional[str] = None,
                               sender: Optional[str] = None) -> str:
        """Record security incident"""
        with self._lock:
            incident_id = f"SEC_{int(time.time())}_{len(self._security_incidents)}"
            
            incident = SecurityIncidentMetric(
                timestamp=datetime.now(),
                incident_id=incident_id,
                incident_type=incident_type,
                severity=severity,
                email_uid=email_uid,
                sender=sender,
                description=description
            )
            
            self._security_incidents.append(incident)
            logger.warning("Security incident recorded: %s - %s", incident_id, description)
            
            return incident_id
    
    def resolve_security_incident(self, incident_id: str) -> bool:
        """Mark security incident as resolved"""
        with self._lock:
            for incident in self._security_incidents:
                if incident.incident_id == incident_id:
                    incident.resolved = True
                    incident.resolution_time = datetime.now()
                    logger.info("Security incident resolved: %s", incident_id)
                    return True
            return False
    
    def get_processing_latency_metrics(self, hours: int = 1) -> Dict[str, float]:
        """Get processing latency metrics for specified time window"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [m for m in self._processing_metrics 
                            if m.timestamp >= cutoff_time and m.success]
            
            if not recent_metrics:
                return {
                    "average_latency_ms": 0.0,
                    "median_latency_ms": 0.0,
                    "p95_latency_ms": 0.0,
                    "p99_latency_ms": 0.0,
                    "max_latency_ms": 0.0,
                    "min_latency_ms": 0.0,
                    "total_processed": 0
                }
            
            latencies = [m.latency_ms for m in recent_metrics]
            latencies.sort()
            
            return {
                "average_latency_ms": statistics.mean(latencies),
                "median_latency_ms": statistics.median(latencies),
                "p95_latency_ms": latencies[int(len(latencies) * 0.95)] if latencies else 0.0,
                "p99_latency_ms": latencies[int(len(latencies) * 0.99)] if latencies else 0.0,
                "max_latency_ms": max(latencies),
                "min_latency_ms": min(latencies),
                "total_processed": len(recent_metrics)
            }
    
    def get_throughput_metrics(self, hours: int = 1) -> Dict[str, float]:
        """Get throughput metrics for specified time window"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [m for m in self._processing_metrics 
                            if m.timestamp >= cutoff_time and m.success]
            
            if not recent_metrics:
                return {
                    "emails_per_hour": 0.0,
                    "emails_per_minute": 0.0,
                    "total_emails": 0,
                    "time_window_hours": hours
                }
            
            total_emails = len(recent_metrics)
            actual_hours = min(hours, (datetime.now() - recent_metrics[0].timestamp).total_seconds() / 3600)
            
            return {
                "emails_per_hour": total_emails / max(actual_hours, 0.1),
                "emails_per_minute": total_emails / max(actual_hours * 60, 1),
                "total_emails": total_emails,
                "time_window_hours": actual_hours
            }
    
    def get_classification_accuracy_metrics(self) -> Dict[str, float]:
        """Get classification accuracy metrics by email type"""
        with self._lock:
            accuracy_by_type = {}
            overall_correct = 0
            overall_total = 0
            
            for email_type, results in self._classification_results.items():
                if results:
                    correct = sum(results)
                    total = len(results)
                    accuracy_by_type[email_type] = (correct / total) * 100
                    overall_correct += correct
                    overall_total += total
                else:
                    accuracy_by_type[email_type] = 0.0
            
            overall_accuracy = (overall_correct / overall_total * 100) if overall_total > 0 else 0.0
            
            return {
                "overall_accuracy": overall_accuracy,
                "by_type": accuracy_by_type,
                "total_classifications": overall_total
            }
    
    def get_connection_health_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get connection health metrics for all connections"""
        with self._lock:
            health_summary = {}
            
            for connection_id, metric in self._connection_status.items():
                recent_metrics = list(self._connection_metrics[connection_id])[-10:]  # Last 10 metrics
                
                if recent_metrics:
                    avg_response_time = statistics.mean([m.response_time_ms for m in recent_metrics])
                    total_errors = sum([m.error_count for m in recent_metrics])
                else:
                    avg_response_time = metric.response_time_ms
                    total_errors = metric.error_count
                
                health_summary[connection_id] = {
                    "status": metric.status,
                    "uptime_percentage": metric.uptime_percentage,
                    "average_response_time_ms": avg_response_time,
                    "total_errors": total_errors,
                    "last_successful_operation": metric.last_successful_operation.isoformat(),
                    "connection_type": metric.connection_type
                }
            
            return health_summary
    
    def get_security_incident_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get security incident metrics for specified time window"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_incidents = [i for i in self._security_incidents 
                              if i.timestamp >= cutoff_time]
            
            # Count by type and severity
            by_type = defaultdict(int)
            by_severity = defaultdict(int)
            resolved_count = 0
            
            for incident in recent_incidents:
                by_type[incident.incident_type.value] += 1
                by_severity[incident.severity] += 1
                if incident.resolved:
                    resolved_count += 1
            
            return {
                "total_incidents": len(recent_incidents),
                "resolved_incidents": resolved_count,
                "unresolved_incidents": len(recent_incidents) - resolved_count,
                "by_type": dict(by_type),
                "by_severity": dict(by_severity),
                "resolution_rate": (resolved_count / len(recent_incidents) * 100) 
                                 if recent_incidents else 100.0
            }
    
    def get_system_uptime_metrics(self) -> Dict[str, Any]:
        """Get system uptime metrics"""
        current_time = time.time()
        uptime_seconds = current_time - self._system_start_time
        uptime_hours = uptime_seconds / 3600
        uptime_days = uptime_hours / 24
        
        return {
            "uptime_seconds": uptime_seconds,
            "uptime_hours": uptime_hours,
            "uptime_days": uptime_days,
            "start_time": datetime.fromtimestamp(self._system_start_time).isoformat(),
            "current_time": datetime.fromtimestamp(current_time).isoformat()
        }
    
    def get_comprehensive_health_snapshot(self) -> SystemHealthSnapshot:
        """Get comprehensive system health snapshot"""
        with self._lock:
            # Get latest processing metric
            latest_processing = self._processing_metrics[-1] if self._processing_metrics else None
            
            # Calculate throughput
            throughput = self.get_throughput_metrics(1)
            throughput_metric = ThroughputMetric(
                timestamp=datetime.now(),
                emails_processed=throughput["total_emails"],
                time_window_minutes=60,
                emails_per_hour=throughput["emails_per_hour"],
                peak_processing_time_ms=0.0,  # Would need more complex tracking
                average_processing_time_ms=self.get_processing_latency_metrics(1)["average_latency_ms"]
            )
            
            # Get classification accuracy
            accuracy = self.get_classification_accuracy_metrics()
            
            # Get connection health
            connection_health = {}
            for conn_id, status in self._connection_status.items():
                connection_health[conn_id] = status
            
            # Count recent security incidents
            security_metrics = self.get_security_incident_metrics(1)
            
            # Determine overall health
            overall_health = "HEALTHY"
            if security_metrics["unresolved_incidents"] > 0:
                overall_health = "DEGRADED"
            if any(conn.status == "FAILED" for conn in connection_health.values()):
                overall_health = "CRITICAL"
            
            # Get uptime
            uptime = self.get_system_uptime_metrics()
            
            return SystemHealthSnapshot(
                timestamp=datetime.now(),
                overall_health=overall_health,
                processing_metrics=latest_processing,
                throughput_metrics=throughput_metric,
                classification_accuracy=accuracy["overall_accuracy"],
                connection_health=connection_health,
                security_incidents_count=security_metrics["unresolved_incidents"],
                uptime_percentage=min(100.0, uptime["uptime_hours"] / 24 * 100)
            )
    
    def export_metrics_to_json(self, include_raw_data: bool = False) -> str:
        """Export all metrics to JSON format for dashboard integration"""
        with self._lock:
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "processing_latency": self.get_processing_latency_metrics(),
                "throughput": self.get_throughput_metrics(),
                "classification_accuracy": self.get_classification_accuracy_metrics(),
                "connection_health": self.get_connection_health_metrics(),
                "security_incidents": self.get_security_incident_metrics(),
                "system_uptime": self.get_system_uptime_metrics()
            }
            
            if include_raw_data:
                export_data["raw_data"] = {
                    "processing_metrics_count": len(self._processing_metrics),
                    "classification_metrics_count": len(self._classification_metrics),
                    "security_incidents_count": len(self._security_incidents),
                    "connection_count": len(self._connection_status)
                }
            
            return json.dumps(export_data, indent=2, default=str)
    
    def _cleanup_old_metrics(self) -> None:
        """Background thread to cleanup old metrics"""
        while True:
            try:
                time.sleep(3600)  # Run every hour
                cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
                
                with self._lock:
                    # Clean processing metrics
                    while (self._processing_metrics and 
                           self._processing_metrics[0].timestamp < cutoff_time):
                        self._processing_metrics.popleft()
                    
                    # Clean classification metrics
                    while (self._classification_metrics and 
                           self._classification_metrics[0].timestamp < cutoff_time):
                        self._classification_metrics.popleft()
                    
                    # Clean security incidents
                    while (self._security_incidents and 
                           self._security_incidents[0].timestamp < cutoff_time):
                        self._security_incidents.popleft()
                    
                    # Clean connection metrics
                    for connection_id in list(self._connection_metrics.keys()):
                        metrics = self._connection_metrics[connection_id]
                        while metrics and metrics[0].timestamp < cutoff_time:
                            metrics.popleft()
                        
                        # Remove empty connection metric queues
                        if not metrics:
                            del self._connection_metrics[connection_id]
                
                logger.debug("Cleaned up old metrics older than %d hours", self.retention_hours)
                
            except Exception as e:
                logger.error("Error in metrics cleanup: %s", e)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics for monitoring dashboards"""
        return {
            "processing": self.get_processing_latency_metrics(),
            "throughput": self.get_throughput_metrics(),
            "accuracy": self.get_classification_accuracy_metrics(),
            "connections": self.get_connection_health_metrics(),
            "security": self.get_security_incident_metrics(),
            "uptime": self.get_system_uptime_metrics(),
            "health_snapshot": self.get_comprehensive_health_snapshot()
        }