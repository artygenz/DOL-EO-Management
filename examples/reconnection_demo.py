#!/usr/bin/env python3
"""
Demonstration of the Enhanced GoDaddy Email Client with Intelligent Reconnection

This script demonstrates the automatic reconnection capabilities, including:
- Exponential backoff with jitter
- Connection failure detection and recovery
- Fallback mechanisms for persistent failures
- Connection state persistence for recovery scenarios
- Comprehensive monitoring and metrics
"""

import os
import sys
import time
import logging
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email.enhanced_godaddy_client import EnhancedGoDaddyEmailClient
from email.reconnection_manager import (
    ReconnectionConfig,
    FallbackMechanism,
    ConnectionState,
    FailureType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_basic_reconnection():
    """Demonstrate basic reconnection functionality"""
    print("\n" + "="*60)
    print("DEMO 1: Basic Reconnection with Exponential Backoff")
    print("="*60)
    
    # Configuration for fast testing
    account_config = {
        'imap_host': 'imap.secureserver.net',
        'imap_port': 993,
        'smtp_host': 'smtpout.secureserver.net',
        'smtp_port': 465,
        'username': os.getenv('EMAIL_USER', 'demo@example.com'),
        'password': os.getenv('EMAIL_PASS', 'demo_password')
    }
    
    reconnection_config = ReconnectionConfig(
        initial_backoff=1.0,
        max_backoff=30.0,
        backoff_multiplier=2.0,
        jitter_factor=0.1,
        max_retry_attempts=5,
        health_check_interval=10.0
    )
    
    print(f"Account: {account_config['username']}")
    print(f"IMAP Host: {account_config['imap_host']}")
    print(f"Reconnection Config: {reconnection_config.max_retry_attempts} max attempts")
    
    try:
        with EnhancedGoDaddyEmailClient(
            account_config=account_config,
            reconnection_config=reconnection_config,
            auto_reconnect=True
        ) as client:
            
            print(f"\nInitial connection state: {client.get_connection_state().value}")
            
            # Try to connect
            try:
                client.connect()
                print(f"Connection successful: {client.is_connected()}")
                print(f"Connection healthy: {client.is_healthy()}")
                
                # Get connection metrics
                metrics = client.get_connection_metrics()
                print(f"Connection metrics:")
                print(f"  - Total connections: {metrics.total_connections}")
                print(f"  - Successful connections: {metrics.successful_connections}")
                print(f"  - Failed connections: {metrics.failed_connections}")
                print(f"  - Uptime percentage: {metrics.uptime_percentage:.2f}%")
                
            except Exception as e:
                print(f"Connection failed: {e}")
                
                # Show failure history
                failures = client.get_failure_history()
                if failures:
                    print(f"\nFailure history ({len(failures)} failures):")
                    for i, failure in enumerate(failures[-3:], 1):  # Show last 3
                        print(f"  {i}. {failure.failure_type.value}: {failure.error_message}")
                        print(f"     Retry count: {failure.retry_count}, Backoff: {failure.backoff_duration:.2f}s")
            
            # Demonstrate force reconnect
            print(f"\nForcing reconnection...")
            success = client.force_reconnect()
            print(f"Force reconnect result: {success}")
            
    except Exception as e:
        print(f"Demo error: {e}")


def demo_fallback_mechanisms():
    """Demonstrate fallback server mechanisms"""
    print("\n" + "="*60)
    print("DEMO 2: Fallback Mechanisms for Persistent Failures")
    print("="*60)
    
    account_config = {
        'imap_host': 'invalid.server.com',  # Intentionally invalid
        'imap_port': 993,
        'smtp_host': 'invalid.server.com',
        'smtp_port': 465,
        'username': 'demo@example.com',
        'password': 'demo_password'
    }
    
    # Configure fallback servers
    fallback_config = FallbackMechanism(
        enabled=True,
        fallback_servers=[
            {
                'imap_host': 'imap.secureserver.net',
                'smtp_host': 'smtpout.secureserver.net',
                'username': os.getenv('EMAIL_USER', 'demo@example.com'),
                'password': os.getenv('EMAIL_PASS', 'demo_password')
            },
            {
                'imap_host': 'backup.secureserver.net',
                'smtp_host': 'backup.secureserver.net'
            }
        ],
        fallback_timeout=5.0,
        max_fallback_attempts=2
    )
    
    reconnection_config = ReconnectionConfig(
        initial_backoff=0.5,
        max_backoff=5.0,
        max_retry_attempts=2,  # Fail quickly to trigger fallback
        health_check_interval=5.0
    )
    
    print(f"Primary server (invalid): {account_config['imap_host']}")
    print(f"Fallback servers: {len(fallback_config.fallback_servers)}")
    
    try:
        with EnhancedGoDaddyEmailClient(
            account_config=account_config,
            reconnection_config=reconnection_config,
            fallback_config=fallback_config,
            auto_reconnect=True
        ) as client:
            
            print(f"\nAttempting connection to primary server...")
            
            # Wait for connection attempts and potential fallback
            max_wait = 30.0
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                state = client.get_connection_state()
                print(f"Connection state: {state.value}")
                
                if state == ConnectionState.CONNECTED:
                    print("✓ Connection successful!")
                    break
                elif state == ConnectionState.SUSPENDED:
                    print("✗ Connection suspended after max attempts")
                    break
                
                time.sleep(2.0)
            
            # Show final metrics
            metrics = client.get_connection_metrics()
            failures = client.get_failure_history()
            
            print(f"\nFinal Results:")
            print(f"  - Connection attempts: {metrics.total_connections}")
            print(f"  - Successful: {metrics.successful_connections}")
            print(f"  - Failed: {metrics.failed_connections}")
            print(f"  - Total failures recorded: {len(failures)}")
            
            if failures:
                print(f"\nFailure breakdown:")
                failure_types = {}
                for failure in failures:
                    failure_type = failure.failure_type.value
                    failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
                
                for failure_type, count in failure_types.items():
                    print(f"  - {failure_type}: {count}")
    
    except Exception as e:
        print(f"Demo error: {e}")


def demo_connection_monitoring():
    """Demonstrate connection monitoring and health checks"""
    print("\n" + "="*60)
    print("DEMO 3: Connection Monitoring and Health Checks")
    print("="*60)
    
    account_config = {
        'imap_host': 'imap.secureserver.net',
        'imap_port': 993,
        'smtp_host': 'smtpout.secureserver.net',
        'smtp_port': 465,
        'username': os.getenv('EMAIL_USER', 'demo@example.com'),
        'password': os.getenv('EMAIL_PASS', 'demo_password')
    }
    
    reconnection_config = ReconnectionConfig(
        health_check_interval=3.0,  # Check every 3 seconds
        initial_backoff=1.0,
        max_retry_attempts=3
    )
    
    print(f"Health check interval: {reconnection_config.health_check_interval}s")
    
    try:
        with EnhancedGoDaddyEmailClient(
            account_config=account_config,
            reconnection_config=reconnection_config,
            auto_reconnect=True
        ) as client:
            
            # Add connection monitoring callbacks
            def on_connection_change(state, error):
                timestamp = datetime.now().strftime("%H:%M:%S")
                if error:
                    print(f"[{timestamp}] Connection state changed to {state.value}: {error}")
                else:
                    print(f"[{timestamp}] Connection state changed to {state.value}")
            
            def on_failure(failure):
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] Connection failure: {failure.failure_type.value} - {failure.error_message}")
            
            client.add_connection_callback(on_connection_change)
            client.add_failure_callback(on_failure)
            
            print(f"\nStarting connection monitoring...")
            
            # Try to connect
            try:
                client.connect()
                print(f"Initial connection: {client.is_connected()}")
            except Exception as e:
                print(f"Initial connection failed: {e}")
            
            # Monitor for a period
            monitor_duration = 15.0
            print(f"Monitoring for {monitor_duration} seconds...")
            
            start_time = time.time()
            while time.time() - start_time < monitor_duration:
                # Perform connection test
                test_results = client.perform_connection_test()
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{timestamp}] Connection Test Results:")
                print(f"  - State: {test_results['connection_state']}")
                print(f"  - Connected: {test_results['is_connected']}")
                print(f"  - Healthy: {test_results['is_healthy']}")
                
                if test_results.get('connection_health'):
                    health = test_results['connection_health']
                    print(f"  - Response time: {health['response_time_ms']:.1f}ms")
                    print(f"  - Error count: {health['error_count']}")
                    print(f"  - Uptime: {health['uptime_percentage']:.1f}%")
                
                # Show uptime stats
                uptime_stats = client.get_uptime_stats()
                print(f"  - Overall uptime: {uptime_stats['uptime_percentage']:.1f}%")
                
                time.sleep(5.0)
            
            print(f"\nMonitoring complete.")
    
    except Exception as e:
        print(f"Demo error: {e}")


def demo_state_persistence():
    """Demonstrate connection state persistence"""
    print("\n" + "="*60)
    print("DEMO 4: Connection State Persistence and Recovery")
    print("="*60)
    
    state_file = "demo_connection_state.json"
    
    account_config = {
        'imap_host': 'imap.secureserver.net',
        'imap_port': 993,
        'smtp_host': 'smtpout.secureserver.net',
        'smtp_port': 465,
        'username': os.getenv('EMAIL_USER', 'demo@example.com'),
        'password': os.getenv('EMAIL_PASS', 'demo_password')
    }
    
    reconnection_config = ReconnectionConfig(
        state_persistence_path=state_file,
        initial_backoff=1.0,
        max_retry_attempts=3
    )
    
    print(f"State persistence file: {state_file}")
    
    # First session - create some state
    print(f"\n--- First Session ---")
    try:
        with EnhancedGoDaddyEmailClient(
            account_config=account_config,
            reconnection_config=reconnection_config,
            auto_reconnect=False
        ) as client1:
            
            print("Attempting connection...")
            try:
                client1.connect()
                print(f"Connection successful: {client1.is_connected()}")
            except Exception as e:
                print(f"Connection failed: {e}")
            
            # Get metrics from first session
            metrics1 = client1.get_connection_metrics()
            failures1 = client1.get_failure_history()
            
            print(f"Session 1 metrics:")
            print(f"  - Total connections: {metrics1.total_connections}")
            print(f"  - Failed connections: {metrics1.failed_connections}")
            print(f"  - Failure history: {len(failures1)} entries")
            
            print("Ending first session...")
    
    except Exception as e:
        print(f"First session error: {e}")
    
    # Brief pause
    time.sleep(1.0)
    
    # Second session - should load previous state
    print(f"\n--- Second Session (State Recovery) ---")
    try:
        with EnhancedGoDaddyEmailClient(
            account_config=account_config,
            reconnection_config=reconnection_config,
            auto_reconnect=False
        ) as client2:
            
            print("Loading previous state...")
            
            # Get metrics from second session (should include previous state)
            metrics2 = client2.get_connection_metrics()
            failures2 = client2.get_failure_history()
            
            print(f"Session 2 metrics (with loaded state):")
            print(f"  - Total connections: {metrics2.total_connections}")
            print(f"  - Failed connections: {metrics2.failed_connections}")
            print(f"  - Failure history: {len(failures2)} entries")
            
            if failures2:
                print(f"Loaded failure history:")
                for i, failure in enumerate(failures2, 1):
                    print(f"  {i}. {failure.failure_type.value}: {failure.error_message}")
            
            # Try new connection
            print("Attempting new connection...")
            try:
                client2.connect()
                print(f"New connection successful: {client2.is_connected()}")
            except Exception as e:
                print(f"New connection failed: {e}")
    
    except Exception as e:
        print(f"Second session error: {e}")
    
    # Cleanup
    if os.path.exists(state_file):
        os.unlink(state_file)
        print(f"\nCleaned up state file: {state_file}")


def main():
    """Run all reconnection demos"""
    print("Enhanced GoDaddy Email Client - Reconnection Demos")
    print("=" * 60)
    
    # Check for credentials
    if not os.getenv('EMAIL_USER') or not os.getenv('EMAIL_PASS'):
        print("WARNING: EMAIL_USER and EMAIL_PASS environment variables not set.")
        print("Demos will use placeholder credentials and may fail to connect.")
        print("Set these variables for full functionality testing.")
    
    try:
        # Run demos
        demo_basic_reconnection()
        demo_fallback_mechanisms()
        demo_connection_monitoring()
        demo_state_persistence()
        
        print("\n" + "="*60)
        print("All demos completed successfully!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\nDemos interrupted by user.")
    except Exception as e:
        print(f"\nDemo suite error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()