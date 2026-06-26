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

    # legs: children of low spine that descend in Z
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
                x = (armature.matrix_world @ child.head_local).x
                side = "R" if x > 0 else "L"
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
                    side = "R" if ch.x > sp_h.x else "L"
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

    renamed = {}
    for role, old in roles.items():
        new = rename_map.get(role)
        if new and old in armature.data.edit_bones:
            armature.data.edit_bones[old].name = new
            renamed[role] = (old, new)
    bpy.ops.object.mode_set(mode='OBJECT')

    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature:
            for role, (old, new) in renamed.items():
                vg = obj.vertex_groups.get(old)
                if vg:
                    vg.name = new
    return renamed


def detect_arms_by_position(armature):
    """Fallback: the topology heuristic above misses arms on some UniRig rigs.
    Arms are unambiguous by position — bones out to the side (large |x|) at
    upper-body height. Walk each side's chain outward and map shoulder/upperarm/
    lowerarm/hand. Renames bones + vertex groups in place; returns {role:(old,new)}."""
    mw = armature.matrix_world
    heads = {b.name: (mw @ b.head_local) for b in armature.data.bones}
    zmax = max(h.z for h in heads.values())
    xmax = max(abs(h.x) for h in heads.values()) or 1.0
    renamed = {}
    edits = {}  # old -> new
    for sx, sign in [(".r", 1), (".l", -1)]:
        cands = [b for b in armature.data.bones
                 if (mw @ b.head_local).x * sign > 0.15 * xmax
                 and (mw @ b.head_local).z > 0.45 * zmax]
        if len(cands) < 2:
            continue
        root = min(cands, key=lambda b: abs((mw @ b.head_local).x))  # innermost = shoulder
        chain = [root]; cur = root
        while True:
            nxt = [c for c in cur.children
                   if abs((mw @ c.head_local).x) > abs((mw @ cur.head_local).x) + 0.01]
            if not nxt:
                break
            cur = max(nxt, key=lambda c: abs((mw @ c.head_local).x)); chain.append(cur)
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
        for old, new in edits.items():
            if old in armature.data.edit_bones:
                armature.data.edit_bones[old].name = new
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
