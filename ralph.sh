#!/usr/bin/env bash
# ralph.sh — Orchestrator for all mini-ralph loops
#
# Usage:
#   bash ralph.sh --preset <name>       Run a specific mini-ralph loop
#   bash ralph.sh --status              Show dashboard of all loops
#   bash ralph.sh --chain <a> <b> ...   Run multiple presets sequentially
#   bash ralph.sh --list                List all available presets
#
# Each preset maps to a pipeline's PROMPT.md. The loop feeds the prompt
# to claude-code repeatedly until a completion promise is detected or
# max iterations is reached.

set -euo pipefail

PIPELINES_DIR="$(cd "$(dirname "$0")" && pwd)/pipelines"

# ─────────────────────────────────────────────────────────
# Preset → Prompt resolution
# ─────────────────────────────────────────────────────────
resolve_preset() {
  case "$1" in
    fusion)          echo "$PIPELINES_DIR/fusion-ralph/PROMPT.md" ;;
    asset-forge)     echo "$PIPELINES_DIR/asset-forge-ralph/PROMPT.md" ;;
    character)       echo "$PIPELINES_DIR/character-ralph/PROMPT.md" ;;
    video)           echo "$PIPELINES_DIR/video-ralph/PROMPT.md" ;;
    audio)           echo "$PIPELINES_DIR/audio-ralph/PROMPT.md" ;;
    tileset)         echo "$PIPELINES_DIR/tileset-ralph/PROMPT.md" ;;
    style-transfer)  echo "$PIPELINES_DIR/style-transfer-ralph/PROMPT.md" ;;
    upscale)         echo "$PIPELINES_DIR/upscale-ralph/PROMPT.md" ;;
    inpaint)         echo "$PIPELINES_DIR/inpaint-ralph/PROMPT.md" ;;
    art-to-rig)      echo "$PIPELINES_DIR/art-to-rig-ralph/PROMPT.md" ;;
    animate)         echo "$PIPELINES_DIR/animate-ralph/PROMPT.md" ;;
    validate)        echo "$PIPELINES_DIR/validate-ralph/PROMPT.md" ;;
    cleanup)         echo "$PIPELINES_DIR/cleanup-ralph/PROMPT.md" ;;
    hot-reload)      echo "$PIPELINES_DIR/hot-reload-ralph/PROMPT.md" ;;
    scene)           echo "$PIPELINES_DIR/scene-ralph/PROMPT.md" ;;
    autorig)         echo "$PIPELINES_DIR/autorig-ralph/PROMPT.md" ;;
    *)               echo "" ;;
  esac
}

# ─────────────────────────────────────────────────────────
# Completion promise detection
# ─────────────────────────────────────────────────────────
resolve_promise() {
  case "$1" in
    fusion)          echo "PIPELINE COMPLETE" ;;
    asset-forge)     echo "ASSET FORGE COMPLETE" ;;
    character)       echo "CHARACTER COMPLETE" ;;
    video)           echo "VIDEO COMPLETE" ;;
    audio)           echo "AUDIO COMPLETE" ;;
    tileset)         echo "TILESET COMPLETE" ;;
    style-transfer)  echo "STYLE TRANSFER COMPLETE" ;;
    upscale)         echo "UPSCALE COMPLETE" ;;
    inpaint)         echo "INPAINT COMPLETE" ;;
    art-to-rig)      echo "ART TO RIG COMPLETE" ;;
    animate)         echo "ANIMATE COMPLETE" ;;
    validate)        echo "" ;;  # daemon — no completion
    cleanup)         echo "" ;;  # daemon — no completion
    hot-reload)      echo "" ;;  # daemon — no completion
    scene)           echo "SCENE COMPLETE" ;;
    autorig)         echo "AUTORIG COMPLETE" ;;
    *)               echo "" ;;
  esac
}

# ─────────────────────────────────────────────────────────
# Status dashboard
# ─────────────────────────────────────────────────────────
show_status() {
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║              RALPH PIPELINE STATUS DASHBOARD                ║"
  echo "╠══════════════════════════╤════════╤══════╤═════════════════╣"
  printf "║ %-24s │ %6s │ %4s │ %-15s ║\n" "Pipeline" "Stage" "Iter" "Status"
  echo "╠══════════════════════════╪════════╪══════╪═════════════════╣"

  for dir in "$PIPELINES_DIR"/*/; do
    name=$(basename "$dir" | sed 's/-ralph$//')
    state_file="$dir/output/pipeline-state.json"

    if [ -f "$state_file" ]; then
      stage=$(python3 -c "import json; d=json.load(open('$state_file')); print(d.get('current_stage', '?'))" 2>/dev/null || echo "?")
      iteration=$(python3 -c "import json; d=json.load(open('$state_file')); print(d.get('iteration', '?'))" 2>/dev/null || echo "?")
      completed=$(python3 -c "
import json
d=json.load(open('$state_file'))
stages=d.get('stages',{})
done=sum(1 for s in stages.values() if s.get('gate_passed'))
total=len(stages)
mode=d.get('mode','pipeline')
if d.get('completed'): print('COMPLETE')
elif mode=='daemon': print('DAEMON')
elif int('$stage' if '$stage' != '?' else '0')>0: print(f'{done}/{total} gates')
else: print('IDLE')
" 2>/dev/null || echo "?")
      printf "║ %-24s │ %6s │ %4s │ %-15s ║\n" "$name" "$stage" "$iteration" "$completed"
    else
      printf "║ %-24s │ %6s │ %4s │ %-15s ║\n" "$name" "-" "-" "NO STATE"
    fi
  done

  echo "╚══════════════════════════╧════════╧══════╧═════════════════╝"
}

# ─────────────────────────────────────────────────────────
# List available presets
# ─────────────────────────────────────────────────────────
list_presets() {
  echo "Available presets:"
  echo ""
  echo "  Production pipelines:"
  echo "    fusion          3D print-ready STL for Fusion 360"
  echo "    asset-forge     Text → rigged animated 3D game asset"
  echo "    character       Character art + 3D + rig package"
  echo "    art-to-rig      2D illustration → rigged 3D (batch, multi-style)"
  echo "    video           Script → video production pipeline"
  echo "    audio           Script → TTS + voice clone + SFX + mix"
  echo "    tileset         Game tileset generation + atlas"
  echo "    style-transfer  Batch style application"
  echo "    upscale         Batch upscale + multi-format export"
  echo "    inpaint         Self-correcting image refinement loop"
  echo "    scene           Text -> 3D rendered scene (comfyui-mcp + blender-mcp)"
  echo "    autorig         ML auto-rigging: mesh -> skeleton -> weights -> IK -> export"
  echo ""
  echo "  Daemon pipelines:"
  echo "    validate        Continuous asset validation sweep"
  echo "    cleanup         TTL cleanup + material deduplication"
  echo "    hot-reload      File watcher + rebuild trigger"
  echo ""
  echo "Usage:"
  echo "  bash ralph.sh --preset <name>"
  echo "  bash ralph.sh --chain fusion asset-forge"
  echo "  bash ralph.sh --status"
}

# ─────────────────────────────────────────────────────────
# Run a single preset
# ─────────────────────────────────────────────────────────
run_preset() {
  local preset="$1"
  local prompt_file
  prompt_file=$(resolve_preset "$preset")

  if [ -z "$prompt_file" ] || [ ! -f "$prompt_file" ]; then
    echo "ERROR: Unknown preset '$preset' or prompt file not found"
    echo "Run 'bash ralph.sh --list' to see available presets"
    exit 1
  fi

  local promise
  promise=$(resolve_promise "$preset")

  echo "Starting ralph loop: $preset"
  echo "  Prompt: $prompt_file"
  [ -n "$promise" ] && echo "  Promise: $promise"
  echo ""

  local max_default=30
  if [ -z "$promise" ]; then
    max_default=999  # daemon mode
  fi

  local iteration=0
  while [ $iteration -lt $max_default ]; do
    iteration=$((iteration + 1))
    echo "─── Iteration $iteration ───"

    # Feed prompt to claude-code
    local output
    output=$(cat "$prompt_file" | claude --continue 2>&1) || true

    # Check for completion promise
    if [ -n "$promise" ] && echo "$output" | grep -q "$promise"; then
      echo ""
      echo "Pipeline '$preset' completed after $iteration iterations"
      echo "Promise detected: $promise"
      return 0
    fi

    # Check for BLOCKED signal
    if echo "$output" | grep -q "BLOCKED"; then
      echo ""
      echo "Pipeline '$preset' is BLOCKED after $iteration iterations"
      echo "$output" | grep "BLOCKED"
      return 1
    fi
  done

  echo "Pipeline '$preset' reached max iterations ($max_default)"
  return 1
}

# ─────────────────────────────────────────────────────────
# Chain multiple presets
# ─────────────────────────────────────────────────────────
run_chain() {
  local presets=("$@")
  echo "Running chain: ${presets[*]}"
  echo ""

  for preset in "${presets[@]}"; do
    echo "═══════════════════════════════════════"
    echo "  Chain step: $preset"
    echo "═══════════════════════════════════════"
    run_preset "$preset"
    local result=$?
    if [ $result -ne 0 ]; then
      echo "Chain aborted at '$preset'"
      return $result
    fi
  done

  echo ""
  echo "Chain complete: ${presets[*]}"
}

# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
case "${1:-}" in
  --preset)
    shift
    run_preset "${1:?ERROR: --preset requires a name}"
    ;;
  --status)
    show_status
    ;;
  --list)
    list_presets
    ;;
  --chain)
    shift
    run_chain "$@"
    ;;
  --help|-h|"")
    echo "ralph.sh — Mini-ralph loop orchestrator"
    echo ""
    echo "  --preset <name>       Run a mini-ralph loop"
    echo "  --status              Show all pipeline status"
    echo "  --chain <a> <b> ...   Run presets sequentially"
    echo "  --list                List available presets"
    echo "  --help                Show this help"
    ;;
  *)
    echo "Unknown option: $1"
    echo "Run 'bash ralph.sh --help' for usage"
    exit 1
    ;;
esac
