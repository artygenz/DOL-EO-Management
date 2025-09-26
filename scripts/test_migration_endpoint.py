#!/usr/bin/env python3
"""
Test script for the migration endpoints
"""

import requests
import json
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

def test_migration_endpoints():
    """Test the migration endpoints"""
    
    # Configuration
    base_url = "http://localhost:8000"
    api_url = f"{base_url}/api/monitoring"
    
    # You'll need to get a valid admin token for testing
    # This is just a placeholder - in real testing you'd authenticate first
    headers = {
        "Authorization": "Bearer YOUR_ADMIN_TOKEN_HERE",
        "Content-Type": "application/json"
    }
    
    print("Testing Migration Endpoints")
    print("=" * 50)
    
    # Test 1: Get migration status
    print("\n1. Testing GET /migrations/status")
    try:
        response = requests.get(f"{api_url}/migrations/status", headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Current Revision: {data.get('current_revision')}")
            print(f"Head Revision: {data.get('head_revision')}")
            print(f"Is Up to Date: {data.get('is_up_to_date')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 2: Run migrations (commented out for safety)
    print("\n2. Testing POST /migrations/upgrade (COMMENTED OUT FOR SAFETY)")
    print("To test this endpoint:")
    print("1. Make sure you have a valid admin token")
    print("2. Uncomment the code below")
    print("3. Ensure you're in a test environment")
    
    # Uncomment the following lines to test the upgrade endpoint
    # try:
    #     response = requests.post(f"{api_url}/migrations/upgrade", headers=headers)
    #     print(f"Status Code: {response.status_code}")
    #     if response.status_code == 200:
    #         data = response.json()
    #         print(f"Success: {data.get('success')}")
    #         print(f"Message: {data.get('message')}")
    #         print(f"Current Revision: {data.get('current_revision')}")
    #     else:
    #         print(f"Error: {response.text}")
    # except Exception as e:
    #     print(f"Request failed: {e}")
    
    print("\n" + "=" * 50)
    print("Migration endpoint testing completed!")
    print("\nTo use these endpoints in production:")
    print("1. POST /api/monitoring/migrations/upgrade - Run migrations")
    print("2. GET /api/monitoring/migrations/status - Check migration status")
    print("\nBoth endpoints require admin authentication.")

if __name__ == "__main__":
    test_migration_endpoints()
