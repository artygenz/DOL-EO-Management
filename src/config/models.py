"""
Configuration data models for the Email Agent system.
Defines the structure and validation for all configuration types.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import os


class Environment(Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class EmailAccountType(Enum):
    """Types of email accounts supported by the system."""
    EO_INTAKE = "eo_intake"
    PMO = "pmo"
    DEVELOPER = "developer"
    EXECUTIVE = "executive"


class SecurityLevel(Enum):
    """Security levels for email accounts."""
    STANDARD = "standard"
    ELEVATED = "elevated"
    FEDERAL = "federal"


@dataclass
class IMAPSettings:
    """IMAP server configuration settings."""
    host: str
    port: int = 993
    use_ssl: bool = True
    timeout: int = 30
    idle_timeout: int = 1740  # 29 minutes (IMAP IDLE max is 30 minutes)
    max_connections: int = 5
    connection_retry_attempts: int = 3
    connection_retry_delay: int = 5
    
    def __post_init__(self):
        """Validate IMAP settings after initialization."""
        if not self.host:
            raise ValueError("IMAP host cannot be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError("IMAP port must be between 1 and 65535")
        if self.timeout <= 0:
            raise ValueError("IMAP timeout must be positive")


@dataclass
class SMTPSettings:
    """SMTP server configuration settings."""
    host: str
    port: int = 465
    use_ssl: bool = True
    use_tls: bool = False
    timeout: int = 30
    max_connections: int = 3
    retry_attempts: int = 3
    retry_delay: int = 5
    
    def __post_init__(self):
        """Validate SMTP settings after initialization."""
        if not self.host:
            raise ValueError("SMTP host cannot be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError("SMTP port must be between 1 and 65535")
        if self.timeout <= 0:
            raise ValueError("SMTP timeout must be positive")


@dataclass
class SecuritySettings:
    """Security configuration settings."""
    encryption_key_path: str
    credential_rotation_days: int = 90
    require_sender_validation: bool = True
    enable_attachment_scanning: bool = True
    enable_content_filtering: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    max_attachment_size_mb: int = 25
    
    def __post_init__(self):
        """Validate security settings after initialization."""
        if not self.encryption_key_path:
            raise ValueError("Encryption key path cannot be empty")
        if self.credential_rotation_days <= 0:
            raise ValueError("Credential rotation days must be positive")
        if self.max_attachment_size_mb <= 0:
            raise ValueError("Max attachment size must be positive")


@dataclass
class EmailAccountConfig:
    """Configuration for a single email account."""
    account_id: str
    account_type: EmailAccountType
    username: str
    password: str  # Will be encrypted in storage
    imap_settings: IMAPSettings
    smtp_settings: SMTPSettings
    security_level: SecurityLevel = SecurityLevel.STANDARD
    monitoring_enabled: bool = True
    rate_limit_per_hour: int = 1000
    priority_weight: int = 1
    
    def __post_init__(self):
        """Validate email account configuration after initialization."""
        if not self.account_id:
            raise ValueError("Account ID cannot be empty")
        if not self.username:
            raise ValueError("Username cannot be empty")
        if not self.password:
            raise ValueError("Password cannot be empty")
        if self.rate_limit_per_hour <= 0:
            raise ValueError("Rate limit must be positive")
        if self.priority_weight <= 0:
            raise ValueError("Priority weight must be positive")


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    host: str
    port: int = 5432
    database: str = "email_agent"
    username: str = ""
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    ssl_mode: str = "require"
    
    def __post_init__(self):
        """Validate database configuration after initialization."""
        if not self.host:
            raise ValueError("Database host cannot be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError("Database port must be between 1 and 65535")
        if not self.database:
            raise ValueError("Database name cannot be empty")
        if self.pool_size <= 0:
            raise ValueError("Pool size must be positive")


@dataclass
class RedisConfig:
    """Redis configuration for caching and queues."""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    ssl: bool = False
    socket_timeout: int = 30
    connection_pool_size: int = 10
    retry_attempts: int = 3
    
    def __post_init__(self):
        """Validate Redis configuration after initialization."""
        if not self.host:
            raise ValueError("Redis host cannot be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError("Redis port must be between 1 and 65535")
        if self.database < 0:
            raise ValueError("Redis database number must be non-negative")


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration."""
    enabled: bool = True
    metrics_port: int = 8080
    health_check_interval: int = 30
    performance_monitoring: bool = True
    audit_logging: bool = True
    log_level: str = "INFO"
    log_file_path: str = "/var/log/email-agent/app.log"
    metrics_retention_days: int = 30
    
    def __post_init__(self):
        """Validate monitoring configuration after initialization."""
        if self.enabled and not (1 <= self.metrics_port <= 65535):
            raise ValueError("Metrics port must be between 1 and 65535")
        if self.health_check_interval <= 0:
            raise ValueError("Health check interval must be positive")
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("Invalid log level")


@dataclass
class SystemConfig:
    """Main system configuration containing all subsystem configs."""
    environment: Environment
    email_accounts: Dict[str, EmailAccountConfig] = field(default_factory=dict)
    database: Optional[DatabaseConfig] = None
    redis: Optional[RedisConfig] = None
    security: Optional[SecuritySettings] = None
    monitoring: Optional[MonitoringConfig] = None
    hot_reload_enabled: bool = True
    config_file_path: str = ""
    
    def __post_init__(self):
        """Validate system configuration after initialization."""
        if not self.email_accounts:
            raise ValueError("At least one email account must be configured")
        
        # Validate that we have required account types for production
        if self.environment == Environment.PRODUCTION:
            required_types = {EmailAccountType.EO_INTAKE, EmailAccountType.PMO}
            configured_types = {acc.account_type for acc in self.email_accounts.values()}
            missing_types = required_types - configured_types
            if missing_types:
                raise ValueError(f"Production environment requires account types: {missing_types}")
    
    def get_account_by_type(self, account_type: EmailAccountType) -> Optional[EmailAccountConfig]:
        """Get the first account configuration of the specified type."""
        for account in self.email_accounts.values():
            if account.account_type == account_type:
                return account
        return None
    
    def get_accounts_by_type(self, account_type: EmailAccountType) -> List[EmailAccountConfig]:
        """Get all account configurations of the specified type."""
        return [acc for acc in self.email_accounts.values() if acc.account_type == account_type]