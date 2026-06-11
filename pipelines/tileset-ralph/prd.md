# Tileset — Requirements

## Overview

Tileset-ralph generates complete, game-ready tilesets from a terrain specification. It produces seamless base tiles, transition blends between terrain types, validated texture atlases, and export packages suitable for Godot, Unity, RPG Maker, and other game engines.

## Target State

Given a tileset specification (terrain types, tile size, style), the pipeline delivers a power-of-2 texture atlas containing all base tiles and transition tiles, with seamless tiling validated at pixel level, plus metadata JSON for engine integration and optional 3D tile variants.

## Acceptance Criteria

1. All base terrain tiles are generated at the specified tile size (default 64x64) with consistent art style
2. Every terrain type in the specification has a corresponding base tile (zero missing types)
3. Transition tiles are generated for all required terrain-pair combinations
4. All tiles are seamlessly tileable: edge pixels match within a tolerance of 5 RGB units when placed adjacent
5. No visible seams when tiles are rendered in a test grid layout
6. Color palette is consistent across all tiles in the set -- no terrain type has a drastically different color temperature
7. Texture atlas is packed to the smallest power-of-2 dimensions that fit all tiles
8. Atlas metadata JSON maps each tile to its (x, y, width, height) region in the atlas
9. Atlas metadata includes terrain type labels and transition pair identifiers for each tile
10. No duplicate tiles in the atlas (each tile is unique)
11. Export package includes: atlas PNG, metadata JSON, and optionally individual tile PNGs
12. If 3D tile variants are requested, each tile has a corresponding mesh with correct UV mapping to the atlas
13. TILESET-MANIFEST.md documents: terrain types, tile count, atlas dimensions, style settings, and engine compatibility notes
14. Pipeline completes within max_iterations (25) without manual intervention
