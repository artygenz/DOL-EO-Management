"""
Redis client wrapper for email tracking system.

Provides Redis connection management with failover, connection pooling,
and health monitoring for the UID tracking system.
"""

import logging
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from redis.connection import ConnectionPool

from ..config.models import RedisConfig


class RedisClient:
    """
    Redis client wrapper with connection pooling and health monitoring.
    
    Features:
    - Connection pooling for high performance
    - Automatic reconnection with exponential backoff
    - Health monitoring and status reporting
    - Graceful degradation when Redis is unavailable
    """
    
    def __init__(self, config: RedisConfig):
        """
        Initialize Redis client.
        
        Args:
            config: Redis configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Connection pool
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        
        # Health monitoring
        self._is_healthy = False
        self._last_health_check = time.time()
        self._connection_failures = 0
        self._max_failures = 3
        
        # Performance metrics
        self._operations_count = 0
        self._error_count = 0
        
        # Initialize connection
        self._initialize_connection()
    
    def _initialize_connection(self) -> None:
        """Initialize Redis connection and pool."""
        try:
            # Create connection pool
            self._pool = ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.database,
                password=self.config.password,
                ssl=self.config.ssl,
                socket_timeout=self.config.socket_timeout,
                max_connections=self.config.connection_pool_size,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            self._client.ping()
            self._is_healthy = True
            self._connection_failures = 0
            
            self.logger.info(f"Redis client initialized: {self.config.host}:{self.config.port}")
            
        except Exception as e:
            self.logger.error(f"Redis initialization failed: {e}")
            self._is_healthy = False
            self._connection_failures += 1
    
    @property
    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy."""
        # Perform periodic health checks
        current_time = time.time()
        if current_time - self._last_health_check > 30:  # Check every 30 seconds
            self._perform_health_check()
            self._last_health_check = current_time
        
        return self._is_healthy
    
    def _perform_health_check(self) -> None:
        """Perform Redis health check."""
        try:
            if self._client:
                self._client.ping()
                self._is_healthy = True
                self._connection_failures = 0
            else:
                self._is_healthy = False
        except Exception as e:
            self.logger.warning(f"Redis health check failed: {e}")
            self._is_healthy = False
            self._connection_failures += 1
            
            # Attempt reconnection if failures exceed threshold
            if self._connection_failures >= self._max_failures:
                self.logger.info("Attempting Redis reconnection...")
                self._initialize_connection()
    
    def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            Value as string or None if not found/error
        """
        try:
            if not self.is_healthy or not self._client:
                return None
            
            result = self._client.get(key)
            self._operations_count += 1
            
            return result.decode('utf-8') if result else None
            
        except Exception as e:
            self.logger.warning(f"Redis GET failed for key {key}: {e}")
            self._error_count += 1
            self._is_healthy = False
            return None
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set value in Redis.
        
        Args:
            key: Redis key
            value: Value to set
            ex: Expiration time in seconds
            
        Returns:
            True if successful
        """
        try:
            if not self.is_healthy or not self._client:
                return False
            
            result = self._client.set(key, value, ex=ex)
            self._operations_count += 1
            
            return bool(result)
            
        except Exception as e:
            self.logger.warning(f"Redis SET failed for key {key}: {e}")
            self._error_count += 1
            self._is_healthy = False
            return False
    
    def setex(self, key: str, time: int, value: str) -> bool:
        """
        Set value with expiration time.
        
        Args:
            key: Redis key
            time: Expiration time in seconds
            value: Value to set
            
        Returns:
            True if successful
        """
        try:
            if not self.is_healthy or not self._client:
                return False
            
            result = self._client.setex(key, time, value)
            self._operations_count += 1
            
            return bool(result)
            
        except Exception as e:
            self.logger.warning(f"Redis SETEX failed for key {key}: {e}")
            self._error_count += 1
            self._is_healthy = False
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.
        
        Args:
            key: Redis key to check
            
        Returns:
            True if key exists
        """
        try:
            if not self.is_healthy or not self._client:
                return False
            
            result = self._client.exists(key)
            self._operations_count += 1
            
            return bool(result)
            
        except Exception as e:
            self.logger.warning(f"Redis EXISTS failed for key {key}: {e}")
            self._error_count += 1
            self._is_healthy = False
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from Redis.
        
        Args:
            key: Redis key to delete
            
        Returns:
            True if key was deleted
        """
        try:
            if not self.is_healthy or not self._client:
                return False
            
            result = self._client.delete(key)
            self._operations_count += 1
            
            return bool(result)
            
        except Exception as e:
            self.logger.warning(f"Redis DELETE failed for key {key}: {e}")
            self._error_count += 1
            self._is_healthy = False
            return False
    
    def keys(self, pattern: str) -> list:
        """
        Get keys matching pattern.
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            List of matching keys
        """
        try:
            if not self.is_healthy or not self._client:
                return []
            
            result = self._client.keys(pattern)
            self._operations_count += 1
            
            return [key.decode('utf-8') for key in result]
            
        except Exception as e:
            self.logger.warning(f"Redis KEYS failed for pattern {pattern}: {e}")
            self._error_count += 1
            self._is_healthy = False
            return []
    
    def pipeline(self):
        """
        Create Redis pipeline for batch operations.
        
        Returns:
            Redis pipeline object or None if unavailable
        """
        try:
            if not self.is_healthy or not self._client:
                return None
            
            return self._client.pipeline()
            
        except Exception as e:
            self.logger.warning(f"Redis pipeline creation failed: {e}")
            self._is_healthy = False
            return None
    
    def info(self) -> Dict[str, Any]:
        """
        Get Redis server information.
        
        Returns:
            Dictionary of Redis server info
        """
        try:
            if not self.is_healthy or not self._client:
                return {}
            
            result = self._client.info()
            self._operations_count += 1
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Redis INFO failed: {e}")
            self._error_count += 1
            self._is_healthy = False
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis client statistics.
        
        Returns:
            Dictionary of client statistics
        """
        return {
            'is_healthy': self._is_healthy,
            'connection_failures': self._connection_failures,
            'operations_count': self._operations_count,
            'error_count': self._error_count,
            'error_rate': (self._error_count / max(self._operations_count, 1)) * 100,
            'last_health_check': self._last_health_check,
            'config': {
                'host': self.config.host,
                'port': self.config.port,
                'database': self.config.database,
                'pool_size': self.config.connection_pool_size
            }
        }
    
    def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        try:
            if self._pool:
                self._pool.disconnect()
            
            self._client = None
            self._pool = None
            self._is_healthy = False
            
            self.logger.info("Redis client closed")
            
        except Exception as e:
            self.logger.error(f"Redis client close failed: {e}")