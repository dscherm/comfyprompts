# AutoRig Ralph -- Memories

## Initial Context (2026-03-29)

Pipeline created to unify ML-based rigging tools (UniRig, Rigify, Meshy) into a single automated pipeline with quality gates. Key lessons from prior work:

- UniRig skeleton prediction works well but skinning step often fails on complex meshes -- use proximity weighting as fallback (proven in art-to-rig-ralph)
- UniRig bone local axes are arbitrary -- IK constraints required for arm posing (Euler rotation produces wrong results)
- Boot fin artifacts from Hunyuan3D mesh generation need cleanup before rigging
- Mesh split by region (head/arms/legs/torso) improves weight painting accuracy for proximity weighting
- RTX 3070 8GB is near VRAM limit for UniRig -- skeleton prediction takes ~30min, budget accordingly
- blender-mcp (port 9876) is always preferred over headless Blender for visual validation
