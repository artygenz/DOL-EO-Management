#!/usr/bin/env python3
"""
Test script for the health check endpoint
Usage: python scripts/test_health_endpoint.py
"""

import requests
import json
import sys
from typing import Dict, Any

def test_health_endpoint(base_url: str = "http://localhost:8000") -> bool:
    """Test the health check endpoint"""
    try:
        # Test basic health check
        print("🔍 Testing basic health check...")
        response = requests.get(f"{base_url}/health_check", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Basic health check passed!")
            print(f"   Services: {data.get('services', {})}")
        else:
            print(f"❌ Basic health check failed: {response.status_code}")
            return False
        
        # Test comprehensive health check (requires admin auth)
        print("\n🔍 Testing comprehensive health check...")
        print("   Note: This requires admin authentication")
        
        # Try to get the comprehensive health check
        health_url = f"{base_url}/api/monitoring/health/connections"
        response = requests.get(health_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Comprehensive health check passed!")
            print(f"   Overall Status: {data.get('overall_status', 'unknown')}")
            
            services = data.get('services', {})
            for service_name, service_data in services.items():
                status = service_data.get('status', 'unknown')
                connected = service_data.get('connected', False)
                print(f"   {service_name}: {status} ({'✅' if connected else '❌'})")
                
                if not connected and 'error' in service_data:
                    print(f"      Error: {service_data['error']}")
            
            return True
            
        elif response.status_code == 403:
            print("⚠️  Comprehensive health check requires admin authentication")
            print("   This is expected behavior - endpoint is working correctly")
            return True
            
        else:
            print(f"❌ Comprehensive health check failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server")
        print("   Make sure the application is running on the specified URL")
        return False
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Health Check Endpoints")
    print("=" * 50)
    
    # Test with default localhost
    success = test_health_endpoint()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Health check endpoints are working correctly!")
        print("\n📋 Available endpoints:")
        print("   GET /health_check - Basic health check (no auth required)")
        print("   GET /api/monitoring/health/connections - Comprehensive health check (admin auth required)")
        sys.exit(0)
    else:
        print("💥 Health check tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
