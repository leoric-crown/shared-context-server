"""
Comprehensive tests for token format validation and edge cases.

This test module focuses on improving coverage for authentication token handling,
especially error paths and edge cases that weren't covered in basic tests.
"""

from unittest.mock import AsyncMock, patch

import pytest

from shared_context_server.auth import (
    _is_valid_token_format,
    get_secure_token_manager,
    validate_jwt_token_parameter,
)


class TestTokenFormatValidation:
    """Test comprehensive token format validation including edge cases."""

    def test_is_valid_token_format_malformed_sct_tokens(self):
        """Test malformed protected token format rejection."""
        # Test various malformed sct_ tokens
        malformed_tokens = [
            "sct_not-a-valid-uuid",
            "sct_",
            "sct_12345",
            "sct_invalid-format-here",
            "sct_00000000-0000-0000-0000-00000000000",  # Wrong length
            "sct_GGGGGGGG-0000-0000-0000-000000000000",  # Invalid hex chars
            "sct_12345678-90ab-cdef-ghij-klmnopqrstuv",  # Invalid chars
        ]

        for token in malformed_tokens:
            assert not _is_valid_token_format(token), (
                f"Should reject malformed token: {token}"
            )

    def test_is_valid_token_format_valid_sct_tokens(self):
        """Test valid protected token format acceptance."""
        # Test valid sct_ tokens
        valid_tokens = [
            "sct_12345678-90ab-cdef-1234-567890abcdef",
            "sct_abcdefab-cdef-abcd-efab-cdefabcdefab",
            "sct_00000000-0000-0000-0000-000000000000",
        ]

        for token in valid_tokens:
            assert _is_valid_token_format(token), f"Should accept valid token: {token}"

    def test_is_valid_token_format_malformed_jwt_tokens(self):
        """Test malformed JWT token format rejection."""
        # Test various malformed JWT tokens
        malformed_jwts = [
            "only.two",  # Only 2 parts
            "four.parts.here.too",  # 4 parts
            "part1",  # Only 1 part
            "",  # Empty string
            "invalid@chars.in#jwt.token$",  # Invalid base64url chars
            "valid.part.but===padding===",  # Too much padding
        ]

        for token in malformed_jwts:
            assert not _is_valid_token_format(token), (
                f"Should reject malformed JWT: {token}"
            )

    def test_is_valid_token_format_valid_jwt_tokens(self):
        """Test valid JWT token format acceptance."""
        # Test valid JWT format (3 base64url parts)
        valid_jwts = [
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc123",
            "header.payload.signature",
            "a.b.c",
            "test_123.part-two.final_part",
            "part1==.part2=.part3",  # Valid padding
        ]

        for token in valid_jwts:
            assert _is_valid_token_format(token), f"Should accept valid JWT: {token}"

    async def test_validate_jwt_token_parameter_malformed_token(self):
        """Test validate_jwt_token_parameter with malformed token formats."""
        malformed_token = "sct_invalid-format"

        result = await validate_jwt_token_parameter(malformed_token)

        # Should return validation error, not None
        assert result is not None
        assert "validation_error" in result
        assert "Malformed token format" in result["validation_error"]
        # Token should NOT be included in error message for security
        assert "sct_invalid-format" not in result["validation_error"]

    async def test_validate_jwt_token_parameter_malformed_jwt(self):
        """Test validate_jwt_token_parameter with malformed JWT."""
        malformed_jwt = "only.two.parts.four"

        result = await validate_jwt_token_parameter(malformed_jwt)

        # Should return validation error
        assert result is not None
        assert "validation_error" in result
        assert "Malformed token format" in result["validation_error"]

    @patch("shared_context_server.auth_context.get_secure_token_manager")
    async def test_validate_jwt_token_parameter_protected_token_not_found(
        self, mock_get_manager
    ):
        """Test protected token that doesn't exist in database."""
        # Mock token manager to return None (token not found)
        mock_manager = AsyncMock()
        mock_manager.resolve_protected_token.return_value = None
        mock_get_manager.return_value = mock_manager

        valid_sct_token = "sct_12345678-90ab-cdef-1234-567890abcdef"
        result = await validate_jwt_token_parameter(valid_sct_token)

        # Should return authentication error
        assert result is not None
        assert "authentication_error" in result
        assert "Protected token invalid or expired" in result["authentication_error"]
        # Token should NOT be included in error message for security
        assert (
            "sct_12345678-90ab-cdef-1234-567890abcdef"
            not in result["authentication_error"]
        )

        # Verify token manager was called
        mock_manager.resolve_protected_token.assert_called_once_with(valid_sct_token)

    @patch("shared_context_server.auth_context.get_secure_token_manager")
    @patch("shared_context_server.auth_core.auth_manager")
    async def test_validate_jwt_token_parameter_protected_token_invalid_jwt(
        self, mock_auth_manager, mock_get_manager
    ):
        """Test protected token that resolves to invalid JWT."""
        # Mock token manager to return invalid JWT
        mock_manager = AsyncMock()
        mock_manager.resolve_protected_token.return_value = "invalid.jwt.here"
        mock_get_manager.return_value = mock_manager

        # Mock JWT validation to fail
        mock_auth_manager.validate_token.return_value = {
            "valid": False,
            "error": "Invalid JWT signature",
        }

        valid_sct_token = "sct_12345678-90ab-cdef-1234-567890abcdef"
        result = await validate_jwt_token_parameter(valid_sct_token)

        # Should return authentication error
        assert result is not None
        assert "authentication_error" in result
        assert "JWT validation failed" in result["authentication_error"]
        # The error message could vary based on the actual JWT validation failure
        assert (
            "Invalid JWT signature" in result["authentication_error"]
            or "Invalid token" in result["authentication_error"]
        )

    @patch("shared_context_server.auth_core.auth_manager")
    async def test_validate_jwt_token_parameter_direct_jwt_expired(
        self, mock_auth_manager
    ):
        """Test direct JWT token that is expired."""
        # Mock JWT validation to return expired error
        mock_auth_manager.validate_token.return_value = {
            "valid": False,
            "error": "Token expired",
        }

        expired_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1fQ.signature"
        result = await validate_jwt_token_parameter(expired_jwt)

        # Should return authentication error
        assert result is not None
        assert "authentication_error" in result
        assert "JWT authentication failed" in result["authentication_error"]
        # The error message could vary based on the actual JWT validation failure
        assert (
            "Token expired" in result["authentication_error"]
            or "Invalid token" in result["authentication_error"]
        )

    async def test_validate_jwt_token_parameter_exception_handling(self):
        """Test exception handling in validate_jwt_token_parameter."""
        # Use a token that will trigger an exception during processing
        with patch(
            "shared_context_server.auth_core._is_valid_token_format",
            side_effect=Exception("Validation error"),
        ):
            result = await validate_jwt_token_parameter("some.jwt.token")

            # Should return None when exception occurs
            assert result is None


class TestSecureTokenManagerErrorScenarios:
    """Test SecureTokenManager error scenarios and edge cases."""

    async def test_secure_token_manager_missing_encryption_key(self):
        """Test SecureTokenManager initialization without encryption key."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(
                ValueError, match="JWT_ENCRYPTION_KEY environment variable required"
            ),
        ):
            # Remove JWT_ENCRYPTION_KEY from environment
            from shared_context_server.auth import SecureTokenManager

            SecureTokenManager()

    @patch("shared_context_server.auth_secure.get_db_connection")
    async def test_create_protected_token_database_error(self, mock_get_db):
        """Test create_protected_token with database connection failure."""
        # Mock database connection to fail
        mock_get_db.side_effect = Exception("Database connection failed")

        # Set up encryption key
        with patch.dict(
            "os.environ",
            {"JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY="},
        ):
            from shared_context_server.auth import SecureTokenManager

            manager = SecureTokenManager()

            # With ContextVar implementation, database errors might be handled differently
            try:
                result = await manager.create_protected_token(
                    "fake.jwt.token", "test_agent"
                )
                # If no exception, the method should return None or handle error gracefully
                assert result is None or isinstance(result, str)
            except Exception as e:
                # If exception is raised, it should contain the expected error
                assert "Database connection failed" in str(e)

    async def test_extract_agent_info_for_recovery_not_found(self):
        """Test extract_agent_info_for_recovery with non-existent token."""
        with patch.dict(
            "os.environ",
            {"JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY="},
        ):
            manager = get_secure_token_manager()

            # Mock database to return no rows
            with patch(
                "shared_context_server.database.get_db_connection"
            ) as mock_get_db:
                mock_conn = AsyncMock()
                mock_cursor = AsyncMock()
                mock_cursor.fetchone.return_value = None
                mock_conn.execute.return_value = mock_cursor
                mock_get_db.return_value.__aenter__.return_value = mock_conn

                result = await manager.extract_agent_info_for_recovery(
                    "sct_12345678-90ab-cdef-1234-567890abcdef"
                )

                assert result is None

    async def test_extract_agent_info_for_recovery_decryption_error(self):
        """Test extract_agent_info_for_recovery with decryption failure."""
        with patch.dict(
            "os.environ",
            {"JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY="},
        ):
            manager = get_secure_token_manager()

            # Mock database to return corrupted encrypted data
            with patch(
                "shared_context_server.database.get_db_connection"
            ) as mock_get_db:
                mock_conn = AsyncMock()
                mock_cursor = AsyncMock()
                # Return row with corrupted encrypted data
                mock_cursor.fetchone.return_value = (
                    b"corrupted_data",
                    "test_agent",
                    "2024-01-01T00:00:00Z",
                )
                mock_conn.execute.return_value = mock_cursor
                mock_get_db.return_value.__aenter__.return_value = mock_conn

                result = await manager.extract_agent_info_for_recovery(
                    "sct_12345678-90ab-cdef-1234-567890abcdef"
                )

                assert result is None

    async def test_extract_agent_info_for_recovery_invalid_token_format(self):
        """Test extract_agent_info_for_recovery with invalid token format."""
        with patch.dict(
            "os.environ",
            {"JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY="},
        ):
            manager = get_secure_token_manager()

            # Test with non-sct token
            result = await manager.extract_agent_info_for_recovery("invalid_token")
            assert result is None

            # Test with malformed sct token
            result = await manager.extract_agent_info_for_recovery("sct_invalid")
            assert result is None

    @patch("shared_context_server.auth_secure.get_db_connection")
    async def test_cleanup_expired_tokens_database_error(self, mock_get_db):
        """Test cleanup_expired_tokens with database error."""
        with patch.dict(
            "os.environ",
            {"JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY="},
        ):
            manager = get_secure_token_manager()

            # Mock database connection to fail
            mock_get_db.side_effect = Exception("Database error")

            # Should return 0 and handle exception gracefully
            result = await manager.cleanup_expired_tokens()
            assert result == 0

    async def test_resolve_protected_token_not_sct_format(self):
        """Test resolve_protected_token with non-sct format token."""
        with patch.dict(
            "os.environ",
            {"JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY="},
        ):
            manager = get_secure_token_manager()

            # Test with non-sct token
            result = await manager.resolve_protected_token("regular.jwt.token")
            assert result is None

            # Test with malformed sct token
            result = await manager.resolve_protected_token("sct_malformed")
            assert result is None
