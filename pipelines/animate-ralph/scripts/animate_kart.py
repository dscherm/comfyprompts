"""
animate_kart.py — Kart animation generator for Blender 5.0+

Creates Mario Kart-style animation clips by keyframing object transforms
(no armature/pose bones — karts use object hierarchy).

Usage:
    blender --background --python animate_kart.py -- \
        --input path/to/kart_blender.glb \
        --output-dir path/to/output/ \
        --kart-id player_kart \
        --clips idle,engine_vibrate,steer_left,steer_right,boost,drift_hop,hit_left,hit_right,banana_spin,shell_tumble
"""

import argparse
import json
import math
import os
import random
import sys

import bpy
import mathutils  # noqa: F401 — available in Blender's bundled Python

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FPS = 30

# All supported clip names in canonical order
ALL_CLIPS = [
    "idle",
    "engine_vibrate",
    "steer_left",
    "steer_right",
    "boost",
    "drift_hop",
    "hit_left",
    "hit_right",
    "banana_spin",
    "shell_tumble",
]

# Canonical hierarchy node names expected in the GLB
HIERARCHY_NODES = [
    "KartRoot",
    "Chassis",
    "Hood",
    "Bumper_Front",
    "Bumper_Rear",
    "Panel_L",
    "Panel_R",
    "Spoiler",
    "Seat",
    "EngineBay",
    "Axle_Front",
    "Axle_Rear",
    "WheelMount_FL",
    "WheelMount_FR",
    "SteeringColumn",
    "WheelMount_RL",
    "WheelMount_RR",
    "Exhaust_L",
    "Exhaust_R",
    "FX_Boost_L",
    "FX_Boost_R",
    "FX_Drift_L",
    "FX_Drift_R",
]


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse arguments after the '--' separator that Blender uses."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(
        description="Generate kart animation clips in Blender"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input kart GLB file",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        dest="output_dir",
        help="Directory to write output GLB files and report",
    )
    parser.add_argument(
        "--kart-id",
        required=True,
        dest="kart_id",
        help="Identifier prefix for output files and action names",
    )
    parser.add_argument(
        "--clips",
        default=",".join(ALL_CLIPS),
        help="Comma-separated list of clips to generate (default: all)",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------

def clear_scene() -> None:
    """Remove all objects, actions, and NLA data from a fresh scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path: str) -> None:
    """Import a GLB file into the current scene."""
    bpy.ops.import_scene.gltf(filepath=path)


def find_objects(names: list[str]) -> dict[str, bpy.types.Object]:
    """
    Return a mapping of name -> bpy.types.Object for all names found in the scene.
    Missing names are silently omitted so callers can handle them gracefully.
    """
    result: dict[str, bpy.types.Object] = {}
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            result[name] = obj
    return result


# ---------------------------------------------------------------------------
# Keyframe utilities
# ---------------------------------------------------------------------------

def ensure_rotation_mode(obj: bpy.types.Object, mode: str = "XYZ") -> None:
    obj.rotation_mode = mode


def kf_loc(obj: bpy.types.Object, frame: float, x=None, y=None, z=None) -> None:
    """Insert location keyframes for specified axes only (Blender coords: Z=up, -Y=forward)."""
    axes = {"x": 0, "y": 1, "z": 2}
    values = {"x": x, "y": y, "z": z}
    scene = bpy.context.scene
    scene.frame_set(int(round(frame)))
    for axis, index in axes.items():
        val = values[axis]
        if val is not None:
            obj.location[index] = val
            obj.keyframe_insert(data_path="location", index=index, frame=frame)


def kf_loc_unity(obj: bpy.types.Object, frame: float,
                  ux=None, uy=None, uz=None) -> None:
    """Insert location keyframes using Unity coordinates (Y=up, Z=forward).

    Converts: Unity(x,y,z) → Blender(x, -z, y)
    - Unity X (right)   → Blender X (right)
    - Unity Y (up)      → Blender Z (up)
    - Unity Z (forward) → Blender -Y (forward is -Y in Blender)
    """
    bx = ux
    by = -uz if uz is not None else None
    bz = uy
    kf_loc(obj, frame, x=bx, y=by, z=bz)


def kf_rot(obj: bpy.types.Object, frame: float, x_deg=None, y_deg=None, z_deg=None) -> None:
    """Insert rotation_euler keyframes for specified axes only (degrees, Blender coords)."""
    ensure_rotation_mode(obj)
    scene = bpy.context.scene
    scene.frame_set(int(round(frame)))
    pairs = [
        (0, x_deg),
        (1, y_deg),
        (2, z_deg),
    ]
    for index, deg in pairs:
        if deg is not None:
            obj.rotation_euler[index] = math.radians(deg)
            obj.keyframe_insert(data_path="rotation_euler", index=index, frame=frame)


def kf_rot_unity(obj: bpy.types.Object, frame: float,
                  ux_deg=None, uy_deg=None, uz_deg=None) -> None:
    """Insert rotation keyframes using Unity Euler conventions.

    Converts: Unity(pitch_x, yaw_y, roll_z) → Blender(pitch_x, -roll_z, yaw_y)
    - Unity X (pitch)  → Blender X (pitch)
    - Unity Y (yaw)    → Blender Z (yaw)
    - Unity Z (roll)   → Blender -Y (roll, negated)
    """
    bx = ux_deg
    by = -uz_deg if uz_deg is not None else None
    bz = uy_deg
    kf_rot(obj, frame, x_deg=bx, y_deg=by, z_deg=bz)


def get_fcurves(action: bpy.types.Action) -> list:
    """Get all F-curves from an action (Blender 5.0+ layered action API)."""
    # Blender 5.0 removed action.fcurves — fcurves live inside
    # action.layers[].strips[].channelbags[].fcurves
    fcurves = []
    if hasattr(action, "fcurves"):
        # Legacy API (Blender < 5.0)
        fcurves = list(action.fcurves)
    else:
        # Blender 5.0+ layered actions
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    fcurves.extend(cb.fcurves)
    return fcurves


def make_cyclic(action: bpy.types.Action) -> None:
    """Add CYCLES modifier (REPEAT) to every F-curve in the action."""
    for fcurve in get_fcurves(action):
        mod = fcurve.modifiers.new(type="CYCLES")
        mod.mode_before = "REPEAT"
        mod.mode_after = "REPEAT"


def set_handles_auto_clamped(action: bpy.types.Action) -> None:
    """Set all keyframe handles to AUTO_CLAMPED for smooth easing."""
    for fcurve in get_fcurves(action):
        for kp in fcurve.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"


def set_ease_out(action: bpy.types.Action) -> None:
    """
    Set all keyframe interpolation to EASE_OUT (fast start, slow end).
    Uses BEZIER with AUTO handles which Blender resolves as ease-out for
    one-shot monotonic curves.
    """
    for fcurve in get_fcurves(action):
        for kp in fcurve.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
        fcurve.update()


def new_action(name: str) -> bpy.types.Action:
    """Create (or replace) a named action."""
    if name in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[name])
    action = bpy.data.actions.new(name=name)
    return action


def assign_action(obj: bpy.types.Object, action: bpy.types.Action) -> None:
    """Assign an action to an object's animation_data, creating it if needed."""
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.animation_data.action = action


def push_to_nla(obj: bpy.types.Object, action: bpy.types.Action, track_name: str) -> None:
    """Push the action as an NLA strip on a named track."""
    if obj.animation_data is None:
        obj.animation_data_create()
    # Stash any active action first so it can become an NLA strip
    obj.animation_data.action = action
    # Create a dedicated track
    track = obj.animation_data.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(name=action.name, start=1, action=action)
    strip.action_frame_start = action.frame_range[0]
    strip.action_frame_end = action.frame_range[1]
    # Clear the active action so the NLA strip drives the object
    obj.animation_data.action = None


# ---------------------------------------------------------------------------
# Clip builders
# ---------------------------------------------------------------------------

def build_kart_idle(
    kart_id: str,
    objs: dict[str, bpy.types.Object],
) -> dict:
    """
    kart_idle — 60 frames, looping.
    Chassis: y oscillates 0 → -0.015 → 0 (sine pattern).
    EngineBay: subtle y jitter, keyframe every 2 frames.
    """
    clip_name = "kart_idle"
    action_name = f"{kart_id}_{clip_name}"
    targets_used: list[str] = []

    chassis = objs.get("Chassis")
    engine_bay = objs.get("EngineBay")

    chassis_action = new_action(action_name + "_chassis") if chassis else None
    engine_action = new_action(action_name + "_engine") if engine_bay else None

    # We combine into a single action per logical clip by keying objects
    # directly. Blender allows multiple objects to share one action only if
    # their data paths match, which they won't across different objects.
    # Strategy: create one action per animated object, then push all to NLA
    # under the same track name so exporters pick them up together.

    if chassis:
        ensure_rotation_mode(chassis)
        assign_action(chassis, chassis_action)
        chassis_keyframes = [
            (0, 0.0),
            (15, -0.015),
            (30, 0.0),
            (45, -0.015),
            (60, 0.0),
        ]
        for frame, uy_val in chassis_keyframes:
            kf_loc_unity(chassis, frame, uy=uy_val)
        make_cyclic(chassis_action)
        set_handles_auto_clamped(chassis_action)
        targets_used.append("Chassis")

    if engine_bay:
        ensure_rotation_mode(engine_bay)
        assign_action(engine_bay, engine_action)
        rng = random.Random(42)  # deterministic seed
        for frame in range(0, 62, 2):
            jitter = rng.uniform(-0.002, 0.002)
            kf_loc_unity(engine_bay, frame, uy=jitter)
        # Ensure frame 60 == frame 0 for seamless loop
        kf_loc_unity(engine_bay, 60, uy=0.0)
        make_cyclic(engine_action)
        targets_used.append("EngineBay")

    if chassis:
        push_to_nla(chassis, chassis_action, clip_name)
    if engine_bay:
        push_to_nla(engine_bay, engine_action, clip_name)

    return {
        "name": f"kart_{clip_name}",
        "frames": 60,
        "duration_s": round(60 / FPS, 3),
        "loop": True,
        "targets": targets_used,
        "_actions": [a for a in [chassis_action, engine_action] if a],
        "_primary_obj": chassis or engine_bay,
    }


def build_kart_engine_vibrate(
    kart_id: str,
    objs: dict[str, bpy.types.Object],
) -> dict:
    """
    kart_engine_vibrate — 15 frames, looping.
    Chassis: rapid y shake + slight z roll.
    """
    clip_name = "engine_vibrate"
    action_name = f"{kart_id}_kart_{clip_name}"
    targets_used: list[str] = []

    chassis = objs.get("Chassis")
    if not chassis:
        return {
            "name": f"kart_{clip_name}",
            "frames": 15,
            "duration_s": round(15 / FPS, 3),
            "loop": True,
            "targets": [],
        }

    ensure_rotation_mode(chassis)
    action = new_action(action_name)
    assign_action(chassis, action)

    # Unity Y position shake (vertical bounce → Blender Z)
    y_kf = [
        (0, 0.0),
        (2, -0.003),
        (4, 0.002),
        (6, -0.004),
        (8, 0.001),
        (10, -0.003),
        (12, 0.002),
        (15, 0.0),
    ]
    for frame, uy_val in y_kf:
        kf_loc_unity(chassis, frame, uy=uy_val)

    # Unity Z rotation (roll → Blender -Y)
    z_rot_kf = [
        (0, 0.0),
        (4, 0.3),
        (8, -0.2),
        (12, 0.3),
        (15, 0.0),
    ]
    for frame, uz_deg in z_rot_kf:
        kf_rot_unity(chassis, frame, uz_deg=uz_deg)

    make_cyclic(action)
    set_handles_auto_clamped(action)
    targets_used.append("Chassis")
    push_to_nla(chassis, action, f"kart_{clip_name}")

    return {
        "name": f"kart_{clip_name}",
        "frames": 15,
        "duration_s": round(15 / FPS, 3),
        "loop": True,
        "targets": targets_used,
        "_actions": [action],
        "_primary_obj": chassis,
    }


def build_kart_steer_left(
    kart_id: str,
    objs: dict[str, bpy.types.Object],
) -> dict:
    """
    kart_steer_left — 9 frames, one-shot.
    Axle_Front: rotation.y 0° → -25°, ease-out.
    """
    clip_name = "steer_left"
    action_name = f"{kart_id}_kart_{clip_name}"
    targets_used: list[str] = []

    axle = objs.get("Axle_Front")
    if not axle:
        return {
            "name": f"kart_{clip_name}",
            "frames": 9,
            "duration_s": round(9 / FPS, 3),
            "loop": False,
            "targets": [],
        }

    ensure_rotation_mode(axle)
    action = new_action(action_name)
    assign_action(axle, action)

    kf_data = [(0, 0.0), (9, -25.0)]
    for frame, uy_deg in kf_data:
        kf_rot_unity(axle, frame, uy_deg=uy_deg)

    set_ease_out(action)
    targets_used.append("Axle_Front")
    push_to_nla(axle, action, f"kart_{clip_name}")

    return {
        "name": f"kart_{clip_name}",
        "frames": 9,
        "duration_s": round(9 / FPS, 3),
        "loop": False,
        "targets": targets_used,
        "_actions": [action],
        "_primary_obj": axle,
    }


def build_kart_steer_right(
    kart_id: str,
    objs: dict[str, bpy.types.Object],
) -> dict:
    """
    kart_steer_right — 9 frames, one-shot.
    Axle_Front: rotation.y 0° → +25°, ease-out.
    """
    clip_name = "steer_right"
    action_name = f"{kart_id}_kart_{clip_name}"
    targets_used: list[str] = []

    axle = objs.get("Axle_Front")
    if not axle:
        return {
            "name": f"kart_{clip_name}",
            "frames": 9,
            "duration_s": round(9 / FPS, 3),
            "loop": False,
            "targets": [],
        }

    ensure_rotation_mode(axle)
    action = new_action(action_name)
    assign_action(axle, action)

    kf_data = [(0, 0.0), (9, 25.0)]
    for frame, uy_deg in kf_data:
        kf_rot_unity(axle, frame, uy_deg=uy_deg)

    set_ease_out(action)
    targets_used.append("Axle_Front")
    push_to_nla(axle, action, f"kart_{clip_name}")

    return {
        "name": f"kart_{clip_name}",
        "frames": 9,
        "duration_s": round(9 / FPS, 3),
        "loop": False,
        "targets": targets_used,
        "_actions": [action],
        "_primary_obj": axle,
    }


def build_kart_boost(
    kart_id: str,
    objs: dict[str, bpy.types.Object],
) -> dict:
    """
    kart_boost — 29 frames, one-shot.
    KartRoot: pitch tilt (rotation.x) + vertical lift (location.y) + forward push (location.z).
    """
    clip_name = "boost"
    action_name = f"{kart_id}_kart_{clip_name}"
    targets_used: list[str] = []

    root = objs.get("KartRoot")
    if not root:
        return {
            "name": f"kart_{clip_name}",
            "frames": 29,
            "duration_s": round(29 / FPS, 3),
            "loop": False,
            "targets": [],
        }

    ensure_rotation_mode(root)
    action = new_action(action_name)
    assign_action(root, action)

    # Unity X rotation (pitch — stays Blender X)
    rx_kf = [
        (0, 0.0),
        (8, -8.0),
        (17, -9.0),
        (24, 3.0),
        (29, 0.0),
    ]
    for frame, ux_deg in rx_kf:
        kf_rot_unity(root, frame, ux_deg=ux_deg)

    # Unity Y position (vertical lift → Blender Z)
    ly_kf = [
        (0, 0.0),
        (8, 0.1),
        (17, 0.1),
        (24, -0.028),
        (29, 0.0),
    ]
    for frame, uy_val in ly_kf:
        kf_loc_unity(root, frame, uy=uy_val)

    # Unity Z position (forward push → Blender -Y)
    lz_kf = [
        (0, 0.0),
        (8, -0.02),
        (17, -0.007),
        (24, 0.0),
        (29, 0.0),
    ]
    for frame, uz_val in lz_kf:
        kf_loc_unity(root, frame, uz=uz_val)

    set_handles_auto_clamped(action)
    targets_used.append("KartRoot")
    push_to_nla(root, action, f"kart_{clip_name}")

    return {
        "name": f"kart_{clip_name}",
        "frames": 29,
        "duration_s": round(29 / FPS, 3),
        "loop": False,
        "targets": targets_used,
        "_actions": [action],
        "_primary_obj": root,
    }


def build_kart_drift_hop(
    kart_id: str,
    objs: dict[str, bpy.types.Object],
) -> dict:
    """
    kart_drift_hop — 13 frames, one-shot.
    KartRoot: parabolic hop arc on location.y.
    """
    clip_name = "drift_hop"
    action_name = f"{kart_id}_kart_{clip_name}"
    targets_used: list[str] = []

    root = objs.get("KartRoot")
    if not root:
        return {
            "name": f"kart_{clip_name}",
            "frames": 13,
            "duration_s": round(13 / FPS, 3),
            "loop": False,
            "targets": [],
        }

    ensure_rotation_mode(root)
    action = new_action(action_name)
    assign_action(root, action)

    # Unity Y position — hop arc, normalized to 0 baseline (vertical → Blender Z)
    ly_kf = [
        (0, 0.0),
        (3, 0.62),
        (6.5, 0.0),
        (9, -0.06),
        (10, 0.0),
        (13, 0.0),
    ]
    for frame, uy_val in ly_kf:
        kf_loc_unity(root, frame, uy=uy_val)

    set_handles_auto_clamped(action)
    targets_used.append("KartRoot")
    push_to_nla(root, action, f"kart_{clip_name}")

    return {
        "name": f"kart_{clip_name}",
        "frames": 13,
        "duration_s": round(13 / FPS, 3),
        "loop": False,
        "targets": targets_used,
        "_actions": [action],
        "_primary_obj": root,
    }


def build_kart_hit_left(
    kart_id: str,
    objs: dict[str, bpy.types.Object],
) -> dict:
    """
    kart_hit_left — 17 frames, one-shot.
    KartRoot: rotation.z 0° → +10° → 0°, location.y bounce.
    """
    clip_name = "hit_left"
    action_name = f"{kart_id}_kart_{clip_name}"
    targets_used: list[str] = []

    root = objs.get("KartRoot")
    if not root:
        return {
            "name": f"kart_{clip_name}",
            "frames": 17,
            "duration_s": round(17 / FPS, 3),
            "loop": False,
            "targets": [],
        }

    ensure_rotation_mode(root)
    action = new_action(action_name)
    assign_action(root, action)

    # Unity Z rotation (roll/yaw impact → Blender -Y)
    rz_kf = [
        (0, 0.0),
        (2.5, 10.0),
        (17, 0.0),
    ]
    for frame, uz_deg in rz_kf:
        kf_rot_unity(root, frame, uz_deg=uz_deg)

    # Unity Y position (bounce → Blender Z)
    ly_kf = [
        (0, 0.0),
        (2.5, 0.11),
        (17, 0.0),
    ]
    for frame, uy_val in ly_kf:
        kf_loc_unity(root, frame, uy=uy_val)

    set_handles_auto_clamped(action)
    targets_used.append("KartRoot")
    push_to_nla(root, action, f"kart_{clip_name}")

    return {
        "name": f"kart_{clip_name}",
        "frames": 17,
        "duration_s": round(17 / FPS, 3),
        "loop": False,
        "targets": targets_used,
        "_actions": [action],
        "_primary_obj": root,
    }


def build_kart_hit_right(
    kart_id: str,
    objs: dict[str, bpy.types.Object],
) -> dict:
    """
    kart_hit_right — 17 frames, one-shot.
    KartRoot: rotation.z 0° → -10° → 0°, location.y bounce.
    """
    clip_name = "hit_right"
    action_name = f"{kart_id}_kart_{clip_name}"
    targets_used: list[str] = []

    root = objs.get("KartRoot")
    if not root:
        return {
            "name": f"kart_{clip_name}",
            "frames": 17,
            "duration_s": round(17 / FPS, 3),
            "loop": False,
            "targets": [],
        }

    ensure_rotation_mode(root)
    action = new_action(action_name)
    assign_action(root, action)

    # Unity Z rotation (mirror of hit_left → Blender -Y)
    rz_kf = [
        (0, 0.0),
        (2.5, -10.0),
        (17, 0.0),
    ]
    for frame, uz_deg in rz_kf:
        kf_rot_unity(root, frame, uz_deg=uz_deg)

    # Unity Y position (bounce → Blender Z, same as hit_left)
    ly_kf = [
        (0, 0.0),
        (2.5, 0.11),
        (17, 0.0),
    ]
    for frame, uy_val in ly_kf:
        kf_loc_unity(root, frame, uy=uy_val)

    set_handles_auto_clamped(action)
    targets_used.append("KartRoot")
    push_to_nla(root, action, f"kart_{clip_name}")

    return {
        "name": f"kart_{clip_name}",
        "frames": 17,
        "duration_s": round(17 / FPS, 3),
        "loop": False,
        "targets": targets_used,
        "_actions": [action],
        "_primary_obj": root,
    }


def build_kart_banana_spin(
    kart_id: str,
    objs: dict[str, bpy.types.Object],
) -> dict:
    """
    kart_banana_spin — 22 frames, one-shot.
    KartRoot: pitch oscillation (rotation.x) + full Y spin (decelerating).
    """
    clip_name = "banana_spin"
    action_name = f"{kart_id}_kart_{clip_name}"
    targets_used: list[str] = []

    root = objs.get("KartRoot")
    if not root:
        return {
            "name": f"kart_{clip_name}",
            "frames": 22,
            "duration_s": round(22 / FPS, 3),
            "loop": False,
            "targets": [],
        }

    ensure_rotation_mode(root)
    action = new_action(action_name)
    assign_action(root, action)

    # Unity X rotation (pitch oscillation → stays Blender X)
    rx_kf = [
        (0, 0.0),
        (5, -15.0),
        (10, 10.0),
        (15, -15.0),
        (22, 0.0),
    ]
    for frame, ux_deg in rx_kf:
        kf_rot_unity(root, frame, ux_deg=ux_deg)

    # Unity Y rotation (full 360° yaw spin, decelerating → Blender Z, index=2)
    ry_kf = [
        (0, 0.0),
        (5, -52.0),
        (10, -148.0),
        (15, -260.0),
        (22, -360.0),
    ]
    for frame, uy_deg in ry_kf:
        kf_rot_unity(root, frame, uy_deg=uy_deg)

    # Set spin curve to ease-in-out: fast at start, decelerates toward end
    # We achieve this by manually setting handle types on the Z rotation fcurve
    # (Unity Y yaw maps to Blender Z = array_index 2)
    for fcurve in get_fcurves(action):
        if fcurve.data_path == "rotation_euler" and fcurve.array_index == 2:
            for kp in fcurve.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"
        else:
            for kp in fcurve.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"

    targets_used.append("KartRoot")
    push_to_nla(root, action, f"kart_{clip_name}")

    return {
        "name": f"kart_{clip_name}",
        "frames": 22,
        "duration_s": round(22 / FPS, 3),
        "loop": False,
        "targets": targets_used,
        "_actions": [action],
        "_primary_obj": root,
    }


def build_kart_shell_tumble(
    kart_id: str,
    objs: dict[str, bpy.types.Object],
) -> dict:
    """
    kart_shell_tumble — 35 frames, one-shot.
    KartRoot: complex X rotation tumble + parabolic Y bounce.
    """
    clip_name = "shell_tumble"
    action_name = f"{kart_id}_kart_{clip_name}"
    targets_used: list[str] = []

    root = objs.get("KartRoot")
    if not root:
        return {
            "name": f"kart_{clip_name}",
            "frames": 35,
            "duration_s": round(35 / FPS, 3),
            "loop": False,
            "targets": [],
        }

    ensure_rotation_mode(root)
    action = new_action(action_name)
    assign_action(root, action)

    # Unity X rotation (complex tumble → stays Blender X)
    rx_kf = [
        (0, 0.0),
        (8, -174.0),
        (15, -308.0),
        (19, -370.0),
        (22, -365.0),
        (25.5, -360.0),
        (29, -362.0),
        (31.5, -365.0),
        (35, -360.0),
    ]
    for frame, ux_deg in rx_kf:
        kf_rot_unity(root, frame, ux_deg=ux_deg)

    # Unity Y position (parabolic bounce, lands at frame 19 → Blender Z)
    ly_kf = [
        (0, 0.0),
        (8, 2.0),
        (12.5, 1.53),
        (15, 0.75),
        (19, 0.0),
        (25.5, 0.0),
    ]
    for frame, uy_val in ly_kf:
        kf_loc_unity(root, frame, uy=uy_val)

    set_handles_auto_clamped(action)
    targets_used.append("KartRoot")
    push_to_nla(root, action, f"kart_{clip_name}")

    return {
        "name": f"kart_{clip_name}",
        "frames": 35,
        "duration_s": round(35 / FPS, 3),
        "loop": False,
        "targets": targets_used,
        "_actions": [action],
        "_primary_obj": root,
    }


# ---------------------------------------------------------------------------
# Clip dispatch table
# ---------------------------------------------------------------------------

CLIP_BUILDERS = {
    "idle": build_kart_idle,
    "engine_vibrate": build_kart_engine_vibrate,
    "steer_left": build_kart_steer_left,
    "steer_right": build_kart_steer_right,
    "boost": build_kart_boost,
    "drift_hop": build_kart_drift_hop,
    "hit_left": build_kart_hit_left,
    "hit_right": build_kart_hit_right,
    "banana_spin": build_kart_banana_spin,
    "shell_tumble": build_kart_shell_tumble,
}


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def export_single_clip_glb(
    output_path: str,
    clip_info: dict,
) -> None:
    """
    Export a GLB for a single clip.
    Strategy: mute all NLA tracks, then unmute only the tracks for this clip,
    export, then restore.
    """
    clip_track_name = clip_info["name"]  # e.g. "kart_idle"
    primary_obj = clip_info.get("_primary_obj")

    # Collect all animated objects in the scene
    all_animated_objs: list[bpy.types.Object] = [
        o for o in bpy.data.objects if o.animation_data
    ]

    # Mute all NLA tracks on all objects
    track_states: dict[tuple, bool] = {}
    for obj in all_animated_objs:
        for track in obj.animation_data.nla_tracks:
            key = (obj.name, track.name)
            track_states[key] = track.mute
            track.mute = True

    # Unmute only the tracks matching this clip
    for obj in all_animated_objs:
        for track in obj.animation_data.nla_tracks:
            if track.name == clip_track_name:
                track.mute = False

    # Deselect all, then select all objects (GLB exporter uses selection or all)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        obj.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        export_animations=True,
        export_nla_strips=True,
        export_nla_strips_merged_animation_name=clip_track_name,
        use_selection=False,
    )

    # Restore track mute states
    for obj in all_animated_objs:
        for track in obj.animation_data.nla_tracks:
            key = (obj.name, track.name)
            if key in track_states:
                track.mute = track_states[key]


def export_combined_glb(output_path: str) -> None:
    """Export a combined GLB with all NLA tracks active."""
    all_animated_objs: list[bpy.types.Object] = [
        o for o in bpy.data.objects if o.animation_data
    ]

    # Unmute all NLA tracks
    for obj in all_animated_objs:
        for track in obj.animation_data.nla_tracks:
            track.mute = False

    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        obj.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        export_animations=True,
        export_nla_strips=True,
        use_selection=False,
    )


# ---------------------------------------------------------------------------
# FBX export for Unity
# ---------------------------------------------------------------------------

# Clips that should be exported as baked FBX for Unity's Animator/Legacy system.
# These have complex multi-keyframe curves hard to replicate procedurally.
UNITY_IMPACT_CLIPS = {"boost", "drift_hop", "hit_left", "hit_right", "banana_spin", "shell_tumble"}


def export_single_clip_fbx_unity(
    output_path: str,
    clip_info: dict,
) -> None:
    """Export a single animation clip as FBX for Unity import.

    Uses the same mute/unmute strategy as GLB export, but with FBX settings
    optimized for Unity (Y-up, -Z forward, baked animation, no leaf bones).
    """
    clip_track_name = clip_info["name"]

    all_animated_objs: list[bpy.types.Object] = [
        o for o in bpy.data.objects if o.animation_data
    ]

    # Mute all NLA tracks
    track_states: dict[tuple, bool] = {}
    for obj in all_animated_objs:
        for track in obj.animation_data.nla_tracks:
            key = (obj.name, track.name)
            track_states[key] = track.mute
            track.mute = True

    # Unmute only this clip's tracks
    for obj in all_animated_objs:
        for track in obj.animation_data.nla_tracks:
            if track.name == clip_track_name:
                track.mute = False

    # Select all objects for export
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        obj.select_set(True)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=False,
        object_types={"MESH", "EMPTY"},
        bake_anim=True,
        bake_anim_use_all_bones=False,
        bake_anim_use_nla_strips=True,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        add_leaf_bones=False,
        mesh_smooth_type="FACE",
    )

    # Restore track mute states
    for obj in all_animated_objs:
        for track in obj.animation_data.nla_tracks:
            key = (obj.name, track.name)
            if key in track_states:
                track.mute = track_states[key]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    input_path = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output_dir)
    kart_id = args.kart_id
    requested_clips = [c.strip() for c in args.clips.split(",") if c.strip()]

    # Validate
    if not os.path.isfile(input_path):
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    unknown = [c for c in requested_clips if c not in CLIP_BUILDERS]
    if unknown:
        print(f"ERROR: Unknown clip(s): {unknown}. Valid: {list(CLIP_BUILDERS.keys())}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"[animate_kart] Input:      {input_path}")
    print(f"[animate_kart] Output dir: {output_dir}")
    print(f"[animate_kart] Kart ID:    {kart_id}")
    print(f"[animate_kart] Clips:      {requested_clips}")

    # ---- Scene setup ----
    clear_scene()
    bpy.context.scene.render.fps = FPS

    print("[animate_kart] Importing GLB...")
    import_glb(input_path)

    # Find all expected hierarchy objects
    objs = find_objects(HIERARCHY_NODES)
    found_names = list(objs.keys())
    missing_names = [n for n in HIERARCHY_NODES if n not in objs]

    print(f"[animate_kart] Found objects:   {found_names}")
    if missing_names:
        print(f"[animate_kart] Missing objects: {missing_names} (will skip animations targeting them)")

    # ---- Build clips ----
    clip_reports: list[dict] = []
    clip_infos: list[dict] = []

    for clip_key in requested_clips:
        print(f"[animate_kart] Building clip: kart_{clip_key}")
        builder = CLIP_BUILDERS[clip_key]
        info = builder(kart_id, objs)
        clip_reports.append({
            "name": info["name"],
            "frames": info["frames"],
            "duration_s": info["duration_s"],
            "loop": info["loop"],
            "targets": info["targets"],
        })
        clip_infos.append(info)

    # ---- Export individual GLBs ----
    print("[animate_kart] Exporting individual clip GLBs...")
    for clip_key, info in zip(requested_clips, clip_infos):
        out_file = os.path.join(output_dir, f"{kart_id}_{clip_key}.glb")
        print(f"  -> {out_file}")
        try:
            export_single_clip_glb(out_file, info)
        except Exception as exc:
            print(f"  WARNING: Export failed for {clip_key}: {exc}", file=sys.stderr)

    # ---- Export combined GLB ----
    combined_path = os.path.join(output_dir, f"{kart_id}_all_anims.glb")
    print(f"[animate_kart] Exporting combined GLB: {combined_path}")
    try:
        export_combined_glb(combined_path)
    except Exception as exc:
        print(f"  WARNING: Combined export failed: {exc}", file=sys.stderr)

    # ---- Export impact clips as FBX for Unity ----
    fbx_dir = os.path.join(output_dir, "unity_fbx")
    os.makedirs(fbx_dir, exist_ok=True)
    fbx_exported = []
    for clip_key, info in zip(requested_clips, clip_infos):
        if clip_key in UNITY_IMPACT_CLIPS:
            fbx_path = os.path.join(fbx_dir, f"{kart_id}_kart_{clip_key}.fbx")
            print(f"[animate_kart] Exporting Unity FBX: {fbx_path}")
            try:
                export_single_clip_fbx_unity(fbx_path, info)
                fbx_exported.append(clip_key)
            except Exception as exc:
                print(f"  WARNING: FBX export failed for {clip_key}: {exc}", file=sys.stderr)

    if fbx_exported:
        print(f"[animate_kart] Unity FBX clips exported: {fbx_exported}")

    # ---- Write report ----
    report = {
        "kart_id": kart_id,
        "clips": clip_reports,
        "total_clips": len(clip_reports),
        "output_dir": output_dir,
    }
    report_path = os.path.join(output_dir, f"{kart_id}_animation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    print(f"[animate_kart] Report written: {report_path}")

    # Print summary
    print("\n[animate_kart] Done.")
    print(f"  Clips generated: {len(clip_reports)}")
    for cr in clip_reports:
        loop_tag = " (loop)" if cr["loop"] else ""
        targets_tag = ", ".join(cr["targets"]) if cr["targets"] else "no targets found"
        print(f"    {cr['name']:30s}  {cr['frames']:3d} frames  {cr['duration_s']:.3f}s{loop_tag}  [{targets_tag}]")


if __name__ == "__main__":
    main()
