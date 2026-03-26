# Recent Activity (auto-generated)

## 2026-03-26 - Task 3: Blender-Specific Parametric Workflows

**Goal:** Add depth-guided, normal-map texturing, and pose-to-render workflows for the Blender-ComfyUI pipeline

**Changes Made:**
- `workflows/mcp/blender_depth_guided.json`: Depth-guided img2img workflow — loads Blender depth pass + source render, applies ControlNet depth conditioning (control_v11f1p_sd15_depth.pth), KSampler with configurable denoise for img2img
- `workflows/mcp/blender_depth_guided.meta.json`: Metadata sidecar — SD1.5 + depth ControlNet requirements, 3 required params (depth_image, source_image, prompt), defaults (strength 0.85, denoise 0.65, dpmpp_2m/karras)
- `workflows/mcp/blender_normal_texturing.json`: Normal-map texturing workflow — loads Blender normal pass, applies ControlNet normal conditioning (control_v11p_sd15_normalbae.pth), txt2img generation
- `workflows/mcp/blender_normal_texturing.meta.json`: Metadata sidecar — SD1.5 + normal ControlNet, defaults (strength 0.9, 512x512, 30 steps)
- `workflows/mcp/blender_pose_to_render.json`: Pose-to-render workflow — loads OpenPose stick figure from Blender armature, generates character render via ControlNet (control_v11p_sd15_openpose.pth)
- `workflows/mcp/blender_pose_to_render.meta.json`: Metadata sidecar — SD1.5 + openpose ControlNet, defaults (strength 0.8, 512x768 portrait)
- `packages/mcp-server/tests/test_blender_workflows.py`: 37 tests covering file validation, WorkflowManager discovery, parameter parsing, and render substitution

**Design Decisions:**
- Used built-in `ControlNetApply` node (not FluxUnionControlNetApply) — no custom nodes needed
- Targeted SD1.5 (`v1-5-pruned-emaonly.ckpt`) since that's what's installed locally
- All three workflows use standard ControlNet v1.1 models (depth, normalbae, openpose)
- Category "blender" and tag "blender" for easy filtering
- Each meta.json includes Blender setup notes and model download URLs

**Verification:**
- `pytest packages/mcp-server/tests/test_blender_workflows.py -v` -- 37 passed, 0 failures
- `pytest packages/mcp-server/tests/ -v --tb=short -q` -- 194 passed, 9 failed (pre-existing), 6 skipped

**Status:** COMPLETE
