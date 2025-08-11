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
from typing import Any, Literal

import dotenv
from pydantic import Field, field_serializer, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Load .env file at module level
dotenv.load_dotenv()


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""

    # Database connection
    database_path: str = Field(
        default="./chat_history.db", json_schema_extra={"env": "DATABASE_PATH"}
    )
    database_url: str | None = Field(
        default=None, json_schema_extra={"env": "DATABASE_URL"}
    )
    database_timeout: int = Field(
        default=30, json_schema_extra={"env": "DATABASE_TIMEOUT"}
    )
    database_busy_timeout: int = Field(
        default=5, json_schema_extra={"env": "DATABASE_BUSY_TIMEOUT"}
    )

    # Connection pooling
    database_max_connections: int = Field(
        default=20, json_schema_extra={"env": "DATABASE_MAX_CONNECTIONS"}
    )
    database_min_connections: int = Field(
        default=2, json_schema_extra={"env": "DATABASE_MIN_CONNECTIONS"}
    )

    # Retention policies
    audit_log_retention_days: int = Field(
        default=30, json_schema_extra={"env": "AUDIT_LOG_RETENTION_DAYS"}
    )
    inactive_session_retention_days: int = Field(
        default=7, json_schema_extra={"env": "INACTIVE_SESSION_RETENTION_DAYS"}
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
    mcp_server_name: str = Field(
        default="shared-context-server", json_schema_extra={"env": "MCP_SERVER_NAME"}
    )
    mcp_server_version: str = Field(
        default="1.0.0",
        json_schema_extra={"env": "MCP_SERVER_VERSION"},
    )

    # Transport configuration
    mcp_transport: Literal["stdio", "http"] = Field(
        default="stdio", json_schema_extra={"env": "MCP_TRANSPORT"}
    )
    http_host: str = Field(default="localhost", json_schema_extra={"env": "HTTP_HOST"})
    http_port: int = Field(default=8000, json_schema_extra={"env": "HTTP_PORT"})

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
    api_key: str = Field(json_schema_extra={"env": "API_KEY"})
    jwt_secret_key: str | None = Field(
        default=None, json_schema_extra={"env": "JWT_SECRET_KEY"}
    )
    jwt_expiration_time: int = Field(
        default=86400, json_schema_extra={"env": "JWT_EXPIRATION_TIME"}
    )

    # Session security
    session_timeout: int = Field(
        default=3600, json_schema_extra={"env": "SESSION_TIMEOUT"}
    )
    max_sessions_per_agent: int = Field(
        default=50, json_schema_extra={"env": "MAX_SESSIONS_PER_AGENT"}
    )

    # CORS settings
    cors_origins: str = Field(default="*", json_schema_extra={"env": "CORS_ORIGINS"})
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1", json_schema_extra={"env": "ALLOWED_HOSTS"}
    )

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in v.split(",")]

    @field_serializer("cors_origins")
    def serialize_cors_origins(self, v: list[str]) -> str:
        """Serialize CORS origins list back to comma-separated string."""
        return ",".join(v)

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Ensure API key is secure with helpful error messages."""
        if not v:
            raise ValueError(
                "❌ API_KEY environment variable is required!\n\n"
                "Quick fix:\n"
                "  1. Generate a secure key: openssl rand -base64 32\n"
                "  2. Add to .env: API_KEY=your-generated-key-here\n"
                "  3. Restart the server\n"
            )

        # Allow insecure key only in development
        if v == "your-secure-api-key-replace-this-in-production":
            import os

            env_mode = os.getenv("ENVIRONMENT", "development")
            if env_mode == "production":
                raise ValueError(
                    "❌ Default API_KEY detected in production!\n\n"
                    "Security risk: Using the default API_KEY in production.\n"
                    "Quick fix:\n"
                    "  1. Generate secure key: openssl rand -base64 32\n"
                    "  2. Update .env: API_KEY=your-new-secure-key\n"
                    "  3. Restart the server\n"
                )
            logger.warning("Using default API_KEY - only suitable for development")

        if len(v) < 32 and v not in [
            "your-secure-api-key-replace-this-in-production",
            "test-api-key-for-ci-only",
        ]:
            logger.warning(
                "⚠️ API_KEY should be at least 32 characters for security. Generate with: openssl rand -base64 32"
            )
        return v


class OperationalConfig(BaseSettings):
    """Operational and monitoring configuration."""

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", json_schema_extra={"env": "LOG_LEVEL"}
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        json_schema_extra={"env": "LOG_FORMAT"},
    )
    database_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", json_schema_extra={"env": "DATABASE_LOG_LEVEL"}
    )

    # Performance monitoring
    enable_performance_monitoring: bool = Field(
        default=True, json_schema_extra={"env": "ENABLE_PERFORMANCE_MONITORING"}
    )
    performance_log_interval: int = Field(
        default=300, json_schema_extra={"env": "PERFORMANCE_LOG_INTERVAL"}
    )

    # Resource limits
    max_memory_entries_per_agent: int = Field(
        default=1000, json_schema_extra={"env": "MAX_MEMORY_ENTRIES_PER_AGENT"}
    )
    max_memory_size_mb: int = Field(
        default=100, json_schema_extra={"env": "MAX_MEMORY_SIZE_MB"}
    )
    max_message_length: int = Field(
        default=100000, json_schema_extra={"env": "MAX_MESSAGE_LENGTH"}
    )
    max_messages_per_session: int = Field(
        default=10000, json_schema_extra={"env": "MAX_MESSAGES_PER_SESSION"}
    )
    max_metadata_size_kb: int = Field(
        default=10, json_schema_extra={"env": "MAX_METADATA_SIZE_KB"}
    )

    # Cleanup settings
    enable_automatic_cleanup: bool = Field(
        default=True, json_schema_extra={"env": "ENABLE_AUTOMATIC_CLEANUP"}
    )
    cleanup_interval: int = Field(
        default=3600, json_schema_extra={"env": "CLEANUP_INTERVAL"}
    )


class DevelopmentConfig(BaseSettings):
    """Development and debugging configuration."""

    # Environment mode
    environment: Literal["development", "testing", "production"] = Field(
        default="development", json_schema_extra={"env": "ENVIRONMENT"}
    )
    debug: bool = Field(default=False, json_schema_extra={"env": "DEBUG"})
    enable_debug_tools: bool = Field(
        default=False, json_schema_extra={"env": "ENABLE_DEBUG_TOOLS"}
    )

    # Development database
    dev_reset_database_on_start: bool = Field(
        default=False, json_schema_extra={"env": "DEV_RESET_DATABASE_ON_START"}
    )
    dev_seed_test_data: bool = Field(
        default=False, json_schema_extra={"env": "DEV_SEED_TEST_DATA"}
    )
    test_database_path: str = Field(
        default="./test_chat_history.db",
        json_schema_extra={"env": "TEST_DATABASE_PATH"},
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

    def __init__(self, **kwargs: Any) -> None:
        """Initialize configuration with proper section instantiation."""
        # Initialize sub-configurations
        if "database" not in kwargs:
            kwargs["database"] = DatabaseConfig()
        if "mcp_server" not in kwargs:
            kwargs["mcp_server"] = MCPServerConfig()
        if "security" not in kwargs:
            kwargs["security"] = SecurityConfig(
                api_key=os.getenv("API_KEY", "default-dev-key")
            )
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
        # Note: BasicConfig is handled by individual scripts to avoid conflicts
        # This method only configures library-specific loggers

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
_config: SharedContextServerConfig | None = None


def _raise_production_config_error(issues: list[str]) -> None:
    """Raise a production configuration error."""
    raise ValueError(f"Production configuration issues: {', '.join(issues)}")


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


def load_config(env_file: str | None = None) -> SharedContextServerConfig:
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
                _raise_production_config_error(issues)

        logger.info(
            f"Configuration loaded successfully for {config.development.environment} environment"
        )

    except Exception as e:
        logger.exception("Failed to load configuration")
        raise ValueError(f"Configuration loading failed: {e}") from e
    else:
        return config


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
        ValueError: If required variables are missing with helpful setup instructions
    """
    required_vars = {
        "API_KEY": "Secure API key for agent authentication (generate with: openssl rand -base64 32)"
    }

    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  • {var}: {description}")

    if missing_vars:
        error_msg = (
            "❌ Required environment variables are missing!\n\n"
            + "Missing variables:\n"
            + "\n".join(missing_vars)
            + "\n\nQuick fix:\n"
            + "  1. Copy .env.example to .env\n"
            + "  2. Set the required variables in .env\n"
            + "  3. For API_KEY, run: openssl rand -base64 32\n\n"
            + "Example .env content:\n"
            + "  API_KEY=your-secure-random-key-here\n"
            + "  DATABASE_PATH=./chat_history.db\n"
            + "  ENVIRONMENT=development\n"
        )
        raise ValueError(error_msg)


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
