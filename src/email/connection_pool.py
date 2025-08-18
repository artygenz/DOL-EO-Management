# src/email/connection_pool.py
import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue, Empty, Full
from concurrent.futures import ThreadPoolExecutor, Future
import psutil
import weakref

from .godaddy_client import GoDaddyEmailClient, ConnectionHealth, ConnectionHealthStatus


class PoolStatus(Enum):
    """Connection pool status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"
    CRITICAL = "critical"


@dataclass
class PoolMetrics:
    """Connection pool performance metrics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    queue_depth: int = 0
    average_response_time: float = 0.0
    peak_usage: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class LoadMetrics:
    """System load metrics for dynamic pool sizing"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    network_io: float = 0.0
    email_processing_rate: float = 0.0
    queue_wait_time: float = 0.0
    last_measured: datetime = field(default_factory=datetime.now)


@dataclass
class PooledConnection:
    """Wrapper for pooled email connections"""
    connection: GoDaddyEmailClient
    created_at: datetime
    last_used: datetime
    usage_count: int = 0
    is_healthy: bool = True
    connection_id: str = ""
    
    def __post_init__(self):
        if not self.connection_id:
            self.connection_id = f"conn_{id(self.connection)}"


class ConnectionPoolManager:
    """Multi-connection pooling system with dynamic sizing and health management"""
    
    def __init__(self, 
                 account_config: Dict[str, Any],
                 min_pool_size: int = 2,
                 max_pool_size: int = 10,
                 max_queue_size: int = 100,
                 connection_timeout: int = 30,
                 health_check_interval: int = 60,
                 max_connection_age: int = 3600):  # 1 hour
        
        self.account_config = account_config
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.max_queue_size = max_queue_size
        self.connection_timeout = connection_timeout
        self.health_check_interval = health_check_interval
        self.max_connection_age = max_connection_age
        
        # Connection pools and queues
        self._available_connections: Queue[PooledConnection] = Queue(maxsize=max_pool_size)
        self._active_connections: Dict[str, PooledConnection] = {}
        self._request_queue: Queue[Dict[str, Any]] = Queue(maxsize=max_queue_size)
        
        # Metrics and monitoring
        self._metrics = PoolMetrics()
        self._load_metrics = LoadMetrics()
        self._pool_status = PoolStatus.HEALTHY
        
        # Threading and synchronization
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()
        self._health_check_thread: Optional[threading.Thread] = None
        self._load_monitor_thread: Optional[threading.Thread] = None
        self._pool_scaler_thread: Optional[threading.Thread] = None
        
        # Performance tracking
        self._response_times: List[float] = []
        self._request_timestamps: List[datetime] = []
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize pool
        self._initialize_pool()
        self._start_background_threads()

    def _initialize_pool(self) -> None:
        """Initialize the connection pool with minimum connections"""
        self.logger.info(f"Initializing connection pool with {self.min_pool_size} connections")
        
        for i in range(self.min_pool_size):
            try:
                connection = self._create_new_connection()
                pooled_conn = PooledConnection(
                    connection=connection,
                    created_at=datetime.now(),
                    last_used=datetime.now(),
                    connection_id=f"init_conn_{i}"
                )
                self._available_connections.put(pooled_conn, block=False)
                self._metrics.total_connections += 1
                self._metrics.idle_connections += 1
                
            except Exception as e:
                self.logger.error(f"Failed to create initial connection {i}: {e}")
                self._metrics.failed_connections += 1

    def _create_new_connection(self) -> GoDaddyEmailClient:
        """Create a new email client connection"""
        client = GoDaddyEmailClient()
        client.connect()
        return client

    def _start_background_threads(self) -> None:
        """Start background monitoring and management threads"""
        self._health_check_thread = threading.Thread(
            target=self._health_check_worker,
            daemon=True,
            name="PoolHealthChecker"
        )
        self._health_check_thread.start()
        
        self._load_monitor_thread = threading.Thread(
            target=self._load_monitor_worker,
            daemon=True,
            name="LoadMonitor"
        )
        self._load_monitor_thread.start()
        
        self._pool_scaler_thread = threading.Thread(
            target=self._pool_scaler_worker,
            daemon=True,
            name="PoolScaler"
        )
        self._pool_scaler_thread.start()

    def get_connection(self, timeout: Optional[int] = None) -> PooledConnection:
        """Get a connection from the pool with backpressure handling"""
        if timeout is None:
            timeout = self.connection_timeout
            
        start_time = time.time()
        
        # Check if pool is at capacity and implement backpressure
        if self._should_apply_backpressure():
            self._handle_backpressure()
        
        try:
            # Try to get an available connection
            with self._lock:
                if not self._available_connections.empty():
                    pooled_conn = self._available_connections.get(block=False)
                    
                    # Validate connection health
                    if self._validate_connection_health(pooled_conn):
                        pooled_conn.last_used = datetime.now()
                        pooled_conn.usage_count += 1
                        
                        self._active_connections[pooled_conn.connection_id] = pooled_conn
                        self._metrics.active_connections += 1
                        self._metrics.idle_connections -= 1
                        
                        response_time = (time.time() - start_time) * 1000
                        self._update_response_time(response_time)
                        
                        return pooled_conn
                    else:
                        # Connection is unhealthy, replace it
                        self._replace_unhealthy_connection(pooled_conn)
                
                # No available connections, try to create a new one if under limit
                if self._metrics.total_connections < self.max_pool_size:
                    pooled_conn = self._create_pooled_connection()
                    if pooled_conn:
                        self._active_connections[pooled_conn.connection_id] = pooled_conn
                        self._metrics.active_connections += 1
                        
                        response_time = (time.time() - start_time) * 1000
                        self._update_response_time(response_time)
                        
                        return pooled_conn
                
                # Pool is at capacity, queue the request
                self._queue_request(timeout)
                
                # Wait for a connection to become available
                return self._wait_for_available_connection(timeout, start_time)
                
        except Exception as e:
            self.logger.error(f"Failed to get connection from pool: {e}")
            self._metrics.failed_requests += 1
            raise

    def _should_apply_backpressure(self) -> bool:
        """Determine if backpressure should be applied"""
        with self._lock:
            queue_utilization = self._request_queue.qsize() / self.max_queue_size
            pool_utilization = self._metrics.active_connections / self.max_pool_size
            
            # Apply backpressure if queue is >80% full or pool is >90% utilized
            return queue_utilization > 0.8 or pool_utilization > 0.9

    def _handle_backpressure(self) -> None:
        """Handle backpressure by implementing delays and load shedding"""
        with self._lock:
            queue_size = self._request_queue.qsize()
            active_conns = self._metrics.active_connections
            
            if queue_size > self.max_queue_size * 0.9:
                # Critical backpressure - implement exponential backoff
                backoff_time = min(5.0, 0.1 * (queue_size / 10))
                self.logger.warning(f"Critical backpressure detected, applying {backoff_time:.2f}s backoff")
                time.sleep(backoff_time)
                
                # Update pool status
                self._pool_status = PoolStatus.CRITICAL
                
            elif active_conns > self.max_pool_size * 0.8:
                # High utilization - apply moderate backoff
                backoff_time = 0.05 * (active_conns / self.max_pool_size)
                self.logger.info(f"High pool utilization, applying {backoff_time:.2f}s backoff")
                time.sleep(backoff_time)
                
                # Update pool status
                self._pool_status = PoolStatus.OVERLOADED

    def _queue_request(self, timeout: int) -> None:
        """Queue a connection request when pool is at capacity"""
        request = {
            'timestamp': datetime.now(),
            'timeout': timeout,
            'thread_id': threading.get_ident()
        }
        
        try:
            self._request_queue.put(request, block=False)
            self._metrics.queue_depth = self._request_queue.qsize()
            self.logger.debug(f"Queued connection request, queue depth: {self._metrics.queue_depth}")
            
        except Full:
            # Queue is full, implement load shedding
            self.logger.error("Connection request queue is full, rejecting request")
            raise Exception("Connection pool overloaded, request rejected")

    def _wait_for_available_connection(self, timeout: int, start_time: float) -> PooledConnection:
        """Wait for a connection to become available"""
        wait_start = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                # Check if a connection became available
                with self._lock:
                    if not self._available_connections.empty():
                        pooled_conn = self._available_connections.get(block=False)
                        
                        if self._validate_connection_health(pooled_conn):
                            pooled_conn.last_used = datetime.now()
                            pooled_conn.usage_count += 1
                            
                            self._active_connections[pooled_conn.connection_id] = pooled_conn
                            self._metrics.active_connections += 1
                            self._metrics.idle_connections -= 1
                            
                            # Update wait time metrics
                            wait_time = (time.time() - wait_start) * 1000
                            self._load_metrics.queue_wait_time = wait_time
                            
                            return pooled_conn
                
                # Brief sleep before checking again
                time.sleep(0.1)
                
            except Empty:
                continue
        
        # Timeout reached
        self.logger.error(f"Connection request timed out after {timeout}s")
        self._metrics.failed_requests += 1
        raise TimeoutError(f"Failed to get connection within {timeout} seconds")

    def return_connection(self, pooled_conn: PooledConnection) -> None:
        """Return a connection to the pool"""
        try:
            with self._lock:
                if pooled_conn.connection_id in self._active_connections:
                    del self._active_connections[pooled_conn.connection_id]
                    self._metrics.active_connections -= 1
                    
                    # Check if connection is still healthy and not too old
                    if (self._validate_connection_health(pooled_conn) and 
                        self._is_connection_fresh(pooled_conn)):
                        
                        # Return to available pool
                        try:
                            self._available_connections.put(pooled_conn, block=False)
                            self._metrics.idle_connections += 1
                            self.logger.debug(f"Returned connection {pooled_conn.connection_id} to pool")
                            
                        except Full:
                            # Pool is full, close the connection
                            self._close_connection(pooled_conn)
                            
                    else:
                        # Connection is unhealthy or too old, replace it
                        self._replace_unhealthy_connection(pooled_conn)
                        
        except Exception as e:
            self.logger.error(f"Failed to return connection to pool: {e}")

    def _validate_connection_health(self, pooled_conn: PooledConnection) -> bool:
        """Validate that a pooled connection is healthy"""
        try:
            if not pooled_conn.is_healthy:
                return False
                
            # Perform health check on the underlying connection
            health_status = pooled_conn.connection.get_connection_health()
            
            if health_status.status in [ConnectionHealth.HEALTHY, ConnectionHealth.DEGRADED]:
                pooled_conn.is_healthy = True
                return True
            else:
                pooled_conn.is_healthy = False
                return False
                
        except Exception as e:
            self.logger.warning(f"Connection health check failed: {e}")
            pooled_conn.is_healthy = False
            return False

    def _is_connection_fresh(self, pooled_conn: PooledConnection) -> bool:
        """Check if connection is within maximum age limit"""
        age = (datetime.now() - pooled_conn.created_at).total_seconds()
        return age < self.max_connection_age

    def _create_pooled_connection(self) -> Optional[PooledConnection]:
        """Create a new pooled connection"""
        try:
            connection = self._create_new_connection()
            pooled_conn = PooledConnection(
                connection=connection,
                created_at=datetime.now(),
                last_used=datetime.now()
            )
            
            self._metrics.total_connections += 1
            self.logger.debug(f"Created new pooled connection {pooled_conn.connection_id}")
            
            return pooled_conn
            
        except Exception as e:
            self.logger.error(f"Failed to create new pooled connection: {e}")
            self._metrics.failed_connections += 1
            return None

    def _replace_unhealthy_connection(self, pooled_conn: PooledConnection) -> None:
        """Replace an unhealthy connection with a new one"""
        try:
            # Close the unhealthy connection
            self._close_connection(pooled_conn)
            
            # Create a replacement if we're below minimum
            if self._metrics.total_connections < self.min_pool_size:
                replacement = self._create_pooled_connection()
                if replacement:
                    try:
                        self._available_connections.put(replacement, block=False)
                        self._metrics.idle_connections += 1
                        
                    except Full:
                        # Pool is full, close the replacement
                        self._close_connection(replacement)
                        
        except Exception as e:
            self.logger.error(f"Failed to replace unhealthy connection: {e}")

    def _close_connection(self, pooled_conn: PooledConnection) -> None:
        """Close a pooled connection and update metrics"""
        try:
            pooled_conn.connection.close()
            self._metrics.total_connections -= 1
            self.logger.debug(f"Closed connection {pooled_conn.connection_id}")
            
        except Exception as e:
            self.logger.warning(f"Error closing connection {pooled_conn.connection_id}: {e}")

    def _update_response_time(self, response_time: float) -> None:
        """Update response time metrics"""
        self._response_times.append(response_time)
        
        # Keep only last 100 response times for rolling average
        if len(self._response_times) > 100:
            self._response_times.pop(0)
        
        # Calculate average response time
        if self._response_times:
            self._metrics.average_response_time = sum(self._response_times) / len(self._response_times)

    def get_pool_metrics(self) -> PoolMetrics:
        """Get current pool metrics"""
        with self._lock:
            self._metrics.last_updated = datetime.now()
            self._metrics.queue_depth = self._request_queue.qsize()
            
            # Update peak usage
            current_usage = self._metrics.active_connections + self._metrics.idle_connections
            if current_usage > self._metrics.peak_usage:
                self._metrics.peak_usage = current_usage
                
            return self._metrics

    def get_load_metrics(self) -> LoadMetrics:
        """Get current system load metrics"""
        return self._load_metrics

    def get_pool_status(self) -> PoolStatus:
        """Get current pool status"""
        return self._pool_status

    def _health_check_worker(self) -> None:
        """Background worker for connection health monitoring"""
        self.logger.info("Starting connection health check worker")
        
        while not self._shutdown_event.is_set():
            try:
                self._perform_health_checks()
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Health check worker error: {e}")
                time.sleep(5)  # Brief pause on error

    def _perform_health_checks(self) -> None:
        """Perform health checks on all connections"""
        unhealthy_connections = []
        
        with self._lock:
            # Check active connections
            for conn_id, pooled_conn in list(self._active_connections.items()):
                if not self._validate_connection_health(pooled_conn):
                    unhealthy_connections.append(pooled_conn)
            
            # Check idle connections
            temp_connections = []
            while not self._available_connections.empty():
                try:
                    pooled_conn = self._available_connections.get(block=False)
                    if self._validate_connection_health(pooled_conn) and self._is_connection_fresh(pooled_conn):
                        temp_connections.append(pooled_conn)
                    else:
                        unhealthy_connections.append(pooled_conn)
                        
                except Empty:
                    break
            
            # Return healthy connections to pool
            for conn in temp_connections:
                try:
                    self._available_connections.put(conn, block=False)
                except Full:
                    unhealthy_connections.append(conn)
        
        # Replace unhealthy connections
        for conn in unhealthy_connections:
            self._replace_unhealthy_connection(conn)
        
        if unhealthy_connections:
            self.logger.info(f"Replaced {len(unhealthy_connections)} unhealthy connections")

    def _load_monitor_worker(self) -> None:
        """Background worker for system load monitoring"""
        self.logger.info("Starting load monitor worker")
        
        while not self._shutdown_event.is_set():
            try:
                self._collect_load_metrics()
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Load monitor worker error: {e}")
                time.sleep(5)

    def _collect_load_metrics(self) -> None:
        """Collect system load metrics for dynamic scaling"""
        try:
            # CPU and memory usage
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            memory_usage = memory_info.percent
            
            # Network I/O (simplified)
            net_io = psutil.net_io_counters()
            network_io = (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024)  # MB
            
            # Email processing rate (requests per minute)
            now = datetime.now()
            self._request_timestamps.append(now)
            
            # Keep only last minute of timestamps
            cutoff_time = now - timedelta(minutes=1)
            self._request_timestamps = [ts for ts in self._request_timestamps if ts > cutoff_time]
            
            email_processing_rate = len(self._request_timestamps)
            
            # Update load metrics
            self._load_metrics = LoadMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                network_io=network_io,
                email_processing_rate=email_processing_rate,
                queue_wait_time=self._load_metrics.queue_wait_time,  # Keep previous value
                last_measured=now
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect load metrics: {e}")

    def _pool_scaler_worker(self) -> None:
        """Background worker for dynamic pool scaling"""
        self.logger.info("Starting pool scaler worker")
        
        while not self._shutdown_event.is_set():
            try:
                self._perform_dynamic_scaling()
                time.sleep(30)  # Scale every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Pool scaler worker error: {e}")
                time.sleep(10)

    def _perform_dynamic_scaling(self) -> None:
        """Perform dynamic pool scaling based on load metrics"""
        with self._lock:
            current_size = self._metrics.total_connections
            active_connections = self._metrics.active_connections
            queue_depth = self._request_queue.qsize()
            
            # Calculate utilization metrics
            pool_utilization = active_connections / max(1, current_size)
            queue_utilization = queue_depth / self.max_queue_size
            
            # Determine scaling action
            should_scale_up = (
                (pool_utilization > 0.8 and current_size < self.max_pool_size) or
                (queue_utilization > 0.5 and current_size < self.max_pool_size) or
                (self._load_metrics.cpu_usage < 70 and queue_depth > 5)
            )
            
            should_scale_down = (
                pool_utilization < 0.3 and 
                current_size > self.min_pool_size and
                queue_depth == 0 and
                self._load_metrics.cpu_usage < 50
            )
            
            if should_scale_up:
                self._scale_up()
            elif should_scale_down:
                self._scale_down()
            
            # Update pool status based on current conditions
            self._update_pool_status(pool_utilization, queue_utilization)

    def _scale_up(self) -> None:
        """Scale up the connection pool"""
        try:
            new_connection = self._create_pooled_connection()
            if new_connection:
                self._available_connections.put(new_connection, block=False)
                self._metrics.idle_connections += 1
                
                self.logger.info(f"Scaled up pool to {self._metrics.total_connections} connections")
                
        except (Full, Exception) as e:
            self.logger.warning(f"Failed to scale up pool: {e}")

    def _scale_down(self) -> None:
        """Scale down the connection pool"""
        try:
            if not self._available_connections.empty():
                pooled_conn = self._available_connections.get(block=False)
                self._close_connection(pooled_conn)
                self._metrics.idle_connections -= 1
                
                self.logger.info(f"Scaled down pool to {self._metrics.total_connections} connections")
                
        except (Empty, Exception) as e:
            self.logger.warning(f"Failed to scale down pool: {e}")

    def _update_pool_status(self, pool_utilization: float, queue_utilization: float) -> None:
        """Update pool status based on current metrics"""
        if queue_utilization > 0.9 or pool_utilization > 0.95:
            self._pool_status = PoolStatus.CRITICAL
        elif queue_utilization > 0.7 or pool_utilization > 0.85:
            self._pool_status = PoolStatus.OVERLOADED
        elif queue_utilization > 0.4 or pool_utilization > 0.7:
            self._pool_status = PoolStatus.DEGRADED
        else:
            self._pool_status = PoolStatus.HEALTHY

    def shutdown(self) -> None:
        """Shutdown the connection pool and cleanup resources"""
        self.logger.info("Shutting down connection pool")
        
        # Signal shutdown to background threads
        self._shutdown_event.set()
        
        # Wait for background threads to finish
        if self._health_check_thread and self._health_check_thread.is_alive():
            self._health_check_thread.join(timeout=5)
        
        if self._load_monitor_thread and self._load_monitor_thread.is_alive():
            self._load_monitor_thread.join(timeout=5)
            
        if self._pool_scaler_thread and self._pool_scaler_thread.is_alive():
            self._pool_scaler_thread.join(timeout=5)
        
        # Close all connections
        with self._lock:
            # Close active connections
            for pooled_conn in list(self._active_connections.values()):
                self._close_connection(pooled_conn)
            self._active_connections.clear()
            
            # Close idle connections
            while not self._available_connections.empty():
                try:
                    pooled_conn = self._available_connections.get(block=False)
                    self._close_connection(pooled_conn)
                except Empty:
                    break
        
        self.logger.info("Connection pool shutdown complete")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()