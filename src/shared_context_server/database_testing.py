"""
Simplified database testing infrastructure for shared context server.

This module provides testing utilities for the SQLAlchemy-only database backend,
eliminating dual-backend complexity while maintaining test isolation and reliability.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from .database_manager import SimpleSQLAlchemyManager, SQLAlchemyConnectionWrapper

logger = logging.getLogger(__name__)


class TestDatabaseManager:
    """
    Simplified SQLAlchemy-based test database manager.
    
    Uses temporary SQLite files for testing to ensure schema persistence
    and proper cleanup without the complexity of dual backends.
    """
    
    def __init__(self, database_url: str = "sqlite:///:memory:") -> None:
        """
        Initialize test database manager.
        
        Args:
            database_url: Database URL (defaults to memory database)
        """
        # Create temporary file for SQLite testing
        self._temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=True)
        self.database_path = self._temp_file.name
        
        # Create SQLAlchemy manager with temporary database
        test_url = f"sqlite+aiosqlite:///{self.database_path}"
        self._manager = SimpleSQLAlchemyManager(test_url)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize test database with schema."""
        if not self._initialized:
            await self._manager.initialize()
            self._initialized = True
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[SQLAlchemyConnectionWrapper, None]:
        """Get test database connection."""
        if not self._initialized:
            await self.initialize()
        
        async with self._manager.get_connection() as conn:
            # Enable dict-like row access for testing compatibility
            conn.row_factory = lambda row: row  # Use raw SQLAlchemy row
            yield conn
    
    async def close(self) -> None:
        """Close test database and clean up resources."""
        if self._manager:
            await self._manager.close()
        
        if hasattr(self, '_temp_file'):
            self._temp_file.close()
    
    def get_stats(self) -> dict[str, Any]:
        """Get test database statistics."""
        return {
            "database_path": self.database_path,
            "is_initialized": self._initialized,
            "connection_count": 1,  # Simplified for testing
            "database_exists": True,
            "database_size_mb": 0.1,  # Minimal for testing
        }


@asynccontextmanager
async def patch_database_connection(
    test_db_manager: TestDatabaseManager,
) -> AsyncGenerator[None, None]:
    """
    Patch database connection to use test database.
    
    Simplified version that only supports SQLAlchemy backend testing.
    
    Args:
        test_db_manager: Test database manager to use
    """
    # Import here to avoid circular imports
    from . import database_manager
    
    # Store original manager function
    original_get_manager = database_manager.get_sqlalchemy_manager
    
    # Patch to return test manager
    database_manager.get_sqlalchemy_manager = lambda: test_db_manager._manager
    
    try:
        # Initialize test database
        await test_db_manager.initialize()
        yield
    finally:
        # Restore original function
        database_manager.get_sqlalchemy_manager = original_get_manager
        # Clean up test database
        await test_db_manager.close()