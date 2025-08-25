#!/usr/bin/env python3
"""
Test script for authentication endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """Test user login"""
    print("🔐 Testing Login Endpoint")
    print("=" * 40)
    
    # Test with valid credentials
    login_data = {
        "email": "jack.smith@lumenlighthouse.ai",
        "password": "Lumen@2025"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"Access Token: {data['access_token'][:50]}...")
            print(f"User: {data['user']['name']} ({data['user']['email']})")
            return data['access_token']
        else:
            print(f"❌ Login failed: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_me_endpoint(token):
    """Test /auth/me endpoint with token"""
    if not token:
        print("❌ No token available for /auth/me test")
        return
    
    print("\n👤 Testing /auth/me Endpoint")
    print("=" * 40)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ /auth/me successful!")
            print(f"User: {data['data']['name']} ({data['data']['email']})")
            print(f"Role: {data['data']['role']}")
            print(f"Org Role: {data['data']['org_role']}")
        else:
            print(f"❌ /auth/me failed: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_invalid_login():
    """Test login with invalid credentials"""
    print("\n❌ Testing Invalid Login")
    print("=" * 40)
    
    login_data = {
        "email": "invalid@example.com",
        "password": "wrongpassword"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Correctly rejected invalid credentials")
        else:
            print(f"❌ Unexpected response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health_check():
    """Test health check endpoint"""
    print("🏥 Testing Health Check")
    print("=" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/health_check")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Health check successful!")
        else:
            print(f"❌ Health check failed: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Authentication API Test Suite")
    print("=" * 50)
    
    # Test health check first
    test_health_check()
    
    # Test login
    token = test_login()
    
    # Test /auth/me with token
    test_me_endpoint(token)
    
    # Test invalid login
    test_invalid_login()
    
    print("\n" + "=" * 50)
    print("🏁 Test suite completed!")
