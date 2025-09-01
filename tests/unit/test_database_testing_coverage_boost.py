"""
Coverage boost tests for database_testing module.

Targets untested utility functions and error paths for significant coverage gains.
"""

from unittest.mock import Mock, patch

import pytest

from src.shared_context_server.database_testing import (
    TestDatabaseManager,
    patch_database_connection,
)


class TestDatabaseTestingCoverageBoost:
    """High-impact tests for untested database testing utilities."""

    def test_get_stats_returns_expected_structure(self):
        """Test get_stats returns proper statistics dictionary."""
        db_manager = TestDatabaseManager()

        stats = db_manager.get_stats()

        assert isinstance(stats, dict)
        assert "database_path" in stats
        assert "is_initialized" in stats
        assert "connection_count" in stats
        assert "database_exists" in stats
        assert "database_size_mb" in stats

        # Verify specific values
        assert stats["is_initialized"] is False  # Not initialized yet
        assert stats["connection_count"] == 1
        assert stats["database_exists"] is True
        assert stats["database_size_mb"] == 0.1

    def test_get_stats_reflects_initialization_state(self):
        """Test get_stats reflects actual initialization state."""
        db_manager = TestDatabaseManager()

        # Before initialization
        stats = db_manager.get_stats()
        assert stats["is_initialized"] is False

        # After marking as initialized
        db_manager._initialized = True
        stats = db_manager.get_stats()
        assert stats["is_initialized"] is True

    @patch("tempfile.NamedTemporaryFile")
    @patch("time.sleep")
    def test_create_temp_file_retry_on_oserror(self, mock_sleep, mock_named_temp_file):
        """Test temp file creation retries on OSError."""
        # Mock first attempt to fail, subsequent attempts to succeed
        mock_temp_file = Mock()
        mock_named_temp_file.side_effect = [
            OSError("Permission denied"),  # First attempt fails
            mock_temp_file,  # Second attempt succeeds
        ]

        # Create manager with memory database to avoid calling temp file creation in init
        db_manager = TestDatabaseManager()
        result = db_manager._create_temp_file_with_retry(max_retries=2)

        assert result is mock_temp_file
        assert mock_named_temp_file.call_count == 2
        mock_sleep.assert_called_once_with(0.1)  # First retry delay

    @patch("tempfile.NamedTemporaryFile")
    @patch("time.sleep")
    def test_create_temp_file_all_retries_fail(self, mock_sleep, mock_named_temp_file):
        """Test temp file creation raises OSError after all retries fail."""
        mock_named_temp_file.side_effect = [
            OSError("Persistent error")
        ] * 5  # Enough for all attempts

        # Create manager with memory database to avoid calling temp file creation in init
        db_manager = TestDatabaseManager()

        with pytest.raises(
            OSError, match="Failed to create temporary database file after 3 attempts"
        ):
            db_manager._create_temp_file_with_retry(max_retries=2)

        assert mock_named_temp_file.call_count == 3  # Initial + 2 retries
        assert mock_sleep.call_count == 2  # Two retry delays

    @patch("tempfile.NamedTemporaryFile")
    @patch("time.sleep")
    def test_create_temp_file_exponential_backoff(
        self, mock_sleep, mock_named_temp_file
    ):
        """Test temp file creation uses exponential backoff."""
        mock_temp_file = Mock()
        mock_named_temp_file.side_effect = [
            OSError("Error 1"),  # First attempt fails
            OSError("Error 2"),  # Second attempt fails
            mock_temp_file,  # Third attempt succeeds
        ]

        # Create manager with memory database to avoid calling temp file creation in init
        db_manager = TestDatabaseManager()
        result = db_manager._create_temp_file_with_retry(max_retries=2)

        assert result is mock_temp_file
        # Verify exponential backoff: 0.1s, then 0.2s
        expected_calls = [((0.1,),), ((0.2,),)]
        assert mock_sleep.call_args_list == expected_calls

    @pytest.mark.asyncio
    async def test_patch_database_connection_context_manager(self):
        """Test patch_database_connection context manager basic functionality."""
        test_db = TestDatabaseManager()

        # Test context manager doesn't crash
        async with patch_database_connection(test_db):
            # Context manager entered successfully
            pass

        # Should reach here without errors

    @pytest.mark.asyncio
    async def test_patch_database_connection_initializes_database(self):
        """Test patch_database_connection initializes the test database."""
        test_db = TestDatabaseManager()

        with (
            patch.object(test_db, "initialize") as mock_init,
            patch.object(test_db, "close") as mock_close,
        ):
            async with patch_database_connection(test_db):
                pass

            mock_init.assert_called_once()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_patch_database_connection_cleans_up_on_exception(self):
        """Test patch_database_connection cleans up even if exception occurs."""
        test_db = TestDatabaseManager()

        with (
            patch.object(test_db, "initialize") as mock_init,
            patch.object(test_db, "close") as mock_close,
        ):
            with pytest.raises(ValueError):
                async with patch_database_connection(test_db):
                    raise ValueError("Test exception")

            mock_init.assert_called_once()
            mock_close.assert_called_once()  # Should still clean up
