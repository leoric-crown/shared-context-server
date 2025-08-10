"""
Configuration management for Shared Context MCP Server.

This module provides centralized configuration loading and validation using
Pydantic BaseSettings with .env file support. Ensures all required environment
variables are present and validates configuration at startup.

Key features:
- Environment variable validation with type checking
- .env file support with python-dotenv
- Pydantic BaseSettings for robust configuration management
- Clear error messages for missing or invalid configuration
- Development vs production configuration support
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal, Optional

import dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Load .env file at module level
dotenv.load_dotenv()


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""

    # Database connection
    database_path: str = Field(default="./chat_history.db", env="DATABASE_PATH")
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_timeout: int = Field(default=30, env="DATABASE_TIMEOUT")
    database_busy_timeout: int = Field(default=5, env="DATABASE_BUSY_TIMEOUT")

    # Connection pooling
    database_max_connections: int = Field(default=20, env="DATABASE_MAX_CONNECTIONS")
    database_min_connections: int = Field(default=2, env="DATABASE_MIN_CONNECTIONS")

    # Retention policies
    audit_log_retention_days: int = Field(default=30, env="AUDIT_LOG_RETENTION_DAYS")
    inactive_session_retention_days: int = Field(
        default=7, env="INACTIVE_SESSION_RETENTION_DAYS"
    )

    @field_validator("database_path")
    @classmethod
    def validate_database_path(cls, v: str) -> str:
        """Ensure database path is valid and directory exists."""
        path = Path(v)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())

    @field_validator("database_timeout", "database_busy_timeout")
    @classmethod
    def validate_timeouts(cls, v: int) -> int:
        """Ensure timeout values are reasonable."""
        if v < 1 or v > 300:
            raise ValueError("Timeout must be between 1 and 300 seconds")
        return v

    @field_validator("database_max_connections")
    @classmethod
    def validate_max_connections(cls, v: int) -> int:
        """Ensure max connections is reasonable."""
        if v < 1 or v > 100:
            raise ValueError("Max connections must be between 1 and 100")
        return v


class MCPServerConfig(BaseSettings):
    """MCP server configuration settings."""

    # Server identification
    mcp_server_name: str = Field(default="shared-context-server", env="MCP_SERVER_NAME")
    mcp_server_version: str = Field(default="1.0.0", env="MCP_SERVER_VERSION")

    # Transport configuration
    mcp_transport: Literal["stdio", "http"] = Field(
        default="stdio", env="MCP_TRANSPORT"
    )
    http_host: str = Field(default="localhost", env="HTTP_HOST")
    http_port: int = Field(default=8000, env="HTTP_PORT")

    @field_validator("http_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Ensure port is in valid range."""
        if v < 1024 or v > 65535:
            raise ValueError("HTTP port must be between 1024 and 65535")
        return v


class SecurityConfig(BaseSettings):
    """Security and authentication configuration."""

    # API authentication
    api_key: str = Field(env="API_KEY")
    jwt_secret_key: Optional[str] = Field(default=None, env="JWT_SECRET_KEY")
    jwt_expiration_time: int = Field(default=86400, env="JWT_EXPIRATION_TIME")

    # Session security
    session_timeout: int = Field(default=3600, env="SESSION_TIMEOUT")
    max_sessions_per_agent: int = Field(default=50, env="MAX_SESSIONS_PER_AGENT")

    # CORS settings
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    allowed_hosts: str = Field(default="localhost,127.0.0.1", env="ALLOWED_HOSTS")

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Ensure API key is secure."""
        if not v:
            raise ValueError("API_KEY environment variable is required")

        # Allow insecure key only in development
        if v == "your-secure-api-key-replace-this-in-production":
            import os

            env_mode = os.getenv("ENVIRONMENT", "development")
            if env_mode == "production":
                raise ValueError("API_KEY must be set to a secure value in production")
            logger.warning("Using default API_KEY - only suitable for development")

        if len(v) < 32 and v != "your-secure-api-key-replace-this-in-production":
            logger.warning("API_KEY should be at least 32 characters for security")
        return v

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in v.split(",")]


class OperationalConfig(BaseSettings):
    """Operational and monitoring configuration."""

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", env="LOG_LEVEL"
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT"
    )
    database_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", env="DATABASE_LOG_LEVEL"
    )

    # Performance monitoring
    enable_performance_monitoring: bool = Field(
        default=True, env="ENABLE_PERFORMANCE_MONITORING"
    )
    performance_log_interval: int = Field(default=300, env="PERFORMANCE_LOG_INTERVAL")

    # Resource limits
    max_memory_entries_per_agent: int = Field(
        default=1000, env="MAX_MEMORY_ENTRIES_PER_AGENT"
    )
    max_memory_size_mb: int = Field(default=100, env="MAX_MEMORY_SIZE_MB")
    max_message_length: int = Field(default=100000, env="MAX_MESSAGE_LENGTH")
    max_messages_per_session: int = Field(default=10000, env="MAX_MESSAGES_PER_SESSION")
    max_metadata_size_kb: int = Field(default=10, env="MAX_METADATA_SIZE_KB")

    # Cleanup settings
    enable_automatic_cleanup: bool = Field(default=True, env="ENABLE_AUTOMATIC_CLEANUP")
    cleanup_interval: int = Field(default=3600, env="CLEANUP_INTERVAL")


class DevelopmentConfig(BaseSettings):
    """Development and debugging configuration."""

    # Environment mode
    environment: Literal["development", "testing", "production"] = Field(
        default="development", env="ENVIRONMENT"
    )
    debug: bool = Field(default=False, env="DEBUG")
    enable_debug_tools: bool = Field(default=False, env="ENABLE_DEBUG_TOOLS")

    # Development database
    dev_reset_database_on_start: bool = Field(
        default=False, env="DEV_RESET_DATABASE_ON_START"
    )
    dev_seed_test_data: bool = Field(default=False, env="DEV_SEED_TEST_DATA")
    test_database_path: str = Field(
        default="./test_chat_history.db", env="TEST_DATABASE_PATH"
    )


class SharedContextServerConfig(BaseSettings):
    """Main configuration class combining all configuration sections."""

    # Configuration sections - these will be populated during initialization
    database: DatabaseConfig
    mcp_server: MCPServerConfig
    security: SecurityConfig
    operational: OperationalConfig
    development: DevelopmentConfig

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        """Initialize configuration with proper section instantiation."""
        # Initialize sub-configurations
        if "database" not in kwargs:
            kwargs["database"] = DatabaseConfig()
        if "mcp_server" not in kwargs:
            kwargs["mcp_server"] = MCPServerConfig()
        if "security" not in kwargs:
            kwargs["security"] = SecurityConfig()
        if "operational" not in kwargs:
            kwargs["operational"] = OperationalConfig()
        if "development" not in kwargs:
            kwargs["development"] = DevelopmentConfig()

        super().__init__(**kwargs)

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.development.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.development.environment == "development"

    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.development.environment == "testing"

    def configure_logging(self) -> None:
        """Configure logging based on settings."""
        # Set up root logger
        logging.basicConfig(
            level=getattr(logging, self.operational.log_level),
            format=self.operational.log_format,
        )

        # Set database-specific logging level
        db_logger = logging.getLogger("src.shared_context_server.database")
        db_logger.setLevel(getattr(logging, self.operational.database_log_level))

        # Reduce noise in production
        if self.is_production():
            logging.getLogger("aiosqlite").setLevel(logging.WARNING)
            logging.getLogger("fastmcp").setLevel(logging.WARNING)

    def validate_production_settings(self) -> list[str]:
        """Validate settings for production deployment."""
        issues = []

        if self.is_production():
            # Security checks
            if (
                self.security.api_key
                == "your-secure-api-key-replace-this-in-production"
            ):
                issues.append("API_KEY must be changed from default value")

            if "*" in self.security.cors_origins:
                issues.append("CORS_ORIGINS should not be '*' in production")

            if self.development.debug:
                issues.append("DEBUG should be False in production")

            # Performance checks
            if self.operational.log_level == "DEBUG":
                issues.append("LOG_LEVEL should not be DEBUG in production")

        return issues


# Global configuration instance
_config: Optional[SharedContextServerConfig] = None


def get_config() -> SharedContextServerConfig:
    """
    Get global configuration instance.

    Returns:
        SharedContextServerConfig: Global configuration
    """
    global _config

    if _config is None:
        _config = load_config()

    return _config


def load_config(env_file: Optional[str] = None) -> SharedContextServerConfig:
    """
    Load configuration from environment and .env file.

    Args:
        env_file: Optional path to .env file (defaults to .env in current directory)

    Returns:
        SharedContextServerConfig: Loaded and validated configuration

    Raises:
        ValueError: If configuration is invalid
        FileNotFoundError: If required .env file is missing
    """
    try:
        # Load configuration with optional custom .env file
        if env_file:
            config = SharedContextServerConfig(_env_file=env_file)
        else:
            config = SharedContextServerConfig()

        # Configure logging
        config.configure_logging()

        # Validate production settings
        if config.is_production():
            issues = config.validate_production_settings()
            if issues:
                raise ValueError(
                    f"Production configuration issues: {', '.join(issues)}"
                )

        logger.info(
            f"Configuration loaded successfully for {config.development.environment} environment"
        )
        return config

    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise ValueError(f"Configuration loading failed: {e}")


def reload_config() -> SharedContextServerConfig:
    """
    Reload global configuration from environment.

    Returns:
        SharedContextServerConfig: Reloaded configuration
    """
    global _config
    _config = None
    return get_config()


# Convenience functions for accessing configuration sections
def get_database_config() -> DatabaseConfig:
    """Get database configuration section."""
    return get_config().database


def get_security_config() -> SecurityConfig:
    """Get security configuration section."""
    return get_config().security


def get_operational_config() -> OperationalConfig:
    """Get operational configuration section."""
    return get_config().operational


def is_production() -> bool:
    """Check if running in production mode."""
    return get_config().is_production()


def is_development() -> bool:
    """Check if running in development mode."""
    return get_config().is_development()


# Configuration validation utilities
def validate_required_env_vars() -> None:
    """
    Validate that all required environment variables are set.

    Raises:
        ValueError: If required variables are missing
    """
    required_vars = ["API_KEY"]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(
            f"Required environment variables not set: {', '.join(missing_vars)}"
        )


def get_database_url() -> str:
    """
    Get database URL for connection.

    Returns:
        str: Database connection URL
    """
    config = get_database_config()

    # Prefer DATABASE_URL if set, otherwise use DATABASE_PATH
    if config.database_url:
        return config.database_url
    return f"sqlite:///{config.database_path}"
