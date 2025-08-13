"""
SQLAlchemy Core integration for Shared Context MCP Server.

This module provides a drop-in replacement for the aiosqlite database implementation
using SQLAlchemy Core. It maintains exact interface compatibility while enabling
future PostgreSQL support through SQLAlchemy's unified database interface.

Key features:
- Interface-compatible with existing aiosqlite patterns
- Supports all current database operations without changes to server.py
- Transaction handling that matches aiosqlite behavior
- Row factory compatibility for dict-like access
- Parameter binding translation between ? and SQLAlchemy formats
- Future-ready for PostgreSQL scaling if needed
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Iterator

    from sqlalchemy.engine import Result
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = logging.getLogger(__name__)


class CompatibleRow:
    """
    Row class that supports both index and key access for compatibility.

    This class bridges the gap between aiosqlite.Row (which supports both
    row[0] and row['column_name']) and SQLAlchemy Row objects.
    """

    def __init__(self, mapping_dict: dict[str, Any]):
        """Initialize with a dictionary from SQLAlchemy Row._mapping."""
        self._data = mapping_dict
        self._keys = list(mapping_dict.keys())
        self._values = list(mapping_dict.values())

    def __getitem__(self, key: int | str) -> Any:
        """Support both index and key access."""
        if isinstance(key, int):
            return self._values[key]
        return self._data[key]

    def __contains__(self, key: int | str) -> bool:
        """Support 'in' operator for key checking."""
        if isinstance(key, int):
            return 0 <= key < len(self._values)
        return key in self._data

    def __iter__(self) -> Iterator[Any]:
        """Support iteration over values (like tuple)."""
        return iter(self._values)

    def __len__(self) -> int:
        """Support len() for compatibility."""
        return len(self._values)

    def keys(self) -> Any:
        """Support .keys() method for dict-like access."""
        return self._data.keys()

    def values(self) -> Any:
        """Support .values() method for dict-like access."""
        return self._data.values()

    def items(self) -> Any:
        """Support .items() method for dict-like access."""
        return self._data.items()

    def __repr__(self) -> str:
        """String representation showing both interfaces."""
        return f"CompatibleRow({self._data})"


class SQLAlchemyCursorWrapper:
    """
    Wrapper to make SQLAlchemy Result look like aiosqlite Cursor.

    Provides interface compatibility for cursor.lastrowid, fetchone(), fetchall()
    operations that are used throughout server.py.
    """

    def __init__(self, result: Result[Any]):
        """Initialize cursor wrapper with SQLAlchemy result."""
        self._result = result
        self._lastrowid: int | None = None

        # Extract lastrowid if available (for INSERT operations)
        if hasattr(result, "lastrowid") and result.lastrowid is not None:
            self._lastrowid = result.lastrowid

    @property
    def lastrowid(self) -> int | None:
        """Return last inserted row ID, compatible with aiosqlite."""
        return self._lastrowid

    @property
    def rowcount(self) -> int:
        """Return number of affected rows, compatible with aiosqlite."""
        return getattr(self._result, "rowcount", 0)

    async def fetchone(self) -> CompatibleRow | None:
        """
        Fetch one row as CompatibleRow, compatible with aiosqlite.Row behavior.

        Returns:
            CompatibleRow representing row data or None if no rows available
        """
        try:
            row = self._result.fetchone()
            return CompatibleRow(dict(row._mapping)) if row else None
        except Exception:
            # If result is already consumed or not a select, return None
            return None

    async def fetchall(self) -> list[CompatibleRow]:
        """
        Fetch all rows as list of CompatibleRows, compatible with aiosqlite.Row behavior.

        Returns:
            List of CompatibleRows representing row data
        """
        try:
            rows = self._result.fetchall()
            return [CompatibleRow(dict(row._mapping)) for row in rows]
        except Exception:
            # If result is already consumed or not a select, return empty list
            return []


class SQLAlchemyConnectionWrapper:
    """
    Wrapper to make SQLAlchemy Connection look exactly like aiosqlite Connection.

    Provides interface compatibility for execute(), commit(), and close() operations
    while handling parameter translation and transaction management.
    """

    def __init__(self, engine: AsyncEngine, conn: AsyncConnection):
        """Initialize connection wrapper."""
        self.engine = engine
        self.conn = conn
        self.row_factory = None  # Compatibility with aiosqlite.Row assignment

    def _convert_params(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> tuple[str, dict[str, Any]]:
        """
        Convert aiosqlite-style ? parameters to SQLAlchemy named parameters.

        Args:
            query: SQL query with ? placeholders
            params: Tuple of parameter values

        Returns:
            Tuple of (converted_query, named_params_dict)
        """
        if not params:
            return query, {}

        # Convert ? placeholders to :param1, :param2, etc.
        converted_query = query
        named_params = {}

        param_count = 0
        while "?" in converted_query:
            param_count += 1
            param_name = f"param{param_count}"
            converted_query = converted_query.replace("?", f":{param_name}", 1)

            if param_count <= len(params):
                named_params[param_name] = params[param_count - 1]

        return converted_query, named_params

    async def execute(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> SQLAlchemyCursorWrapper:
        """
        Execute query with parameter translation.

        Args:
            query: SQL query string (with ? placeholders)
            params: Query parameters tuple

        Returns:
            SQLAlchemyCursorWrapper compatible with aiosqlite cursor
        """
        try:
            # Convert parameters from aiosqlite format to SQLAlchemy format
            converted_query, named_params = self._convert_params(query, params)

            # Execute query using SQLAlchemy text() for raw SQL
            result = await self.conn.execute(text(converted_query), named_params)

            return SQLAlchemyCursorWrapper(result)

        except Exception as e:
            logger.exception(f"Query execution failed: {query}")
            raise RuntimeError(f"Database query failed: {e}") from e

    async def executescript(self, script: str) -> None:
        """
        Execute SQL script (multiple statements).

        Args:
            script: SQL script with multiple statements
        """
        try:
            # Split script into individual statements
            statements = [stmt.strip() for stmt in script.split(";") if stmt.strip()]

            for statement in statements:
                if statement:
                    await self.conn.execute(text(statement))

        except Exception as e:
            logger.exception(f"Script execution failed: {script[:100]}...")
            raise RuntimeError(f"Database script execution failed: {e}") from e

    async def commit(self) -> None:
        """
        Handle transaction commit for SQLAlchemy.

        Note: In SQLAlchemy async context manager, commits are handled automatically
        at the end of the transaction block, but we provide this for compatibility.
        """
        # No-op for SQLAlchemy since transaction is committed automatically
        # when the context manager exits
        pass

    async def rollback(self) -> None:
        """
        Handle transaction rollback for SQLAlchemy.

        For compatibility with aiosqlite interface.
        """
        try:
            await self.conn.rollback()
        except Exception as e:
            logger.warning(f"Rollback failed: {e}")
            # Don't raise exception on rollback failure to maintain compatibility

    async def close(self) -> None:
        """
        Connection cleanup - handled by context manager.

        This is a no-op as the async context manager handles cleanup,
        but provided for interface compatibility.
        """
        pass


class SimpleSQLAlchemyManager:
    """
    Drop-in replacement for current database connection factory.

    Provides the same get_connection() context manager interface while using
    SQLAlchemy Core for database operations.
    """

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./chat_history.db"):
        """
        Initialize SQLAlchemy manager.

        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            # SQLite-specific options for compatibility
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.is_initialized = False

    async def initialize(self) -> None:
        """
        Initialize database with schema using a temporary aiosqlite connection.

        This leverages the existing DatabaseManager initialization logic
        to ensure the schema is properly applied.
        """
        if self.is_initialized:
            return

        # Extract the actual database file path from SQLAlchemy URL
        if self.database_url.startswith("sqlite+aiosqlite:///"):
            db_path = self.database_url[len("sqlite+aiosqlite:///") :]

            # Use the existing DatabaseManager for initialization
            # This ensures all PRAGMAs, schema, and validation work correctly
            from .database import DatabaseManager

            temp_manager = DatabaseManager(db_path)
            await temp_manager.initialize()

            self.is_initialized = True
        else:
            # For non-SQLite databases, we'd need different initialization
            raise NotImplementedError("Non-SQLite databases not yet supported")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[SQLAlchemyConnectionWrapper, None]:
        """
        Return connection wrapper that matches current interface exactly.

        Yields:
            SQLAlchemyConnectionWrapper: Connection compatible with aiosqlite.Connection
        """
        try:
            async with self.engine.connect() as conn, conn.begin():
                wrapper = SQLAlchemyConnectionWrapper(self.engine, conn)
                yield wrapper
        except Exception as e:
            logger.exception("SQLAlchemy connection failed")
            raise RuntimeError(f"Database connection failed: {e}") from e

    async def close(self) -> None:
        """Close the engine and all connections."""
        await self.engine.dispose()
