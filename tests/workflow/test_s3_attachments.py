#!/usr/bin/env python3
"""
Test script for S3 attachment processing functionality.
"""

import os
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_s3_attachment_processing():
    """Test the S3 attachment processing functionality."""
    
    # Mock EO payload with S3 attachment
    eo_payload = {
        "message_id": "test-msg-123",
        "subject": "Test EO with S3 Attachment",
        "sender": "test@example.com",
        "recipients": ["ops@dol.gov"],
        "received_at": datetime.now(timezone.utc),
        "body_text": "This is a test EO with an S3 attachment.",
        "raw_mime_s3_key": "eo-attachments/test-123/test-eo.pdf"  # Mock S3 key
    }
    
    print("=== Testing S3 Attachment Processing ===")
    print(f"EO Payload: {eo_payload}")
    
    try:
        # Test S3 service initialization
        from src.email.s3_service import S3Service, process_eo_attachment
        
        print("\n1. Testing S3 Service initialization...")
        s3_service = S3Service()
        print(f"✅ S3 Service initialized with bucket: {s3_service.bucket_name}")
        
        # Test file existence check
        print("\n2. Testing file existence check...")
        exists = s3_service.file_exists(eo_payload["raw_mime_s3_key"])
        print(f"File exists: {exists}")
        
        if exists:
            # Test text extraction
            print("\n3. Testing PDF text extraction...")
            success, result = process_eo_attachment(eo_payload["raw_mime_s3_key"])
            if success:
                print(f"✅ Text extraction successful: {len(result)} characters")
                print(f"First 200 characters: {result[:200]}...")
            else:
                print(f"❌ Text extraction failed: {result}")
        else:
            print("⚠️  Test file not found in S3, skipping text extraction")
        
        # Test workflow integration
        print("\n4. Testing workflow integration...")
        from src.workflow.tasks import store_email
        
        # This would normally be called by Celery
        result = store_email(eo_payload)
        print(f"✅ Workflow result: {result}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        print("\nMake sure to set up AWS credentials:")
        print("export AWS_ACCESS_KEY_ID=your_key")
        print("export AWS_SECRET_ACCESS_KEY=your_secret")
        print("export AWS_S3_BUCKET=your_bucket")
        print("export AWS_REGION=us-east-1")

def test_email_attachment_processing():
    """Test email attachment processing functionality."""
    
    print("\n=== Testing Email Attachment Processing ===")
    
    try:
        from src.email.attachment_processor import create_eo_payload_from_email
        from email.message import EmailMessage
        
        # Create a mock email with attachment
        email_msg = EmailMessage()
        email_msg["Subject"] = "Test EO with Attachment"
        email_msg["From"] = "test@example.com"
        email_msg["To"] = "ops@dol.gov"
        email_msg.set_content("This is a test EO email with a PDF attachment.")
        
        # Add a mock PDF attachment
        email_msg.add_attachment(
            b"Mock PDF content",
            maintype="application",
            subtype="pdf",
            filename="test-eo.pdf"
        )
        
        print("✅ Mock email created with attachment")
        
        # Test payload creation
        payload = create_eo_payload_from_email(email_msg, "test-msg-456")
        print(f"✅ EO payload created: {payload}")
        
    except Exception as e:
        print(f"❌ Error during email testing: {e}")

if __name__ == "__main__":
    test_s3_attachment_processing()
    test_email_attachment_processing()
    
    print("\n=== Summary ===")
    print("To use S3 attachments:")
    print("1. Set up AWS credentials in environment variables")
    print("2. Create an S3 bucket for EO attachments")
    print("3. Upload PDF attachments to S3")
    print("4. Use the raw_mime_s3_key in EO payloads")
    print("5. The workflow will automatically extract text from PDFs") 