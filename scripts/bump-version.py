#!/usr/bin/env python3
"""
Atomic version bump script that ensures consistency across all version sources.
Usage: python scripts/bump-version.py [major|minor|patch|x.y.z]
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

import toml


def get_current_version() -> str:
    """Get current version from pyproject.toml"""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")

    data = toml.load(pyproject_path)
    return data["project"]["version"]


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse semantic version string into components"""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")

    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(current: str, bump_type: str) -> str:
    """Calculate new version based on bump type"""
    if re.match(r"^\d+\.\d+\.\d+$", bump_type):
        # Explicit version provided
        return bump_type

    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    if bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    if bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Invalid bump type: {bump_type}")


def update_pyproject_version(new_version: str):
    """Update version in pyproject.toml"""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()

    # Replace version line
    updated = re.sub(
        r'^version = "[^"]*"', f'version = "{new_version}"', content, flags=re.MULTILINE
    )

    pyproject_path.write_text(updated)
    print(f"✅ Updated pyproject.toml version to {new_version}")


def run_command(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return result"""
    print(f"🔧 Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description="Atomic version bump and release")
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"] + ["x.y.z"],
        nargs="?",
        default="patch",
        help="Version bump type or explicit version (e.g., 1.2.3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Update version but don't commit or tag",
    )

    args = parser.parse_args()

    try:
        current_version = get_current_version()
        print(f"📦 Current version: {current_version}")

        # Handle explicit version format
        bump_type = args.bump_type
        if bump_type not in ["major", "minor", "patch"] and not re.match(
            r"^\d+\.\d+\.\d+$", bump_type
        ):
            print(f"❌ Invalid version format: {bump_type}")
            print("   Use: major, minor, patch, or x.y.z format")
            sys.exit(1)

        new_version = bump_version(current_version, bump_type)
        print(f"🚀 New version: {new_version}")

        if args.dry_run:
            print("🔍 DRY RUN - No changes made")
            return

        # Update pyproject.toml
        update_pyproject_version(new_version)

        if not args.no_commit:
            # Stage and commit changes
            run_command(["git", "add", "pyproject.toml", "uv.lock"])
            run_command(
                ["git", "commit", "-m", f"chore: Bump version to {new_version}"]
            )

            # Create git tag
            tag_name = f"v{new_version}"
            run_command(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"])

            print(f"✅ Created commit and tag: {tag_name}")
            print("\n🔧 Next steps:")
            print(f"   git push && git push origin {tag_name}")
            print(f"   gh release create {tag_name}")
        else:
            print("✅ Version updated (no commit created)")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
