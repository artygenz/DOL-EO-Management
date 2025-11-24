#!/usr/bin/env python3
"""
Test script for the chat API endpoints.
This script tests both streaming and non-streaming chat endpoints.
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"
CHAT_QUERY_URL = f"{BASE_URL}/chat/query"
CHAT_STREAM_URL = f"{BASE_URL}/chat/stream"

# Test credentials (you may need to adjust these based on your test data)
TEST_CREDENTIALS = {
    "username": "admin@example.com",  # Adjust based on your test user
    "password": "admin123"  # Adjust based on your test user
}

def get_auth_token():
    """Get authentication token by logging in."""
    try:
        response = requests.post(LOGIN_URL, json=TEST_CREDENTIALS)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error during login: {e}")
        return None

def test_non_streaming_chat(token):
    """Test the non-streaming chat endpoint."""
    print("\n=== Testing Non-Streaming Chat ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": "Hello, this is a test message",
        "context": {
            "role": "admin",
            "user_id": "1"
        }
    }
    
    try:
        response = requests.post(CHAT_QUERY_URL, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_streaming_chat(token):
    """Test the streaming chat endpoint."""
    print("\n=== Testing Streaming Chat ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": "Hello, this is a streaming test message",
        "context": {
            "role": "admin",
            "user_id": "1"
        }
    }
    
    try:
        response = requests.post(CHAT_STREAM_URL, headers=headers, json=payload, stream=True)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Streaming response:")
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            print(f"  {data}")
                        except json.JSONDecodeError:
                            print(f"  Raw line: {line_str}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Main test function."""
    print("Chat API Test Script")
    print("===================")
    
    # Get authentication token
    print("Getting authentication token...")
    token = get_auth_token()
    
    if not token:
        print("Failed to get authentication token. Exiting.")
        sys.exit(1)
    
    print(f"Token obtained: {token[:20]}...")
    
    # Test non-streaming endpoint
    non_streaming_success = test_non_streaming_chat(token)
    
    # Test streaming endpoint
    streaming_success = test_streaming_chat(token)
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Non-streaming chat: {'PASS' if non_streaming_success else 'FAIL'}")
    print(f"Streaming chat: {'PASS' if streaming_success else 'FAIL'}")
    
    if non_streaming_success and streaming_success:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
