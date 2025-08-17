#!/usr/bin/env python3
"""
Comprehensive Test Failure Analysis Script

Categorizes and analyzes the 92 test failures post-modularization.
"""

import re
import subprocess
from typing import Dict, List


def run_pytest_and_capture():
    """Run pytest and capture all failure information."""
    cmd = ["uv", "run", "pytest", "--tb=line", "-v", "--disable-warnings"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
    return result.stdout + result.stderr


def parse_failures(pytest_output: str) -> List[Dict]:
    """Parse pytest output to extract structured failure information."""
    failures = []

    # Remove ANSI color codes
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    clean_output = ansi_escape.sub("", pytest_output)

    lines = clean_output.split("\n")

    for line in lines:
        # Look for FAILED lines in output
        if "FAILED" in line and "::" in line:
            # Pattern: FAILED tests/path/file.py::TestClass::test_method - ErrorType: message
            parts = line.split(" - ", 1)
            if len(parts) == 2:
                test_path = parts[0].replace("FAILED ", "").strip()
                error_info = parts[1].strip()

                # Extract file and test name
                if "::" in test_path:
                    path_parts = test_path.split("::")
                    file_path = path_parts[0]
                    test_name = "::".join(path_parts[1:])
                else:
                    file_path = test_path
                    test_name = "unknown"

                failure = {
                    "file": file_path,
                    "test": test_name,
                    "error_summary": error_info,
                    "error_details": [],
                }
                failures.append(failure)

    return failures


def categorize_failures(failures: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize failures by type and priority."""
    categories = {
        "missing_exports": [],
        "missing_attributes": [],
        "functional_behavior": [],
        "performance_regression": [],
        "error_message_changes": [],
        "data_structure_issues": [],
        "unknown": [],
    }

    for failure in failures:
        error_text = failure["error_summary"].lower()

        # Missing imports/exports
        if "importerror" in error_text and "cannot import name" in error_text:
            categories["missing_exports"].append(failure)

        # Missing attributes
        elif (
            "attributeerror" in error_text
            and "does not have the attribute" in error_text
        ):
            categories["missing_attributes"].append(failure)

        # Performance issues
        elif "took" in error_text and ("ms" in error_text or "exceeds" in error_text):
            categories["performance_regression"].append(failure)

        # Data structure issues
        elif (
            "string indices must be integers" in error_text or "keyerror" in error_text
        ):
            categories["data_structure_issues"].append(failure)

        # Assertion errors - could be functional or message changes
        elif "assert" in error_text:
            # Check if it's about error messages
            if any(
                keyword in error_text
                for keyword in ["'token", "'performance", "'invalid", "message"]
            ):
                categories["error_message_changes"].append(failure)
            else:
                categories["functional_behavior"].append(failure)

        else:
            categories["unknown"].append(failure)

    return categories


def extract_missing_exports(missing_export_failures: List[Dict]) -> List[str]:
    """Extract list of missing exports that need to be added back to facade."""
    missing_exports = set()

    for failure in missing_export_failures:
        error_text = failure["error_summary"]
        # Extract the missing name from "cannot import name 'X' from"
        match = re.search(r"cannot import name '([^']+)'", error_text)
        if match:
            missing_exports.add(match.group(1))

    return sorted(list(missing_exports))


def analyze_performance_regressions(perf_failures: List[Dict]) -> List[Dict]:
    """Analyze performance regression failures to understand timing issues."""
    regressions = []

    for failure in perf_failures:
        error_text = failure["error_summary"]

        # Extract timing information
        time_match = re.search(r"(\d+\.?\d*)(ms|s)", error_text)
        target_match = re.search(
            r"target|expected|exceeds\s+(\d+\.?\d*)(ms|s)", error_text
        )

        regression = {
            "test": failure["test"],
            "file": failure["file"],
            "error": error_text,
            "actual_time": time_match.group(0) if time_match else "unknown",
            "target_time": target_match.group(0) if target_match else "unknown",
        }
        regressions.append(regression)

    return regressions


def generate_analysis_report(categories: Dict[str, List[Dict]]) -> str:
    """Generate comprehensive analysis report."""

    report = []
    report.append("# Critical Test Suite Analysis - Post-Modularization Assessment")
    report.append(
        f"**Total Failures: {sum(len(failures) for failures in categories.values())}**\n"
    )

    # Priority Summary
    report.append("## Executive Summary")
    critical_count = len(categories["missing_exports"]) + len(
        categories["missing_attributes"]
    )
    high_count = len(categories["performance_regression"]) + len(
        categories["functional_behavior"]
    )
    medium_count = len(categories["data_structure_issues"])
    low_count = len(categories["error_message_changes"])

    report.append(
        f"- **CRITICAL ({critical_count} failures)**: Missing exports/attributes - Break basic functionality"
    )
    report.append(
        f"- **HIGH ({high_count} failures)**: Performance regressions and functional behavior changes"
    )
    report.append(f"- **MEDIUM ({medium_count} failures)**: Data structure issues")
    report.append(f"- **LOW ({low_count} failures)**: Error message text changes")
    report.append("")

    # Detailed Analysis by Category
    for category, failures in categories.items():
        if not failures:
            continue

        report.append(
            f"## {category.replace('_', ' ').title()} ({len(failures)} failures)"
        )

        if category == "missing_exports":
            missing_exports = extract_missing_exports(failures)
            report.append("**Missing Exports Requiring Facade Updates:**")
            for export in missing_exports:
                report.append(f"- `{export}`")
            report.append("")

        elif category == "performance_regression":
            regressions = analyze_performance_regressions(failures)
            report.append("**Performance Issues:**")
            for reg in regressions:
                report.append(
                    f"- {reg['test']}: {reg['actual_time']} vs target {reg['target_time']}"
                )
            report.append("")

        # Show first few examples for each category
        report.append("**Sample Failures:**")
        for failure in failures[:3]:  # Show first 3
            report.append(f"- `{failure['test']}`: {failure['error_summary']}")

        if len(failures) > 3:
            report.append(f"- ... and {len(failures) - 3} more")
        report.append("")

    # Remediation Strategy
    report.append("## Remediation Strategy")
    report.append("### Phase 1: CRITICAL - Restore Missing Exports (Immediate)")
    if categories["missing_exports"]:
        report.append("- Add missing exports to `server.py` facade")
        report.append("- Estimated effort: 1-2 hours")
        report.append("- Risk: Low - simple import additions")

    if categories["missing_attributes"]:
        report.append("- Add missing CLI attributes")
        report.append("- Estimated effort: 30 minutes")

    report.append("\n### Phase 2: HIGH - Address Functional Issues (Same Day)")
    if categories["performance_regression"]:
        report.append("- Investigate performance regressions")
        report.append("- Estimated effort: 2-4 hours")
        report.append("- Risk: Medium - may require optimization")

    if categories["functional_behavior"]:
        report.append("- Review functional behavior changes")
        report.append("- Estimated effort: 3-6 hours")
        report.append("- Risk: Medium - may require architectural fixes")

    report.append("\n### Phase 3: MEDIUM - Data Structure Fixes (Next Day)")
    if categories["data_structure_issues"]:
        report.append("- Fix data structure compatibility issues")
        report.append("- Estimated effort: 2-3 hours")

    report.append("\n### Phase 4: LOW - Error Message Updates (Future)")
    if categories["error_message_changes"]:
        report.append("- Update tests for new error message formats")
        report.append("- Estimated effort: 1-2 hours")
        report.append("- Risk: Low - test updates only")

    return "\n".join(report)


def main():
    """Main analysis function."""
    print("🔍 Running comprehensive test failure analysis...")

    # Capture pytest output
    print("📊 Capturing test results...")
    pytest_output = run_pytest_and_capture()

    # Parse failures
    print("🔬 Parsing failure patterns...")
    failures = parse_failures(pytest_output)

    # Categorize
    print("📝 Categorizing failures...")
    categories = categorize_failures(failures)

    # Generate report
    print("📋 Generating analysis report...")
    report = generate_analysis_report(categories)

    # Save and display
    with open("test_failure_analysis_report.md", "w") as f:
        f.write(report)

    print("✅ Analysis complete!")
    print("📄 Report saved to: test_failure_analysis_report.md")
    print(f"📊 Total analyzed: {len(failures)} failures")

    # Quick summary
    print("\n🎯 Quick Summary:")
    for category, failures in categories.items():
        if failures:
            print(f"  - {category.replace('_', ' ').title()}: {len(failures)}")


if __name__ == "__main__":
    main()
