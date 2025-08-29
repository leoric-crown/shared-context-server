"""
Startup Validation Module - Environment validation and system checks.

This module contains the startup validation logic extracted from the monolithic
cli.py, providing comprehensive environment validation and configuration checks.
"""

import logging
import os
import sys
from typing import Any

from .utils import Colors, print_color

logger = logging.getLogger(__name__)


async def validate_environment() -> bool:
    """
    Comprehensive environment validation.

    Validates critical configuration requirements at startup to ensure
    the server fails fast with helpful error messages if essential
    configuration is missing.

    Returns:
        True if environment validation passes, exits process on failure
    """
    logger.info("Validating startup configuration...")

    # Check JWT encryption key (required for authentication)
    jwt_encryption_key = os.getenv("JWT_ENCRYPTION_KEY")
    if not jwt_encryption_key:
        _show_jwt_encryption_key_error()
        sys.exit(1)

    # Validate JWT encryption key format (should be a valid Fernet key)
    if not _validate_jwt_key_format(jwt_encryption_key):
        _show_jwt_format_error()
        sys.exit(1)

    logger.info("✅ Startup configuration validation completed")
    return True


def check_dependencies() -> dict[str, Any]:
    """
    Dependency verification and reporting.

    Returns:
        Dictionary with dependency status information
    """
    dependencies = {}

    # Check cryptography package
    try:
        import cryptography.fernet  # noqa: F401

        dependencies["cryptography"] = {"available": True, "version": "installed"}
    except ImportError:
        dependencies["cryptography"] = {
            "available": False,
            "error": "Missing cryptography package",
        }

    # Check uvloop availability
    try:
        import uvloop  # noqa: F401

        dependencies["uvloop"] = {"available": True, "version": "installed"}
    except ImportError:
        dependencies["uvloop"] = {"available": False, "error": "uvloop not available"}

    return dependencies


def validate_configuration() -> tuple[bool, list[str]]:
    """
    Configuration validation with error details.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # JWT configuration validation
    if not os.getenv("JWT_ENCRYPTION_KEY"):
        errors.append("Missing JWT_ENCRYPTION_KEY environment variable")

    if not os.getenv("JWT_SECRET_KEY"):
        errors.append("Missing JWT_SECRET_KEY environment variable")

    # Database configuration validation
    database_url = os.getenv("DATABASE_URL")
    if database_url and not _validate_database_url(database_url):
        errors.append("Invalid DATABASE_URL format")

    return len(errors) == 0, errors


def _validate_jwt_key_format(jwt_key: str) -> bool:
    """Validate JWT encryption key format."""
    try:
        from cryptography.fernet import Fernet

        Fernet(jwt_key.encode())
        return True
    except Exception:
        return False


def _validate_database_url(url: str) -> bool:
    """Validate database URL format."""
    # Basic validation - should start with supported schemes
    supported_schemes = [
        "sqlite://",
        "sqlite+aiosqlite://",
        "postgresql://",
        "mysql://",
    ]
    return any(url.startswith(scheme) for scheme in supported_schemes)


def _show_jwt_encryption_key_error() -> None:
    """Show JWT encryption key missing error."""
    colors = Colors()

    print_color("", colors.RED)
    print_color("🔐 CONFIGURATION ERROR: Missing JWT encryption key", colors.RED)
    print_color("", colors.RED)
    print_color("JWT_ENCRYPTION_KEY is required for secure authentication.", colors.RED)
    print_color("The server cannot start without this key.", colors.RED)
    print_color("", colors.RED)
    print_color("Quick fixes:", colors.RED)
    print_color("  1. Generate secure keys:", colors.RED)
    print_color("     scs setup", colors.RED)
    print_color("", colors.RED)
    print_color("  2. Copy the generated configuration:", colors.RED)
    print_color("     cp .env.generated .env", colors.RED)
    print_color("", colors.RED)
    print_color("  3. Or set the environment variable:", colors.RED)
    print_color("     export JWT_ENCRYPTION_KEY='your-fernet-key-here'", colors.RED)
    print_color("", colors.RED)


def _show_jwt_format_error() -> None:
    """Show JWT format validation error."""
    colors = Colors()

    print_color("", colors.RED)
    print_color("🔐 CONFIGURATION ERROR: Invalid JWT encryption key format", colors.RED)
    print_color("", colors.RED)
    print_color("JWT_ENCRYPTION_KEY must be a valid Fernet key.", colors.RED)
    print_color("", colors.RED)
    print_color("Quick fix:", colors.RED)
    print_color("  scs setup", colors.RED)
    print_color("  cp .env.generated .env", colors.RED)
    print_color("", colors.RED)
