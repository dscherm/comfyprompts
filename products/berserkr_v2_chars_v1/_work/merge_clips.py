"""Merge several single-clip rigged GLBs into ONE multi-clip Godot-ready GLB.

Meshy returns each animation as its own full-mesh GLB (rigged mesh + one clip).
This imports the FIRST as the base (keeps its textured mesh + armature), appends
each other GLB's action onto that same armature, renames every action, and
exports one GLB with all actions as separate glTF clips.

Usage:
  blender --background --factory-startup --python merge_clips.py \
    -- <out.glb> idle=<idle.glb> walk=<walk.glb> run=<run.glb> [attack=<attack.glb>]
"""

from __future__ import annotations

import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
# optional --albedo=<png> swaps the base mesh's colour texture (e.g. a Meshy
# retexture) onto the rigged/animated mesh before export (same UV assumed).
ALBEDO = ""
rest = []
for a in argv:
    if a.startswith("--albedo="):
        ALBEDO = a.split("=", 1)[1]
    else:
        rest.append(a)
OUT = rest[0]
specs = [(s.split("=", 1)[0], s.split("=", 1)[1]) for s in rest[1:]]

bpy.ops.wm.read_factory_settings(use_empty=True)

# --- base: first clip GLB keeps the mesh + armature ------------------------
base_name, base_path = specs[0]
bpy.ops.import_scene.gltf(filepath=base_path)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if arm.animation_data and arm.animation_data.action:
    arm.animation_data.action.name = base_name
    arm.animation_data.action.use_fake_user = True

keep = {arm, *arm.children_recursive}
for o in bpy.data.objects:
    if o.type == "MESH" and o.find_armature() == arm:
        keep.add(o)

# --- append each other clip's action, then drop its duplicate mesh/armature -
for name, path in specs[1:]:
    before = set(bpy.data.actions.keys())
    bpy.ops.import_scene.gltf(filepath=path)
    new_action = next((bpy.data.actions[n] for n in bpy.data.actions.keys()
                       if n not in before), None)
    if new_action:
        new_action.name = name
        new_action.use_fake_user = True
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)

# --- optional: swap the base-colour texture (retexture) ---------------------
if ALBEDO:
    img = bpy.data.images.load(ALBEDO)
    swapped = 0
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        for slot in o.material_slots:
            mat = slot.material
            if mat and mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == "TEX_IMAGE":
                        node.image = img
                        swapped += 1
    print("ALBEDO swapped on %d texture node(s): %s" % (swapped, ALBEDO))

# --- export every action as its own clip -----------------------------------
for o in bpy.data.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(
    filepath=OUT, export_format="GLB", use_selection=True,
    export_animation_mode="ACTIONS", export_animations=True,
    export_skins=True, export_morph=False,
)
print("MERGED %s  actions=%s" % (OUT, sorted(bpy.data.actions.keys())))
