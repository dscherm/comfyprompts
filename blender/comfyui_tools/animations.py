"""Animation generators for ComfyUI Blender addon."""

import math

import bpy

from .utils import (
    RigBones,
    ease_in_out_sine,
    ease_out_back,
    ease_out_elastic,
    lerp,
    make_cyclic,
    set_interpolation,
    set_keyframe,
    smooth_step,
)


def generate_walk_cycle(armature, duration, fps, intensity, loop):
    """Generate a walk cycle animation."""
    frame_count = int(fps * duration)

    if armature.animation_data:
        armature.animation_data_clear()

    action = bpy.data.actions.new(name=f"{armature.name}_walk")
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action

    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count

    rig = RigBones(armature)

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

        hips = rig.find('hips')
        if hips:
            sway_x = math.sin(walk_phase) * hip_sway
            bounce_z = -abs(math.sin(half_phase)) * 0.015 * intensity
            rot_z = math.sin(walk_phase) * hip_rotation
            rot_x = math.sin(walk_phase) * hip_tilt
            set_keyframe(hips, frame, location=(sway_x, 0, bounce_z), rotation=(rot_x, 0, rot_z))

        spine = rig.find('spine')
        if spine:
            twist = -math.sin(walk_phase) * spine_twist
            set_keyframe(spine, frame, rotation=(spine_bend, 0, twist))

        spine2 = rig.find('spine2') or rig.find('chest')
        if spine2:
            twist = -math.sin(walk_phase) * spine_twist * 0.7
            set_keyframe(spine2, frame, rotation=(0, 0, twist))

        shoulder_l = rig.find('shoulder_l')
        if shoulder_l:
            rot = -math.sin(walk_phase) * shoulder_rotation
            set_keyframe(shoulder_l, frame, rotation=(rot * 0.3, 0, rot))

        shoulder_r = rig.find('shoulder_r')
        if shoulder_r:
            rot = math.sin(walk_phase) * shoulder_rotation
            set_keyframe(shoulder_r, frame, rotation=(rot * 0.3, 0, -rot))

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

        thigh_l = rig.find('thigh_l')
        if thigh_l:
            swing = math.sin(walk_phase) * leg_swing
            set_keyframe(thigh_l, frame, rotation=(swing, 0, 0))

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

        thigh_r = rig.find('thigh_r')
        if thigh_r:
            swing = -math.sin(walk_phase) * leg_swing
            set_keyframe(thigh_r, frame, rotation=(swing, 0, 0))

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
    if loop:
        make_cyclic(action)
    return action


def generate_run_cycle(armature, duration, fps, intensity, loop):
    """Generate a run cycle animation."""
    frame_count = int(fps * duration)

    if armature.animation_data:
        armature.animation_data_clear()

    action = bpy.data.actions.new(name=f"{armature.name}_run")
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action

    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count

    rig = RigBones(armature)

    body_lean = 0.18 * intensity
    hip_bounce = 0.04 * intensity
    arm_swing = 0.6 * intensity
    leg_swing = 0.65 * intensity
    knee_bend_max = 0.7 * intensity

    num_keys = max(8, frame_count // 2)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))
        run_phase = t * 2 * math.pi
        double_phase = t * 4 * math.pi

        hips = rig.find('hips')
        if hips:
            bounce = -abs(math.sin(double_phase)) * hip_bounce
            sway = math.sin(run_phase) * 0.03 * intensity
            set_keyframe(hips, frame, location=(sway, 0, bounce), rotation=(body_lean, 0, math.sin(run_phase) * 0.08))

        spine = rig.find('spine')
        if spine:
            set_keyframe(spine, frame, rotation=(body_lean * 0.7, 0, -math.sin(run_phase) * 0.05))

        upper_arm_l = rig.find('upper_arm_l')
        if upper_arm_l:
            swing = -math.sin(run_phase) * arm_swing
            set_keyframe(upper_arm_l, frame, rotation=(swing, 0.15, 0))

        forearm_l = rig.find('forearm_l')
        if forearm_l:
            bend = 0.4 + (-math.sin(run_phase) + 1) / 2 * 0.5
            set_keyframe(forearm_l, frame, rotation=(bend * intensity, 0, 0))

        upper_arm_r = rig.find('upper_arm_r')
        if upper_arm_r:
            swing = math.sin(run_phase) * arm_swing
            set_keyframe(upper_arm_r, frame, rotation=(swing, -0.15, 0))

        forearm_r = rig.find('forearm_r')
        if forearm_r:
            bend = 0.4 + (math.sin(run_phase) + 1) / 2 * 0.5
            set_keyframe(forearm_r, frame, rotation=(bend * intensity, 0, 0))

        thigh_l = rig.find('thigh_l')
        if thigh_l:
            swing = math.sin(run_phase) * leg_swing
            set_keyframe(thigh_l, frame, rotation=(swing, 0, 0))

        shin_l = rig.find('shin_l')
        if shin_l:
            phase = (math.sin(run_phase) + 1) / 2
            bend = smooth_step(phase) * knee_bend_max
            set_keyframe(shin_l, frame, rotation=(bend, 0, 0))

        thigh_r = rig.find('thigh_r')
        if thigh_r:
            swing = -math.sin(run_phase) * leg_swing
            set_keyframe(thigh_r, frame, rotation=(swing, 0, 0))

        shin_r = rig.find('shin_r')
        if shin_r:
            phase = (-math.sin(run_phase) + 1) / 2
            bend = smooth_step(phase) * knee_bend_max
            set_keyframe(shin_r, frame, rotation=(bend, 0, 0))

        head = rig.find('head')
        if head:
            counter = -body_lean * 0.5
            set_keyframe(head, frame, rotation=(counter, 0, 0))

    set_interpolation(action, 'BEZIER')
    if loop:
        make_cyclic(action)
    return action


def generate_idle(armature, duration, fps, intensity, loop):
    """Generate an idle/breathing animation."""
    frame_count = int(fps * duration)

    if armature.animation_data:
        armature.animation_data_clear()

    action = bpy.data.actions.new(name=f"{armature.name}_idle")
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action

    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count

    rig = RigBones(armature)

    breath_amount = 0.02 * intensity
    sway_amount = 0.01 * intensity
    head_movement = 0.015 * intensity

    num_keys = max(16, frame_count // 4)

    for i in range(num_keys + 1):
        t = i / num_keys
        frame = 1 + int(t * (frame_count - 1))
        breath_phase = t * 2 * math.pi
        sway_phase = t * math.pi

        hips = rig.find('hips')
        if hips:
            sway = math.sin(sway_phase) * sway_amount
            set_keyframe(hips, frame, location=(sway, 0, 0), rotation=(0, 0, sway * 2))

        spine = rig.find('spine')
        if spine:
            breath = ease_in_out_sine(t) * breath_amount
            set_keyframe(spine, frame, rotation=(-breath, 0, 0))

        spine2 = rig.find('spine2') or rig.find('chest')
        if spine2:
            breath = ease_in_out_sine(t) * breath_amount * 1.5
            set_keyframe(spine2, frame, rotation=(-breath, 0, 0))

        shoulder_l = rig.find('shoulder_l')
        if shoulder_l:
            rise = ease_in_out_sine(t) * breath_amount * 0.5
            set_keyframe(shoulder_l, frame, rotation=(rise, 0, 0))

        shoulder_r = rig.find('shoulder_r')
        if shoulder_r:
            rise = ease_in_out_sine(t) * breath_amount * 0.5
            set_keyframe(shoulder_r, frame, rotation=(rise, 0, 0))

        upper_arm_l = rig.find('upper_arm_l')
        if upper_arm_l:
            set_keyframe(upper_arm_l, frame, rotation=(0.05, 0.1, 0))

        upper_arm_r = rig.find('upper_arm_r')
        if upper_arm_r:
            set_keyframe(upper_arm_r, frame, rotation=(0.05, -0.1, 0))

        forearm_l = rig.find('forearm_l')
        if forearm_l:
            set_keyframe(forearm_l, frame, rotation=(0.15, 0, 0))

        forearm_r = rig.find('forearm_r')
        if forearm_r:
            set_keyframe(forearm_r, frame, rotation=(0.15, 0, 0))

        head = rig.find('head')
        if head:
            look_x = math.sin(sway_phase * 0.7) * head_movement
            look_z = math.sin(sway_phase * 0.5) * head_movement
            set_keyframe(head, frame, rotation=(look_x, 0, look_z))

        neck = rig.find('neck')
        if neck:
            look_z = math.sin(sway_phase * 0.5) * head_movement * 0.5
            set_keyframe(neck, frame, rotation=(0, 0, look_z))

    set_interpolation(action, 'BEZIER')
    if loop:
        make_cyclic(action)
    return action


def generate_wave(armature, duration, fps, intensity, loop):
    """Generate a waving gesture animation."""
    frame_count = int(fps * duration)

    if armature.animation_data:
        armature.animation_data_clear()

    action = bpy.data.actions.new(name=f"{armature.name}_wave")
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action

    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count

    rig = RigBones(armature)

    wave_cycles = 3
    arm_raise = 1.2 * intensity
    wave_amount = 0.4 * intensity

    for i in range(frame_count + 1):
        frame = i + 1
        t = i / frame_count

        if t < 0.3:
            raise_t = ease_out_back(t / 0.3)
            arm_angle = raise_t * arm_raise
            wave_rot = 0
        elif t < 0.8:
            arm_angle = arm_raise
            wave_t = (t - 0.3) / 0.5
            wave_rot = math.sin(wave_t * wave_cycles * 2 * math.pi) * wave_amount
        else:
            lower_t = ease_in_out_sine((t - 0.8) / 0.2)
            arm_angle = arm_raise * (1 - lower_t)
            wave_rot = 0

        upper_arm_r = rig.find('upper_arm_r')
        if upper_arm_r:
            set_keyframe(upper_arm_r, frame, rotation=(-arm_angle, -0.3, 0.5))

        forearm_r = rig.find('forearm_r')
        if forearm_r:
            set_keyframe(forearm_r, frame, rotation=(0.8 * intensity, wave_rot, 0))

        hand_r = rig.find('hand_r')
        if hand_r:
            set_keyframe(hand_r, frame, rotation=(wave_rot * 0.5, 0, 0))

        spine = rig.find('spine')
        if spine:
            lean = arm_angle * 0.05
            set_keyframe(spine, frame, rotation=(0, 0, -lean))

        head = rig.find('head')
        if head:
            set_keyframe(head, frame, rotation=(0.05, 0, 0.1))

    set_interpolation(action, 'BEZIER')
    return action


def generate_jump(armature, duration, fps, intensity, loop):
    """Generate a jump animation."""
    frame_count = int(fps * duration)

    if armature.animation_data:
        armature.animation_data_clear()

    action = bpy.data.actions.new(name=f"{armature.name}_jump")
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action

    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count

    rig = RigBones(armature)

    crouch_depth = 0.08 * intensity
    jump_height = 0.15 * intensity
    arm_raise = 0.8 * intensity

    for i in range(frame_count + 1):
        frame = i + 1
        t = i / frame_count

        if t < 0.2:
            crouch_t = ease_in_out_sine(t / 0.2)
            height = -crouch_depth * crouch_t
            leg_bend = 0.6 * crouch_t * intensity
            arm_pos = 0.3 * crouch_t
            spine_lean = 0.15 * crouch_t * intensity
        elif t < 0.3:
            launch_t = (t - 0.2) / 0.1
            height = lerp(-crouch_depth, jump_height * 0.5, ease_out_back(launch_t))
            leg_bend = 0.6 * (1 - launch_t) * intensity
            arm_pos = lerp(0.3, -arm_raise, launch_t)
            spine_lean = lerp(0.15, -0.1, launch_t) * intensity
        elif t < 0.7:
            air_t = (t - 0.3) / 0.4
            height = jump_height * (1 - 4 * (air_t - 0.5) ** 2)
            leg_bend = 0.2 * intensity
            arm_pos = -arm_raise
            spine_lean = -0.1 * intensity
        else:
            land_t = (t - 0.7) / 0.3
            height = lerp(0, -crouch_depth * 0.5, ease_out_elastic(land_t) if land_t < 0.5 else ease_in_out_sine((land_t - 0.5) * 2) * 0.5)
            leg_bend = lerp(0, 0.4, land_t if land_t < 0.3 else 0.4 * (1 - (land_t - 0.3) / 0.7)) * intensity
            arm_pos = lerp(-arm_raise, 0, land_t)
            spine_lean = lerp(-0.1, 0, land_t) * intensity

        hips = rig.find('hips')
        if hips:
            set_keyframe(hips, frame, location=(0, 0, height), rotation=(0, 0, 0))

        spine = rig.find('spine')
        if spine:
            set_keyframe(spine, frame, rotation=(spine_lean, 0, 0))

        thigh_l = rig.find('thigh_l')
        if thigh_l:
            set_keyframe(thigh_l, frame, rotation=(leg_bend * 0.5, 0, 0))

        thigh_r = rig.find('thigh_r')
        if thigh_r:
            set_keyframe(thigh_r, frame, rotation=(leg_bend * 0.5, 0, 0))

        shin_l = rig.find('shin_l')
        if shin_l:
            set_keyframe(shin_l, frame, rotation=(leg_bend, 0, 0))

        shin_r = rig.find('shin_r')
        if shin_r:
            set_keyframe(shin_r, frame, rotation=(leg_bend, 0, 0))

        upper_arm_l = rig.find('upper_arm_l')
        if upper_arm_l:
            set_keyframe(upper_arm_l, frame, rotation=(arm_pos, 0.2, 0))

        upper_arm_r = rig.find('upper_arm_r')
        if upper_arm_r:
            set_keyframe(upper_arm_r, frame, rotation=(arm_pos, -0.2, 0))

    set_interpolation(action, 'BEZIER')
    return action


def generate_nod(armature, duration, fps, intensity, loop):
    """Generate a head nodding animation."""
    frame_count = int(fps * duration)

    if armature.animation_data:
        armature.animation_data_clear()

    action = bpy.data.actions.new(name=f"{armature.name}_nod")
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action

    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count

    rig = RigBones(armature)

    nod_amount = 0.25 * intensity
    nods = 2

    for i in range(frame_count + 1):
        frame = i + 1
        t = i / frame_count
        nod_phase = t * nods * 2 * math.pi
        nod = math.sin(nod_phase) * nod_amount

        head = rig.find('head')
        if head:
            set_keyframe(head, frame, rotation=(nod, 0, 0))

        neck = rig.find('neck')
        if neck:
            set_keyframe(neck, frame, rotation=(nod * 0.3, 0, 0))

    set_interpolation(action, 'BEZIER')
    return action


def generate_look_around(armature, duration, fps, intensity, loop):
    """Generate a looking around animation."""
    frame_count = int(fps * duration)

    if armature.animation_data:
        armature.animation_data_clear()

    action = bpy.data.actions.new(name=f"{armature.name}_look_around")
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = action

    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count

    rig = RigBones(armature)

    turn_amount = 0.4 * intensity

    for i in range(frame_count + 1):
        frame = i + 1
        t = i / frame_count

        if t < 0.25:
            look = ease_in_out_sine(t / 0.25) * turn_amount
        elif t < 0.5:
            look = lerp(turn_amount, 0, ease_in_out_sine((t - 0.25) / 0.25))
        elif t < 0.75:
            look = -ease_in_out_sine((t - 0.5) / 0.25) * turn_amount
        else:
            look = lerp(-turn_amount, 0, ease_in_out_sine((t - 0.75) / 0.25))

        head = rig.find('head')
        if head:
            set_keyframe(head, frame, rotation=(0, 0, look))

        neck = rig.find('neck')
        if neck:
            set_keyframe(neck, frame, rotation=(0, 0, look * 0.5))

        spine = rig.find('spine')
        if spine:
            set_keyframe(spine, frame, rotation=(0, 0, look * 0.1))

    set_interpolation(action, 'BEZIER')
    if loop:
        make_cyclic(action)
    return action


ANIMATION_GENERATORS = {
    'walk': generate_walk_cycle,
    'run': generate_run_cycle,
    'idle': generate_idle,
    'wave': generate_wave,
    'jump': generate_jump,
    'nod': generate_nod,
    'look_around': generate_look_around,
}
