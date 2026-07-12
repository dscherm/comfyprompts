---
name: photo-to-3d
description: Turn a single photo (or a few) of a real object/creature/person into a clean, workable 3D mesh file (GLB/OBJ/STL) — TRELLIS.2 image-to-3D geometry → weld/heal/smooth to a continuous solid → export, with an optional guaranteed-watertight pass for 3D printing. Use when the user hands you a photo and wants "a 3d file", "turn this into 3D", "printable model", "mesh from this image". Proven on the dog run, 2026-07-11. Runs in D:\Projects\comfyui-toolchain.
---

# Photo → 3D (proven on the dog run, 2026-07-11)

Takes one photo (ideally a **background-removed cutout PNG with alpha**) to a
clean, continuous 3D mesh in GLB / OBJ / STL. The generator invents any surface
it can't see, so **coverage of the subject is the quality ceiling** — set
expectations up front (see Traps).

Two scripts do the work:
- **TRELLIS geometry** — `pipelines/art-to-rig-ralph/scripts/trellis_queue.py`
  (runs a ComfyUI-Trellis2 example workflow via the API; urllib-only).
- **Cleanup → solid** — `pipelines/photo-to-3d/scripts/mesh_to_solid.py`
  (Blender headless: weld → fill → drop floaters → smooth → export; the
  weld-before-smooth order is the whole ballgame).

Blender = `"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"`.
ComfyUI venv py = `"D:/Projects/ComfyUI/venv/Scripts/python.exe"` (urllib scripts
run on any 3.10+, but the venv py is always safe).

## Decide two things with the user first
1. **Color/texture, or geometry only?** Geometry-only is faster and avoids the
   texture-seam problem entirely — pick `MeshOnly` and strip materials. Only go
   textured (`MeshWithTexturing`) if they want color AND accept that a single
   view textures the far side poorly (fragmented-atlas crackle; not fixable in
   post — see Traps).
2. **What's it for?** General viewing/game → default high-poly clean solid.
   3D printing → add `--voxel-remesh` (guaranteed watertight) + `--longest-mm`.

## Phase 0 — Preflight
- ComfyUI up on the 3090 Ti venv: `curl -s http://localhost:8188/system_stats`
  (if down: `D:/Projects/ComfyUI/run_3090ti.ps1`).
- Stage the image in `D:/Projects/ComfyUI/input/` (e.g. `subject.png`). A clean
  alpha cutout is best; a plain photo also works (`remove_background` runs in
  preprocess). `Trellis2LoadImageWithTransparency` reads the alpha.
- **Prefer TRELLIS, not Hunyuan3D**: the Hunyuan3D *wrapper* node
  (`Hy3DModelLoader`) is frequently NOT loaded in the running ComfyUI — its
  workflows error `node ... does not exist`. TRELLIS.2 is reliably present.

## Phase 1 — Geometry (TRELLIS.2, GPU ~1–3 min, single view)
```
"D:/Projects/ComfyUI/venv/Scripts/python.exe" \
  pipelines/art-to-rig-ralph/scripts/trellis_queue.py \
  --workflow MeshOnly --front subject.png --prefix <name> --seed 42
```
- Textured instead: `--workflow MeshWithTexturing` (outputs `<name>_*.glb`, the
  larger file is the textured one).
- True multi-view (only if you have the SAME pose from front AND back):
  `--workflow MeshOnly_MultiView --front f.png --back b.png`. Do NOT feed
  mismatched poses (a standing shot + a curled shot) — it produces a mangled
  mesh; different poses cannot be fused.
**Gate**: script prints `STATUS success` and `OUTPUT <glb>`. TRELLIS blocks
ComfyUI's HTTP server while "Reconstructing mesh" — that is NORMAL, the job is
fine; never kill it (memory `project_trellis_reconstruction_blocks_server`).

## Phase 2 — Clean to a workable solid (Blender headless, ~1 min)
```
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" --background \
  --python pipelines/photo-to-3d/scripts/mesh_to_solid.py -- \
  --input <phase1.glb> --output-dir <out> --name <name> \
  --formats glb,obj,stl --render --report <out>/<name>_report.json
```
Add for **printing**: `--voxel-remesh 0.004 --longest-mm <mm>` (guarantees
`watertight=True`; `--longest-mm` bakes real-world size into the STL — STL must
be mm, memory `feedback_stl_units`).
Keep color: `--keep-textures` (only meaningful if Phase 1 was textured).

**Gate** (read the report / stdout):
- `BEFORE` boundary is usually huge (100k–250k) — that's the unwelded triangle
  soup, expected.
- `WELDED` must drop verts ~40–50% and boundary by ~99%. If it doesn't, the
  mesh wasn't unwelded (fine) or `--weld-dist` is too small.
- `FINAL watertight=True` only with `--voxel-remesh`; default mode leaves a few
  small holes (fine for viewing/games, not for printing).
- Always show the user the `_clay_*.png` renders (pure geometry, no texture) —
  the surface must read as one continuous piece with NO etched crack-lines. If
  you see cracks, the weld didn't take.

## Phase 3 — Deliver
Hand over the files in `<out>/` and state: poly count, watertight or not, and
scale (normalized ~1u unless `--longest-mm` was set). Delete any earlier
pre-weld exports so the user can't grab the broken version.

## Traps (each one cost real time on the dog run — read before improvising)
- **TRELLIS meshes ship UNWELDED** (coincident duplicate verts, 20k+ fragments).
  They render fine flat but crack the instant you smooth them. `mesh_to_solid.py`
  welds FIRST, then smooths — never smooth a raw TRELLIS export. Memory
  `project_trellis_unwelded_mesh_weld_before_smooth`.
- **Single view = hard quality ceiling.** The far/occluded side is invented. For
  TEXTURE this shows as dark seam "crackle" that is NOT fixable by 2D atlas heal,
  vertex-color baking, more `max_views`, or any post-process — it's missing data,
  not a cleanup problem. Don't burn cycles chasing it; either get more photos of
  the subject (same pose, other angles) or go geometry-only.
- **Hunyuan3D wrapper often unloaded** — `Hy3DModelLoader does not exist`. Use
  TRELLIS.2; don't restart ComfyUI hunting for Hunyuan unless the user insists.
- **flash_attn not installed** — TRELLIS backends must be sdpa/xformers
  (`trellis_queue.py` forces this).
- **`--watertight` alone is best-effort** (largest shell + hole fill); it leaves
  a few edges on complex holes. Use `--voxel-remesh` for a guaranteed manifold —
  it resamples topology (softens fine detail) but is the correct printing path.
- **STL scale**: normalized mesh is ~1 unit; always pass `--longest-mm` for a
  printable STL (memory `feedback_stl_units`).
