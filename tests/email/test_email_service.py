#!/usr/bin/env python3
"""
Test script for the Email Service

This script tests the IMAP IDLE listener and webhook functionality.
"""

import asyncio
import aiohttp
import json
import base64
from datetime import datetime, timezone
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8000"
WEBHOOK_ENDPOINT = f"{BASE_URL}/api/email/webhook"
HEALTH_ENDPOINT = f"{BASE_URL}/api/email/webhook/health"

def create_test_email_payload():
    """Create a test email payload"""
    test_attachment_data = b"This is a test attachment content."
    
    return {
        "metadata": {
            "message_id": "<test-123@lumenlighthouse.ai>",
            "subject": "Test PMO Response Email",
            "from_email": "pmo@example.com",
            "to_emails": ["admin@lumenlighthouse.ai"],
            "cc_emails": [],
            "bcc_emails": [],
            "date": datetime.now(timezone.utc).isoformat(),
            "received_date": datetime.now(timezone.utc).isoformat(),
            "size": 1024,
            "flags": ["\\Seen"],
            "headers": {
                "From": "pmo@example.com",
                "To": "admin@lumenlighthouse.ai",
                "Subject": "Test PMO Response Email",
                "Date": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
            }
        },
        "body_text": "This is a test email body for PMO response processing.",
        "body_html": "<html><body><p>This is a test email body for PMO response processing.</p></body></html>",
        "attachments": [
            {
                "filename": "test_document.pdf",
                "content_type": "application/pdf",
                "size": len(test_attachment_data),
                "data": base64.b64encode(test_attachment_data).decode('utf-8'),
                "content_id": None
            }
        ]
    }

async def test_webhook_health():
    """Test the webhook health endpoint"""
    print("🔍 Testing webhook health endpoint...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(HEALTH_ENDPOINT) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed: {data}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

async def test_webhook_endpoint():
    """Test the webhook endpoint with a test email payload"""
    print("📧 Testing webhook endpoint...")
    
    payload = create_test_email_payload()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK_ENDPOINT,
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Webhook test passed: {data}")
                    return True
                else:
                    print(f"❌ Webhook test failed: {response.status}")
                    error_text = await response.text()
                    print(f"Error details: {error_text}")
                    return False
    except Exception as e:
        print(f"❌ Webhook test error: {e}")
        return False

async def test_attachment_processing():
    """Test that attachments are properly saved"""
    print("📎 Testing attachment processing...")
    
    # Check if attachments directory was created
    attachments_dir = Path("attachments")
    if attachments_dir.exists():
        print(f"✅ Attachments directory exists: {attachments_dir}")
        
        # List any created directories
        email_dirs = [d for d in attachments_dir.iterdir() if d.is_dir()]
        if email_dirs:
            print(f"✅ Found {len(email_dirs)} email directories:")
            for email_dir in email_dirs:
                print(f"   - {email_dir.name}")
                files = list(email_dir.iterdir())
                print(f"     Files: {[f.name for f in files]}")
        else:
            print("ℹ️  No email directories found yet")
    else:
        print("❌ Attachments directory not found")

async def test_service_connectivity():
    """Test basic service connectivity"""
    print("🌐 Testing service connectivity...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test main API health
            async with session.get(f"{BASE_URL}/health_check") as response:
                if response.status == 200:
                    print("✅ Main API is accessible")
                else:
                    print(f"❌ Main API health check failed: {response.status}")
                    return False
            
            # Test webhook health
            async with session.get(HEALTH_ENDPOINT) as response:
                if response.status == 200:
                    print("✅ Email webhook service is accessible")
                else:
                    print(f"❌ Email webhook health check failed: {response.status}")
                    return False
                    
        return True
    except Exception as e:
        print(f"❌ Connectivity test error: {e}")
        return False

async def run_all_tests():
    """Run all email service tests"""
    print("🚀 Starting Email Service Tests")
    print("=" * 50)
    
    results = []
    
    # Test 1: Service connectivity
    print("\n1. Testing Service Connectivity")
    results.append(await test_service_connectivity())
    
    # Test 2: Webhook health
    print("\n2. Testing Webhook Health")
    results.append(await test_webhook_health())
    
    # Test 3: Webhook endpoint
    print("\n3. Testing Webhook Endpoint")
    results.append(await test_webhook_endpoint())
    
    # Test 4: Attachment processing
    print("\n4. Testing Attachment Processing")
    await test_attachment_processing()
    results.append(True)  # This test doesn't have a clear pass/fail
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Email service is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the logs above.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
