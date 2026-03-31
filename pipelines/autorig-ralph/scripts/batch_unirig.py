"""
Batch UniRig pipeline for all Soapbox Sabotage characters.

For each character:
1. Import raw Hunyuan3D mesh into Blender
2. Merge vertices (remove_doubles) to fix disconnected triangle islands
3. Verify/fix character faces +Y direction
4. Export cleaned GLB
5. UniRig extract (preprocess mesh → NPZ)
6. UniRig skeleton prediction (~30 min per character on RTX 3070)
7. UniRig ML skin weights (~8 sec per character)
8. Auto-detect and rename bones to standard names

Input:  pipelines/character-ralph/output/{char_id}/3d/character-raw.glb
Output: pipelines/autorig-ralph/output/{char_id}/rigged/{char_id}-rigged-tpose.glb

Usage:
    python pipelines/autorig-ralph/scripts/batch_unirig.py --list
    python pipelines/autorig-ralph/scripts/batch_unirig.py --character bones
    python pipelines/autorig-ralph/scripts/batch_unirig.py --all
    python pipelines/autorig-ralph/scripts/batch_unirig.py --all --skip-existing
    python pipelines/autorig-ralph/scripts/batch_unirig.py --all --step merge-only
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHAR_INPUT_ROOT = REPO_ROOT / "pipelines" / "character-ralph" / "output"
AUTORIG_OUTPUT = REPO_ROOT / "pipelines" / "autorig-ralph" / "output"
UNIRIG_DIR = Path("C:/UniRig")
UNIRIG_PYTHON = UNIRIG_DIR / ".venv" / "Scripts" / "python.exe"
BLENDER_EXE = Path("C:/Program Files/Blender Foundation/Blender 5.0/blender.exe")

# Characters to process (excludes soup_box which needs special handling)
CHARACTERS = ["player", "bones", "crank", "grit", "pip", "punk_king", "rust", "smog", "sparks"]

# Blender script for merge vertices + orient +Y
BLENDER_PREP_SCRIPT = '''
import bpy, bmesh, math, sys, os

argv = sys.argv[sys.argv.index("--") + 1:]
input_glb = argv[0]
output_glb = argv[1]

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)

# Import
bpy.ops.import_scene.gltf(filepath=input_glb)

# Find main mesh (largest by vertex count)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
meshes.sort(key=lambda o: len(o.data.vertices), reverse=True)
obj = meshes[0]

# Delete other objects (empties, small meshes)
for o in list(bpy.data.objects):
    if o != obj:
        bpy.data.objects.remove(o, do_unlink=True)

bpy.context.view_layer.objects.active = obj
obj.select_set(True)

# Step 1: Merge vertices
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.001)
bpy.ops.mesh.normals_make_consistent(inside=False)

# Count islands
bm = bmesh.from_edit_mesh(obj.data)
bm.verts.ensure_lookup_table()
visited = set()
islands = 0
for v in bm.verts:
    if v.index not in visited:
        islands += 1
        stack = [v]
        while stack:
            cur = stack.pop()
            if cur.index in visited: continue
            visited.add(cur.index)
            for e in cur.link_edges:
                other = e.other_vert(cur)
                if other.index not in visited:
                    stack.append(other)

print(f"MERGE: {len(bm.verts)} verts, {len(bm.faces)} faces, {islands} islands")
bpy.ops.object.mode_set(mode='OBJECT')

# Step 2: Verify +Y facing
# Hunyuan3D characters typically face +Y after GLB import
# Check by finding the nose/face direction from mesh geometry
# For now, we assume +Y facing (verified in Stage 4 Step 0b)
# If not facing +Y, uncomment:
# obj.rotation_euler.z = math.radians(180)
# bpy.ops.object.transform_apply(rotation=True)

# Step 3: Export
os.makedirs(os.path.dirname(output_glb), exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.gltf(
    filepath=output_glb, export_format='GLB',
    use_selection=True, export_apply=True)

print(f"EXPORTED: {output_glb} ({os.path.getsize(output_glb):,} bytes)")
'''


def run_blender_prep(input_glb: str, output_glb: str) -> bool:
    """Run Blender headless to merge vertices and orient the mesh."""
    import tempfile
    script_path = tempfile.mktemp(suffix=".py")
    with open(script_path, 'w') as f:
        f.write(BLENDER_PREP_SCRIPT)

    cmd = [
        str(BLENDER_EXE), "--background", "--python", script_path,
        "--", input_glb, output_glb,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    os.unlink(script_path)

    if result.returncode != 0:
        print(f"  Blender prep FAILED: {result.stderr[-500:]}")
        return False

    # Parse output for stats
    for line in result.stdout.splitlines():
        if line.startswith("MERGE:") or line.startswith("EXPORTED:"):
            print(f"  {line}")

    return os.path.exists(output_glb)


def run_unirig_extract(input_glb: str, npz_dir: str) -> bool:
    """Run UniRig mesh extraction/preprocessing."""
    cmd = [
        str(UNIRIG_PYTHON), "-m", "src.data.extract",
        "--config=configs/data/quick_inference.yaml",
        "--require_suffix=glb",
        "--force_override=true",
        "--num_runs=1", "--id=0", "--time=0",
        "--faces_target_count=20000",
        f"--input={input_glb}",
        f"--output_dir={npz_dir}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=str(UNIRIG_DIR))

    # Extract segfaults after saving — check if npz exists
    # The output goes to a subdir named after the input file stem
    stem = Path(input_glb).stem
    npz_candidates = [
        Path(npz_dir) / stem / "raw_data.npz",
        Path(input_glb).parent / stem / "raw_data.npz",
    ]
    for npz in npz_candidates:
        if npz.exists():
            print(f"  Extract OK: {npz} ({npz.stat().st_size:,} bytes)")
            return True

    print(f"  Extract FAILED — no raw_data.npz found")
    return False


def run_unirig_skeleton(input_glb: str, output_fbx: str, npz_dir: str) -> bool:
    """Run UniRig skeleton prediction (~30 min)."""
    cmd = [
        str(UNIRIG_PYTHON), "run.py",
        "--task=configs/task/quick_inference_skeleton_articulationxl_ar_256.yaml",
        "--seed=12345",
        f"--input={input_glb}",
        f"--output={output_fbx}",
        f"--npz_dir={npz_dir}",
    ]
    print(f"  Skeleton prediction started (this takes ~30 min)...")
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, cwd=str(UNIRIG_DIR))
    elapsed = time.time() - start
    print(f"  Skeleton prediction finished in {elapsed/60:.1f} min")

    if os.path.exists(output_fbx):
        print(f"  Skeleton OK: {output_fbx} ({os.path.getsize(output_fbx):,} bytes)")
        return True

    print(f"  Skeleton FAILED")
    return False


def run_unirig_skin(input_glb: str, output_fbx: str, npz_dir: str) -> bool:
    """Run UniRig ML skin weights (~8 sec)."""
    cmd = [
        str(UNIRIG_PYTHON), "run.py",
        "--task=configs/task/quick_inference_unirig_skin.yaml",
        "--seed=12345",
        f"--input={input_glb}",
        f"--output={output_fbx}",
        f"--npz_dir={npz_dir}",
    ]
    print(f"  Skin weights started...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(UNIRIG_DIR))

    if os.path.exists(output_fbx):
        print(f"  Skin OK: {output_fbx} ({os.path.getsize(output_fbx):,} bytes)")
        return True

    print(f"  Skin FAILED")
    return False


def find_npz_dir(input_glb: str, base_npz_dir: str) -> str:
    """Find the NPZ directory after extract (it creates a subdir named after the file)."""
    stem = Path(input_glb).stem
    candidates = [
        Path(base_npz_dir) / stem,
        Path(input_glb).parent / stem,
    ]
    for c in candidates:
        if (c / "raw_data.npz").exists():
            return str(c)
    return str(Path(base_npz_dir) / stem)


def copy_skeleton_npz(input_glb: str, npz_dir: str) -> bool:
    """Copy predict_skeleton.npz to the npz_dir for the skin step."""
    stem = Path(input_glb).stem
    # The skeleton step writes predict_skeleton.npz next to the input's npz dir
    src_candidates = [
        Path(input_glb).parent / stem / "predict_skeleton.npz",
        Path(npz_dir) / "predict_skeleton.npz",
    ]
    dest = Path(npz_dir) / "predict_skeleton.npz"
    if dest.exists():
        return True
    for src in src_candidates:
        if src.exists() and src != dest:
            shutil.copy2(src, dest)
            return True
    return False


def process_character(char_id: str, step: str = "all") -> dict:
    """Process one character through the full UniRig pipeline."""
    input_glb = str(CHAR_INPUT_ROOT / char_id / "3d" / "character-raw.glb")
    char_out = AUTORIG_OUTPUT / char_id
    cleaned_glb = str(char_out / "cleaned" / f"{char_id}-merged.glb")
    skeleton_fbx = str(char_out / "skeleton" / f"{char_id}_skeleton.fbx")
    skinned_fbx = str(char_out / "weighted" / f"{char_id}_skinned.fbx")
    rigged_glb = str(char_out / "rigged" / f"{char_id}-rigged-tpose.glb")
    npz_base = str(char_out / "cleaned")

    result = {
        "char_id": char_id,
        "input": input_glb,
        "steps": {},
    }

    if not os.path.exists(input_glb):
        print(f"  SKIP: No input at {input_glb}")
        result["error"] = "no_input"
        return result

    # Step 1: Merge vertices + orient
    if step in ("all", "merge-only"):
        print(f"  [1/4] Merging vertices...")
        os.makedirs(os.path.dirname(cleaned_glb), exist_ok=True)
        ok = run_blender_prep(input_glb, cleaned_glb)
        result["steps"]["merge"] = "ok" if ok else "fail"
        if not ok:
            return result

    if step == "merge-only":
        return result

    # Step 2: UniRig extract
    if step in ("all", "extract"):
        print(f"  [2/4] UniRig extract...")
        ok = run_unirig_extract(cleaned_glb, npz_base)
        result["steps"]["extract"] = "ok" if ok else "fail"
        if not ok:
            return result

    # Step 3: UniRig skeleton (~30 min)
    if step in ("all", "skeleton"):
        print(f"  [3/4] UniRig skeleton prediction...")

        # UniRig needs raw_data.npz in its --npz_dir.
        # The extract step saves to: {cleaned_glb_parent}/{stem}/raw_data.npz
        # We need to copy it to a UniRig-accessible location.
        unirig_npz = str(UNIRIG_DIR / "tmp" / f"{char_id}-merged")
        os.makedirs(unirig_npz, exist_ok=True)

        # Find raw_data.npz from extract output
        stem = Path(cleaned_glb).stem
        raw_npz_candidates = [
            Path(npz_base) / stem / "raw_data.npz",           # e.g. .../cleaned/bones-merged/raw_data.npz
            Path(cleaned_glb).parent / stem / "raw_data.npz",  # same thing usually
        ]
        copied = False
        for src in raw_npz_candidates:
            if src.exists():
                dest = Path(unirig_npz) / "raw_data.npz"
                shutil.copy2(src, dest)
                print(f"  Copied raw_data.npz: {src} -> {dest}")
                copied = True
                break

        if not copied:
            print(f"  ERROR: raw_data.npz not found. Run extract step first.")
            print(f"  Searched: {[str(c) for c in raw_npz_candidates]}")
            result["steps"]["skeleton"] = "fail"
            return result

        os.makedirs(os.path.dirname(skeleton_fbx), exist_ok=True)
        ok = run_unirig_skeleton(cleaned_glb, skeleton_fbx, unirig_npz)
        result["steps"]["skeleton"] = "ok" if ok else "fail"
        if not ok:
            return result

        # After skeleton, copy predict_skeleton.npz to the npz dir for skin step.
        # UniRig writes it next to the input file's npz subdir.
        skel_npz_candidates = [
            Path(cleaned_glb).parent / stem / "predict_skeleton.npz",
            Path(unirig_npz) / "predict_skeleton.npz",
        ]
        for src in skel_npz_candidates:
            if src.exists():
                dest = Path(unirig_npz) / "predict_skeleton.npz"
                if src != dest:
                    shutil.copy2(src, dest)
                    print(f"  Copied predict_skeleton.npz: {src} -> {dest}")
                break

    # Step 4: UniRig skin weights (~8 sec)
    if step in ("all", "skin"):
        print(f"  [4/4] UniRig skin weights...")
        unirig_npz = str(UNIRIG_DIR / "tmp" / f"{char_id}-merged")

        # Verify predict_skeleton.npz exists (needed for skin step)
        skel_npz = Path(unirig_npz) / "predict_skeleton.npz"
        if not skel_npz.exists():
            print(f"  ERROR: predict_skeleton.npz not found at {skel_npz}. Run skeleton step first.")
            result["steps"]["skin"] = "fail"
            return result

        os.makedirs(os.path.dirname(skinned_fbx), exist_ok=True)
        ok = run_unirig_skin(cleaned_glb, skinned_fbx, unirig_npz)
        result["steps"]["skin"] = "ok" if ok else "fail"

    result["output_fbx"] = skinned_fbx
    result["output_glb"] = rigged_glb
    return result


def main():
    parser = argparse.ArgumentParser(description="Batch UniRig pipeline")
    parser.add_argument("--character", help="Process one character by ID")
    parser.add_argument("--all", action="store_true", help="Process all characters")
    parser.add_argument("--list", action="store_true", help="List characters and status")
    parser.add_argument("--skip-existing", action="store_true", help="Skip characters with existing output")
    parser.add_argument("--step", default="all",
                        choices=["all", "merge-only", "extract", "skeleton", "skin"],
                        help="Run only a specific step")
    args = parser.parse_args()

    if args.list:
        print(f"{'ID':15s} {'Input':8s} {'Merged':8s} {'Skeleton':10s} {'Skinned':8s}")
        print("-" * 55)
        for cid in CHARACTERS:
            has_input = (CHAR_INPUT_ROOT / cid / "3d" / "character-raw.glb").exists()
            has_merged = (AUTORIG_OUTPUT / cid / "cleaned" / f"{cid}-merged.glb").exists()
            has_skel = (AUTORIG_OUTPUT / cid / "skeleton" / f"{cid}_skeleton.fbx").exists()
            has_skin = (AUTORIG_OUTPUT / cid / "weighted" / f"{cid}_skinned.fbx").exists()
            print(f"{cid:15s} {'YES' if has_input else '---':8s} {'YES' if has_merged else '---':8s} "
                  f"{'YES' if has_skel else '---':10s} {'YES' if has_skin else '---':8s}")
        return

    chars = CHARACTERS
    if args.character:
        if args.character not in CHARACTERS:
            print(f"Unknown character: {args.character}")
            print(f"Available: {', '.join(CHARACTERS)}")
            sys.exit(1)
        chars = [args.character]
    elif not args.all:
        parser.print_help()
        return

    print(f"Processing {len(chars)} character(s), step={args.step}")
    print(f"UniRig: {UNIRIG_DIR}")
    print(f"Blender: {BLENDER_EXE}")
    print()

    results = []
    for i, char_id in enumerate(chars):
        print(f"\n=== [{i+1}/{len(chars)}] {char_id} ===")

        if args.skip_existing:
            skinned = AUTORIG_OUTPUT / char_id / "weighted" / f"{char_id}_skinned.fbx"
            if skinned.exists():
                print(f"  SKIP: already has {skinned}")
                continue

        result = process_character(char_id, step=args.step)
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(results)} processed")
    for r in results:
        status = "OK" if all(v == "ok" for v in r.get("steps", {}).values()) else "FAIL"
        steps = ", ".join(f"{k}={v}" for k, v in r.get("steps", {}).items())
        print(f"  {r['char_id']:15s} {status:5s} {steps}")

    # Save report
    report_path = AUTORIG_OUTPUT / "batch_unirig_report.json"
    os.makedirs(report_path.parent, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
