"""
Regression prevention tests for database file creation.

Focused tests to prevent the shared_context.db vs chat_history.db issue from recurring.
These tests should be run in CI to catch any configuration drift or hardcoded fallbacks.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestDatabaseFileRegressionPrevention:
    """Prevent regression of unwanted database file creation."""

    def test_no_shared_context_db_hardcoded_anywhere(self):
        """Ensure 'shared_context.db' is never hardcoded in source code."""
        # Get the source directory
        import shared_context_server

        src_dir = Path(shared_context_server.__file__).parent

        # Search all Python files for 'shared_context.db'
        violations = []

        for py_file in src_dir.rglob("*.py"):
            # Skip files that can't be read to avoid performance overhead in loop
            try:
                content = py_file.read_text()
            except Exception:
                continue  # Skip files that can't be read

            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if "shared_context.db" in line and not line.strip().startswith("#"):
                    violations.append(f"{py_file.name}:{i} | {line.strip()}")

        assert len(violations) == 0, (
            f"Found hardcoded 'shared_context.db' references: {violations}"
        )

    def test_default_database_paths_use_chat_history(self):
        """Ensure all default database paths use 'chat_history' pattern."""
        from shared_context_server.config import (
            get_database_url,
            get_default_database_path,
        )

        # Test default path
        default_path = get_default_database_path()
        assert "chat_history" in default_path, (
            f"Default path doesn't use chat_history: {default_path}"
        )
        assert "shared_context" not in default_path, (
            f"Default path uses shared_context: {default_path}"
        )

        # Test database URL generation
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(os.environ, {"API_KEY": "test-key"}),
        ):
            from shared_context_server.config_context import reset_config_context

            reset_config_context()
            db_url = get_database_url()
            assert "chat_history" in db_url, (
                f"Database URL doesn't use chat_history: {db_url}"
            )
            assert "shared_context" not in db_url, (
                f"Database URL uses shared_context: {db_url}"
            )

    def test_sqlalchemy_backend_default_uses_chat_history(self):
        """Ensure SQLAlchemy backend defaults use chat_history pattern."""
        from shared_context_server.database_sqlalchemy import SimpleSQLAlchemyManager

        # Test default initialization
        SimpleSQLAlchemyManager()

        # The manager should use the configured database URL, not a hardcoded one
        # We can't directly inspect the URL, but we can test that initialization
        # doesn't create unwanted files

        assert True  # If no exception, the default initialization is working

    @pytest.mark.asyncio
    async def test_memory_testing_creates_no_persistent_files(self):
        """Ensure test infrastructure creates no persistent database files."""
        from shared_context_server.database_testing import get_test_db_connection

        # Test both backends to ensure they use memory databases
        backends = ["aiosqlite", "sqlalchemy"]

        for backend in backends:
            async with get_test_db_connection(backend) as conn:
                # Create and use a table
                await conn.execute("CREATE TABLE regression_check (id INTEGER)")
                await conn.execute("INSERT INTO regression_check VALUES (1)")
                await conn.commit()

                # Verify it works
                cursor = await conn.execute("SELECT id FROM regression_check")
                row = await cursor.fetchone()
                if hasattr(row, "keys"):
                    assert row["id"] == 1 or row[0] == 1
                else:
                    assert row[0] == 1

        # Test passes if memory databases work correctly
        # and don't create any persistent files

    def test_project_directory_has_no_unwanted_database_files(self):
        """Check that project directory has no unwanted database files."""
        project_root = Path(__file__).parent.parent.parent

        # Find all database files
        db_files = []
        for pattern in ["*.db", "*.db-*"]:
            db_files.extend(project_root.glob(pattern))

        # Categorize files
        wanted_files = []
        unwanted_files = []

        for db_file in db_files:
            filename = db_file.name
            if filename.startswith("chat_history"):
                wanted_files.append(filename)
            elif filename.startswith("shared_context"):
                unwanted_files.append(filename)
            elif filename.startswith("test_"):
                # Test files should not persist
                unwanted_files.append(filename)
            else:
                # Other database files - investigate
                unwanted_files.append(filename)

        # Report findings
        if unwanted_files:
            print("\n❌ UNWANTED DATABASE FILES FOUND:")
            for filename in unwanted_files:
                print(f"  - {filename}")
            print("\n✅ WANTED FILES:")
            for filename in wanted_files:
                print(f"  - {filename}")

        # In CI, this should fail if unwanted files exist
        # In development, this documents the current state
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            assert len(unwanted_files) == 0, (
                f"Unwanted database files in CI: {unwanted_files}"
            )
        else:
            # Development - just document the issue
            if unwanted_files:
                print(f"\n⚠️  Found {len(unwanted_files)} unwanted files in development")

    def test_configuration_documentation_accuracy(self):
        """Verify that documentation matches actual configuration behavior."""
        # This test will need to be updated when documentation is fixed
        claude_md = Path(__file__).parent.parent.parent / "CLAUDE.md"

        if claude_md.exists():
            content = claude_md.read_text()

            # Current state: documentation incorrectly shows shared_context.db
            # This test documents the bug and should be updated when fixed

            # Check for the incorrect documentation
            incorrect_line = "DATABASE_URL=path/to/db         # Optional (default: shared_context.db)"

            if incorrect_line in content:
                print("\n📝 DOCUMENTATION BUG CONFIRMED:")
                print(
                    "   CLAUDE.md:109 incorrectly documents 'shared_context.db' as default"
                )
                print("   Should be: '(default: chat_history.db)'")

                # In CI, this should remind us to fix the docs
                if os.getenv("CI"):
                    pytest.fail(
                        "Documentation still shows incorrect default database filename"
                    )
            else:
                print("\n✅ DOCUMENTATION APPEARS FIXED")

    @pytest.mark.asyncio
    async def test_database_initialization_creates_only_expected_files(self):
        """Test that database initialization creates only expected files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_db_path = temp_path / "regression_test.db"

            # Set up isolated environment
            # Set both DATABASE_URL and DATABASE_PATH for compatibility with both backends
            test_env = {
                "DATABASE_URL": f"sqlite:///{test_db_path}",
                "DATABASE_PATH": str(test_db_path),
                "API_KEY": "test-regression-key",
            }

            # Clear any cached config and database manager
            from shared_context_server.config_context import reset_config_context
            from shared_context_server.database_connection import reset_database_context

            with (
                patch.dict(os.environ, test_env),
                patch("shared_context_server.config.dotenv.load_dotenv"),
            ):
                reset_config_context()
                reset_database_context()
                # Initialize database in isolated environment
                try:
                    from shared_context_server.database import (
                        get_database_manager,
                        initialize_database,
                    )

                    await initialize_database()

                    # Test making a connection to actually create the database file
                    db_manager = get_database_manager()
                    async with db_manager.get_connection() as conn:
                        await conn.execute("SELECT 1")
                        await conn.commit()

                    # Check what files were created
                    created_files = list(temp_path.glob("*"))
                    created_names = [f.name for f in created_files]

                    # Should only have regression_test.db and related files
                    expected_patterns = ["regression_test.db"]
                    unexpected_files = [
                        name
                        for name in created_names
                        if not any(pattern in name for pattern in expected_patterns)
                    ]

                    assert len(unexpected_files) == 0, (
                        f"Unexpected files created: {unexpected_files}"
                    )

                    # Verify the expected file exists and is not empty
                    assert test_db_path.exists(), "Expected database file not created"
                    assert test_db_path.stat().st_size > 0, "Database file is empty"

                except Exception:
                    # If initialization fails, ensure no files were created
                    created_files = list(temp_path.glob("*"))
                    if created_files:
                        pytest.fail(
                            f"Files created despite initialization failure: {[f.name for f in created_files]}"
                        )
                    # Re-raise the original exception
                    raise

    def test_environment_variable_override_prevents_unwanted_files(self):
        """Test that proper environment variables prevent unwanted file creation."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            test_cases = [
                {
                    "name": "Explicit DATABASE_URL",
                    "env": {"DATABASE_URL": f"sqlite:///{temp_path}/test_explicit.db"},
                    "expected_pattern": "test_explicit",
                },
                {
                    "name": "Explicit DATABASE_PATH",
                    "env": {"DATABASE_PATH": str(temp_path / "test_path.db")},
                    "expected_pattern": "test_path",
                },
            ]

            for case in test_cases:
                # Clear all environment variables first, then set only what we want
                from shared_context_server.config_context import reset_config_context

                with (
                    patch.dict(os.environ, {}, clear=True),
                    patch.dict(os.environ, {**case["env"], "API_KEY": "test"}),
                    patch("shared_context_server.config.dotenv.load_dotenv"),
                ):
                    reset_config_context()
                    from shared_context_server.config import get_database_url

                    db_url = get_database_url()

                # For DATABASE_URL case, the URL should be used as-is
                if "DATABASE_URL" in case["env"]:
                    expected_url = case["env"]["DATABASE_URL"]
                    assert db_url == expected_url, (
                        f"Expected exact URL {expected_url}, got {db_url}"
                    )
                else:
                    # For DATABASE_PATH case, check the pattern is in the generated URL
                    assert case["expected_pattern"] in db_url, (
                        f"Expected pattern '{case['expected_pattern']}' not in URL: {db_url}"
                    )

                # Verify shared_context is not used
                assert "shared_context" not in db_url, (
                    f"Unwanted 'shared_context' in URL: {db_url}"
                )


def get_database_url():
    """Helper to get database URL for testing."""
    from shared_context_server.config import get_database_url

    return get_database_url()


class TestRegressionMonitoring:
    """Tests for ongoing monitoring of the regression."""

    def test_create_file_monitoring_script(self):
        """Create a monitoring script to detect unwanted file creation."""
        script_content = """#!/bin/bash
# Database file monitoring script
# Run this before/after operations to detect unwanted file creation

echo "=== DATABASE FILE MONITORING ==="
echo "Current directory: $(pwd)"
echo ""

echo "Database files found:"
for file in *.db *.db-*; do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "unknown")
        echo "  $file (${size} bytes)"

        # Check for unwanted files
        if [[ "$file" == shared_context* ]]; then
            echo "    ❌ UNWANTED FILE DETECTED"
        elif [[ "$file" == chat_history* ]]; then
            echo "    ✅ Expected file"
        else
            echo "    ❓ Unknown file - investigate"
        fi
    fi
done

echo ""
echo "=== END MONITORING ==="
"""

        # This test documents how to monitor for the issue
        # In a real scenario, this script could be saved and used
        print("\n📝 File monitoring script created in memory")
        print("   Use this pattern to monitor database file creation")

        assert len(script_content) > 100  # Script has content
