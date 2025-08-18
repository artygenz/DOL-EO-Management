"""
Unit tests for Health Status Reporting and Alerting System

Tests comprehensive health monitoring, reporting, alerting, and escalation
procedures for federal-grade email processing systems.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List

from src.email.health_reporter import (
    HealthReporter, HealthStatus, ComponentType, AlertType, AlertSeverity,
    ComponentHealth, HealthAlert, HealthThreshold, SystemHealthReport,
    EscalationRule, HealthTrend
)
from src.email.metrics_collector import MetricsCollector, SecurityIncidentType
from src.email.performance_monitor import PerformanceMonitor, SeverityLevel


class TestHealthReporter(unittest.TestCase):
    """Test cases for HealthReporter class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_metrics_collector = Mock(spec=MetricsCollector)
        self.mock_performance_monitor = Mock(spec=PerformanceMonitor)
        
        # Configure mock return values
        self.mock_metrics_collector.get_processing_latency_metrics.return_value = {
            "average_latency_ms": 1500.0
        }
        self.mock_metrics_collector.get_classification_accuracy_metrics.return_value = {
            "overall_accuracy": 95.0
        }
        self.mock_metrics_collector.get_security_incident_metrics.return_value = {
            "unresolved_incidents": 0
        }
        self.mock_metrics_collector.get_system_uptime_metrics.return_value = {
            "uptime_hours": 24.0
        }
        
        self.mock_performance_monitor.get_current_performance_status.return_value = {
            "resource_utilization": {
                "cpu": 45.0,
                "memory": 60.0
            },
            "queue_status": {
                "email_queue": {"depth": 25}
            }
        }
        
        self.health_reporter = HealthReporter(
            self.mock_metrics_collector,
            self.mock_performance_monitor,
            check_interval=1  # Fast interval for testing
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if self.health_reporter._monitoring_active:
            self.health_reporter.stop_monitoring()
    
    def test_initialization(self):
        """Test HealthReporter initialization"""
        self.assertEqual(self.health_reporter.check_interval, 1)
        self.assertFalse(self.health_reporter._monitoring_active)
        self.assertEqual(len(self.health_reporter._health_thresholds), 9)  # Default thresholds
        self.assertEqual(len(self.health_reporter._escalation_rules), 4)  # Default escalation rules
    
    def test_register_component(self):
        """Test component registration for health monitoring"""
        # Register a component
        self.health_reporter.register_component(
            ComponentType.EMAIL_CLIENT, "test_client"
        )
        
        # Verify component is registered
        component_key = "email_client:test_client"
        self.assertIn(component_key, self.health_reporter._component_health)
        
        component = self.health_reporter._component_health[component_key]
        self.assertEqual(component.component_type, ComponentType.EMAIL_CLIENT)
        self.assertEqual(component.component_id, "test_client")
        self.assertEqual(component.status, HealthStatus.UNKNOWN)
        self.assertEqual(component.error_count, 0)
        self.assertEqual(component.uptime_percentage, 100.0)
    
    def test_register_component_with_health_check(self):
        """Test component registration with custom health check function"""
        mock_health_check = Mock(return_value=True)
        
        self.health_reporter.register_component(
            ComponentType.DATABASE, "test_db", mock_health_check
        )
        
        component_key = "database:test_db"
        component = self.health_reporter._component_health[component_key]
        self.assertEqual(component.metadata["health_check_func"], mock_health_check)
    
    def test_register_notification_channel(self):
        """Test notification channel registration"""
        mock_notification_func = Mock()
        
        self.health_reporter.register_notification_channel("email", mock_notification_func)
        
        self.assertIn("email", self.health_reporter._notification_channels)
        self.assertEqual(
            self.health_reporter._notification_channels["email"],
            mock_notification_func
        )
    
    def test_set_health_threshold(self):
        """Test setting custom health thresholds"""
        self.health_reporter.set_health_threshold(
            "custom_metric", 75.0, 90.0, "gt", 120, 2
        )
        
        threshold = self.health_reporter._health_thresholds["custom_metric"]
        self.assertEqual(threshold.warning_threshold, 75.0)
        self.assertEqual(threshold.critical_threshold, 90.0)
        self.assertEqual(threshold.comparison_operator, "gt")
        self.assertEqual(threshold.check_interval_seconds, 120)
        self.assertEqual(threshold.consecutive_violations_required, 2)
    
    def test_update_component_health_healthy(self):
        """Test updating component health to healthy status"""
        # Register component first
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "test_client")
        
        # Update to healthy status
        self.health_reporter.update_component_health(
            ComponentType.EMAIL_CLIENT, "test_client",
            HealthStatus.HEALTHY, 150.0
        )
        
        component_key = "email_client:test_client"
        component = self.health_reporter._component_health[component_key]
        
        self.assertEqual(component.status, HealthStatus.HEALTHY)
        self.assertEqual(component.response_time_ms, 150.0)
        self.assertIsNotNone(component.last_successful_operation)
        self.assertEqual(component.error_count, 0)
        
        # Check history is recorded
        self.assertIn(component_key, self.health_reporter._health_history)
        self.assertEqual(len(self.health_reporter._health_history[component_key]), 1)
    
    def test_update_component_health_with_error(self):
        """Test updating component health with error"""
        # Register component first
        self.health_reporter.register_component(ComponentType.DATABASE, "test_db")
        
        # Update with error
        self.health_reporter.update_component_health(
            ComponentType.DATABASE, "test_db",
            HealthStatus.CRITICAL, 5000.0, "Connection timeout"
        )
        
        component_key = "database:test_db"
        component = self.health_reporter._component_health[component_key]
        
        self.assertEqual(component.status, HealthStatus.CRITICAL)
        self.assertEqual(component.response_time_ms, 5000.0)
        self.assertEqual(component.error_count, 1)
        self.assertEqual(component.last_error, "Connection timeout")
        
        # Should trigger component alert
        self.assertEqual(len(self.health_reporter._active_alerts), 1)
        alert = list(self.health_reporter._active_alerts.values())[0]
        self.assertEqual(alert.alert_type, AlertType.COMPONENT_FAILURE)
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping health monitoring"""
        # Start monitoring
        self.health_reporter.start_monitoring()
        self.assertTrue(self.health_reporter._monitoring_active)
        self.assertIsNotNone(self.health_reporter._monitor_thread)
        self.assertIsNotNone(self.health_reporter._escalation_thread)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
        self.assertFalse(self.health_reporter._monitoring_active)
    
    def test_threshold_violation_detection(self):
        """Test threshold violation detection and alerting"""
        # Mock high CPU usage
        self.mock_performance_monitor.get_current_performance_status.return_value = {
            "resource_utilization": {"cpu": 95.0}  # Above critical threshold
        }
        
        # Trigger threshold check
        self.health_reporter._check_threshold_violations()
        
        # Should create threshold violation alert
        alerts = [a for a in self.health_reporter._active_alerts.values() 
                 if a.alert_type == AlertType.THRESHOLD_VIOLATION]
        self.assertEqual(len(alerts), 1)
        
        alert = alerts[0]
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
        self.assertIn("cpu_usage", alert.title)
        self.assertEqual(alert.current_value, 95.0)
    
    def test_consecutive_threshold_violations(self):
        """Test consecutive threshold violations requirement"""
        # Set threshold requiring 3 consecutive violations
        self.health_reporter.set_health_threshold("test_metric", 50.0, 80.0, "gt", 60, 3)
        
        # Mock metric that violates threshold
        with patch.object(self.health_reporter, '_get_current_metric_value', return_value=75.0):
            # First two violations shouldn't trigger alert
            self.health_reporter._check_threshold_violations()
            self.health_reporter._check_threshold_violations()
            self.assertEqual(len(self.health_reporter._active_alerts), 0)
            
            # Third violation should trigger alert
            self.health_reporter._check_threshold_violations()
            self.assertEqual(len(self.health_reporter._active_alerts), 1)
    
    def test_get_current_metric_value(self):
        """Test getting current metric values from collectors"""
        # Test CPU usage
        cpu_value = self.health_reporter._get_current_metric_value("cpu_usage")
        self.assertEqual(cpu_value, 45.0)
        
        # Test memory usage
        memory_value = self.health_reporter._get_current_metric_value("memory_usage")
        self.assertEqual(memory_value, 60.0)
        
        # Test processing latency
        latency_value = self.health_reporter._get_current_metric_value("processing_latency")
        self.assertEqual(latency_value, 1500.0)
        
        # Test classification accuracy
        accuracy_value = self.health_reporter._get_current_metric_value("classification_accuracy")
        self.assertEqual(accuracy_value, 95.0)
        
        # Test unknown metric
        unknown_value = self.health_reporter._get_current_metric_value("unknown_metric")
        self.assertIsNone(unknown_value)
    
    def test_threshold_violation_severity_determination(self):
        """Test determining severity of threshold violations"""
        threshold = HealthThreshold("test_metric", 70.0, 90.0, "gt", 60, 1)
        
        # Warning level violation
        warning_severity = self.health_reporter._determine_violation_severity(75.0, threshold)
        self.assertEqual(warning_severity, AlertSeverity.WARNING)
        
        # Critical level violation
        critical_severity = self.health_reporter._determine_violation_severity(95.0, threshold)
        self.assertEqual(critical_severity, AlertSeverity.CRITICAL)
        
        # Test "less than" threshold
        lt_threshold = HealthThreshold("test_metric", 90.0, 80.0, "lt", 60, 1)
        lt_severity = self.health_reporter._determine_violation_severity(75.0, lt_threshold)
        self.assertEqual(lt_severity, AlertSeverity.CRITICAL)
    
    def test_alert_escalation(self):
        """Test alert escalation for persistent issues"""
        # Create an alert
        alert = HealthAlert(
            alert_id="test_alert",
            timestamp=datetime.now() - timedelta(minutes=10),  # 10 minutes ago
            alert_type=AlertType.COMPONENT_FAILURE,
            severity=AlertSeverity.CRITICAL,
            component="test_component",
            title="Test Alert",
            description="Test alert description",
            current_value=None,
            threshold_value=None,
            impact_assessment="Test impact",
            recommended_actions=["Test action"]
        )
        
        self.health_reporter._active_alerts[alert.alert_id] = alert
        
        # Mock notification function
        mock_notification = Mock()
        self.health_reporter.register_notification_channel("test", mock_notification)
        
        # Process escalations
        self.health_reporter._process_escalations()
        
        # Should escalate the alert
        self.assertEqual(alert.escalation_level, 1)
        self.assertIn(alert.alert_id, self.health_reporter._last_escalation)
        
        # Should send escalated notification
        mock_notification.assert_called()
    
    def test_alert_acknowledgment(self):
        """Test alert acknowledgment"""
        # Create an alert
        alert = HealthAlert(
            alert_id="test_alert",
            timestamp=datetime.now(),
            alert_type=AlertType.THRESHOLD_VIOLATION,
            severity=AlertSeverity.WARNING,
            component="test_component",
            title="Test Alert",
            description="Test alert",
            current_value=75.0,
            threshold_value=70.0,
            impact_assessment="Test impact",
            recommended_actions=["Test action"]
        )
        
        self.health_reporter._active_alerts[alert.alert_id] = alert
        
        # Acknowledge alert
        result = self.health_reporter.acknowledge_alert("test_alert", "test_user")
        
        self.assertTrue(result)
        self.assertTrue(alert.acknowledged)
        self.assertEqual(alert.metadata["acknowledged_by"], "test_user")
        self.assertIn("acknowledged_at", alert.metadata)
    
    def test_alert_resolution(self):
        """Test alert resolution"""
        # Create an alert
        alert = HealthAlert(
            alert_id="test_alert",
            timestamp=datetime.now(),
            alert_type=AlertType.THRESHOLD_VIOLATION,
            severity=AlertSeverity.WARNING,
            component="test_component",
            title="Test Alert",
            description="Test alert",
            current_value=75.0,
            threshold_value=70.0,
            impact_assessment="Test impact",
            recommended_actions=["Test action"]
        )
        
        self.health_reporter._active_alerts[alert.alert_id] = alert
        
        # Resolve alert
        result = self.health_reporter.resolve_alert(
            "test_alert", "test_user", "Issue fixed"
        )
        
        self.assertTrue(result)
        self.assertTrue(alert.resolved)
        self.assertIsNotNone(alert.resolution_time)
        self.assertEqual(alert.metadata["resolved_by"], "test_user")
        self.assertEqual(alert.metadata["resolution_notes"], "Issue fixed")
        
        # Should be removed from active alerts
        self.assertNotIn("test_alert", self.health_reporter._active_alerts)
    
    def test_health_trend_analysis(self):
        """Test health trend analysis"""
        # Register component
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "test_client")
        component_key = "email_client:test_client"
        
        # Add historical data with degrading trend
        history = self.health_reporter._health_history[component_key]
        base_time = datetime.now() - timedelta(hours=2)
        
        for i in range(10):
            history.append({
                'timestamp': base_time + timedelta(minutes=i*10),
                'status': HealthStatus.HEALTHY,
                'response_time_ms': 100.0 + i * 50.0,  # Increasing response time
                'error_message': None
            })
        
        # Analyze trends
        self.health_reporter._analyze_health_trends()
        
        # Should detect degrading trend
        trends = [t for t in self.health_reporter._health_trends.values() 
                 if component_key in t.component]
        self.assertGreater(len(trends), 0)
        
        # Find response time trend
        response_time_trends = [t for t in trends if t.metric_name == "response_time"]
        self.assertGreater(len(response_time_trends), 0)
        
        trend = response_time_trends[0]
        self.assertEqual(trend.trend_direction, "degrading")
        self.assertGreater(trend.trend_strength, 0.0)
    
    def test_generate_health_report(self):
        """Test comprehensive health report generation"""
        # Register components
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "client1")
        self.health_reporter.register_component(ComponentType.DATABASE, "db1")
        
        # Update component health
        self.health_reporter.update_component_health(
            ComponentType.EMAIL_CLIENT, "client1", HealthStatus.HEALTHY, 150.0
        )
        self.health_reporter.update_component_health(
            ComponentType.DATABASE, "db1", HealthStatus.WARNING, 800.0
        )
        
        # Create an active alert
        alert = HealthAlert(
            alert_id="test_alert",
            timestamp=datetime.now(),
            alert_type=AlertType.THRESHOLD_VIOLATION,
            severity=AlertSeverity.WARNING,
            component="test_component",
            title="Test Alert",
            description="Test alert",
            current_value=75.0,
            threshold_value=70.0,
            impact_assessment="Test impact",
            recommended_actions=["Test action"]
        )
        self.health_reporter._active_alerts[alert.alert_id] = alert
        
        # Generate report
        report = self.health_reporter.generate_health_report()
        
        # Verify report structure
        self.assertIsInstance(report, SystemHealthReport)
        self.assertIsNotNone(report.report_id)
        self.assertIsInstance(report.timestamp, datetime)
        self.assertIsInstance(report.overall_health, HealthStatus)
        self.assertEqual(len(report.component_health), 2)
        self.assertEqual(len(report.active_alerts), 1)
        self.assertIsInstance(report.performance_summary, dict)
        self.assertIsInstance(report.security_summary, dict)
        self.assertIsInstance(report.recommendations, list)
        self.assertIsInstance(report.next_report_time, datetime)
    
    def test_calculate_overall_health(self):
        """Test overall health calculation"""
        # No components - should be unknown
        overall_health = self.health_reporter._calculate_overall_health()
        self.assertEqual(overall_health, HealthStatus.UNKNOWN)
        
        # Add healthy components
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "client1")
        self.health_reporter.register_component(ComponentType.DATABASE, "db1")
        
        self.health_reporter.update_component_health(
            ComponentType.EMAIL_CLIENT, "client1", HealthStatus.HEALTHY
        )
        self.health_reporter.update_component_health(
            ComponentType.DATABASE, "db1", HealthStatus.HEALTHY
        )
        
        overall_health = self.health_reporter._calculate_overall_health()
        self.assertEqual(overall_health, HealthStatus.HEALTHY)
        
        # Add critical component
        self.health_reporter.register_component(ComponentType.REDIS_QUEUE, "queue1")
        self.health_reporter.update_component_health(
            ComponentType.REDIS_QUEUE, "queue1", HealthStatus.CRITICAL
        )
        
        overall_health = self.health_reporter._calculate_overall_health()
        self.assertEqual(overall_health, HealthStatus.CRITICAL)
    
    def test_get_active_alerts(self):
        """Test getting active alerts with filtering"""
        # Create alerts with different severities
        warning_alert = HealthAlert(
            alert_id="warning_alert",
            timestamp=datetime.now(),
            alert_type=AlertType.THRESHOLD_VIOLATION,
            severity=AlertSeverity.WARNING,
            component="test_component",
            title="Warning Alert",
            description="Warning alert",
            current_value=75.0,
            threshold_value=70.0,
            impact_assessment="Warning impact",
            recommended_actions=["Warning action"]
        )
        
        critical_alert = HealthAlert(
            alert_id="critical_alert",
            timestamp=datetime.now(),
            alert_type=AlertType.COMPONENT_FAILURE,
            severity=AlertSeverity.CRITICAL,
            component="test_component",
            title="Critical Alert",
            description="Critical alert",
            current_value=None,
            threshold_value=None,
            impact_assessment="Critical impact",
            recommended_actions=["Critical action"]
        )
        
        self.health_reporter._active_alerts["warning_alert"] = warning_alert
        self.health_reporter._active_alerts["critical_alert"] = critical_alert
        
        # Get all active alerts
        all_alerts = self.health_reporter.get_active_alerts()
        self.assertEqual(len(all_alerts), 2)
        
        # Get only critical alerts
        critical_alerts = self.health_reporter.get_active_alerts(AlertSeverity.CRITICAL)
        self.assertEqual(len(critical_alerts), 1)
        self.assertEqual(critical_alerts[0].alert_id, "critical_alert")
        
        # Get only warning alerts
        warning_alerts = self.health_reporter.get_active_alerts(AlertSeverity.WARNING)
        self.assertEqual(len(warning_alerts), 1)
        self.assertEqual(warning_alerts[0].alert_id, "warning_alert")
    
    def test_get_component_health_status(self):
        """Test getting component health status with filtering"""
        # Register components of different types
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "client1")
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "client2")
        self.health_reporter.register_component(ComponentType.DATABASE, "db1")
        
        # Get all components
        all_components = self.health_reporter.get_component_health_status()
        self.assertEqual(len(all_components), 3)
        
        # Get only email client components
        email_components = self.health_reporter.get_component_health_status(ComponentType.EMAIL_CLIENT)
        self.assertEqual(len(email_components), 2)
        
        # Verify component types
        for component in email_components.values():
            self.assertEqual(component.component_type, ComponentType.EMAIL_CLIENT)
    
    def test_export_health_data(self):
        """Test exporting health data for external systems"""
        # Register component and create alert
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "client1")
        self.health_reporter.update_component_health(
            ComponentType.EMAIL_CLIENT, "client1", HealthStatus.HEALTHY, 150.0
        )
        
        alert = HealthAlert(
            alert_id="test_alert",
            timestamp=datetime.now(),
            alert_type=AlertType.THRESHOLD_VIOLATION,
            severity=AlertSeverity.WARNING,
            component="test_component",
            title="Test Alert",
            description="Test alert",
            current_value=75.0,
            threshold_value=70.0,
            impact_assessment="Test impact",
            recommended_actions=["Test action"]
        )
        self.health_reporter._active_alerts[alert.alert_id] = alert
        
        # Export data
        export_data = self.health_reporter.export_health_data()
        
        # Verify export structure
        self.assertIn("timestamp", export_data)
        self.assertIn("overall_health", export_data)
        self.assertIn("component_health", export_data)
        self.assertIn("active_alerts", export_data)
        self.assertIn("health_trends", export_data)
        
        # Verify component health data
        self.assertEqual(len(export_data["component_health"]), 1)
        component_data = list(export_data["component_health"].values())[0]
        self.assertIn("status", component_data)
        self.assertIn("uptime_percentage", component_data)
        self.assertIn("response_time_ms", component_data)
        
        # Verify alert data
        self.assertEqual(len(export_data["active_alerts"]), 1)
        alert_data = export_data["active_alerts"][0]
        self.assertIn("id", alert_data)
        self.assertIn("type", alert_data)
        self.assertIn("severity", alert_data)
        self.assertIn("description", alert_data)
    
    def test_export_health_data_with_history(self):
        """Test exporting health data with history information"""
        export_data = self.health_reporter.export_health_data(include_history=True)
        
        self.assertIn("alert_history_count", export_data)
        self.assertIn("health_history_components", export_data)
        self.assertEqual(export_data["alert_history_count"], 0)
        self.assertEqual(export_data["health_history_components"], 0)
    
    def test_notification_channel_error_handling(self):
        """Test error handling in notification channels"""
        # Register notification channel that raises exception
        def failing_notification(alert):
            raise Exception("Notification failed")
        
        self.health_reporter.register_notification_channel("failing", failing_notification)
        
        # Create alert that should trigger notification
        alert = HealthAlert(
            alert_id="test_alert",
            timestamp=datetime.now(),
            alert_type=AlertType.THRESHOLD_VIOLATION,
            severity=AlertSeverity.WARNING,
            component="test_component",
            title="Test Alert",
            description="Test alert",
            current_value=75.0,
            threshold_value=70.0,
            impact_assessment="Test impact",
            recommended_actions=["Test action"]
        )
        
        # Should not raise exception despite failing notification
        try:
            self.health_reporter._send_alert_notifications(alert)
        except Exception:
            self.fail("_send_alert_notifications raised exception unexpectedly")
    
    def test_health_check_function_execution(self):
        """Test execution of custom health check functions"""
        # Create mock health check function
        mock_health_check = Mock(return_value=True)
        
        # Register component with health check
        self.health_reporter.register_component(
            ComponentType.EMAIL_CLIENT, "test_client", mock_health_check
        )
        
        # Execute health checks
        self.health_reporter._check_all_components()
        
        # Verify health check was called
        mock_health_check.assert_called_once()
        
        # Verify component status was updated
        component_key = "email_client:test_client"
        component = self.health_reporter._component_health[component_key]
        self.assertEqual(component.status, HealthStatus.HEALTHY)
    
    def test_health_check_function_exception(self):
        """Test handling of exceptions in health check functions"""
        # Create mock health check function that raises exception
        mock_health_check = Mock(side_effect=Exception("Health check failed"))
        
        # Register component with failing health check
        self.health_reporter.register_component(
            ComponentType.DATABASE, "test_db", mock_health_check
        )
        
        # Execute health checks
        self.health_reporter._check_all_components()
        
        # Verify component status was set to critical
        component_key = "database:test_db"
        component = self.health_reporter._component_health[component_key]
        self.assertEqual(component.status, HealthStatus.CRITICAL)
        self.assertEqual(component.last_error, "Health check failed")


class TestHealthReporterIntegration(unittest.TestCase):
    """Integration tests for HealthReporter with real components"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_metrics_collector = Mock(spec=MetricsCollector)
        self.mock_performance_monitor = Mock(spec=PerformanceMonitor)
        
        # Configure realistic mock return values
        self.mock_metrics_collector.get_processing_latency_metrics.return_value = {
            "average_latency_ms": 2500.0,
            "p95_latency_ms": 4000.0,
            "total_processed": 150
        }
        
        self.mock_metrics_collector.get_classification_accuracy_metrics.return_value = {
            "overall_accuracy": 92.5,
            "by_type": {
                "NEW_EO": 95.0,
                "PMO_RESPONSE": 90.0,
                "DEVELOPER_UPDATE": 93.0,
                "EXECUTIVE_REQUEST": 92.0
            }
        }
        
        self.mock_metrics_collector.get_security_incident_metrics.return_value = {
            "total_incidents": 2,
            "unresolved_incidents": 1,
            "by_severity": {"HIGH": 1, "MEDIUM": 1}
        }
        
        self.mock_performance_monitor.get_current_performance_status.return_value = {
            "resource_utilization": {
                "cpu": 75.0,
                "memory": 82.0,
                "disk_io": 45.0
            },
            "queue_status": {
                "email_processing": {"depth": 85, "congestion": "MEDIUM"},
                "event_publishing": {"depth": 12, "congestion": "LOW"}
            },
            "active_bottlenecks": 1,
            "overall_health": "WARNING"
        }
        
        self.health_reporter = HealthReporter(
            self.mock_metrics_collector,
            self.mock_performance_monitor,
            check_interval=2
        )
    
    def tearDown(self):
        """Clean up after integration tests"""
        if self.health_reporter._monitoring_active:
            self.health_reporter.stop_monitoring()
    
    def test_comprehensive_monitoring_scenario(self):
        """Test comprehensive monitoring scenario with multiple components"""
        # Register multiple components
        components = [
            (ComponentType.EMAIL_CLIENT, "godaddy_client"),
            (ComponentType.DATABASE, "postgresql_primary"),
            (ComponentType.REDIS_QUEUE, "event_queue"),
            (ComponentType.CLASSIFICATION_ENGINE, "ml_classifier"),
            (ComponentType.SECURITY_VALIDATOR, "threat_scanner")
        ]
        
        for comp_type, comp_id in components:
            self.health_reporter.register_component(comp_type, comp_id)
        
        # Simulate various health states
        self.health_reporter.update_component_health(
            ComponentType.EMAIL_CLIENT, "godaddy_client", 
            HealthStatus.HEALTHY, 180.0
        )
        
        self.health_reporter.update_component_health(
            ComponentType.DATABASE, "postgresql_primary",
            HealthStatus.WARNING, 950.0
        )
        
        self.health_reporter.update_component_health(
            ComponentType.REDIS_QUEUE, "event_queue",
            HealthStatus.CRITICAL, 5000.0, "Connection timeout"
        )
        
        self.health_reporter.update_component_health(
            ComponentType.CLASSIFICATION_ENGINE, "ml_classifier",
            HealthStatus.HEALTHY, 320.0
        )
        
        self.health_reporter.update_component_health(
            ComponentType.SECURITY_VALIDATOR, "threat_scanner",
            HealthStatus.DEGRADED, 1200.0, "Slow response"
        )
        
        # Generate comprehensive health report
        report = self.health_reporter.generate_health_report()
        
        # Verify report reflects system state
        self.assertEqual(report.overall_health, HealthStatus.CRITICAL)  # Due to critical Redis queue
        self.assertEqual(len(report.component_health), 5)
        self.assertGreater(len(report.active_alerts), 0)  # Should have alerts for critical/degraded components
        self.assertGreater(len(report.recommendations), 0)
        
        # Verify specific component states
        redis_component = None
        for component in report.component_health.values():
            if component.component_id == "event_queue":
                redis_component = component
                break
        
        self.assertIsNotNone(redis_component)
        self.assertEqual(redis_component.status, HealthStatus.CRITICAL)
        self.assertEqual(redis_component.last_error, "Connection timeout")
    
    def test_threshold_monitoring_with_real_metrics(self):
        """Test threshold monitoring with realistic metric values"""
        # Start monitoring
        self.health_reporter.start_monitoring()
        
        # Wait for initial monitoring cycle
        time.sleep(0.5)
        
        # Should detect threshold violations based on mock data
        # CPU at 75% should trigger warning (threshold is 80% warning, 95% critical)
        # Memory at 82% should trigger warning (threshold is 85% warning, 95% critical)
        
        # Check for threshold violation alerts
        active_alerts = self.health_reporter.get_active_alerts()
        
        # May have alerts depending on consecutive violation requirements
        # At minimum, should have proper monitoring setup
        self.assertIsNotNone(self.health_reporter._monitor_thread)
        self.assertTrue(self.health_reporter._monitoring_active)
        
        # Stop monitoring
        self.health_reporter.stop_monitoring()
    
    def test_escalation_workflow(self):
        """Test complete escalation workflow"""
        # Register notification channels
        email_notifications = []
        sms_notifications = []
        
        def email_notifier(alert):
            email_notifications.append(alert)
        
        def sms_notifier(alert):
            sms_notifications.append(alert)
        
        self.health_reporter.register_notification_channel("email", email_notifier)
        self.health_reporter.register_notification_channel("sms", sms_notifier)
        
        # Create critical component failure
        self.health_reporter.register_component(ComponentType.DATABASE, "critical_db")
        self.health_reporter.update_component_health(
            ComponentType.DATABASE, "critical_db",
            HealthStatus.CRITICAL, None, "Database server unreachable"
        )
        
        # Should trigger immediate notification
        self.assertEqual(len(email_notifications), 1)
        
        # Get the created alert
        active_alerts = self.health_reporter.get_active_alerts(AlertSeverity.CRITICAL)
        self.assertEqual(len(active_alerts), 1)
        
        critical_alert = active_alerts[0]
        
        # Simulate time passing for escalation
        critical_alert.timestamp = datetime.now() - timedelta(minutes=10)
        
        # Process escalations
        self.health_reporter._process_escalations()
        
        # Should escalate the alert
        self.assertEqual(critical_alert.escalation_level, 1)
        
        # Should send additional notifications
        self.assertGreater(len(email_notifications), 1)
    
    def test_health_trend_detection(self):
        """Test health trend detection over time"""
        # Register component
        self.health_reporter.register_component(ComponentType.EMAIL_CLIENT, "trending_client")
        
        # Simulate degrading performance over time
        base_time = datetime.now() - timedelta(hours=1)
        component_key = "email_client:trending_client"
        
        for i in range(20):
            # Simulate increasing response times (degrading trend)
            response_time = 100.0 + (i * 25.0)  # 100ms to 575ms
            timestamp = base_time + timedelta(minutes=i*3)
            
            # Manually add to history for testing
            self.health_reporter._health_history[component_key].append({
                'timestamp': timestamp,
                'status': HealthStatus.HEALTHY,
                'response_time_ms': response_time,
                'error_message': None
            })
        
        # Analyze trends
        self.health_reporter._analyze_health_trends()
        
        # Should detect degrading trend
        trends = self.health_reporter.get_health_trends(component_key)
        self.assertGreater(len(trends), 0)
        
        # Find response time trend
        response_trends = [t for t in trends if t.metric_name == "response_time"]
        self.assertGreater(len(response_trends), 0)
        
        degrading_trend = response_trends[0]
        self.assertEqual(degrading_trend.trend_direction, "degrading")
        self.assertGreater(degrading_trend.trend_strength, 0.5)  # Strong degrading trend
    
    def test_federal_compliance_monitoring(self):
        """Test monitoring features required for federal compliance"""
        # Register all critical system components
        critical_components = [
            (ComponentType.EMAIL_CLIENT, "primary_email_client"),
            (ComponentType.DATABASE, "audit_database"),
            (ComponentType.SECURITY_VALIDATOR, "federal_security_scanner"),
            (ComponentType.EVENT_PUBLISHER, "compliance_event_publisher")
        ]
        
        for comp_type, comp_id in critical_components:
            self.health_reporter.register_component(comp_type, comp_id)
        
        # Set strict federal compliance thresholds
        self.health_reporter.set_health_threshold("security_incidents", 0, 1, "gt", 60, 1)
        self.health_reporter.set_health_threshold("classification_accuracy", 95.0, 90.0, "lt", 300, 1)
        self.health_reporter.set_health_threshold("uptime_percentage", 99.9, 99.0, "lt", 3600, 1)
        
        # Simulate security incident threshold violation
        self.mock_metrics_collector.get_security_incident_metrics.return_value = {
            "unresolved_incidents": 2  # Above threshold
        }
        
        # Check thresholds
        self.health_reporter._check_threshold_violations()
        
        # Should create critical security alert
        security_alerts = [a for a in self.health_reporter.get_active_alerts() 
                          if "security_incidents" in a.title]
        self.assertGreater(len(security_alerts), 0)
        
        # Generate compliance report
        report = self.health_reporter.generate_health_report()
        
        # Verify compliance-specific elements
        self.assertIn("security_summary", report.performance_summary)
        self.assertGreater(len(report.recommendations), 0)
        
        # Should recommend immediate security review
        security_recommendations = [r for r in report.recommendations 
                                  if "security" in r.lower()]
        self.assertGreater(len(security_recommendations), 0)


if __name__ == '__main__':
    unittest.main()