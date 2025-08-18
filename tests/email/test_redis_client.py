"""
Unit tests for Redis client wrapper.

Tests Redis connection management, health monitoring, and graceful degradation.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from src.email.redis_client import RedisClient
from src.config.models import RedisConfig


class TestRedisClient:
    """Test Redis client wrapper functionality."""
    
    @pytest.fixture
    def redis_config(self):
        """Create Redis configuration for testing."""
        return RedisConfig(
            host="localhost",
            port=6379,
            database=0,
            password=None,
            connection_pool_size=10,
            socket_timeout=30
        )
    
    @pytest.fixture
    def mock_redis_pool(self):
        """Create mock Redis connection pool."""
        with patch('src.email.redis_client.ConnectionPool') as mock_pool:
            yield mock_pool
    
    @pytest.fixture
    def mock_redis_instance(self):
        """Create mock Redis instance."""
        with patch('src.email.redis_client.redis.Redis') as mock_redis:
            mock_instance = Mock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True
            yield mock_instance
    
    def test_initialization_success(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test successful Redis client initialization."""
        client = RedisClient(redis_config)
        
        assert client.config == redis_config
        assert client._is_healthy is True
        assert client._connection_failures == 0
        
        # Verify connection pool was created with correct parameters
        mock_redis_pool.assert_called_once_with(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.database,
            password=redis_config.password,
            ssl=redis_config.ssl,
            socket_timeout=redis_config.socket_timeout,
            max_connections=redis_config.connection_pool_size,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Verify ping was called to test connection
        mock_redis_instance.ping.assert_called_once()
    
    def test_initialization_failure(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test Redis client initialization failure."""
        mock_redis_instance.ping.side_effect = RedisConnectionError("Connection failed")
        
        client = RedisClient(redis_config)
        
        assert client._is_healthy is False
        assert client._connection_failures == 1
    
    def test_health_check_success(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test successful health check."""
        client = RedisClient(redis_config)
        
        # Force health check
        client._last_health_check = time.time() - 31  # More than 30 seconds ago
        
        is_healthy = client.is_healthy
        
        assert is_healthy is True
        assert client._is_healthy is True
        assert client._connection_failures == 0
    
    def test_health_check_failure(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test health check failure."""
        client = RedisClient(redis_config)
        
        # Mock ping failure
        mock_redis_instance.ping.side_effect = RedisConnectionError("Connection lost")
        
        # Force health check
        client._last_health_check = time.time() - 31
        
        is_healthy = client.is_healthy
        
        assert is_healthy is False
        assert client._is_healthy is False
        assert client._connection_failures > 0
    
    def test_get_success(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test successful GET operation."""
        mock_redis_instance.get.return_value = b"test_value"
        
        client = RedisClient(redis_config)
        result = client.get("test_key")
        
        assert result == "test_value"
        assert client._operations_count == 1
        mock_redis_instance.get.assert_called_once_with("test_key")
    
    def test_get_not_found(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test GET operation when key not found."""
        mock_redis_instance.get.return_value = None
        
        client = RedisClient(redis_config)
        result = client.get("nonexistent_key")
        
        assert result is None
        assert client._operations_count == 1
    
    def test_get_failure(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test GET operation failure."""
        mock_redis_instance.get.side_effect = RedisError("Redis error")
        
        client = RedisClient(redis_config)
        result = client.get("test_key")
        
        assert result is None
        assert client._error_count == 1
        assert client._is_healthy is False
    
    def test_get_unhealthy_client(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test GET operation with unhealthy client."""
        client = RedisClient(redis_config)
        client._is_healthy = False
        
        result = client.get("test_key")
        
        assert result is None
        mock_redis_instance.get.assert_not_called()
    
    def test_set_success(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test successful SET operation."""
        mock_redis_instance.set.return_value = True
        
        client = RedisClient(redis_config)
        result = client.set("test_key", "test_value", ex=3600)
        
        assert result is True
        assert client._operations_count == 1
        mock_redis_instance.set.assert_called_once_with("test_key", "test_value", ex=3600)
    
    def test_set_failure(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test SET operation failure."""
        mock_redis_instance.set.side_effect = RedisError("Redis error")
        
        client = RedisClient(redis_config)
        result = client.set("test_key", "test_value")
        
        assert result is False
        assert client._error_count == 1
        assert client._is_healthy is False
    
    def test_setex_success(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test successful SETEX operation."""
        mock_redis_instance.setex.return_value = True
        
        client = RedisClient(redis_config)
        result = client.setex("test_key", 3600, "test_value")
        
        assert result is True
        assert client._operations_count == 1
        mock_redis_instance.setex.assert_called_once_with("test_key", 3600, "test_value")
    
    def test_exists_success(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test successful EXISTS operation."""
        mock_redis_instance.exists.return_value = 1
        
        client = RedisClient(redis_config)
        result = client.exists("test_key")
        
        assert result is True
        assert client._operations_count == 1
        mock_redis_instance.exists.assert_called_once_with("test_key")
    
    def test_exists_not_found(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test EXISTS operation when key doesn't exist."""
        mock_redis_instance.exists.return_value = 0
        
        client = RedisClient(redis_config)
        result = client.exists("test_key")
        
        assert result is False
        assert client._operations_count == 1
    
    def test_delete_success(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test successful DELETE operation."""
        mock_redis_instance.delete.return_value = 1
        
        client = RedisClient(redis_config)
        result = client.delete("test_key")
        
        assert result is True
        assert client._operations_count == 1
        mock_redis_instance.delete.assert_called_once_with("test_key")
    
    def test_delete_not_found(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test DELETE operation when key doesn't exist."""
        mock_redis_instance.delete.return_value = 0
        
        client = RedisClient(redis_config)
        result = client.delete("test_key")
        
        assert result is False
        assert client._operations_count == 1
    
    def test_keys_success(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test successful KEYS operation."""
        mock_redis_instance.keys.return_value = [b"key1", b"key2", b"key3"]
        
        client = RedisClient(redis_config)
        result = client.keys("test_*")
        
        assert result == ["key1", "key2", "key3"]
        assert client._operations_count == 1
        mock_redis_instance.keys.assert_called_once_with("test_*")
    
    def test_keys_empty_result(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test KEYS operation with no matching keys."""
        mock_redis_instance.keys.return_value = []
        
        client = RedisClient(redis_config)
        result = client.keys("nonexistent_*")
        
        assert result == []
        assert client._operations_count == 1
    
    def test_pipeline_success(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test successful pipeline creation."""
        mock_pipeline = Mock()
        mock_redis_instance.pipeline.return_value = mock_pipeline
        
        client = RedisClient(redis_config)
        result = client.pipeline()
        
        assert result == mock_pipeline
        mock_redis_instance.pipeline.assert_called_once()
    
    def test_pipeline_failure(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test pipeline creation failure."""
        mock_redis_instance.pipeline.side_effect = RedisError("Pipeline error")
        
        client = RedisClient(redis_config)
        result = client.pipeline()
        
        assert result is None
        assert client._is_healthy is False
    
    def test_info_success(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test successful INFO operation."""
        mock_info = {
            'redis_version': '6.2.0',
            'connected_clients': 5,
            'used_memory': 1024000
        }
        mock_redis_instance.info.return_value = mock_info
        
        client = RedisClient(redis_config)
        result = client.info()
        
        assert result == mock_info
        assert client._operations_count == 1
        mock_redis_instance.info.assert_called_once()
    
    def test_info_failure(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test INFO operation failure."""
        mock_redis_instance.info.side_effect = RedisError("Info error")
        
        client = RedisClient(redis_config)
        result = client.info()
        
        assert result == {}
        assert client._error_count == 1
        assert client._is_healthy is False
    
    def test_get_stats(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test getting client statistics."""
        client = RedisClient(redis_config)
        
        # Perform some operations to generate stats
        client._operations_count = 100
        client._error_count = 5
        
        stats = client.get_stats()
        
        assert stats['is_healthy'] is True
        assert stats['operations_count'] == 100
        assert stats['error_count'] == 5
        assert stats['error_rate'] == 5.0  # 5/100 * 100
        assert 'config' in stats
        assert stats['config']['host'] == redis_config.host
        assert stats['config']['port'] == redis_config.port
    
    def test_reconnection_after_failures(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test automatic reconnection after multiple failures."""
        client = RedisClient(redis_config)
        
        # Simulate multiple failures
        client._connection_failures = 3  # Exceeds max_failures
        client._is_healthy = False
        
        # Mock successful reconnection
        mock_redis_instance.ping.return_value = True
        
        # Force health check (should trigger reconnection)
        client._last_health_check = time.time() - 31
        
        is_healthy = client.is_healthy
        
        assert is_healthy is True
        assert client._connection_failures == 0
    
    def test_close_connection(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test closing Redis connection."""
        mock_pool_instance = Mock()
        mock_redis_pool.return_value = mock_pool_instance
        
        client = RedisClient(redis_config)
        client.close()
        
        assert client._client is None
        assert client._pool is None
        assert client._is_healthy is False
        mock_pool_instance.disconnect.assert_called_once()
    
    def test_close_connection_error(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test closing connection with error."""
        mock_pool_instance = Mock()
        mock_pool_instance.disconnect.side_effect = Exception("Disconnect error")
        mock_redis_pool.return_value = mock_pool_instance
        
        client = RedisClient(redis_config)
        
        # Should not raise exception
        client.close()
        
        assert client._client is None
        assert client._pool is None
        assert client._is_healthy is False
    
    def test_operations_with_ssl_config(self):
        """Test Redis client with SSL configuration."""
        ssl_config = RedisConfig(
            host="secure.redis.com",
            port=6380,
            ssl=True,
            password="secure_password"
        )
        
        with patch('src.email.redis_client.ConnectionPool') as mock_pool, \
             patch('src.email.redis_client.redis.Redis') as mock_redis:
            
            mock_instance = Mock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True
            
            client = RedisClient(ssl_config)
            
            # Verify SSL parameters were passed to connection pool
            mock_pool.assert_called_once_with(
                host="secure.redis.com",
                port=6380,
                db=0,
                password="secure_password",
                ssl=True,
                socket_timeout=30,
                max_connections=10,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            assert client._is_healthy is True
    
    def test_error_rate_calculation(self, redis_config, mock_redis_pool, mock_redis_instance):
        """Test error rate calculation in statistics."""
        client = RedisClient(redis_config)
        
        # Test with no operations
        stats = client.get_stats()
        assert stats['error_rate'] == 0.0
        
        # Test with operations and errors
        client._operations_count = 200
        client._error_count = 10
        
        stats = client.get_stats()
        assert stats['error_rate'] == 5.0  # 10/200 * 100
        
        # Test with only errors (edge case)
        client._operations_count = 0
        client._error_count = 5
        
        stats = client.get_stats()
        assert stats['error_rate'] == 500.0  # 5/1 * 100 (max of operations_count, 1)


if __name__ == "__main__":
    pytest.main([__file__])