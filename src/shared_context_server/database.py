"""
Unified database connection management for Shared Context MCP Server.

This module addresses critical issues identified in consultant review:
- Enables foreign keys on every connection
- Applies optimized PRAGMA settings consistently
- Provides unified connection factory with proper lifecycle
- Handles UTC timestamp operations correctly
- Includes connection pooling support for concurrent agents

FACADE MODULE: This file maintains 100% backward compatibility while delegating
to specialized submodules for better maintainability. All existing imports and
function signatures are preserved exactly.

Modular Structure:
- database_connection.py: Connection management and DatabaseManager class
- database_operations.py: Schema management and query utilities
- database_utilities.py: Health checks, cleanup, and validation helpers
"""

# Import all public functions and classes to maintain 100% backward compatibility

# From database_connection.py - Connection management
from .database_connection import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseManager,
    DatabaseSchemaError,
    _get_sqlalchemy_manager,
    _is_testing_environment,
    _raise_journal_mode_check_error,
    _raise_no_schema_version_error,
    _raise_table_not_found_error,
    _raise_wal_mode_error,
    adapt_datetime_iso,
    convert_datetime,
    get_database_manager,
    get_db_connection,
)

# From database_operations.py - Operations and utilities
from .database_operations import (
    execute_insert,
    execute_query,
    execute_update,
    get_schema_version,
    initialize_database,
)

# From database_utilities.py - Utilities and helpers
from .database_utilities import (
    _raise_basic_query_error,
    cleanup_expired_data,
    health_check,
    parse_utc_timestamp,
    utc_now,
    utc_timestamp,
    validate_json_string,
    validate_session_id,
)

# Export all public items for backward compatibility
__all__ = [
    # Exception classes
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseSchemaError",
    # Main classes
    "DatabaseManager",
    # DateTime utilities
    "adapt_datetime_iso",
    "convert_datetime",
    "utc_now",
    "utc_timestamp",
    "parse_utc_timestamp",
    # Connection management
    "get_database_manager",
    "get_db_connection",
    "initialize_database",
    # Query operations
    "execute_query",
    "execute_update",
    "execute_insert",
    # Schema management
    "get_schema_version",
    # Validation utilities
    "validate_session_id",
    "validate_json_string",
    # Health and maintenance
    "health_check",
    "cleanup_expired_data",
    # Private functions (preserved for backward compatibility)
    "_get_sqlalchemy_manager",
    "_is_testing_environment",
    "_raise_wal_mode_error",
    "_raise_journal_mode_check_error",
    "_raise_table_not_found_error",
    "_raise_no_schema_version_error",
    "_raise_basic_query_error",
]
