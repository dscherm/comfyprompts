# photo-to-3d

Turn a single photo (or a coordinated multi-view set) of a real
object/creature/person into a clean, workable 3D mesh: **GLB / OBJ / STL**,
with an optional guaranteed-watertight pass for 3D printing.

Proven end-to-end on the dog run (2026-07-11). Driven by the **`photo-to-3d`
skill** (`.claude/skills/photo-to-3d/SKILL.md`) — that's the orchestration and
the gotchas; this README is the code reference.

## Flow

```
photo (cutout PNG, alpha)
      │
      ▼  ComfyUI TRELLIS.2  —  pipelines/art-to-rig-ralph/scripts/trellis_queue.py
   raw mesh .glb   (LOOKS solid, is actually 20k+ unwelded fragments)
      │
      ▼  Blender headless  —  scripts/mesh_to_solid.py
   weld → fill holes → drop floaters → [voxel remesh] → smooth → export
      │
      ▼
   dog.glb  dog.obj  dog.stl   (+ clay renders, + json report)
```

## `scripts/mesh_to_solid.py`

The reusable cleanup. The one thing that matters: **weld before smooth.**
TRELLIS's Cumesh simplifier emits coincident-but-separate vertices; smoothing a
raw export pulls the duplicates apart into visible surface cracks. This script
merges-by-distance first, then everything else is safe.

```
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" --background \
  --python scripts/mesh_to_solid.py -- \
  --input raw.glb --output-dir out --name dog --formats glb,obj,stl --render
```

Key flags:

| Flag | Purpose |
|------|---------|
| `--weld-dist 0.001` | merge-by-distance threshold (mesh normalized ~1u) |
| `--smooth-iters 10 --smooth-factor 0.5` | surface relax after welding |
| `--min-part-faces 100` | drop disconnected specks smaller than this |
| `--watertight` | keep only the largest shell + close holes (best-effort) |
| `--voxel-remesh 0.004` | **guarantee** a watertight manifold (resamples topology; for printing) |
| `--longest-mm 120` | scale the **STL** so its longest axis = 120 mm (STL wants mm) |
| `--keep-textures` | keep material/vertex color instead of stripping to geometry |
| `--render` | write `<name>_clay_*.png` turntable (pure geometry) |
| `--report out/x.json` | before/after verts·faces·boundary·watertight·bbox |

Output modes:
- **General 3D file** (default): high-poly, cracks removed, a few tiny holes ok.
- **Printing**: add `--voxel-remesh 0.004 --longest-mm <mm>` → `watertight=True`,
  clean uniform topology, correct real-world STL scale.

## `trellis_queue.py` (shared, in art-to-rig-ralph)

Runs a ComfyUI-Trellis2 example workflow via the API. For this pipeline:
- `--workflow MeshOnly` — geometry only (fast; recommended when color isn't needed)
- `--workflow MeshWithTexturing` — single-view geometry + texture
- `--workflow MeshOnly_MultiView --front f --back b` — only for the SAME pose
  shot front and back (mismatched poses cannot be fused)

## Known ceilings

- A single view invents the far side. Geometry is plausible; **texture** on the
  unseen side comes out as fragmented-atlas "crackle" and is not fixable in post.
  Want it right all around → more photos of the subject, or geometry-only.
- Hunyuan3D's wrapper node is often unloaded in the running ComfyUI; TRELLIS.2 is
  the reliable generator here.
