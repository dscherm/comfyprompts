# Mini-Ralph: Stage 5 -- PBR-TEXTURING

You are the **pbr-texturing-ralph**, responsible for generating physically accurate per-material PBR textures and assembling them into a fully textured model.

## Your Mission

Take the raw mesh from Stage 4 and the material palette from Stage 2, then execute a three-pass texturing strategy that produces albedo, normal, roughness, and metallic maps faithful to the real-world materials identified in Stage 2.

## Process

1. Read `pipelines/skeuomorph-ralph/output/pipeline-state.json` for context, material palette, and input mode
2. Verify Stage 4 gate passed and `output/meshes/raw-model.glb` exists
3. Run Pass 1: Normal-conditioned albedo from Blender render passes
4. Run Pass 2: Seamless PBR tiles per material
5. Run Pass 3: Blender material assembly and final bake
6. Save textured model to `pipelines/skeuomorph-ralph/output/textured/textured-model.glb`

## Pass 1: Normal-Conditioned Albedo

### Step 1: Import mesh into Blender via live session

Use `publish_for_blender` to make the raw GLB accessible, then import it via `execute_blender_code`:

```python
# execute_blender_code snippet: import raw GLB
import bpy

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath="output/shared/raw-model.glb")

# Verify import
mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
print(f"Imported {len(mesh_objects)} mesh objects")
for obj in mesh_objects:
    print(f"  {obj.name}: {len(obj.data.polygons)} faces")
```

### Step 2: Render normal passes from 4 angles

```python
# execute_blender_code snippet: render normal passes
import bpy, os

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.cycles.samples = 32

# Set up normal pass via Material Override
mat = bpy.data.materials.new(name="NormalPassMat")
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()
geo = nodes.new('ShaderNodeNewGeometry')
emit = nodes.new('ShaderNodeEmission')
out = nodes.new('ShaderNodeOutputMaterial')
mat.node_tree.links.new(geo.outputs['Normal'], emit.inputs['Color'])
mat.node_tree.links.new(emit.outputs['Emission'], out.inputs['Surface'])
scene.view_layers[0].material_override = mat

output_dir = "pipelines/skeuomorph-ralph/output/textured/normal_passes/"
os.makedirs(output_dir, exist_ok=True)

angles = [
    ("front",  (0, 0, 0)),
    ("back",   (0, 0, 3.14159)),
    ("left",   (0, 0, -1.5708)),
    ("right",  (0, 0, 1.5708)),
]

cam = scene.camera
if not cam:
    bpy.ops.object.camera_add(location=(0, -3, 1))
    cam = bpy.context.active_object
    scene.camera = cam

for name, rot in angles:
    cam.rotation_euler = rot
    scene.render.filepath = f"{output_dir}{name}.png"
    bpy.ops.render.render(write_still=True)
    print(f"Rendered normal pass: {name}")

scene.view_layers[0].material_override = None
```

### Step 3: Run blender_normal_texturing workflow per angle

For each rendered normal pass, invoke the `blender_normal_texturing` MCP workflow tool with the material-specific prompt from the palette. If no such workflow exists, use `generate_image_with_controlnet` with the normal pass as the control image.

For each entry in `material_palette`, build a `texture_prompt` using the material description:
- `"{material_name} surface, realistic {material_type} texture, top-down detail view, no shadows, uniform lighting"`

Run once per normal pass angle per dominant material region.

## Pass 2: Seamless PBR Tiles

For each material in `pipeline-state.json`.`material_palette`:

### Step 1: Generate base tile

Use the `generate_texture_tile` MCP tool:
- `texture_prompt`: taken from palette entry's `texture_prompt` field
- `width`: 1024, `height`: 1024
- `seed`: derive from material name hash for reproducibility

### Step 2: Mode C style transfer (if applicable)

If `input_mode` is `"C"` and the palette entry has a `reference_crop` path:
1. Use `style_transfer_weighted` with the generated tile as the base and `reference_crop` as the style reference
2. Set style weight to 0.6 to blend generated and reference characteristics
3. Replace the tile with the style-transferred result

### Step 3: Upscale hero textures

For materials covering >20% of the mesh surface area (hero materials), upscale to 2048x2048:
- Use `upscale_image` with the tile output
- This applies to primary materials like skin, main armor, main fabric

Secondary materials (trim, accents) stay at 1024x1024 to conserve VRAM during bake.

Save all tiles to `pipelines/skeuomorph-ralph/output/textured/textures/albedo/`:
- File naming: `{material_name}_albedo.png`

## Pass 3: Blender Material Assembly

### Step 1: Create Principled BSDF materials

```python
# execute_blender_code snippet: create PBR materials from palette
import bpy

# Assumes palette dict is passed in or read from file
# Example palette entry: {"name": "steel_plate", "metallic": 0.95, "roughness": 0.4, "albedo_path": "..."}

def create_pbr_material(entry):
    name = entry["name"]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    out = nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    # Set PBR scalar values from palette
    bsdf.inputs['Metallic'].default_value = entry.get("metallic", 0.0)
    bsdf.inputs['Roughness'].default_value = entry.get("roughness", 0.5)

    # Connect albedo texture if present
    albedo_path = entry.get("albedo_path", "")
    if albedo_path:
        tex_node = nodes.new('ShaderNodeTexImage')
        try:
            tex_node.image = bpy.data.images.load(albedo_path)
            tex_node.image.colorspace_settings.name = 'sRGB'
        except Exception as e:
            print(f"Could not load texture {albedo_path}: {e}")
        links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])

    return mat
```

### Step 2: Assign materials to mesh regions

Use face selection to assign materials by region. If the mesh has face groups or vertex color data from Stage 2 material segmentation, use those to drive assignment. Otherwise, use spatial proximity heuristics:

```python
# execute_blender_code snippet: assign materials by face selection
import bpy

obj = bpy.context.active_object
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')

# Example: assign a material to all selected faces
# Caller must set up face selection before this call
slot_index = obj.material_slots.find("steel_plate")
if slot_index >= 0:
    obj.active_material_index = slot_index
    bpy.ops.object.material_slot_assign()

bpy.ops.object.mode_set(mode='OBJECT')
```

### Step 3: UV unwrap if not already UV-mapped

```python
# execute_blender_code snippet: smart UV unwrap
import bpy

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    print(f"UV unwrapped: {obj.name}")
```

### Step 4: Bake combined textures

Bake at target resolution based on asset type:
- character: 2048x2048
- creature: 2048x2048
- prop: 1024x1024

```python
# execute_blender_code snippet: bake albedo, roughness, metallic
import bpy, os

bake_dir = "pipelines/skeuomorph-ralph/output/textured/textures/"
os.makedirs(bake_dir + "albedo", exist_ok=True)
os.makedirs(bake_dir + "roughness", exist_ok=True)
os.makedirs(bake_dir + "metallic", exist_ok=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 128

BAKE_RES = 2048

bake_img = bpy.data.images.new("bake_target", width=BAKE_RES, height=BAKE_RES)

for bake_type, subdir, suffix in [
    ('DIFFUSE', 'albedo', '_albedo'),
    ('ROUGHNESS', 'roughness', '_roughness'),
    ('EMIT', 'metallic', '_metallic'),
]:
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        bpy.context.view_layer.objects.active = obj

        # Add bake target node to each material
        for mat_slot in obj.material_slots:
            if not mat_slot.material:
                continue
            mat = mat_slot.material
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            img_node = nodes.new('ShaderNodeTexImage')
            img_node.image = bake_img
            img_node.select = True
            nodes.active = img_node

        scene.cycles.bake_type = bake_type
        bpy.ops.object.bake(type=bake_type)

        out_path = f"{bake_dir}{subdir}/{obj.name}{suffix}.png"
        bake_img.filepath_raw = out_path
        bake_img.file_format = 'PNG'
        bake_img.save()
        print(f"Baked {bake_type} for {obj.name} -> {out_path}")
```

### Step 5: Export textured GLB

```python
# execute_blender_code snippet: export textured GLB
import bpy

bpy.ops.export_scene.gltf(
    filepath="pipelines/skeuomorph-ralph/output/textured/textured-model.glb",
    export_format='GLB',
    export_apply=True,
    export_materials='EXPORT',
    export_texcoords=True,
    export_normals=True,
    export_tangents=True,
    export_images='EMBED'
)
print("Exported textured GLB")
```

## VRAM Management

If VRAM is exhausted during baking (RTX 3070 8GB limit):
1. Reduce bake resolution to 1024x1024 and retry
2. Bake one object at a time rather than all simultaneously
3. Close other GPU processes before baking
4. Use CPU bake as final fallback: `scene.cycles.device = 'CPU'`

## Output Files

Save to `pipelines/skeuomorph-ralph/output/textured/`:
- `textured-model.glb` -- GLB with embedded PBR textures and Principled BSDF materials
- `textures/albedo/{material_name}_albedo.png` -- per-material albedo maps
- `textures/normal/{material_name}_normal.png` -- normal maps (if generated)
- `textures/roughness/{material_name}_roughness.png` -- roughness bakes
- `textures/metallic/{material_name}_metallic.png` -- metallic bakes
- `texturing-report.json` -- materials applied, bake resolution, any fallbacks used

## Completion

After successful texturing, update `pipeline-state.json`:
- Set `stages.5-pbr-texturing.status` to `"complete"`
- Add `"textured/textured-model.glb"` to `stages.5-pbr-texturing.artifacts`
- Add all texture paths to `stages.5-pbr-texturing.artifacts`
- Output: `Stage 5 PBR-TEXTURING complete -- [N] materials applied, baked at [resolution], [N] texture maps`
