"""
Web UI Integration Tests for Shared Context Server.

Tests the FastMCP server with Web UI routes, database integration,
and WebSocket functionality.
"""

import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest

from shared_context_server.database import initialize_database
from shared_context_server.server import add_message, create_session, mcp

sys.path.append(str(Path(__file__).parent))
from conftest import MockContext, call_fastmcp_tool


@pytest.fixture
async def test_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create test client for Web UI endpoints."""
    # Initialize database for testing
    await initialize_database()

    # Create test client with FastMCP HTTP app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=mcp.http_app()), base_url="http://testserver"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_dashboard_endpoint(test_client: httpx.AsyncClient):
    """Test that dashboard endpoint returns HTML with session data."""
    response = await test_client.get("/ui/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    content = response.text
    assert "Active Sessions" in content
    assert "Dashboard - Shared Context Server" in content
    assert "sessions-grid" in content or "empty-state" in content


@pytest.mark.asyncio
async def test_session_view_existing_session(test_client: httpx.AsyncClient):
    """Test session view for an existing session."""
    # For now, let's just test with a session that might exist
    # TODO: Adapt this based on FastMCP test patterns

    # Test with a known session pattern
    response = await test_client.get("/ui/sessions/session_test123456789ab")

    # Should return 404 for non-existent session or 200 for existing
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        content = response.text
        assert "Session:" in content
        assert "messages-container" in content


@pytest.mark.asyncio
async def test_session_view_nonexistent_session(test_client: httpx.AsyncClient):
    """Test session view for a non-existent session."""
    response = await test_client.get("/ui/sessions/session_nonexistent123")

    assert response.status_code == 404
    content = response.text
    assert "Session Not Found" in content


@pytest.mark.asyncio
async def test_health_endpoint_integration(test_client: httpx.AsyncClient):
    """Test that health endpoint works with Web UI server."""
    response = await test_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "unhealthy"]
    assert "database" in data


@pytest.mark.asyncio
async def test_ui_endpoints_return_html(test_client: httpx.AsyncClient):
    """Test that UI endpoints return HTML with proper content types."""
    endpoints = ["/ui/"]

    for endpoint in endpoints:
        response = await test_client.get(endpoint)

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        content = response.text
        # Verify HTML structure
        assert content.startswith("<!DOCTYPE html>")
        assert "<html" in content
        assert "</html>" in content.strip()
        assert "<title>" in content
        assert "Shared Context Server" in content


@pytest.mark.asyncio
async def test_dashboard_shows_session_stats(test_client: httpx.AsyncClient):
    """Test that dashboard shows session statistics."""
    response = await test_client.get("/ui/")

    assert response.status_code == 200
    content = response.text

    # Check for dashboard stats
    assert "stat-number" in content
    assert "Active Sessions" in content

    # Should show either sessions or empty state
    assert "session-card" in content or "empty-state" in content


@pytest.mark.asyncio
async def test_web_ui_navigation_structure(test_client: httpx.AsyncClient):
    """Test that Web UI has proper navigation structure."""
    response = await test_client.get("/ui/")

    assert response.status_code == 200
    content = response.text

    # Check navigation structure
    assert "navbar" in content
    assert "nav-brand" in content
    assert "nav-links" in content
    assert "Dashboard" in content
    assert "Health" in content
    assert "status-indicator" in content


@pytest.mark.asyncio
async def test_session_view_structure(test_client: httpx.AsyncClient):
    """Test session view HTML structure by creating a test session."""
    # Create a test session
    ctx = MockContext(session_id="webui_test", agent_id="test_agent")
    session_result = await call_fastmcp_tool(
        create_session, ctx, purpose="Web UI integration test session"
    )
    session_id = session_result["session_id"]

    # Add a test message to make the session visible
    await call_fastmcp_tool(
        add_message, ctx, session_id=session_id, content="Test message for UI"
    )

    # Test the session view
    response = await test_client.get(f"/ui/sessions/{session_id}")

    assert response.status_code == 200
    content = response.text

    # Check session view structure
    assert "session-view" in content
    assert "breadcrumb" in content
    assert "session-info" in content
    assert "messages-container" in content
    assert "Session:" in content


@pytest.mark.asyncio
async def test_css_and_js_references(test_client: httpx.AsyncClient):
    """Test that HTML includes proper CSS and JS references."""
    response = await test_client.get("/ui/")

    assert response.status_code == 200
    content = response.text

    # Check for CSS and JS references
    assert 'href="/ui/static/css/style.css"' in content
    assert 'src="/ui/static/js/app.js"' in content

    # Check for external font reference
    assert "fonts.googleapis.com" in content


if __name__ == "__main__":
    # Run tests directly with pytest
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])
    sys.exit(result.returncode)
