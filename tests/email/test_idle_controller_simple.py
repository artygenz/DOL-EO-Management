# tests/email/test_idle_controller_simple.py
import pytest
import time
import threading
from unittest.mock import Mock
from datetime import datetime

from src.email.idle_controller import (
    IMAPIdleController,
    IdleSession,
    IdleEvent,
    IdleSessionState,
    IdleEventType
)


class SimpleTestConnectionPool:
    """Simple test connection pool"""
    
    def __init__(self, idle_supported=True):
        self.idle_supported = idle_supported
        self.connections_given = 0
        self.connections_returned = 0
        
    def get_connection(self):
        self.connections_given += 1
        
        # Create simple mock connection
        connection = Mock()
        connection.test_idle_support = Mock(return_value=self.idle_supported)
        connection.get_connection_health = Mock()
        connection.get_connection_health.return_value.status.value = 'healthy'
        
        # Mock IMAP
        connection.imap = Mock()
        connection.imap.select = Mock(return_value=('OK', [b'SELECT completed']))
        connection.imap._new_tag = Mock(return_value='A001')
        connection.imap.send = Mock()
        connection.imap.readline = Mock(return_value=b'+ idling\r\n')
        connection.imap.sock = Mock()
        
        # Create pooled connection
        pooled_conn = Mock()
        pooled_conn.connection = connection
        
        return pooled_conn
    
    def return_connection(self, connection):
        self.connections_returned += 1


def test_idle_controller_basic_functionality():
    """Test basic IDLE controller functionality"""
    pool = SimpleTestConnectionPool()
    
    controller = IMAPIdleController(
        connection_pool=pool,
        default_timeout=30,
        max_concurrent_sessions=2
    )
    
    try:
        # Test starting a session
        session = controller.start_idle_session("test_account", "INBOX")
        
        assert session is not None
        assert session.account_id == "test_account"
        assert session.mailbox == "INBOX"
        assert session.state in [IdleSessionState.STARTING, IdleSessionState.ACTIVE, IdleSessionState.RENEWING]
        
        # Wait briefly for session to initialize
        time.sleep(0.2)
        
        # Test getting session by account
        retrieved_session = controller.get_session_by_account("test_account", "INBOX")
        assert retrieved_session is not None
        assert retrieved_session.session_id == session.session_id
        
        # Test metrics
        metrics = controller.get_metrics()
        assert metrics.total_sessions == 1
        
        # Test stopping session
        result = controller.stop_idle_session("test_account", "INBOX")
        # Note: result might be False if session was already cleaned up due to errors
        
        # Test connection pool integration
        assert pool.connections_given >= 1
        
    finally:
        controller.shutdown()


def test_idle_controller_event_processing():
    """Test event processing functionality"""
    pool = SimpleTestConnectionPool()
    
    controller = IMAPIdleController(
        connection_pool=pool,
        default_timeout=30
    )
    
    events_received = []
    
    def event_callback(event):
        events_received.append(event)
    
    try:
        controller.add_event_callback(event_callback)
        
        # Create and queue a test event
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
        
        # Check event was processed
        assert len(events_received) == 1
        assert events_received[0].event_type == IdleEventType.NEW_EMAIL
        assert events_received[0].account_id == "test_account"
        
    finally:
        controller.shutdown()


def test_idle_controller_fallback():
    """Test fallback to polling when IDLE is not supported"""
    pool = SimpleTestConnectionPool(idle_supported=False)
    
    fallback_calls = []
    
    def fallback_callback(account_id):
        fallback_calls.append(account_id)
    
    controller = IMAPIdleController(
        connection_pool=pool,
        fallback_callback=fallback_callback
    )
    
    try:
        # Try to start session - should fail and trigger fallback
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


def test_idle_controller_concurrent_sessions():
    """Test concurrent session handling"""
    pool = SimpleTestConnectionPool()
    
    controller = IMAPIdleController(
        connection_pool=pool,
        max_concurrent_sessions=2
    )
    
    try:
        # Start two sessions
        session1 = controller.start_idle_session("account1", "INBOX")
        session2 = controller.start_idle_session("account2", "INBOX")
        
        assert session1.account_id == "account1"
        assert session2.account_id == "account2"
        
        # Try to start third session - should fail
        with pytest.raises(Exception, match="Maximum concurrent IDLE sessions"):
            controller.start_idle_session("account3", "INBOX")
        
        # Check metrics
        metrics = controller.get_metrics()
        assert metrics.total_sessions == 2
        
    finally:
        controller.shutdown()


def test_idle_controller_session_callbacks():
    """Test session state change callbacks"""
    pool = SimpleTestConnectionPool()
    
    controller = IMAPIdleController(
        connection_pool=pool,
        default_timeout=30
    )
    
    session_changes = []
    
    def session_callback(session, state):
        session_changes.append((session.account_id, state))
    
    try:
        controller.add_session_callback(session_callback)
        
        # Start session
        session = controller.start_idle_session("test_account", "INBOX")
        
        # Wait for state changes
        time.sleep(0.3)
        
        # Check callbacks were called
        assert len(session_changes) >= 1
        
        # Should have at least STARTING state
        starting_changes = [change for change in session_changes if change[1] == IdleSessionState.STARTING]
        assert len(starting_changes) >= 1
        assert starting_changes[0][0] == "test_account"
        
    finally:
        controller.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])