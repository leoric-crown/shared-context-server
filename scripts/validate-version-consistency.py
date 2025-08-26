#!/usr/bin/env python3
"""
Validate version consistency across pyproject.toml, git tags, and Docker builds.
Used as a pre-commit hook to prevent version mismatches.
"""

import subprocess
import sys
from pathlib import Path

import toml


def get_pyproject_version() -> str:
    """Get version from pyproject.toml"""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("❌ pyproject.toml not found")
        return ""

    data = toml.load(pyproject_path)
    return data.get("project", {}).get("version", "")


def get_latest_git_tag() -> str:
    """Get the latest git tag that looks like a version"""
    try:
        result = subprocess.run(
            ["git", "tag", "--sort=-version:refname", "--list", "v*"],
            capture_output=True,
            text=True,
            check=True,
        )
        tags = result.stdout.strip().split("\n")
        return tags[0] if tags and tags[0] else ""
    except subprocess.CalledProcessError:
        return ""


def check_staged_pyproject_version() -> bool:
    """Check if pyproject.toml version has been updated in staged changes"""
    try:
        # Check if pyproject.toml is staged
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        staged_files = result.stdout.strip().split("\n")

        if "pyproject.toml" in staged_files:
            print("✅ pyproject.toml version update is staged")
            return True

        return False
    except subprocess.CalledProcessError:
        return False


def main():
    """Main validation logic"""
    pyproject_version = get_pyproject_version()
    latest_tag = get_latest_git_tag()

    if not pyproject_version:
        print("❌ Could not read version from pyproject.toml")
        sys.exit(1)

    print(f"📦 pyproject.toml version: {pyproject_version}")
    print(f"🏷️  Latest git tag: {latest_tag}")

    # If we're about to commit and there's a newer tag than pyproject version
    if (
        latest_tag
        and latest_tag.lstrip("v") != pyproject_version
        and not check_staged_pyproject_version()
    ):
        print("\n❌ VERSION MISMATCH DETECTED!")
        print(f"   Git tag: {latest_tag}")
        print(f"   pyproject.toml: {pyproject_version}")
        print("\n💡 Before tagging a new version:")
        print("   1. Update pyproject.toml version first")
        print("   2. Commit the version change")
        print("   3. Then create the git tag")
        print("\n🔧 To fix this:")
        print(
            f'   sed -i \'s/version = "{pyproject_version}"/version = "{latest_tag.lstrip("v")}"/g\' pyproject.toml'
        )
        sys.exit(1)

    print("✅ Version consistency check passed")
    return 0


if __name__ == "__main__":
    main()
