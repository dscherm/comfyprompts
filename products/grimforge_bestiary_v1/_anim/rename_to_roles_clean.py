import bpy, sys
RENAME = {
 "CC_Base_Hip":"hips","CC_Base_Waist":"spine","CC_Base_Spine01":"chest",
 "CC_Base_NeckTwist01":"neck","CC_Base_Head":"head",
 "CC_Base_L_Clavicle":"shoulder.l","CC_Base_L_Upperarm":"upperarm.l","CC_Base_L_Forearm":"lowerarm.l","CC_Base_L_Hand":"hand.l",
 "CC_Base_R_Clavicle":"shoulder.r","CC_Base_R_Upperarm":"upperarm.r","CC_Base_R_Forearm":"lowerarm.r","CC_Base_R_Hand":"hand.r",
 "CC_Base_L_Thigh":"upperleg.l","CC_Base_L_Calf":"lowerleg.l","CC_Base_L_Foot":"foot.l",
 "CC_Base_R_Thigh":"upperleg.r","CC_Base_R_Calf":"lowerleg.r","CC_Base_R_Foot":"foot.r",
}
a = sys.argv[sys.argv.index("--")+1:]
INP, OUT = a[0], a[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=INP)
arm = next(o for o in bpy.context.scene.objects if o.type=="ARMATURE")
meshes = [o for o in bpy.context.scene.objects if o.type=="MESH"]
# NeckTwist01 must be renamed to neck; but "NeckTwist" contains "Twist" -> exclude from delete
for cc,role in RENAME.items():
    b = arm.data.bones.get(cc)
    if b: b.name = role
    for m in meshes:
        vg = m.vertex_groups.get(cc)
        if vg: vg.name = role
# delete twist/share sibling bones (edit mode) so each role bone's only joint-child is the next role
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
todel = [b.name for b in arm.data.edit_bones if ("Twist" in b.name or "ShareBone" in b.name)]
for n in todel:
    eb = arm.data.edit_bones.get(n)
    if eb: arm.data.edit_bones.remove(eb)
bpy.ops.object.mode_set(mode="OBJECT")
print("DELETED_SIBLINGS", len(todel))
present = [role for role in RENAME.values() if arm.data.bones.get(role)]
print("ROLES_PRESENT", len(present))
bpy.ops.object.select_all(action="DESELECT"); arm.select_set(True)
for m in meshes: m.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True)
print("ROLE_RIG_CLEAN_OK", OUT)
