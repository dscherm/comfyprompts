"""rename_unirig_bones — wire a UniRig rig into the mocap-retarget naming.

UniRig outputs generic `bone_XX` names; the animate-ralph retarget maps
(e.g. retarget_maps/mixamo_to_unirig.json) target standard role names
(hips, spine, chest, neck, head, shoulder/upperarm/lowerarm/hand .l/.r,
upperleg/lowerleg/foot .l/.r). This script auto-detects bone roles by
topology/position and renames bones + vertex groups to those role names,
producing a retarget-ready rig.

The detection logic is lifted verbatim from
autorig-ralph/scripts/apply_driving_pose.py (proven), so this stays the
single source of truth for UniRig->role naming.

Usage (headless; blender-mcp not required):
    blender --background --python rename_unirig_bones.py -- input.fbx output.glb
"""
import bpy, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) < 2:
    print("Usage: blender --background --python rename_unirig_bones.py -- input.fbx output.glb")
    sys.exit(1)
INPUT, OUTPUT = argv[0], argv[1]


def auto_detect_and_rename(armature):
    """Auto-detect bone roles and rename to standard role names (+ vertex groups)."""
    bones = armature.data.bones
    roles = {}
    root = [b for b in bones if b.parent is None]
    if not root:
        return {}
    roles["root"] = root[0].name

    # spine chain: keep climbing to the highest child in Z
    spine_chain = [root[0]]
    current = root[0]
    while True:
        up = sorted(
            [c for c in current.children
             if (armature.matrix_world @ c.head_local).z >
                (armature.matrix_world @ current.head_local).z],
            key=lambda c: (armature.matrix_world @ c.head_local).z, reverse=True)
        if not up:
            break
        spine_chain.append(up[0]); current = up[0]
    spine_names = set(b.name for b in spine_chain)

    # legs: children of low spine that descend in Z — collect chains first, then
    # assign sides FACING-AWARE. The old rule (side = "R" if x > 0) assumed the
    # character binds facing +Y; every TRELLIS/UniRig rig here binds facing -Y,
    # which mirrored every .l/.r label anatomically (crossed limbs downstream).
    leg_chains = []
    for sp in spine_chain[:3]:
        for child in sp.children:
            if child.name in spine_names:
                continue
            chain = [child]; cur = child
            while True:
                down = [c for c in cur.children
                        if (armature.matrix_world @ c.head_local).z <
                           (armature.matrix_world @ cur.head_local).z - 0.05]
                if down:
                    chain.append(down[0]); cur = down[0]
                else:
                    break
            if len(chain) >= 3:
                leg_chains.append(chain)

    # bind facing from the leg-chain END bones (feet): their tails point toe-ward
    # on UniRig/glTF rigs, which disambiguates front/back. left = up x forward.
    fwd = Vector((0.0, 0.0, 0.0))
    for chain in leg_chains:
        end = chain[-1]
        v = (armature.matrix_world @ end.tail_local) - (armature.matrix_world @ end.head_local)
        v.z = 0.0
        if v.length > 1e-9:
            fwd += v.normalized()
    if fwd.length > 1e-9:
        fwd.normalize()
    else:
        fwd = Vector((0.0, -1.0, 0.0))  # every TRELLIS/UniRig rig in this shop binds -Y
        print("WARN facing undetectable from feet; assuming -Y bind facing")
    left_v = Vector((0.0, 0.0, 1.0)).cross(fwd)
    root_head = armature.matrix_world @ root[0].head_local
    print(f"FACING fwd=({fwd.x:.2f},{fwd.y:.2f},{fwd.z:.2f}) "
          f"left=({left_v.x:.2f},{left_v.y:.2f},{left_v.z:.2f})")

    def side_of(bone, ref=None):
        off = (armature.matrix_world @ bone.head_local) - (ref if ref is not None else root_head)
        return "L" if off.dot(left_v) > 0 else "R"

    def chain_side(chain):
        # judge by the chain's MOST-LATERAL bone: chain roots (hip connectors)
        # sit on the centerline where the sign is noise.
        best = max(chain, key=lambda b: abs(
            ((armature.matrix_world @ b.head_local) - root_head).dot(left_v)))
        return side_of(best)

    for chain in leg_chains:
        side = chain_side(chain)
        if f"hip_{side}" not in roles:
            for i, label in enumerate(["hip", "upperleg", "lowerleg", "foot"]):
                if i < len(chain):
                    roles[f"{label}_{side}"] = chain[i].name

    if len(spine_chain) >= 2: roles["spine"] = spine_chain[1].name
    if len(spine_chain) >= 3: roles["chest"] = spine_chain[2].name

    # head + arms from the first branching upper-spine bone
    for sp_bone in reversed(spine_chain[2:]):
        if len(sp_bone.children) >= 2:
            for child in sp_bone.children:
                if child.name in spine_names:
                    continue
                ch = armature.matrix_world @ child.head_local
                sp_h = armature.matrix_world @ sp_bone.head_local
                if ch.z > sp_h.z + 0.02 and abs(ch.x) < 0.1:
                    if "neck" not in roles:
                        roles["neck"] = child.name
                        for gc in child.children:
                            if (armature.matrix_world @ gc.head_local).z > ch.z:
                                roles["head"] = gc.name
                elif abs(ch.x - sp_h.x) > 0.02:
                    # facing-aware, relative to the branching spine bone (shoulder
                    # heads sit close to the centerline; root-relative is noisy)
                    side = side_of(child, ref=sp_h)
                    if f"shoulder_{side}" not in roles:
                        roles[f"shoulder_{side}"] = child.name
                        arm_chain = []; cur = child
                        for _ in range(5):
                            if cur.children:
                                best = max(cur.children, key=lambda c: len(c.children))
                                arm_chain.append(best); cur = best
                            else:
                                break
                        if len(arm_chain) >= 1: roles[f"upperarm_{side}"] = arm_chain[0].name
                        if len(arm_chain) >= 2: roles[f"lowerarm_{side}"] = arm_chain[1].name
                        if len(arm_chain) >= 3: roles[f"hand_{side}"] = arm_chain[2].name
            break

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    rename_map = {"root": "hips", "spine": "spine", "chest": "chest",
                  "neck": "neck", "head": "head"}
    for sl, sx in [("R", ".r"), ("L", ".l")]:
        rename_map[f"hip_{sl}"] = f"hip_connector{sx}"
        for part in ("upperleg", "lowerleg", "foot", "shoulder", "upperarm", "lowerarm", "hand"):
            rename_map[f"{part}_{sl}"] = f"{part}{sx}"

    # TWO-PHASE rename so the script is safely RE-RUNNABLE on already-renamed
    # rigs (e.g. re-labeling pre-2026-07 mirrored .l/.r rigs): renaming directly
    # collides with existing role names and Blender silently .001-suffixes them.
    # Phase 1 parks every role bone on a unique temp name; phase 2 assigns the
    # final names; squatters (non-role bones already holding a target name) are
    # shunted aside. Bone renames auto-sync matching vertex groups in Blender,
    # so the vg pass below is a no-op safety net for detached meshes.
    renamed = {}
    plan = []
    planned_bones = set()
    for role, old in roles.items():
        new = rename_map.get(role)
        if new and old in armature.data.edit_bones and old not in planned_bones:
            plan.append((role, old, new))
            planned_bones.add(old)   # a bone can back only one role (first wins)
    for i, (role, old, new) in enumerate(plan):
        armature.data.edit_bones[old].name = f"TMP_ROLE_{i}"
    for i, (role, old, new) in enumerate(plan):
        squatter = armature.data.edit_bones.get(new)
        if squatter is not None:
            squatter.name = new + ".unassigned"
        armature.data.edit_bones[f"TMP_ROLE_{i}"].name = new
        renamed[role] = (old, new)
    bpy.ops.object.mode_set(mode='OBJECT')

    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature:
            for role, (old, new) in renamed.items():
                vg = obj.vertex_groups.get(old)
                if vg:
                    vg.name = new
    return renamed


def bind_left_axis(armature):
    """Character-left axis from bind geometry: forward = averaged foot-bone
    direction (toe-ward tails on UniRig/glTF rigs), left = up x forward.
    Falls back to -Y facing (this shop's TRELLIS/UniRig bind convention)."""
    mw = armature.matrix_world
    fwd = Vector((0.0, 0.0, 0.0))
    for n in ("foot.l", "foot.r"):
        b = armature.data.bones.get(n)
        if b:
            v = (mw @ b.tail_local) - (mw @ b.head_local)
            v.z = 0.0
            if v.length > 1e-9:
                fwd += v.normalized()
    if fwd.length < 1e-9:
        fwd = Vector((0.0, -1.0, 0.0))
    return Vector((0.0, 0.0, 1.0)).cross(fwd.normalized())


def detect_arms_by_position(armature):
    """Fallback: the topology heuristic above misses arms on some UniRig rigs.
    Arms are unambiguous by position — bones far out laterally at upper-body
    height. Sides are FACING-AWARE (lateral = offset along the character-left
    axis), not raw +/-X. Walk each side's chain outward and map shoulder/
    upperarm/lowerarm/hand. Renames bones + vertex groups in place."""
    mw = armature.matrix_world
    left_v = bind_left_axis(armature)
    root_b = next((b for b in armature.data.bones if b.parent is None), None)
    origin = (mw @ root_b.head_local) if root_b else Vector((0.0, 0.0, 0.0))

    def lat(b):
        return ((mw @ b.head_local) - origin).dot(left_v)

    heads = {b.name: (mw @ b.head_local) for b in armature.data.bones}
    zmax = max(h.z for h in heads.values())
    latmax = max(abs(lat(b)) for b in armature.data.bones) or 1.0
    renamed = {}
    edits = {}  # old -> new
    for sx, sign in [(".l", 1), (".r", -1)]:
        cands = [b for b in armature.data.bones
                 if lat(b) * sign > 0.15 * latmax
                 and (mw @ b.head_local).z > 0.45 * zmax]
        if len(cands) < 2:
            continue
        root = min(cands, key=lambda b: abs(lat(b)))  # innermost = shoulder
        chain = [root]; cur = root
        while True:
            nxt = [c for c in cur.children
                   if abs(lat(c)) > abs(lat(cur)) + 0.01]
            if not nxt:
                break
            cur = max(nxt, key=lambda c: abs(lat(c))); chain.append(cur)
        if len(chain) < 2:
            continue
        picks = {"shoulder": chain[0], "upperarm": chain[1] if len(chain) > 1 else chain[0],
                 "lowerarm": chain[max(2, len(chain) // 2)] if len(chain) > 2 else chain[-1],
                 "hand": chain[-1]}
        for part, b in picks.items():
            edits[b.name] = f"{part}{sx}"; renamed[f"{part}_{sx}"] = (b.name, f"{part}{sx}")
    if edits:
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        # TWO-PHASE (see auto_detect_and_rename): on already-labeled rigs the
        # targets collide with existing names and Blender .001-suffixes them.
        plan = [(old, new) for old, new in edits.items()
                if old in armature.data.edit_bones]
        for i, (old, new) in enumerate(plan):
            armature.data.edit_bones[old].name = f"TMP_ARM_{i}"
        for i, (old, new) in enumerate(plan):
            squatter = armature.data.edit_bones.get(new)
            if squatter is not None:
                squatter.name = new + ".unassigned"
            armature.data.edit_bones[f"TMP_ARM_{i}"].name = new
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.parent == armature:
                for old, new in edits.items():
                    vg = obj.vertex_groups.get(old)
                    if vg:
                        vg.name = new
    return renamed


def main():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    if INPUT.lower().endswith(".glb") or INPUT.lower().endswith(".gltf"):
        bpy.ops.import_scene.gltf(filepath=INPUT)
    else:
        bpy.ops.import_scene.fbx(filepath=INPUT)
    arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not arm:
        print("RENAME_FAIL no armature"); sys.exit(1)
    renamed = auto_detect_and_rename(arm)
    # arm fallback if the topology heuristic missed them
    if not any(r.startswith("upperarm") for r in renamed):
        renamed.update(detect_arms_by_position(arm))
    # head fallback: highest bone above 'neck' that isn't already a named role
    if "head" not in {nn for _, (_, nn) in renamed.items()} and "neck" in arm.data.bones:
        mw = arm.matrix_world
        named = {nn for _, (_, nn) in renamed.items()}
        neck_z = (mw @ arm.data.bones["neck"].head_local).z
        above = [b for b in arm.data.bones
                 if b.name not in named and (mw @ b.head_local).z > neck_z]
        if above:
            top = max(above, key=lambda b: (mw @ b.head_local).z)
            old = top.name
            bpy.context.view_layer.objects.active = arm
            bpy.ops.object.mode_set(mode='EDIT')
            arm.data.edit_bones[old].name = "head"
            bpy.ops.object.mode_set(mode='OBJECT')
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.parent == arm:
                    vg = obj.vertex_groups.get(old)
                    if vg:
                        vg.name = "head"
            renamed["head"] = (old, "head")
    final = sorted(b.name for b in arm.data.bones)
    # coverage vs the role names the retarget map targets
    map_targets = {"hips", "spine", "chest", "neck", "head",
                   "shoulder.l", "shoulder.r", "upperarm.l", "upperarm.r",
                   "lowerarm.l", "lowerarm.r", "hand.l", "hand.r",
                   "upperleg.l", "upperleg.r", "lowerleg.l", "lowerleg.r",
                   "foot.l", "foot.r"}
    got = map_targets & set(final)
    missing = map_targets - set(final)
    for o in bpy.data.objects:
        o.select_set(o.type in ("ARMATURE", "MESH"))
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(filepath=OUTPUT, use_selection=True, export_format="GLB")
    print(f"RENAMED {len(renamed)} bones")
    print(f"MAP_COVERAGE {len(got)}/{len(map_targets)} got; MISSING={sorted(missing)}")
    print(f"FINAL_BONES {final}")
    print(f"EXPORTED {OUTPUT}")


main()
