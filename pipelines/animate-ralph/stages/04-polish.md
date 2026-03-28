# Mini-Ralph: Stage 4 -- POLISH

Graph editor pass. Clean up F-Curves, fix arcs, adjust timing, ensure professional quality.

## Process

1. Check blender-mcp availability via `get_external_app_status` -> `blender_mcp.available`
2. Open each refined .blend file (or continue in live Blender session if blender-mcp active)
3. In the Graph Editor, clean up every F-Curve:
   - Remove redundant keyframes (keys that don't change the curve)
   - Fix overshoots that cause jitter
   - Smooth handle tangents for natural motion
   - Verify rotation curves don't gimbal lock (use quaternion)
3. Verify loop continuity for looping clips
4. Check timing against frame budget (30fps default)
5. Save polished .blend files

## Polish Checklist

- [ ] No knee/elbow pops (sudden direction changes in joint rotations)
- [ ] Hips drive all locomotion (not floating/sliding)
- [ ] Feet don't slide during grounded poses
- [ ] Hands maintain contact with held objects
- [ ] Head leads eye direction naturally
- [ ] Looping clips: frame 0 and last frame are identical
- [ ] No unnecessary keyframes (clean curves)
- [ ] Quaternion rotations (no gimbal lock)

## Visual Validation (blender-mcp Path A)

If blender-mcp is available, after polishing each clip:
1. Scrub to key poses and call `get_viewport_screenshot()` to verify:
   - No knee/elbow pops visible
   - Clean silhouettes at each key pose
   - Feet are grounded (no floating/sliding)
2. Play back the animation and screenshot at problem frames
3. Fix any issues via `execute_blender_code` before exporting

## Completion

Update pipeline-state.json, output: `Stage 4 POLISH complete -- {N} clips polished for {model_name}`
