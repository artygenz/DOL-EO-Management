#!/usr/bin/env python3
"""
IMAP IDLE Controller Demo

This script demonstrates the IMAP IDLE Controller functionality including:
- Starting IDLE sessions for real-time email monitoring
- Processing IDLE events (new emails, deletions, flag changes)
- Session renewal and timeout handling
- Graceful fallback to polling when IDLE is not supported
- Connection pool integration
- Comprehensive metrics and monitoring

Usage:
    python examples/idle_controller_demo.py
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.email.idle_controller import (
    IMAPIdleController,
    IdleSession,
    IdleEvent,
    IdleSessionState,
    IdleEventType
)
from src.email.connection_pool import ConnectionPoolManager
from src.config.manager import ConfigurationManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IdleControllerDemo:
    """Demo class for IMAP IDLE Controller"""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.connection_pool = None
        self.idle_controller = None
        self.events_received = []
        self.session_changes = []
        
    def setup(self):
        """Setup demo environment"""
        logger.info("Setting up IDLE Controller demo...")
        
        # Load configuration
        try:
            config = self.config_manager.load_config()
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load configuration: {e}")
            # Use demo configuration
            config = self._get_demo_config()
        
        # Create connection pool
        try:
            account_config = config.get('email_accounts', {}).get('primary', {})
            self.connection_pool = ConnectionPoolManager(
                account_config=account_config,
                min_pool_size=2,
                max_pool_size=5,
                health_check_interval=30
            )
            logger.info("Connection pool created")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            return False
        
        # Create IDLE controller
        try:
            self.idle_controller = IMAPIdleController(
                connection_pool=self.connection_pool,
                default_timeout=1800,  # 30 minutes
                renewal_buffer=60,     # Renew 1 minute before timeout
                max_concurrent_sessions=3,
                fallback_callback=self._on_fallback_to_polling
            )
            
            # Add event and session callbacks
            self.idle_controller.add_event_callback(self._on_idle_event)
            self.idle_controller.add_session_callback(self._on_session_state_change)
            
            logger.info("IDLE controller created and configured")
        except Exception as e:
            logger.error(f"Failed to create IDLE controller: {e}")
            return False
        
        return True
    
    def _get_demo_config(self) -> Dict[str, Any]:
        """Get demo configuration"""
        return {
            'email_accounts': {
                'primary': {
                    'imap_host': os.getenv('EMAIL_HOST', 'imap.secureserver.net'),
                    'imap_port': int(os.getenv('EMAIL_PORT', 993)),
                    'smtp_host': os.getenv('SMTP_HOST', 'smtpout.secureserver.net'),
                    'smtp_port': int(os.getenv('SMTP_PORT', 465)),
                    'username': os.getenv('EMAIL_USER', 'demo@example.com'),
                    'password': os.getenv('EMAIL_PASS', 'demopass')
                }
            }
        }
    
    def _on_idle_event(self, event: IdleEvent):
        """Handle IDLE events"""
        self.events_received.append(event)
        
        logger.info(f"IDLE Event: {event.event_type.value} from {event.account_id}/{event.mailbox}")
        
        if event.event_type == IdleEventType.NEW_EMAIL:
            logger.info(f"  New email detected! Count: {event.metadata.get('email_count', 'unknown')}")
        elif event.event_type == IdleEventType.EMAIL_DELETED:
            logger.info(f"  Email deleted! Sequence: {event.metadata.get('sequence_number', 'unknown')}")
        elif event.event_type == IdleEventType.EMAIL_FLAGGED:
            logger.info(f"  Email flags changed!")
        
        # Print event details
        print(f"\n📧 IDLE EVENT RECEIVED:")
        print(f"   Type: {event.event_type.value}")
        print(f"   Account: {event.account_id}")
        print(f"   Mailbox: {event.mailbox}")
        print(f"   Time: {event.timestamp.strftime('%H:%M:%S')}")
        if event.metadata:
            print(f"   Metadata: {event.metadata}")
        print()
    
    def _on_session_state_change(self, session: IdleSession, state: IdleSessionState):
        """Handle session state changes"""
        self.session_changes.append((session.session_id, state, datetime.now()))
        
        logger.info(f"Session {session.account_id}: {state.value}")
        
        if state == IdleSessionState.ACTIVE:
            print(f"✅ IDLE session active for {session.account_id}/{session.mailbox}")
        elif state == IdleSessionState.RENEWING:
            print(f"🔄 Renewing IDLE session for {session.account_id} (renewal #{session.renewal_count})")
        elif state == IdleSessionState.FAILED:
            print(f"❌ IDLE session failed for {session.account_id}")
        elif state == IdleSessionState.TERMINATED:
            print(f"🛑 IDLE session terminated for {session.account_id}")
    
    def _on_fallback_to_polling(self, account_id: str):
        """Handle fallback to polling"""
        logger.warning(f"Falling back to polling for account: {account_id}")
        print(f"⚠️  IDLE not supported for {account_id}, falling back to polling")
    
    def run_demo(self):
        """Run the IDLE controller demo"""
        if not self.setup():
            logger.error("Demo setup failed")
            return
        
        try:
            print("\n" + "="*60)
            print("🚀 IMAP IDLE CONTROLLER DEMO")
            print("="*60)
            print()
            
            # Start IDLE sessions for different accounts
            accounts_to_monitor = [
                ("primary_account", "INBOX"),
                ("secondary_account", "INBOX"),
            ]
            
            sessions = []
            
            print("📡 Starting IDLE sessions...")
            for account_id, mailbox in accounts_to_monitor:
                try:
                    session = self.idle_controller.start_idle_session(account_id, mailbox)
                    sessions.append(session)
                    print(f"   Started session for {account_id}/{mailbox}")
                except Exception as e:
                    logger.error(f"Failed to start session for {account_id}: {e}")
            
            if not sessions:
                print("❌ No IDLE sessions could be started")
                return
            
            print(f"\n✅ Started {len(sessions)} IDLE session(s)")
            print("\n📊 Initial Metrics:")
            self._print_metrics()
            
            print("\n🔍 Monitoring for email events...")
            print("   (This demo will run for 60 seconds)")
            print("   Send emails to monitored accounts to see IDLE events!")
            print()
            
            # Monitor for events
            start_time = time.time()
            last_metrics_time = start_time
            
            while time.time() - start_time < 60:  # Run for 60 seconds
                time.sleep(1)
                
                # Print metrics every 10 seconds
                if time.time() - last_metrics_time >= 10:
                    print(f"\n📊 Metrics Update ({int(time.time() - start_time)}s elapsed):")
                    self._print_metrics()
                    self._print_session_status()
                    last_metrics_time = time.time()
                
                # Simulate some events for demo purposes (every 15 seconds)
                if int(time.time() - start_time) % 15 == 0 and int(time.time() - start_time) > 0:
                    self._simulate_demo_events()
            
            print("\n⏰ Demo time completed!")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Demo interrupted by user")
        
        except Exception as e:
            logger.error(f"Demo error: {e}")
            print(f"\n❌ Demo error: {e}")
        
        finally:
            self._cleanup()
    
    def _print_metrics(self):
        """Print current metrics"""
        if not self.idle_controller:
            return
        
        metrics = self.idle_controller.get_metrics()
        
        print(f"   Total Sessions: {metrics.total_sessions}")
        print(f"   Active Sessions: {metrics.active_sessions}")
        print(f"   Events Processed: {metrics.total_events_processed}")
        print(f"   Successful Renewals: {metrics.successful_renewals}")
        print(f"   Failed Renewals: {metrics.failed_renewals}")
        print(f"   Fallback Count: {metrics.fallback_to_polling_count}")
        if metrics.average_session_duration > 0:
            print(f"   Avg Session Duration: {metrics.average_session_duration:.1f}s")
    
    def _print_session_status(self):
        """Print status of active sessions"""
        if not self.idle_controller:
            return
        
        active_sessions = self.idle_controller.get_active_sessions()
        
        if active_sessions:
            print(f"\n📋 Active Sessions ({len(active_sessions)}):")
            for session in active_sessions:
                uptime = (datetime.now() - session.started_at).total_seconds()
                print(f"   {session.account_id}/{session.mailbox}: {session.state.value} "
                      f"(uptime: {uptime:.0f}s, renewals: {session.renewal_count}, "
                      f"events: {session.event_count})")
    
    def _simulate_demo_events(self):
        """Simulate some demo events for demonstration"""
        if not self.idle_controller:
            return
        
        # Create a simulated new email event
        demo_event = IdleEvent(
            event_type=IdleEventType.NEW_EMAIL,
            account_id="primary_account",
            mailbox="INBOX",
            timestamp=datetime.now(),
            metadata={'email_count': '5', 'demo': True}
        )
        
        self.idle_controller._queue_event(demo_event)
        logger.info("Simulated demo event queued")
    
    def _cleanup(self):
        """Cleanup resources"""
        print("\n🧹 Cleaning up...")
        
        if self.idle_controller:
            self.idle_controller.shutdown()
            logger.info("IDLE controller shutdown")
        
        if self.connection_pool:
            self.connection_pool.shutdown()
            logger.info("Connection pool shutdown")
        
        # Print final statistics
        print(f"\n📈 Final Statistics:")
        print(f"   Total Events Received: {len(self.events_received)}")
        print(f"   Total Session Changes: {len(self.session_changes)}")
        
        if self.events_received:
            print(f"\n📧 Events Summary:")
            event_types = {}
            for event in self.events_received:
                event_types[event.event_type.value] = event_types.get(event.event_type.value, 0) + 1
            
            for event_type, count in event_types.items():
                print(f"   {event_type}: {count}")
        
        print("\n✅ Demo completed successfully!")


def main():
    """Main demo function"""
    demo = IdleControllerDemo()
    demo.run_demo()


if __name__ == "__main__":
    main()