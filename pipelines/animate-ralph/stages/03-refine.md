# Mini-Ralph: Stage 3 -- REFINE

Add breakdowns and in-betweens to blocked animations. Switch from stepped to spline interpolation. This is where motion starts to feel alive.

## Process

1. Check blender-mcp availability via `get_external_app_status` -> `blender_mcp.available`
2. Open each blocked .blend file (or use the live Blender session from Stage 2 if blender-mcp is active)
3. Add breakdown poses between key poses (halfway points that define the arc)
4. Switch interpolation from CONSTANT to BEZIER
5. Add anticipation frames before major actions
6. Add follow-through frames after impacts
7. Ensure loop seams are smooth (for looping clips)
8. **Path A (blender-mcp)**: After adding breakdowns, scrub to key frames and call `get_viewport_screenshot()` to verify arcs look natural. Adjust if needed.
9. Save refined .blend files

## Refinement Rules

- Add **1-2 breakdown poses** between each pair of key poses
- Breakdowns define the **arc** — straight line between keys = dead motion
- **Anticipation**: 2-4 frames of opposite motion before any action
- **Follow-through**: 3-6 frames of overshoot after impacts/stops
- **Overlapping action**: Hair, cloth, accessories should lag behind body by 2-3 frames
- **Ease in/out**: Use Bezier handles to ease into and out of holds

## Completion

Update pipeline-state.json, output: `Stage 3 REFINE complete -- {N} clips refined for {model_name}`
