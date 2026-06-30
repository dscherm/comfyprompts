# godot_verify — Godot import-verify + showcase template

A reusable Godot 4.6 project that proves an exported GrimForge kit imports and
renders in-engine, and produces a showcase scene/screenshot. `build.gd`
auto-discovers every GLB under `models/`, lays them on an adaptive grid, and
applies a named **aesthetic profile** (`medieval` | `occult`) whose lighting
mirrors `kit_pipeline.py`'s catalog `PROFILES`.

## Usage

```bash
# 1. copy the template to a working dir
cp -r godot_verify /tmp/verify

# 2. drop the kit's GLBs in (from kit_pipeline output)
cp <out_dir>/glb/*.glb /tmp/verify/models/

# 3. pick the aesthetic (optional; defaults to medieval)
echo occult > /tmp/verify/aesthetic.txt

GODOT=/path/to/Godot_v4.6_console.exe
# 4. import, build the showcase scene, render a screenshot
"$GODOT" --headless --path /tmp/verify --import
"$GODOT" --headless --path /tmp/verify res://build.tscn       # writes village.tscn
"$GODOT" --path /tmp/verify --resolution 1280x900 res://capture.tscn  # writes verify_shot.png
```

`build.tscn` (runs `build.gd`) regenerates `village.tscn`; `capture.tscn`
(runs `capture.gd`) renders `verify_shot.png` with the scene camera.

## Notes
- glTF import is **Y-up**: a piece built Z-up in Blender ends up upright along
  Godot's +Y, and its Blender `-Y` "front" becomes Godot `+Z`.
- Only ever run **one** Godot process against a project at a time — a second
  process (e.g. an open editor) holds a lock and headless runs will hang.
- `.godot/`, `*.import`, `*.uid`, `verify_shot.png`, and generated `village.tscn`
  are build artifacts, not committed.
