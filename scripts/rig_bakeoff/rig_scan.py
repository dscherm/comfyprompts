"""Scan a rigged mesh and persist its MEASURED kinematic facts as <rig>.rigvec.json.

WHY
---
Animators kept ASSUMING conventions and getting them wrong. Two real bugs, one
session, both from assumed-not-measured facts (2026-07-17, exemplar walk):

  * knee sign copied from the QUADRUPED animator -> human knees bent backwards
    (quad hind legs fold the opposite way to human knees);
  * arms swung around the world side axis while the rest pose was a T-POSE, so
    the axis was PARALLEL to the arm -> it twisted instead of swinging.

Both are catchable by measurement. This scanner writes the facts down once per
rig so animation code references them instead of guessing.

WHAT IS MEASURED vs INFERRED (the honest split)
----------------------------------------------
  MEASURED   frame axes (forward from ankle->toe, averaged across feet so the
             toe-splay X cancels), per-bone rest directions, chain topology,
             degenerate-axis flags (rotation axis ~parallel to the bone).
  INFERRED   semantic roles, from topology + position (thigh = child of root
             that descends; upperarm = lateral chain whose parent is central).
  VERIFIED   hinge fold signs. NOT taken on faith from an anatomy prior: each
             sign is TESTED by posing the joint and measuring which way the end
             effector actually travelled along the measured forward axis. The
             prior only supplies the expected direction; geometry decides.

Rest-bend hinge derivation (cross(parent_dir, child_dir)) is used when the rest
pose actually bends the joint, and REJECTED as degenerate when it does not --
measured on the exemplar: elbow 24.2 deg (usable), knee 5.6 deg (noise).

Usage:
    blender --background --factory-startup --python rig_scan.py \\
        -- <rigged.glb|fbx> <out.rigvec.json> [humanoid|quadruped]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
SRC = argv[0]
OUT = Path(argv[1])
KIND = argv[2] if len(argv) > 2 else "humanoid"

DEGENERATE_DOT = 0.85      # |rest_dir . axis| above this => rotating about it is a twist
REST_BEND_MIN_CROSS = 0.15  # |cross(parent,child)| below this => rest bend is noise
PROBE_DEG = 45.0            # test bend used to measure fold direction

bpy.ops.wm.read_factory_settings(use_empty=True)
suffix = Path(SRC).suffix.lower()
if suffix == ".fbx":
    bpy.ops.import_scene.fbx(filepath=SRC)
else:
    bpy.ops.import_scene.gltf(filepath=SRC)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
arm.animation_data_clear()
meshes = [o for o in bpy.data.objects
          if o.type == "MESH"
          and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
for mesh in meshes:
    if mesh.animation_data:
        mesh.animation_data_clear()
    if mesh.data.shape_keys and mesh.data.shape_keys.animation_data:
        mesh.data.shape_keys.animation_data_clear()
bones = arm.pose.bones


def head(pb) -> Vector:
    return arm.matrix_world @ pb.bone.head_local


def tail(pb) -> Vector:
    return arm.matrix_world @ pb.bone.tail_local


def rest_dir(pb) -> Vector:
    v = tail(pb) - head(pb)
    return v.normalized() if v.length > 1e-9 else Vector((0, 0, 1))


def axis_in_bone(pb, world_vec: Vector) -> Vector:
    R = (arm.matrix_world @ pb.bone.matrix_local).to_3x3()
    return (R.inverted() @ world_vec).normalized()


def reset():
    for pb in bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion()
        pb.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()


H = {pb.name: head(pb) for pb in bones}
zs = [v.z for v in H.values()]
z_min, z_max = min(zs), max(zs)
height = z_max - z_min
xs = [v.x for v in H.values()]
cx = (min(xs) + max(xs)) / 2

root = next((pb for pb in bones if pb.parent is None), None)
if root is None:
    print("ERROR: no root bone", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------- leg chains
# Find the PELVIS as the first branch point whose subtrees reach the floor, then
# its floor-reaching children are the thighs. Two rejected alternatives, both
# measured to fail on real rigs:
#   * "lowest bone, trace up parents" -> finds the TOE, shifting the whole chain
#     by one (thigh:=calf, knee:=ankle);
#   * "thigh = child of root that descends" -> works on UniRig/Meshy (thighs hang
#     off the root) but finds ZERO legs on AccuRIG, whose chain is
#     root -> Hip -> Pelvis -> Thigh and whose Hip ASCENDS from the root.
FLOOR_BAND = z_min + height * 0.15


def reaches_floor(pb) -> bool:
    stack = [pb]
    while stack:
        n = stack.pop()
        if H[n.name].z <= FLOOR_BAND:
            return True
        stack.extend(n.children)
    return False


def first_child_chain(pb, depth: int):
    """Follow the single longest descending child chain for `depth` steps."""
    out = []
    node = pb
    for _ in range(depth):
        kids = [c for c in node.children if reaches_floor(c)] or list(node.children)
        if not kids:
            out.append(None)
            continue
        node = min(kids, key=lambda c: H[c.name].z)
        out.append(node)
    return out


node = root
thighs = []
while True:
    downs = [c for c in node.children if reaches_floor(c)]
    if len(downs) >= 2:
        thighs = downs
        break
    if len(downs) == 1:
        node = downs[0]
        continue
    break

legs = []
for thigh in thighs:
    calf, foot, toe = first_child_chain(thigh, 3)
    if not (calf and foot):
        continue
    legs.append({"thigh": thigh, "calf": calf, "foot": foot, "toe": toe,
                 "left": H[thigh.name].x >= cx})

# ---------------------------------------------------------------- arm chains
def subtree_max_lateral(pb) -> float:
    """Furthest |x - centre| anywhere in this bone's subtree."""
    best = 0.0
    stack = [pb]
    while stack:
        n = stack.pop()
        best = max(best, abs(H[n.name].x - cx))
        stack.extend(n.children)
    return best


def first_lateral_chain(pb, depth: int):
    """Follow the child whose subtree extends furthest out the limb, `depth` steps.
    Twist bones stop short of the hand/fingers, so they lose this comparison."""
    out = []
    node = pb
    for _ in range(depth):
        kids = list(node.children)
        if not kids:
            out.append(None)
            continue
        node = max(kids, key=subtree_max_lateral)
        out.append(node)
    return out


arms = []
for side_is_left in (True, False):
    side_bones = [pb for pb in bones
                  if (H[pb.name].x >= cx) == side_is_left
                  and H[pb.name].z > z_min + height * 0.50]
    if not side_bones:
        continue
    node = max(side_bones, key=lambda pb: abs(H[pb.name].x - cx))
    upperarm = None
    while node.parent is not None:
        if abs(H[node.parent.name].x - cx) < height * 0.06:
            upperarm = node
            break
        node = node.parent
    if upperarm:
        # Follow the child whose SUBTREE reaches furthest out the limb — never
        # children[0]. AccuRIG hangs UpperarmTwist01/02 as siblings of Forearm,
        # so children[0] walks the twist chain on whichever side ordering favours
        # it; that produced a 10deg vs 75deg rest-bend asymmetry between mirrored
        # elbows, which is anatomically impossible and betrayed the bug.
        forearm, hand = first_lateral_chain(upperarm, 2)
        arms.append({"upperarm": upperarm, "forearm": forearm, "hand": hand,
                     "left": side_is_left})

# ------------------------------------------------- MEASURED frame: forward
# ankle->toe per foot. The X components are equal-and-opposite (toes splay
# outward), so averaging cancels them and leaves the true facing axis.
forward_evidence = []
acc = Vector((0.0, 0.0, 0.0))
for leg in legs:
    if not leg["toe"]:
        continue
    v = H[leg["toe"].name] - H[leg["foot"].name]
    forward_evidence.append({"side": "L" if leg["left"] else "R",
                             "ankle_to_toe": [round(c, 3) for c in v]})
    acc += v
if acc.length < 1e-6:
    print("ERROR: no toe bones — cannot measure forward from the rig", file=sys.stderr)
    sys.exit(1)
acc.z = 0.0                       # toes also slope down; keep it horizontal
FORWARD = acc.normalized()
UP = Vector((0.0, 0.0, 1.0))
SIDE = FORWARD.cross(UP).normalized()
AXES = {"forward": FORWARD, "up": UP, "side": SIDE}

# ------------------------------------------------- VERIFIED hinge fold signs
# The prior supplies only the EXPECTED direction of travel; the sign is chosen
# by posing the joint and measuring where the end effector actually goes.
FOLD_RULES = {
    "humanoid": {
        "knee": {"expect_along_forward": -1,
                 "rule": "human knee folds the foot BEHIND (heel toward buttocks)"},
        "elbow": {"expect_along_forward": +1,
                  "rule": "human elbow folds the hand FORWARD"},
    },
    "quadruped": {
        "knee": {"expect_along_forward": +1,
                 "rule": "quadruped hock folds the foot FORWARD (opposite the human knee)"},
        "elbow": {"expect_along_forward": -1, "rule": "quadruped front knee folds back"},
    },
}


def measure_fold(hinge_bone, effector_bone, world_axis: Vector) -> dict:
    """Pose the hinge both ways about world_axis; report effector travel along FORWARD."""
    out = {}
    for sign in (+1.0, -1.0):
        reset()
        before = head(effector_bone).copy()
        hinge_bone.rotation_quaternion = Quaternion(
            axis_in_bone(hinge_bone, world_axis), math.radians(PROBE_DEG) * sign)
        bpy.context.view_layer.update()
        # posed head must be read through the evaluated depsgraph
        dg = bpy.context.evaluated_depsgraph_get()
        arm_eval = arm.evaluated_get(dg)
        after = arm.matrix_world @ arm_eval.pose.bones[effector_bone.name].head
        out[sign] = (after - before).dot(FORWARD)
    reset()
    return out


def resolve_axis(rb: dict, prior_axis_name: str) -> tuple[Vector, str, str]:
    """Prefer the rig's OWN measured hinge axis; fall back to the prior only when
    the rest pose is too straight to encode one (measured: knee 5.6deg = noise,
    elbow 24deg = usable). Measuring and then ignoring the measurement would
    defeat the purpose of this scanner."""
    if rb["usable"]:
        v = Vector(rb["rest_bend_axis"]).normalized()
        # name it by whichever frame axis it lies along (sign-insensitive)
        near = max(AXES.items(), key=lambda kv: abs(v.dot(kv[1])))
        return v, f"measured~{near[0]}", "rest_bend"
    return AXES[prior_axis_name], prior_axis_name, "prior+verified"


def rest_bend(a, b, c) -> dict:
    p = (head(b) - head(a)).normalized()
    ch = (head(c) - head(b)).normalized()
    x = p.cross(ch)
    ang = math.degrees(p.angle(ch)) if p.length and ch.length else 0.0
    usable = x.length >= REST_BEND_MIN_CROSS
    # NB: key is rest_bend_axis, NOT "axis" — these dicts get **spread into the
    # hinge record, and an "axis" key there would silently clobber the hinge's
    # own axis name with None whenever the rest bend is degenerate.
    return {"rest_bend_deg": round(ang, 2), "cross_len": round(x.length, 4),
            "usable": usable,
            "rest_bend_axis": [round(c_, 3) for c_ in x.normalized()] if usable else None}


hinges = {}
rules = FOLD_RULES.get(KIND, FOLD_RULES["humanoid"])

for leg in legs:
    side = "L" if leg["left"] else "R"
    rb = rest_bend(leg["thigh"], leg["calf"], leg["foot"])
    axis_vec, axis_name, axis_source = resolve_axis(rb, "side")
    travel = measure_fold(leg["calf"], leg["foot"], axis_vec)
    want = rules["knee"]["expect_along_forward"]
    chosen = max(travel, key=lambda s: travel[s] * want)
    hinges[f"knee.{side}"] = {
        "bone": leg["calf"].name,
        "axis": axis_name,
        "axis_vector": [round(c, 3) for c in axis_vec],
        "axis_source": axis_source,
        **rb,
        "fold_sign": chosen,
        "fold_rule": rules["knee"]["rule"],
        "verified": True,
        "evidence": {"foot_travel_along_forward": {str(k): round(v, 4)
                                                   for k, v in travel.items()},
                     "method": f"posed {PROBE_DEG} deg both ways; kept the sign whose "
                               f"effector travel matches the rule"},
    }

for a in arms:
    if not (a["forearm"] and a["hand"]):
        continue
    side = "L" if a["left"] else "R"
    rb = rest_bend(a["upperarm"], a["forearm"], a["hand"])
    axis_vec, axis_name, axis_source = resolve_axis(rb, "up")
    travel = measure_fold(a["forearm"], a["hand"], axis_vec)
    want = rules["elbow"]["expect_along_forward"]
    chosen = max(travel, key=lambda s: travel[s] * want)
    hinges[f"elbow.{side}"] = {
        "bone": a["forearm"].name,
        "axis": axis_name,
        "axis_vector": [round(c, 3) for c in axis_vec],
        "axis_source": axis_source,
        **rb,
        "fold_sign": chosen,
        "fold_rule": rules["elbow"]["rule"],
        "verified": True,
        "evidence": {"hand_travel_along_forward": {str(k): round(v, 4)
                                                   for k, v in travel.items()}},
    }

# ------------------------------------------------- per-bone facts
def bone_record(pb, role: str) -> dict:
    rd = rest_dir(pb)
    degenerate = [name for name, ax in AXES.items() if abs(rd.dot(ax)) >= DEGENERATE_DOT]
    rec = {"role": role,
           "rest_dir": [round(c, 3) for c in rd],
           "head": [round(c, 3) for c in head(pb)],
           "length": round(pb.bone.length, 4),
           "parent": pb.parent.name if pb.parent else None,
           "degenerate_axes": degenerate}
    if degenerate:
        rec["degenerate_note"] = (
            f"rest direction is ~parallel to {', '.join(degenerate)} — rotating about "
            f"{'that axis' if len(degenerate) == 1 else 'those axes'} TWISTS this bone "
            f"instead of swinging it; reorient first (e.g. lower a T-posed arm)")
    return rec


bone_facts = {}
for leg in legs:
    side = "L" if leg["left"] else "R"
    for role, pb in (("thigh", leg["thigh"]), ("calf", leg["calf"]),
                     ("foot", leg["foot"]), ("toe", leg["toe"])):
        if pb:
            bone_facts[pb.name] = bone_record(pb, f"{role}.{side}")
for a in arms:
    side = "L" if a["left"] else "R"
    for role, pb in (("upperarm", a["upperarm"]), ("forearm", a["forearm"]),
                     ("hand", a["hand"])):
        if pb:
            bone_facts[pb.name] = bone_record(pb, f"{role}.{side}")
bone_facts[root.name] = bone_record(root, "root")

# ------------------------------------------------- MEASURED neutral standing pose
# Motion recipes are authored against a NEUTRAL STANDING pose (legs vertical, arms
# hanging at the sides). Authored rest poses are not that — this mesh rests in a
# T-pose with ~10deg of leg splay, and applying gait curves straight onto that
# carried the splay/T-pose through every frame (arms winged out; legs swung wide).
#
# So the correction is measured HERE, once per rig, not hardcoded per recipe (the
# walk recipe had ARM_LOWER=75deg baked in — a guess, and wrong on Meshy, which
# needs ASYMMETRIC 79/77deg). Measured hierarchically top-down: each bone's
# correction is read in the posed state of its already-corrected parent, because
# rotating a thigh carries its calf.
#
# Depends on a correct UP. This scanner uses UP=(0,0,1), valid for Z-up rigs
# (glTF); it is NOT valid for FBX rigs that import with an axis swap. Recorded in
# neutral_pose.valid_for so a consumer can refuse rather than misapply.
NEUTRAL_TARGET = {"thigh": -UP, "calf": -UP, "upperarm": -UP, "forearm": -UP}


def posed_dir(name: str) -> Vector:
    dg = bpy.context.evaluated_depsgraph_get()
    ev = arm.evaluated_get(dg).pose.bones[name]
    return (arm.matrix_world.to_3x3() @ (ev.tail - ev.head)).normalized()


reset()
neutral = {}
_order = []
for leg in legs:
    _order += [("thigh", leg["thigh"]), ("calf", leg["calf"])]
for a in arms:
    _order += [("upperarm", a["upperarm"]), ("forearm", a["forearm"])]
for role, pb in _order:
    if pb is None:
        continue
    cur = posed_dir(pb.name)
    q_world = cur.rotation_difference(NEUTRAL_TARGET[role])
    axis_w, angle = q_world.to_axis_angle()
    pb.rotation_quaternion = Quaternion(axis_in_bone(pb, axis_w), angle)
    bpy.context.view_layer.update()
    neutral[pb.name] = {
        "role": bone_facts[pb.name]["role"],
        "world_axis": [round(c, 4) for c in axis_w],
        "angle_deg": round(math.degrees(angle), 2),
    }
reset()

# ------------------------------------------------- MEASURED palm orientation
# The palm plane is spanned by the arm axis and the finger-root spread, so its
# normal is cross(arm_dir, spread). Measurable ONLY when the rig has finger bones
# (UniRig gives them on clean meshes; Meshy's 24-bone skeleton does not). The
# normal's SIGN is arbitrary (depends which finger pair spans the spread), so
# palm-in vs back-of-hand-in is a 180deg ambiguity this cannot settle — a consumer
# resolves it by rendering. Null is an honest answer, not a default.
def palm_normal(hand_pb, arm_dir: Vector):
    fingers = list(hand_pb.children) if hand_pb else []
    if len(fingers) < 2:
        return None
    pts = [H[f.name] for f in fingers]
    _, i, j = max((( pts[a] - pts[b]).length, a, b)
                  for a in range(len(pts)) for b in range(len(pts)) if a != b)
    spread = pts[i] - pts[j]
    spread = spread - arm_dir * spread.dot(arm_dir)
    if spread.length < 1e-6:
        return None
    n = arm_dir.cross(spread.normalized())
    return n.normalized() if n.length > 1e-6 else None


palms = {}
for a in arms:
    side = "L" if a["left"] else "R"
    n = palm_normal(a["hand"], rest_dir(a["upperarm"])) if a["hand"] else None
    palms[f"palm.{side}"] = {
        "hand": a["hand"].name if a["hand"] else None,
        "palm_plane_normal": [round(c, 3) for c in n] if n else None,
        "finger_count": len(list(a["hand"].children)) if a["hand"] else 0,
        "note": ("plane measured (finger spread x arm axis); normal sign is "
                 "ambiguous, resolve by rendering" if n else
                 "UNAVAILABLE — no finger bones; do not assume a palm orientation"),
    }

manifest = {
    "rig": Path(SRC).name,
    "rig_kind": KIND,
    "scanner_version": 1,
    "bone_count": len(bones),
    "frame": {
        "forward": [round(c, 3) for c in FORWARD],
        "up": [round(c, 3) for c in UP],
        "side": [round(c, 3) for c in SIDE],
        "forward_source": "measured: mean(ankle->toe) over feet, horizontal-projected "
                          "(per-foot X cancels because toes splay symmetrically)",
        "forward_evidence": forward_evidence,
    },
    "root": root.name,
    "chains": {
        **{f"leg.{'L' if l['left'] else 'R'}": {
            k: (v.name if v else None) for k, v in l.items() if k != "left"}
           for l in legs},
        **{f"arm.{'L' if a['left'] else 'R'}": {
            k: (v.name if v else None) for k, v in a.items() if k != "left"}
           for a in arms},
    },
    "hinges": hinges,
    "palms": palms,
    "neutral_pose": {
        "note": "Per-bone corrections from AUTHORED rest -> neutral standing (legs "
                "vertical, arms at sides). Recipes MUST apply these before their own "
                "curves; compose world-space as R_motion . R_neutral.",
        "valid_for": "z-up rigs (UP=(0,0,1)); unreliable on axis-swapped FBX imports",
        "corrections": neutral,
    },
    "bones": bone_facts,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(manifest, indent=1) + "\n")
print(f"SCANNED {Path(SRC).name}: {len(legs)} legs, {len(arms)} arms, "
      f"{len(hinges)} hinges -> {OUT}")
print(f"  forward (measured) = {[round(c,3) for c in FORWARD]}")
for hid, h in hinges.items():
    print(f"  {hid:<9} axis={h['axis']:<8} sign={h['fold_sign']:+.0f} "
          f"src={h['axis_source']:<16} rest_bend={h['rest_bend_deg']}deg "
          f"{'(usable)' if h['usable'] else '(degenerate)'}")
for bn, bf in bone_facts.items():
    if bf["degenerate_axes"]:
        print(f"  DEGENERATE {bn} ({bf['role']}): axes {bf['degenerate_axes']}")
