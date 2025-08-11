#!/usr/bin/env python3
"""
Coverage tracking script that shows current vs target coverage for each module.
Provides real-time progress toward the 85% target as we add tests.
"""

import json
import subprocess
import sys
from pathlib import Path

# Target coverage for key modules
TARGET_COVERAGE = {
    "src/shared_context_server/utils/performance.py": 85,
    "src/shared_context_server/utils/caching.py": 85,
    "src/shared_context_server/models.py": 85,
    "src/shared_context_server/config.py": 85,
    "src/shared_context_server/database.py": 85,
    "src/shared_context_server/server.py": 85,
    "src/shared_context_server/auth.py": 85,
    "src/shared_context_server/scripts/cli.py": 85,
    "src/shared_context_server/tools.py": 85,
    "src/shared_context_server/scripts/dev.py": 85,
}


# ANSI color codes
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def run_coverage() -> dict[str, float]:
    """Run coverage and return module coverage percentages."""
    try:
        # Run coverage with JSON output
        subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                "--cov=src",
                "--cov-report=json",
                "--cov-report=term-missing",
                "-q",
                "-n",
                "0",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Read the JSON coverage report
        coverage_file = Path("coverage.json")
        if not coverage_file.exists():
            print(f"{Colors.RED}Error: coverage.json not found{Colors.END}")
            return {}

        with open(coverage_file) as f:
            coverage_data = json.load(f)

        # Extract file coverage percentages
        file_coverage = {}
        for file_path, file_data in coverage_data["files"].items():
            if file_data["summary"]["num_statements"] > 0:
                coverage_percent = file_data["summary"]["percent_covered"]
                file_coverage[file_path] = coverage_percent

    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}Error running coverage: {e}{Colors.END}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return {}
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return {}
    else:
        return file_coverage


def format_coverage_status(current: float, target: float) -> str:
    """Format coverage status with colors."""
    if current >= target:
        return f"{Colors.GREEN}✓ {current:.1f}%{Colors.END}"
    if current >= target - 10:
        return f"{Colors.YELLOW}⚠ {current:.1f}%{Colors.END}"
    return f"{Colors.RED}✗ {current:.1f}%{Colors.END}"


def calculate_progress(current: float, target: float) -> str:
    """Calculate and format progress bar."""
    progress = min(current / target, 1.0) if target > 0 else 0
    bar_length = 20
    filled = int(progress * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)

    if progress >= 1.0:
        color = Colors.GREEN
    elif progress >= 0.8:
        color = Colors.YELLOW
    else:
        color = Colors.RED

    return f"{color}{bar}{Colors.END} {progress:.1%}"


def show_coverage_dashboard(file_coverage: dict[str, float]) -> None:
    """Display coverage dashboard with current vs target coverage."""
    print(
        f"\n{Colors.BOLD}📊 Coverage Dashboard - Phase 4 Test Coverage Completion{Colors.END}"
    )
    print("=" * 80)

    # Overall statistics
    total_files = len(TARGET_COVERAGE)
    files_at_target = sum(
        1
        for file_path in TARGET_COVERAGE
        if file_coverage.get(file_path, 0) >= TARGET_COVERAGE[file_path]
    )

    print(f"\n{Colors.BOLD}Overall Progress:{Colors.END}")
    print(f"Files at target coverage: {files_at_target}/{total_files}")
    print(f"Progress: {calculate_progress(files_at_target, total_files)}")

    # Module-specific coverage
    print(f"\n{Colors.BOLD}Module Coverage Status:{Colors.END}")
    print(f"{'Module':<50} {'Current':<12} {'Target':<8} {'Progress':<25} {'Gap':<8}")
    print("-" * 110)

    for file_path, target in TARGET_COVERAGE.items():
        current = file_coverage.get(file_path, 0)
        module_name = file_path.replace("src/shared_context_server/", "").replace(
            ".py", ""
        )

        status = format_coverage_status(current, target)
        progress = calculate_progress(current, target)
        gap = max(0, target - current)

        print(
            f"{module_name:<50} {status:<20} {target}%      {progress:<33} {gap:+.1f}%"
        )

    # Priority recommendations
    print(f"\n{Colors.BOLD}🎯 Priority Modules (Biggest Gaps):{Colors.END}")
    gaps = [
        (file_path, max(0, target - file_coverage.get(file_path, 0)), target)
        for file_path, target in TARGET_COVERAGE.items()
    ]
    gaps.sort(key=lambda x: x[1], reverse=True)

    for i, (file_path, gap, target) in enumerate(gaps[:5]):
        if gap > 0:
            module_name = file_path.replace("src/shared_context_server/", "").replace(
                ".py", ""
            )
            current = file_coverage.get(file_path, 0)
            print(
                f"{i + 1}. {module_name}: {current:.1f}% → {target}% (gap: {gap:.1f}%)"
            )

    # Test commands for priority modules
    print(f"\n{Colors.BOLD}🧪 Module-Specific Test Commands:{Colors.END}")
    priority_modules = [
        ("utils/performance.py", "test_performance_comprehensive.py"),
        ("utils/caching.py", "test_caching_comprehensive.py"),
        ("models.py", "test_models_comprehensive.py"),
        ("config.py", "test_config_comprehensive.py"),
    ]

    for module_path, test_file in priority_modules:
        full_path = f"src/shared_context_server/{module_path}"
        if full_path in TARGET_COVERAGE:
            current = file_coverage.get(full_path, 0)
            target = TARGET_COVERAGE[full_path]
            if current < target:
                print(
                    f"pytest tests/unit/{test_file} --cov={full_path} --cov-report=term-missing"
                )


def show_module_coverage(module_path: str, file_coverage: dict[str, float]) -> None:
    """Show detailed coverage for a specific module."""
    if module_path not in file_coverage:
        print(f"{Colors.RED}Module not found: {module_path}{Colors.END}")
        return

    current = file_coverage[module_path]
    target = TARGET_COVERAGE.get(module_path, 85)

    print(f"\n{Colors.BOLD}📋 Module Coverage Details: {module_path}{Colors.END}")
    print("=" * 60)
    print(f"Current Coverage: {format_coverage_status(current, target)}")
    print(f"Target Coverage:  {target}%")
    print(f"Gap:             {max(0, target - current):.1f}%")
    print(f"Progress:        {calculate_progress(current, target)}")

    # Run detailed coverage for this module
    module_path.replace("src/shared_context_server/", "").replace(".py", "")
    test_command = f"pytest --cov={module_path} --cov-report=term-missing -v"
    print(f"\n{Colors.BOLD}Detailed Test Command:{Colors.END}")
    print(f"{test_command}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Show specific module coverage
        module_path = sys.argv[1]
        if not module_path.startswith("src/"):
            module_path = f"src/shared_context_server/{module_path}"
        if not module_path.endswith(".py"):
            module_path += ".py"

        file_coverage = run_coverage()
        show_module_coverage(module_path, file_coverage)
    else:
        # Show full dashboard
        file_coverage = run_coverage()
        if file_coverage:
            show_coverage_dashboard(file_coverage)
        else:
            print(f"{Colors.RED}Failed to get coverage data{Colors.END}")
            sys.exit(1)


if __name__ == "__main__":
    main()
