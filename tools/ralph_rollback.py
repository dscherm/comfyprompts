"""Recovery tool for Ralph Loop.

Uses only stdlib — no pip dependencies.

Usage:
    python tools/ralph_rollback.py                    # Show status
    python tools/ralph_rollback.py --to-last-good     # Rollback to last known good
    python tools/ralph_rollback.py --to-commit <hash> # Rollback to specific commit
    python tools/ralph_rollback.py --soft             # Keep changes (default)
    python tools/ralph_rollback.py --hard             # Discard changes
    python tools/ralph_rollback.py --confirm          # Skip interactive prompt
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RALPH_DIR = ROOT / ".ralph"
LAST_GOOD_FILE = RALPH_DIR / "last_known_good"


def run_git(*args) -> str:
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return result.stdout.strip()


def get_head() -> str:
    return run_git("rev-parse", "HEAD")


def get_last_good() -> str | None:
    if not LAST_GOOD_FILE.exists():
        return None
    return LAST_GOOD_FILE.read_text(encoding="utf-8").strip()


def show_status():
    head = get_head()
    last_good = get_last_good()

    print(f"Current HEAD:     {head[:12]}")
    if last_good:
        print(f"Last known good:  {last_good[:12]}")
        # Distance
        log = run_git("log", "--oneline", f"{last_good}..HEAD")
        lines = [l for l in log.splitlines() if l.strip()]
        if lines:
            print(f"Distance:         {len(lines)} commit(s) ahead of last good")
            print(f"\nCommits since last good:")
            for line in lines:
                print(f"  {line}")
        else:
            print("Distance:         AT last known good")
    else:
        print("Last known good:  not recorded yet")


def rollback(target: str, hard: bool = False, confirm: bool = False):
    mode = "hard" if hard else "soft"
    current = get_head()

    if current == target:
        print("Already at target commit. Nothing to do.")
        return

    print(f"Will reset --{mode} to {target[:12]}")
    if hard:
        print("WARNING: --hard will DISCARD all uncommitted changes!")

    if not confirm:
        response = input("Proceed? [y/N] ").strip().lower()
        if response != "y":
            print("Cancelled.")
            return

    flag = "--hard" if hard else "--soft"
    result = subprocess.run(
        ["git", "reset", flag, target],
        capture_output=True, text=True, cwd=str(ROOT),
    )

    if result.returncode == 0:
        print(f"Reset to {target[:12]} ({mode})")
        if not hard:
            print("Changes are preserved in working tree.")
    else:
        print(f"Reset failed: {result.stderr}")


def main():
    to_last_good = "--to-last-good" in sys.argv
    hard = "--hard" in sys.argv
    confirm = "--confirm" in sys.argv

    to_commit = None
    if "--to-commit" in sys.argv:
        idx = sys.argv.index("--to-commit")
        if idx + 1 < len(sys.argv):
            to_commit = sys.argv[idx + 1]

    if to_last_good:
        target = get_last_good()
        if not target:
            print("No last_known_good recorded. Cannot rollback.")
            sys.exit(1)
        rollback(target, hard=hard, confirm=confirm)
    elif to_commit:
        rollback(to_commit, hard=hard, confirm=confirm)
    else:
        show_status()


if __name__ == "__main__":
    main()
