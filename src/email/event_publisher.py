"""
Reliable Event Publishing System with Retry Logic for Email Agent.

This module implements Redis queue publishing with confirmation and retry logic,
event buffering for queue unavailability scenarios, exponential backoff retry
mechanism for failed publishes, and backup publishing methods for persistent failures.

Implements requirements:
- 3.2: Sub-second publishing latency
- 3.4: Retry with exponential backoff until successful
- 3.5: Buffer events and resume publishing when connectivity is restored
- 3.8: Switch to backup publishing methods when latency exceeds 5 seconds
"""

import logging
import json
import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, Future
import hashlib
import uuid

import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from .event_schema import StandardizedEvent, EventSchemaValidator
from .redis_client import RedisClient
from ..database.manager import DatabaseManager
from ..database.exceptions import DatabaseError


class PublishingStatus(Enum):
    """Event publishing status."""
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    BUFFERED = "buffered"
    RETRYING = "retrying"
    BACKUP_PUBLISHED = "backup_published"


class BackupMethod(Enum):
    """Backup publishing methods."""
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    WEBHOOK = "webhook"


@dataclass
class PublishingResult:
    """Result of event publishing attempt."""
    success: bool
    event_id: str
    status: PublishingStatus
    latency_ms: float
    queue_name: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    backup_method: Optional[BackupMethod] = None
    confirmation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class BufferedEvent:
    """Event stored in buffer during queue unavailability."""
    event: StandardizedEvent
    queue_name: str
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 10
    next_retry: Optional[datetime] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if buffered event has expired."""
        # Events expire after 24 hours
        return datetime.now(timezone.utc) - self.timestamp > timedelta(hours=24)
    
    @property
    def can_retry(self) -> bool:
        """Check if event can be retried."""
        return (self.retry_count < self.max_retries and 
                not self.is_expired and
                (not self.next_retry or datetime.now(timezone.utc) >= self.next_retry))


@dataclass
class PublishingStats:
    """Event publishing statistics."""
    total_events: int = 0
    successful_publishes: int = 0
    failed_publishes: int = 0
    buffered_events: int = 0
    backup_publishes: int = 0
    retry_attempts: int = 0
    average_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    queue_unavailable_count: int = 0
    confirmation_failures: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate publishing success rate."""
        if self.total_events == 0:
            return 0.0
        return (self.successful_publishes / self.total_events) * 100.0
    
    @property
    def backup_rate(self) -> float:
        """Calculate backup publishing rate."""
        if self.total_events == 0:
            return 0.0
        return (self.backup_publishes / self.total_events) * 100.0


class ReliableEventPublisher:
    """
    Reliable event publishing system with comprehensive retry logic and backup methods.
    
    Features:
    - Redis queue publishing with confirmation
    - Exponential backoff retry mechanism
    - Event buffering for queue unavailability
    - Backup publishing methods for persistent failures
    - Sub-second latency monitoring and alerting
    - Comprehensive metrics and health monitoring
    """
    
    # Configuration constants
    MAX_RETRY_ATTEMPTS = 10
    BASE_RETRY_DELAY = 0.1  # 100ms base delay
    MAX_RETRY_DELAY = 30.0  # 30 seconds max delay
    LATENCY_THRESHOLD_MS = 5000  # 5 seconds threshold for backup methods
    BUFFER_MAX_SIZE = 10000  # Maximum buffered events
    CONFIRMATION_TIMEOUT = 2.0  # 2 seconds confirmation timeout
    
    # Queue names
    DEFAULT_QUEUE = "email_events"
    BACKUP_QUEUE = "email_events_backup"
    DLQ_QUEUE = "email_events_dlq"  # Dead letter queue
    
    def __init__(self, 
                 redis_client: RedisClient,
                 database_manager: DatabaseManager,
                 schema_validator: Optional[EventSchemaValidator] = None):
        """
        Initialize reliable event publisher.
        
        Args:
            redis_client: Redis client for queue operations
            database_manager: Database manager for backup storage
            schema_validator: Optional schema validator
        """
        self.logger = logging.getLogger(__name__)
        self.redis = redis_client
        self.db = database_manager
        self.schema_validator = schema_validator or EventSchemaValidator()
        
        # Event buffer for queue unavailability
        self._event_buffer: Queue[BufferedEvent] = Queue(maxsize=self.BUFFER_MAX_SIZE)
        self._buffer_lock = threading.Lock()
        
        # Retry management
        self._retry_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="event-retry")
        self._active_retries: Dict[str, Future] = {}
        
        # Statistics and monitoring
        self._stats = PublishingStats()
        self._latency_samples: List[float] = []
        self._health_status = True
        
        # Background processing
        self._buffer_processor_running = False
        self._buffer_processor_thread: Optional[threading.Thread] = None
        
        # Backup methods
        self._backup_methods = {
            BackupMethod.DATABASE: self._publish_to_database,
            BackupMethod.FILE_SYSTEM: self._publish_to_filesystem,
            BackupMethod.WEBHOOK: self._publish_to_webhook
        }
        
        # Initialize database schema
        self._initialize_backup_storage()
        
        # Start background buffer processor
        self._start_buffer_processor()
        
        self.logger.info("Reliable event publisher initialized")
    
    def publish_event(self, 
                     event: StandardizedEvent,
                     queue_name: str = DEFAULT_QUEUE,
                     require_confirmation: bool = True) -> PublishingResult:
        """
        Publish event to Redis queue with retry logic and backup methods.
        
        Args:
            event: Standardized event to publish
            queue_name: Target queue name
            require_confirmation: Whether to require publishing confirmation
            
        Returns:
            PublishingResult with detailed publishing information
        """
        start_time = time.time()
        self._stats.total_events += 1
        
        try:
            # Validate event schema
            is_valid, error_msg = self.schema_validator.validate_event(event.to_dict())
            if not is_valid:
                self.logger.error(f"Event schema validation failed: {error_msg}")
                return PublishingResult(
                    success=False,
                    event_id=event.event_id,
                    status=PublishingStatus.FAILED,
                    latency_ms=0.0,
                    error_message=f"Schema validation failed: {error_msg}"
                )
            
            # Attempt primary publishing
            result = self._publish_to_redis(event, queue_name, require_confirmation)
            
            # Check latency threshold
            if result.latency_ms > self.LATENCY_THRESHOLD_MS:
                self.logger.warning(f"Publishing latency {result.latency_ms}ms exceeds threshold, using backup method")
                backup_result = self._publish_with_backup_method(event, queue_name)
                if backup_result.success:
                    return backup_result
            
            # If primary publishing failed, try backup methods
            if not result.success:
                self.logger.info(f"Primary publishing failed for event {event.event_id}, trying backup methods")
                backup_result = self._publish_with_backup_method(event, queue_name)
                if backup_result.success:
                    return backup_result
                
                # If all methods fail, buffer the event
                self._buffer_event(event, queue_name)
                return PublishingResult(
                    success=False,
                    event_id=event.event_id,
                    status=PublishingStatus.BUFFERED,
                    latency_ms=(time.time() - start_time) * 1000,
                    error_message="All publishing methods failed, event buffered"
                )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Event publishing failed for {event.event_id}: {e}")
            self._stats.failed_publishes += 1
            
            return PublishingResult(
                success=False,
                event_id=event.event_id,
                status=PublishingStatus.FAILED,
                latency_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    def publish_batch(self, 
                     events: List[StandardizedEvent],
                     queue_name: str = DEFAULT_QUEUE) -> List[PublishingResult]:
        """
        Publish multiple events in batch for improved performance.
        
        Args:
            events: List of events to publish
            queue_name: Target queue name
            
        Returns:
            List of PublishingResult for each event
        """
        if not events:
            return []
        
        self.logger.info(f"Publishing batch of {len(events)} events to {queue_name}")
        
        # Use thread pool for parallel publishing
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(self.publish_event, event, queue_name, False)
                for event in events
            ]
            
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=30)  # 30 second timeout per event
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Batch publishing failed: {e}")
                    results.append(PublishingResult(
                        success=False,
                        event_id="unknown",
                        status=PublishingStatus.FAILED,
                        latency_ms=0.0,
                        error_message=str(e)
                    ))
        
        successful = sum(1 for r in results if r.success)
        self.logger.info(f"Batch publishing completed: {successful}/{len(events)} successful")
        
        return results
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """
        Get current buffer status and statistics.
        
        Returns:
            Dictionary with buffer information
        """
        with self._buffer_lock:
            buffer_size = self._event_buffer.qsize()
            
            # Count events by status
            expired_count = 0
            retry_ready_count = 0
            
            # Note: This is a snapshot and doesn't modify the queue
            temp_events = []
            try:
                while True:
                    event = self._event_buffer.get_nowait()
                    temp_events.append(event)
                    
                    if event.is_expired:
                        expired_count += 1
                    elif event.can_retry:
                        retry_ready_count += 1
            except Empty:
                pass
            
            # Put events back
            for event in temp_events:
                try:
                    self._event_buffer.put_nowait(event)
                except:
                    pass  # Queue might be full
        
        return {
            'buffer_size': buffer_size,
            'max_buffer_size': self.BUFFER_MAX_SIZE,
            'buffer_utilization': (buffer_size / self.BUFFER_MAX_SIZE) * 100,
            'expired_events': expired_count,
            'retry_ready_events': retry_ready_count,
            'processor_running': self._buffer_processor_running,
            'active_retries': len(self._active_retries)
        }
    
    def get_publishing_stats(self) -> PublishingStats:
        """
        Get comprehensive publishing statistics.
        
        Returns:
            PublishingStats object with current metrics
        """
        # Update average latency
        if self._latency_samples:
            self._stats.average_latency_ms = sum(self._latency_samples) / len(self._latency_samples)
            self._stats.max_latency_ms = max(self._latency_samples)
            
            # Keep only recent samples (last 1000)
            if len(self._latency_samples) > 1000:
                self._latency_samples = self._latency_samples[-1000:]
        
        return self._stats
    
    def force_buffer_flush(self) -> Dict[str, Any]:
        """
        Force flush of buffered events (for testing/maintenance).
        
        Returns:
            Dictionary with flush results
        """
        self.logger.info("Force flushing event buffer")
        
        processed = 0
        successful = 0
        failed = 0
        
        with self._buffer_lock:
            temp_events = []
            try:
                while True:
                    event = self._event_buffer.get_nowait()
                    temp_events.append(event)
            except Empty:
                pass
            
            for buffered_event in temp_events:
                processed += 1
                
                if not buffered_event.is_expired:
                    result = self._publish_to_redis(
                        buffered_event.event, 
                        buffered_event.queue_name, 
                        False
                    )
                    
                    if result.success:
                        successful += 1
                    else:
                        failed += 1
                        # Put back in buffer if not expired
                        try:
                            self._event_buffer.put_nowait(buffered_event)
                        except:
                            pass
                else:
                    failed += 1  # Count expired as failed
        
        return {
            'processed': processed,
            'successful': successful,
            'failed': failed,
            'remaining_in_buffer': self._event_buffer.qsize()
        }
    
    def shutdown(self) -> None:
        """Shutdown publisher and cleanup resources."""
        self.logger.info("Shutting down reliable event publisher")
        
        # Stop buffer processor
        self._buffer_processor_running = False
        if self._buffer_processor_thread:
            self._buffer_processor_thread.join(timeout=10)
        
        # Cancel active retries
        for future in self._active_retries.values():
            future.cancel()
        
        # Shutdown retry executor
        self._retry_executor.shutdown(wait=True, timeout=30)
        
        self.logger.info("Reliable event publisher shutdown complete")
    
    # Private methods for core functionality
    
    def _publish_to_redis(self, 
                         event: StandardizedEvent,
                         queue_name: str,
                         require_confirmation: bool) -> PublishingResult:
        """Publish event to Redis queue with optional confirmation."""
        start_time = time.time()
        
        try:
            if not self.redis.is_healthy:
                return PublishingResult(
                    success=False,
                    event_id=event.event_id,
                    status=PublishingStatus.FAILED,
                    latency_ms=0.0,
                    error_message="Redis client is unhealthy"
                )
            
            # Serialize event
            event_data = event.to_json()
            
            # Generate confirmation ID if required
            confirmation_id = None
            if require_confirmation:
                confirmation_id = str(uuid.uuid4())
                event_dict = event.to_dict()
                event_dict['_confirmation_id'] = confirmation_id
                event_data = json.dumps(event_dict, indent=2, ensure_ascii=False)
            
            # Publish to Redis queue using LPUSH (left push for FIFO with BRPOP)
            pipeline = self.redis.pipeline()
            if pipeline:
                pipeline.lpush(queue_name, event_data)
                if require_confirmation:
                    # Set confirmation key with short expiration
                    confirmation_key = f"confirm:{confirmation_id}"
                    pipeline.setex(confirmation_key, int(self.CONFIRMATION_TIMEOUT), "pending")
                
                results = pipeline.execute()
                
                if results and results[0]:  # LPUSH returns queue length
                    latency_ms = (time.time() - start_time) * 1000
                    self._latency_samples.append(latency_ms)
                    
                    # Wait for confirmation if required
                    if require_confirmation and confirmation_id:
                        confirmed = self._wait_for_confirmation(confirmation_id)
                        if not confirmed:
                            self._stats.confirmation_failures += 1
                            return PublishingResult(
                                success=False,
                                event_id=event.event_id,
                                status=PublishingStatus.FAILED,
                                latency_ms=latency_ms,
                                error_message="Publishing confirmation timeout",
                                confirmation_id=confirmation_id
                            )
                    
                    self._stats.successful_publishes += 1
                    return PublishingResult(
                        success=True,
                        event_id=event.event_id,
                        status=PublishingStatus.PUBLISHED,
                        latency_ms=latency_ms,
                        queue_name=queue_name,
                        confirmation_id=confirmation_id
                    )
            
            # Fallback to direct Redis operations
            queue_length = self.redis._client.lpush(queue_name, event_data)
            if queue_length:
                latency_ms = (time.time() - start_time) * 1000
                self._latency_samples.append(latency_ms)
                self._stats.successful_publishes += 1
                
                return PublishingResult(
                    success=True,
                    event_id=event.event_id,
                    status=PublishingStatus.PUBLISHED,
                    latency_ms=latency_ms,
                    queue_name=queue_name
                )
            
            return PublishingResult(
                success=False,
                event_id=event.event_id,
                status=PublishingStatus.FAILED,
                latency_ms=(time.time() - start_time) * 1000,
                error_message="Redis LPUSH returned 0"
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._stats.failed_publishes += 1
            
            return PublishingResult(
                success=False,
                event_id=event.event_id,
                status=PublishingStatus.FAILED,
                latency_ms=latency_ms,
                error_message=str(e)
            )
    
    def _wait_for_confirmation(self, confirmation_id: str) -> bool:
        """Wait for publishing confirmation."""
        try:
            confirmation_key = f"confirm:{confirmation_id}"
            start_time = time.time()
            
            while time.time() - start_time < self.CONFIRMATION_TIMEOUT:
                status = self.redis.get(confirmation_key)
                if status == "confirmed":
                    return True
                elif status == "failed":
                    return False
                
                time.sleep(0.01)  # 10ms polling interval
            
            return False  # Timeout
            
        except Exception as e:
            self.logger.warning(f"Confirmation check failed: {e}")
            return False
    
    def _publish_with_backup_method(self, 
                                  event: StandardizedEvent,
                                  queue_name: str) -> PublishingResult:
        """Try backup publishing methods in order of preference."""
        backup_methods = [BackupMethod.DATABASE, BackupMethod.FILE_SYSTEM]
        
        for method in backup_methods:
            try:
                backup_func = self._backup_methods.get(method)
                if backup_func:
                    result = backup_func(event, queue_name)
                    if result.success:
                        self._stats.backup_publishes += 1
                        return result
            except Exception as e:
                self.logger.warning(f"Backup method {method.value} failed: {e}")
                continue
        
        return PublishingResult(
            success=False,
            event_id=event.event_id,
            status=PublishingStatus.FAILED,
            latency_ms=0.0,
            error_message="All backup methods failed"
        )
    
    def _publish_to_database(self, 
                           event: StandardizedEvent,
                           queue_name: str) -> PublishingResult:
        """Publish event to database as backup method."""
        start_time = time.time()
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO event_backup_queue 
                        (event_id, queue_name, event_data, created_at, status)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        event.event_id,
                        queue_name,
                        event.to_json(),
                        datetime.now(timezone.utc),
                        'pending'
                    ))
                    
                    conn.commit()
                    
                    return PublishingResult(
                        success=True,
                        event_id=event.event_id,
                        status=PublishingStatus.BACKUP_PUBLISHED,
                        latency_ms=(time.time() - start_time) * 1000,
                        backup_method=BackupMethod.DATABASE
                    )
                    
        except Exception as e:
            return PublishingResult(
                success=False,
                event_id=event.event_id,
                status=PublishingStatus.FAILED,
                latency_ms=(time.time() - start_time) * 1000,
                error_message=f"Database backup failed: {e}"
            )
    
    def _publish_to_filesystem(self, 
                             event: StandardizedEvent,
                             queue_name: str) -> PublishingResult:
        """Publish event to filesystem as backup method."""
        start_time = time.time()
        
        try:
            import os
            
            # Create backup directory if it doesn't exist
            backup_dir = "/tmp/email_agent_backup"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Write event to file
            filename = f"{event.event_id}_{int(time.time())}.json"
            filepath = os.path.join(backup_dir, filename)
            
            with open(filepath, 'w') as f:
                f.write(event.to_json())
            
            return PublishingResult(
                success=True,
                event_id=event.event_id,
                status=PublishingStatus.BACKUP_PUBLISHED,
                latency_ms=(time.time() - start_time) * 1000,
                backup_method=BackupMethod.FILE_SYSTEM
            )
            
        except Exception as e:
            return PublishingResult(
                success=False,
                event_id=event.event_id,
                status=PublishingStatus.FAILED,
                latency_ms=(time.time() - start_time) * 1000,
                error_message=f"Filesystem backup failed: {e}"
            )
    
    def _publish_to_webhook(self, 
                          event: StandardizedEvent,
                          queue_name: str) -> PublishingResult:
        """Publish event to webhook as backup method."""
        # Placeholder for webhook implementation
        return PublishingResult(
            success=False,
            event_id=event.event_id,
            status=PublishingStatus.FAILED,
            latency_ms=0.0,
            error_message="Webhook backup not implemented"
        )
    
    def _buffer_event(self, event: StandardizedEvent, queue_name: str) -> None:
        """Buffer event for later retry."""
        try:
            buffered_event = BufferedEvent(
                event=event,
                queue_name=queue_name,
                timestamp=datetime.now(timezone.utc)
            )
            
            with self._buffer_lock:
                if self._event_buffer.qsize() < self.BUFFER_MAX_SIZE:
                    self._event_buffer.put_nowait(buffered_event)
                    self._stats.buffered_events += 1
                    self.logger.debug(f"Event {event.event_id} buffered for retry")
                else:
                    self.logger.warning(f"Buffer full, dropping event {event.event_id}")
                    
        except Exception as e:
            self.logger.error(f"Failed to buffer event {event.event_id}: {e}")
    
    def _start_buffer_processor(self) -> None:
        """Start background thread to process buffered events."""
        if self._buffer_processor_running:
            return
        
        self._buffer_processor_running = True
        self._buffer_processor_thread = threading.Thread(
            target=self._process_buffered_events,
            name="event-buffer-processor",
            daemon=True
        )
        self._buffer_processor_thread.start()
        
        self.logger.info("Buffer processor started")
    
    def _process_buffered_events(self) -> None:
        """Background processor for buffered events with exponential backoff."""
        while self._buffer_processor_running:
            try:
                # Process events with exponential backoff
                events_to_retry = []
                
                with self._buffer_lock:
                    temp_events = []
                    try:
                        while True:
                            event = self._event_buffer.get_nowait()
                            temp_events.append(event)
                    except Empty:
                        pass
                    
                    # Filter events ready for retry
                    for event in temp_events:
                        if event.is_expired:
                            # Drop expired events
                            continue
                        elif event.can_retry:
                            events_to_retry.append(event)
                        else:
                            # Put back events not ready for retry
                            try:
                                self._event_buffer.put_nowait(event)
                            except:
                                pass
                
                # Process retry events
                for buffered_event in events_to_retry:
                    self._retry_buffered_event(buffered_event)
                
                # Sleep before next processing cycle
                time.sleep(1.0)  # Process every second
                
            except Exception as e:
                self.logger.error(f"Buffer processor error: {e}")
                time.sleep(5.0)  # Longer sleep on error
    
    def _retry_buffered_event(self, buffered_event: BufferedEvent) -> None:
        """Retry publishing a buffered event with exponential backoff."""
        try:
            # Calculate exponential backoff delay
            delay = min(
                self.BASE_RETRY_DELAY * (2 ** buffered_event.retry_count),
                self.MAX_RETRY_DELAY
            )
            
            # Submit retry task
            future = self._retry_executor.submit(
                self._execute_retry,
                buffered_event,
                delay
            )
            
            self._active_retries[buffered_event.event.event_id] = future
            
        except Exception as e:
            self.logger.error(f"Failed to schedule retry for event {buffered_event.event.event_id}: {e}")
    
    def _execute_retry(self, buffered_event: BufferedEvent, delay: float) -> None:
        """Execute retry attempt for buffered event."""
        try:
            # Wait for backoff delay
            time.sleep(delay)
            
            # Increment retry count
            buffered_event.retry_count += 1
            self._stats.retry_attempts += 1
            
            # Attempt to publish
            result = self._publish_to_redis(
                buffered_event.event,
                buffered_event.queue_name,
                False  # No confirmation for retries
            )
            
            if result.success:
                self.logger.info(f"Retry successful for event {buffered_event.event.event_id} after {buffered_event.retry_count} attempts")
            else:
                # Calculate next retry time
                next_delay = min(
                    self.BASE_RETRY_DELAY * (2 ** buffered_event.retry_count),
                    self.MAX_RETRY_DELAY
                )
                buffered_event.next_retry = datetime.now(timezone.utc) + timedelta(seconds=next_delay)
                
                # Put back in buffer if not at max retries
                if buffered_event.retry_count < buffered_event.max_retries:
                    with self._buffer_lock:
                        try:
                            self._event_buffer.put_nowait(buffered_event)
                        except:
                            self.logger.warning(f"Failed to re-buffer event {buffered_event.event.event_id}")
                else:
                    self.logger.error(f"Max retries exceeded for event {buffered_event.event.event_id}")
            
        except Exception as e:
            self.logger.error(f"Retry execution failed for event {buffered_event.event.event_id}: {e}")
        finally:
            # Remove from active retries
            self._active_retries.pop(buffered_event.event.event_id, None)
    
    def _initialize_backup_storage(self) -> None:
        """Initialize database schema for backup storage."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Create backup queue table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS event_backup_queue (
                            id SERIAL PRIMARY KEY,
                            event_id VARCHAR(255) NOT NULL UNIQUE,
                            queue_name VARCHAR(255) NOT NULL,
                            event_data TEXT NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                            processed_at TIMESTAMP WITH TIME ZONE,
                            status VARCHAR(50) DEFAULT 'pending',
                            retry_count INTEGER DEFAULT 0,
                            error_message TEXT,
                            INDEX idx_event_backup_status (status),
                            INDEX idx_event_backup_created (created_at)
                        )
                    """)
                    
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Failed to initialize backup storage: {e}")


# Exception classes
class EventPublishingError(Exception):
    """Base exception for event publishing errors."""
    pass


class PublishingTimeoutError(EventPublishingError):
    """Exception raised when publishing times out."""
    pass


class BufferFullError(EventPublishingError):
    """Exception raised when event buffer is full."""
    pass