# tests/email/test_idle_controller.py
import pytest
import threading
import time
import socket
import select
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
from queue import Queue, Empty

from src.email.idle_controller import (
    IMAPIdleController,
    IdleSession,
    IdleEvent,
    IdleSessionState,
    IdleEventType,
    IdleControllerMetrics
)
from src.email.connection_pool import ConnectionPoolManager, PooledConnection
from src.email.godaddy_client import GoDaddyEmailClient, ServerCapabilities


class MockIMAPConnection:
    """Mock IMAP connection for testing"""
    
    def __init__(self, idle_supported=True, should_fail=False):
        self.idle_supported = idle_supported
        self.should_fail = should_fail
        self.selected_mailbox = None
        self.idle_active = False
        self.responses = Queue()
        self.sent_commands = []
        self.sock = Mock()
        self._tag_counter = 0
        
        # Configure socket mock
        self.sock.settimeout = Mock()
        
    def select(self, mailbox):
        """Mock mailbox selection"""
        if self.should_fail:
            raise Exception("Mock IMAP failure")
        self.selected_mailbox = mailbox
        return ('OK', [b'SELECT completed'])
    
    def _new_tag(self):
        """Generate new IMAP tag"""
        self._tag_counter += 1
        return f'A{self._tag_counter:04d}'
    
    def send(self, command):
        """Mock send command"""
        if self.should_fail:
            raise Exception("Mock send failure")
        
        self.sent_commands.append(command)
        
        if b'IDLE' in command:
            self.idle_active = True
            # Simulate IDLE confirmation
            self.responses.put(b'+ idling\r\n')
        elif b'DONE' in command:
            self.idle_active = False
            # Simulate DONE response
            self.responses.put(b'A0001 OK IDLE terminated\r\n')
    
    def readline(self):
        """Mock readline for responses"""
        if self.should_fail:
            raise Exception("Mock readline failure")
        
        try:
            return self.responses.get(timeout=0.1)
        except Empty:
            return b''
    
    def simulate_new_email(self):
        """Simulate new email arrival"""
        if self.idle_active:
            self.responses.put(b'* 5 EXISTS\r\n')
    
    def simulate_email_deleted(self):
        """Simulate email deletion"""
        if self.idle_active:
            self.responses.put(b'* 3 EXPUNGE\r\n')
    
    def simulate_connection_close(self):
        """Simulate server closing connection"""
        if self.idle_active:
            self.responses.put(b'* BYE Server shutting down\r\n')


class MockGoDaddyClient:
    """Mock GoDaddy email client for testing"""
    
    def __init__(self, idle_supported=True, should_fail=False):
        self.imap = MockIMAPConnection(idle_supported, should_fail)
        self.idle_supported = idle_supported
        self.should_fail = should_fail
        
    def test_idle_support(self):
        """Mock IDLE support test"""
        if self.should_fail:
            raise Exception("Mock test failure")
        return self.idle_supported
    
    def get_connection_health(self):
        """Mock connection health"""
        health_mock = Mock()
        if self.should_fail:
            health_mock.status.value = 'unhealthy'
        else:
            health_mock.status.value = 'healthy'
        return health_mock


class MockConnectionPool:
    """Mock connection pool for testing"""
    
    def __init__(self, idle_supported=True, should_fail=False):
        self.idle_supported = idle_supported
        self.should_fail = should_fail
        self.connections_given = 0
        self.connections_returned = 0
        
    def get_connection(self):
        """Mock get connection"""
        if self.should_fail:
            raise Exception("Mock pool failure")
        
        self.connections_given += 1
        
        # Create mock pooled connection
        pooled_conn = Mock(spec=PooledConnection)
        pooled_conn.connection = MockGoDaddyClient(self.idle_supported, self.should_fail)
        
        return pooled_conn
    
    def return_connection(self, connection):
        """Mock return connection"""
        self.connections_returned += 1


@pytest.fixture
def mock_connection_pool():
    """Fixture for mock connection pool"""
    return MockConnectionPool()


@pytest.fixture
def mock_failing_connection_pool():
    """Fixture for mock failing connection pool"""
    return MockConnectionPool(should_fail=True)


@pytest.fixture
def mock_no_idle_connection_pool():
    """Fixture for mock connection pool without IDLE support"""
    return MockConnectionPool(idle_supported=False)


@pytest.fixture
def idle_controller(mock_connection_pool):
    """Fixture for IDLE controller with mock dependencies"""
    controller = IMAPIdleController(
        connection_pool=mock_connection_pool,
        default_timeout=60,  # Short timeout for testing
        renewal_buffer=10,
        max_concurrent_sessions=3
    )
    yield controller
    controller.shutdown()


class TestIMAPIdleController:
    """Test suite for IMAP IDLE Controller"""
    
    def test_controller_initialization(self, mock_connection_pool):
        """Test controller initialization"""
        controller = IMAPIdleController(
            connection_pool=mock_connection_pool,
            default_timeout=1800,
            renewal_buffer=60,
            max_concurrent_sessions=5
        )
        
        assert controller.connection_pool == mock_connection_pool
        assert controller.default_timeout == 1800
        assert controller.renewal_buffer == 60
        assert controller.max_concurrent_sessions == 5
        assert len(controller._active_sessions) == 0
        
        # Check background threads are started
        assert controller._event_processor_thread is not None
        assert controller._session_monitor_thread is not None
        assert controller._event_processor_thread.is_alive()
        assert controller._session_monitor_thread.is_alive()
        
        controller.shutdown()
    
    def test_start_idle_session_success(self, idle_controller):
        """Test successful IDLE session start"""
        # Mock fallback callback
        fallback_called = []
        def fallback_callback(account_id):
            fallback_called.append(account_id)
        
        idle_controller.fallback_callback = fallback_callback
        
        # Start session
        session = idle_controller.start_idle_session("test_account", "INBOX")
        
        assert session is not None
        assert session.account_id == "test_account"
        assert session.mailbox == "INBOX"
        assert session.state in [IdleSessionState.STARTING, IdleSessionState.ACTIVE]
        
        # Wait for session to become active
        time.sleep(0.5)
        
        # Check session is tracked
        active_sessions = idle_controller.get_active_sessions()
        assert len(active_sessions) == 1
        assert active_sessions[0].account_id == "test_account"
        
        # Check no fallback was triggered
        assert len(fallback_called) == 0
        
        # Check metrics
        metrics = idle_controller.get_metrics()
        assert metrics.total_sessions == 1
        assert metrics.active_sessions == 1
    
    def test_start_idle_session_no_idle_support(self, mock_no_idle_connection_pool):
        """Test IDLE session start when IDLE is not supported"""
        fallback_called = []
        def fallback_callback(account_id):
            fallback_called.append(account_id)
        
        controller = IMAPIdleController(
            connection_pool=mock_no_idle_connection_pool,
            fallback_callback=fallback_callback
        )
        
        try:
            # Should raise exception and trigger fallback
            with pytest.raises(Exception, match="IDLE not supported"):
                controller.start_idle_session("test_account", "INBOX")
            
            # Check fallback was called
            assert len(fallback_called) == 1
            assert fallback_called[0] == "test_account"
            
            # Check metrics
            metrics = controller.get_metrics()
            assert metrics.fallback_to_polling_count == 1
            
        finally:
            controller.shutdown()
    
    def test_start_idle_session_connection_failure(self, mock_failing_connection_pool):
        """Test IDLE session start with connection failure"""
        fallback_called = []
        def fallback_callback(account_id):
            fallback_called.append(account_id)
        
        controller = IMAPIdleController(
            connection_pool=mock_failing_connection_pool,
            fallback_callback=fallback_callback
        )
        
        try:
            # Should raise exception and trigger fallback
            with pytest.raises(Exception):
                controller.start_idle_session("test_account", "INBOX")
            
            # Check fallback was called
            assert len(fallback_called) == 1
            assert fallback_called[0] == "test_account"
            
        finally:
            controller.shutdown()
    
    def test_concurrent_session_limit(self, idle_controller):
        """Test concurrent session limit enforcement"""
        # Start maximum allowed sessions
        sessions = []
        for i in range(idle_controller.max_concurrent_sessions):
            session = idle_controller.start_idle_session(f"account_{i}", "INBOX")
            sessions.append(session)
        
        # Try to start one more session - should fail
        with pytest.raises(Exception, match="Maximum concurrent IDLE sessions"):
            idle_controller.start_idle_session("overflow_account", "INBOX")
        
        # Check correct number of active sessions
        active_sessions = idle_controller.get_active_sessions()
        assert len(active_sessions) == idle_controller.max_concurrent_sessions
    
    def test_duplicate_session_handling(self, idle_controller):
        """Test handling of duplicate session requests"""
        # Start first session
        session1 = idle_controller.start_idle_session("test_account", "INBOX")
        
        # Try to start duplicate session
        session2 = idle_controller.start_idle_session("test_account", "INBOX")
        
        # Should return the same session
        assert session1.session_id == session2.session_id
        
        # Should still have only one active session
        active_sessions = idle_controller.get_active_sessions()
        assert len(active_sessions) == 1
    
    def test_idle_event_processing(self, idle_controller):
        """Test IDLE event processing"""
        events_received = []
        
        def event_callback(event):
            events_received.append(event)
        
        idle_controller.add_event_callback(event_callback)
        
        # Start session
        session = idle_controller.start_idle_session("test_account", "INBOX")
        time.sleep(0.5)  # Wait for session to become active
        
        # Get the mock IMAP connection
        pooled_conn = idle_controller.connection_pool.get_connection()
        mock_imap = pooled_conn.connection.imap
        
        # Simulate new email event
        mock_imap.simulate_new_email()
        
        # Wait for event processing
        time.sleep(0.5)
        
        # Check event was processed
        assert len(events_received) >= 1
        new_email_events = [e for e in events_received if e.event_type == IdleEventType.NEW_EMAIL]
        assert len(new_email_events) >= 1
        
        event = new_email_events[0]
        assert event.account_id == "test_account"
        assert event.mailbox == "INBOX"
        assert event.metadata.get('email_count') == '5'
    
    def test_session_renewal(self, idle_controller):
        """Test IDLE session renewal"""
        session_states = []
        
        def session_callback(session, state):
            session_states.append((session.session_id, state))
        
        idle_controller.add_session_callback(session_callback)
        
        # Start session with very short timeout for testing
        session = idle_controller.start_idle_session("test_account", "INBOX")
        session.timeout_seconds = 5  # 5 seconds for testing
        idle_controller.renewal_buffer = 2  # Renew after 3 seconds
        
        # Wait for renewal to occur
        time.sleep(4)
        
        # Check that renewal occurred
        renewal_states = [state for _, state in session_states if state == IdleSessionState.RENEWING]
        assert len(renewal_states) >= 1
        
        # Check session is still active
        assert session.renewal_count >= 1
        assert session.state == IdleSessionState.ACTIVE
    
    def test_session_timeout_handling(self, idle_controller):
        """Test IDLE session timeout handling"""
        # Start session
        session = idle_controller.start_idle_session("test_account", "INBOX")
        
        # Manually trigger timeout condition
        session.last_renewal = datetime.now() - timedelta(seconds=session.timeout_seconds + 10)
        
        # Wait for timeout handling
        time.sleep(1)
        
        # Session should be renewed or terminated
        assert session.renewal_count >= 1 or session.state == IdleSessionState.TERMINATED
    
    def test_stop_idle_session(self, idle_controller):
        """Test stopping an IDLE session"""
        # Start session
        session = idle_controller.start_idle_session("test_account", "INBOX")
        time.sleep(0.5)
        
        # Stop session
        result = idle_controller.stop_idle_session("test_account", "INBOX")
        assert result is True
        
        # Check session state
        assert session.state == IdleSessionState.TERMINATED
        
        # Try to stop non-existent session
        result = idle_controller.stop_idle_session("nonexistent", "INBOX")
        assert result is False
    
    def test_get_session_by_account(self, idle_controller):
        """Test getting session by account"""
        # Start session
        session = idle_controller.start_idle_session("test_account", "INBOX")
        
        # Get session by account
        retrieved_session = idle_controller.get_session_by_account("test_account", "INBOX")
        assert retrieved_session is not None
        assert retrieved_session.session_id == session.session_id
        
        # Try to get non-existent session
        no_session = idle_controller.get_session_by_account("nonexistent", "INBOX")
        assert no_session is None
    
    def test_metrics_collection(self, idle_controller):
        """Test metrics collection"""
        # Start multiple sessions
        for i in range(2):
            idle_controller.start_idle_session(f"account_{i}", "INBOX")
        
        time.sleep(0.5)
        
        # Get metrics
        metrics = idle_controller.get_metrics()
        
        assert metrics.total_sessions == 2
        assert metrics.active_sessions == 2
        assert isinstance(metrics.last_updated, datetime)
    
    def test_event_callbacks(self, idle_controller):
        """Test event callback functionality"""
        callback1_events = []
        callback2_events = []
        
        def callback1(event):
            callback1_events.append(event)
        
        def callback2(event):
            callback2_events.append(event)
        
        # Add callbacks
        idle_controller.add_event_callback(callback1)
        idle_controller.add_event_callback(callback2)
        
        # Create and queue test event
        test_event = IdleEvent(
            event_type=IdleEventType.NEW_EMAIL,
            account_id="test_account",
            mailbox="INBOX",
            timestamp=datetime.now()
        )
        
        idle_controller._queue_event(test_event)
        
        # Wait for processing
        time.sleep(0.5)
        
        # Check both callbacks received the event
        assert len(callback1_events) == 1
        assert len(callback2_events) == 1
        assert callback1_events[0].event_type == IdleEventType.NEW_EMAIL
        assert callback2_events[0].event_type == IdleEventType.NEW_EMAIL
    
    def test_session_callbacks(self, idle_controller):
        """Test session callback functionality"""
        session_changes = []
        
        def session_callback(session, state):
            session_changes.append((session.account_id, state))
        
        idle_controller.add_session_callback(session_callback)
        
        # Start session
        session = idle_controller.start_idle_session("test_account", "INBOX")
        
        # Wait for state changes
        time.sleep(0.5)
        
        # Check callbacks were called
        assert len(session_changes) >= 1
        
        # Should have at least STARTING state
        starting_changes = [change for change in session_changes if change[1] == IdleSessionState.STARTING]
        assert len(starting_changes) >= 1
        assert starting_changes[0][0] == "test_account"
    
    def test_connection_pool_integration(self, idle_controller):
        """Test integration with connection pool"""
        # Start session
        session = idle_controller.start_idle_session("test_account", "INBOX")
        time.sleep(0.5)
        
        # Check connection was obtained from pool
        assert idle_controller.connection_pool.connections_given >= 1
        
        # Stop session
        idle_controller.stop_idle_session("test_account", "INBOX")
        time.sleep(0.5)
        
        # Check connection was returned to pool
        assert idle_controller.connection_pool.connections_returned >= 1
    
    def test_graceful_shutdown(self, idle_controller):
        """Test graceful shutdown"""
        # Start multiple sessions
        sessions = []
        for i in range(2):
            session = idle_controller.start_idle_session(f"account_{i}", "INBOX")
            sessions.append(session)
        
        time.sleep(0.5)
        
        # Shutdown controller
        idle_controller.shutdown()
        
        # Check all sessions are terminated
        for session in sessions:
            assert session.state == IdleSessionState.TERMINATED
        
        # Check background threads are stopped
        assert not idle_controller._event_processor_thread.is_alive()
        assert not idle_controller._session_monitor_thread.is_alive()
    
    def test_error_handling_in_session_worker(self, idle_controller):
        """Test error handling in session worker"""
        fallback_called = []
        
        def fallback_callback(account_id):
            fallback_called.append(account_id)
        
        idle_controller.fallback_callback = fallback_callback
        
        # Create a connection that will fail during session
        mock_pool = Mock()
        failing_connection = Mock()
        failing_connection.connection.imap.select.side_effect = Exception("Mock failure")
        failing_connection.connection.test_idle_support.return_value = True
        
        mock_pool.get_connection.return_value = failing_connection
        mock_pool.return_connection = Mock()
        
        controller = IMAPIdleController(connection_pool=mock_pool)
        
        try:
            # Start session - should fail during worker execution
            session = controller.start_idle_session("test_account", "INBOX")
            
            # Wait for failure
            time.sleep(1)
            
            # Session should be in failed state
            assert session.state == IdleSessionState.FAILED
            
        finally:
            controller.shutdown()
    
    def test_context_manager(self, mock_connection_pool):
        """Test context manager functionality"""
        with IMAPIdleController(connection_pool=mock_connection_pool) as controller:
            # Start session
            session = controller.start_idle_session("test_account", "INBOX")
            assert session is not None
            
            # Controller should be active
            assert not controller._shutdown_event.is_set()
        
        # After context exit, controller should be shutdown
        assert controller._shutdown_event.is_set()


class TestIdleEventTypes:
    """Test different IDLE event types"""
    
    def test_new_email_event_parsing(self):
        """Test parsing of new email IDLE events"""
        controller = IMAPIdleController(connection_pool=MockConnectionPool())
        
        try:
            # Create mock session
            session = Mock()
            session.account_id = "test_account"
            session.mailbox = "INBOX"
            session.event_count = 0
            session.last_event = None
            
            # Test new email response
            controller._handle_new_email_event(session, "* 5 EXISTS")
            
            # Check event was queued
            assert not controller._event_queue.empty()
            
            event = controller._event_queue.get()
            assert event.event_type == IdleEventType.NEW_EMAIL
            assert event.account_id == "test_account"
            assert event.mailbox == "INBOX"
            assert event.metadata['email_count'] == '5'
            
        finally:
            controller.shutdown()
    
    def test_email_deleted_event_parsing(self):
        """Test parsing of email deleted IDLE events"""
        controller = IMAPIdleController(connection_pool=MockConnectionPool())
        
        try:
            # Create mock session
            session = Mock()
            session.account_id = "test_account"
            session.mailbox = "INBOX"
            session.event_count = 0
            session.last_event = None
            
            # Test email deleted response
            controller._handle_email_deleted_event(session, "* 3 EXPUNGE")
            
            # Check event was queued
            assert not controller._event_queue.empty()
            
            event = controller._event_queue.get()
            assert event.event_type == IdleEventType.EMAIL_DELETED
            assert event.account_id == "test_account"
            assert event.mailbox == "INBOX"
            assert event.metadata['sequence_number'] == '3'
            
        finally:
            controller.shutdown()
    
    def test_email_flagged_event_parsing(self):
        """Test parsing of email flagged IDLE events"""
        controller = IMAPIdleController(connection_pool=MockConnectionPool())
        
        try:
            # Create mock session
            session = Mock()
            session.account_id = "test_account"
            session.mailbox = "INBOX"
            session.event_count = 0
            session.last_event = None
            
            # Test email flagged response
            controller._handle_email_flagged_event(session, "* 2 FETCH (FLAGS (\\Seen))")
            
            # Check event was queued
            assert not controller._event_queue.empty()
            
            event = controller._event_queue.get()
            assert event.event_type == IdleEventType.EMAIL_FLAGGED
            assert event.account_id == "test_account"
            assert event.mailbox == "INBOX"
            
        finally:
            controller.shutdown()


class TestIdleSessionManagement:
    """Test IDLE session management functionality"""
    
    def test_session_health_checking(self):
        """Test session health checking"""
        controller = IMAPIdleController(connection_pool=MockConnectionPool())
        
        try:
            # Create mock session with healthy connection
            session = Mock()
            session.connection.connection.get_connection_health.return_value.status.value = 'healthy'
            session.last_event = datetime.now() - timedelta(minutes=30)
            
            # Health check should pass
            assert controller._check_session_health(session) is True
            
            # Create session with unhealthy connection
            session.connection.connection.get_connection_health.return_value.status.value = 'unhealthy'
            
            # Health check should fail
            assert controller._check_session_health(session) is False
            
        finally:
            controller.shutdown()
    
    def test_session_renewal_logic(self):
        """Test session renewal logic"""
        controller = IMAPIdleController(connection_pool=MockConnectionPool())
        
        try:
            # Create session that needs renewal
            session = Mock()
            session.state = IdleSessionState.ACTIVE
            session.last_renewal = datetime.now() - timedelta(seconds=1800)  # 30 minutes ago
            session.timeout_seconds = 1740  # 29 minutes
            session.renewal_count = 5
            session.max_renewals = 100
            
            # Should need renewal
            assert controller._should_renew_session(session) is True
            
            # Create session that doesn't need renewal
            session.last_renewal = datetime.now() - timedelta(seconds=300)  # 5 minutes ago
            
            # Should not need renewal
            assert controller._should_renew_session(session) is False
            
            # Create session that reached max renewals
            session.renewal_count = 100
            session.max_renewals = 100
            session.last_renewal = datetime.now() - timedelta(seconds=1800)
            
            # Should not renew due to max renewals
            assert controller._should_renew_session(session) is False
            
        finally:
            controller.shutdown()
    
    def test_session_cleanup(self):
        """Test session cleanup"""
        mock_pool = MockConnectionPool()
        controller = IMAPIdleController(connection_pool=mock_pool)
        
        try:
            # Create mock session
            session = Mock()
            session.session_id = "test_session"
            session.state = IdleSessionState.ACTIVE
            session.started_at = datetime.now() - timedelta(minutes=10)
            session.connection.connection.imap.send = Mock()
            
            # Add session to active sessions
            session_key = "test_account_INBOX"
            controller._active_sessions[session_key] = session
            controller._session_threads[session_key] = Mock()
            controller._metrics.active_sessions = 1
            
            # Cleanup session
            controller._cleanup_idle_session(session, session_key)
            
            # Check session was cleaned up
            assert session_key not in controller._active_sessions
            assert session_key not in controller._session_threads
            assert controller._metrics.active_sessions == 0
            assert session.state == IdleSessionState.TERMINATED
            
            # Check connection was returned to pool
            assert mock_pool.connections_returned == 1
            
        finally:
            controller.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])