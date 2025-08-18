"""
Unit tests for GoDaddyEmailClient capability detection and caching functionality.
Tests Requirements: 1.6, 1.7, 1.1
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time
import imaplib
import smtplib

from src.email.godaddy_client import (
    GoDaddyEmailClient, 
    ServerCapabilities, 
    ConnectionHealth, 
    ConnectionHealthStatus,
    RateLimitInfo
)


class TestGoDaddyClientCapabilities(unittest.TestCase):
    """Test server capability detection and caching"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = GoDaddyEmailClient()
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'EMAIL_HOST': 'test.imap.server.com',
            'EMAIL_PORT': '993',
            'SMTP_HOST': 'test.smtp.server.com', 
            'SMTP_PORT': '465',
            'EMAIL_USER': 'test@example.com',
            'EMAIL_PASS': 'testpass'
        })
        self.env_patcher.start()
        
    def tearDown(self):
        """Clean up test fixtures"""
        self.env_patcher.stop()
        if self.client.imap:
            self.client.imap = None
        if self.client.smtp:
            self.client.smtp = None

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_capability_detection_with_idle_support(self, mock_smtp, mock_imap):
        """Test capability detection when IDLE is supported"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        # Mock IMAP capability response with IDLE support
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1 IDLE NAMESPACE'])
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Connect and detect capabilities
        self.client.connect()
        capabilities = self.client.get_server_capabilities()
        
        # Verify IDLE support detected
        self.assertTrue(capabilities.idle_supported)
        self.assertEqual(capabilities.idle_timeout, 29 * 60)  # 29 minutes
        self.assertIn('IDLE', capabilities.supported_extensions)
        self.assertIsNotNone(capabilities.last_checked)
        self.assertIsNotNone(capabilities.cache_expires)
        
        # Verify cache expiration is 24 hours from now
        expected_expiry = datetime.now() + timedelta(hours=24)
        time_diff = abs((capabilities.cache_expires - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60)  # Within 1 minute tolerance

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_capability_detection_without_idle_support(self, mock_smtp, mock_imap):
        """Test capability detection when IDLE is not supported"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        # Mock IMAP capability response without IDLE support
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1 NAMESPACE'])
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Connect and detect capabilities
        self.client.connect()
        capabilities = self.client.get_server_capabilities()
        
        # Verify IDLE support not detected
        self.assertFalse(capabilities.idle_supported)
        self.assertIsNone(capabilities.idle_timeout)
        self.assertNotIn('IDLE', capabilities.supported_extensions)

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_capability_caching_24_hours(self, mock_smtp, mock_imap):
        """Test that capabilities are cached for 24 hours"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1 IDLE'])
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Connect and get capabilities first time
        self.client.connect()
        capabilities1 = self.client.get_server_capabilities()
        
        # Reset mock call count
        mock_imap_instance.capability.reset_mock()
        
        # Get capabilities second time - should use cache
        capabilities2 = self.client.get_server_capabilities()
        
        # Verify capability() was not called again (using cache)
        mock_imap_instance.capability.assert_not_called()
        
        # Verify same capabilities returned
        self.assertEqual(capabilities1.idle_supported, capabilities2.idle_supported)
        self.assertEqual(capabilities1.last_checked, capabilities2.last_checked)

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_capability_cache_expiration(self, mock_smtp, mock_imap):
        """Test that expired cache triggers new capability detection"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1 IDLE'])
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Connect and get capabilities
        self.client.connect()
        capabilities1 = self.client.get_server_capabilities()
        
        # Manually expire the cache
        self.client._capabilities_cache.cache_expires = datetime.now() - timedelta(hours=1)
        
        # Reset mock call count
        mock_imap_instance.capability.reset_mock()
        
        # Get capabilities again - should detect again due to expired cache
        capabilities2 = self.client.get_server_capabilities()
        
        # Verify capability() was called again
        mock_imap_instance.capability.assert_called_once()
        
        # Verify new timestamp
        self.assertGreater(capabilities2.last_checked, capabilities1.last_checked)

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_idle_support_testing(self, mock_smtp, mock_imap):
        """Test actual IDLE support testing with server interaction"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        # Mock successful IDLE test
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1 IDLE'])
        mock_imap_instance.select.return_value = ('OK', [b'INBOX selected'])
        mock_imap_instance._new_tag.return_value = 'A001'
        mock_imap_instance.send = Mock()
        mock_imap_instance.readline.side_effect = [b'+ idling\r\n', b'A001 OK IDLE completed\r\n']
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Connect and test IDLE
        self.client.connect()
        idle_supported = self.client.test_idle_support()
        
        # Verify IDLE test was successful
        self.assertTrue(idle_supported)
        
        # Verify IDLE commands were sent
        expected_calls = [
            unittest.mock.call(b'A001 IDLE\r\n'),
            unittest.mock.call(b'DONE\r\n')
        ]
        mock_imap_instance.send.assert_has_calls(expected_calls)

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_idle_support_testing_failure(self, mock_smtp, mock_imap):
        """Test IDLE support testing when server doesn't support it"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        # Mock IDLE test failure
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1 IDLE'])
        mock_imap_instance.select.return_value = ('OK', [b'INBOX selected'])
        mock_imap_instance._new_tag.return_value = 'A001'
        mock_imap_instance.send = Mock()
        mock_imap_instance.readline.return_value = b'A001 BAD IDLE not supported\r\n'
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Connect and test IDLE
        self.client.connect()
        idle_supported = self.client.test_idle_support()
        
        # Verify IDLE test failed
        self.assertFalse(idle_supported)

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_rate_limit_detection(self, mock_smtp, mock_imap):
        """Test rate limit detection during capability detection"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        # Mock successful operations for rate limit testing
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1 IDLE'])
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Connect and detect capabilities
        self.client.connect()
        capabilities = self.client.get_server_capabilities()
        
        # Verify rate limit was detected (should be 60 for successful quick operations)
        self.assertGreaterEqual(capabilities.rate_limit_per_minute, 30)
        self.assertLessEqual(capabilities.rate_limit_per_minute, 60)

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_capability_detection_failure_fallback(self, mock_smtp, mock_imap):
        """Test fallback to default capabilities when detection fails"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        # Mock capability detection failure
        mock_imap_instance.capability.return_value = ('NO', [b'Capability command failed'])
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Connect and detect capabilities
        self.client.connect()
        capabilities = self.client.get_server_capabilities()
        
        # Verify default capabilities are used
        self.assertFalse(capabilities.idle_supported)
        self.assertIsNone(capabilities.idle_timeout)
        self.assertEqual(capabilities.max_connections, 5)
        self.assertEqual(capabilities.rate_limit_per_minute, 30)
        self.assertEqual(capabilities.supported_extensions, [])
        
        # Verify shorter cache expiration on failure (1 hour instead of 24)
        expected_expiry = datetime.now() + timedelta(hours=1)
        time_diff = abs((capabilities.cache_expires - expected_expiry).total_seconds())
        self.assertLess(time_diff, 300)  # Within 5 minutes tolerance


class TestConnectionHealthMonitoring(unittest.TestCase):
    """Test connection health monitoring functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = GoDaddyEmailClient()
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'EMAIL_HOST': 'test.imap.server.com',
            'EMAIL_PORT': '993',
            'SMTP_HOST': 'test.smtp.server.com',
            'SMTP_PORT': '465', 
            'EMAIL_USER': 'test@example.com',
            'EMAIL_PASS': 'testpass'
        })
        self.env_patcher.start()
        
    def tearDown(self):
        """Clean up test fixtures"""
        self.env_patcher.stop()

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_connection_health_healthy_status(self, mock_smtp, mock_imap):
        """Test connection health reporting as healthy"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1'])
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Connect
        self.client.connect()
        
        # Get health status
        health = self.client.get_connection_health()
        
        # Verify healthy status
        self.assertEqual(health.status, ConnectionHealth.HEALTHY)
        self.assertIsNotNone(health.last_check)
        self.assertGreaterEqual(health.response_time_ms, 0)
        self.assertEqual(health.error_count, 0)
        self.assertIsNone(health.last_error)
        self.assertGreaterEqual(health.uptime_percentage, 90.0)

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_connection_health_degraded_status(self, mock_smtp, mock_imap):
        """Test connection health reporting as degraded due to slow response"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Mock slow IMAP response
        def slow_noop():
            time.sleep(2)  # 2 second delay
            return ('OK', [b'NOOP completed'])
        
        mock_imap_instance.noop.side_effect = slow_noop
        
        # Connect
        self.client.connect()
        
        # Perform health check
        health = self.client._perform_health_check()
        
        # Verify degraded status due to slow response
        self.assertEqual(health.status, ConnectionHealth.DEGRADED)
        self.assertGreater(health.response_time_ms, 1000)  # > 1 second

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_connection_health_unhealthy_status(self, mock_smtp, mock_imap):
        """Test connection health reporting as unhealthy due to errors"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1'])
        mock_imap_instance.noop.return_value = ('NO', [b'NOOP failed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Connect
        self.client.connect()
        
        # Perform health check
        health = self.client._perform_health_check()
        
        # Verify unhealthy status
        self.assertEqual(health.status, ConnectionHealth.UNHEALTHY)
        self.assertGreater(health.error_count, 0)
        self.assertIsNotNone(health.last_error)

    def test_connection_health_disconnected_status(self):
        """Test connection health reporting as disconnected when not connected"""
        # Get health status without connecting
        health = self.client.get_connection_health()
        
        # Verify disconnected status
        self.assertEqual(health.status, ConnectionHealth.DISCONNECTED)
        self.assertIsNotNone(health.last_error)
        self.assertEqual(health.response_time_ms, 0)


class TestRateLimitHandling(unittest.TestCase):
    """Test rate limiting detection and handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = GoDaddyEmailClient()
        
    def test_rate_limit_info_initialization(self):
        """Test rate limit info is properly initialized"""
        rate_info = self.client.get_rate_limit_info()
        
        self.assertFalse(rate_info.is_rate_limited)
        self.assertEqual(rate_info.requests_per_minute, 60)
        self.assertEqual(rate_info.current_usage, 0)
        self.assertIsNone(rate_info.reset_time)
        self.assertEqual(rate_info.backoff_seconds, 0)

    def test_rate_limit_handling_with_retry_after(self):
        """Test rate limit handling with specific retry-after time"""
        # Simulate rate limiting with 30 second retry
        with patch('time.sleep') as mock_sleep:
            self.client.handle_rate_limiting(retry_after=30)
            
            # Verify sleep was called with correct duration
            mock_sleep.assert_called_once_with(30)
            
            # Verify rate limit info was updated and then reset
            rate_info = self.client.get_rate_limit_info()
            self.assertFalse(rate_info.is_rate_limited)
            self.assertEqual(rate_info.current_usage, 0)

    def test_rate_limit_handling_exponential_backoff(self):
        """Test rate limit handling with exponential backoff"""
        with patch('time.sleep') as mock_sleep:
            # First rate limit should use 1 second backoff
            self.client.handle_rate_limiting()
            mock_sleep.assert_called_with(1)
            
            # Simulate multiple rate limits to test exponential backoff
            for i in range(5):
                self.client._rate_limit_info.current_usage = (i + 1) * 10
                self.client.handle_rate_limiting()
            
            # Verify exponential backoff was applied (should reach max of 60 seconds)
            final_call = mock_sleep.call_args_list[-1]
            self.assertLessEqual(final_call[0][0], 60)

    @patch('src.email.godaddy_client.time.sleep')
    def test_rate_limit_check_before_operation(self, mock_sleep):
        """Test rate limit checking before operations"""
        # Set up rate limited state
        self.client._rate_limit_info = RateLimitInfo(
            is_rate_limited=True,
            requests_per_minute=60,
            current_usage=0,
            reset_time=datetime.now() + timedelta(seconds=5),
            backoff_seconds=5
        )
        
        # Check rate limit before operation
        self.client._check_rate_limit_before_operation()
        
        # Verify sleep was called
        mock_sleep.assert_called_once()
        
        # Verify usage counter was incremented
        self.assertEqual(self.client._rate_limit_info.current_usage, 1)


if __name__ == '__main__':
    unittest.main()