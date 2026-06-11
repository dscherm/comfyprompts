"""Retarget CMU Motion Capture BVH data to UniRig-rigged GLB models.

Blender script -- run via:
    blender --background --python retarget_mocap.py -- \\
        --input input_rigged.glb \\
        --bvh walk.bvh \\
        --action-name walk \\
        --output output.glb \\
        [--cyclic] \\
        [--trim-start 0] \\
        [--trim-end 0] \\
        [--scale 1.0]

Or list both skeleton hierarchies for debugging:
    blender --background --python retarget_mocap.py -- \\
        --input model_rigged.glb --bvh walk.bvh --list-bones

Retargets BVH mocap from the CMU Motion Capture Database
(https://mocap.cs.cmu.edu/) onto UniRig-rigged character models.

Approach:
1. Import the rigged GLB and auto-detect its bone topology (same as animate_unirig.py)
2. Import the BVH file as a separate armature
3. Build a semantic mapping: CMU bone names -> roles -> UniRig bone names
4. Sample each frame: read CMU bone transforms, apply rotation offsets,
   write to UniRig bones (with scale correction for root translation)
5. Push the retargeted action as an NLA track and export as GLB

CMU BVH Skeleton (MotionBuilder-friendly naming by B. Hahne):
    Hips
    +-- LHipJoint -> LeftUpLeg -> LeftLeg -> LeftFoot -> LeftToeBase
    +-- RHipJoint -> RightUpLeg -> RightLeg -> RightFoot -> RightToeBase
    +-- LowerBack -> Spine -> Spine1
        +-- Neck -> Neck1 -> Head
        +-- LeftShoulder -> LeftArm -> LeftForeArm -> LeftHand -> ...
        +-- RightShoulder -> RightArm -> RightForeArm -> RightHand -> ...

CMU Database Quick Reference (freely available, no restrictions):
    Walk:      35_01, 16_15, 02_01, 07_01, 08_01
    Run:       09_01, 16_35, 35_17
    Swordplay: 02_07, 02_08, 02_09
    Punch:     02_05, 76_01
    Standing:  77_02
    Fall:      85_15, 90_16
    Dodge:     76_03, 77_09

BVH files: https://github.com/una-dinosauria/cmu-mocap/tree/master/data
(originally from cgspeed.com, converted by B. Hahne from CMU ASF/AMC)

Data is free for research and commercial use per CMU:
"The data used in this project was obtained from mocap.cs.cmu.edu.
The database was created with funding from NSF EIA-0196217."
"""

import bpy
import math
import sys
import argparse
import traceback
from mathutils import Vector, Euler, Matrix, Quaternion


# ============================================================
# CMU BVH bone name -> semantic role mapping
# ============================================================

# Maps CMU MotionBuilder-friendly BVH bone names to the same semantic
# role names used by animate_unirig.py's detect_bone_map().
CMU_BONE_TO_ROLE = {
    'Hips':           'hips',
    # Legs -- LHipJoint/RHipJoint are zero-offset connectors with no keyframes
    'LHipJoint':      None,          # skip (no data)
    'LeftUpLeg':      'thigh_l',
    'LeftLeg':        'shin_l',
    'LeftFoot':       'foot_l',
    'LeftToeBase':    'toe_l',
    'RHipJoint':      None,          # skip (no data)
    'RightUpLeg':     'thigh_r',
    'RightLeg':       'shin_r',
    'RightFoot':      'foot_r',
    'RightToeBase':   'toe_r',
    # Spine
    'LowerBack':      'spine1',      # CMU LowerBack = same pos as Hips
    'Spine':          'spine2',
    'Spine1':         'chest',       # CMU Spine1 = thorax area
    # Neck / Head
    'Neck':           'neck',
    'Neck1':          None,          # skip -- UniRig has single neck bone
    'Head':           'head',
    # Arms
    'LeftShoulder':   'shoulder_l',
    'LeftArm':        'upper_arm_l',
    'LeftForeArm':    'forearm_l',
    'LeftHand':       'hand_l',
    'RightShoulder':  'shoulder_r',
    'RightArm':       'upper_arm_r',
    'RightForeArm':   'forearm_r',
    'RightHand':      'hand_r',
    # Fingers/thumbs -- CMU has no real data for these, skip
    'LeftFingerBase':  None,
    'LeftHandIndex1':  None,
    'LFingers':        None,
    'LThumb':          None,
    'RightFingerBase': None,
    'RightHandIndex1': None,
    'RFingers':        None,
    'RThumb':          None,
}


# ============================================================
# UniRig bone topology detection (from animate_unirig.py)
# ============================================================

def detect_bone_map(armature):
    """Analyze bone hierarchy and rest positions to build a semantic bone map.

    Returns a dict mapping role names to bone names, e.g.:
        {'hips': 'bone_0', 'spine1': 'bone_1', 'thigh_r': 'bone_49', ...}
    """
    bones = armature.data.bones
    if len(bones) == 0:
        return {}

    root = None
    for b in bones:
        if b.parent is None:
            root = b
            break
    if root is None:
        return {}

    all_heads = [b.head_local for b in bones]
    z_range = max(h.z for h in all_heads) - min(h.z for h in all_heads)
    y_range = max(h.y for h in all_heads) - min(h.y for h in all_heads)

    if z_range >= y_range:
        def height(bone): return bone.head_local.z
        def lateral(bone): return bone.head_local.x
        def depth(bone): return bone.head_local.y
    else:
        def height(bone): return bone.head_local.y
        def lateral(bone): return bone.head_local.x
        def depth(bone): return bone.head_local.z

    def children_of(bone):
        return [b for b in bones if b.parent == bone]

    def longest_chain(bone, max_depth=20):
        kids = children_of(bone)
        if not kids or max_depth <= 0:
            return [bone]
        best = []
        for kid in kids:
            chain = longest_chain(kid, max_depth - 1)
            if len(chain) > len(best):
                best = chain
        return [bone] + best

    def find_chains(bone, min_len=2, max_depth=20):
        kids = children_of(bone)
        chains = []
        for kid in kids:
            chain = longest_chain(kid, max_depth)
            if len(chain) >= min_len:
                chains.append(chain)
        return chains

    bone_map = {}

    hips = root
    root_kids = children_of(root)
    if len(root_kids) == 1:
        hips = root_kids[0]
        bone_map['hips'] = root.name
    else:
        bone_map['hips'] = root.name

    hip_base = hips if hips != root else root
    hip_kids = children_of(hip_base)
    hips_height = height(hip_base)

    up_chains = []
    down_chains = []

    for kid in hip_kids:
        chain = longest_chain(kid)
        chain_top = max(height(b) for b in chain)
        if chain_top > hips_height + 0.01:
            up_chains.append(chain)
        else:
            down_chains.append(chain)

    if len(down_chains) < 2:
        all_chains = find_chains(hip_base, min_len=2)
        for chain in all_chains:
            if chain not in up_chains and chain not in down_chains:
                if len(chain) >= 3:
                    down_chains.append(chain)

    spine_chain = []
    if up_chains:
        up_chains.sort(key=len, reverse=True)
        spine_chain = up_chains[0]

    if len(spine_chain) >= 1:
        bone_map['spine1'] = spine_chain[0].name
    if len(spine_chain) >= 2:
        bone_map['spine2'] = spine_chain[1].name
    if len(spine_chain) >= 3:
        bone_map['chest'] = spine_chain[2].name

    chest_bone = None
    if 'chest' in bone_map:
        chest_bone = bones[bone_map['chest']]
    elif 'spine2' in bone_map:
        chest_bone = bones[bone_map['spine2']]

    if chest_bone:
        chest_kids = children_of(chest_bone)
        arm_candidates = []
        neck_candidate = None
        neck_height = -999

        for kid in chest_kids:
            kid_chain = longest_chain(kid)
            avg_lateral = abs(lateral(kid_chain[-1]) - lateral(chest_bone)) if len(kid_chain) > 0 else 0
            chain_height = height(kid_chain[-1]) if kid_chain else height(kid)

            if chain_height > neck_height and avg_lateral < 0.1:
                if neck_candidate is not None:
                    arm_candidates.append(neck_candidate)
                neck_candidate = kid_chain
                neck_height = chain_height
            else:
                arm_candidates.append(kid_chain)

        if neck_candidate and len(neck_candidate) >= 1:
            bone_map['neck'] = neck_candidate[0].name
            if len(neck_candidate) >= 2:
                bone_map['head'] = neck_candidate[1].name

        if len(arm_candidates) >= 2:
            arm_candidates.sort(key=lambda chain: lateral(chain[0]))
            arm_l_chain = arm_candidates[0]
            arm_r_chain = arm_candidates[-1]
            _map_arm(bone_map, arm_r_chain, '_r')
            _map_arm(bone_map, arm_l_chain, '_l')
        elif len(arm_candidates) == 1:
            chain = arm_candidates[0]
            if lateral(chain[0]) > lateral(chest_bone):
                _map_arm(bone_map, chain, '_r')
            else:
                _map_arm(bone_map, chain, '_l')

    if len(down_chains) >= 2:
        down_chains.sort(key=lambda chain: lateral(chain[0]))
        leg_l = down_chains[0]
        leg_r = down_chains[-1]
        _map_leg(bone_map, leg_r, '_r')
        _map_leg(bone_map, leg_l, '_l')
    elif len(down_chains) == 1:
        chain = down_chains[0]
        if lateral(chain[0]) > lateral(hip_base):
            _map_leg(bone_map, chain, '_r')
        else:
            _map_leg(bone_map, chain, '_l')

    return bone_map


def _map_arm(bone_map, chain, suffix):
    if len(chain) >= 1:
        bone_map[f'shoulder{suffix}'] = chain[0].name
    if len(chain) >= 2:
        bone_map[f'upper_arm{suffix}'] = chain[1].name
    if len(chain) >= 3:
        bone_map[f'forearm{suffix}'] = chain[2].name
    if len(chain) >= 4:
        bone_map[f'hand{suffix}'] = chain[3].name


def _map_leg(bone_map, chain, suffix):
    if len(chain) >= 1:
        bone_map[f'thigh{suffix}'] = chain[0].name
    if len(chain) >= 2:
        bone_map[f'shin{suffix}'] = chain[1].name
    if len(chain) >= 3:
        bone_map[f'foot{suffix}'] = chain[2].name
    if len(chain) >= 4:
        bone_map[f'toe{suffix}'] = chain[3].name


# ============================================================
# Rest-pose-aware retargeting
# ============================================================

def compute_rest_rotation(pose_bone):
    """Get the rest-pose rotation of a bone in world space."""
    if pose_bone.bone.parent:
        parent_mat = pose_bone.bone.parent.matrix_local
        bone_mat = pose_bone.bone.matrix_local
        rest_rot = (parent_mat.inverted() @ bone_mat).to_quaternion()
    else:
        rest_rot = pose_bone.bone.matrix_local.to_quaternion()
    return rest_rot


def build_retarget_map(cmu_armature, unirig_armature, unirig_bone_map):
    """Build the final bone-to-bone mapping with rest-pose offset corrections.

    Returns list of tuples:
        (cmu_pose_bone, unirig_pose_bone, rest_offset_quat, is_root)
    """
    # Invert unirig_bone_map: role -> unirig_bone_name
    role_to_unirig = unirig_bone_map  # already role -> bone_name

    mapping = []
    for cmu_bone in cmu_armature.pose.bones:
        role = CMU_BONE_TO_ROLE.get(cmu_bone.name)
        if role is None:
            continue

        unirig_bone_name = role_to_unirig.get(role)
        if unirig_bone_name is None:
            continue

        unirig_bone = unirig_armature.pose.bones.get(unirig_bone_name)
        if unirig_bone is None:
            continue

        # Compute rest-pose offset between CMU and UniRig for this bone.
        # retarget formula: unirig_pose = offset * cmu_pose
        # where offset = unirig_rest * cmu_rest.inverted()
        cmu_rest = compute_rest_rotation(cmu_bone)
        unirig_rest = compute_rest_rotation(unirig_bone)
        rest_offset = unirig_rest @ cmu_rest.inverted()

        is_root = (role == 'hips')
        mapping.append((cmu_bone, unirig_bone, rest_offset, is_root))

    return mapping


# ============================================================
# Frame sampling and keyframe writing
# ============================================================

def get_fcurves_from_action(action):
    """Get fcurves from an action, handling both legacy and layered actions."""
    if hasattr(action, 'fcurves') and action.fcurves:
        return list(action.fcurves)
    if hasattr(action, 'layers') and action.layers:
        fcurves = []
        for layer in action.layers:
            if hasattr(layer, 'strips'):
                for strip in layer.strips:
                    if hasattr(strip, 'channelbags'):
                        for channelbag in strip.channelbags:
                            if hasattr(channelbag, 'fcurves'):
                                fcurves.extend(channelbag.fcurves)
        return fcurves
    return []


def set_interpolation(action, interpolation='BEZIER'):
    """Set interpolation type for all keyframes in an action."""
    fcurves = get_fcurves_from_action(action)
    for fcurve in fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = interpolation
            if interpolation == 'BEZIER':
                keyframe.handle_left_type = 'AUTO_CLAMPED'
                keyframe.handle_right_type = 'AUTO_CLAMPED'


def make_cyclic(action):
    """Add CYCLES modifier to all fcurves for seamless looping."""
    fcurves = get_fcurves_from_action(action)
    for fcurve in fcurves:
        mod = fcurve.modifiers.new(type='CYCLES')
        mod.mode_before = 'REPEAT'
        mod.mode_after = 'REPEAT'


def push_to_nla(armature, action, track_name):
    """Push current action to NLA track."""
    if not armature.animation_data:
        armature.animation_data_create()
    track = armature.animation_data.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(track_name, int(action.frame_range[0]), action)
    strip.name = track_name
    armature.animation_data.action = None


def retarget_bvh_to_unirig(cmu_armature, unirig_armature, unirig_bone_map,
                             action_name, scale_factor, cyclic, trim_start, trim_end):
    """Sample CMU armature animation and write retargeted keyframes to UniRig armature.

    Args:
        cmu_armature: Blender armature object with BVH animation
        unirig_armature: Blender armature object (target GLB character)
        unirig_bone_map: dict from detect_bone_map() {role: bone_name}
        action_name: name for the output NLA track (e.g. 'walk', 'run')
        scale_factor: multiplier for root translation (CMU is in inches ~2.54cm)
        cyclic: if True, add CYCLES fcurve modifier
        trim_start: number of frames to skip at beginning
        trim_end: number of frames to skip at end
    """
    # Get source action
    if not cmu_armature.animation_data or not cmu_armature.animation_data.action:
        raise RuntimeError("CMU armature has no animation action")

    source_action = cmu_armature.animation_data.action
    src_start = int(source_action.frame_range[0])
    src_end = int(source_action.frame_range[1])

    # CMU BVH frame 0 is the T-pose (added by B. Hahne), skip it
    # Frame 1 onward is actual motion data
    effective_start = max(src_start + 1, src_start + trim_start)
    effective_end = max(effective_start + 1, src_end - trim_end)
    num_frames = effective_end - effective_start + 1

    print(f"  Source frames: {src_start}-{src_end} ({src_end - src_start + 1} total)")
    print(f"  Effective range: {effective_start}-{effective_end} ({num_frames} frames)")

    # Build mapping
    mapping = build_retarget_map(cmu_armature, unirig_armature, unirig_bone_map)
    print(f"  Mapped {len(mapping)} bones:")
    for cmu_b, uni_b, _, is_root in mapping:
        root_tag = " (ROOT)" if is_root else ""
        print(f"    {cmu_b.name:20s} -> {uni_b.name:12s}{root_tag}")

    if len(mapping) == 0:
        raise RuntimeError("No bone mappings found -- check skeleton compatibility")

    # Reset UniRig pose
    for pb in unirig_armature.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
        pb.location = Vector((0, 0, 0))

    # Create new action
    action = bpy.data.actions.new(name=action_name)
    if not unirig_armature.animation_data:
        unirig_armature.animation_data_create()
    unirig_armature.animation_data.action = action

    # Set scene frame range
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = num_frames

    # Compute CMU skeleton total height for scale normalization.
    # Sum hip-to-head chain length from rest pose offsets.
    cmu_height = 0
    unirig_height = 0
    for b in cmu_armature.data.bones:
        if b.name in ('Hips', 'LowerBack', 'Spine', 'Spine1', 'Neck', 'Neck1', 'Head'):
            cmu_height += b.length
    for role in ('hips', 'spine1', 'spine2', 'chest', 'neck', 'head'):
        bname = unirig_bone_map.get(role)
        if bname and bname in unirig_armature.data.bones:
            unirig_height += unirig_armature.data.bones[bname].length

    if cmu_height > 0 and unirig_height > 0:
        height_ratio = unirig_height / cmu_height
    else:
        height_ratio = scale_factor

    print(f"  CMU spine height: {cmu_height:.3f}, UniRig spine height: {unirig_height:.3f}")
    print(f"  Height ratio: {height_ratio:.4f}, user scale: {scale_factor}")

    root_scale = height_ratio * scale_factor

    # Sample each frame
    for frame_idx in range(num_frames):
        src_frame = effective_start + frame_idx
        dst_frame = frame_idx + 1

        # Set scene to source frame so CMU bones evaluate
        bpy.context.scene.frame_set(src_frame)

        for cmu_bone, unirig_bone, rest_offset, is_root in mapping:
            # Read CMU bone's current pose rotation
            if cmu_bone.rotation_mode == 'QUATERNION':
                cmu_rot = cmu_bone.rotation_quaternion.copy()
            else:
                cmu_rot = cmu_bone.rotation_euler.to_quaternion()

            # Apply rest-pose offset: target_rot = offset * source_rot
            retargeted_rot = rest_offset @ cmu_rot

            # Write to UniRig bone
            unirig_bone.rotation_mode = 'QUATERNION'
            unirig_bone.rotation_quaternion = retargeted_rot
            unirig_bone.keyframe_insert(data_path='rotation_quaternion', frame=dst_frame)

            # Root translation (hips only)
            if is_root:
                loc = cmu_bone.location.copy()
                # Scale CMU translation to UniRig proportions
                unirig_bone.location = loc * root_scale
                unirig_bone.keyframe_insert(data_path='location', frame=dst_frame)

    # Post-process
    set_interpolation(action, 'BEZIER')
    if cyclic:
        make_cyclic(action)

    push_to_nla(unirig_armature, action, action_name)

    print(f"  Created NLA track '{action_name}' ({num_frames} frames)")
    return action


# ============================================================
# CLI and main
# ============================================================

def parse_args():
    """Parse command-line arguments after Blender's -- separator."""
    argv = sys.argv
    try:
        idx = argv.index("--") + 1
        script_args = argv[idx:]
    except ValueError:
        script_args = []

    parser = argparse.ArgumentParser(
        description="Retarget CMU BVH mocap to UniRig-rigged GLB"
    )
    # --input and --glb are aliases (task spec uses --input, original uses --glb)
    glb_group = parser.add_mutually_exclusive_group(required=True)
    glb_group.add_argument("--input", dest="glb", help="Input rigged GLB file")
    glb_group.add_argument("--glb", dest="glb", help="Input rigged GLB file (alias for --input)")
    parser.add_argument("--bvh", required=True, help="Input BVH mocap file")
    # --action-name and --action are aliases
    parser.add_argument("--action-name", "--action", dest="action", default="mocap",
                        help="NLA track name (default: mocap)")
    parser.add_argument("--output", default=None,
                        help="Output GLB file path (required unless --list-bones)")
    parser.add_argument("--cyclic", action="store_true", help="Make animation loop")
    parser.add_argument("--trim-start", type=int, default=0,
                        help="Skip N frames from start (after T-pose)")
    parser.add_argument("--trim-end", type=int, default=0,
                        help="Skip N frames from end")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="Additional root translation scale (default: 1.0)")
    parser.add_argument("--fps", type=int, default=30,
                        help="Output FPS (CMU is 120fps, default resample to 30)")
    parser.add_argument("--list-bones", action="store_true",
                        help="Dump both skeleton bone hierarchies and exit (no output written)")

    return parser.parse_args(script_args)


def print_bone_tree(armature, label="Skeleton"):
    """Print an indented bone hierarchy for debugging (--list-bones)."""
    bones = armature.data.bones
    print(f"\n{'='*60}")
    print(f"  {label}: {armature.name} ({len(bones)} bones)")
    print(f"{'='*60}")

    def _recurse(bone, depth=0):
        indent = "  " * (depth + 1)
        pos = bone.head_local
        print(f"{indent}{bone.name:30s}  pos=({pos.x:+.4f}, {pos.y:+.4f}, {pos.z:+.4f})")
        for child in bone.children:
            _recurse(child, depth + 1)

    roots = [b for b in bones if b.parent is None]
    for root in roots:
        _recurse(root)
    print()


def main():
    args = parse_args()

    if not args.list_bones and not args.output:
        print("ERROR: --output is required (unless using --list-bones)")
        sys.exit(1)

    print("=" * 60)
    print("CMU Mocap -> UniRig Retargeter")
    print("=" * 60)
    print(f"  GLB:        {args.glb}")
    print(f"  BVH:        {args.bvh}")
    print(f"  Action:     {args.action}")
    print(f"  Output:     {args.output}")
    print(f"  Cyclic:     {args.cyclic}")
    print(f"  Scale:      {args.scale}")
    print(f"  FPS:        {args.fps}")
    print(f"  List bones: {args.list_bones}")
    print()

    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = args.fps

    # Step 1: Import the rigged GLB
    print("[1/5] Importing rigged GLB...")
    bpy.ops.import_scene.gltf(filepath=args.glb)

    unirig_armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            unirig_armature = obj
            break

    if not unirig_armature:
        print("ERROR: No armature found in GLB")
        sys.exit(1)

    bone_count = len(unirig_armature.data.bones)
    print(f"  Armature: {unirig_armature.name} ({bone_count} bones)")

    # Step 2: Detect UniRig bone topology
    print("\n[2/5] Detecting UniRig bone topology...")
    unirig_bone_map = detect_bone_map(unirig_armature)
    print(f"  Detected {len(unirig_bone_map)} roles:")
    for role, bone_name in sorted(unirig_bone_map.items()):
        print(f"    {role:20s} -> {bone_name}")

    essential = ['hips', 'spine1', 'chest', 'upper_arm_r', 'upper_arm_l', 'thigh_r', 'thigh_l']
    missing = [r for r in essential if r not in unirig_bone_map]
    if missing:
        print(f"  WARNING: Missing essential roles: {missing}")

    # Clear any existing animation on the UniRig armature
    if unirig_armature.animation_data:
        unirig_armature.animation_data_clear()

    # Step 3: Import BVH mocap
    print("\n[3/5] Importing BVH mocap...")
    bpy.ops.import_anim.bvh(
        filepath=args.bvh,
        filter_glob="*.bvh",
        target='ARMATURE',
        global_scale=1.0,
        frame_start=0,
        use_fps_scale=True,    # Resample from 120fps to scene fps
        update_scene_fps=False,
        update_scene_duration=True,
        use_cyclic=False,
        rotate_mode='NATIVE',
    )

    cmu_armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj != unirig_armature:
            cmu_armature = obj
            break

    if not cmu_armature:
        print("ERROR: BVH import failed -- no new armature created")
        sys.exit(1)

    cmu_bone_count = len(cmu_armature.data.bones)
    print(f"  CMU Armature: {cmu_armature.name} ({cmu_bone_count} bones)")

    # List CMU bones for diagnostics
    print("  CMU bones:")
    for b in cmu_armature.data.bones:
        role = CMU_BONE_TO_ROLE.get(b.name, '???')
        print(f"    {b.name:25s} -> role: {role}")

    # --list-bones: dump both hierarchies with semantic maps and exit
    if args.list_bones:
        print_bone_tree(unirig_armature, "TARGET (UniRig)")
        print_bone_tree(cmu_armature, "SOURCE (CMU BVH)")

        print(f"\nUniRig auto-detected semantic map ({len(unirig_bone_map)} roles):")
        for role, bone_name in sorted(unirig_bone_map.items()):
            print(f"  {role:20s} -> {bone_name}")

        print(f"\nCMU BVH bones -> semantic roles:")
        for b in cmu_armature.data.bones:
            role = CMU_BONE_TO_ROLE.get(b.name, '(not in map)')
            skip = " [SKIP]" if role is None else ""
            print(f"  {b.name:25s} -> {role}{skip}")

        print(f"\nFinal retarget mapping:")
        mapping = build_retarget_map(cmu_armature, unirig_armature, unirig_bone_map)
        for cmu_b, uni_b, _, is_root in mapping:
            root_tag = " (ROOT)" if is_root else ""
            print(f"  {cmu_b.name:20s} -> {uni_b.name:12s}{root_tag}")

        print(f"\nDone (--list-bones mode, no output written)")
        return

    # Step 4: Retarget
    print(f"\n[4/5] Retargeting '{args.action}'...")
    retarget_bvh_to_unirig(
        cmu_armature=cmu_armature,
        unirig_armature=unirig_armature,
        unirig_bone_map=unirig_bone_map,
        action_name=args.action,
        scale_factor=args.scale,
        cyclic=args.cyclic,
        trim_start=args.trim_start,
        trim_end=args.trim_end,
    )

    # Remember the CMU action name so we can delete it
    cmu_action_name = None
    if cmu_armature.animation_data and cmu_armature.animation_data.action:
        cmu_action_name = cmu_armature.animation_data.action.name

    # Delete the CMU armature (no longer needed)
    bpy.ops.object.select_all(action='DESELECT')
    cmu_armature.select_set(True)
    bpy.context.view_layer.objects.active = cmu_armature
    bpy.ops.object.delete()

    # Clean up the leftover CMU BVH action from bpy.data.actions
    # (Otherwise the glTF exporter warns about CMU bone names not found)
    if cmu_action_name and cmu_action_name in bpy.data.actions:
        cmu_action = bpy.data.actions[cmu_action_name]
        bpy.data.actions.remove(cmu_action)
        print(f"  Cleaned up leftover CMU action: {cmu_action_name}")

    # Also remove any other orphaned actions with CMU bone references
    actions_to_remove = []
    for act in bpy.data.actions:
        # Skip our retargeted actions (they reference UniRig bone_N names)
        if any(fc.data_path.startswith('pose.bones["bone_') for fc in get_fcurves_from_action(act)):
            continue
        # If an action references CMU bone names, remove it
        fcurves = get_fcurves_from_action(act)
        if fcurves and any('pose.bones["Hips"]' in fc.data_path or
                           'pose.bones["LeftUpLeg"]' in fc.data_path or
                           'pose.bones["RightUpLeg"]' in fc.data_path
                           for fc in fcurves):
            actions_to_remove.append(act)
    for act in actions_to_remove:
        print(f"  Removing orphaned CMU action: {act.name}")
        bpy.data.actions.remove(act)

    # Clear active action (all anims in NLA tracks)
    if unirig_armature.animation_data:
        unirig_armature.animation_data.action = None

    # Step 5: Export
    print(f"\n[5/5] Exporting to: {args.output}")
    bpy.ops.export_scene.gltf(
        filepath=args.output,
        export_format='GLB',
        export_animations=True,
        export_skins=True,
        export_nla_strips=True,
        export_current_frame=False,
    )

    print("\nDONE -- Retargeted mocap exported successfully")


# ============================================================
# Entry point
# ============================================================

try:
    main()
except SystemExit:
    raise
except Exception as e:
    print(f"\nFATAL ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
