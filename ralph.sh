#!/usr/bin/env bash
# Ralph Loop — Build Mode Harness
# Usage: ./ralph.sh [max_iterations] [--gate-mode warn|block|off] [--gate-cmd CMD]
#        [--timeout SECONDS] [--max-files N] [--force] [--dry-run]

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────
CLAUDE="${CLAUDE_PATH:-claude}"
MAX_ITERATIONS="${1:-20}"
GATE_MODE="warn"
GATE_CMD="python tools/smart_gate.py"
TIMEOUT=1800
MAX_FILES=20
FORCE=false
DRY_RUN=false
CONSEC_FAIL_THRESHOLD=3

# Parse flags (skip positional arg 1 if numeric)
shift_done=false
for arg in "$@"; do
    if [[ "$shift_done" == false && "$arg" =~ ^[0-9]+$ ]]; then
        shift_done=true
        continue
    fi
    case "$arg" in
        --gate-mode)  next_is="gate_mode" ;;
        --gate-cmd)   next_is="gate_cmd" ;;
        --timeout)    next_is="timeout" ;;
        --max-files)  next_is="max_files" ;;
        --force)      FORCE=true ;;
        --dry-run)    DRY_RUN=true ;;
        *)
            if [[ -n "${next_is:-}" ]]; then
                case "$next_is" in
                    gate_mode)  GATE_MODE="$arg" ;;
                    gate_cmd)   GATE_CMD="$arg" ;;
                    timeout)    TIMEOUT="$arg" ;;
                    max_files)  MAX_FILES="$arg" ;;
                esac
                unset next_is
            fi
            ;;
    esac
done

# ── Directories ───────────────────────────────────────────────
RALPH_DIR=".ralph"
LOGS_DIR="$RALPH_DIR/logs"
LOCK_FILE="$RALPH_DIR/lock"
GATE_FAILURE="$RALPH_DIR/gate_failure.md"
LAST_GOOD="$RALPH_DIR/last_known_good"
METRICS="$RALPH_DIR/metrics.jsonl"
HUMAN_NOTE="$RALPH_DIR/human_note.md"
PAUSE_FILE="$RALPH_DIR/pause"

mkdir -p "$LOGS_DIR"

# ── Cleanup trap ──────────────────────────────────────────────
cleanup() {
    rm -f "$LOCK_FILE"
    echo "[ralph] Lock released."
}
trap cleanup EXIT INT TERM

# ── Startup checks ────────────────────────────────────────────
if [[ "$FORCE" != true ]]; then
    # Lock file
    if [[ -f "$LOCK_FILE" ]]; then
        old_pid=$(head -1 "$LOCK_FILE" 2>/dev/null || echo "")
        if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
            echo "[ralph] ERROR: Another Ralph Loop is running (PID $old_pid)."
            echo "[ralph] Use --force to override."
            exit 1
        else
            echo "[ralph] Removing stale lock (PID $old_pid no longer running)."
            rm -f "$LOCK_FILE"
        fi
    fi

    # Dirty tree
    dirty=$(git status --porcelain | grep -v "^??" || true)
    if [[ -n "$dirty" ]]; then
        echo "[ralph] WARNING: Working tree has uncommitted changes."
        echo "$dirty"
        read -p "Continue anyway? [y/N] " -r
        [[ "$REPLY" =~ ^[Yy]$ ]] || exit 1
    fi

    # Branch safety
    branch=$(git branch --show-current)
    if [[ "$branch" == "main" || "$branch" == "master" ]]; then
        echo "[ralph] WARNING: Running on '$branch'. Consider using a feature branch."
        read -p "Continue on $branch? [y/N] " -r
        [[ "$REPLY" =~ ^[Yy]$ ]] || exit 1
    fi
fi

# Write lock
echo "$$" > "$LOCK_FILE"
echo "$(git branch --show-current)" >> "$LOCK_FILE"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOCK_FILE"

branch=$(git branch --show-current)
echo "[ralph] Starting on branch: $branch"
echo "[ralph] Max iterations: $MAX_ITERATIONS"
echo "[ralph] Gate mode: $GATE_MODE"
echo "[ralph] Timeout: ${TIMEOUT}s"

if [[ "$DRY_RUN" == true ]]; then
    echo "[ralph] DRY RUN — validating setup only."
    echo "[ralph] Required files:"
    for f in PROMPT.md plan.md activity.md CLAUDE.md tools/prepare_context.py tools/smart_gate.py; do
        if [[ -f "$f" ]]; then
            echo "  OK  $f"
        else
            echo "  MISSING  $f"
        fi
    done
    echo "[ralph] Dry run complete."
    exit 0
fi

# ── State tracking ────────────────────────────────────────────
consec_failures=0
last_gate_output=""
run_id="$(date +%Y%m%d_%H%M%S)"

# ── Main loop ─────────────────────────────────────────────────
for iteration in $(seq 1 "$MAX_ITERATIONS"); do
    echo ""
    echo "================================================================"
    echo "  ITERATION $iteration / $MAX_ITERATIONS  (run: $run_id)"
    echo "================================================================"

    iter_start=$SECONDS
    log_file="$LOGS_DIR/iteration_$(printf '%03d' "$iteration").log"

    # ── Check pause file ──────────────────────────────────────
    if [[ -f "$PAUSE_FILE" ]]; then
        echo "[ralph] Paused. Options:"
        echo "  r) Resume"
        echo "  s) Status"
        echo "  q) Quit"
        while true; do
            read -p "[ralph] > " -r choice
            case "$choice" in
                r) rm -f "$PAUSE_FILE"; echo "[ralph] Resuming."; break ;;
                s) python tools/ralph_status.py 2>/dev/null || echo "Status unavailable" ;;
                q) echo "[ralph] Quitting."; exit 0 ;;
                *) echo "  r/s/q?" ;;
            esac
        done
    fi

    # ── Prepare context ───────────────────────────────────────
    echo "[ralph] Preparing context..."
    python tools/prepare_context.py

    # ── Clear human note after reading ────────────────────────
    # (Agent reads it via @-include, then we clear it)

    # ── Invoke agent ──────────────────────────────────────────
    echo "[ralph] Invoking Claude..."

    # Use timeout if available, otherwise just run directly
    if command -v timeout &>/dev/null; then
        timeout "${TIMEOUT}s" "$CLAUDE" -p "$(cat PROMPT.md)" --output-format text \
            > "$log_file" 2>&1 || true
    else
        "$CLAUDE" -p "$(cat PROMPT.md)" --output-format text \
            > "$log_file" 2>&1 || true
    fi

    iter_duration=$(( SECONDS - iter_start ))

    # Clear human note (single-use)
    if [[ -f "$HUMAN_NOTE" ]]; then
        > "$HUMAN_NOTE"
    fi

    # ── Check signals ─────────────────────────────────────────
    if grep -q '<promise>COMPLETE</promise>' "$log_file" 2>/dev/null; then
        echo "[ralph] COMPLETE signal received. All tasks done!"
        # Tag the repo
        tag="v0.$(git rev-list --count HEAD)"
        git tag -a "$tag" -m "Ralph Loop completed: $run_id" 2>/dev/null || true
        echo "[ralph] Tagged as $tag"
        python tools/ralph_status.py --oneline 2>/dev/null || true
        exit 0
    fi

    if grep -q '<promise>BLOCKED</promise>' "$log_file" 2>/dev/null; then
        echo "[ralph] BLOCKED signal received. Human intervention needed."
        echo "[ralph] Check activity.md for details."
        exit 1
    fi

    if grep -q '<promise>NEEDS_REVIEW</promise>' "$log_file" 2>/dev/null; then
        echo "[ralph] NEEDS_REVIEW signal. Pausing for human review."
        touch "$PAUSE_FILE"
    fi

    if grep -q '<promise>SPAWN_REQUESTED</promise>' "$log_file" 2>/dev/null; then
        echo "[ralph] SPAWN_REQUESTED — mini-ralph not yet implemented."
        echo "[ralph] Decompose the task manually and continue."
        touch "$PAUSE_FILE"
    fi

    # ── Count changed files ───────────────────────────────────
    files_changed=$(git diff --name-only HEAD 2>/dev/null | wc -l || echo 0)
    files_changed=$(echo "$files_changed" | tr -d ' ')

    if [[ "$files_changed" -gt "$MAX_FILES" ]]; then
        echo "[ralph] WARNING: $files_changed files changed (threshold: $MAX_FILES)."
        echo "[ralph] Pausing for review."
        touch "$PAUSE_FILE"
    fi

    # ── Run gate ──────────────────────────────────────────────
    gate_result="skip"
    gate_output=""

    if [[ "$GATE_MODE" != "off" ]]; then
        echo "[ralph] Running gate..."
        gate_output=$($GATE_CMD 2>&1) && gate_result="pass" || gate_result="fail"

        if [[ "$gate_result" == "pass" ]]; then
            echo "[ralph] Gate PASSED."
            > "$GATE_FAILURE"  # Clear gate failure file
            consec_failures=0
            # Update last known good
            git rev-parse HEAD > "$LAST_GOOD" 2>/dev/null || true
        else
            echo "[ralph] Gate FAILED."
            echo "$gate_output" | tail -20
            consec_failures=$(( consec_failures + 1 ))

            # Write failure for agent feedback
            {
                echo "# Gate Failure (iteration $iteration)"
                echo ""
                echo '```'
                echo "$gate_output"
                echo '```'
            } > "$GATE_FAILURE"

            # Same-error detection
            if [[ "$gate_output" == "$last_gate_output" ]]; then
                echo "[ralph] WARNING: Same gate error as previous iteration!"
                if [[ $consec_failures -ge $CONSEC_FAIL_THRESHOLD ]]; then
                    echo "[ralph] $consec_failures consecutive identical failures. Auto-BLOCKED."
                    exit 2
                fi
            fi
            last_gate_output="$gate_output"

            if [[ "$GATE_MODE" == "block" ]]; then
                echo "[ralph] Gate mode is 'block'. Halting."
                exit 2
            fi

            if [[ $consec_failures -ge $CONSEC_FAIL_THRESHOLD ]]; then
                echo "[ralph] WARNING: $consec_failures consecutive gate failures!"
            fi
        fi
    fi

    # ── Record metrics ────────────────────────────────────────
    log_size=$(wc -c < "$log_file" 2>/dev/null || echo 0)
    log_size=$(echo "$log_size" | tr -d ' ')
    input_est=$(( log_size / 4 ))    # rough token estimate
    output_est=$(( log_size / 8 ))   # output is typically half of input

    echo "{\"iteration\":$iteration,\"run_id\":\"$run_id\",\"duration_s\":$iter_duration,\"gate_result\":\"$gate_result\",\"files_changed\":$files_changed,\"input_tokens_est\":$input_est,\"output_tokens_est\":$output_est,\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >> "$METRICS"

    echo "[ralph] Iteration $iteration complete. Duration: ${iter_duration}s, Files: $files_changed, Gate: $gate_result"

    # Brief pause between iterations
    sleep 2
done

echo ""
echo "[ralph] Max iterations ($MAX_ITERATIONS) reached."
python tools/ralph_status.py --oneline 2>/dev/null || true
exit 0
