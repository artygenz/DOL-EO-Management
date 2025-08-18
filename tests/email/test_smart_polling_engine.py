# tests/email/test_smart_polling_engine.py
import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from collections import deque
import numpy as np

from src.email.smart_polling_engine import (
    SmartPollingEngine, PollingStrategy, LoadLevel, EmailPattern,
    PollingInterval, PollingMetrics, LoadMetrics
)
from src.email.connection_pool import ConnectionPoolManager, PooledConnection
from src.database.manager import DatabaseManager
from src.database.models import EmailMetadata
from src.email.godaddy_client import GoDaddyEmailClient, RateLimitInfo


class TestSmartPollingEngine:
    """Test suite for Smart Polling Engine"""
    
    @pytest.fixture
    def mock_connection_pool(self):
        """Mock connection pool manager"""
        pool = Mock(spec=ConnectionPoolManager)
        
        # Mock connection
        mock_connection = Mock(spec=GoDaddyEmailClient)
        mock_connection.fetch_unread_emails.return_value = []
        mock_connection.get_rate_limit_info.return_value = RateLimitInfo(
            is_rate_limited=False,
            requests_per_minute=60,
            current_usage=0,
            reset_time=None,
            backoff_seconds=0
        )
        
        # Mock pooled connection
        pooled_conn = Mock(spec=PooledConnection)
        pooled_conn.connection = mock_connection
        
        pool.get_connection.return_value = pooled_conn
        pool.return_connection.return_value = None
        
        return pool
    
    @pytest.fixture
    def mock_database_manager(self):
        """Mock database manager"""
        return Mock(spec=DatabaseManager)
    
    @pytest.fixture
    def mock_load_monitor(self):
        """Mock load monitor callback"""
        def load_callback():
            return LoadMetrics(
                cpu_usage=30.0,
                memory_usage=40.0,
                active_connections=5,
                queue_depth=10,
                processing_latency=100.0
            )
        return load_callback
    
    @pytest.fixture
    def polling_engine(self, mock_connection_pool, mock_database_manager, mock_load_monitor):
        """Create polling engine instance"""
        with patch('src.email.smart_polling_engine.joblib'):
            engine = SmartPollingEngine(
                connection_pool=mock_connection_pool,
                database_manager=mock_database_manager,
                strategy=PollingStrategy.HYBRID,
                base_interval=60,
                load_monitor_callback=mock_load_monitor
            )
            yield engine
            engine.shutdown()

    def test_initialization(self, polling_engine):
        """Test polling engine initialization"""
        assert polling_engine.strategy == PollingStrategy.HYBRID
        assert polling_engine._default_interval.base_interval == 60
        assert polling_engine._default_interval.min_interval == 30
        assert polling_engine._default_interval.max_interval == 300
        assert len(polling_engine._active_sessions) == 0

    def test_start_adaptive_polling(self, polling_engine):
        """Test starting adaptive polling for an account"""
        account_id = "test_account"
        
        # Start polling
        polling_engine.start_adaptive_polling(account_id)
        
        # Verify session was created
        session_key = f"{account_id}_INBOX"
        assert session_key in polling_engine._active_sessions
        assert session_key in polling_engine._session_control
        
        # Verify thread is running
        thread = polling_engine._active_sessions[session_key]
        assert thread.is_alive()
        
        # Stop polling
        polling_engine.stop_polling(account_id)
        
        # Verify cleanup
        assert session_key not in polling_engine._active_sessions
        assert session_key not in polling_engine._session_control

    def test_duplicate_polling_session(self, polling_engine):
        """Test handling of duplicate polling sessions"""
        account_id = "test_account"
        
        # Start first session
        polling_engine.start_adaptive_polling(account_id)
        
        # Try to start duplicate session
        polling_engine.start_adaptive_polling(account_id)  # Should not create duplicate
        
        # Verify only one session exists
        session_key = f"{account_id}_INBOX"
        assert len([k for k in polling_engine._active_sessions.keys() if k.startswith(account_id)]) == 1
        
        polling_engine.stop_polling(account_id)

    def test_fixed_interval_strategy(self, polling_engine):
        """Test fixed interval polling strategy"""
        polling_engine.set_strategy(PollingStrategy.FIXED_INTERVAL)
        account_id = "test_account"
        
        # Set up polling interval
        polling_engine._polling_intervals[account_id] = PollingInterval(base_interval=120)
        
        # Calculate interval
        interval = polling_engine._calculate_optimal_interval(account_id)
        
        assert interval == 120

    def test_adaptive_interval_strategy(self, polling_engine):
        """Test adaptive interval calculation based on patterns"""
        polling_engine.set_strategy(PollingStrategy.ADAPTIVE_INTERVAL)
        account_id = "test_account"
        
        # Set up polling interval
        polling_engine._polling_intervals[account_id] = PollingInterval(base_interval=60)
        
        # Add some email patterns
        now = datetime.now()
        patterns = deque()
        
        # Add patterns indicating high activity
        for i in range(10):
            pattern = EmailPattern(
                timestamp=now - timedelta(minutes=i*10),
                email_count=3,  # High email count
                account_id=account_id,
                hour_of_day=now.hour,
                day_of_week=now.weekday(),
                is_business_hours=True,
                interval_since_last=300  # 5 minutes
            )
            patterns.append(pattern)
        
        polling_engine._email_patterns[account_id] = patterns
        
        # Calculate adaptive interval
        interval = polling_engine._calculate_adaptive_interval(account_id)
        
        # Should reduce interval due to high activity
        assert interval < 300  # Should be less than the pattern interval
        assert interval >= 30   # Should respect minimum

    def test_load_based_interval_strategy(self, polling_engine):
        """Test load-based interval calculation"""
        polling_engine.set_strategy(PollingStrategy.LOAD_BASED)
        account_id = "test_account"
        
        # Set up polling interval
        polling_engine._polling_intervals[account_id] = PollingInterval(base_interval=60)
        
        # Test with high load
        def high_load_callback():
            return LoadMetrics(
                cpu_usage=85.0,  # High CPU
                memory_usage=90.0,  # High memory
                active_connections=20,
                queue_depth=150,  # High queue depth
                processing_latency=6000.0  # High latency
            )
        
        polling_engine.load_monitor_callback = high_load_callback
        interval = polling_engine._calculate_load_based_interval(account_id)
        
        # Should increase interval due to high load
        assert interval > 60
        assert interval <= 300

    def test_hybrid_interval_strategy(self, polling_engine):
        """Test hybrid interval calculation"""
        polling_engine.set_strategy(PollingStrategy.HYBRID)
        account_id = "test_account"
        
        # Set up polling interval
        polling_engine._polling_intervals[account_id] = PollingInterval(base_interval=60)
        
        # Add some patterns
        now = datetime.now()
        patterns = deque()
        pattern = EmailPattern(
            timestamp=now,
            email_count=1,
            account_id=account_id,
            hour_of_day=now.hour,
            day_of_week=now.weekday(),
            is_business_hours=True,
            interval_since_last=120
        )
        patterns.append(pattern)
        polling_engine._email_patterns[account_id] = patterns
        
        # Calculate hybrid interval
        interval = polling_engine._calculate_hybrid_interval(account_id)
        
        # Should be within reasonable bounds
        assert 30 <= interval <= 300

    def test_rate_limit_detection(self, polling_engine, mock_connection_pool):
        """Test rate limit detection and handling"""
        account_id = "test_account"
        
        # Mock rate limited connection
        mock_connection = mock_connection_pool.get_connection.return_value.connection
        mock_connection.get_rate_limit_info.return_value = RateLimitInfo(
            is_rate_limited=True,
            requests_per_minute=60,
            current_usage=65,
            reset_time=datetime.now() + timedelta(seconds=30),
            backoff_seconds=30
        )
        
        # Test rate limit detection
        should_delay = polling_engine._should_delay_for_rate_limit(account_id)
        assert should_delay is True
        
        # Test delay calculation
        delay = polling_engine._get_rate_limit_delay(account_id)
        assert delay == 30

    def test_email_pattern_recording(self, polling_engine):
        """Test email pattern recording and analysis"""
        account_id = "test_account"
        
        # Record some patterns
        last_poll_time = datetime.now() - timedelta(minutes=5)
        polling_engine._record_email_pattern(account_id, 3, last_poll_time)
        
        # Verify pattern was recorded
        patterns = polling_engine._email_patterns[account_id]
        assert len(patterns) == 1
        
        pattern = patterns[0]
        assert pattern.email_count == 3
        assert pattern.account_id == account_id
        assert pattern.interval_since_last == pytest.approx(300, abs=10)  # ~5 minutes

    def test_interval_adjustment_after_success(self, polling_engine):
        """Test interval adjustment after successful email detection"""
        account_id = "test_account"
        
        # Set up initial interval
        polling_engine._polling_intervals[account_id] = PollingInterval(base_interval=120)
        
        # Track interval changes
        interval_changes = []
        def interval_callback(acc_id, old_int, new_int):
            interval_changes.append((acc_id, old_int, new_int))
        
        polling_engine.add_interval_callback(interval_callback)
        
        # Adjust interval after success
        polling_engine._adjust_interval_after_success(account_id)
        
        # Verify interval was reduced
        new_interval = polling_engine._polling_intervals[account_id].base_interval
        assert new_interval < 120
        assert len(interval_changes) == 1

    def test_interval_adjustment_after_empty_polls(self, polling_engine):
        """Test interval adjustment after consecutive empty polls"""
        account_id = "test_account"
        
        # Set up initial interval
        polling_engine._polling_intervals[account_id] = PollingInterval(base_interval=60)
        
        # Track interval changes
        interval_changes = []
        def interval_callback(acc_id, old_int, new_int):
            interval_changes.append((acc_id, old_int, new_int))
        
        polling_engine.add_interval_callback(interval_callback)
        
        # Adjust interval after empty polls
        polling_engine._adjust_interval_after_empty_polls(account_id, 5)
        
        # Verify interval was increased
        new_interval = polling_engine._polling_intervals[account_id].base_interval
        assert new_interval > 60
        assert len(interval_changes) == 1

    def test_polling_metrics_update(self, polling_engine):
        """Test polling metrics tracking"""
        account_id = "test_account"
        
        # Update metrics for successful poll
        polling_engine._update_polling_metrics(account_id, 0.5, 2, True)
        
        metrics = polling_engine.get_polling_metrics(account_id)
        assert metrics.total_polls == 1
        assert metrics.successful_polls == 1
        assert metrics.emails_detected == 2
        assert metrics.average_response_time == 500.0  # 0.5s in ms
        
        # Update metrics for failed poll
        polling_engine._update_polling_metrics(account_id, 0.0, 0, False)
        
        metrics = polling_engine.get_polling_metrics(account_id)
        assert metrics.total_polls == 2
        assert metrics.successful_polls == 1
        assert metrics.failed_polls == 1
        assert metrics.success_rate == 50.0

    def test_load_metrics_calculation(self, polling_engine):
        """Test load level calculation from metrics"""
        # Test low load
        low_load = LoadMetrics(
            cpu_usage=20.0,
            memory_usage=30.0,
            active_connections=2,
            queue_depth=5,
            processing_latency=500.0
        )
        assert low_load.get_load_level() == LoadLevel.LOW
        
        # Test medium load
        medium_load = LoadMetrics(
            cpu_usage=50.0,
            memory_usage=60.0,
            active_connections=10,
            queue_depth=30,
            processing_latency=1500.0
        )
        assert medium_load.get_load_level() == LoadLevel.MEDIUM
        
        # Test high load
        high_load = LoadMetrics(
            cpu_usage=70.0,
            memory_usage=75.0,
            active_connections=15,
            queue_depth=60,
            processing_latency=3000.0
        )
        assert high_load.get_load_level() == LoadLevel.HIGH
        
        # Test critical load
        critical_load = LoadMetrics(
            cpu_usage=90.0,
            memory_usage=95.0,
            active_connections=25,
            queue_depth=150,
            processing_latency=8000.0
        )
        assert critical_load.get_load_level() == LoadLevel.CRITICAL

    def test_email_callback_notification(self, polling_engine):
        """Test email detection callback notification"""
        account_id = "test_account"
        
        # Set up callback
        detected_emails = []
        def email_callback(acc_id, emails):
            detected_emails.append((acc_id, emails))
        
        polling_engine.add_email_callback(email_callback)
        
        # Create test emails
        test_emails = [
            EmailMetadata(
                uid="test_uid_1",
                message_id="msg_1",
                sender="test@example.com",
                subject="Test Email 1",
                received_date=datetime.now(),
                account_id=account_id
            )
        ]
        
        # Notify callbacks
        polling_engine._notify_email_callbacks(account_id, test_emails)
        
        # Verify callback was called
        assert len(detected_emails) == 1
        assert detected_emails[0][0] == account_id
        assert len(detected_emails[0][1]) == 1

    def test_ml_model_training_data_collection(self, polling_engine):
        """Test ML model training data collection"""
        account_id = "test_account"
        
        # Record patterns to generate training data
        for i in range(10):
            last_poll_time = datetime.now() - timedelta(minutes=i*5)
            polling_engine._record_email_pattern(account_id, i % 3, last_poll_time)
        
        # Verify feature history was populated
        assert len(polling_engine._feature_history) == 10
        
        # Verify feature structure
        feature_data = polling_engine._feature_history[0]
        assert 'features' in feature_data
        assert 'target' in feature_data
        assert 'timestamp' in feature_data
        assert len(feature_data['features']) == 5  # Expected feature count

    def test_pattern_analysis_insights(self, polling_engine):
        """Test email pattern analysis for insights"""
        account_id = "test_account"
        
        # Add patterns with different characteristics
        now = datetime.now()
        patterns = deque()
        
        # Morning patterns (high activity)
        for i in range(5):
            pattern = EmailPattern(
                timestamp=now.replace(hour=9) - timedelta(days=i),
                email_count=5,
                account_id=account_id,
                hour_of_day=9,
                day_of_week=1,  # Monday
                is_business_hours=True,
                interval_since_last=600
            )
            patterns.append(pattern)
        
        # Evening patterns (low activity)
        for i in range(5):
            pattern = EmailPattern(
                timestamp=now.replace(hour=18) - timedelta(days=i),
                email_count=1,
                account_id=account_id,
                hour_of_day=18,
                day_of_week=1,
                is_business_hours=False,
                interval_since_last=1800
            )
            patterns.append(pattern)
        
        polling_engine._email_patterns[account_id] = patterns
        
        # Run pattern analysis
        polling_engine._analyze_patterns()
        
        # Verify analysis completed without errors
        assert len(polling_engine._email_patterns[account_id]) == 10

    def test_concurrent_polling_sessions(self, polling_engine):
        """Test multiple concurrent polling sessions"""
        accounts = ["account_1", "account_2", "account_3"]
        
        # Start polling for multiple accounts
        for account in accounts:
            polling_engine.start_adaptive_polling(account)
        
        # Verify all sessions are active
        assert len(polling_engine._active_sessions) == 3
        
        # Verify all threads are running
        for account in accounts:
            session_key = f"{account}_INBOX"
            thread = polling_engine._active_sessions[session_key]
            assert thread.is_alive()
        
        # Stop all sessions
        for account in accounts:
            polling_engine.stop_polling(account)
        
        # Verify cleanup
        assert len(polling_engine._active_sessions) == 0

    def test_error_handling_in_polling_worker(self, polling_engine, mock_connection_pool):
        """Test error handling in polling worker"""
        account_id = "test_account"
        
        # Mock connection to raise exception
        mock_connection = mock_connection_pool.get_connection.return_value.connection
        mock_connection.fetch_unread_emails.side_effect = Exception("Connection failed")
        
        # Start polling
        polling_engine.start_adaptive_polling(account_id)
        
        # Wait a bit for polling attempts
        time.sleep(0.5)
        
        # Verify metrics show failed polls
        metrics = polling_engine.get_polling_metrics(account_id)
        assert metrics.failed_polls > 0
        
        polling_engine.stop_polling(account_id)

    def test_shutdown_cleanup(self, polling_engine):
        """Test proper cleanup during shutdown"""
        account_id = "test_account"
        
        # Start polling
        polling_engine.start_adaptive_polling(account_id)
        
        # Verify session is active
        assert len(polling_engine._active_sessions) == 1
        
        # Shutdown engine
        polling_engine.shutdown()
        
        # Verify cleanup
        assert len(polling_engine._active_sessions) == 0
        assert polling_engine._shutdown_event.is_set()


class TestPollingEnginePerformance:
    """Performance tests for Smart Polling Engine"""
    
    @pytest.fixture
    def performance_engine(self):
        """Create polling engine for performance testing"""
        mock_pool = Mock(spec=ConnectionPoolManager)
        mock_db = Mock(spec=DatabaseManager)
        
        # Mock fast connection
        mock_connection = Mock(spec=GoDaddyEmailClient)
        mock_connection.fetch_unread_emails.return_value = []
        mock_connection.get_rate_limit_info.return_value = RateLimitInfo(
            is_rate_limited=False,
            requests_per_minute=60,
            current_usage=0,
            reset_time=None,
            backoff_seconds=0
        )
        
        pooled_conn = Mock(spec=PooledConnection)
        pooled_conn.connection = mock_connection
        mock_pool.get_connection.return_value = pooled_conn
        
        with patch('src.email.smart_polling_engine.joblib'):
            engine = SmartPollingEngine(
                connection_pool=mock_pool,
                database_manager=mock_db,
                strategy=PollingStrategy.HYBRID,
                base_interval=10  # Fast polling for testing
            )
            yield engine
            engine.shutdown()

    def test_polling_efficiency_under_load(self, performance_engine):
        """Test polling efficiency under high load"""
        accounts = [f"account_{i}" for i in range(10)]
        
        start_time = time.time()
        
        # Start polling for multiple accounts
        for account in accounts:
            performance_engine.start_adaptive_polling(account)
        
        # Let it run for a short time
        time.sleep(2.0)
        
        # Check metrics
        total_polls = 0
        total_successful = 0
        
        for account in accounts:
            metrics = performance_engine.get_polling_metrics(account)
            total_polls += metrics.total_polls
            total_successful += metrics.successful_polls
        
        # Stop all polling
        for account in accounts:
            performance_engine.stop_polling(account)
        
        elapsed_time = time.time() - start_time
        
        # Verify performance metrics
        assert total_polls > 0
        success_rate = (total_successful / total_polls) * 100 if total_polls > 0 else 0
        assert success_rate > 80  # At least 80% success rate
        
        # Verify reasonable polling frequency
        polls_per_second = total_polls / elapsed_time
        assert polls_per_second > 0.5  # At least 0.5 polls per second across all accounts

    def test_interval_adjustment_responsiveness(self, performance_engine):
        """Test responsiveness of interval adjustments"""
        account_id = "test_account"
        
        # Track interval changes
        interval_changes = []
        def track_changes(acc_id, old_int, new_int):
            interval_changes.append((time.time(), old_int, new_int))
        
        performance_engine.add_interval_callback(track_changes)
        
        # Start with base interval
        performance_engine._polling_intervals[account_id] = PollingInterval(base_interval=60)
        
        # Simulate successful email detection (should reduce interval)
        start_time = time.time()
        performance_engine._adjust_interval_after_success(account_id)
        
        # Simulate empty polls (should increase interval)
        performance_engine._adjust_interval_after_empty_polls(account_id, 5)
        
        end_time = time.time()
        
        # Verify adjustments were made quickly
        assert len(interval_changes) == 2
        adjustment_time = end_time - start_time
        assert adjustment_time < 0.1  # Should be very fast

    def test_memory_usage_with_pattern_history(self, performance_engine):
        """Test memory usage with large pattern history"""
        account_id = "test_account"
        
        # Generate large number of patterns
        for i in range(2000):  # More than the deque maxlen
            last_poll_time = datetime.now() - timedelta(minutes=i)
            performance_engine._record_email_pattern(account_id, i % 5, last_poll_time)
        
        # Verify deque size is limited
        patterns = performance_engine._email_patterns[account_id]
        assert len(patterns) <= 1000  # Should be limited by maxlen
        
        # Verify feature history is also limited
        assert len(performance_engine._feature_history) <= 10000

    def test_concurrent_access_thread_safety(self, performance_engine):
        """Test thread safety under concurrent access"""
        account_id = "test_account"
        
        # Function to record patterns concurrently
        def record_patterns():
            for i in range(100):
                last_poll_time = datetime.now() - timedelta(seconds=i)
                performance_engine._record_email_pattern(account_id, i % 3, last_poll_time)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=record_patterns)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify data integrity
        patterns = performance_engine._email_patterns[account_id]
        assert len(patterns) > 0
        assert len(patterns) <= 1000  # Should respect maxlen

    def test_ml_prediction_performance(self, performance_engine):
        """Test ML prediction performance"""
        account_id = "test_account"
        
        # Initialize polling interval for the account
        performance_engine._polling_intervals[account_id] = PollingInterval(base_interval=60)
        
        # Set up ML components
        performance_engine._ml_model = Mock()
        performance_engine._scaler = Mock()
        
        # Mock prediction
        performance_engine._ml_model.predict.return_value = [2.5]
        performance_engine._scaler.transform.return_value = [[1, 2, 3, 4, 5]]
        
        # Time ML predictions
        start_time = time.time()
        
        for _ in range(100):
            interval = performance_engine._calculate_ml_optimized_interval(account_id)
        
        end_time = time.time()
        
        # Verify predictions are fast
        avg_prediction_time = (end_time - start_time) / 100
        assert avg_prediction_time < 0.01  # Less than 10ms per prediction

    def test_rate_limit_backoff_efficiency(self, performance_engine):
        """Test efficiency of rate limit backoff"""
        account_id = "test_account"
        
        # Mock rate limited connection
        mock_connection = performance_engine.connection_pool.get_connection.return_value.connection
        
        # Test progressive backoff
        backoff_times = []
        
        for usage in [10, 20, 30, 40, 50]:
            mock_connection.get_rate_limit_info.return_value = RateLimitInfo(
                is_rate_limited=True,
                requests_per_minute=60,
                current_usage=usage,
                reset_time=datetime.now() + timedelta(seconds=30),
                backoff_seconds=30
            )
            
            start_time = time.time()
            delay = performance_engine._get_rate_limit_delay(account_id)
            end_time = time.time()
            
            backoff_times.append(end_time - start_time)
            assert delay > 0
        
        # Verify backoff calculation is consistent and reasonably fast
        assert all(t < 0.1 for t in backoff_times)  # Should be reasonably fast calculation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])