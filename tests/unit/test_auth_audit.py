"""
Unit tests for audit logging functionality in authentication system.

Tests the audit_log_auth_event function to ensure proper security event logging
and monitoring capabilities across different authentication scenarios.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from shared_context_server.auth import audit_log_auth_event


class TestAuditLogAuthEvent:
    """Test audit_log_auth_event function for security monitoring."""

    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection for audit logging."""
        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "shared_context_server.auth_core.get_db_connection",
            return_value=mock_context_manager,
        ):
            yield mock_conn

    async def test_audit_log_jwt_authentication_success(self, mock_db_connection):
        """Test audit logging for successful JWT authentication."""
        await audit_log_auth_event(
            "jwt_authentication_success",
            "claude_agent_123",
            "session_456",
            {
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "token_id": "jwt_token_789",
            },
        )

        # Verify database insert was called
        mock_db_connection.execute.assert_called_once()
        call_args = mock_db_connection.execute.call_args[0]

        # Verify SQL query
        sql_query = call_args[0]
        assert "INSERT INTO audit_log" in sql_query
        assert "(event_type, agent_id, session_id, metadata)" in sql_query

        # Verify parameters
        params = call_args[1]
        assert params[0] == "jwt_authentication_success"
        assert params[1] == "claude_agent_123"
        assert params[2] == "session_456"

        # Verify metadata JSON
        metadata_json = params[3]
        metadata = json.loads(metadata_json)
        assert metadata["agent_type"] == "claude"
        assert metadata["permissions"] == ["read", "write"]
        assert metadata["token_id"] == "jwt_token_789"

        # Verify commit was called
        mock_db_connection.commit.assert_called_once()

    async def test_audit_log_jwt_authentication_failure(self, mock_db_connection):
        """Test audit logging for failed JWT authentication."""
        await audit_log_auth_event(
            "jwt_authentication_failed", "unknown", None, {"error": "Token expired"}
        )

        mock_db_connection.execute.assert_called_once()
        call_args = mock_db_connection.execute.call_args[0]
        params = call_args[1]

        assert params[0] == "jwt_authentication_failed"
        assert params[1] == "unknown"
        assert params[2] is None  # No session_id for failed auth

        metadata = json.loads(params[3])
        assert metadata["error"] == "Token expired"

    async def test_audit_log_api_key_authentication_success(self, mock_db_connection):
        """Test audit logging for successful API key authentication."""
        await audit_log_auth_event(
            "api_key_authentication_success",
            "api_agent_456",
            "session_789",
            {"auth_method": "api_key"},
        )

        mock_db_connection.execute.assert_called_once()
        call_args = mock_db_connection.execute.call_args[0]
        params = call_args[1]

        assert params[0] == "api_key_authentication_success"
        assert params[1] == "api_agent_456"
        assert params[2] == "session_789"

        metadata = json.loads(params[3])
        assert metadata["auth_method"] == "api_key"

    async def test_audit_log_permission_denied(self, mock_db_connection):
        """Test audit logging for permission denied events."""
        await audit_log_auth_event(
            "permission_denied",
            "limited_agent_123",
            "session_456",
            {
                "required_permission": "admin",
                "agent_permissions": ["read", "write"],
                "requested_operation": "delete_all_sessions",
            },
        )

        mock_db_connection.execute.assert_called_once()
        call_args = mock_db_connection.execute.call_args[0]
        params = call_args[1]

        assert params[0] == "permission_denied"
        assert params[1] == "limited_agent_123"
        assert params[2] == "session_456"

        metadata = json.loads(params[3])
        assert metadata["required_permission"] == "admin"
        assert metadata["agent_permissions"] == ["read", "write"]
        assert metadata["requested_operation"] == "delete_all_sessions"

    async def test_audit_log_no_metadata(self, mock_db_connection):
        """Test audit logging with no metadata provided."""
        await audit_log_auth_event("simple_event", "agent_123", "session_456")

        mock_db_connection.execute.assert_called_once()
        call_args = mock_db_connection.execute.call_args[0]
        params = call_args[1]

        assert params[0] == "simple_event"
        assert params[1] == "agent_123"
        assert params[2] == "session_456"

        # Should default to empty dict
        metadata = json.loads(params[3])
        assert metadata == {}

    async def test_audit_log_empty_metadata_dict(self, mock_db_connection):
        """Test audit logging with empty metadata dict."""
        await audit_log_auth_event(
            "event_with_empty_metadata", "agent_123", "session_456", {}
        )

        mock_db_connection.execute.assert_called_once()
        call_args = mock_db_connection.execute.call_args[0]
        params = call_args[1]

        metadata = json.loads(params[3])
        assert metadata == {}

    async def test_audit_log_complex_metadata(self, mock_db_connection):
        """Test audit logging with complex metadata structure."""
        complex_metadata = {
            "auth_details": {
                "method": "jwt",
                "token_info": {
                    "issuer": "shared-context-server",
                    "audience": "mcp-agents",
                    "expiry": "2024-12-31T23:59:59Z",
                },
            },
            "request_info": {
                "tool_name": "create_session",
                "parameters": ["purpose", "metadata"],
            },
            "security_flags": ["verified", "non_suspicious"],
            "risk_score": 0.1,
        }

        await audit_log_auth_event(
            "complex_operation", "complex_agent", "session_123", complex_metadata
        )

        mock_db_connection.execute.assert_called_once()
        call_args = mock_db_connection.execute.call_args[0]
        params = call_args[1]

        # Verify complex metadata serialization/deserialization
        metadata_json = params[3]
        metadata = json.loads(metadata_json)

        assert metadata["auth_details"]["method"] == "jwt"
        assert (
            metadata["auth_details"]["token_info"]["issuer"] == "shared-context-server"
        )
        assert metadata["request_info"]["tool_name"] == "create_session"
        assert metadata["security_flags"] == ["verified", "non_suspicious"]
        assert metadata["risk_score"] == 0.1

    async def test_audit_log_utc_timestamp(self, mock_db_connection):
        """Test that audit log function executes without timestamp parameter (database auto-generates)."""
        await audit_log_auth_event(
            "timestamp_test", "agent_123", "session_456", {"test": "timestamp"}
        )

        mock_db_connection.execute.assert_called_once()
        call_args = mock_db_connection.execute.call_args[0]
        params = call_args[1]

        # Verify only 4 parameters are passed (no timestamp - database auto-generates)
        assert len(params) == 4
        assert params[0] == "timestamp_test"
        assert params[1] == "agent_123"
        assert params[2] == "session_456"

        # Verify metadata
        metadata = json.loads(params[3])
        assert metadata["test"] == "timestamp"

        # Verify commit was called
        mock_db_connection.commit.assert_called_once()

    async def test_audit_log_database_exception_handling(self, mock_db_connection):
        """Test graceful handling of database exceptions during audit logging."""
        # Make database operations raise exception
        mock_db_connection.execute.side_effect = Exception("Database connection failed")

        # Should not raise exception - audit logging failures are logged but don't break flow
        await audit_log_auth_event(
            "test_event", "agent_123", "session_456", {"test": "data"}
        )

        # Verify execute was attempted
        mock_db_connection.execute.assert_called_once()
        # Commit should not be called due to exception
        mock_db_connection.commit.assert_not_called()

    async def test_audit_log_commit_exception_handling(self, mock_db_connection):
        """Test handling of commit exceptions during audit logging."""
        # Make commit raise exception
        mock_db_connection.commit.side_effect = Exception("Commit failed")

        # Should not raise exception
        await audit_log_auth_event(
            "commit_test_event", "agent_123", "session_456", {"test": "data"}
        )

        # Verify both execute and commit were attempted
        mock_db_connection.execute.assert_called_once()
        mock_db_connection.commit.assert_called_once()

    async def test_audit_log_json_serialization_error(self, mock_db_connection):
        """Test handling of JSON serialization errors in metadata."""
        # Mock json.dumps to raise an error in the auth_core module
        with patch(
            "shared_context_server.auth_core.json.dumps",
            side_effect=TypeError("Object is not JSON serializable"),
        ):
            metadata_with_error = {"test": "data"}

            # Should handle serialization error gracefully (doesn't break execution)
            await audit_log_auth_event(
                "serialization_test", "agent_123", "session_456", metadata_with_error
            )

            # The function might not call execute if JSON serialization fails early
            # This test ensures the function handles the error gracefully

    async def test_audit_log_different_event_types(self, mock_db_connection):
        """Test audit logging for various event types."""
        event_scenarios = [
            (
                "session_created",
                "creator_agent",
                "new_session",
                {"purpose": "collaboration"},
            ),
            ("session_deleted", "admin_agent", "old_session", {"reason": "cleanup"}),
            (
                "permission_escalation",
                "test_agent",
                "session_123",
                {"old_perms": ["read"], "new_perms": ["read", "write"]},
            ),
            (
                "suspicious_activity",
                "unknown_agent",
                None,
                {"reason": "multiple_failed_attempts"},
            ),
            (
                "token_refresh",
                "long_running_agent",
                "session_456",
                {"old_token_id": "token_123", "new_token_id": "token_456"},
            ),
        ]

        for event_type, agent_id, session_id, metadata in event_scenarios:
            await audit_log_auth_event(event_type, agent_id, session_id, metadata)

        # Verify all events were logged
        assert mock_db_connection.execute.call_count == len(event_scenarios)
        assert mock_db_connection.commit.call_count == len(event_scenarios)

        # Verify last call parameters
        last_call_args = mock_db_connection.execute.call_args[0]
        params = last_call_args[1]
        assert params[0] == "token_refresh"
        assert params[1] == "long_running_agent"
        assert params[2] == "session_456"

        metadata = json.loads(params[3])
        assert metadata["old_token_id"] == "token_123"
        assert metadata["new_token_id"] == "token_456"
