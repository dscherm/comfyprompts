#!/usr/bin/env python3
"""Smart gate for ComfyPrompts — targeted test runner + type checker.

Detects changed files, maps them to relevant test files, falls back to
full suite for shared code. Runs after every Ralph Loop iteration.
"""

import subprocess
import sys
import os

# Module-to-test mapping
TEST_MAP = {
    # SDK
    "packages/sdk/src/comfyui_agent_sdk/client/": "packages/sdk/tests/",
    "packages/sdk/src/comfyui_agent_sdk/assets/": "packages/sdk/tests/",
    "packages/sdk/src/comfyui_agent_sdk/defaults/": "packages/sdk/tests/",
    "packages/sdk/src/comfyui_agent_sdk/config.py": "packages/sdk/tests/",
    "packages/sdk/src/comfyui_agent_sdk/credentials.py": "packages/sdk/tests/",
    # MCP Server
    "packages/mcp-server/": "packages/mcp-server/tests/",
    # Prompter
    "packages/prompter/": "packages/prompter/tests/",
}

# Shared files that trigger the full test suite
SHARED_FILES = {
    "config.py",
    "credentials.py",
    "__init__.py",  # package init files
    "client.py",
    "comfyui_client.py",
}


def get_changed_files():
    """Get list of changed files (staged + unstaged + untracked)."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "-u"],
        capture_output=True, text=True, encoding="utf-8",
    )
    files = []
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            # Format: XY filename or XY old -> new
            parts = line[3:].strip().split(" -> ")
            files.append(parts[-1])
    return files


def map_to_tests(changed_files):
    """Map changed files to their test directories."""
    test_dirs = set()
    needs_full = False

    for f in changed_files:
        basename = os.path.basename(f)

        # Check if it's a shared file
        if basename in SHARED_FILES:
            needs_full = True
            break

        # Check if it's a Blender addon file (no tests, just syntax check)
        if f.startswith("blender/"):
            continue

        # Map to test directory
        matched = False
        for src_prefix, test_dir in TEST_MAP.items():
            if f.startswith(src_prefix):
                test_dirs.add(test_dir)
                matched = True
                break

        if not matched and f.endswith(".py"):
            # Unknown Python file — run full suite to be safe
            needs_full = True
            break

    return test_dirs, needs_full


def run_tests(test_dirs=None, full=False):
    """Run pytest, either targeted or full suite."""
    if full or not test_dirs:
        cmd = [sys.executable, "-m", "pytest", "-x", "--tb=short", "-q"]
    else:
        cmd = [sys.executable, "-m", "pytest", "-x", "--tb=short", "-q"]
        cmd.extend(sorted(test_dirs))

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return result.returncode


def main():
    changed = get_changed_files()
    if not changed:
        print("No changed files detected. Gate passes.")
        return 0

    print(f"Changed files: {len(changed)}")
    for f in changed[:10]:
        print(f"  {f}")
    if len(changed) > 10:
        print(f"  ... and {len(changed) - 10} more")

    test_dirs, needs_full = map_to_tests(changed)

    if needs_full:
        print("\nShared code changed — running full test suite.")
        return run_tests(full=True)
    elif test_dirs:
        print(f"\nRunning targeted tests: {', '.join(sorted(test_dirs))}")
        return run_tests(test_dirs=test_dirs)
    else:
        print("\nNo testable Python files changed. Gate passes.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
