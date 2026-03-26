"""Move old activity.md entries to .ralph/activity_archive.md.

Keeps the last N entries in activity.md (default 10).
Uses only stdlib — no pip dependencies.

Usage: python tools/archive_activity.py [--keep N]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTIVITY_FILE = ROOT / "activity.md"
ARCHIVE_FILE = ROOT / ".ralph" / "activity_archive.md"

DEFAULT_KEEP = 10


def main():
    keep = DEFAULT_KEEP
    if "--keep" in sys.argv:
        idx = sys.argv.index("--keep")
        if idx + 1 < len(sys.argv):
            keep = int(sys.argv[idx + 1])

    if not ACTIVITY_FILE.exists():
        print("[archive] No activity.md found. Nothing to archive.")
        return

    text = ACTIVITY_FILE.read_text(encoding="utf-8")

    # Split: header (everything before first ## entry) and entries
    entry_pattern = re.compile(r"^(## \d{4}-\d{2}-\d{2}\b.*)$", re.MULTILINE)
    positions = [m.start() for m in entry_pattern.finditer(text)]

    if len(positions) <= keep:
        print(f"[archive] {len(positions)} entries, keeping {keep}. Nothing to archive.")
        return

    # Split into header + entries
    header = text[:positions[0]].rstrip() + "\n\n" if positions else ""
    entries = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        entries.append(text[pos:end].rstrip())

    # Entries to archive (oldest) and keep (newest)
    to_archive = entries[:-keep]
    to_keep = entries[-keep:]

    # Write updated activity.md
    kept_text = header + "\n\n".join(to_keep) + "\n"
    ACTIVITY_FILE.write_text(kept_text, encoding="utf-8")

    # Append to archive (newest batch first within the prepend)
    archive_text = ""
    if ARCHIVE_FILE.exists():
        archive_text = ARCHIVE_FILE.read_text(encoding="utf-8")

    batch_header = f"\n\n---\n\n"
    archived_block = batch_header + "\n\n".join(to_archive) + "\n"

    # Insert after the archive file header
    if "# Activity Archive" in archive_text:
        # Insert after the header line
        header_end = archive_text.index("\n", archive_text.index("# Activity Archive")) + 1
        archive_text = archive_text[:header_end] + archived_block + archive_text[header_end:]
    else:
        archive_text = "# Activity Archive — Weather Alpha\n" + archived_block + archive_text

    ARCHIVE_FILE.write_text(archive_text, encoding="utf-8")
    print(f"[archive] Archived {len(to_archive)} entries. Kept {len(to_keep)} in activity.md.")


if __name__ == "__main__":
    main()
