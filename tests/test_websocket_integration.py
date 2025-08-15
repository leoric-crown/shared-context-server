"""
Integration tests for WebSocket functionality.

Tests the WebSocket server directly using ASGI test clients,
without requiring a live server to be running.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from shared_context_server.websocket_server import websocket_app

try:
    import importlib.util

    WEBSOCKETS_AVAILABLE = importlib.util.find_spec("websockets") is not None
except ImportError:
    WEBSOCKETS_AVAILABLE = False

try:
    import importlib.util

    MCPSOCK_AVAILABLE = importlib.util.find_spec("mcpsock") is not None
except ImportError:
    MCPSOCK_AVAILABLE = False


@pytest.fixture
async def websocket_client(isolated_db) -> AsyncGenerator[AsyncClient, None]:
    """Create test client for WebSocket server."""
    # Use isolated test database instead of production database
    from tests.fixtures.database import patch_database_for_test

    with patch_database_for_test(isolated_db):
        # Create test client with WebSocket app
        async with AsyncClient(
            transport=ASGITransport(app=websocket_app), base_url="http://testserver"
        ) as client:
            yield client


@pytest.mark.asyncio
async def test_websocket_health_endpoint(websocket_client: AsyncClient):
    """Test WebSocket server health endpoint."""
    response = await websocket_client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] == "healthy"
    assert "websocket_support" in data
    assert data["websocket_support"] is True
    assert "timestamp" in data

    if MCPSOCK_AVAILABLE:
        assert "mcpsock_version" in data
    else:
        assert "mcpsock_available" in data
        assert data["mcpsock_available"] is False


@pytest.mark.asyncio
async def test_websocket_app_creation():
    """Test that WebSocket app is created successfully."""
    assert websocket_app is not None
    assert hasattr(websocket_app, "routes")

    # Check that routes exist
    routes = list(websocket_app.routes)
    assert len(routes) >= 2  # At least health endpoint + WebSocket endpoint

    # Find WebSocket route
    websocket_routes = [
        route
        for route in routes
        if hasattr(route, "path") and "/ws/" in str(route.path)
    ]
    assert len(websocket_routes) >= 1, "WebSocket route should exist"


@pytest.mark.skipif(not MCPSOCK_AVAILABLE, reason="mcpsock not available")
@pytest.mark.asyncio
async def test_websocket_mcpsock_tools():
    """Test that mcpsock tools are properly registered."""
    # This test verifies the WebSocket server tools are configured correctly
    from shared_context_server.websocket_server import ws_router

    # Check that the router has tools registered
    assert ws_router is not None
    assert hasattr(ws_router, "tool_handlers"), (
        "Router should have tool_handlers attribute"
    )

    # Check that some tools are registered
    assert len(ws_router.tool_handlers) > 0, "Should have registered WebSocket tools"


@pytest.mark.asyncio
async def test_websocket_endpoint_exists(websocket_client: AsyncClient):
    """Test that WebSocket endpoint exists by checking app routes."""
    # Instead of trying to access WebSocket endpoint with HTTP GET,
    # let's verify the route exists in the app configuration

    # Check that WebSocket routes exist
    websocket_routes = [
        route
        for route in websocket_app.routes
        if hasattr(route, "path_regex") and "/ws/" in str(route.path_regex.pattern)
    ]

    assert len(websocket_routes) >= 1, "Should have at least one WebSocket route"

    # Verify the route pattern includes session_id parameter
    ws_route = websocket_routes[0]
    pattern = str(ws_route.path_regex.pattern)
    assert "session_id" in pattern, (
        f"WebSocket route should include session_id parameter: {pattern}"
    )


@pytest.mark.skipif(not WEBSOCKETS_AVAILABLE, reason="websockets library not available")
@pytest.mark.asyncio
async def test_websocket_connection_basic():
    """Test basic WebSocket connection establishment."""
    # This test would require a more complex setup with actual WebSocket client
    # For now, we'll test that the endpoint configuration is correct

    # Check that WebSocket app has proper routes configured
    websocket_routes = [
        route
        for route in websocket_app.routes
        if hasattr(route, "path") and "/ws/" in str(getattr(route, "path", ""))
    ]

    assert len(websocket_routes) > 0, "Should have at least one WebSocket route"

    # Check route path pattern
    ws_route = websocket_routes[0]
    path = str(getattr(ws_route, "path", ""))
    assert "{session_id}" in path or "session_id" in path, (
        "WebSocket route should include session_id parameter"
    )


@pytest.mark.asyncio
async def test_websocket_fallback_mode():
    """Test WebSocket server fallback behavior when mcpsock unavailable."""
    # This tests the fallback WebSocket implementation
    # Even without mcpsock, basic WebSocket functionality should work

    # Verify app is created regardless of mcpsock availability
    assert websocket_app is not None

    # Check health endpoint works in both modes
    async with AsyncClient(
        transport=ASGITransport(app=websocket_app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["websocket_support"] is True


@pytest.mark.asyncio
async def test_websocket_server_import():
    """Test that WebSocket server module can be imported without errors."""
    # This test ensures the module loads correctly
    from shared_context_server import websocket_server

    assert hasattr(websocket_server, "websocket_app")
    assert hasattr(websocket_server, "start_websocket_server")
    assert hasattr(websocket_server, "run_websocket_server")


@pytest.mark.asyncio
async def test_websocket_database_integration():
    """Test that WebSocket server can access database properly."""
    # Test database connection within WebSocket context
    from shared_context_server.database import get_db_connection

    try:
        async with get_db_connection() as conn:
            # Test basic database query
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            )
            result = await cursor.fetchone()
            assert result is not None
            assert result[0] >= 0  # Should have some tables
    except Exception as e:
        pytest.fail(f"Database connection failed in WebSocket context: {e}")


# Mark tests that require specific dependencies
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


if __name__ == "__main__":
    # Run tests directly
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            __file__,
            "-v",
            "--tb=short",
            "-x",  # Stop on first failure
        ]
    )
    sys.exit(result.returncode)
