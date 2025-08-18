#!/usr/bin/env python3
"""
Simple demonstration of the Enhanced Configuration Management System.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import ConfigurationManager
from config.models import EmailAccountType


def main():
    """Demonstrate the configuration management system."""
    
    print("=== Enhanced Configuration Management System Demo ===\n")
    
    # Set environment for demo
    os.environ['EMAIL_AGENT_ENV'] = 'development'
    
    # Initialize configuration manager
    print("1. Loading configuration...")
    config_manager = ConfigurationManager()
    config = config_manager.get_configuration()
    
    print(f"   Environment: {config.environment.value}")
    print(f"   Email accounts: {len(config.email_accounts)}")
    print(f"   Hot reload: {config.hot_reload_enabled}")
    print()
    
    # Show all configured accounts
    print("2. Configured email accounts:")
    for account_id, account in config.email_accounts.items():
        print(f"   - {account_id}:")
        print(f"     Type: {account.account_type.value}")
        print(f"     Username: {account.username}")
        print(f"     Security Level: {account.security_level.value}")
        print(f"     Rate Limit: {account.rate_limit_per_hour}/hour")
        print(f"     IMAP: {account.imap_settings.host}:{account.imap_settings.port}")
        print(f"     SMTP: {account.smtp_settings.host}:{account.smtp_settings.port}")
        print()
    
    # Demonstrate account access by type
    print("3. Accessing accounts by type...")
    for account_type in EmailAccountType:
        accounts = config_manager.get_accounts_by_type(account_type)
        print(f"   {account_type.value}: {len(accounts)} account(s)")
        for account in accounts:
            print(f"     - {account.account_id} ({account.username})")
    print()
    
    # Show system configuration
    print("4. System configuration:")
    if config.database:
        print(f"   Database: {config.database.host}:{config.database.port}")
        print(f"   Pool size: {config.database.pool_size}")
    
    if config.redis:
        print(f"   Redis: {config.redis.host}:{config.redis.port}")
        print(f"   Connection pool: {config.redis.connection_pool_size}")
    
    if config.security:
        print(f"   Security: {len(config.security.allowed_domains)} allowed domains")
        print(f"   Attachment scanning: {config.security.enable_attachment_scanning}")
        print(f"   Content filtering: {config.security.enable_content_filtering}")
    
    if config.monitoring:
        print(f"   Monitoring: {config.monitoring.enabled}")
        print(f"   Log level: {config.monitoring.log_level}")
        print(f"   Metrics port: {config.monitoring.metrics_port}")
    print()
    
    # Demonstrate configuration validation
    print("5. Configuration validation...")
    try:
        validation_errors = config_manager.validate_configuration_file(config.config_file_path)
        if validation_errors:
            print("   Validation errors found:")
            for error in validation_errors:
                print(f"     - {error}")
        else:
            print("   ✓ Configuration is valid!")
    except Exception as e:
        print(f"   Validation error: {e}")
    print()
    
    # Test configuration access methods
    print("6. Testing configuration access methods...")
    try:
        # Get specific account
        eo_account = config_manager.get_email_account_config('eo_intake_account')
        print(f"   ✓ Retrieved EO account: {eo_account.username}")
        
        # Get accounts by type
        pmo_accounts = config_manager.get_accounts_by_type(EmailAccountType.PMO)
        print(f"   ✓ Found {len(pmo_accounts)} PMO account(s)")
        
        # Test nonexistent account
        try:
            config_manager.get_email_account_config('nonexistent_account')
        except Exception as e:
            print(f"   ✓ Correctly handled nonexistent account: {type(e).__name__}")
        
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # Clean up
    config_manager.close()
    print("7. ✓ Configuration manager closed successfully!")
    print("\n=== Demo completed successfully! ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)