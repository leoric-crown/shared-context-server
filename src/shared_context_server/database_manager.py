"""
SQLAlchemy-based database connection management for Shared Context MCP Server.

This module provides unified database connection management using SQLAlchemy Core,
eliminating the dual-backend complexity. All connections use SQLAlchemy with
asyncpg for PostgreSQL or aiosqlite for SQLite databases.

Key features:
- ContextVar-based connection management for thread safety
- Connection pooling and lifecycle management  
- SQLAlchemy-optimized configuration
- Schema validation and recovery
- Performance monitoring and statistics
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import weakref
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime as dt
from datetime import timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class DatabaseSchemaError(DatabaseError):
    """Exception raised when database schema validation fails."""
    pass


# SQLite PRAGMA settings optimized for production performance
_SQLITE_PRAGMAS = [
    "PRAGMA foreign_keys = ON;",  # Critical: Enable foreign key constraints
    "PRAGMA journal_mode = WAL;",  # Write-Ahead Logging for concurrency
    "PRAGMA synchronous = NORMAL;",  # Balance performance and safety
    "PRAGMA cache_size = -8000;",  # 8MB cache per connection
    "PRAGMA temp_store = MEMORY;",  # Use memory for temporary tables
    "PRAGMA mmap_size = 268435456;",  # 256MB memory mapping
    "PRAGMA busy_timeout = 5000;",  # 5 second timeout for busy database
    "PRAGMA optimize;",  # Enable query optimizer
]


def _is_testing_environment() -> bool:
    """Check if running in testing environment."""
    import sys
    return bool(
        "pytest" in sys.modules
        or os.getenv("CI")
        or os.getenv("GITHUB_ACTIONS")
        or os.getenv("PYTEST_CURRENT_TEST")
    )


class CompatibleRow:
    """Row wrapper that supports both index and key access for compatibility."""
    
    def __init__(self, sqlalchemy_row: Any) -> None:
        self._row = sqlalchemy_row
        self._keys = list(sqlalchemy_row.keys()) if hasattr(sqlalchemy_row, 'keys') else []
    
    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, int):
            return self._row[key] if hasattr(self._row, '__getitem__') else list(self._row)[key]
        return self._row[key]
    
    def __iter__(self):
        return iter(self._row)
    
    def keys(self):
        return self._keys
    
    def values(self):
        return [self._row[key] for key in self._keys]


class SQLAlchemyConnectionWrapper:
    """Connection wrapper that provides aiosqlite-compatible interface."""
    
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection
        self.row_factory = None
    
    async def execute(self, query: str, parameters: tuple[Any, ...] = ()) -> SQLAlchemyCursorWrapper:
        """Execute SQL query with parameter binding."""
        # Convert ? placeholders to SQLAlchemy :param format
        converted_query, converted_params = self._convert_query_params(query, parameters)
        result = await self._connection.execute(text(converted_query), converted_params)
        return SQLAlchemyCursorWrapper(result, self.row_factory)
    
    async def commit(self) -> None:
        """Commit transaction."""
        await self._connection.commit()
    
    def _convert_query_params(self, query: str, params: tuple[Any, ...]) -> tuple[str, dict[str, Any]]:
        """Convert ? placeholders to SQLAlchemy named parameters."""
        if not params:
            return query, {}
        
        converted_query = query
        converted_params = {}
        
        for i, param in enumerate(params):
            param_name = f"param_{i}"
            converted_query = converted_query.replace("?", f":{param_name}", 1)
            converted_params[param_name] = param
        
        return converted_query, converted_params


class SQLAlchemyCursorWrapper:
    """Cursor wrapper that provides aiosqlite-compatible interface."""
    
    def __init__(self, result: Any, row_factory: Any = None) -> None:
        self._result = result
        self._row_factory = row_factory
        self.rowcount = result.rowcount
        self.lastrowid = result.lastrowid
    
    async def fetchone(self) -> CompatibleRow | None:
        """Fetch one row."""
        row = self._result.fetchone()
        if row is None:
            return None
        
        if self._row_factory:
            return CompatibleRow(row)
        return row
    
    async def fetchall(self) -> list[CompatibleRow]:
        """Fetch all rows."""
        rows = self._result.fetchall()
        if self._row_factory:
            return [CompatibleRow(row) for row in rows]
        return rows


class SimpleSQLAlchemyManager:
    """Simplified SQLAlchemy connection manager for single-backend architecture."""
    
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine: AsyncEngine | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the SQLAlchemy engine with optimized settings."""
        if self._initialized:
            return
        
        async with self._init_lock:
            if self._initialized:
                return
            
            # Create engine with optimized settings
            if "sqlite" in self.database_url.lower():
                # SQLite doesn't support connection pooling
                self.engine = create_async_engine(
                    self.database_url,
                    echo=False,
                    connect_args={"check_same_thread": False, "timeout": 30},
                )
            else:
                # PostgreSQL/MySQL with connection pooling
                self.engine = create_async_engine(
                    self.database_url,
                    echo=False,
                    pool_size=10,
                    max_overflow=20,
                    pool_timeout=30,
                    pool_recycle=3600,
                )
            
            # Apply SQLite PRAGMA settings if using SQLite
            if "sqlite" in self.database_url:
                @event.listens_for(self.engine.sync_engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    for pragma in _SQLITE_PRAGMAS:
                        cursor.execute(pragma)
                    cursor.close()
            
            # Initialize schema
            await self._initialize_schema()
            self._initialized = True
            logger.info("SQLAlchemy engine initialized successfully")
    
    async def _initialize_schema(self) -> None:
        """Initialize database schema if needed."""
        if not self.engine:
            raise DatabaseConnectionError("Engine not initialized")
        
        # Load and execute schema if database doesn't exist or is empty
        async with self.engine.begin() as conn:
            # Check if schema_version table exists
            result = await conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            ))
            
            if not result.fetchone():
                # Schema doesn't exist, create it
                schema_path = self._get_schema_path()
                if schema_path.exists():
                    schema_sql = schema_path.read_text()
                    # Split and execute schema statements, filtering properly
                    statements = []
                    current_statement = []
                    in_trigger = False
                    
                    for line in schema_sql.split('\n'):
                        line = line.strip()
                        
                        # Skip empty lines and comments
                        if not line or line.startswith('--'):
                            continue
                        
                        # Handle trigger blocks (BEGIN...END)
                        if 'CREATE TRIGGER' in line.upper():
                            in_trigger = True
                            current_statement = [line]
                        elif in_trigger:
                            current_statement.append(line)
                            if line.upper().startswith('END'):
                                # Complete trigger statement
                                statements.append('\n'.join(current_statement))
                                current_statement = []
                                in_trigger = False
                        else:
                            # Regular statement
                            current_statement.append(line)
                            if line.endswith(';'):
                                # Complete statement
                                stmt = '\n'.join(current_statement).rstrip(';')
                                if stmt:
                                    statements.append(stmt)
                                current_statement = []
                    
                    # Add any remaining statement
                    if current_statement:
                        stmt = '\n'.join(current_statement).rstrip(';')
                        if stmt:
                            statements.append(stmt)
                    
                    # Execute each statement
                    for statement in statements:
                        try:
                            await conn.execute(text(statement))
                        except Exception as e:
                            logger.warning(f"Failed to execute schema statement: {e}")
                            logger.debug(f"Statement: {statement}")
                    
                    logger.info("Database schema initialized from SQL file")
    
    def _get_schema_path(self) -> Path:
        """Get path to schema SQL file."""
        # Look for schema file relative to project root
        current_dir = Path(__file__).parent
        schema_file = "database_sqlite.sql"
        
        # Try project root first
        project_root = current_dir.parent.parent
        schema_path = project_root / schema_file
        if schema_path.exists():
            return schema_path
        
        # Fall back to current directory
        return current_dir / schema_file
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[SQLAlchemyConnectionWrapper, None]:
        """Get database connection with automatic cleanup."""
        if not self.engine:
            await self.initialize()
        
        if not self.engine:
            raise DatabaseConnectionError("Failed to initialize engine")
        
        async with self.engine.begin() as conn:
            wrapper = SQLAlchemyConnectionWrapper(conn)
            try:
                yield wrapper
            except Exception:
                # Connection will be automatically rolled back by SQLAlchemy
                raise
    
    async def close(self) -> None:
        """Close the SQLAlchemy engine and clean up resources."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self._initialized = False


# ContextVar-based manager for thread-safe database access
_sqlalchemy_manager_context: ContextVar[SimpleSQLAlchemyManager | None] = ContextVar(
    "sqlalchemy_manager_context", default=None
)

# Global tracking for manager disposal (prevents memory leaks)
_global_sqlalchemy_managers: set[SimpleSQLAlchemyManager] = set()
_global_managers_lock = threading.Lock()


def get_sqlalchemy_manager() -> SimpleSQLAlchemyManager:
    """Get thread-local SQLAlchemy manager instance."""
    manager = _sqlalchemy_manager_context.get()
    
    if manager is None:
        # Import here to avoid circular dependency
        from .config import get_database_config
        
        try:
            db_config = get_database_config()
            
            # Determine database URL for SQLAlchemy
            if db_config.database_url:
                database_url = db_config.database_url
                # Convert sqlite:// to sqlite+aiosqlite:// if needed
                if database_url.startswith("sqlite://"):
                    database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
            else:
                # Convert database_path to SQLAlchemy URL
                database_url = f"sqlite+aiosqlite:///{db_config.database_path}"
            
            manager = SimpleSQLAlchemyManager(database_url)
            
        except Exception:
            # Fallback to environment variables
            database_url = os.getenv("DATABASE_URL") or ""
            if database_url:
                # Convert sqlite:// to sqlite+aiosqlite:// if needed
                if database_url.startswith("sqlite://"):
                    database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
                manager = SimpleSQLAlchemyManager(database_url)
            else:
                # Fallback to database path
                database_path = os.getenv("DATABASE_PATH", "./chat_history.db")
                database_url = f"sqlite+aiosqlite:///{database_path}"
                manager = SimpleSQLAlchemyManager(database_url)
            logger.warning("Using fallback SQLAlchemy database configuration")
        
        _sqlalchemy_manager_context.set(manager)
        
        # Register manager globally for comprehensive disposal
        with _global_managers_lock:
            _global_sqlalchemy_managers.add(manager)
    
    return manager


async def dispose_current_sqlalchemy_manager() -> None:
    """Dispose SQLAlchemy manager in current context."""
    manager = _sqlalchemy_manager_context.get()
    
    if manager is not None:
        try:
            await manager.close()
            # Remove from global tracking
            with _global_managers_lock:
                _global_sqlalchemy_managers.discard(manager)
        except Exception as e:
            logger.warning(f"Failed to dispose SQLAlchemy manager: {e}")
        finally:
            _sqlalchemy_manager_context.set(None)


async def dispose_all_sqlalchemy_managers() -> None:
    """Dispose ALL SQLAlchemy managers across all contexts."""
    disposed_count = 0
    
    # Get copy of managers to avoid modification during iteration
    with _global_managers_lock:
        managers_to_dispose = list(_global_sqlalchemy_managers)
        _global_sqlalchemy_managers.clear()
    
    # Dispose all managers
    for manager in managers_to_dispose:
        try:
            await manager.close()
            disposed_count += 1
        except Exception as e:
            logger.warning(f"Failed to dispose SQLAlchemy manager {id(manager)}: {e}")
    
    # Clear current context as well
    _sqlalchemy_manager_context.set(None)
    
    logger.info(f"Disposed {disposed_count} SQLAlchemy managers")


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[SQLAlchemyConnectionWrapper, None]:
    """Get database connection using SQLAlchemy backend."""
    sqlalchemy_manager = get_sqlalchemy_manager()
    
    async with sqlalchemy_manager.get_connection() as conn:
        # Enable dict-like row access by default
        conn.row_factory = CompatibleRow
        yield conn


# DateTime handling utilities for backward compatibility
def adapt_datetime_iso(val: dt) -> str:
    """Adapt datetime to ISO format string."""
    return val.isoformat()


def convert_datetime(val: bytes) -> dt:
    """Convert ISO format string or Unix timestamp to datetime."""
    decoded_val = val.decode()
    
    # Handle Unix timestamp format
    try:
        timestamp = float(decoded_val)
        return dt.fromtimestamp(timestamp, timezone.utc)
    except ValueError:
        pass
    
    # Handle ISO format string
    try:
        return dt.fromisoformat(decoded_val)
    except ValueError:
        if decoded_val.endswith("Z"):
            return dt.fromisoformat(decoded_val[:-1] + "+00:00")
        raise