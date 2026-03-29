# AutoRig Ralph -- Requirements

## Overview

AutoRig Ralph is an ML-powered auto-rigging pipeline that takes unrigged 3D meshes (GLB/FBX/OBJ) and produces fully rigged, game-ready models with accurate skeleton placement, refined skin weights, hard-surface attachment, and skeleton adjustments. It operates like Reallusion AccuRig, UniRig, and Mixamo -- but locally, using the full tool stack (UniRig ML, blender-mcp, coplay-mcp Meshy, and Blender Rigify).

## Current State (Pre-Work)

- UniRig is installed at C:/UniRig but requires manual CLI invocation
- blender-mcp provides interactive Blender control but no unified rigging pipeline
- coplay-mcp has Meshy cloud rigging but no local fallback orchestration
- Skin weight refinement is manual (no automated pipeline)
- Hard-surface attachment (armor, weapons, accessories) is fully manual
- No automated skeleton adjustment or IK setup pipeline
- No unified quality gates for rig validation across tools

## Target State

A single pipeline that accepts any unrigged mesh and produces:
1. ML-predicted skeleton with correct bone hierarchy and placement
2. Refined skin weights with >95% vertex coverage and smooth deformation
3. Hard-surface items (armor, weapons, accessories) correctly parented/constrained to skeleton
4. Skeleton adjustments (proportions, IK chains, twist bones) tuned for target platform
5. Multi-platform export (Blender GLB, Unity FBX, Unreal FBX)

## Acceptance Criteria

1. Pipeline accepts GLB, FBX, or OBJ input meshes (single or batch)
2. Body type auto-detection classifies mesh as humanoid/quadruped/creature/mech with >90% accuracy
3. UniRig skeleton prediction runs successfully for humanoid and creature meshes
4. Fallback to Rigify (blender-mcp) or Meshy (coplay-mcp) when UniRig fails
5. Skin weight coverage >95% for all rigged meshes (no floating vertices)
6. Weight smoothing eliminates sharp deformation artifacts at joints
7. Hard-surface items detected and attached via bone parenting or Copy Transform constraints
8. IK chains generated for arms and legs with correct pole targets
9. Twist bones added for forearms and upper arms (optional, platform-dependent)
10. Final rig passes deformation test: 5 key poses without mesh collapse or >2cm penetration
11. Export produces valid GLB (Blender names), FBX (Unity Mecanim), and FBX (Unreal) variants
12. Full pipeline completes in <10 minutes per mesh on RTX 3070 8GB
13. Pipeline state tracked in output/pipeline-state.json with per-asset progress
14. Each stage has PASS/WARN/FAIL gate with automated validation
