# tests/email/test_reconnection_manager.py
import pytest
import time
import threading
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.email.reconnection_manager import (
    IntelligentReconnectionManager,
    ConnectionState,
    FailureType,
    ConnectionFailure,
    ReconnectionConfig,
    FallbackMechanism,
    ConnectionMetrics
)
from src.email.godaddy_client import ConnectionHealth, ConnectionHealthStatus


class TestIntelligentReconnectionManager:
    """Test suite for IntelligentReconnectionManager"""
    
    @pytest.fixture
    def account_config(self):
        """Sample account configuration"""
        return {
            'imap_host': 'imap.test.com',
            'imap_port': 993,
            'smtp_host': 'smtp.test.com',
            'smtp_port': 465,
            'username': 'test@test.com',
            'password': 'testpass'
        }
    
    @pytest.fixture
    def reconnection_config(self):
        """Sample reconnection configuration"""
        return ReconnectionConfig(
            initial_backoff=0.1,  # Fast for testing
            max_backoff=1.0,
            backoff_multiplier=2.0,
            jitter_factor=0.1,
            max_retry_attempts=3,
            persistent_failure_threshold=2,
            health_check_interval=0.5,
            state_persistence_path=tempfile.mktemp(suffix='.json')
        )
    
    @pytest.fixture
    def fallback_config(self):
        """Sample fallback configuration"""
        return FallbackMechanism(
            enabled=True,
            fallback_servers=[
                {'imap_host': 'backup1.test.com', 'smtp_host': 'backup1.test.com'},
                {'imap_host': 'backup2.test.com', 'smtp_host': 'backup2.test.com'}
            ],
            fallback_timeout=1.0,
            max_fallback_attempts=2
        )
    
    @pytest.fixture
    def manager(self, account_config, reconnection_config, fallback_config):
        """Create reconnection manager instance"""
        manager = IntelligentReconnectionManager(
            account_config=account_config,
            reconnection_config=reconnection_config,
            fallback_config=fallback_config
        )
        yield manager
        manager.shutdown()
        
        # Cleanup state file
        if os.path.exists(reconnection_config.state_persistence_path):
            os.unlink(reconnection_config.state_persistence_path)

    def test_initial_state(self, manager):
        """Test initial state of reconnection manager"""
        assert manager.get_connection_state() == ConnectionState.DISCONNECTED
        assert manager.get_connection() is None
        assert manager._consecutive_failures == 0
        assert manager.get_current_failure() is None

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_successful_connection(self, mock_client_class, manager):
        """Test successful connection establishment"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.connect.return_value = None
        mock_client.get_connection_health.return_value = ConnectionHealthStatus(
            status=ConnectionHealth.HEALTHY,
            last_check=datetime.now(),
            response_time_ms=100.0,
            error_count=0,
            last_error=None,
            uptime_percentage=100.0
        )
        
        # Test connection
        success = manager.connect()
        
        assert success is True
        assert manager.get_connection_state() == ConnectionState.CONNECTED
        assert manager.get_connection() is not None
        assert manager._consecutive_failures == 0
        
        # Verify metrics
        metrics = manager.get_connection_metrics()
        assert metrics.successful_connections == 1
        assert metrics.total_connections == 1
        assert metrics.failed_connections == 0

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_connection_failure_with_retry(self, mock_client_class, manager):
        """Test connection failure with automatic retry"""
        # Setup mock to fail first time, succeed second time
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        call_count = 0
        def connect_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network error")
            return None
        
        mock_client.connect.side_effect = connect_side_effect
        mock_client.get_connection_health.return_value = ConnectionHealthStatus(
            status=ConnectionHealth.HEALTHY,
            last_check=datetime.now(),
            response_time_ms=100.0,
            error_count=0,
            last_error=None,
            uptime_percentage=100.0
        )
        
        # Test initial connection failure
        success = manager.connect()
        assert success is False
        assert manager.get_connection_state() == ConnectionState.FAILED
        assert manager._consecutive_failures == 1
        
        # Wait for automatic retry
        time.sleep(0.5)  # Wait for backoff and retry
        
        # Should eventually succeed
        retry_count = 0
        while manager.get_connection_state() != ConnectionState.CONNECTED and retry_count < 10:
            time.sleep(0.1)
            retry_count += 1
        
        assert manager.get_connection_state() == ConnectionState.CONNECTED
        assert manager._consecutive_failures == 0

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_exponential_backoff_calculation(self, mock_client_class, manager):
        """Test exponential backoff calculation"""
        # Setup mock to always fail
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.connect.side_effect = Exception("Connection failed")
        
        # Track backoff durations
        backoff_durations = []
        
        # Override _schedule_reconnection to capture backoff durations
        original_schedule = manager._schedule_reconnection
        def capture_backoff(delay):
            backoff_durations.append(delay)
            # Don't actually schedule to avoid waiting
        
        manager._schedule_reconnection = capture_backoff
        
        # Attempt multiple connections to trigger backoff
        for i in range(3):
            manager.connect()
            time.sleep(0.01)  # Small delay between attempts
        
        # Verify exponential backoff
        assert len(backoff_durations) >= 2
        assert backoff_durations[1] > backoff_durations[0]  # Should increase
        
        # Restore original method
        manager._schedule_reconnection = original_schedule

    def test_failure_classification(self, manager):
        """Test failure type classification"""
        # Test different error types
        test_cases = [
            ("Connection timeout", FailureType.TIMEOUT_ERROR),
            ("Authentication failed", FailureType.AUTHENTICATION_ERROR),
            ("Rate limit exceeded", FailureType.RATE_LIMIT_ERROR),
            ("Network unreachable", FailureType.NETWORK_ERROR),
            ("Server error 500", FailureType.SERVER_ERROR),
            ("Unknown error", FailureType.UNKNOWN_ERROR)
        ]
        
        for error_msg, expected_type in test_cases:
            error = Exception(error_msg)
            failure_type = manager._classify_failure(error)
            assert failure_type == expected_type

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_max_retry_attempts(self, mock_client_class, manager):
        """Test maximum retry attempts before suspension"""
        # Setup mock to always fail
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.connect.side_effect = Exception("Persistent failure")
        
        # Attempt connection multiple times
        for i in range(manager.config.max_retry_attempts + 1):
            manager.connect()
            time.sleep(0.01)
        
        # Wait for all retry attempts
        time.sleep(1.0)
        
        # Should be suspended after max attempts
        assert manager._consecutive_failures >= manager.config.max_retry_attempts

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_fallback_mechanism(self, mock_client_class, manager):
        """Test fallback server mechanism"""
        # Setup mock to fail for primary, succeed for fallback
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        call_count = 0
        def connect_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count <= manager.config.max_retry_attempts:
                raise Exception("Primary server failed")
            return None  # Fallback succeeds
        
        mock_client.connect.side_effect = connect_side_effect
        mock_client.get_connection_health.return_value = ConnectionHealthStatus(
            status=ConnectionHealth.HEALTHY,
            last_check=datetime.now(),
            response_time_ms=100.0,
            error_count=0,
            last_error=None,
            uptime_percentage=100.0
        )
        
        # Trigger fallback by exhausting retries
        for i in range(manager.config.max_retry_attempts + 1):
            manager.connect()
            time.sleep(0.01)
        
        # Wait for fallback attempt
        time.sleep(2.0)
        
        # Should eventually connect via fallback
        retry_count = 0
        while manager.get_connection_state() != ConnectionState.CONNECTED and retry_count < 20:
            time.sleep(0.1)
            retry_count += 1
        
        # Verify fallback was attempted (config should be updated)
        assert call_count > manager.config.max_retry_attempts

    def test_connection_state_persistence(self, manager, reconnection_config):
        """Test connection state persistence and recovery"""
        # Create some failure history
        failure = ConnectionFailure(
            failure_type=FailureType.NETWORK_ERROR,
            timestamp=datetime.now(),
            error_message="Test failure",
            retry_count=1
        )
        
        manager._failure_history.append(failure)
        manager._consecutive_failures = 2
        manager._current_failure = failure
        
        # Persist state
        manager._persist_connection_state()
        
        # Create new manager instance to test loading
        new_manager = IntelligentReconnectionManager(
            account_config=manager.account_config,
            reconnection_config=reconnection_config
        )
        
        try:
            # Verify state was loaded
            assert new_manager._consecutive_failures == 2
            assert len(new_manager._failure_history) == 1
            assert new_manager._current_failure is not None
            assert new_manager._current_failure.failure_type == FailureType.NETWORK_ERROR
            
        finally:
            new_manager.shutdown()

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_health_check_monitoring(self, mock_client_class, manager):
        """Test connection health monitoring"""
        # Setup mock with healthy connection initially
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.connect.return_value = None
        
        # Start with healthy connection
        mock_client.get_connection_health.return_value = ConnectionHealthStatus(
            status=ConnectionHealth.HEALTHY,
            last_check=datetime.now(),
            response_time_ms=100.0,
            error_count=0,
            last_error=None,
            uptime_percentage=100.0
        )
        
        # Establish connection
        success = manager.connect()
        assert success is True
        assert manager.get_connection_state() == ConnectionState.CONNECTED
        
        # Change health to unhealthy
        mock_client.get_connection_health.return_value = ConnectionHealthStatus(
            status=ConnectionHealth.UNHEALTHY,
            last_check=datetime.now(),
            response_time_ms=5000.0,
            error_count=5,
            last_error="Health check failed",
            uptime_percentage=50.0
        )
        
        # Wait for health check to detect issue
        time.sleep(1.0)
        
        # Should trigger reconnection
        assert manager.get_connection_state() in [ConnectionState.FAILED, ConnectionState.RECONNECTING]

    def test_connection_callbacks(self, manager):
        """Test connection state change callbacks"""
        callback_calls = []
        
        def connection_callback(state, error):
            callback_calls.append((state, error))
        
        def failure_callback(failure):
            callback_calls.append(('failure', failure))
        
        manager.add_connection_callback(connection_callback)
        manager.add_failure_callback(failure_callback)
        
        # Trigger state changes
        with patch('src.email.reconnection_manager.GoDaddyEmailClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.connect.side_effect = Exception("Test failure")
            
            manager.connect()
        
        # Verify callbacks were called
        assert len(callback_calls) > 0
        
        # Should have failure callback
        failure_calls = [call for call in callback_calls if call[0] == 'failure']
        assert len(failure_calls) > 0

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_force_reconnect(self, mock_client_class, manager):
        """Test force reconnect functionality"""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.connect.return_value = None
        mock_client.get_connection_health.return_value = ConnectionHealthStatus(
            status=ConnectionHealth.HEALTHY,
            last_check=datetime.now(),
            response_time_ms=100.0,
            error_count=0,
            last_error=None,
            uptime_percentage=100.0
        )
        
        # Establish initial connection
        success = manager.connect()
        assert success is True
        
        # Add some failure history
        manager._consecutive_failures = 3
        
        # Force reconnect
        success = manager.force_reconnect()
        assert success is True
        
        # Should reset failure counters
        assert manager._consecutive_failures == 0
        assert manager.get_connection_state() == ConnectionState.CONNECTED

    def test_metrics_tracking(self, manager):
        """Test connection metrics tracking"""
        initial_metrics = manager.get_connection_metrics()
        assert initial_metrics.total_connections == 0
        assert initial_metrics.successful_connections == 0
        assert initial_metrics.failed_connections == 0
        
        with patch('src.email.reconnection_manager.GoDaddyEmailClient') as mock_client_class:
            # Test successful connection
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_connection_health.return_value = ConnectionHealthStatus(
                status=ConnectionHealth.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=100.0,
                error_count=0,
                last_error=None,
                uptime_percentage=100.0
            )
            
            manager.connect()
            
            metrics = manager.get_connection_metrics()
            assert metrics.total_connections == 1
            assert metrics.successful_connections == 1
            assert metrics.failed_connections == 0
            assert metrics.last_successful_connection is not None
            
            # Test failed connection
            mock_client.connect.side_effect = Exception("Connection failed")
            manager.force_reconnect()
            
            metrics = manager.get_connection_metrics()
            assert metrics.failed_connections > 0
            assert metrics.last_failure is not None

    def test_jitter_in_backoff(self, manager):
        """Test that jitter is applied to backoff calculations"""
        backoff_values = []
        
        # Calculate multiple backoff values for the same failure count
        manager._consecutive_failures = 2
        for _ in range(10):
            backoff = manager._calculate_backoff_duration()
            backoff_values.append(backoff)
        
        # Should have some variation due to jitter
        unique_values = set(backoff_values)
        assert len(unique_values) > 1, "Jitter should create variation in backoff values"

    def test_connection_age_tracking(self, manager):
        """Test connection age and freshness tracking"""
        with patch('src.email.reconnection_manager.GoDaddyEmailClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_connection_health.return_value = ConnectionHealthStatus(
                status=ConnectionHealth.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=100.0,
                error_count=0,
                last_error=None,
                uptime_percentage=100.0
            )
            
            # Establish connection
            manager.connect()
            
            # Verify connection start time is tracked
            assert manager._connection_start_time is not None
            
            # Verify uptime is calculated
            metrics = manager.get_connection_metrics()
            assert metrics.current_uptime.total_seconds() >= 0

    def test_concurrent_connection_attempts(self, manager):
        """Test handling of concurrent connection attempts"""
        with patch('src.email.reconnection_manager.GoDaddyEmailClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_connection_health.return_value = ConnectionHealthStatus(
                status=ConnectionHealth.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=100.0,
                error_count=0,
                last_error=None,
                uptime_percentage=100.0
            )
            
            # Start multiple connection attempts concurrently
            threads = []
            results = []
            
            def connect_worker():
                result = manager.connect()
                results.append(result)
            
            for _ in range(5):
                thread = threading.Thread(target=connect_worker)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Should have at least one successful connection
            assert any(results)
            assert manager.get_connection_state() == ConnectionState.CONNECTED

    def test_shutdown_cleanup(self, manager):
        """Test proper cleanup during shutdown"""
        with patch('src.email.reconnection_manager.GoDaddyEmailClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.close.return_value = None
            mock_client.get_connection_health.return_value = ConnectionHealthStatus(
                status=ConnectionHealth.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=100.0,
                error_count=0,
                last_error=None,
                uptime_percentage=100.0
            )
            
            # Establish connection
            manager.connect()
            assert manager.get_connection_state() == ConnectionState.CONNECTED
            
            # Shutdown
            manager.shutdown()
            
            # Verify cleanup
            assert manager.get_connection_state() == ConnectionState.DISCONNECTED
            assert manager._shutdown_event.is_set()
            mock_client.close.assert_called_once()


class TestReconnectionIntegration:
    """Integration tests for reconnection manager with real scenarios"""
    
    @pytest.fixture
    def temp_state_file(self):
        """Create temporary state file"""
        temp_file = tempfile.mktemp(suffix='.json')
        yield temp_file
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    def test_state_persistence_integration(self, temp_state_file):
        """Test complete state persistence and recovery cycle"""
        account_config = {
            'imap_host': 'imap.test.com',
            'username': 'test@test.com',
            'password': 'testpass'
        }
        
        reconnection_config = ReconnectionConfig(
            state_persistence_path=temp_state_file,
            health_check_interval=0.1
        )
        
        # Create first manager instance
        with patch('src.email.reconnection_manager.GoDaddyEmailClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.connect.side_effect = Exception("Network error")
            
            manager1 = IntelligentReconnectionManager(
                account_config=account_config,
                reconnection_config=reconnection_config
            )
            
            try:
                # Trigger some failures
                manager1.connect()
                time.sleep(0.1)
                
                # Verify state file was created
                assert os.path.exists(temp_state_file)
                
                # Verify state content
                with open(temp_state_file, 'r') as f:
                    state_data = json.load(f)
                
                assert 'consecutive_failures' in state_data
                assert 'metrics' in state_data
                assert 'failure_history' in state_data
                
            finally:
                manager1.shutdown()
        
        # Create second manager instance to test recovery
        with patch('src.email.reconnection_manager.GoDaddyEmailClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_connection_health.return_value = ConnectionHealthStatus(
                status=ConnectionHealth.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=100.0,
                error_count=0,
                last_error=None,
                uptime_percentage=100.0
            )
            
            manager2 = IntelligentReconnectionManager(
                account_config=account_config,
                reconnection_config=reconnection_config
            )
            
            try:
                # Should have loaded previous state
                assert manager2._consecutive_failures > 0
                assert len(manager2.get_failure_history()) > 0
                
                # Should be able to connect successfully
                success = manager2.connect()
                assert success is True
                
            finally:
                manager2.shutdown()

    def test_end_to_end_reconnection_scenario(self):
        """Test complete end-to-end reconnection scenario"""
        account_config = {
            'imap_host': 'imap.test.com',
            'username': 'test@test.com',
            'password': 'testpass'
        }
        
        reconnection_config = ReconnectionConfig(
            initial_backoff=0.1,
            max_backoff=0.5,
            max_retry_attempts=3,
            health_check_interval=0.2
        )
        
        fallback_config = FallbackMechanism(
            enabled=True,
            fallback_servers=[
                {'imap_host': 'backup.test.com'}
            ],
            max_fallback_attempts=1
        )
        
        with patch('src.email.reconnection_manager.GoDaddyEmailClient') as mock_client_class:
            # Setup mock to fail initially, then succeed
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            connection_attempts = 0
            def connect_side_effect():
                nonlocal connection_attempts
                connection_attempts += 1
                if connection_attempts <= 2:
                    raise Exception("Temporary network error")
                return None  # Success on third attempt
            
            mock_client.connect.side_effect = connect_side_effect
            mock_client.get_connection_health.return_value = ConnectionHealthStatus(
                status=ConnectionHealth.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=100.0,
                error_count=0,
                last_error=None,
                uptime_percentage=100.0
            )
            
            manager = IntelligentReconnectionManager(
                account_config=account_config,
                reconnection_config=reconnection_config,
                fallback_config=fallback_config
            )
            
            try:
                # Initial connection should fail
                success = manager.connect()
                assert success is False
                assert manager.get_connection_state() == ConnectionState.FAILED
                
                # Wait for automatic reconnection
                max_wait_time = 5.0
                start_time = time.time()
                
                while (manager.get_connection_state() != ConnectionState.CONNECTED and 
                       time.time() - start_time < max_wait_time):
                    time.sleep(0.1)
                
                # Should eventually succeed
                assert manager.get_connection_state() == ConnectionState.CONNECTED
                assert connection_attempts >= 3
                
                # Verify metrics
                metrics = manager.get_connection_metrics()
                assert metrics.successful_connections >= 1
                assert metrics.failed_connections >= 2
                assert metrics.reconnection_attempts >= 2
                
            finally:
                manager.shutdown()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])