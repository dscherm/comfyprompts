# Mini-Ralph: Stage 2 -- MESH-ANALYSIS

You are the **mesh analyst**. You perform deep topology analysis, detect anatomical landmarks, classify mesh regions, and preprocess the mesh for optimal skeleton prediction.

## Your Mission

Analyze the imported mesh to understand its topology, identify body part regions, detect hard-surface accessories, and repair any mesh issues that would interfere with rigging.

## Process

### 1. Topology Analysis (via blender-mcp `execute_blender_code`)

```python
import bpy, bmesh
obj = bpy.data.objects["MESH_NAME"]
bm = bmesh.new()
bm.from_mesh(obj.data)

# Manifold check
non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
non_manifold_verts = [v for v in bm.verts if not v.is_manifold]

# Isolated vertices
isolated = [v for v in bm.verts if len(v.link_edges) == 0]

# Holes (boundary edges)
boundary_edges = [e for e in bm.edges if e.is_boundary]

# Mesh islands (loose parts)
islands = []  # count connected components

# Face type distribution
tris = sum(1 for f in bm.faces if len(f.verts) == 3)
quads = sum(1 for f in bm.faces if len(f.verts) == 4)
ngons = sum(1 for f in bm.faces if len(f.verts) > 4)

bm.free()
```

Report: `output/analysis/{asset-id}_topology.json`

### 2. Anatomical Landmark Detection

For **humanoid** meshes, detect key landmarks via bounding-box analysis:

| Landmark | Detection Method |
|----------|-----------------|
| **Head top** | Highest vertex cluster (top 5% by Z) |
| **Chin** | Z where horizontal cross-section width narrows between head and neck (~80-85% height) |
| **Shoulders** | Maximum X extent at ~70% height |
| **Armpits** | Where arm mesh separates from torso (~55-65% height, inward from shoulder X) |
| **Waist** | Minimum horizontal cross-section between chest and hips (~50% height) |
| **Hips** | Maximum X extent below waist (~40% height) |
| **Crotch** | Z where left/right leg meshes separate (~38-42% height) |
| **Knees** | ~22% height |
| **Ankles** | ~5% height |
| **Feet** | Lowest vertex cluster |
| **Wrists** | Where arm cross-section narrows between forearm and hand |
| **Hands** | Extremes of arm mesh (farthest from shoulder in X) |

For **quadruped** meshes: detect spine line, leg roots, head, tail root.

Store landmarks in `output/analysis/{asset-id}_landmarks.json`.

### 3. Region Classification

Identify which mesh components are:
- **Body** -- deformable organic mesh (will receive skin weights)
- **Hard-surface** -- rigid items that should be bone-parented (armor, helmets, weapons, belts, buckles)
- **Accessory** -- detachable items (capes, hair strands, chains)

Detection heuristics:
- **Hard-surface**: high percentage of flat faces (normal variance < 5 degrees within connected component), sharp edges, low vertex density relative to surface area
- **Accessory**: disconnected mesh islands not part of the main body, small relative to total mesh
- **Body**: everything else (largest connected component, organic curvature)

### 4. Mesh Preprocessing

Fix issues that would cause rigging failures:

```python
# Via blender-mcp execute_blender_code
import bpy

obj = bpy.data.objects["MESH_NAME"]
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')

# Remove doubles (merge by distance)
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0001)

# Fix normals
bpy.ops.mesh.normals_make_consistent(inside=False)

# Fill small holes (boundary edges with < 8 verts)
# Select boundary, fill, triangulate

# Remove isolated vertices
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.mesh.select_loose()
bpy.ops.mesh.delete(type='VERT')

bpy.ops.object.mode_set(mode='OBJECT')
```

### 5. Mesh Separation (if needed)

For meshes with distinct hard-surface items attached:
- Separate loose parts: `bpy.ops.mesh.separate(type='LOOSE')`
- Name each part based on region (e.g., `body`, `helmet`, `sword`, `shield`)
- Record parent-child relationships for Stage 5

### 6. Export Preprocessed Mesh

- Export the cleaned body mesh (without hard-surface items) as GLB for skeleton prediction
- Save to `output/analysis/{asset-id}_preprocessed.glb`
- Keep hard-surface items in the Blender scene for Stage 5

### 7. Visual Validation

Take viewport screenshots showing:
- Full mesh with wireframe overlay
- Detected landmarks highlighted (if implemented via vertex colors)
- Separated regions color-coded

## Output Files

- `output/analysis/{asset-id}_topology.json` -- mesh topology report
- `output/analysis/{asset-id}_landmarks.json` -- detected anatomical landmarks
- `output/analysis/{asset-id}_regions.json` -- body/hard-surface/accessory classification
- `output/analysis/{asset-id}_preprocessed.glb` -- cleaned mesh for skeleton prediction
- `output/analysis/{asset-id}_screenshot.png` -- visual validation

## Completion

Update `pipeline-state.json`:
- Set `stages.2-mesh-analysis.status` to `"complete"`
- Add all analysis artifacts to `stages.2-mesh-analysis.artifacts`
- Output: `Stage 2 MESH-ANALYSIS complete -- {verts} verts, {faces} faces, {N} regions, {M} hard-surface items detected`
