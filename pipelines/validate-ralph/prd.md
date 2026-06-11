# Validate — Requirements

## Overview

Validate-ralph is a continuous validation daemon that scans all pipeline output directories for newly created or modified assets and validates their integrity. It catches corrupt files, invalid geometry, blank renders, and malformed metadata before they propagate downstream.

## Target State

The daemon continuously sweeps all `pipelines/*/output/` directories, validates every asset file against format-specific rules, and produces a validation report each iteration. Any failing file is clearly reported with its path and the specific validation failure.

## Acceptance Criteria

1. All `pipelines/*/output/` directories are scanned recursively each iteration with zero missed directories
2. GLB and STL files are validated for manifold geometry with zero non-manifold edges
3. GLB and STL files have face count checked against sane range (1 to 500,000 faces)
4. GLB and STL files have bounding box dimensions checked (non-zero, no axis > 10m)
5. PNG files are validated via magic bytes (`\x89PNG` header) to confirm valid format
6. PNG files are checked for non-zero dimensions (valid image header)
7. PNG files are checked for solid-color content (blank render detection)
8. PNG file sizes are checked against bounds (> 0 bytes, < 100MB)
9. JSON files are validated as parseable without errors
10. `pipeline-state.json` files are checked for required fields: `project_name`, `iteration`
11. Gate result JSON files are checked for required fields: `stage`, `result`, `checks`
12. `validation-report.json` is written each iteration with PASS/FAIL per file and specific failure reasons
13. Cumulative statistics (total files checked, total passes, total failures) are tracked across iterations
14. Zero false positives -- files that are genuinely valid must never be reported as failures
15. Daemon respects `max_iterations` and halts when the limit is reached
