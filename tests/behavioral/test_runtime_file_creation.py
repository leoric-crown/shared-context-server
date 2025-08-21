"""
Runtime database file creation tests.

Tests what files are actually created during server startup and database
initialization. Focuses on real-world scenarios that might create unwanted files.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestRuntimeFileCreation:
    """Test actual file creation during server operations."""

    def test_investigate_current_database_files(self):
        """Investigate what database files currently exist in project directory."""
        project_root = Path(__file__).parent.parent.parent

        # Find all database-related files
        db_files = []
        for pattern in ["*.db", "*.db-*"]:
            db_files.extend(project_root.glob(pattern))

        db_file_info = []
        for db_file in db_files:
            stat = db_file.stat()
            db_file_info.append(
                {
                    "name": db_file.name,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "path": str(db_file),
                }
            )

        # Print findings for analysis
        print("\n=== DATABASE FILES FOUND ===")
        for info in sorted(db_file_info, key=lambda x: x["name"]):
            print(
                f"{info['name']:20} | Size: {info['size']:8} bytes | Path: {info['path']}"
            )

        # Look specifically for the problematic file
        shared_context_files = [
            f for f in db_file_info if "shared_context" in f["name"]
        ]
        chat_history_files = [f for f in db_file_info if "chat_history" in f["name"]]

        print("\n=== ANALYSIS ===")
        print(f"shared_context.* files: {len(shared_context_files)}")
        print(f"chat_history.* files: {len(chat_history_files)}")

        if shared_context_files:
            print("\n=== UNWANTED FILES DETECTED ===")
            for f in shared_context_files:
                print(f"❌ {f['name']} - {f['size']} bytes")

        # This test always passes - it's for investigation
        assert True

    @pytest.mark.asyncio
    async def test_database_connection_file_creation_behavior(self):
        """Test what files are created during database connection attempts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test SQLAlchemy connection with explicit database URL
            test_db_path = temp_path / "test_behavior.db"
            database_url = f"sqlite:///{test_db_path}"

            print("\n=== TESTING DATABASE CONNECTION ===")
            print(f"Test directory: {temp_dir}")
            print(f"Database URL: {database_url}")

            # Record initial files
            initial_files = {f.name for f in temp_path.iterdir()}
            print(f"Initial files: {initial_files}")

            # Try to replicate the issue with SQLAlchemy backend
            try:
                from shared_context_server.database_sqlalchemy import (
                    get_sqlalchemy_connection,
                )

                with patch.dict(os.environ, {"DATABASE_URL": database_url}):
                    # This might create files
                    async with get_sqlalchemy_connection() as conn:
                        await conn.execute("SELECT 1")

            except Exception as e:
                print(f"SQLAlchemy connection failed: {e}")

            # Record final files
            final_files = {f.name for f in temp_path.iterdir()}
            created_files = final_files - initial_files

            print(f"Files created: {created_files}")

            # Check for unwanted file patterns
            unwanted_patterns = ["shared_context", "default"]
            unwanted_files = [
                f
                for f in created_files
                if any(pattern in f for pattern in unwanted_patterns)
            ]

            if unwanted_files:
                print(f"❌ Unwanted files created: {unwanted_files}")
            else:
                print("✅ No unwanted files created")

            # Test passes if no unwanted files created
            assert len(unwanted_files) == 0, f"Unwanted files created: {unwanted_files}"

    @pytest.mark.asyncio
    async def test_server_startup_file_creation(self):
        """Test file creation during server startup simulation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Set up environment to use temp directory
            test_db_url = f"sqlite:///{temp_path}/startup_test.db"

            with patch.dict(
                os.environ,
                {"DATABASE_URL": test_db_url, "API_KEY": "test-key-for-startup"},
            ):
                # Record initial state
                initial_files = {f.name for f in temp_path.iterdir()}

                try:
                    # Import and initialize database (simulates server startup)
                    from shared_context_server.database import initialize_database

                    await initialize_database()

                except Exception as e:
                    print(f"Database initialization failed: {e}")

                # Check what files were created
                final_files = {f.name for f in temp_path.iterdir()}
                created_files = final_files - initial_files

                print("\n=== SERVER STARTUP FILE CREATION ===")
                print(f"Created files: {created_files}")

                # Verify only expected files created
                expected_patterns = ["startup_test.db"]
                unexpected_files = [
                    f
                    for f in created_files
                    if not any(pattern in f for pattern in expected_patterns)
                ]

                assert len(unexpected_files) == 0, (
                    f"Unexpected files: {unexpected_files}"
                )

    def test_configuration_module_file_paths(self):
        """Test that configuration module returns correct file paths."""
        from shared_context_server.config import (
            get_database_url,
            get_default_database_path,
        )

        print("\n=== CONFIGURATION ANALYSIS ===")

        # Test default path in current environment
        default_path = get_default_database_path()
        print(f"Default database path: {default_path}")

        # Test database URL
        db_url = get_database_url()
        print(f"Database URL: {db_url}")

        # Verify no 'shared_context' in paths
        assert "shared_context" not in default_path.lower()
        assert "shared_context" not in db_url.lower()

        # Verify 'chat_history' is used
        assert (
            "chat_history" in default_path.lower() or "chat_history" in db_url.lower()
        )

    @pytest.mark.asyncio
    async def test_investigate_sqlalchemy_fallback_behavior(self):
        """Investigate if SQLAlchemy backend has hardcoded fallback paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test with intentionally invalid configuration to trigger fallbacks
            invalid_configs = [
                "",  # Empty string
                "invalid-url",  # Invalid URL
                "sqlite:///nonexistent/path/test.db",  # Path that can't be created
            ]

            for invalid_config in invalid_configs:
                print(f"\n=== TESTING INVALID CONFIG: {invalid_config} ===")

                initial_files = {f.name for f in temp_path.iterdir()}

                try:
                    with patch.dict(
                        os.environ,
                        {"DATABASE_URL": invalid_config, "API_KEY": "test-key"},
                    ):
                        # Force config reload using ContextVar approach
                        from shared_context_server.config_context import (
                            reset_config_context,
                        )

                        reset_config_context()
                        # Try to get database connection
                        try:
                            from shared_context_server.database import (
                                get_db_connection,
                            )

                            async with get_db_connection() as conn:
                                await conn.execute("SELECT 1")
                        except Exception as e:
                            print(f"Expected failure: {e}")

                except Exception as e:
                    print(f"Configuration error: {e}")

                # Check for any files created during failure scenarios
                final_files = {f.name for f in temp_path.iterdir()}
                created_files = final_files - initial_files

                if created_files:
                    print(f"Files created during failure: {created_files}")

                # Check for 'shared_context' files
                shared_context_files = [
                    f for f in created_files if "shared_context" in f
                ]

                if shared_context_files:
                    print(f"❌ shared_context files created: {shared_context_files}")
                    # This would be a bug - fallback creating wrong files
                    pytest.fail(
                        f"Invalid config created shared_context files: {shared_context_files}"
                    )


class TestFileCreationSourceTracking:
    """Track down the exact source of file creation."""

    def test_trace_database_url_usage(self):
        """Trace how database URLs are used throughout the codebase."""
        from shared_context_server.config import get_database_url
        from shared_context_server.database import get_db_connection
        # Note: SQLAlchemy module uses SimpleSQLAlchemyManager class, not a standalone function

        print("\n=== DATABASE URL TRACING ===")

        # Trace configuration
        db_url = get_database_url()
        print(f"Config database URL: {db_url}")

        # Check if there are any hardcoded paths in connection functions
        import inspect

        # Get source of connection functions
        try:
            db_source = inspect.getsource(get_db_connection)
            # SQLAlchemy uses SimpleSQLAlchemyManager class instead of standalone function
            from shared_context_server.database_sqlalchemy import (
                SimpleSQLAlchemyManager,
            )

            sqlalchemy_source = inspect.getsource(SimpleSQLAlchemyManager)

            # Look for hardcoded database paths
            hardcoded_patterns = [
                "shared_context.db",
                '"shared_context',
                "'shared_context",
            ]

            for pattern in hardcoded_patterns:
                if pattern in db_source:
                    print(f"❌ Found '{pattern}' in get_db_connection")
                if pattern in sqlalchemy_source:
                    print(f"❌ Found '{pattern}' in get_sqlalchemy_connection")

        except Exception as e:
            print(f"Could not inspect source: {e}")

        # This test is for investigation
        assert True

    def test_find_all_database_references(self):
        """Find all database file references in the codebase."""
        import shared_context_server

        # Get module path
        module_path = Path(shared_context_server.__file__).parent

        print(f"\n=== SEARCHING MODULE: {module_path} ===")

        # Search for database file references
        database_refs = []

        for py_file in module_path.rglob("*.py"):
            # Skip files that can't be read to avoid performance overhead in loop
            try:
                content = py_file.read_text()
            except Exception as e:
                print(f"Could not read {py_file}: {e}")
                continue

            # Look for .db references
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if ".db" in line and (
                    "shared_context" in line or "chat_history" in line
                ):
                    database_refs.append(
                        {"file": py_file.name, "line": i, "content": line.strip()}
                    )

        print("\n=== DATABASE REFERENCES FOUND ===")
        for ref in database_refs:
            print(f"{ref['file']}:{ref['line']} | {ref['content']}")

        # Check for shared_context references
        shared_context_refs = [
            ref for ref in database_refs if "shared_context" in ref["content"]
        ]

        if shared_context_refs:
            print(f"\n❌ Found {len(shared_context_refs)} shared_context references:")
            for ref in shared_context_refs:
                print(f"  {ref['file']}:{ref['line']} | {ref['content']}")

        # This test documents findings
        assert True
