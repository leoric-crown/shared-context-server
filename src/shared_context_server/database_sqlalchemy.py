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
from pathlib import Path
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

    def __init__(
        self, engine: AsyncEngine, conn: AsyncConnection, db_type: str = "sqlite"
    ):
        """Initialize connection wrapper."""
        self.engine = engine
        self.conn = conn
        self.row_factory = None  # Compatibility with aiosqlite.Row assignment
        self.db_type = db_type

    def _convert_params(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> tuple[str, dict[str, Any]]:
        """
        Convert aiosqlite-style ? parameters to SQLAlchemy named parameters.
        Also handles database-specific column name translations.

        Args:
            query: SQL query with ? placeholders
            params: Tuple of parameter values

        Returns:
            Tuple of (converted_query, named_params_dict)
        """
        # Handle MySQL column name translation (key -> key_name)
        if self.db_type == "mysql" and "agent_memory" in query.lower():
            # Replace references to agent_memory.key with agent_memory.key_name
            query = query.replace("agent_memory.key", "agent_memory.key_name")
            # Handle cases where 'key' is used in INSERT/UPDATE for agent_memory
            if "INSERT INTO agent_memory" in query and " key," in query:
                query = query.replace(" key,", " key_name,")
            if "INSERT INTO agent_memory" in query and " key)" in query:
                query = query.replace(" key)", " key_name)")
            # Handle WHERE clauses with key column
            if " key " in query and any(
                clause in query.lower() for clause in ["where", "and", "or"]
            ):
                query = query.replace(" key ", " key_name ")
            if " key=" in query:
                query = query.replace(" key=", " key_name=")
            # Handle UPDATE statements
            if "UPDATE agent_memory" in query and " key " in query:
                query = query.replace(" key ", " key_name ")

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
    Multi-database SQLAlchemy manager with URL-based database detection.

    Provides the same get_connection() context manager interface while using
    SQLAlchemy Core for database operations across SQLite, PostgreSQL, and MySQL.
    """

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./chat_history.db"):
        """
        Initialize SQLAlchemy manager with database detection.

        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url

        # Simple URL-based detection (KISS principle) - case insensitive
        url_lower = database_url.lower()
        if url_lower.startswith("sqlite+aiosqlite://"):
            self.db_type = "sqlite"
        elif url_lower.startswith("postgresql+asyncpg://"):
            self.db_type = "postgresql"
        elif url_lower.startswith("mysql+aiomysql://"):
            self.db_type = "mysql"
        else:
            raise ValueError(f"Unsupported database URL: {database_url}")

        # Database-specific engine configuration
        engine_config = self._get_engine_config()
        self.engine = create_async_engine(database_url, **engine_config)
        self.is_initialized = False

    def _get_engine_config(self) -> dict[str, Any]:
        """Return database-specific engine configuration."""
        if self.db_type == "sqlite":
            return {
                "pool_pre_ping": True,
                "pool_recycle": 3600,
                # Keep existing SQLite optimizations
            }
        if self.db_type == "postgresql":
            return {
                "pool_size": 20,
                "max_overflow": 30,
                "pool_recycle": 3600,
                "pool_pre_ping": True,
                "connect_args": {
                    "prepared_statement_cache_size": 500,
                    "server_settings": {
                        "jit": "off",  # Optimize performance
                        "application_name": "shared_context_mcp",
                    },
                },
            }
        if self.db_type == "mysql":
            return {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_recycle": 3600,  # Handle MySQL 8-hour timeout
                "pool_pre_ping": True,
                "connect_args": {
                    "charset": "utf8mb4",
                    "autocommit": False,
                    "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
                },
            }
        return {"pool_pre_ping": True, "pool_recycle": 3600}

    def _get_schema_file_path(self) -> Path:
        """Get the appropriate schema file path for the database type."""
        # Get the project root directory (where schema files are located)
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent

        if self.db_type == "sqlite":
            return project_root / "database_sqlite.sql"
        if self.db_type == "postgresql":
            return project_root / "database_postgresql.sql"
        if self.db_type == "mysql":
            return project_root / "database_mysql.sql"
        raise ValueError(f"No schema file for database type: {self.db_type}")

    async def _load_schema_file(self) -> str:
        """Load the appropriate schema file for the database type."""
        schema_file = self._get_schema_file_path()

        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        return schema_file.read_text(encoding="utf-8")

    async def initialize(self) -> None:
        """
        Initialize database with database-specific schema.
        """
        if self.is_initialized:
            return

        if self.db_type == "sqlite":
            # Use existing DatabaseManager for SQLite to preserve all optimizations
            db_path = self.database_url[len("sqlite+aiosqlite:///") :]
            from .database import DatabaseManager

            temp_manager = DatabaseManager(db_path)
            await temp_manager.initialize()
        else:
            # Initialize PostgreSQL/MySQL with database-specific schema
            try:
                schema_sql = await self._load_schema_file()

                # Execute schema using SQLAlchemy connection
                async with self.engine.connect() as conn, conn.begin():
                    # Split schema into individual statements for execution
                    statements = []
                    current_statement = []

                    for line in schema_sql.split("\n"):
                        line = line.strip()
                        if not line or line.startswith("--"):
                            continue

                        current_statement.append(line)

                        # Check for statement endings (semicolon not inside function/trigger)
                        if line.endswith(";") and not self._is_inside_function_block(
                            current_statement
                        ):
                            statements.append("\n".join(current_statement))
                            current_statement = []

                    # Execute each statement
                    for statement in statements:
                        if statement.strip():
                            try:
                                await conn.execute(text(statement))
                            except Exception as e:
                                logger.warning(
                                    f"Failed to execute statement (continuing): {e}"
                                )
                                # Continue with other statements, some might be idempotent

                logger.info(
                    f"Initialized {self.db_type} database with {len(statements)} statements"
                )

            except Exception as e:
                logger.exception(f"Failed to initialize {self.db_type} database")
                raise RuntimeError(f"Database initialization failed: {e}") from e

        self.is_initialized = True

    def _is_inside_function_block(self, statement_lines: list[str]) -> bool:
        """Check if we're inside a PostgreSQL function or MySQL procedure block."""
        full_statement = "\n".join(statement_lines).upper()

        # PostgreSQL function/trigger patterns
        if (
            "CREATE OR REPLACE FUNCTION" in full_statement
            or "CREATE FUNCTION" in full_statement
        ):
            return "$$" not in full_statement or full_statement.count("$$") < 2

        if "CREATE TRIGGER" in full_statement:
            return "END;" not in full_statement

        # MySQL procedure patterns
        if "CREATE PROCEDURE" in full_statement or "CREATE FUNCTION" in full_statement:
            return "END" not in full_statement

        return False

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[SQLAlchemyConnectionWrapper, None]:
        """
        Return connection wrapper that matches current interface exactly.

        Yields:
            SQLAlchemyConnectionWrapper: Connection compatible with aiosqlite.Connection
        """
        try:
            async with self.engine.connect() as conn, conn.begin():
                wrapper = SQLAlchemyConnectionWrapper(self.engine, conn, self.db_type)
                yield wrapper
        except Exception as e:
            logger.exception("SQLAlchemy connection failed")
            raise RuntimeError(f"Database connection failed: {e}") from e

    async def close(self) -> None:
        """Close the engine and all connections."""
        await self.engine.dispose()
