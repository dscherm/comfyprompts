# Character — Requirements

## Overview

Character-ralph generates consistent character art across multiple views and formats, then converts to rigged, animated 3D models. It bridges 2D concept art and 3D game assets, ensuring visual consistency from portrait through multi-view sheet through final rigged model.

## Target State

Given a character description and style directive, the pipeline delivers a complete character package: portrait, full-body reference, multi-view orthographic sheet, clean 3D mesh, rigged skeleton with animations, and a packaged delivery bundle with manifest.

## Acceptance Criteria

1. Portrait is generated at minimum 1024x1024 with the character clearly recognizable and matching the description
2. Full-body reference matches the portrait's art style, color palette, and character features with high visual consistency
3. Multi-view sheet contains at minimum front, side, and back views with consistent proportions and details across all views
4. 3D mesh is generated from the multi-view references and is manifold with zero non-manifold edges
5. Mesh face count is in the target range for characters (5k-50k faces)
6. Auto-rig produces a humanoid skeleton with standard bone hierarchy (root -> hips -> spine -> head, arms, legs)
7. All vertices are weighted to at least one bone with normalized weights
8. At least idle and walk animation clips are attached and play without mesh deformation artifacts
9. Character identity is visually consistent across all outputs (portrait, fullbody, 3D model match the same character)
10. Final package includes GLB with embedded textures, standalone texture PNGs, and a CHARACTER-MANIFEST.md
11. CHARACTER-MANIFEST.md documents: character name, description, style, checkpoint used, face count, bone count, animation list
12. Pipeline completes within max_iterations without manual intervention
13. Each stage gate passes before artifacts advance to the next stage
