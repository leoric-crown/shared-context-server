"""
Test suite for PRP-006 Secure Token Authentication System.

Tests the secure token manager, protected token handling, and JWT hiding
functionality with multi-agent concurrency safety.
"""

import contextlib
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from shared_context_server.auth import SecureTokenManager, get_secure_token_manager
from shared_context_server.database import (
    get_db_connection,
)


# Test fixtures
@pytest.fixture(scope="function")
async def temp_database():
    """Create temporary database for testing."""
    # Create unique temp file with process ID and thread ID for parallel safety
    import threading

    pid = os.getpid()
    tid = threading.get_ident()

    with tempfile.NamedTemporaryFile(
        suffix=f"_test_{pid}_{tid}.db", delete=False, prefix="scs_test_"
    ) as f:
        temp_path = f.name

    # Initialize the database and reset global managers
    with patch.dict(os.environ, {"DATABASE_PATH": temp_path}):
        # Clear both global database managers to force reinitialization
        import shared_context_server.database_connection as db_module

        db_module._db_manager = None
        # Reset SQLAlchemy manager for USE_SQLALCHEMY=true tests
        if hasattr(db_module, "_sqlalchemy_manager") and db_module._sqlalchemy_manager:
            with contextlib.suppress(Exception):
                await db_module._sqlalchemy_manager.close()
            db_module._sqlalchemy_manager = None

        try:
            # Use the same backend initialization logic as get_db_connection()
            from shared_context_server.database import initialize_database

            await initialize_database()

            yield temp_path
        finally:
            # Cleanup - close SQLAlchemy manager if it exists
            if (
                hasattr(db_module, "_sqlalchemy_manager")
                and db_module._sqlalchemy_manager
            ):
                with contextlib.suppress(Exception):
                    await db_module._sqlalchemy_manager.close()

            # Close aiosqlite manager if it exists
            if hasattr(db_module, "_db_manager") and db_module._db_manager:
                # The manager doesn't have a close method, but connections auto-close
                pass

            # Reset both global managers after test
            db_module._db_manager = None
            db_module._sqlalchemy_manager = None

    # Cleanup temp file with retry logic for Windows
    import time

    for attempt in range(3):
        try:
            Path(temp_path).unlink()
            break
        except (FileNotFoundError, PermissionError):
            if attempt < 2:
                time.sleep(0.1)  # Brief pause before retry
            else:
                pass  # Give up after 3 attempts


@pytest.fixture
def encryption_key():
    """Generate a test encryption key."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


@pytest.fixture
async def token_manager(temp_database, encryption_key):
    """Create SecureTokenManager with test encryption key."""
    with patch.dict(
        os.environ,
        {"JWT_ENCRYPTION_KEY": encryption_key, "DATABASE_PATH": temp_database},
    ):
        manager = SecureTokenManager()
        yield manager


@pytest.fixture
def sample_jwt():
    """Sample JWT token for testing."""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhZ2VudF9pZCI6InRlc3RfYWdlbnQiLCJhZ2VudF90eXBlIjoiY2xhdWRlIiwicGVybWlzc2lvbnMiOlsicmVhZCIsIndyaXRlIl0sImlhdCI6MTY0MDk5NTIwMCwiZXhwIjoxNjQxMDgxNjAwLCJpc3MiOiJzaGFyZWQtY29udGV4dC1zZXJ2ZXIiLCJhdWQiOiJtY3AtYWdlbnRzIiwianRpIjoidGVzdF9hZ2VudF8xNjQwOTk1MjAwIn0.example_signature"


class TestSecureTokenManager:
    """Test SecureTokenManager functionality."""

    @pytest.mark.asyncio
    async def test_create_protected_token(self, token_manager, sample_jwt):
        """Test creating a protected token."""
        agent_id = "test_agent"

        # Create protected token
        protected_token = await token_manager.create_protected_token(
            sample_jwt, agent_id
        )

        # Verify token format
        assert protected_token.startswith("sct_")
        assert len(protected_token) == 40  # sct_ + 36 char UUID

        # Verify token is stored in database
        async with get_db_connection() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM secure_tokens WHERE token_id = ?",
                (protected_token,),
            )
            count = (await cursor.fetchone())[0]
            assert count == 1

    @pytest.mark.asyncio
    async def test_resolve_protected_token(self, token_manager, sample_jwt):
        """Test resolving protected token back to JWT."""
        agent_id = "test_agent"

        # Create and resolve token
        protected_token = await token_manager.create_protected_token(
            sample_jwt, agent_id
        )
        resolved_jwt = await token_manager.resolve_protected_token(protected_token)

        # Verify resolution
        assert resolved_jwt == sample_jwt

    @pytest.mark.asyncio
    async def test_resolve_invalid_token(self, token_manager):
        """Test resolving invalid protected token."""
        # Test with invalid format
        result = await token_manager.resolve_protected_token("invalid_token")
        assert result is None

        # Test with non-existent token
        result = await token_manager.resolve_protected_token(
            "sct_00000000-0000-0000-0000-000000000000"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_token_expiration(self, token_manager, sample_jwt):
        """Test token expiration handling."""
        agent_id = "test_agent"

        # Create token with immediate expiration
        protected_token = await token_manager.create_protected_token(
            sample_jwt, agent_id
        )

        # Manually expire the token in database
        async with get_db_connection() as conn:
            await conn.execute(
                "UPDATE secure_tokens SET expires_at = ? WHERE token_id = ?",
                (
                    (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                    protected_token,
                ),
            )
            await conn.commit()

        # Verify expired token returns None
        resolved_jwt = await token_manager.resolve_protected_token(protected_token)
        assert resolved_jwt is None

    @pytest.mark.asyncio
    async def test_refresh_token_safely(self, token_manager, sample_jwt):
        """Test atomic token refresh."""
        agent_id = "test_agent"

        # Create initial token
        old_token = await token_manager.create_protected_token(sample_jwt, agent_id)

        # Refresh token
        new_token = await token_manager.refresh_token_safely(old_token, agent_id)

        # Verify new token is different and valid
        assert new_token != old_token
        assert new_token.startswith("sct_")

        resolved_jwt = await token_manager.resolve_protected_token(new_token)
        assert resolved_jwt == sample_jwt

        # Verify old token is cleaned up
        old_jwt = await token_manager.resolve_protected_token(old_token)
        assert old_jwt is None

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, token_manager):
        """Test refreshing invalid token."""
        agent_id = "test_agent"

        with pytest.raises(ValueError, match="Token invalid or expired"):
            await token_manager.refresh_token_safely("sct_invalid", agent_id)

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, token_manager, sample_jwt):
        """Test cleanup of expired tokens."""
        agent_id = "test_agent"

        # Clean up any existing tokens first
        await token_manager.cleanup_expired_tokens()
        async with get_db_connection() as conn:
            await conn.execute("DELETE FROM secure_tokens")
            await conn.commit()

        # Create multiple tokens
        tokens = []
        for i in range(3):
            token = await token_manager.create_protected_token(
                sample_jwt, f"{agent_id}_{i}"
            )
            tokens.append(token)

        # Expire first two tokens, ensure third has future expiration
        async with get_db_connection() as conn:
            # Expire first two tokens
            for token in tokens[:2]:
                await conn.execute(
                    "UPDATE secure_tokens SET expires_at = ? WHERE token_id = ?",
                    (
                        (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                        token,
                    ),
                )
            # Ensure third token has future expiration
            await conn.execute(
                "UPDATE secure_tokens SET expires_at = ? WHERE token_id = ?",
                (
                    (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    tokens[2],
                ),
            )
            await conn.commit()

        # Run cleanup
        cleaned_count = await token_manager.cleanup_expired_tokens()
        # Should clean up at least the 2 expired tokens we created
        assert cleaned_count >= 2

        # Verify only non-expired token remains
        valid_jwt = await token_manager.resolve_protected_token(tokens[2])
        assert valid_jwt == sample_jwt

        expired_jwt = await token_manager.resolve_protected_token(tokens[0])
        assert expired_jwt is None


class TestSecureTokenIntegration:
    """Test integration with existing authentication system."""

    @pytest.mark.asyncio
    async def test_validate_jwt_token_parameter_with_protected_token(
        self, encryption_key, sample_jwt
    ):
        """Test validate_jwt_token_parameter with protected tokens."""
        from shared_context_server.auth import (
            auth_manager,
            validate_jwt_token_parameter,
        )

        with (
            patch.dict(os.environ, {"JWT_ENCRYPTION_KEY": encryption_key}),
            patch.object(auth_manager, "validate_token") as mock_validate,
        ):
            mock_validate.return_value = {
                "valid": True,
                "agent_id": "test_agent",
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "token_id": "test_token_id",
            }

            # Create protected token
            token_manager = get_secure_token_manager()
            protected_token = await token_manager.create_protected_token(
                sample_jwt, "test_agent"
            )

            # Validate protected token
            result = await validate_jwt_token_parameter(protected_token)

            # Verify successful validation
            assert result is not None
            assert result["agent_id"] == "test_agent"
            assert result["agent_type"] == "claude"
            assert result["auth_method"] == "protected_jwt"
            assert result["protected_token"] == protected_token

            # Verify JWT validation was called with resolved token
            mock_validate.assert_called_once_with(sample_jwt)

    @pytest.mark.asyncio
    async def test_validate_jwt_token_parameter_backward_compatibility(
        self, sample_jwt
    ):
        """Test backward compatibility with raw JWT tokens."""
        from shared_context_server.auth import (
            auth_manager,
            validate_jwt_token_parameter,
        )

        # Mock JWT validation to return valid result
        with patch.object(auth_manager, "validate_token") as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "agent_id": "test_agent",
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "token_id": "test_token_id",
            }

            # Validate raw JWT token
            result = await validate_jwt_token_parameter(sample_jwt)

            # Verify successful validation
            assert result is not None
            assert result["agent_id"] == "test_agent"
            assert result["agent_type"] == "claude"
            assert result["auth_method"] == "jwt"
            assert "protected_token" not in result

            # Verify JWT validation was called with original token
            mock_validate.assert_called_once_with(sample_jwt)


class TestJWTExposurePrevention:
    """Test JWT exposure prevention in logs and responses."""

    @pytest.mark.asyncio
    async def test_no_jwt_in_protected_token_format(self, token_manager, sample_jwt):
        """Verify JWT is not exposed in protected token format."""
        agent_id = "test_agent"

        # Create protected token
        protected_token = await token_manager.create_protected_token(
            sample_jwt, agent_id
        )

        # Verify protected token doesn't contain JWT
        assert sample_jwt not in protected_token
        assert "eyJ" not in protected_token  # Base64 JWT header start

        # Verify format is as expected
        assert protected_token.startswith("sct_")

        # Verify database doesn't store raw JWT
        async with get_db_connection() as conn:
            cursor = await conn.execute(
                "SELECT encrypted_jwt FROM secure_tokens WHERE token_id = ?",
                (protected_token,),
            )
            row = await cursor.fetchone()
            assert row is not None, f"Token {protected_token} not found in database"
            encrypted_data = row[0]

            # Encrypted data should not contain raw JWT
            assert sample_jwt.encode() not in encrypted_data
            assert b"eyJ" not in encrypted_data
