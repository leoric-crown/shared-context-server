"""Basic import test to verify Phase 1 implementation works."""


def test_server_import():
    """Test that the server can be imported successfully."""
    from shared_context_server.server import (
        add_message,
        create_session,
        get_messages,
        get_session,
        mcp,
    )

    assert mcp.name == "shared-context-server"
    assert create_session is not None
    assert get_session is not None
    assert add_message is not None
    assert get_messages is not None


def test_database_import():
    """Test that database utilities can be imported."""
    from shared_context_server.database import get_db_connection, initialize_database

    assert get_db_connection is not None
    assert initialize_database is not None


def test_models_import():
    """Test that models can be imported."""
    from shared_context_server.models import (
        MessageVisibility,
        create_error_response,
        create_standard_response,
        sanitize_text_input,
        serialize_metadata,
    )

    assert MessageVisibility.PUBLIC == "public"
    assert MessageVisibility.PRIVATE == "private"
    assert MessageVisibility.AGENT_ONLY == "agent_only"

    # Test utility functions work
    error = create_error_response("Test error", "TEST_CODE")
    assert error["success"] is False
    assert error["error"] == "Test error"
    assert error["code"] == "TEST_CODE"

    success = create_standard_response(success=True, test="value")
    assert success["success"] is True
    assert success["test"] == "value"

    # Test sanitization
    sanitized = sanitize_text_input("  hello world  ")
    assert sanitized == "hello world"

    # Test metadata serialization
    metadata_str = serialize_metadata({"test": True})
    assert '"test":true' in metadata_str
