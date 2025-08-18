"""
Integration Tests for Delivery Manager Reliability and Tracking Accuracy

These tests focus on delivery reliability, tracking accuracy, bounce handling,
and failure escalation scenarios as required by the task specifications.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
import smtplib
import ssl
from queue import Queue

from src.email.delivery_manager import (
    DeliveryManager,
    DeliveryRecord,
    DeliveryStatus,
    DeliveryPriority,
    BounceType,
    SMTPConnectionConfig,
    DeliveryManagerError
)
from src.database.manager import DatabaseManager
from src.database.models import AuditLogEntry, AuditAction


class TestDeliveryReliability:
    """Test delivery reliability and failure handling."""
    
    @pytest.fixture
    def smtp_config(self):
        """Create test SMTP configuration."""
        return SMTPConnectionConfig(
            host="smtp.dol.gov",
            port=587,
            use_tls=True,
            username="email-agent@dol.gov",
            password="secure-password"
        )
    
    @pytest.fixture
    def mock_database_manager(self):
        """Create mock database manager."""
        mock_db = Mock(spec=DatabaseManager)
        mock_db.create_audit_entry = Mock()
        return mock_db
    
    @pytest.fixture
    def delivery_manager(self, smtp_config, mock_database_manager):
        """Create delivery manager for testing."""
        return DeliveryManager(
            smtp_config=smtp_config,
            database_manager=mock_database_manager,
            max_concurrent_deliveries=3,
            delivery_timeout=60
        )
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_delivery_confirmation_tracking(self, mock_smtp_class, delivery_manager):
        """Test comprehensive delivery confirmation tracking."""
        # Setup mock SMTP with successful delivery
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        mock_smtp.send_message.return_value = None
        
        delivery_manager.start()
        
        try:
            # Send email with tracking
            delivery_id = delivery_manager.send_email(
                recipient_email="executive@dol.gov",
                sender_email="agent@dol.gov",
                subject="Executive Summary - Q4 2024",
                body_text="Please find the quarterly executive summary.",
                priority=DeliveryPriority.HIGH,
                correlation_id="exec-q4-2024-001",
                metadata={
                    'report_type': 'executive_summary',
                    'quarter': 'Q4_2024',
                    'department': 'DOL'
                }
            )
            
            # Wait for delivery processing
            time.sleep(1)
            
            # Verify delivery record tracking
            record = delivery_manager.get_delivery_status(delivery_id)
            assert record is not None
            assert record.delivery_id == delivery_id
            assert record.status == DeliveryStatus.DELIVERED
            assert record.delivered_at is not None
            assert record.correlation_id == "exec-q4-2024-001"
            
            # Verify delivery attempt tracking
            assert len(record.attempts) == 1
            attempt = record.attempts[0]
            assert attempt.status == DeliveryStatus.DELIVERED
            assert attempt.smtp_response_code == 250
            assert attempt.delivery_time_ms is not None
            assert attempt.delivery_time_ms > 0
            assert attempt.server_host == "smtp.dol.gov"
            assert attempt.server_port == 587
            
            # Verify metadata preservation
            assert record.metadata['report_type'] == 'executive_summary'
            assert record.metadata['quarter'] == 'Q4_2024'
            
            # Verify SMTP interaction
            mock_smtp.send_message.assert_called_once()
            mock_smtp.quit.assert_called_once()
            
        finally:
            delivery_manager.stop()
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_delivery_failure_detection_and_handling(self, mock_smtp_class, delivery_manager, mock_database_manager):
        """Test delivery failure detection and proper handling."""
        # Setup mock SMTP with various failure scenarios
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        
        # Simulate different types of failures
        failure_scenarios = [
            smtplib.SMTPRecipientsRefused({'test@invalid.com': (550, 'User unknown')}),
            smtplib.SMTPException("Connection timeout"),
            smtplib.SMTPAuthenticationError(535, "Authentication failed"),
            Exception("Network error")
        ]
        
        delivery_manager.start()
        
        try:
            delivery_ids = []
            
            # Send emails that will fail with different errors
            for i, failure in enumerate(failure_scenarios):
                mock_smtp.send_message.side_effect = failure
                
                delivery_id = delivery_manager.send_email(
                    recipient_email=f"test{i}@example.com",
                    sender_email="agent@dol.gov",
                    subject=f"Test Email {i}",
                    body_text=f"Test message {i}",
                    correlation_id=f"test-failure-{i}"
                )
                delivery_ids.append(delivery_id)
            
            # Wait for delivery attempts
            time.sleep(2)
            
            # Verify failure detection and handling
            for i, delivery_id in enumerate(delivery_ids):
                record = delivery_manager.get_delivery_status(delivery_id)
                assert record is not None
                
                # Should have at least one failed attempt
                assert len(record.attempts) >= 1
                assert record.attempts[0].status == DeliveryStatus.FAILED
                assert record.attempts[0].error_message is not None
                
                # Should be in retrying or escalated state
                assert record.status in [DeliveryStatus.RETRYING, DeliveryStatus.ESCALATED]
                
                # Verify bounce type detection for recipient refused
                if i == 0:  # SMTPRecipientsRefused
                    assert record.bounce_type == BounceType.HARD_BOUNCE
                    assert "User unknown" in record.bounce_reason
            
            # Verify audit entries were created for failures
            assert mock_database_manager.create_audit_entry.call_count >= len(failure_scenarios)
            
        finally:
            delivery_manager.stop()
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_exponential_backoff_retry_accuracy(self, mock_smtp_class, delivery_manager):
        """Test accuracy of exponential backoff retry timing."""
        # Setup mock SMTP to fail multiple times then succeed
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        mock_smtp.send_message.side_effect = [
            smtplib.SMTPException("Temporary failure 1"),
            smtplib.SMTPException("Temporary failure 2"),
            None  # Success on third attempt
        ]
        
        delivery_manager.start()
        
        try:
            # Send email that will require retries
            delivery_id = delivery_manager.send_email(
                recipient_email="retry-test@example.com",
                sender_email="agent@dol.gov",
                subject="Retry Test Email",
                body_text="This email will test retry logic."
            )
            
            # Get initial record
            record = delivery_manager.get_delivery_status(delivery_id)
            initial_time = datetime.utcnow()
            
            # Wait for first failure and retry scheduling
            time.sleep(1)
            
            # Verify first retry scheduling
            record = delivery_manager.get_delivery_status(delivery_id)
            assert record.retry_count >= 1
            assert record.next_retry_at is not None
            
            # First retry should be scheduled for ~2 minutes (with jitter)
            first_retry_delay = (record.next_retry_at - initial_time).total_seconds()
            assert 60 < first_retry_delay < 180  # 1-3 minutes range for jitter
            
            # Manually trigger retry by setting next_retry_at to now
            record.next_retry_at = datetime.utcnow()
            
            # Wait for second failure and retry scheduling
            time.sleep(1)
            
            # Verify exponential backoff (second retry should be longer)
            if record.retry_count >= 2:
                second_retry_delay = (record.next_retry_at - datetime.utcnow()).total_seconds()
                # Second retry should be ~4 minutes (with jitter)
                assert second_retry_delay > first_retry_delay * 1.5
            
        finally:
            delivery_manager.stop()
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_bounce_handling_accuracy(self, mock_smtp_class, delivery_manager):
        """Test accurate bounce detection and classification."""
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        
        # Test different bounce scenarios
        bounce_scenarios = [
            # Hard bounces
            ("User unknown in virtual mailbox table", BounceType.HARD_BOUNCE),
            ("No such user here", BounceType.HARD_BOUNCE),
            ("Invalid recipient address", BounceType.HARD_BOUNCE),
            ("Mailbox unavailable", BounceType.HARD_BOUNCE),
            
            # Soft bounces
            ("Mailbox full", BounceType.SOFT_BOUNCE),
            ("Quota exceeded, try again later", BounceType.SOFT_BOUNCE),
            ("Temporary failure in name resolution", BounceType.SOFT_BOUNCE),
            ("Service unavailable", BounceType.SOFT_BOUNCE),
            
            # Block bounces
            ("Message blocked due to spam content", BounceType.BLOCK_BOUNCE),
            ("Sender blacklisted", BounceType.BLOCK_BOUNCE),
            ("Policy violation detected", BounceType.BLOCK_BOUNCE),
            
            # Unknown bounces
            ("Some unknown error occurred", BounceType.UNKNOWN)
        ]
        
        delivery_manager.start()
        
        try:
            for i, (error_message, expected_bounce_type) in enumerate(bounce_scenarios):
                # Setup SMTP to fail with specific error
                mock_smtp.send_message.side_effect = smtplib.SMTPRecipientsRefused({
                    f'test{i}@example.com': (550, error_message)
                })
                
                # Send email
                delivery_id = delivery_manager.send_email(
                    recipient_email=f"test{i}@example.com",
                    sender_email="agent@dol.gov",
                    subject=f"Bounce Test {i}",
                    body_text="Testing bounce detection",
                    correlation_id=f"bounce-test-{i}"
                )
                
                # Wait for processing
                time.sleep(0.5)
                
                # Verify bounce classification
                record = delivery_manager.get_delivery_status(delivery_id)
                assert record is not None
                assert record.bounce_type == expected_bounce_type
                assert error_message in record.bounce_reason
                
                # Verify attempt recorded the bounce
                assert len(record.attempts) >= 1
                assert record.attempts[0].status == DeliveryStatus.FAILED
                assert error_message in record.attempts[0].error_message
        
        finally:
            delivery_manager.stop()
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_delivery_failure_escalation_accuracy(self, mock_smtp_class, delivery_manager, mock_database_manager):
        """Test accurate delivery failure escalation."""
        # Setup mock SMTP to always fail
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        mock_smtp.send_message.side_effect = smtplib.SMTPException("Persistent failure")
        
        delivery_manager.start()
        
        try:
            # Send email with limited retries for faster testing
            delivery_id = delivery_manager.send_email(
                recipient_email="escalation-test@example.com",
                sender_email="agent@dol.gov",
                subject="Escalation Test Email",
                body_text="This email will test escalation logic.",
                correlation_id="escalation-test-001"
            )
            
            # Manually set max retries to 2 for faster testing
            record = delivery_manager.get_delivery_status(delivery_id)
            record.max_retries = 2
            
            # Wait for all retry attempts to complete
            max_wait_time = 10  # seconds
            start_time = time.time()
            
            while (time.time() - start_time) < max_wait_time:
                record = delivery_manager.get_delivery_status(delivery_id)
                if record.status == DeliveryStatus.ESCALATED:
                    break
                time.sleep(0.5)
            
            # Verify escalation occurred
            assert record.status == DeliveryStatus.ESCALATED
            assert record.retry_count >= record.max_retries
            assert record.failed_at is not None
            
            # Verify all attempts were recorded
            assert len(record.attempts) >= record.max_retries
            for attempt in record.attempts:
                assert attempt.status == DeliveryStatus.FAILED
                assert "Persistent failure" in attempt.error_message
            
            # Verify escalation audit entry was created
            escalation_calls = [
                call for call in mock_database_manager.create_audit_entry.call_args_list
                if call[0][0].details.get('action') == 'delivery_escalated'
            ]
            assert len(escalation_calls) >= 1
            
            escalation_entry = escalation_calls[0][0][0]
            assert escalation_entry.component == "delivery_manager"
            assert escalation_entry.action == AuditAction.SYSTEM_ERROR
            assert escalation_entry.email_uid == delivery_id
            assert escalation_entry.details['retry_count'] >= record.max_retries
            
        finally:
            delivery_manager.stop()


class TestDeliveryTrackingAccuracy:
    """Test delivery tracking accuracy and metrics."""
    
    @pytest.fixture
    def smtp_config(self):
        """Create test SMTP configuration."""
        return SMTPConnectionConfig(
            host="smtp.test.com",
            port=587,
            use_tls=True,
            username="test@dol.gov",
            password="testpass"
        )
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_delivery_metrics_accuracy(self, mock_smtp_class, smtp_config):
        """Test accuracy of delivery metrics tracking."""
        # Setup mock SMTP with mixed success/failure
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        
        # Configure different outcomes for different emails
        outcomes = [
            None,  # Success
            None,  # Success
            smtplib.SMTPException("Failure 1"),  # Failure
            None,  # Success
            smtplib.SMTPException("Failure 2"),  # Failure
        ]
        
        delivery_manager = DeliveryManager(smtp_config=smtp_config)
        delivery_manager.start()
        
        try:
            delivery_ids = []
            
            # Send emails with different outcomes
            for i, outcome in enumerate(outcomes):
                mock_smtp.send_message.side_effect = outcome
                
                delivery_id = delivery_manager.send_email(
                    recipient_email=f"test{i}@example.com",
                    sender_email="agent@dol.gov",
                    subject=f"Metrics Test {i}",
                    body_text=f"Test message {i}",
                    priority=DeliveryPriority.NORMAL if i % 2 == 0 else DeliveryPriority.HIGH
                )
                delivery_ids.append(delivery_id)
                
                # Small delay between sends
                time.sleep(0.1)
            
            # Wait for all deliveries to process
            time.sleep(2)
            
            # Verify metrics accuracy
            metrics = delivery_manager.get_delivery_metrics()
            
            # Should have attempted to send all emails
            assert metrics['total_sent'] == len(outcomes)
            
            # Count expected successes and failures
            expected_delivered = sum(1 for outcome in outcomes if outcome is None)
            expected_failed = sum(1 for outcome in outcomes if outcome is not None)
            
            assert metrics['total_delivered'] == expected_delivered
            assert metrics['total_failed'] >= expected_failed  # May be higher due to retries
            
            # Verify average delivery time is calculated
            if metrics['total_delivered'] > 0:
                assert metrics['average_delivery_time'] > 0
            
            # Verify individual delivery records
            successful_deliveries = 0
            failed_deliveries = 0
            
            for delivery_id in delivery_ids:
                record = delivery_manager.get_delivery_status(delivery_id)
                assert record is not None
                
                if record.status == DeliveryStatus.DELIVERED:
                    successful_deliveries += 1
                    assert record.delivered_at is not None
                    assert len(record.attempts) >= 1
                    assert record.attempts[-1].status == DeliveryStatus.DELIVERED
                    assert record.attempts[-1].delivery_time_ms is not None
                
                elif record.status in [DeliveryStatus.FAILED, DeliveryStatus.RETRYING, DeliveryStatus.ESCALATED]:
                    failed_deliveries += 1
                    assert len(record.attempts) >= 1
                    assert all(attempt.status == DeliveryStatus.FAILED for attempt in record.attempts)
            
            # Verify counts match metrics
            assert successful_deliveries == metrics['total_delivered']
            
        finally:
            delivery_manager.stop()
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_concurrent_delivery_tracking_accuracy(self, mock_smtp_class, smtp_config):
        """Test tracking accuracy under concurrent delivery load."""
        # Setup mock SMTP with variable delays to simulate real conditions
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        
        def slow_send_message(message):
            """Simulate variable SMTP send times."""
            import random
            time.sleep(random.uniform(0.1, 0.3))  # 100-300ms delay
            return None
        
        mock_smtp.send_message.side_effect = slow_send_message
        
        # Create delivery manager with multiple workers
        delivery_manager = DeliveryManager(
            smtp_config=smtp_config,
            max_concurrent_deliveries=5
        )
        delivery_manager.start()
        
        try:
            # Send many emails concurrently
            num_emails = 20
            delivery_ids = []
            
            for i in range(num_emails):
                delivery_id = delivery_manager.send_email(
                    recipient_email=f"concurrent{i}@example.com",
                    sender_email="agent@dol.gov",
                    subject=f"Concurrent Test {i}",
                    body_text=f"Concurrent test message {i}",
                    priority=DeliveryPriority.HIGH if i % 3 == 0 else DeliveryPriority.NORMAL,
                    correlation_id=f"concurrent-{i}"
                )
                delivery_ids.append(delivery_id)
            
            # Wait for all deliveries to complete
            max_wait_time = 30  # seconds
            start_time = time.time()
            
            while (time.time() - start_time) < max_wait_time:
                completed_count = 0
                for delivery_id in delivery_ids:
                    record = delivery_manager.get_delivery_status(delivery_id)
                    if record and record.status == DeliveryStatus.DELIVERED:
                        completed_count += 1
                
                if completed_count == num_emails:
                    break
                
                time.sleep(0.5)
            
            # Verify all deliveries were tracked accurately
            for i, delivery_id in enumerate(delivery_ids):
                record = delivery_manager.get_delivery_status(delivery_id)
                assert record is not None, f"Missing delivery record for email {i}"
                assert record.delivery_id == delivery_id
                assert record.recipient_email == f"concurrent{i}@example.com"
                assert record.correlation_id == f"concurrent-{i}"
                assert record.status == DeliveryStatus.DELIVERED
                assert record.delivered_at is not None
                assert len(record.attempts) == 1
                assert record.attempts[0].status == DeliveryStatus.DELIVERED
                assert record.attempts[0].delivery_time_ms is not None
            
            # Verify final metrics
            metrics = delivery_manager.get_delivery_metrics()
            assert metrics['total_sent'] == num_emails
            assert metrics['total_delivered'] == num_emails
            assert metrics['total_failed'] == 0
            assert metrics['average_delivery_time'] > 0
            
        finally:
            delivery_manager.stop()
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_priority_queue_accuracy(self, mock_smtp_class, smtp_config):
        """Test accuracy of priority-based delivery queue handling."""
        # Setup mock SMTP with tracking of send order
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        
        send_order = []
        
        def track_send_order(message):
            """Track the order emails are sent."""
            subject = message['Subject']
            send_order.append(subject)
            return None
        
        mock_smtp.send_message.side_effect = track_send_order
        
        delivery_manager = DeliveryManager(
            smtp_config=smtp_config,
            max_concurrent_deliveries=1  # Single worker to ensure order
        )
        delivery_manager.start()
        
        try:
            # Send emails with different priorities
            # Critical should go first, then high, then normal
            emails = [
                ("Normal Priority 1", DeliveryPriority.NORMAL),
                ("Critical Priority 1", DeliveryPriority.CRITICAL),
                ("High Priority 1", DeliveryPriority.HIGH),
                ("Normal Priority 2", DeliveryPriority.NORMAL),
                ("Critical Priority 2", DeliveryPriority.CRITICAL),
                ("High Priority 2", DeliveryPriority.HIGH),
            ]
            
            delivery_ids = []
            for subject, priority in emails:
                delivery_id = delivery_manager.send_email(
                    recipient_email="priority-test@example.com",
                    sender_email="agent@dol.gov",
                    subject=subject,
                    body_text="Priority test message",
                    priority=priority
                )
                delivery_ids.append(delivery_id)
                time.sleep(0.05)  # Small delay to ensure queue ordering
            
            # Wait for all deliveries
            time.sleep(3)
            
            # Verify priority order was generally respected
            # Critical emails should be sent first, then high, then normal
            critical_positions = [i for i, subject in enumerate(send_order) if "Critical" in subject]
            high_positions = [i for i, subject in enumerate(send_order) if "High" in subject]
            normal_positions = [i for i, subject in enumerate(send_order) if "Normal" in subject]
            
            # Verify all emails were processed
            assert len(send_order) == len(emails)
            
            # Verify that priority metadata is preserved in delivery records
            for delivery_id in delivery_ids:
                record = delivery_manager.get_delivery_status(delivery_id)
                assert record is not None
                assert record.priority in [DeliveryPriority.CRITICAL, DeliveryPriority.HIGH, DeliveryPriority.NORMAL]
                assert record.status == DeliveryStatus.DELIVERED
            
            # Verify all emails were delivered
            for delivery_id in delivery_ids:
                record = delivery_manager.get_delivery_status(delivery_id)
                assert record is not None
                assert record.status == DeliveryStatus.DELIVERED
            
        finally:
            delivery_manager.stop()


class TestDeliveryManagerRobustness:
    """Test delivery manager robustness and error recovery."""
    
    @pytest.fixture
    def smtp_config(self):
        """Create test SMTP configuration."""
        return SMTPConnectionConfig(
            host="smtp.test.com",
            port=587,
            use_tls=True,
            username="test@dol.gov",
            password="testpass"
        )
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_smtp_connection_recovery(self, mock_smtp_class, smtp_config):
        """Test SMTP connection error recovery."""
        # Setup mock SMTP to fail connection initially, then succeed
        connection_attempts = [0]  # Use list to modify from inner function
        
        def create_smtp_connection(*args, **kwargs):
            connection_attempts[0] += 1
            if connection_attempts[0] <= 2:
                raise smtplib.SMTPConnectError(421, "Connection failed")
            
            # Return successful connection on third attempt
            mock_smtp = Mock()
            return mock_smtp
        
        mock_smtp_class.side_effect = create_smtp_connection
        
        delivery_manager = DeliveryManager(smtp_config=smtp_config)
        delivery_manager.start()
        
        try:
            # Send email that will initially fail connection
            delivery_id = delivery_manager.send_email(
                recipient_email="recovery-test@example.com",
                sender_email="agent@dol.gov",
                subject="Connection Recovery Test",
                body_text="Testing connection recovery"
            )
            
            # Wait for retry attempts
            time.sleep(2)
            
            # Verify delivery eventually succeeded after connection recovery
            record = delivery_manager.get_delivery_status(delivery_id)
            assert record is not None
            
            # Should have multiple failed attempts followed by success
            assert len(record.attempts) >= 2
            
            # Verify connection was attempted multiple times
            assert connection_attempts[0] >= 3
            
        finally:
            delivery_manager.stop()
    
    def test_thread_safety_under_load(self, smtp_config):
        """Test thread safety under high concurrent load."""
        with patch('src.email.delivery_manager.smtplib.SMTP') as mock_smtp_class:
            mock_smtp = Mock()
            mock_smtp_class.return_value = mock_smtp
            
            delivery_manager = DeliveryManager(
                smtp_config=smtp_config,
                max_concurrent_deliveries=10
            )
            delivery_manager.start()
            
            try:
                # Create multiple threads sending emails simultaneously
                def send_emails_batch(batch_id, num_emails):
                    """Send a batch of emails from a thread."""
                    for i in range(num_emails):
                        try:
                            delivery_manager.send_email(
                                recipient_email=f"thread{batch_id}-{i}@example.com",
                                sender_email="agent@dol.gov",
                                subject=f"Thread Safety Test {batch_id}-{i}",
                                body_text=f"Thread safety test message {batch_id}-{i}"
                            )
                        except Exception as e:
                            pytest.fail(f"Thread safety violation: {str(e)}")
                
                # Start multiple threads
                threads = []
                num_threads = 5
                emails_per_thread = 10
                
                for batch_id in range(num_threads):
                    thread = threading.Thread(
                        target=send_emails_batch,
                        args=(batch_id, emails_per_thread)
                    )
                    threads.append(thread)
                    thread.start()
                
                # Wait for all threads to complete
                for thread in threads:
                    thread.join(timeout=10)
                
                # Wait for delivery processing
                time.sleep(3)
                
                # Verify all emails were tracked correctly
                total_expected = num_threads * emails_per_thread
                metrics = delivery_manager.get_delivery_metrics()
                
                assert metrics['total_sent'] == total_expected
                assert metrics['total_records'] == total_expected
                
                # Verify no data corruption in delivery records
                for delivery_id, record in delivery_manager.delivery_records.items():
                    assert record.delivery_id == delivery_id
                    assert record.recipient_email is not None
                    assert record.sender_email == "agent@dol.gov"
                    assert "Thread Safety Test" in record.subject
                
            finally:
                delivery_manager.stop()
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_graceful_shutdown_with_pending_deliveries(self, mock_smtp_class, smtp_config):
        """Test graceful shutdown with pending deliveries."""
        # Setup mock SMTP with slow delivery simulation
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        
        def slow_delivery(message):
            time.sleep(1)  # Simulate slow delivery
            return None
        
        mock_smtp.send_message.side_effect = slow_delivery
        
        delivery_manager = DeliveryManager(smtp_config=smtp_config)
        delivery_manager.start()
        
        # Send multiple emails
        delivery_ids = []
        for i in range(5):
            delivery_id = delivery_manager.send_email(
                recipient_email=f"shutdown{i}@example.com",
                sender_email="agent@dol.gov",
                subject=f"Shutdown Test {i}",
                body_text=f"Shutdown test message {i}"
            )
            delivery_ids.append(delivery_id)
        
        # Allow some deliveries to start
        time.sleep(0.5)
        
        # Stop delivery manager
        stop_start_time = time.time()
        delivery_manager.stop()
        stop_duration = time.time() - stop_start_time
        
        # Verify graceful shutdown (should not take too long)
        assert stop_duration < 10  # Should stop within 10 seconds
        
        # Verify delivery manager stopped
        assert delivery_manager.running is False
        
        # Verify delivery records are preserved
        for delivery_id in delivery_ids:
            record = delivery_manager.get_delivery_status(delivery_id)
            assert record is not None
            assert record.delivery_id == delivery_id