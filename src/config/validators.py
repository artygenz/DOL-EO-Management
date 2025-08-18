"""
Configuration validation utilities for the Email Agent system.
Provides comprehensive validation for all configuration types and schemas.
"""

import re
import os
import ipaddress
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from .models import (
    SystemConfig, EmailAccountConfig, IMAPSettings, SMTPSettings,
    SecuritySettings, DatabaseConfig, RedisConfig, MonitoringConfig,
    Environment, EmailAccountType, SecurityLevel
)
from .exceptions import ValidationError, SchemaError


class ConfigurationValidator:
    """Comprehensive configuration validator with schema validation."""
    
    # Email regex pattern for basic validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Domain regex pattern
    DOMAIN_PATTERN = re.compile(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Required configuration schema
    REQUIRED_SCHEMA = {
        'environment': str,
        'email_accounts': dict
    }
    
    # Optional configuration schema
    OPTIONAL_SCHEMA = {
        'database': dict,
        'redis': dict,
        'security': dict,
        'monitoring': dict,
        'hot_reload_enabled': bool
    }
    
    EMAIL_ACCOUNT_SCHEMA = {
        'account_id': str,
        'account_type': str,
        'username': str,
        'password': str,
        'imap_settings': dict,
        'smtp_settings': dict,
        'security_level': str,
        'monitoring_enabled': bool,
        'rate_limit_per_hour': int,
        'priority_weight': int
    }
    
    IMAP_SCHEMA = {
        'host': str,
        'port': int,
        'use_ssl': bool,
        'timeout': int,
        'idle_timeout': int,
        'max_connections': int,
        'connection_retry_attempts': int,
        'connection_retry_delay': int
    }
    
    SMTP_SCHEMA = {
        'host': str,
        'port': int,
        'use_ssl': bool,
        'use_tls': bool,
        'timeout': int,
        'max_connections': int,
        'retry_attempts': int,
        'retry_delay': int
    }
    
    def validate_system_config(self, config: SystemConfig) -> List[str]:
        """
        Validate complete system configuration.
        
        Args:
            config: SystemConfig instance to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            # Validate environment
            errors.extend(self._validate_environment(config.environment))
            
            # Validate email accounts
            errors.extend(self._validate_email_accounts(config.email_accounts))
            
            # Validate database config
            if config.database:
                errors.extend(self._validate_database_config(config.database))
            
            # Validate Redis config
            if config.redis:
                errors.extend(self._validate_redis_config(config.redis))
            
            # Validate security settings
            if config.security:
                errors.extend(self._validate_security_settings(config.security))
            
            # Validate monitoring config
            if config.monitoring:
                errors.extend(self._validate_monitoring_config(config.monitoring))
            
            # Validate cross-component dependencies
            errors.extend(self._validate_cross_dependencies(config))
            
        except Exception as e:
            errors.append(f"Unexpected validation error: {str(e)}")
        
        return errors
    
    def validate_config_schema(self, config_dict: Dict[str, Any]) -> List[str]:
        """
        Validate configuration dictionary against expected schema.
        
        Args:
            config_dict: Configuration dictionary to validate
            
        Returns:
            List of schema validation error messages
        """
        errors = []
        
        # Check required top-level keys
        for key, expected_type in self.REQUIRED_SCHEMA.items():
            if key not in config_dict:
                errors.append(f"Missing required configuration key: {key}")
            elif not isinstance(config_dict[key], expected_type):
                errors.append(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(config_dict[key]).__name__}")
        
        # Check optional top-level keys
        for key, expected_type in self.OPTIONAL_SCHEMA.items():
            if key in config_dict and not isinstance(config_dict[key], expected_type):
                errors.append(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(config_dict[key]).__name__}")
        
        # Validate email accounts schema
        if 'email_accounts' in config_dict:
            errors.extend(self._validate_email_accounts_schema(config_dict['email_accounts']))
        
        return errors
    
    def validate_email_address(self, email: str) -> bool:
        """Validate email address format."""
        return bool(self.EMAIL_PATTERN.match(email))
    
    def validate_domain(self, domain: str) -> bool:
        """Validate domain format."""
        # Allow localhost as a special case
        if domain == "localhost":
            return True
        return bool(self.DOMAIN_PATTERN.match(domain))
    
    def validate_ip_address(self, ip: str) -> bool:
        """Validate IP address format (IPv4 or IPv6)."""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def validate_file_path(self, path: str, must_exist: bool = False) -> bool:
        """Validate file path format and optionally existence."""
        try:
            path_obj = Path(path)
            if must_exist:
                return path_obj.exists() and path_obj.is_file()
            return True
        except (OSError, ValueError):
            return False
    
    def validate_directory_path(self, path: str, must_exist: bool = False) -> bool:
        """Validate directory path format and optionally existence."""
        try:
            path_obj = Path(path)
            if must_exist:
                return path_obj.exists() and path_obj.is_dir()
            return True
        except (OSError, ValueError):
            return False
    
    def _validate_environment(self, environment: Environment) -> List[str]:
        """Validate environment configuration."""
        errors = []
        
        if not isinstance(environment, Environment):
            errors.append(f"Invalid environment type: {type(environment)}")
        
        return errors
    
    def _validate_email_accounts(self, accounts: Dict[str, EmailAccountConfig]) -> List[str]:
        """Validate email accounts configuration."""
        errors = []
        
        if not accounts:
            errors.append("At least one email account must be configured")
            return errors
        
        account_ids = set()
        usernames = set()
        
        for account_id, account in accounts.items():
            # Check for duplicate account IDs
            if account_id in account_ids:
                errors.append(f"Duplicate account ID: {account_id}")
            account_ids.add(account_id)
            
            # Check for duplicate usernames
            if account.username in usernames:
                errors.append(f"Duplicate username: {account.username}")
            usernames.add(account.username)
            
            # Validate individual account
            errors.extend(self._validate_email_account(account))
        
        return errors
    
    def _validate_email_account(self, account: EmailAccountConfig) -> List[str]:
        """Validate individual email account configuration."""
        errors = []
        
        # Validate username as email
        if not self.validate_email_address(account.username):
            errors.append(f"Invalid email format for username: {account.username}")
        
        # Validate password strength for federal accounts
        if account.security_level == SecurityLevel.FEDERAL:
            errors.extend(self._validate_federal_password(account.password))
        
        # Validate IMAP settings
        errors.extend(self._validate_imap_settings(account.imap_settings))
        
        # Validate SMTP settings
        errors.extend(self._validate_smtp_settings(account.smtp_settings))
        
        return errors
    
    def _validate_imap_settings(self, settings: IMAPSettings) -> List[str]:
        """Validate IMAP settings."""
        errors = []
        
        # Validate host (domain, IP, or localhost)
        if not (self.validate_domain(settings.host) or self.validate_ip_address(settings.host) or settings.host == "localhost"):
            errors.append(f"Invalid IMAP host: {settings.host}")
        
        # Validate port range
        if not (1 <= settings.port <= 65535):
            errors.append(f"Invalid IMAP port: {settings.port}")
        
        # Validate timeout values
        if settings.timeout <= 0:
            errors.append("IMAP timeout must be positive")
        
        if settings.idle_timeout <= 0:
            errors.append("IMAP idle timeout must be positive")
        
        # Validate connection limits
        if settings.max_connections <= 0:
            errors.append("IMAP max connections must be positive")
        
        return errors
    
    def _validate_smtp_settings(self, settings: SMTPSettings) -> List[str]:
        """Validate SMTP settings."""
        errors = []
        
        # Validate host (domain, IP, or localhost)
        if not (self.validate_domain(settings.host) or self.validate_ip_address(settings.host) or settings.host == "localhost"):
            errors.append(f"Invalid SMTP host: {settings.host}")
        
        # Validate port range
        if not (1 <= settings.port <= 65535):
            errors.append(f"Invalid SMTP port: {settings.port}")
        
        # Validate timeout
        if settings.timeout <= 0:
            errors.append("SMTP timeout must be positive")
        
        # Validate SSL/TLS configuration
        if settings.use_ssl and settings.use_tls:
            errors.append("Cannot use both SSL and TLS simultaneously")
        
        return errors
    
    def _validate_database_config(self, config: DatabaseConfig) -> List[str]:
        """Validate database configuration."""
        errors = []
        
        # Validate host (domain, IP, or localhost)
        if not (self.validate_domain(config.host) or self.validate_ip_address(config.host) or config.host == "localhost"):
            errors.append(f"Invalid database host: {config.host}")
        
        # Validate port
        if not (1 <= config.port <= 65535):
            errors.append(f"Invalid database port: {config.port}")
        
        # Validate pool settings
        if config.pool_size <= 0:
            errors.append("Database pool size must be positive")
        
        if config.max_overflow < 0:
            errors.append("Database max overflow cannot be negative")
        
        return errors
    
    def _validate_redis_config(self, config: RedisConfig) -> List[str]:
        """Validate Redis configuration."""
        errors = []
        
        # Validate host (domain, IP, or localhost)
        if not (self.validate_domain(config.host) or self.validate_ip_address(config.host) or config.host == "localhost"):
            errors.append(f"Invalid Redis host: {config.host}")
        
        # Validate port
        if not (1 <= config.port <= 65535):
            errors.append(f"Invalid Redis port: {config.port}")
        
        # Validate database number
        if config.database < 0:
            errors.append("Redis database number cannot be negative")
        
        return errors
    
    def _validate_security_settings(self, settings: SecuritySettings) -> List[str]:
        """Validate security settings."""
        errors = []
        
        # Validate encryption key path
        if not self.validate_file_path(settings.encryption_key_path):
            errors.append(f"Invalid encryption key path: {settings.encryption_key_path}")
        
        # Validate domains
        for domain in settings.allowed_domains:
            if not self.validate_domain(domain):
                errors.append(f"Invalid allowed domain: {domain}")
        
        for domain in settings.blocked_domains:
            if not self.validate_domain(domain):
                errors.append(f"Invalid blocked domain: {domain}")
        
        # Check for domain conflicts
        allowed_set = set(settings.allowed_domains)
        blocked_set = set(settings.blocked_domains)
        conflicts = allowed_set.intersection(blocked_set)
        if conflicts:
            errors.append(f"Domains cannot be both allowed and blocked: {conflicts}")
        
        return errors
    
    def _validate_monitoring_config(self, config: MonitoringConfig) -> List[str]:
        """Validate monitoring configuration."""
        errors = []
        
        # Validate metrics port
        if config.enabled and not (1 <= config.metrics_port <= 65535):
            errors.append(f"Invalid metrics port: {config.metrics_port}")
        
        # Validate log file path
        if config.audit_logging:
            log_dir = os.path.dirname(config.log_file_path)
            if log_dir and not self.validate_directory_path(log_dir):
                errors.append(f"Invalid log file directory: {log_dir}")
        
        return errors
    
    def _validate_federal_password(self, password: str) -> List[str]:
        """Validate password meets federal security requirements."""
        errors = []
        
        if len(password) < 12:
            errors.append("Federal passwords must be at least 12 characters long")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Federal passwords must contain uppercase letters")
        
        if not re.search(r'[a-z]', password):
            errors.append("Federal passwords must contain lowercase letters")
        
        if not re.search(r'\d', password):
            errors.append("Federal passwords must contain numbers")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Federal passwords must contain special characters")
        
        return errors
    
    def _validate_cross_dependencies(self, config: SystemConfig) -> List[str]:
        """Validate cross-component dependencies."""
        errors = []
        
        # Production environment requirements
        if config.environment == Environment.PRODUCTION:
            if not config.database:
                errors.append("Production environment requires database configuration")
            
            if not config.redis:
                errors.append("Production environment requires Redis configuration")
            
            if not config.security:
                errors.append("Production environment requires security configuration")
            
            # Check for federal security level accounts
            federal_accounts = [
                acc for acc in config.email_accounts.values()
                if acc.security_level == SecurityLevel.FEDERAL
            ]
            if not federal_accounts:
                errors.append("Production environment requires at least one federal security level account")
        
        return errors
    
    def _validate_email_accounts_schema(self, accounts_dict: Dict[str, Any]) -> List[str]:
        """Validate email accounts dictionary schema."""
        errors = []
        
        if not isinstance(accounts_dict, dict):
            errors.append("Email accounts must be a dictionary")
            return errors
        
        for account_id, account_data in accounts_dict.items():
            if not isinstance(account_data, dict):
                errors.append(f"Email account {account_id} must be a dictionary")
                continue
            
            # Check required fields (only the essential ones for schema validation)
            required_fields = {
                'account_id': str,
                'account_type': str,
                'username': str,
                'password': str,
                'imap_settings': dict,
                'smtp_settings': dict
            }
            
            for field, expected_type in required_fields.items():
                if field not in account_data:
                    errors.append(f"Missing required field '{field}' in account {account_id}")
                elif not isinstance(account_data[field], expected_type):
                    errors.append(f"Invalid type for {account_id}.{field}: expected {expected_type.__name__}")
        
        return errors