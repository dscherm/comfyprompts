import bpy, sys, math
from mathutils import Vector
a=sys.argv[sys.argv.index("--")+1:]
GLB,OUTB=a[0],a[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
new=[o for o in bpy.data.objects if o not in before]
meshes=[o for o in new if o.type=="MESH"]
arm=next(o for o in new if o.type=="ARMATURE")
arm.show_in_front=True
# normalize to ~1 + ground
def mesh_bbox():
    mn=Vector((1e9,)*3);mx=-mn
    for m in meshes:
        for c in m.bound_box:
            w=m.matrix_world@Vector(c)
            for k in range(3): mn[k]=min(mn[k],w[k]);mx[k]=max(mx[k],w[k])
    return mn,mx
mn,mx=mesh_bbox(); s=1.0/(max(mx-mn) or 1)
for r in [o for o in new if o.parent is None]: r.scale=(r.scale[0]*s,)*3
bpy.context.view_layer.update()
mn,mx=mesh_bbox(); ctr=(mn+mx)/2
for r in [o for o in new if o.parent is None]: r.location += Vector((-ctr.x,-ctr.y,-mn.z))
bpy.context.view_layer.update()
# classify legs by BONE z-range (self-consistent; matches deform test)
heads={pb.name:(arm.matrix_world@pb.bone.head_local) for pb in arm.pose.bones}
zs=[h.z for h in heads.values()]; zmin,zmax=min(zs),max(zs); thr=zmin+(zmax-zmin)*0.5
xs=[h.x for h in heads.values()]; ys=[h.y for h in heads.values()]
cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2
legs=[]
for pb in arm.pose.bones:
    h=heads[pb.name]
    if h.z<thr:
        # diagonal trot: (front-left & back-right) vs (front-right & back-left)
        diag=0.0 if ((h.x-cx)*(h.y-cy))>=0 else math.pi
        legs.append((pb,diag)); pb.rotation_mode='XYZ'
root=arm.pose.bones[0]; root.rotation_mode='XYZ'
F=24; amp=math.radians(26); sc.frame_start=1; sc.frame_end=F
for f in range(1,F+2):
    t=(f-1)/F
    for pb,ph in legs:
        pb.rotation_euler.x=amp*math.sin(2*math.pi*t+ph)
        pb.keyframe_insert('rotation_euler',frame=f)
    root.location.z=0.02*math.sin(4*math.pi*t); root.keyframe_insert('location',frame=f)
# cyclic loop on all fcurves
act=arm.animation_data.action
try:
    for fc in act.fcurves:
        m=fc.modifiers.new('CYCLES')
except Exception: pass
bpy.ops.mesh.primitive_plane_add(size=6); pm=bpy.data.materials.new("g");pm.use_nodes=True
pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.17,0.17,0.2,1)
bpy.context.active_object.data.materials.append(pm)
sun=bpy.data.lights.new("s","SUN");so=bpy.data.objects.new("s",sun);sc.collection.objects.link(so);so.rotation_euler=(0.9,0,0.6);sun.energy=3.5
cam=bpy.data.cameras.new("c");co=bpy.data.objects.new("c",cam);sc.collection.objects.link(co);co.location=(1.7,-2.3,1.1);co.rotation_euler=(1.16,0,0.63);sc.camera=co
sc.render.engine="BLENDER_EEVEE"; sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUTB)
print("ANIM_BLEND_SAVED",OUTB,"legbones",len(legs),"frames",F)
