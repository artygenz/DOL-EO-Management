# tests/email/test_connection_pool_load.py
import unittest
import threading
import time
import statistics
from unittest.mock import Mock, patch
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.email.connection_pool import ConnectionPoolManager, PoolStatus
from src.email.godaddy_client import GoDaddyEmailClient, ConnectionHealth, ConnectionHealthStatus


class TestConnectionPoolLoad(unittest.TestCase):
    """Load testing for ConnectionPoolManager under stress conditions"""
    
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
        
        # Configure mock client with realistic response times
        self.mock_client = Mock(spec=GoDaddyEmailClient)
        self.mock_client.get_connection_health.return_value = ConnectionHealthStatus(
            status=ConnectionHealth.HEALTHY,
            last_check=datetime.now(),
            response_time_ms=50.0,
            error_count=0,
            last_error=None,
            uptime_percentage=99.9
        )
        self.mock_client_class.return_value = self.mock_client
        
        # Mock psutil for load monitoring
        self.psutil_patcher = patch('src.email.connection_pool.psutil')
        self.mock_psutil = self.psutil_patcher.start()
        self.mock_psutil.cpu_percent.return_value = 30.0
        self.mock_psutil.virtual_memory.return_value = Mock(percent=45.0)
        self.mock_psutil.net_io_counters.return_value = Mock(bytes_sent=5000, bytes_recv=10000)

    def tearDown(self):
        """Clean up test fixtures"""
        self.mock_client_patcher.stop()
        self.psutil_patcher.stop()

    def test_high_concurrency_load(self):
        """Test pool performance under high concurrent load"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=5,
            max_pool_size=20,
            max_queue_size=100
        )
        
        try:
            num_threads = 50
            operations_per_thread = 20
            results = []
            errors = []
            response_times = []
            
            def worker():
                """Worker function that performs multiple operations"""
                thread_results = []
                thread_errors = []
                thread_times = []
                
                for i in range(operations_per_thread):
                    try:
                        start_time = time.time()
                        
                        # Get connection
                        conn = pool.get_connection(timeout=10)
                        
                        # Simulate email processing work
                        time.sleep(0.01)  # 10ms of work
                        
                        # Return connection
                        pool.return_connection(conn)
                        
                        end_time = time.time()
                        operation_time = (end_time - start_time) * 1000  # Convert to ms
                        
                        thread_results.append(True)
                        thread_times.append(operation_time)
                        
                    except Exception as e:
                        thread_errors.append(str(e))
                
                return thread_results, thread_errors, thread_times
            
            # Execute load test
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker) for _ in range(num_threads)]
                
                for future in as_completed(futures):
                    thread_results, thread_errors, thread_times = future.result()
                    results.extend(thread_results)
                    errors.extend(thread_errors)
                    response_times.extend(thread_times)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze results
            total_operations = num_threads * operations_per_thread
            successful_operations = len(results)
            failed_operations = len(errors)
            
            # Calculate performance metrics
            throughput = successful_operations / total_time  # operations per second
            avg_response_time = statistics.mean(response_times) if response_times else 0
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else 0
            
            # Verify performance requirements
            self.assertGreater(successful_operations, total_operations * 0.95)  # 95% success rate
            self.assertLess(failed_operations, total_operations * 0.05)  # Less than 5% failures
            self.assertGreater(throughput, 100)  # At least 100 operations per second
            self.assertLess(avg_response_time, 1000)  # Average response time under 1 second
            self.assertLess(p95_response_time, 2000)  # 95th percentile under 2 seconds
            
            # Verify pool metrics
            metrics = pool.get_pool_metrics()
            self.assertEqual(metrics.active_connections, 0)  # All connections returned
            self.assertGreaterEqual(metrics.total_connections, pool.min_pool_size)
            self.assertLessEqual(metrics.total_connections, pool.max_pool_size)
            
            print(f"\nLoad Test Results:")
            print(f"Total Operations: {total_operations}")
            print(f"Successful: {successful_operations}")
            print(f"Failed: {failed_operations}")
            print(f"Success Rate: {(successful_operations/total_operations)*100:.2f}%")
            print(f"Throughput: {throughput:.2f} ops/sec")
            print(f"Average Response Time: {avg_response_time:.2f}ms")
            print(f"95th Percentile: {p95_response_time:.2f}ms")
            print(f"99th Percentile: {p99_response_time:.2f}ms")
            print(f"Final Pool Size: {metrics.total_connections}")
            
        finally:
            pool.shutdown()

    def test_sustained_load_over_time(self):
        """Test pool performance under sustained load over extended period"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=3,
            max_pool_size=15,
            max_queue_size=50
        )
        
        try:
            duration_seconds = 30  # 30 second test
            target_rate = 50  # 50 operations per second
            
            results = []
            errors = []
            response_times = []
            pool_sizes = []
            
            def sustained_worker():
                """Worker that maintains sustained load"""
                start_time = time.time()
                operation_count = 0
                
                while (time.time() - start_time) < duration_seconds:
                    try:
                        op_start = time.time()
                        
                        # Get connection
                        conn = pool.get_connection(timeout=5)
                        
                        # Simulate work
                        time.sleep(0.005)  # 5ms of work
                        
                        # Return connection
                        pool.return_connection(conn)
                        
                        op_end = time.time()
                        response_time = (op_end - op_start) * 1000
                        
                        results.append(True)
                        response_times.append(response_time)
                        operation_count += 1
                        
                        # Record pool size periodically
                        if operation_count % 10 == 0:
                            metrics = pool.get_pool_metrics()
                            pool_sizes.append(metrics.total_connections)
                        
                        # Rate limiting to maintain target rate
                        elapsed = time.time() - start_time
                        expected_ops = elapsed * target_rate
                        if operation_count > expected_ops:
                            sleep_time = (operation_count - expected_ops) / target_rate
                            time.sleep(sleep_time)
                            
                    except Exception as e:
                        errors.append(str(e))
            
            # Run sustained load test
            num_workers = 5
            threads = []
            
            for _ in range(num_workers):
                thread = threading.Thread(target=sustained_worker)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Analyze sustained load results
            total_operations = len(results)
            actual_rate = total_operations / duration_seconds
            avg_response_time = statistics.mean(response_times) if response_times else 0
            avg_pool_size = statistics.mean(pool_sizes) if pool_sizes else 0
            
            # Verify sustained performance
            self.assertGreater(total_operations, duration_seconds * target_rate * 0.8)  # 80% of target rate
            self.assertLess(len(errors), total_operations * 0.02)  # Less than 2% errors
            self.assertLess(avg_response_time, 500)  # Average response time under 500ms
            
            # Verify pool adapted appropriately
            self.assertGreaterEqual(avg_pool_size, pool.min_pool_size)
            self.assertLessEqual(max(pool_sizes) if pool_sizes else 0, pool.max_pool_size)
            
            print(f"\nSustained Load Test Results:")
            print(f"Duration: {duration_seconds}s")
            print(f"Total Operations: {total_operations}")
            print(f"Target Rate: {target_rate} ops/sec")
            print(f"Actual Rate: {actual_rate:.2f} ops/sec")
            print(f"Errors: {len(errors)}")
            print(f"Average Response Time: {avg_response_time:.2f}ms")
            print(f"Average Pool Size: {avg_pool_size:.1f}")
            print(f"Max Pool Size: {max(pool_sizes) if pool_sizes else 0}")
            
        finally:
            pool.shutdown()

    def test_burst_load_handling(self):
        """Test pool handling of sudden burst loads"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=2,
            max_pool_size=12,
            max_queue_size=30
        )
        
        try:
            # Phase 1: Low load
            low_load_results = []
            for i in range(10):
                conn = pool.get_connection()
                time.sleep(0.01)
                pool.return_connection(conn)
                low_load_results.append(True)
            
            initial_metrics = pool.get_pool_metrics()
            
            # Phase 2: Sudden burst
            burst_results = []
            burst_errors = []
            burst_times = []
            
            def burst_worker():
                try:
                    start_time = time.time()
                    conn = pool.get_connection(timeout=10)
                    time.sleep(0.02)  # 20ms work
                    pool.return_connection(conn)
                    end_time = time.time()
                    
                    burst_results.append(True)
                    burst_times.append((end_time - start_time) * 1000)
                    
                except Exception as e:
                    burst_errors.append(str(e))
            
            # Create sudden burst of 30 concurrent requests
            burst_threads = []
            for _ in range(30):
                thread = threading.Thread(target=burst_worker)
                burst_threads.append(thread)
                thread.start()
            
            # Wait for burst to complete
            for thread in burst_threads:
                thread.join(timeout=15)
            
            burst_metrics = pool.get_pool_metrics()
            
            # Phase 3: Return to low load
            time.sleep(2)  # Allow pool to scale down
            
            final_results = []
            for i in range(10):
                conn = pool.get_connection()
                time.sleep(0.01)
                pool.return_connection(conn)
                final_results.append(True)
            
            final_metrics = pool.get_pool_metrics()
            
            # Verify burst handling
            self.assertEqual(len(low_load_results), 10)
            self.assertGreater(len(burst_results), 25)  # At least 25/30 successful
            self.assertLess(len(burst_errors), 5)  # Less than 5 failures
            self.assertEqual(len(final_results), 10)
            
            # Verify pool scaling behavior
            self.assertGreater(burst_metrics.peak_usage, initial_metrics.total_connections)
            self.assertLessEqual(burst_metrics.peak_usage, pool.max_pool_size)
            
            # Verify response times during burst
            if burst_times:
                avg_burst_time = statistics.mean(burst_times)
                self.assertLess(avg_burst_time, 5000)  # Under 5 seconds even during burst
            
            print(f"\nBurst Load Test Results:")
            print(f"Low Load Success: {len(low_load_results)}/10")
            print(f"Burst Success: {len(burst_results)}/30")
            print(f"Burst Errors: {len(burst_errors)}")
            print(f"Final Load Success: {len(final_results)}/10")
            print(f"Initial Pool Size: {initial_metrics.total_connections}")
            print(f"Peak Pool Usage: {burst_metrics.peak_usage}")
            print(f"Final Pool Size: {final_metrics.total_connections}")
            if burst_times:
                print(f"Average Burst Response Time: {statistics.mean(burst_times):.2f}ms")
            
        finally:
            pool.shutdown()

    def test_memory_pressure_handling(self):
        """Test pool behavior under simulated memory pressure"""
        # Simulate high memory usage
        self.mock_psutil.virtual_memory.return_value = Mock(percent=85.0)
        
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=3,
            max_pool_size=10,
            max_queue_size=20
        )
        
        try:
            # Perform operations under memory pressure
            results = []
            errors = []
            
            for i in range(100):
                try:
                    conn = pool.get_connection(timeout=5)
                    
                    # Simulate memory-intensive operation
                    time.sleep(0.005)
                    
                    pool.return_connection(conn)
                    results.append(True)
                    
                except Exception as e:
                    errors.append(str(e))
            
            # Verify system handles memory pressure gracefully
            success_rate = len(results) / (len(results) + len(errors))
            self.assertGreater(success_rate, 0.9)  # 90% success rate even under memory pressure
            
            # Verify pool doesn't grow excessively under memory pressure
            metrics = pool.get_pool_metrics()
            self.assertLessEqual(metrics.total_connections, pool.max_pool_size)
            
            print(f"\nMemory Pressure Test Results:")
            print(f"Operations: {len(results) + len(errors)}")
            print(f"Success Rate: {success_rate*100:.2f}%")
            print(f"Final Pool Size: {metrics.total_connections}")
            
        finally:
            pool.shutdown()

    def test_connection_failure_recovery(self):
        """Test pool recovery from connection failures"""
        pool = ConnectionPoolManager(
            account_config=self.account_config,
            min_pool_size=3,
            max_pool_size=8,
            max_queue_size=15
        )
        
        try:
            # Phase 1: Normal operations
            normal_results = []
            for i in range(20):
                conn = pool.get_connection()
                pool.return_connection(conn)
                normal_results.append(True)
            
            initial_metrics = pool.get_pool_metrics()
            
            # Phase 2: Simulate connection failures
            self.mock_client.get_connection_health.return_value = ConnectionHealthStatus(
                status=ConnectionHealth.UNHEALTHY,
                last_check=datetime.now(),
                response_time_ms=10000.0,
                error_count=10,
                last_error="Connection timeout",
                uptime_percentage=10.0
            )
            
            # Continue operations during failures
            failure_results = []
            failure_errors = []
            
            for i in range(30):
                try:
                    conn = pool.get_connection(timeout=3)
                    time.sleep(0.01)
                    pool.return_connection(conn)
                    failure_results.append(True)
                    
                except Exception as e:
                    failure_errors.append(str(e))
            
            # Phase 3: Restore healthy connections
            self.mock_client.get_connection_health.return_value = ConnectionHealthStatus(
                status=ConnectionHealth.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=100.0,
                error_count=0,
                last_error=None,
                uptime_percentage=99.0
            )
            
            # Allow time for recovery
            time.sleep(1)
            
            # Test recovery
            recovery_results = []
            for i in range(20):
                conn = pool.get_connection()
                pool.return_connection(conn)
                recovery_results.append(True)
            
            final_metrics = pool.get_pool_metrics()
            
            # Verify recovery behavior
            self.assertEqual(len(normal_results), 20)
            self.assertEqual(len(recovery_results), 20)
            
            # Some failures are expected during the failure phase
            total_failure_ops = len(failure_results) + len(failure_errors)
            self.assertEqual(total_failure_ops, 30)
            
            # Pool should maintain minimum connections
            self.assertGreaterEqual(final_metrics.total_connections, pool.min_pool_size)
            
            print(f"\nConnection Failure Recovery Test Results:")
            print(f"Normal Phase: {len(normal_results)}/20 successful")
            print(f"Failure Phase: {len(failure_results)}/{total_failure_ops} successful")
            print(f"Recovery Phase: {len(recovery_results)}/20 successful")
            print(f"Initial Pool Size: {initial_metrics.total_connections}")
            print(f"Final Pool Size: {final_metrics.total_connections}")
            
        finally:
            pool.shutdown()


if __name__ == '__main__':
    # Run with verbose output to see performance metrics
    unittest.main(verbosity=2)