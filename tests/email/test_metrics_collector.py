"""
Unit tests for MetricsCollector

Tests comprehensive metrics collection including:
- Email processing latency and throughput metrics
- Classification accuracy rate monitoring  
- Connection health and uptime tracking
- Security incident counting and categorization
- Real-time reporting accuracy

Requirements: 7.1, 7.2
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.email.metrics_collector import (
    MetricsCollector, MetricType, SecurityIncidentType,
    ProcessingMetric, ThroughputMetric, ClassificationAccuracyMetric,
    ConnectionHealthMetric, SecurityIncidentMetric, SystemHealthSnapshot
)


class TestMetricsCollector:
    """Test suite for MetricsCollector"""
    
    @pytest.fixture
    def collector(self):
        """Create a metrics collector for testing"""
        return MetricsCollector(retention_hours=1)
    
    def test_initialization(self, collector):
        """Test metrics collector initialization"""
        assert collector.retention_hours == 1
        assert len(collector._processing_metrics) == 0
        assert len(collector._classification_metrics) == 0
        assert len(collector._security_incidents) == 0
        assert collector._system_start_time > 0
    
    def test_processing_timer_lifecycle(self, collector):
        """Test complete processing timer lifecycle"""
        email_uid = "test_email_123"
        
        # Start timer
        collector.start_processing_timer(email_uid)
        assert email_uid in collector._active_processing
        
        # Simulate processing time
        time.sleep(0.01)
        
        # End timer
        collector.end_processing_timer(
            email_uid=email_uid,
            classification_type="NEW_EO",
            confidence_score=0.95,
            success=True
        )
        
        # Verify metric was recorded
        assert len(collector._processing_metrics) == 1
        metric = collector._processing_metrics[0]
        assert metric.email_uid == email_uid
        assert metric.classification_type == "NEW_EO"
        assert metric.confidence_score == 0.95
        assert metric.success is True
        assert metric.latency_ms > 0
        assert email_uid not in collector._active_processing
    
    def test_processing_timer_with_error(self, collector):
        """Test processing timer with error handling"""
        email_uid = "error_email_123"
        
        collector.start_processing_timer(email_uid)
        time.sleep(0.01)
        
        collector.end_processing_timer(
            email_uid=email_uid,
            classification_type="PMO_RESPONSE",
            confidence_score=0.60,
            success=False,
            error_type="CLASSIFICATION_ERROR"
        )
        
        metric = collector._processing_metrics[0]
        assert metric.success is False
        assert metric.error_type == "CLASSIFICATION_ERROR"
        assert metric.confidence_score == 0.60
    
    def test_processing_timer_missing_start(self, collector):
        """Test ending timer without starting it"""
        # Should not crash, just log warning
        collector.end_processing_timer(
            email_uid="missing_email",
            classification_type="NEW_EO",
            confidence_score=0.95
        )
        
        # No metrics should be recorded
        assert len(collector._processing_metrics) == 0
    
    def test_classification_accuracy_recording(self, collector):
        """Test classification accuracy metric recording"""
        # Record correct classification
        collector.record_classification_accuracy(
            email_type="NEW_EO",
            predicted="NEW_EO",
            actual="NEW_EO",
            confidence=0.95
        )
        
        # Record incorrect classification
        collector.record_classification_accuracy(
            email_type="PMO_RESPONSE",
            predicted="PMO_RESPONSE",
            actual="DEVELOPER_UPDATE",
            confidence=0.75
        )
        
        # Record classification without actual (prediction only)
        collector.record_classification_accuracy(
            email_type="EXECUTIVE_REQUEST",
            predicted="EXECUTIVE_REQUEST",
            actual=None,
            confidence=0.88,
            manual_review=True
        )
        
        assert len(collector._classification_metrics) == 3
        
        # Check first metric (correct)
        metric1 = collector._classification_metrics[0]
        assert metric1.email_type == "NEW_EO"
        assert metric1.correct_prediction is True
        assert metric1.manual_review_required is False
        
        # Check second metric (incorrect)
        metric2 = collector._classification_metrics[1]
        assert metric2.email_type == "PMO_RESPONSE"
        assert metric2.correct_prediction is False
        
        # Check third metric (no actual)
        metric3 = collector._classification_metrics[2]
        assert metric3.email_type == "EXECUTIVE_REQUEST"
        assert metric3.correct_prediction is None
        assert metric3.manual_review_required is True
    
    def test_connection_health_recording(self, collector):
        """Test connection health metric recording"""
        connection_id = "imap_connection_1"
        
        # Record healthy connection
        collector.record_connection_health(
            connection_id=connection_id,
            connection_type="IMAP",
            status="HEALTHY",
            response_time_ms=150.5,
            error_count=0
        )
        
        assert len(collector._connection_metrics[connection_id]) == 1
        assert connection_id in collector._connection_status
        
        metric = collector._connection_status[connection_id]
        assert metric.status == "HEALTHY"
        assert metric.response_time_ms == 150.5
        assert metric.uptime_percentage == 100.0
        
        # Record degraded connection
        collector.record_connection_health(
            connection_id=connection_id,
            connection_type="IMAP",
            status="DEGRADED",
            response_time_ms=500.0,
            error_count=2
        )
        
        assert len(collector._connection_metrics[connection_id]) == 2
        updated_metric = collector._connection_status[connection_id]
        assert updated_metric.status == "DEGRADED"
        assert updated_metric.error_count == 2
    
    def test_security_incident_recording(self, collector):
        """Test security incident recording and resolution"""
        # Record security incident
        incident_id = collector.record_security_incident(
            incident_type=SecurityIncidentType.MALWARE_DETECTED,
            severity="HIGH",
            description="Malware found in email attachment",
            email_uid="malware_email_123",
            sender="suspicious@example.com"
        )
        
        assert incident_id.startswith("SEC_")
        assert len(collector._security_incidents) == 1
        
        incident = collector._security_incidents[0]
        assert incident.incident_id == incident_id
        assert incident.incident_type == SecurityIncidentType.MALWARE_DETECTED
        assert incident.severity == "HIGH"
        assert incident.resolved is False
        
        # Resolve incident
        resolved = collector.resolve_security_incident(incident_id)
        assert resolved is True
        assert incident.resolved is True
        assert incident.resolution_time is not None
        
        # Try to resolve non-existent incident
        not_resolved = collector.resolve_security_incident("fake_incident")
        assert not_resolved is False
    
    def test_processing_latency_metrics(self, collector):
        """Test processing latency metrics calculation"""
        # Add some test metrics
        test_latencies = [100.0, 150.0, 200.0, 250.0, 300.0]
        
        for i, latency in enumerate(test_latencies):
            email_uid = f"test_email_{i}"
            collector.start_processing_timer(email_uid)
            
            # Simulate the latency by directly adding the metric
            metric = ProcessingMetric(
                timestamp=datetime.now(),
                email_uid=email_uid,
                processing_start_time=time.time() - latency/1000,
                processing_end_time=time.time(),
                latency_ms=latency,
                classification_type="NEW_EO",
                confidence_score=0.95,
                success=True
            )
            collector._processing_metrics.append(metric)
        
        latency_metrics = collector.get_processing_latency_metrics(1)
        
        assert latency_metrics["total_processed"] == 5
        assert latency_metrics["average_latency_ms"] == 200.0
        assert latency_metrics["median_latency_ms"] == 200.0
        assert latency_metrics["min_latency_ms"] == 100.0
        assert latency_metrics["max_latency_ms"] == 300.0
        assert latency_metrics["p95_latency_ms"] >= 250.0
    
    def test_throughput_metrics(self, collector):
        """Test throughput metrics calculation"""
        # Add metrics over time
        base_time = datetime.now() - timedelta(minutes=30)
        
        for i in range(10):
            metric = ProcessingMetric(
                timestamp=base_time + timedelta(minutes=i*3),
                email_uid=f"email_{i}",
                processing_start_time=time.time(),
                processing_end_time=time.time(),
                latency_ms=100.0,
                classification_type="NEW_EO",
                confidence_score=0.95,
                success=True
            )
            collector._processing_metrics.append(metric)
        
        throughput_metrics = collector.get_throughput_metrics(1)
        
        assert throughput_metrics["total_emails"] == 10
        assert throughput_metrics["emails_per_hour"] > 0
        assert throughput_metrics["emails_per_minute"] > 0
    
    def test_classification_accuracy_metrics(self, collector):
        """Test classification accuracy metrics calculation"""
        # Add test classification results
        test_cases = [
            ("NEW_EO", "NEW_EO", "NEW_EO", True),  # Correct
            ("NEW_EO", "NEW_EO", "PMO_RESPONSE", False),  # Incorrect
            ("PMO_RESPONSE", "PMO_RESPONSE", "PMO_RESPONSE", True),  # Correct
            ("PMO_RESPONSE", "PMO_RESPONSE", "PMO_RESPONSE", True),  # Correct
        ]
        
        for email_type, predicted, actual, expected_correct in test_cases:
            collector.record_classification_accuracy(
                email_type=email_type,
                predicted=predicted,
                actual=actual,
                confidence=0.90
            )
        
        accuracy_metrics = collector.get_classification_accuracy_metrics()
        
        assert accuracy_metrics["total_classifications"] == 4
        assert accuracy_metrics["overall_accuracy"] == 75.0  # 3 correct out of 4
        assert accuracy_metrics["by_type"]["NEW_EO"] == 50.0  # 1 correct out of 2
        assert accuracy_metrics["by_type"]["PMO_RESPONSE"] == 100.0  # 2 correct out of 2
    
    def test_connection_health_metrics(self, collector):
        """Test connection health metrics aggregation"""
        # Add multiple connection health records
        connections = [
            ("imap_1", "IMAP", "HEALTHY", 100.0, 0),
            ("smtp_1", "SMTP", "HEALTHY", 200.0, 1),
            ("imap_2", "IMAP", "DEGRADED", 500.0, 3)
        ]
        
        for conn_id, conn_type, status, response_time, errors in connections:
            collector.record_connection_health(
                connection_id=conn_id,
                connection_type=conn_type,
                status=status,
                response_time_ms=response_time,
                error_count=errors
            )
        
        health_metrics = collector.get_connection_health_metrics()
        
        assert len(health_metrics) == 3
        assert health_metrics["imap_1"]["status"] == "HEALTHY"
        assert health_metrics["imap_1"]["uptime_percentage"] == 100.0
        assert health_metrics["smtp_1"]["total_errors"] == 1
        assert health_metrics["imap_2"]["status"] == "DEGRADED"
    
    def test_security_incident_metrics(self, collector):
        """Test security incident metrics aggregation"""
        # Add various security incidents
        incidents = [
            (SecurityIncidentType.MALWARE_DETECTED, "HIGH"),
            (SecurityIncidentType.PHISHING_ATTEMPT, "MEDIUM"),
            (SecurityIncidentType.MALWARE_DETECTED, "CRITICAL"),
            (SecurityIncidentType.UNAUTHORIZED_SENDER, "LOW")
        ]
        
        incident_ids = []
        for incident_type, severity in incidents:
            incident_id = collector.record_security_incident(
                incident_type=incident_type,
                severity=severity,
                description=f"Test {incident_type.value} incident"
            )
            incident_ids.append(incident_id)
        
        # Resolve one incident
        collector.resolve_security_incident(incident_ids[0])
        
        security_metrics = collector.get_security_incident_metrics(24)
        
        assert security_metrics["total_incidents"] == 4
        assert security_metrics["resolved_incidents"] == 1
        assert security_metrics["unresolved_incidents"] == 3
        assert security_metrics["by_type"]["malware_detected"] == 2
        assert security_metrics["by_type"]["phishing_attempt"] == 1
        assert security_metrics["by_severity"]["HIGH"] == 1
        assert security_metrics["by_severity"]["CRITICAL"] == 1
        assert security_metrics["resolution_rate"] == 25.0
    
    def test_system_uptime_metrics(self, collector):
        """Test system uptime metrics"""
        uptime_metrics = collector.get_system_uptime_metrics()
        
        assert "uptime_seconds" in uptime_metrics
        assert "uptime_hours" in uptime_metrics
        assert "uptime_days" in uptime_metrics
        assert "start_time" in uptime_metrics
        assert "current_time" in uptime_metrics
        
        assert uptime_metrics["uptime_seconds"] > 0
        assert uptime_metrics["uptime_hours"] >= 0
        assert uptime_metrics["uptime_days"] >= 0
    
    def test_comprehensive_health_snapshot(self, collector):
        """Test comprehensive health snapshot generation"""
        # Add some test data
        collector.start_processing_timer("test_email")
        time.sleep(0.01)
        collector.end_processing_timer("test_email", "NEW_EO", 0.95)
        
        collector.record_connection_health("test_conn", "IMAP", "HEALTHY", 100.0)
        collector.record_classification_accuracy("NEW_EO", "NEW_EO", "NEW_EO", 0.95)
        
        snapshot = collector.get_comprehensive_health_snapshot()
        
        assert isinstance(snapshot, SystemHealthSnapshot)
        assert snapshot.overall_health in ["HEALTHY", "DEGRADED", "CRITICAL"]
        assert snapshot.classification_accuracy >= 0
        assert snapshot.security_incidents_count >= 0
        assert len(snapshot.connection_health) >= 0
    
    def test_json_export(self, collector):
        """Test JSON export functionality"""
        # Add some test data
        collector.start_processing_timer("export_test")
        time.sleep(0.01)
        collector.end_processing_timer("export_test", "NEW_EO", 0.95)
        
        # Export without raw data
        json_data = collector.export_metrics_to_json(include_raw_data=False)
        assert isinstance(json_data, str)
        assert "timestamp" in json_data
        assert "processing_latency" in json_data
        assert "raw_data" not in json_data
        
        # Export with raw data
        json_data_with_raw = collector.export_metrics_to_json(include_raw_data=True)
        assert "raw_data" in json_data_with_raw
    
    def test_metrics_summary(self, collector):
        """Test metrics summary generation"""
        # Add some test data
        collector.start_processing_timer("summary_test")
        time.sleep(0.01)
        collector.end_processing_timer("summary_test", "NEW_EO", 0.95)
        
        summary = collector.get_metrics_summary()
        
        assert "processing" in summary
        assert "throughput" in summary
        assert "accuracy" in summary
        assert "connections" in summary
        assert "security" in summary
        assert "uptime" in summary
        assert "health_snapshot" in summary
    
    def test_thread_safety(self, collector):
        """Test thread safety of metrics collection"""
        def worker(thread_id):
            for i in range(10):
                email_uid = f"thread_{thread_id}_email_{i}"
                collector.start_processing_timer(email_uid)
                time.sleep(0.001)
                collector.end_processing_timer(email_uid, "NEW_EO", 0.95)
                
                collector.record_classification_accuracy(
                    f"TYPE_{thread_id}", "PREDICTED", "ACTUAL", 0.90
                )
                
                collector.record_connection_health(
                    f"conn_{thread_id}", "IMAP", "HEALTHY", 100.0
                )
        
        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all metrics were recorded
        assert len(collector._processing_metrics) == 50  # 5 threads * 10 emails
        assert len(collector._classification_metrics) == 50
        assert len(collector._connection_status) == 5
    
    def test_empty_metrics_handling(self, collector):
        """Test handling of empty metrics collections"""
        # Test with no data
        latency_metrics = collector.get_processing_latency_metrics()
        assert latency_metrics["total_processed"] == 0
        assert latency_metrics["average_latency_ms"] == 0.0
        
        throughput_metrics = collector.get_throughput_metrics()
        assert throughput_metrics["total_emails"] == 0
        assert throughput_metrics["emails_per_hour"] == 0.0
        
        accuracy_metrics = collector.get_classification_accuracy_metrics()
        assert accuracy_metrics["total_classifications"] == 0
        assert accuracy_metrics["overall_accuracy"] == 0.0
        
        security_metrics = collector.get_security_incident_metrics()
        assert security_metrics["total_incidents"] == 0
        assert security_metrics["resolution_rate"] == 100.0
    
    def test_cleanup_old_metrics(self, collector):
        """Test automatic cleanup of old metrics"""
        # Set very short retention for testing
        collector.retention_hours = 0.001  # ~3.6 seconds
        
        # Add old metric
        old_time = datetime.now() - timedelta(hours=1)
        old_metric = ProcessingMetric(
            timestamp=old_time,
            email_uid="old_email",
            processing_start_time=time.time(),
            processing_end_time=time.time(),
            latency_ms=100.0,
            classification_type="NEW_EO",
            confidence_score=0.95,
            success=True
        )
        collector._processing_metrics.append(old_metric)
        
        # Add recent metric
        collector.start_processing_timer("recent_email")
        time.sleep(0.01)
        collector.end_processing_timer("recent_email", "NEW_EO", 0.95)
        
        assert len(collector._processing_metrics) == 2
        
        # Trigger cleanup manually (don't wait for background thread)
        cutoff_time = datetime.now() - timedelta(hours=collector.retention_hours)
        with collector._lock:
            # Clean processing metrics
            while (collector._processing_metrics and 
                   collector._processing_metrics[0].timestamp < cutoff_time):
                collector._processing_metrics.popleft()
        
        # Old metric should be removed, recent one should remain
        assert len(collector._processing_metrics) == 1
        assert collector._processing_metrics[0].email_uid == "recent_email"


class TestMetricsIntegration:
    """Integration tests for metrics collector with other components"""
    
    @pytest.fixture
    def collector(self):
        return MetricsCollector(retention_hours=24)
    
    def test_real_time_processing_metrics(self, collector):
        """Test real-time processing metrics collection"""
        # Simulate email processing pipeline
        emails = [
            ("email_1", "NEW_EO", 0.95, True),
            ("email_2", "PMO_RESPONSE", 0.88, True),
            ("email_3", "DEVELOPER_UPDATE", 0.65, False),  # Low confidence
            ("email_4", "EXECUTIVE_REQUEST", 0.92, True)
        ]
        
        for email_uid, classification, confidence, success in emails:
            collector.start_processing_timer(email_uid)
            time.sleep(0.005)  # Simulate processing time
            collector.end_processing_timer(
                email_uid, classification, confidence, success
            )
            
            # Record classification accuracy
            if success:
                collector.record_classification_accuracy(
                    classification, classification, classification, confidence
                )
        
        # Verify metrics
        latency_metrics = collector.get_processing_latency_metrics()
        assert latency_metrics["total_processed"] == 4
        assert latency_metrics["average_latency_ms"] > 0
        
        accuracy_metrics = collector.get_classification_accuracy_metrics()
        assert accuracy_metrics["total_classifications"] == 3  # Only successful ones
        assert accuracy_metrics["overall_accuracy"] == 100.0  # All correct
    
    def test_security_incident_workflow(self, collector):
        """Test complete security incident workflow"""
        # Simulate security threats
        threats = [
            (SecurityIncidentType.MALWARE_DETECTED, "CRITICAL", "Trojan detected"),
            (SecurityIncidentType.PHISHING_ATTEMPT, "HIGH", "Suspicious links"),
            (SecurityIncidentType.UNAUTHORIZED_SENDER, "MEDIUM", "Unknown domain")
        ]
        
        incident_ids = []
        for threat_type, severity, description in threats:
            incident_id = collector.record_security_incident(
                incident_type=threat_type,
                severity=severity,
                description=description,
                email_uid=f"threat_email_{len(incident_ids)}"
            )
            incident_ids.append(incident_id)
        
        # Check initial state
        security_metrics = collector.get_security_incident_metrics()
        assert security_metrics["total_incidents"] == 3
        assert security_metrics["unresolved_incidents"] == 3
        
        # Resolve incidents
        for incident_id in incident_ids[:2]:  # Resolve first 2
            collector.resolve_security_incident(incident_id)
        
        # Check final state
        final_metrics = collector.get_security_incident_metrics()
        assert final_metrics["resolved_incidents"] == 2
        assert final_metrics["unresolved_incidents"] == 1
        assert final_metrics["resolution_rate"] == 66.67  # 2/3 * 100
    
    def test_connection_health_monitoring(self, collector):
        """Test connection health monitoring over time"""
        connection_id = "production_imap"
        
        # Simulate connection health over time
        health_states = [
            ("HEALTHY", 100.0, 0),
            ("HEALTHY", 120.0, 0),
            ("DEGRADED", 300.0, 1),
            ("DEGRADED", 450.0, 2),
            ("HEALTHY", 110.0, 0)
        ]
        
        for status, response_time, errors in health_states:
            collector.record_connection_health(
                connection_id=connection_id,
                connection_type="IMAP",
                status=status,
                response_time_ms=response_time,
                error_count=errors
            )
            time.sleep(0.001)  # Small delay between measurements
        
        health_metrics = collector.get_connection_health_metrics()
        
        assert connection_id in health_metrics
        connection_health = health_metrics[connection_id]
        assert connection_health["status"] == "HEALTHY"  # Final state
        assert connection_health["average_response_time_ms"] > 0
        assert connection_health["connection_type"] == "IMAP"
    
    def test_performance_under_load(self, collector):
        """Test metrics collection performance under high load"""
        import concurrent.futures
        
        def simulate_high_load():
            # Simulate processing 100 emails rapidly
            for i in range(100):
                email_uid = f"load_test_email_{i}"
                collector.start_processing_timer(email_uid)
                time.sleep(0.001)  # Very fast processing
                collector.end_processing_timer(
                    email_uid, "NEW_EO", 0.95, True
                )
        
        # Run load test
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(simulate_high_load) for _ in range(5)]
            concurrent.futures.wait(futures)
        end_time = time.time()
        
        # Verify all metrics were collected
        assert len(collector._processing_metrics) == 500  # 5 threads * 100 emails
        
        # Verify performance
        processing_time = end_time - start_time
        assert processing_time < 10.0  # Should complete within 10 seconds
        
        # Check throughput calculation
        throughput_metrics = collector.get_throughput_metrics()
        assert throughput_metrics["total_emails"] == 500
        assert throughput_metrics["emails_per_hour"] > 1000  # High throughput


if __name__ == "__main__":
    pytest.main([__file__])