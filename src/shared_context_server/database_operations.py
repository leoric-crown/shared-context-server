"""
Database operations and schema management for Shared Context MCP Server.

This module handles:
- Schema loading and validation
- Database initialization logic
- Query execution utilities
- Schema version management
- PRAGMA validation

Extracted from database.py for better maintainability while preserving
all existing functionality and public interfaces.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import aiosqlite

from .database_connection import (
    get_db_connection,
)

logger = logging.getLogger(__name__)


async def initialize_database() -> None:
    """
    Initialize global database manager.

    Should be called during application startup.
    """
    # Import here to avoid circular dependency
    from .config import get_database_config
    from .database_connection import _get_sqlalchemy_manager, get_database_manager

    try:
        db_config = get_database_config()
        use_sqlalchemy = db_config.use_sqlalchemy
    except Exception:
        # Fallback to environment variable
        use_sqlalchemy = os.getenv("USE_SQLALCHEMY", "false").lower() == "true"

    if use_sqlalchemy:
        # Initialize SQLAlchemy backend
        sqlalchemy_manager = _get_sqlalchemy_manager()
        await sqlalchemy_manager.initialize()
    else:
        # Initialize aiosqlite backend
        db_manager = get_database_manager()
        await db_manager.initialize()


# Utility functions for common operations
async def execute_query(
    query: str, params: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    """
    Execute SELECT query and return results.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        List of result rows as dictionaries
    """
    async with get_db_connection() as conn:
        conn.row_factory = aiosqlite.Row  # Enable dict-like access
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def execute_update(query: str, params: tuple[Any, ...] = ()) -> int:
    """
    Execute UPDATE/INSERT/DELETE query.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        Number of affected rows
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(query, params)
        await conn.commit()
        return cursor.rowcount


async def execute_insert(query: str, params: tuple[Any, ...] = ()) -> int:
    """
    Execute INSERT query and return last row ID.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        Last inserted row ID
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(query, params)
        await conn.commit()
        return cursor.lastrowid or 0


# Migration utilities (for future schema changes)
async def get_schema_version() -> int:
    """
    Get current database schema version.

    Returns:
        Current schema version number
    """
    try:
        async with get_db_connection() as conn:
            cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
            result = await cursor.fetchone()

            if result is None:
                return 0

            # Handle different result formats (dict vs tuple)
            try:
                version = None
                if isinstance(result, dict):  # type: ignore[unreachable]
                    version = list(result.values())[0]  # type: ignore[unreachable]
                elif hasattr(result, "keys") and callable(
                    getattr(result, "keys", None)
                ):
                    try:
                        version = list(dict(result).values())[0]
                    except (TypeError, ValueError):
                        # Fallback to tuple access if dict conversion fails
                        version = result[0]
                else:  # Tuple or other sequence
                    version = result[0]

                return version if version is not None else 0
            except (KeyError, IndexError, TypeError):
                # If we can't extract a version, assume no schema
                return 0

    except Exception:
        return 0  # Schema version table doesn't exist
