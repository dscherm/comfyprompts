# Mini-Ralph: Stage 5 -- EXPORT

Bake animations, split into individual clips, export per-platform FBX/GLB.

## Process

1. Open each polished .blend file
2. Bake all constraints and drivers to keyframes
3. For each clip, create a separate NLA strip
4. Export per platform:
   - **Unity**: FBX with Mecanim bone naming, individual clip files
   - **Unreal**: FBX with UE bone naming, individual clip files
   - **Blender**: GLB with all clips as NLA tracks
5. Also export a combined "all animations" file per platform

## Export Settings

### Unity FBX
```python
bpy.ops.export_scene.fbx(
    filepath=output_path,
    use_selection=True,
    object_types={'ARMATURE', 'MESH'},
    use_armature_deform_only=True,
    add_leaf_bones=False,
    bake_anim=True,
    bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True,
    apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z',
    axis_up='Y',
)
```

### Unreal FBX
Same as Unity but with `axis_forward='X'`, `axis_up='Z'`.

### Blender GLB
```python
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_nla_strips=True,
)
```

## Output Structure

```
output/export/
├── {model_id}/
│   ├── unity/
│   │   ├── {model_id}_{clip_name}.fbx
│   │   └── {model_id}_all_clips.fbx
│   ├── unreal/
│   │   ├── {model_id}_{clip_name}.fbx
│   │   └── {model_id}_all_clips.fbx
│   └── blender/
│       └── {model_id}_animated.glb
```

## Completion

Update pipeline-state.json, output: `Stage 5 EXPORT complete -- {N} clips exported for {model_name} ({P} platforms)`
