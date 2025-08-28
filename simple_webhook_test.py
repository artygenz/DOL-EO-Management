#!/usr/bin/env python3
"""
Simple webhook test to verify the email service endpoint
"""

import requests
import json
from datetime import datetime, timezone

def test_webhook_health():
    """Test the webhook health endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/email/webhook/health", timeout=5)
        print(f"Health check status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_webhook_endpoint():
    """Test the webhook endpoint with a simple payload"""
    test_payload = {
        "metadata": {
            "message_id": "<test-123@lumenlighthouse.ai>",
            "subject": "Test Email",
            "from_email": "test@example.com",
            "to_emails": ["admin@lumenlighthouse.ai"],
            "cc_emails": [],
            "bcc_emails": [],
            "date": datetime.now(timezone.utc).isoformat(),
            "received_date": datetime.now(timezone.utc).isoformat(),
            "size": 512,
            "flags": ["\\Seen"],
            "headers": {
                "From": "test@example.com",
                "To": "admin@lumenlighthouse.ai",
                "Subject": "Test Email"
            }
        },
        "body_text": "This is a test email body.",
        "body_html": "<html><body><p>This is a test email body.</p></body></html>",
        "attachments": []
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/email/webhook",
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f"Webhook test status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"Webhook test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Email Webhook Service")
    print("=" * 40)
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    health_ok = test_webhook_health()
    
    # Test webhook endpoint
    print("\n2. Testing webhook endpoint...")
    webhook_ok = test_webhook_endpoint()
    
    # Summary
    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Health endpoint: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Webhook endpoint: {'✅ PASS' if webhook_ok else '❌ FAIL'}")
    
    if health_ok and webhook_ok:
        print("\n🎉 All tests passed! Email service is working.")
    else:
        print("\n⚠️  Some tests failed. Check the server logs.")
