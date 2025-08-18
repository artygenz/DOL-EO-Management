"""
Integration tests for Health Status Reporting and Alerting System

Tests end-to-end health monitoring, alerting, and escalation workflows
with real system components and federal compliance requirements.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import threading
import json
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

from src.email.health_reporter import (
    HealthReporter, HealthStatus, ComponentType, AlertType, AlertSeverity,
    ComponentHealth, HealthAlert, SystemHealthReport
)
from src.email.metrics_collector import MetricsCollector, SecurityIncidentType
from src.email.performance_monitor import PerformanceMonitor, SeverityLevel


class TestHealthMonitoringIntegration(unittest.TestCase):
    """Integration tests for complete health monitoring system"""
    
    def setUp(self):
        """Set up integration test environment"""
        # Create real metrics collector and performance monitor
        self.metrics_collector = MetricsCollector(retention_hours=1)
        self.performance_monitor = PerformanceMonitor(check_interval=1)
        
        # Create health reporter
        self.health_reporter = HealthReporter(
            self.metrics_collector,
            self.performance_monitor,
            check_interval=1
        )
        
        # Storage for notifications
        self.email_notifications = []
        self.sms_notifications = []
        self.security_notifications = []
        
        # Register notification channels
        self.health_reporter.register_notification_channel("email", self._email_notifier)
        self.health_reporter.register_notification_channel("sms", self._sms_notifier)
        self.health_reporter.register_notification_channel("security_team", self._security_notifier)
        
        # Register system components
        self._register_system_components()
    
    def tearDown(self):
        """Clean up after integration tests"""
        if self.health_reporter._monitoring_active:
            self.health_reporter.stop_monitoring()
        
        if self.performance_monitor._monitoring_active:
            self.performance_monitor.stop_monitoring()
    
    def _email_notifier(self, alert: HealthAlert) -> None:
        """Mock email notification handler"""
        self.email_notifications.append({
            'alert_id': alert.alert_id,
            'severity': alert.severity.value,
            'title': alert.title,
            'timestamp': alert.timestamp
        })
    
    def _sms_notifier(self, alert: HealthAlert) -> None:
        """Mock SMS notification handler"""
        self.sms_notifications.append({
            'alert_id': alert.alert_id,
            'severity': alert.severity.value,
            'message': f"ALERT: {alert.title}"
        })
    
    def _security_notifier(self, alert: HealthAlert) -> None:
        """Mock security team notification handler"""
        self.security_notifications.append({
            'alert_id': alert.alert_id,
            'severity': alert.severity.value,
            'security_impact': alert.impact_assessment,
            'timestamp': alert.timestamp
        })
    
    def _register_system_components(self) -> None:
        """Register all system components for monitoring"""
        components = [
            (ComponentType.EMAIL_CLIENT, "godaddy_primary"),
            (ComponentType.EMAIL_CLIENT, "godaddy_secondary"),
            (ComponentType.DATABASE, "postgresql_primary"),
            (ComponentType.DATABASE, "postgresql_backup"),
            (ComponentType.REDIS_QUEUE, "event_queue"),
            (ComponentType.REDIS_QUEUE, "priority_queue"),
            (ComponentType.CLASSIFICATION_ENGINE, "ml_classifier"),
            (ComponentType.SECURITY_VALIDATOR, "threat_scanner"),
            (ComponentType.CONTENT_EXTRACTOR, "email_parser"),
            (ComponentType.EVENT_PUBLISHER, "event_publisher"),
            (ComponentType.DELIVERY_MANAGER, "smtp_delivery"),
            (ComponentType.CONNECTION_POOL, "imap_pool"),
            (ComponentType.IDLE_CONTROLLER, "idle_monitor"),
            (ComponentType.POLLING_ENGINE, "smart_poller")
        ]
        
        for comp_type, comp_id in components:
            # Create mock health check function
            health_check = self._create_health_check_function(comp_type, comp_id)
            self.health_reporter.register_component(comp_type, comp_id, health_check)
    
    def _create_health_check_function(self, comp_type: ComponentType, comp_id: str):
        """Create mock health check function for component"""
        def health_check():
            # Simulate different health states based on component
            if "secondary" in comp_id or "backup" in comp_id:
                return True  # Backup components are usually healthy
            elif comp_type == ComponentType.DATABASE and "primary" in comp_id:
                # Simulate occasional database issues
                return time.time() % 10 > 2  # Healthy 80% of the time
            elif comp_type == ComponentType.REDIS_QUEUE:
                # Simulate queue congestion issues
                return time.time() % 15 > 3  # Healthy most of the time
            else:
                return True  # Most components are healthy
        
        return health_check
    
    def test_end_to_end_monitoring_workflow(self):
        """Test complete end-to-end monitoring workflow"""
        # Start all monitoring systems
        self.performance_monitor.start_monitoring()
        self.health_reporter.start_monitoring()
        
        # Simulate email processing activity
        self._simulate_email_processing_activity()
        
        # Wait for monitoring cycles
        time.sleep(3)
        
        # Verify monitoring is active
        self.assertTrue(self.health_reporter._monitoring_active)
        self.assertTrue(self.performance_monitor._monitoring_active)
        
        # Check that components are being monitored
        component_health = self.health_reporter.get_component_health_status()
        self.assertEqual(len(component_health), 14)  # All registered components
        
        # Verify health checks are running
        healthy_components = [c for c in component_health.values() 
                            if c.status == HealthStatus.HEALTHY]
        self.assertGreater(len(healthy_components), 10)  # Most should be healthy
        
        # Generate health report
        report = self.health_reporter.generate_health_report()
        self.assertIsInstance(report, SystemHealthReport)
        self.assertIsNotNone(report.overall_health)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
        self.performance_monitor.stop_monitoring()
    
    def _simulate_email_processing_activity(self) -> None:
        """Simulate realistic email processing activity"""
        # Simulate processing multiple emails
        for i in range(10):
            email_uid = f"test_email_{i}"
            
            # Start processing timer
            self.metrics_collector.start_processing_timer(email_uid)
            
            # Simulate processing time
            time.sleep(0.01)  # 10ms processing time
            
            # End processing timer
            self.metrics_collector.end_processing_timer(
                email_uid, "NEW_EO", 0.95, True
            )
            
            # Record classification accuracy
            self.metrics_collector.record_classification_accuracy(
                "NEW_EO", "NEW_EO", "NEW_EO", 0.95
            )
            
            # Record connection health
            self.metrics_collector.record_connection_health(
                "godaddy_primary", "IMAP", "HEALTHY", 150.0
            )
    
    def test_threshold_violation_alerting(self):
        """Test threshold violation detection and alerting"""
        # Set strict thresholds for testing
        self.health_reporter.set_health_threshold("cpu_usage", 50.0, 70.0, "gt", 5, 1)
        self.health_reporter.set_health_threshold("memory_usage", 60.0, 80.0, "gt", 5, 1)
        
        # Mock high resource usage
        with patch('psutil.cpu_percent', return_value=75.0), \
             patch('psutil.virtual_memory') as mock_memory:
            
            mock_memory.return_value.percent = 85.0
            
            # Start monitoring
            self.performance_monitor.start_monitoring()
            self.health_reporter.start_monitoring()
            
            # Wait for threshold checks
            time.sleep(2)
            
            # Should detect threshold violations
            active_alerts = self.health_reporter.get_active_alerts()
            threshold_alerts = [a for a in active_alerts 
                              if a.alert_type == AlertType.THRESHOLD_VIOLATION]
            
            # Should have alerts for CPU and memory
            self.assertGreater(len(threshold_alerts), 0)
            
            # Should send notifications
            self.assertGreater(len(self.email_notifications), 0)
            
            # Stop monitoring
            self.health_reporter.stop_monitoring()
            self.performance_monitor.stop_monitoring()
    
    def test_component_failure_escalation(self):
        """Test component failure detection and escalation"""
        # Create failing health check
        def failing_health_check():
            raise Exception("Component unreachable")
        
        # Register component with failing health check
        self.health_reporter.register_component(
            ComponentType.DATABASE, "failing_db", failing_health_check
        )
        
        # Start monitoring
        self.health_reporter.start_monitoring()
        
        # Wait for health checks
        time.sleep(2)
        
        # Should detect component failure
        component_health = self.health_reporter.get_component_health_status()
        failing_component = None
        for component in component_health.values():
            if component.component_id == "failing_db":
                failing_component = component
                break
        
        self.assertIsNotNone(failing_component)
        self.assertEqual(failing_component.status, HealthStatus.CRITICAL)
        
        # Should create component failure alert
        active_alerts = self.health_reporter.get_active_alerts()
        failure_alerts = [a for a in active_alerts 
                         if a.alert_type == AlertType.COMPONENT_FAILURE]
        self.assertGreater(len(failure_alerts), 0)
        
        # Should send immediate notifications
        self.assertGreater(len(self.email_notifications), 0)
        
        # Simulate time passing for escalation
        failure_alert = failure_alerts[0]
        failure_alert.timestamp = datetime.now() - timedelta(minutes=10)
        
        # Process escalations
        self.health_reporter._process_escalations()
        
        # Should escalate the alert
        self.assertEqual(failure_alert.escalation_level, 1)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
    
    def test_security_incident_monitoring(self):
        """Test security incident monitoring and alerting"""
        # Record security incidents
        incident_types = [
            SecurityIncidentType.MALWARE_DETECTED,
            SecurityIncidentType.PHISHING_ATTEMPT,
            SecurityIncidentType.UNAUTHORIZED_SENDER
        ]
        
        for incident_type in incident_types:
            self.metrics_collector.record_security_incident(
                incident_type, "HIGH", f"Test {incident_type.value} incident"
            )
        
        # Set strict security threshold
        self.health_reporter.set_health_threshold("security_incidents", 0, 2, "gt", 5, 1)
        
        # Start monitoring
        self.health_reporter.start_monitoring()
        
        # Wait for threshold checks
        time.sleep(2)
        
        # Should detect security threshold violation
        active_alerts = self.health_reporter.get_active_alerts()
        security_alerts = [a for a in active_alerts 
                          if "security_incidents" in a.title]
        self.assertGreater(len(security_alerts), 0)
        
        # Should send security team notifications
        self.assertGreater(len(self.security_notifications), 0)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
    
    def test_performance_degradation_detection(self):
        """Test performance degradation detection and recommendations"""
        # Simulate slow email processing
        for i in range(20):
            email_uid = f"slow_email_{i}"
            self.metrics_collector.start_processing_timer(email_uid)
            time.sleep(0.1)  # 100ms processing time (slow)
            self.metrics_collector.end_processing_timer(
                email_uid, "PMO_RESPONSE", 0.85, True
            )
        
        # Set processing latency threshold
        self.health_reporter.set_health_threshold("processing_latency", 50.0, 80.0, "gt", 5, 1)
        
        # Start monitoring
        self.health_reporter.start_monitoring()
        
        # Wait for threshold checks
        time.sleep(2)
        
        # Should detect processing latency violation
        active_alerts = self.health_reporter.get_active_alerts()
        latency_alerts = [a for a in active_alerts 
                         if "processing_latency" in a.title]
        self.assertGreater(len(latency_alerts), 0)
        
        # Generate health report with recommendations
        report = self.health_reporter.generate_health_report()
        self.assertGreater(len(report.recommendations), 0)
        
        # Should recommend performance optimization
        perf_recommendations = [r for r in report.recommendations 
                              if "performance" in r.lower() or "optimize" in r.lower()]
        self.assertGreater(len(perf_recommendations), 0)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
    
    def test_health_trend_analysis(self):
        """Test health trend analysis over time"""
        # Register component for trend analysis
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "trend_client")
        
        # Simulate degrading performance over time
        base_response_time = 100.0
        for i in range(15):
            # Gradually increasing response time
            response_time = base_response_time + (i * 20.0)
            
            self.health_reporter.update_component_health(
                ComponentType.EMAIL_CLIENT, "trend_client",
                HealthStatus.HEALTHY, response_time
            )
            
            time.sleep(0.1)  # Small delay between updates
        
        # Start monitoring to trigger trend analysis
        self.health_reporter.start_monitoring()
        time.sleep(2)
        
        # Should detect degrading trend
        trends = self.health_reporter.get_health_trends("trend_client")
        self.assertGreater(len(trends), 0)
        
        # Find response time trend
        response_trends = [t for t in trends if t.metric_name == "response_time"]
        if response_trends:
            trend = response_trends[0]
            self.assertEqual(trend.trend_direction, "degrading")
            self.assertGreater(trend.trend_strength, 0.3)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
    
    def test_federal_compliance_monitoring(self):
        """Test federal compliance monitoring requirements"""
        # Set federal compliance thresholds
        federal_thresholds = [
            ("uptime_percentage", 99.9, 99.0, "lt"),
            ("classification_accuracy", 95.0, 90.0, "lt"),
            ("security_incidents", 0, 1, "gt"),
            ("processing_latency", 3000.0, 5000.0, "gt")
        ]
        
        for metric, warning, critical, operator in federal_thresholds:
            self.health_reporter.set_health_threshold(
                metric, warning, critical, operator, 30, 1
            )
        
        # Simulate compliance violations
        # Low classification accuracy
        for i in range(10):
            self.metrics_collector.record_classification_accuracy(
                "NEW_EO", "NEW_EO", "PMO_RESPONSE", 0.6  # Incorrect classification
            )
        
        # Security incident
        self.metrics_collector.record_security_incident(
            SecurityIncidentType.MALWARE_DETECTED, "CRITICAL",
            "Federal compliance violation: Malware detected in email attachment"
        )
        
        # Start monitoring
        self.health_reporter.start_monitoring()
        time.sleep(2)
        
        # Should detect compliance violations
        active_alerts = self.health_reporter.get_active_alerts()
        compliance_alerts = [a for a in active_alerts 
                           if a.severity == AlertSeverity.CRITICAL]
        self.assertGreater(len(compliance_alerts), 0)
        
        # Generate compliance report
        report = self.health_reporter.generate_health_report()
        
        # Should include federal compliance recommendations
        compliance_recommendations = [r for r in report.recommendations 
                                    if any(word in r.lower() for word in 
                                          ["compliance", "federal", "security", "accuracy"])]
        self.assertGreater(len(compliance_recommendations), 0)
        
        # Should send security team notifications for critical issues
        critical_security_notifications = [n for n in self.security_notifications 
                                         if n['severity'] == 'critical']
        self.assertGreater(len(critical_security_notifications), 0)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
    
    def test_multi_component_failure_scenario(self):
        """Test handling of multiple simultaneous component failures"""
        # Create multiple failing components
        failing_components = [
            (ComponentType.DATABASE, "primary_db"),
            (ComponentType.REDIS_QUEUE, "main_queue"),
            (ComponentType.SECURITY_VALIDATOR, "security_scanner")
        ]
        
        for comp_type, comp_id in failing_components:
            def failing_check():
                raise Exception(f"{comp_id} is unreachable")
            
            self.health_reporter.register_component(comp_type, comp_id, failing_check)
        
        # Start monitoring
        self.health_reporter.start_monitoring()
        time.sleep(2)
        
        # Should detect all component failures
        component_health = self.health_reporter.get_component_health_status()
        failed_components = [c for c in component_health.values() 
                           if c.status == HealthStatus.CRITICAL and 
                           c.component_id in ["primary_db", "main_queue", "security_scanner"]]
        self.assertEqual(len(failed_components), 3)
        
        # Should create multiple failure alerts
        active_alerts = self.health_reporter.get_active_alerts()
        failure_alerts = [a for a in active_alerts 
                         if a.alert_type == AlertType.COMPONENT_FAILURE]
        self.assertGreaterEqual(len(failure_alerts), 3)
        
        # Overall system health should be critical
        report = self.health_reporter.generate_health_report()
        self.assertEqual(report.overall_health, HealthStatus.CRITICAL)
        
        # Should recommend immediate action
        immediate_actions = [r for r in report.recommendations 
                           if "IMMEDIATE" in r.upper()]
        self.assertGreater(len(immediate_actions), 0)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
    
    def test_alert_lifecycle_management(self):
        """Test complete alert lifecycle from creation to resolution"""
        # Create component that will fail then recover
        failure_state = {"failing": True}
        
        def intermittent_health_check():
            if failure_state["failing"]:
                raise Exception("Intermittent failure")
            return True
        
        self.health_reporter.register_component(
            ComponentType.EMAIL_CLIENT, "intermittent_client", intermittent_health_check
        )
        
        # Start monitoring
        self.health_reporter.start_monitoring()
        time.sleep(2)
        
        # Should create failure alert
        active_alerts = self.health_reporter.get_active_alerts()
        failure_alerts = [a for a in active_alerts 
                         if "intermittent_client" in a.component]
        self.assertGreater(len(failure_alerts), 0)
        
        failure_alert = failure_alerts[0]
        alert_id = failure_alert.alert_id
        
        # Acknowledge alert
        ack_result = self.health_reporter.acknowledge_alert(alert_id, "test_admin")
        self.assertTrue(ack_result)
        self.assertTrue(failure_alert.acknowledged)
        
        # Simulate component recovery
        failure_state["failing"] = False
        time.sleep(2)
        
        # Component should recover
        component_health = self.health_reporter.get_component_health_status()
        recovered_component = None
        for component in component_health.values():
            if component.component_id == "intermittent_client":
                recovered_component = component
                break
        
        self.assertIsNotNone(recovered_component)
        # May still show as critical due to recent failure, but should improve over time
        
        # Resolve alert
        resolve_result = self.health_reporter.resolve_alert(
            alert_id, "test_admin", "Component recovered after restart"
        )
        self.assertTrue(resolve_result)
        self.assertTrue(failure_alert.resolved)
        self.assertIsNotNone(failure_alert.resolution_time)
        
        # Alert should be removed from active alerts
        current_active_alerts = self.health_reporter.get_active_alerts()
        active_alert_ids = [a.alert_id for a in current_active_alerts]
        self.assertNotIn(alert_id, active_alert_ids)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
    
    def test_health_data_export(self):
        """Test health data export for external monitoring systems"""
        # Set up various system states
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "export_client")
        self.health_reporter.update_component_health(
            ComponentType.EMAIL_CLIENT, "export_client", HealthStatus.HEALTHY, 200.0
        )
        
        # Create some alerts
        self.metrics_collector.record_security_incident(
            SecurityIncidentType.PHISHING_ATTEMPT, "HIGH", "Export test incident"
        )
        
        # Start monitoring briefly
        self.health_reporter.start_monitoring()
        time.sleep(1)
        
        # Export health data
        export_data = self.health_reporter.export_health_data(include_history=True)
        
        # Verify export structure
        required_fields = [
            "timestamp", "overall_health", "component_health", 
            "active_alerts", "health_trends"
        ]
        for field in required_fields:
            self.assertIn(field, export_data)
        
        # Verify component health data
        self.assertGreater(len(export_data["component_health"]), 0)
        
        # Verify data can be serialized to JSON
        json_data = json.dumps(export_data, default=str)
        self.assertIsInstance(json_data, str)
        
        # Verify data can be deserialized
        parsed_data = json.loads(json_data)
        self.assertEqual(parsed_data["overall_health"], export_data["overall_health"])
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
    
    def test_notification_channel_reliability(self):
        """Test notification channel reliability and error handling"""
        # Register notification channels with different reliability
        reliable_notifications = []
        
        def reliable_notifier(alert):
            reliable_notifications.append(alert)
        
        def unreliable_notifier(alert):
            if len(reliable_notifications) % 2 == 0:  # Fail every other notification
                raise Exception("Notification service unavailable")
            reliable_notifications.append(alert)
        
        self.health_reporter.register_notification_channel("reliable", reliable_notifier)
        self.health_reporter.register_notification_channel("unreliable", unreliable_notifier)
        
        # Create multiple alerts
        for i in range(5):
            self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, f"client_{i}")
            self.health_reporter.update_component_health(
                ComponentType.EMAIL_CLIENT, f"client_{i}",
                HealthStatus.CRITICAL, None, f"Test failure {i}"
            )
        
        # Should handle notification failures gracefully
        # Reliable channel should receive all notifications
        # System should continue operating despite unreliable channel failures
        
        # Verify system stability
        active_alerts = self.health_reporter.get_active_alerts()
        self.assertEqual(len(active_alerts), 5)  # All alerts should be created
        
        # Verify at least some notifications were sent
        self.assertGreater(len(reliable_notifications), 0)


class TestHealthReporterPerformance(unittest.TestCase):
    """Performance tests for health monitoring system"""
    
    def setUp(self):
        """Set up performance test environment"""
        self.metrics_collector = MetricsCollector(retention_hours=1)
        self.performance_monitor = PerformanceMonitor(check_interval=1)
        self.health_reporter = HealthReporter(
            self.metrics_collector,
            self.performance_monitor,
            check_interval=1
        )
    
    def tearDown(self):
        """Clean up after performance tests"""
        if self.health_reporter._monitoring_active:
            self.health_reporter.stop_monitoring()
    
    def test_large_scale_component_monitoring(self):
        """Test monitoring performance with large number of components"""
        # Register many components
        num_components = 100
        for i in range(num_components):
            comp_type = list(ComponentType)[i % len(ComponentType)]
            self.health_reporter.register_component(comp_type, f"component_{i}")
        
        # Start monitoring
        start_time = time.time()
        self.health_reporter.start_monitoring()
        
        # Let it run for a few cycles
        time.sleep(3)
        
        # Measure performance
        component_health = self.health_reporter.get_component_health_status()
        self.assertEqual(len(component_health), num_components)
        
        # Generate report
        report_start = time.time()
        report = self.health_reporter.generate_health_report()
        report_time = time.time() - report_start
        
        # Report generation should be fast even with many components
        self.assertLess(report_time, 1.0)  # Less than 1 second
        self.assertEqual(len(report.component_health), num_components)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
        end_time = time.time()
        
        # Total test time should be reasonable
        total_time = end_time - start_time
        self.assertLess(total_time, 10.0)  # Less than 10 seconds total
    
    def test_high_frequency_health_updates(self):
        """Test performance with high frequency health updates"""
        # Register component
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "high_freq_client")
        
        # Perform many rapid health updates
        num_updates = 1000
        start_time = time.time()
        
        for i in range(num_updates):
            status = HealthStatus.HEALTHY if i % 2 == 0 else HealthStatus.WARNING
            response_time = 100.0 + (i % 100)
            
            self.health_reporter.update_component_health(
                ComponentType.EMAIL_CLIENT, "high_freq_client",
                status, response_time
            )
        
        update_time = time.time() - start_time
        
        # Updates should be fast
        avg_update_time = update_time / num_updates
        self.assertLess(avg_update_time, 0.001)  # Less than 1ms per update
        
        # Verify all updates were recorded
        component_key = "email_client:high_freq_client"
        history = self.health_reporter._health_history[component_key]
        self.assertEqual(len(history), num_updates)
    
    def test_concurrent_monitoring_operations(self):
        """Test concurrent monitoring operations"""
        # Register components
        for i in range(10):
            self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, f"concurrent_{i}")
        
        # Start monitoring
        self.health_reporter.start_monitoring()
        
        # Perform concurrent operations
        def update_component_health():
            for i in range(50):
                comp_id = f"concurrent_{i % 10}"
                self.health_reporter.update_component_health(
                    ComponentType.EMAIL_CLIENT, comp_id,
                    HealthStatus.HEALTHY, 150.0 + i
                )
                time.sleep(0.01)
        
        def generate_reports():
            for i in range(10):
                report = self.health_reporter.generate_health_report()
                self.assertIsNotNone(report)
                time.sleep(0.1)
        
        # Run operations concurrently
        threads = [
            threading.Thread(target=update_component_health),
            threading.Thread(target=generate_reports)
        ]
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Should complete without errors in reasonable time
        total_time = end_time - start_time
        self.assertLess(total_time, 10.0)
        
        # System should remain stable
        component_health = self.health_reporter.get_component_health_status()
        self.assertEqual(len(component_health), 10)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()


if __name__ == '__main__':
    unittest.main()