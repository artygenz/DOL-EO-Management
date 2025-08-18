# tests/email/test_enhanced_godaddy_client_reconnection.py
import pytest
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from email.message import EmailMessage

from src.email.enhanced_godaddy_client import EnhancedGoDaddyEmailClient
from src.email.reconnection_manager import (
    ConnectionState,
    ReconnectionConfig,
    FallbackMechanism,
    ConnectionFailure,
    FailureType
)
from src.email.godaddy_client import ConnectionHealth, ConnectionHealthStatus


class TestEnhancedGoDaddyClientReconnection:
    """Test suite for EnhancedGoDaddyEmailClient reconnection functionality"""
    
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
        """Fast reconnection config for testing"""
        return ReconnectionConfig(
            initial_backoff=0.1,
            max_backoff=0.5,
            backoff_multiplier=2.0,
            max_retry_attempts=3,
            health_check_interval=0.2,
            state_persistence_path=tempfile.mktemp(suffix='.json')
        )
    
    @pytest.fixture
    def fallback_config(self):
        """Fallback configuration for testing"""
        return FallbackMechanism(
            enabled=True,
            fallback_servers=[
                {'imap_host': 'backup.test.com', 'smtp_host': 'backup.test.com'}
            ],
            max_fallback_attempts=1
        )
    
    @pytest.fixture
    def enhanced_client(self, account_config, reconnection_config, fallback_config):
        """Create enhanced client instance"""
        with patch('src.email.reconnection_manager.GoDaddyEmailClient'):
            client = EnhancedGoDaddyEmailClient(
                account_config=account_config,
                reconnection_config=reconnection_config,
                fallback_config=fallback_config,
                auto_reconnect=False  # Disable auto-reconnect for controlled testing
            )
            yield client
            client.close()
            
            # Cleanup state file
            if os.path.exists(reconnection_config.state_persistence_path):
                os.unlink(reconnection_config.state_persistence_path)

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_successful_connection_establishment(self, mock_client_class, enhanced_client):
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
        enhanced_client.connect()
        
        assert enhanced_client.is_connected()
        assert enhanced_client.is_healthy()
        assert enhanced_client.get_connection_state() == ConnectionState.CONNECTED

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_automatic_reconnection_on_operation_failure(self, mock_client_class, enhanced_client):
        """Test automatic reconnection when operations fail"""
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
        
        # First establish connection
        enhanced_client.connect()
        assert enhanced_client.is_connected()
        
        # Setup operation to fail first time, succeed second time
        call_count = 0
        def fetch_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Connection lost")
            return []  # Success on retry
        
        mock_client.fetch_unread_emails.side_effect = fetch_side_effect
        
        # Test operation with automatic retry
        result = enhanced_client.fetch_unread_emails()
        
        assert result == []
        assert call_count == 2  # Should have retried once
        assert mock_client.connect.call_count >= 2  # Should have reconnected

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_operation_retry_with_exponential_backoff(self, mock_client_class, enhanced_client):
        """Test operation retry with proper backoff"""
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
        
        # Establish connection
        enhanced_client.connect()
        
        # Setup operation to fail multiple times
        mock_client.fetch_unread_emails.side_effect = Exception("Network error")
        
        # Measure retry timing
        start_time = time.time()
        
        with pytest.raises(Exception, match="Network error"):
            enhanced_client.fetch_unread_emails()
        
        elapsed_time = time.time() - start_time
        
        # Should have taken some time due to retry delays
        assert elapsed_time > 0.1  # At least some delay from retries
        assert mock_client.fetch_unread_emails.call_count == enhanced_client.max_operation_retries

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_non_connection_error_no_retry(self, mock_client_class, enhanced_client):
        """Test that non-connection errors don't trigger reconnection"""
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
        
        # Establish connection
        enhanced_client.connect()
        initial_connect_calls = mock_client.connect.call_count
        
        # Setup operation to fail with non-connection error
        mock_client.send_email.side_effect = ValueError("Invalid email address")
        
        # Test operation
        with pytest.raises(ValueError, match="Invalid email address"):
            enhanced_client.send_email("invalid", "test", "test")
        
        # Should not have triggered additional connection attempts
        assert mock_client.connect.call_count == initial_connect_calls
        assert mock_client.send_email.call_count == 1  # No retries for non-connection errors

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_force_reconnect_functionality(self, mock_client_class, enhanced_client):
        """Test force reconnect functionality"""
        # Setup mock
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
        
        # Establish initial connection
        enhanced_client.connect()
        initial_connect_calls = mock_client.connect.call_count
        
        # Force reconnect
        success = enhanced_client.force_reconnect()
        
        assert success is True
        assert mock_client.connect.call_count > initial_connect_calls
        assert mock_client.close.call_count >= 1

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_connection_health_monitoring(self, mock_client_class, enhanced_client):
        """Test connection health monitoring"""
        # Setup mock
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
        enhanced_client.connect()
        assert enhanced_client.is_healthy()
        
        # Change to unhealthy
        mock_client.get_connection_health.return_value = ConnectionHealthStatus(
            status=ConnectionHealth.UNHEALTHY,
            last_check=datetime.now(),
            response_time_ms=5000.0,
            error_count=5,
            last_error="Connection degraded",
            uptime_percentage=50.0
        )
        
        # Should detect unhealthy state
        assert not enhanced_client.is_healthy()

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_server_capability_delegation(self, mock_client_class, enhanced_client):
        """Test server capability detection delegation"""
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
        
        # Setup capability mock
        mock_capabilities = Mock()
        mock_capabilities.idle_supported = True
        mock_client.get_server_capabilities.return_value = mock_capabilities
        mock_client.test_idle_support.return_value = True
        
        # Establish connection
        enhanced_client.connect()
        
        # Test capability methods
        capabilities = enhanced_client.get_server_capabilities()
        assert capabilities.idle_supported is True
        
        idle_support = enhanced_client.test_idle_support()
        assert idle_support is True

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_email_operations_with_reconnection(self, mock_client_class, enhanced_client):
        """Test all email operations work with reconnection"""
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
        
        # Setup operation mocks
        mock_client.fetch_unread_emails.return_value = []
        mock_client.list_inbox.return_value = []
        mock_client.send_email.return_value = None
        mock_client.send_templated_response.return_value = None
        mock_client.extract_pdf_attachments.return_value = []
        
        # Establish connection
        enhanced_client.connect()
        
        # Test all operations
        emails = enhanced_client.fetch_unread_emails()
        assert emails == []
        
        inbox = enhanced_client.list_inbox()
        assert inbox == []
        
        enhanced_client.send_email("test@test.com", "Test", "Body")
        mock_client.send_email.assert_called_once()
        
        enhanced_client.send_templated_response("test@test.com", "template", subject="Test")
        mock_client.send_templated_response.assert_called_once()
        
        test_email = EmailMessage()
        attachments = enhanced_client.extract_pdf_attachments(test_email)
        assert attachments == []

    def test_connection_state_tracking(self, enhanced_client):
        """Test connection state tracking"""
        # Initially disconnected
        assert enhanced_client.get_connection_state() == ConnectionState.DISCONNECTED
        assert not enhanced_client.is_connected()
        
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
            
            # Connect
            enhanced_client.connect()
            assert enhanced_client.get_connection_state() == ConnectionState.CONNECTED
            assert enhanced_client.is_connected()

    def test_connection_metrics_tracking(self, enhanced_client):
        """Test connection metrics tracking"""
        initial_metrics = enhanced_client.get_connection_metrics()
        assert initial_metrics.total_connections == 0
        
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
            
            # Connect
            enhanced_client.connect()
            
            metrics = enhanced_client.get_connection_metrics()
            assert metrics.total_connections == 1
            assert metrics.successful_connections == 1

    def test_failure_history_tracking(self, enhanced_client):
        """Test failure history tracking"""
        initial_history = enhanced_client.get_failure_history()
        assert len(initial_history) == 0
        
        with patch('src.email.reconnection_manager.GoDaddyEmailClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.connect.side_effect = Exception("Connection failed")
            
            # Attempt connection (should fail)
            try:
                enhanced_client.connect()
            except:
                pass
            
            # Should have failure history
            history = enhanced_client.get_failure_history()
            assert len(history) > 0
            assert isinstance(history[0], ConnectionFailure)

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_wait_for_connection(self, mock_client_class, enhanced_client):
        """Test waiting for connection establishment"""
        # Setup mock to succeed after delay
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        connection_delay = 0.2
        def delayed_connect():
            time.sleep(connection_delay)
            return None
        
        mock_client.connect.side_effect = delayed_connect
        mock_client.get_connection_health.return_value = ConnectionHealthStatus(
            status=ConnectionHealth.HEALTHY,
            last_check=datetime.now(),
            response_time_ms=100.0,
            error_count=0,
            last_error=None,
            uptime_percentage=100.0
        )
        
        # Start connection in background
        import threading
        def connect_worker():
            enhanced_client.connect()
        
        thread = threading.Thread(target=connect_worker)
        thread.start()
        
        # Wait for connection
        success = enhanced_client.wait_for_connection(timeout=1.0)
        thread.join()
        
        assert success is True
        assert enhanced_client.is_connected()

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_uptime_statistics(self, mock_client_class, enhanced_client):
        """Test uptime statistics calculation"""
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
        
        # Connect
        enhanced_client.connect()
        
        # Get uptime stats
        stats = enhanced_client.get_uptime_stats()
        
        assert 'uptime_percentage' in stats
        assert 'current_uptime' in stats
        assert 'total_connections' in stats
        assert 'successful_connections' in stats
        assert stats['total_connections'] >= 1

    @patch('src.email.reconnection_manager.GoDaddyEmailClient')
    def test_connection_test_diagnostics(self, mock_client_class, enhanced_client):
        """Test comprehensive connection test"""
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
        
        # Setup capability and operation mocks
        mock_capabilities = Mock()
        mock_capabilities.idle_supported = True
        mock_capabilities.supported_extensions = ['IDLE', 'MOVE']
        mock_client.get_server_capabilities.return_value = mock_capabilities
        
        mock_rate_info = Mock()
        mock_rate_info.is_rate_limited = False
        mock_rate_info.requests_per_minute = 60
        mock_client.get_rate_limit_info.return_value = mock_rate_info
        
        mock_client.list_inbox.return_value = [{'subject': 'test'}]
        
        # Connect and run test
        enhanced_client.connect()
        test_results = enhanced_client.perform_connection_test()
        
        # Verify test results
        assert 'timestamp' in test_results
        assert test_results['is_connected'] is True
        assert test_results['is_healthy'] is True
        assert 'connection_health' in test_results
        assert 'server_capabilities' in test_results
        assert 'rate_limit_info' in test_results
        assert 'test_operations' in test_results
        
        # Verify operation test results
        assert 'list_inbox' in test_results['test_operations']
        assert test_results['test_operations']['list_inbox']['success'] is True
        assert test_results['test_operations']['list_inbox']['email_count'] == 1

    def test_callback_registration(self, enhanced_client):
        """Test connection and failure callback registration"""
        connection_callbacks = []
        failure_callbacks = []
        
        def connection_callback(state, error):
            connection_callbacks.append((state, error))
        
        def failure_callback(failure):
            failure_callbacks.append(failure)
        
        # Register callbacks
        enhanced_client.add_connection_callback(connection_callback)
        enhanced_client.add_failure_callback(failure_callback)
        
        with patch('src.email.reconnection_manager.GoDaddyEmailClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.connect.side_effect = Exception("Test failure")
            
            # Trigger failure
            try:
                enhanced_client.connect()
            except:
                pass
            
            # Wait for callbacks
            time.sleep(0.1)
            
            # Verify callbacks were called
            assert len(connection_callbacks) > 0
            assert len(failure_callbacks) > 0

    def test_configuration_updates(self, enhanced_client):
        """Test account configuration updates"""
        original_host = enhanced_client.account_config['imap_host']
        
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
            
            # Update configuration
            new_config = {'imap_host': 'new.test.com'}
            enhanced_client.update_account_config(new_config)
            
            # Verify configuration was updated
            assert enhanced_client.account_config['imap_host'] == 'new.test.com'
            
            # Should have triggered reconnection
            assert mock_client.connect.call_count >= 1

    def test_auto_reconnect_toggle(self, enhanced_client):
        """Test auto-reconnect enable/disable functionality"""
        # Initially disabled for testing
        assert enhanced_client.auto_reconnect is False
        
        # Enable auto-reconnect
        enhanced_client.enable_auto_reconnect()
        assert enhanced_client.auto_reconnect is True
        
        # Disable auto-reconnect
        enhanced_client.disable_auto_reconnect()
        assert enhanced_client.auto_reconnect is False

    def test_operation_retry_configuration(self, enhanced_client):
        """Test operation retry configuration"""
        # Set custom retry configuration
        enhanced_client.set_operation_retry_config(max_retries=5, retry_delay=0.5)
        
        assert enhanced_client.max_operation_retries == 5
        assert enhanced_client.operation_retry_delay == 0.5

    def test_context_manager_usage(self, account_config, reconnection_config):
        """Test context manager usage"""
        with patch('src.email.reconnection_manager.GoDaddyEmailClient'):
            with EnhancedGoDaddyEmailClient(
                account_config=account_config,
                reconnection_config=reconnection_config,
                auto_reconnect=False
            ) as client:
                assert client is not None
                assert hasattr(client, 'connect')
            
            # Should be properly closed after context exit
            assert client.reconnection_manager._shutdown_event.is_set()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])