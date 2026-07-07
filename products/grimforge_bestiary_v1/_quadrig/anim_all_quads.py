"""Key a diagonal-trot walk onto each UniRig quad rig and export an animated GLB
(Blender glTF keeps the keyframed armature action). CPU only.
    blender -b --python anim_all_quads.py -- <quadrig_dir>
"""
import bpy, sys, math
from mathutils import Vector
QDIR=sys.argv[sys.argv.index("--")+1]
NAMES=["hell_hound","bone_hound","grave_boar","dire_rat"]
import os
for name in NAMES:
    p=os.path.join(QDIR,f"{name}_rigged.glb")
    if not os.path.exists(p): print("MISSING",name); continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=p)
    new=[o for o in bpy.data.objects if o not in before]
    meshes=[o for o in new if o.type=="MESH"]
    arm=next(o for o in new if o.type=="ARMATURE")
    # classify legs by bone z-range (lower half), diagonal phase by x*y quadrant
    heads={pb.name:(arm.matrix_world@pb.bone.head_local) for pb in arm.pose.bones}
    zs=[h.z for h in heads.values()]; zmin,zmax=min(zs),max(zs); thr=zmin+(zmax-zmin)*0.5
    xs=[h.x for h in heads.values()]; ys=[h.y for h in heads.values()]
    cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2
    legs=[]
    for pb in arm.pose.bones:
        h=heads[pb.name]
        if h.z<thr:
            diag=0.0 if ((h.x-cx)*(h.y-cy))>=0 else math.pi
            legs.append((pb,diag)); pb.rotation_mode='XYZ'
    root=arm.pose.bones[0]; root.rotation_mode='XYZ'
    F=24; amp=math.radians(26); sc.frame_start=1; sc.frame_end=F
    for f in range(1,F+2):
        t=(f-1)/F
        for pb,ph in legs:
            pb.rotation_euler.x=amp*math.sin(2*math.pi*t+ph); pb.keyframe_insert('rotation_euler',frame=f)
        root.location.z=0.02*math.sin(4*math.pi*t); root.keyframe_insert('location',frame=f)
    act=arm.animation_data.action
    act.name=f"{name}_walk"
    # export animated GLB (whole scene = just this rig)
    out=os.path.join(QDIR,f"{name}_walk.glb")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=out,export_format="GLB",use_selection=True,export_animations=True,export_frame_range=True)
    print(f"WALK_GLB {name} legs={len(legs)} -> {name}_walk.glb")
print("ALL_WALKS_DONE")
