#!/usr/bin/env python3
"""
Pre-commit hook to validate singleton testing patterns.

This script checks that authentication tests follow proper singleton
isolation patterns to prevent test pollution and race conditions.
"""

import ast
import sys
from pathlib import Path


class SingletonPatternValidator(ast.NodeVisitor):
    """AST visitor to check for singleton pattern violations."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues: list[tuple[int, str]] = []
        self.has_auth_imports = False
        self.has_singleton_reset = False
        self.auth_test_functions = []

    def visit_Import(self, node: ast.Import):
        """Check for authentication-related imports."""
        for name in node.names:
            if any(
                auth_term in name.name
                for auth_term in ["auth", "jwt", "token", "secure"]
            ):
                self.has_auth_imports = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check for authentication-related imports from modules."""
        if node.module and any(
            auth_term in node.module for auth_term in ["auth", "jwt", "token", "secure"]
        ):
            self.has_auth_imports = True

        # Check for singleton reset imports
        if node.module == "shared_context_server.auth_secure" and any(
            name.name == "reset_secure_token_manager" for name in node.names
        ):
            self.has_singleton_reset = True

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check authentication test functions for singleton patterns."""
        # Check if this is a test function
        if node.name.startswith("test_") and any(
            auth_term in node.name.lower()
            for auth_term in [
                "auth",
                "jwt",
                "token",
                "login",
                "permission",
                "secure",
            ]
        ):
            self.auth_test_functions.append((node.lineno, node.name))

            # Check if the function body contains singleton reset
            has_reset_call = self._check_for_reset_call(node)
            if not has_reset_call:
                self.issues.append(
                    (
                        node.lineno,
                        f"Authentication test '{node.name}' missing singleton reset call",
                    )
                )

        self.generic_visit(node)

    def _check_for_reset_call(self, func_node: ast.FunctionDef) -> bool:
        """Check if function contains reset_secure_token_manager call."""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call) and (
                (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "reset_secure_token_manager"
                )
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "reset_secure_token_manager"
                )
            ):
                return True
        return False


def validate_file(file_path: Path) -> list[tuple[int, str]]:
    """Validate singleton patterns in a single file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))

        validator = SingletonPatternValidator(str(file_path))
        validator.visit(tree)

        # Only check files that import auth-related modules
        if (
            validator.has_auth_imports
            and validator.auth_test_functions
            and not validator.has_singleton_reset
        ):
            validator.issues.append(
                (
                    1,
                    "File contains authentication tests but missing singleton reset import",
                )
            )

        return validator.issues

    except SyntaxError as e:
        return [(e.lineno or 1, f"Syntax error: {e}")]
    except Exception as e:
        return [(1, f"Error parsing file: {e}")]


def main() -> int:
    """Main validation function."""
    if len(sys.argv) < 2:
        print("Usage: validate_singleton_patterns.py <file1> [file2] ...")
        return 1

    total_issues = 0

    for file_path in sys.argv[1:]:
        path = Path(file_path)

        # Only check Python test files
        if not (path.suffix == ".py" and "test" in path.name):
            continue

        issues = validate_file(path)

        if issues:
            print(f"\n❌ {file_path}:")
            for line_no, message in issues:
                print(f"  Line {line_no}: {message}")
            total_issues += len(issues)

    if total_issues > 0:
        print(f"\n🚨 Found {total_issues} singleton pattern issue(s)")
        print("\n💡 Fix suggestions:")
        print("1. Add singleton reset import:")
        print(
            "   from shared_context_server.auth_secure import reset_secure_token_manager"
        )
        print("2. Call reset in authentication test setup:")
        print("   reset_secure_token_manager()  # Add at start of test")
        print("3. See CLAUDE.md 'Singleton Testing Patterns' for examples")
        return 1
    print("✅ All singleton patterns validated successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
