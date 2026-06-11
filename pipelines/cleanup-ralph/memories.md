# Cleanup Ralph — Memories

## Initial Context
- Created: 2026-03-25
- Purpose: Periodic disk cleanup daemon that removes stale files and deduplicates materials across pipeline outputs
- Domain: `pipelines/*/output/` — monitors all pipeline output directories for stale files, empty files, and duplicate GLB materials
