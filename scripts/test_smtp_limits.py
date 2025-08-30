#!/usr/bin/env python3
"""
SMTP Limits Testing Script

This script helps identify SMTP provider limits by testing connection behavior.
"""

import smtplib
import ssl
import os
import time
from datetime import datetime

def test_smtp_connection_limits():
    """Test SMTP connection limits and behavior"""
    
    smtp_host = os.getenv('SMTP_HOST', 'lumenlighthouse.ai')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    username = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASS')
    
    print(f"Testing SMTP limits for: {smtp_host}:{smtp_port}")
    print(f"Username: {username}")
    print("=" * 50)
    
    # Test 1: Single connection behavior
    print("\n1. Testing single SMTP connection...")
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.starttls(context=context)
            smtp.login(username, password)
            print("✓ Single connection successful")
            
            # Get server info
            code, msg = smtp.noop()
            print(f"  Server response: {code} {msg.decode()}")
            
    except Exception as e:
        print(f"✗ Single connection failed: {e}")
        return False
    
    # Test 2: Rapid connection attempts
    print("\n2. Testing rapid connection attempts...")
    connection_count = 0
    for i in range(5):
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
                smtp.starttls(context=context)
                smtp.login(username, password)
                connection_count += 1
                print(f"  Connection {i+1}: ✓")
            time.sleep(0.1)  # Small delay
        except Exception as e:
            print(f"  Connection {i+1}: ✗ {e}")
            if "421" in str(e) or "too many" in str(e).lower():
                print(f"  → Rate limit hit at connection {i+1}")
                break
    
    print(f"  Successful rapid connections: {connection_count}/5")
    
    # Test 3: Connection with delay
    print("\n3. Testing connections with 5-second delays...")
    delayed_connections = 0
    for i in range(3):
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
                smtp.starttls(context=context)
                smtp.login(username, password)
                delayed_connections += 1
                print(f"  Delayed connection {i+1}: ✓")
            if i < 2:  # Don't sleep after the last one
                time.sleep(5)
        except Exception as e:
            print(f"  Delayed connection {i+1}: ✗ {e}")
    
    print(f"  Successful delayed connections: {delayed_connections}/3")
    
    # Test 4: Check server capabilities
    print("\n4. Checking server capabilities...")
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.starttls(context=context)
            smtp.login(username, password)
            
            # Get EHLO response
            code, msg = smtp.ehlo()
            print(f"  EHLO response: {code}")
            capabilities = msg.decode().split('\n')
            for cap in capabilities[:5]:  # Show first 5 capabilities
                print(f"    {cap.strip()}")
                
    except Exception as e:
        print(f"  Capabilities check failed: {e}")
    
    print("\n" + "=" * 50)
    print("SMTP Limits Test Complete")
    print("\nRecommendations:")
    print("- If rate limited quickly: Increase delays between emails")
    print("- If 421 errors: Reduce concurrent connections")
    print("- Contact your email provider for specific limits")

def get_provider_recommendations():
    """Get recommendations based on common provider limits"""
    
    recommendations = {
        "general": {
            "max_concurrent": 1,
            "delay_between_emails": 6.0,  # seconds
            "max_per_hour": 100,
            "retry_delay": 60.0  # seconds
        },
        "shared_hosting": {
            "max_concurrent": 1,
            "delay_between_emails": 10.0,
            "max_per_hour": 50,
            "retry_delay": 120.0
        },
        "business_hosting": {
            "max_concurrent": 2,
            "delay_between_emails": 3.0,
            "max_per_hour": 200,
            "retry_delay": 30.0
        }
    }
    
    print("\nCommon SMTP Provider Limits:")
    print("=" * 40)
    
    for provider_type, limits in recommendations.items():
        print(f"\n{provider_type.replace('_', ' ').title()}:")
        print(f"  Max concurrent connections: {limits['max_concurrent']}")
        print(f"  Delay between emails: {limits['delay_between_emails']}s")
        print(f"  Max emails per hour: {limits['max_per_hour']}")
        print(f"  Retry delay: {limits['retry_delay']}s")

if __name__ == "__main__":
    print("SMTP Provider Limits Checker")
    print(f"Timestamp: {datetime.now()}")
    
    if not os.getenv('EMAIL_USER') or not os.getenv('EMAIL_PASS'):
        print("\n❌ Missing EMAIL_USER or EMAIL_PASS environment variables")
        print("Please set these in your .env file to test SMTP limits")
        exit(1)
    
    test_smtp_connection_limits()
    get_provider_recommendations()
