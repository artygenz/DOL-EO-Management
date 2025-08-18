#!/usr/bin/env python3
"""
Delivery Manager Demo

This demo showcases the comprehensive email delivery functionality including:
- SMTP delivery with confirmation tracking
- Delivery status monitoring and failure detection
- Automatic retry logic with exponential backoff
- Bounce handling and delivery failure escalation

Requirements implemented: 4.4, 4.5
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import delivery manager components
from src.email.delivery_manager import (
    DeliveryManager,
    DeliveryRecord,
    DeliveryStatus,
    DeliveryPriority,
    BounceType,
    SMTPConnectionConfig,
    DeliveryManagerError
)
from src.database.manager import DatabaseManager
from src.config.manager import ConfigurationManager


class DeliveryManagerDemo:
    """
    Comprehensive demo of the Delivery Manager functionality.
    """
    
    def __init__(self):
        """Initialize the demo."""
        self.config_manager = ConfigurationManager()
        self.database_manager = None
        self.delivery_manager = None
        
        # Demo configuration
        self.smtp_config = SMTPConnectionConfig(
            host="smtp.example.com",  # Replace with actual SMTP server
            port=587,
            use_tls=True,
            username="demo@dol.gov",  # Replace with actual credentials
            password="demo-password",  # Replace with actual credentials
            timeout=30
        )
        
        logger.info("Initialized DeliveryManagerDemo")
    
    def setup_delivery_manager(self) -> None:
        """Setup the delivery manager with comprehensive tracking."""
        try:
            # Initialize database manager (optional for demo)
            # self.database_manager = DatabaseManager()
            
            # Create delivery manager
            self.delivery_manager = DeliveryManager(
                smtp_config=self.smtp_config,
                database_manager=self.database_manager,
                max_concurrent_deliveries=5,
                delivery_timeout=300,
                enable_bounce_detection=True
            )
            
            # Start delivery manager
            self.delivery_manager.start()
            
            logger.info("✅ Delivery Manager setup complete")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup delivery manager: {str(e)}")
            raise
    
    def demo_basic_email_delivery(self) -> List[str]:
        """Demonstrate basic email delivery with tracking."""
        logger.info("\n🚀 Demo: Basic Email Delivery with Tracking")
        
        delivery_ids = []
        
        try:
            # Send various types of emails
            email_scenarios = [
                {
                    'recipient': 'executive@dol.gov',
                    'subject': 'Executive Summary - Q4 2024',
                    'body_text': 'Please find the quarterly executive summary attached.',
                    'body_html': '<p>Please find the quarterly executive summary attached.</p>',
                    'priority': DeliveryPriority.HIGH,
                    'correlation_id': 'exec-summary-q4-2024',
                    'attachments': [
                        {
                            'filename': 'executive_summary_q4.pdf',
                            'content': b'Mock PDF content for executive summary',
                            'content_type': 'application/pdf'
                        }
                    ]
                },
                {
                    'recipient': 'developer@dol.gov',
                    'subject': 'Task Assignment: Email Agent Enhancement',
                    'body_text': 'You have been assigned a new development task.',
                    'priority': DeliveryPriority.NORMAL,
                    'correlation_id': 'task-assignment-001'
                },
                {
                    'recipient': 'pmo@dol.gov',
                    'subject': 'Approval Request: System Upgrade',
                    'body_text': 'Please review and approve the system upgrade request.',
                    'priority': DeliveryPriority.HIGH,
                    'correlation_id': 'approval-request-001'
                }
            ]
            
            # Send emails
            for i, scenario in enumerate(email_scenarios):
                logger.info(f"📧 Sending email {i+1}: {scenario['subject']}")
                
                delivery_id = self.delivery_manager.send_email(
                    recipient_email=scenario['recipient'],
                    sender_email='email-agent@dol.gov',
                    subject=scenario['subject'],
                    body_text=scenario['body_text'],
                    body_html=scenario.get('body_html'),
                    attachments=scenario.get('attachments'),
                    priority=scenario['priority'],
                    correlation_id=scenario['correlation_id'],
                    metadata={
                        'demo_scenario': f'basic_delivery_{i+1}',
                        'email_type': scenario['subject'].split(':')[0].lower().replace(' ', '_')
                    }
                )
                
                delivery_ids.append(delivery_id)
                logger.info(f"   ✅ Queued for delivery: {delivery_id}")
            
            # Wait for deliveries to process
            logger.info("⏳ Waiting for deliveries to process...")
            time.sleep(3)
            
            # Check delivery status
            self._display_delivery_status(delivery_ids)
            
            return delivery_ids
            
        except Exception as e:
            logger.error(f"❌ Basic delivery demo failed: {str(e)}")
            raise
    
    def demo_retry_and_failure_handling(self) -> List[str]:
        """Demonstrate retry logic and failure handling."""
        logger.info("\n🔄 Demo: Retry Logic and Failure Handling")
        
        delivery_ids = []
        
        try:
            # Simulate different failure scenarios
            failure_scenarios = [
                {
                    'recipient': 'nonexistent@invalid-domain.com',
                    'subject': 'Test Hard Bounce - Invalid Domain',
                    'expected_outcome': 'hard_bounce'
                },
                {
                    'recipient': 'full-mailbox@example.com',
                    'subject': 'Test Soft Bounce - Mailbox Full',
                    'expected_outcome': 'soft_bounce'
                },
                {
                    'recipient': 'blocked@spam-domain.com',
                    'subject': 'Test Block Bounce - Spam Content',
                    'expected_outcome': 'block_bounce'
                }
            ]
            
            for i, scenario in enumerate(failure_scenarios):
                logger.info(f"📧 Sending test email {i+1}: {scenario['subject']}")
                
                delivery_id = self.delivery_manager.send_email(
                    recipient_email=scenario['recipient'],
                    sender_email='email-agent@dol.gov',
                    subject=scenario['subject'],
                    body_text=f"This is a test email to demonstrate {scenario['expected_outcome']} handling.",
                    priority=DeliveryPriority.NORMAL,
                    correlation_id=f"failure-test-{i+1}",
                    metadata={
                        'demo_scenario': 'failure_handling',
                        'expected_outcome': scenario['expected_outcome']
                    }
                )
                
                delivery_ids.append(delivery_id)
                logger.info(f"   ✅ Queued for delivery: {delivery_id}")
            
            # Wait for initial delivery attempts and retries
            logger.info("⏳ Waiting for delivery attempts and retries...")
            time.sleep(5)
            
            # Check delivery status and retry behavior
            self._display_retry_behavior(delivery_ids)
            
            return delivery_ids
            
        except Exception as e:
            logger.error(f"❌ Retry and failure handling demo failed: {str(e)}")
            raise
    
    def demo_priority_handling(self) -> List[str]:
        """Demonstrate priority-based delivery handling."""
        logger.info("\n⚡ Demo: Priority-Based Delivery Handling")
        
        delivery_ids = []
        
        try:
            # Send emails with different priorities
            priority_scenarios = [
                ('Normal Priority Email 1', DeliveryPriority.NORMAL),
                ('Critical Priority Email 1', DeliveryPriority.CRITICAL),
                ('High Priority Email 1', DeliveryPriority.HIGH),
                ('Low Priority Email 1', DeliveryPriority.LOW),
                ('Critical Priority Email 2', DeliveryPriority.CRITICAL),
                ('Normal Priority Email 2', DeliveryPriority.NORMAL),
            ]
            
            # Send all emails quickly to test queue prioritization
            for i, (subject, priority) in enumerate(priority_scenarios):
                logger.info(f"📧 Queuing {priority.value} priority email: {subject}")
                
                delivery_id = self.delivery_manager.send_email(
                    recipient_email=f'priority-test-{i}@dol.gov',
                    sender_email='email-agent@dol.gov',
                    subject=subject,
                    body_text=f"This is a {priority.value} priority email for testing queue handling.",
                    priority=priority,
                    correlation_id=f"priority-test-{i+1}",
                    metadata={
                        'demo_scenario': 'priority_handling',
                        'queue_position': i
                    }
                )
                
                delivery_ids.append(delivery_id)
                time.sleep(0.1)  # Small delay to ensure queue ordering
            
            # Wait for deliveries
            logger.info("⏳ Waiting for priority-based delivery processing...")
            time.sleep(4)
            
            # Analyze delivery order and timing
            self._analyze_priority_delivery(delivery_ids)
            
            return delivery_ids
            
        except Exception as e:
            logger.error(f"❌ Priority handling demo failed: {str(e)}")
            raise
    
    def demo_bounce_detection_and_classification(self) -> None:
        """Demonstrate bounce detection and classification."""
        logger.info("\n🎯 Demo: Bounce Detection and Classification")
        
        try:
            # Test bounce analysis with different error messages
            bounce_test_cases = [
                ("User unknown in virtual mailbox table", BounceType.HARD_BOUNCE),
                ("No such user here", BounceType.HARD_BOUNCE),
                ("Mailbox full, try again later", BounceType.SOFT_BOUNCE),
                ("Quota exceeded", BounceType.SOFT_BOUNCE),
                ("Message blocked due to spam content", BounceType.BLOCK_BOUNCE),
                ("Sender blacklisted", BounceType.BLOCK_BOUNCE),
                ("Some unknown error occurred", BounceType.UNKNOWN)
            ]
            
            logger.info("🔍 Testing bounce classification accuracy:")
            
            for error_message, expected_type in bounce_test_cases:
                bounce_info = self.delivery_manager._analyze_bounce(error_message)
                
                status_icon = "✅" if bounce_info['type'] == expected_type else "❌"
                logger.info(f"   {status_icon} '{error_message}' → {bounce_info['type'].value}")
                
                if bounce_info['type'] != expected_type:
                    logger.warning(f"      Expected: {expected_type.value}, Got: {bounce_info['type'].value}")
            
            logger.info("✅ Bounce classification demo complete")
            
        except Exception as e:
            logger.error(f"❌ Bounce detection demo failed: {str(e)}")
            raise
    
    def demo_delivery_metrics_and_monitoring(self) -> None:
        """Demonstrate delivery metrics and monitoring capabilities."""
        logger.info("\n📊 Demo: Delivery Metrics and Monitoring")
        
        try:
            # Get current metrics
            metrics = self.delivery_manager.get_delivery_metrics()
            
            logger.info("📈 Current Delivery Metrics:")
            logger.info(f"   Total Sent: {metrics['total_sent']}")
            logger.info(f"   Total Delivered: {metrics['total_delivered']}")
            logger.info(f"   Total Failed: {metrics['total_failed']}")
            logger.info(f"   Total Bounced: {metrics['total_bounced']}")
            logger.info(f"   Total Retries: {metrics['total_retries']}")
            logger.info(f"   Average Delivery Time: {metrics['average_delivery_time']:.2f}ms")
            logger.info(f"   Pending Deliveries: {metrics['pending_deliveries']}")
            logger.info(f"   Retrying Deliveries: {metrics['retrying_deliveries']}")
            logger.info(f"   Total Records: {metrics['total_records']}")
            logger.info(f"   Queue Size: {metrics['queue_size']}")
            logger.info(f"   Retry Queue Size: {metrics['retry_queue_size']}")
            
            # Calculate success rate
            if metrics['total_sent'] > 0:
                success_rate = (metrics['total_delivered'] / metrics['total_sent']) * 100
                logger.info(f"   Success Rate: {success_rate:.1f}%")
            
            # Display delivery records summary
            logger.info("\n📋 Delivery Records Summary:")
            status_counts = {}
            
            for delivery_id, record in self.delivery_manager.delivery_records.items():
                status = record.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            for status, count in status_counts.items():
                logger.info(f"   {status.title()}: {count}")
            
            logger.info("✅ Metrics and monitoring demo complete")
            
        except Exception as e:
            logger.error(f"❌ Metrics demo failed: {str(e)}")
            raise
    
    def demo_manual_retry_functionality(self) -> None:
        """Demonstrate manual retry functionality."""
        logger.info("\n🔄 Demo: Manual Retry Functionality")
        
        try:
            # Find failed deliveries
            failed_deliveries = []
            for delivery_id, record in self.delivery_manager.delivery_records.items():
                if record.status == DeliveryStatus.FAILED:
                    failed_deliveries.append(delivery_id)
            
            if failed_deliveries:
                logger.info(f"🔍 Found {len(failed_deliveries)} failed deliveries")
                
                # Attempt manual retry
                retried_ids = self.delivery_manager.retry_failed_deliveries(max_age_hours=24)
                
                logger.info(f"🔄 Manually retried {len(retried_ids)} deliveries:")
                for delivery_id in retried_ids:
                    logger.info(f"   - {delivery_id}")
                
                # Wait for retry processing
                time.sleep(2)
                
                # Check retry results
                logger.info("📊 Retry Results:")
                for delivery_id in retried_ids:
                    record = self.delivery_manager.get_delivery_status(delivery_id)
                    if record:
                        logger.info(f"   {delivery_id}: {record.status.value}")
            else:
                logger.info("ℹ️  No failed deliveries found for manual retry demo")
            
            logger.info("✅ Manual retry demo complete")
            
        except Exception as e:
            logger.error(f"❌ Manual retry demo failed: {str(e)}")
            raise
    
    def _display_delivery_status(self, delivery_ids: List[str]) -> None:
        """Display detailed delivery status for given delivery IDs."""
        logger.info("\n📊 Delivery Status Report:")
        
        for i, delivery_id in enumerate(delivery_ids, 1):
            record = self.delivery_manager.get_delivery_status(delivery_id)
            
            if record:
                logger.info(f"\n   📧 Email {i} ({delivery_id[:8]}...):")
                logger.info(f"      To: {record.recipient_email}")
                logger.info(f"      Subject: {record.subject}")
                logger.info(f"      Status: {record.status.value}")
                logger.info(f"      Priority: {record.priority.value}")
                logger.info(f"      Created: {record.created_at.strftime('%H:%M:%S')}")
                
                if record.delivered_at:
                    logger.info(f"      Delivered: {record.delivered_at.strftime('%H:%M:%S')}")
                
                if record.correlation_id:
                    logger.info(f"      Correlation ID: {record.correlation_id}")
                
                logger.info(f"      Attempts: {len(record.attempts)}")
                
                if record.attempts:
                    latest_attempt = record.attempts[-1]
                    if latest_attempt.delivery_time_ms:
                        logger.info(f"      Delivery Time: {latest_attempt.delivery_time_ms:.2f}ms")
                    
                    if latest_attempt.error_message:
                        logger.info(f"      Last Error: {latest_attempt.error_message}")
                
                if record.bounce_type:
                    logger.info(f"      Bounce Type: {record.bounce_type.value}")
                    logger.info(f"      Bounce Reason: {record.bounce_reason}")
            else:
                logger.warning(f"   ❌ No record found for delivery {delivery_id}")
    
    def _display_retry_behavior(self, delivery_ids: List[str]) -> None:
        """Display retry behavior analysis."""
        logger.info("\n🔄 Retry Behavior Analysis:")
        
        for i, delivery_id in enumerate(delivery_ids, 1):
            record = self.delivery_manager.get_delivery_status(delivery_id)
            
            if record:
                logger.info(f"\n   📧 Email {i} ({delivery_id[:8]}...):")
                logger.info(f"      Status: {record.status.value}")
                logger.info(f"      Retry Count: {record.retry_count}")
                logger.info(f"      Max Retries: {record.max_retries}")
                
                if record.next_retry_at:
                    time_until_retry = (record.next_retry_at - datetime.utcnow()).total_seconds()
                    if time_until_retry > 0:
                        logger.info(f"      Next Retry In: {time_until_retry:.1f} seconds")
                    else:
                        logger.info(f"      Next Retry: Due now")
                
                # Display attempt history
                logger.info(f"      Attempt History ({len(record.attempts)} attempts):")
                for j, attempt in enumerate(record.attempts, 1):
                    timestamp = attempt.timestamp.strftime('%H:%M:%S')
                    logger.info(f"        {j}. {timestamp} - {attempt.status.value}")
                    if attempt.error_message:
                        logger.info(f"           Error: {attempt.error_message}")
                
                # Analyze exponential backoff
                if len(record.attempts) > 1:
                    time_diffs = []
                    for j in range(1, len(record.attempts)):
                        diff = (record.attempts[j].timestamp - record.attempts[j-1].timestamp).total_seconds()
                        time_diffs.append(diff)
                    
                    if time_diffs:
                        logger.info(f"      Retry Intervals: {[f'{diff:.1f}s' for diff in time_diffs]}")
    
    def _analyze_priority_delivery(self, delivery_ids: List[str]) -> None:
        """Analyze priority-based delivery order."""
        logger.info("\n⚡ Priority Delivery Analysis:")
        
        # Collect delivery records with timing
        delivery_records = []
        for delivery_id in delivery_ids:
            record = self.delivery_manager.get_delivery_status(delivery_id)
            if record and record.attempts:
                delivery_records.append({
                    'id': delivery_id,
                    'subject': record.subject,
                    'priority': record.priority,
                    'start_time': record.attempts[0].timestamp,
                    'status': record.status
                })
        
        # Sort by delivery start time
        delivery_records.sort(key=lambda x: x['start_time'])
        
        logger.info("   📊 Delivery Order (by start time):")
        for i, record in enumerate(delivery_records, 1):
            priority_icon = {
                DeliveryPriority.CRITICAL: "🔴",
                DeliveryPriority.HIGH: "🟠", 
                DeliveryPriority.NORMAL: "🟡",
                DeliveryPriority.LOW: "⚪"
            }.get(record['priority'], "❓")
            
            time_str = record['start_time'].strftime('%H:%M:%S.%f')[:-3]
            logger.info(f"      {i}. {priority_icon} {record['priority'].value} - {record['subject']} ({time_str})")
        
        # Analyze priority ordering
        priority_order = [record['priority'] for record in delivery_records]
        critical_positions = [i for i, p in enumerate(priority_order) if p == DeliveryPriority.CRITICAL]
        high_positions = [i for i, p in enumerate(priority_order) if p == DeliveryPriority.HIGH]
        normal_positions = [i for i, p in enumerate(priority_order) if p == DeliveryPriority.NORMAL]
        
        logger.info("\n   🎯 Priority Ordering Analysis:")
        if critical_positions and high_positions:
            if max(critical_positions) < min(high_positions):
                logger.info("      ✅ Critical emails processed before High priority")
            else:
                logger.info("      ⚠️  Priority ordering may not be optimal")
        
        if high_positions and normal_positions:
            if max(high_positions) < min(normal_positions):
                logger.info("      ✅ High priority emails processed before Normal priority")
            else:
                logger.info("      ⚠️  Priority ordering may not be optimal")
    
    def cleanup(self) -> None:
        """Cleanup demo resources."""
        logger.info("\n🧹 Cleaning up demo resources...")
        
        try:
            if self.delivery_manager:
                self.delivery_manager.stop()
                logger.info("   ✅ Delivery manager stopped")
            
            if self.database_manager:
                # Close database connections if needed
                pass
            
            logger.info("✅ Demo cleanup complete")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {str(e)}")
    
    def run_comprehensive_demo(self) -> None:
        """Run the comprehensive delivery manager demo."""
        logger.info("🚀 Starting Comprehensive Delivery Manager Demo")
        logger.info("=" * 60)
        
        try:
            # Setup
            self.setup_delivery_manager()
            
            # Run demo scenarios
            basic_delivery_ids = self.demo_basic_email_delivery()
            retry_delivery_ids = self.demo_retry_and_failure_handling()
            priority_delivery_ids = self.demo_priority_handling()
            
            # Additional demos
            self.demo_bounce_detection_and_classification()
            self.demo_delivery_metrics_and_monitoring()
            self.demo_manual_retry_functionality()
            
            # Final summary
            logger.info("\n" + "=" * 60)
            logger.info("📊 Demo Summary:")
            
            all_delivery_ids = basic_delivery_ids + retry_delivery_ids + priority_delivery_ids
            logger.info(f"   Total Emails Sent: {len(all_delivery_ids)}")
            
            final_metrics = self.delivery_manager.get_delivery_metrics()
            logger.info(f"   Final Success Rate: {(final_metrics['total_delivered'] / final_metrics['total_sent'] * 100):.1f}%")
            logger.info(f"   Average Delivery Time: {final_metrics['average_delivery_time']:.2f}ms")
            
            logger.info("\n✅ Comprehensive Delivery Manager Demo Complete!")
            logger.info("   All requirements 4.4 and 4.5 have been demonstrated:")
            logger.info("   ✅ SMTP delivery with confirmation tracking")
            logger.info("   ✅ Delivery status monitoring and failure detection")
            logger.info("   ✅ Automatic retry logic with exponential backoff")
            logger.info("   ✅ Bounce handling and delivery failure escalation")
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {str(e)}")
            raise
        
        finally:
            self.cleanup()


def main():
    """Main demo function."""
    try:
        demo = DeliveryManagerDemo()
        demo.run_comprehensive_demo()
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Demo failed with error: {str(e)}")
        raise


if __name__ == "__main__":
    main()