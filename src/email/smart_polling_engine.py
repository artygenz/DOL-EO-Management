# src/email/smart_polling_engine.py
import asyncio
import threading
import time
import logging
import statistics
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue, Empty
import json
import pickle
import os
from collections import deque, defaultdict
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import joblib

from .godaddy_client import GoDaddyEmailClient, RateLimitInfo
from .connection_pool import ConnectionPoolManager, PooledConnection
from ..database.manager import DatabaseManager
from ..database.models import EmailMetadata, ProcessingStatus


class PollingStrategy(Enum):
    """Polling strategy enumeration"""
    FIXED_INTERVAL = "fixed_interval"
    ADAPTIVE_INTERVAL = "adaptive_interval"
    ML_OPTIMIZED = "ml_optimized"
    LOAD_BASED = "load_based"
    HYBRID = "hybrid"


class LoadLevel(Enum):
    """System load level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EmailPattern:
    """Email arrival pattern data"""
    timestamp: datetime
    email_count: int
    account_id: str
    hour_of_day: int
    day_of_week: int
    is_business_hours: bool
    interval_since_last: float = 0.0
    
    def to_features(self) -> List[float]:
        """Convert pattern to ML features"""
        return [
            self.hour_of_day,
            self.day_of_week,
            float(self.is_business_hours),
            self.email_count,
            self.interval_since_last
        ]


@dataclass
class PollingInterval:
    """Polling interval configuration"""
    base_interval: int  # seconds
    min_interval: int = 30
    max_interval: int = 300
    backoff_multiplier: float = 1.5
    reduction_factor: float = 0.8
    
    def __post_init__(self):
        if self.base_interval < self.min_interval:
            self.base_interval = self.min_interval
        if self.base_interval > self.max_interval:
            self.base_interval = self.max_interval


@dataclass
class PollingMetrics:
    """Polling engine performance metrics"""
    total_polls: int = 0
    successful_polls: int = 0
    failed_polls: int = 0
    emails_detected: int = 0
    average_response_time: float = 0.0
    rate_limit_hits: int = 0
    interval_adjustments: int = 0
    ml_predictions_made: int = 0
    accuracy_score: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        if self.total_polls == 0:
            return 0.0
        return (self.successful_polls / self.total_polls) * 100.0
    
    @property
    def detection_efficiency(self) -> float:
        if self.successful_polls == 0:
            return 0.0
        return self.emails_detected / self.successful_polls


@dataclass
class LoadMetrics:
    """System load metrics for polling adjustment"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_connections: int = 0
    queue_depth: int = 0
    processing_latency: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_load_level(self) -> LoadLevel:
        """Determine system load level"""
        if (self.cpu_usage > 80 or self.memory_usage > 85 or 
            self.queue_depth > 100 or self.processing_latency > 5000):
            return LoadLevel.CRITICAL
        elif (self.cpu_usage > 60 or self.memory_usage > 70 or 
              self.queue_depth > 50 or self.processing_latency > 2000):
            return LoadLevel.HIGH
        elif (self.cpu_usage > 40 or self.memory_usage > 50 or 
              self.queue_depth > 20 or self.processing_latency > 1000):
            return LoadLevel.MEDIUM
        else:
            return LoadLevel.LOW


class SmartPollingEngine:
    """
    Smart Polling Engine with machine learning-based interval optimization,
    historical pattern analysis, rate limit detection, and load-based adjustment.
    """
    
    def __init__(self,
                 connection_pool: ConnectionPoolManager,
                 database_manager: DatabaseManager,
                 strategy: PollingStrategy = PollingStrategy.HYBRID,
                 base_interval: int = 60,
                 pattern_history_days: int = 30,
                 ml_model_path: Optional[str] = None,
                 load_monitor_callback: Optional[Callable[[], LoadMetrics]] = None):
        
        self.connection_pool = connection_pool
        self.database_manager = database_manager
        self.strategy = strategy
        self.pattern_history_days = pattern_history_days
        self.ml_model_path = ml_model_path or "models/polling_optimizer.pkl"
        self.load_monitor_callback = load_monitor_callback
        
        # Polling configuration
        self._polling_intervals: Dict[str, PollingInterval] = {}
        self._default_interval = PollingInterval(base_interval)
        
        # Pattern analysis
        self._email_patterns: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._pattern_lock = threading.RLock()
        
        # Machine learning components
        self._ml_model: Optional[LinearRegression] = None
        self._scaler: Optional[StandardScaler] = None
        self._feature_history: deque = deque(maxlen=10000)
        self._prediction_accuracy: deque = deque(maxlen=100)
        
        # Active polling sessions
        self._active_sessions: Dict[str, threading.Thread] = {}
        self._session_control: Dict[str, threading.Event] = {}
        self._session_lock = threading.RLock()
        
        # Metrics and monitoring
        self._metrics: Dict[str, PollingMetrics] = defaultdict(PollingMetrics)
        self._load_history: deque = deque(maxlen=100)
        
        # Event callbacks
        self._email_callbacks: List[Callable[[str, List[EmailMetadata]], None]] = []
        self._interval_callbacks: List[Callable[[str, int, int], None]] = []
        
        # Threading
        self._shutdown_event = threading.Event()
        self._pattern_analyzer_thread: Optional[threading.Thread] = None
        self._ml_trainer_thread: Optional[threading.Thread] = None
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._initialize_ml_components()
        self._start_background_threads()

    def _initialize_ml_components(self) -> None:
        """Initialize machine learning components"""
        try:
            # Try to load existing model
            if os.path.exists(self.ml_model_path):
                self._load_ml_model()
                self.logger.info("Loaded existing ML model for polling optimization")
            else:
                # Initialize new model
                self._ml_model = LinearRegression()
                self._scaler = StandardScaler()
                self.logger.info("Initialized new ML model for polling optimization")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize ML components: {e}")
            self._ml_model = None
            self._scaler = None

    def _load_ml_model(self) -> None:
        """Load trained ML model from disk"""
        try:
            model_data = joblib.load(self.ml_model_path)
            self._ml_model = model_data['model']
            self._scaler = model_data['scaler']
            self._feature_history.extend(model_data.get('feature_history', []))
            
        except Exception as e:
            self.logger.error(f"Failed to load ML model: {e}")
            raise

    def _save_ml_model(self) -> None:
        """Save trained ML model to disk"""
        try:
            os.makedirs(os.path.dirname(self.ml_model_path), exist_ok=True)
            
            model_data = {
                'model': self._ml_model,
                'scaler': self._scaler,
                'feature_history': list(self._feature_history)
            }
            
            joblib.dump(model_data, self.ml_model_path)
            self.logger.info(f"Saved ML model to {self.ml_model_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save ML model: {e}")

    def _start_background_threads(self) -> None:
        """Start background analysis and training threads"""
        self._pattern_analyzer_thread = threading.Thread(
            target=self._pattern_analyzer_worker,
            daemon=True,
            name="PollingPatternAnalyzer"
        )
        self._pattern_analyzer_thread.start()
        
        self._ml_trainer_thread = threading.Thread(
            target=self._ml_trainer_worker,
            daemon=True,
            name="PollingMLTrainer"
        )
        self._ml_trainer_thread.start()

    def start_adaptive_polling(self, account_id: str, mailbox: str = "INBOX") -> None:
        """
        Start adaptive polling for an email account
        
        Args:
            account_id: Email account identifier
            mailbox: Mailbox to monitor (default: INBOX)
        """
        session_key = f"{account_id}_{mailbox}"
        
        with self._session_lock:
            if session_key in self._active_sessions:
                self.logger.warning(f"Polling already active for {account_id}/{mailbox}")
                return
            
            # Initialize polling interval for this account
            if account_id not in self._polling_intervals:
                self._polling_intervals[account_id] = PollingInterval(
                    base_interval=self._default_interval.base_interval
                )
            
            # Create session control event
            self._session_control[session_key] = threading.Event()
            
            # Start polling thread
            polling_thread = threading.Thread(
                target=self._polling_worker,
                args=(account_id, mailbox),
                daemon=True,
                name=f"PollingWorker_{session_key}"
            )
            
            self._active_sessions[session_key] = polling_thread
            polling_thread.start()
            
            self.logger.info(f"Started adaptive polling for {account_id}/{mailbox}")

    def stop_polling(self, account_id: str, mailbox: str = "INBOX") -> None:
        """Stop polling for an email account"""
        session_key = f"{account_id}_{mailbox}"
        
        with self._session_lock:
            if session_key in self._session_control:
                self._session_control[session_key].set()
                
            if session_key in self._active_sessions:
                thread = self._active_sessions[session_key]
                thread.join(timeout=5.0)
                
                del self._active_sessions[session_key]
                del self._session_control[session_key]
                
                self.logger.info(f"Stopped polling for {account_id}/{mailbox}")

    def _polling_worker(self, account_id: str, mailbox: str) -> None:
        """Worker thread for adaptive email polling"""
        session_key = f"{account_id}_{mailbox}"
        stop_event = self._session_control[session_key]
        
        self.logger.info(f"Starting polling worker for {account_id}/{mailbox}")
        
        last_poll_time = datetime.now()
        consecutive_empty_polls = 0
        
        try:
            while not stop_event.is_set() and not self._shutdown_event.is_set():
                try:
                    # Get current polling interval
                    current_interval = self._calculate_optimal_interval(account_id)
                    
                    # Check for rate limiting
                    if self._should_delay_for_rate_limit(account_id):
                        rate_limit_delay = self._get_rate_limit_delay(account_id)
                        self.logger.info(f"Rate limit detected, delaying {rate_limit_delay}s for {account_id}")
                        stop_event.wait(rate_limit_delay)
                        continue
                    
                    # Perform email polling
                    poll_start_time = time.time()
                    emails_found = self._poll_for_emails(account_id, mailbox)
                    poll_duration = time.time() - poll_start_time
                    
                    # Update metrics
                    self._update_polling_metrics(account_id, poll_duration, len(emails_found), True)
                    
                    # Record email pattern
                    if emails_found:
                        self._record_email_pattern(account_id, len(emails_found), last_poll_time)
                        consecutive_empty_polls = 0
                        
                        # Notify callbacks
                        self._notify_email_callbacks(account_id, emails_found)
                        
                        # Reduce interval after finding emails
                        self._adjust_interval_after_success(account_id)
                    else:
                        consecutive_empty_polls += 1
                        
                        # Increase interval after empty polls
                        if consecutive_empty_polls >= 3:
                            self._adjust_interval_after_empty_polls(account_id, consecutive_empty_polls)
                    
                    last_poll_time = datetime.now()
                    
                    # Wait for next poll
                    stop_event.wait(current_interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in polling worker for {account_id}: {e}")
                    self._update_polling_metrics(account_id, 0, 0, False)
                    
                    # Exponential backoff on errors
                    error_delay = min(300, 30 * (2 ** min(consecutive_empty_polls, 4)))
                    stop_event.wait(error_delay)
                    
        except Exception as e:
            self.logger.error(f"Polling worker for {account_id} failed: {e}")
        
        finally:
            self.logger.info(f"Polling worker for {account_id}/{mailbox} terminated")

    def _calculate_optimal_interval(self, account_id: str) -> int:
        """Calculate optimal polling interval using selected strategy"""
        try:
            if self.strategy == PollingStrategy.FIXED_INTERVAL:
                return self._polling_intervals[account_id].base_interval
            
            elif self.strategy == PollingStrategy.ADAPTIVE_INTERVAL:
                return self._calculate_adaptive_interval(account_id)
            
            elif self.strategy == PollingStrategy.ML_OPTIMIZED:
                return self._calculate_ml_optimized_interval(account_id)
            
            elif self.strategy == PollingStrategy.LOAD_BASED:
                return self._calculate_load_based_interval(account_id)
            
            elif self.strategy == PollingStrategy.HYBRID:
                return self._calculate_hybrid_interval(account_id)
            
            else:
                return self._polling_intervals[account_id].base_interval
                
        except Exception as e:
            self.logger.error(f"Error calculating optimal interval for {account_id}: {e}")
            return self._polling_intervals[account_id].base_interval

    def _calculate_adaptive_interval(self, account_id: str) -> int:
        """Calculate adaptive interval based on historical patterns"""
        try:
            patterns = self._email_patterns[account_id]
            if len(patterns) < 5:
                return self._polling_intervals[account_id].base_interval
            
            # Analyze recent patterns
            recent_patterns = list(patterns)[-10:]
            current_hour = datetime.now().hour
            current_day = datetime.now().weekday()
            
            # Find similar time periods
            similar_patterns = [
                p for p in recent_patterns
                if abs(p.hour_of_day - current_hour) <= 1 and p.day_of_week == current_day
            ]
            
            if similar_patterns:
                # Calculate average email frequency for similar periods
                avg_emails = statistics.mean(p.email_count for p in similar_patterns)
                avg_interval = statistics.mean(p.interval_since_last for p in similar_patterns if p.interval_since_last > 0)
                
                # Adjust interval based on expected email frequency
                if avg_emails > 2:
                    # High activity period - reduce interval
                    target_interval = max(30, int(avg_interval * 0.7))
                elif avg_emails > 0.5:
                    # Medium activity - maintain interval
                    target_interval = int(avg_interval)
                else:
                    # Low activity - increase interval
                    target_interval = min(300, int(avg_interval * 1.3))
                
                return self._clamp_interval(account_id, target_interval)
            
            return self._polling_intervals[account_id].base_interval
            
        except Exception as e:
            self.logger.error(f"Error calculating adaptive interval: {e}")
            return self._polling_intervals[account_id].base_interval

    def _calculate_ml_optimized_interval(self, account_id: str) -> int:
        """Calculate ML-optimized polling interval"""
        try:
            if not self._ml_model or not self._scaler:
                return self._calculate_adaptive_interval(account_id)
            
            # Prepare features for prediction
            now = datetime.now()
            features = [
                now.hour,
                now.weekday(),
                float(9 <= now.hour <= 17),  # Business hours
                0,  # Email count (unknown, will be predicted)
                self._get_average_interval_since_last(account_id)
            ]
            
            # Make prediction
            features_scaled = self._scaler.transform([features])
            predicted_emails = max(0, self._ml_model.predict(features_scaled)[0])
            
            # Update metrics
            self._metrics[account_id].ml_predictions_made += 1
            
            # Calculate interval based on prediction
            if predicted_emails > 2:
                target_interval = 30  # High activity expected
            elif predicted_emails > 0.5:
                target_interval = 60  # Medium activity expected
            else:
                target_interval = 120  # Low activity expected
            
            return self._clamp_interval(account_id, target_interval)
            
        except Exception as e:
            self.logger.error(f"Error calculating ML-optimized interval: {e}")
            return self._calculate_adaptive_interval(account_id)

    def _calculate_load_based_interval(self, account_id: str) -> int:
        """Calculate interval based on system load"""
        try:
            # Get current load metrics
            if self.load_monitor_callback:
                load_metrics = self.load_monitor_callback()
            else:
                load_metrics = self._estimate_load_metrics()
            
            load_level = load_metrics.get_load_level()
            base_interval = self._polling_intervals[account_id].base_interval
            
            # Adjust interval based on load
            if load_level == LoadLevel.CRITICAL:
                return min(300, base_interval * 3)
            elif load_level == LoadLevel.HIGH:
                return min(240, base_interval * 2)
            elif load_level == LoadLevel.MEDIUM:
                return min(180, int(base_interval * 1.5))
            else:  # LOW
                return max(30, int(base_interval * 0.8))
                
        except Exception as e:
            self.logger.error(f"Error calculating load-based interval: {e}")
            return self._polling_intervals[account_id].base_interval

    def _calculate_hybrid_interval(self, account_id: str) -> int:
        """Calculate hybrid interval combining multiple strategies"""
        try:
            # Get intervals from different strategies
            adaptive_interval = self._calculate_adaptive_interval(account_id)
            ml_interval = self._calculate_ml_optimized_interval(account_id)
            load_interval = self._calculate_load_based_interval(account_id)
            
            # Weight the intervals (adaptive: 40%, ML: 40%, load: 20%)
            weighted_interval = int(
                adaptive_interval * 0.4 +
                ml_interval * 0.4 +
                load_interval * 0.2
            )
            
            return self._clamp_interval(account_id, weighted_interval)
            
        except Exception as e:
            self.logger.error(f"Error calculating hybrid interval: {e}")
            return self._polling_intervals[account_id].base_interval

    def _clamp_interval(self, account_id: str, interval: int) -> int:
        """Clamp interval to configured min/max values"""
        config = self._polling_intervals[account_id]
        return max(config.min_interval, min(config.max_interval, interval))

    def _should_delay_for_rate_limit(self, account_id: str) -> bool:
        """Check if polling should be delayed due to rate limiting"""
        try:
            # Get connection to check rate limit status
            connection = self.connection_pool.get_connection()
            try:
                rate_limit_info = connection.connection.get_rate_limit_info()
                return rate_limit_info.is_rate_limited
            finally:
                self.connection_pool.return_connection(connection)
                
        except Exception as e:
            self.logger.error(f"Error checking rate limit status: {e}")
            return False

    def _get_rate_limit_delay(self, account_id: str) -> int:
        """Get delay time for rate limiting"""
        try:
            connection = self.connection_pool.get_connection()
            try:
                rate_limit_info = connection.connection.get_rate_limit_info()
                return rate_limit_info.backoff_seconds
            finally:
                self.connection_pool.return_connection(connection)
                
        except Exception as e:
            self.logger.error(f"Error getting rate limit delay: {e}")
            return 60  # Default delay

    def _poll_for_emails(self, account_id: str, mailbox: str) -> List[EmailMetadata]:
        """Poll for new emails and return metadata"""
        try:
            connection = self.connection_pool.get_connection()
            try:
                # Fetch unread emails
                emails = connection.connection.fetch_unread_emails()
                
                # Convert to EmailMetadata objects
                email_metadata = []
                for email in emails:
                    try:
                        metadata = EmailMetadata(
                            uid=email.get('Message-ID', f"unknown_{int(time.time())}"),
                            message_id=email.get('Message-ID', ''),
                            sender=email.get('From', ''),
                            subject=email.get('Subject', ''),
                            received_date=datetime.now(),  # Simplified for now
                            account_id=account_id,
                            thread_id=email.get('In-Reply-To'),
                            size_bytes=len(str(email))
                        )
                        email_metadata.append(metadata)
                        
                    except Exception as e:
                        self.logger.error(f"Error creating email metadata: {e}")
                        continue
                
                return email_metadata
                
            finally:
                self.connection_pool.return_connection(connection)
                
        except Exception as e:
            self.logger.error(f"Error polling for emails: {e}")
            raise

    def _record_email_pattern(self, account_id: str, email_count: int, last_poll_time: datetime) -> None:
        """Record email arrival pattern for analysis"""
        try:
            now = datetime.now()
            interval_since_last = (now - last_poll_time).total_seconds()
            
            pattern = EmailPattern(
                timestamp=now,
                email_count=email_count,
                account_id=account_id,
                hour_of_day=now.hour,
                day_of_week=now.weekday(),
                is_business_hours=(9 <= now.hour <= 17),
                interval_since_last=interval_since_last
            )
            
            with self._pattern_lock:
                self._email_patterns[account_id].append(pattern)
                
                # Add to feature history for ML training
                self._feature_history.append({
                    'features': pattern.to_features(),
                    'target': email_count,
                    'timestamp': now
                })
            
        except Exception as e:
            self.logger.error(f"Error recording email pattern: {e}")

    def _adjust_interval_after_success(self, account_id: str) -> None:
        """Adjust polling interval after successful email detection"""
        try:
            config = self._polling_intervals[account_id]
            new_interval = max(
                config.min_interval,
                int(config.base_interval * config.reduction_factor)
            )
            
            if new_interval != config.base_interval:
                old_interval = config.base_interval
                config.base_interval = new_interval
                self._metrics[account_id].interval_adjustments += 1
                
                self._notify_interval_callbacks(account_id, old_interval, new_interval)
                self.logger.debug(f"Reduced polling interval for {account_id}: {old_interval}s -> {new_interval}s")
                
        except Exception as e:
            self.logger.error(f"Error adjusting interval after success: {e}")

    def _adjust_interval_after_empty_polls(self, account_id: str, consecutive_empty: int) -> None:
        """Adjust polling interval after consecutive empty polls"""
        try:
            config = self._polling_intervals[account_id]
            backoff_factor = config.backoff_multiplier ** min(consecutive_empty - 2, 3)
            new_interval = min(
                config.max_interval,
                int(config.base_interval * backoff_factor)
            )
            
            if new_interval != config.base_interval:
                old_interval = config.base_interval
                config.base_interval = new_interval
                self._metrics[account_id].interval_adjustments += 1
                
                self._notify_interval_callbacks(account_id, old_interval, new_interval)
                self.logger.debug(f"Increased polling interval for {account_id}: {old_interval}s -> {new_interval}s")
                
        except Exception as e:
            self.logger.error(f"Error adjusting interval after empty polls: {e}")

    def _update_polling_metrics(self, account_id: str, duration: float, emails_found: int, success: bool) -> None:
        """Update polling performance metrics"""
        try:
            metrics = self._metrics[account_id]
            metrics.total_polls += 1
            
            if success:
                metrics.successful_polls += 1
                metrics.emails_detected += emails_found
                
                # Update average response time
                if metrics.average_response_time == 0:
                    metrics.average_response_time = duration * 1000  # Convert to ms
                else:
                    # Exponential moving average
                    alpha = 0.1
                    metrics.average_response_time = (
                        alpha * (duration * 1000) + 
                        (1 - alpha) * metrics.average_response_time
                    )
            else:
                metrics.failed_polls += 1
            
            metrics.last_updated = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error updating polling metrics: {e}")

    def _get_average_interval_since_last(self, account_id: str) -> float:
        """Get average interval since last email for account"""
        try:
            patterns = self._email_patterns[account_id]
            if len(patterns) < 2:
                return 60.0  # Default
            
            intervals = [p.interval_since_last for p in patterns if p.interval_since_last > 0]
            return statistics.mean(intervals) if intervals else 60.0
            
        except Exception as e:
            self.logger.error(f"Error calculating average interval: {e}")
            return 60.0

    def _estimate_load_metrics(self) -> LoadMetrics:
        """Estimate system load metrics when callback not available"""
        try:
            # Simple estimation based on active sessions and recent metrics
            active_sessions = len(self._active_sessions)
            
            # Estimate CPU usage based on active sessions
            cpu_usage = min(100, active_sessions * 10)
            
            # Estimate memory usage
            memory_usage = min(100, active_sessions * 5 + 20)
            
            # Estimate queue depth based on recent polling activity
            total_polls = sum(m.total_polls for m in self._metrics.values())
            queue_depth = min(100, total_polls % 50)
            
            # Estimate processing latency
            avg_response_times = [m.average_response_time for m in self._metrics.values() if m.average_response_time > 0]
            processing_latency = statistics.mean(avg_response_times) if avg_response_times else 100
            
            return LoadMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                active_connections=active_sessions,
                queue_depth=queue_depth,
                processing_latency=processing_latency
            )
            
        except Exception as e:
            self.logger.error(f"Error estimating load metrics: {e}")
            return LoadMetrics()

    def _notify_email_callbacks(self, account_id: str, emails: List[EmailMetadata]) -> None:
        """Notify email detection callbacks"""
        for callback in self._email_callbacks:
            try:
                callback(account_id, emails)
            except Exception as e:
                self.logger.error(f"Error in email callback: {e}")

    def _notify_interval_callbacks(self, account_id: str, old_interval: int, new_interval: int) -> None:
        """Notify interval adjustment callbacks"""
        for callback in self._interval_callbacks:
            try:
                callback(account_id, old_interval, new_interval)
            except Exception as e:
                self.logger.error(f"Error in interval callback: {e}")

    def _pattern_analyzer_worker(self) -> None:
        """Background worker for analyzing email patterns"""
        self.logger.info("Starting pattern analyzer worker")
        
        while not self._shutdown_event.is_set():
            try:
                self._analyze_patterns()
                time.sleep(300)  # Analyze every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Pattern analyzer worker error: {e}")
                time.sleep(60)

    def _analyze_patterns(self) -> None:
        """Analyze email patterns and update predictions"""
        try:
            with self._pattern_lock:
                for account_id, patterns in self._email_patterns.items():
                    if len(patterns) < 10:
                        continue
                    
                    # Analyze patterns for this account
                    recent_patterns = list(patterns)[-50:]  # Last 50 patterns
                    
                    # Calculate pattern statistics
                    hourly_stats = defaultdict(list)
                    daily_stats = defaultdict(list)
                    
                    for pattern in recent_patterns:
                        hourly_stats[pattern.hour_of_day].append(pattern.email_count)
                        daily_stats[pattern.day_of_week].append(pattern.email_count)
                    
                    # Log insights
                    peak_hours = sorted(hourly_stats.keys(), 
                                      key=lambda h: statistics.mean(hourly_stats[h]), 
                                      reverse=True)[:3]
                    
                    self.logger.debug(f"Peak email hours for {account_id}: {peak_hours}")
            
        except Exception as e:
            self.logger.error(f"Error analyzing patterns: {e}")

    def _ml_trainer_worker(self) -> None:
        """Background worker for training ML models"""
        self.logger.info("Starting ML trainer worker")
        
        while not self._shutdown_event.is_set():
            try:
                if len(self._feature_history) >= 100:  # Minimum data for training
                    self._train_ml_model()
                
                time.sleep(3600)  # Train every hour
                
            except Exception as e:
                self.logger.error(f"ML trainer worker error: {e}")
                time.sleep(300)

    def _train_ml_model(self) -> None:
        """Train ML model with collected feature data"""
        try:
            if not self._ml_model or not self._scaler:
                return
            
            # Prepare training data
            features = []
            targets = []
            
            for data in list(self._feature_history)[-1000:]:  # Use last 1000 samples
                features.append(data['features'])
                targets.append(data['target'])
            
            if len(features) < 50:
                return
            
            # Convert to numpy arrays
            X = np.array(features)
            y = np.array(targets)
            
            # Scale features
            X_scaled = self._scaler.fit_transform(X)
            
            # Train model
            self._ml_model.fit(X_scaled, y)
            
            # Calculate accuracy on recent data
            if len(features) > 20:
                test_X = X_scaled[-20:]
                test_y = y[-20:]
                predictions = self._ml_model.predict(test_X)
                
                # Calculate mean absolute error as accuracy metric
                mae = np.mean(np.abs(predictions - test_y))
                accuracy = max(0, 1 - (mae / (np.mean(test_y) + 1)))
                
                self._prediction_accuracy.append(accuracy)
                
                # Update metrics
                for metrics in self._metrics.values():
                    if self._prediction_accuracy:
                        metrics.accuracy_score = statistics.mean(self._prediction_accuracy)
            
            # Save model periodically
            if len(self._feature_history) % 500 == 0:
                self._save_ml_model()
            
            self.logger.debug(f"Trained ML model with {len(features)} samples")
            
        except Exception as e:
            self.logger.error(f"Error training ML model: {e}")

    # Public API methods
    
    def add_email_callback(self, callback: Callable[[str, List[EmailMetadata]], None]) -> None:
        """Add callback for email detection events"""
        self._email_callbacks.append(callback)

    def add_interval_callback(self, callback: Callable[[str, int, int], None]) -> None:
        """Add callback for interval adjustment events"""
        self._interval_callbacks.append(callback)

    def get_polling_metrics(self, account_id: str) -> PollingMetrics:
        """Get polling metrics for an account"""
        return self._metrics[account_id]

    def get_all_metrics(self) -> Dict[str, PollingMetrics]:
        """Get polling metrics for all accounts"""
        return dict(self._metrics)

    def adjust_polling_interval(self, account_id: str, new_interval: int) -> None:
        """Manually adjust polling interval for an account"""
        if account_id in self._polling_intervals:
            old_interval = self._polling_intervals[account_id].base_interval
            self._polling_intervals[account_id].base_interval = self._clamp_interval(account_id, new_interval)
            self._notify_interval_callbacks(account_id, old_interval, new_interval)

    def set_strategy(self, strategy: PollingStrategy) -> None:
        """Change polling strategy"""
        self.strategy = strategy
        self.logger.info(f"Changed polling strategy to {strategy.value}")

    def shutdown(self) -> None:
        """Shutdown the polling engine"""
        self.logger.info("Shutting down smart polling engine")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Stop all polling sessions
        with self._session_lock:
            for session_key in list(self._active_sessions.keys()):
                account_id, mailbox = session_key.split('_', 1)
                self.stop_polling(account_id, mailbox)
        
        # Save ML model
        try:
            self._save_ml_model()
        except Exception as e:
            self.logger.error(f"Error saving ML model during shutdown: {e}")
        
        self.logger.info("Smart polling engine shutdown complete")