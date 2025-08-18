#!/usr/bin/env python3
"""
Smart Polling Engine Demo

This demo showcases the Smart Polling Engine's capabilities including:
- Adaptive interval optimization based on email patterns
- Machine learning-based interval prediction
- Load-based polling frequency adjustment
- Rate limit detection and handling
- Multi-account concurrent polling
- Performance monitoring and metrics

Requirements: 1.4, 1.7, 6.1
"""

import os
import sys
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import List
import random

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.email.smart_polling_engine import (
    SmartPollingEngine, PollingStrategy, LoadLevel, EmailPattern,
    PollingInterval, PollingMetrics, LoadMetrics
)
from src.email.connection_pool import ConnectionPoolManager
from src.database.manager import DatabaseManager
from src.database.models import EmailMetadata
from src.email.godaddy_client import GoDaddyEmailClient, RateLimitInfo


class MockGoDaddyClient(GoDaddyEmailClient):
    """Mock GoDaddy client for demonstration purposes"""
    
    def __init__(self, account_id: str, email_frequency: float = 0.3):
        # Don't call parent __init__ to avoid environment variable requirements
        self.account_id = account_id
        self.email_frequency = email_frequency  # Emails per minute
        self.last_email_time = datetime.now()
        self.email_counter = 0
        self.rate_limited = False
        self.rate_limit_until = None
        
        # Simulate different email patterns for different accounts
        if "high_volume" in account_id:
            self.email_frequency = 2.0  # 2 emails per minute
        elif "low_volume" in account_id:
            self.email_frequency = 0.1  # 1 email per 10 minutes
        elif "business" in account_id:
            # Business hours pattern
            current_hour = datetime.now().hour
            if 9 <= current_hour <= 17:
                self.email_frequency = 1.5  # High during business hours
            else:
                self.email_frequency = 0.2  # Low outside business hours
    
    def connect(self):
        """Mock connection"""
        time.sleep(0.1)  # Simulate connection time
        print(f"[{self.account_id}] Connected to mock GoDaddy server")
    
    def fetch_unread_emails(self):
        """Mock email fetching with realistic patterns"""
        # Simulate rate limiting occasionally
        if random.random() < 0.05:  # 5% chance of rate limiting
            self.rate_limited = True
            self.rate_limit_until = datetime.now() + timedelta(seconds=30)
            raise Exception("Rate limit exceeded")
        
        # Check if we should generate new emails
        now = datetime.now()
        time_since_last = (now - self.last_email_time).total_seconds() / 60.0  # minutes
        
        # Probability of new emails based on frequency and time elapsed
        email_probability = self.email_frequency * time_since_last
        
        emails = []
        if random.random() < email_probability:
            # Generate 1-3 emails
            num_emails = random.randint(1, 3)
            
            for i in range(num_emails):
                self.email_counter += 1
                
                # Create mock email message
                from email.message import EmailMessage
                email = EmailMessage()
                email['From'] = f'sender{self.email_counter}@example.com'
                email['Subject'] = f'Email {self.email_counter} for {self.account_id}'
                email['Message-ID'] = f'<{self.account_id}_{self.email_counter}@example.com>'
                email['Date'] = now.strftime('%a, %d %b %Y %H:%M:%S %z')
                email.set_content(f'This is email {self.email_counter} for account {self.account_id}')
                
                emails.append(email)
            
            self.last_email_time = now
            
            if emails:
                print(f"[{self.account_id}] Generated {len(emails)} new emails")
        
        return emails
    
    def get_rate_limit_info(self):
        """Mock rate limit info"""
        if self.rate_limited and self.rate_limit_until and datetime.now() < self.rate_limit_until:
            remaining_time = (self.rate_limit_until - datetime.now()).total_seconds()
            return RateLimitInfo(
                is_rate_limited=True,
                requests_per_minute=60,
                current_usage=65,
                reset_time=self.rate_limit_until,
                backoff_seconds=int(remaining_time)
            )
        else:
            self.rate_limited = False
            return RateLimitInfo(
                is_rate_limited=False,
                requests_per_minute=60,
                current_usage=random.randint(10, 40),
                reset_time=None,
                backoff_seconds=0
            )
    
    def close(self):
        """Mock close"""
        print(f"[{self.account_id}] Disconnected from mock GoDaddy server")


class MockConnectionPool:
    """Mock connection pool for demonstration"""
    
    def __init__(self):
        self.connections = {}
        self.connection_count = 0
    
    def get_connection(self):
        """Get a mock connection"""
        self.connection_count += 1
        
        # Create a mock pooled connection
        class MockPooledConnection:
            def __init__(self, client):
                self.connection = client
                self.account_id = client.account_id
                self.is_healthy = True
        
        # Simulate getting connection for different accounts
        account_id = f"demo_account_{self.connection_count % 3}"
        if account_id not in self.connections:
            self.connections[account_id] = MockGoDaddyClient(account_id)
        
        return MockPooledConnection(self.connections[account_id])
    
    def return_connection(self, connection):
        """Return connection to pool"""
        pass


class MockDatabaseManager:
    """Mock database manager for demonstration"""
    
    def __init__(self):
        self.email_states = {}
    
    def get_email_processing_state(self, uid):
        return self.email_states.get(uid)
    
    def create_email_processing_state(self, state):
        self.email_states[state.email_uid] = state
        return len(self.email_states)


class SmartPollingDemo:
    """Smart Polling Engine demonstration"""
    
    def __init__(self):
        self.setup_logging()
        self.connection_pool = MockConnectionPool()
        self.database_manager = MockDatabaseManager()
        self.polling_engine = None
        self.demo_accounts = [
            "high_volume_account",
            "low_volume_account", 
            "business_hours_account"
        ]
        self.detected_emails = []
        self.interval_changes = []
        
    def setup_logging(self):
        """Set up logging for the demo"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('smart_polling_demo.log')
            ]
        )
        
        # Reduce noise from some loggers
        logging.getLogger('src.email.smart_polling_engine').setLevel(logging.WARNING)
    
    def create_load_monitor(self):
        """Create a load monitor that simulates varying system load"""
        def load_monitor():
            # Simulate varying load throughout the day
            current_hour = datetime.now().hour
            
            if 9 <= current_hour <= 17:  # Business hours
                cpu_usage = random.uniform(40, 70)
                memory_usage = random.uniform(50, 75)
                queue_depth = random.randint(10, 40)
                processing_latency = random.uniform(500, 2000)
            else:  # Off hours
                cpu_usage = random.uniform(15, 35)
                memory_usage = random.uniform(25, 45)
                queue_depth = random.randint(2, 15)
                processing_latency = random.uniform(100, 800)
            
            return LoadMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                active_connections=len(self.demo_accounts),
                queue_depth=queue_depth,
                processing_latency=processing_latency
            )
        
        return load_monitor
    
    def email_detection_callback(self, account_id: str, emails: List[EmailMetadata]):
        """Callback for email detection events"""
        self.detected_emails.extend(emails)
        print(f"📧 [{account_id}] Detected {len(emails)} new emails")
        
        for email in emails:
            print(f"   - From: {email.sender}")
            print(f"   - Subject: {email.subject}")
    
    def interval_change_callback(self, account_id: str, old_interval: int, new_interval: int):
        """Callback for interval adjustment events"""
        self.interval_changes.append((account_id, old_interval, new_interval))
        direction = "↓" if new_interval < old_interval else "↑"
        print(f"⏱️  [{account_id}] Interval adjusted: {old_interval}s {direction} {new_interval}s")
    
    def print_metrics_summary(self):
        """Print comprehensive metrics summary"""
        print("\n" + "="*80)
        print("📊 SMART POLLING ENGINE METRICS SUMMARY")
        print("="*80)
        
        all_metrics = self.polling_engine.get_all_metrics()
        
        for account_id, metrics in all_metrics.items():
            print(f"\n🏢 Account: {account_id}")
            print(f"   Total Polls: {metrics.total_polls}")
            print(f"   Successful Polls: {metrics.successful_polls}")
            print(f"   Failed Polls: {metrics.failed_polls}")
            print(f"   Success Rate: {metrics.success_rate:.1f}%")
            print(f"   Emails Detected: {metrics.emails_detected}")
            print(f"   Detection Efficiency: {metrics.detection_efficiency:.2f} emails/poll")
            print(f"   Average Response Time: {metrics.average_response_time:.1f}ms")
            print(f"   Interval Adjustments: {metrics.interval_adjustments}")
            print(f"   ML Predictions Made: {metrics.ml_predictions_made}")
            print(f"   Accuracy Score: {metrics.accuracy_score:.3f}")
        
        # Overall statistics
        total_polls = sum(m.total_polls for m in all_metrics.values())
        total_emails = sum(m.emails_detected for m in all_metrics.values())
        total_successful = sum(m.successful_polls for m in all_metrics.values())
        
        print(f"\n🌟 Overall Statistics:")
        print(f"   Total Emails Detected: {total_emails}")
        print(f"   Total Polls Across All Accounts: {total_polls}")
        print(f"   Overall Success Rate: {(total_successful/total_polls*100):.1f}%")
        print(f"   Total Interval Adjustments: {len(self.interval_changes)}")
    
    def demonstrate_strategy_comparison(self):
        """Demonstrate different polling strategies"""
        print("\n" + "="*80)
        print("🔬 POLLING STRATEGY COMPARISON")
        print("="*80)
        
        strategies = [
            PollingStrategy.FIXED_INTERVAL,
            PollingStrategy.ADAPTIVE_INTERVAL,
            PollingStrategy.LOAD_BASED,
            PollingStrategy.HYBRID
        ]
        
        test_account = "strategy_test_account"
        
        for strategy in strategies:
            print(f"\n🧪 Testing {strategy.value.upper()} strategy...")
            
            self.polling_engine.set_strategy(strategy)
            
            # Run for a short period
            self.polling_engine.start_adaptive_polling(test_account)
            time.sleep(10)  # 10 seconds
            self.polling_engine.stop_polling(test_account)
            
            # Get metrics
            metrics = self.polling_engine.get_polling_metrics(test_account)
            print(f"   Polls: {metrics.total_polls}")
            print(f"   Emails: {metrics.emails_detected}")
            print(f"   Success Rate: {metrics.success_rate:.1f}%")
            print(f"   Avg Response Time: {metrics.average_response_time:.1f}ms")
    
    def demonstrate_load_adaptation(self):
        """Demonstrate load-based adaptation"""
        print("\n" + "="*80)
        print("⚡ LOAD-BASED ADAPTATION DEMONSTRATION")
        print("="*80)
        
        test_account = "load_adaptation_test"
        
        # Create different load scenarios
        load_scenarios = [
            ("Low Load", LoadMetrics(20, 30, 2, 5, 200)),
            ("Medium Load", LoadMetrics(50, 60, 8, 25, 1200)),
            ("High Load", LoadMetrics(75, 80, 15, 60, 3000)),
            ("Critical Load", LoadMetrics(90, 95, 25, 150, 8000))
        ]
        
        self.polling_engine.set_strategy(PollingStrategy.LOAD_BASED)
        
        for scenario_name, load_metrics in load_scenarios:
            print(f"\n🔥 {scenario_name} Scenario:")
            print(f"   CPU: {load_metrics.cpu_usage:.1f}%")
            print(f"   Memory: {load_metrics.memory_usage:.1f}%")
            print(f"   Queue Depth: {load_metrics.queue_depth}")
            print(f"   Processing Latency: {load_metrics.processing_latency:.1f}ms")
            print(f"   Load Level: {load_metrics.get_load_level().value}")
            
            # Temporarily override load monitor
            original_callback = self.polling_engine.load_monitor_callback
            self.polling_engine.load_monitor_callback = lambda: load_metrics
            
            # Initialize polling interval for test account
            self.polling_engine._polling_intervals[test_account] = PollingInterval(base_interval=60)
            
            # Calculate interval for this load
            interval = self.polling_engine._calculate_load_based_interval(test_account)
            print(f"   Calculated Interval: {interval}s")
            
            # Restore original callback
            self.polling_engine.load_monitor_callback = original_callback
    
    def run_demo(self):
        """Run the complete Smart Polling Engine demonstration"""
        print("🚀 Starting Smart Polling Engine Demo")
        print("="*80)
        
        try:
            # Create polling engine
            self.polling_engine = SmartPollingEngine(
                connection_pool=self.connection_pool,
                database_manager=self.database_manager,
                strategy=PollingStrategy.HYBRID,
                base_interval=30,
                load_monitor_callback=self.create_load_monitor()
            )
            
            # Set up callbacks
            self.polling_engine.add_email_callback(self.email_detection_callback)
            self.polling_engine.add_interval_callback(self.interval_change_callback)
            
            print(f"✅ Smart Polling Engine initialized with {PollingStrategy.HYBRID.value} strategy")
            print(f"📋 Demo accounts: {', '.join(self.demo_accounts)}")
            
            # Start polling for all demo accounts
            print(f"\n🎯 Starting adaptive polling for {len(self.demo_accounts)} accounts...")
            for account in self.demo_accounts:
                self.polling_engine.start_adaptive_polling(account)
                print(f"   ✓ Started polling for {account}")
            
            # Let the system run and adapt
            print(f"\n⏳ Running polling engine for 60 seconds...")
            print("   Watch for email detections and interval adjustments...")
            
            for i in range(12):  # 12 * 5 seconds = 60 seconds
                time.sleep(5)
                print(f"   ⏱️  {(i+1)*5}s elapsed...")
                
                # Print current status every 15 seconds
                if (i + 1) % 3 == 0:
                    active_sessions = len(self.polling_engine._active_sessions)
                    total_emails = len(self.detected_emails)
                    print(f"      Active sessions: {active_sessions}")
                    print(f"      Total emails detected: {total_emails}")
            
            print(f"\n🛑 Stopping polling for all accounts...")
            for account in self.demo_accounts:
                self.polling_engine.stop_polling(account)
                print(f"   ✓ Stopped polling for {account}")
            
            # Print comprehensive metrics
            self.print_metrics_summary()
            
            # Demonstrate strategy comparison
            self.demonstrate_strategy_comparison()
            
            # Demonstrate load adaptation
            self.demonstrate_load_adaptation()
            
            print(f"\n🎉 Demo completed successfully!")
            print(f"   Total emails detected: {len(self.detected_emails)}")
            print(f"   Total interval adjustments: {len(self.interval_changes)}")
            print(f"   Log file: smart_polling_demo.log")
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Demo interrupted by user")
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            if self.polling_engine:
                print(f"\n🧹 Shutting down polling engine...")
                self.polling_engine.shutdown()
                print("   ✓ Shutdown complete")


def main():
    """Main demo function"""
    print("Smart Polling Engine Demo")
    print("This demo showcases adaptive email polling with ML optimization")
    print("Press Ctrl+C to stop the demo at any time\n")
    
    demo = SmartPollingDemo()
    demo.run_demo()


if __name__ == "__main__":
    main()