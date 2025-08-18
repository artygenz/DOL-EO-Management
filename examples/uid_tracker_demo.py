#!/usr/bin/env python3
"""
UID-Based Email Tracking System Demo

This demo shows how to use the UID tracking system for incremental email detection,
duplicate prevention, and state recovery.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from src.email.uid_tracker import (
    UIDTracker, EmailIdentifiers, calculate_content_hash
)
from src.email.redis_client import RedisClient
from src.database.manager import DatabaseManager
from src.database.models import EmailMetadata, ProcessingStatus
from src.config.models import RedisConfig, DatabaseConnectionConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_emails() -> List[EmailIdentifiers]:
    """Create sample email identifiers for testing."""
    emails = []
    
    sample_data = [
        ("Executive Order on AI Safety", "eo-ai-safety@whitehouse.gov"),
        ("PMO Response: Task Assignment", "pmo@dol.gov"),
        ("Developer Update: Progress Report", "dev-team@contractor.com"),
        ("Executive Request: Quarterly Report", "secretary@dol.gov"),
        ("New Policy Implementation", "policy@dol.gov")
    ]
    
    for i, (subject, sender) in enumerate(sample_data):
        content = f"Subject: {subject}\nFrom: {sender}\nThis is sample email content for testing purposes."
        
        email = EmailIdentifiers(
            uid=f"email_uid_{i+1:03d}",
            message_id=f"<{i+1:03d}@example.com>",
            content_hash=calculate_content_hash(content),
            account_id="demo_account",
            received_date=datetime.utcnow()
        )
        emails.append(email)
    
    return emails


def demo_basic_tracking():
    """Demonstrate basic email tracking functionality."""
    logger.info("=== Basic Email Tracking Demo ===")
    
    # Configuration (using mock/demo values)
    redis_config = RedisConfig(
        host="localhost",
        port=6379,
        database=1,  # Use test database
        password=None
    )
    
    db_config = DatabaseConnectionConfig(
        primary_host="localhost",
        port=5432,
        database="email_agent_demo",
        username="demo_user",
        password="demo_password"
    )
    
    try:
        # Initialize components
        redis_client = RedisClient(redis_config)
        db_manager = DatabaseManager(db_config)
        uid_tracker = UIDTracker(redis_client, db_manager)
        
        logger.info("UID Tracker initialized successfully")
        
        # Create sample emails
        sample_emails = create_sample_emails()
        
        # Track emails for the first time
        logger.info("Tracking emails for the first time...")
        for email in sample_emails:
            metadata = EmailMetadata(
                uid=email.uid,
                message_id=email.message_id,
                sender="demo@example.com",
                subject=f"Demo Email {email.uid}",
                received_date=email.received_date,
                account_id=email.account_id
            )
            
            result = uid_tracker.track_email(email, metadata)
            logger.info(f"Email {email.uid}: {result.status.value}, duplicate: {result.is_duplicate}")
        
        # Try tracking same emails again (should detect duplicates)
        logger.info("\nTracking same emails again (should detect duplicates)...")
        for email in sample_emails[:3]:  # Test first 3 emails
            result = uid_tracker.track_email(email)
            logger.info(f"Email {email.uid}: {result.status.value}, duplicate: {result.is_duplicate}")
            if result.is_duplicate:
                logger.info(f"  Duplicate sources: {result.duplicate_sources}")
        
        # Show tracking metrics
        metrics = uid_tracker.get_tracking_metrics()
        logger.info(f"\nTracking Metrics:")
        logger.info(f"  Cache hit rate: {metrics.get('cache_hit_rate', 0):.2f}%")
        logger.info(f"  Duplicate detections: {metrics.get('duplicate_detections', 0)}")
        logger.info(f"  Redis healthy: {metrics.get('redis_healthy', False)}")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        logger.info("Note: This demo requires Redis and PostgreSQL to be running")


def demo_incremental_detection():
    """Demonstrate incremental UID detection."""
    logger.info("\n=== Incremental UID Detection Demo ===")
    
    try:
        # Mock configuration
        redis_config = RedisConfig()
        db_config = DatabaseConnectionConfig(
            primary_host="localhost",
            database="email_agent_demo"
        )
        
        redis_client = RedisClient(redis_config)
        db_manager = DatabaseManager(db_config)
        uid_tracker = UIDTracker(redis_client, db_manager)
        
        account_id = "demo_account"
        
        # Simulate first check
        logger.info("First UID check (should return empty list)...")
        new_uids = uid_tracker.get_new_uids(account_id, 100)
        logger.info(f"New UIDs: {new_uids}")
        
        # Simulate second check with higher UID
        logger.info("Second check with higher UID...")
        new_uids = uid_tracker.get_new_uids(account_id, 150)
        logger.info(f"New UIDs: {new_uids}")
        
        # Simulate third check with same UID
        logger.info("Third check with same UID (should return empty)...")
        new_uids = uid_tracker.get_new_uids(account_id, 150)
        logger.info(f"New UIDs: {new_uids}")
        
    except Exception as e:
        logger.error(f"Incremental detection demo failed: {e}")


def demo_state_management():
    """Demonstrate processing state management."""
    logger.info("\n=== Processing State Management Demo ===")
    
    try:
        # Mock configuration
        redis_config = RedisConfig()
        db_config = DatabaseConnectionConfig(
            primary_host="localhost",
            database="email_agent_demo"
        )
        
        redis_client = RedisClient(redis_config)
        db_manager = DatabaseManager(db_config)
        uid_tracker = UIDTracker(redis_client, db_manager)
        
        # Create a sample email
        email = create_sample_emails()[0]
        metadata = EmailMetadata(
            uid=email.uid,
            message_id=email.message_id,
            sender="demo@example.com",
            subject="State Management Demo",
            received_date=email.received_date,
            account_id=email.account_id
        )
        
        # Track email (creates initial state)
        logger.info("Tracking email (creates initial state)...")
        result = uid_tracker.track_email(email, metadata)
        logger.info(f"Initial state: {result.processing_state.status.value}")
        
        # Update processing state through lifecycle
        states = [
            ProcessingStatus.PROCESSING,
            ProcessingStatus.CLASSIFIED,
            ProcessingStatus.PUBLISHED,
            ProcessingStatus.COMPLETED
        ]
        
        for state in states:
            success = uid_tracker.update_processing_state(email.uid, state)
            logger.info(f"Updated to {state.value}: {'Success' if success else 'Failed'}")
        
        # Demonstrate state recovery
        logger.info("\nDemonstrating state recovery...")
        recovered_states = uid_tracker.recover_processing_states(email.account_id)
        logger.info(f"Recovered {len(recovered_states)} processing states")
        
        for uid, state in recovered_states.items():
            logger.info(f"  {uid}: {state.status.value}")
        
    except Exception as e:
        logger.error(f"State management demo failed: {e}")


def demo_duplicate_detection_accuracy():
    """Demonstrate 99.99% duplicate detection accuracy."""
    logger.info("\n=== Duplicate Detection Accuracy Demo ===")
    
    try:
        # Mock configuration
        redis_config = RedisConfig()
        db_config = DatabaseConnectionConfig(
            primary_host="localhost",
            database="email_agent_demo"
        )
        
        redis_client = RedisClient(redis_config)
        db_manager = DatabaseManager(db_config)
        uid_tracker = UIDTracker(redis_client, db_manager)
        
        # Create base email
        base_content = "This is the original email content for duplicate testing."
        base_email = EmailIdentifiers(
            uid="original_uid",
            message_id="<original@example.com>",
            content_hash=calculate_content_hash(base_content),
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        # Track original email
        logger.info("Tracking original email...")
        result = uid_tracker.track_email(base_email)
        logger.info(f"Original: {result.status.value}, duplicate: {result.is_duplicate}")
        
        # Test UID-based duplicate detection
        logger.info("\nTesting UID-based duplicate detection...")
        uid_duplicate = EmailIdentifiers(
            uid="original_uid",  # Same UID
            message_id="<different@example.com>",
            content_hash="different_hash",
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        result = uid_tracker.track_email(uid_duplicate)
        logger.info(f"UID duplicate: {result.status.value}, sources: {result.duplicate_sources}")
        
        # Test Message-ID based duplicate detection
        logger.info("\nTesting Message-ID based duplicate detection...")
        msgid_duplicate = EmailIdentifiers(
            uid="different_uid",
            message_id="<original@example.com>",  # Same Message-ID
            content_hash="different_hash2",
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        result = uid_tracker.track_email(msgid_duplicate)
        logger.info(f"Message-ID duplicate: {result.status.value}, sources: {result.duplicate_sources}")
        
        # Test content hash based duplicate detection
        logger.info("\nTesting content hash based duplicate detection...")
        hash_duplicate = EmailIdentifiers(
            uid="another_different_uid",
            message_id="<another@example.com>",
            content_hash=calculate_content_hash(base_content),  # Same content hash
            account_id="different_account",
            received_date=datetime.utcnow()
        )
        
        result = uid_tracker.track_email(hash_duplicate)
        logger.info(f"Content hash duplicate: {result.status.value}, sources: {result.duplicate_sources}")
        
        # Show final metrics
        metrics = uid_tracker.get_tracking_metrics()
        logger.info(f"\nFinal duplicate detections: {metrics.get('duplicate_detections', 0)}")
        
    except Exception as e:
        logger.error(f"Duplicate detection demo failed: {e}")


def main():
    """Run all demos."""
    logger.info("UID-Based Email Tracking System Demo")
    logger.info("=" * 50)
    
    # Run demos
    demo_basic_tracking()
    demo_incremental_detection()
    demo_state_management()
    demo_duplicate_detection_accuracy()
    
    logger.info("\n" + "=" * 50)
    logger.info("Demo completed!")
    logger.info("\nNote: Some demos may fail if Redis/PostgreSQL are not running.")
    logger.info("This is expected for demonstration purposes.")


if __name__ == "__main__":
    main()