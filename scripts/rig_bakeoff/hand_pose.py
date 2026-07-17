"""Relaxed-hand posing + sign-resolved palm direction, measured live in Blender.

Two things make a hanging hand read as natural: the fingers CURL into a loose
relaxed shape (not splayed straight out), and the PALM faces the body.

Both are measured, not assumed — the same discipline the rig scanner uses:

  * flexion direction is found by the displacement test (curl reduces the
    finger's outward reach), so we never guess which way a knuckle folds;
  * the palm direction is the direction the FINGERTIPS travel when they curl
    (they move toward the palm), which resolves the sign ambiguity that a
    static palm-plane normal cannot.

Isolated from rig_scan.py on purpose: the scanner is working and was regressed
once by an over-reaching edit, so hand logic lives here and measures against the
live armature instead of extending the manifest schema.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Quaternion, Vector

RELAX_CURL_DEG = 26.0     # per-phalanx flexion for a loose relaxed hand
_PROBE_DEG = 20.0


def _wh(arm, pb) -> Vector:
    return arm.matrix_world @ pb.bone.head_local


def _wt(arm, pb) -> Vector:
    return arm.matrix_world @ pb.bone.tail_local


def _axis_in_bone(arm, pb, world_vec: Vector) -> Vector:
    R = (arm.matrix_world @ pb.bone.matrix_local).to_3x3()
    return (R.inverted() @ world_vec).normalized()


def _finger_chains(arm, hand_pb):
    """Each hand child is a finger root; follow the outward child to the tip."""
    chains = []
    for root in hand_pb.children:
        chain, node = [root], root
        while node.children:
            node = max(node.children,
                       key=lambda c: (_wh(arm, c) - _wh(arm, hand_pb)).length)
            chain.append(node)
        chains.append(chain)
    return chains


def _tip_world(arm, tip_pb) -> Vector:
    dg = bpy.context.evaluated_depsgraph_get()
    ev = arm.evaluated_get(dg).pose.bones[tip_pb.name]
    return arm.matrix_world @ ev.tail


def pose_relaxed_hands(arm, arm_chains, curl_deg: float = RELAX_CURL_DEG) -> dict:
    """Curl fingers on each hand (bone-local, static — rides with the arm), and
    return {upperarm_name: palm_in_world | None}: the measured palm-facing
    direction in the REST world frame, sign resolved by the curl motion."""
    palm_in = {}
    for a in arm_chains:
        hand_name = a.get("hand")
        if not hand_name or hand_name not in arm.pose.bones:
            palm_in[a["upperarm"]] = None
            continue
        hand = arm.pose.bones[hand_name]
        chains = _finger_chains(arm, hand)
        # need at least a few multi-segment fingers to be a real hand
        if sum(1 for c in chains if len(c) >= 2) < 3:
            palm_in[a["upperarm"]] = None
            continue

        roots = [_wh(arm, c[0]) for c in chains]
        tips = [_wt(arm, c[-1]) for c in chains]
        mean_out = sum(((t - r) for t, r in zip(tips, roots)), Vector()).normalized()
        fore = a.get("forearm")
        arm_dir = ((_wh(arm, hand) - _wh(arm, arm.pose.bones[fore])).normalized()
                   if fore and fore in arm.pose.bones else Vector((0, 0, 1)))
        knuckle = mean_out.cross(arm_dir).normalized()   # across-the-knuckles axis

        # resolve flexion sign by the reach test: flexion shortens outward reach
        prox = chains[0][0]
        tip0 = chains[0][-1]

        def outward_reach(sign):
            prox.rotation_quaternion = Quaternion(
                _axis_in_bone(arm, prox, knuckle), math.radians(_PROBE_DEG) * sign)
            bpy.context.view_layer.update()
            reach = (_tip_world(arm, tip0) - _wh(arm, prox)).dot(mean_out)
            prox.rotation_quaternion = Quaternion()
            bpy.context.view_layer.update()
            return reach

        flex_sign = -1.0 if outward_reach(-1.0) < outward_reach(1.0) else 1.0

        # measure palm direction: fingertips travel toward the palm as they curl
        before = sum((_tip_world(arm, c[-1]) for c in chains), Vector()) / len(chains)
        for ch in chains:
            for pb in ch:
                pb.rotation_quaternion = Quaternion(
                    _axis_in_bone(arm, pb, knuckle), math.radians(curl_deg) * flex_sign)
        bpy.context.view_layer.update()
        after = sum((_tip_world(arm, c[-1]) for c in chains), Vector()) / len(chains)

        disp = after - before
        disp = disp - mean_out * disp.dot(mean_out)      # drop the "shortening" part
        palm_in[a["upperarm"]] = (list(disp.normalized()) if disp.length > 1e-6
                                  else None)
        # fingers stay curled (static); they ride with the arm through the walk
    return palm_in
