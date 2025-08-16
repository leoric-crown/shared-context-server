#!/usr/bin/env python3
"""
Search function wrapper for testing with direct database connection injection.
"""

from typing import Any

from shared_context_server.server import search_context as original_search_context
from tests.conftest import MockContext, call_fastmcp_tool


async def search_context_with_test_db(
    ctx: MockContext,
    test_db_connection: Any,
    session_id: str,
    query: str,
    fuzzy_threshold: float = 60.0,
    limit: int = 10,
    search_metadata: bool = True,
    search_scope: str = "all",
    auth_token: str | None = None,
) -> dict[str, Any]:
    """
    Call search_context with a test database connection injection.

    This wrapper temporarily patches the database connection for a single call.
    """
    from contextlib import asynccontextmanager
    from unittest.mock import patch

    @asynccontextmanager
    async def mock_get_db_connection():
        """Mock get_db_connection to return the test connection."""
        yield test_db_connection

    # Patch the get_db_connection specifically for this call
    with patch(
        "shared_context_server.server.get_db_connection", mock_get_db_connection
    ):
        return await call_fastmcp_tool(
            original_search_context,
            ctx,
            session_id=session_id,
            query=query,
            fuzzy_threshold=fuzzy_threshold,
            limit=limit,
            search_metadata=search_metadata,
            search_scope=search_scope,
            auth_token=auth_token,
        )
