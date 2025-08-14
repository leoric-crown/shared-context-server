#!/usr/bin/env python3
"""
Migration script to move from complex file-based testing to simplified memory-based testing.

This script helps teams migrate from the old complex database testing approach
to the new simplified memory-based approach following KISS/YAGNI principles.
"""

import re
import shutil
from pathlib import Path


def find_test_files(test_dir: Path) -> list[Path]:
    """Find all Python test files in the test directory."""
    return list(test_dir.rglob("test_*.py")) + list(test_dir.rglob("*_test.py"))


def backup_file(file_path: Path) -> Path:
    """Create a backup of the file before modification."""
    backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
    shutil.copy2(file_path, backup_path)
    return backup_path


def migrate_tempfile_usage(content: str) -> tuple[str, list[str]]:
    """
    Replace tempfile usage with memory database patterns.

    Returns:
        tuple of (modified_content, list_of_changes)
    """
    changes = []

    # Pattern 1: tempfile.NamedTemporaryFile usage
    old_pattern = r"with tempfile\.NamedTemporaryFile\([^)]*\) as temp_db:\s*\n\s*temp_db_path = temp_db\.name"
    new_replacement = '# Using memory database (no file needed)\n    memory_db_url = "sqlite:///:memory:"'

    if re.search(old_pattern, content):
        content = re.sub(old_pattern, new_replacement, content)
        changes.append("Replaced tempfile.NamedTemporaryFile with memory database")

    # Pattern 2: DatabaseManager with file path
    old_pattern = r'DatabaseManager\(f?["\']sqlite:///\{[^}]*\}["\']?\)'
    new_replacement = 'TestDatabaseManager("sqlite:///:memory:")'

    if re.search(old_pattern, content):
        content = re.sub(old_pattern, new_replacement, content)
        changes.append("Replaced DatabaseManager with TestDatabaseManager")

    # Pattern 3: File cleanup in finally blocks
    cleanup_pattern = r"finally:\s*\n.*?(?:unlink|remove).*?\n"
    if re.search(cleanup_pattern, content, re.MULTILINE | re.DOTALL):
        content = re.sub(
            cleanup_pattern,
            "finally:\n    # No cleanup needed for memory database\n    pass\n",
            content,
        )
        changes.append("Removed file cleanup code")

    return content, changes


def migrate_ci_environment_checks(content: str) -> tuple[str, list[str]]:
    """
    Replace CI environment checks with testing environment checks.

    Returns:
        tuple of (modified_content, list_of_changes)
    """
    changes = []

    # Replace _is_ci_environment with _is_testing_environment
    if "_is_ci_environment" in content:
        content = content.replace("_is_ci_environment", "_is_testing_environment")
        changes.append(
            "Updated CI environment detection to testing environment detection"
        )

    # Replace CI-specific logic
    ci_pattern = r"if.*CI.*or.*GITHUB_ACTIONS"
    testing_replacement = (
        'if "pytest" in sys.modules or os.getenv("CI") or os.getenv("GITHUB_ACTIONS")'
    )

    if re.search(ci_pattern, content):
        content = re.sub(ci_pattern, testing_replacement, content)
        changes.append("Updated CI detection logic")

    return content, changes


def add_imports(content: str) -> tuple[str, list[str]]:
    """
    Add necessary imports for the new testing infrastructure.

    Returns:
        tuple of (modified_content, list_of_changes)
    """
    changes = []

    # Check if we need to add the testing import
    if (
        "TestDatabaseManager" in content
        and "from shared_context_server.database_testing import" not in content
    ):
        # Find the import section
        import_pattern = r"(from shared_context_server\.[a-zA-Z_]+ import[^\n]*\n)"
        if re.search(import_pattern, content):
            # Add after existing shared_context_server imports
            new_import = "from shared_context_server.database_testing import TestDatabaseManager, get_test_db_connection\n"
            content = re.sub(import_pattern, r"\1" + new_import, content, count=1)
            changes.append("Added database_testing imports")
        else:
            # Add at the beginning of imports
            content = (
                "from shared_context_server.database_testing import TestDatabaseManager, get_test_db_connection\n"
                + content
            )
            changes.append("Added database_testing imports at top")

    return content, changes


def migrate_backend_switching_tests(content: str) -> tuple[str, list[str]]:
    """
    Simplify backend switching tests using the new unified approach.

    Returns:
        tuple of (modified_content, list_of_changes)
    """
    changes = []

    # Replace complex backend switching with unified approach
    if "isolated_database_backend" in content:
        # Replace with get_test_db_connection usage
        old_pattern = r"with isolated_database_backend\([^)]*\):"
        new_replacement = "async with get_test_db_connection(backend) as conn:"

        content = re.sub(old_pattern, new_replacement, content)
        changes.append("Simplified backend switching using unified approach")

    # Replace patch_database_connection calls
    if "patch_database_connection" in content:
        old_pattern = r"patch_database_connection\(test_db_manager\)"
        new_replacement = 'patch_database_connection(backend="aiosqlite")'

        content = re.sub(old_pattern, new_replacement, content)
        changes.append("Updated database connection patching")

    return content, changes


def migrate_file(file_path: Path) -> tuple[bool, list[str]]:
    """
    Migrate a single test file to use memory-based testing.

    Returns:
        tuple of (was_modified, list_of_changes)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        content = original_content
        all_changes = []

        # Apply all migrations
        content, changes = migrate_tempfile_usage(content)
        all_changes.extend(changes)

        content, changes = migrate_ci_environment_checks(content)
        all_changes.extend(changes)

        content, changes = add_imports(content)
        all_changes.extend(changes)

        content, changes = migrate_backend_switching_tests(content)
        all_changes.extend(changes)

        # Only write if changes were made
        if content != original_content:
            # Create backup
            backup_path = backup_file(file_path)
            print(f"Created backup: {backup_path}")

            # Write modified content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return True, all_changes

        return False, []

    except Exception as e:
        print(f"Error migrating {file_path}: {e}")
        return False, [f"Error: {e}"]


def main():
    """Main migration function."""
    print("🔄 Migrating to simplified memory-based database testing...")

    # Find project root
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    test_dir = project_root / "tests"

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return

    # Find all test files
    test_files = find_test_files(test_dir)
    print(f"📁 Found {len(test_files)} test files")

    modified_files = 0
    total_changes = 0

    for test_file in test_files:
        print(f"\n📝 Processing: {test_file.relative_to(project_root)}")

        was_modified, changes = migrate_file(test_file)

        if was_modified:
            modified_files += 1
            total_changes += len(changes)
            print(f"   ✅ Modified ({len(changes)} changes)")
            for change in changes:
                print(f"      - {change}")
        else:
            print("   ⚪ No changes needed")

    print("\n🎉 Migration complete!")
    print(f"   📊 Modified {modified_files}/{len(test_files)} files")
    print(f"   🔧 Made {total_changes} total changes")

    if modified_files > 0:
        print("\n💡 Next steps:")
        print("   1. Review the changes in modified files")
        print("   2. Run tests to ensure everything works: pytest tests/")
        print("   3. Update any remaining manual file-based tests")
        print("   4. Remove backup files once satisfied: rm tests/**/*.backup")


if __name__ == "__main__":
    main()
