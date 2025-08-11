#!/usr/bin/env python3
"""
Real-time coverage dashboard that shows progress toward the 85% target.
Provides comprehensive coverage analysis and actionable recommendations.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


# ANSI color codes and formatting
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


class Symbols:
    CHECK = "✓"
    CROSS = "✗"
    WARNING = "⚠"
    TARGET = "🎯"
    PROGRESS = "📊"
    ROCKET = "🚀"
    FIRE = "🔥"
    CLOCK = "⏰"


class CoverageDashboard:
    """Real-time coverage dashboard for Phase 4 completion."""

    TARGET_OVERALL = 85
    TARGET_MODULES = {
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

    def __init__(self):
        self.coverage_data = {}
        self.last_update = None

    def run_coverage_analysis(self) -> bool:
        """Run comprehensive coverage analysis."""
        try:
            print(
                f"{Colors.BLUE}{Symbols.CLOCK} Running coverage analysis...{Colors.END}"
            )

            # Run coverage with JSON and HTML output
            subprocess.run(
                [
                    "uv",
                    "run",
                    "pytest",
                    "--cov=src",
                    "--cov-report=json",
                    "--cov-report=html",
                    "--cov-report=term-missing",
                    "-q",
                    "-n",
                    "0",  # Disable parallel execution for coverage
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            # Load coverage data
            coverage_file = Path("coverage.json")
            if not coverage_file.exists():
                print(f"{Colors.RED}Error: coverage.json not found{Colors.END}")
                return False

            with open(coverage_file) as f:
                self.coverage_data = json.load(f)
            self.last_update = datetime.now()

        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}Coverage analysis failed: {e}{Colors.END}")
            if e.stderr:
                print(f"Error output: {e.stderr}")
            return False
        else:
            return True

    def get_file_coverage(self) -> dict[str, float]:
        """Extract file coverage percentages."""
        if not self.coverage_data:
            return {}

        file_coverage = {}
        for file_path, file_data in self.coverage_data["files"].items():
            if file_data["summary"]["num_statements"] > 0:
                coverage_percent = file_data["summary"]["percent_covered"]
                file_coverage[file_path] = coverage_percent

        return file_coverage

    def get_overall_coverage(self) -> tuple[float, float]:
        """Get overall coverage percentage and branch coverage."""
        if not self.coverage_data:
            return 0.0, 0.0

        summary = self.coverage_data["totals"]
        line_coverage = summary["percent_covered"]
        # Extract numeric branch coverage from display string
        branch_display = summary.get("percent_covered_display", "0%")
        if isinstance(branch_display, str) and branch_display.endswith("%"):
            try:
                branch_coverage = float(branch_display[:-1])
            except ValueError:
                branch_coverage = 0
        else:
            branch_coverage = float(branch_display) if branch_display else 0

        return line_coverage, branch_coverage

    def format_progress_bar(
        self, current: float, target: float, width: int = 20
    ) -> str:
        """Create a visual progress bar."""
        progress = min(current / target, 1.0) if target > 0 else 0
        filled = int(progress * width)
        empty = width - filled

        if progress >= 1.0:
            color = Colors.GREEN
            char = "█"
        elif progress >= 0.8:
            color = Colors.YELLOW
            char = "█"
        else:
            color = Colors.RED
            char = "█"

        bar = f"{color}{char * filled}{Colors.DIM}{'░' * empty}{Colors.END}"
        percentage = f"{progress:.1%}"

        return f"{bar} {percentage}"

    def format_coverage_status(self, current: float, target: float) -> str:
        """Format coverage status with appropriate colors and symbols."""
        if current >= target:
            return f"{Colors.GREEN}{Symbols.CHECK} {current:.1f}%{Colors.END}"
        if current >= target - 5:
            return f"{Colors.YELLOW}{Symbols.WARNING} {current:.1f}%{Colors.END}"
        return f"{Colors.RED}{Symbols.CROSS} {current:.1f}%{Colors.END}"

    def show_header(self):
        """Display dashboard header."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
        print(
            f"{Colors.BOLD}{Colors.BLUE}{Symbols.ROCKET} PHASE 4 TEST COVERAGE COMPLETION DASHBOARD {Symbols.ROCKET}{Colors.END}"
        )
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")

        if self.last_update:
            timestamp = self.last_update.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{Colors.DIM}Last updated: {timestamp}{Colors.END}")

    def show_overall_status(self):
        """Display overall coverage status."""
        line_coverage, branch_coverage = self.get_overall_coverage()

        print(f"\n{Colors.BOLD}{Symbols.PROGRESS} OVERALL COVERAGE STATUS{Colors.END}")
        print("-" * 50)

        # Line coverage
        line_status = self.format_coverage_status(line_coverage, self.TARGET_OVERALL)
        line_progress = self.format_progress_bar(line_coverage, self.TARGET_OVERALL)
        print(f"Line Coverage:   {line_status:<20} {line_progress}")

        # Branch coverage (if available)
        if branch_coverage > 0:
            branch_target = 80  # Branch coverage target is typically lower
            branch_status = self.format_coverage_status(branch_coverage, branch_target)
            branch_progress = self.format_progress_bar(branch_coverage, branch_target)
            print(f"Branch Coverage: {branch_status:<20} {branch_progress}")

        # Gap analysis
        gap = max(0, self.TARGET_OVERALL - line_coverage)
        if gap > 0:
            print(
                f"\n{Colors.RED}{Symbols.TARGET} Gap to target: {gap:.1f}% remaining{Colors.END}"
            )
        else:
            print(
                f"\n{Colors.GREEN}{Symbols.CHECK} Target achieved! {Symbols.FIRE}{Colors.END}"
            )

    def show_module_status(self):
        """Display module-specific coverage status."""
        file_coverage = self.get_file_coverage()

        print(f"\n{Colors.BOLD}{Symbols.TARGET} MODULE COVERAGE TARGETS{Colors.END}")
        print("-" * 100)
        print(
            f"{'Module':<45} {'Current':<15} {'Target':<10} {'Progress':<25} {'Gap':<10}"
        )
        print("-" * 100)

        modules_at_target = 0
        total_gap = 0

        for file_path, target in self.TARGET_MODULES.items():
            current = file_coverage.get(file_path, 0)
            module_name = file_path.replace("src/shared_context_server/", "")

            status = self.format_coverage_status(current, target)
            progress = self.format_progress_bar(current, target, 15)
            gap = max(0, target - current)

            if current >= target:
                modules_at_target += 1
            else:
                total_gap += gap

            gap_str = f"{gap:+.1f}%" if gap > 0 else f"{Colors.GREEN}✓{Colors.END}"

            print(
                f"{module_name:<45} {status:<25} {target}%       {progress:<35} {gap_str:<15}"
            )

        # Summary stats
        total_modules = len(self.TARGET_MODULES)
        completion_rate = modules_at_target / total_modules

        print(f"\n{Colors.BOLD}Module Summary:{Colors.END}")
        print(
            f"Modules at target: {modules_at_target}/{total_modules} ({completion_rate:.1%})"
        )
        print(f"Total coverage gap: {total_gap:.1f}%")

        if modules_at_target == total_modules:
            print(
                f"{Colors.GREEN}{Symbols.ROCKET} All modules at target! Phase 4 ready! {Symbols.ROCKET}{Colors.END}"
            )

    def show_priority_actions(self):
        """Show priority actions and recommendations."""
        file_coverage = self.get_file_coverage()

        # Find modules with biggest gaps
        gaps = []
        for file_path, target in self.TARGET_MODULES.items():
            current = file_coverage.get(file_path, 0)
            gap = max(0, target - current)
            if gap > 0:
                gaps.append((file_path, current, target, gap))

        gaps.sort(key=lambda x: x[3], reverse=True)  # Sort by gap size

        if not gaps:
            print(
                f"\n{Colors.GREEN}{Symbols.ROCKET} All targets achieved! Phase 4 complete! {Symbols.ROCKET}{Colors.END}"
            )
            return

        print(f"\n{Colors.BOLD}{Symbols.FIRE} PRIORITY ACTIONS{Colors.END}")
        print("-" * 60)

        for i, (file_path, current, target, gap) in enumerate(gaps[:5]):
            module_name = file_path.replace("src/shared_context_server/", "")
            print(f"{i + 1}. {Colors.YELLOW}{module_name}{Colors.END}")
            print(f"   Current: {current:.1f}% → Target: {target}% (Gap: {gap:.1f}%)")

            # Suggest test command
            test_file = self._get_test_file(module_name)
            if test_file:
                cmd = (
                    f"python scripts/module_coverage.py {module_name} --verbose --html"
                )
                print(f"   {Colors.BLUE}Command:{Colors.END} {cmd}")
            print()

    def _get_test_file(self, module_name: str) -> Optional[str]:
        """Get the test file for a module."""
        test_mapping = {
            "utils/performance.py": "tests/unit/test_performance_comprehensive.py",
            "utils/caching.py": "tests/unit/test_caching_comprehensive.py",
            "models.py": "tests/unit/test_models_comprehensive.py",
            "config.py": "tests/unit/test_config_comprehensive.py",
        }
        return test_mapping.get(module_name)

    def show_quick_commands(self):
        """Show quick commands for common tasks."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}⚡ QUICK COMMANDS{Colors.END}")
        print("-" * 40)
        print(
            f"{Colors.BLUE}Full dashboard:{Colors.END}        python scripts/coverage_dashboard.py"
        )
        print(
            f"{Colors.BLUE}Module analysis:{Colors.END}      python scripts/module_coverage.py <module>"
        )
        print(
            f"{Colors.BLUE}Priority modules:{Colors.END}     python scripts/module_coverage.py --priority"
        )
        print(
            f"{Colors.BLUE}Coverage tracker:{Colors.END}     python scripts/coverage_tracker.py"
        )
        print(f"{Colors.BLUE}HTML report:{Colors.END}          open htmlcov/index.html")
        print(
            f"{Colors.BLUE}Run all tests:{Colors.END}        uv run pytest --cov=src --cov-report=html"
        )

    def run_dashboard(self, watch: bool = False, interval: int = 30):
        """Run the complete dashboard."""
        while True:
            # Clear screen for watch mode
            if watch and self.last_update:
                print("\033[2J\033[H")  # Clear screen and move cursor to top

            # Run analysis
            if not self.run_coverage_analysis():
                print(f"{Colors.RED}Failed to run coverage analysis{Colors.END}")
                return False

            # Display dashboard
            self.show_header()
            self.show_overall_status()
            self.show_module_status()
            self.show_priority_actions()
            self.show_quick_commands()

            if not watch:
                break

            print(f"\n{Colors.DIM}Watching for changes... (Ctrl+C to exit){Colors.END}")
            print(f"{Colors.DIM}Next update in {interval} seconds{Colors.END}")

            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Dashboard stopped by user{Colors.END}")
                break

        return True


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 4 Coverage Dashboard")
    parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Watch mode - continuously update dashboard",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=30,
        help="Update interval in seconds for watch mode (default: 30)",
    )

    args = parser.parse_args()

    dashboard = CoverageDashboard()
    success = dashboard.run_dashboard(watch=args.watch, interval=args.interval)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
