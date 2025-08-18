# tests/email/test_smart_polling_integration.py
import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from email.message import EmailMessage

from src.email.smart_polling_engine import SmartPollingEngine, PollingStrategy, LoadMetrics
from src.email.connection_pool import ConnectionPoolManager, PooledConnection
from src.email.godaddy_client import GoDaddyEmailClient, RateLimitInfo, ServerCapabilities
from src.database.manager import DatabaseManager
from src.database.models import EmailMetadata, ProcessingStatus


class TestSmartPollingIntegration:
    """Integration tests for Smart Polling Engine with existing email infrastructure"""
    
    @pytest.fixture
    def mock_godaddy_client(self):
        """Mock GoDaddy email client with realistic behavior"""
        client = Mock(spec=GoDaddyEmailClient)
        
        # Mock server capabilities
        capabilities = ServerCapabilities(
            idle_supported=False,  # Force polling mode
            idle_timeout=None,
            max_connections=10,
            rate_limit_per_minute=60,
            supported_extensions=['IMAP4REV1'],
            last_checked=datetime.now(),
            cache_expires=datetime.now() + timedelta(hours=24)
        )
        client.get_server_capabilities.return_value = capabilities
        
        # Mock rate limit info
        client.get_rate_limit_info.return_value = RateLimitInfo(
            is_rate_limited=False,
            requests_per_minute=60,
            current_usage=0,
            reset_time=None,
            backoff_seconds=0
        )
        
        # Mock email fetching
        client.fetch_unread_emails.return_value = []
        
        return client
    
    @pytest.fixture
    def mock_connection_pool(self, mock_godaddy_client):
        """Mock connection pool with GoDaddy client"""
        pool = Mock(spec=ConnectionPoolManager)
        
        pooled_conn = Mock(spec=PooledConnection)
        pooled_conn.connection = mock_godaddy_client
        pooled_conn.account_id = "test_account"
        pooled_conn.is_healthy = True
        
        pool.get_connection.return_value = pooled_conn
        pool.return_connection.return_value = None
        # Add get_pool_stats method to mock
        pool.get_pool_stats = Mock(return_value=Mock(
            pool_size=5,
            checked_out=1,
            overflow=0,
            checked_in=4,
            total_connections=5,
            failed_connections=0
        ))
        
        return pool
    
    @pytest.fixture
    def mock_database_manager(self):
        """Mock database manager"""
        db = Mock(spec=DatabaseManager)
        
        # Mock email state tracking
        db.get_email_processing_state.return_value = None
        db.create_email_processing_state.return_value = 1
        db.update_email_processing_state.return_value = True
        
        return db
    
    @pytest.fixture
    def integrated_polling_engine(self, mock_connection_pool, mock_database_manager):
        """Create integrated polling engine"""
        def load_monitor():
            return LoadMetrics(
                cpu_usage=35.0,
                memory_usage=45.0,
                active_connections=3,
                queue_depth=8,
                processing_latency=150.0
            )
        
        with patch('src.email.smart_polling_engine.joblib'):
            engine = SmartPollingEngine(
                connection_pool=mock_connection_pool,
                database_manager=mock_database_manager,
                strategy=PollingStrategy.HYBRID,
                base_interval=30,
                load_monitor_callback=load_monitor
            )
            yield engine
            engine.shutdown()

    def test_integration_with_godaddy_client(self, integrated_polling_engine, mock_godaddy_client):
        """Test integration with GoDaddy email client"""
        account_id = "godaddy_integration_test"
        
        # Create test emails
        test_emails = []
        for i in range(3):
            email = EmailMessage()
            email['From'] = f'sender{i}@example.com'
            email['Subject'] = f'Test Email {i}'
            email['Message-ID'] = f'<test{i}@example.com>'
            email.set_content(f'This is test email {i}')
            test_emails.append(email)
        
        # Mock client to return test emails
        mock_godaddy_client.fetch_unread_emails.return_value = test_emails
        
        # Set up email detection callback
        detected_emails = []
        def email_callback(acc_id, emails):
            detected_emails.extend(emails)
        
        integrated_polling_engine.add_email_callback(email_callback)
        
        # Start polling
        integrated_polling_engine.start_adaptive_polling(account_id)
        
        # Wait for polling to occur
        time.sleep(1.0)
        
        # Stop polling
        integrated_polling_engine.stop_polling(account_id)
        
        # Verify integration
        assert mock_godaddy_client.fetch_unread_emails.called
        assert len(detected_emails) > 0
        
        # Verify email metadata creation
        for email_meta in detected_emails:
            assert isinstance(email_meta, EmailMetadata)
            assert email_meta.account_id == account_id
            assert email_meta.sender
            assert email_meta.subject

    def test_rate_limit_integration(self, integrated_polling_engine, mock_godaddy_client):
        """Test integration with rate limiting from GoDaddy client"""
        account_id = "rate_limit_integration"
        
        # Simulate rate limiting
        rate_limited_info = RateLimitInfo(
            is_rate_limited=True,
            requests_per_minute=60,
            current_usage=65,
            reset_time=datetime.now() + timedelta(seconds=45),
            backoff_seconds=45
        )
        
        mock_godaddy_client.get_rate_limit_info.return_value = rate_limited_info
        
        # Start polling
        integrated_polling_engine.start_adaptive_polling(account_id)
        
        # Wait briefly
        time.sleep(0.5)
        
        # Verify rate limit detection
        should_delay = integrated_polling_engine._should_delay_for_rate_limit(account_id)
        delay_time = integrated_polling_engine._get_rate_limit_delay(account_id)
        
        assert should_delay is True
        assert delay_time == 45
        
        # Stop polling
        integrated_polling_engine.stop_polling(account_id)

    def test_connection_pool_integration(self, integrated_polling_engine, mock_connection_pool):
        """Test integration with connection pool manager"""
        account_id = "connection_pool_test"
        
        # Track connection usage
        get_connection_calls = []
        return_connection_calls = []
        
        def track_get_connection():
            get_connection_calls.append(datetime.now())
            return mock_connection_pool.get_connection.return_value
        
        def track_return_connection(conn):
            return_connection_calls.append(datetime.now())
        
        mock_connection_pool.get_connection.side_effect = track_get_connection
        mock_connection_pool.return_connection.side_effect = track_return_connection
        
        # Start polling
        integrated_polling_engine.start_adaptive_polling(account_id)
        
        # Wait for some polling cycles
        time.sleep(1.5)
        
        # Stop polling
        integrated_polling_engine.stop_polling(account_id)
        
        # Verify connection pool usage
        assert len(get_connection_calls) > 0
        assert len(return_connection_calls) > 0
        assert len(get_connection_calls) == len(return_connection_calls)  # Proper cleanup

    def test_database_integration(self, integrated_polling_engine, mock_database_manager):
        """Test integration with database manager"""
        account_id = "database_integration"
        
        # Mock database operations
        email_states = {}
        
        def mock_get_state(uid):
            return email_states.get(uid)
        
        def mock_create_state(state):
            email_states[state.email_uid] = state
            return len(email_states)
        
        mock_database_manager.get_email_processing_state.side_effect = mock_get_state
        mock_database_manager.create_email_processing_state.side_effect = mock_create_state
        
        # Create test scenario with emails
        test_emails = [
            EmailMessage(),
            EmailMessage(),
        ]
        
        for i, email in enumerate(test_emails):
            email['From'] = f'test{i}@example.com'
            email['Subject'] = f'Database Test {i}'
            email['Message-ID'] = f'<dbtest{i}@example.com>'
        
        # Mock client to return emails
        mock_client = integrated_polling_engine.connection_pool.get_connection.return_value.connection
        mock_client.fetch_unread_emails.return_value = test_emails
        
        # Set up callback to simulate database operations
        def email_callback(acc_id, emails):
            for email_meta in emails:
                # Simulate checking if email already processed
                existing_state = mock_database_manager.get_email_processing_state(email_meta.uid)
                if not existing_state:
                    # Create new processing state
                    from src.database.models import EmailProcessingState
                    new_state = EmailProcessingState(
                        email_uid=email_meta.uid,
                        message_id=email_meta.message_id,
                        account_id=acc_id,
                        status=ProcessingStatus.DETECTED,
                        metadata=email_meta
                    )
                    mock_database_manager.create_email_processing_state(new_state)
        
        integrated_polling_engine.add_email_callback(email_callback)
        
        # Start polling
        integrated_polling_engine.start_adaptive_polling(account_id)
        
        # Wait for processing
        time.sleep(1.0)
        
        # Stop polling
        integrated_polling_engine.stop_polling(account_id)
        
        # Verify database integration
        assert len(email_states) > 0
        assert mock_database_manager.get_email_processing_state.called
        assert mock_database_manager.create_email_processing_state.called

    def test_fallback_from_idle_to_polling(self, integrated_polling_engine):
        """Test fallback from IDLE to polling when IDLE is not supported"""
        account_id = "fallback_test"
        
        # Mock server capabilities indicating no IDLE support
        mock_client = integrated_polling_engine.connection_pool.get_connection.return_value.connection
        capabilities = ServerCapabilities(
            idle_supported=False,  # No IDLE support
            idle_timeout=None,
            max_connections=5,
            rate_limit_per_minute=30,
            supported_extensions=['IMAP4REV1'],
            last_checked=datetime.now(),
            cache_expires=datetime.now() + timedelta(hours=24)
        )
        mock_client.get_server_capabilities.return_value = capabilities
        mock_client.test_idle_support.return_value = False
        
        # Track fallback callback
        fallback_calls = []
        def fallback_callback(acc_id):
            fallback_calls.append(acc_id)
        
        # Create new engine with fallback callback
        with patch('src.email.smart_polling_engine.joblib'):
            fallback_engine = SmartPollingEngine(
                connection_pool=integrated_polling_engine.connection_pool,
                database_manager=integrated_polling_engine.database_manager,
                strategy=PollingStrategy.ADAPTIVE_INTERVAL,
                base_interval=30
            )
        
        try:
            # Start polling (should use polling instead of IDLE)
            fallback_engine.start_adaptive_polling(account_id)
            
            # Wait for polling activity
            time.sleep(1.0)
            
            # Verify polling is working
            metrics = fallback_engine.get_polling_metrics(account_id)
            assert metrics.total_polls > 0
            
            # Stop polling
            fallback_engine.stop_polling(account_id)
            
        finally:
            fallback_engine.shutdown()

    def test_multi_account_polling_coordination(self, integrated_polling_engine):
        """Test coordination of polling across multiple email accounts"""
        accounts = ["account_1", "account_2", "account_3"]
        
        # Set up different email patterns for each account
        mock_client = integrated_polling_engine.connection_pool.get_connection.return_value.connection
        
        def mock_fetch_emails():
            # Simulate different email volumes per account
            account_emails = {
                "account_1": 3,  # High volume
                "account_2": 1,  # Medium volume
                "account_3": 0,  # Low volume
            }
            
            # Return emails based on which account is being polled
            # (This is simplified - in reality we'd need to track which account is polling)
            return [EmailMessage() for _ in range(account_emails.get("account_1", 0))]
        
        mock_client.fetch_unread_emails.side_effect = mock_fetch_emails
        
        # Track polling activity per account
        account_activity = {account: [] for account in accounts}
        
        def activity_callback(acc_id, emails):
            account_activity[acc_id].append(len(emails))
        
        integrated_polling_engine.add_email_callback(activity_callback)
        
        # Start polling for all accounts
        for account in accounts:
            integrated_polling_engine.start_adaptive_polling(account)
        
        # Let them run concurrently
        time.sleep(2.0)
        
        # Stop all polling
        for account in accounts:
            integrated_polling_engine.stop_polling(account)
        
        # Verify coordination
        all_metrics = integrated_polling_engine.get_all_metrics()
        
        # All accounts should have some polling activity
        for account in accounts:
            assert account in all_metrics
            assert all_metrics[account].total_polls > 0
        
        # Verify no resource conflicts (all should have reasonable success rates)
        for account in accounts:
            metrics = all_metrics[account]
            assert metrics.success_rate >= 80.0  # At least 80% success rate

    def test_adaptive_interval_based_on_email_patterns(self, integrated_polling_engine):
        """Test adaptive interval adjustment based on real email patterns"""
        account_id = "adaptive_pattern_test"
        
        # Simulate email arrival patterns
        mock_client = integrated_polling_engine.connection_pool.get_connection.return_value.connection
        
        email_sequence = [3, 2, 4, 1, 0, 0, 2, 3, 1, 0]  # Varying email counts
        sequence_index = [0]  # Use list to allow modification in nested function
        
        def mock_fetch_with_pattern():
            if sequence_index[0] < len(email_sequence):
                count = email_sequence[sequence_index[0]]
                sequence_index[0] += 1
                
                emails = []
                for i in range(count):
                    email = EmailMessage()
                    email['From'] = f'pattern{i}@example.com'
                    email['Subject'] = f'Pattern Email {i}'
                    email['Message-ID'] = f'<pattern{sequence_index[0]}{i}@example.com>'
                    emails.append(email)
                
                return emails
            return []
        
        mock_client.fetch_unread_emails.side_effect = mock_fetch_with_pattern
        
        # Track interval changes
        interval_changes = []
        def interval_callback(acc_id, old_int, new_int):
            interval_changes.append((datetime.now(), old_int, new_int))
        
        integrated_polling_engine.add_interval_callback(interval_callback)
        
        # Start polling
        integrated_polling_engine.start_adaptive_polling(account_id)
        
        # Let it adapt over time
        time.sleep(3.0)
        
        # Stop polling
        integrated_polling_engine.stop_polling(account_id)
        
        # Verify adaptive behavior
        metrics = integrated_polling_engine.get_polling_metrics(account_id)
        assert metrics.emails_detected > 0
        assert metrics.interval_adjustments > 0
        
        # Verify interval changes occurred
        assert len(interval_changes) > 0
        
        # Verify patterns were recorded
        patterns = integrated_polling_engine._email_patterns[account_id]
        assert len(patterns) > 0

    def test_error_recovery_and_resilience(self, integrated_polling_engine, mock_godaddy_client):
        """Test error recovery and system resilience"""
        account_id = "error_recovery_test"
        
        # Simulate intermittent connection errors
        call_count = [0]
        
        def mock_fetch_with_errors():
            call_count[0] += 1
            if call_count[0] % 3 == 0:  # Every 3rd call fails
                raise Exception("Simulated connection error")
            return []
        
        mock_godaddy_client.fetch_unread_emails.side_effect = mock_fetch_with_errors
        
        # Start polling
        integrated_polling_engine.start_adaptive_polling(account_id)
        
        # Let it run with errors
        time.sleep(2.0)
        
        # Stop polling
        integrated_polling_engine.stop_polling(account_id)
        
        # Verify error handling
        metrics = integrated_polling_engine.get_polling_metrics(account_id)
        assert metrics.total_polls > 0
        assert metrics.failed_polls > 0
        assert metrics.successful_polls > 0  # Should have some successful polls despite errors
        
        # Verify system continued operating
        assert metrics.success_rate > 0  # Should have some success despite errors

    def test_performance_under_realistic_load(self, integrated_polling_engine):
        """Test performance under realistic email load"""
        accounts = [f"perf_account_{i}" for i in range(5)]
        
        # Mock realistic email volumes
        mock_client = integrated_polling_engine.connection_pool.get_connection.return_value.connection
        
        def mock_realistic_fetch():
            # Simulate realistic email arrival (0-5 emails per poll)
            import random
            email_count = random.randint(0, 5)
            
            emails = []
            for i in range(email_count):
                email = EmailMessage()
                email['From'] = f'realistic{i}@company.com'
                email['Subject'] = f'Business Email {i}'
                email['Message-ID'] = f'<biz{time.time()}{i}@company.com>'
                email.set_content(f'Business email content {i}')
                emails.append(email)
            
            return emails
        
        mock_client.fetch_unread_emails.side_effect = mock_realistic_fetch
        
        # Start performance monitoring
        start_time = time.time()
        
        # Start polling for all accounts
        for account in accounts:
            integrated_polling_engine.start_adaptive_polling(account)
        
        # Run under load
        load_duration = 3.0
        time.sleep(load_duration)
        
        # Collect performance metrics
        all_metrics = integrated_polling_engine.get_all_metrics()
        total_polls = sum(m.total_polls for m in all_metrics.values())
        total_emails = sum(m.emails_detected for m in all_metrics.values())
        total_successful = sum(m.successful_polls for m in all_metrics.values())
        
        # Stop all polling
        for account in accounts:
            integrated_polling_engine.stop_polling(account)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Performance assertions
        overall_success_rate = (total_successful / total_polls * 100) if total_polls > 0 else 0
        polls_per_second = total_polls / actual_duration
        emails_per_second = total_emails / actual_duration
        
        assert overall_success_rate >= 85.0  # At least 85% success rate
        assert polls_per_second >= 0.5  # At least 0.5 polls per second total
        
        print(f"Performance Results:")
        print(f"  Accounts: {len(accounts)}")
        print(f"  Duration: {actual_duration:.1f}s")
        print(f"  Total polls: {total_polls}")
        print(f"  Total emails detected: {total_emails}")
        print(f"  Success rate: {overall_success_rate:.1f}%")
        print(f"  Polls per second: {polls_per_second:.2f}")
        print(f"  Emails per second: {emails_per_second:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])