# Quality Gate 5: RIG

## PASS Criteria (ALL must pass)
- [ ] `output/rigged/character-rigged.glb` exists and is >100KB
- [ ] `output/rigged/character-rigged-split.glb` exists (kart-assembly contract)
- [ ] Rigged GLB contains an armature/skeleton (bone data present)
- [ ] Bone count is within range: 20 - 100 bones
- [ ] Skeleton follows humanoid hierarchy (root > spine > limbs)
- [ ] autorig-ralph Stage 7 validation score >= 80 (if quality report available)
- [ ] gate-05-alignment-result.json shows PASS or WARN
- [ ] gate-05b-deformation-result.json shows PASS or WARN

## WARN Criteria (log but don't block)
- [ ] Bone count below 30 (simplified rig)
- [ ] Bone naming is non-standard (may cause retargeting issues)
- [ ] Left/right symmetry is imperfect
- [ ] autorig-ralph used fallback tool (not UniRig primary)
- [ ] Some vertices have zero weight (small number)
- [ ] Missing rig-report.json

## FAIL Criteria (block advancement)
- [ ] No rigged GLB file generated
- [ ] Rigged GLB has no skeleton/armature data
- [ ] Bone count is 0 or >500
- [ ] Mesh is severely broken in rigged pose
- [ ] Skeleton has no hierarchy (all bones at root level)
- [ ] gate-05-alignment FAIL
- [ ] gate-05b-deformation FAIL

## Validation Method

### Rig validation via Blender
```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python - <<'PYTHON' -- RIGGED_GLB
import bpy, sys, json

argv = sys.argv[sys.argv.index("--") + 1:]
rigged_glb = argv[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=rigged_glb)

report = {"has_armature": False, "bone_count": 0, "bones": [], "meshes": []}

for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        report["has_armature"] = True
        report["bone_count"] = len(obj.data.bones)
        for bone in obj.data.bones:
            report["bones"].append({
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else None
            })
    elif obj.type == 'MESH':
        report["meshes"].append({
            "name": obj.name,
            "vertices": len(obj.data.vertices),
            "vertex_groups": len(obj.vertex_groups)
        })

print(json.dumps(report, indent=2))
PYTHON
```

### Gate Result Format
Write to `output/gate-05-result.json`:
```json
{
  "stage": "5-rig",
  "result": "PASS|WARN|FAIL",
  "checks": [
    { "name": "rigged_file_exists", "passed": true, "detail": "character-rigged.glb exists, 5.1MB" },
    { "name": "split_file_exists", "passed": true, "detail": "character-rigged-split.glb exists" },
    { "name": "has_armature", "passed": true, "detail": "Armature found" },
    { "name": "bone_count", "passed": true, "detail": "52 bones (range: 20-100)" },
    { "name": "hierarchy_valid", "passed": true, "detail": "Standard humanoid chain" },
    { "name": "alignment_gate", "passed": true, "detail": "gate-05-alignment PASS" },
    { "name": "deformation_gate", "passed": true, "detail": "gate-05b-deformation PASS" }
  ],
  "warnings": [],
  "blocking_errors": [],
  "recommendation": "Proceed to animation (Stage 6)"
}
```
