#!/usr/bin/env bash
# Ralph Loop — Plan Mode (single-shot read-only analysis)
# Usage: ./ralph-plan.sh

set -euo pipefail

CLAUDE="${CLAUDE_PATH:-claude}"
RALPH_DIR=".ralph"
LOGS_DIR="$RALPH_DIR/logs"

mkdir -p "$LOGS_DIR"

log_file="$LOGS_DIR/plan_$(date +%Y%m%d_%H%M%S).log"

echo "[ralph-plan] Starting read-only analysis..."
echo "[ralph-plan] Log: $log_file"

"$CLAUDE" -p "$(cat PLAN_PROMPT.md)" --output-format text > "$log_file" 2>&1 || true

if grep -q '<promise>PLAN_COMPLETE</promise>' "$log_file" 2>/dev/null; then
    echo "[ralph-plan] Analysis complete."
    # Count issues in fix_plan.md
    if [[ -f fix_plan.md ]]; then
        count=$(grep -c '^\- \[ \]' fix_plan.md 2>/dev/null || echo 0)
        echo "[ralph-plan] Found $count unchecked issues in fix_plan.md"
        echo "[ralph-plan] Run 'python tools/triage_fix_plan.py' to convert to build tasks."
    fi
else
    echo "[ralph-plan] Analysis did not complete. Check log: $log_file"
fi
