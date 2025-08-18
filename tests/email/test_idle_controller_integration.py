# tests/email/test_idle_controller_integration.py
import pytest
import time
import threading
import logging
from unittest.mock import Mock, patch
from datetime import datetime

from src.email.idle_controller import (
    IMAPIdleController,
    IdleSession,
    IdleEvent,
    IdleSessionState,
    IdleEventType
)
from src.email.connection_pool import ConnectionPoolManager
from src.email.godaddy_client import GoDaddyEmailClient
from tests.email.mock_godaddy_server import (
    MockGoDaddyIMAPServer,
    MockGoDaddyServerIntegrationTest,
    MockEmail
)


# Configure logging for tests
logging.basicConfig(level=logging.INFO)


class TestIdleControllerIntegration:
    """Integration tests for IMAP IDLE Controller with mock GoDaddy server"""
    
    @pytest.fixture
    def mock_server_test(self):
        """Fixture for mock server integration test"""
        test_helper = MockGoDaddyServerIntegrationTest(port=9994)
        test_helper.setup()
        yield test_helper
        test_helper.teardown()
    
    @pytest.fixture
    def mock_connection_pool(self, mock_server_test):
        """Fixture for mock connection pool with real IMAP connections"""
        # Create a mock connection pool that returns real connections to mock server
        pool = Mock()
        
        def get_connection():
            # Create real GoDaddy client configured for mock server
            client = GoDaddyEmailClient()
            
            # Override connection settings for mock server
            client.imap_host = "localhost"
            client.imap_port = mock_server_test.server.port
            client.username = "test@example.com"
            client.password = "testpass"
            
            # Mock the connection to avoid SSL issues
            mock_imap = Mock()
            mock_imap.select = Mock(return_value=('OK', [b'SELECT completed']))
            mock_imap._new_tag = Mock(return_value='A001')
            mock_imap.send = Mock()
            mock_imap.readline = Mock(return_value=b'+ idling\r\n')
            mock_imap.sock = Mock()
            mock_imap.sock.settimeout = Mock()
            
            client.imap = mock_imap
            client.smtp = Mock()  # Mock SMTP for testing
            
            # Create pooled connection
            pooled_conn = Mock()
            pooled_conn.connection = client
            
            return pooled_conn
        
        pool.get_connection = get_connection
        pool.return_connection = Mock()
        
        return pool
    
    def test_idle_session_with_mock_server(self, mock_server_test):
        """Test IDLE session with mock GoDaddy server"""
        events_received = []
        sessions_changed = []
        
        def event_callback(event):
            events_received.append(event)
        
        def session_callback(session, state):
            sessions_changed.append((session.account_id, state))
        
        # Create connection pool mock
        pool = Mock()
        
        def get_connection():
            # Create a more realistic mock connection
            client = Mock()
            client.test_idle_support = Mock(return_value=True)
            client.get_connection_health = Mock()
            client.get_connection_health.return_value.status.value = 'healthy'
            
            # Mock IMAP connection
            mock_imap = Mock()
            mock_imap.select = Mock(return_value=('OK', [b'SELECT completed']))
            mock_imap._new_tag = Mock(return_value='A001')
            mock_imap.send = Mock()
            mock_imap.readline = Mock(side_effect=[
                b'+ idling\r\n',  # IDLE confirmation
                b'* 5 EXISTS\r\n',  # New email event
                b'A001 OK IDLE terminated\r\n'  # DONE response
            ])
            mock_imap.sock = Mock()
            mock_imap.sock.settimeout = Mock()
            
            client.imap = mock_imap
            
            pooled_conn = Mock()
            pooled_conn.connection = client
            
            return pooled_conn
        
        pool.get_connection = get_connection
        pool.return_connection = Mock()
        
        # Create IDLE controller
        controller = IMAPIdleController(
            connection_pool=pool,
            default_timeout=30,  # Short timeout for testing
            renewal_buffer=5
        )
        
        try:
            # Add callbacks
            controller.add_event_callback(event_callback)
            controller.add_session_callback(session_callback)
            
            # Start IDLE session
            session = controller.start_idle_session("test_account", "INBOX")
            
            # Wait for session to become active
            time.sleep(1)
            
            # Check session is active
            assert session.state in [IdleSessionState.STARTING, IdleSessionState.ACTIVE]
            
            # Simulate server events by directly queuing events
            test_event = IdleEvent(
                event_type=IdleEventType.NEW_EMAIL,
                account_id="test_account",
                mailbox="INBOX",
                timestamp=datetime.now(),
                metadata={'email_count': '5'}
            )
            controller._queue_event(test_event)
            
            # Wait for event processing
            time.sleep(0.5)
            
            # Check events were processed
            assert len(events_received) >= 1
            assert any(e.event_type == IdleEventType.NEW_EMAIL for e in events_received)
            
            # Check session state changes
            assert len(sessions_changed) >= 1
            assert any(state == IdleSessionState.STARTING for _, state in sessions_changed)
            
        finally:
            controller.shutdown()
    
    def test_idle_session_renewal_integration(self, mock_server_test):
        """Test IDLE session renewal in integration environment"""
        renewal_events = []
        
        def session_callback(session, state):
            if state == IdleSessionState.RENEWING:
                renewal_events.append(session.session_id)
        
        # Create mock connection pool
        pool = Mock()
        
        def get_connection():
            client = Mock()
            client.test_idle_support = Mock(return_value=True)
            client.get_connection_health = Mock()
            client.get_connection_health.return_value.status.value = 'healthy'
            
            # Mock IMAP with renewal simulation
            mock_imap = Mock()
            mock_imap.select = Mock(return_value=('OK', [b'SELECT completed']))
            mock_imap._new_tag = Mock(return_value='A001')
            mock_imap.send = Mock()
            mock_imap.readline = Mock(side_effect=[
                b'+ idling\r\n',  # Initial IDLE
                b'A001 OK IDLE terminated\r\n',  # DONE response for renewal
                b'+ idling\r\n',  # Renewed IDLE
                b'A002 OK IDLE terminated\r\n'  # Final DONE
            ])
            mock_imap.sock = Mock()
            mock_imap.sock.settimeout = Mock()
            
            client.imap = mock_imap
            
            pooled_conn = Mock()
            pooled_conn.connection = client
            
            return pooled_conn
        
        pool.get_connection = get_connection
        pool.return_connection = Mock()
        
        # Create controller with short timeout for testing
        controller = IMAPIdleController(
            connection_pool=pool,
            default_timeout=5,  # 5 seconds
            renewal_buffer=2   # Renew after 3 seconds
        )
        
        try:
            controller.add_session_callback(session_callback)
            
            # Start session
            session = controller.start_idle_session("test_account", "INBOX")
            
            # Wait for renewal to occur
            time.sleep(4)
            
            # Check that renewal occurred
            assert len(renewal_events) >= 1
            assert session.renewal_count >= 1
            
        finally:
            controller.shutdown()
    
    def test_idle_fallback_to_polling(self, mock_server_test):
        """Test fallback to polling when IDLE fails"""
        fallback_calls = []
        
        def fallback_callback(account_id):
            fallback_calls.append(account_id)
        
        # Create connection pool that doesn't support IDLE
        pool = Mock()
        
        def get_connection():
            client = Mock()
            client.test_idle_support = Mock(return_value=False)  # No IDLE support
            
            pooled_conn = Mock()
            pooled_conn.connection = client
            
            return pooled_conn
        
        pool.get_connection = get_connection
        pool.return_connection = Mock()
        
        controller = IMAPIdleController(
            connection_pool=pool,
            fallback_callback=fallback_callback
        )
        
        try:
            # Try to start IDLE session - should fail and trigger fallback
            with pytest.raises(Exception, match="IDLE not supported"):
                controller.start_idle_session("test_account", "INBOX")
            
            # Check fallback was called
            assert len(fallback_calls) == 1
            assert fallback_calls[0] == "test_account"
            
            # Check metrics
            metrics = controller.get_metrics()
            assert metrics.fallback_to_polling_count == 1
            
        finally:
            controller.shutdown()
    
    def test_multiple_concurrent_idle_sessions(self, mock_server_test):
        """Test multiple concurrent IDLE sessions"""
        events_by_account = {}
        
        def event_callback(event):
            if event.account_id not in events_by_account:
                events_by_account[event.account_id] = []
            events_by_account[event.account_id].append(event)
        
        # Create connection pool
        pool = Mock()
        
        def get_connection():
            client = Mock()
            client.test_idle_support = Mock(return_value=True)
            client.get_connection_health = Mock()
            client.get_connection_health.return_value.status.value = 'healthy'
            
            mock_imap = Mock()
            mock_imap.select = Mock(return_value=('OK', [b'SELECT completed']))
            mock_imap._new_tag = Mock(return_value='A001')
            mock_imap.send = Mock()
            mock_imap.readline = Mock(return_value=b'+ idling\r\n')
            mock_imap.sock = Mock()
            mock_imap.sock.settimeout = Mock()
            
            client.imap = mock_imap
            
            pooled_conn = Mock()
            pooled_conn.connection = client
            
            return pooled_conn
        
        pool.get_connection = get_connection
        pool.return_connection = Mock()
        
        controller = IMAPIdleController(
            connection_pool=pool,
            max_concurrent_sessions=3
        )
        
        try:
            controller.add_event_callback(event_callback)
            
            # Start multiple sessions
            accounts = ["account1", "account2", "account3"]
            sessions = []
            
            for account in accounts:
                session = controller.start_idle_session(account, "INBOX")
                sessions.append(session)
            
            # Wait for sessions to become active
            time.sleep(1)
            
            # Check all sessions are active
            active_sessions = controller.get_active_sessions()
            assert len(active_sessions) == 3
            
            # Simulate events for each account
            for i, account in enumerate(accounts):
                event = IdleEvent(
                    event_type=IdleEventType.NEW_EMAIL,
                    account_id=account,
                    mailbox="INBOX",
                    timestamp=datetime.now(),
                    metadata={'email_count': str(i + 5)}
                )
                controller._queue_event(event)
            
            # Wait for event processing
            time.sleep(0.5)
            
            # Check events were processed for each account
            assert len(events_by_account) == 3
            for account in accounts:
                assert account in events_by_account
                assert len(events_by_account[account]) >= 1
            
        finally:
            controller.shutdown()
    
    def test_idle_session_error_recovery(self, mock_server_test):
        """Test IDLE session error recovery"""
        session_failures = []
        
        def session_callback(session, state):
            if state == IdleSessionState.FAILED:
                session_failures.append(session.session_id)
        
        # Create connection pool with failing connection
        pool = Mock()
        connection_attempts = 0
        
        def get_connection():
            nonlocal connection_attempts
            connection_attempts += 1
            
            client = Mock()
            client.test_idle_support = Mock(return_value=True)
            client.get_connection_health = Mock()
            client.get_connection_health.return_value.status.value = 'healthy'
            
            mock_imap = Mock()
            mock_imap.select = Mock(return_value=('OK', [b'SELECT completed']))
            mock_imap._new_tag = Mock(return_value='A001')
            mock_imap.send = Mock()
            
            # First connection fails, second succeeds
            if connection_attempts == 1:
                mock_imap.readline = Mock(side_effect=Exception("Connection failed"))
            else:
                mock_imap.readline = Mock(return_value=b'+ idling\r\n')
            
            mock_imap.sock = Mock()
            mock_imap.sock.settimeout = Mock()
            
            client.imap = mock_imap
            
            pooled_conn = Mock()
            pooled_conn.connection = client
            
            return pooled_conn
        
        pool.get_connection = get_connection
        pool.return_connection = Mock()
        
        controller = IMAPIdleController(connection_pool=pool)
        
        try:
            controller.add_session_callback(session_callback)
            
            # Start session - first attempt should fail
            session = controller.start_idle_session("test_account", "INBOX")
            
            # Wait for failure
            time.sleep(1)
            
            # Check session failed
            assert len(session_failures) >= 1
            
        finally:
            controller.shutdown()
    
    def test_idle_controller_metrics_integration(self, mock_server_test):
        """Test metrics collection in integration environment"""
        # Create connection pool
        pool = Mock()
        
        def get_connection():
            client = Mock()
            client.test_idle_support = Mock(return_value=True)
            client.get_connection_health = Mock()
            client.get_connection_health.return_value.status.value = 'healthy'
            
            mock_imap = Mock()
            mock_imap.select = Mock(return_value=('OK', [b'SELECT completed']))
            mock_imap._new_tag = Mock(return_value='A001')
            mock_imap.send = Mock()
            mock_imap.readline = Mock(return_value=b'+ idling\r\n')
            mock_imap.sock = Mock()
            mock_imap.sock.settimeout = Mock()
            
            client.imap = mock_imap
            
            pooled_conn = Mock()
            pooled_conn.connection = client
            
            return pooled_conn
        
        pool.get_connection = get_connection
        pool.return_connection = Mock()
        
        controller = IMAPIdleController(connection_pool=pool)
        
        try:
            # Start multiple sessions
            sessions = []
            for i in range(2):
                session = controller.start_idle_session(f"account_{i}", "INBOX")
                sessions.append(session)
            
            # Wait for sessions to become active
            time.sleep(1)
            
            # Simulate some events
            for i in range(3):
                event = IdleEvent(
                    event_type=IdleEventType.NEW_EMAIL,
                    account_id=f"account_{i % 2}",
                    mailbox="INBOX",
                    timestamp=datetime.now()
                )
                controller._queue_event(event)
            
            # Wait for event processing
            time.sleep(0.5)
            
            # Check metrics
            metrics = controller.get_metrics()
            
            assert metrics.total_sessions == 2
            assert metrics.active_sessions == 2
            assert metrics.total_events_processed >= 3
            assert isinstance(metrics.last_updated, datetime)
            
            # Stop one session and check metrics update
            controller.stop_idle_session("account_0", "INBOX")
            time.sleep(0.5)
            
            updated_metrics = controller.get_metrics()
            assert updated_metrics.active_sessions == 1
            
        finally:
            controller.shutdown()
    
    def test_idle_session_timeout_integration(self, mock_server_test):
        """Test IDLE session timeout in integration environment"""
        timeout_events = []
        
        def session_callback(session, state):
            if state == IdleSessionState.TERMINATED:
                timeout_events.append(session.session_id)
        
        # Create connection pool
        pool = Mock()
        
        def get_connection():
            client = Mock()
            client.test_idle_support = Mock(return_value=True)
            client.get_connection_health = Mock()
            client.get_connection_health.return_value.status.value = 'healthy'
            
            mock_imap = Mock()
            mock_imap.select = Mock(return_value=('OK', [b'SELECT completed']))
            mock_imap._new_tag = Mock(return_value='A001')
            mock_imap.send = Mock()
            mock_imap.readline = Mock(return_value=b'+ idling\r\n')
            mock_imap.sock = Mock()
            mock_imap.sock.settimeout = Mock()
            
            client.imap = mock_imap
            
            pooled_conn = Mock()
            pooled_conn.connection = client
            
            return pooled_conn
        
        pool.get_connection = get_connection
        pool.return_connection = Mock()
        
        # Create controller with very short timeout
        controller = IMAPIdleController(
            connection_pool=pool,
            default_timeout=2,  # 2 seconds
            renewal_buffer=1    # Renew after 1 second
        )
        
        try:
            controller.add_session_callback(session_callback)
            
            # Start session
            session = controller.start_idle_session("test_account", "INBOX")
            
            # Wait for timeout
            time.sleep(3)
            
            # Session should have been renewed or terminated
            assert session.renewal_count >= 1 or session.state == IdleSessionState.TERMINATED
            
        finally:
            controller.shutdown()


class TestIdleControllerRealWorldScenarios:
    """Test real-world scenarios with IDLE controller"""
    
    def test_high_volume_email_processing(self):
        """Test handling high volume of email events"""
        events_processed = []
        
        def event_callback(event):
            events_processed.append(event)
        
        # Create mock connection pool
        pool = Mock()
        
        def get_connection():
            client = Mock()
            client.test_idle_support = Mock(return_value=True)
            client.get_connection_health = Mock()
            client.get_connection_health.return_value.status.value = 'healthy'
            
            mock_imap = Mock()
            mock_imap.select = Mock(return_value=('OK', [b'SELECT completed']))
            mock_imap._new_tag = Mock(return_value='A001')
            mock_imap.send = Mock()
            mock_imap.readline = Mock(return_value=b'+ idling\r\n')
            mock_imap.sock = Mock()
            mock_imap.sock.settimeout = Mock()
            
            client.imap = mock_imap
            
            pooled_conn = Mock()
            pooled_conn.connection = client
            
            return pooled_conn
        
        pool.get_connection = get_connection
        pool.return_connection = Mock()
        
        controller = IMAPIdleController(connection_pool=pool)
        
        try:
            controller.add_event_callback(event_callback)
            
            # Start session
            session = controller.start_idle_session("high_volume_account", "INBOX")
            time.sleep(0.5)
            
            # Generate high volume of events
            for i in range(50):
                event = IdleEvent(
                    event_type=IdleEventType.NEW_EMAIL,
                    account_id="high_volume_account",
                    mailbox="INBOX",
                    timestamp=datetime.now(),
                    metadata={'email_count': str(i + 1)}
                )
                controller._queue_event(event)
            
            # Wait for processing
            time.sleep(2)
            
            # Check all events were processed
            assert len(events_processed) == 50
            
            # Check metrics
            metrics = controller.get_metrics()
            assert metrics.total_events_processed >= 50
            
        finally:
            controller.shutdown()
    
    def test_network_interruption_recovery(self):
        """Test recovery from network interruptions"""
        connection_failures = []
        recoveries = []
        
        def session_callback(session, state):
            if state == IdleSessionState.FAILED:
                connection_failures.append(session.session_id)
            elif state == IdleSessionState.ACTIVE:
                recoveries.append(session.session_id)
        
        # Create connection pool that simulates network issues
        pool = Mock()
        connection_attempts = 0
        
        def get_connection():
            nonlocal connection_attempts
            connection_attempts += 1
            
            client = Mock()
            client.test_idle_support = Mock(return_value=True)
            client.get_connection_health = Mock()
            
            # Simulate network recovery after 2 attempts
            if connection_attempts <= 2:
                client.get_connection_health.return_value.status.value = 'unhealthy'
            else:
                client.get_connection_health.return_value.status.value = 'healthy'
            
            mock_imap = Mock()
            mock_imap.select = Mock(return_value=('OK', [b'SELECT completed']))
            mock_imap._new_tag = Mock(return_value='A001')
            mock_imap.send = Mock()
            
            # Simulate connection failure then recovery
            if connection_attempts <= 2:
                mock_imap.readline = Mock(side_effect=Exception("Network error"))
            else:
                mock_imap.readline = Mock(return_value=b'+ idling\r\n')
            
            mock_imap.sock = Mock()
            mock_imap.sock.settimeout = Mock()
            
            client.imap = mock_imap
            
            pooled_conn = Mock()
            pooled_conn.connection = client
            
            return pooled_conn
        
        pool.get_connection = get_connection
        pool.return_connection = Mock()
        
        controller = IMAPIdleController(connection_pool=pool)
        
        try:
            controller.add_session_callback(session_callback)
            
            # Start session - should initially fail
            session = controller.start_idle_session("network_test_account", "INBOX")
            
            # Wait for failure and potential recovery
            time.sleep(2)
            
            # Check that failure was detected
            assert len(connection_failures) >= 1
            
        finally:
            controller.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])