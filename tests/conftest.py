"""
Testing utilities for FastMCP-based shared context server.

Provides modern database testing infrastructure using real in-memory SQLite databases
instead of fragile hardcoded mocks. This approach ensures tests remain valid as
database schemas evolve and provides better test fidelity.
"""

import inspect
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
from pydantic.fields import FieldInfo

from shared_context_server.auth import AuthInfo
from shared_context_server.database import DatabaseManager


def extract_field_defaults(fastmcp_tool) -> dict[str, Any]:
    """
    Extract actual default values from a FastMCP tool function.

    FastMCP decorated functions have FieldInfo objects as defaults,
    but we need the actual default values for testing.

    Args:
        fastmcp_tool: A FastMCP FunctionTool object

    Returns:
        Dict mapping parameter names to their actual default values
    """
    defaults = {}
    sig = inspect.signature(fastmcp_tool.fn)

    for name, param in sig.parameters.items():
        if name == "ctx":  # Skip context parameter
            continue

        if isinstance(param.default, FieldInfo):
            # Extract the actual default from FieldInfo
            defaults[name] = param.default.default
        elif param.default is not inspect.Parameter.empty:
            defaults[name] = param.default

    return defaults


async def call_fastmcp_tool(fastmcp_tool, ctx, **kwargs):
    """
    Call a FastMCP tool function with proper default handling.

    This helper automatically extracts Field defaults and merges them
    with provided kwargs to avoid FieldInfo object issues.

    Args:
        fastmcp_tool: A FastMCP FunctionTool object
        ctx: Mock context object
        **kwargs: Arguments to pass to the function

    Returns:
        Result of the function call
    """
    # Get the actual defaults
    defaults = extract_field_defaults(fastmcp_tool)

    # Merge defaults with provided kwargs (kwargs override defaults)
    call_args = {**defaults, **kwargs}

    # Call the function with context as first parameter
    return await fastmcp_tool.fn(ctx, **call_args)


class MockContext:
    """Standard mock context for FastMCP testing."""

    def __init__(self, session_id="test_session", agent_id="test_agent"):
        self.session_id = session_id
        # Set up authentication using AuthInfo pattern
        self._auth_info = AuthInfo(
            jwt_validated=False,
            agent_id=agent_id,
            agent_type="test",
            permissions=["read", "write"],
            authenticated=True,
            auth_method="api_key",
            token_id=None,
        )

    # Backward compatibility properties for old attribute access
    @property
    def agent_id(self) -> str:
        return self._auth_info.agent_id

    @agent_id.setter
    def agent_id(self, value: str) -> None:
        self._auth_info.agent_id = value

    @property
    def agent_type(self) -> str:
        return self._auth_info.agent_type


# =============================================================================
# MODERN DATABASE TESTING INFRASTRUCTURE
# =============================================================================


@pytest.fixture(scope="function")
async def test_db_manager():
    """
    Create an isolated in-memory SQLite database manager for each test.

    This fixture provides a real database with the complete schema applied,
    ensuring tests work with actual database constraints and behaviors.
    Each test gets a clean database state.

    Yields:
        DatabaseManager: Initialized database manager with applied schema
    """
    # Create temporary database file for this test
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        temp_db_path = temp_db.name

    try:
        # Create database manager with temporary database
        db_manager = DatabaseManager(f"sqlite:///{temp_db_path}")

        # Initialize database with schema
        await db_manager.initialize()

        # Verify schema is correctly applied
        async with db_manager.get_connection() as conn:
            # Quick validation that our schema version is correct
            cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
            version = await cursor.fetchone()
            assert (
                version and version[0] == 2
            ), f"Expected schema version 2, got {version[0] if version else None}"

        yield db_manager

    finally:
        # Clean up temporary database file
        temp_path = Path(temp_db_path)
        if temp_path.exists():
            temp_path.unlink()


@pytest.fixture(scope="function")
async def test_db_connection(test_db_manager):
    """
    Provide a database connection for tests that need direct database access.

    Args:
        test_db_manager: The test database manager fixture

    Yields:
        aiosqlite.Connection: Database connection with optimized settings
    """
    async with test_db_manager.get_connection() as conn:
        yield conn


@asynccontextmanager
async def get_test_db_connection():
    """
    Get database connection using the test database manager.

    This function can be used to patch the global get_db_connection function
    in server modules during testing.

    Yields:
        aiosqlite.Connection: Test database connection
    """
    # This will be dynamically set by the test infrastructure
    # Each test should patch this appropriately
    raise RuntimeError("get_test_db_connection must be patched by test fixtures")


# =============================================================================
# TEST DATA UTILITIES
# =============================================================================


@pytest.fixture(scope="function")
async def seed_test_data(test_db_connection):
    """
    Seed the test database with common test data for comprehensive scenarios.

    Args:
        test_db_connection: Database connection fixture
    """
    # Create test sessions
    await test_db_connection.execute(
        """
        INSERT INTO sessions (id, purpose, created_by, metadata)
        VALUES (?, ?, ?, ?)
        """,
        ("session_test_1", "Test session 1", "test_agent", '{"test": true}'),
    )

    await test_db_connection.execute(
        """
        INSERT INTO sessions (id, purpose, created_by, metadata)
        VALUES (?, ?, ?, ?)
        """,
        ("session_test_2", "Test session 2", "another_agent", '{"test": true}'),
    )

    # Create test messages with proper schema (including sender_type)
    test_messages = [
        (
            "session_test_1",
            "test_agent",
            "test",
            "Public test message",
            "public",
            None,
            None,
        ),
        (
            "session_test_1",
            "test_agent",
            "test",
            "Private test message",
            "private",
            None,
            None,
        ),
        (
            "session_test_2",
            "another_agent",
            "test",
            "Another session message",
            "public",
            None,
            None,
        ),
    ]

    for msg_data in test_messages:
        await test_db_connection.execute(
            """
            INSERT INTO messages (session_id, sender, sender_type, content, visibility, metadata, parent_message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            msg_data,
        )

    # Create test agent memory
    await test_db_connection.execute(
        """
        INSERT INTO agent_memory (agent_id, session_id, key, value, metadata)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("test_agent", "session_test_1", "test_key", '{"test": "data"}', None),
    )

    await test_db_connection.commit()


# =============================================================================
# INTEGRATION WITH EXISTING FASTMCP PATTERNS
# =============================================================================


def patch_database_connection(test_db_manager):
    """
    Create a patcher for the global get_db_connection function.

    Args:
        test_db_manager: The test database manager to use

    Returns:
        unittest.mock.patch context manager
    """
    from unittest.mock import patch

    @asynccontextmanager
    async def mock_get_db_connection():
        async with test_db_manager.get_connection() as conn:
            yield conn

    return patch(
        "shared_context_server.server.get_db_connection", mock_get_db_connection
    )


# Example usage patterns for common tools:

# Use call_fastmcp_tool(tool_function, ctx, **kwargs) to call any MCP tool
# - create_session: purpose="Test session"
# - add_message: session_id, content, visibility
# - set_memory: key, value, session_id (optional)
# - search_context: session_id, query

# New database testing patterns:
# 1. Use test_db_manager fixture for isolated database testing
# 2. Use patch_database_connection(test_db_manager) to integrate with FastMCP tools
# 3. Use seed_test_data fixture for tests requiring pre-populated data
# 4. All tests automatically get clean database state with proper schema applied
