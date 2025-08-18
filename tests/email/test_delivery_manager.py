"""
Tests for Delivery Manager with Comprehensive Tracking

Tests cover SMTP delivery, confirmation tracking, delivery status monitoring,
automatic retry logic with exponential backoff, bounce handling, and delivery failure escalation.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from email.mime.multipart import MIMEMultipart
import smtplib

from src.email.delivery_manager import (
    DeliveryManager,
    DeliveryRecord,
    DeliveryAttempt,
    DeliveryStatus,
    DeliveryPriority,
    BounceType,
    SMTPConnectionConfig,
    DeliveryManagerError,
    SMTPConnectionError,
    DeliveryFailureError
)
from src.database.manager import DatabaseManager
from src.database.models import AuditLogEntry, AuditAction


class TestDeliveryRecord:
    """Test DeliveryRecord functionality."""
    
    def test_delivery_record_creation(self):
        """Test creating a delivery record."""
        record = DeliveryRecord(
            recipient_email="test@example.com",
            sender_email="sender@dol.gov",
            subject="Test Email",
            priority=DeliveryPriority.HIGH
        )
        
        assert record.recipient_email == "test@example.com"
        assert record.sender_email == "sender@dol.gov"
        assert record.subject == "Test Email"
        assert record.priority == DeliveryPriority.HIGH
        assert record.status == DeliveryStatus.PENDING
        assert record.retry_count == 0
        assert len(record.attempts) == 0
        assert record.delivery_id is not None
    
    def test_delivery_record_validation(self):
        """Test delivery record validation."""
        with pytest.raises(ValueError, match="Recipient email cannot be empty"):
            DeliveryRecord(recipient_email="", sender_email="sender@dol.gov", subject="Test")
        
        with pytest.raises(ValueError, match="Sender email cannot be empty"):
            DeliveryRecord(recipient_email="test@example.com", sender_email="", subject="Test")
        
        with pytest.raises(ValueError, match="Subject cannot be empty"):
            DeliveryRecord(recipient_email="test@example.com", sender_email="sender@dol.gov", subject="")
    
    def test_add_successful_attempt(self):
        """Test adding a successful delivery attempt."""
        record = DeliveryRecord(
            recipient_email="test@example.com",
            sender_email="sender@dol.gov",
            subject="Test Email"
        )
        
        attempt = DeliveryAttempt(
            status=DeliveryStatus.DELIVERED,
            smtp_response_code=250,
            smtp_response_message="OK",
            delivery_time_ms=150.5
        )
        
        record.add_attempt(attempt)
        
        assert len(record.attempts) == 1
        assert record.status == DeliveryStatus.DELIVERED
        assert record.delivered_at is not None
        assert record.attempts[0] == attempt
    
    def test_add_failed_attempt_with_retry(self):
        """Test adding a failed attempt that triggers retry."""
        record = DeliveryRecord(
            recipient_email="test@example.com",
            sender_email="sender@dol.gov",
            subject="Test Email",
            max_retries=3
        )
        
        attempt = DeliveryAttempt(
            status=DeliveryStatus.FAILED,
            error_message="Connection timeout"
        )
        
        record.add_attempt(attempt)
        
        assert len(record.attempts) == 1
        assert record.status == DeliveryStatus.RETRYING
        assert record.retry_count == 1
        assert record.next_retry_at is not None
        assert record.next_retry_at > datetime.utcnow()
    
    def test_add_failed_attempt_with_escalation(self):
        """Test adding a failed attempt that triggers escalation."""
        record = DeliveryRecord(
            recipient_email="test@example.com",
            sender_email="sender@dol.gov",
            subject="Test Email",
            max_retries=2
        )
        
        # Add two failed attempts to reach max retries
        for i in range(2):
            attempt = DeliveryAttempt(
                status=DeliveryStatus.FAILED,
                error_message=f"Failure {i+1}"
            )
            record.add_attempt(attempt)
        
        assert len(record.attempts) == 2
        assert record.status == DeliveryStatus.ESCALATED
        assert record.retry_count == 2
        assert record.failed_at is not None
    
    def test_exponential_backoff_scheduling(self):
        """Test exponential backoff retry scheduling."""
        record = DeliveryRecord(
            recipient_email="test@example.com",
            sender_email="sender@dol.gov",
            subject="Test Email"
        )
        
        # First failure - should schedule retry in ~2 minutes
        attempt1 = DeliveryAttempt(status=DeliveryStatus.FAILED)
        record.add_attempt(attempt1)
        first_retry = record.next_retry_at
        
        # Second failure - should schedule retry in ~4 minutes
        attempt2 = DeliveryAttempt(status=DeliveryStatus.FAILED)
        record.add_attempt(attempt2)
        second_retry = record.next_retry_at
        
        # Verify exponential backoff (second retry should be later)
        assert second_retry > first_retry
        assert (second_retry - datetime.utcnow()).total_seconds() > (first_retry - datetime.utcnow()).total_seconds()


class TestSMTPConnectionConfig:
    """Test SMTP connection configuration."""
    
    def test_smtp_config_creation(self):
        """Test creating SMTP configuration."""
        config = SMTPConnectionConfig(
            host="smtp.example.com",
            port=587,
            use_tls=True,
            username="user@example.com",
            password="password123"
        )
        
        assert config.host == "smtp.example.com"
        assert config.port == 587
        assert config.use_tls is True
        assert config.username == "user@example.com"
        assert config.password == "password123"
    
    def test_smtp_config_validation(self):
        """Test SMTP configuration validation."""
        with pytest.raises(ValueError, match="SMTP host cannot be empty"):
            SMTPConnectionConfig(host="")
        
        with pytest.raises(ValueError, match="SMTP port must be between 1 and 65535"):
            SMTPConnectionConfig(host="smtp.example.com", port=0)
        
        with pytest.raises(ValueError, match="SMTP port must be between 1 and 65535"):
            SMTPConnectionConfig(host="smtp.example.com", port=70000)
        
        with pytest.raises(ValueError, match="SMTP timeout must be positive"):
            SMTPConnectionConfig(host="smtp.example.com", timeout=0)


class TestDeliveryManager:
    """Test DeliveryManager functionality."""
    
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
    
    @pytest.fixture
    def mock_database_manager(self):
        """Create mock database manager."""
        mock_db = Mock(spec=DatabaseManager)
        mock_db.create_audit_entry = Mock()
        return mock_db
    
    @pytest.fixture
    def delivery_manager(self, smtp_config, mock_database_manager):
        """Create test delivery manager."""
        manager = DeliveryManager(
            smtp_config=smtp_config,
            database_manager=mock_database_manager,
            max_concurrent_deliveries=2
        )
        return manager
    
    def test_delivery_manager_initialization(self, delivery_manager):
        """Test delivery manager initialization."""
        assert delivery_manager.smtp_config.host == "smtp.test.com"
        assert delivery_manager.max_concurrent_deliveries == 2
        assert delivery_manager.running is False
        assert len(delivery_manager.delivery_records) == 0
        assert delivery_manager.delivery_metrics['total_sent'] == 0
    
    def test_start_stop_delivery_manager(self, delivery_manager):
        """Test starting and stopping delivery manager."""
        # Start manager
        delivery_manager.start()
        assert delivery_manager.running is True
        assert len(delivery_manager.delivery_threads) == 2
        assert delivery_manager.retry_thread is not None
        
        # Stop manager
        delivery_manager.stop()
        assert delivery_manager.running is False
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp_class, delivery_manager):
        """Test successful email sending."""
        # Setup mock SMTP
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        
        # Start delivery manager
        delivery_manager.start()
        
        try:
            # Send email
            delivery_id = delivery_manager.send_email(
                recipient_email="test@example.com",
                sender_email="sender@dol.gov",
                subject="Test Email",
                body_text="Test message",
                priority=DeliveryPriority.HIGH,
                correlation_id="test-correlation-123"
            )
            
            # Verify delivery record created
            assert delivery_id in delivery_manager.delivery_records
            record = delivery_manager.delivery_records[delivery_id]
            assert record.recipient_email == "test@example.com"
            assert record.sender_email == "sender@dol.gov"
            assert record.subject == "Test Email"
            assert record.priority == DeliveryPriority.HIGH
            assert record.correlation_id == "test-correlation-123"
            
            # Wait for delivery processing
            time.sleep(0.5)
            
            # Verify SMTP was called
            mock_smtp.send_message.assert_called_once()
            mock_smtp.quit.assert_called_once()
            
        finally:
            delivery_manager.stop()
    
    def test_send_email_validation(self, delivery_manager):
        """Test email sending validation."""
        with pytest.raises(DeliveryManagerError):
            delivery_manager.send_email(
                recipient_email="",  # Invalid email
                sender_email="sender@dol.gov",
                subject="Test Email",
                body_text="Test message"
            )
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_delivery_retry_logic(self, mock_smtp_class, delivery_manager):
        """Test delivery retry logic with exponential backoff."""
        # Setup mock SMTP to fail first time, succeed second time
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        mock_smtp.send_message.side_effect = [
            smtplib.SMTPException("Temporary failure"),
            None  # Success on retry
        ]
        
        delivery_manager.start()
        
        try:
            # Send email
            delivery_id = delivery_manager.send_email(
                recipient_email="test@example.com",
                sender_email="sender@dol.gov",
                subject="Test Email",
                body_text="Test message"
            )
            
            # Wait for initial delivery attempt and retry
            time.sleep(1)
            
            # Check delivery record
            record = delivery_manager.delivery_records[delivery_id]
            assert len(record.attempts) >= 1
            assert record.attempts[0].status == DeliveryStatus.FAILED
            
            # Verify retry was scheduled
            assert record.status in [DeliveryStatus.RETRYING, DeliveryStatus.DELIVERED]
            
        finally:
            delivery_manager.stop()
    
    def test_bounce_analysis(self, delivery_manager):
        """Test bounce message analysis."""
        # Test hard bounce
        hard_bounce = delivery_manager._analyze_bounce("User unknown in virtual mailbox table")
        assert hard_bounce['type'] == BounceType.HARD_BOUNCE
        
        # Test soft bounce
        soft_bounce = delivery_manager._analyze_bounce("Mailbox full, try again later")
        assert soft_bounce['type'] == BounceType.SOFT_BOUNCE
        
        # Test block bounce
        block_bounce = delivery_manager._analyze_bounce("Message blocked due to spam content")
        assert block_bounce['type'] == BounceType.BLOCK_BOUNCE
        
        # Test unknown bounce
        unknown_bounce = delivery_manager._analyze_bounce("Some unknown error occurred")
        assert unknown_bounce['type'] == BounceType.UNKNOWN
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_delivery_failure_escalation(self, mock_smtp_class, delivery_manager, mock_database_manager):
        """Test delivery failure escalation."""
        # Setup mock SMTP to always fail
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        mock_smtp.send_message.side_effect = smtplib.SMTPException("Permanent failure")
        
        delivery_manager.start()
        
        try:
            # Send email with low max retries
            delivery_id = delivery_manager.send_email(
                recipient_email="test@example.com",
                sender_email="sender@dol.gov",
                subject="Test Email",
                body_text="Test message"
            )
            
            # Manually set max retries to 1 for faster testing
            record = delivery_manager.delivery_records[delivery_id]
            record.max_retries = 1
            
            # Wait for delivery attempts
            time.sleep(1)
            
            # Verify escalation
            assert record.status == DeliveryStatus.ESCALATED
            assert record.retry_count >= record.max_retries
            
            # Verify audit log entry was created
            mock_database_manager.create_audit_entry.assert_called()
            
        finally:
            delivery_manager.stop()
    
    def test_get_delivery_status(self, delivery_manager):
        """Test getting delivery status."""
        # Send email
        delivery_id = delivery_manager.send_email(
            recipient_email="test@example.com",
            sender_email="sender@dol.gov",
            subject="Test Email",
            body_text="Test message"
        )
        
        # Get status
        status = delivery_manager.get_delivery_status(delivery_id)
        assert status is not None
        assert status.delivery_id == delivery_id
        assert status.recipient_email == "test@example.com"
        
        # Test non-existent delivery
        non_existent_status = delivery_manager.get_delivery_status("non-existent-id")
        assert non_existent_status is None
    
    def test_get_delivery_metrics(self, delivery_manager):
        """Test getting delivery metrics."""
        # Initial metrics
        metrics = delivery_manager.get_delivery_metrics()
        assert metrics['total_sent'] == 0
        assert metrics['total_delivered'] == 0
        assert metrics['total_failed'] == 0
        assert metrics['pending_deliveries'] == 0
        
        # Send email
        delivery_manager.send_email(
            recipient_email="test@example.com",
            sender_email="sender@dol.gov",
            subject="Test Email",
            body_text="Test message"
        )
        
        # Check updated metrics
        updated_metrics = delivery_manager.get_delivery_metrics()
        assert updated_metrics['pending_deliveries'] == 1
        assert updated_metrics['total_records'] == 1
    
    def test_retry_failed_deliveries(self, delivery_manager):
        """Test manual retry of failed deliveries."""
        # Create a failed delivery record
        delivery_id = delivery_manager.send_email(
            recipient_email="test@example.com",
            sender_email="sender@dol.gov",
            subject="Test Email",
            body_text="Test message"
        )
        
        # Manually set status to failed
        record = delivery_manager.delivery_records[delivery_id]
        record.status = DeliveryStatus.FAILED
        record.retry_count = 1
        
        # Retry failed deliveries
        retried_ids = delivery_manager.retry_failed_deliveries(max_age_hours=24)
        
        assert delivery_id in retried_ids
        assert record.status == DeliveryStatus.RETRYING
        assert record.next_retry_at is not None
    
    @patch('src.email.delivery_manager.smtplib.SMTP_SSL')
    def test_smtp_ssl_connection(self, mock_smtp_ssl_class, smtp_config):
        """Test SMTP SSL connection creation."""
        # Configure for SSL
        smtp_config.use_ssl = True
        smtp_config.use_tls = False
        
        delivery_manager = DeliveryManager(smtp_config=smtp_config)
        
        # Setup mock
        mock_smtp_ssl = Mock()
        mock_smtp_ssl_class.return_value = mock_smtp_ssl
        
        # Create connection
        connection = delivery_manager._create_smtp_connection()
        
        # Verify SSL connection was created
        mock_smtp_ssl_class.assert_called_once()
        mock_smtp_ssl.login.assert_called_once_with(smtp_config.username, smtp_config.password)
        assert connection == mock_smtp_ssl
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_smtp_tls_connection(self, mock_smtp_class, smtp_config):
        """Test SMTP TLS connection creation."""
        # Configure for TLS
        smtp_config.use_ssl = False
        smtp_config.use_tls = True
        
        delivery_manager = DeliveryManager(smtp_config=smtp_config)
        
        # Setup mock
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        
        # Create connection
        connection = delivery_manager._create_smtp_connection()
        
        # Verify TLS connection was created
        mock_smtp_class.assert_called_once()
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with(smtp_config.username, smtp_config.password)
        assert connection == mock_smtp
    
    def test_prepare_email_message(self, delivery_manager):
        """Test email message preparation."""
        record = DeliveryRecord(
            recipient_email="test@example.com",
            sender_email="sender@dol.gov",
            subject="Test Email",
            priority=DeliveryPriority.HIGH,
            correlation_id="test-123"
        )
        
        message = delivery_manager._prepare_email_message(
            record,
            "Plain text body",
            "<html><body>HTML body</body></html>",
            [
                {
                    'filename': 'test.txt',
                    'content': b'Test file content',
                    'content_type': 'text/plain'
                }
            ]
        )
        
        assert isinstance(message, MIMEMultipart)
        assert message['From'] == "sender@dol.gov"
        assert message['To'] == "test@example.com"
        assert message['Subject'] == "Test Email"
        assert message['X-Correlation-ID'] == "test-123"
        assert message['X-Priority'] == '1'  # High priority
        assert message['Importance'] == 'high'
    
    def test_prepare_email_message_text_only(self, delivery_manager):
        """Test email message preparation with text only."""
        record = DeliveryRecord(
            recipient_email="test@example.com",
            sender_email="sender@dol.gov",
            subject="Test Email"
        )
        
        message = delivery_manager._prepare_email_message(
            record,
            "Plain text body only"
        )
        
        assert isinstance(message, MIMEMultipart)
        assert message['From'] == "sender@dol.gov"
        assert message['To'] == "test@example.com"
        assert message['Subject'] == "Test Email"
        # Should not have priority headers for normal priority
        assert 'X-Priority' not in message
        assert 'Importance' not in message
    
    def test_add_attachment_error_handling(self, delivery_manager):
        """Test attachment error handling."""
        message = MIMEMultipart()
        
        # Test invalid attachment
        with pytest.raises(DeliveryManagerError):
            delivery_manager._add_attachment(message, {
                'filename': 'test.txt',
                'content': None,  # Invalid content
                'content_type': 'text/plain'
            })
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_smtp_connection_error_handling(self, mock_smtp_class, delivery_manager):
        """Test SMTP connection error handling."""
        # Setup mock to raise connection error
        mock_smtp_class.side_effect = smtplib.SMTPConnectError(421, "Connection failed")
        
        with pytest.raises(SMTPConnectionError):
            delivery_manager._create_smtp_connection()
    
    def test_audit_entry_creation(self, delivery_manager, mock_database_manager):
        """Test audit entry creation."""
        delivery_manager._create_audit_entry(
            AuditAction.EMAIL_PROCESSED,
            "test-delivery-id",
            {'action': 'test_action', 'status': 'success'}
        )
        
        # Verify audit entry was created
        mock_database_manager.create_audit_entry.assert_called_once()
        call_args = mock_database_manager.create_audit_entry.call_args[0][0]
        assert isinstance(call_args, AuditLogEntry)
        assert call_args.component == "delivery_manager"
        assert call_args.action == AuditAction.EMAIL_PROCESSED
        assert call_args.email_uid == "test-delivery-id"
        assert call_args.details['action'] == 'test_action'


class TestDeliveryManagerIntegration:
    """Integration tests for delivery manager."""
    
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
    def test_end_to_end_delivery_success(self, mock_smtp_class, smtp_config):
        """Test end-to-end successful delivery."""
        # Setup mock SMTP
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        
        # Create delivery manager
        delivery_manager = DeliveryManager(smtp_config=smtp_config)
        delivery_manager.start()
        
        try:
            # Send email
            delivery_id = delivery_manager.send_email(
                recipient_email="executive@dol.gov",
                sender_email="agent@dol.gov",
                subject="Executive Summary Report",
                body_text="Please find the executive summary attached.",
                body_html="<p>Please find the executive summary attached.</p>",
                attachments=[
                    {
                        'filename': 'summary.pdf',
                        'content': b'PDF content here',
                        'content_type': 'application/pdf'
                    }
                ],
                priority=DeliveryPriority.HIGH,
                correlation_id="exec-summary-001"
            )
            
            # Wait for delivery
            time.sleep(1)
            
            # Verify delivery
            record = delivery_manager.get_delivery_status(delivery_id)
            assert record is not None
            assert record.status == DeliveryStatus.DELIVERED
            assert len(record.attempts) == 1
            assert record.attempts[0].status == DeliveryStatus.DELIVERED
            
            # Verify SMTP interaction
            mock_smtp.send_message.assert_called_once()
            mock_smtp.quit.assert_called_once()
            
            # Verify metrics
            metrics = delivery_manager.get_delivery_metrics()
            assert metrics['total_sent'] == 1
            assert metrics['total_delivered'] == 1
            assert metrics['total_failed'] == 0
            
        finally:
            delivery_manager.stop()
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_end_to_end_delivery_with_retry(self, mock_smtp_class, smtp_config):
        """Test end-to-end delivery with retry logic."""
        # Setup mock SMTP to fail first, succeed second
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        mock_smtp.send_message.side_effect = [
            smtplib.SMTPException("Temporary failure"),
            None  # Success
        ]
        
        # Create delivery manager
        delivery_manager = DeliveryManager(smtp_config=smtp_config)
        delivery_manager.start()
        
        try:
            # Send email
            delivery_id = delivery_manager.send_email(
                recipient_email="test@example.com",
                sender_email="agent@dol.gov",
                subject="Test Email with Retry",
                body_text="This email should retry on failure."
            )
            
            # Wait for initial attempt and retry
            time.sleep(2)
            
            # Verify delivery record
            record = delivery_manager.get_delivery_status(delivery_id)
            assert record is not None
            assert len(record.attempts) >= 1
            
            # First attempt should have failed
            assert record.attempts[0].status == DeliveryStatus.FAILED
            assert "Temporary failure" in record.attempts[0].error_message
            
            # Should be in retrying state or delivered (if retry completed)
            assert record.status in [DeliveryStatus.RETRYING, DeliveryStatus.DELIVERED]
            
        finally:
            delivery_manager.stop()
    
    @patch('src.email.delivery_manager.smtplib.SMTP')
    def test_concurrent_deliveries(self, mock_smtp_class, smtp_config):
        """Test concurrent email deliveries."""
        # Setup mock SMTP
        mock_smtp = Mock()
        mock_smtp_class.return_value = mock_smtp
        
        # Create delivery manager with multiple workers
        delivery_manager = DeliveryManager(
            smtp_config=smtp_config,
            max_concurrent_deliveries=3
        )
        delivery_manager.start()
        
        try:
            # Send multiple emails
            delivery_ids = []
            for i in range(5):
                delivery_id = delivery_manager.send_email(
                    recipient_email=f"test{i}@example.com",
                    sender_email="agent@dol.gov",
                    subject=f"Test Email {i}",
                    body_text=f"Test message {i}"
                )
                delivery_ids.append(delivery_id)
            
            # Wait for deliveries
            time.sleep(2)
            
            # Verify all emails were processed
            for delivery_id in delivery_ids:
                record = delivery_manager.get_delivery_status(delivery_id)
                assert record is not None
                assert record.status in [DeliveryStatus.DELIVERED, DeliveryStatus.SENDING]
            
            # Verify metrics
            metrics = delivery_manager.get_delivery_metrics()
            assert metrics['total_sent'] >= 5
            
        finally:
            delivery_manager.stop()