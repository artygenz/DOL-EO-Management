#!/usr/bin/env python3
"""
Test script for the dedicated health check endpoints
"""

import requests
import json
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

def test_health_endpoints():
    """Test the dedicated health check endpoints"""
    
    # Configuration
    base_url = "http://localhost:8000"
    api_url = f"{base_url}/api/monitoring"
    
    # You'll need to get a valid admin token for testing
    # This is just a placeholder - in real testing you'd authenticate first
    headers = {
        "Authorization": "Bearer YOUR_ADMIN_TOKEN_HERE",
        "Content-Type": "application/json"
    }
    
    print("Testing Dedicated Health Check Endpoints")
    print("=" * 60)
    
    # Test 1: Database health check
    print("\n1. Testing GET /health/database")
    print("-" * 40)
    try:
        response = requests.get(f"{api_url}/health/database", headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Connected: {data.get('connected')}")
            print(f"Response Time: {data.get('response_time_ms')}ms")
            print(f"Database Version: {data.get('database_version')}")
            print(f"Table Counts: {data.get('table_counts')}")
            print(f"Connection Pool: {data.get('connection_pool')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 2: Redis health check
    print("\n2. Testing GET /health/redis")
    print("-" * 40)
    try:
        response = requests.get(f"{api_url}/health/redis", headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Connected: {data.get('connected')}")
            print(f"Response Time: {data.get('response_time_ms')}ms")
            print(f"Host: {data.get('host')}:{data.get('port')}")
            print(f"Operations Tested: {data.get('operations_tested')}")
            print(f"Redis Info: {data.get('redis_info')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 3: Compare with general health check
    print("\n3. Testing GET /health/connections (for comparison)")
    print("-" * 40)
    try:
        response = requests.get(f"{api_url}/health/connections", headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Overall Status: {data.get('overall_status')}")
            print(f"Services: {list(data.get('services', {}).keys())}")
            for service, status in data.get('services', {}).items():
                print(f"  {service}: {status.get('status', 'unknown')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("\n" + "=" * 60)
    print("Health endpoint testing completed!")
    print("\nAvailable health endpoints:")
    print("1. GET /api/monitoring/health/database - Detailed database health")
    print("2. GET /api/monitoring/health/redis - Detailed Redis health")
    print("3. GET /api/monitoring/health/connections - General health check")
    print("\nAll endpoints require admin authentication.")

if __name__ == "__main__":
    test_health_endpoints()
