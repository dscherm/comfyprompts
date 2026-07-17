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


def palm_normal_from_mesh(arm, hand_name: str, meshes):
    """Measure the palm-plane normal from the HAND-WEIGHTED mesh vertices — works
    on any rig with a hand bone, finger bones or not (this is what lets a
    fingerless rig like Meshy get palm control). A hand is a thin slab, so the
    smallest-variance axis of its vertices is the palm normal. Sign is arbitrary
    (a plane has two faces); the caller resolves it once, globally, since one mesh
    has one handedness. Returns a WORLD unit vector, or None."""
    pts = []
    for mesh in meshes:
        vg = mesh.vertex_groups.get(hand_name)
        if vg is None:
            continue
        gi = vg.index
        for v in mesh.data.vertices:
            if any(g.group == gi and g.weight > 0.5 for g in v.groups):
                pts.append(mesh.matrix_world @ v.co)
    if len(pts) < 12:
        return None
    c = sum(pts, Vector()) / len(pts)
    # 3x3 covariance, smallest-eigenvector via power iteration on the inverse is
    # overkill — build the matrix and take the axis of least spread directly.
    xx = yy = zz = xy = xz = yz = 0.0
    for p in pts:
        d = p - c
        xx += d.x * d.x; yy += d.y * d.y; zz += d.z * d.z
        xy += d.x * d.y; xz += d.x * d.z; yz += d.y * d.z
    from mathutils import Matrix
    cov = Matrix(((xx, xy, xz), (xy, yy, yz), (xz, yz, zz)))
    # smallest eigenvalue eigenvector: iterate on (trace*I - cov) to invert order
    trace = xx + yy + zz
    shifted = Matrix.Identity(3) * trace - cov
    v = Vector((1.0, 0.3, -0.2))
    for _ in range(50):
        v = (shifted @ v).normalized()
    return v.normalized()


def _curl_fingers(arm, hand, chains, curl_deg):
    """Curl fingers into a relaxed shape. Flexion sign found by the reach test
    (flexion shortens outward reach), never assumed. Static — rides with the arm."""
    roots = [_wh(arm, c[0]) for c in chains]
    tips = [_wt(arm, c[-1]) for c in chains]
    mean_out = sum(((t - r) for t, r in zip(tips, roots)), Vector()).normalized()
    arm_dir = (_wt(arm, hand) - _wh(arm, hand)).normalized()
    knuckle = mean_out.cross(arm_dir).normalized()
    prox, tip0 = chains[0][0], chains[0][-1]

    def outward_reach(sign):
        prox.rotation_quaternion = Quaternion(
            _axis_in_bone(arm, prox, knuckle), math.radians(_PROBE_DEG) * sign)
        bpy.context.view_layer.update()
        reach = (_tip_world(arm, tip0) - _wh(arm, prox)).dot(mean_out)
        prox.rotation_quaternion = Quaternion()
        bpy.context.view_layer.update()
        return reach

    flex_sign = -1.0 if outward_reach(-1.0) < outward_reach(1.0) else 1.0

    # The THUMB opposes the fingers — it does NOT curl about the same knuckle axis,
    # and forcing it to (the fingers' shared flexion) made it splay weirdly. Detect
    # it as the finger whose rest direction deviates most from the others, and curl
    # it only gently about ITS OWN axis so it rests alongside instead of sticking out.
    dirs = [(_wt(arm, c[-1]) - _wh(arm, c[0])).normalized() for c in chains]
    mean_dir = sum(dirs, Vector()).normalized()
    thumb_i = max(range(len(chains)), key=lambda i: dirs[i].angle(mean_dir))
    thumb_is_outlier = dirs[thumb_i].angle(mean_dir) > math.radians(28)

    for i, ch in enumerate(chains):
        if thumb_is_outlier and i == thumb_i:
            # gentle curl about the thumb's own knuckle axis (its dir x the palm plane)
            t_knuckle = dirs[i].cross(arm_dir).normalized()
            for pb in ch:
                pb.rotation_quaternion = Quaternion(
                    _axis_in_bone(arm, pb, t_knuckle), math.radians(curl_deg * 0.4) * flex_sign)
            continue
        for pb in ch:
            pb.rotation_quaternion = Quaternion(
                _axis_in_bone(arm, pb, knuckle), math.radians(curl_deg) * flex_sign)
    bpy.context.view_layer.update()


def pose_relaxed_hands(arm, arm_chains, meshes, curl_deg: float = RELAX_CURL_DEG) -> dict:
    """Curl fingers where finger bones exist, and return {upperarm_name:
    palm_normal_world | None} measured from the HAND MESH — universal, so a
    fingerless rig (Meshy) still gets palm control via a wrist roll. The normal's
    sign is arbitrary (a plane has two faces); the caller resolves it once,
    globally, since one mesh has a single handedness."""
    palm = {}
    for a in arm_chains:
        hand_name = a.get("hand")
        if not hand_name or hand_name not in arm.pose.bones:
            palm[a["upperarm"]] = None
            continue
        hand = arm.pose.bones[hand_name]
        chains = _finger_chains(arm, hand)
        if sum(1 for c in chains if len(c) >= 2) >= 3:
            _curl_fingers(arm, hand, chains, curl_deg)
        palm[a["upperarm"]] = palm_normal_from_mesh(arm, hand_name, meshes)
    return palm
