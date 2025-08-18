"""
Integration tests for enhanced GoDaddyEmailClient functionality.
Tests Requirements: 1.6, 1.7, 1.1
"""

import unittest
from unittest.mock import Mock, patch
import os

from src.email.godaddy_client import GoDaddyEmailClient, ConnectionHealth


class TestGoDaddyClientIntegration(unittest.TestCase):
    """Integration tests for enhanced GoDaddyEmailClient"""
    
    def setUp(self):
        """Set up test fixtures"""
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
    def test_enhanced_client_maintains_original_interface(self, mock_smtp, mock_imap):
        """Test that enhanced client maintains original EmailClient interface"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        # Mock responses
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1 IDLE'])
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_imap_instance.select.return_value = ('OK', [b'INBOX selected'])
        mock_imap_instance.search.return_value = ('OK', [b'1 2 3'])
        mock_imap_instance.fetch.return_value = ('OK', [(b'1 (RFC822 {100}', b'From: test@example.com\r\nSubject: Test\r\n\r\nTest body')])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        mock_smtp_instance.send_message = Mock()
        
        # Create client and test original interface methods
        client = GoDaddyEmailClient()
        
        # Test connect method
        client.connect()
        self.assertIsNotNone(client.imap)
        self.assertIsNotNone(client.smtp)
        
        # Test that capabilities were detected during connect
        capabilities = client.get_server_capabilities()
        self.assertIsNotNone(capabilities)
        self.assertTrue(capabilities.idle_supported)
        
        # Test connection health is available
        health = client.get_connection_health()
        self.assertEqual(health.status, ConnectionHealth.HEALTHY)
        
        # Test original methods still work
        emails = client.fetch_unread_emails()
        self.assertIsInstance(emails, list)
        
        # Test send email with health monitoring
        client.send_email("test@example.com", "Test Subject", "Test Body")
        mock_smtp_instance.send_message.assert_called_once()
        
        # Test close method
        client.close()

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_enhanced_features_work_together(self, mock_smtp, mock_imap):
        """Test that all enhanced features work together properly"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        # Mock responses for capability detection
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1 IDLE NAMESPACE'])
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_imap_instance.select.return_value = ('OK', [b'INBOX selected'])
        mock_imap_instance.search.return_value = ('OK', [b''])  # No emails
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        # Mock IDLE testing
        mock_imap_instance._new_tag.return_value = 'A001'
        mock_imap_instance.send = Mock()
        mock_imap_instance.readline.side_effect = [b'+ idling\r\n', b'A001 OK IDLE completed\r\n']
        
        client = GoDaddyEmailClient()
        
        # Connect (triggers capability detection)
        client.connect()
        
        # Verify capabilities were detected
        capabilities = client.get_server_capabilities()
        self.assertTrue(capabilities.idle_supported)
        self.assertIn('IDLE', capabilities.supported_extensions)
        self.assertIn('NAMESPACE', capabilities.supported_extensions)
        
        # Test IDLE support
        idle_works = client.test_idle_support()
        self.assertTrue(idle_works)
        
        # Verify health monitoring is working
        health = client.get_connection_health()
        self.assertEqual(health.status, ConnectionHealth.HEALTHY)
        self.assertGreaterEqual(health.uptime_percentage, 90.0)
        
        # Test rate limiting info
        rate_info = client.get_rate_limit_info()
        self.assertFalse(rate_info.is_rate_limited)
        self.assertGreater(rate_info.requests_per_minute, 0)
        
        # Test that operations include rate limiting checks
        emails = client.fetch_unread_emails()
        self.assertIsInstance(emails, list)
        
        # Verify rate limiting counter was incremented
        updated_rate_info = client.get_rate_limit_info()
        self.assertGreater(updated_rate_info.current_usage, 0)

    @patch('src.email.godaddy_client.imaplib.IMAP4_SSL')
    @patch('src.email.godaddy_client.smtplib.SMTP_SSL')
    def test_error_handling_with_health_monitoring(self, mock_smtp, mock_imap):
        """Test that errors are properly handled and health is updated"""
        # Setup mocks
        mock_imap_instance = Mock()
        mock_smtp_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_smtp.return_value = mock_smtp_instance
        
        # Mock initial successful connection
        mock_imap_instance.capability.return_value = ('OK', [b'IMAP4rev1'])
        mock_imap_instance.noop.return_value = ('OK', [b'NOOP completed'])
        mock_smtp_instance.noop.return_value = (250, b'OK')
        
        client = GoDaddyEmailClient()
        client.connect()
        
        # Verify initial healthy status
        health = client.get_connection_health()
        self.assertEqual(health.status, ConnectionHealth.HEALTHY)
        self.assertEqual(health.error_count, 0)
        
        # Mock an operation failure
        mock_imap_instance.select.side_effect = Exception("Connection lost")
        
        # Attempt operation that will fail
        with self.assertRaises(Exception):
            client.fetch_unread_emails()
        
        # Verify health status was updated
        health = client.get_connection_health()
        self.assertEqual(health.status, ConnectionHealth.UNHEALTHY)
        self.assertGreater(health.error_count, 0)
        self.assertIsNotNone(health.last_error)


if __name__ == '__main__':
    unittest.main()