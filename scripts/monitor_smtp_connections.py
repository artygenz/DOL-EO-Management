#!/usr/bin/env python3
"""
SMTP Connection Monitor

This script monitors and tests SMTP connections to understand rate limiting.
"""

import os
import time
import socket
import subprocess
import threading
from datetime import datetime

def get_smtp_config():
    """Get SMTP configuration"""
    return {
        'host': os.getenv('SMTP_HOST', 'lumenlighthouse.ai'),
        'port': int(os.getenv('SMTP_PORT', 587)),
        'username': os.getenv('EMAIL_USER'),
        'password': os.getenv('EMAIL_PASS')
    }

def resolve_smtp_host(hostname):
    """Resolve SMTP hostname to IP"""
    try:
        ip = socket.gethostbyname(hostname)
        print(f"📍 {hostname} → {ip}")
        return ip
    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")
        return None

def check_active_connections(ip_address):
    """Check active connections to SMTP server"""
    try:
        # Check netstat for connections to SMTP server
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
        connections = []
        
        for line in result.stdout.split('\n'):
            if ip_address in line and ':587' in line:
                connections.append(line.strip())
        
        return connections
    except Exception as e:
        print(f"❌ Error checking connections: {e}")
        return []

def test_smtp_connection_quick(config):
    """Test a quick SMTP connection"""
    import smtplib
    import ssl
    
    start_time = time.time()
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(config['host'], config['port'], timeout=10) as smtp:
            smtp.starttls(context=context)
            if config['username'] and config['password']:
                smtp.login(config['username'], config['password'])
            
            # Just test the connection
            code, msg = smtp.noop()
            
        duration = time.time() - start_time
        print(f"✅ SMTP connection successful in {duration:.2f}s - Code: {code}")
        return True, f"Code: {code}"
        
    except Exception as e:
        duration = time.time() - start_time
        error_str = str(e)
        
        # Check for rate limiting
        if '421' in error_str or 'too many' in error_str.lower():
            print(f"🚫 RATE LIMITED in {duration:.2f}s: {e}")
            return False, "RATE_LIMITED"
        else:
            print(f"❌ SMTP connection failed in {duration:.2f}s: {e}")
            return False, str(e)

def monitor_connections_continuous(duration_seconds=60):
    """Monitor SMTP connections continuously"""
    config = get_smtp_config()
    ip = resolve_smtp_host(config['host'])
    
    if not ip:
        return
    
    print(f"\n🔍 Monitoring SMTP connections for {duration_seconds} seconds...")
    print(f"   Host: {config['host']}:{config['port']}")
    print(f"   IP: {ip}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    start_time = time.time()
    check_interval = 5  # Check every 5 seconds
    
    while time.time() - start_time < duration_seconds:
        # Check active connections
        connections = check_active_connections(ip)
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if connections:
            print(f"[{timestamp}] 🔗 Active connections: {len(connections)}")
            for conn in connections:
                print(f"    {conn}")
        else:
            print(f"[{timestamp}] ✅ No active SMTP connections")
        
        time.sleep(check_interval)

def test_multiple_connections(num_connections=3, delay_between=1):
    """Test multiple SMTP connections to see rate limiting"""
    config = get_smtp_config()
    
    print(f"\n🧪 Testing {num_connections} SMTP connections with {delay_between}s delay...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    results = []
    
    for i in range(num_connections):
        print(f"\n🔄 Connection {i+1}/{num_connections}")
        success, message = test_smtp_connection_quick(config)
        results.append({
            'connection': i+1,
            'success': success,
            'message': message,
            'timestamp': datetime.now()
        })
        
        if i < num_connections - 1:  # Don't delay after last connection
            print(f"   ⏱️  Waiting {delay_between}s...")
            time.sleep(delay_between)
    
    # Summary
    print(f"\n📊 Results Summary:")
    successful = sum(1 for r in results if r['success'])
    print(f"   Successful: {successful}/{num_connections}")
    print(f"   Failed: {num_connections - successful}/{num_connections}")
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"   {status} Connection {result['connection']}: {result['message']}")

def main():
    print("🔧 SMTP Connection Monitor")
    print("=" * 50)
    
    config = get_smtp_config()
    
    if not config['username'] or not config['password']:
        print("⚠️  SMTP credentials not found in environment variables")
        print("   Set EMAIL_USER and EMAIL_PASS to test connections")
        print("   Continuing with connection monitoring only...")
    
    print("\n1️⃣  Testing single SMTP connection...")
    test_smtp_connection_quick(config)
    
    print("\n2️⃣  Testing multiple connections (rate limit test)...")
    test_multiple_connections(num_connections=3, delay_between=1)
    
    print("\n3️⃣  Monitoring active connections...")
    monitor_connections_continuous(duration_seconds=30)

if __name__ == "__main__":
    main()
