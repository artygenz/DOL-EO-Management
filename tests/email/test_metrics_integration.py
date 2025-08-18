"""
Integration tests for MetricsCollector with Email Agent components

Tests metrics collection integration with:
- Email processing pipeline
- Classification system
- Connection management
- Security validation
- Real-time reporting

Requirements: 7.1, 7.2
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.email.metrics_collector import MetricsCollector, SecurityIncidentType
from src.email.email_classifier import EmailClassifier
from src.email.content_extractor import EnhancedContentExtractor
from src.email.security_validator import EmailSecurityValidator
from src.email.connection_pool import ConnectionPoolManager
from src.config.models import EmailAccountConfig, IMAPSettings, SMTPSettings


class TestMetricsIntegrationWithEmailProcessing:
    """Test metrics integration with email processing components"""
    
    @pytest.fixture
    def metrics_collector(self):
        return MetricsCollector(retention_hours=1)
    
    @pytest.fixture
    def email_classifier(self):
        return EmailClassifier()
    
    @pytest.fixture
    def content_extractor(self):
        return EnhancedContentExtractor()
    
    @pytest.fixture
    def security_validator(self):
        config = {
            'government_domains': ['government.gov', 'agency.gov'],
            'antivirus_engine': '/usr/bin/clamav',
            'max_attachment_size': 10485760,  # 10MB
            'quarantine_directory': '/tmp/quarantine',
            'signature_verification_enabled': True
        }
        return EmailSecurityValidator(config)
    
    def test_email_processing_pipeline_metrics(self, metrics_collector, email_classifier, 
                                             content_extractor, security_validator):
        """Test metrics collection throughout email processing pipeline"""
        
        # Mock email data
        mock_email = Mock()
        mock_email.uid = "integration_test_email_001"
        mock_email.sender = "test@government.gov"
        mock_email.subject = "Executive Order Implementation"
        mock_email.body = "Please implement the new executive order requirements..."
        mock_email.attachments = []
        
        # Start processing metrics
        metrics_collector.start_processing_timer(mock_email.uid)
        
        # Simulate content extraction
        time.sleep(0.01)
        extracted_content = {
            'body_text': mock_email.body,
            'sender': mock_email.sender,
            'subject': mock_email.subject,
            'attachments': []
        }
        
        # Simulate security validation
        security_result = {
            'sender_authorized': True,
            'content_safe': True,
            'attachments_clean': True,
            'threats_detected': []
        }
        
        # Simulate classification
        with patch.object(email_classifier, 'classify_email') as mock_classify:
            mock_classify.return_value = {
                'email_type': 'NEW_EO',
                'confidence': 0.95,
                'features': {'sender_domain': 'government.gov'}
            }
            
            classification_result = email_classifier.classify_email(extracted_content)
        
        # End processing metrics
        metrics_collector.end_processing_timer(
            email_uid=mock_email.uid,
            classification_type=classification_result['email_type'],
            confidence_score=classification_result['confidence'],
            success=True
        )
        
        # Record classification accuracy
        metrics_collector.record_classification_accuracy(
            email_type=classification_result['email_type'],
            predicted=classification_result['email_type'],
            actual='NEW_EO',  # Simulate ground truth
            confidence=classification_result['confidence']
        )
        
        # Verify metrics were collected
        processing_metrics = metrics_collector.get_processing_latency_metrics()
        assert processing_metrics['total_processed'] == 1
        assert processing_metrics['average_latency_ms'] > 0
        
        accuracy_metrics = metrics_collector.get_classification_accuracy_metrics()
        assert accuracy_metrics['total_classifications'] == 1
        assert accuracy_metrics['overall_accuracy'] == 100.0
    
    def test_security_validation_metrics_integration(self, metrics_collector, security_validator):
        """Test metrics collection during security validation"""
        
        # Mock email with security threats
        mock_email = Mock()
        mock_email.uid = "security_test_email_001"
        mock_email.sender = "suspicious@malicious.com"
        mock_email.attachments = [Mock(filename="malware.exe", content=b"fake_malware")]
        
        # Start processing
        metrics_collector.start_processing_timer(mock_email.uid)
        
        # Simulate security validation with threats
        with patch.object(security_validator, 'validate_email_security') as mock_validate:
            mock_validate.return_value = {
                'sender_authorized': False,
                'content_safe': False,
                'attachments_clean': False,
                'threats_detected': ['malware', 'unauthorized_sender']
            }
            
            security_result = security_validator.validate_email_security(mock_email)
        
        # Record security incidents based on validation
        if not security_result['sender_authorized']:
            metrics_collector.record_security_incident(
                incident_type=SecurityIncidentType.UNAUTHORIZED_SENDER,
                severity="HIGH",
                description="Email from unauthorized domain",
                email_uid=mock_email.uid,
                sender=mock_email.sender
            )
        
        if not security_result['attachments_clean']:
            metrics_collector.record_security_incident(
                incident_type=SecurityIncidentType.MALWARE_DETECTED,
                severity="CRITICAL",
                description="Malware detected in attachment",
                email_uid=mock_email.uid,
                sender=mock_email.sender
            )
        
        # End processing with failure
        metrics_collector.end_processing_timer(
            email_uid=mock_email.uid,
            classification_type="UNKNOWN",
            confidence_score=0.0,
            success=False,
            error_type="SECURITY_VALIDATION_FAILED"
        )
        
        # Verify security metrics
        security_metrics = metrics_collector.get_security_incident_metrics()
        assert security_metrics['total_incidents'] == 2
        assert security_metrics['by_type']['unauthorized_sender'] == 1
        assert security_metrics['by_type']['malware_detected'] == 1
        assert security_metrics['by_severity']['HIGH'] == 1
        assert security_metrics['by_severity']['CRITICAL'] == 1
        
        # Verify processing metrics show failure
        processing_metrics = metrics_collector.get_processing_latency_metrics()
        assert processing_metrics['total_processed'] == 0  # Failed processing not counted
    
    def test_connection_pool_metrics_integration(self, metrics_collector):
        """Test metrics collection with connection pool management"""
        
        # Mock connection pool configuration
        config = EmailAccountConfig(
            account_id="test_account",
            account_type="EO_INTAKE",
            imap_settings=IMAPSettings(
                host="imap.test.com",
                port=993,
                use_ssl=True
            ),
            smtp_settings=SMTPSettings(
                host="smtp.test.com",
                port=587,
                use_tls=True
            )
        )
        
        # Create connection pool with metrics integration
        with patch('src.email.connection_pool.ConnectionPoolManager') as MockConnectionPool:
            mock_pool = Mock()
            MockConnectionPool.return_value = mock_pool
            
            # Simulate connection health monitoring
            connection_states = [
                ("HEALTHY", 100.0, 0),
                ("HEALTHY", 120.0, 0),
                ("DEGRADED", 300.0, 1),
                ("HEALTHY", 110.0, 0)
            ]
            
            for i, (status, response_time, errors) in enumerate(connection_states):
                connection_id = f"pool_connection_{i}"
                
                # Simulate connection operation
                start_time = time.time()
                time.sleep(response_time / 10000)  # Convert ms to seconds for simulation
                
                # Record connection health
                metrics_collector.record_connection_health(
                    connection_id=connection_id,
                    connection_type="IMAP",
                    status=status,
                    response_time_ms=response_time,
                    error_count=errors
                )
        
        # Verify connection health metrics
        health_metrics = metrics_collector.get_connection_health_metrics()
        assert len(health_metrics) == 4
        
        # Check that we have both healthy and degraded connections
        statuses = [health['status'] for health in health_metrics.values()]
        assert 'HEALTHY' in statuses
        assert 'DEGRADED' in statuses
    
    def test_concurrent_processing_metrics(self, metrics_collector):
        """Test metrics collection under concurrent email processing"""
        
        def process_email_batch(batch_id: int, num_emails: int):
            """Process a batch of emails concurrently"""
            for i in range(num_emails):
                email_uid = f"batch_{batch_id}_email_{i}"
                
                # Start processing
                metrics_collector.start_processing_timer(email_uid)
                
                # Simulate variable processing time
                processing_time = 0.01 + (i * 0.001)  # Increasing processing time
                time.sleep(processing_time)
                
                # Simulate classification
                email_types = ["NEW_EO", "PMO_RESPONSE", "DEVELOPER_UPDATE"]
                email_type = email_types[i % len(email_types)]
                confidence = 0.8 + (i * 0.02)  # Increasing confidence
                
                # End processing
                metrics_collector.end_processing_timer(
                    email_uid=email_uid,
                    classification_type=email_type,
                    confidence_score=min(confidence, 0.99),
                    success=True
                )
                
                # Record classification accuracy
                metrics_collector.record_classification_accuracy(
                    email_type=email_type,
                    predicted=email_type,
                    actual=email_type,  # Perfect accuracy for test
                    confidence=min(confidence, 0.99)
                )
        
        # Run concurrent processing
        num_batches = 3
        emails_per_batch = 10
        threads = []
        
        start_time = time.time()
        
        for batch_id in range(num_batches):
            thread = threading.Thread(
                target=process_email_batch,
                args=(batch_id, emails_per_batch)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_processing_time = end_time - start_time
        
        # Verify all emails were processed
        processing_metrics = metrics_collector.get_processing_latency_metrics()
        expected_total = num_batches * emails_per_batch
        assert processing_metrics['total_processed'] == expected_total
        
        # Verify throughput calculation
        throughput_metrics = metrics_collector.get_throughput_metrics()
        assert throughput_metrics['total_emails'] == expected_total
        assert throughput_metrics['emails_per_hour'] > 0
        
        # Verify classification accuracy
        accuracy_metrics = metrics_collector.get_classification_accuracy_metrics()
        assert accuracy_metrics['total_classifications'] == expected_total
        assert accuracy_metrics['overall_accuracy'] == 100.0  # Perfect accuracy in test
        
        # Verify performance (should process quickly)
        assert total_processing_time < 5.0  # Should complete within 5 seconds
    
    def test_real_time_dashboard_integration(self, metrics_collector):
        """Test real-time dashboard metrics integration"""
        
        # Simulate continuous email processing for dashboard
        def continuous_processing():
            for i in range(20):
                email_uid = f"dashboard_email_{i}"
                
                metrics_collector.start_processing_timer(email_uid)
                time.sleep(0.01)  # Fast processing
                
                metrics_collector.end_processing_timer(
                    email_uid=email_uid,
                    classification_type="NEW_EO",
                    confidence_score=0.95,
                    success=True
                )
                
                # Simulate connection health updates
                metrics_collector.record_connection_health(
                    connection_id="dashboard_connection",
                    connection_type="IMAP",
                    status="HEALTHY",
                    response_time_ms=100.0 + (i * 5),  # Gradually increasing response time
                    error_count=0
                )
                
                time.sleep(0.05)  # Small delay between emails
        
        # Start continuous processing
        processing_thread = threading.Thread(target=continuous_processing, daemon=True)
        processing_thread.start()
        
        # Simulate dashboard polling for metrics
        dashboard_updates = []
        for update_cycle in range(5):
            time.sleep(0.2)  # Dashboard update interval
            
            # Get current metrics snapshot
            snapshot = metrics_collector.get_comprehensive_health_snapshot()
            dashboard_updates.append({
                'cycle': update_cycle,
                'timestamp': snapshot.timestamp,
                'health': snapshot.overall_health,
                'processed_emails': len(metrics_collector._processing_metrics),
                'classification_accuracy': snapshot.classification_accuracy
            })
        
        processing_thread.join(timeout=2)
        
        # Verify dashboard received real-time updates
        assert len(dashboard_updates) == 5
        
        # Verify metrics increased over time
        first_update = dashboard_updates[0]
        last_update = dashboard_updates[-1]
        assert last_update['processed_emails'] > first_update['processed_emails']
        
        # Verify JSON export for dashboard
        json_export = metrics_collector.export_metrics_to_json(include_raw_data=True)
        assert 'timestamp' in json_export
        assert 'processing_latency' in json_export
        assert 'throughput' in json_export
        assert 'raw_data' in json_export
    
    def test_metrics_persistence_and_recovery(self, metrics_collector):
        """Test metrics persistence and recovery scenarios"""
        
        # Add initial metrics
        initial_emails = 10
        for i in range(initial_emails):
            email_uid = f"persistent_email_{i}"
            metrics_collector.start_processing_timer(email_uid)
            time.sleep(0.001)
            metrics_collector.end_processing_timer(
                email_uid=email_uid,
                classification_type="NEW_EO",
                confidence_score=0.90,
                success=True
            )
        
        # Record some security incidents
        incident_id = metrics_collector.record_security_incident(
            incident_type=SecurityIncidentType.PHISHING_ATTEMPT,
            severity="MEDIUM",
            description="Suspicious email detected"
        )
        
        # Get initial state
        initial_processing = metrics_collector.get_processing_latency_metrics()
        initial_security = metrics_collector.get_security_incident_metrics()
        
        # Simulate system restart by creating new collector with same retention
        new_collector = MetricsCollector(retention_hours=1)
        
        # Verify new collector starts fresh (as expected - metrics are in-memory)
        new_processing = new_collector.get_processing_latency_metrics()
        assert new_processing['total_processed'] == 0
        
        # Add new metrics to new collector
        for i in range(5):
            email_uid = f"recovery_email_{i}"
            new_collector.start_processing_timer(email_uid)
            time.sleep(0.001)
            new_collector.end_processing_timer(
                email_uid=email_uid,
                classification_type="PMO_RESPONSE",
                confidence_score=0.85,
                success=True
            )
        
        # Verify new collector has new metrics
        recovery_processing = new_collector.get_processing_latency_metrics()
        assert recovery_processing['total_processed'] == 5
        
        # Original collector should still have original metrics
        final_processing = metrics_collector.get_processing_latency_metrics()
        assert final_processing['total_processed'] == initial_emails
    
    def test_performance_monitoring_integration(self, metrics_collector):
        """Test performance monitoring and bottleneck detection"""
        
        # Simulate various performance scenarios
        performance_scenarios = [
            ("fast_processing", 0.01, "NEW_EO", 0.95),
            ("slow_processing", 0.1, "PMO_RESPONSE", 0.90),
            ("very_slow_processing", 0.2, "DEVELOPER_UPDATE", 0.85),
            ("timeout_processing", 0.3, "EXECUTIVE_REQUEST", 0.80)
        ]
        
        for scenario_name, processing_time, email_type, confidence in performance_scenarios:
            for i in range(5):  # 5 emails per scenario
                email_uid = f"{scenario_name}_{i}"
                
                metrics_collector.start_processing_timer(email_uid)
                time.sleep(processing_time)
                
                # Simulate occasional failures for slow processing
                success = processing_time < 0.15 or i < 3
                
                metrics_collector.end_processing_timer(
                    email_uid=email_uid,
                    classification_type=email_type,
                    confidence_score=confidence,
                    success=success,
                    error_type="TIMEOUT" if not success else None
                )
        
        # Analyze performance metrics
        latency_metrics = metrics_collector.get_processing_latency_metrics()
        
        # Verify we captured different performance characteristics
        assert latency_metrics['total_processed'] > 0
        assert latency_metrics['max_latency_ms'] > latency_metrics['min_latency_ms']
        assert latency_metrics['p95_latency_ms'] > latency_metrics['median_latency_ms']
        
        # Check for performance bottlenecks (high latency)
        if latency_metrics['p95_latency_ms'] > 150:  # 150ms threshold
            print(f"Performance bottleneck detected: P95 latency = {latency_metrics['p95_latency_ms']:.2f}ms")
        
        # Verify throughput calculation accounts for failures
        throughput_metrics = metrics_collector.get_throughput_metrics()
        assert throughput_metrics['total_emails'] == latency_metrics['total_processed']


class TestMetricsRealtimeReporting:
    """Test real-time metrics reporting capabilities"""
    
    @pytest.fixture
    def metrics_collector(self):
        return MetricsCollector(retention_hours=1)
    
    def test_realtime_metrics_streaming(self, metrics_collector):
        """Test real-time metrics streaming for monitoring dashboards"""
        
        # Simulate real-time email processing
        def email_processor():
            for i in range(30):
                email_uid = f"stream_email_{i}"
                metrics_collector.start_processing_timer(email_uid)
                time.sleep(0.01)
                metrics_collector.end_processing_timer(
                    email_uid=email_uid,
                    classification_type="NEW_EO",
                    confidence_score=0.90 + (i * 0.001),
                    success=True
                )
                time.sleep(0.02)  # 50 emails per second rate
        
        # Start processing in background
        processor_thread = threading.Thread(target=email_processor, daemon=True)
        processor_thread.start()
        
        # Collect real-time metrics snapshots
        snapshots = []
        for i in range(10):
            time.sleep(0.1)  # 10Hz monitoring rate
            
            snapshot = {
                'timestamp': datetime.now(),
                'processing': metrics_collector.get_processing_latency_metrics(hours=0.01),
                'throughput': metrics_collector.get_throughput_metrics(hours=0.01),
                'health': metrics_collector.get_comprehensive_health_snapshot()
            }
            snapshots.append(snapshot)
        
        processor_thread.join(timeout=2)
        
        # Verify real-time data collection
        assert len(snapshots) == 10
        
        # Verify metrics increased over time
        first_snapshot = snapshots[0]
        last_snapshot = snapshots[-1]
        
        assert (last_snapshot['processing']['total_processed'] >= 
                first_snapshot['processing']['total_processed'])
        
        # Verify timestamps are sequential
        for i in range(1, len(snapshots)):
            assert snapshots[i]['timestamp'] > snapshots[i-1]['timestamp']
    
    def test_metrics_alerting_thresholds(self, metrics_collector):
        """Test metrics-based alerting and threshold monitoring"""
        
        # Define alerting thresholds
        thresholds = {
            'max_latency_ms': 200.0,
            'min_accuracy_percent': 90.0,
            'max_error_rate_percent': 5.0,
            'max_security_incidents': 3
        }
        
        alerts_triggered = []
        
        def check_thresholds():
            """Check metrics against thresholds and trigger alerts"""
            latency = metrics_collector.get_processing_latency_metrics()
            accuracy = metrics_collector.get_classification_accuracy_metrics()
            security = metrics_collector.get_security_incident_metrics()
            
            # Check latency threshold
            if latency['max_latency_ms'] > thresholds['max_latency_ms']:
                alerts_triggered.append({
                    'type': 'HIGH_LATENCY',
                    'value': latency['max_latency_ms'],
                    'threshold': thresholds['max_latency_ms']
                })
            
            # Check accuracy threshold
            if accuracy['overall_accuracy'] < thresholds['min_accuracy_percent']:
                alerts_triggered.append({
                    'type': 'LOW_ACCURACY',
                    'value': accuracy['overall_accuracy'],
                    'threshold': thresholds['min_accuracy_percent']
                })
            
            # Check security incidents threshold
            if security['unresolved_incidents'] > thresholds['max_security_incidents']:
                alerts_triggered.append({
                    'type': 'HIGH_SECURITY_INCIDENTS',
                    'value': security['unresolved_incidents'],
                    'threshold': thresholds['max_security_incidents']
                })
        
        # Simulate normal operations (should not trigger alerts)
        for i in range(5):
            email_uid = f"normal_email_{i}"
            metrics_collector.start_processing_timer(email_uid)
            time.sleep(0.05)  # Normal processing time
            metrics_collector.end_processing_timer(
                email_uid=email_uid,
                classification_type="NEW_EO",
                confidence_score=0.95,
                success=True
            )
            metrics_collector.record_classification_accuracy(
                "NEW_EO", "NEW_EO", "NEW_EO", 0.95
            )
        
        check_thresholds()
        assert len(alerts_triggered) == 0  # No alerts for normal operations
        
        # Simulate high latency scenario
        email_uid = "slow_email"
        metrics_collector.start_processing_timer(email_uid)
        time.sleep(0.25)  # Slow processing time
        metrics_collector.end_processing_timer(
            email_uid=email_uid,
            classification_type="NEW_EO",
            confidence_score=0.95,
            success=True
        )
        
        check_thresholds()
        high_latency_alerts = [a for a in alerts_triggered if a['type'] == 'HIGH_LATENCY']
        assert len(high_latency_alerts) > 0
        
        # Simulate low accuracy scenario
        for i in range(10):
            metrics_collector.record_classification_accuracy(
                "PMO_RESPONSE", "PMO_RESPONSE", "NEW_EO", 0.70  # Incorrect classification
            )
        
        check_thresholds()
        low_accuracy_alerts = [a for a in alerts_triggered if a['type'] == 'LOW_ACCURACY']
        assert len(low_accuracy_alerts) > 0
        
        # Simulate high security incidents
        for i in range(5):
            metrics_collector.record_security_incident(
                SecurityIncidentType.PHISHING_ATTEMPT,
                "HIGH",
                f"Security incident {i}"
            )
        
        check_thresholds()
        security_alerts = [a for a in alerts_triggered if a['type'] == 'HIGH_SECURITY_INCIDENTS']
        assert len(security_alerts) > 0


if __name__ == "__main__":
    pytest.main([__file__])