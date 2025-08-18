# Enhanced Configuration Management System

The Enhanced Configuration Management System provides comprehensive, federal-grade configuration management for the Email Agent system. It supports environment-specific configurations, hot reloading, comprehensive validation, and secure credential management.

## Features

### Core Features
- **Environment-specific configuration loading** - Automatic detection and loading of development, staging, and production configurations
- **Schema validation** - Comprehensive validation of all configuration types with detailed error reporting
- **Hot configuration reloading** - Reload configuration without service restart (configurable)
- **Thread-safe configuration access** - Safe concurrent access to configuration data
- **Federal-grade security validation** - Password strength validation and security controls for government compliance

### Configuration Types
- **Email Account Configuration** - IMAP/SMTP settings, security levels, rate limits
- **Database Configuration** - PostgreSQL connection settings with pooling
- **Redis Configuration** - Cache and queue configuration
- **Security Settings** - Encryption, domain validation, attachment scanning
- **Monitoring Configuration** - Logging, metrics, health checks

## Quick Start

### Basic Usage

```python
from src.config import ConfigurationManager
from src.config.models import EmailAccountType

# Initialize configuration manager (auto-detects environment)
config_manager = ConfigurationManager()

# Get system configuration
config = config_manager.get_configuration()

# Access email accounts
eo_accounts = config_manager.get_accounts_by_type(EmailAccountType.EO_INTAKE)
specific_account = config_manager.get_email_account_config('eo_intake_account')

# Clean up
config_manager.close()
```

### Environment Configuration

Set the environment using the `EMAIL_AGENT_ENV` environment variable:

```bash
export EMAIL_AGENT_ENV=development  # or staging, production
```

Or specify explicitly:

```python
config_manager = ConfigurationManager(environment='production')
```

## Configuration Files

Configuration files are automatically detected in the following order:

1. `config/{environment}.yaml`
2. `config/{environment}.yml`
3. `config/{environment}.json`
4. `config/config.{environment}.yaml`
5. `config/config.{environment}.yml`
6. `config/config.{environment}.json`
7. `config/config.yaml`
8. `config/config.yml`
9. `config/config.json`

### Configuration File Structure

```yaml
# Environment specification
environment: development

# Email account configurations
email_accounts:
  eo_intake_account:
    account_id: "eo_intake_account"
    account_type: "eo_intake"  # eo_intake, pmo, developer, executive
    username: "eo-intake@example.com"
    password: "SecurePassword123!"
    imap_settings:
      host: "imap.secureserver.net"
      port: 993
      use_ssl: true
      timeout: 30
      idle_timeout: 1740
      max_connections: 5
      connection_retry_attempts: 3
      connection_retry_delay: 5
    smtp_settings:
      host: "smtpout.secureserver.net"
      port: 465
      use_ssl: true
      use_tls: false
      timeout: 30
      max_connections: 3
      retry_attempts: 3
      retry_delay: 5
    security_level: "standard"  # standard, elevated, federal
    monitoring_enabled: true
    rate_limit_per_hour: 1000
    priority_weight: 1

# Database configuration (optional)
database:
  host: "localhost"
  port: 5432
  database: "email_agent"
  username: "db_user"
  password: "db_password"
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  pool_recycle: 3600
  ssl_mode: "require"

# Redis configuration (optional)
redis:
  host: "localhost"
  port: 6379
  database: 0
  password: null
  ssl: false
  socket_timeout: 30
  connection_pool_size: 10
  retry_attempts: 3

# Security settings (optional)
security:
  encryption_key_path: "/path/to/encryption.key"
  credential_rotation_days: 90
  require_sender_validation: true
  enable_attachment_scanning: true
  enable_content_filtering: true
  allowed_domains:
    - "example.com"
    - "agency.gov"
  blocked_domains:
    - "spam.com"
  max_attachment_size_mb: 25

# Monitoring configuration (optional)
monitoring:
  enabled: true
  metrics_port: 8080
  health_check_interval: 30
  performance_monitoring: true
  audit_logging: true
  log_level: "INFO"
  log_file_path: "/var/log/email-agent/app.log"
  metrics_retention_days: 30

# Hot reload configuration
hot_reload_enabled: true
```

## Configuration Models

### EmailAccountConfig

Represents a single email account configuration:

```python
@dataclass
class EmailAccountConfig:
    account_id: str
    account_type: EmailAccountType  # EO_INTAKE, PMO, DEVELOPER, EXECUTIVE
    username: str
    password: str
    imap_settings: IMAPSettings
    smtp_settings: SMTPSettings
    security_level: SecurityLevel = SecurityLevel.STANDARD
    monitoring_enabled: bool = True
    rate_limit_per_hour: int = 1000
    priority_weight: int = 1
```

### IMAPSettings

IMAP server configuration:

```python
@dataclass
class IMAPSettings:
    host: str
    port: int = 993
    use_ssl: bool = True
    timeout: int = 30
    idle_timeout: int = 1740  # 29 minutes
    max_connections: int = 5
    connection_retry_attempts: int = 3
    connection_retry_delay: int = 5
```

### SMTPSettings

SMTP server configuration:

```python
@dataclass
class SMTPSettings:
    host: str
    port: int = 465
    use_ssl: bool = True
    use_tls: bool = False
    timeout: int = 30
    max_connections: int = 3
    retry_attempts: int = 3
    retry_delay: int = 5
```

## Validation

The system provides comprehensive validation at multiple levels:

### Schema Validation
- Validates configuration file structure
- Checks required fields and data types
- Validates email account schemas

### Model Validation
- Validates individual configuration models
- Enforces business rules and constraints
- Validates cross-component dependencies

### Security Validation
- Federal password requirements for production
- Domain and IP address validation
- Security level enforcement

### Example Validation

```python
# Validate a configuration file
errors = config_manager.validate_configuration_file('config/production.yaml')
if errors:
    for error in errors:
        print(f"Validation error: {error}")
```

## Hot Reloading

The configuration system supports hot reloading without service restart:

```python
# Enable hot reloading (default: true)
config_manager = ConfigurationManager()

# Add reload callback
def on_config_reload(new_config):
    print(f"Configuration reloaded: {new_config.environment}")

config_manager.add_reload_callback(on_config_reload)

# Manual reload
new_config = config_manager.reload_configuration()
```

## Security Features

### Federal-Grade Password Validation

For production environments with federal security level accounts:

- Minimum 12 characters
- Must contain uppercase letters
- Must contain lowercase letters
- Must contain numbers
- Must contain special characters

### Credential Security

- AES-256 encryption support for stored credentials
- Automatic credential rotation capabilities
- Secure key derivation functions

### Domain Validation

- Government domain whitelist support
- Blocked domain enforcement
- Email address format validation

## Environment-Specific Features

### Development Environment
- Relaxed validation rules
- Hot reloading enabled by default
- Debug logging enabled
- Local database/Redis connections

### Staging Environment
- Moderate validation rules
- Hot reloading configurable
- Standard logging
- Staging infrastructure connections

### Production Environment
- Strict validation rules
- Hot reloading disabled by default
- Audit logging required
- Federal security requirements enforced
- Required account types: EO_INTAKE, PMO
- At least one federal security level account required

## Error Handling

The system provides detailed error messages for common issues:

```python
from src.config.exceptions import (
    ConfigurationError,
    ValidationError,
    EnvironmentError,
    SchemaError,
    ReloadError
)

try:
    config_manager = ConfigurationManager()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except ValidationError as e:
    print(f"Validation error: {e}")
except EnvironmentError as e:
    print(f"Environment error: {e}")
```

## Integration Examples

### With Existing Email Client

```python
from src.config import ConfigurationManager
from src.config.models import EmailAccountType

# Get configuration
config_manager = ConfigurationManager()
eo_accounts = config_manager.get_accounts_by_type(EmailAccountType.EO_INTAKE)
account_config = eo_accounts[0]

# Use with existing email client
class EnhancedEmailClient:
    def __init__(self, account_config):
        self.imap_host = account_config.imap_settings.host
        self.imap_port = account_config.imap_settings.port
        self.username = account_config.username
        self.password = account_config.password
        # ... rest of initialization
```

### With Database Connections

```python
# Get database configuration
config = config_manager.get_configuration()
if config.database:
    db_url = f"postgresql://{config.database.username}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.database}"
    # Use with SQLAlchemy, psycopg2, etc.
```

## Testing

The configuration system includes comprehensive unit tests:

```bash
# Run all configuration tests
python -m pytest tests/config/ -v

# Run specific test categories
python -m pytest tests/config/test_models.py -v
python -m pytest tests/config/test_validators.py -v
python -m pytest tests/config/test_manager.py -v
```

## Best Practices

### Configuration Management
1. Use environment-specific configuration files
2. Keep sensitive data in environment variables or encrypted storage
3. Validate configurations before deployment
4. Use hot reloading carefully in production

### Security
1. Use federal security level for production government accounts
2. Rotate credentials regularly
3. Validate all domains and email addresses
4. Enable attachment scanning in production

### Performance
1. Use connection pooling for databases
2. Configure appropriate timeouts
3. Monitor configuration reload frequency
4. Use caching for frequently accessed configurations

### Monitoring
1. Enable audit logging in production
2. Monitor configuration validation errors
3. Set up alerts for configuration reload failures
4. Track configuration access patterns

## Troubleshooting

### Common Issues

**Configuration file not found**
```
ConfigurationError: No configuration file found for environment development
```
Solution: Create a configuration file in the `config/` directory with the appropriate name.

**Validation errors**
```
ValidationError: Configuration validation failed: ['Invalid email format for username: invalid-email']
```
Solution: Check the validation error messages and fix the configuration accordingly.

**Environment detection issues**
```
EnvironmentError: Invalid environment: invalid_env
```
Solution: Use valid environment values: `development`, `staging`, or `production`.

### Debug Mode

Enable debug logging to troubleshoot configuration issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

config_manager = ConfigurationManager()
```

## Contributing

When adding new configuration options:

1. Add the field to the appropriate model in `models.py`
2. Add validation logic in `validators.py`
3. Update the configuration parsing in `manager.py`
4. Add comprehensive unit tests
5. Update this documentation

## License

This configuration management system is part of the Email Agent project and follows the same licensing terms.