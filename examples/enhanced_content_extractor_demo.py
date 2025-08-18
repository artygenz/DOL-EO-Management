#!/usr/bin/env python3
"""
Enhanced Content Extractor Demo

This script demonstrates the capabilities of the Enhanced Content Extractor
for the Email Agent system, showing how it processes emails with security
validation, thread analysis, and attachment handling.
"""

import os
import sys
import tempfile
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.email.content_extractor import EnhancedContentExtractor


def create_sample_emails():
    """Create sample emails for demonstration"""
    emails = []
    
    # 1. Simple plain text email
    simple_email = EmailMessage()
    simple_email['From'] = 'john.doe@dol.gov'
    simple_email['To'] = 'jane.smith@dol.gov'
    simple_email['Subject'] = 'Executive Order Processing Update'
    simple_email['Message-ID'] = '<simple123@dol.gov>'
    simple_email['Date'] = 'Mon, 15 Jan 2024 10:30:00 -0500'
    simple_email.set_content("""
Dear Jane,

I wanted to provide you with an update on the Executive Order processing system.
The new automated workflow has been successfully implemented and is now processing
incoming EO documents at a rate of 95% accuracy.

Key achievements:
- Reduced processing time by 60%
- Improved accuracy to 95%
- Enhanced security validation

Please let me know if you have any questions.

Best regards,
John Doe
Senior Systems Analyst
""")
    emails.append(("Simple Email", simple_email))
    
    # 2. HTML email with potential security issues
    html_email = MIMEMultipart('alternative')
    html_email['From'] = 'external.sender@contractor.com'
    html_email['To'] = 'security.team@dol.gov'
    html_email['Subject'] = 'System Integration Proposal'
    html_email['Message-ID'] = '<html456@contractor.com>'
    html_email['Date'] = 'Tue, 16 Jan 2024 14:15:00 -0500'
    
    # Plain text version
    text_part = MIMEText("""
Dear Security Team,

We would like to propose a new system integration that will enhance
your current email processing capabilities.

Please visit our demo site for more information.

Best regards,
External Contractor
""", 'plain')
    html_email.attach(text_part)
    
    # HTML version with potentially dangerous content
    html_content = """
    <html>
    <head><title>System Integration Proposal</title></head>
    <body>
        <h1>Enhanced Email Processing System</h1>
        <p>Dear Security Team,</p>
        <p>We would like to propose a new <strong>system integration</strong> that will enhance
        your current email processing capabilities.</p>
        
        <!-- This script tag should be removed by sanitization -->
        <script>
            console.log("This should be removed for security");
            // Potentially malicious code
        </script>
        
        <p>Please visit our demo site: 
        <a href="https://demo.contractor.com/integration">Demo Site</a></p>
        
        <!-- This should also be sanitized -->
        <a href="javascript:alert('XSS attempt')">Click here</a>
        
        <p>Best regards,<br>
        External Contractor</p>
    </body>
    </html>
    """
    html_part = MIMEText(html_content, 'html')
    html_email.attach(html_part)
    
    emails.append(("HTML Email with Security Issues", html_email))
    
    # 3. Threaded email (reply)
    reply_email = EmailMessage()
    reply_email['From'] = 'jane.smith@dol.gov'
    reply_email['To'] = 'john.doe@dol.gov'
    reply_email['Subject'] = 'Re: Executive Order Processing Update'
    reply_email['Message-ID'] = '<reply789@dol.gov>'
    reply_email['In-Reply-To'] = '<simple123@dol.gov>'
    reply_email['References'] = '<thread-root@dol.gov> <simple123@dol.gov>'
    reply_email['Date'] = 'Mon, 15 Jan 2024 11:45:00 -0500'
    reply_email.set_content("""
Hi John,

Thanks for the update on the Executive Order processing system.
The improvements are impressive!

I have a few follow-up questions:
1. What is the error rate for the remaining 5%?
2. How are we handling edge cases?
3. Can we schedule a demo for the executive team?

Looking forward to your response.

Best,
Jane Smith
Director of Operations
""")
    emails.append(("Threaded Reply Email", reply_email))
    
    # 4. Email with attachments (including potentially dangerous one)
    attachment_email = MIMEMultipart()
    attachment_email['From'] = 'analyst@dol.gov'
    attachment_email['To'] = 'team@dol.gov'
    attachment_email['Subject'] = 'Monthly Report and System Files'
    attachment_email['Message-ID'] = '<attach101@dol.gov>'
    attachment_email['Date'] = 'Wed, 17 Jan 2024 09:00:00 -0500'
    
    # Email body
    body = MIMEText("""
Team,

Please find attached the monthly report and some system files for review.

The PDF contains our performance metrics, and the text file has configuration notes.

Note: Please be careful with the executable file - it's a system utility that should
only be run by authorized personnel.

Best regards,
System Analyst
""", 'plain')
    attachment_email.attach(body)
    
    # Safe PDF attachment
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF'
    pdf_attachment = MIMEApplication(pdf_content, _subtype='pdf')
    pdf_attachment.add_header('Content-Disposition', 'attachment', filename='monthly_report.pdf')
    attachment_email.attach(pdf_attachment)
    
    # Safe text file attachment
    txt_content = b'# Configuration Notes\n\n## Email Processing Settings\n- Max concurrent connections: 10\n- Timeout: 30 seconds\n- Retry attempts: 3\n\n## Security Settings\n- TLS version: 1.3\n- Certificate validation: enabled\n- Attachment scanning: enabled'
    txt_attachment = MIMEApplication(txt_content, _subtype='plain')
    txt_attachment.add_header('Content-Disposition', 'attachment', filename='config_notes.txt')
    attachment_email.attach(txt_attachment)
    
    # Dangerous executable attachment (simulated)
    exe_content = b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00\xb8\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00'  # PE header
    exe_attachment = MIMEApplication(exe_content, _subtype='octet-stream')
    exe_attachment.add_header('Content-Disposition', 'attachment', filename='system_utility.exe')
    attachment_email.attach(exe_attachment)
    
    emails.append(("Email with Attachments", attachment_email))
    
    return emails


def demonstrate_content_extraction():
    """Demonstrate the enhanced content extraction capabilities"""
    print("=" * 80)
    print("ENHANCED CONTENT EXTRACTOR DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Create temporary directory for attachments
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        print()
        
        # Initialize the enhanced content extractor
        extractor = EnhancedContentExtractor(temp_dir=temp_dir, cleanup_interval_hours=1)
        
        # Create sample emails
        sample_emails = create_sample_emails()
        
        for email_name, email_msg in sample_emails:
            print("-" * 60)
            print(f"PROCESSING: {email_name}")
            print("-" * 60)
            
            try:
                # Extract content
                extracted = extractor.extract_email_content(email_msg)
                
                # Display results
                print(f"Message ID: {extracted.headers.message_id}")
                print(f"From: {extracted.headers.sender}")
                if extracted.headers.sender_name:
                    print(f"Sender Name: {extracted.headers.sender_name}")
                print(f"To: {', '.join(extracted.headers.recipients)}")
                print(f"Subject: {extracted.headers.subject}")
                print(f"Date: {extracted.headers.date}")
                print()
                
                # Thread analysis
                print("THREAD ANALYSIS:")
                print(f"  Thread ID: {extracted.thread_analysis.thread_id}")
                print(f"  Is Reply: {extracted.thread_analysis.is_reply}")
                print(f"  Is Forward: {extracted.thread_analysis.is_forward}")
                print(f"  Thread Depth: {extracted.thread_analysis.thread_depth}")
                print(f"  Original Subject: {extracted.thread_analysis.original_subject}")
                print(f"  Participants: {len(extracted.thread_analysis.conversation_participants)}")
                print()
                
                # Content summary
                print("CONTENT SUMMARY:")
                print(f"  Plain Text Length: {len(extracted.plain_text)} characters")
                if extracted.html_content:
                    print(f"  HTML Content Length: {len(extracted.html_content)} characters")
                    print(f"  Sanitized HTML Length: {len(extracted.sanitized_html or '')} characters")
                print(f"  Content Hash: {extracted.content_hash[:16]}...")
                print()
                
                # Attachments
                if extracted.attachments:
                    print("ATTACHMENTS:")
                    for i, attachment in enumerate(extracted.attachments, 1):
                        print(f"  {i}. {attachment.filename}")
                        print(f"     Type: {attachment.content_type}")
                        print(f"     Size: {attachment.size_bytes} bytes")
                        print(f"     Safe: {'✓' if attachment.is_safe else '✗'}")
                        if not attachment.is_safe:
                            print(f"     Security Issue: {attachment.security_scan_result}")
                        if attachment.temporary_path:
                            print(f"     Temp Path: {attachment.temporary_path}")
                        print()
                else:
                    print("ATTACHMENTS: None")
                    print()
                
                # Security flags
                if extracted.security_flags:
                    print("SECURITY FLAGS:")
                    for flag in extracted.security_flags:
                        print(f"  ⚠️  {flag}")
                    print()
                else:
                    print("SECURITY FLAGS: None (Clean)")
                    print()
                
                # Extraction metadata
                print("EXTRACTION METADATA:")
                print(f"  Duration: {extracted.extraction_metadata['extraction_duration_ms']:.2f} ms")
                print(f"  Content Length: {extracted.extraction_metadata['content_length']} chars")
                print(f"  Attachment Count: {extracted.extraction_metadata['attachment_count']}")
                print(f"  Security Flags: {extracted.extraction_metadata['security_flags_count']}")
                print()
                
                # Show a snippet of the plain text content
                if extracted.plain_text:
                    print("CONTENT PREVIEW:")
                    preview = extracted.plain_text[:200].replace('\n', ' ').strip()
                    if len(extracted.plain_text) > 200:
                        preview += "..."
                    print(f"  {preview}")
                    print()
                
                # Show HTML sanitization results if applicable
                if extracted.html_content and extracted.sanitized_html:
                    print("HTML SANITIZATION:")
                    print(f"  Original HTML contained: {len(extracted.html_content)} characters")
                    print(f"  Sanitized HTML contains: {len(extracted.sanitized_html)} characters")
                    
                    # Check for removed dangerous content
                    dangerous_removed = []
                    if '<script>' in extracted.html_content.lower() and '<script>' not in extracted.sanitized_html.lower():
                        dangerous_removed.append("Script tags")
                    if 'javascript:' in extracted.html_content.lower() and 'javascript:' not in extracted.sanitized_html.lower():
                        dangerous_removed.append("JavaScript URLs")
                    if 'data:' in extracted.html_content.lower() and 'data:' not in extracted.sanitized_html.lower():
                        dangerous_removed.append("Data URLs")
                    
                    if dangerous_removed:
                        print(f"  Removed: {', '.join(dangerous_removed)}")
                    print()
                
            except Exception as e:
                print(f"❌ ERROR: Failed to extract content: {e}")
                print()
        
        # Show extraction statistics
        print("-" * 60)
        print("EXTRACTION STATISTICS")
        print("-" * 60)
        stats = extractor.get_extraction_stats()
        print(f"Total Extractions: {stats['total_extractions']}")
        print(f"Successful: {stats['successful_extractions']}")
        print(f"Failed: {stats['failed_extractions']}")
        print(f"Security Violations: {stats['security_violations']}")
        print(f"Attachments Processed: {stats['attachments_processed']}")
        print()
        
        # Demonstrate cleanup
        print("CLEANUP DEMONSTRATION:")
        cleaned_files = extractor.cleanup_expired_attachments()
        print(f"Cleaned up {cleaned_files} expired temporary files")
        print()
        
        print("=" * 80)
        print("DEMONSTRATION COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    demonstrate_content_extraction()