# src/email/enhanced_godaddy_client.py
import logging
import time
from typing import List, Optional, Dict, Any, Callable
from email.message import EmailMessage
from datetime import datetime, timedelta

from .godaddy_client import GoDaddyEmailClient, ConnectionHealth, ConnectionHealthStatus
from .reconnection_manager import (
    IntelligentReconnectionManager,
    ConnectionState,
    ReconnectionConfig,
    FallbackMechanism,
    ConnectionFailure
)


class EnhancedGoDaddyEmailClient:
    """
    Enhanced GoDaddy email client with intelligent reconnection,
    automatic failure recovery, and connection state persistence.
    """
    
    def __init__(self, 
                 account_config: Dict[str, Any],
                 reconnection_config: Optional[ReconnectionConfig] = None,
                 fallback_config: Optional[FallbackMechanism] = None,
                 auto_reconnect: bool = True):
        
        self.account_config = account_config
        self.auto_reconnect = auto_reconnect
        
        # Initialize reconnection manager
        self.reconnection_manager = IntelligentReconnectionManager(
            account_config=account_config,
            reconnection_config=reconnection_config,
            fallback_config=fallback_config
        )
        
        # Connection event callbacks
        self.reconnection_manager.add_connection_callback(self._on_connection_state_change)
        self.reconnection_manager.add_failure_callback(self._on_connection_failure)
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Operation retry configuration
        self.max_operation_retries = 3
        self.operation_retry_delay = 1.0
        
        # Connection establishment
        if self.auto_reconnect:
            self._establish_initial_connection()

    def _establish_initial_connection(self) -> None:
        """Establish initial connection with retry logic"""
        try:
            success = self.reconnection_manager.connect()
            if success:
                self.logger.info("Initial connection established successfully")
            else:
                self.logger.warning("Initial connection failed, will retry automatically")
        except Exception as e:
            self.logger.error(f"Failed to establish initial connection: {e}")

    def _on_connection_state_change(self, state: ConnectionState, error: Optional[Exception]) -> None:
        """Handle connection state changes"""
        if state == ConnectionState.CONNECTED:
            self.logger.info("Connection established")
        elif state == ConnectionState.DISCONNECTED:
            self.logger.info("Connection disconnected")
        elif state == ConnectionState.FAILED:
            self.logger.warning(f"Connection failed: {error}")
        elif state == ConnectionState.RECONNECTING:
            self.logger.info("Attempting to reconnect...")
        elif state == ConnectionState.SUSPENDED:
            self.logger.error("Connection suspended after maximum retry attempts")

    def _on_connection_failure(self, failure: ConnectionFailure) -> None:
        """Handle connection failures"""
        self.logger.error(f"Connection failure: {failure.failure_type.value} - {failure.error_message}")
        if failure.is_persistent:
            self.logger.critical("Persistent connection failure detected")

    def _ensure_connection(self) -> GoDaddyEmailClient:
        """Ensure we have a healthy connection, reconnecting if necessary"""
        connection = self.reconnection_manager.get_connection()
        
        if connection is None:
            if self.auto_reconnect:
                self.logger.info("No healthy connection available, attempting to reconnect")
                success = self.reconnection_manager.connect()
                if success:
                    connection = self.reconnection_manager.get_connection()
                
                if connection is None:
                    raise Exception("Unable to establish connection to email server")
            else:
                raise Exception("No connection available and auto-reconnect is disabled")
        
        return connection

    def _execute_with_retry(self, operation: Callable, operation_name: str, *args, **kwargs):
        """Execute an operation with automatic retry on connection failures"""
        last_exception = None
        
        for attempt in range(self.max_operation_retries):
            try:
                # Ensure we have a connection
                connection = self._ensure_connection()
                
                # Execute the operation
                return operation(connection, *args, **kwargs)
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"{operation_name} failed (attempt {attempt + 1}): {e}")
                
                # Check if this is a connection-related error
                if self._is_connection_error(e):
                    # Force reconnection for connection errors
                    self.logger.info("Connection error detected, forcing reconnection")
                    self.reconnection_manager.force_reconnect()
                    
                    if attempt < self.max_operation_retries - 1:
                        time.sleep(self.operation_retry_delay * (attempt + 1))
                        continue
                else:
                    # Non-connection error, don't retry
                    break
        
        # All retries exhausted
        raise last_exception

    def _is_connection_error(self, error: Exception) -> bool:
        """Determine if an error is connection-related"""
        error_str = str(error).lower()
        connection_indicators = [
            'connection', 'network', 'timeout', 'unreachable',
            'broken pipe', 'connection reset', 'socket error'
        ]
        
        return any(indicator in error_str for indicator in connection_indicators)

    # Email operations with automatic reconnection

    def connect(self) -> None:
        """Establish connection to the email server"""
        success = self.reconnection_manager.connect()
        if not success:
            raise Exception("Failed to connect to email server")

    def fetch_unread_emails(self) -> List[EmailMessage]:
        """Fetch unread emails with automatic reconnection"""
        def _fetch_operation(connection: GoDaddyEmailClient) -> List[EmailMessage]:
            return connection.fetch_unread_emails()
        
        return self._execute_with_retry(_fetch_operation, "fetch_unread_emails")

    def list_inbox(self) -> List[dict]:
        """List all emails with automatic reconnection"""
        def _list_operation(connection: GoDaddyEmailClient) -> List[dict]:
            return connection.list_inbox()
        
        return self._execute_with_retry(_list_operation, "list_inbox")

    def send_email(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> None:
        """Send an email with automatic reconnection"""
        def _send_operation(connection: GoDaddyEmailClient, to: str, subject: str, body: str, attachments: Optional[List[str]]) -> None:
            return connection.send_email(to, subject, body, attachments)
        
        return self._execute_with_retry(_send_operation, "send_email", to, subject, body, attachments)

    def send_templated_response(self, to: str, template: str, **kwargs) -> None:
        """Send a templated email with automatic reconnection"""
        def _send_templated_operation(connection: GoDaddyEmailClient, to: str, template: str, **kwargs) -> None:
            return connection.send_templated_response(to, template, **kwargs)
        
        return self._execute_with_retry(_send_templated_operation, "send_templated_response", to, template, **kwargs)

    def extract_pdf_attachments(self, email_msg: EmailMessage, output_dir: str = "attachments") -> List[str]:
        """Extract PDF attachments with automatic reconnection"""
        def _extract_operation(connection: GoDaddyEmailClient, email_msg: EmailMessage, output_dir: str) -> List[str]:
            return connection.extract_pdf_attachments(email_msg, output_dir)
        
        return self._execute_with_retry(_extract_operation, "extract_pdf_attachments", email_msg, output_dir)

    # Connection management and monitoring

    def get_connection_state(self) -> ConnectionState:
        """Get the current connection state"""
        return self.reconnection_manager.get_connection_state()

    def get_connection_health(self) -> Optional[ConnectionHealthStatus]:
        """Get connection health status"""
        connection = self.reconnection_manager.get_connection()
        if connection:
            return connection.get_connection_health()
        return None

    def get_connection_metrics(self):
        """Get connection performance metrics"""
        return self.reconnection_manager.get_connection_metrics()

    def get_failure_history(self):
        """Get connection failure history"""
        return self.reconnection_manager.get_failure_history()

    def force_reconnect(self) -> bool:
        """Force a reconnection attempt"""
        return self.reconnection_manager.force_reconnect()

    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self.get_connection_state() == ConnectionState.CONNECTED

    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        health = self.get_connection_health()
        if health:
            return health.status in [ConnectionHealth.HEALTHY, ConnectionHealth.DEGRADED]
        return False

    # Server capability detection (delegated to underlying client)

    def get_server_capabilities(self):
        """Get server capabilities"""
        connection = self._ensure_connection()
        return connection.get_server_capabilities()

    def test_idle_support(self) -> bool:
        """Test IMAP IDLE support"""
        connection = self._ensure_connection()
        return connection.test_idle_support()

    def get_rate_limit_info(self):
        """Get rate limiting information"""
        connection = self._ensure_connection()
        return connection.get_rate_limit_info()

    # Configuration and management

    def update_account_config(self, new_config: Dict[str, Any]) -> None:
        """Update account configuration"""
        self.account_config.update(new_config)
        # Force reconnection to apply new configuration
        self.force_reconnect()

    def enable_auto_reconnect(self) -> None:
        """Enable automatic reconnection"""
        self.auto_reconnect = True

    def disable_auto_reconnect(self) -> None:
        """Disable automatic reconnection"""
        self.auto_reconnect = False

    def set_operation_retry_config(self, max_retries: int, retry_delay: float) -> None:
        """Configure operation retry behavior"""
        self.max_operation_retries = max_retries
        self.operation_retry_delay = retry_delay

    # Cleanup and shutdown

    def close(self) -> None:
        """Close the connection and shutdown reconnection manager"""
        self.logger.info("Shutting down enhanced email client")
        self.reconnection_manager.shutdown()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    # Advanced connection recovery methods

    def wait_for_connection(self, timeout: float = 30.0) -> bool:
        """Wait for connection to be established"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_connected():
                return True
            time.sleep(0.1)
        
        return False

    def get_uptime_stats(self) -> Dict[str, Any]:
        """Get connection uptime statistics"""
        metrics = self.get_connection_metrics()
        
        return {
            'uptime_percentage': metrics.uptime_percentage,
            'current_uptime': metrics.current_uptime,
            'total_connections': metrics.total_connections,
            'successful_connections': metrics.successful_connections,
            'failed_connections': metrics.failed_connections,
            'last_successful_connection': metrics.last_successful_connection,
            'last_failure': metrics.last_failure
        }

    def reset_failure_counters(self) -> None:
        """Reset failure counters (useful for testing or manual recovery)"""
        self.reconnection_manager._consecutive_failures = 0
        self.reconnection_manager._current_failure = None
        self.logger.info("Failure counters reset")

    def add_connection_callback(self, callback: Callable[[ConnectionState, Optional[Exception]], None]) -> None:
        """Add callback for connection state changes"""
        self.reconnection_manager.add_connection_callback(callback)

    def add_failure_callback(self, callback: Callable[[ConnectionFailure], None]) -> None:
        """Add callback for connection failures"""
        self.reconnection_manager.add_failure_callback(callback)

    # Health monitoring and diagnostics

    def perform_connection_test(self) -> Dict[str, Any]:
        """Perform comprehensive connection test"""
        test_results = {
            'timestamp': datetime.now(),
            'connection_state': self.get_connection_state().value,
            'is_connected': self.is_connected(),
            'is_healthy': self.is_healthy(),
            'connection_health': None,
            'server_capabilities': None,
            'rate_limit_info': None,
            'test_operations': {}
        }
        
        try:
            # Get connection health
            health = self.get_connection_health()
            if health:
                test_results['connection_health'] = {
                    'status': health.status.value,
                    'response_time_ms': health.response_time_ms,
                    'error_count': health.error_count,
                    'uptime_percentage': health.uptime_percentage
                }
            
            # Test basic operations
            if self.is_connected():
                try:
                    # Test server capabilities
                    capabilities = self.get_server_capabilities()
                    test_results['server_capabilities'] = {
                        'idle_supported': capabilities.idle_supported,
                        'extensions_count': len(capabilities.supported_extensions)
                    }
                except Exception as e:
                    test_results['test_operations']['capabilities_error'] = str(e)
                
                try:
                    # Test rate limit info
                    rate_info = self.get_rate_limit_info()
                    test_results['rate_limit_info'] = {
                        'is_rate_limited': rate_info.is_rate_limited,
                        'requests_per_minute': rate_info.requests_per_minute
                    }
                except Exception as e:
                    test_results['test_operations']['rate_limit_error'] = str(e)
                
                try:
                    # Test inbox listing (lightweight operation)
                    start_time = time.time()
                    inbox_count = len(self.list_inbox())
                    operation_time = time.time() - start_time
                    
                    test_results['test_operations']['list_inbox'] = {
                        'success': True,
                        'email_count': inbox_count,
                        'operation_time_ms': operation_time * 1000
                    }
                except Exception as e:
                    test_results['test_operations']['list_inbox'] = {
                        'success': False,
                        'error': str(e)
                    }
        
        except Exception as e:
            test_results['test_error'] = str(e)
        
        return test_results