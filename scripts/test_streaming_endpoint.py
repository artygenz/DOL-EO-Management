#!/usr/bin/env python3
"""
Test script to verify the streaming endpoint is working correctly.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"
CHAT_STREAM_URL = f"{BASE_URL}/chat/stream"

# Test credentials
TEST_CREDENTIALS = {
    "username": "admin@example.com",
    "password": "admin123"
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

def test_streaming_endpoint(token):
    """Test the streaming endpoint and verify response format."""
    print("\n=== Testing Streaming Endpoint ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    
    payload = {
        "message": "Hello, test streaming message",
        "context": {
            "role": "admin",
            "user_id": "1"
        }
    }
    
    try:
        print("Making streaming request...")
        response = requests.post(CHAT_STREAM_URL, headers=headers, json=payload, stream=True)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        if response.status_code == 200:
            print("\nStreaming response:")
            chunk_count = 0
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    chunk_count += 1
                    print(f"Chunk {chunk_count}: {line_str}")
                    
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            print(f"  Parsed data: {data}")
                        except json.JSONDecodeError:
                            print(f"  Failed to parse JSON: {line_str[6:]}")
                    
                    # Stop after 10 chunks for testing
                    if chunk_count >= 10:
                        print("Stopping after 10 chunks for testing...")
                        break
                        
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Main test function."""
    print("Streaming Endpoint Test")
    print("======================")
    
    # Get authentication token
    print("Getting authentication token...")
    token = get_auth_token()
    
    if not token:
        print("Failed to get authentication token. Exiting.")
        return
    
    print(f"Token obtained: {token[:20]}...")
    
    # Test streaming endpoint
    success = test_streaming_endpoint(token)
    
    if success:
        print("\n✅ Streaming endpoint test completed successfully!")
    else:
        print("\n❌ Streaming endpoint test failed!")

if __name__ == "__main__":
    main()
