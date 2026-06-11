# Fusion — Requirements

## Overview

Fusion-ralph generates 3D printer-ready models with interlocking multi-part assemblies suitable for Fusion 360 and FDM/SLA printing. It takes a concept through mesh generation, geometry validation, printability preparation, multi-part decomposition, and final STL export.

## Target State

Given a text or image description, the pipeline delivers a complete set of print-ready STL files: each part is watertight, has proper wall thickness, fits within the declared build volume, and interlocks with adjacent parts using tolerance-correct joints. A BUILD-MANIFEST.md documents all parts with recommended print settings.

## Acceptance Criteria

1. All STL files are watertight with zero non-manifold edges
2. All parts fit within the declared build volume (default 220x220x250mm for standard FDM)
3. Minimum wall thickness is enforced (>= 1.2mm for FDM, >= 0.4mm for SLA)
4. Assembly has alignment features (pins/holes) with correct tolerances (0.2mm clearance for FDM, 0.1mm for SLA)
5. Each part can be printed without supports or with minimal auto-generated supports
6. No overhangs exceed 60 degrees from vertical without support structures
7. All parts have flat bottom surfaces suitable for bed adhesion
8. Combined assembly GLB exists showing all parts in their assembled positions
9. Each individual part has both GLB and STL exports
10. BUILD-MANIFEST.md documents each part: name, dimensions, face count, recommended layer height, infill percentage, and print time estimate
11. Mesh decimation keeps face count under 500k per part while preserving detail
12. No degenerate triangles (zero-area faces) in any exported mesh
13. Pipeline completes within max_iterations (50) without manual intervention
14. Each stage gate passes before artifacts advance to the next stage
