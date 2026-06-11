# Hot Reload — Requirements

## Overview

Hot-reload-ralph is a file watcher daemon that monitors source files for changes and triggers appropriate re-validation, re-testing, or re-generation notifications when modifications are detected. It provides continuous feedback on workflow JSON validity, script test coverage, and pipeline stage dependencies.

## Target State

The daemon continuously watches configured directories, detects file changes via hash comparison, and reports actionable information: workflow validation results, test coverage gaps, image dependency chains, and pipeline re-run recommendations. It never triggers actions automatically -- it only reports what needs attention.

## Acceptance Criteria

1. All configured watch directories are scanned each iteration without missing any file
2. File change detection uses modification time + file size hashing with zero false negatives between iterations
3. Changed workflow JSON files are validated as parseable JSON and report the number of PARAM_* placeholders found
4. Changed workflow JSON files with a `.meta.json` sidecar are cross-validated: all PARAM_* placeholders have corresponding parameter definitions
5. Changed `.meta.json` files are validated for required fields: `parameters` array, `tool.name`, `tool.description`, `tool.category`
6. Changed Python scripts report whether corresponding test files exist in `packages/mcp-server/tests/`
7. Changed pipeline stage files report which pipeline and stage number was modified with a re-run recommendation
8. Changed source images report which pipeline(s) reference them as inputs
9. File hashes are persisted in `pipeline-state.json` between iterations so restarts do not produce false change events
10. No files are modified or deleted by this daemon -- it is strictly read-only and report-only
11. Daemon respects `max_iterations` and halts when the limit is reached
12. Each iteration produces a clear summary line: number of files checked, number of changes detected, number of issues found
