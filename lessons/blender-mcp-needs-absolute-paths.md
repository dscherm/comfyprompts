---
title: blender-mcp import fails on relative paths with an opaque "Please select a file"
severity: low
tags: [blender, blender-mcp, paths, rendering, gotcha]
source: hand-authored
created: 2026-07-17
project: comfyui-toolchain
---

## Symptom

Rendering a mesh through blender-mcp (render_multiview.py) with a repo-relative
`--src` path failed per mesh with:

    Code execution error: Error: Please select a file

The same command with an **absolute** path to the identical file rendered all
views fine. The error text does not mention paths, so it reads like a UI/selection
bug rather than a bad filepath.

## Root cause

blender-mcp runs code inside the Blender process, whose working directory is
**not** the repo (it's wherever Blender launched from). A relative path handed to
`bpy.ops.import_scene.gltf(filepath=...)` resolves against Blender's CWD, finds
nothing, and the glTF importer reports its generic "Please select a file". The
socket layer doesn't rewrite paths, so relative paths silently point elsewhere.

## Mitigation

1. **Always pass absolute paths to blender-mcp** for any file the Blender side
   opens (mesh import, texture load, render output). Resolve with
   `Path(p).resolve()` (or absolute constants) before sending.
2. If a tool takes `--src`, feed it an absolute path — or have the tool
   `.resolve()` inputs itself. (Staging meshes into an absolute working dir, as
   build_lowpoly_flat_dataset.py does, sidesteps this entirely.)
3. Read "Please select a file" from blender-mcp as **"the path didn't resolve"**,
   not a selection/UI problem — check absoluteness first.
