# Asset Forge — Requirements

## Overview

Asset-forge-ralph transforms text descriptions into fully rigged, animated, game-ready 3D models. It is the highest-value pipeline in the toolchain, producing export-ready GLB/FBX/STL files with skeletons and animations suitable for real-time engines (Unity, Unreal, Godot) and 3D printing.

## Target State

Given any text description of a character, creature, or prop, the pipeline delivers a complete asset package: high-quality reference art, a clean manifold mesh, a properly weighted skeleton, at least one animation clip, and multi-format exports with a manifest documenting the full provenance chain.

## Acceptance Criteria

1. Reference image is generated at minimum 1024x1024 resolution and accurately reflects the text description
2. Generated 3D mesh is manifold with zero non-manifold edges
3. Mesh face count is within the target range for the asset type (characters: 5k-50k, props: 1k-20k)
4. Mesh bounding box dimensions are non-zero and within sane limits (no axis > 5m for game assets)
5. Rig has a proper bone hierarchy with root bone at origin (root -> spine -> limbs for humanoids)
6. All bone weights are normalized (sum to 1.0 per vertex, no unweighted vertices)
7. At least one animation clip (idle) is attached and plays without mesh distortion
8. Final GLB export is loadable in a standard glTF viewer without errors
9. Final FBX export is loadable in Blender without import errors
10. Final STL export is watertight and suitable for slicing
11. An ASSET-MANIFEST.md documents: source prompt, model checkpoint used, face count, bone count, animation list, and file sizes
12. All intermediate artifacts (concept images, raw meshes) are preserved in stage-specific output directories
13. Pipeline completes within max_iterations (30) without manual intervention
14. Each stage gate passes before artifacts advance to the next stage
