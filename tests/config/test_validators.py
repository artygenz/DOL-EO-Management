"""
Unit tests for configuration validators.
Tests comprehensive validation logic for all configuration types.
"""

import pytest
from src.config.validators import ConfigurationValidator
from src.config.models import (
    SystemConfig, EmailAccountConfig, IMAPSettings, SMTPSettings,
    SecuritySettings, DatabaseConfig, RedisConfig, MonitoringConfig,
    Environment, EmailAccountType, SecurityLevel
)


class TestConfigurationValidator:
    """Test configuration validator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()
    
    def create_valid_email_account(self, account_id="test", account_type=EmailAccountType.EO_INTAKE):
        """Helper to create valid email account."""
        return EmailAccountConfig(
            account_id=account_id,
            account_type=account_type,
            username="test@example.com",
            password="SecurePass123!",
            imap_settings=IMAPSettings(host="imap.example.com"),
            smtp_settings=SMTPSettings(host="smtp.example.com")
        )
    
    def create_valid_system_config(self):
        """Helper to create valid system configuration."""
        email_accounts = {
            "test_account": self.create_valid_email_account()
        }
        
        return SystemConfig(
            environment=Environment.DEVELOPMENT,
            email_accounts=email_accounts,
            database=DatabaseConfig(host="db.example.com"),
            redis=RedisConfig(host="redis.example.com"),
            security=SecuritySettings(encryption_key_path="/path/to/key"),
            monitoring=MonitoringConfig()
        )


class TestEmailValidation:
    """Test email address validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()
    
    def test_valid_email_addresses(self):
        """Test validation of valid email addresses."""
        valid_emails = [
            "user@example.com",
            "test.user@domain.org",
            "user+tag@example.co.uk",
            "user123@test-domain.com"
        ]
        
        for email in valid_emails:
            assert self.validator.validate_email_address(email), f"Should be valid: {email}"
    
    def test_invalid_email_addresses(self):
        """Test validation of invalid email addresses."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com",
            "user space@example.com",
            ""
        ]
        
        for email in invalid_emails:
            assert not self.validator.validate_email_address(email), f"Should be invalid: {email}"


class TestDomainValidation:
    """Test domain validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()
    
    def test_valid_domains(self):
        """Test validation of valid domains."""
        valid_domains = [
            "example.com",
            "sub.example.com",
            "test-domain.org",
            "domain.co.uk"
        ]
        
        for domain in valid_domains:
            assert self.validator.validate_domain(domain), f"Should be valid: {domain}"
    
    def test_invalid_domains(self):
        """Test validation of invalid domains."""
        invalid_domains = [
            "invalid-domain",
            ".com",
            "domain.",
            "domain with spaces.com",
            ""
        ]
        
        for domain in invalid_domains:
            assert not self.validator.validate_domain(domain), f"Should be invalid: {domain}"


class TestIPAddressValidation:
    """Test IP address validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()
    
    def test_valid_ip_addresses(self):
        """Test validation of valid IP addresses."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "127.0.0.1",
            "2001:db8::1",
            "::1"
        ]
        
        for ip in valid_ips:
            assert self.validator.validate_ip_address(ip), f"Should be valid: {ip}"
    
    def test_invalid_ip_addresses(self):
        """Test validation of invalid IP addresses."""
        invalid_ips = [
            "256.256.256.256",
            "192.168.1",
            "not-an-ip",
            ""
        ]
        
        for ip in invalid_ips:
            assert not self.validator.validate_ip_address(ip), f"Should be invalid: {ip}"


class TestSystemConfigValidation:
    """Test system configuration validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()
    
    def create_valid_email_account(self, account_id="test", account_type=EmailAccountType.EO_INTAKE):
        """Helper to create valid email account."""
        return EmailAccountConfig(
            account_id=account_id,
            account_type=account_type,
            username="test@example.com",
            password="SecurePass123!",
            imap_settings=IMAPSettings(host="imap.example.com"),
            smtp_settings=SMTPSettings(host="smtp.example.com")
        )
    
    def test_valid_system_config(self):
        """Test validation of valid system configuration."""
        email_accounts = {
            "test_account": self.create_valid_email_account()
        }
        
        config = SystemConfig(
            environment=Environment.DEVELOPMENT,
            email_accounts=email_accounts
        )
        
        errors = self.validator.validate_system_config(config)
        assert len(errors) == 0, f"Should be valid, but got errors: {errors}"
    
    def test_empty_email_accounts(self):
        """Test validation with empty email accounts."""
        # This should fail at model level
        with pytest.raises(ValueError, match="At least one email account must be configured"):
            SystemConfig(
                environment=Environment.DEVELOPMENT,
                email_accounts={}
            )
    
    def test_duplicate_usernames(self):
        """Test validation with duplicate usernames."""
        email_accounts = {
            "account1": self.create_valid_email_account("account1"),
            "account2": self.create_valid_email_account("account2")  # Same username
        }
        
        config = SystemConfig(
            environment=Environment.DEVELOPMENT,
            email_accounts=email_accounts
        )
        
        errors = self.validator.validate_system_config(config)
        assert any("duplicate username" in error.lower() for error in errors)
    
    def test_production_environment_requirements(self):
        """Test production environment validation requirements."""
        # Missing required account types - this should fail at model level
        email_accounts = {
            "dev_account": self.create_valid_email_account("dev", EmailAccountType.DEVELOPER)
        }
        
        with pytest.raises(ValueError, match="Production environment requires account types"):
            SystemConfig(
                environment=Environment.PRODUCTION,
                email_accounts=email_accounts
            )


class TestFederalPasswordValidation:
    """Test federal password validation requirements."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()
    
    def test_valid_federal_password(self):
        """Test validation of valid federal password."""
        password = "SecurePassword123!"
        errors = self.validator._validate_federal_password(password)
        assert len(errors) == 0, f"Should be valid, but got errors: {errors}"
    
    def test_password_too_short(self):
        """Test password that's too short."""
        password = "Short1!"
        errors = self.validator._validate_federal_password(password)
        assert any("12 characters" in error for error in errors)
    
    def test_password_missing_uppercase(self):
        """Test password missing uppercase letters."""
        password = "lowercase123!"
        errors = self.validator._validate_federal_password(password)
        assert any("uppercase" in error for error in errors)
    
    def test_password_missing_lowercase(self):
        """Test password missing lowercase letters."""
        password = "UPPERCASE123!"
        errors = self.validator._validate_federal_password(password)
        assert any("lowercase" in error for error in errors)
    
    def test_password_missing_numbers(self):
        """Test password missing numbers."""
        password = "PasswordOnly!"
        errors = self.validator._validate_federal_password(password)
        assert any("numbers" in error for error in errors)
    
    def test_password_missing_special_chars(self):
        """Test password missing special characters."""
        password = "Password123"
        errors = self.validator._validate_federal_password(password)
        assert any("special characters" in error for error in errors)


class TestSchemaValidation:
    """Test configuration schema validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()
    
    def test_valid_config_schema(self):
        """Test validation of valid configuration schema."""
        config_dict = {
            'environment': 'development',
            'email_accounts': {
                'test_account': {
                    'account_id': 'test_account',
                    'account_type': 'eo_intake',
                    'username': 'test@example.com',
                    'password': 'secure_password',
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
            'database': {},
            'redis': {},
            'security': {},
            'monitoring': {}
        }
        
        errors = self.validator.validate_config_schema(config_dict)
        assert len(errors) == 0, f"Should be valid, but got errors: {errors}"
    
    def test_missing_required_keys(self):
        """Test schema validation with missing required keys."""
        config_dict = {
            'environment': 'development'
            # Missing other required keys
        }
        
        errors = self.validator.validate_config_schema(config_dict)
        assert len(errors) > 0
        assert any("missing required" in error.lower() for error in errors)
    
    def test_invalid_data_types(self):
        """Test schema validation with invalid data types."""
        config_dict = {
            'environment': 123,  # Should be string
            'email_accounts': "not_a_dict",  # Should be dict
            'database': {},
            'redis': {},
            'security': {},
            'monitoring': {}
        }
        
        errors = self.validator.validate_config_schema(config_dict)
        assert len(errors) > 0
        assert any("invalid type" in error.lower() for error in errors)


class TestCrossDependencyValidation:
    """Test cross-component dependency validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()
    
    def create_valid_email_account(self, account_id="test", account_type=EmailAccountType.EO_INTAKE, security_level=SecurityLevel.STANDARD):
        """Helper to create valid email account."""
        return EmailAccountConfig(
            account_id=account_id,
            account_type=account_type,
            username="test@example.com",
            password="SecurePass123!",
            imap_settings=IMAPSettings(host="imap.example.com"),
            smtp_settings=SMTPSettings(host="smtp.example.com"),
            security_level=security_level
        )
    
    def test_production_missing_database(self):
        """Test production environment missing database configuration."""
        email_accounts = {
            "eo_account": self.create_valid_email_account("eo", EmailAccountType.EO_INTAKE),
            "pmo_account": self.create_valid_email_account("pmo", EmailAccountType.PMO)
        }
        
        config = SystemConfig(
            environment=Environment.PRODUCTION,
            email_accounts=email_accounts,
            database=None  # Missing database
        )
        
        errors = self.validator._validate_cross_dependencies(config)
        assert any("database configuration" in error.lower() for error in errors)
    
    def test_production_missing_federal_accounts(self):
        """Test production environment missing federal security level accounts."""
        email_accounts = {
            "eo_account": self.create_valid_email_account("eo", EmailAccountType.EO_INTAKE, SecurityLevel.STANDARD),
            "pmo_account": self.create_valid_email_account("pmo", EmailAccountType.PMO, SecurityLevel.STANDARD)
        }
        
        config = SystemConfig(
            environment=Environment.PRODUCTION,
            email_accounts=email_accounts,
            database=DatabaseConfig(host="db.example.com"),
            redis=RedisConfig(host="redis.example.com"),
            security=SecuritySettings(encryption_key_path="/path/to/key")
        )
        
        errors = self.validator._validate_cross_dependencies(config)
        assert any("federal security level" in error.lower() for error in errors)