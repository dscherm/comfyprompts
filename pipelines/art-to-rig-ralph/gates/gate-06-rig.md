# Quality Gate 6: RIG

## PASS Criteria (ALL must pass)
- [ ] Rigged GLB exists for each variation in `output/rigged/`
- [ ] Armature object exists in the GLB with >5 bones
- [ ] Bone count is within the expected range for the skeleton type
- [ ] Root bone exists and is the parent of the entire hierarchy
- [ ] Bone hierarchy matches the expected structure for the skeleton type
- [ ] Weight paint coverage >90% (fewer than 10% of vertices are unweighted)
- [ ] Mesh is still parented to the armature (relationship intact)
- [ ] Rig report JSON exists for each variation
- [ ] autorig-ralph quality report exists with validation score >= 80 (if autorig-ralph was used)

## WARN Criteria (log but don't block)
- [ ] Weight paint coverage between 85-90% (minor gaps, may cause slight mesh tearing)
- [ ] Bone count slightly outside expected range (within 20% tolerance)
- [ ] Some weight paint bleed detected between adjacent bones (may cause slight deformation artifacts)
- [ ] Fallback rigging tool was used instead of primary (UniRig)
- [ ] Some finger/toe bones missing (simplified rig -- still functional for body animation)
- [ ] Tail or accessory bones missing (non-critical for core animation)
- [ ] autorig-ralph used a fallback rigging tool instead of primary (UniRig)
- [ ] autorig-ralph quality score between 60-80 (marginal)

## FAIL Criteria (block -- re-run Stage 6 or go back to Stage 5)
- [ ] No armature in the output GLB
- [ ] Fewer than 5 bones total (skeleton is trivial/broken)
- [ ] No root bone (disconnected bone hierarchy)
- [ ] Weight paint coverage <70% (will cause severe mesh tearing)
- [ ] Wrong skeleton type applied (e.g., biped on a quadruped mesh)
- [ ] Mesh is no longer connected to armature (parenting broken)
- [ ] Rigging tool crashed completely (check error logs)
- [ ] GLB file is corrupt after rigging

## Skeleton Type Validation

### biped_rigify
- Must have: spine chain (3+ bones), head, both arms (3 bones each), both legs (3 bones each)
- Minimum bones: 15 (simplified) to 80 (full Rigify)
- Root must be spine/hips

### quadruped_spine
- Must have: spine chain (4+ bones), head, 4 leg chains (3 bones each)
- Minimum bones: 20
- Root must be spine/pelvis

### dragon
- Must have: everything in quadruped_spine PLUS wing chains (3+ bones each side)
- Minimum bones: 30
- Wing bones must be children of upper spine

### spine_chain
- Must have: continuous spine chain (20+ bones), head at one end
- Minimum bones: 20
- All bones in a single chain (no branching except optional head/tail)

### multi_leg
- Must have: body chain (3+ bones), 6-8 leg chains (3+ bones each)
- Minimum bones: 25
- Legs must be children of body bones

### rigid_hierarchy
- Must have: root bone, child bones at each articulation point
- Minimum bones: 5
- No smooth skinning required (rigid binding acceptable)

## Validation Method
```bash
# Validate rig
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python -c "
import bpy, json, sys

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=sys.argv[-1])

armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
meshes = [o for o in bpy.data.objects if o.type == 'MESH']

if not armatures:
    print('FAIL: no armature found')
    sys.exit(1)

arm = armatures[0]
bone_count = len(arm.data.bones)
root_bones = [b for b in arm.data.bones if b.parent is None]

# Check weight coverage
if meshes:
    mesh = meshes[0]
    total_verts = len(mesh.data.vertices)
    unweighted = sum(1 for v in mesh.data.vertices if len(v.groups) == 0)
    coverage = 1.0 - (unweighted / total_verts) if total_verts > 0 else 0

result = {
    'bone_count': bone_count,
    'root_bones': [b.name for b in root_bones],
    'has_root': len(root_bones) >= 1,
    'weight_coverage': round(coverage, 3) if meshes else 'N/A',
    'mesh_parented': meshes[0].parent == arm if meshes else False,
}
print(json.dumps(result, indent=2))

if bone_count < 5:
    print('FAIL: too few bones')
    sys.exit(1)
elif coverage < 0.70:
    print(f'FAIL: weight coverage too low ({coverage:.1%})')
    sys.exit(1)
elif coverage < 0.90:
    print(f'WARN: weight coverage below target ({coverage:.1%})')
else:
    print('PASS')
" -- pipelines/art-to-rig-ralph/output/rigged/{asset-id}_v1_rigged_blender.glb
```
