"""
Unit tests for configuration models.
Tests data model validation, initialization, and constraints.
"""

import pytest
from src.config.models import (
    EmailAccountConfig, IMAPSettings, SMTPSettings, SecuritySettings,
    DatabaseConfig, RedisConfig, MonitoringConfig, SystemConfig,
    Environment, EmailAccountType, SecurityLevel
)


class TestIMAPSettings:
    """Test IMAP settings validation and initialization."""
    
    def test_valid_imap_settings(self):
        """Test creation of valid IMAP settings."""
        settings = IMAPSettings(
            host="imap.example.com",
            port=993,
            use_ssl=True,
            timeout=30
        )
        assert settings.host == "imap.example.com"
        assert settings.port == 993
        assert settings.use_ssl is True
        assert settings.timeout == 30
    
    def test_imap_settings_defaults(self):
        """Test IMAP settings with default values."""
        settings = IMAPSettings(host="imap.example.com")
        assert settings.port == 993
        assert settings.use_ssl is True
        assert settings.timeout == 30
        assert settings.idle_timeout == 1740
        assert settings.max_connections == 5
    
    def test_invalid_imap_host(self):
        """Test IMAP settings with invalid host."""
        with pytest.raises(ValueError, match="IMAP host cannot be empty"):
            IMAPSettings(host="")
    
    def test_invalid_imap_port(self):
        """Test IMAP settings with invalid port."""
        with pytest.raises(ValueError, match="IMAP port must be between 1 and 65535"):
            IMAPSettings(host="imap.example.com", port=0)
        
        with pytest.raises(ValueError, match="IMAP port must be between 1 and 65535"):
            IMAPSettings(host="imap.example.com", port=65536)
    
    def test_invalid_imap_timeout(self):
        """Test IMAP settings with invalid timeout."""
        with pytest.raises(ValueError, match="IMAP timeout must be positive"):
            IMAPSettings(host="imap.example.com", timeout=0)


class TestSMTPSettings:
    """Test SMTP settings validation and initialization."""
    
    def test_valid_smtp_settings(self):
        """Test creation of valid SMTP settings."""
        settings = SMTPSettings(
            host="smtp.example.com",
            port=465,
            use_ssl=True,
            timeout=30
        )
        assert settings.host == "smtp.example.com"
        assert settings.port == 465
        assert settings.use_ssl is True
        assert settings.timeout == 30
    
    def test_smtp_settings_defaults(self):
        """Test SMTP settings with default values."""
        settings = SMTPSettings(host="smtp.example.com")
        assert settings.port == 465
        assert settings.use_ssl is True
        assert settings.use_tls is False
        assert settings.timeout == 30
    
    def test_invalid_smtp_host(self):
        """Test SMTP settings with invalid host."""
        with pytest.raises(ValueError, match="SMTP host cannot be empty"):
            SMTPSettings(host="")
    
    def test_invalid_smtp_port(self):
        """Test SMTP settings with invalid port."""
        with pytest.raises(ValueError, match="SMTP port must be between 1 and 65535"):
            SMTPSettings(host="smtp.example.com", port=0)


class TestSecuritySettings:
    """Test security settings validation and initialization."""
    
    def test_valid_security_settings(self):
        """Test creation of valid security settings."""
        settings = SecuritySettings(
            encryption_key_path="/path/to/key",
            credential_rotation_days=90,
            allowed_domains=["example.com", "test.gov"],
            blocked_domains=["spam.com"]
        )
        assert settings.encryption_key_path == "/path/to/key"
        assert settings.credential_rotation_days == 90
        assert "example.com" in settings.allowed_domains
        assert "spam.com" in settings.blocked_domains
    
    def test_invalid_encryption_key_path(self):
        """Test security settings with invalid encryption key path."""
        with pytest.raises(ValueError, match="Encryption key path cannot be empty"):
            SecuritySettings(encryption_key_path="")
    
    def test_invalid_credential_rotation_days(self):
        """Test security settings with invalid rotation days."""
        with pytest.raises(ValueError, match="Credential rotation days must be positive"):
            SecuritySettings(
                encryption_key_path="/path/to/key",
                credential_rotation_days=0
            )


class TestEmailAccountConfig:
    """Test email account configuration validation."""
    
    def create_valid_imap_settings(self):
        """Helper to create valid IMAP settings."""
        return IMAPSettings(host="imap.example.com")
    
    def create_valid_smtp_settings(self):
        """Helper to create valid SMTP settings."""
        return SMTPSettings(host="smtp.example.com")
    
    def test_valid_email_account_config(self):
        """Test creation of valid email account configuration."""
        config = EmailAccountConfig(
            account_id="test_account",
            account_type=EmailAccountType.EO_INTAKE,
            username="test@example.com",
            password="secure_password",
            imap_settings=self.create_valid_imap_settings(),
            smtp_settings=self.create_valid_smtp_settings()
        )
        assert config.account_id == "test_account"
        assert config.account_type == EmailAccountType.EO_INTAKE
        assert config.username == "test@example.com"
        assert config.security_level == SecurityLevel.STANDARD
    
    def test_invalid_account_id(self):
        """Test email account config with invalid account ID."""
        with pytest.raises(ValueError, match="Account ID cannot be empty"):
            EmailAccountConfig(
                account_id="",
                account_type=EmailAccountType.EO_INTAKE,
                username="test@example.com",
                password="secure_password",
                imap_settings=self.create_valid_imap_settings(),
                smtp_settings=self.create_valid_smtp_settings()
            )
    
    def test_invalid_username(self):
        """Test email account config with invalid username."""
        with pytest.raises(ValueError, match="Username cannot be empty"):
            EmailAccountConfig(
                account_id="test_account",
                account_type=EmailAccountType.EO_INTAKE,
                username="",
                password="secure_password",
                imap_settings=self.create_valid_imap_settings(),
                smtp_settings=self.create_valid_smtp_settings()
            )
    
    def test_invalid_password(self):
        """Test email account config with invalid password."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            EmailAccountConfig(
                account_id="test_account",
                account_type=EmailAccountType.EO_INTAKE,
                username="test@example.com",
                password="",
                imap_settings=self.create_valid_imap_settings(),
                smtp_settings=self.create_valid_smtp_settings()
            )


class TestDatabaseConfig:
    """Test database configuration validation."""
    
    def test_valid_database_config(self):
        """Test creation of valid database configuration."""
        config = DatabaseConfig(
            host="db.example.com",
            port=5432,
            database="email_agent",
            username="dbuser",
            password="dbpass"
        )
        assert config.host == "db.example.com"
        assert config.port == 5432
        assert config.database == "email_agent"
        assert config.pool_size == 10  # default
    
    def test_database_config_defaults(self):
        """Test database configuration with default values."""
        config = DatabaseConfig(host="db.example.com")
        assert config.port == 5432
        assert config.database == "email_agent"
        assert config.pool_size == 10
        assert config.ssl_mode == "require"
    
    def test_invalid_database_host(self):
        """Test database config with invalid host."""
        with pytest.raises(ValueError, match="Database host cannot be empty"):
            DatabaseConfig(host="")
    
    def test_invalid_database_port(self):
        """Test database config with invalid port."""
        with pytest.raises(ValueError, match="Database port must be between 1 and 65535"):
            DatabaseConfig(host="db.example.com", port=0)


class TestSystemConfig:
    """Test system configuration validation and functionality."""
    
    def create_valid_email_account(self, account_id="test", account_type=EmailAccountType.EO_INTAKE):
        """Helper to create valid email account."""
        return EmailAccountConfig(
            account_id=account_id,
            account_type=account_type,
            username="test@example.com",
            password="secure_password",
            imap_settings=IMAPSettings(host="imap.example.com"),
            smtp_settings=SMTPSettings(host="smtp.example.com")
        )
    
    def test_valid_system_config(self):
        """Test creation of valid system configuration."""
        email_accounts = {
            "test_account": self.create_valid_email_account()
        }
        
        config = SystemConfig(
            environment=Environment.DEVELOPMENT,
            email_accounts=email_accounts
        )
        assert config.environment == Environment.DEVELOPMENT
        assert len(config.email_accounts) == 1
        assert "test_account" in config.email_accounts
    
    def test_system_config_no_email_accounts(self):
        """Test system config with no email accounts."""
        with pytest.raises(ValueError, match="At least one email account must be configured"):
            SystemConfig(
                environment=Environment.DEVELOPMENT,
                email_accounts={}
            )
    
    def test_production_environment_requirements(self):
        """Test production environment validation requirements."""
        email_accounts = {
            "test_account": self.create_valid_email_account()
        }
        
        # Should fail without required account types
        with pytest.raises(ValueError, match="Production environment requires account types"):
            SystemConfig(
                environment=Environment.PRODUCTION,
                email_accounts=email_accounts
            )
        
        # Should pass with required account types
        email_accounts["eo_account"] = self.create_valid_email_account("eo", EmailAccountType.EO_INTAKE)
        email_accounts["pmo_account"] = self.create_valid_email_account("pmo", EmailAccountType.PMO)
        
        config = SystemConfig(
            environment=Environment.PRODUCTION,
            email_accounts=email_accounts
        )
        assert config.environment == Environment.PRODUCTION
    
    def test_get_account_by_type(self):
        """Test getting account by type."""
        email_accounts = {
            "eo_account": self.create_valid_email_account("eo", EmailAccountType.EO_INTAKE),
            "pmo_account": self.create_valid_email_account("pmo", EmailAccountType.PMO)
        }
        
        config = SystemConfig(
            environment=Environment.DEVELOPMENT,
            email_accounts=email_accounts
        )
        
        eo_account = config.get_account_by_type(EmailAccountType.EO_INTAKE)
        assert eo_account is not None
        assert eo_account.account_type == EmailAccountType.EO_INTAKE
        
        dev_account = config.get_account_by_type(EmailAccountType.DEVELOPER)
        assert dev_account is None
    
    def test_get_accounts_by_type(self):
        """Test getting multiple accounts by type."""
        email_accounts = {
            "eo_account1": self.create_valid_email_account("eo1", EmailAccountType.EO_INTAKE),
            "eo_account2": self.create_valid_email_account("eo2", EmailAccountType.EO_INTAKE),
            "pmo_account": self.create_valid_email_account("pmo", EmailAccountType.PMO)
        }
        
        config = SystemConfig(
            environment=Environment.DEVELOPMENT,
            email_accounts=email_accounts
        )
        
        eo_accounts = config.get_accounts_by_type(EmailAccountType.EO_INTAKE)
        assert len(eo_accounts) == 2
        
        pmo_accounts = config.get_accounts_by_type(EmailAccountType.PMO)
        assert len(pmo_accounts) == 1
        
        dev_accounts = config.get_accounts_by_type(EmailAccountType.DEVELOPER)
        assert len(dev_accounts) == 0