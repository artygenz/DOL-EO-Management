#!/usr/bin/env python3
"""
Test script to verify Redis connection for Celery
Usage: python scripts/test_redis_connection.py
"""

import os
import sys
import redis
from celery import Celery

def test_redis_connection():
    """Test basic Redis connection"""
    try:
        # Get Redis configuration from environment
        redis_host = os.getenv('REDIS_HOST', 'redis')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_url = os.getenv('REDIS_URL', f'redis://{redis_host}:{redis_port}/0')
        
        print(f"Testing Redis connection to: {redis_url}")
        
        # Test basic Redis connection
        r = redis.from_url(redis_url)
        r.ping()
        print("✅ Redis connection successful!")
        
        # Test basic operations
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        assert value.decode() == 'test_value'
        print("✅ Redis read/write operations successful!")
        
        # Clean up
        r.delete('test_key')
        print("✅ Redis cleanup successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def test_celery_connection():
    """Test Celery broker connection"""
    try:
        # Get Celery configuration
        broker_url = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://redis:6379/0'))
        result_backend = os.getenv('CELERY_RESULT_BACKEND', broker_url)
        
        print(f"Testing Celery broker: {broker_url}")
        print(f"Testing Celery backend: {result_backend}")
        
        # Create Celery app
        celery_app = Celery(
            'test_app',
            broker=broker_url,
            backend=result_backend
        )
        
        # Test broker connection
        celery_app.control.inspect().stats()
        print("✅ Celery broker connection successful!")
        
        # Test result backend
        celery_app.backend.get('test_result')
        print("✅ Celery result backend connection successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Celery connection failed: {e}")
        return False

def main():
    """Main test function"""
    print("🔍 Testing Redis and Celery connections...")
    print("=" * 50)
    
    # Test Redis
    redis_success = test_redis_connection()
    print()
    
    # Test Celery
    celery_success = test_celery_connection()
    print()
    
    # Summary
    print("=" * 50)
    if redis_success and celery_success:
        print("🎉 All tests passed! Redis and Celery are properly configured.")
        sys.exit(0)
    else:
        print("💥 Some tests failed. Please check your configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()
