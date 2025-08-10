"""
Unit tests for permission decorators and enforcement in authentication system.

Tests the require_permission decorator and permission checking functionality
to ensure proper access control across MCP tools and resources.
"""

from shared_context_server.auth import (
    AuthInfo,
    get_auth_info,
    require_permission,
    set_auth_info,
)

# Models import handled by the decorator internally


class MockContext:
    """Mock FastMCP context for permission testing."""

    def __init__(self, auth_info: AuthInfo = None):
        if auth_info:
            self._auth_info = auth_info
        else:
            # Default to basic authenticated context
            self._auth_info = AuthInfo(
                jwt_validated=False,
                agent_id="test_agent",
                agent_type="test",
                permissions=["read", "write"],
                authenticated=True,
                auth_method="api_key",
            )


class TestRequirePermissionDecorator:
    """Test the require_permission decorator functionality."""

    async def test_require_permission_success(self):
        """Test successful permission check."""

        @require_permission("read")
        async def mock_tool(ctx, param1="default"):
            return {"success": True, "param1": param1}

        ctx = MockContext()

        # Should succeed since test agent has read permission
        result = await mock_tool(ctx, param1="test_value")
        assert result == {"success": True, "param1": "test_value"}

    async def test_require_permission_denied(self):
        """Test permission denied scenario."""

        @require_permission("admin")
        async def mock_tool(ctx, param1="default"):
            return {"success": True}

        # Create context with limited permissions
        auth_info = AuthInfo(
            agent_id="limited_agent",
            agent_type="generic",
            permissions=["read"],  # No admin permission
            authenticated=True,
        )
        ctx = MockContext(auth_info)

        result = await mock_tool(ctx)

        # Should return error response
        assert "error" in result
        assert result["error"] == "Permission 'admin' required"
        assert result["code"] == "PERMISSION_DENIED"
        assert result["metadata"]["required_permission"] == "admin"
        assert result["metadata"]["agent_permissions"] == ["read"]
        assert result["metadata"]["agent_id"] == "limited_agent"

    async def test_require_permission_no_context(self):
        """Test behavior when no context is available."""

        @require_permission("read")
        async def mock_tool(param1="default"):
            return {"success": True}

        # Call without context
        result = await mock_tool(param1="test")

        assert "error" in result
        assert result["error"] == "No context available for permission check"
        assert result["code"] == "NO_CONTEXT"

    async def test_require_permission_context_not_first_arg(self):
        """Test decorator when context is not the first argument."""

        @require_permission("write")
        async def mock_tool(param1, ctx, param2="default"):
            return {"success": True, "param1": param1, "param2": param2}

        ctx = MockContext()
        result = await mock_tool("value1", ctx, param2="value2")

        assert result == {"success": True, "param1": "value1", "param2": "value2"}

    async def test_require_permission_multiple_context_args(self):
        """Test decorator behavior with multiple context-like args."""

        @require_permission("read")
        async def mock_tool(ctx1, ctx2, param1="default"):
            return {"success": True, "param1": param1}

        ctx1 = MockContext()
        ctx2 = "not_a_context"

        # Should use the first Context object found
        result = await mock_tool(ctx1, ctx2, param1="test")
        assert result == {"success": True, "param1": "test"}

    async def test_require_permission_debug_permission(self):
        """Test debug permission requirement."""

        @require_permission("debug")
        async def debug_tool(ctx):
            return {"debug_info": "sensitive data"}

        # Context without debug permission
        auth_info = AuthInfo(
            agent_id="regular_agent",
            permissions=["read", "write"],
            authenticated=True,
        )
        ctx = MockContext(auth_info)

        result = await debug_tool(ctx)
        assert "error" in result
        assert result["error"] == "Permission 'debug' required"

    async def test_require_permission_with_jwt_context(self):
        """Test permission check with JWT-authenticated context."""

        @require_permission("write")
        async def write_tool(ctx, data="test"):
            return {"written": data}

        # JWT-authenticated context
        auth_info = AuthInfo(
            jwt_validated=True,
            agent_id="jwt_agent",
            agent_type="claude",
            permissions=["read", "write", "debug"],
            authenticated=True,
            auth_method="jwt",
            token_id="token_123",
        )
        ctx = MockContext(auth_info)

        result = await write_tool(ctx, data="jwt_data")
        assert result == {"written": "jwt_data"}

    async def test_require_permission_unauthenticated_context(self):
        """Test permission check with unauthenticated context."""

        @require_permission("read")
        async def read_tool(ctx):
            return {"data": "public"}

        # Unauthenticated context with read-only permissions
        auth_info = AuthInfo(
            agent_id="anonymous",
            permissions=["read"],
            authenticated=False,
        )
        ctx = MockContext(auth_info)

        result = await read_tool(ctx)
        assert result == {"data": "public"}

    async def test_require_permission_empty_permissions(self):
        """Test permission check when agent has no permissions."""

        @require_permission("read")
        async def read_tool(ctx):
            return {"data": "protected"}

        auth_info = AuthInfo(
            agent_id="no_perms_agent",
            permissions=[],  # No permissions
            authenticated=False,
        )
        ctx = MockContext(auth_info)

        result = await read_tool(ctx)
        assert "error" in result
        assert result["error"] == "Permission 'read' required"

    async def test_require_permission_case_sensitive(self):
        """Test that permission checking is case-sensitive."""

        @require_permission("Read")  # Capital R
        async def case_sensitive_tool(ctx):
            return {"success": True}

        auth_info = AuthInfo(
            agent_id="case_test_agent",
            permissions=["read"],  # lowercase
            authenticated=True,
        )
        ctx = MockContext(auth_info)

        result = await case_sensitive_tool(ctx)
        assert "error" in result
        assert result["error"] == "Permission 'Read' required"


class TestAuthInfoContextManagement:
    """Test AuthInfo context management functions."""

    def test_get_auth_info_existing(self):
        """Test getting existing AuthInfo from context."""
        auth_info = AuthInfo(
            agent_id="test_agent",
            agent_type="test",
            permissions=["read", "write"],
        )
        ctx = MockContext(auth_info)

        retrieved = get_auth_info(ctx)
        assert retrieved.agent_id == "test_agent"
        assert retrieved.agent_type == "test"
        assert retrieved.permissions == ["read", "write"]

    def test_get_auth_info_missing(self):
        """Test getting AuthInfo when none exists (returns default)."""

        class EmptyContext:
            pass

        ctx = EmptyContext()
        auth_info = get_auth_info(ctx)

        # Should return default AuthInfo
        assert auth_info.agent_id == "unknown"
        assert auth_info.agent_type == "generic"
        assert auth_info.permissions == ["read"]
        assert auth_info.authenticated is False

    def test_set_auth_info(self):
        """Test setting AuthInfo on context."""

        class TestContext:
            pass

        ctx = TestContext()
        auth_info = AuthInfo(
            agent_id="new_agent",
            agent_type="custom",
            permissions=["admin", "debug"],
        )

        set_auth_info(ctx, auth_info)

        # Verify it was set correctly
        assert hasattr(ctx, "_auth_info")
        retrieved = get_auth_info(ctx)
        assert retrieved.agent_id == "new_agent"
        assert retrieved.agent_type == "custom"
        assert retrieved.permissions == ["admin", "debug"]

    def test_auth_info_dataclass_defaults(self):
        """Test AuthInfo dataclass default values."""
        auth_info = AuthInfo()

        assert auth_info.jwt_validated is False
        assert auth_info.agent_id == "unknown"
        assert auth_info.agent_type == "generic"
        assert auth_info.permissions == ["read"]
        assert auth_info.authenticated is False
        assert auth_info.auth_method == "none"
        assert auth_info.token_id is None
        assert auth_info.auth_error is None

    def test_auth_info_custom_values(self):
        """Test AuthInfo dataclass with custom values."""
        auth_info = AuthInfo(
            jwt_validated=True,
            agent_id="custom_agent",
            agent_type="claude",
            permissions=["read", "write", "admin"],
            authenticated=True,
            auth_method="jwt",
            token_id="token_abc_123",
            auth_error="test_error",
        )

        assert auth_info.jwt_validated is True
        assert auth_info.agent_id == "custom_agent"
        assert auth_info.agent_type == "claude"
        assert auth_info.permissions == ["read", "write", "admin"]
        assert auth_info.authenticated is True
        assert auth_info.auth_method == "jwt"
        assert auth_info.token_id == "token_abc_123"
        assert auth_info.auth_error == "test_error"


class TestPermissionEnforcementScenarios:
    """Test real-world permission enforcement scenarios."""

    async def test_admin_tools_require_admin_permission(self):
        """Test that admin tools properly require admin permission."""

        @require_permission("admin")
        async def delete_all_sessions(ctx):
            return {"deleted": "all_sessions"}

        # Regular agent trying to access admin tool
        regular_auth = AuthInfo(
            agent_id="regular_agent",
            agent_type="claude",
            permissions=["read", "write"],
            authenticated=True,
        )
        ctx = MockContext(regular_auth)

        result = await delete_all_sessions(ctx)
        assert "error" in result
        assert result["code"] == "PERMISSION_DENIED"

        # Admin agent accessing admin tool
        admin_auth = AuthInfo(
            agent_id="admin_agent",
            agent_type="admin",
            permissions=["read", "write", "admin"],
            authenticated=True,
        )
        ctx = MockContext(admin_auth)

        result = await delete_all_sessions(ctx)
        assert result == {"deleted": "all_sessions"}

    async def test_debug_tools_require_debug_permission(self):
        """Test that debug tools properly require debug permission."""

        @require_permission("debug")
        async def get_system_stats(ctx):
            return {"memory_usage": "85%", "cpu_usage": "45%"}

        # Test agent with debug permission
        test_auth = AuthInfo(
            agent_id="test_agent",
            agent_type="test",
            permissions=["read", "write", "debug"],
            authenticated=True,
        )
        ctx = MockContext(test_auth)

        result = await get_system_stats(ctx)
        assert result == {"memory_usage": "85%", "cpu_usage": "45%"}

        # Claude agent without debug permission
        claude_auth = AuthInfo(
            agent_id="claude_agent",
            agent_type="claude",
            permissions=["read", "write"],  # No debug
            authenticated=True,
        )
        ctx = MockContext(claude_auth)

        result = await get_system_stats(ctx)
        assert "error" in result
        assert result["error"] == "Permission 'debug' required"

    async def test_write_tools_require_write_permission(self):
        """Test that write tools properly require write permission."""

        @require_permission("write")
        async def create_session(ctx, purpose="test"):
            return {"session_id": "new_session", "purpose": purpose}

        # Read-only agent
        readonly_auth = AuthInfo(
            agent_id="readonly_agent",
            agent_type="generic",
            permissions=["read"],  # No write permission
            authenticated=True,
        )
        ctx = MockContext(readonly_auth)

        result = await create_session(ctx, purpose="test_session")
        assert "error" in result
        assert result["code"] == "PERMISSION_DENIED"
        assert result["metadata"]["required_permission"] == "write"

    async def test_read_tools_accessible_to_all(self):
        """Test that read tools are accessible to all authenticated agents."""

        @require_permission("read")
        async def get_session_info(ctx, session_id="test"):
            return {"session_id": session_id, "status": "active"}

        # Test different agent types all having read access
        agent_types = [
            ("claude", ["read", "write"]),
            ("gemini", ["read", "write"]),
            ("generic", ["read"]),
            ("admin", ["read", "write", "admin"]),
        ]

        for agent_type, permissions in agent_types:
            auth_info = AuthInfo(
                agent_id=f"{agent_type}_agent",
                agent_type=agent_type,
                permissions=permissions,
                authenticated=True,
            )
            ctx = MockContext(auth_info)

            result = await get_session_info(ctx, session_id="test_123")
            assert result == {"session_id": "test_123", "status": "active"}

    async def test_permission_metadata_in_error_response(self):
        """Test that permission errors include helpful metadata."""

        @require_permission("admin")
        async def sensitive_operation(ctx):
            return {"result": "sensitive"}

        auth_info = AuthInfo(
            agent_id="test_user_123",
            agent_type="claude",
            permissions=["read", "write"],
            authenticated=True,
            auth_method="jwt",
            token_id="jwt_token_456",
        )
        ctx = MockContext(auth_info)

        result = await sensitive_operation(ctx)

        assert result["error"] == "Permission 'admin' required"
        assert result["code"] == "PERMISSION_DENIED"
        assert result["metadata"]["required_permission"] == "admin"
        assert result["metadata"]["agent_permissions"] == ["read", "write"]
        assert result["metadata"]["agent_id"] == "test_user_123"
