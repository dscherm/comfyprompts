#!/usr/bin/env bash
# =============================================================================
# T-Pose Concept Art → GLB → FBX Pipeline
# =============================================================================
#
# Runs the full pipeline to regenerate T-pose concept art, convert to textured
# GLB models via Hunyuan3D v2.0, and prepare FBX exports for Mixamo rigging.
#
# Prerequisites:
#   - ComfyUI running at localhost:8188 (with Flux + Hunyuan3D v2.0 models)
#   - Python 3.11+ with comfyui-agent-sdk on path
#   - Blender 5.0+ installed (for FBX export stage)
#
# Usage:
#   bash run_tpose_pipeline.sh [--stage STAGE] [--dry-run]
#
# Stages:
#   1 - Generate T-pose character concept art PNGs (24 images, ~30 min)
#   2 - Generate T-pose creature concept art PNGs (10 humanoid, ~12 min)
#   3 - Convert character PNGs to textured GLBs via Hunyuan3D v2.0 (~55 min)
#   4 - Convert creature PNGs to textured GLBs via Hunyuan3D v2.0 (~20 min)
#   5 - Export GLBs to FBX for Mixamo rigging via Blender (~10 min)
#   all - Run all stages (default)
#
# Each stage is idempotent — skips already-generated files.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLCHAIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
GODOT_PROJECT="D:/Projects/berserkr-godot"
GAME_ASSETS="$GODOT_PROJECT/games/berserkr/assets"
BLENDER="C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"

# Parse arguments
STAGE="all"
DRY_RUN=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --stage) STAGE="$2"; shift 2 ;;
        --dry-run) DRY_RUN="--dry-run"; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

echo "============================================================"
echo "T-Pose Pipeline — Stage: $STAGE ${DRY_RUN:+(dry run)}"
echo "============================================================"
echo ""

# --- Stage 1: Character concept art PNGs ---
if [[ "$STAGE" == "1" || "$STAGE" == "all" ]]; then
    echo "[Stage 1/5] Generating T-pose character concept art..."
    echo "  Script: generate_berserkr_characters.py --phase 3"
    echo "  Output: $GAME_ASSETS/sprites/characters/concepts/{classes,npcs}/"
    echo "  Expect: 24 PNGs, ~75s each, ~30 min total"
    echo ""
    python "$SCRIPT_DIR/generate_berserkr_characters.py" --phase 3 $DRY_RUN
    echo ""
    echo "[Stage 1] DONE"
    echo ""
fi

# --- Stage 2: Creature concept art PNGs (humanoid only) ---
if [[ "$STAGE" == "2" || "$STAGE" == "all" ]]; then
    echo "[Stage 2/5] Generating T-pose humanoid creature concept art..."
    echo "  Script: generate_berserkr_creatures.py"
    echo "  Output: $GAME_ASSETS/sprites/creatures/{realm}/"
    echo "  Expect: 10 humanoid PNGs (8 non-humanoid skipped), ~75s each, ~12 min total"
    echo ""
    python "$SCRIPT_DIR/generate_berserkr_creatures.py" $DRY_RUN
    echo ""
    echo "[Stage 2] DONE"
    echo ""
fi

# --- Stage 3: Character PNGs → textured GLBs via Hunyuan3D v2.0 ---
if [[ "$STAGE" == "3" || "$STAGE" == "all" ]]; then
    echo "[Stage 3/5] Converting character PNGs to textured GLBs..."
    echo "  Script: hunyuan3d_batch_convert.py --asset-type characters"
    echo "  Input:  $GAME_ASSETS/sprites/characters/concepts/{classes,npcs}/*.png"
    echo "  Output: $GAME_ASSETS/models/characters/{classes,npcs}/*.glb"
    echo "  Expect: 24 GLBs, ~124s each, ~55 min total"
    echo "  Note: Old GLBs backed up to models/_backup_pre_textured/"
    echo ""
    if [[ -n "$DRY_RUN" ]]; then
        echo "  [DRY RUN] Would run: hunyuan3d_batch_convert.py --asset-type characters --force"
    else
        python "$SCRIPT_DIR/hunyuan3d_batch_convert.py" --asset-type characters --force
    fi
    echo ""
    echo "[Stage 3] DONE"
    echo ""
fi

# --- Stage 4: Creature PNGs → textured GLBs via Hunyuan3D v2.0 ---
if [[ "$STAGE" == "4" || "$STAGE" == "all" ]]; then
    echo "[Stage 4/5] Converting creature PNGs to textured GLBs..."
    echo "  Script: hunyuan3d_batch_convert.py --asset-type creatures"
    echo "  Input:  $GAME_ASSETS/sprites/creatures/{realm}/*.png"
    echo "  Output: $GAME_ASSETS/models/creatures/{realm}/*.glb"
    echo "  Expect: 18 GLBs (incl. non-humanoid), ~124s each, ~37 min total"
    echo "  Note: Old GLBs backed up to models/_backup_pre_textured/"
    echo ""
    if [[ -n "$DRY_RUN" ]]; then
        echo "  [DRY RUN] Would run: hunyuan3d_batch_convert.py --asset-type creatures --force"
    else
        python "$SCRIPT_DIR/hunyuan3d_batch_convert.py" --asset-type creatures --force
    fi
    echo ""
    echo "[Stage 4] DONE"
    echo ""
fi

# --- Stage 5: GLBs → FBX for Mixamo via Blender ---
if [[ "$STAGE" == "5" || "$STAGE" == "all" ]]; then
    echo "[Stage 5/5] Exporting GLBs to FBX for Mixamo rigging..."
    echo "  Script: rig_and_animate.py --stage prepare"
    echo "  Input:  $GAME_ASSETS/models/characters/{classes,npcs}/*.glb"
    echo "  Output: $GODOT_PROJECT/scripts/rigging/export_for_mixamo/*.fbx"
    echo "  Expect: 34 FBXes (24 characters + 10 humanoid creatures)"
    echo ""
    if [[ -n "$DRY_RUN" ]]; then
        echo "  [DRY RUN] Would run: rig_and_animate.py --stage prepare"
        echo "  [DRY RUN] Would run: rig_and_animate.py --stage prepare --creature"
    else
        # Characters
        echo "  Preparing character FBXes..."
        "$BLENDER" --background --python "$GODOT_PROJECT/scripts/rigging/rig_and_animate.py" -- --stage prepare
        # Humanoid creatures
        echo "  Preparing humanoid creature FBXes..."
        "$BLENDER" --background --python "$GODOT_PROJECT/scripts/rigging/rig_and_animate.py" -- --stage prepare --creature
    fi
    echo ""
    echo "[Stage 5] DONE"
    echo ""
fi

echo "============================================================"
echo "Pipeline complete!"
echo ""
echo "Next steps:"
echo "  1. Visually inspect generated PNGs for T-pose quality"
echo "  2. Upload FBXes from scripts/rigging/export_for_mixamo/ to Mixamo"
echo "  3. Auto-rig in Mixamo (place 5 markers: chin, wrists, elbows, knees, groin)"
echo "  4. Download rigged FBX + 6 animations per character"
echo "  5. Run: rig_and_animate.py --stage process (strip mixamorig: prefix, export GLB)"
echo "============================================================"
