"""
Unit tests for configuration manager.
Tests configuration loading, validation, hot reloading, and error handling.
"""

import os
import json
import yaml
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.config.manager import ConfigurationManager
from src.config.models import (
    SystemConfig, EmailAccountConfig, IMAPSettings, SMTPSettings,
    Environment, EmailAccountType, SecurityLevel
)
from src.config.exceptions import (
    ConfigurationError, ValidationError, EnvironmentError, 
    SchemaError, ReloadError
)


class TestConfigurationManager:
    """Test configuration manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
        
        # Create a valid test configuration
        self.valid_config = {
            'environment': 'development',
            'email_accounts': {
                'test_account': {
                    'account_id': 'test_account',
                    'account_type': 'eo_intake',
                    'username': 'test@example.com',
                    'password': 'SecurePass123!',
                    'imap_settings': {
                        'host': 'imap.example.com',
                        'port': 993,
                        'use_ssl': True,
                        'timeout': 30,
                        'idle_timeout': 1740,
                        'max_connections': 5,
                        'connection_retry_attempts': 3,
                        'connection_retry_delay': 5
                    },
                    'smtp_settings': {
                        'host': 'smtp.example.com',
                        'port': 465,
                        'use_ssl': True,
                        'use_tls': False,
                        'timeout': 30,
                        'max_connections': 3,
                        'retry_attempts': 3,
                        'retry_delay': 5
                    },
                    'security_level': 'standard',
                    'monitoring_enabled': True,
                    'rate_limit_per_hour': 1000,
                    'priority_weight': 1
                }
            },
            'database': {
                'host': 'db.example.com',
                'port': 5432,
                'database': 'email_agent',
                'username': 'dbuser',
                'password': 'dbpass',
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'ssl_mode': 'require'
            },
            'redis': {
                'host': 'redis.example.com',
                'port': 6379,
                'database': 0,
                'password': None,
                'ssl': False,
                'socket_timeout': 30,
                'connection_pool_size': 10,
                'retry_attempts': 3
            },
            'security': {
                'encryption_key_path': '/path/to/key',
                'credential_rotation_days': 90,
                'require_sender_validation': True,
                'enable_attachment_scanning': True,
                'enable_content_filtering': True,
                'allowed_domains': ['example.com'],
                'blocked_domains': ['spam.com'],
                'max_attachment_size_mb': 25
            },
            'monitoring': {
                'enabled': True,
                'metrics_port': 8080,
                'health_check_interval': 30,
                'performance_monitoring': True,
                'audit_logging': True,
                'log_level': 'INFO',
                'log_file_path': '/var/log/email-agent/app.log',
                'metrics_retention_days': 30
            },
            'hot_reload_enabled': False  # Disable for testing
        }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temp files
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def write_config_file(self, config_data, file_format='yaml'):
        """Helper to write configuration to file."""
        if file_format == 'yaml':
            with open(self.config_file, 'w') as f:
                yaml.dump(config_data, f)
        elif file_format == 'json':
            json_file = self.config_file.replace('.yaml', '.json')
            with open(json_file, 'w') as f:
                json.dump(config_data, f)
            return json_file
        return self.config_file


class TestConfigurationLoading:
    """Test configuration loading functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
        
        # Valid minimal configuration
        self.valid_config = {
            'environment': 'development',
            'email_accounts': {
                'test_account': {
                    'account_id': 'test_account',
                    'account_type': 'eo_intake',
                    'username': 'test@example.com',
                    'password': 'SecurePass123!',
                    'imap_settings': {
                        'host': 'imap.example.com',
                        'port': 993,
                        'use_ssl': True,
                        'timeout': 30,
                        'idle_timeout': 1740,
                        'max_connections': 5,
                        'connection_retry_attempts': 3,
                        'connection_retry_delay': 5
                    },
                    'smtp_settings': {
                        'host': 'smtp.example.com',
                        'port': 465,
                        'use_ssl': True,
                        'use_tls': False,
                        'timeout': 30,
                        'max_connections': 3,
                        'retry_attempts': 3,
                        'retry_delay': 5
                    },
                    'security_level': 'standard',
                    'monitoring_enabled': True,
                    'rate_limit_per_hour': 1000,
                    'priority_weight': 1
                }
            },
            'hot_reload_enabled': False
        }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def write_config_file(self, config_data):
        """Helper to write configuration to file."""
        with open(self.config_file, 'w') as f:
            yaml.dump(config_data, f)
    
    def test_load_valid_yaml_configuration(self):
        """Test loading valid YAML configuration."""
        self.write_config_file(self.valid_config)
        
        with patch.dict(os.environ, {'EMAIL_AGENT_ENV': 'development'}):
            manager = ConfigurationManager(config_file_path=self.config_file)
            config = manager.get_configuration()
            
            assert config.environment == Environment.DEVELOPMENT
            assert len(config.email_accounts) == 1
            assert 'test_account' in config.email_accounts
    
    def test_load_valid_json_configuration(self):
        """Test loading valid JSON configuration."""
        json_file = self.config_file.replace('.yaml', '.json')
        with open(json_file, 'w') as f:
            json.dump(self.valid_config, f)
        
        with patch.dict(os.environ, {'EMAIL_AGENT_ENV': 'development'}):
            manager = ConfigurationManager(config_file_path=json_file)
            config = manager.get_configuration()
            
            assert config.environment == Environment.DEVELOPMENT
            assert len(config.email_accounts) == 1
        
        os.remove(json_file)
    
    def test_load_nonexistent_file(self):
        """Test loading configuration from nonexistent file."""
        nonexistent_file = "/path/that/does/not/exist.yaml"
        
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            ConfigurationManager(config_file_path=nonexistent_file)
    
    def test_load_invalid_yaml(self):
        """Test loading invalid YAML configuration."""
        with open(self.config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(ConfigurationError, match="Failed to load configuration file"):
            ConfigurationManager(config_file_path=self.config_file)
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON configuration."""
        json_file = self.config_file.replace('.yaml', '.json')
        with open(json_file, 'w') as f:
            f.write('{"invalid": json content}')
        
        with pytest.raises(ConfigurationError, match="Failed to load configuration file"):
            ConfigurationManager(config_file_path=json_file)
        
        os.remove(json_file)


class TestEnvironmentDetection:
    """Test environment detection functionality."""
    
    def test_explicit_environment(self):
        """Test explicit environment specification."""
        config_data = {
            'environment': 'staging', 
            'email_accounts': {
                'test_account': {
                    'account_id': 'test_account',
                    'account_type': 'eo_intake',
                    'username': 'test@example.com',
                    'password': 'SecurePass123!',
                    'imap_settings': {'host': 'imap.example.com'},
                    'smtp_settings': {'host': 'smtp.example.com'}
                }
            }, 
            'hot_reload_enabled': False
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            manager = ConfigurationManager(config_file_path=config_file, environment='production')
            assert manager.environment == Environment.PRODUCTION
        finally:
            os.unlink(config_file)
    
    def test_environment_from_env_var(self):
        """Test environment detection from environment variable."""
        config_data = {
            'environment': 'development', 
            'email_accounts': {
                'test_account': {
                    'account_id': 'test_account',
                    'account_type': 'eo_intake',
                    'username': 'test@example.com',
                    'password': 'SecurePass123!',
                    'imap_settings': {'host': 'imap.example.com'},
                    'smtp_settings': {'host': 'smtp.example.com'}
                }
            }, 
            'hot_reload_enabled': False
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            with patch.dict(os.environ, {'EMAIL_AGENT_ENV': 'staging'}):
                manager = ConfigurationManager(config_file_path=config_file)
                assert manager.environment == Environment.STAGING
        finally:
            os.unlink(config_file)
    
    def test_invalid_environment(self):
        """Test invalid environment specification."""
        with pytest.raises(EnvironmentError, match="Invalid environment"):
            ConfigurationManager(environment='invalid_env')


class TestConfigurationValidation:
    """Test configuration validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_schema_validation_failure(self):
        """Test configuration with schema validation failure."""
        invalid_config = {
            'environment': 'development',
            # Missing required email_accounts
            'hot_reload_enabled': False
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(invalid_config, f)
        
        with pytest.raises(SchemaError, match="Configuration schema validation failed"):
            ConfigurationManager(config_file_path=self.config_file)
    
    def test_model_validation_failure(self):
        """Test configuration with model validation failure."""
        invalid_config = {
            'environment': 'development',
            'email_accounts': {
                'test_account': {
                    'account_id': '',  # Invalid empty account_id
                    'account_type': 'eo_intake',
                    'username': 'test@example.com',
                    'password': 'password',
                    'imap_settings': {'host': 'imap.example.com'},
                    'smtp_settings': {'host': 'smtp.example.com'}
                }
            },
            'hot_reload_enabled': False
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(invalid_config, f)
        
        with pytest.raises((ConfigurationError, SchemaError)):
            ConfigurationManager(config_file_path=self.config_file)


class TestConfigurationAccess:
    """Test configuration access methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
        
        self.valid_config = {
            'environment': 'development',
            'email_accounts': {
                'eo_account': {
                    'account_id': 'eo_account',
                    'account_type': 'eo_intake',
                    'username': 'eo@example.com',
                    'password': 'SecurePass123!',
                    'imap_settings': {
                        'host': 'imap.example.com',
                        'port': 993,
                        'use_ssl': True,
                        'timeout': 30,
                        'idle_timeout': 1740,
                        'max_connections': 5,
                        'connection_retry_attempts': 3,
                        'connection_retry_delay': 5
                    },
                    'smtp_settings': {
                        'host': 'smtp.example.com',
                        'port': 465,
                        'use_ssl': True,
                        'use_tls': False,
                        'timeout': 30,
                        'max_connections': 3,
                        'retry_attempts': 3,
                        'retry_delay': 5
                    },
                    'security_level': 'standard',
                    'monitoring_enabled': True,
                    'rate_limit_per_hour': 1000,
                    'priority_weight': 1
                },
                'pmo_account': {
                    'account_id': 'pmo_account',
                    'account_type': 'pmo',
                    'username': 'pmo@example.com',
                    'password': 'SecurePass123!',
                    'imap_settings': {
                        'host': 'imap.example.com',
                        'port': 993,
                        'use_ssl': True,
                        'timeout': 30,
                        'idle_timeout': 1740,
                        'max_connections': 5,
                        'connection_retry_attempts': 3,
                        'connection_retry_delay': 5
                    },
                    'smtp_settings': {
                        'host': 'smtp.example.com',
                        'port': 465,
                        'use_ssl': True,
                        'use_tls': False,
                        'timeout': 30,
                        'max_connections': 3,
                        'retry_attempts': 3,
                        'retry_delay': 5
                    },
                    'security_level': 'standard',
                    'monitoring_enabled': True,
                    'rate_limit_per_hour': 1000,
                    'priority_weight': 1
                }
            },
            'hot_reload_enabled': False
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(self.valid_config, f)
        
        self.manager = ConfigurationManager(config_file_path=self.config_file)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.manager.close()
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_get_configuration(self):
        """Test getting system configuration."""
        config = self.manager.get_configuration()
        assert isinstance(config, SystemConfig)
        assert config.environment == Environment.DEVELOPMENT
        assert len(config.email_accounts) == 2
    
    def test_get_email_account_config(self):
        """Test getting specific email account configuration."""
        account_config = self.manager.get_email_account_config('eo_account')
        assert account_config.account_id == 'eo_account'
        assert account_config.account_type == EmailAccountType.EO_INTAKE
        assert account_config.username == 'eo@example.com'
    
    def test_get_nonexistent_email_account(self):
        """Test getting nonexistent email account configuration."""
        with pytest.raises(ConfigurationError, match="Email account not found"):
            self.manager.get_email_account_config('nonexistent_account')
    
    def test_get_accounts_by_type(self):
        """Test getting accounts by type."""
        eo_accounts = self.manager.get_accounts_by_type(EmailAccountType.EO_INTAKE)
        assert len(eo_accounts) == 1
        assert eo_accounts[0].account_id == 'eo_account'
        
        pmo_accounts = self.manager.get_accounts_by_type(EmailAccountType.PMO)
        assert len(pmo_accounts) == 1
        assert pmo_accounts[0].account_id == 'pmo_account'
        
        dev_accounts = self.manager.get_accounts_by_type(EmailAccountType.DEVELOPER)
        assert len(dev_accounts) == 0


class TestHotReloading:
    """Test hot configuration reloading functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
        
        self.initial_config = {
            'environment': 'development',
            'email_accounts': {
                'test_account': {
                    'account_id': 'test_account',
                    'account_type': 'eo_intake',
                    'username': 'test@example.com',
                    'password': 'SecurePass123!',
                    'imap_settings': {
                        'host': 'imap.example.com',
                        'port': 993,
                        'use_ssl': True,
                        'timeout': 30,
                        'idle_timeout': 1740,
                        'max_connections': 5,
                        'connection_retry_attempts': 3,
                        'connection_retry_delay': 5
                    },
                    'smtp_settings': {
                        'host': 'smtp.example.com',
                        'port': 465,
                        'use_ssl': True,
                        'use_tls': False,
                        'timeout': 30,
                        'max_connections': 3,
                        'retry_attempts': 3,
                        'retry_delay': 5
                    },
                    'security_level': 'standard',
                    'monitoring_enabled': True,
                    'rate_limit_per_hour': 1000,
                    'priority_weight': 1
                }
            },
            'hot_reload_enabled': False  # Disable file watching for manual testing
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(self.initial_config, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_manual_reload(self):
        """Test manual configuration reload."""
        manager = ConfigurationManager(config_file_path=self.config_file)
        
        # Verify initial configuration
        initial_config = manager.get_configuration()
        assert len(initial_config.email_accounts) == 1
        
        # Update configuration file
        updated_config = self.initial_config.copy()
        updated_config['email_accounts']['new_account'] = {
            'account_id': 'new_account',
            'account_type': 'pmo',
            'username': 'new@example.com',
            'password': 'SecurePass123!',
            'imap_settings': {
                'host': 'imap.example.com',
                'port': 993,
                'use_ssl': True,
                'timeout': 30,
                'idle_timeout': 1740,
                'max_connections': 5,
                'connection_retry_attempts': 3,
                'connection_retry_delay': 5
            },
            'smtp_settings': {
                'host': 'smtp.example.com',
                'port': 465,
                'use_ssl': True,
                'use_tls': False,
                'timeout': 30,
                'max_connections': 3,
                'retry_attempts': 3,
                'retry_delay': 5
            },
            'security_level': 'standard',
            'monitoring_enabled': True,
            'rate_limit_per_hour': 1000,
            'priority_weight': 1
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(updated_config, f)
        
        # Reload configuration
        reloaded_config = manager.reload_configuration()
        assert len(reloaded_config.email_accounts) == 2
        assert 'new_account' in reloaded_config.email_accounts
        
        manager.close()
    
    def test_reload_callbacks(self):
        """Test reload callback functionality."""
        manager = ConfigurationManager(config_file_path=self.config_file)
        
        # Add reload callback
        callback_called = threading.Event()
        callback_config = None
        
        def reload_callback(config):
            nonlocal callback_config
            callback_config = config
            callback_called.set()
        
        manager.add_reload_callback(reload_callback)
        
        # Trigger reload
        manager.reload_configuration()
        
        # Verify callback was called
        assert callback_called.wait(timeout=1.0)
        assert callback_config is not None
        assert isinstance(callback_config, SystemConfig)
        
        manager.close()
    
    def test_reload_failure(self):
        """Test reload failure handling."""
        manager = ConfigurationManager(config_file_path=self.config_file)
        
        # Write invalid configuration
        with open(self.config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Attempt reload should fail
        with pytest.raises(ReloadError, match="Failed to reload configuration"):
            manager.reload_configuration()
        
        manager.close()


class TestThreadSafety:
    """Test thread safety of configuration manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
        
        self.valid_config = {
            'environment': 'development',
            'email_accounts': {
                'test_account': {
                    'account_id': 'test_account',
                    'account_type': 'eo_intake',
                    'username': 'test@example.com',
                    'password': 'SecurePass123!',
                    'imap_settings': {
                        'host': 'imap.example.com',
                        'port': 993,
                        'use_ssl': True,
                        'timeout': 30,
                        'idle_timeout': 1740,
                        'max_connections': 5,
                        'connection_retry_attempts': 3,
                        'connection_retry_delay': 5
                    },
                    'smtp_settings': {
                        'host': 'smtp.example.com',
                        'port': 465,
                        'use_ssl': True,
                        'use_tls': False,
                        'timeout': 30,
                        'max_connections': 3,
                        'retry_attempts': 3,
                        'retry_delay': 5
                    },
                    'security_level': 'standard',
                    'monitoring_enabled': True,
                    'rate_limit_per_hour': 1000,
                    'priority_weight': 1
                }
            },
            'hot_reload_enabled': False
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(self.valid_config, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_concurrent_access(self):
        """Test concurrent configuration access."""
        manager = ConfigurationManager(config_file_path=self.config_file)
        
        results = []
        errors = []
        
        def access_config():
            try:
                for _ in range(10):
                    config = manager.get_configuration()
                    results.append(config.environment)
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_config)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 50  # 5 threads * 10 accesses each
        assert all(env == Environment.DEVELOPMENT for env in results)
        
        manager.close()