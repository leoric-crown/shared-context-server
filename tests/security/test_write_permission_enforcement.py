"""
Security tests for write permission enforcement.

Tests that READ_ONLY agents cannot perform write operations like:
- create_session
- add_message
- set_memory

This fixes the critical security vulnerability where READ_ONLY agents
could perform privileged operations they shouldn't have access to.
"""

import os
from unittest.mock import patch

import pytest

from shared_context_server.auth_core import AuthInfo
from shared_context_server.memory_tools import set_memory
from shared_context_server.session_tools import add_message, create_session
from tests.conftest import call_fastmcp_tool


class MockContext:
    """Mock context for testing permission enforcement."""

    def __init__(self, agent_id="test_agent", permissions=None):
        if permissions is None:
            permissions = ["read"]

        self.session_id = "test_session"
        self.headers = {"X-API-Key": "T34PEv/IEUoVx18/g+xOIk/zT4S/MaQUm0dlU9jQhXk="}

        self._auth_info = AuthInfo(
            jwt_validated=True,
            agent_id=agent_id,
            agent_type="generic" if permissions == ["read"] else "claude",
            permissions=permissions,
            authenticated=True,
            auth_method="jwt",
        )


@pytest.fixture
def read_only_context():
    """Create a context with read-only permissions."""
    return MockContext(agent_id="readonly_agent", permissions=["read"])


@pytest.fixture
def write_enabled_context():
    """Create a context with write permissions."""
    return MockContext(agent_id="write_agent", permissions=["read", "write"])


class TestWritePermissionEnforcement:
    """Test suite for write permission enforcement."""

    @pytest.mark.asyncio
    async def test_create_session_blocked_for_readonly(
        self, read_only_context, test_db_manager
    ):
        """Test that create_session is blocked for READ_ONLY agents."""
        result = await call_fastmcp_tool(
            create_session, read_only_context, purpose="Test session"
        )

        # Should return permission denied error
        assert "error" in result
        assert result["code"] == "PERMISSION_DENIED"
        assert "Write permission required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_session_allowed_for_write_agent(
        self, write_enabled_context, test_db_manager
    ):
        """Test that create_session is allowed for agents with write permission."""
        result = await call_fastmcp_tool(
            create_session, write_enabled_context, purpose="Test session"
        )

        # Should succeed
        assert "error" not in result
        assert "session_id" in result
        assert result["session_id"].startswith("session_")

    @pytest.mark.asyncio
    async def test_add_message_blocked_for_readonly(
        self, read_only_context, write_enabled_context, test_db_manager
    ):
        """Test that add_message is blocked for READ_ONLY agents."""
        # First create a session with a write-enabled agent
        session_result = await call_fastmcp_tool(
            create_session, write_enabled_context, purpose="Test session for message"
        )
        session_id = session_result["session_id"]

        # Now try to add message with read-only agent
        result = await call_fastmcp_tool(
            add_message,
            read_only_context,
            session_id=session_id,
            content="Test message",
        )

        # Should return permission denied error
        assert "error" in result
        assert result["code"] == "PERMISSION_DENIED"
        assert "Write permission required" in result["error"]

    @pytest.mark.asyncio
    async def test_add_message_allowed_for_write_agent(
        self, write_enabled_context, test_db_manager
    ):
        """Test that add_message is allowed for agents with write permission."""
        # First create a session
        session_result = await call_fastmcp_tool(
            create_session, write_enabled_context, purpose="Test session for message"
        )
        session_id = session_result["session_id"]

        # Add message should succeed
        result = await call_fastmcp_tool(
            add_message,
            write_enabled_context,
            session_id=session_id,
            content="Test message",
        )

        # Should succeed
        assert "error" not in result
        assert "message_id" in result

    @pytest.mark.asyncio
    async def test_set_memory_blocked_for_readonly(
        self, read_only_context, test_db_manager
    ):
        """Test that set_memory is blocked for READ_ONLY agents."""
        result = await call_fastmcp_tool(
            set_memory, read_only_context, key="test_key", value="test_value"
        )

        # Should return permission denied error
        assert "error" in result
        assert result["code"] == "PERMISSION_DENIED"
        assert "Write permission required" in result["error"]

    @pytest.mark.asyncio
    async def test_set_memory_allowed_for_write_agent(
        self, write_enabled_context, test_db_manager
    ):
        """Test that set_memory is allowed for agents with write permission."""
        result = await call_fastmcp_tool(
            set_memory, write_enabled_context, key="test_key", value="test_value"
        )

        # Should succeed
        assert "error" not in result
        assert "success" in result
        assert result["success"] is True


class TestPermissionErrorMessages:
    """Test that permission error messages are informative and helpful."""

    @pytest.mark.asyncio
    async def test_write_permission_error_provides_guidance(
        self, read_only_context, test_db_manager
    ):
        """Test that write permission errors provide helpful guidance."""
        result = await call_fastmcp_tool(
            create_session, read_only_context, purpose="Test session"
        )

        # Check error structure
        assert "error" in result
        assert "code" in result
        assert "suggestions" in result
        assert (
            "context" in result
        )  # The error format uses 'context' instead of 'metadata'

        # Check error details
        assert result["code"] == "PERMISSION_DENIED"
        assert "Write permission required" in result["error"]

        # Check suggestions include helpful guidance
        suggestions = result["suggestions"]
        assert any(
            "read-only operations" in suggestion.lower() for suggestion in suggestions
        )
        assert any(
            "write permission" in suggestion.lower() for suggestion in suggestions
        )

        # Check context includes permission details (the error format uses 'context' instead of 'metadata')
        context_info = result.get("context", result.get("metadata", {}))
        assert "required_permission" in context_info
        assert context_info["required_permission"] == "write"
        assert "current_permissions" in context_info
        assert context_info["current_permissions"] == ["read"]


class TestSecurityBoundaries:
    """Test security boundaries are properly enforced."""

    @pytest.mark.asyncio
    async def test_permission_cannot_be_bypassed_with_token_parameter(
        self, read_only_context, test_db_manager
    ):
        """Test that providing auth_token parameter doesn't bypass permission checks."""
        # Even if we provide a token as parameter, the context permissions should apply
        result = await call_fastmcp_tool(
            add_message,
            read_only_context,
            session_id="session_test123",
            content="Test message",
            auth_token=None,
        )

        # Should still be blocked
        assert "error" in result
        assert result["code"] == "PERMISSION_DENIED"
        assert "Write permission required" in result["error"]

    @pytest.mark.asyncio
    async def test_permission_inheritance_is_correct(self, test_db_manager):
        """Test that different agent types get expected permissions."""
        # Test generic (read-only) agent
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Test that generic agent gets only read permissions
            readonly_context = MockContext(
                agent_id="generic_agent", permissions=["read"]
            )
            assert readonly_context._auth_info.permissions == ["read"]
            assert readonly_context._auth_info.agent_type == "generic"

            # Test that claude agent gets read+write permissions
            write_context = MockContext(
                agent_id="claude_agent", permissions=["read", "write"]
            )
            assert "read" in write_context._auth_info.permissions
            assert "write" in write_context._auth_info.permissions
            assert write_context._auth_info.agent_type == "claude"
