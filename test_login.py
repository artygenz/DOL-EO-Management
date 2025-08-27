#!/usr/bin/env python3
"""
Simple test script for login endpoint
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login(email, password):
    """Test login with given credentials"""
    print(f"🔐 Testing login for: {email}")
    print("=" * 50)
    
    login_data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"Access Token: {data['access_token'][:50]}...")
            print(f"User: {data['user']['name']} ({data['user']['email']})")
            print(f"Role: {data['user']['role']}")
            print(f"Org Role: {data['user']['org_role']}")
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

if __name__ == "__main__":
    print("🧪 Login Test Suite")
    print("=" * 50)
    
    # Test with different users
    test_users = [
        ("jack.smith@lumenlighthouse.ai", "Lumen@2025"),
        ("Kevin.Brown@lumenlighthouse.ai", "Lumen@2025"),
        ("Sophia.Carty@lumenlighthouse.ai", "Lumen@2025"),
    ]
    
    for email, password in test_users:
        token = test_login(email, password)
        if token:
            test_me_endpoint(token)
        print("\n" + "-" * 50)
    
    # Test invalid login
    print("\n❌ Testing Invalid Login")
    print("=" * 40)
    test_login("invalid@example.com", "wrongpassword")
