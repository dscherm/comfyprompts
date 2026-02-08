"""Shared animation library for ComfyUI MCP Server.

This module consolidates all animation-related code into a single source of truth.
It is imported by:
- blender_animate.py (standalone Blender script)
- blender_addon/__init__.py (Blender addon)
- Any future animation scripts

Contains:
- Easing functions
- Blender action/keyframe utilities (Blender 4.x and 5.0+ compatible)
- Universal RigBones class (Rigify, UniRig bone_N, standard naming)
- All procedural animation generators (walk, run, idle, wave, jump, nod, look_around)
"""

import math

try:
    import bpy
    from mathutils import Vector, Euler, Quaternion
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False


# =============================================================================
# EASING FUNCTIONS
# =============================================================================

def ease_in_out_sine(t):
    """Sine ease in/out - smooth acceleration and deceleration."""
    return -(math.cos(math.pi * t) - 1) / 2


def ease_in_out_quad(t):
    """Quadratic ease in/out."""
    if t < 0.5:
        return 2 * t * t
    return 1 - pow(-2 * t + 2, 2) / 2


def ease_out_elastic(t):
    """Elastic ease out - bouncy overshoot."""
    if t == 0 or t == 1:
        return t
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1


def ease_out_back(t):
    """Back ease out - slight overshoot."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def ease_in_out_back(t):
    """Back ease in/out - overshoot on both ends."""
    c1 = 1.70158
    c2 = c1 * 1.525
    if t < 0.5:
        return (pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2)) / 2
    return (pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2


def lerp(a, b, t):
    """Linear interpolation."""
    return a + (b - a) * t


def smooth_step(t):
    """Smooth step function (Hermite interpolation)."""
    return t * t * (3 - 2 * t)


# =============================================================================
# BLENDER UTILITIES (require bpy)
# =============================================================================

def get_armature():
    """Find the main armature in the scene.

    Priority: RIG- prefix (Rigify generated) > most bones > first found.
    """
    armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
    if not armatures:
        return None

    # Prefer Rigify-generated control rigs
    for arm in armatures:
        if arm.name.startswith("RIG-"):
            return arm

    # Prefer named rigs over generic armatures
    for arm in armatures:
        if arm.name.startswith("rig") or "Rig" in arm.name:
            return arm

    # Fallback: most bones (likely the main rig)
    return max(armatures, key=lambda a: len(a.pose.bones))


def get_fcurves_from_action(action):
    """Get fcurves from an action, handling both legacy and layered actions.

    Blender < 5.0: action.fcurves
    Blender 5.0+: action.layers[].strips[].channelbags[].fcurves
    """
    # Legacy fcurves (Blender < 5.0)
    if hasattr(action, 'fcurves') and action.fcurves:
        return list(action.fcurves)

    # Layered action (Blender 5.0+)
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


def set_keyframe(bone, frame, location=None, rotation=None, scale=None):
    """Set keyframes for a pose bone.

    Args:
        bone: A pose bone (bpy.types.PoseBone)
        frame: Frame number
        location: (x, y, z) tuple or None
        rotation: (x, y, z) euler tuple, (w, x, y, z) quaternion tuple, or None
        scale: (x, y, z) tuple or None
    """
    try:
        if location is not None:
            bone.location = Vector(location)
            bone.keyframe_insert(data_path="location", frame=frame)

        if rotation is not None:
            if len(rotation) == 3:
                bone.rotation_mode = 'XYZ'
                bone.rotation_euler = Euler(rotation)
                bone.keyframe_insert(data_path="rotation_euler", frame=frame)
            elif len(rotation) == 4:
                bone.rotation_mode = 'QUATERNION'
                bone.rotation_quaternion = Quaternion(rotation)
                bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)

        if scale is not None:
            bone.scale = Vector(scale)
            bone.keyframe_insert(data_path="scale", frame=frame)
    except Exception as e:
        print(f"  Warning: keyframe failed for {bone.name}: {e}")


def clear_animation(armature):
    """Clear existing animation data from an armature."""
    if armature.animation_data:
        armature.animation_data_clear()


def setup_animation(armature, name, fps, frame_end):
    """Set up a new animation action on an armature.

    Clears existing animation, creates a new action, enters pose mode,
    and configures scene frame range.

    Returns:
        The new bpy.types.Action
    """
    clear_animation(armature)

    # Ensure armature is active and in pose mode
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    # Create and assign action
    action = bpy.data.actions.new(name=name)
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action

    # Configure scene
    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_end

    return action


def make_cyclic(action):
    """Make all animation curves cyclic for seamless looping."""
    fcurves = get_fcurves_from_action(action)
    for fcurve in fcurves:
        mod = fcurve.modifiers.new(type='CYCLES')
        mod.mode_before = 'REPEAT'
        mod.mode_after = 'REPEAT'


def set_interpolation(action, interpolation='BEZIER'):
    """Set interpolation type for all keyframes in an action."""
    fcurves = get_fcurves_from_action(action)
    for fcurve in fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = interpolation
            if interpolation == 'BEZIER':
                keyframe.handle_left_type = 'AUTO_CLAMPED'
                keyframe.handle_right_type = 'AUTO_CLAMPED'


# =============================================================================
# UNIVERSAL RIG BONES
# =============================================================================

# UniRig bone_N -> semantic role mapping
# UniRig typically produces: bone_0=hips, bone_1-5=spine chain,
# bone_6-9=right arm, bone_10-13=left arm, bone_14-17=right leg, bone_18-21=left leg
UNIRIG_BONE_MAP = {
    'bone_0': 'hips',
    'bone_1': 'spine',
    'bone_2': 'spine2',
    'bone_3': 'chest',
    'bone_4': 'neck',
    'bone_5': 'head',
    'bone_6': 'shoulder_r',
    'bone_7': 'upper_arm_r',
    'bone_8': 'forearm_r',
    'bone_9': 'hand_r',
    'bone_10': 'shoulder_l',
    'bone_11': 'upper_arm_l',
    'bone_12': 'forearm_l',
    'bone_13': 'hand_l',
    'bone_14': 'thigh_r',
    'bone_15': 'shin_r',
    'bone_16': 'foot_r',
    'bone_17': 'toe_r',
    'bone_18': 'thigh_l',
    'bone_19': 'shin_l',
    'bone_20': 'foot_l',
    'bone_21': 'toe_l',
}


class RigBones:
    """Universal helper class to find bones in any rig type.

    Supports:
    - Rigify FK controls (spine_fk, upper_arm_fk.L, etc.)
    - Rigify IK controls (foot_ik.L, hand_ik.L, etc.)
    - Standard naming (spine, upper_arm.L, thigh.L, etc.)
    - DEF- prefix (deformation bones)
    - UniRig bone_N naming convention
    - Case-insensitive matching with caching
    """

    # Pattern lists ordered by priority (FK controls first, then standard, then DEF)
    PATTERNS = {
        'root': ['root', 'master', 'main', 'torso'],
        'hips': ['hip', 'pelvis', 'torso', 'hips'],
        'spine': ['spine_fk', 'spine', 'spine.001', 'spine1'],
        'spine2': ['spine_fk.001', 'spine.002', 'spine2', 'chest'],
        'chest': ['chest', 'spine_fk.002', 'spine.003', 'spine3'],
        'neck': ['neck'],
        'head': ['head'],
        'shoulder_l': ['shoulder.l', 'shoulder_l', 'clavicle.l', 'shoulder.L', 'DEF-shoulder.L'],
        'shoulder_r': ['shoulder.r', 'shoulder_r', 'clavicle.r', 'shoulder.R', 'DEF-shoulder.R'],
        'upper_arm_l': ['upper_arm_fk.l', 'upper_arm.l', 'upperarm.l', 'arm.l',
                        'upper_arm_fk.L', 'DEF-upper_arm.L'],
        'upper_arm_r': ['upper_arm_fk.r', 'upper_arm.r', 'upperarm.r', 'arm.r',
                        'upper_arm_fk.R', 'DEF-upper_arm.R'],
        'forearm_l': ['forearm_fk.l', 'forearm.l', 'lower_arm.l', 'lowerarm.l',
                      'forearm_fk.L', 'DEF-forearm.L'],
        'forearm_r': ['forearm_fk.r', 'forearm.r', 'lower_arm.r', 'lowerarm.r',
                      'forearm_fk.R', 'DEF-forearm.R'],
        'hand_l': ['hand_fk.l', 'hand.l', 'wrist.l', 'hand_fk.L', 'DEF-hand.L'],
        'hand_r': ['hand_fk.r', 'hand.r', 'wrist.r', 'hand_fk.R', 'DEF-hand.R'],
        'thigh_l': ['thigh_fk.l', 'thigh.l', 'upper_leg.l', 'upperleg.l', 'leg.l',
                    'thigh_fk.L', 'DEF-thigh.L'],
        'thigh_r': ['thigh_fk.r', 'thigh.r', 'upper_leg.r', 'upperleg.r', 'leg.r',
                    'thigh_fk.R', 'DEF-thigh.R'],
        'shin_l': ['shin_fk.l', 'shin.l', 'lower_leg.l', 'lowerleg.l', 'calf.l',
                   'shin_fk.L', 'DEF-shin.L'],
        'shin_r': ['shin_fk.r', 'shin.r', 'lower_leg.r', 'lowerleg.r', 'calf.r',
                   'shin_fk.R', 'DEF-shin.R'],
        'foot_l': ['foot_fk.l', 'foot.l', 'ankle.l', 'foot_fk.L', 'DEF-foot.L'],
        'foot_r': ['foot_fk.r', 'foot.r', 'ankle.r', 'foot_fk.R', 'DEF-foot.R'],
        'toe_l': ['toe.l', 'toes.l', 'toe.L', 'DEF-toe.L'],
        'toe_r': ['toe.r', 'toes.r', 'toe.R', 'DEF-toe.R'],
        # IK targets (Rigify)
        'ik_foot_l': ['foot_ik.l', 'ik_foot.l', 'foot.ik.l', 'leg_ik.l', 'foot_ik.L'],
        'ik_foot_r': ['foot_ik.r', 'ik_foot.r', 'foot.ik.r', 'leg_ik.r', 'foot_ik.R'],
        'ik_hand_l': ['hand_ik.l', 'ik_hand.l', 'hand.ik.l', 'arm_ik.l', 'hand_ik.L'],
        'ik_hand_r': ['hand_ik.r', 'ik_hand.r', 'hand.ik.r', 'arm_ik.r', 'hand_ik.R'],
    }

    def __init__(self, armature):
        """Initialize with a Blender armature object.

        Auto-detects if this is a UniRig rig (bone_N naming) and builds
        a reverse lookup table for fast bone resolution.
        """
        self.armature = armature
        self.bones = armature.pose.bones
        self._cache = {}

        # Detect UniRig rigs by checking for bone_0, bone_1, etc.
        self._unirig_map = {}
        bone_names = {b.name for b in self.bones}
        if 'bone_0' in bone_names and 'bone_1' in bone_names:
            # Build UniRig reverse map: role -> pose bone
            for bone_name, role in UNIRIG_BONE_MAP.items():
                if bone_name in bone_names:
                    self._unirig_map[role] = self.bones[bone_name]

    def find(self, role):
        """Find a pose bone by its semantic role.

        Args:
            role: Semantic name like 'hips', 'upper_arm_l', 'head', etc.

        Returns:
            The matching PoseBone, or None if not found.
        """
        if role in self._cache:
            return self._cache[role]

        # Check UniRig mapping first (fast path)
        if role in self._unirig_map:
            self._cache[role] = self._unirig_map[role]
            return self._unirig_map[role]

        # Fall back to pattern matching
        if role not in self.PATTERNS:
            return None

        # Exact match pass
        for pattern in self.PATTERNS[role]:
            pattern_lower = pattern.lower()
            for bone in self.bones:
                if bone.name.lower() == pattern_lower:
                    self._cache[role] = bone
                    return bone

        # Partial match pass
        for pattern in self.PATTERNS[role]:
            pattern_lower = pattern.lower()
            for bone in self.bones:
                if pattern_lower in bone.name.lower():
                    self._cache[role] = bone
                    return bone

        return None

    def find_all(self, role):
        """Find all bones matching a group role pattern.

        Args:
            role: Group name like 'spine_chain', 'fingers_l', 'fingers_r'

        Returns:
            List of matching PoseBones.
        """
        group_patterns = {
            'spine_chain': ['spine', 'chest'],
            'fingers_l': ['finger', '.l'],
            'fingers_r': ['finger', '.r'],
        }

        if role not in group_patterns:
            return []

        results = []
        for bone in self.bones:
            bone_lower = bone.name.lower()
            if all(p in bone_lower for p in group_patterns[role]):
                results.append(bone)
        return results

    @property
    def is_unirig(self):
        """True if this armature uses UniRig bone_N naming."""
        return bool(self._unirig_map)

    def describe(self):
        """Return a dict describing which roles were found, for diagnostics."""
        found = {}
        for role in self.PATTERNS:
            bone = self.find(role)
            if bone:
                found[role] = bone.name
        return found


# =============================================================================
# ANIMATION GENERATORS
# =============================================================================

def generate_walk_cycle(armature, options):
    """Generate a natural walk cycle animation.

    Args:
        armature: Blender armature object
        options: Dict with keys: fps, duration, intensity, loop

    Returns:
        bpy.types.Action
    """
    fps = options.get('fps', 30)
    duration = options.get('duration', 1.0)
    intensity = options.get('intensity', 1.0)

    frame_count = int(fps * duration)
    action = setup_animation(armature, "WalkCycle", fps, frame_count)

    rig = RigBones(armature)

    # Animation parameters tuned for natural movement
    hip_sway = 0.025 * intensity
    hip_rotation = 0.06 * intensity
    hip_tilt = 0.04 * intensity
    spine_twist = 0.04 * intensity
    spine_bend = 0.015 * intensity
    shoulder_rotation = 0.08 * intensity
    arm_swing = 0.35 * intensity
    forearm_bend = 0.25 * intensity
    leg_swing = 0.38 * intensity
    knee_bend_max = 0.45 * intensity
    foot_roll = 0.15 * intensity
    head_bob = 0.01 * intensity
    head_sway = 0.03 * intensity

    num_keys = max(12, frame_count // 2)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))
        walk_phase = t * 2 * math.pi
        half_phase = t * 4 * math.pi

        # Hips - sway, bounce, rotation, tilt
        hips = rig.find('hips')
        if hips:
            sway_x = math.sin(walk_phase) * hip_sway
            bounce_z = -abs(math.sin(half_phase)) * 0.015 * intensity
            rot_z = math.sin(walk_phase) * hip_rotation
            rot_x = math.sin(walk_phase) * hip_tilt
            set_keyframe(hips, frame,
                         location=(sway_x, 0, bounce_z),
                         rotation=(rot_x, 0, rot_z))

        # Spine - counter-twist with slight forward lean
        spine = rig.find('spine')
        if spine:
            twist = -math.sin(walk_phase) * spine_twist
            set_keyframe(spine, frame, rotation=(spine_bend, 0, twist))

        spine2 = rig.find('spine2') or rig.find('chest')
        if spine2:
            twist = -math.sin(walk_phase) * spine_twist * 0.7
            set_keyframe(spine2, frame, rotation=(0, 0, twist))

        # Shoulders
        shoulder_l = rig.find('shoulder_l')
        if shoulder_l:
            rot = -math.sin(walk_phase) * shoulder_rotation
            set_keyframe(shoulder_l, frame, rotation=(rot * 0.3, 0, rot))

        shoulder_r = rig.find('shoulder_r')
        if shoulder_r:
            rot = math.sin(walk_phase) * shoulder_rotation
            set_keyframe(shoulder_r, frame, rotation=(rot * 0.3, 0, -rot))

        # Arms with follow-through
        upper_arm_l = rig.find('upper_arm_l')
        if upper_arm_l:
            swing = -math.sin(walk_phase) * arm_swing
            set_keyframe(upper_arm_l, frame, rotation=(swing, 0.1 * intensity, 0))

        forearm_l = rig.find('forearm_l')
        if forearm_l:
            base_bend = forearm_bend * 0.5
            swing_factor = (-math.sin(walk_phase) + 1) / 2
            bend = base_bend + swing_factor * forearm_bend
            set_keyframe(forearm_l, frame, rotation=(bend, 0, 0))

        upper_arm_r = rig.find('upper_arm_r')
        if upper_arm_r:
            swing = math.sin(walk_phase) * arm_swing
            set_keyframe(upper_arm_r, frame, rotation=(swing, -0.1 * intensity, 0))

        forearm_r = rig.find('forearm_r')
        if forearm_r:
            base_bend = forearm_bend * 0.5
            swing_factor = (math.sin(walk_phase) + 1) / 2
            bend = base_bend + swing_factor * forearm_bend
            set_keyframe(forearm_r, frame, rotation=(bend, 0, 0))

        # Left leg
        thigh_l = rig.find('thigh_l')
        if thigh_l:
            swing = math.sin(walk_phase) * leg_swing
            side = abs(math.sin(walk_phase)) * 0.02 * intensity
            set_keyframe(thigh_l, frame, rotation=(swing, side, 0))

        shin_l = rig.find('shin_l')
        if shin_l:
            swing_phase_l = (math.sin(walk_phase) + 1) / 2
            bend = smooth_step(swing_phase_l) * knee_bend_max
            pushoff = max(0, -math.sin(walk_phase)) * knee_bend_max * 0.3
            set_keyframe(shin_l, frame, rotation=(bend + pushoff, 0, 0))

        foot_l = rig.find('foot_l')
        if foot_l:
            roll = -math.sin(walk_phase) * foot_roll
            set_keyframe(foot_l, frame, rotation=(roll, 0, 0))

        # Right leg (opposite phase)
        thigh_r = rig.find('thigh_r')
        if thigh_r:
            swing = -math.sin(walk_phase) * leg_swing
            side = -abs(math.sin(walk_phase)) * 0.02 * intensity
            set_keyframe(thigh_r, frame, rotation=(swing, side, 0))

        shin_r = rig.find('shin_r')
        if shin_r:
            swing_phase_r = (-math.sin(walk_phase) + 1) / 2
            bend = smooth_step(swing_phase_r) * knee_bend_max
            pushoff = max(0, math.sin(walk_phase)) * knee_bend_max * 0.3
            set_keyframe(shin_r, frame, rotation=(bend + pushoff, 0, 0))

        foot_r = rig.find('foot_r')
        if foot_r:
            roll = math.sin(walk_phase) * foot_roll
            set_keyframe(foot_r, frame, rotation=(roll, 0, 0))

        # Head and neck
        head = rig.find('head')
        if head:
            bob = math.sin(half_phase) * head_bob
            sway = -math.sin(walk_phase) * head_sway
            set_keyframe(head, frame, rotation=(bob, 0, sway))

        neck = rig.find('neck')
        if neck:
            sway = -math.sin(walk_phase) * head_sway * 0.5
            set_keyframe(neck, frame, rotation=(0, 0, sway))

    set_interpolation(action, 'BEZIER')

    if options.get('loop', True):
        make_cyclic(action)

    return action


def generate_run_cycle(armature, options):
    """Generate a running cycle animation.

    Args:
        armature: Blender armature object
        options: Dict with keys: fps, duration, intensity, loop

    Returns:
        bpy.types.Action
    """
    fps = options.get('fps', 30)
    duration = options.get('duration', 0.5)
    intensity = options.get('intensity', 1.0)

    frame_count = int(fps * duration)
    action = setup_animation(armature, "RunCycle", fps, frame_count)

    rig = RigBones(armature)

    body_lean = 0.18 * intensity
    hip_bounce = 0.04 * intensity
    arm_swing = 0.65 * intensity
    arm_bend = 0.9 * intensity
    leg_swing = 0.55 * intensity
    knee_bend = 0.7 * intensity
    hip_rotation = 0.1 * intensity

    num_keys = max(10, frame_count // 2)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))
        run_phase = t * 2 * math.pi
        double_phase = t * 4 * math.pi

        # Body
        spine = rig.find('spine')
        if spine:
            twist = math.sin(run_phase) * 0.06 * intensity
            set_keyframe(spine, frame, rotation=(body_lean, 0, twist))

        hips = rig.find('hips')
        if hips:
            bounce = abs(math.sin(double_phase)) * hip_bounce
            sway = math.sin(run_phase) * 0.03 * intensity
            rot = math.sin(run_phase) * hip_rotation
            set_keyframe(hips, frame,
                         location=(sway, 0, bounce),
                         rotation=(0, 0, rot))

        # Arms - pumping action
        upper_arm_l = rig.find('upper_arm_l')
        if upper_arm_l:
            swing = -math.sin(run_phase) * arm_swing
            set_keyframe(upper_arm_l, frame, rotation=(swing, 0.15 * intensity, 0))

        forearm_l = rig.find('forearm_l')
        if forearm_l:
            set_keyframe(forearm_l, frame, rotation=(arm_bend, 0, 0))

        upper_arm_r = rig.find('upper_arm_r')
        if upper_arm_r:
            swing = math.sin(run_phase) * arm_swing
            set_keyframe(upper_arm_r, frame, rotation=(swing, -0.15 * intensity, 0))

        forearm_r = rig.find('forearm_r')
        if forearm_r:
            set_keyframe(forearm_r, frame, rotation=(arm_bend, 0, 0))

        # Legs
        thigh_l = rig.find('thigh_l')
        if thigh_l:
            swing = math.sin(run_phase) * leg_swing
            set_keyframe(thigh_l, frame, rotation=(swing, 0, 0))

        shin_l = rig.find('shin_l')
        if shin_l:
            phase = (math.sin(run_phase) + 1) / 2
            bend = 0.2 + smooth_step(phase) * knee_bend
            set_keyframe(shin_l, frame, rotation=(bend, 0, 0))

        thigh_r = rig.find('thigh_r')
        if thigh_r:
            swing = -math.sin(run_phase) * leg_swing
            set_keyframe(thigh_r, frame, rotation=(swing, 0, 0))

        shin_r = rig.find('shin_r')
        if shin_r:
            phase = (-math.sin(run_phase) + 1) / 2
            bend = 0.2 + smooth_step(phase) * knee_bend
            set_keyframe(shin_r, frame, rotation=(bend, 0, 0))

        # Head stays stable
        head = rig.find('head')
        if head:
            counter = -body_lean * 0.5
            set_keyframe(head, frame, rotation=(counter, 0, 0))

    set_interpolation(action, 'BEZIER')

    if options.get('loop', True):
        make_cyclic(action)

    return action


def generate_idle(armature, options):
    """Generate a natural idle/breathing animation.

    Args:
        armature: Blender armature object
        options: Dict with keys: fps, duration, intensity, loop

    Returns:
        bpy.types.Action
    """
    fps = options.get('fps', 30)
    duration = options.get('duration', 4.0)
    intensity = options.get('intensity', 1.0)

    frame_count = int(fps * duration)
    action = setup_animation(armature, "Idle", fps, frame_count)

    rig = RigBones(armature)

    breath_amount = 0.012 * intensity
    sway_amount = 0.008 * intensity
    weight_shift = 0.015 * intensity

    num_keys = max(20, frame_count // 4)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))
        breath_phase = t * 2 * math.pi
        shift_phase = t * math.pi

        # Breathing - chest rises and expands
        chest = rig.find('chest') or rig.find('spine2')
        if chest:
            rise = math.sin(breath_phase) * breath_amount
            expand = math.sin(breath_phase) * breath_amount * 0.5
            set_keyframe(chest, frame,
                         location=(0, 0, rise),
                         rotation=(expand, 0, 0))

        spine = rig.find('spine')
        if spine:
            breathe = math.sin(breath_phase) * breath_amount * 0.3
            set_keyframe(spine, frame, rotation=(breathe, 0, 0))

        # Shoulders rise with breath
        shoulder_l = rig.find('shoulder_l')
        if shoulder_l:
            rise = math.sin(breath_phase) * breath_amount * 0.5
            set_keyframe(shoulder_l, frame, rotation=(rise, 0, 0))

        shoulder_r = rig.find('shoulder_r')
        if shoulder_r:
            rise = math.sin(breath_phase) * breath_amount * 0.5
            set_keyframe(shoulder_r, frame, rotation=(rise, 0, 0))

        # Weight shift
        hips = rig.find('hips')
        if hips:
            shift = math.sin(shift_phase) * weight_shift
            set_keyframe(hips, frame, location=(shift, 0, 0))

        # Head - subtle look around
        head = rig.find('head')
        if head:
            look_x = math.sin(breath_phase * 0.7) * sway_amount
            look_y = math.sin(shift_phase * 1.3) * sway_amount * 0.5
            set_keyframe(head, frame, rotation=(look_x, look_y, 0))

        # Arms - slight sway
        upper_arm_l = rig.find('upper_arm_l')
        if upper_arm_l:
            sway = math.sin(shift_phase) * sway_amount
            set_keyframe(upper_arm_l, frame, rotation=(sway, 0, 0))

        upper_arm_r = rig.find('upper_arm_r')
        if upper_arm_r:
            sway = -math.sin(shift_phase) * sway_amount
            set_keyframe(upper_arm_r, frame, rotation=(sway, 0, 0))

    set_interpolation(action, 'BEZIER')

    if options.get('loop', True):
        make_cyclic(action)

    return action


def generate_wave(armature, options):
    """Generate a waving gesture with anticipation and follow-through.

    Args:
        armature: Blender armature object
        options: Dict with keys: fps, duration, intensity, loop

    Returns:
        bpy.types.Action
    """
    fps = options.get('fps', 30)
    duration = options.get('duration', 2.5)
    intensity = options.get('intensity', 1.0)

    frame_count = int(fps * duration)
    action = setup_animation(armature, "Wave", fps, frame_count)

    rig = RigBones(armature)

    # Phase timing
    anticipation_end = 0.1
    raise_end = 0.25
    wave_start = 0.25
    wave_end = 0.8
    wave_count = 3

    num_keys = max(30, frame_count)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))

        upper_arm_r = rig.find('upper_arm_r')
        forearm_r = rig.find('forearm_r')
        hand_r = rig.find('hand_r')

        if t < anticipation_end:
            # Anticipation - slight dip
            p = t / anticipation_end
            if upper_arm_r:
                set_keyframe(upper_arm_r, frame, rotation=(0.1 * p * intensity, 0, 0))

        elif t < raise_end:
            # Raise arm with overshoot
            p = (t - anticipation_end) / (raise_end - anticipation_end)
            p_eased = ease_out_back(p)

            if upper_arm_r:
                raise_angle = -1.4 * p_eased * intensity
                side_angle = -0.4 * p_eased * intensity
                set_keyframe(upper_arm_r, frame, rotation=(raise_angle, 0, side_angle))

            if forearm_r:
                bend = 0.6 * p_eased * intensity
                set_keyframe(forearm_r, frame, rotation=(bend, 0, 0))

        elif t < wave_end:
            # Waving motion
            wave_t = (t - wave_start) / (wave_end - wave_start)
            wave_angle = math.sin(wave_t * wave_count * 2 * math.pi) * 0.4 * intensity

            if upper_arm_r:
                set_keyframe(upper_arm_r, frame, rotation=(-1.4 * intensity, 0, -0.4 * intensity))

            if forearm_r:
                set_keyframe(forearm_r, frame, rotation=(0.6 * intensity, 0, 0))

            if hand_r:
                set_keyframe(hand_r, frame, rotation=(0, wave_angle, 0))

        else:
            # Lower arm with ease
            p = (t - wave_end) / (1.0 - wave_end)
            p_eased = ease_in_out_sine(p)

            if upper_arm_r:
                raise_angle = -1.4 * (1 - p_eased) * intensity
                side_angle = -0.4 * (1 - p_eased) * intensity
                set_keyframe(upper_arm_r, frame, rotation=(raise_angle, 0, side_angle))

            if forearm_r:
                bend = 0.6 * (1 - p_eased) * intensity
                set_keyframe(forearm_r, frame, rotation=(bend, 0, 0))

            if hand_r:
                set_keyframe(hand_r, frame, rotation=(0, 0, 0))

        # Body reaction
        spine = rig.find('spine')
        if spine:
            lean = 0.04 * intensity if wave_start <= t <= wave_end else 0
            set_keyframe(spine, frame, rotation=(0, 0, lean))

        head = rig.find('head')
        if head:
            tilt = 0.08 * intensity if wave_start <= t <= wave_end else 0
            set_keyframe(head, frame, rotation=(0, 0, tilt))

    set_interpolation(action, 'BEZIER')

    return action


def generate_jump(armature, options):
    """Generate a jump animation with anticipation and squash/stretch.

    Args:
        armature: Blender armature object
        options: Dict with keys: fps, duration, intensity, loop

    Returns:
        bpy.types.Action
    """
    fps = options.get('fps', 30)
    duration = options.get('duration', 1.2)
    intensity = options.get('intensity', 1.0)

    frame_count = int(fps * duration)
    action = setup_animation(armature, "Jump", fps, frame_count)

    rig = RigBones(armature)

    # Phase timing
    anticipation_end = 0.15
    launch_end = 0.25
    air_peak = 0.5
    land_start = 0.75
    land_impact = 0.82

    num_keys = max(25, frame_count)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))

        hips = rig.find('hips')
        spine = rig.find('spine')
        thigh_l = rig.find('thigh_l')
        thigh_r = rig.find('thigh_r')
        shin_l = rig.find('shin_l')
        shin_r = rig.find('shin_r')
        upper_arm_l = rig.find('upper_arm_l')
        upper_arm_r = rig.find('upper_arm_r')

        if t < anticipation_end:
            # Crouch down
            p = ease_in_out_sine(t / anticipation_end)
            crouch = 0.35 * p * intensity
            hip_drop = -0.12 * p * intensity

            if hips:
                set_keyframe(hips, frame, location=(0, 0, hip_drop))
            if spine:
                set_keyframe(spine, frame, rotation=(0.15 * p * intensity, 0, 0))
            if thigh_l:
                set_keyframe(thigh_l, frame, rotation=(crouch, 0, 0))
            if thigh_r:
                set_keyframe(thigh_r, frame, rotation=(crouch, 0, 0))
            if shin_l:
                set_keyframe(shin_l, frame, rotation=(crouch * 1.8, 0, 0))
            if shin_r:
                set_keyframe(shin_r, frame, rotation=(crouch * 1.8, 0, 0))
            if upper_arm_l:
                set_keyframe(upper_arm_l, frame, rotation=(0.4 * p * intensity, 0, -0.2 * p * intensity))
            if upper_arm_r:
                set_keyframe(upper_arm_r, frame, rotation=(0.4 * p * intensity, 0, 0.2 * p * intensity))

        elif t < launch_end:
            # Explosive extension
            p = ease_out_back((t - anticipation_end) / (launch_end - anticipation_end))

            if hips:
                set_keyframe(hips, frame, location=(0, 0, 0.1 * p * intensity))
            if spine:
                set_keyframe(spine, frame, rotation=(-0.1 * p * intensity, 0, 0))
            if thigh_l:
                set_keyframe(thigh_l, frame, rotation=(-0.15 * p * intensity, 0, 0))
            if thigh_r:
                set_keyframe(thigh_r, frame, rotation=(-0.15 * p * intensity, 0, 0))
            if shin_l:
                set_keyframe(shin_l, frame, rotation=(0.05 * intensity, 0, 0))
            if shin_r:
                set_keyframe(shin_r, frame, rotation=(0.05 * intensity, 0, 0))
            if upper_arm_l:
                set_keyframe(upper_arm_l, frame, rotation=(-0.9 * p * intensity, 0, -0.3 * p * intensity))
            if upper_arm_r:
                set_keyframe(upper_arm_r, frame, rotation=(-0.9 * p * intensity, 0, 0.3 * p * intensity))

        elif t < land_start:
            # Air time
            if t < air_peak:
                p = (t - launch_end) / (air_peak - launch_end)
            else:
                p = 1 - (t - air_peak) / (land_start - air_peak)
            p = smooth_step(p)

            height = 0.25 * intensity * (1 - abs(2 * ((t - launch_end) / (land_start - launch_end)) - 1))

            if hips:
                set_keyframe(hips, frame, location=(0, 0, height))
            if spine:
                set_keyframe(spine, frame, rotation=(0, 0, 0))
            if thigh_l:
                set_keyframe(thigh_l, frame, rotation=(0.15 * p * intensity, 0, 0))
            if thigh_r:
                set_keyframe(thigh_r, frame, rotation=(0.15 * p * intensity, 0, 0))
            if shin_l:
                set_keyframe(shin_l, frame, rotation=(0.35 * p * intensity, 0, 0))
            if shin_r:
                set_keyframe(shin_r, frame, rotation=(0.35 * p * intensity, 0, 0))
            if upper_arm_l:
                set_keyframe(upper_arm_l, frame, rotation=(-0.7 * intensity, 0, -0.5 * intensity))
            if upper_arm_r:
                set_keyframe(upper_arm_r, frame, rotation=(-0.7 * intensity, 0, 0.5 * intensity))

        elif t < land_impact:
            # Descending
            p = (t - land_start) / (land_impact - land_start)

            if hips:
                set_keyframe(hips, frame, location=(0, 0, 0.1 * (1 - p) * intensity))
            if thigh_l:
                set_keyframe(thigh_l, frame, rotation=(0.2 * p * intensity, 0, 0))
            if thigh_r:
                set_keyframe(thigh_r, frame, rotation=(0.2 * p * intensity, 0, 0))

        else:
            # Landing impact and recovery
            impact_t = (t - land_impact) / (1.0 - land_impact)

            if impact_t < 0.3:
                squash = ease_out_elastic(impact_t / 0.3)
                crouch = 0.4 * (1 - squash * 0.7) * intensity
                drop = -0.15 * (1 - squash * 0.8) * intensity
            else:
                recover = ease_in_out_sine((impact_t - 0.3) / 0.7)
                crouch = 0.4 * 0.3 * (1 - recover) * intensity
                drop = -0.15 * 0.2 * (1 - recover) * intensity

            if hips:
                set_keyframe(hips, frame, location=(0, 0, drop))
            if spine:
                set_keyframe(spine, frame, rotation=(crouch * 0.4, 0, 0))
            if thigh_l:
                set_keyframe(thigh_l, frame, rotation=(crouch, 0, 0))
            if thigh_r:
                set_keyframe(thigh_r, frame, rotation=(crouch, 0, 0))
            if shin_l:
                set_keyframe(shin_l, frame, rotation=(crouch * 1.5, 0, 0))
            if shin_r:
                set_keyframe(shin_r, frame, rotation=(crouch * 1.5, 0, 0))
            if upper_arm_l:
                set_keyframe(upper_arm_l, frame,
                             rotation=(0.2 * (1 - impact_t) * intensity, 0,
                                       -0.3 * (1 - impact_t) * intensity))
            if upper_arm_r:
                set_keyframe(upper_arm_r, frame,
                             rotation=(0.2 * (1 - impact_t) * intensity, 0,
                                       0.3 * (1 - impact_t) * intensity))

    set_interpolation(action, 'BEZIER')

    return action


def generate_nod(armature, options):
    """Generate a head nodding animation.

    Args:
        armature: Blender armature object
        options: Dict with keys: fps, duration, intensity, loop

    Returns:
        bpy.types.Action
    """
    fps = options.get('fps', 30)
    duration = options.get('duration', 1.5)
    intensity = options.get('intensity', 1.0)

    frame_count = int(fps * duration)
    action = setup_animation(armature, "Nod", fps, frame_count)

    rig = RigBones(armature)
    head = rig.find('head')
    neck = rig.find('neck')

    if not head:
        print("Warning: No head bone found")
        return action

    nods = 3
    nod_duration = 1.0 / nods

    num_keys = max(20, frame_count)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))

        nod_index = min(int(t / nod_duration), nods - 1)
        nod_t = (t - nod_index * nod_duration) / nod_duration

        # Decreasing intensity for each nod
        nod_intensity = intensity * (1 - nod_index * 0.25)

        if nod_t < 0.4:
            p = ease_out_back(nod_t / 0.4)
            nod_angle = 0.2 * p * nod_intensity
        else:
            p = ease_in_out_sine((nod_t - 0.4) / 0.6)
            nod_angle = 0.2 * (1 - p) * nod_intensity

        set_keyframe(head, frame, rotation=(nod_angle, 0, 0))

        if neck:
            set_keyframe(neck, frame, rotation=(nod_angle * 0.3, 0, 0))

    set_interpolation(action, 'BEZIER')

    return action


def generate_look_around(armature, options):
    """Generate a looking around animation with holds.

    Args:
        armature: Blender armature object
        options: Dict with keys: fps, duration, intensity, loop

    Returns:
        bpy.types.Action
    """
    fps = options.get('fps', 30)
    duration = options.get('duration', 4.0)
    intensity = options.get('intensity', 1.0)

    frame_count = int(fps * duration)
    action = setup_animation(armature, "LookAround", fps, frame_count)

    rig = RigBones(armature)
    head = rig.find('head')
    neck = rig.find('neck')
    spine = rig.find('spine')

    if not head:
        print("Warning: No head bone found")
        return action

    # Look sequence: (time_fraction, pitch, yaw)
    look_sequence = [
        (0.0, 0, 0),
        (0.15, 0.05, 0.35),
        (0.35, 0.05, 0.35),      # Hold
        (0.45, 0, 0),
        (0.55, -0.08, -0.4),
        (0.75, -0.08, -0.4),     # Hold
        (0.85, 0.1, 0),
        (0.95, 0, 0),
        (1.0, 0, 0),
    ]

    num_keys = max(30, frame_count)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))

        # Find current segment and interpolate
        pitch, yaw = 0, 0
        for j in range(len(look_sequence) - 1):
            t1, p1, y1 = look_sequence[j]
            t2, p2, y2 = look_sequence[j + 1]

            if t1 <= t <= t2:
                seg_t = (t - t1) / (t2 - t1) if t2 > t1 else 0
                seg_t = ease_in_out_sine(seg_t)
                pitch = lerp(p1, p2, seg_t) * intensity
                yaw = lerp(y1, y2, seg_t) * intensity
                break

        set_keyframe(head, frame, rotation=(pitch, yaw, 0))

        if neck:
            set_keyframe(neck, frame, rotation=(pitch * 0.3, yaw * 0.4, 0))

        if spine:
            set_keyframe(spine, frame, rotation=(0, yaw * 0.1, 0))

    set_interpolation(action, 'BEZIER')

    if options.get('loop', True):
        make_cyclic(action)

    return action


# =============================================================================
# ANIMATION REGISTRY
# =============================================================================

ANIMATION_GENERATORS = {
    'walk': generate_walk_cycle,
    'run': generate_run_cycle,
    'idle': generate_idle,
    'wave': generate_wave,
    'jump': generate_jump,
    'nod': generate_nod,
    'look_around': generate_look_around,
}


def list_animations():
    """Return a list of available animation type names."""
    return list(ANIMATION_GENERATORS.keys())


def generate_animation(armature, animation_type, options=None):
    """Generate an animation by type name.

    Args:
        armature: Blender armature object
        animation_type: One of 'walk', 'run', 'idle', 'wave', 'jump', 'nod', 'look_around'
        options: Dict with fps, duration, intensity, loop, etc.

    Returns:
        bpy.types.Action, or None if animation_type is unknown

    Raises:
        ValueError: If animation_type is not recognized
    """
    if options is None:
        options = {}

    generator = ANIMATION_GENERATORS.get(animation_type)
    if not generator:
        raise ValueError(
            f"Unknown animation type: {animation_type}. "
            f"Available: {list(ANIMATION_GENERATORS.keys())}"
        )

    return generator(armature, options)
