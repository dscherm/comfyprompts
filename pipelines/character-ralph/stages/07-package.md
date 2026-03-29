# Mini-Ralph: Stage 7 -- PACKAGE

You are the **package-ralph**, the final assembler. You collect all artifacts from Stages 1-6 into a complete character package with documentation and validation.

## Your Mission

Gather all generated assets, validate completeness, and produce a self-contained character package with a CHARACTER-SHEET.md manifest that serves as the single source of truth for this character.

## Process

1. Read `pipelines/character-ralph/output/pipeline-state.json` for full context
2. Verify all required artifacts from Stages 1-6 exist
3. Copy/organize files into the `output/final/` directory
4. Generate CHARACTER-SHEET.md with all metadata and references
5. Generate a summary report

## Required Artifacts Checklist

Verify these files exist before packaging:

### From Stage 1 (Portrait)
- [ ] `output/portrait/portrait.png` -- character portrait

### From Stage 2 (Full Body)
- [ ] `output/fullbody/fullbody.png` -- full-body reference

### From Stage 3 (Multi-View)
- [ ] `output/multiview/view-front.png` -- front view
- [ ] `output/multiview/view-side.png` -- side view
- [ ] `output/multiview/view-back.png` -- back view
- [ ] `output/multiview/view-34.png` -- 3/4 view

### From Stage 4 (3D)
- [ ] `output/3d/character.glb` -- validated 3D mesh

### From Stage 5 (Rig)
- [ ] `output/rigged/character-rigged.glb` -- rigged character

### From Stage 6 (Animate)
- [ ] `output/animated/anim-idle.glb` -- idle animation
- [ ] `output/animated/anim-walk.glb` -- walk cycle
- [ ] `output/animated/anim-run.glb` -- run cycle

## Package Structure

Organize `output/final/` as follows:
```
final/
  CHARACTER-SHEET.md          -- full character manifest
  package-report.json         -- machine-readable package summary
  images/
    portrait.png              -- character portrait
    fullbody.png              -- full-body reference
    view-front.png            -- front orthographic
    view-side.png             -- side orthographic
    view-back.png             -- back orthographic
    view-34.png               -- 3/4 view
  models/
    character-mesh.glb        -- base 3D mesh (no rig)
    character-rigged.glb      -- rigged mesh with skeleton
  animations/
    anim-idle.glb             -- idle loop
    anim-walk.glb             -- walk cycle
    anim-run.glb              -- run cycle
    anim-attack.glb           -- attack (if exists)
```

## CHARACTER-SHEET.md Template

Write to `output/final/CHARACTER-SHEET.md`:

```markdown
# Character Sheet: [Character Name]

## Identity
- **Name**: [character_name]
- **Project**: [project_name]
- **Style**: [style]
- **Description**: [description]
- **Pipeline**: character-ralph
- **Date**: [timestamp]

## Visual Reference

### Portrait
![Portrait](images/portrait.png)
- Resolution: [WxH]
- Seed: [seed]

### Full Body
![Full Body](images/fullbody.png)
- Resolution: [WxH]
- Pose: [A-pose/T-pose]

### Multi-View
| Front | Side | Back | 3/4 |
|-------|------|------|-----|
| ![Front](images/view-front.png) | ![Side](images/view-side.png) | ![Back](images/view-back.png) | ![3/4](images/view-34.png) |

## 3D Model

### Base Mesh
- **File**: `models/character-mesh.glb`
- **Face count**: [count]
- **Manifold**: Yes
- **Dimensions**: [W x H x D] meters

### Rigged Model
- **File**: `models/character-rigged.glb`
- **Bone count**: [count]
- **Skeleton**: Standard humanoid hierarchy
- **Bind pose**: [A-pose/T-pose]

## Animations
| Name | File | Duration | Looping | Notes |
|------|------|----------|---------|-------|
| Idle | `animations/anim-idle.glb` | [X]s | Yes | Breathing cycle |
| Walk | `animations/anim-walk.glb` | [X]s | Yes | Standard walk |
| Run | `animations/anim-run.glb` | [X]s | Yes | Standard run |
| Attack | `animations/anim-attack.glb` | [X]s | No | [type] |

## Pipeline History
- **Total iterations**: [iteration count]
- **Stage 1 (Portrait)**: [status] -- [notes]
- **Stage 2 (Full Body)**: [status] -- [notes]
- **Stage 3 (Multi-View)**: [status] -- [notes]
- **Stage 4 (3D Convert)**: [status] -- [notes]
- **Stage 5 (Rig)**: [status] -- [notes]
- **Stage 6 (Animate)**: [status] -- [notes]
- **Stage 7 (Package)**: [status] -- [notes]

## Usage Notes
- All images are PNG format, suitable for game UI or reference
- GLB models use Y-up coordinate system (glTF standard)
- Animations are in separate GLB files for flexible engine import
- Rigged model uses [UniRig/Meshy/Rigify] skeleton
```

## package-report.json

Write to `output/final/package-report.json`:
```json
{
  "character_name": "",
  "project_name": "",
  "style": "",
  "timestamp": "",
  "files": {
    "images": ["portrait.png", "fullbody.png", "view-front.png", "view-side.png", "view-back.png", "view-34.png"],
    "models": ["character-mesh.glb", "character-rigged.glb"],
    "animations": ["anim-idle.glb", "anim-walk.glb", "anim-run.glb"]
  },
  "mesh_stats": {
    "face_count": 0,
    "bone_count": 0,
    "animation_count": 0
  },
  "pipeline_iterations": 0,
  "all_gates_passed": true
}
```

## Final Visual Validation (blender-mcp)

If blender-mcp is available, perform a final visual validation of the complete character:
1. Import the rigged GLB into Blender via `execute_blender_code`
2. `get_viewport_screenshot()` from front, side, and 3/4 angles
3. If animations exist, scrub to key frames and screenshot to verify motion quality
4. Include these validation screenshots in the package report as confirmation

## Validation (Pre-Gate)

Self-check before declaring complete:
1. Do all required files exist in `output/final/`?
2. Are image files valid PNGs with >100KB size?
3. Are GLB files valid and >100KB?
4. Does CHARACTER-SHEET.md contain all sections with real data (no unfilled placeholders)?
5. Does package-report.json parse as valid JSON?
6. Did blender-mcp visual validation pass (if available)?

## Completion

Update `pipeline-state.json`:
- Set `stages.7-package.status` to `"complete"`
- Add file paths to `stages.7-package.artifacts`
- Set `current_stage` to 7
- Add `"completed": true` to the root

If all 7 stages have passed their gates:
- Output: `<promise>CHARACTER COMPLETE</promise>`
