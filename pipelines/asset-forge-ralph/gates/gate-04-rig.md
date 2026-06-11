# Quality Gate 4: AUTO-RIG

## Stage Skipped Handling
If `stages.4-rig.status` is `"skipped"` (prop or vehicle without articulation), this gate automatically passes. Verify that `output/rigged/rigged-model.glb` exists (should be a copy of the cleaned mesh).

## PASS Criteria (ALL must pass for rigged assets)
- [ ] `output/rigged/rigged-model.glb` exists and is >10KB
- [ ] GLB contains an armature (skeleton) with at least 10 bones
- [ ] All bones have names (no empty-string bone names)
- [ ] Bone hierarchy has a single root bone
- [ ] Weight paint coverage is >90% (at least 90% of vertices are assigned to a bone with weight >0.01)
- [ ] Vertex weights are normalized (sum to ~1.0 per vertex, tolerance 0.01)
- [ ] Mesh geometry is intact (vertex/face count matches Stage 3 output within 1%)

## WARN Criteria (log but don't block)
- [ ] Bone count is <15 (minimal skeleton -- animations may look stiff)
- [ ] Bone count is >100 (complex skeleton -- may hit performance limits on mobile)
- [ ] Weight coverage is between 90-95% (some vertices unweighted -- may cause mesh artifacts)
- [ ] Bone names do not follow standard naming convention (Mixamo, UE4 Mannequin, etc.)
- [ ] Some bones have zero-length (collapsed bones -- usually cosmetic issue)
- [ ] Armature has multiple root bones (some engines handle this poorly)

## FAIL Criteria (block advancement -- re-run Stage 4)
- [ ] No rigged GLB file generated
- [ ] GLB has no armature data (rigging tool failed silently)
- [ ] Bone count is 0 or 1 (skeleton not actually created)
- [ ] Weight coverage is <50% (most vertices float freely -- mesh will collapse during animation)
- [ ] Mesh vertex count changed by >5% from Stage 3 (rigging tool corrupted geometry)
- [ ] Rigging tool returned an explicit error
- [ ] All weights are uniform (every vertex has identical weights -- no meaningful deformation)

## Validation Method

### Blender headless rig inspection
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- RIGGED_GLB
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=glb_path)

# Find armature
armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
if not armatures:
    print("FAIL: No armature found")
    sys.exit(1)

armature = armatures[0]
bone_count = len(armature.data.bones)
bone_names = [b.name for b in armature.data.bones]
root_bones = [b for b in armature.data.bones if b.parent is None]

print(f"Bone count: {bone_count}")
print(f"Root bones: {len(root_bones)} ({', '.join(b.name for b in root_bones)})")
print(f"Bone names: {bone_names}")

# Check weight coverage on mesh objects
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    total_verts = len(obj.data.vertices)
    weighted_verts = 0
    for v in obj.data.vertices:
        if any(g.weight > 0.01 for g in v.groups):
            weighted_verts += 1
    coverage = (weighted_verts / total_verts * 100) if total_verts > 0 else 0
    print(f"{obj.name}: {weighted_verts}/{total_verts} vertices weighted ({coverage:.1f}%)")
PYTHON
```

### Expected skeleton structure by asset type

**Character (humanoid):**
Minimum 19 bones: Hips, Spine, Spine1, Spine2, Neck, Head, Left/Right Shoulder, UpperArm, LowerArm, Hand, UpperLeg, LowerLeg, Foot.

**Creature:**
Variable. At minimum: Root, Spine chain (3+), Head, and limb chains matching visible limbs.

## Gate Result Output

Write to `output/gate-04-result.json`:
```json
{
  "stage": "4-rig",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "file_exists", "passed": true, "detail": "rigged-model.glb exists, 7.8MB" },
    { "name": "armature_exists", "passed": true, "detail": "Armature found with 32 bones" },
    { "name": "single_root", "passed": true, "detail": "Single root bone: Hips" },
    { "name": "bone_count", "passed": true, "detail": "32 bones (>10 minimum)" },
    { "name": "weight_coverage", "passed": true, "detail": "97.3% vertices weighted (>90% threshold)" },
    { "name": "weights_normalized", "passed": true, "detail": "All vertex weights sum to ~1.0" },
    { "name": "geometry_intact", "passed": true, "detail": "48200 faces (matches Stage 3)" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Skeleton looks good -- proceed to animation"
}
```
