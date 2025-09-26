"""
Centralized Client Hub

This module provides a singleton-based centralized client management system
for all external service clients used throughout the application. It handles
client initialization, connection management, and debugging for environment
variable access issues.

Key Features:
- Singleton pattern for client instances
- Centralized environment variable management
- Connection health monitoring
- Debugging and logging for client access
- Lazy initialization of clients
- Error handling and fallback mechanisms
"""

import os
import logging
import threading
from typing import Optional, Dict, Any, Union
from functools import wraps
from datetime import datetime, timedelta

# Database imports
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
import redis

# AI/ML imports
try:
    from openai import OpenAI
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Email imports
import imaplib
import smtplib
import ssl

# AWS imports
try:
    import boto3
    from botocore.exceptions import NoCredentialsError
    AWS_AVAILABLE = True
except ImportError:
    boto3 = None
    NoCredentialsError = Exception
    AWS_AVAILABLE = False

# Celery imports
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

logger = logging.getLogger(__name__)


def debug_env_access(func):
    """Decorator to log environment variable access for debugging."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Client access successful: {func.__name__} in {duration:.3f}s")
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Client access failed: {func.__name__} in {duration:.3f}s - {e}")
            raise
    return wrapper


class ClientHub:
    """
    Centralized client management hub using singleton pattern.
    
    This class manages all external service clients and provides
    a single point of access for client instances throughout the application.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ClientHub, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the client hub (only once due to singleton)."""
        if self._initialized:
            return
            
        self._initialized = True
        self._clients: Dict[str, Any] = {}
        self._client_health: Dict[str, Dict[str, Any]] = {}
        self._env_vars_cache: Dict[str, str] = {}
        
        # Initialize environment variable cache
        self._load_env_vars()
        
        logger.info("ClientHub initialized")
    
    def _load_env_vars(self):
        """Load and cache environment variables for debugging."""
        env_vars = [
            # Database
            'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB',
            'DATABASE_URL',
            
            # Redis
            'REDIS_HOST', 'REDIS_PORT', 'REDIS_URL',
            
            # OpenAI
            'OPENAI_API_KEY', 'OPENAI_MODEL',
            
            # Email
            'IMAP_HOST', 'IMAP_PORT', 'IMAP_USERNAME', 'IMAP_PASSWORD',
            'SMTP_HOST', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_PASSWORD',
            'EMAIL_USER', 'EMAIL_PASS', 'PMO_EMAIL_ADDRESS',
            
            # AWS
            'AWS_S3_BUCKET', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION',
            
            # Celery
            'CELERY_BROKER_URL', 'CELERY_RESULT_BACKEND',
            
            # Application
            'JWT_SECRET', 'JWT_ALG', 'APP_LOG_DIR', 'LOG_LEVEL'
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive values for logging
                if any(sensitive in var.upper() for sensitive in ['PASSWORD', 'SECRET', 'KEY']):
                    self._env_vars_cache[var] = f"***{value[-4:]}" if len(value) > 4 else "***"
                else:
                    self._env_vars_cache[var] = value
            else:
                self._env_vars_cache[var] = None
    
    def get_env_var(self, var_name: str, default: str = None) -> Optional[str]:
        """Get environment variable with debugging."""
        value = os.getenv(var_name, default)
        if value is None:
            logger.warning(f"Environment variable {var_name} not found")
        else:
            logger.debug(f"Environment variable {var_name} accessed")
        return value
    
    def get_env_status(self) -> Dict[str, Any]:
        """Get status of all environment variables."""
        return {
            'cached_vars': self._env_vars_cache,
            'timestamp': datetime.now().isoformat()
        }
    
    @debug_env_access
    def get_database_engine(self) -> Engine:
        """Get PostgreSQL database engine."""
        if 'db_engine' not in self._clients:
            try:
                # Try DATABASE_URL first
                database_url = self.get_env_var('DATABASE_URL')
                if not database_url:
                    # Build from individual components
                    host = self.get_env_var('POSTGRES_HOST', 'db')
                    port = self.get_env_var('POSTGRES_PORT', '5432')
                    user = self.get_env_var('POSTGRES_USER', 'dol_user')
                    password = self.get_env_var('POSTGRES_PASSWORD', 'artygenz')
                    db = self.get_env_var('POSTGRES_DB', 'dol_db')
                    database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
                
                self._clients['db_engine'] = create_engine(
                    database_url,
                    pool_pre_ping=True,
                    future=True
                )
                self._update_client_health('db_engine', True, "Connected successfully")
                logger.info("Database engine initialized")
                
            except Exception as e:
                self._update_client_health('db_engine', False, str(e))
                logger.error(f"Failed to initialize database engine: {e}")
                raise
        
        return self._clients['db_engine']
    
    @debug_env_access
    def get_database_session_maker(self) -> sessionmaker:
        """Get database session maker."""
        if 'db_session_maker' not in self._clients:
            engine = self.get_database_engine()
            self._clients['db_session_maker'] = sessionmaker(
                bind=engine, 
                autoflush=False, 
                autocommit=False, 
                future=True
            )
            logger.info("Database session maker initialized")
        
        return self._clients['db_session_maker']
    
    @debug_env_access
    def get_redis_client(self) -> redis.Redis:
        """Get Redis client."""
        if 'redis_client' not in self._clients:
            try:
                # Try REDIS_URL first
                redis_url = self.get_env_var('REDIS_URL')
                if not redis_url:
                    # Build from individual components
                    host = self.get_env_var('REDIS_HOST', 'redis')
                    port = self.get_env_var('REDIS_PORT', '6379')
                    redis_url = f"redis://{host}:{port}/0"
                
                self._clients['redis_client'] = redis.from_url(redis_url)
                
                # Test connection
                self._clients['redis_client'].ping()
                self._update_client_health('redis_client', True, "Connected successfully")
                logger.info("Redis client initialized")
                
            except Exception as e:
                self._update_client_health('redis_client', False, str(e))
                logger.error(f"Failed to initialize Redis client: {e}")
                raise
        
        return self._clients['redis_client']
    
    @debug_env_access
    def get_openai_client(self) -> Optional[OpenAI]:
        """Get OpenAI client."""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not available")
            return None
            
        if 'openai_client' not in self._clients:
            try:
                api_key = self.get_env_var('OPENAI_API_KEY')
                if not api_key:
                    logger.warning("OPENAI_API_KEY not found")
                    return None
                
                self._clients['openai_client'] = OpenAI(api_key=api_key)
                self._update_client_health('openai_client', True, "Connected successfully")
                logger.info("OpenAI client initialized")
                
            except Exception as e:
                self._update_client_health('openai_client', False, str(e))
                logger.error(f"Failed to initialize OpenAI client: {e}")
                return None
        
        return self._clients['openai_client']
    
    @debug_env_access
    def get_langchain_client(self) -> Optional[ChatOpenAI]:
        """Get LangChain OpenAI client."""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not available for LangChain")
            return None
            
        if 'langchain_client' not in self._clients:
            try:
                api_key = self.get_env_var('OPENAI_API_KEY')
                model = self.get_env_var('OPENAI_MODEL', 'gpt-4.1')
                
                if not api_key:
                    logger.warning("OPENAI_API_KEY not found for LangChain")
                    return None
                
                self._clients['langchain_client'] = ChatOpenAI(
                    model=model,
                    openai_api_key=api_key,
                    temperature=0
                )
                self._update_client_health('langchain_client', True, "Connected successfully")
                logger.info("LangChain client initialized")
                
            except Exception as e:
                self._update_client_health('langchain_client', False, str(e))
                logger.error(f"Failed to initialize LangChain client: {e}")
                return None
        
        return self._clients['langchain_client']
    
    @debug_env_access
    def get_imap_client(self) -> Optional[imaplib.IMAP4_SSL]:
        """Get IMAP client for email monitoring."""
        if 'imap_client' not in self._clients:
            try:
                host = self.get_env_var('IMAP_HOST', 'lumenlighthouse.ai')
                port = int(self.get_env_var('IMAP_PORT', '993'))
                username = self.get_env_var('IMAP_USERNAME')
                password = self.get_env_var('IMAP_PASSWORD')
                
                if not username or not password:
                    logger.warning("IMAP credentials not found")
                    return None
                
                self._clients['imap_client'] = imaplib.IMAP4_SSL(host, port)
                self._clients['imap_client'].login(username, password)
                self._update_client_health('imap_client', True, "Connected successfully")
                logger.info("IMAP client initialized")
                
            except Exception as e:
                self._update_client_health('imap_client', False, str(e))
                logger.error(f"Failed to initialize IMAP client: {e}")
                return None
        
        return self._clients['imap_client']
    
    @debug_env_access
    def get_smtp_client(self) -> Optional[smtplib.SMTP]:
        """Get SMTP client for sending emails (cached instance)."""
        if 'smtp_client' not in self._clients:
            try:
                host = self.get_env_var('SMTP_HOST', 'lumenlighthouse.ai')
                port = int(self.get_env_var('SMTP_PORT', '587'))
                username = self.get_env_var('EMAIL_USER') or self.get_env_var('SMTP_USERNAME')
                password = self.get_env_var('EMAIL_PASS') or self.get_env_var('SMTP_PASSWORD')
                
                if not username or not password:
                    logger.warning("SMTP credentials not found")
                    return None
                
                self._clients['smtp_client'] = smtplib.SMTP(host, port)
                self._clients['smtp_client'].starttls()
                self._clients['smtp_client'].login(username, password)
                self._update_client_health('smtp_client', True, "Connected successfully")
                logger.info("SMTP client initialized")
                
            except Exception as e:
                self._update_client_health('smtp_client', False, str(e))
                logger.error(f"Failed to initialize SMTP client: {e}")
                return None
        
        return self._clients['smtp_client']
    
    @debug_env_access
    def create_smtp_connection(self) -> Optional[smtplib.SMTP]:
        """Create a fresh SMTP connection for email sending."""
        try:
            host = self.get_env_var('SMTP_HOST', 'lumenlighthouse.ai')
            port = int(self.get_env_var('SMTP_PORT', '587'))
            username = self.get_env_var('EMAIL_USER') or self.get_env_var('SMTP_USERNAME')
            password = self.get_env_var('EMAIL_PASS') or self.get_env_var('SMTP_PASSWORD')
            
            if not username or not password:
                logger.warning("SMTP credentials not found")
                return None
            
            # Create fresh connection
            smtp = smtplib.SMTP(host, port, timeout=30)
            smtp.starttls()
            smtp.login(username, password)
            logger.debug("Fresh SMTP connection created")
            return smtp
            
        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {e}")
            return None
    
    @debug_env_access
    def get_s3_client(self) -> Optional[Any]:
        """Get AWS S3 client."""
        if not AWS_AVAILABLE:
            logger.warning("AWS boto3 library not available")
            return None
            
        if 's3_client' not in self._clients:
            try:
                access_key = self.get_env_var('AWS_ACCESS_KEY_ID')
                secret_key = self.get_env_var('AWS_SECRET_ACCESS_KEY')
                region = self.get_env_var('AWS_REGION', 'us-east-1')
                
                if not access_key or not secret_key:
                    logger.warning("AWS credentials not found")
                    return None
                
                self._clients['s3_client'] = boto3.client(
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )
                self._update_client_health('s3_client', True, "Connected successfully")
                logger.info("S3 client initialized")
                
            except Exception as e:
                self._update_client_health('s3_client', False, str(e))
                logger.error(f"Failed to initialize S3 client: {e}")
                return None
        
        return self._clients['s3_client']
    
    @debug_env_access
    def get_celery_app(self) -> Optional[Celery]:
        """Get Celery application."""
        if not CELERY_AVAILABLE:
            logger.warning("Celery library not available")
            return None
            
        if 'celery_app' not in self._clients:
            try:
                broker_url = self.get_env_var('CELERY_BROKER_URL')
                result_backend = self.get_env_var('CELERY_RESULT_BACKEND')
                
                if not broker_url:
                    # Build from Redis URL
                    redis_url = self.get_env_var('REDIS_URL')
                    if not redis_url:
                        host = self.get_env_var('REDIS_HOST', 'redis')
                        port = self.get_env_var('REDIS_PORT', '6379')
                        redis_url = f"redis://{host}:{port}/0"
                    broker_url = redis_url
                
                if not result_backend:
                    result_backend = broker_url
                
                self._clients['celery_app'] = Celery(
                    "dol_eo_workflow",
                    broker=broker_url,
                    backend=result_backend
                )
                self._update_client_health('celery_app', True, "Initialized successfully")
                logger.info("Celery app initialized")
                
            except Exception as e:
                self._update_client_health('celery_app', False, str(e))
                logger.error(f"Failed to initialize Celery app: {e}")
                return None
        
        return self._clients['celery_app']
    
    def _update_client_health(self, client_name: str, is_healthy: bool, message: str):
        """Update client health status."""
        self._client_health[client_name] = {
            'is_healthy': is_healthy,
            'message': message,
            'last_check': datetime.now().isoformat(),
            'error_count': self._client_health.get(client_name, {}).get('error_count', 0) + (0 if is_healthy else 1)
        }
    
    def get_client_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all clients."""
        return self._client_health.copy()
    
    def get_all_clients(self) -> Dict[str, Any]:
        """Get all initialized clients."""
        return self._clients.copy()
    
    def reset_client(self, client_name: str):
        """Reset a specific client."""
        if client_name in self._clients:
            del self._clients[client_name]
        if client_name in self._client_health:
            del self._client_health[client_name]
        logger.info(f"Client {client_name} reset")
    
    def reset_all_clients(self):
        """Reset all clients."""
        self._clients.clear()
        self._client_health.clear()
        logger.info("All clients reset")
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get comprehensive client information for debugging."""
        return {
            'clients_initialized': list(self._clients.keys()),
            'client_health': self.get_client_health(),
            'environment_status': self.get_env_status(),
            'timestamp': datetime.now().isoformat()
        }


# Global client hub instance
_client_hub: Optional[ClientHub] = None
_hub_lock = threading.Lock()


def get_client_hub() -> ClientHub:
    """Get the global client hub instance."""
    global _client_hub
    if _client_hub is None:
        with _hub_lock:
            if _client_hub is None:
                _client_hub = ClientHub()
    return _client_hub


# Convenience functions for easy access
def get_database_engine() -> Engine:
    """Get database engine."""
    return get_client_hub().get_database_engine()


def get_database_session_maker() -> sessionmaker:
    """Get database session maker."""
    return get_client_hub().get_database_session_maker()


def get_redis_client() -> redis.Redis:
    """Get Redis client."""
    return get_client_hub().get_redis_client()


def get_openai_client() -> Optional[OpenAI]:
    """Get OpenAI client."""
    return get_client_hub().get_openai_client()


def get_langchain_client() -> Optional[ChatOpenAI]:
    """Get LangChain client."""
    return get_client_hub().get_langchain_client()


def get_imap_client() -> Optional[imaplib.IMAP4_SSL]:
    """Get IMAP client."""
    return get_client_hub().get_imap_client()


def get_smtp_client() -> Optional[smtplib.SMTP]:
    """Get SMTP client."""
    return get_client_hub().get_smtp_client()


def create_smtp_connection() -> Optional[smtplib.SMTP]:
    """Create a fresh SMTP connection for email sending."""
    return get_client_hub().create_smtp_connection()


def get_s3_client() -> Optional[Any]:
    """Get S3 client."""
    return get_client_hub().get_s3_client()


def get_celery_app() -> Optional[Celery]:
    """Get Celery app."""
    return get_client_hub().get_celery_app()


def get_client_health() -> Dict[str, Dict[str, Any]]:
    """Get client health status."""
    return get_client_hub().get_client_health()


def get_client_info() -> Dict[str, Any]:
    """Get comprehensive client information."""
    return get_client_hub().get_client_info()
