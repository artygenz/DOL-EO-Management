# Email Client Automatic Reconnection System

This document describes the intelligent reconnection system implemented for the Enhanced GoDaddy Email Client, providing automatic connection recovery with exponential backoff, fallback mechanisms, and connection state persistence.

## Overview

The reconnection system consists of two main components:

1. **IntelligentReconnectionManager** - Core reconnection logic with state management
2. **EnhancedGoDaddyEmailClient** - High-level client with integrated reconnection capabilities

## Key Features

### 🔄 Intelligent Reconnection Logic
- **Exponential Backoff**: Automatically increases retry delays to prevent server overload
- **Jitter**: Adds randomization to prevent thundering herd problems
- **Connection Failure Detection**: Automatically detects and classifies different failure types
- **Automatic Recovery**: Seamlessly recovers from temporary network issues

### 🛡️ Fallback Mechanisms
- **Multiple Fallback Servers**: Configure backup servers for persistent failures
- **Automatic Failover**: Switches to fallback servers when primary fails
- **Health Validation**: Tests fallback servers before switching
- **Configuration Persistence**: Maintains fallback settings across restarts

### 📊 Connection State Persistence
- **State Recovery**: Recovers connection state after application restarts
- **Failure History**: Maintains history of connection failures for analysis
- **Metrics Tracking**: Tracks connection performance and reliability metrics
- **JSON Serialization**: Stores state in human-readable JSON format

### 🔍 Comprehensive Monitoring
- **Real-time Health Checks**: Continuously monitors connection health
- **Performance Metrics**: Tracks response times, uptime, and error rates
- **Connection Callbacks**: Provides hooks for custom monitoring and alerting
- **Diagnostic Tools**: Built-in connection testing and troubleshooting

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Enhanced GoDaddy Email Client                │
├─────────────────────────────────────────────────────────────┤
│  • Email Operations (fetch, send, list)                    │
│  • Operation Retry Logic                                   │
│  • Connection Health Monitoring                            │
│  • Configuration Management                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│            Intelligent Reconnection Manager                │
├─────────────────────────────────────────────────────────────┤
│  • Connection State Management                              │
│  • Exponential Backoff Calculation                         │
│  • Failure Classification and Tracking                     │
│  • Fallback Server Management                              │
│  • State Persistence and Recovery                          │
│  • Health Check Monitoring                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 GoDaddy Email Client                       │
├─────────────────────────────────────────────────────────────┤
│  • IMAP/SMTP Connection Management                         │
│  • Server Capability Detection                             │
│  • Rate Limiting Handling                                  │
│  • Email Protocol Operations                               │
└─────────────────────────────────────────────────────────────┘
```

## Usage Examples

### Basic Usage with Auto-Reconnection

```python
from src.email.enhanced_godaddy_client import EnhancedGoDaddyEmailClient
from src.email.reconnection_manager import ReconnectionConfig

# Configure account settings
account_config = {
    'imap_host': 'imap.secureserver.net',
    'imap_port': 993,
    'smtp_host': 'smtpout.secureserver.net',
    'smtp_port': 465,
    'username': 'your-email@domain.com',
    'password': 'your-password'
}

# Configure reconnection behavior
reconnection_config = ReconnectionConfig(
    initial_backoff=1.0,      # Start with 1 second delay
    max_backoff=300.0,        # Maximum 5 minute delay
    backoff_multiplier=2.0,   # Double delay each retry
    jitter_factor=0.1,        # Add 10% randomization
    max_retry_attempts=10,    # Try up to 10 times
    health_check_interval=30.0 # Check health every 30 seconds
)

# Create enhanced client with auto-reconnection
with EnhancedGoDaddyEmailClient(
    account_config=account_config,
    reconnection_config=reconnection_config,
    auto_reconnect=True
) as client:
    
    # Email operations automatically handle reconnection
    emails = client.fetch_unread_emails()
    client.send_email("recipient@domain.com", "Subject", "Body")
```

### Advanced Configuration with Fallback Servers

```python
from src.email.reconnection_manager import FallbackMechanism

# Configure fallback servers
fallback_config = FallbackMechanism(
    enabled=True,
    fallback_servers=[
        {
            'imap_host': 'backup1.secureserver.net',
            'smtp_host': 'backup1.secureserver.net'
        },
        {
            'imap_host': 'backup2.secureserver.net',
            'smtp_host': 'backup2.secureserver.net'
        }
    ],
    fallback_timeout=60.0,    # Wait 1 minute before trying fallback
    max_fallback_attempts=2   # Try up to 2 fallback servers
)

# Create client with fallback support
client = EnhancedGoDaddyEmailClient(
    account_config=account_config,
    reconnection_config=reconnection_config,
    fallback_config=fallback_config
)
```

### Connection Monitoring and Callbacks

```python
def on_connection_change(state, error):
    print(f"Connection state changed to: {state.value}")
    if error:
        print(f"Error: {error}")

def on_connection_failure(failure):
    print(f"Connection failed: {failure.failure_type.value}")
    print(f"Error: {failure.error_message}")
    print(f"Retry count: {failure.retry_count}")

# Add monitoring callbacks
client.add_connection_callback(on_connection_change)
client.add_failure_callback(on_connection_failure)

# Monitor connection health
health = client.get_connection_health()
if health:
    print(f"Response time: {health.response_time_ms}ms")
    print(f"Uptime: {health.uptime_percentage}%")
```

### Connection Metrics and Diagnostics

```python
# Get connection performance metrics
metrics = client.get_connection_metrics()
print(f"Total connections: {metrics.total_connections}")
print(f"Successful: {metrics.successful_connections}")
print(f"Failed: {metrics.failed_connections}")
print(f"Uptime: {metrics.uptime_percentage}%")

# Get failure history
failures = client.get_failure_history()
for failure in failures:
    print(f"Failure: {failure.failure_type.value} at {failure.timestamp}")

# Perform comprehensive connection test
test_results = client.perform_connection_test()
print(f"Connection test results: {test_results}")
```

### State Persistence and Recovery

```python
# Configure state persistence
reconnection_config = ReconnectionConfig(
    state_persistence_path="email_connection_state.json",
    # ... other config
)

# State is automatically saved and loaded
client = EnhancedGoDaddyEmailClient(
    account_config=account_config,
    reconnection_config=reconnection_config
)

# Connection state, metrics, and failure history are preserved
# across application restarts
```

## Configuration Reference

### ReconnectionConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `initial_backoff` | float | 1.0 | Initial backoff delay in seconds |
| `max_backoff` | float | 300.0 | Maximum backoff delay in seconds |
| `backoff_multiplier` | float | 2.0 | Exponential backoff multiplier |
| `jitter_factor` | float | 0.1 | Jitter randomization factor (0.0-1.0) |
| `max_retry_attempts` | int | 10 | Maximum retry attempts before giving up |
| `persistent_failure_threshold` | int | 5 | Failures before marking as persistent |
| `health_check_interval` | float | 30.0 | Health check interval in seconds |
| `state_persistence_path` | str | "connection_state.json" | Path for state file |

### FallbackMechanism

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | True | Enable fallback mechanisms |
| `fallback_servers` | List[Dict] | [] | List of fallback server configurations |
| `fallback_timeout` | float | 60.0 | Timeout before trying fallback |
| `max_fallback_attempts` | int | 3 | Maximum fallback servers to try |
| `fallback_health_check` | bool | True | Test fallback server health |

## Connection States

The system tracks the following connection states:

- **CONNECTED** - Successfully connected and operational
- **DISCONNECTED** - Not connected (initial state)
- **RECONNECTING** - Attempting to reconnect
- **FAILED** - Connection failed, will retry
- **SUSPENDED** - Maximum retries reached, manual intervention needed

## Failure Types

The system classifies failures into the following types:

- **NETWORK_ERROR** - Network connectivity issues
- **AUTHENTICATION_ERROR** - Login/credential problems
- **TIMEOUT_ERROR** - Connection or operation timeouts
- **RATE_LIMIT_ERROR** - Server rate limiting
- **SERVER_ERROR** - Server-side errors (5xx responses)
- **UNKNOWN_ERROR** - Unclassified errors

## Best Practices

### 1. Configure Appropriate Backoff Settings
```python
# For production environments
reconnection_config = ReconnectionConfig(
    initial_backoff=2.0,      # Start with 2 seconds
    max_backoff=600.0,        # Maximum 10 minutes
    backoff_multiplier=1.5,   # Moderate exponential growth
    jitter_factor=0.2,        # 20% jitter for load distribution
    max_retry_attempts=15     # Allow more retries in production
)
```

### 2. Set Up Comprehensive Monitoring
```python
def setup_monitoring(client):
    def log_connection_changes(state, error):
        logger.info(f"Connection state: {state.value}")
        if error:
            logger.error(f"Connection error: {error}")
    
    def log_failures(failure):
        logger.warning(f"Connection failure: {failure.failure_type.value}")
        if failure.is_persistent:
            logger.critical("Persistent connection failure detected!")
    
    client.add_connection_callback(log_connection_changes)
    client.add_failure_callback(log_failures)
```

### 3. Configure Fallback Servers
```python
# Use geographically distributed fallback servers
fallback_config = FallbackMechanism(
    enabled=True,
    fallback_servers=[
        {'imap_host': 'us-east.backup.com', 'smtp_host': 'us-east.backup.com'},
        {'imap_host': 'us-west.backup.com', 'smtp_host': 'us-west.backup.com'},
        {'imap_host': 'eu.backup.com', 'smtp_host': 'eu.backup.com'}
    ],
    fallback_timeout=30.0,
    max_fallback_attempts=2
)
```

### 4. Handle Connection State Changes
```python
def handle_connection_state(client):
    state = client.get_connection_state()
    
    if state == ConnectionState.CONNECTED:
        # Normal operations
        return client.fetch_unread_emails()
    
    elif state == ConnectionState.RECONNECTING:
        # Wait for reconnection
        if client.wait_for_connection(timeout=30.0):
            return client.fetch_unread_emails()
        else:
            raise Exception("Reconnection timeout")
    
    elif state == ConnectionState.SUSPENDED:
        # Manual intervention needed
        logger.critical("Connection suspended, manual recovery required")
        client.force_reconnect()
    
    else:
        # Other states - wait or retry
        time.sleep(1.0)
        return handle_connection_state(client)
```

### 5. Regular Health Monitoring
```python
def monitor_connection_health(client):
    """Regular health monitoring routine"""
    test_results = client.perform_connection_test()
    
    if not test_results['is_healthy']:
        logger.warning("Connection health degraded")
        
        # Get detailed metrics
        metrics = client.get_connection_metrics()
        if metrics.uptime_percentage < 95.0:
            logger.error(f"Low uptime: {metrics.uptime_percentage}%")
        
        # Check recent failures
        failures = client.get_failure_history()
        recent_failures = [f for f in failures 
                          if (datetime.now() - f.timestamp).total_seconds() < 3600]
        
        if len(recent_failures) > 5:
            logger.error(f"High failure rate: {len(recent_failures)} in last hour")
```

## Troubleshooting

### Common Issues and Solutions

1. **High Connection Failure Rate**
   - Check network connectivity
   - Verify server credentials
   - Review server rate limits
   - Consider adjusting backoff settings

2. **Persistent Connection Failures**
   - Verify server configuration
   - Check firewall settings
   - Test with fallback servers
   - Review authentication settings

3. **Slow Reconnection**
   - Reduce initial backoff time
   - Lower backoff multiplier
   - Increase health check frequency
   - Optimize network configuration

4. **State Persistence Issues**
   - Check file permissions
   - Verify disk space
   - Review state file path
   - Check JSON serialization

### Debugging Tools

```python
# Enable debug logging
import logging
logging.getLogger('src.email.reconnection_manager').setLevel(logging.DEBUG)
logging.getLogger('src.email.enhanced_godaddy_client').setLevel(logging.DEBUG)

# Perform connection diagnostics
test_results = client.perform_connection_test()
print(json.dumps(test_results, indent=2, default=str))

# Review failure history
failures = client.get_failure_history()
for failure in failures:
    print(f"{failure.timestamp}: {failure.failure_type.value} - {failure.error_message}")

# Check connection metrics
metrics = client.get_connection_metrics()
print(f"Success rate: {metrics.successful_connections / max(1, metrics.total_connections) * 100:.1f}%")
```

## Performance Considerations

### Memory Usage
- Failure history is limited to last 10 entries by default
- State persistence uses JSON format for efficiency
- Connection objects are properly cleaned up

### Network Efficiency
- Exponential backoff prevents server overload
- Jitter reduces synchronized retry attempts
- Health checks use lightweight operations

### CPU Usage
- Background threads use minimal CPU
- Health checks are performed at configurable intervals
- State persistence is asynchronous

## Security Considerations

### Credential Protection
- Credentials are not stored in state files
- Connection state excludes sensitive information
- Fallback servers can use different credentials

### Network Security
- All connections use TLS encryption
- Certificate validation is enforced
- Rate limiting prevents abuse

### Audit Trail
- All connection attempts are logged
- Failure history provides audit trail
- State changes are tracked with timestamps

## Integration with Email Agent

The reconnection system is designed to integrate seamlessly with the broader Email Agent architecture:

```python
# Integration example
from src.email.enhanced_godaddy_client import EnhancedGoDaddyEmailClient
from src.email.connection_pool import ConnectionPoolManager

# Use enhanced client in connection pool
pool_manager = ConnectionPoolManager(
    account_config=account_config,
    client_factory=lambda: EnhancedGoDaddyEmailClient(
        account_config=account_config,
        reconnection_config=reconnection_config,
        auto_reconnect=True
    )
)
```

This reconnection system provides the foundation for reliable, production-ready email processing with automatic recovery from network issues, server failures, and other connectivity problems.