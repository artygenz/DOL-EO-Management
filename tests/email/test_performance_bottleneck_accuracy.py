"""
Performance Tests for Bottleneck Detection Accuracy

Tests the accuracy and performance of bottleneck detection algorithms
under various load conditions and scenarios.

Requirements: 7.4, 6.1, 6.3
"""

import pytest
import time
import threading
import queue
import random
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

from src.email.performance_monitor import (
    PerformanceMonitor, BottleneckType, SeverityLevel, ResourceType
)


class TestBottleneckDetectionAccuracy:
    """Test bottleneck detection accuracy under various conditions"""
    
    @pytest.fixture
    def monitor(self):
        """Create a performance monitor for accuracy testing"""
        return PerformanceMonitor(check_interval=0.1)  # Very fast for testing
    
    def test_cpu_bottleneck_detection_accuracy(self, monitor):
        """Test accuracy of CPU bottleneck detection"""
        # Set precise thresholds
        monitor.set_resource_threshold(ResourceType.CPU, 70.0, 85.0)
        
        test_cases = [
            (60.0, None),           # Below warning - no bottleneck
            (75.0, SeverityLevel.HIGH),     # Above warning - high severity
            (90.0, SeverityLevel.CRITICAL), # Above critical - critical severity
            (69.9, None),           # Just below warning - no bottleneck
            (70.1, SeverityLevel.HIGH),     # Just above warning - high severity
            (84.9, SeverityLevel.HIGH),     # Just below critical - high severity
            (85.1, SeverityLevel.CRITICAL), # Just above critical - critical severity
        ]
        
        correct_detections = 0
        total_tests = len(test_cases)
        
        for cpu_value, expected_severity in test_cases:
            # Clear previous detections
            monitor._bottleneck_detections.clear()
            
            # Record CPU metric
            timestamp = datetime.now()
            monitor._record_metric(timestamp, ResourceType.CPU, cpu_value, "percentage", "system")
            
            # Detect bottlenecks
            monitor._detect_bottlenecks()
            
            # Check detection accuracy
            cpu_bottlenecks = [b for b in monitor._bottleneck_detections 
                              if b.bottleneck_type == BottleneckType.CPU_BOUND]
            
            if expected_severity is None:
                # Should not detect bottleneck
                if len(cpu_bottlenecks) == 0:
                    correct_detections += 1
            else:
                # Should detect bottleneck with correct severity
                if (len(cpu_bottlenecks) == 1 and 
                    cpu_bottlenecks[0].severity == expected_severity):
                    correct_detections += 1
        
        accuracy = (correct_detections / total_tests) * 100
        assert accuracy >= 95.0, f"CPU bottleneck detection accuracy: {accuracy}% (expected >= 95%)"
    
    def test_memory_bottleneck_detection_accuracy(self, monitor):
        """Test accuracy of memory bottleneck detection"""
        monitor.set_resource_threshold(ResourceType.MEMORY, 75.0, 90.0)
        
        test_cases = [
            (65.0, None),
            (80.0, SeverityLevel.HIGH),
            (95.0, SeverityLevel.CRITICAL),
            (74.9, None),
            (75.1, SeverityLevel.HIGH),
            (89.9, SeverityLevel.HIGH),
            (90.1, SeverityLevel.CRITICAL),
        ]
        
        correct_detections = 0
        
        for memory_value, expected_severity in test_cases:
            monitor._bottleneck_detections.clear()
            
            timestamp = datetime.now()
            monitor._record_metric(timestamp, ResourceType.MEMORY, memory_value, "percentage", "system")
            
            monitor._detect_bottlenecks()
            
            memory_bottlenecks = [b for b in monitor._bottleneck_detections 
                                 if b.bottleneck_type == BottleneckType.MEMORY_BOUND]
            
            if expected_severity is None:
                if len(memory_bottlenecks) == 0:
                    correct_detections += 1
            else:
                if (len(memory_bottlenecks) == 1 and 
                    memory_bottlenecks[0].severity == expected_severity):
                    correct_detections += 1
        
        accuracy = (correct_detections / len(test_cases)) * 100
        assert accuracy >= 95.0, f"Memory bottleneck detection accuracy: {accuracy}%"
    
    def test_queue_congestion_detection_accuracy(self, monitor):
        """Test accuracy of queue congestion detection"""
        monitor.set_resource_threshold(ResourceType.QUEUE_DEPTH, 50, 100)
        
        test_queue = queue.Queue()
        monitor.register_queue("accuracy_test_queue", test_queue)
        
        test_cases = [
            (25, None),             # Below warning
            (60, SeverityLevel.HIGH),       # Above warning
            (120, SeverityLevel.CRITICAL),  # Above critical
            (49, None),             # Just below warning
            (51, SeverityLevel.HIGH),       # Just above warning
            (99, SeverityLevel.HIGH),       # Just below critical
            (101, SeverityLevel.CRITICAL),  # Just above critical
        ]
        
        correct_detections = 0
        
        for queue_depth, expected_severity in test_cases:
            # Clear queue and detections
            while not test_queue.empty():
                test_queue.get()
            monitor._bottleneck_detections.clear()
            
            # Fill queue to desired depth
            for i in range(queue_depth):
                test_queue.put(f"item_{i}")
            
            # Analyze and detect
            monitor._analyze_queue_performance()
            monitor._detect_bottlenecks()
            
            # Check accuracy
            queue_bottlenecks = [b for b in monitor._bottleneck_detections 
                               if b.bottleneck_type == BottleneckType.QUEUE_CONGESTION]
            
            if expected_severity is None:
                if len(queue_bottlenecks) == 0:
                    correct_detections += 1
            else:
                if (len(queue_bottlenecks) == 1 and 
                    queue_bottlenecks[0].severity == expected_severity):
                    correct_detections += 1
        
        accuracy = (correct_detections / len(test_cases)) * 100
        assert accuracy >= 95.0, f"Queue congestion detection accuracy: {accuracy}%"
    
    def test_processing_time_bottleneck_accuracy(self, monitor):
        """Test accuracy of processing time bottleneck detection"""
        monitor.set_resource_threshold(ResourceType.PROCESSING_TIME, 1000.0, 2000.0)  # 1s warning, 2s critical
        
        test_cases = [
            (500, None),            # 500ms - below warning
            (1200, SeverityLevel.HIGH),     # 1.2s - above warning
            (2500, SeverityLevel.CRITICAL), # 2.5s - above critical
            (999, None),            # Just below warning
            (1001, SeverityLevel.HIGH),     # Just above warning
            (1999, SeverityLevel.HIGH),     # Just below critical
            (2001, SeverityLevel.CRITICAL), # Just above critical
        ]
        
        correct_detections = 0
        
        for duration_ms, expected_severity in test_cases:
            monitor._bottleneck_detections.clear()
            
            # Simulate operation with specific duration
            start_time = time.time()
            end_time = start_time + (duration_ms / 1000.0)
            
            # Manually create processing metric
            timestamp = datetime.now()
            monitor._record_metric(timestamp, ResourceType.PROCESSING_TIME, duration_ms, 
                                 "milliseconds", "test_component", {"operation": "test_op"})
            
            # Detect bottlenecks
            monitor._detect_bottlenecks()
            
            # Check accuracy
            processing_bottlenecks = [b for b in monitor._bottleneck_detections 
                                    if b.bottleneck_type == BottleneckType.CLASSIFICATION_SLOWDOWN]
            
            if expected_severity is None:
                if len(processing_bottlenecks) == 0:
                    correct_detections += 1
            else:
                if (len(processing_bottlenecks) == 1 and 
                    processing_bottlenecks[0].severity == expected_severity):
                    correct_detections += 1
        
        accuracy = (correct_detections / len(test_cases)) * 100
        assert accuracy >= 95.0, f"Processing time bottleneck detection accuracy: {accuracy}%"
    
    def test_false_positive_rate(self, monitor):
        """Test false positive rate for bottleneck detection"""
        # Set reasonable thresholds
        monitor.set_resource_threshold(ResourceType.CPU, 70.0, 85.0)
        monitor.set_resource_threshold(ResourceType.MEMORY, 75.0, 90.0)
        
        # Generate metrics that should NOT trigger bottlenecks
        safe_values = [
            (ResourceType.CPU, [50.0, 55.0, 60.0, 65.0, 69.0]),
            (ResourceType.MEMORY, [60.0, 65.0, 70.0, 74.0, 74.9]),
        ]
        
        false_positives = 0
        total_tests = 0
        
        for resource_type, values in safe_values:
            for value in values:
                monitor._bottleneck_detections.clear()
                
                timestamp = datetime.now()
                monitor._record_metric(timestamp, resource_type, value, "percentage", "system")
                
                monitor._detect_bottlenecks()
                
                # Count any bottlenecks as false positives
                relevant_bottlenecks = [b for b in monitor._bottleneck_detections 
                                      if (resource_type == ResourceType.CPU and 
                                          b.bottleneck_type == BottleneckType.CPU_BOUND) or
                                         (resource_type == ResourceType.MEMORY and 
                                          b.bottleneck_type == BottleneckType.MEMORY_BOUND)]
                
                if len(relevant_bottlenecks) > 0:
                    false_positives += 1
                
                total_tests += 1
        
        false_positive_rate = (false_positives / total_tests) * 100
        assert false_positive_rate <= 5.0, f"False positive rate: {false_positive_rate}% (expected <= 5%)"
    
    def test_detection_latency_performance(self, monitor):
        """Test bottleneck detection latency performance"""
        monitor.set_resource_threshold(ResourceType.CPU, 60.0, 80.0)
        
        detection_times = []
        
        # Test detection latency for multiple scenarios
        for i in range(50):
            monitor._bottleneck_detections.clear()
            
            # Record metric
            timestamp = datetime.now()
            monitor._record_metric(timestamp, ResourceType.CPU, 85.0, "percentage", "system")
            
            # Time the detection process
            start_time = time.time()
            monitor._detect_bottlenecks()
            end_time = time.time()
            
            detection_time_ms = (end_time - start_time) * 1000
            detection_times.append(detection_time_ms)
        
        # Analyze detection performance
        avg_detection_time = statistics.mean(detection_times)
        max_detection_time = max(detection_times)
        p95_detection_time = sorted(detection_times)[int(len(detection_times) * 0.95)]
        
        # Performance requirements
        assert avg_detection_time <= 50.0, f"Average detection time: {avg_detection_time}ms (expected <= 50ms)"
        assert max_detection_time <= 200.0, f"Max detection time: {max_detection_time}ms (expected <= 200ms)"
        assert p95_detection_time <= 100.0, f"P95 detection time: {p95_detection_time}ms (expected <= 100ms)"
    
    def test_concurrent_detection_accuracy(self, monitor):
        """Test bottleneck detection accuracy under concurrent load"""
        monitor.set_resource_threshold(ResourceType.CPU, 70.0, 85.0)
        monitor.set_resource_threshold(ResourceType.MEMORY, 75.0, 90.0)
        
        def simulate_metrics(thread_id):
            """Simulate metrics generation in a thread"""
            results = []
            
            for i in range(10):
                # Generate random metrics that should trigger bottlenecks
                cpu_value = random.uniform(80.0, 95.0)  # Above warning threshold
                memory_value = random.uniform(80.0, 95.0)  # Above warning threshold
                
                timestamp = datetime.now()
                monitor._record_metric(timestamp, ResourceType.CPU, cpu_value, "percentage", f"thread_{thread_id}")
                monitor._record_metric(timestamp, ResourceType.MEMORY, memory_value, "percentage", f"thread_{thread_id}")
                
                time.sleep(0.01)  # Small delay
                
                results.append((cpu_value, memory_value))
            
            return results
        
        # Run concurrent metric generation
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(simulate_metrics, i) for i in range(5)]
            
            # Wait for all threads to complete
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        # Run detection after all metrics are recorded
        monitor._detect_bottlenecks()
        
        # Analyze results
        cpu_bottlenecks = [b for b in monitor._bottleneck_detections 
                          if b.bottleneck_type == BottleneckType.CPU_BOUND]
        memory_bottlenecks = [b for b in monitor._bottleneck_detections 
                             if b.bottleneck_type == BottleneckType.MEMORY_BOUND]
        
        # Should detect bottlenecks (exact count may vary due to timing)
        assert len(cpu_bottlenecks) > 0, "Should detect CPU bottlenecks under concurrent load"
        assert len(memory_bottlenecks) > 0, "Should detect memory bottlenecks under concurrent load"
        
        # Check that all detections have valid data
        for bottleneck in cpu_bottlenecks + memory_bottlenecks:
            assert bottleneck.current_value > 0
            assert bottleneck.threshold_value > 0
            assert len(bottleneck.optimization_recommendations) > 0
    
    def test_threshold_boundary_accuracy(self, monitor):
        """Test detection accuracy at threshold boundaries"""
        monitor.set_resource_threshold(ResourceType.CPU, 70.0, 85.0)
        
        # Test values very close to thresholds
        boundary_tests = [
            (69.99, None),          # Just below warning
            (70.00, SeverityLevel.HIGH),    # Exactly at warning
            (70.01, SeverityLevel.HIGH),    # Just above warning
            (84.99, SeverityLevel.HIGH),    # Just below critical
            (85.00, SeverityLevel.CRITICAL), # Exactly at critical
            (85.01, SeverityLevel.CRITICAL), # Just above critical
        ]
        
        correct_detections = 0
        
        for cpu_value, expected_severity in boundary_tests:
            monitor._bottleneck_detections.clear()
            
            timestamp = datetime.now()
            monitor._record_metric(timestamp, ResourceType.CPU, cpu_value, "percentage", "system")
            
            monitor._detect_bottlenecks()
            
            cpu_bottlenecks = [b for b in monitor._bottleneck_detections 
                              if b.bottleneck_type == BottleneckType.CPU_BOUND]
            
            if expected_severity is None:
                if len(cpu_bottlenecks) == 0:
                    correct_detections += 1
            else:
                if (len(cpu_bottlenecks) == 1 and 
                    cpu_bottlenecks[0].severity == expected_severity):
                    correct_detections += 1
        
        accuracy = (correct_detections / len(boundary_tests)) * 100
        assert accuracy >= 95.0, f"Boundary detection accuracy: {accuracy}%"
    
    def test_recommendation_quality(self, monitor):
        """Test quality and relevance of optimization recommendations"""
        # Test different bottleneck types
        bottleneck_scenarios = [
            (BottleneckType.CPU_BOUND, ["cpu", "scaling", "optimize", "process"]),
            (BottleneckType.MEMORY_BOUND, ["memory", "cache", "optimize", "pool"]),
            (BottleneckType.QUEUE_CONGESTION, ["queue", "worker", "capacity", "process"]),
            (BottleneckType.IO_BOUND, ["database", "query", "connection", "index"]),
        ]
        
        for bottleneck_type, expected_keywords in bottleneck_scenarios:
            # Create a mock metric
            mock_metric = Mock()
            mock_metric.component = "test_component"
            
            recommendations = monitor._generate_optimization_recommendations(
                bottleneck_type, SeverityLevel.HIGH, mock_metric
            )
            
            # Check recommendation quality
            assert len(recommendations) >= 3, f"Should have at least 3 recommendations for {bottleneck_type}"
            
            # Check that recommendations contain relevant keywords
            all_recommendations_text = " ".join(recommendations).lower()
            keyword_matches = sum(1 for keyword in expected_keywords 
                                if keyword in all_recommendations_text)
            
            keyword_coverage = (keyword_matches / len(expected_keywords)) * 100
            assert keyword_coverage >= 50.0, f"Recommendation relevance for {bottleneck_type}: {keyword_coverage}%"
    
    def test_detection_consistency(self, monitor):
        """Test consistency of bottleneck detection across multiple runs"""
        monitor.set_resource_threshold(ResourceType.CPU, 70.0, 85.0)
        
        # Test same conditions multiple times
        test_value = 90.0  # Should consistently trigger critical bottleneck
        detection_results = []
        
        for run in range(20):
            monitor._bottleneck_detections.clear()
            
            timestamp = datetime.now()
            monitor._record_metric(timestamp, ResourceType.CPU, test_value, "percentage", "system")
            
            monitor._detect_bottlenecks()
            
            cpu_bottlenecks = [b for b in monitor._bottleneck_detections 
                              if b.bottleneck_type == BottleneckType.CPU_BOUND]
            
            if len(cpu_bottlenecks) == 1:
                detection_results.append(cpu_bottlenecks[0].severity)
            else:
                detection_results.append(None)
        
        # Check consistency
        critical_detections = sum(1 for result in detection_results 
                                if result == SeverityLevel.CRITICAL)
        consistency_rate = (critical_detections / len(detection_results)) * 100
        
        assert consistency_rate >= 95.0, f"Detection consistency: {consistency_rate}% (expected >= 95%)"


class TestPerformanceUnderLoad:
    """Test performance monitoring system under various load conditions"""
    
    @pytest.fixture
    def monitor(self):
        """Create a performance monitor for load testing"""
        return PerformanceMonitor(check_interval=0.1)
    
    def test_high_frequency_metrics_performance(self, monitor):
        """Test performance with high-frequency metric collection"""
        start_time = time.time()
        
        # Generate high-frequency metrics
        for i in range(1000):
            timestamp = datetime.now()
            cpu_value = random.uniform(50.0, 100.0)
            memory_value = random.uniform(60.0, 95.0)
            
            monitor._record_metric(timestamp, ResourceType.CPU, cpu_value, "percentage", "system")
            monitor._record_metric(timestamp, ResourceType.MEMORY, memory_value, "percentage", "system")
        
        collection_time = time.time() - start_time
        
        # Performance requirements
        assert collection_time <= 5.0, f"High-frequency collection time: {collection_time}s (expected <= 5s)"
        assert len(monitor._performance_metrics) == 2000  # 1000 CPU + 1000 memory metrics
        
        # Test detection performance with large dataset
        detection_start = time.time()
        monitor._detect_bottlenecks()
        detection_time = time.time() - detection_start
        
        assert detection_time <= 2.0, f"Detection time with 2000 metrics: {detection_time}s (expected <= 2s)"
    
    def test_concurrent_queue_monitoring_performance(self, monitor):
        """Test performance with multiple concurrent queues"""
        # Create multiple queues
        queues = {}
        for i in range(10):
            queue_name = f"queue_{i}"
            test_queue = queue.Queue()
            queues[queue_name] = test_queue
            monitor.register_queue(queue_name, test_queue)
        
        # Fill queues with different loads
        for i, (queue_name, test_queue) in enumerate(queues.items()):
            queue_size = (i + 1) * 20  # 20, 40, 60, ... 200 items
            for j in range(queue_size):
                test_queue.put(f"item_{j}")
        
        # Test analysis performance
        start_time = time.time()
        monitor._analyze_queue_performance()
        analysis_time = time.time() - start_time
        
        assert analysis_time <= 1.0, f"Queue analysis time for 10 queues: {analysis_time}s (expected <= 1s)"
        
        # Verify all queues were analyzed
        assert len(monitor._queue_analyses) == 10
        
        for queue_name in queues.keys():
            assert queue_name in monitor._queue_analyses
            assert len(monitor._queue_analyses[queue_name]) >= 1
    
    def test_memory_usage_under_load(self, monitor):
        """Test memory usage of monitoring system under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate large amount of data
        for i in range(5000):
            timestamp = datetime.now()
            monitor._record_metric(timestamp, ResourceType.CPU, random.uniform(0, 100), "percentage", "system")
            
            # Add some processing time data
            monitor.start_operation_timer(f"op_{i}", "component", "operation")
            time.sleep(0.001)  # 1ms
            monitor.end_operation_timer(f"op_{i}", "component", "operation")
            
            # Trigger analysis periodically
            if i % 100 == 0:
                monitor._analyze_processing_times()
                monitor._detect_bottlenecks()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory usage should be reasonable (less than 100MB increase)
        assert memory_increase <= 100.0, f"Memory increase: {memory_increase}MB (expected <= 100MB)"
    
    def test_bottleneck_detection_scalability(self, monitor):
        """Test bottleneck detection scalability with many metrics"""
        # Set multiple thresholds
        monitor.set_resource_threshold(ResourceType.CPU, 70.0, 85.0)
        monitor.set_resource_threshold(ResourceType.MEMORY, 75.0, 90.0)
        monitor.set_resource_threshold(ResourceType.PROCESSING_TIME, 1000.0, 2000.0)
        
        # Generate metrics that will trigger bottlenecks
        bottleneck_metrics = [
            (ResourceType.CPU, 90.0),
            (ResourceType.MEMORY, 95.0),
            (ResourceType.PROCESSING_TIME, 2500.0),
        ]
        
        # Generate many instances of each
        for _ in range(100):
            for resource_type, value in bottleneck_metrics:
                timestamp = datetime.now()
                unit = "percentage" if resource_type != ResourceType.PROCESSING_TIME else "milliseconds"
                monitor._record_metric(timestamp, resource_type, value, unit, "system")
        
        # Test detection performance
        start_time = time.time()
        monitor._detect_bottlenecks()
        detection_time = time.time() - start_time
        
        # Should complete detection quickly even with many metrics
        assert detection_time <= 3.0, f"Detection time with 300 bottleneck metrics: {detection_time}s"
        
        # Should detect bottlenecks for each type
        cpu_bottlenecks = [b for b in monitor._bottleneck_detections 
                          if b.bottleneck_type == BottleneckType.CPU_BOUND]
        memory_bottlenecks = [b for b in monitor._bottleneck_detections 
                             if b.bottleneck_type == BottleneckType.MEMORY_BOUND]
        processing_bottlenecks = [b for b in monitor._bottleneck_detections 
                                if b.bottleneck_type == BottleneckType.CLASSIFICATION_SLOWDOWN]
        
        assert len(cpu_bottlenecks) > 0
        assert len(memory_bottlenecks) > 0
        assert len(processing_bottlenecks) > 0


if __name__ == "__main__":
    pytest.main([__file__])