# Art-to-Rig Ralph -- Memories

## Initial Context
- Created: 2026-03-25
- Purpose: Generate consistent 2D illustrations and convert to rigged 3D models for Blender/Unity/Unreal
- Domain: `pipelines/art-to-rig-ralph/output/` -- concept images, cleaned images, raw meshes, prepared geometry, rigged models, platform exports
- Expertise: Illustration styles (cartoon, comic, fantasy, sci-fi, realistic, pencil, painting, pixel art), 3D topology, skeletal rigging, bone naming conventions, multi-platform export

## Style Knowledge
- Cartoon/Chibi: Use bold outlines, flat colors, exaggerated proportions. Best with Flux + transparent background. Clean silhouettes convert well to 3D because edge detection is unambiguous.
- Comic Book: Heavy inks, dynamic composition. Works well with style_transfer_ipadapter for consistency across a batch. Halftone patterns may confuse mesh generation -- consider removing them in prompt.
- Dark Fantasy: Painterly rendering, dramatic lighting. Hunyuan3D v2.5 handles these textures best. Frazetta-style poses are often too dynamic for T-pose rigging -- prompt for neutral stance.
- High Fantasy: Luminous, ethereal effects (glows, particles) do not survive 3D conversion. Prompt for solid forms.
- Hard Sci-Fi: Clean hard surfaces, technical detail. TripoSG actually outperforms Hunyuan3D on pure mechanical forms.
- Cyberpunk: Neon glow effects get baked as geometry artifacts. Prompt for the object without glow, add effects in engine.
- Realistic: Photorealistic needs highest-quality 3D conversion. Use Hunyuan3D v2.5 PBR exclusively. Avoid Turbo fallback -- quality drop is severe.
- Pencil/Sketch: Line art converts poorly to 3D -- the mesh generator sees lines as surface features. Recommend adding shading/volume via img2img before 3D stage.
- Oil Painting: Soft edges may confuse background removal. Prefer generate_transparent approach. Brushstroke texture becomes mesh noise.
- Watercolor: Bleeds and transparency effects create ambiguous silhouettes. Not recommended for 3D conversion without heavy cleanup.
- Digital Painting: Best of both worlds -- painterly feel with clean edges. Good 3D conversion characteristics.
- Pixel Art: Convert at 4x upscale first, then generate 3D. Raw pixel art at native resolution fails mesh generation.

## Rigging Knowledge
- UniRig works best for standard humanoids in T-pose/A-pose with clear limb separation
- blender_autorig.py with 'quadruped' type handles 4-legged creatures but needs clearly separated legs in the mesh
- Non-standard body types (serpentine, insect, mech) need custom Blender scripts -- no reliable auto-rig exists
- Unity Humanoid Avatar requires EXACT bone naming -- even one wrong name breaks Mecanim mapping
- Unreal's IK retargeting is more forgiving on naming but strict on hierarchy order (pelvis must be root)
- Weight painting coverage below 90% causes visible mesh tearing during animation
- Meshes with merged/overlapping limbs will fail auto-rigging -- Stage 5 must ensure limb separation

## 3D Conversion Knowledge
- Hunyuan3D v2.5 PBR: Best quality, 12-16GB VRAM, slow (3-5 min). Handles texture and color well.
- Hunyuan3D v2.0: Good quality, 8-12GB VRAM. Geometry-only mode produces cleaner topology.
- Hunyuan3D Turbo: Fast (30-60s) but lower detail. Good for props, bad for characters.
- TripoSG: Cloud-based fallback. Good for mechanical/hard-surface. Weak on organic forms.
- A-pose hint: Critical for character mesh generation. Without it, limbs often merge with the body.
- Front orthographic view: Always the primary reference. 3/4 views help but front is essential.

## Platform Export Knowledge
- Blender GLB: Standard glTF 2.0. Bone names use dot notation for sides (.L, .R). Supports shape keys.
- Unity FBX: Must use FBX 7.4 binary format. Bone names are PascalCase with Left/Right prefix. Humanoid Avatar auto-detection requires minimum 15 matched bones.
- Unreal FBX: Must use FBX 7.4 binary format. Bone names are snake_case with _l/_r suffix. pelvis must be root bone. UE5 accepts glTF but FBX gives better retargeting.
- STL for 3D printing: Use mm directly in Blender coordinates. Do NOT divide by 1000 -- Blender's unit system handles the conversion. Scale model so 1 Blender unit = 1mm before STL export.
