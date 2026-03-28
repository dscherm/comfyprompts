# Mini-Ralph: Stage 1 -- PARSE

Parse the scene description into a structured asset plan with positions, materials, lighting, and camera.

## Process

1. Read the user's scene description (from pipeline-state.json or user prompt)
2. Identify distinct objects that need 3D models
3. Plan spatial layout (positions, scales, rotations)
4. Choose environment settings (HDRI, ground plane, ambient)
5. Plan camera placement and focal length
6. Write `output/parse/scene-plan.json`

## Output

```json
{
  "assets": [
    {"id": "unique-id", "description": "detailed generation prompt", "type": "3d",
     "position": [x, y, z], "rotation": [rx, ry, rz], "scale": 1.0,
     "material_hint": "wood|metal|fabric|custom"}
  ],
  "environment": {
    "hdri": "suggested poly haven hdri name or null",
    "ground_plane": true,
    "ground_material": "concrete|grass|wood|custom"
  },
  "camera": {
    "position": [x, y, z],
    "target": [x, y, z],
    "focal_length": 50
  },
  "mood": "description of lighting mood",
  "style": "photorealistic|stylized|cartoon"
}
```

## Completion

Update pipeline-state.json with scene plan. Output: `Stage 1 PARSE complete -- {N} assets planned`
