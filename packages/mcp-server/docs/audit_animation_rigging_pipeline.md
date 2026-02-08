# Animation & Rigging Pipeline Audit Report

**Date:** 2026-02-06
**Auditor:** Animation & Rigging Specialist Agent

---

## 1. Executive Summary

The animation/rigging pipeline is well-structured with a solid foundation covering multiple rigging backends (Rigify, UniRig, Tripo3D), 7 procedural animation types, and mocap import with retargeting. The code is organized across standalone Blender scripts, a Blender addon, MCP server integration managers, and MCP tool definitions. However, there is significant code duplication, missing animation types for common use cases, no animation blending/layering support, and incomplete Blender 5.0 compatibility for the new layered actions system.

---

## 2. Existing Code Inventory

### 2.1 Blender Scripts (D:\Projects\comfyui-mcp-server\scripts\)

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `blender_autorig.py` | Auto-rigging (humanoid, biped_simple, quadruped, simple, custom) | 634 | Mature |
| `blender_animate.py` | Procedural animation (walk, run, idle, wave, jump, nod, look_around) | 1211 | Mature |
| `blender_mocap_import.py` | BVH/FBX mocap import + retargeting | 402 | Functional |
| `animate_unirig.py` | Walk animation for UniRig bone_N naming convention | 186 | Limited (walk only) |
| `apply_animation.py` | Generic walk cycle with RigBones helper | 301 | Redundant |
| `run_animate.py` | Hardcoded walk animation with raw bone_N references | 143 | Prototype/test |

### 2.2 Blender Addon (D:\Projects\comfyui-mcp-server\blender_addon\__init__.py)

- **Version:** 1.1.0
- **Blender Compatibility:** 4.0+
- **UI Panels:** Main, Auto-Rigging, Animation, Mocap Import, Export
- **Operators:** auto_rig, generate_animation, import_mocap, export_model
- **Animation Generators:** All 7 types duplicated from blender_animate.py
- **Easing Functions:** 6 functions (sine, quad, elastic, back, smooth_step, lerp)

### 2.3 Integration Managers

| File | Purpose |
|------|---------|
| `managers/external_app_manager.py` | Orchestrates Blender subprocess calls for rig/animate/mocap |
| `managers/unirig_client.py` | UniRig AI rigging via subprocess (conda env support) |
| `managers/tripo_client.py` | Tripo3D cloud API for rigging + 8 animation presets |

### 2.4 MCP Tool Definitions (tools/external.py)

Registered tools: `auto_rig_model`, `list_rig_types`, `animate_model`, `list_animation_types`, `import_mocap`, `smart_rig_model`, `get_rigging_backends`, `tripo_rig_and_animate`, `list_tripo_animations`

---

## 3. Available Rigging Methods

| Method | Quality | Speed | Availability | Notes |
|--------|---------|-------|-------------|-------|
| **Rigify** (Blender built-in) | Good | Fast | Always | Humanoid metarig, generates IK/FK controls |
| **UniRig AI** (VAST-AI) | Best | 1-5s | Requires install | 215% accuracy improvement, SIGGRAPH 2025 |
| **Tripo3D Cloud** | Good | 10-30s | API key needed | Cloud service, supports animation presets |
| **Biped Simple** (manual) | Basic | Instant | Always | Proportional bone placement, basic IK |
| **Quadruped** (manual) | Basic | Instant | Always | 4-legged rig with tail |
| **Simple/Custom** (manual) | Minimal | Instant | Always | Spine chain or custom bone defs |

**Smart rigging fallback order:** UniRig -> Tripo3D -> Rigify

### 3.1 Rig Types Supported

- Humanoid (Rigify full rig with IK/FK)
- Biped Simple (manual bone placement)
- Quadruped (4-legged animals)
- Simple (bone chain)
- Custom (user-defined bone positions)

---

## 4. Available Animations

### 4.1 Procedural Animations (blender_animate.py + addon)

| Animation | Loop | Duration | Bones Used | Quality |
|-----------|------|----------|------------|---------|
| **Walk** | Yes | 1.0s default | Hips, spine, shoulders, arms, legs, head, neck | High - natural motion with follow-through |
| **Run** | Yes | 0.5s default | Hips, spine, arms, legs, head | High - body lean, pumping arms |
| **Idle** | Yes | 4.0s default | Chest, spine, shoulders, arms, hips, head | Good - breathing + weight shift |
| **Wave** | No | 2.5s default | Right arm, hand, spine, head | Good - anticipation + follow-through |
| **Jump** | No | 1.2s default | Hips, spine, chest, legs, arms, head | High - squash/stretch, elastic landing |
| **Nod** | No | 1.5s default | Head, neck | Good - 3 nods with decreasing intensity |
| **Look Around** | Yes | 4.0s default | Head, neck, spine | Good - sequence with holds |

### 4.2 Tripo3D Animation Presets (Cloud)

| Preset | ID |
|--------|----|
| Idle | preset:idle |
| Walk | preset:walk |
| Run | preset:run |
| Jump | preset:jump |
| Dance | preset:dance |
| Wave | preset:wave |
| Attack | preset:attack |
| Die | preset:die |

### 4.3 Easing Functions Available

- `ease_in_out_sine` - Smooth acceleration/deceleration
- `ease_in_out_quad` - Quadratic ease
- `ease_out_elastic` - Bouncy overshoot
- `ease_out_back` - Slight overshoot
- `ease_in_out_back` - Overshoot both ends
- `smooth_step` - Hermite interpolation
- `lerp` - Linear interpolation

---

## 5. Bone Finding / Retargeting

### 5.1 RigBones Helper Class

The `RigBones` class exists in **three separate copies** (blender_animate.py, apply_animation.py, blender_addon/__init__.py) with slightly different pattern lists. It supports:

- Rigify FK control bones (spine_fk, upper_arm_fk, etc.)
- Standard naming (.L/.R suffixes)
- DEF- prefix bones (deformation bones)
- Case-insensitive matching
- Exact match priority, then partial match fallback
- Caching for performance

### 5.2 Mocap Bone Mapping

- **Mixamo** -> Standard: 20 bone mappings
- **CMU/BVH** -> Standard: 20 bone mappings
- Partial name matching as fallback
- Retargeting: frame-by-frame rotation copy with root location

### 5.3 UniRig Bone Mapping

Separate `BONE_MAP` dict in animate_unirig.py maps semantic names (hips, spine1, etc.) to UniRig's `bone_N` naming convention (22 bones mapped).

---

## 6. Blender Compatibility

### 6.1 Current Support

- **Blender 4.0-4.x:** Fully supported
- **Blender 5.0:** Partially supported via `get_fcurves_from_action()` which handles both legacy fcurves and the new layered action structure (layers -> strips -> channelbags -> fcurves)

### 6.2 Blender 5.0 Layered Actions

The codebase already has basic support for reading fcurves from Blender 5.0's new layered action system. However:
- Currently Blender 5.0 limits to 1 layer and 1 strip per action
- Full layered animation (multiple layers for blending) is not yet exposed in Blender's UI (expected Q2 2026)
- The addon's `bl_info` correctly declares `"blender": (4, 0, 0)` minimum

---

## 7. Identified Issues

### 7.1 Critical: Code Duplication

**The same animation code exists in 3+ places:**
- `blender_animate.py` (standalone script, most complete)
- `blender_addon/__init__.py` (duplicate of all 7 generators)
- `apply_animation.py` (duplicate walk cycle + RigBones)
- `animate_unirig.py` (duplicate walk cycle for UniRig bones)
- `run_animate.py` (hardcoded walk with raw bone names)

**Impact:** Bug fixes or improvements must be applied in 3+ places. The addon's animation generators have slightly different parameter signatures than the standalone scripts.

**Recommendation:** Extract shared animation code into a common module (e.g., `animation_library.py`) that both the standalone scripts and addon can import.

### 7.2 High: Missing Common Animation Types

Animations that are commonly needed but missing:
- **Sit/Stand transitions** - essential for VN characters
- **Talk/Speak** - mouth/jaw + gesture animation
- **Point/Gesture** - directional pointing
- **Crouch** - combat/stealth stance
- **Dance** - Tripo has it, but no procedural version
- **Attack/Combat** - Tripo has it, no procedural version
- **Emote animations** - happy, sad, angry, surprised reactions
- **Pick up / Interact** - object interaction animations
- **Turn in place** - 90/180 degree turns without locomotion

### 7.3 High: No Animation Blending / Layering

- Cannot combine animations (e.g., walk + wave, idle + talk)
- No NLA strip management
- No transition/crossfade between animations
- No additive animation layer support

### 7.4 Medium: UniRig Animation is Walk-Only

`animate_unirig.py` and `run_animate.py` only support walk animation. All other 6 animation types would need separate UniRig-compatible versions, or the bone mapping needs to be integrated into the main RigBones class.

### 7.5 Medium: Mocap Retargeting Limitations

- Frame-by-frame sampling is slow for long animations
- No bone roll/orientation correction during retargeting
- No scale compensation between source and target rigs
- No support for `.c3d` format (common in research mocap)
- Missing retarget preview/validation

### 7.6 Medium: No Animation Preview / Thumbnail Generation

- No way to generate a preview image or turntable video of an animation
- Would be useful for MCP tool responses to show animation results

### 7.7 Low: Addon Auto-Rig Operator is Minimal

The `COMFY_OT_auto_rig` operator just adds a basic armature and parents with auto-weights. It does NOT use the full `blender_autorig.py` logic (humanoid proportions, Rigify metarig, quadruped, etc.). The addon UI exposes rig_type and backend properties but the operator ignores them.

### 7.8 Low: Hardcoded File Paths

`run_animate.py` has hardcoded paths (`C:\comfyui-mcp-server\TripoSG_unirig_rigged.glb`) - appears to be a test script that should be cleaned up or removed.

---

## 8. Improvement Recommendations

### 8.1 Shared Animation Library (Priority: Critical)

Create `D:\Projects\comfyui-mcp-server\scripts\animation_library.py` containing:
- All easing functions
- RigBones class (unified, with UniRig bone_N support integrated)
- All animation generators
- Common keyframe/action utilities

Both `blender_animate.py` and the addon would import from this shared library. Delete `apply_animation.py` and `run_animate.py` as they are redundant.

### 8.2 Expand Animation Library (Priority: High)

Add these procedural animations:
1. **Talk/Speak** - subtle body movement + optional jaw animation
2. **Sit** and **Stand** transitions
3. **Point Left/Right/Forward**
4. **Emote: Happy** (bounce, arms up)
5. **Emote: Sad** (slump, head down)
6. **Emote: Angry** (tense, fists)
7. **Emote: Surprised** (jump back, hands up)
8. **Combat: Attack** (swing/punch)
9. **Combat: Hit React** (stagger)
10. **Turn 90/180** (in-place rotation)

### 8.3 Animation Blending System (Priority: High)

Implement NLA-based animation layering:
- Stack multiple actions as NLA strips
- Support influence/weight per strip
- Crossfade transitions between animations
- Additive layers (e.g., breathing on top of any pose)

### 8.4 UniRig Bone Integration (Priority: Medium)

Extend the RigBones class to detect and map UniRig's `bone_N` naming convention automatically, so all 7+ animation types work with UniRig-rigged models without separate scripts.

### 8.5 Mocap Enhancement (Priority: Medium)

- Add `.c3d` format support
- Implement bone orientation correction in retargeting
- Add scale normalization between source/target
- Batch import support (apply multiple mocaps in sequence)
- Integrate Mixamo FBX download workflow

### 8.6 ComfyUI Animation Nodes Integration (Priority: Medium)

Research and integrate:
- **ComfyUI-UniRig** wrapper node (already exists on GitHub: PozzettiAndrea/ComfyUI-UniRig)
- **Tripo ComfyUI nodes** for rig + animate (TripoRigNode, TripoAnimateRigNode already exist)
- **AnimateDiff** for video-based animation generation
- Potential pipeline: Generate 3D model -> UniRig/Tripo rig -> Procedural animate -> AnimateDiff for video render

### 8.7 Animation Preview System (Priority: Low)

Add turntable render capability:
- Generate a short MP4 preview of any animation
- Create thumbnail images at key poses
- Return preview URLs in MCP tool responses

### 8.8 Blender 5.0 Full Support (Priority: Low - Future)

When Blender 5.0 exposes full layered actions (expected Q2 2026):
- Update animation generators to use new layer API
- Support multiple animation layers per action
- Update NLA integration for new strip system

---

## 9. Architecture Diagram

```
MCP Client Request
        |
        v
  tools/external.py (MCP tool definitions)
        |
        v
  managers/external_app_manager.py
        |
        +--- smart_rig_model() ---> UniRig Client (subprocess)
        |                      ---> Tripo Client (HTTP API)
        |                      ---> Rigify (Blender subprocess)
        |
        +--- auto_rig_model() ---> blender_autorig.py (Blender subprocess)
        |
        +--- animate_model() ---> blender_animate.py (Blender subprocess)
        |
        +--- import_mocap() ---> blender_mocap_import.py (Blender subprocess)
        |
        v
  Blender Addon (interactive UI in Blender)
        |
        +--- COMFY_OT_auto_rig (simplified)
        +--- COMFY_OT_generate_animation (full 7 types)
        +--- COMFY_OT_import_mocap (BVH/FBX)
        +--- COMFY_OT_export_model (GLB/FBX/BLEND)
```

---

## 10. File-by-File Summary

### Scripts to Keep & Improve
- `blender_autorig.py` - Keep as-is, solid implementation
- `blender_animate.py` - Refactor to use shared library
- `blender_mocap_import.py` - Keep, add .c3d support and improve retargeting

### Scripts to Consolidate / Remove
- `apply_animation.py` - **Remove** (redundant with blender_animate.py)
- `animate_unirig.py` - **Remove** after integrating bone_N mapping into RigBones
- `run_animate.py` - **Remove** (test script with hardcoded paths)

### New Files to Create
- `scripts/animation_library.py` - Shared animation module
- `scripts/animation_blend.py` - NLA blending utilities (future)

---

## 11. Conclusion

The animation/rigging pipeline has a strong foundation with support for 3 rigging backends, 7 animation types, mocap import, and a Blender addon. The main improvements needed are:

1. **Eliminate code duplication** by creating a shared animation library
2. **Add more animation types** (talk, sit, emotes, combat)
3. **Implement animation blending** for combining actions
4. **Integrate UniRig bone mapping** into the universal RigBones class
5. **Connect ComfyUI-UniRig and Tripo nodes** for end-to-end workflows

The pipeline is production-ready for basic rigging and simple animation workflows. The recommended improvements would make it suitable for full character animation pipelines including game assets, VN characters, and video production.
