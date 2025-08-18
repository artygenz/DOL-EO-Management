#!/usr/bin/env python3
"""
Example demonstrating integration of the Enhanced Configuration Management System
with the existing Email Agent components.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import ConfigurationManager
from config.models import EmailAccountType
from email.godaddy_client import GoDaddyEmailClient


def create_enhanced_godaddy_client(config_manager: ConfigurationManager, account_type: EmailAccountType):
    """
    Create an enhanced GoDaddy email client using configuration management.
    
    This demonstrates how the new configuration system can be integrated
    with the existing email client implementation.
    """
    # Get account configuration by type
    accounts = config_manager.get_accounts_by_type(account_type)
    if not accounts:
        raise ValueError(f"No accounts configured for type: {account_type}")
    
    account_config = accounts[0]  # Use first account of this type
    
    # Create enhanced client with configuration
    class EnhancedGoDaddyEmailClient(GoDaddyEmailClient):
        def __init__(self, account_config):
            # Don't call parent __init__ as it uses environment variables
            self.account_config = account_config
            
            # Set connection parameters from configuration
            self.imap_host = account_config.imap_settings.host
            self.imap_port = account_config.imap_settings.port
            self.smtp_host = account_config.smtp_settings.host
            self.smtp_port = account_config.smtp_settings.port
            self.username = account_config.username
            self.password = account_config.password
            
            # Connection objects
            self.imap = None
            self.smtp = None
            
            print(f"Enhanced client created for {account_config.account_id}")
            print(f"  Account type: {account_config.account_type.value}")
            print(f"  Security level: {account_config.security_level.value}")
            print(f"  Rate limit: {account_config.rate_limit_per_hour}/hour")
            print(f"  IMAP: {self.imap_host}:{self.imap_port}")
            print(f"  SMTP: {self.smtp_host}:{self.smtp_port}")
        
        def get_connection_settings(self):
            """Get connection settings for monitoring/debugging."""
            return {
                'imap_host': self.imap_host,
                'imap_port': self.imap_port,
                'smtp_host': self.smtp_host,
                'smtp_port': self.smtp_port,
                'max_connections': self.account_config.imap_settings.max_connections,
                'timeout': self.account_config.imap_settings.timeout,
                'rate_limit': self.account_config.rate_limit_per_hour
            }
    
    return EnhancedGoDaddyEmailClient(account_config)


def demonstrate_configuration_features():
    """Demonstrate key features of the configuration management system."""
    
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
    
    # Demonstrate account access by type
    print("2. Accessing accounts by type...")
    for account_type in EmailAccountType:
        accounts = config_manager.get_accounts_by_type(account_type)
        print(f"   {account_type.value}: {len(accounts)} account(s)")
    print()
    
    # Demonstrate enhanced email client creation
    print("3. Creating enhanced email clients...")
    try:
        # Create EO intake client
        eo_client = create_enhanced_godaddy_client(config_manager, EmailAccountType.EO_INTAKE)
        print()
        
        # Create PMO client
        pmo_client = create_enhanced_godaddy_client(config_manager, EmailAccountType.PMO)
        print()
        
        # Show connection settings
        print("4. Connection settings comparison:")
        eo_settings = eo_client.get_connection_settings()
        pmo_settings = pmo_client.get_connection_settings()
        
        print("   EO Intake Client:")
        for key, value in eo_settings.items():
            print(f"     {key}: {value}")
        
        print("   PMO Client:")
        for key, value in pmo_settings.items():
            print(f"     {key}: {value}")
        print()
        
    except ValueError as e:
        print(f"   Error: {e}")
        print()
    
    # Demonstrate configuration validation
    print("5. Configuration validation...")
    try:
        # Validate a configuration file
        validation_errors = config_manager.validate_configuration_file(config.config_file_path)
        if validation_errors:
            print("   Validation errors found:")
            for error in validation_errors:
                print(f"     - {error}")
        else:
            print("   Configuration is valid!")
    except Exception as e:
        print(f"   Validation error: {e}")
    print()
    
    # Demonstrate configuration access patterns
    print("6. Configuration access patterns...")
    
    # Get specific account
    try:
        eo_account = config_manager.get_email_account_config('eo_intake_account')
        print(f"   EO account username: {eo_account.username}")
        print(f"   EO account priority: {eo_account.priority_weight}")
    except Exception as e:
        print(f"   Error accessing account: {e}")
    
    # Show database configuration
    if config.database:
        print(f"   Database: {config.database.host}:{config.database.port}")
        print(f"   Pool size: {config.database.pool_size}")
    
    # Show security settings
    if config.security:
        print(f"   Security: {len(config.security.allowed_domains)} allowed domains")
        print(f"   Attachment scanning: {config.security.enable_attachment_scanning}")
    
    print()
    
    # Clean up
    config_manager.close()
    print("7. Configuration manager closed successfully!")
    print("\n=== Demo completed successfully! ===")


if __name__ == "__main__":
    try:
        demonstrate_configuration_features()
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)