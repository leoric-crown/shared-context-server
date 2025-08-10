"""
Database validation tests for Shared Context MCP Server.

These tests validate the critical database fixes identified in consultant review:
- Schema creation and validation
- PRAGMA settings application
- Foreign key enforcement
- Updated triggers functionality
- JSON validation constraints
- Index performance verification
- UTC timestamp handling

Run with: pytest tests/test_database.py -v
"""

import asyncio
import contextlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest

from src.shared_context_server.database import (
    DatabaseManager,
    cleanup_expired_data,
    execute_insert,
    execute_query,
    execute_update,
    get_schema_version,
    health_check,
    initialize_database,
    parse_utc_timestamp,
    utc_now,
    utc_timestamp,
    validate_json_string,
    validate_session_id,
)


@pytest.fixture
async def temp_database():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name

    # Set environment variable for test database
    with patch.dict(os.environ, {"DATABASE_PATH": temp_path}):
        yield temp_path

    # Cleanup
    with contextlib.suppress(FileNotFoundError):
        Path(temp_path).unlink()


class TestDatabaseSchemaSmoke:
    """Schema smoke tests to validate basic functionality."""

    @pytest.mark.asyncio
    async def test_wal_mode_assertion(self, temp_database):
        """Test that WAL mode is properly enabled and fails fast if not."""
        db_manager = DatabaseManager(temp_database)
        await db_manager.initialize()

        async with db_manager.get_connection() as conn:
            cursor = await conn.execute("PRAGMA journal_mode;")
            mode = (await cursor.fetchone())[0].lower()
            assert mode == "wal", f"WAL mode not enabled, got: {mode}"

    @pytest.mark.asyncio
    async def test_required_tables_exist(self, temp_database):
        """Test that all required tables exist after schema application."""
        db_manager = DatabaseManager(temp_database)
        await db_manager.initialize()

        required_tables = [
            "sessions",
            "messages",
            "agent_memory",
            "audit_log",
            "schema_version",
        ]

        async with db_manager.get_connection() as conn:
            for table in required_tables:
                cursor = await conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                result = await cursor.fetchone()
                assert result is not None, f"Required table '{table}' not found"

    @pytest.mark.asyncio
    async def test_foreign_keys_enabled(self, temp_database):
        """Test that foreign key constraints are enabled."""
        db_manager = DatabaseManager(temp_database)
        await db_manager.initialize()

        async with db_manager.get_connection() as conn:
            cursor = await conn.execute("PRAGMA foreign_keys;")
            result = (await cursor.fetchone())[0]
            assert str(result) == "1", f"Foreign keys not enabled, got: {result}"

    @pytest.mark.asyncio
    async def test_schema_version_exists(self, temp_database):
        """Test that schema version table exists and contains version 1."""
        db_manager = DatabaseManager(temp_database)
        await db_manager.initialize()

        version = await get_schema_version()
        assert version == 1, f"Expected schema version 1, got: {version}"


class TestErrorEnvelopeValidation:
    """Test error envelope structure and exception handling."""

    @pytest.mark.asyncio
    async def test_database_connection_error_structure(self):
        """Test DatabaseConnectionError produces proper error envelope."""
        from unittest.mock import patch

        from src.shared_context_server.database import DatabaseConnectionError

        # Test that DatabaseConnectionError can be raised and has proper structure
        try:
            # Use a mock to force a connection error during get_connection
            with patch(
                "aiosqlite.connect", side_effect=Exception("Mocked connection failure")
            ):
                manager = DatabaseManager(":memory:")
                await manager.initialize()  # This should succeed (in-memory)

                # Now try to get a connection, which should fail due to the mock
                async with manager.get_connection():
                    pass

                raise AssertionError("Should have raised DatabaseConnectionError")

        except DatabaseConnectionError as e:
            # Verify exception has proper structure
            error_msg = str(e)
            assert "Connection failed" in error_msg
            assert len(error_msg) > 0, "Error message should not be empty"

    @pytest.mark.asyncio
    def _raise_test_schema_error(self) -> None:
        """Helper to raise a test schema error."""
        from src.shared_context_server.database import DatabaseSchemaError

        raise DatabaseSchemaError("Test schema validation failure")

    async def test_database_schema_error_structure(self, temp_database):
        """Test DatabaseSchemaError produces proper error envelope."""
        from src.shared_context_server.database import DatabaseSchemaError

        # Test that DatabaseSchemaError can be raised and has proper structure
        try:
            # Use helper function to raise a DatabaseSchemaError to test its structure
            self._raise_test_schema_error()

        except DatabaseSchemaError as e:
            # Verify exception has proper structure
            error_msg = str(e)
            assert "Test schema validation failure" in error_msg
            assert len(error_msg) > 0, "Error message should not be empty"

    @pytest.mark.asyncio
    async def test_health_check_error_envelope(self, temp_database):
        """Test health check returns proper error envelope on failure."""
        # Test healthy case first
        db_manager = DatabaseManager(temp_database)
        await db_manager.initialize()

        health_result = await health_check()

        # Verify healthy envelope structure
        assert "status" in health_result
        assert "timestamp" in health_result
        assert health_result["status"] == "healthy"

        # Test unhealthy case by corrupting database path
        with patch(
            "src.shared_context_server.database.get_database_manager"
        ) as mock_get_db:
            mock_get_db.return_value.is_initialized = False
            mock_get_db.return_value.initialize.side_effect = Exception(
                "Simulated database failure"
            )

            unhealthy_result = await health_check()

            # Verify error envelope structure
            assert "status" in unhealthy_result
            assert "error" in unhealthy_result
            assert "timestamp" in unhealthy_result
            assert unhealthy_result["status"] == "unhealthy"
            assert "Simulated database failure" in str(unhealthy_result["error"])


class TestUtcTimestampValidation:
    """UTC timestamp and metadata validation tests."""

    @pytest.mark.asyncio
    async def test_utc_timestamp_creation(self, temp_database):
        """Test that UTC timestamps are created and stored correctly."""
        from src.shared_context_server.models import SessionModel

        db_manager = DatabaseManager(temp_database)
        await db_manager.initialize()

        # Create session with UTC timestamp
        now = utc_now()
        session = SessionModel(
            id="session_1234567890abcdef",
            purpose="UTC timestamp test",
            created_by="test_agent",
            created_at=now,
        )

        # Insert session
        async with db_manager.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by, created_at)
                VALUES (?, ?, ?, ?)
            """,
                (
                    session.id,
                    session.purpose,
                    session.created_by,
                    session.created_at.isoformat(),
                ),
            )
            await conn.commit()

        # Retrieve and verify UTC timestamp using the same database manager
        async with db_manager.get_connection() as conn:
            # Set row factory to return dict-like rows
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT created_at FROM sessions WHERE id = ?", (session.id,)
            )
            result = await cursor.fetchall()

        stored_timestamp = parse_utc_timestamp(result[0]["created_at"])

        # Should be within 1 second of creation time
        time_diff = abs((stored_timestamp - now).total_seconds())
        assert time_diff < 1, f"Timestamp mismatch: {time_diff} seconds"
        assert stored_timestamp.tzinfo == timezone.utc, "Timestamp not in UTC"

    @pytest.mark.asyncio
    async def test_metadata_round_trip(self, temp_database):
        """Test metadata serialization and deserialization."""
        from src.shared_context_server.models import (
            deserialize_metadata,
            serialize_metadata,
        )

        db_manager = DatabaseManager(temp_database)
        await db_manager.initialize()

        # Test complex metadata with unicode and nested structures
        test_metadata = {
            "unicode_test": "こんにちは世界 🌍",
            "nested_array": [1, 2, {"nested": "value"}],
            "boolean_flags": {"active": True, "debug": False},
            "numbers": {"pi": 3.14159, "answer": 42},
            "null_value": None,
            "empty_string": "",
            "special_chars": "!@#$%^&*()[]{}|\\:;\"'<>,.?/",
        }

        # Serialize metadata
        metadata_json = serialize_metadata(test_metadata)

        # Insert session with metadata
        session_id = "session_metadata_test"
        async with db_manager.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by, metadata)
                VALUES (?, ?, ?, ?)
            """,
                (session_id, "Metadata test", "test_agent", metadata_json),
            )
            await conn.commit()

        # Retrieve and deserialize using the same database manager
        async with db_manager.get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT metadata FROM sessions WHERE id = ?", (session_id,)
            )
            result = await cursor.fetchall()

        retrieved_metadata = deserialize_metadata(result[0]["metadata"])

        # Verify round-trip integrity
        assert retrieved_metadata == test_metadata, "Metadata round-trip failed"
        assert (
            retrieved_metadata["unicode_test"] == "こんにちは世界 🌍"
        ), "Unicode handling failed"
        assert (
            retrieved_metadata["nested_array"][2]["nested"] == "value"
        ), "Nested structure failed"


@pytest.fixture
async def test_db_manager():
    """Create test database manager."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name

    try:
        db_manager = DatabaseManager(temp_path)
        await db_manager.initialize()
        yield db_manager
    finally:
        with contextlib.suppress(FileNotFoundError):
            Path(temp_path).unlink()


class TestDatabaseSchema:
    """Test database schema creation and validation."""

    @pytest.mark.asyncio
    async def test_schema_initialization(self, test_db_manager):
        """Test that database schema is created correctly."""

        # Check that all required tables exist
        async with test_db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table'
                ORDER BY name
            """
            )
            tables = [row[0] for row in await cursor.fetchall()]

        required_tables = [
            "agent_memory",
            "audit_log",
            "messages",
            "schema_version",
            "sessions",
        ]

        for table in required_tables:
            assert table in tables, f"Required table '{table}' not found"

    @pytest.mark.asyncio
    async def test_schema_version_tracking(self, test_db_manager):
        """Test that schema version is tracked correctly."""

        async with test_db_manager.get_connection() as conn:
            cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
            version = (await cursor.fetchone())[0]

        assert version == 1, f"Expected schema version 1, got {version}"

    @pytest.mark.asyncio
    async def test_views_creation(self, test_db_manager):
        """Test that helpful views are created."""

        async with test_db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='view'
                ORDER BY name
            """
            )
            views = [row[0] for row in await cursor.fetchall()]

        expected_views = [
            "active_sessions_with_activity",
            "agent_memory_summary",
            "audit_activity_summary",
        ]

        for view in expected_views:
            assert view in views, f"Expected view '{view}' not found"


class TestPragmaSettings:
    """Test PRAGMA settings application and validation."""

    @pytest.mark.asyncio
    async def test_pragma_application(self, test_db_manager):
        """Test that critical PRAGMA settings are applied correctly."""

        async with test_db_manager.get_connection() as conn:
            # Test journal_mode = WAL
            cursor = await conn.execute("PRAGMA journal_mode;")
            result = (await cursor.fetchone())[0]
            assert result.lower() == "wal", f"Expected WAL mode, got {result}"

            # Test foreign_keys = ON
            cursor = await conn.execute("PRAGMA foreign_keys;")
            result = (await cursor.fetchone())[0]
            assert result == 1, f"Expected foreign_keys=1, got {result}"

            # Test synchronous = NORMAL
            cursor = await conn.execute("PRAGMA synchronous;")
            result = (await cursor.fetchone())[0]
            assert result == 1, f"Expected synchronous=1 (NORMAL), got {result}"

            # Test cache_size is reasonable
            cursor = await conn.execute("PRAGMA cache_size;")
            result = (await cursor.fetchone())[0]
            assert result == -8000, f"Expected cache_size=-8000, got {result}"

            # Test mmap_size is optimized (256MB = 268435456)
            cursor = await conn.execute("PRAGMA mmap_size;")
            result = (await cursor.fetchone())[0]
            assert result == 268435456, f"Expected mmap_size=268435456, got {result}"

    @pytest.mark.asyncio
    async def test_multiple_connections_pragma_consistency(self, test_db_manager):
        """Test that PRAGMA settings are applied consistently across connections."""

        pragma_checks = []

        # Open multiple connections and check PRAGMA settings
        for i in range(3):
            async with test_db_manager.get_connection() as conn:
                cursor = await conn.execute("PRAGMA journal_mode;")
                journal_mode = (await cursor.fetchone())[0]

                cursor = await conn.execute("PRAGMA foreign_keys;")
                foreign_keys = (await cursor.fetchone())[0]

                pragma_checks.append(
                    {
                        "connection": i,
                        "journal_mode": journal_mode.lower(),
                        "foreign_keys": foreign_keys,
                    }
                )

        # Verify all connections have consistent settings
        for check in pragma_checks:
            assert check["journal_mode"] == "wal"
            assert check["foreign_keys"] == 1


class TestForeignKeyEnforcement:
    """Test foreign key constraint enforcement."""

    @pytest.mark.asyncio
    async def test_foreign_key_enforcement_enabled(self, test_db_manager):
        """Test that foreign key constraints are enforced."""

        async with test_db_manager.get_connection() as conn:
            # Try to insert message with non-existent session_id
            with pytest.raises(aiosqlite.IntegrityError):
                await conn.execute(
                    """
                    INSERT INTO messages (session_id, sender, content)
                    VALUES ('session_nonexistent', 'test_agent', 'test content')
                """
                )
                await conn.commit()

    @pytest.mark.asyncio
    async def test_cascade_delete_sessions(self, test_db_manager):
        """Test that deleting session cascades to messages and agent_memory."""

        async with test_db_manager.get_connection() as conn:
            # Create test session
            session_id = "session_test12345678"
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by)
                VALUES (?, 'test session', 'test_agent')
            """,
                (session_id,),
            )

            # Add message and memory entries
            await conn.execute(
                """
                INSERT INTO messages (session_id, sender, content)
                VALUES (?, 'test_agent', 'test message')
            """,
                (session_id,),
            )

            await conn.execute(
                """
                INSERT INTO agent_memory (agent_id, session_id, key, value)
                VALUES ('test_agent', ?, 'test_key', '{"test": true}')
            """,
                (session_id,),
            )

            await conn.commit()

            # Verify data exists
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
            )
            message_count_before = (await cursor.fetchone())[0]
            assert message_count_before == 1

            cursor = await conn.execute(
                "SELECT COUNT(*) FROM agent_memory WHERE session_id = ?", (session_id,)
            )
            memory_count_before = (await cursor.fetchone())[0]
            assert memory_count_before == 1

            # Delete session
            await conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await conn.commit()

            # Verify cascade delete worked
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
            )
            message_count_after = (await cursor.fetchone())[0]
            assert message_count_after == 0

            cursor = await conn.execute(
                "SELECT COUNT(*) FROM agent_memory WHERE session_id = ?", (session_id,)
            )
            memory_count_after = (await cursor.fetchone())[0]
            assert memory_count_after == 0


class TestUpdatedTriggers:
    """Test updated_at trigger functionality."""

    @pytest.mark.asyncio
    async def test_sessions_updated_trigger(self, test_db_manager):
        """Test that sessions.updated_at is updated automatically."""

        async with test_db_manager.get_connection() as conn:
            session_id = "session_trigger123456"

            # Create session
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by)
                VALUES (?, 'trigger test', 'test_agent')
            """,
                (session_id,),
            )
            await conn.commit()

            # Get initial timestamps
            cursor = await conn.execute(
                """
                SELECT created_at, updated_at FROM sessions WHERE id = ?
            """,
                (session_id,),
            )
            initial_times = await cursor.fetchone()
            initial_created = initial_times[0]
            initial_updated = initial_times[1]

            # Wait a moment and update (SQLite CURRENT_TIMESTAMP has second precision)
            await asyncio.sleep(1.1)
            await conn.execute(
                """
                UPDATE sessions SET purpose = 'updated purpose' WHERE id = ?
            """,
                (session_id,),
            )
            await conn.commit()

            # Get updated timestamps
            cursor = await conn.execute(
                """
                SELECT created_at, updated_at FROM sessions WHERE id = ?
            """,
                (session_id,),
            )
            final_times = await cursor.fetchone()
            final_created = final_times[0]
            final_updated = final_times[1]

            # Verify created_at unchanged, updated_at changed
            assert final_created == initial_created
            assert final_updated != initial_updated

    @pytest.mark.asyncio
    async def test_agent_memory_updated_trigger(self, test_db_manager):
        """Test that agent_memory.updated_at is updated automatically."""

        async with test_db_manager.get_connection() as conn:
            # Create memory entry
            await conn.execute(
                """
                INSERT INTO agent_memory (agent_id, key, value)
                VALUES ('test_agent', 'trigger_test', '{"version": 1}')
            """
            )
            await conn.commit()

            # Get initial timestamps
            cursor = await conn.execute(
                """
                SELECT created_at, updated_at FROM agent_memory
                WHERE agent_id = 'test_agent' AND key = 'trigger_test'
            """
            )
            initial_times = await cursor.fetchone()
            initial_created = initial_times[0]
            initial_updated = initial_times[1]

            # Wait and update (SQLite CURRENT_TIMESTAMP has second precision)
            await asyncio.sleep(1.1)
            await conn.execute(
                """
                UPDATE agent_memory SET value = '{"version": 2}'
                WHERE agent_id = 'test_agent' AND key = 'trigger_test'
            """
            )
            await conn.commit()

            # Get updated timestamps
            cursor = await conn.execute(
                """
                SELECT created_at, updated_at FROM agent_memory
                WHERE agent_id = 'test_agent' AND key = 'trigger_test'
            """
            )
            final_times = await cursor.fetchone()
            final_created = final_times[0]
            final_updated = final_times[1]

            # Verify trigger worked
            assert final_created == initial_created
            assert final_updated != initial_updated


class TestJsonValidation:
    """Test JSON validation constraints."""

    @pytest.mark.asyncio
    async def test_valid_json_metadata_accepted(self, test_db_manager):
        """Test that valid JSON metadata is accepted."""

        async with test_db_manager.get_connection() as conn:
            # Valid JSON should work
            valid_metadata = json.dumps({"key": "value", "number": 42})

            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by, metadata)
                VALUES ('session_json_test123', 'json test', 'test_agent', ?)
            """,
                (valid_metadata,),
            )
            await conn.commit()

            # Verify it was stored
            cursor = await conn.execute(
                """
                SELECT metadata FROM sessions WHERE id = 'session_json_test123'
            """
            )
            stored_metadata = (await cursor.fetchone())[0]
            assert stored_metadata == valid_metadata

    @pytest.mark.asyncio
    async def test_invalid_json_metadata_rejected(self, test_db_manager):
        """Test that invalid JSON metadata is rejected."""

        async with test_db_manager.get_connection() as conn:
            # Invalid JSON should be rejected
            invalid_metadata = '{"invalid": json,}'

            with pytest.raises(aiosqlite.IntegrityError):
                await conn.execute(
                    """
                    INSERT INTO sessions (id, purpose, created_by, metadata)
                    VALUES ('session_bad_json123', 'json test', 'test_agent', ?)
                """,
                    (invalid_metadata,),
                )
                await conn.commit()

    @pytest.mark.asyncio
    async def test_null_metadata_allowed(self, test_db_manager):
        """Test that NULL metadata is allowed."""

        async with test_db_manager.get_connection() as conn:
            # NULL metadata should be allowed
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by, metadata)
                VALUES ('session_null_meta123', 'null test', 'test_agent', NULL)
            """
            )
            await conn.commit()

            # Verify it was stored
            cursor = await conn.execute(
                """
                SELECT metadata FROM sessions WHERE id = 'session_null_meta123'
            """
            )
            stored_metadata = (await cursor.fetchone())[0]
            assert stored_metadata is None


class TestIndexPerformance:
    """Test that performance indexes are working correctly."""

    @pytest.mark.asyncio
    async def test_indexes_exist(self, test_db_manager):
        """Test that performance indexes are created."""

        async with test_db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='index' AND sql IS NOT NULL
                ORDER BY name
            """
            )
            indexes = [row[0] for row in await cursor.fetchall()]

        expected_indexes = [
            "idx_agent_memory_lookup",
            "idx_audit_log_timestamp",
            "idx_messages_session_id",
            "idx_messages_session_time",
        ]

        for index in expected_indexes:
            assert index in indexes, f"Expected index '{index}' not found"

    @pytest.mark.asyncio
    async def test_index_usage(self, test_db_manager):
        """Test that indexes are being used for queries."""

        async with test_db_manager.get_connection() as conn:
            # Add test data
            session_id = "session_perf_test123"
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by)
                VALUES (?, 'performance test', 'test_agent')
            """,
                (session_id,),
            )

            # Add multiple messages
            for i in range(10):
                await conn.execute(
                    """
                    INSERT INTO messages (session_id, sender, content)
                    VALUES (?, ?, ?)
                """,
                    (session_id, f"agent_{i}", f"Message {i}"),
                )

            await conn.commit()

            # Query with EXPLAIN QUERY PLAN to check index usage
            cursor = await conn.execute(
                """
                EXPLAIN QUERY PLAN
                SELECT * FROM messages WHERE session_id = ?
            """,
                (session_id,),
            )

            plan = await cursor.fetchall()
            plan_text = " ".join([str(row) for row in plan])

            # Check that index is mentioned in query plan
            assert (
                "idx_messages_session_id" in plan_text
            ), f"Index not used in query plan: {plan_text}"


class TestUtcTimestamps:
    """Test UTC timestamp handling."""

    @pytest.mark.asyncio
    async def test_utc_timestamp_functions(self, test_db_manager):
        """Test UTC timestamp utility functions."""

        # Test utc_now
        now = utc_now()
        assert now.tzinfo == timezone.utc

        # Test utc_timestamp
        timestamp_str = utc_timestamp()
        assert timestamp_str.endswith("+00:00") or timestamp_str.endswith("Z")

        # Test parse_utc_timestamp
        parsed = parse_utc_timestamp(timestamp_str)
        assert parsed.tzinfo == timezone.utc
        assert abs((parsed - now).total_seconds()) < 2  # Should be very close

    @pytest.mark.asyncio
    async def test_database_timestamp_storage(self, test_db_manager):
        """Test that timestamps are stored and retrieved correctly."""

        async with test_db_manager.get_connection() as conn:
            session_id = "session_time_test123"

            # Insert with explicit timestamp
            test_time = datetime.now(timezone.utc)
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by, created_at, updated_at)
                VALUES (?, 'time test', 'test_agent', ?, ?)
            """,
                (session_id, test_time.isoformat(), test_time.isoformat()),
            )
            await conn.commit()

            # Retrieve and verify
            cursor = await conn.execute(
                """
                SELECT created_at, updated_at FROM sessions WHERE id = ?
            """,
                (session_id,),
            )
            times = await cursor.fetchone()
            stored_created = times[0]
            stored_updated = times[1]

            # Parse stored timestamps
            parsed_created = parse_utc_timestamp(stored_created)
            parsed_updated = parse_utc_timestamp(stored_updated)

            # Verify UTC timezone
            assert parsed_created.tzinfo == timezone.utc
            assert parsed_updated.tzinfo == timezone.utc


class TestValidationFunctions:
    """Test validation utility functions."""

    def test_validate_session_id(self):
        """Test session ID validation."""

        # Valid session IDs
        valid_ids = [
            "session_1234567890abcdef",
            "session_abcdef1234567890",
            "session_0000000000000000",
        ]

        for session_id in valid_ids:
            assert validate_session_id(session_id) is True

        # Invalid session IDs
        invalid_ids = [
            "invalid_format",
            "session_",
            "session_123",  # Too short
            "session_1234567890abcdefg",  # Too long
            "session_123456789GABCDEF",  # Uppercase
            "not_session_1234567890ab",  # Wrong prefix
        ]

        for session_id in invalid_ids:
            assert validate_session_id(session_id) is False

    def test_validate_json_string(self):
        """Test JSON string validation."""

        # Valid JSON
        assert validate_json_string('{"key": "value"}') is True
        assert validate_json_string("[]") is True
        assert validate_json_string("null") is True
        assert validate_json_string("") is True  # Empty is valid
        assert validate_json_string(None) is True  # None is valid

        # Invalid JSON
        assert validate_json_string('{"invalid": json,}') is False
        assert validate_json_string("{key: value}") is False
        assert validate_json_string("undefined") is False


class TestHealthCheck:
    """Test database health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, temp_database):
        """Test health check on healthy database."""

        with patch.dict(os.environ, {"DATABASE_PATH": temp_database}):
            result = await health_check()

        assert result["status"] == "healthy"
        assert result["database_initialized"] is True
        assert result["database_exists"] is True
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_schema_version(self, test_db_manager):
        """Test schema version retrieval."""

        # Initialize the database if not already done
        await test_db_manager.initialize()

        # Patch the DATABASE_PATH and reset global manager to use test database
        with patch.dict(
            os.environ, {"DATABASE_PATH": str(test_db_manager.database_path)}
        ):
            # Reset global database manager so it uses the patched path
            import src.shared_context_server.database as db_module

            db_module._db_manager = None

            # Initialize the global database manager with test database
            await initialize_database()

            version = await get_schema_version()

        assert version == 1


class TestCleanupOperations:
    """Test database cleanup operations."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_data(self, test_db_manager):
        """Test cleanup of expired agent memory."""

        async with test_db_manager.get_connection() as conn:
            # Add memory entry that will expire very soon
            now = datetime.now(timezone.utc)
            created_at = now
            expires_at = now + timedelta(milliseconds=100)
            await conn.execute(
                """
                INSERT INTO agent_memory (agent_id, key, value, created_at, expires_at)
                VALUES ('test_agent', 'expires_soon_key', '{"expires_soon": true}', ?, ?)
            """,
                (created_at.timestamp(), expires_at.timestamp()),
            )

            # Wait for it to expire
            await asyncio.sleep(0.2)

            # Add non-expired memory entry
            now2 = datetime.now(timezone.utc)
            future_time = now2 + timedelta(hours=1)
            await conn.execute(
                """
                INSERT INTO agent_memory (agent_id, key, value, created_at, expires_at)
                VALUES ('test_agent', 'valid_key', '{"valid": true}', ?, ?)
            """,
                (now2.timestamp(), future_time.timestamp()),
            )

            await conn.commit()

        # Set DATABASE_PATH for cleanup function and reset global manager
        with patch.dict(
            os.environ, {"DATABASE_PATH": str(test_db_manager.database_path)}
        ):
            # Reset global database manager so it uses the existing test database
            import src.shared_context_server.database as db_module

            db_module._db_manager = test_db_manager

            # Run cleanup (using the existing initialized database)
            stats = await cleanup_expired_data()

        # Verify expired data was cleaned
        assert stats["expired_memory"] >= 1

        # Verify valid data remains
        async with test_db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT COUNT(*) FROM agent_memory WHERE key = 'valid_key'
            """
            )
            valid_count = (await cursor.fetchone())[0]
            assert valid_count == 1

            cursor = await conn.execute(
                """
                SELECT COUNT(*) FROM agent_memory WHERE key = 'expired_key'
            """
            )
            expired_count = (await cursor.fetchone())[0]
            assert expired_count == 0


class TestConnectionPooling:
    """Test connection management and statistics."""

    @pytest.mark.asyncio
    async def test_connection_statistics(self, test_db_manager):
        """Test connection statistics tracking."""

        initial_stats = test_db_manager.get_stats()
        assert initial_stats["connection_count"] == 0
        assert initial_stats["is_initialized"] is True

        # Use a connection
        async with test_db_manager.get_connection():
            # Connection count should be tracked during usage
            pass

        # Connection should be cleaned up after context exit
        final_stats = test_db_manager.get_stats()
        assert final_stats["connection_count"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_connections(self, test_db_manager):
        """Test multiple concurrent connections."""

        async def use_connection(connection_id):
            async with test_db_manager.get_connection() as conn:
                cursor = await conn.execute("SELECT ?", (connection_id,))
                result = (await cursor.fetchone())[0]
                assert result == connection_id
                await asyncio.sleep(0.1)  # Hold connection briefly
                return result

        # Run multiple concurrent connections
        tasks = [use_connection(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify all connections worked
        assert results == list(range(5))


@pytest.mark.asyncio
async def test_integration_with_global_functions(test_db_manager):
    """Test integration with global database functions."""

    # Initialize the database if not already done
    await test_db_manager.initialize()

    with patch.dict(os.environ, {"DATABASE_PATH": str(test_db_manager.database_path)}):
        # Reset global database manager so it uses the patched path
        import src.shared_context_server.database as db_module

        db_module._db_manager = None

        # Initialize global database manager
        await initialize_database()

        # Test execute_query
        results = await execute_query(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [row["name"] for row in results]
        assert "sessions" in table_names

        # Test execute_insert
        session_id = await execute_insert(
            """
            INSERT INTO sessions (id, purpose, created_by)
            VALUES ('session_global_test12', 'global test', 'test_agent')
        """
        )
        assert session_id is not None

        # Test execute_update
        affected_rows = await execute_update(
            """
            UPDATE sessions SET purpose = 'updated global test'
            WHERE id = 'session_global_test12'
        """
        )
        assert affected_rows == 1
