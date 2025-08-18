"""
Performance Bottleneck Detection System for Email Agent

This module implements real-time performance monitoring and bottleneck detection
with optimization recommendations, resource utilization monitoring, and queue
depth analysis for federal-grade email processing systems.

Requirements: 7.4, 6.1, 6.3
"""

import time
import threading
import psutil
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from collections import defaultdict, deque
import statistics
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class BottleneckType(Enum):
    """Types of performance bottlenecks that can be detected"""
    CPU_BOUND = "cpu_bound"
    MEMORY_BOUND = "memory_bound"
    IO_BOUND = "io_bound"
    NETWORK_BOUND = "network_bound"
    DATABASE_BOUND = "database_bound"
    QUEUE_CONGESTION = "queue_congestion"
    CONNECTION_POOL_EXHAUSTION = "connection_pool_exhaustion"
    CLASSIFICATION_SLOWDOWN = "classification_slowdown"
    SECURITY_VALIDATION_DELAY = "security_validation_delay"


class SeverityLevel(Enum):
    """Severity levels for performance issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResourceType(Enum):
    """Types of system resources monitored"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    DATABASE_CONNECTIONS = "database_connections"
    QUEUE_DEPTH = "queue_depth"
    PROCESSING_TIME = "processing_time"


@dataclass
class ResourceThreshold:
    """Threshold configuration for resource monitoring"""
    resource_type: ResourceType
    warning_threshold: float
    critical_threshold: float
    measurement_unit: str
    check_interval_seconds: int = 30


@dataclass
class PerformanceMetric:
    """Individual performance measurement"""
    timestamp: datetime
    resource_type: ResourceType
    value: float
    unit: str
    component: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BottleneckDetection:
    """Detected performance bottleneck"""
    detection_id: str
    timestamp: datetime
    bottleneck_type: BottleneckType
    severity: SeverityLevel
    component: str
    description: str
    current_value: float
    threshold_value: float
    impact_assessment: str
    optimization_recommendations: List[str]
    estimated_improvement: Optional[str] = None
    resolution_status: str = "OPEN"  # OPEN, IN_PROGRESS, RESOLVED
    resolution_time: Optional[datetime] = None


@dataclass
class QueueAnalysis:
    """Queue depth and processing analysis"""
    timestamp: datetime
    queue_name: str
    current_depth: int
    max_depth: int
    average_depth: float
    processing_rate: float  # items per second
    average_wait_time: float  # seconds
    oldest_item_age: float  # seconds
    congestion_level: str  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class ProcessingTimeAnalysis:
    """Processing time analysis for different components"""
    timestamp: datetime
    component: str
    operation: str
    average_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    max_time_ms: float
    sample_count: int
    trend: str  # IMPROVING, STABLE, DEGRADING


@dataclass
class OptimizationRecommendation:
    """Specific optimization recommendation"""
    recommendation_id: str
    bottleneck_type: BottleneckType
    priority: SeverityLevel
    title: str
    description: str
    implementation_steps: List[str]
    expected_improvement: str
    implementation_effort: str  # LOW, MEDIUM, HIGH
    risk_level: str  # LOW, MEDIUM, HIGH


class PerformanceMonitor:
    """
    Real-time performance monitoring and bottleneck detection system
    
    Monitors system resources, queue depths, processing times, and detects
    performance bottlenecks with actionable optimization recommendations.
    """
    
    def __init__(self, check_interval: int = 30):
        """
        Initialize performance monitor
        
        Args:
            check_interval: Interval in seconds between performance checks
        """
        self.check_interval = check_interval
        self._lock = threading.RLock()
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Performance data storage
        self._performance_metrics: deque = deque(maxlen=10000)
        self._bottleneck_detections: deque = deque(maxlen=1000)
        self._queue_analyses: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self._processing_analyses: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        
        # Resource thresholds (configurable)
        self._resource_thresholds = {
            ResourceType.CPU: ResourceThreshold(
                ResourceType.CPU, 70.0, 90.0, "percentage", 30
            ),
            ResourceType.MEMORY: ResourceThreshold(
                ResourceType.MEMORY, 80.0, 95.0, "percentage", 30
            ),
            ResourceType.DISK_IO: ResourceThreshold(
                ResourceType.DISK_IO, 80.0, 95.0, "percentage", 60
            ),
            ResourceType.NETWORK_IO: ResourceThreshold(
                ResourceType.NETWORK_IO, 100.0, 200.0, "mbps", 60
            ),
            ResourceType.QUEUE_DEPTH: ResourceThreshold(
                ResourceType.QUEUE_DEPTH, 100, 500, "items", 15
            ),
            ResourceType.PROCESSING_TIME: ResourceThreshold(
                ResourceType.PROCESSING_TIME, 5000.0, 10000.0, "milliseconds", 30
            )
        }
        
        # Queue monitoring
        self._monitored_queues: Dict[str, queue.Queue] = {}
        self._queue_processors: Dict[str, Callable] = {}
        
        # Processing time tracking
        self._active_operations: Dict[str, float] = {}
        self._operation_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Alert callbacks
        self._alert_callbacks: List[Callable] = []
        
        logger.info("PerformanceMonitor initialized with %ds check interval", check_interval)
    
    def set_resource_threshold(self, resource_type: ResourceType, 
                             warning_threshold: float, critical_threshold: float) -> None:
        """Set custom threshold for resource monitoring"""
        with self._lock:
            if resource_type in self._resource_thresholds:
                threshold = self._resource_thresholds[resource_type]
                threshold.warning_threshold = warning_threshold
                threshold.critical_threshold = critical_threshold
                logger.info("Updated threshold for %s: warning=%.2f, critical=%.2f",
                           resource_type.value, warning_threshold, critical_threshold)
    
    def register_queue(self, queue_name: str, queue_obj: queue.Queue,
                      processor_func: Optional[Callable] = None) -> None:
        """Register a queue for monitoring"""
        with self._lock:
            self._monitored_queues[queue_name] = queue_obj
            if processor_func:
                self._queue_processors[queue_name] = processor_func
            logger.info("Registered queue for monitoring: %s", queue_name)
    
    def register_alert_callback(self, callback: Callable[[BottleneckDetection], None]) -> None:
        """Register callback for bottleneck alerts"""
        self._alert_callbacks.append(callback)
        callback_name = getattr(callback, '__name__', str(callback))
        logger.info("Registered alert callback: %s", callback_name)
    
    def start_monitoring(self) -> None:
        """Start performance monitoring"""
        if self._monitoring_active:
            logger.warning("Performance monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def start_operation_timer(self, operation_id: str, component: str, operation: str) -> None:
        """Start timing an operation"""
        with self._lock:
            key = f"{component}:{operation}:{operation_id}"
            self._active_operations[key] = time.time()
    
    def end_operation_timer(self, operation_id: str, component: str, operation: str) -> float:
        """End timing an operation and return duration"""
        with self._lock:
            key = f"{component}:{operation}:{operation_id}"
            if key not in self._active_operations:
                logger.warning("No start time found for operation %s", key)
                return 0.0
            
            start_time = self._active_operations.pop(key)
            duration_ms = (time.time() - start_time) * 1000
            
            # Store in operation history
            history_key = f"{component}:{operation}"
            self._operation_history[history_key].append({
                'timestamp': datetime.now(),
                'duration_ms': duration_ms,
                'operation_id': operation_id
            })
            
            return duration_ms
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Analyze queue performance
                self._analyze_queue_performance()
                
                # Analyze processing times
                self._analyze_processing_times()
                
                # Detect bottlenecks
                self._detect_bottlenecks()
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error("Error in monitoring loop: %s", e)
                time.sleep(self.check_interval)
    
    def _collect_system_metrics(self) -> None:
        """Collect system resource metrics"""
        timestamp = datetime.now()
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self._record_metric(timestamp, ResourceType.CPU, cpu_percent, "percentage", "system")
            
            # Memory usage
            memory = psutil.virtual_memory()
            self._record_metric(timestamp, ResourceType.MEMORY, memory.percent, "percentage", "system")
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                # Calculate disk utilization percentage (simplified)
                disk_util = min(100.0, (disk_io.read_bytes + disk_io.write_bytes) / (1024**3))  # GB/s
                self._record_metric(timestamp, ResourceType.DISK_IO, disk_util, "percentage", "system")
            
            # Network I/O
            network_io = psutil.net_io_counters()
            if network_io:
                # Calculate network utilization in Mbps (simplified)
                network_mbps = (network_io.bytes_sent + network_io.bytes_recv) / (1024**2) / 8  # Mbps
                self._record_metric(timestamp, ResourceType.NETWORK_IO, network_mbps, "mbps", "system")
            
        except Exception as e:
            logger.error("Error collecting system metrics: %s", e)
    
    def _record_metric(self, timestamp: datetime, resource_type: ResourceType,
                      value: float, unit: str, component: str, metadata: Dict = None) -> None:
        """Record a performance metric"""
        metric = PerformanceMetric(
            timestamp=timestamp,
            resource_type=resource_type,
            value=value,
            unit=unit,
            component=component,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._performance_metrics.append(metric)
    
    def _analyze_queue_performance(self) -> None:
        """Analyze performance of monitored queues"""
        timestamp = datetime.now()
        
        for queue_name, queue_obj in self._monitored_queues.items():
            try:
                current_depth = queue_obj.qsize()
                
                # Get historical data for this queue
                history = list(self._queue_analyses[queue_name])
                
                # Calculate metrics
                if history:
                    recent_history = [h for h in history if 
                                    (timestamp - h.timestamp).total_seconds() < 300]  # Last 5 minutes
                    
                    if recent_history:
                        avg_depth = statistics.mean([h.current_depth for h in recent_history])
                        max_depth = max([h.current_depth for h in recent_history])
                        
                        # Estimate processing rate
                        if len(recent_history) > 1:
                            time_diff = (recent_history[-1].timestamp - recent_history[0].timestamp).total_seconds()
                            depth_change = recent_history[0].current_depth - recent_history[-1].current_depth
                            processing_rate = max(0, depth_change / time_diff) if time_diff > 0 else 0
                        else:
                            processing_rate = 0
                    else:
                        avg_depth = current_depth
                        max_depth = current_depth
                        processing_rate = 0
                else:
                    avg_depth = current_depth
                    max_depth = current_depth
                    processing_rate = 0
                
                # Determine congestion level
                if current_depth < 10:
                    congestion_level = "LOW"
                elif current_depth < 25:
                    congestion_level = "MEDIUM"
                elif current_depth < 100:
                    congestion_level = "HIGH"
                else:
                    congestion_level = "CRITICAL"
                
                # Estimate wait time and oldest item age (simplified)
                avg_wait_time = current_depth / max(processing_rate, 0.1)
                oldest_item_age = avg_wait_time * 2  # Simplified estimation
                
                analysis = QueueAnalysis(
                    timestamp=timestamp,
                    queue_name=queue_name,
                    current_depth=current_depth,
                    max_depth=max_depth,
                    average_depth=avg_depth,
                    processing_rate=processing_rate,
                    average_wait_time=avg_wait_time,
                    oldest_item_age=oldest_item_age,
                    congestion_level=congestion_level
                )
                
                with self._lock:
                    self._queue_analyses[queue_name].append(analysis)
                
                # Record as metric for threshold checking
                self._record_metric(timestamp, ResourceType.QUEUE_DEPTH, current_depth, 
                                  "items", f"queue:{queue_name}")
                
            except Exception as e:
                logger.error("Error analyzing queue %s: %s", queue_name, e)
    
    def _analyze_processing_times(self) -> None:
        """Analyze processing times for different operations"""
        timestamp = datetime.now()
        
        for operation_key, history in self._operation_history.items():
            try:
                if not history:
                    continue
                
                # Get recent operations (last 5 minutes)
                recent_ops = [op for op in history if 
                            (timestamp - op['timestamp']).total_seconds() < 300]
                
                if len(recent_ops) < 5:  # Need minimum sample size
                    continue
                
                durations = [op['duration_ms'] for op in recent_ops]
                durations.sort()
                
                # Calculate statistics
                avg_time = statistics.mean(durations)
                median_time = statistics.median(durations)
                p95_time = durations[int(len(durations) * 0.95)] if durations else 0
                p99_time = durations[int(len(durations) * 0.99)] if durations else 0
                max_time = max(durations)
                
                # Determine trend (simplified)
                if len(history) >= 20:
                    recent_avg = statistics.mean([op['duration_ms'] for op in list(history)[-10:]])
                    older_avg = statistics.mean([op['duration_ms'] for op in list(history)[-20:-10]])
                    
                    if recent_avg < older_avg * 0.9:
                        trend = "IMPROVING"
                    elif recent_avg > older_avg * 1.1:
                        trend = "DEGRADING"
                    else:
                        trend = "STABLE"
                else:
                    trend = "STABLE"
                
                component, operation = operation_key.split(':', 1)
                
                analysis = ProcessingTimeAnalysis(
                    timestamp=timestamp,
                    component=component,
                    operation=operation,
                    average_time_ms=avg_time,
                    median_time_ms=median_time,
                    p95_time_ms=p95_time,
                    p99_time_ms=p99_time,
                    max_time_ms=max_time,
                    sample_count=len(recent_ops),
                    trend=trend
                )
                
                with self._lock:
                    self._processing_analyses[operation_key].append(analysis)
                
                # Record as metric for threshold checking
                self._record_metric(timestamp, ResourceType.PROCESSING_TIME, avg_time, 
                                  "milliseconds", component, {"operation": operation})
                
            except Exception as e:
                logger.error("Error analyzing processing times for %s: %s", operation_key, e)
    
    def _detect_bottlenecks(self) -> None:
        """Detect performance bottlenecks based on collected metrics"""
        timestamp = datetime.now()
        
        # Check resource thresholds
        for resource_type, threshold in self._resource_thresholds.items():
            try:
                recent_metrics = [m for m in self._performance_metrics 
                                if m.resource_type == resource_type and 
                                (timestamp - m.timestamp).total_seconds() < threshold.check_interval_seconds * 2]
                
                if not recent_metrics:
                    continue
                
                # Get latest value
                latest_metric = max(recent_metrics, key=lambda x: x.timestamp)
                current_value = latest_metric.value
                
                # Check thresholds
                severity = None
                if current_value >= threshold.critical_threshold:
                    severity = SeverityLevel.CRITICAL
                elif current_value >= threshold.warning_threshold:
                    severity = SeverityLevel.HIGH
                
                if severity:
                    bottleneck_type = self._map_resource_to_bottleneck(resource_type)
                    detection = self._create_bottleneck_detection(
                        bottleneck_type, severity, latest_metric.component,
                        f"{resource_type.value} usage at {current_value:.2f}{threshold.measurement_unit}",
                        current_value, threshold.warning_threshold, latest_metric
                    )
                    
                    with self._lock:
                        self._bottleneck_detections.append(detection)
                    
                    # Trigger alerts
                    self._trigger_alert(detection)
                
            except Exception as e:
                logger.error("Error detecting bottlenecks for %s: %s", resource_type, e)
    
    def _map_resource_to_bottleneck(self, resource_type: ResourceType) -> BottleneckType:
        """Map resource type to bottleneck type"""
        mapping = {
            ResourceType.CPU: BottleneckType.CPU_BOUND,
            ResourceType.MEMORY: BottleneckType.MEMORY_BOUND,
            ResourceType.DISK_IO: BottleneckType.IO_BOUND,
            ResourceType.NETWORK_IO: BottleneckType.NETWORK_BOUND,
            ResourceType.QUEUE_DEPTH: BottleneckType.QUEUE_CONGESTION,
            ResourceType.PROCESSING_TIME: BottleneckType.CLASSIFICATION_SLOWDOWN
        }
        return mapping.get(resource_type, BottleneckType.CPU_BOUND)
    
    def _create_bottleneck_detection(self, bottleneck_type: BottleneckType, 
                                   severity: SeverityLevel, component: str,
                                   description: str, current_value: float,
                                   threshold_value: float, metric: PerformanceMetric) -> BottleneckDetection:
        """Create a bottleneck detection with recommendations"""
        detection_id = f"BTL_{int(time.time())}_{len(self._bottleneck_detections)}"
        
        # Generate optimization recommendations
        recommendations = self._generate_optimization_recommendations(bottleneck_type, severity, metric)
        
        # Assess impact
        impact_assessment = self._assess_bottleneck_impact(bottleneck_type, severity, current_value)
        
        return BottleneckDetection(
            detection_id=detection_id,
            timestamp=datetime.now(),
            bottleneck_type=bottleneck_type,
            severity=severity,
            component=component,
            description=description,
            current_value=current_value,
            threshold_value=threshold_value,
            impact_assessment=impact_assessment,
            optimization_recommendations=recommendations
        )
    
    def _generate_optimization_recommendations(self, bottleneck_type: BottleneckType,
                                             severity: SeverityLevel, metric: PerformanceMetric) -> List[str]:
        """Generate specific optimization recommendations for bottleneck"""
        recommendations = []
        
        if bottleneck_type == BottleneckType.CPU_BOUND:
            recommendations.extend([
                "Consider horizontal scaling by adding more worker processes",
                "Optimize CPU-intensive operations like email classification",
                "Implement caching for frequently accessed data",
                "Profile code to identify CPU hotspots"
            ])
        
        elif bottleneck_type == BottleneckType.MEMORY_BOUND:
            recommendations.extend([
                "Increase available memory or optimize memory usage",
                "Implement memory pooling for large objects",
                "Review and optimize data structures",
                "Add memory-based caching with proper eviction policies"
            ])
        
        elif bottleneck_type == BottleneckType.IO_BOUND:
            recommendations.extend([
                "Optimize database queries and add appropriate indexes",
                "Implement connection pooling for database connections",
                "Consider using SSD storage for better I/O performance",
                "Batch database operations where possible"
            ])
        
        elif bottleneck_type == BottleneckType.NETWORK_BOUND:
            recommendations.extend([
                "Optimize network calls and implement request batching",
                "Add network-level caching and compression",
                "Consider using faster network infrastructure",
                "Implement connection keep-alive and pooling"
            ])
        
        elif bottleneck_type == BottleneckType.QUEUE_CONGESTION:
            recommendations.extend([
                "Increase queue processing capacity by adding workers",
                "Implement priority queues for critical emails",
                "Add queue partitioning to distribute load",
                "Monitor and optimize queue processing algorithms"
            ])
        
        elif bottleneck_type == BottleneckType.CLASSIFICATION_SLOWDOWN:
            recommendations.extend([
                "Optimize machine learning model inference time",
                "Implement model caching and batch processing",
                "Consider using faster classification algorithms",
                "Add preprocessing optimizations"
            ])
        
        # Add severity-specific recommendations
        if severity == SeverityLevel.CRITICAL:
            recommendations.insert(0, "IMMEDIATE ACTION REQUIRED: Consider emergency scaling")
        
        return recommendations
    
    def _assess_bottleneck_impact(self, bottleneck_type: BottleneckType, 
                                severity: SeverityLevel, current_value: float) -> str:
        """Assess the impact of a detected bottleneck"""
        impact_levels = {
            SeverityLevel.LOW: "Minimal impact on system performance",
            SeverityLevel.MEDIUM: "Moderate impact, may cause occasional delays",
            SeverityLevel.HIGH: "Significant impact, affecting user experience",
            SeverityLevel.CRITICAL: "Severe impact, system may become unresponsive"
        }
        
        base_impact = impact_levels.get(severity, "Unknown impact")
        
        # Add bottleneck-specific impact details
        if bottleneck_type == BottleneckType.QUEUE_CONGESTION:
            base_impact += f". Queue depth at {current_value:.0f} items may cause processing delays."
        elif bottleneck_type == BottleneckType.CPU_BOUND:
            base_impact += f". CPU usage at {current_value:.1f}% may slow down email processing."
        elif bottleneck_type == BottleneckType.MEMORY_BOUND:
            base_impact += f". Memory usage at {current_value:.1f}% may cause system instability."
        
        return base_impact
    
    def _trigger_alert(self, detection: BottleneckDetection) -> None:
        """Trigger alerts for bottleneck detection"""
        logger.warning("Performance bottleneck detected: %s - %s", 
                      detection.detection_id, detection.description)
        
        for callback in self._alert_callbacks:
            try:
                callback(detection)
            except Exception as e:
                logger.error("Error in alert callback: %s", e)
    
    def get_current_performance_status(self) -> Dict[str, Any]:
        """Get current performance status summary"""
        with self._lock:
            timestamp = datetime.now()
            
            # Get latest metrics for each resource type
            latest_metrics = {}
            for resource_type in ResourceType:
                recent = [m for m in self._performance_metrics 
                         if m.resource_type == resource_type and 
                         (timestamp - m.timestamp).total_seconds() < 300]
                if recent:
                    latest_metrics[resource_type.value] = max(recent, key=lambda x: x.timestamp).value
            
            # Get active bottlenecks
            active_bottlenecks = [b for b in self._bottleneck_detections 
                                if b.resolution_status == "OPEN" and 
                                (timestamp - b.timestamp).total_seconds() < 3600]
            
            # Get queue status
            queue_status = {}
            for queue_name, analyses in self._queue_analyses.items():
                if analyses:
                    latest = analyses[-1]
                    queue_status[queue_name] = {
                        "depth": latest.current_depth,
                        "congestion": latest.congestion_level,
                        "processing_rate": latest.processing_rate
                    }
            
            return {
                "timestamp": timestamp.isoformat(),
                "resource_utilization": latest_metrics,
                "active_bottlenecks": len(active_bottlenecks),
                "bottleneck_summary": [
                    {
                        "id": b.detection_id,
                        "type": b.bottleneck_type.value,
                        "severity": b.severity.value,
                        "component": b.component
                    } for b in active_bottlenecks
                ],
                "queue_status": queue_status,
                "overall_health": self._calculate_overall_health(latest_metrics, active_bottlenecks)
            }
    
    def _calculate_overall_health(self, metrics: Dict[str, float], 
                                bottlenecks: List[BottleneckDetection]) -> str:
        """Calculate overall system health based on metrics and bottlenecks"""
        if any(b.severity == SeverityLevel.CRITICAL for b in bottlenecks):
            return "CRITICAL"
        elif any(b.severity == SeverityLevel.HIGH for b in bottlenecks):
            return "DEGRADED"
        elif len(bottlenecks) > 0:
            return "WARNING"
        else:
            return "HEALTHY"
    
    def get_bottleneck_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get bottleneck detection history"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_bottlenecks = [b for b in self._bottleneck_detections 
                                if b.timestamp >= cutoff_time]
            
            return [
                {
                    "id": b.detection_id,
                    "timestamp": b.timestamp.isoformat(),
                    "type": b.bottleneck_type.value,
                    "severity": b.severity.value,
                    "component": b.component,
                    "description": b.description,
                    "current_value": b.current_value,
                    "threshold_value": b.threshold_value,
                    "recommendations": b.optimization_recommendations,
                    "status": b.resolution_status
                } for b in recent_bottlenecks
            ]
    
    def get_optimization_recommendations(self) -> List[OptimizationRecommendation]:
        """Get comprehensive optimization recommendations"""
        recommendations = []
        
        # Analyze recent bottlenecks for patterns
        with self._lock:
            recent_bottlenecks = [b for b in self._bottleneck_detections 
                                if (datetime.now() - b.timestamp).total_seconds() < 86400]  # Last 24 hours
        
        # Group by bottleneck type
        bottleneck_counts = defaultdict(int)
        for bottleneck in recent_bottlenecks:
            bottleneck_counts[bottleneck.bottleneck_type] += 1
        
        # Generate recommendations based on patterns
        for bottleneck_type, count in bottleneck_counts.items():
            if count >= 3:  # Recurring bottleneck
                rec = OptimizationRecommendation(
                    recommendation_id=f"OPT_{bottleneck_type.value}_{int(time.time())}",
                    bottleneck_type=bottleneck_type,
                    priority=SeverityLevel.HIGH,
                    title=f"Address Recurring {bottleneck_type.value.replace('_', ' ').title()} Issues",
                    description=f"Detected {count} instances of {bottleneck_type.value} bottlenecks in the last 24 hours",
                    implementation_steps=self._get_implementation_steps(bottleneck_type),
                    expected_improvement=f"Reduce {bottleneck_type.value} bottlenecks by 70-90%",
                    implementation_effort="MEDIUM",
                    risk_level="LOW"
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _get_implementation_steps(self, bottleneck_type: BottleneckType) -> List[str]:
        """Get implementation steps for bottleneck type"""
        steps_map = {
            BottleneckType.CPU_BOUND: [
                "Profile application to identify CPU hotspots",
                "Optimize algorithms and data structures",
                "Implement horizontal scaling",
                "Add CPU-based load balancing"
            ],
            BottleneckType.MEMORY_BOUND: [
                "Analyze memory usage patterns",
                "Implement memory pooling",
                "Optimize data structures",
                "Add memory monitoring and alerts"
            ],
            BottleneckType.QUEUE_CONGESTION: [
                "Increase queue processing workers",
                "Implement priority queues",
                "Add queue partitioning",
                "Optimize queue processing algorithms"
            ]
        }
        return steps_map.get(bottleneck_type, ["Analyze and optimize system performance"])
    
    def resolve_bottleneck(self, detection_id: str) -> bool:
        """Mark a bottleneck as resolved"""
        with self._lock:
            for bottleneck in self._bottleneck_detections:
                if bottleneck.detection_id == detection_id:
                    bottleneck.resolution_status = "RESOLVED"
                    bottleneck.resolution_time = datetime.now()
                    logger.info("Bottleneck resolved: %s", detection_id)
                    return True
            return False
    
    def export_performance_report(self) -> str:
        """Export comprehensive performance report"""
        with self._lock:
            report = {
                "timestamp": datetime.now().isoformat(),
                "performance_status": self.get_current_performance_status(),
                "bottleneck_history": self.get_bottleneck_history(24),
                "optimization_recommendations": [
                    {
                        "id": r.recommendation_id,
                        "type": r.bottleneck_type.value,
                        "priority": r.priority.value,
                        "title": r.title,
                        "description": r.description,
                        "steps": r.implementation_steps,
                        "improvement": r.expected_improvement,
                        "effort": r.implementation_effort,
                        "risk": r.risk_level
                    } for r in self.get_optimization_recommendations()
                ],
                "system_metrics": {
                    "total_metrics_collected": len(self._performance_metrics),
                    "total_bottlenecks_detected": len(self._bottleneck_detections),
                    "monitored_queues": list(self._monitored_queues.keys()),
                    "monitoring_active": self._monitoring_active
                }
            }
            
            return json.dumps(report, indent=2, default=str)