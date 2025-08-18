# src/email/reconnection_manager.py
import asyncio
import threading
import time
import logging
import random
import json
import os
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
import pickle

from .godaddy_client import GoDaddyEmailClient, ConnectionHealth, ConnectionHealthStatus


class ConnectionState(Enum):
    """Connection state enumeration"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    SUSPENDED = "suspended"


class FailureType(Enum):
    """Types of connection failures"""
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SERVER_ERROR = "server_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ConnectionFailure:
    """Information about a connection failure"""
    failure_type: FailureType
    timestamp: datetime
    error_message: str
    retry_count: int = 0
    backoff_duration: float = 0.0
    is_persistent: bool = False


@dataclass
class ReconnectionConfig:
    """Configuration for reconnection behavior"""
    initial_backoff: float = 1.0  # Initial backoff in seconds
    max_backoff: float = 300.0    # Maximum backoff in seconds (5 minutes)
    backoff_multiplier: float = 2.0  # Exponential backoff multiplier
    jitter_factor: float = 0.1    # Jitter factor (0.0 to 1.0)
    max_retry_attempts: int = 10  # Maximum retry attempts before giving up
    persistent_failure_threshold: int = 5  # Failures before marking as persistent
    health_check_interval: float = 30.0  # Health check interval in seconds
    state_persistence_path: str = "connection_state.json"  # Path for state persistence


@dataclass
class ConnectionMetrics:
    """Metrics for connection performance and reliability"""
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    reconnection_attempts: int = 0
    successful_reconnections: int = 0
    average_connection_time: float = 0.0
    uptime_percentage: float = 100.0
    last_successful_connection: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    current_uptime: timedelta = field(default_factory=lambda: timedelta(0))


@dataclass
class FallbackMechanism:
    """Configuration for fallback mechanisms"""
    enabled: bool = True
    fallback_servers: List[Dict[str, Any]] = field(default_factory=list)
    fallback_timeout: float = 60.0  # Time to wait before trying fallback
    max_fallback_attempts: int = 3
    fallback_health_check: bool = True


class IntelligentReconnectionManager:
    """
    Intelligent reconnection manager with exponential backoff, jitter,
    connection state persistence, and fallback mechanisms.
    """
    
    def __init__(self, 
                 account_config: Dict[str, Any],
                 reconnection_config: Optional[ReconnectionConfig] = None,
                 fallback_config: Optional[FallbackMechanism] = None):
        
        self.account_config = account_config
        self.config = reconnection_config or ReconnectionConfig()
        self.fallback_config = fallback_config or FallbackMechanism()
        
        # Connection management
        self._connection: Optional[GoDaddyEmailClient] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._connection_lock = threading.RLock()
        
        # Failure tracking
        self._failure_history: List[ConnectionFailure] = []
        self._current_failure: Optional[ConnectionFailure] = None
        self._consecutive_failures = 0
        
        # Reconnection management
        self._reconnection_thread: Optional[threading.Thread] = None
        self._health_check_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._reconnection_event = threading.Event()
        
        # Metrics and monitoring
        self._metrics = ConnectionMetrics()
        self._connection_start_time: Optional[datetime] = None
        
        # State persistence
        self._state_file_path = self.config.state_persistence_path
        
        # Callbacks for connection events
        self._connection_callbacks: List[Callable[[ConnectionState, Optional[Exception]], None]] = []
        self._failure_callbacks: List[Callable[[ConnectionFailure], None]] = []
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Load persisted state
        self._load_connection_state()
        
        # Start background threads
        self._start_background_threads()

    def _start_background_threads(self) -> None:
        """Start background monitoring threads"""
        self._health_check_thread = threading.Thread(
            target=self._health_check_worker,
            daemon=True,
            name="ReconnectionHealthChecker"
        )
        self._health_check_thread.start()
        
        self.logger.info("Reconnection manager background threads started")

    def connect(self, force_reconnect: bool = False) -> bool:
        """
        Establish connection with intelligent retry logic
        
        Args:
            force_reconnect: Force reconnection even if already connected
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        with self._connection_lock:
            if self._connection and self._connection_state == ConnectionState.CONNECTED and not force_reconnect:
                # Already connected
                return True
            
            if self._connection_state == ConnectionState.RECONNECTING:
                # Already attempting to reconnect
                self.logger.info("Reconnection already in progress")
                return False
            
            return self._attempt_connection()

    def _attempt_connection(self) -> bool:
        """Attempt to establish connection with retry logic"""
        self._connection_state = ConnectionState.RECONNECTING
        self._notify_connection_state_change()
        
        start_time = time.time()
        
        try:
            # Create new connection
            self._connection = GoDaddyEmailClient()
            
            # Apply account configuration
            self._apply_account_config()
            
            # Attempt connection
            self._connection.connect()
            
            # Connection successful
            connection_time = time.time() - start_time
            self._handle_successful_connection(connection_time)
            
            return True
            
        except Exception as e:
            # Connection failed
            connection_time = time.time() - start_time
            self._handle_connection_failure(e, connection_time)
            
            return False

    def _apply_account_config(self) -> None:
        """Apply account configuration to the connection"""
        if not self._connection:
            return
            
        # Apply configuration from account_config
        for key, value in self.account_config.items():
            if hasattr(self._connection, key):
                setattr(self._connection, key, value)

    def _handle_successful_connection(self, connection_time: float) -> None:
        """Handle successful connection establishment"""
        with self._connection_lock:
            self._connection_state = ConnectionState.CONNECTED
            self._connection_start_time = datetime.now()
            
            # Reset failure tracking
            self._consecutive_failures = 0
            self._current_failure = None
            
            # Update metrics
            self._metrics.total_connections += 1
            self._metrics.successful_connections += 1
            self._metrics.last_successful_connection = datetime.now()
            
            # Update average connection time
            if self._metrics.average_connection_time == 0:
                self._metrics.average_connection_time = connection_time
            else:
                self._metrics.average_connection_time = (
                    (self._metrics.average_connection_time + connection_time) / 2
                )
            
            # Persist state
            self._persist_connection_state()
            
            # Notify callbacks
            self._notify_connection_state_change()
            
            self.logger.info(f"Connection established successfully in {connection_time:.2f}s")

    def _handle_connection_failure(self, error: Exception, connection_time: float) -> None:
        """Handle connection failure with intelligent retry logic"""
        with self._connection_lock:
            self._connection_state = ConnectionState.FAILED
            self._consecutive_failures += 1
            
            # Classify failure type
            failure_type = self._classify_failure(error)
            
            # Create failure record
            failure = ConnectionFailure(
                failure_type=failure_type,
                timestamp=datetime.now(),
                error_message=str(error),
                retry_count=self._consecutive_failures,
                is_persistent=(self._consecutive_failures >= self.config.persistent_failure_threshold)
            )
            
            self._current_failure = failure
            self._failure_history.append(failure)
            
            # Update metrics
            self._metrics.failed_connections += 1
            self._metrics.last_failure = datetime.now()
            
            # Calculate backoff duration
            backoff_duration = self._calculate_backoff_duration()
            failure.backoff_duration = backoff_duration
            
            # Persist state
            self._persist_connection_state()
            
            # Notify callbacks
            self._notify_failure_callbacks(failure)
            self._notify_connection_state_change(error)
            
            self.logger.error(f"Connection failed: {error} (attempt {self._consecutive_failures})")
            self.logger.info(f"Next retry in {backoff_duration:.2f} seconds")
            
            # Schedule reconnection attempt
            self._schedule_reconnection(backoff_duration)

    def _classify_failure(self, error: Exception) -> FailureType:
        """Classify the type of connection failure"""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return FailureType.TIMEOUT_ERROR
        elif "authentication" in error_str or "login" in error_str or "password" in error_str:
            return FailureType.AUTHENTICATION_ERROR
        elif "rate" in error_str or "limit" in error_str:
            return FailureType.RATE_LIMIT_ERROR
        elif "network" in error_str or "connection" in error_str or "host" in error_str:
            return FailureType.NETWORK_ERROR
        elif "server" in error_str or "5" in error_str[:2]:  # 5xx server errors
            return FailureType.SERVER_ERROR
        else:
            return FailureType.UNKNOWN_ERROR

    def _calculate_backoff_duration(self) -> float:
        """Calculate exponential backoff duration with jitter"""
        # Base exponential backoff
        backoff = min(
            self.config.initial_backoff * (self.config.backoff_multiplier ** (self._consecutive_failures - 1)),
            self.config.max_backoff
        )
        
        # Add jitter to prevent thundering herd
        jitter = backoff * self.config.jitter_factor * random.random()
        
        # Apply jitter (can be positive or negative)
        if random.random() < 0.5:
            backoff += jitter
        else:
            backoff -= jitter
        
        # Ensure minimum backoff
        backoff = max(backoff, self.config.initial_backoff)
        
        return backoff

    def _schedule_reconnection(self, delay: float) -> None:
        """Schedule a reconnection attempt after the specified delay"""
        if self._reconnection_thread and self._reconnection_thread.is_alive():
            # Already have a reconnection thread running
            return
        
        self._reconnection_thread = threading.Thread(
            target=self._reconnection_worker,
            args=(delay,),
            daemon=True,
            name="ReconnectionWorker"
        )
        self._reconnection_thread.start()

    def _reconnection_worker(self, delay: float) -> None:
        """Background worker for handling reconnection attempts"""
        try:
            # Wait for the backoff period
            if self._shutdown_event.wait(delay):
                # Shutdown requested during wait
                return
            
            # Check if we should attempt reconnection
            if self._consecutive_failures >= self.config.max_retry_attempts:
                self.logger.error(f"Maximum retry attempts ({self.config.max_retry_attempts}) reached")
                self._connection_state = ConnectionState.SUSPENDED
                self._notify_connection_state_change()
                
                # Try fallback mechanisms
                if self.fallback_config.enabled:
                    self._attempt_fallback_connection()
                
                return
            
            # Attempt reconnection
            self.logger.info(f"Attempting reconnection (attempt {self._consecutive_failures + 1})")
            self._metrics.reconnection_attempts += 1
            
            success = self._attempt_connection()
            
            if success:
                self._metrics.successful_reconnections += 1
                self.logger.info("Reconnection successful")
            else:
                self.logger.warning("Reconnection failed, will retry with increased backoff")
                
        except Exception as e:
            self.logger.error(f"Reconnection worker error: {e}")

    def _attempt_fallback_connection(self) -> bool:
        """Attempt connection using fallback mechanisms"""
        if not self.fallback_config.fallback_servers:
            self.logger.warning("No fallback servers configured")
            return False
        
        self.logger.info("Attempting fallback connection mechanisms")
        
        for i, fallback_server in enumerate(self.fallback_config.fallback_servers):
            if i >= self.fallback_config.max_fallback_attempts:
                break
                
            try:
                self.logger.info(f"Trying fallback server {i + 1}: {fallback_server.get('host', 'unknown')}")
                
                # Create temporary config with fallback server
                fallback_config = self.account_config.copy()
                fallback_config.update(fallback_server)
                
                # Store original config
                original_config = self.account_config.copy()
                
                # Apply fallback config
                self.account_config = fallback_config
                
                # Attempt connection
                success = self._attempt_connection()
                
                if success:
                    self.logger.info(f"Fallback connection successful using server {i + 1}")
                    return True
                else:
                    # Restore original config
                    self.account_config = original_config
                    
            except Exception as e:
                self.logger.error(f"Fallback server {i + 1} failed: {e}")
                # Restore original config
                self.account_config = original_config
        
        self.logger.error("All fallback mechanisms failed")
        return False

    def disconnect(self) -> None:
        """Disconnect from the email server"""
        with self._connection_lock:
            if self._connection:
                try:
                    self._connection.close()
                except Exception as e:
                    self.logger.warning(f"Error during disconnect: {e}")
                
                self._connection = None
            
            self._connection_state = ConnectionState.DISCONNECTED
            
            # Update uptime metrics
            if self._connection_start_time:
                uptime = datetime.now() - self._connection_start_time
                self._metrics.current_uptime = uptime
                self._connection_start_time = None
            
            # Persist state
            self._persist_connection_state()
            
            # Notify callbacks
            self._notify_connection_state_change()
            
            self.logger.info("Disconnected from email server")

    def get_connection(self) -> Optional[GoDaddyEmailClient]:
        """Get the current connection if available and healthy"""
        with self._connection_lock:
            if (self._connection and 
                self._connection_state == ConnectionState.CONNECTED and
                self._is_connection_healthy()):
                return self._connection
            
            return None

    def _is_connection_healthy(self) -> bool:
        """Check if the current connection is healthy"""
        if not self._connection:
            return False
        
        try:
            health_status = self._connection.get_connection_health()
            return health_status.status in [ConnectionHealth.HEALTHY, ConnectionHealth.DEGRADED]
            
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False

    def force_reconnect(self) -> bool:
        """Force a reconnection attempt"""
        self.logger.info("Forcing reconnection")
        
        # Disconnect current connection
        self.disconnect()
        
        # Reset failure counters for forced reconnect
        with self._connection_lock:
            self._consecutive_failures = 0
            self._current_failure = None
        
        # Attempt new connection
        return self.connect()

    def get_connection_state(self) -> ConnectionState:
        """Get the current connection state"""
        return self._connection_state

    def get_connection_metrics(self) -> ConnectionMetrics:
        """Get connection performance metrics"""
        with self._connection_lock:
            # Update uptime percentage
            if self._connection_start_time:
                current_uptime = datetime.now() - self._connection_start_time
                self._metrics.current_uptime = current_uptime
            
            # Calculate uptime percentage based on failure history
            if self._metrics.total_connections > 0:
                success_rate = self._metrics.successful_connections / self._metrics.total_connections
                self._metrics.uptime_percentage = success_rate * 100
            
            return self._metrics

    def get_failure_history(self) -> List[ConnectionFailure]:
        """Get the history of connection failures"""
        return self._failure_history.copy()

    def get_current_failure(self) -> Optional[ConnectionFailure]:
        """Get information about the current failure, if any"""
        return self._current_failure

    def add_connection_callback(self, callback: Callable[[ConnectionState, Optional[Exception]], None]) -> None:
        """Add a callback for connection state changes"""
        self._connection_callbacks.append(callback)

    def add_failure_callback(self, callback: Callable[[ConnectionFailure], None]) -> None:
        """Add a callback for connection failures"""
        self._failure_callbacks.append(callback)

    def _notify_connection_state_change(self, error: Optional[Exception] = None) -> None:
        """Notify all connection callbacks of state change"""
        for callback in self._connection_callbacks:
            try:
                callback(self._connection_state, error)
            except Exception as e:
                self.logger.error(f"Connection callback error: {e}")

    def _notify_failure_callbacks(self, failure: ConnectionFailure) -> None:
        """Notify all failure callbacks"""
        for callback in self._failure_callbacks:
            try:
                callback(failure)
            except Exception as e:
                self.logger.error(f"Failure callback error: {e}")

    def _persist_connection_state(self) -> None:
        """Persist connection state to disk for recovery"""
        try:
            state_data = {
                'connection_state': self._connection_state.value,
                'consecutive_failures': self._consecutive_failures,
                'metrics': asdict(self._metrics),
                'failure_history': [asdict(f) for f in self._failure_history[-10:]],  # Keep last 10
                'current_failure': asdict(self._current_failure) if self._current_failure else None,
                'timestamp': datetime.now().isoformat()
            }
            
            # Convert datetime objects and enums to JSON-serializable format
            def convert_for_json(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, timedelta):
                    return obj.total_seconds()
                elif isinstance(obj, Enum):
                    return obj.value
                return obj
            
            # Recursively convert objects for JSON serialization
            def recursive_convert(data):
                if isinstance(data, dict):
                    return {k: recursive_convert(v) for k, v in data.items()}
                elif isinstance(data, list):
                    return [recursive_convert(item) for item in data]
                else:
                    return convert_for_json(data)
            
            state_data = recursive_convert(state_data)
            
            with open(self._state_file_path, 'w') as f:
                json.dump(state_data, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to persist connection state: {e}")

    def _load_connection_state(self) -> None:
        """Load persisted connection state from disk"""
        try:
            if not os.path.exists(self._state_file_path):
                return
            
            with open(self._state_file_path, 'r') as f:
                state_data = json.load(f)
            
            # Restore basic state
            self._consecutive_failures = state_data.get('consecutive_failures', 0)
            
            # Restore metrics (with datetime conversion)
            metrics_data = state_data.get('metrics', {})
            if metrics_data:
                # Convert ISO format strings back to datetime objects
                if 'last_successful_connection' in metrics_data and metrics_data['last_successful_connection']:
                    metrics_data['last_successful_connection'] = datetime.fromisoformat(metrics_data['last_successful_connection'])
                if 'last_failure' in metrics_data and metrics_data['last_failure']:
                    metrics_data['last_failure'] = datetime.fromisoformat(metrics_data['last_failure'])
                if 'current_uptime' in metrics_data:
                    metrics_data['current_uptime'] = timedelta(seconds=metrics_data['current_uptime'])
                
                self._metrics = ConnectionMetrics(**metrics_data)
            
            # Restore failure history
            failure_history_data = state_data.get('failure_history', [])
            self._failure_history = []
            for failure_data in failure_history_data:
                failure_data['timestamp'] = datetime.fromisoformat(failure_data['timestamp'])
                failure_data['failure_type'] = FailureType(failure_data['failure_type'])
                self._failure_history.append(ConnectionFailure(**failure_data))
            
            # Restore current failure
            current_failure_data = state_data.get('current_failure')
            if current_failure_data:
                current_failure_data['timestamp'] = datetime.fromisoformat(current_failure_data['timestamp'])
                current_failure_data['failure_type'] = FailureType(current_failure_data['failure_type'])
                self._current_failure = ConnectionFailure(**current_failure_data)
            
            self.logger.info("Connection state loaded from persistence")
            
        except Exception as e:
            self.logger.warning(f"Failed to load connection state: {e}")

    def _health_check_worker(self) -> None:
        """Background worker for connection health monitoring"""
        self.logger.info("Starting connection health check worker")
        
        while not self._shutdown_event.is_set():
            try:
                self._perform_health_check()
                
                # Wait for next health check
                if self._shutdown_event.wait(self.config.health_check_interval):
                    break
                    
            except Exception as e:
                self.logger.error(f"Health check worker error: {e}")
                time.sleep(5)  # Brief pause on error

    def _perform_health_check(self) -> None:
        """Perform connection health check"""
        with self._connection_lock:
            if self._connection_state != ConnectionState.CONNECTED:
                return
            
            if not self._is_connection_healthy():
                self.logger.warning("Health check failed, initiating reconnection")
                
                # Create a failure record for health check failure
                failure = ConnectionFailure(
                    failure_type=FailureType.NETWORK_ERROR,
                    timestamp=datetime.now(),
                    error_message="Health check failed",
                    retry_count=self._consecutive_failures + 1
                )
                
                # Handle the failure
                self._handle_connection_failure(Exception("Health check failed"), 0.0)

    def shutdown(self) -> None:
        """Shutdown the reconnection manager"""
        self.logger.info("Shutting down reconnection manager")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Disconnect
        self.disconnect()
        
        # Wait for background threads
        if self._health_check_thread and self._health_check_thread.is_alive():
            self._health_check_thread.join(timeout=5)
        
        if self._reconnection_thread and self._reconnection_thread.is_alive():
            self._reconnection_thread.join(timeout=5)
        
        # Final state persistence
        self._persist_connection_state()
        
        self.logger.info("Reconnection manager shutdown complete")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()