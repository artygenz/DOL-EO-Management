"""
Configuration Manager for the Email Agent system.
Provides environment-specific configuration loading, validation, and hot reloading.
"""

import os
import json
import yaml
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

from .models import (
    SystemConfig, EmailAccountConfig, IMAPSettings, SMTPSettings,
    SecuritySettings, DatabaseConfig, RedisConfig, MonitoringConfig,
    Environment, EmailAccountType, SecurityLevel
)
from .validators import ConfigurationValidator
from .exceptions import (
    ConfigurationError, ValidationError, EnvironmentError, 
    SchemaError, ReloadError
)


class ConfigurationFileHandler(FileSystemEventHandler):
    """File system event handler for configuration file changes."""
    
    def __init__(self, config_manager: 'ConfigurationManager'):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
    
    def on_modified(self, event):
        """Handle configuration file modification events."""
        if not event.is_directory and event.src_path == self.config_manager.config_file_path:
            self.logger.info(f"Configuration file modified: {event.src_path}")
            try:
                self.config_manager._reload_configuration()
            except Exception as e:
                self.logger.error(f"Failed to reload configuration: {e}")


class ConfigurationManager:
    """
    Comprehensive configuration management system with validation and hot reloading.
    
    Features:
    - Environment-specific configuration loading
    - Schema validation for all configuration types
    - Hot configuration reloading without service restart
    - Thread-safe configuration access
    - Comprehensive validation with detailed error reporting
    """
    
    def __init__(self, config_file_path: Optional[str] = None, environment: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_file_path: Path to configuration file (auto-detected if None)
            environment: Target environment (auto-detected if None)
        """
        self.logger = logging.getLogger(__name__)
        self.validator = ConfigurationValidator()
        self._config_lock = threading.RLock()
        self._reload_callbacks: List[Callable[[SystemConfig], None]] = []
        
        # Determine environment
        self.environment = self._determine_environment(environment)
        
        # Determine configuration file path
        self.config_file_path = self._determine_config_file_path(config_file_path)
        
        # Initialize configuration
        self._current_config: Optional[SystemConfig] = None
        self._file_observer: Optional[Observer] = None
        
        # Load initial configuration
        self.load_configuration()
        
        # Start file watching if hot reload is enabled
        if self._current_config and self._current_config.hot_reload_enabled:
            self._start_file_watching()
    
    def load_configuration(self) -> SystemConfig:
        """
        Load configuration from file with comprehensive validation.
        
        Returns:
            Loaded and validated SystemConfig instance
            
        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        try:
            with self._config_lock:
                # Load raw configuration data
                config_data = self._load_config_file()
                
                # Validate schema
                schema_errors = self.validator.validate_config_schema(config_data)
                if schema_errors:
                    raise SchemaError(f"Configuration schema validation failed: {schema_errors}")
                
                # Parse configuration into models
                system_config = self._parse_configuration(config_data)
                
                # Validate parsed configuration
                validation_errors = self.validator.validate_system_config(system_config)
                if validation_errors:
                    raise ValidationError(f"Configuration validation failed: {validation_errors}")
                
                # Store validated configuration
                self._current_config = system_config
                
                self.logger.info(f"Configuration loaded successfully from {self.config_file_path}")
                return system_config
                
        except Exception as e:
            if isinstance(e, (ConfigurationError, ValidationError, SchemaError)):
                raise
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def get_configuration(self) -> SystemConfig:
        """
        Get current system configuration (thread-safe).
        
        Returns:
            Current SystemConfig instance
            
        Raises:
            ConfigurationError: If no configuration is loaded
        """
        with self._config_lock:
            if self._current_config is None:
                raise ConfigurationError("No configuration loaded")
            return self._current_config
    
    def get_email_account_config(self, account_id: str) -> EmailAccountConfig:
        """
        Get configuration for a specific email account.
        
        Args:
            account_id: ID of the email account
            
        Returns:
            EmailAccountConfig for the specified account
            
        Raises:
            ConfigurationError: If account not found
        """
        config = self.get_configuration()
        if account_id not in config.email_accounts:
            raise ConfigurationError(f"Email account not found: {account_id}")
        return config.email_accounts[account_id]
    
    def get_accounts_by_type(self, account_type: EmailAccountType) -> List[EmailAccountConfig]:
        """
        Get all email accounts of a specific type.
        
        Args:
            account_type: Type of email accounts to retrieve
            
        Returns:
            List of EmailAccountConfig instances
        """
        config = self.get_configuration()
        return config.get_accounts_by_type(account_type)
    
    def reload_configuration(self) -> SystemConfig:
        """
        Manually reload configuration from file.
        
        Returns:
            Newly loaded SystemConfig instance
            
        Raises:
            ReloadError: If reload fails
        """
        try:
            old_config = self._current_config
            new_config = self.load_configuration()
            
            # Notify reload callbacks
            self._notify_reload_callbacks(new_config)
            
            self.logger.info("Configuration reloaded successfully")
            return new_config
            
        except Exception as e:
            self.logger.error(f"Configuration reload failed: {e}")
            raise ReloadError(f"Failed to reload configuration: {e}")
    
    def add_reload_callback(self, callback: Callable[[SystemConfig], None]) -> None:
        """
        Add a callback to be notified when configuration is reloaded.
        
        Args:
            callback: Function to call with new configuration
        """
        with self._config_lock:
            self._reload_callbacks.append(callback)
    
    def remove_reload_callback(self, callback: Callable[[SystemConfig], None]) -> None:
        """
        Remove a reload callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        with self._config_lock:
            if callback in self._reload_callbacks:
                self._reload_callbacks.remove(callback)
    
    def validate_configuration_file(self, file_path: str) -> List[str]:
        """
        Validate a configuration file without loading it.
        
        Args:
            file_path: Path to configuration file to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            # Load and parse file
            config_data = self._load_config_file(file_path)
            
            # Validate schema
            schema_errors = self.validator.validate_config_schema(config_data)
            if schema_errors:
                return schema_errors
            
            # Parse and validate configuration
            system_config = self._parse_configuration(config_data)
            validation_errors = self.validator.validate_system_config(system_config)
            
            return validation_errors
            
        except Exception as e:
            return [f"Configuration file validation failed: {e}"]
    
    def close(self) -> None:
        """Clean up resources and stop file watching."""
        if self._file_observer:
            self._file_observer.stop()
            self._file_observer.join()
            self._file_observer = None
        
        with self._config_lock:
            self._reload_callbacks.clear()
    
    def _determine_environment(self, environment: Optional[str]) -> Environment:
        """Determine the target environment."""
        if environment:
            try:
                return Environment(environment.lower())
            except ValueError:
                raise EnvironmentError(f"Invalid environment: {environment}")
        
        # Auto-detect from environment variable
        env_var = os.getenv('EMAIL_AGENT_ENV', 'development').lower()
        try:
            return Environment(env_var)
        except ValueError:
            raise EnvironmentError(f"Invalid environment in EMAIL_AGENT_ENV: {env_var}")
    
    def _determine_config_file_path(self, config_file_path: Optional[str]) -> str:
        """Determine the configuration file path."""
        if config_file_path:
            return config_file_path
        
        # Auto-detect configuration file
        env_name = self.environment.value
        possible_paths = [
            f"config/{env_name}.yaml",
            f"config/{env_name}.yml",
            f"config/{env_name}.json",
            f"config/config.{env_name}.yaml",
            f"config/config.{env_name}.yml",
            f"config/config.{env_name}.json",
            "config/config.yaml",
            "config/config.yml",
            "config/config.json"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        raise ConfigurationError(f"No configuration file found for environment {env_name}")
    
    def _load_config_file(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration data from file."""
        path = file_path or self.config_file_path
        
        if not os.path.exists(path):
            raise ConfigurationError(f"Configuration file not found: {path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.endswith('.json'):
                    return json.load(f)
                elif path.endswith(('.yaml', '.yml')):
                    return yaml.safe_load(f) or {}
                else:
                    raise ConfigurationError(f"Unsupported configuration file format: {path}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration file {path}: {e}")
    
    def _parse_configuration(self, config_data: Dict[str, Any]) -> SystemConfig:
        """Parse configuration data into SystemConfig model."""
        try:
            # Parse environment
            environment = Environment(config_data['environment'])
            
            # Parse email accounts
            email_accounts = {}
            for account_id, account_data in config_data['email_accounts'].items():
                email_accounts[account_id] = self._parse_email_account(account_data)
            
            # Parse optional components
            database = self._parse_database_config(config_data.get('database')) if config_data.get('database') else None
            redis = self._parse_redis_config(config_data.get('redis')) if config_data.get('redis') else None
            security = self._parse_security_settings(config_data.get('security')) if config_data.get('security') else None
            monitoring = self._parse_monitoring_config(config_data.get('monitoring')) if config_data.get('monitoring') else None
            
            # Create system configuration
            return SystemConfig(
                environment=environment,
                email_accounts=email_accounts,
                database=database,
                redis=redis,
                security=security,
                monitoring=monitoring,
                hot_reload_enabled=config_data.get('hot_reload_enabled', True),
                config_file_path=self.config_file_path
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to parse configuration: {e}")
    
    def _parse_email_account(self, account_data: Dict[str, Any]) -> EmailAccountConfig:
        """Parse email account configuration."""
        imap_settings = IMAPSettings(**account_data['imap_settings'])
        smtp_settings = SMTPSettings(**account_data['smtp_settings'])
        
        return EmailAccountConfig(
            account_id=account_data['account_id'],
            account_type=EmailAccountType(account_data['account_type']),
            username=account_data['username'],
            password=account_data['password'],
            imap_settings=imap_settings,
            smtp_settings=smtp_settings,
            security_level=SecurityLevel(account_data.get('security_level', 'standard')),
            monitoring_enabled=account_data.get('monitoring_enabled', True),
            rate_limit_per_hour=account_data.get('rate_limit_per_hour', 1000),
            priority_weight=account_data.get('priority_weight', 1)
        )
    
    def _parse_database_config(self, db_data: Dict[str, Any]) -> DatabaseConfig:
        """Parse database configuration."""
        return DatabaseConfig(**db_data)
    
    def _parse_redis_config(self, redis_data: Dict[str, Any]) -> RedisConfig:
        """Parse Redis configuration."""
        return RedisConfig(**redis_data)
    
    def _parse_security_settings(self, security_data: Dict[str, Any]) -> SecuritySettings:
        """Parse security settings."""
        return SecuritySettings(**security_data)
    
    def _parse_monitoring_config(self, monitoring_data: Dict[str, Any]) -> MonitoringConfig:
        """Parse monitoring configuration."""
        return MonitoringConfig(**monitoring_data)
    
    def _start_file_watching(self) -> None:
        """Start watching configuration file for changes."""
        if self._file_observer:
            return
        
        try:
            self._file_observer = Observer()
            handler = ConfigurationFileHandler(self)
            
            # Watch the directory containing the config file
            config_dir = os.path.dirname(os.path.abspath(self.config_file_path))
            self._file_observer.schedule(handler, config_dir, recursive=False)
            self._file_observer.start()
            
            self.logger.info(f"Started watching configuration file: {self.config_file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to start configuration file watching: {e}")
    
    def _reload_configuration(self) -> None:
        """Internal method to reload configuration (called by file watcher)."""
        try:
            # Add a small delay to ensure file write is complete
            time.sleep(0.1)
            
            old_config = self._current_config
            new_config = self.load_configuration()
            
            # Notify callbacks
            self._notify_reload_callbacks(new_config)
            
            self.logger.info("Configuration automatically reloaded due to file change")
            
        except Exception as e:
            self.logger.error(f"Automatic configuration reload failed: {e}")
    
    def _notify_reload_callbacks(self, new_config: SystemConfig) -> None:
        """Notify all registered reload callbacks."""
        with self._config_lock:
            for callback in self._reload_callbacks:
                try:
                    callback(new_config)
                except Exception as e:
                    self.logger.error(f"Reload callback failed: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()