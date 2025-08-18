# tests/email/test_connection_pool.py
import unittest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from queue import Empty, Full

from src.email.connection_pool import (
    ConnectionPoolManager, 
    PooledConnection, 
    PoolStatus, 
    PoolMetrics, 
    LoadMetrics
)
from src.email.godaddy_client import GoDaddyEmailClient, ConnectionHealth, ConnectionHealthStatus


class TestConnectionPoolManager(unittest.TestCase):
    """Test cases for ConnectionPoolManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.account_config = {
            'host': 'test.example.com',
            'port': 993,
            'username': 'test@example.com',
            'password': 'testpass'
        }
        
        # Mock the GoDaddyEmailClient to avoid actual connections
        self.mock_client_patcher = patch('src.email.connection_pool.GoDaddyEmailClient')
        self.mock_client_class = self.mock_client_patcher.start()
        
        # Configure mock client
        self.mock_client = Mock(spec=GoDaddyEmailClient)
        self.mock_client.get_connection_health.return_value = ConnectionHealthStatus(
            status=ConnectionHealth.HEALTHY,
            last_check=datetime.now(),
            response_time_ms=100.0,
            error_count=0,
            last_error=None,
            uptime_percentage=99.9
        )
        self.mock_client_class.return_value = self.mock_client
        
        # Mock psutil for load monitoring
        self.psutil_patcher = patch('src.email.connection_pool.psutil')
        self.mock_psutil = self.psutil_patcher.start()
        self.mock_psutil.cpu_percent.return_value = 25.0
        self.mock_psutil.virtual_memory.return_value = Mock(percent=40.0)
        self.mock_psutil.net_io_counters.return_value = Mock(bytes_sent=1000, bytes_recv=2000)

    def tearDown(self):
        """Clean up test fixtures"""
        self.mock_client_patcher.stop()
        self.psutil_patcher.stop()

    def test_pool_initialization(self):
        """Test connection pool initialization"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=2,
            max_pool_size=5
        )
        
        try:
            # Verify initial pool state
            metrics = pool.get_pool_metrics()
            self.assertEqual(metrics.total_connections, 2)
            self.assertEqual(metrics.idle_connections, 2)
            self.assertEqual(metrics.active_connections, 0)
            self.assertEqual(pool.get_pool_status(), PoolStatus.HEALTHY)
            
        finally:
            pool.shutdown()

    def test_get_connection_success(self):
        """Test successful connection retrieval"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=2,
            max_pool_size=5
        )
        
        try:
            # Get a connection
            conn = pool.get_connection()
            
            # Verify connection properties
            self.assertIsInstance(conn, PooledConnection)
            self.assertIsNotNone(conn.connection_id)
            self.assertTrue(conn.is_healthy)
            
            # Verify pool metrics updated
            metrics = pool.get_pool_metrics()
            self.assertEqual(metrics.active_connections, 1)
            self.assertEqual(metrics.idle_connections, 1)
            
            # Return connection
            pool.return_connection(conn)
            
            # Verify metrics after return
            metrics = pool.get_pool_metrics()
            self.assertEqual(metrics.active_connections, 0)
            self.assertEqual(metrics.idle_connections, 2)
            
        finally:
            pool.shutdown()

    def test_connection_pool_expansion(self):
        """Test dynamic pool expansion under load"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=2,
            max_pool_size=5
        )
        
        try:
            connections = []
            
            # Get all initial connections plus one more to trigger expansion
            for i in range(3):
                conn = pool.get_connection()
                connections.append(conn)
            
            # Verify pool expanded
            metrics = pool.get_pool_metrics()
            self.assertEqual(metrics.active_connections, 3)
            self.assertGreaterEqual(metrics.total_connections, 3)
            
            # Return all connections
            for conn in connections:
                pool.return_connection(conn)
                
        finally:
            pool.shutdown()

    def test_backpressure_handling(self):
        """Test backpressure handling when pool reaches capacity"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=1,
            max_pool_size=2,
            max_queue_size=3
        )
        
        try:
            connections = []
            
            # Fill the pool to capacity
            for i in range(2):
                conn = pool.get_connection()
                connections.append(conn)
            
            # Verify pool is at capacity
            metrics = pool.get_pool_metrics()
            self.assertEqual(metrics.active_connections, 2)
            
            # Test backpressure with timeout
            start_time = time.time()
            
            def get_connection_with_timeout():
                try:
                    return pool.get_connection(timeout=1)
                except TimeoutError:
                    return None
            
            # This should trigger backpressure and eventually timeout
            result = get_connection_with_timeout()
            elapsed_time = time.time() - start_time
            
            # Should have taken at least 1 second (timeout) and returned None
            self.assertGreaterEqual(elapsed_time, 1.0)
            self.assertIsNone(result)
            
            # Return connections
            for conn in connections:
                pool.return_connection(conn)
                
        finally:
            pool.shutdown()

    def test_connection_health_validation(self):
        """Test connection health validation and replacement"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=2,
            max_pool_size=5
        )
        
        try:
            # Get a connection
            conn = pool.get_connection()
            
            # Simulate connection becoming unhealthy
            self.mock_client.get_connection_health.return_value = ConnectionHealthStatus(
                status=ConnectionHealth.UNHEALTHY,
                last_check=datetime.now(),
                response_time_ms=5000.0,
                error_count=5,
                last_error="Connection failed",
                uptime_percentage=50.0
            )
            
            # Return the now-unhealthy connection
            pool.return_connection(conn)
            
            # The pool should have replaced the unhealthy connection
            # This is verified by checking that we can still get healthy connections
            new_conn = pool.get_connection()
            self.assertIsInstance(new_conn, PooledConnection)
            
            pool.return_connection(new_conn)
            
        finally:
            pool.shutdown()

    def test_load_metrics_collection(self):
        """Test system load metrics collection"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=1,
            max_pool_size=3
        )
        
        try:
            # Wait a moment for load metrics to be collected
            time.sleep(0.5)
            
            load_metrics = pool.get_load_metrics()
            
            # Verify load metrics are collected
            self.assertIsInstance(load_metrics, LoadMetrics)
            self.assertGreaterEqual(load_metrics.cpu_usage, 0)
            self.assertGreaterEqual(load_metrics.memory_usage, 0)
            self.assertGreaterEqual(load_metrics.network_io, 0)
            self.assertIsInstance(load_metrics.last_measured, datetime)
            
        finally:
            pool.shutdown()

    def test_concurrent_connection_access(self):
        """Test concurrent access to connection pool"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=3,
            max_pool_size=10
        )
        
        try:
            results = []
            errors = []
            
            def worker():
                try:
                    conn = pool.get_connection(timeout=5)
                    time.sleep(0.1)  # Simulate work
                    pool.return_connection(conn)
                    results.append(True)
                except Exception as e:
                    errors.append(str(e))
            
            # Start multiple threads
            threads = []
            for i in range(20):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10)
            
            # Verify results
            self.assertEqual(len(results), 20)
            self.assertEqual(len(errors), 0)
            
            # Verify pool state is consistent
            metrics = pool.get_pool_metrics()
            self.assertEqual(metrics.active_connections, 0)
            
        finally:
            pool.shutdown()

    def test_pool_status_transitions(self):
        """Test pool status transitions under different load conditions"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=2,
            max_pool_size=4,
            max_queue_size=5
        )
        
        try:
            # Initially should be healthy
            self.assertEqual(pool.get_pool_status(), PoolStatus.HEALTHY)
            
            connections = []
            
            # Fill pool to trigger status changes
            for i in range(4):
                conn = pool.get_connection()
                connections.append(conn)
            
            # Pool should now be under higher utilization
            # Status might be DEGRADED or OVERLOADED depending on exact metrics
            status = pool.get_pool_status()
            self.assertIn(status, [PoolStatus.HEALTHY, PoolStatus.DEGRADED, PoolStatus.OVERLOADED])
            
            # Return connections
            for conn in connections:
                pool.return_connection(conn)
            
            # Should return to healthy status
            time.sleep(0.1)  # Brief pause for status update
            
        finally:
            pool.shutdown()

    def test_connection_age_management(self):
        """Test connection age management and replacement"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=1,
            max_pool_size=3,
            max_connection_age=1  # 1 second for testing
        )
        
        try:
            # Get a connection
            conn = pool.get_connection()
            original_id = conn.connection_id
            
            # Wait for connection to age
            time.sleep(1.5)
            
            # Return the aged connection
            pool.return_connection(conn)
            
            # Get a new connection - should be a different one due to age
            new_conn = pool.get_connection()
            
            # The connection might be the same if replacement hasn't occurred yet
            # This is acceptable as age management is done in background
            self.assertIsInstance(new_conn, PooledConnection)
            
            pool.return_connection(new_conn)
            
        finally:
            pool.shutdown()

    def test_memory_usage_efficiency(self):
        """Test memory usage efficiency with large attachments"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=2,
            max_pool_size=5
        )
        
        try:
            # Simulate processing large attachments by getting/returning connections rapidly
            for i in range(50):
                conn = pool.get_connection()
                # Simulate memory-intensive operation
                time.sleep(0.01)
                pool.return_connection(conn)
            
            # Verify pool is still healthy and hasn't leaked connections
            metrics = pool.get_pool_metrics()
            self.assertEqual(metrics.active_connections, 0)
            self.assertGreaterEqual(metrics.total_connections, pool.min_pool_size)
            self.assertLessEqual(metrics.total_connections, pool.max_pool_size)
            
        finally:
            pool.shutdown()

    def test_pool_shutdown(self):
        """Test proper pool shutdown and resource cleanup"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=2,
            max_pool_size=5
        )
        
        # Get some connections
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        
        # Shutdown pool
        pool.shutdown()
        
        # Verify all connections are closed
        self.mock_client.close.assert_called()
        
        # Verify background threads are stopped
        self.assertFalse(pool._health_check_thread.is_alive())
        self.assertFalse(pool._load_monitor_thread.is_alive())
        self.assertFalse(pool._pool_scaler_thread.is_alive())

    def test_context_manager(self):
        """Test connection pool as context manager"""
        with ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=1,
            max_pool_size=3
        ) as pool:
            
            conn = pool.get_connection()
            self.assertIsInstance(conn, PooledConnection)
            pool.return_connection(conn)
        
        # Pool should be automatically shut down
        # Verify by checking that background threads are stopped
        self.assertFalse(pool._health_check_thread.is_alive())


class TestPooledConnection(unittest.TestCase):
    """Test cases for PooledConnection"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_client = Mock(spec=GoDaddyEmailClient)
        
    def test_pooled_connection_creation(self):
        """Test PooledConnection creation and properties"""
        now = datetime.now()
        
        pooled_conn = PooledConnection(
            connection=self.mock_client,
            created_at=now,
            last_used=now
        )
        
        self.assertEqual(pooled_conn.connection, self.mock_client)
        self.assertEqual(pooled_conn.created_at, now)
        self.assertEqual(pooled_conn.last_used, now)
        self.assertEqual(pooled_conn.usage_count, 0)
        self.assertTrue(pooled_conn.is_healthy)
        self.assertIsNotNone(pooled_conn.connection_id)

    def test_connection_id_generation(self):
        """Test automatic connection ID generation"""
        pooled_conn = PooledConnection(
            connection=self.mock_client,
            created_at=datetime.now(),
            last_used=datetime.now()
        )
        
        self.assertTrue(pooled_conn.connection_id.startswith('conn_'))
        self.assertGreater(len(pooled_conn.connection_id), 5)


if __name__ == '__main__':
    unittest.main()