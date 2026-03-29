"""Apply 6 procedural animations to UniRig-rigged GLB models.

Blender script -- run via:
    blender --background --python animate_unirig.py -- input.glb output.glb

Creates 6 NLA tracks matching Godot ModelRenderer scan names:
    idle, walk, run, attack_1, hit_reaction, death

Auto-detects skeleton topology from bone hierarchy and rest positions.
Works with any UniRig bone count (22-bone simple to 60+ detailed).

Interpolation quality: Uses Bezier curves with AUTO_CLAMPED handles for
smooth motion, plus easing functions (sine, quadratic, elastic, back) ported
from the ComfyUI Blender addon for physically plausible acceleration curves.
"""

import bpy
import math
import sys
import traceback
from mathutils import Vector, Euler

# --- Parse CLI args ---
argv = sys.argv
input_glb = None
output_glb = None
try:
    idx = argv.index("--") + 1
    if idx < len(argv):
        input_glb = argv[idx]
    if idx + 1 < len(argv):
        output_glb = argv[idx + 1]
except ValueError:
    pass

if not input_glb or not output_glb:
    print("Usage: blender --background --python animate_unirig.py -- input.glb output.glb")
    sys.exit(1)

# --- Constants ---
FPS = 30


# ============================================================
# Easing & interpolation functions
# (ported from blender/comfyui_tools/utils.py — standalone,
#  no addon imports needed for headless Blender)
# ============================================================

def ease_in_out_sine(t):
    """Sine ease in/out -- smooth acceleration and deceleration."""
    return -(math.cos(math.pi * t) - 1) / 2


def ease_in_out_quad(t):
    """Quadratic ease in/out."""
    if t < 0.5:
        return 2 * t * t
    return 1 - pow(-2 * t + 2, 2) / 2


def ease_out_elastic(t):
    """Elastic ease out -- bouncy overshoot."""
    if t == 0 or t == 1:
        return t
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1


def ease_out_back(t):
    """Back ease out -- slight overshoot past target."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def smooth_step(t):
    """Hermite smooth step (3t^2 - 2t^3)."""
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    """Linear interpolation between a and b."""
    return a + (b - a) * t


# ============================================================
# Auto-detect skeleton topology
# ============================================================

def detect_bone_map(armature):
    """Analyze bone hierarchy and rest positions to build a semantic bone map.

    Returns a dict mapping role names to bone names, e.g.:
        {'hips': 'bone_0', 'spine1': 'bone_1', 'thigh_r': 'bone_49', ...}
    """
    bones = armature.data.bones
    if len(bones) == 0:
        return {}

    # Find root bone (no parent)
    root = None
    for b in bones:
        if b.parent is None:
            root = b
            break
    if root is None:
        return {}

    # Helper: get bone vertical position (rest pose, head position)
    # Blender uses Z-up by default for imported models, but some GLBs use Y-up
    # Detect orientation: check if model extends more in Y or Z
    all_heads = [b.head_local for b in bones]
    z_range = max(h.z for h in all_heads) - min(h.z for h in all_heads)
    y_range = max(h.y for h in all_heads) - min(h.y for h in all_heads)

    if z_range >= y_range:
        # Z-up (standard Blender)
        def height(bone): return bone.head_local.z
        def lateral(bone): return bone.head_local.x
        def depth(bone): return bone.head_local.y
    else:
        # Y-up (some GLB imports)
        def height(bone): return bone.head_local.y
        def lateral(bone): return bone.head_local.x
        def depth(bone): return bone.head_local.z

    # Helper: get children of a bone
    def children_of(bone):
        return [b for b in bones if b.parent == bone]

    # Helper: find longest chain from a bone (depth-first)
    def longest_chain(bone, max_depth=20):
        """Returns list of bones in the longest chain starting from bone."""
        kids = children_of(bone)
        if not kids or max_depth <= 0:
            return [bone]
        best = []
        for kid in kids:
            chain = longest_chain(kid, max_depth - 1)
            if len(chain) > len(best):
                best = chain
        return [bone] + best

    # Helper: find all chains of length >= min_len branching from bone
    def find_chains(bone, min_len=2, max_depth=20):
        """Returns list of chains (each chain is a list of bones)."""
        kids = children_of(bone)
        chains = []
        for kid in kids:
            chain = longest_chain(kid, max_depth)
            if len(chain) >= min_len:
                chains.append(chain)
        return chains

    bone_map = {}

    # Helper: compute bone rest-pose length
    def bone_length(bone):
        return (bone.tail_local - bone.head_local).length

    # --- Step 1: Find hips ---
    # Walk down single-child chains from root until we find the real hip pivot.
    # The real hips is where the skeleton branches into spine + legs.
    # A root bone that is disproportionately long (e.g. spanning feet to hips)
    # is just a structural bone, not the actual hip pivot.
    hips = root
    while True:
        kids = children_of(hips)
        if len(kids) != 1:
            break  # hips branches here (or is a leaf)
        child = kids[0]
        # If hips has only 1 child, check if this bone is a "connector" bone:
        # either it's very long relative to its child (structural bone spanning
        # a large distance) or the child is where branching happens
        child_kids = children_of(child)
        if len(child_kids) >= 3:
            # Child branches into spine + 2 legs — child is real hips
            hips = child
            break
        elif len(child_kids) == 1:
            # Another single-child — keep walking
            hips = child
        else:
            # 0 or 2 children but not 3+ — stop here
            break

    bone_map['hips'] = hips.name

    # --- Step 2: From hips, separate upward chain (spine) from downward chains (legs) ---
    hip_base = hips
    hip_kids = children_of(hip_base)
    hips_height = height(hip_base)

    # Classify children as going up (spine) or down/sideways (legs)
    up_chains = []
    down_chains = []

    for kid in hip_kids:
        chain = longest_chain(kid)
        chain_top = max(height(b) for b in chain)
        chain_bot = min(height(b) for b in chain)
        if chain_top > hips_height + 0.01:
            up_chains.append(chain)
        else:
            down_chains.append(chain)

    # If no clear down chains, check all hip children for lateral spread (legs go sideways)
    if len(down_chains) < 2:
        # Re-check: legs might be at same height as hips but spread laterally
        all_chains = find_chains(hip_base, min_len=2)
        for chain in all_chains:
            if chain not in up_chains and chain not in down_chains:
                if len(chain) >= 3:  # legs have at least 3 segments
                    down_chains.append(chain)

    # --- Step 3: Spine chain ---
    spine_chain = []
    if up_chains:
        # Pick the longest upward chain as spine
        up_chains.sort(key=len, reverse=True)
        spine_chain = up_chains[0]

    # Map spine bones
    if len(spine_chain) >= 1:
        bone_map['spine1'] = spine_chain[0].name
    if len(spine_chain) >= 2:
        bone_map['spine2'] = spine_chain[1].name
    if len(spine_chain) >= 3:
        bone_map['chest'] = spine_chain[2].name

    # --- Step 4: From upper spine/chest, find head and arms ---
    chest_bone = None
    if 'chest' in bone_map:
        chest_bone = bones[bone_map['chest']]
    elif 'spine2' in bone_map:
        chest_bone = bones[bone_map['spine2']]

    if chest_bone:
        chest_kids = children_of(chest_bone)
        # Among chest children, the one going most upward = neck
        # The ones going sideways = shoulders/arms
        arm_candidates = []
        neck_candidate = None
        neck_height = -999

        for kid in chest_kids:
            kid_chain = longest_chain(kid)
            avg_lateral = abs(lateral(kid_chain[-1]) - lateral(chest_bone)) if len(kid_chain) > 0 else 0
            chain_height = height(kid_chain[-1]) if kid_chain else height(kid)

            if chain_height > neck_height and avg_lateral < 0.1:
                # Going up = neck/head candidate
                if neck_candidate is not None:
                    arm_candidates.append(neck_candidate)
                neck_candidate = kid_chain
                neck_height = chain_height
            else:
                arm_candidates.append(kid_chain)

        # Map neck and head
        if neck_candidate and len(neck_candidate) >= 1:
            bone_map['neck'] = neck_candidate[0].name
            if len(neck_candidate) >= 2:
                bone_map['head'] = neck_candidate[1].name

        # Map arms — sort by lateral position (right = positive X, left = negative X)
        if len(arm_candidates) >= 2:
            arm_candidates.sort(key=lambda chain: lateral(chain[0]))
            arm_l_chain = arm_candidates[0]  # negative X = left
            arm_r_chain = arm_candidates[-1]  # positive X = right

            _map_arm(bone_map, arm_r_chain, '_r')
            _map_arm(bone_map, arm_l_chain, '_l')
        elif len(arm_candidates) == 1:
            # Only one arm found, determine side
            chain = arm_candidates[0]
            if lateral(chain[0]) > lateral(chest_bone):
                _map_arm(bone_map, chain, '_r')
            else:
                _map_arm(bone_map, chain, '_l')

    # --- Step 5: Legs ---
    if len(down_chains) >= 2:
        # Sort by lateral position
        down_chains.sort(key=lambda chain: lateral(chain[0]))
        leg_l = down_chains[0]   # negative X = left
        leg_r = down_chains[-1]  # positive X = right
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
    """Map an arm chain to shoulder, upper_arm, forearm, hand roles.

    Skips bones with near-zero length (< 0.02) that are structural joints
    rather than actual limb segments, so the mapping doesn't waste a role
    on a bone that has no visual effect when rotated.
    """
    MIN_BONE_LEN = 0.02
    # Filter out near-zero-length bones (keep chain order)
    significant = [b for b in chain if (b.tail_local - b.head_local).length >= MIN_BONE_LEN]
    roles = ['shoulder', 'upper_arm', 'forearm', 'hand']
    for i, role in enumerate(roles):
        if i < len(significant):
            bone_map[f'{role}{suffix}'] = significant[i].name


def _map_leg(bone_map, chain, suffix):
    """Map a leg chain to thigh, shin, foot, toe roles.

    Skips bones with near-zero length (< 0.02) that are structural joints.
    """
    MIN_BONE_LEN = 0.02
    significant = [b for b in chain if (b.tail_local - b.head_local).length >= MIN_BONE_LEN]
    roles = ['thigh', 'shin', 'foot', 'toe']
    for i, role in enumerate(roles):
        if i < len(significant):
            bone_map[f'{role}{suffix}'] = significant[i].name


# ============================================================
# Keyframe helpers
# ============================================================

# Will be set after bone map detection
BONE_MAP = {}

# Per-bone swing axis: 'x' or 'z' — which Euler component produces forward/back swing.
# Detected from bone rest orientation after bone map is built.
SWING_AXIS = {}


def detect_swing_axes(armature):
    """Detect which local axis produces forward/back swing for each mapped bone.

    UniRig skeletons can have bones pointing sideways (T-pose/spread) or downward.
    - Bone pointing mostly sideways (|X| > |Z|): Z rotation = forward/back swing
    - Bone pointing mostly vertical  (|Z| > |X|): X rotation = forward/back swing
    """
    global SWING_AXIS
    SWING_AXIS = {}
    for role, bone_name in BONE_MAP.items():
        data_bone = armature.data.bones.get(bone_name)
        if data_bone is None:
            continue
        # Bone direction = head → tail in armature space
        direction = (data_bone.tail_local - data_bone.head_local).normalized()
        # Check primary component: sideways (X) vs vertical (Z)
        if abs(direction.x) > abs(direction.z):
            SWING_AXIS[role] = 'z'  # bone points sideways → Z rot = swing
        else:
            SWING_AXIS[role] = 'x'  # bone points vertical → X rot = swing


def swing_rot(role, amount):
    """Return rotation tuple that produces forward/back swing for the given bone role.

    Uses detected swing axis to put the rotation on the correct component.
    """
    if SWING_AXIS.get(role, 'x') == 'z':
        return (0, 0, amount)
    return (amount, 0, 0)


def spread_rot(role, amount):
    """Return rotation tuple that produces lateral spread for the given bone role.

    Opposite of swing: if swing is Z, spread is X; if swing is X, spread is Z.
    """
    if SWING_AXIS.get(role, 'x') == 'z':
        return (amount, 0, 0)
    return (0, 0, amount)


def get_bone(armature, role):
    """Get pose bone by semantic role name."""
    bone_name = BONE_MAP.get(role)
    if bone_name and bone_name in armature.pose.bones:
        return armature.pose.bones[bone_name]
    return None


def set_key(bone, frame, rotation=None, location=None):
    """Set keyframe on bone (rotation as Euler XYZ tuple, exported as quaternion).

    Accepts Euler angles for readability but stores as quaternion to avoid
    GLTF export issues (GLTF uses quaternions natively; Euler keyframes get
    collapsed during the Euler->Quaternion conversion in the exporter).
    """
    if rotation is not None:
        bone.rotation_mode = 'QUATERNION'
        quat = Euler(rotation, 'XYZ').to_quaternion()
        bone.rotation_quaternion = quat
        bone.keyframe_insert(data_path='rotation_quaternion', frame=frame)
    if location is not None:
        bone.location = location
        bone.keyframe_insert(data_path='location', frame=frame)


def reset_pose(armature):
    """Reset all pose bones to rest position (quaternion mode for GLTF compat)."""
    for pb in armature.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)  # Identity quaternion
        pb.location = (0, 0, 0)


def create_action(armature, name, num_frames):
    """Create a new action and set it active. Returns (action, num_frames)."""
    reset_pose(armature)
    action = bpy.data.actions.new(name=name)
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = num_frames
    return action


def get_fcurves_from_action(action):
    """Get fcurves from an action, handling both legacy and layered actions.

    Blender 4.x+ introduced layered actions; this helper handles both formats.
    """
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
    """Set interpolation type for all keyframes in an action.

    BEZIER with AUTO_CLAMPED handles produces smooth curves without overshoot,
    which is superior to the default LINEAR interpolation for organic motion.
    """
    fcurves = get_fcurves_from_action(action)
    for fcurve in fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = interpolation
            if interpolation == 'BEZIER':
                keyframe.handle_left_type = 'AUTO_CLAMPED'
                keyframe.handle_right_type = 'AUTO_CLAMPED'


def make_cyclic(action):
    """Make animation curves cyclic for seamless looping.

    Adds CYCLES modifier to all fcurves so the animation repeats smoothly
    without discontinuities at loop boundaries.
    """
    fcurves = get_fcurves_from_action(action)
    for fcurve in fcurves:
        mod = fcurve.modifiers.new(type='CYCLES')
        mod.mode_before = 'REPEAT'
        mod.mode_after = 'REPEAT'


def push_to_nla(armature, action, track_name):
    """Push current action to NLA track so multiple anims can coexist."""
    if not armature.animation_data:
        armature.animation_data_create()
    track = armature.animation_data.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(track_name, int(action.frame_range[0]), action)
    strip.name = track_name
    armature.animation_data.action = None


# ============================================================
# Animation generators (identical logic, use BONE_MAP via get_bone)
# ============================================================

def anim_idle(armature):
    """Subtle breathing idle -- gentle chest rise, slight sway.

    Uses ease_in_out_sine for breathing curve (naturalistic inhale/exhale)
    instead of raw sin(). Bezier interpolation + cyclic modifier for
    seamless looping.
    """
    num_frames = int(2.0 * FPS)  # 2 second loop
    action = create_action(armature, "idle", num_frames)

    # Use fewer keyframes with Bezier interpolation for smoother curves
    num_keys = max(16, num_frames // 4)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (num_frames - 1))
        phase = t * 2 * math.pi
        sway_phase = t * math.pi

        # Breathing uses eased curve instead of raw sin
        breath = ease_in_out_sine(t) * 0.02

        chest = get_bone(armature, 'chest')
        if chest:
            set_key(chest, frame, rotation=(breath * 1.5, 0, 0))

        spine = get_bone(armature, 'spine2')
        if spine:
            set_key(spine, frame, rotation=(breath, 0, math.sin(sway_phase * 0.5) * 0.005))

        head = get_bone(armature, 'head')
        if head:
            look_x = math.sin(sway_phase * 0.7) * 0.015
            look_z = math.sin(sway_phase * 0.5) * 0.015
            set_key(head, frame, rotation=(look_x, 0, look_z))

        neck = get_bone(armature, 'neck')
        if neck:
            set_key(neck, frame, rotation=(0, 0, math.sin(sway_phase * 0.5) * 0.008))

        hips = get_bone(armature, 'hips')
        if hips:
            sway = math.sin(sway_phase) * 0.01
            set_key(hips, frame, location=(sway, 0, 0), rotation=(0, 0, sway * 2))

        # Shoulders rise with breathing
        for side in ['_r', '_l']:
            shoulder = get_bone(armature, f'shoulder{side}')
            if shoulder:
                rise = ease_in_out_sine(t) * 0.01
                set_key(shoulder, frame, rotation=(rise, 0, 0))

        # Subtle weight shift between feet (axis-aware)
        for side, sign in [('_r', 1), ('_l', -1)]:
            thigh = get_bone(armature, f'thigh{side}')
            if thigh:
                set_key(thigh, frame, rotation=spread_rot(f'thigh{side}', sign * math.sin(phase) * 0.008))

        for side in ['_r', '_l']:
            upper = get_bone(armature, f'upper_arm{side}')
            if upper:
                sign_val = 0.1 if side == '_l' else -0.1
                r = list(swing_rot(f'upper_arm{side}', 0.05))
                sr = list(spread_rot(f'upper_arm{side}', sign_val))
                set_key(upper, frame, rotation=(r[0]+sr[0], r[1]+sr[1], r[2]+sr[2]))

            forearm = get_bone(armature, f'forearm{side}')
            if forearm:
                set_key(forearm, frame, rotation=swing_rot(f'forearm{side}', 0.15))

    set_interpolation(action, 'BEZIER')
    make_cyclic(action)
    push_to_nla(armature, action, "idle")
    return num_frames


def _leg_gait_phase(t, sign, stance_ratio):
    """Compute gait phase for one leg in a walk/run cycle.

    Args:
        t: Normalized cycle time [0, 1)
        sign: +1 for right leg, -1 for left leg (left is offset by half cycle)
        stance_ratio: Fraction of cycle spent in stance (0.6 for walk, 0.5 for run)

    Returns:
        (phase_name, phase_t) where:
            phase_name: 'stance' or 'swing'
            phase_t: Normalized progress within that phase [0, 1]
    """
    # Right leg: heel strike at t=0, left leg: heel strike at t=0.5
    offset = 0.0 if sign > 0 else 0.5
    leg_t = (t + offset) % 1.0

    if leg_t < stance_ratio:
        return 'stance', leg_t / stance_ratio
    else:
        return 'swing', (leg_t - stance_ratio) / (1.0 - stance_ratio)


def _walk_leg_poses(phase_name, phase_t, I):
    """Compute thigh, shin, foot rotations for a walk cycle leg.

    During stance: foot stays planted. Thigh rotates from forward-extended to
    behind the body. Shin stays nearly straight. Foot rolls heel-to-toe.

    During swing: foot lifts, knee bends to clear ground, leg swings forward
    to prepare for next heel strike.

    Returns: (thigh_x, shin_x, foot_x) rotation values
    """
    # Walk stride angles (radians)
    stride_fwd = 0.35 * I    # Thigh angle at heel strike (forward)
    stride_back = -0.28 * I  # Thigh angle at toe-off (behind)
    knee_stance = 0.12 * I   # Slight knee flex during midstance
    knee_swing = 0.55 * I    # Knee bend during swing (clear ground)

    if phase_name == 'stance':
        # Stance: foot planted, body passes over
        # Thigh sweeps from forward to behind
        p = smooth_step(phase_t)
        thigh_x = lerp(stride_fwd, stride_back, p)

        # Knee: slight flex at midstance (passing position), straighter at ends
        mid_flex = math.sin(phase_t * math.pi) * knee_stance
        shin_x = mid_flex

        # Foot roll: heel strike -> flat -> toe push-off
        if phase_t < 0.2:
            # Heel strike to flat
            foot_x = lerp(0.15 * I, 0.0, smooth_step(phase_t / 0.2))
        elif phase_t < 0.7:
            # Flat on ground (contact hold)
            foot_x = 0.0
        else:
            # Toe push-off
            foot_x = lerp(0.0, -0.2 * I, smooth_step((phase_t - 0.7) / 0.3))

    else:
        # Swing: foot lifts and swings forward
        if phase_t < 0.4:
            # Toe-off to mid-swing: knee bends, thigh starts swinging forward
            p = smooth_step(phase_t / 0.4)
            thigh_x = lerp(stride_back, 0.0, p)
            shin_x = lerp(0.0, knee_swing, ease_in_out_sine(p))
            foot_x = lerp(-0.2 * I, 0.0, p)
        elif phase_t < 0.7:
            # Mid-swing: thigh swings forward, knee stays bent
            p = smooth_step((phase_t - 0.4) / 0.3)
            thigh_x = lerp(0.0, stride_fwd * 0.7, p)
            shin_x = lerp(knee_swing, knee_swing * 0.6, p)
            foot_x = 0.0
        else:
            # Terminal swing: leg extends for heel strike
            p = smooth_step((phase_t - 0.7) / 0.3)
            thigh_x = lerp(stride_fwd * 0.7, stride_fwd, p)
            shin_x = lerp(knee_swing * 0.6, 0.05 * I, ease_in_out_sine(p))
            foot_x = lerp(0.0, 0.15 * I, p)  # Dorsiflex for heel strike

    return thigh_x, shin_x, foot_x


def anim_walk(armature):
    """Walk cycle with ground-contact hold frames to reduce foot sliding.

    Gait is split into stance (~60%) and swing (~40%) phases per leg.
    During stance, the contact foot holds position (thigh sweeps back, foot
    rolls heel-to-toe). During swing, the foot lifts and passes forward.
    Hip drop at contact points simulates weight transfer.

    Bezier interpolation + cyclic modifier for seamless looping.
    """
    num_frames = int(1.0 * FPS)
    action = create_action(armature, "walk", num_frames)
    I = 1.0
    stance_ratio = 0.6  # 60% stance, 40% swing (standard walk)

    # More keyframes for accurate gait phases
    num_keys = max(24, num_frames)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (num_frames - 1))
        phase = t * 2 * math.pi

        # Determine which leg is in stance for hip drop
        r_phase, r_pt = _leg_gait_phase(t, 1, stance_ratio)
        l_phase, l_pt = _leg_gait_phase(t, -1, stance_ratio)

        # Hip drop: dip toward the swing leg side at midstance
        # Right stance midstance -> hips tilt left (drop on swing side)
        hip_drop = 0.0
        if r_phase == 'stance':
            hip_drop -= math.sin(r_pt * math.pi) * 0.012 * I  # Drop left
        if l_phase == 'stance':
            hip_drop += math.sin(l_pt * math.pi) * 0.012 * I  # Drop right

        hips = get_bone(armature, 'hips')
        if hips:
            sway_x = math.sin(phase) * 0.02 * I
            # Bounce: lowest at double-support, highest at midstance
            bounce_z = -abs(math.sin(phase * 2)) * 0.012 * I
            rot_z = math.sin(phase) * 0.05 * I + hip_drop
            rot_x = math.sin(phase) * 0.03 * I
            set_key(hips, frame,
                    location=(sway_x, 0, bounce_z),
                    rotation=(rot_x, hip_drop * 2, rot_z))

        spine = get_bone(armature, 'spine1')
        if spine:
            twist = -math.sin(phase) * 0.04 * I
            set_key(spine, frame, rotation=(0.015 * I, 0, twist))

        spine2 = get_bone(armature, 'spine2')
        if spine2:
            twist = -math.sin(phase) * 0.04 * I * 0.7
            set_key(spine2, frame, rotation=(0, 0, twist))

        chest = get_bone(armature, 'chest')
        if chest:
            set_key(chest, frame, rotation=(0, -math.sin(phase) * 0.015 * I, 0))

        head = get_bone(armature, 'head')
        if head:
            bob = math.sin(phase * 2) * 0.01 * I
            sway = -math.sin(phase) * 0.025 * I
            set_key(head, frame, rotation=(bob, 0, sway))

        neck = get_bone(armature, 'neck')
        if neck:
            sway = -math.sin(phase) * 0.025 * I * 0.5
            set_key(neck, frame, rotation=(0, 0, sway))

        # Shoulders counter-rotate with arms
        for side, sign in [('_r', 1), ('_l', -1)]:
            shoulder = get_bone(armature, f'shoulder{side}')
            if shoulder:
                rot = sign * math.sin(phase) * 0.08 * I
                set_key(shoulder, frame, rotation=(rot * 0.3, 0, -sign * rot))

        # Legs with gait-phase foot contact (axis-aware)
        for side, sign in [('_r', 1), ('_l', -1)]:
            phase_name, phase_t = _leg_gait_phase(t, sign, stance_ratio)
            thigh_swing, shin_swing, foot_swing = _walk_leg_poses(phase_name, phase_t, I)

            thigh = get_bone(armature, f'thigh{side}')
            if thigh:
                set_key(thigh, frame, rotation=swing_rot(f'thigh{side}', thigh_swing))

            shin = get_bone(armature, f'shin{side}')
            if shin:
                set_key(shin, frame, rotation=swing_rot(f'shin{side}', shin_swing))

            foot = get_bone(armature, f'foot{side}')
            if foot:
                set_key(foot, frame, rotation=swing_rot(f'foot{side}', foot_swing))

        # Arms: opposite to legs (axis-aware swing)
        for side, sign in [('_r', -1), ('_l', 1)]:
            upper = get_bone(armature, f'upper_arm{side}')
            if upper:
                arm_swing = sign * math.sin(phase) * 0.35 * I
                r = list(swing_rot(f'upper_arm{side}', arm_swing))
                # Add slight outward hold
                sr = list(spread_rot(f'upper_arm{side}', -sign * 0.1 * I))
                combined = (r[0]+sr[0], r[1]+sr[1], r[2]+sr[2])
                set_key(upper, frame, rotation=combined)

            forearm = get_bone(armature, f'forearm{side}')
            if forearm:
                base_bend = 0.25 * I * 0.5
                swing_factor = (sign * math.sin(phase) + 1) / 2
                bend = base_bend + swing_factor * 0.25 * I
                set_key(forearm, frame, rotation=swing_rot(f'forearm{side}', bend))

    set_interpolation(action, 'BEZIER')
    make_cyclic(action)
    push_to_nla(armature, action, "walk")
    return num_frames


def _run_leg_poses(phase_name, phase_t, I):
    """Compute thigh, shin, foot rotations for a run cycle leg.

    Running has more extreme ranges than walking: higher knee lift during
    swing, stronger push-off during late stance, and a flight phase where
    both feet are off the ground.

    Returns: (thigh_x, shin_x, foot_x) rotation values
    """
    Ir = I / 1.6  # Normalize intensity to base 1.0

    # Run stride angles (larger than walk)
    stride_fwd = 0.55 * Ir    # Thigh angle at initial contact
    stride_back = -0.45 * Ir  # Thigh angle at toe-off (more behind than walk)
    knee_stance = 0.18 * Ir   # Knee flex at midstance (absorption)
    knee_swing = 0.85 * Ir    # High knee bend during swing recovery

    if phase_name == 'stance':
        p = smooth_step(phase_t)
        thigh_x = lerp(stride_fwd, stride_back, p)

        # Knee: absorb impact early, extend for push-off late
        if phase_t < 0.3:
            # Impact absorption
            kp = ease_in_out_sine(phase_t / 0.3)
            shin_x = lerp(0.08 * Ir, knee_stance, kp)
        elif phase_t < 0.6:
            # Midstance -- knee passes through
            kp = smooth_step((phase_t - 0.3) / 0.3)
            shin_x = lerp(knee_stance, knee_stance * 0.5, kp)
        else:
            # Push-off extension
            kp = smooth_step((phase_t - 0.6) / 0.4)
            shin_x = lerp(knee_stance * 0.5, 0.05 * Ir, kp)

        # Foot: forefoot strike -> flat -> aggressive toe push-off
        if phase_t < 0.15:
            foot_x = lerp(0.1 * Ir, 0.0, smooth_step(phase_t / 0.15))
        elif phase_t < 0.6:
            foot_x = 0.0  # Ground contact hold
        else:
            foot_x = lerp(0.0, -0.3 * Ir, smooth_step((phase_t - 0.6) / 0.4))

    else:
        # Swing phase for running
        if phase_t < 0.35:
            # Toe-off to recovery: knee folds up high
            p = smooth_step(phase_t / 0.35)
            thigh_x = lerp(stride_back, 0.15 * Ir, p)
            shin_x = lerp(0.1 * Ir, knee_swing, ease_in_out_sine(p))
            foot_x = lerp(-0.3 * Ir, -0.1 * Ir, p)
        elif phase_t < 0.65:
            # Mid-swing: thigh drives forward, knee still bent
            p = smooth_step((phase_t - 0.35) / 0.3)
            thigh_x = lerp(0.15 * Ir, stride_fwd * 0.8, p)
            shin_x = lerp(knee_swing, knee_swing * 0.5, p)
            foot_x = lerp(-0.1 * Ir, 0.0, p)
        else:
            # Terminal swing: extend leg for ground contact
            p = smooth_step((phase_t - 0.65) / 0.35)
            thigh_x = lerp(stride_fwd * 0.8, stride_fwd, p)
            shin_x = lerp(knee_swing * 0.5, 0.08 * Ir, ease_in_out_sine(p))
            foot_x = lerp(0.0, 0.1 * Ir, p)  # Dorsiflex for contact

    return thigh_x, shin_x, foot_x


def anim_run(armature):
    """Run cycle with ground-contact hold frames to reduce foot sliding.

    Running gait: 50% stance / 50% swing per leg, with a flight phase
    where both feet are off the ground. Stronger push-off, higher knee
    lift, and forward body lean compared to walk.

    Hip drop at contact for weight transfer. Bezier + cyclic for looping.
    """
    num_frames = int(0.6 * FPS)
    action = create_action(armature, "run", num_frames)
    I = 1.6
    Ir = I / 1.6  # Normalized intensity
    body_lean = 0.18 * Ir
    stance_ratio = 0.5  # 50/50 for run (shorter ground contact than walk)

    # More keyframes for accurate gait phases
    num_keys = max(24, num_frames * 2)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (num_frames - 1))
        phase = t * 2 * math.pi

        # Determine gait phases for hip dynamics
        r_phase, r_pt = _leg_gait_phase(t, 1, stance_ratio)
        l_phase, l_pt = _leg_gait_phase(t, -1, stance_ratio)

        # Hip drop toward swing side at contact
        hip_drop = 0.0
        if r_phase == 'stance':
            hip_drop -= math.sin(r_pt * math.pi) * 0.015 * Ir
        if l_phase == 'stance':
            hip_drop += math.sin(l_pt * math.pi) * 0.015 * Ir

        hips = get_bone(armature, 'hips')
        if hips:
            # Bounce: higher amplitude than walk, driven by gait contact
            bounce = -abs(math.sin(phase * 2)) * 0.035 * Ir
            sway = math.sin(phase) * 0.025 * Ir
            set_key(hips, frame,
                    location=(sway, 0, bounce),
                    rotation=(body_lean, hip_drop * 2, math.sin(phase) * 0.06 + hip_drop))

        spine = get_bone(armature, 'spine1')
        if spine:
            set_key(spine, frame, rotation=(body_lean * 0.7, 0, -math.sin(phase) * 0.05))

        spine2 = get_bone(armature, 'spine2')
        if spine2:
            set_key(spine2, frame, rotation=(0.04, -math.sin(phase) * 0.03 * I, 0))

        chest = get_bone(armature, 'chest')
        if chest:
            set_key(chest, frame, rotation=(0.02, -math.sin(phase) * 0.025 * I, 0))

        head = get_bone(armature, 'head')
        if head:
            counter = -body_lean * 0.5
            set_key(head, frame, rotation=(counter, 0, 0))

        # Legs with gait-phase foot contact
        for side, sign in [('_r', 1), ('_l', -1)]:
            phase_name, phase_t = _leg_gait_phase(t, sign, stance_ratio)
            thigh_x, shin_x, foot_x = _run_leg_poses(phase_name, phase_t, I)

            thigh = get_bone(armature, f'thigh{side}')
            if thigh:
                set_key(thigh, frame, rotation=swing_rot(f'thigh{side}', thigh_x))

            shin = get_bone(armature, f'shin{side}')
            if shin:
                set_key(shin, frame, rotation=swing_rot(f'shin{side}', shin_x))

            foot = get_bone(armature, f'foot{side}')
            if foot:
                set_key(foot, frame, rotation=swing_rot(f'foot{side}', foot_x))

        # Arms: vigorous counter-swing (axis-aware)
        for side, sign in [('_r', -1), ('_l', 1)]:
            upper = get_bone(armature, f'upper_arm{side}')
            if upper:
                arm_swing = sign * math.sin(phase) * 0.6 * Ir
                r = list(swing_rot(f'upper_arm{side}', arm_swing))
                sr = list(spread_rot(f'upper_arm{side}', -sign * 0.15))
                combined = (r[0]+sr[0], r[1]+sr[1], r[2]+sr[2])
                set_key(upper, frame, rotation=combined)

            forearm = get_bone(armature, f'forearm{side}')
            if forearm:
                bend = 0.4 + (sign * math.sin(phase) + 1) / 2 * 0.5
                set_key(forearm, frame, rotation=swing_rot(f'forearm{side}', bend * Ir))

    set_interpolation(action, 'BEZIER')
    make_cyclic(action)
    push_to_nla(armature, action, "run")
    return num_frames


def anim_attack(armature):
    """Attack swing -- right arm overhead slash, weight shift forward.

    Uses ease_in_out_sine for anticipation/recovery, ease_out_back for the
    wind-up overshoot, and smooth_step for follow-through deceleration.
    Bezier interpolation for smooth arcs.
    """
    num_frames = int(0.8 * FPS)
    action = create_action(armature, "attack_1", num_frames)

    for i in range(num_frames):
        t = i / max(num_frames - 1, 1)
        frame = i + 1

        if t < 0.15:
            # Anticipation -- slight crouch, weight back (ease_in_out_sine)
            p = ease_in_out_sine(t / 0.15)
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame, location=(0, 0, -0.02 * p), rotation=(-0.03 * p, 0, 0))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(-0.04 * p, 0, 0))
            for side in ['_r', '_l']:
                thigh = get_bone(armature, f'thigh{side}')
                if thigh:
                    set_key(thigh, frame, rotation=swing_rot(f'thigh{side}', 0.05 * p))

        elif t < 0.35:
            # Wind-up -- arm raises overhead (ease_out_back for overshoot)
            p = ease_out_back((t - 0.15) / 0.2)
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame, location=(0, 0, -0.02), rotation=(-0.03 - 0.05 * p, 0.05 * p, 0))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(-0.04 - 0.06 * p, 0.08 * p, 0))
            upper_r = get_bone(armature, 'upper_arm_r')
            if upper_r:
                set_key(upper_r, frame, rotation=(-1.2 * p, 0, -0.3 * p))
            forearm_r = get_bone(armature, 'forearm_r')
            if forearm_r:
                set_key(forearm_r, frame, rotation=(0.8 * p, 0, 0))
            upper_l = get_bone(armature, 'upper_arm_l')
            if upper_l:
                set_key(upper_l, frame, rotation=(-0.3 * p, 0, 0.2 * p))

        elif t < 0.55:
            # Strike -- fast downswing (ease_in_out_quad for snap)
            p = ease_in_out_quad((t - 0.35) / 0.2)
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame, location=(0, 0, -0.02 * (1 - p)), rotation=(-0.08 + 0.2 * p, 0.05 - 0.15 * p, 0))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(-0.1 + 0.25 * p, 0.08 - 0.2 * p, 0))
            upper_r = get_bone(armature, 'upper_arm_r')
            if upper_r:
                set_key(upper_r, frame, rotation=(-1.2 + 1.8 * p, 0, -0.3 + 0.3 * p))
            forearm_r = get_bone(armature, 'forearm_r')
            if forearm_r:
                set_key(forearm_r, frame, rotation=(0.8 - 0.6 * p, 0, 0))
            thigh_r = get_bone(armature, 'thigh_r')
            if thigh_r:
                set_key(thigh_r, frame, rotation=swing_rot('thigh_r', 0.15 * p))
            shin_r = get_bone(armature, 'shin_r')
            if shin_r:
                set_key(shin_r, frame, rotation=swing_rot('shin_r', 0.1 * p))

        elif t < 0.8:
            # Follow-through (smooth_step deceleration)
            p = smooth_step((t - 0.55) / 0.25)
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame, rotation=(lerp(0.12, 0.04, p), lerp(-0.1, -0.04, p), 0))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(lerp(0.15, 0.05, p), lerp(-0.12, -0.04, p), 0))
            upper_r = get_bone(armature, 'upper_arm_r')
            if upper_r:
                set_key(upper_r, frame, rotation=(lerp(0.6, 0.2, p), 0, 0))
            forearm_r = get_bone(armature, 'forearm_r')
            if forearm_r:
                set_key(forearm_r, frame, rotation=(lerp(0.2, 0.3, p), 0, 0))
            thigh_r = get_bone(armature, 'thigh_r')
            if thigh_r:
                set_key(thigh_r, frame, rotation=swing_rot('thigh_r', lerp(0.15, 0.05, p)))

        else:
            # Recovery to rest (ease_in_out_sine)
            p = ease_in_out_sine((t - 0.8) / 0.2)
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame, rotation=(0.04 * (1 - p), -0.04 * (1 - p), 0))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(0.05 * (1 - p), -0.04 * (1 - p), 0))
            upper_r = get_bone(armature, 'upper_arm_r')
            if upper_r:
                set_key(upper_r, frame, rotation=(0.2 * (1 - p), 0, 0))
            forearm_r = get_bone(armature, 'forearm_r')
            if forearm_r:
                set_key(forearm_r, frame, rotation=(0.3 * (1 - p), 0, 0))

    set_interpolation(action, 'BEZIER')
    push_to_nla(armature, action, "attack_1")
    return num_frames


def anim_hit_reaction(armature):
    """Hit stagger -- jolt backward, recover.

    Uses ease_out_elastic for the recovery phase to simulate the body
    rebounding from impact. smooth_step for the final settle.
    """
    num_frames = int(0.6 * FPS)
    action = create_action(armature, "hit_reaction", num_frames)

    for i in range(num_frames):
        t = i / max(num_frames - 1, 1)
        frame = i + 1

        if t < 0.15:
            # Impact -- fast jolt (ease_in_out_quad for sharp snap)
            p = ease_in_out_quad(t / 0.15)
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame,
                        location=(0, 0, -0.04 * p),
                        rotation=(-0.15 * p, 0, 0))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(-0.2 * p, 0, 0.05 * p))
            head = get_bone(armature, 'head')
            if head:
                set_key(head, frame, rotation=(-0.15 * p, 0, 0))
            for side, sz in [('_r', 1), ('_l', -1)]:
                upper = get_bone(armature, f'upper_arm{side}')
                if upper:
                    set_key(upper, frame, rotation=(-0.3 * p, 0, sz * 0.2 * p))

        elif t < 0.5:
            # Stagger -- shaking with decay
            p = (t - 0.15) / 0.35
            shake = math.sin(p * 6 * math.pi) * 0.02 * (1 - p)
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame,
                        location=(shake, 0, -0.04 * (1 - p * 0.3)),
                        rotation=(-0.15 * (1 - p * 0.4), 0, shake))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(-0.2 * (1 - p * 0.5), 0, 0.05 * (1 - p)))
            head = get_bone(armature, 'head')
            if head:
                set_key(head, frame, rotation=(-0.15 * (1 - p * 0.6), shake * 2, 0))
            for side, sz in [('_r', 1), ('_l', -1)]:
                upper = get_bone(armature, f'upper_arm{side}')
                if upper:
                    set_key(upper, frame, rotation=(-0.3 * (1 - p * 0.6), 0, sz * 0.2 * (1 - p)))

        else:
            # Recovery -- smooth_step settle back to neutral
            p = (t - 0.5) / 0.5
            ease = smooth_step(p)
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame,
                        location=(0, 0, -0.028 * (1 - ease)),
                        rotation=(-0.09 * (1 - ease), 0, 0))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(-0.1 * (1 - ease), 0, 0))
            head = get_bone(armature, 'head')
            if head:
                set_key(head, frame, rotation=(-0.06 * (1 - ease), 0, 0))
            for side, sz in [('_r', 1), ('_l', -1)]:
                upper = get_bone(armature, f'upper_arm{side}')
                if upper:
                    set_key(upper, frame, rotation=(-0.12 * (1 - ease), 0, sz * 0.08 * (1 - ease)))

    set_interpolation(action, 'BEZIER')
    push_to_nla(armature, action, "hit_reaction")
    return num_frames


def anim_death(armature):
    """Death -- collapse backward and fall to ground.

    Uses ease_in_out_sine for the initial stagger, ease_in_out_quad for the
    accelerating fall (gravity), and holds the final pose. Bezier interpolation
    for smooth arc.
    """
    num_frames = int(1.2 * FPS)
    action = create_action(armature, "death", num_frames)

    for i in range(num_frames):
        t = i / max(num_frames - 1, 1)
        frame = i + 1

        if t < 0.2:
            # Stagger from lethal hit (ease_in_out_sine for smooth onset)
            p = ease_in_out_sine(t / 0.2)
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame,
                        location=(0, 0, -0.03 * p),
                        rotation=(-0.1 * p, 0, 0.05 * p))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(-0.15 * p, 0, 0.05 * p))
            head = get_bone(armature, 'head')
            if head:
                set_key(head, frame, rotation=(-0.2 * p, 0.1 * p, 0))
            for side, sz in [('_r', 1), ('_l', -1)]:
                upper = get_bone(armature, f'upper_arm{side}')
                if upper:
                    set_key(upper, frame, rotation=(-0.2 * p, 0, sz * 0.3 * p))
                forearm = get_bone(armature, f'forearm{side}')
                if forearm:
                    set_key(forearm, frame, rotation=(0.2 * p, 0, 0))

        elif t < 0.7:
            # Falling -- accelerating collapse (ease_in_out_quad for gravity)
            p = (t - 0.2) / 0.5
            ease = ease_in_out_quad(p)
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame,
                        location=(0, -0.3 * ease, -0.03 - 0.15 * ease),
                        rotation=(-0.1 - 0.8 * ease, 0, 0.05))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(-0.15 - 0.3 * ease, 0, 0.05 * (1 - p)))
            head = get_bone(armature, 'head')
            if head:
                set_key(head, frame, rotation=(-0.2 - 0.4 * ease, 0.1 * (1 - p), 0))
            for side in ['_r', '_l']:
                thigh = get_bone(armature, f'thigh{side}')
                if thigh:
                    set_key(thigh, frame, rotation=swing_rot(f'thigh{side}', 0.3 * ease))
                shin = get_bone(armature, f'shin{side}')
                if shin:
                    set_key(shin, frame, rotation=swing_rot(f'shin{side}', 0.5 * ease))
            for side, sz in [('_r', 1), ('_l', -1)]:
                upper = get_bone(armature, f'upper_arm{side}')
                if upper:
                    set_key(upper, frame, rotation=(-0.2 - 0.8 * ease, 0, sz * (0.3 + 0.5 * ease)))
                forearm = get_bone(armature, f'forearm{side}')
                if forearm:
                    set_key(forearm, frame, rotation=(0.2 + 0.3 * ease, 0, 0))

        else:
            # Dead -- hold final pose
            hips = get_bone(armature, 'hips')
            if hips:
                set_key(hips, frame,
                        location=(0, -0.3, -0.18),
                        rotation=(-0.9, 0, 0.05))
            chest = get_bone(armature, 'chest')
            if chest:
                set_key(chest, frame, rotation=(-0.45, 0, 0))
            head = get_bone(armature, 'head')
            if head:
                set_key(head, frame, rotation=(-0.6, 0, 0))
            for side in ['_r', '_l']:
                thigh = get_bone(armature, f'thigh{side}')
                if thigh:
                    set_key(thigh, frame, rotation=swing_rot(f'thigh{side}', 0.3))
                shin = get_bone(armature, f'shin{side}')
                if shin:
                    set_key(shin, frame, rotation=swing_rot(f'shin{side}', 0.5))
            for side, sz in [('_r', 1), ('_l', -1)]:
                upper = get_bone(armature, f'upper_arm{side}')
                if upper:
                    set_key(upper, frame, rotation=(-1.0, 0, sz * 0.8))
                forearm = get_bone(armature, f'forearm{side}')
                if forearm:
                    set_key(forearm, frame, rotation=(0.5, 0, 0))

    set_interpolation(action, 'BEZIER')
    push_to_nla(armature, action, "death")
    return num_frames


# ============================================================
# Main
# ============================================================

try:
    # Clear default scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Import the rigged GLB
    print(f"Importing: {input_glb}")
    bpy.ops.import_scene.gltf(filepath=input_glb)

    # Find armature
    armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
            break

    if not armature:
        print("ERROR: No armature found in GLB")
        sys.exit(1)

    # Make armature active
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)

    bone_count = len(armature.data.bones)
    print(f"Armature: {armature.name} ({bone_count} bones)")

    # Auto-detect bone mapping
    BONE_MAP = detect_bone_map(armature)
    print(f"\nDetected bone map ({len(BONE_MAP)} roles):")
    for role, bone_name in sorted(BONE_MAP.items()):
        print(f"  {role:20s} -> {bone_name}")

    # Report unmapped essential roles
    essential = ['hips', 'spine1', 'chest', 'head', 'upper_arm_r', 'upper_arm_l', 'thigh_r', 'thigh_l']
    missing = [r for r in essential if r not in BONE_MAP]
    if missing:
        print(f"\nWARNING: Missing essential roles: {missing}")

    # Detect swing axes for each bone (sideways bones need Z rotation, vertical need X)
    detect_swing_axes(armature)
    z_bones = [r for r, a in SWING_AXIS.items() if a == 'z']
    if z_bones:
        print(f"\nSwing axis overrides (Z): {sorted(z_bones)}")

    # Clear any existing animation data and orphan actions from prior runs
    if armature.animation_data:
        armature.animation_data_clear()
    # Remove ALL existing actions to prevent _001/_002 name collisions on re-runs
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)

    # Generate all 6 animations with per-animation error handling
    print("\nGenerating animations...")
    anims = [
        ("idle", anim_idle),
        ("walk", anim_walk),
        ("run", anim_run),
        ("attack_1", anim_attack),
        ("hit_reaction", anim_hit_reaction),
        ("death", anim_death),
    ]

    failed_anims = []
    for name, func in anims:
        try:
            frames = func(armature)
            print(f"  {name}: {frames} frames (Bezier interpolation)")
        except Exception as anim_err:
            print(f"  ERROR generating {name}: {anim_err}")
            traceback.print_exc()
            failed_anims.append(name)

    if failed_anims:
        print(f"\nWARNING: {len(failed_anims)} animation(s) failed: {failed_anims}")

    # Validate: report fcurve counts per action
    print("\nAnimation validation:")
    for action in bpy.data.actions:
        fcurves = get_fcurves_from_action(action)
        multi = sum(1 for fc in fcurves if len(fc.keyframe_points) > 1)
        total = len(fcurves)
        print(f"  {action.name}: {total} fcurves, {multi} with >1 keyframe")

    # Clear active action (all anims are in NLA tracks now)
    if armature.animation_data:
        armature.animation_data.action = None

    # Export
    print(f"\nExporting to: {output_glb}")
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_animations=True,
        export_skins=True,
        export_nla_strips=True,
        export_current_frame=False,
        export_force_sampling=True,
        export_optimize_animation_size=False,
    )
    print("DONE")

except Exception as e:
    print(f"FATAL ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
