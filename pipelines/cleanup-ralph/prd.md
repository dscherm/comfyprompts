# Cleanup — Requirements

## Overview

Cleanup-ralph is a periodic maintenance daemon that monitors disk usage across all pipeline output directories, identifies stale files and duplicate materials, and cleans them up. It prevents unbounded disk growth from accumulated intermediate artifacts and failed generations.

## Target State

The daemon continuously monitors all `pipelines/*/output/` directories. Stale files beyond the TTL are identified and optionally removed. Duplicate materials in GLB files are detected and merged. Disk usage stays within manageable bounds, and a clear cleanup report is produced each iteration.

## Acceptance Criteria

1. Daemon scans all `pipelines/*/output/` directories recursively each iteration without missing any subdirectory
2. Stale files (older than configured `ttl_hours`, default 72) are correctly identified by last-modified time
3. Empty files (0-byte, from failed generations) are always flagged as cleanup candidates
4. Intermediate artifacts in `meshes/` or `concept/` subdirectories are flagged when a `final/` directory exists alongside them
5. `dedup_materials.py` is executed on all GLB files found, reporting duplicate material counts
6. `cleanup-report.json` is written each iteration with per-pipeline disk usage breakdown
7. In dry-run mode (`auto_cleanup: false`), zero files are deleted and the report shows what would be cleaned
8. In auto-cleanup mode (`auto_cleanup: true`), only files matching cleanup criteria are deleted (no false positives)
9. Cumulative statistics (`total_space_freed_mb`, `total_files_cleaned`, `total_materials_deduped`) are accurately tracked across iterations
10. Pipeline state JSON is updated with current iteration count and statistics after each sweep
11. No files outside of `pipelines/*/output/` are ever modified or deleted
12. Daemon respects `max_iterations` and halts when the limit is reached
