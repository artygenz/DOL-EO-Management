# tests/email/test_content_extractor.py
import pytest
import tempfile
import os
import hashlib
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.email.content_extractor import (
    EnhancedContentExtractor,
    EmailHeaders,
    ThreadAnalysis,
    ValidatedAttachment,
    ExtractedContent,
    ContentExtractionError,
    AttachmentSecurityError
)


# Global fixtures available to all test classes
@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def extractor(temp_dir):
    """Create content extractor instance"""
    return EnhancedContentExtractor(temp_dir=temp_dir, cleanup_interval_hours=1)

@pytest.fixture
def simple_email():
    """Create simple test email"""
    msg = EmailMessage()
    msg['From'] = 'sender@example.com'
    msg['To'] = 'recipient@example.com'
    msg['Subject'] = 'Test Subject'
    msg['Message-ID'] = '<test123@example.com>'
    msg['Date'] = 'Mon, 01 Jan 2024 12:00:00 +0000'
    msg.set_content('This is a test email body.')
    return msg

@pytest.fixture
def html_email():
    """Create HTML test email"""
    msg = MIMEMultipart('alternative')
    msg['From'] = 'sender@example.com'
    msg['To'] = 'recipient@example.com'
    msg['Subject'] = 'HTML Test Subject'
    msg['Message-ID'] = '<html123@example.com>'
    msg['Date'] = 'Mon, 01 Jan 2024 12:00:00 +0000'
    
    # Plain text part
    text_part = MIMEText('This is plain text content.', 'plain')
    msg.attach(text_part)
    
    # HTML part with potentially dangerous content
    html_content = '''
    <html>
    <body>
        <h1>Test HTML Email</h1>
        <p>This is <strong>HTML</strong> content.</p>
        <script>alert('dangerous');</script>
        <a href="javascript:void(0)">Dangerous link</a>
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==" alt="test">
    </body>
    </html>
    '''
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)
    
    return msg

@pytest.fixture
def threaded_email():
    """Create threaded email (reply)"""
    msg = EmailMessage()
    msg['From'] = 'replier@example.com'
    msg['To'] = 'original@example.com'
    msg['Subject'] = 'Re: Original Subject'
    msg['Message-ID'] = '<reply123@example.com>'
    msg['In-Reply-To'] = '<original123@example.com>'
    msg['References'] = '<thread-root@example.com> <original123@example.com>'
    msg['Date'] = 'Mon, 01 Jan 2024 13:00:00 +0000'
    msg.set_content('This is a reply to the original email.')
    return msg

@pytest.fixture
def email_with_attachments():
    """Create email with various attachments"""
    msg = MIMEMultipart()
    msg['From'] = 'sender@example.com'
    msg['To'] = 'recipient@example.com'
    msg['Subject'] = 'Email with Attachments'
    msg['Message-ID'] = '<attach123@example.com>'
    msg['Date'] = 'Mon, 01 Jan 2024 12:00:00 +0000'
    
    # Add text body
    text_part = MIMEText('Email with attachments.', 'plain')
    msg.attach(text_part)
    
    # Add safe PDF attachment
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
    pdf_attachment = MIMEApplication(pdf_content, _subtype='pdf')
    pdf_attachment.add_header('Content-Disposition', 'attachment', filename='document.pdf')
    msg.attach(pdf_attachment)
    
    # Add text file attachment
    txt_content = b'This is a text file attachment.'
    txt_attachment = MIMEApplication(txt_content, _subtype='plain')
    txt_attachment.add_header('Content-Disposition', 'attachment', filename='notes.txt')
    msg.attach(txt_attachment)
    
    return msg

@pytest.fixture
def dangerous_email():
    """Create email with dangerous attachment"""
    msg = MIMEMultipart()
    msg['From'] = 'malicious@example.com'
    msg['To'] = 'victim@example.com'
    msg['Subject'] = 'Dangerous Email'
    msg['Message-ID'] = '<danger123@example.com>'
    msg['Date'] = 'Mon, 01 Jan 2024 12:00:00 +0000'
    
    # Add text body
    text_part = MIMEText('This email contains dangerous content.', 'plain')
    msg.attach(text_part)
    
    # Add dangerous executable attachment
    exe_content = b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff'  # PE header
    exe_attachment = MIMEApplication(exe_content, _subtype='octet-stream')
    exe_attachment.add_header('Content-Disposition', 'attachment', filename='malware.exe')
    msg.attach(exe_attachment)
    
    return msg


class TestEnhancedContentExtractor:
    """Test suite for Enhanced Content Extractor"""
    pass


class TestEmailHeaderExtraction:
    """Test email header extraction functionality"""
    
    def test_extract_basic_headers(self, extractor, simple_email):
        """Test extraction of basic email headers"""
        headers = extractor._extract_email_headers(simple_email)
        
        assert headers.message_id == '<test123@example.com>'
        assert headers.sender == 'sender@example.com'
        assert headers.recipients == ['recipient@example.com']
        assert headers.subject == 'Test Subject'
        assert headers.date.year == 2024
        assert headers.date.month == 1
        assert headers.date.day == 1
    
    def test_extract_threaded_headers(self, extractor, threaded_email):
        """Test extraction of threading headers"""
        headers = extractor._extract_email_headers(threaded_email)
        
        assert headers.in_reply_to == '<original123@example.com>'
        assert headers.references == ['thread-root@example.com', 'original123@example.com']
        assert headers.subject == 'Re: Original Subject'
    
    def test_decode_encoded_headers(self, extractor):
        """Test decoding of RFC 2047 encoded headers"""
        msg = EmailMessage()
        msg['From'] = '=?utf-8?B?VGVzdCBVc2Vy?= <test@example.com>'
        msg['Subject'] = '=?utf-8?Q?Test_Subject_with_=C3=A9ncoding?='
        msg['Message-ID'] = '<encoded123@example.com>'
        msg.set_content('Test content')
        
        headers = extractor._extract_email_headers(msg)
        
        assert headers.sender == 'test@example.com'
        assert headers.sender_name == 'Test User'
        assert 'éncoding' in headers.subject.lower()
    
    def test_parse_multiple_recipients(self, extractor):
        """Test parsing of multiple recipients"""
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'user1@example.com, User Two <user2@example.com>'
        msg['Cc'] = 'cc1@example.com, cc2@example.com'
        msg['Subject'] = 'Multiple Recipients'
        msg['Message-ID'] = '<multi123@example.com>'
        msg.set_content('Test content')
        
        headers = extractor._extract_email_headers(msg)
        
        assert 'user1@example.com' in headers.recipients
        assert 'user2@example.com' in headers.recipients
        assert 'cc1@example.com' in headers.cc_recipients
        assert 'cc2@example.com' in headers.cc_recipients
    
    def test_handle_malformed_date(self, extractor):
        """Test handling of malformed date headers"""
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Bad Date'
        msg['Message-ID'] = '<baddate123@example.com>'
        msg['Date'] = 'Invalid Date Format'
        msg.set_content('Test content')
        
        headers = extractor._extract_email_headers(msg)
        
        # Should use current time when date parsing fails
        assert isinstance(headers.date, datetime)
        assert abs((headers.date - datetime.now()).total_seconds()) < 60


class TestContentExtractionAndSanitization:
    """Test content extraction and sanitization functionality"""
    
    def test_extract_plain_text(self, extractor, simple_email):
        """Test plain text extraction"""
        plain_text, html_content, sanitized_html = extractor._extract_and_sanitize_content(simple_email)
        
        assert plain_text == 'This is a test email body.'
        assert html_content is None
        assert sanitized_html is None
    
    def test_extract_and_sanitize_html(self, extractor, html_email):
        """Test HTML extraction and sanitization"""
        plain_text, html_content, sanitized_html = extractor._extract_and_sanitize_content(html_email)
        
        assert 'This is plain text content.' in plain_text
        assert '<h1>Test HTML Email</h1>' in html_content
        assert '<script>' not in sanitized_html  # Script tags should be removed
        assert 'javascript:' not in sanitized_html  # JavaScript URLs should be removed
        assert 'data:' not in sanitized_html  # Data URLs should be removed
        assert '<h1>Test HTML Email</h1>' in sanitized_html  # Safe tags should remain
    
    def test_html_to_plain_text_conversion(self, extractor):
        """Test conversion of HTML to plain text"""
        html_content = '<h1>Title</h1><p>This is <strong>bold</strong> text.</p>'
        plain_text = extractor._html_to_plain_text(html_content)
        
        assert 'Title' in plain_text
        assert 'This is bold text.' in plain_text
        assert '<h1>' not in plain_text
        assert '<strong>' not in plain_text
    
    def test_clean_plain_text(self, extractor):
        """Test plain text cleaning"""
        messy_text = '  Line 1  \r\n\r\n\r\n  Line 2  \r\n  '
        cleaned = extractor._clean_plain_text(messy_text)
        
        assert cleaned == '  Line 1\n\n  Line 2\n'
    
    def test_html_entity_decoding(self, extractor):
        """Test HTML entity decoding"""
        text_with_entities = 'This &amp; that &lt;tag&gt; &quot;quoted&quot;'
        cleaned = extractor._clean_plain_text(text_with_entities)
        
        assert 'This & that <tag> "quoted"' == cleaned


class TestThreadAnalysis:
    """Test email thread analysis functionality"""
    
    def test_analyze_new_thread(self, extractor, simple_email):
        """Test analysis of new thread (not a reply)"""
        headers = extractor._extract_email_headers(simple_email)
        thread_analysis = extractor._analyze_email_threading(simple_email, headers)
        
        assert thread_analysis.thread_id == '<test123@example.com>'
        assert not thread_analysis.is_reply
        assert not thread_analysis.is_forward
        assert thread_analysis.thread_depth == 0
        assert thread_analysis.parent_message_id is None
        assert 'sender@example.com' in thread_analysis.conversation_participants
        assert 'recipient@example.com' in thread_analysis.conversation_participants
    
    def test_analyze_reply_thread(self, extractor, threaded_email):
        """Test analysis of reply thread"""
        headers = extractor._extract_email_headers(threaded_email)
        thread_analysis = extractor._analyze_email_threading(threaded_email, headers)
        
        assert thread_analysis.thread_id == 'thread-root@example.com'
        assert thread_analysis.is_reply
        assert not thread_analysis.is_forward
        assert thread_analysis.thread_depth == 2  # Two references
        assert thread_analysis.parent_message_id == '<original123@example.com>'
        assert thread_analysis.original_subject == 'Original Subject'
    
    def test_analyze_forward_thread(self, extractor):
        """Test analysis of forwarded email"""
        msg = EmailMessage()
        msg['From'] = 'forwarder@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Fwd: Important Message'
        msg['Message-ID'] = '<fwd123@example.com>'
        msg.set_content('Forwarded message content')
        
        headers = extractor._extract_email_headers(msg)
        thread_analysis = extractor._analyze_email_threading(msg, headers)
        
        assert thread_analysis.is_forward
        assert thread_analysis.original_subject == 'Important Message'
    
    def test_extract_original_subject(self, extractor):
        """Test extraction of original subject from reply/forward prefixes"""
        test_cases = [
            ('Re: Original Subject', 'Original Subject'),
            ('Fwd: Important Message', 'Important Message'),
            ('RE: FW: Multiple Prefixes', 'Multiple Prefixes'),
            ('[EXTERNAL] Re: Tagged Subject', 'Tagged Subject'),
            ('Normal Subject', 'Normal Subject'),
        ]
        
        for input_subject, expected_output in test_cases:
            result = extractor._extract_original_subject(input_subject)
            assert result == expected_output


class TestAttachmentExtraction:
    """Test attachment extraction and validation functionality"""
    
    def test_extract_safe_attachments(self, extractor, email_with_attachments):
        """Test extraction of safe attachments"""
        attachments = extractor._extract_and_validate_attachments(email_with_attachments)
        
        assert len(attachments) == 2
        
        # Check PDF attachment
        pdf_attachment = next((att for att in attachments if att.filename.endswith('.pdf')), None)
        assert pdf_attachment is not None
        assert pdf_attachment.is_safe
        assert pdf_attachment.content_type == 'application/pdf'
        assert pdf_attachment.size_bytes > 0
        assert pdf_attachment.temporary_path is not None
        assert os.path.exists(pdf_attachment.temporary_path)
        
        # Check text attachment
        txt_attachment = next((att for att in attachments if att.filename.endswith('.txt')), None)
        assert txt_attachment is not None
        assert txt_attachment.is_safe
    
    def test_detect_dangerous_attachments(self, extractor, dangerous_email):
        """Test detection of dangerous attachments"""
        attachments = extractor._extract_and_validate_attachments(dangerous_email)
        
        assert len(attachments) == 1
        exe_attachment = attachments[0]
        
        assert not exe_attachment.is_safe
        assert 'Dangerous file extension' in exe_attachment.security_scan_result
        assert exe_attachment.temporary_path is None  # Should not create temp file for unsafe attachments
    
    def test_attachment_size_validation(self, extractor):
        """Test attachment size validation"""
        # Create email with oversized attachment
        msg = MIMEMultipart()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Large Attachment'
        msg['Message-ID'] = '<large123@example.com>'
        
        # Create attachment larger than limit
        large_content = b'x' * (extractor.MAX_ATTACHMENT_SIZE + 1)
        large_attachment = MIMEApplication(large_content, _subtype='octet-stream')
        large_attachment.add_header('Content-Disposition', 'attachment', filename='large.bin')
        msg.attach(large_attachment)
        
        attachments = extractor._extract_and_validate_attachments(msg)
        
        assert len(attachments) == 1
        assert not attachments[0].is_safe
        assert 'File too large' in attachments[0].security_scan_result
    
    def test_suspicious_content_detection(self, extractor):
        """Test detection of suspicious content in attachments"""
        msg = MIMEMultipart()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Suspicious Content'
        msg['Message-ID'] = '<suspicious123@example.com>'
        
        # Create attachment with suspicious content
        suspicious_content = b'<script>alert("malicious")</script>'
        suspicious_attachment = MIMEApplication(suspicious_content, _subtype='plain')
        suspicious_attachment.add_header('Content-Disposition', 'attachment', filename='suspicious.txt')
        msg.attach(suspicious_attachment)
        
        attachments = extractor._extract_and_validate_attachments(msg)
        
        assert len(attachments) == 1
        assert not attachments[0].is_safe
        assert 'Suspicious content pattern' in attachments[0].security_scan_result
    
    def test_filename_sanitization(self, extractor):
        """Test filename sanitization"""
        test_cases = [
            ('../../etc/passwd', '.._.._etc_passwd'),
            ('file with spaces.txt', 'file_with_spaces.txt'),
            ('file<>:|"*.txt', 'file______.txt'),
            ('very_long_filename_' + 'x' * 100 + '.txt', 'very_long_filename_' + 'x' * 71 + '.txt'),
        ]
        
        for dangerous_filename, expected_safe in test_cases:
            safe_filename = extractor._sanitize_filename(dangerous_filename)
            assert safe_filename == expected_safe
            assert '/' not in safe_filename
            assert '\\' not in safe_filename
    
    def test_secure_temp_file_creation(self, extractor, temp_dir):
        """Test secure temporary file creation"""
        content = b'test content'
        temp_path = extractor._create_secure_temp_file('test.txt', content)
        
        assert os.path.exists(temp_path)
        assert temp_path.startswith(temp_dir)
        
        # Check file permissions (should be 0o600)
        file_stat = os.stat(temp_path)
        assert oct(file_stat.st_mode)[-3:] == '600'
        
        # Check content
        with open(temp_path, 'rb') as f:
            assert f.read() == content


class TestCompleteContentExtraction:
    """Test complete content extraction workflow"""
    
    def test_extract_simple_email_content(self, extractor, simple_email):
        """Test complete extraction of simple email"""
        extracted = extractor.extract_email_content(simple_email)
        
        assert isinstance(extracted, ExtractedContent)
        assert extracted.headers.message_id == '<test123@example.com>'
        assert extracted.plain_text == 'This is a test email body.'
        assert extracted.html_content is None
        assert len(extracted.attachments) == 0
        assert not extracted.thread_analysis.is_reply
        assert len(extracted.content_hash) == 64  # SHA-256 hash length
        assert extracted.extraction_metadata['content_length'] > 0
    
    def test_extract_complex_email_content(self, extractor, html_email):
        """Test complete extraction of complex HTML email"""
        extracted = extractor.extract_email_content(html_email)
        
        assert isinstance(extracted, ExtractedContent)
        assert 'This is plain text content.' in extracted.plain_text
        assert extracted.html_content is not None
        assert extracted.sanitized_html is not None
        assert '<script>' not in extracted.sanitized_html
        assert 'CONTAINS_EXTERNAL_LINKS' not in extracted.security_flags  # No external links in test
    
    def test_extract_threaded_email_content(self, extractor, threaded_email):
        """Test complete extraction of threaded email"""
        extracted = extractor.extract_email_content(threaded_email)
        
        assert extracted.thread_analysis.is_reply
        assert extracted.thread_analysis.thread_depth == 2
        assert extracted.thread_analysis.original_subject == 'Original Subject'
    
    def test_extract_email_with_attachments(self, extractor, email_with_attachments):
        """Test complete extraction of email with attachments"""
        extracted = extractor.extract_email_content(email_with_attachments)
        
        assert len(extracted.attachments) == 2
        assert all(att.is_safe for att in extracted.attachments)
        assert extracted.extraction_metadata['attachment_count'] == 2
    
    def test_extract_dangerous_email_content(self, extractor, dangerous_email):
        """Test complete extraction of dangerous email"""
        extracted = extractor.extract_email_content(dangerous_email)
        
        assert len(extracted.attachments) == 1
        assert not extracted.attachments[0].is_safe
        assert len(extracted.security_flags) > 0
        assert any('UNSAFE_ATTACHMENTS' in flag for flag in extracted.security_flags)
    
    def test_content_hash_consistency(self, extractor, simple_email):
        """Test that content hash is consistent for same content"""
        extracted1 = extractor.extract_email_content(simple_email)
        extracted2 = extractor.extract_email_content(simple_email)
        
        assert extracted1.content_hash == extracted2.content_hash
    
    def test_extraction_statistics(self, extractor, simple_email):
        """Test extraction statistics tracking"""
        initial_stats = extractor.get_extraction_stats()
        assert initial_stats['total_extractions'] == 0
        
        extractor.extract_email_content(simple_email)
        
        stats = extractor.get_extraction_stats()
        assert stats['total_extractions'] == 1
        assert stats['successful_extractions'] == 1
        assert stats['failed_extractions'] == 0


class TestSecurityAndCleanup:
    """Test security features and cleanup functionality"""
    
    def test_security_flag_collection(self, extractor):
        """Test collection of security flags"""
        # Create email with suspicious headers
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Fwd: Suspicious Email'
        msg['Message-ID'] = '<suspicious123@example.com>'
        msg['X-Spam-Flag'] = 'YES'
        msg.set_content('Check out this link: https://suspicious-site.com')
        
        extracted = extractor.extract_email_content(msg)
        
        assert 'FORWARDED_EMAIL' in extracted.security_flags
        assert 'CONTAINS_EXTERNAL_LINKS' in extracted.security_flags
        assert any('SUSPICIOUS_HEADER' in flag for flag in extracted.security_flags)
    
    def test_cleanup_expired_attachments(self, extractor, temp_dir):
        """Test cleanup of expired temporary attachments"""
        # Create some temporary files
        old_file = os.path.join(temp_dir, 'old_file.txt')
        new_file = os.path.join(temp_dir, 'new_file.txt')
        
        with open(old_file, 'w') as f:
            f.write('old content')
        with open(new_file, 'w') as f:
            f.write('new content')
        
        # Make old file appear old by modifying its timestamp
        old_time = datetime.now() - timedelta(hours=25)  # Older than cleanup interval
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
        
        cleaned_count = extractor.cleanup_expired_attachments()
        
        assert cleaned_count == 1
        assert not os.path.exists(old_file)
        assert os.path.exists(new_file)
    
    def test_error_handling_malformed_email(self, extractor):
        """Test error handling with malformed email"""
        # Create malformed email
        msg = EmailMessage()
        # Missing required headers
        msg.set_content('Content without proper headers')
        
        # Should not raise exception but handle gracefully
        extracted = extractor.extract_email_content(msg)
        
        assert isinstance(extracted, ExtractedContent)
        assert extracted.headers.message_id.startswith('generated-')
    
    def test_statistics_reset(self, extractor, simple_email):
        """Test statistics reset functionality"""
        extractor.extract_email_content(simple_email)
        
        stats_before = extractor.get_extraction_stats()
        assert stats_before['total_extractions'] > 0
        
        extractor.reset_extraction_stats()
        
        stats_after = extractor.get_extraction_stats()
        assert stats_after['total_extractions'] == 0
        assert stats_after['successful_extractions'] == 0


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_content_extraction_error_handling(self, extractor):
        """Test handling of content extraction errors"""
        # Create invalid email object
        invalid_email = "not an email object"
        
        with pytest.raises(ContentExtractionError):
            extractor.extract_email_content(invalid_email)
    
    def test_attachment_security_error_handling(self, extractor, temp_dir):
        """Test handling of attachment security errors"""
        # Mock file creation to fail
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with pytest.raises(AttachmentSecurityError):
                extractor._create_secure_temp_file('test.txt', b'content')
    
    def test_graceful_degradation_on_partial_failures(self, extractor):
        """Test graceful degradation when some operations fail"""
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Test Subject'
        msg['Message-ID'] = '<test123@example.com>'
        msg.set_content('Test content')
        
        # Mock thread analysis to fail
        with patch.object(extractor, '_analyze_email_threading', side_effect=Exception("Thread analysis failed")):
            # Should still extract other content successfully
            extracted = extractor.extract_email_content(msg)
            
            assert isinstance(extracted, ExtractedContent)
            assert extracted.plain_text == 'Test content'
            # Thread analysis should have fallback values
            assert extracted.thread_analysis.thread_id == '<test123@example.com>'


if __name__ == '__main__':
    pytest.main([__file__])