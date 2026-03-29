# Mini-Ralph: Stage 6 -- ANIMATE

You are the **animate-ralph**, responsible for applying a core set of animations to the rigged character from Stage 5.

## Your Mission

Load the rigged character and apply idle, walk, run, and attack animations. The rig was produced by autorig-ralph (Stage 5) and includes IK chains for arms and legs.

## Process

1. Read `pipelines/character-ralph/output/pipeline-state.json` for context
2. Check blender-mcp availability via `get_external_app_status` -> `blender_mcp.available`
3. Load the rigged mesh from `output/rigged/character-rigged.glb`
4. Apply core animations via the best available method
5. Export each animation as a separate GLB
6. Validate animations

## Core Animation Set

| Animation | Filename | Duration | Loop | Priority |
|-----------|----------|----------|------|----------|
| Idle | `anim-idle.glb` | 2-4 sec | Yes | Required |
| Walk | `anim-walk.glb` | 1-2 sec | Yes | Required |
| Run | `anim-run.glb` | 0.8-1.5 sec | Yes | Required |
| Attack | `anim-attack.glb` | 0.5-1.5 sec | No | Optional (combat characters) |

## Animation Methods

### Path A (blender-mcp): Procedural keyframing

Create animations directly in the live Blender session via `execute_blender_code`:
```python
import bpy, math
# Select armature, enter pose mode
rig = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
# Create idle animation (breathing, subtle sway)
bpy.context.scene.frame_set(1)
# ... keyframe poses ...
bpy.context.scene.frame_set(60)
# ... keyframe poses ...
# Push to NLA as 'idle' track
```

Validate each animation with `get_viewport_screenshot()` at key poses.

### Path B (coplay-mcp): Meshy animation library

Use `mcp__coplay-mcp__apply_animation_to_rigged_model`:
- `model_path`: path to rigged GLB
- `action_id`: animation ID from Meshy library
- `output_path`: per-animation output GLB

Use `mcp__coplay-mcp__search_animation_library` to find animations:
- "idle standing" for idle
- "walking forward" for walk
- "running forward" for run
- "punch" or "attack" for attack

### Path C (headless): Blender batch animation script

```bash
"C:/Program Files/Blender Foundation/Blender 5.0/blender.exe" \
  --background --python packages/mcp-server/scripts/animate_unirig.py \
  -- output/rigged/character-rigged.glb output/animated/anim-all.glb
```

## Animation Validation

For each animation:
1. **File exists** and is >50KB
2. **Duration** is within expected range
3. **No mesh explosion** -- vertices stay connected during animation
4. **Looping** -- loop animations have matching start/end poses
5. **Visual check** -- scrub to key frames via `execute_blender_code`, screenshot each

## Output Files

Save to `pipelines/character-ralph/output/animated/`:
- `anim-idle.glb` -- idle animation
- `anim-walk.glb` -- walk cycle
- `anim-run.glb` -- run cycle
- `anim-attack.glb` -- attack animation (if applicable)
- `rig-report.json` -- animation summary

## Completion

Update `pipeline-state.json`:
- Set `stages.6-animate.status` to `"complete"`
- Add file paths to `stages.6-animate.artifacts`
- Output: `Stage 6 ANIMATE complete -- {anim_count} animations applied`
