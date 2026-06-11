# Quality Gate 5: MESH PREPARATION

## PASS Criteria (ALL must pass)
- [ ] Prepared GLB exists for each variation in `output/prepared/`
- [ ] Each mesh is manifold (0 non-manifold edges) -- **hard requirement**
- [ ] All normals are consistent (outward-facing)
- [ ] Zero degenerate faces (zero-area triangles)
- [ ] Face count is within 10,000-80,000 range
- [ ] Model is scaled to correct real-world dimensions for its body type
- [ ] Model is centered with bottom at Z=0 (grounded)
- [ ] All transforms applied (no residual scale/rotation/location on the object)
- [ ] Prep report JSON exists for each variation with operation log

## WARN Criteria (log but don't block)
- [ ] Decimation reduced face count by >60% (may have lost fine detail on fingers, face)
- [ ] Floating geometry was removed (some detail may be lost)
- [ ] Remove doubles merged >500 vertices (mesh had significant overlap)
- [ ] Face count is below 20,000 (rigging may be coarse, but functional)
- [ ] Some thin regions remain that may deform poorly during animation
- [ ] Scale factor was very large (>10x) or very small (<0.1x), indicating unusual source mesh scale

## FAIL Criteria (block -- re-run Stage 5 with different parameters)
- [ ] Mesh is still non-manifold after repair attempts
- [ ] Normals still inconsistent after recalculation
- [ ] Mesh collapsed during decimation (face count dropped to <1,000)
- [ ] Mesh has negative or zero volume after repair (inside-out)
- [ ] Blender prep script crashed (check error logs)
- [ ] Prepared GLB is smaller than raw GLB by >90% (data loss)
- [ ] Bounding box has a zero-length axis (mesh is flat/degenerate)

## Validation Method
```bash
# Validate prepared meshes
python packages/mcp-server/scripts/validate_glb.py pipelines/art-to-rig-ralph/output/prepared/{asset-id}_v1_prepared.glb

# Blender manifold check
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python -c "
import bpy, bmesh, sys, json

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=sys.argv[-1])
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(obj.data)

non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
degenerate = sum(1 for f in bm.faces if f.calc_area() < 0.0000001)
face_count = len(bm.faces)
vert_count = len(bm.verts)

bpy.ops.object.mode_set(mode='OBJECT')
dims = obj.dimensions

result = {
    'non_manifold_edges': non_manifold,
    'degenerate_faces': degenerate,
    'face_count': face_count,
    'vertex_count': vert_count,
    'dimensions_m': [round(dims.x, 3), round(dims.y, 3), round(dims.z, 3)],
    'is_manifold': non_manifold == 0,
    'is_clean': degenerate == 0,
}
print(json.dumps(result, indent=2))

if non_manifold > 0:
    print('FAIL: non-manifold edges remain')
    sys.exit(1)
else:
    print('PASS: mesh is manifold and clean')
" -- pipelines/art-to-rig-ralph/output/prepared/{asset-id}_v1_prepared.glb
```
