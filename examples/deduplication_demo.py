"""
Multi-Layer Deduplication System Demo

This demo showcases the comprehensive email deduplication system with:
1. UID-based duplicate detection with Redis caching
2. Message-ID comparison with database persistence
3. SHA-256 content hash verification for content-based deduplication
4. Cross-layer duplicate validation with 99.99% accuracy

Run this demo to see the deduplication system in action.
"""

import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import redis
    from src.email.deduplication_handler import (
        MultiLayerDeduplicationHandler,
        EmailIdentifiers,
        DeduplicationResult,
        DuplicateSource,
        calculate_content_hash,
        create_email_identifiers
    )
    from src.database.manager import DatabaseManager
    from src.config.manager import ConfigurationManager
    from src.config.models import DatabaseConfig, RedisConfig
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed and the project is properly set up.")
    exit(1)


class DeduplicationDemo:
    """Demo class for the multi-layer deduplication system."""
    
    def __init__(self):
        """Initialize the demo with mock configurations."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.redis_client = None
        self.db_manager = None
        self.dedup_handler = None
        
        # Demo data
        self.test_emails = []
        self.duplicate_scenarios = []
        
        self.logger.info("Deduplication Demo initialized")
    
    def setup_demo_environment(self):
        """Set up demo environment with mock Redis and database."""
        try:
            # Try to connect to Redis (use mock if not available)
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=15,  # Use test database
                    decode_responses=False
                )
                self.redis_client.ping()
                self.redis_client.flushdb()  # Clean test database
                self.logger.info("Connected to Redis for demo")
            except Exception as e:
                self.logger.warning(f"Redis not available, using mock: {e}")
                self.redis_client = self._create_mock_redis()
            
            # Create mock database manager
            self.db_manager = self._create_mock_database()
            
            # Initialize deduplication handler
            self.dedup_handler = MultiLayerDeduplicationHandler(
                self.redis_client,
                self.db_manager
            )
            
            self.logger.info("Demo environment setup complete")
            
        except Exception as e:
            self.logger.error(f"Demo setup failed: {e}")
            raise
    
    def generate_test_emails(self, count: int = 100) -> List[EmailIdentifiers]:
        """Generate test emails with various duplicate scenarios."""
        emails = []
        
        # Generate unique emails
        for i in range(count):
            email = EmailIdentifiers(
                uid=f"email_{i:04d}",
                message_id=f"<email_{i:04d}@example.com>",
                content_hash=calculate_content_hash(f"Unique email content number {i}"),
                account_id="demo_account",
                received_date=datetime.utcnow() - timedelta(minutes=random.randint(0, 1440)),
                sender=f"sender_{i % 10}@example.com",
                subject=f"Email Subject {i}"
            )
            emails.append(email)
        
        # Add duplicate scenarios
        duplicate_count = count // 10  # 10% duplicates
        
        for i in range(duplicate_count):
            original_idx = random.randint(0, count - 1)
            original = emails[original_idx]
            
            # Create different types of duplicates
            duplicate_type = i % 3
            
            if duplicate_type == 0:
                # UID duplicate (same UID, different content)
                duplicate = EmailIdentifiers(
                    uid=original.uid,  # Same UID
                    message_id=f"<dup_uid_{i}@example.com>",
                    content_hash=calculate_content_hash(f"Different content {i}"),
                    account_id="demo_account",
                    received_date=datetime.utcnow(),
                    sender=f"different_sender_{i}@example.com",
                    subject=f"Different Subject {i}"
                )
                self.duplicate_scenarios.append(("UID", original_idx, len(emails)))
                
            elif duplicate_type == 1:
                # Message-ID duplicate (same Message-ID, different UID)
                duplicate = EmailIdentifiers(
                    uid=f"dup_msgid_{i}",
                    message_id=original.message_id,  # Same Message-ID
                    content_hash=calculate_content_hash(f"Different content {i}"),
                    account_id="demo_account",
                    received_date=datetime.utcnow(),
                    sender=f"different_sender_{i}@example.com",
                    subject=f"Different Subject {i}"
                )
                self.duplicate_scenarios.append(("MESSAGE_ID", original_idx, len(emails)))
                
            else:
                # Content hash duplicate (same content, different identifiers)
                duplicate = EmailIdentifiers(
                    uid=f"dup_content_{i}",
                    message_id=f"<dup_content_{i}@example.com>",
                    content_hash=original.content_hash,  # Same content hash
                    account_id="demo_account",
                    received_date=datetime.utcnow(),
                    sender=f"different_sender_{i}@example.com",
                    subject=f"Different Subject {i}"
                )
                self.duplicate_scenarios.append(("CONTENT_HASH", original_idx, len(emails)))
            
            emails.append(duplicate)
        
        # Add some multi-source duplicates for highest confidence testing
        for i in range(5):
            original_idx = random.randint(0, count - 1)
            original = emails[original_idx]
            
            # Exact duplicate (all three sources match)
            exact_duplicate = EmailIdentifiers(
                uid=original.uid,  # Same UID
                message_id=original.message_id,  # Same Message-ID
                content_hash=original.content_hash,  # Same content hash
                account_id="demo_account",
                received_date=datetime.utcnow(),
                sender=original.sender,
                subject=original.subject
            )
            emails.append(exact_duplicate)
            self.duplicate_scenarios.append(("MULTI_SOURCE", original_idx, len(emails) - 1))
        
        self.test_emails = emails
        self.logger.info(f"Generated {len(emails)} test emails with {len(self.duplicate_scenarios)} duplicate scenarios")
        
        return emails
    
    def run_deduplication_demo(self):
        """Run the main deduplication demonstration."""
        print("\n" + "="*80)
        print("MULTI-LAYER DEDUPLICATION SYSTEM DEMO")
        print("="*80)
        
        # Generate test data
        print("\n1. Generating test emails...")
        emails = self.generate_test_emails(100)
        print(f"   Generated {len(emails)} emails with various duplicate scenarios")
        
        # Process emails and collect results
        print("\n2. Processing emails through deduplication system...")
        results = []
        processing_times = []
        
        for i, email in enumerate(emails):
            start_time = time.time()
            result = self.dedup_handler.check_duplicate(email)
            processing_time = (time.time() - start_time) * 1000
            
            results.append(result)
            processing_times.append(processing_time)
            
            if i % 20 == 0:
                print(f"   Processed {i+1}/{len(emails)} emails...")
        
        print(f"   Completed processing {len(emails)} emails")
        
        # Analyze results
        print("\n3. Analyzing deduplication results...")
        self._analyze_results(results, processing_times)
        
        # Show detailed examples
        print("\n4. Detailed duplicate detection examples...")
        self._show_detailed_examples(emails, results)
        
        # Performance metrics
        print("\n5. Performance metrics...")
        self._show_performance_metrics(processing_times)
        
        # Accuracy validation
        print("\n6. Accuracy validation...")
        self._validate_accuracy(emails, results)
        
        # System statistics
        print("\n7. System statistics...")
        self._show_system_statistics()
        
        print("\n" + "="*80)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*80)
    
    def _analyze_results(self, results: List[DeduplicationResult], processing_times: List[float]):
        """Analyze deduplication results."""
        total_emails = len(results)
        duplicates_found = sum(1 for r in results if r.is_duplicate)
        unique_emails = total_emails - duplicates_found
        
        # Count by source type
        uid_duplicates = sum(1 for r in results if DuplicateSource.UID in r.duplicate_sources)
        msgid_duplicates = sum(1 for r in results if DuplicateSource.MESSAGE_ID in r.duplicate_sources)
        content_duplicates = sum(1 for r in results if DuplicateSource.CONTENT_HASH in r.duplicate_sources)
        multi_source = sum(1 for r in results if len(r.duplicate_sources) > 1)
        
        # Confidence scores
        avg_confidence = sum(r.confidence_score for r in results) / len(results)
        high_confidence = sum(1 for r in results if r.confidence_score >= 0.99)
        
        print(f"   Total emails processed: {total_emails}")
        print(f"   Unique emails: {unique_emails}")
        print(f"   Duplicates found: {duplicates_found} ({duplicates_found/total_emails*100:.1f}%)")
        print(f"   ")
        print(f"   Duplicate detection by source:")
        print(f"     UID duplicates: {uid_duplicates}")
        print(f"     Message-ID duplicates: {msgid_duplicates}")
        print(f"     Content hash duplicates: {content_duplicates}")
        print(f"     Multi-source duplicates: {multi_source}")
        print(f"   ")
        print(f"   Confidence metrics:")
        print(f"     Average confidence: {avg_confidence:.4f} ({avg_confidence*100:.2f}%)")
        print(f"     High confidence (≥99%): {high_confidence}/{total_emails} ({high_confidence/total_emails*100:.1f}%)")
    
    def _show_detailed_examples(self, emails: List[EmailIdentifiers], results: List[DeduplicationResult]):
        """Show detailed examples of duplicate detection."""
        print("   Duplicate detection examples:")
        
        examples_shown = 0
        for i, (result, email) in enumerate(zip(results, emails)):
            if result.is_duplicate and examples_shown < 5:
                print(f"   ")
                print(f"   Example {examples_shown + 1}:")
                print(f"     Email UID: {email.uid}")
                print(f"     Message-ID: {email.message_id[:50]}...")
                print(f"     Content Hash: {email.content_hash[:16]}...")
                print(f"     Duplicate Sources: {[s.value for s in result.duplicate_sources]}")
                print(f"     Confidence Score: {result.confidence_score:.4f}")
                print(f"     Processing Time: {result.processing_time_ms:.2f}ms")
                if result.first_seen:
                    print(f"     First Seen: {result.first_seen.strftime('%Y-%m-%d %H:%M:%S')}")
                examples_shown += 1
    
    def _show_performance_metrics(self, processing_times: List[float]):
        """Show performance metrics."""
        avg_time = sum(processing_times) / len(processing_times)
        min_time = min(processing_times)
        max_time = max(processing_times)
        
        # Calculate percentiles
        sorted_times = sorted(processing_times)
        p50 = sorted_times[len(sorted_times) // 2]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        print(f"   Processing time statistics:")
        print(f"     Average: {avg_time:.2f}ms")
        print(f"     Minimum: {min_time:.2f}ms")
        print(f"     Maximum: {max_time:.2f}ms")
        print(f"     50th percentile: {p50:.2f}ms")
        print(f"     95th percentile: {p95:.2f}ms")
        print(f"     99th percentile: {p99:.2f}ms")
        print(f"   ")
        print(f"   Throughput: {len(processing_times) / (sum(processing_times) / 1000):.0f} emails/second")
    
    def _validate_accuracy(self, emails: List[EmailIdentifiers], results: List[DeduplicationResult]):
        """Validate deduplication accuracy."""
        # Check accuracy against known duplicate scenarios
        correct_detections = 0
        false_positives = 0
        false_negatives = 0
        
        # Create set of expected duplicate indices
        expected_duplicates = set()
        for _, _, dup_idx in self.duplicate_scenarios:
            expected_duplicates.add(dup_idx)
        
        for i, result in enumerate(results):
            is_expected_duplicate = i in expected_duplicates
            
            if result.is_duplicate and is_expected_duplicate:
                correct_detections += 1
            elif result.is_duplicate and not is_expected_duplicate:
                false_positives += 1
            elif not result.is_duplicate and is_expected_duplicate:
                false_negatives += 1
        
        total_checks = len(results)
        accuracy = ((correct_detections + (total_checks - len(expected_duplicates) - false_positives)) / total_checks) * 100
        
        print(f"   Accuracy validation:")
        print(f"     Expected duplicates: {len(expected_duplicates)}")
        print(f"     Correct detections: {correct_detections}")
        print(f"     False positives: {false_positives}")
        print(f"     False negatives: {false_negatives}")
        print(f"     Overall accuracy: {accuracy:.2f}%")
        print(f"     Meets 99.99% target: {'✓' if accuracy >= 99.99 else '✗'}")
    
    def _show_system_statistics(self):
        """Show system statistics."""
        stats = self.dedup_handler.get_deduplication_stats()
        
        print(f"   System statistics:")
        print(f"     Total checks: {stats.total_checks}")
        print(f"     Duplicates found: {stats.duplicates_found}")
        print(f"     Duplicate rate: {stats.duplicate_rate:.2f}%")
        print(f"     Cache hit rate: {stats.cache_hit_rate:.2f}%")
        print(f"     Average processing time: {stats.average_processing_time_ms:.2f}ms")
        print(f"     Accuracy rate: {stats.accuracy_rate:.2f}%")
        print(f"   ")
        print(f"   Duplicate breakdown:")
        print(f"     UID duplicates: {stats.uid_duplicates}")
        print(f"     Message-ID duplicates: {stats.message_id_duplicates}")
        print(f"     Content hash duplicates: {stats.content_hash_duplicates}")
        print(f"     Multi-source duplicates: {stats.multi_source_duplicates}")
    
    def _create_mock_redis(self):
        """Create mock Redis client for demo."""
        class MockRedis:
            def __init__(self):
                self.data = {}
            
            def get(self, key):
                return self.data.get(key)
            
            def setex(self, key, time, value):
                self.data[key] = value
                return True
            
            def exists(self, key):
                return key in self.data
            
            def pipeline(self):
                return MockPipeline(self)
            
            def info(self):
                return {
                    'keyspace_hits': 100,
                    'keyspace_misses': 10
                }
            
            def flushdb(self):
                self.data.clear()
            
            def ping(self):
                return True
        
        class MockPipeline:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.commands = []
            
            def setex(self, key, time, value):
                self.commands.append(('setex', key, time, value))
                return self
            
            def execute(self):
                for cmd in self.commands:
                    if cmd[0] == 'setex':
                        self.redis.setex(cmd[1], cmd[2], cmd[3])
                self.commands.clear()
                return [True] * len(self.commands)
        
        return MockRedis()
    
    def _create_mock_database(self):
        """Create mock database manager for demo."""
        class MockDatabaseManager:
            def __init__(self):
                self.data = {}
            
            def get_connection(self):
                return MockConnection(self)
        
        class MockConnection:
            def __init__(self, db):
                self.db = db
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass
            
            def cursor(self):
                return MockCursor(self.db)
            
            def commit(self):
                pass
        
        class MockCursor:
            def __init__(self, db):
                self.db = db
                self.rowcount = 0
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass
            
            def execute(self, query, params=None):
                if "SELECT" in query and params:
                    # Simulate lookup
                    key = f"{params[0]}_{params[1] if len(params) > 1 else ''}"
                    if key in self.db.data:
                        self._result = self.db.data[key]
                    else:
                        self._result = None
                elif "INSERT" in query or "ON CONFLICT" in query:
                    # Simulate insert
                    if params:
                        key = f"{params[0]}_{params[1] if len(params) > 1 else ''}"
                        self.db.data[key] = (params[6], params[8])  # first_seen, count
                elif "DELETE" in query:
                    # Simulate cleanup
                    self.rowcount = len(self.db.data)
                    self.db.data.clear()
            
            def fetchone(self):
                return getattr(self, '_result', None)
        
        return MockDatabaseManager()


def main():
    """Run the deduplication demo."""
    try:
        demo = DeduplicationDemo()
        demo.setup_demo_environment()
        demo.run_deduplication_demo()
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()