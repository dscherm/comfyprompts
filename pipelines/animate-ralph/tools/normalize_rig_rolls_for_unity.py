"""
normalize_rig_rolls_for_unity.py — rig-finalization for Unity Humanoid retarget.

Makes each limb's forearm/hand (and forearm-twist) bone ROLL consistent with the
upperarm so Unity's muscle-space retarget hinges the elbow in a clean plane.
SAFE: edit-mode roll change only — no re-pose, no re-bake. At rest, pose==rest so
deformation is identity; the mesh, skin weights, and leg pose are untouched.

  Why roll-only (not "Apply Pose as Rest" to force a T-pose): re-posing + baking the
  armature modifier desyncs the skinned mesh's bind matrices from the new rest, and
  Unity collapses the character (arms-up / legs-merged). Roll edits avoid that
  entirely. See lessons/unity-humanoid-bone-roll-normalize.md.

Run HEADLESS (the blender-mcp socket fails FBX import on Blender 5.0):
  blender --background --python normalize_rig_rolls_for_unity.py -- <in.fbx> <out.fbx>

After re-export, REBUILD the Unity avatar fresh (Generic→reimport→Humanoid/
CreateFromThisModel→reimport) or it validates the old skeleton (isHuman=False).

NOTE: bone names target the CC_Base / AccuRIG skeleton. The foot flap is a SEPARATE
Unity avatar muscle-config issue and is NOT addressed here.
"""
import bpy
import sys
import math
import os

SIDES = ("L", "R")
# Chain bones whose roll is forced to match the upperarm (per side).
CHAIN = ("Forearm", "Hand", "ForearmTwist01", "ForearmTwist02")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) < 2:
        raise SystemExit("usage: -- <in.fbx> <out.fbx>")
    src, out = argv[0], argv[1]

    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.fbx(filepath=src)
    new = [o for o in bpy.data.objects if o.name not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    mesh = next(o for o in new if o.type == "MESH")

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones

    def deg(name):
        b = eb.get(name)
        return round(math.degrees(b.roll), 1) if b else None

    parts = ("Upperarm", "Forearm", "Hand")
    print("[roll] BEFORE:", {p: tuple(deg("CC_Base_%s_%s" % (s, p)) for s in SIDES) for p in parts})

    for side in SIDES:
        ua = eb.get("CC_Base_%s_Upperarm" % side)
        if not ua:
            continue
        for part in CHAIN:
            b = eb.get("CC_Base_%s_%s" % (side, part))
            if b:
                b.roll = ua.roll

    print("[roll] AFTER :", {p: tuple(deg("CC_Base_%s_%s" % (s, p)) for s in SIDES) for p in parts})

    bpy.ops.object.mode_set(mode="OBJECT")
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    arm.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(
        filepath=out, use_selection=True, object_types={"ARMATURE", "MESH"},
        add_leaf_bones=False, bake_anim=False, mesh_smooth_type="FACE",
    )
    print("[roll] EXPORTED %s (%.2f MB)" % (out, os.path.getsize(out) / 1e6))


if __name__ == "__main__":
    main()
