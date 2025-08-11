#!/usr/bin/env python3
"""
Module-specific coverage commands for tracking progress on individual modules.
Provides targeted coverage analysis for specific modules and test files.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Module to test file mapping
MODULE_TEST_MAPPING = {
    "utils/performance.py": "tests/unit/test_performance_comprehensive.py",
    "utils/caching.py": "tests/unit/test_caching_comprehensive.py",
    "models.py": "tests/unit/test_models_comprehensive.py",
    "config.py": "tests/unit/test_config_comprehensive.py",
    "database.py": "tests/unit/test_database.py",
    "server.py": "tests/unit/test_server.py",
    "auth.py": "tests/unit/test_auth.py",
    "scripts/cli.py": "tests/unit/test_cli.py",
    "tools.py": "tests/unit/test_tools.py",
    "scripts/dev.py": "tests/unit/test_dev.py",
}


# ANSI color codes
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def run_module_coverage(
    module_path: str,
    test_file: Optional[str] = None,
    verbose: bool = False,
    html: bool = False,
) -> bool:
    """Run coverage for a specific module."""

    # Normalize module path
    if not module_path.startswith("src/"):
        module_path = f"src/shared_context_server/{module_path}"
    if not module_path.endswith(".py"):
        module_path += ".py"

    # Check if module exists
    if not Path(module_path).exists():
        print(f"{Colors.RED}Error: Module not found: {module_path}{Colors.END}")
        return False

    # Determine test file
    if not test_file:
        module_key = module_path.replace("src/shared_context_server/", "")
        test_file = MODULE_TEST_MAPPING.get(module_key)

        if not test_file:
            print(
                f"{Colors.YELLOW}Warning: No specific test file mapped for {module_key}{Colors.END}"
            )
            print(f"Running all tests with coverage for {module_path}")
            test_file = "tests/"

    # Build coverage command
    cmd = ["uv", "run", "pytest"]

    if test_file != "tests/":
        cmd.append(test_file)
    else:
        cmd.append("tests/")

    # Convert file path to module path for coverage
    cov_module = module_path.replace("src/", "").replace("/", ".").replace(".py", "")

    cmd.extend(
        [
            f"--cov={cov_module}",
            "--cov-report=term-missing",
            "-n",
            "0",  # Disable parallel execution for coverage
        ]
    )

    if html:
        cmd.append("--cov-report=html")

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    print(f"{Colors.BOLD}Running coverage for module: {module_path}{Colors.END}")
    print(f"Test file: {test_file}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(
            f"\n{Colors.RED}✗ Coverage analysis failed with exit code {e.returncode}{Colors.END}"
        )
        return False
    else:
        print(f"\n{Colors.GREEN}✓ Coverage analysis completed successfully{Colors.END}")

        if html:
            print(f"{Colors.BLUE}HTML report generated in htmlcov/{Colors.END}")

        return True


def list_modules():
    """List available modules and their test files."""
    print(f"{Colors.BOLD}📋 Available Modules for Coverage Analysis:{Colors.END}")
    print("=" * 70)
    print(f"{'Module':<30} {'Test File':<40}")
    print("-" * 70)

    for module, test_file in MODULE_TEST_MAPPING.items():
        module_path = f"src/shared_context_server/{module}"
        exists = "✓" if Path(module_path).exists() else "✗"
        test_exists = "✓" if Path(test_file).exists() else "✗"

        print(f"{module:<30} {test_file:<40} {exists}/{test_exists}")

    print(f"\n{Colors.BLUE}Legend: Module/Test (✓ = exists, ✗ = missing){Colors.END}")


def run_priority_modules(html: bool = False):
    """Run coverage for priority modules that need improvement."""
    priority_modules = [
        "utils/performance.py",
        "utils/caching.py",
        "models.py",
        "config.py",
    ]

    print(f"{Colors.BOLD}🎯 Running Coverage for Priority Modules{Colors.END}")
    print("=" * 60)

    results = {}
    for module in priority_modules:
        print(f"\n{Colors.BLUE}Analyzing {module}...{Colors.END}")
        success = run_module_coverage(module, verbose=False, html=html)
        results[module] = success

        if not success:
            print(f"{Colors.RED}Failed to analyze {module}{Colors.END}")

    # Summary
    print(f"\n{Colors.BOLD}📊 Priority Module Coverage Summary:{Colors.END}")
    print("-" * 40)
    for module, success in results.items():
        status = (
            f"{Colors.GREEN}✓{Colors.END}" if success else f"{Colors.RED}✗{Colors.END}"
        )
        print(f"{status} {module}")


def create_test_file_template(module_path: str):
    """Create a test file template for a module."""
    if not module_path.startswith("src/"):
        module_path = f"src/shared_context_server/{module_path}"
    if not module_path.endswith(".py"):
        module_path += ".py"

    module_key = module_path.replace("src/shared_context_server/", "")
    test_file = MODULE_TEST_MAPPING.get(module_key)

    if not test_file:
        print(f"{Colors.RED}No test file mapping found for {module_key}{Colors.END}")
        return

    if Path(test_file).exists():
        print(f"{Colors.YELLOW}Test file already exists: {test_file}{Colors.END}")
        return

    # Create test file directory if needed
    test_dir = Path(test_file).parent
    test_dir.mkdir(parents=True, exist_ok=True)

    # Generate test template
    module_name = module_key.replace("/", "_").replace(".py", "")
    import_path = module_key.replace("/", ".").replace(".py", "")

    template = f'''"""
Comprehensive test suite for {module_key}.
This file provides extensive test coverage to meet the 85% threshold.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

# Import the module under test
from shared_context_server.{import_path} import *


class Test{module_name.title().replace("_", "")}:
    """Comprehensive test suite for {module_key}."""

    def test_placeholder(self):
        """Placeholder test - replace with actual tests."""
        # TODO: Implement comprehensive tests for {module_key}
        # Target: 85% coverage
        assert True

    # TODO: Add more test methods to achieve 85% coverage
    # Focus on:
    # - Edge cases and boundary conditions
    # - Error handling scenarios
    # - All code paths and branches
    # - Integration points
'''

    with open(test_file, "w") as f:
        f.write(template)

    print(f"{Colors.GREEN}✓ Created test file template: {test_file}{Colors.END}")
    print(f"Edit the file to add comprehensive tests for {module_key}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Module-specific coverage analysis for Phase 4 completion"
    )
    parser.add_argument(
        "module",
        nargs="?",
        help="Module to analyze (e.g., 'utils/performance.py' or 'models')",
    )
    parser.add_argument(
        "--test-file", help="Specific test file to run (overrides default mapping)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--html", action="store_true", help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List available modules"
    )
    parser.add_argument(
        "--priority",
        "-p",
        action="store_true",
        help="Run coverage for priority modules",
    )
    parser.add_argument(
        "--create-template",
        "-t",
        action="store_true",
        help="Create test file template for module",
    )

    args = parser.parse_args()

    if args.list:
        list_modules()
    elif args.priority:
        run_priority_modules(html=args.html)
    elif args.create_template and args.module:
        create_test_file_template(args.module)
    elif args.module:
        success = run_module_coverage(
            args.module, test_file=args.test_file, verbose=args.verbose, html=args.html
        )
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
