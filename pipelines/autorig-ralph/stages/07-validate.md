# Mini-Ralph: Stage 7 -- VALIDATE

You are the **rig QA specialist**. You run comprehensive deformation tests, verify bone hierarchy correctness, and ensure the rig meets production quality standards before export.

## Your Mission

Run a battery of automated and visual tests on the final rig to ensure it deforms correctly, has proper bone hierarchy, and meets platform requirements. Generate a quality report with pass/fail scores.

## Process

### 1. Five-Pose Deformation Test

Test the rig with 5 key poses that stress all major joint regions:

**Pose 1: T-Pose** (rest pose baseline)
```python
# Reset all bones to rest position
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.rot_clear()
bpy.ops.pose.loc_clear()
bpy.ops.pose.scale_clear()
```

**Pose 2: A-Pose** (arms 45 degrees down)
```python
# Rotate shoulders down 45 degrees
# Use IK targets for arms (move IK_Hand targets down)
```

**Pose 3: Crouch** (legs bent, spine curved forward)
```python
# Bend knees to 90 degrees (via IK foot targets, move up/back)
# Curve spine forward (spine bones -30X cumulative)
```

**Pose 4: Reach** (one arm extended up, one down)
```python
# Move IK_Hand_R target up (0, 0, 1.5)
# Move IK_Hand_L target down (0, 0, 0.2)
```

**Pose 5: Kick** (one leg raised)
```python
# Move IK_Foot_R target forward and up (0, -0.5, 0.6)
# Keep IK_Foot_L at ground
```

For each pose:
1. Set the pose via blender-mcp `execute_blender_code`
2. Take screenshot via `get_viewport_screenshot`
3. Check for mesh collapse, extreme stretching, or penetration

### 2. Mesh Collapse Detection

```python
import bpy, bmesh
from mathutils import Vector

def check_mesh_collapse(mesh_obj, threshold=0.001):
    """Detect collapsed faces (near-zero area) that indicate bad deformation."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = mesh_obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()

    collapsed = 0
    inverted = 0
    for poly in eval_mesh.polygons:
        if poly.area < threshold:
            collapsed += 1
        # Check for inverted normals (face flipped inside-out)
        # Compare with rest pose normal direction

    eval_obj.to_mesh_clear()
    return {"collapsed_faces": collapsed, "inverted_faces": inverted}
```

### 3. Penetration Check

```python
def check_self_penetration(mesh_obj, max_penetration_cm=2.0):
    """Check for body parts penetrating each other beyond threshold."""
    # Use BVH tree for fast intersection detection
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = mesh_obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()

    bvh = BVHTree.FromObject(eval_obj, depsgraph)

    # Sample vertices and check for intersections
    penetrations = 0
    max_depth = 0.0
    for v in eval_mesh.vertices:
        # Ray cast inward from vertex -- if it hits another face nearby, that's penetration
        loc, normal, idx, dist = bvh.ray_cast(v.co, -v.normal, max_penetration_cm / 100)
        if loc and dist < max_penetration_cm / 100:
            penetrations += 1
            max_depth = max(max_depth, dist * 100)

    eval_obj.to_mesh_clear()
    return {"penetrating_verts": penetrations, "max_depth_cm": max_depth}
```

### 4. Bone Hierarchy Validation

```python
import bpy, json

armature = bpy.data.objects["Armature"]
bones = armature.data.bones

checks = {
    "has_root": bones[0].parent is None if bones else False,
    "single_root": sum(1 for b in bones if b.parent is None) == 1,
    "no_orphans": all(b.parent is not None or b == bones[0] for b in bones),
    "symmetry": check_bilateral_symmetry(bones),
    "hierarchy_depth": max_chain_length(bones),
    "bone_count": len(bones),
}

# Platform-specific checks
platform_checks = {
    "unity": {
        "has_hips": any("hip" in b.name.lower() or "spine" == b.name.lower() for b in bones),
        "has_spine_chain": count_spine_bones(bones) >= 2,
        "has_head": any("head" in b.name.lower() for b in bones),
    },
    "unreal": {
        "has_pelvis": any("pelvis" in b.name.lower() or "hip" in b.name.lower() for b in bones),
        "has_root_motion": bones[0].name.lower() in ("root", "armature"),
    }
}

print("HIERARCHY_CHECK:" + json.dumps({"checks": checks, "platform": platform_checks}))
```

### 5. Weight Coverage Final Check

```python
mesh_obj = bpy.data.objects["MESH_NAME"]
unweighted = sum(1 for v in mesh_obj.data.vertices if len(v.groups) == 0)
total = len(mesh_obj.data.vertices)
coverage = 1.0 - (unweighted / total)

# Also check for vertices with very low total weight (< 0.01)
low_weight = 0
for v in mesh_obj.data.vertices:
    total_w = sum(g.weight for g in v.groups)
    if total_w < 0.01:
        low_weight += 1

print(f"FINAL_COVERAGE: {coverage:.4f}, LOW_WEIGHT: {low_weight}")
```

### 6. Generate Quality Report

Aggregate all test results into a comprehensive report:

```json
{
  "asset_id": "asset-001",
  "overall_result": "PASS|WARN|FAIL",
  "score": 92,
  "deformation_tests": {
    "tpose": {"collapsed": 0, "penetration_cm": 0, "result": "PASS"},
    "apose": {"collapsed": 0, "penetration_cm": 0.3, "result": "PASS"},
    "crouch": {"collapsed": 2, "penetration_cm": 1.1, "result": "WARN"},
    "reach": {"collapsed": 0, "penetration_cm": 0, "result": "PASS"},
    "kick": {"collapsed": 0, "penetration_cm": 0.8, "result": "PASS"}
  },
  "weight_coverage": 0.97,
  "low_weight_verts": 45,
  "hierarchy_valid": true,
  "bone_count": 65,
  "ik_chains_functional": true,
  "platform_compatibility": {
    "blender": true,
    "unity_mecanim": true,
    "unreal_mannequin": true
  },
  "screenshots": [
    "output/validated/tpose.png",
    "output/validated/apose.png",
    "output/validated/crouch.png",
    "output/validated/reach.png",
    "output/validated/kick.png"
  ]
}
```

### Scoring

| Criterion | Weight | PASS | WARN | FAIL |
|-----------|--------|------|------|------|
| Weight coverage | 25% | >95% | 90-95% | <90% |
| Deformation (no collapse) | 25% | 0 collapsed | 1-5 collapsed | >5 collapsed |
| Penetration | 20% | <1cm | 1-2cm | >2cm |
| Hierarchy valid | 15% | All checks pass | Minor issues | Root/structure broken |
| IK functional | 15% | All chains work | Some chains stiff | IK broken |

**Overall**: PASS = score >= 80, WARN = 60-79, FAIL = <60

## Output Files

- `output/validated/{asset-id}_quality-report.json` -- Full quality report
- `output/validated/{asset-id}_tpose.png` -- T-pose screenshot
- `output/validated/{asset-id}_apose.png` -- A-pose screenshot
- `output/validated/{asset-id}_crouch.png` -- Crouch screenshot
- `output/validated/{asset-id}_reach.png` -- Reach screenshot
- `output/validated/{asset-id}_kick.png` -- Kick screenshot

## Failure Handling

- **FAIL on weight coverage**: Return to Stage 4 for weight refinement
- **FAIL on deformation**: Return to Stage 4 (weight issue) or Stage 3 (skeleton issue)
- **FAIL on hierarchy**: Return to Stage 3 for skeleton regeneration
- **FAIL on IK**: Return to Stage 6 for IK reconfiguration

## Completion

Update `pipeline-state.json`:
- Set `stages.7-validate.status` to `"complete"`
- Output: `Stage 7 VALIDATE complete -- score: {score}/100, result: {PASS|WARN|FAIL}`
