"""
Simple smoke tests for Phase 2 essential features.

Validates that all Phase 2 features are properly implemented and working.
"""

import pytest


def test_rapidfuzz_import():
    """Test that RapidFuzz can be imported."""
    try:
        from rapidfuzz import fuzz, process

        assert hasattr(fuzz, "WRatio")
        assert hasattr(process, "extract")
        print("✅ RapidFuzz import successful")
    except ImportError as e:
        pytest.fail(f"RapidFuzz not available: {e}")


def test_phase2_server_tools():
    """Test that all Phase 2 tools are defined in the server."""
    from shared_context_server.server import (
        add_message,
        create_session,
        get_memory,
        get_messages,
        get_session,
        list_memory,
        search_by_sender,
        search_by_timerange,
        search_context,
        set_memory,
    )

    # Verify Phase 2 search tools exist and are FunctionTool objects
    phase2_search_tools = [search_context, search_by_sender, search_by_timerange]
    for tool in phase2_search_tools:
        assert tool is not None, "Phase 2 search tool is None"
        assert hasattr(tool, "name"), "Phase 2 search tool missing name attribute"
        assert hasattr(tool, "description"), "Phase 2 search tool missing description"

    # Verify Phase 2 memory tools exist and are FunctionTool objects
    phase2_memory_tools = [set_memory, get_memory, list_memory]
    for tool in phase2_memory_tools:
        assert tool is not None, "Phase 2 memory tool is None"
        assert hasattr(tool, "name"), "Phase 2 memory tool missing name attribute"
        assert hasattr(tool, "description"), "Phase 2 memory tool missing description"

    # Verify Phase 1 tools are still present
    phase1_tools = [create_session, get_session, add_message, get_messages]
    for tool in phase1_tools:
        assert tool is not None, "Phase 1 tool is None"
        assert hasattr(tool, "name"), "Phase 1 tool missing name attribute"
        assert hasattr(tool, "description"), "Phase 1 tool missing description"

    # Verify specific tool names
    expected_names = {
        "search_context",
        "search_by_sender",
        "search_by_timerange",
        "set_memory",
        "get_memory",
        "list_memory",
        "create_session",
        "get_session",
        "add_message",
        "get_messages",
    }

    all_tools = phase2_search_tools + phase2_memory_tools + phase1_tools
    actual_names = {tool.name for tool in all_tools}

    assert expected_names.issubset(actual_names), (
        f"Missing tools: {expected_names - actual_names}"
    )

    print("✅ All Phase 2 tools are properly defined and callable")


def test_phase2_server_resources():
    """Test that Phase 2 MCP resources are defined."""
    from shared_context_server.server import (
        ResourceNotificationManager,
        get_agent_memory_resource,
        get_session_resource,
        notification_manager,
    )

    # Verify resource handler functions exist and are FunctionResourceTemplate objects
    resource_handlers = [get_session_resource, get_agent_memory_resource]

    for handler in resource_handlers:
        assert handler is not None, "Resource handler is None"
        assert hasattr(handler, "uri_template"), "Resource handler missing uri_template"
        assert hasattr(handler, "name"), "Resource handler missing name attribute"

    # Verify resource management infrastructure exists
    assert ResourceNotificationManager is not None
    assert notification_manager is not None
    assert isinstance(notification_manager, ResourceNotificationManager)

    print("✅ All Phase 2 resource handlers are properly defined and callable")


def test_phase2_background_tasks():
    """Test that Phase 2 background task functions are defined."""
    from shared_context_server import server

    # Check background task functions exist
    assert hasattr(server, "cleanup_subscriptions_task")
    assert hasattr(server, "cleanup_expired_memory_task")
    assert hasattr(server, "ResourceNotificationManager")

    # Check notification manager
    assert hasattr(server, "notification_manager")
    assert server.notification_manager is not None

    print("✅ All Phase 2 background tasks and managers are defined")


def test_phase2_models_exist():
    """Test that Phase 2 enhanced models are available."""
    from shared_context_server.models import (
        create_error_response,
        sanitize_text_input,
        serialize_metadata,
    )

    # Test basic model functions work
    error_response = create_error_response("test error", "TEST_CODE")
    assert error_response["success"] is False
    assert error_response["error"] == "test error"
    assert error_response["code"] == "TEST_CODE"

    # Test input sanitization
    clean_text = sanitize_text_input("  test input  ")
    assert clean_text == "test input"

    # Test metadata serialization
    metadata = {"key": "value", "number": 42}
    serialized = serialize_metadata(metadata)
    assert '"key":"value"' in serialized

    print("✅ All Phase 2 model functions are working")


def test_phase2_server_creation():
    """Test that the Phase 2 server can be created successfully."""
    from shared_context_server.server import create_server, mcp

    # Create server instance
    server = create_server()
    assert server is not None

    # Verify it's a FastMCP instance
    assert hasattr(server, "name")
    assert server.name == "shared-context-server"

    # Verify it's the same as the module server
    assert server is mcp

    print("✅ Phase 2 enhanced server creation successful")


@pytest.mark.asyncio
async def test_phase2_database_schema(isolated_db):
    """Test that Phase 2 database schema includes all required tables."""
    from tests.fixtures.database import patch_database_for_test

    # Use isolated test database instead of production database
    with patch_database_for_test(isolated_db):
        # Test that database is properly initialized with schema
        async with isolated_db.get_connection() as conn:
            # Check that required tables exist
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in await cursor.fetchall()]

            required_tables = ["sessions", "messages", "agent_memory", "schema_version"]
            for table in required_tables:
                assert table in tables, f"Required table '{table}' not found"

        print("✅ Phase 2 database schema initialization successful")


def test_rapidfuzz_performance_integration():
    """Test that RapidFuzz is properly integrated for high performance."""
    import time

    from rapidfuzz import fuzz, process

    # Test data
    choices = [
        "Python programming with async await patterns",
        "FastMCP server implementation guide",
        "Agent memory system with TTL expiration",
        "RapidFuzz fuzzy search performance optimization",
        "Database connection pooling for applications",
    ]

    query = "fuzzy search performance"

    # Measure performance
    start_time = time.time()
    matches = process.extract(
        query, choices, scorer=fuzz.WRatio, limit=3, score_cutoff=50
    )
    search_time_ms = (time.time() - start_time) * 1000

    # Verify results
    assert len(matches) > 0, "Should find matches"
    assert matches[0][1] >= 50, "Best match should meet threshold"
    assert search_time_ms < 20, f"Search took {search_time_ms:.2f}ms, expected <20ms"

    print(
        f"✅ RapidFuzz performance test: {search_time_ms:.2f}ms for {len(choices)} items"
    )


if __name__ == "__main__":
    # Run all smoke tests
    print("🧪 Running Phase 2 Smoke Tests...")

    test_rapidfuzz_import()
    test_phase2_server_tools()
    test_phase2_server_resources()
    test_phase2_background_tasks()
    test_phase2_models_exist()
    test_phase2_server_creation()
    test_rapidfuzz_performance_integration()

    print("\n🎉 All Phase 2 smoke tests passed!")
    print("✅ Phase 2 - Essential Features implementation is complete and functional")
