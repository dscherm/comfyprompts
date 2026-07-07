"""Author clean quad cycles (idle/walk/run/attack) on a UniRig rig and export a
multi-clip animated GLB (via NLA). Identifies the 4 leg CHAINS (foot->lower->upper)
by quadrant, swings the upper leg fore/aft around the WORLD sideways axis (robust to
UniRig's arbitrary bone orientation), bends the knee to lift the foot in swing, and
bobs the body. CPU only.
    blender -b --python quad_anim_v2.py -- <rigged.glb> <out.glb> [render_montage.png]
"""
import bpy, sys, math
from mathutils import Vector, Quaternion, Matrix
a=sys.argv[sys.argv.index("--")+1:]
GLB,OUT=a[0],a[1]; MONT=a[2] if len(a)>2 else ""

bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
bpy.ops.import_scene.gltf(filepath=GLB)
arm=next(o for o in bpy.context.scene.objects if o.type=="ARMATURE")
meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]

def wh(pb): return arm.matrix_world @ pb.bone.head_local
H={pb:wh(pb) for pb in arm.pose.bones}
xs=[h.x for h in H.values()]; ys=[h.y for h in H.values()]; zs=[h.z for h in H.values()]
cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2; zmin,zmax=min(zs),max(zs)
# forward = longest horizontal axis; side = the other
ext_x=max(xs)-min(xs); ext_y=max(ys)-min(ys)
FWD=Vector((0,1,0)) if ext_y>=ext_x else Vector((1,0,0))
SIDE=Vector((1,0,0)) if ext_y>=ext_x else Vector((0,1,0))

# 4 feet = lowest bone per XY quadrant (within bottom 30% of z)
foot_thr=zmin+(zmax-zmin)*0.30
cand=[pb for pb in arm.pose.bones if H[pb].z<foot_thr]
quads={}
for pb in cand:
    q=(H[pb].x>=cx, (H[pb].dot(FWD))>= (cy if FWD.y else cx))
    if q not in quads or H[pb].z<H[quads[q]].z: quads[q]=pb
legs=[]
for q,foot in quads.items():
    lower=foot.parent; upper=lower.parent if lower else None
    if upper is None: continue
    fwdpos=H[upper].dot(FWD)
    is_front = fwdpos >= (cy if FWD.y else cx)
    side = H[upper].x>=cx
    legs.append({'foot':foot,'lower':lower,'upper':upper,'front':is_front,'left':side})
root=arm.pose.bones[0]
# spine bones: upper half, not legs
legset=set()
for L in legs: legset|={L['foot'],L['lower'],L['upper']}
spine=[pb for pb in arm.pose.bones if H[pb].z>=zmin+(zmax-zmin)*0.55 and pb not in legset]

def axis_in_bone(pb, world_vec):
    R=(arm.matrix_world @ pb.bone.matrix_local).to_3x3()
    return (R.inverted() @ world_vec).normalized()

for pb in arm.pose.bones: pb.rotation_mode='QUATERNION'
arm.animation_data_create()

def leg_phase(L):
    # diagonal trot: front-left & back-right together; front-right & back-left together
    return 0.0 if (L['front']==L['left']) else 0.5

def clear_pose():
    for pb in arm.pose.bones:
        pb.rotation_quaternion=Quaternion(); pb.location=(0,0,0)

def key_all(f):
    for pb in arm.pose.bones:
        pb.keyframe_insert('rotation_quaternion',frame=f)
    root.keyframe_insert('location',frame=f)

def make_clip(name, F, stride, knee, bob, spine_sway=0.0, oneshot=False):
    clear_pose()
    act=bpy.data.actions.new(name); arm.animation_data.action=act
    for f in range(1,F+2):
        t=(f-1)/F
        clear_pose()
        for L in legs:
            ph=leg_phase(L)
            th=2*math.pi*(t)+2*math.pi*ph if not oneshot else 0
            up=stride*math.sin(th)
            kn=knee*max(0.0,math.cos(th))
            L['upper'].rotation_quaternion=Quaternion(axis_in_bone(L['upper'],SIDE), up)
            if L['lower']:
                L['lower'].rotation_quaternion=Quaternion(axis_in_bone(L['lower'],SIDE), -kn)
        # body bob (2x) + sway
        root.location = (arm.matrix_world.inverted().to_3x3() @ (Vector((0,0,1))*bob*math.sin(4*math.pi*t)))
        for i,sp in enumerate(spine):
            sp.rotation_quaternion=Quaternion(axis_in_bone(sp,Vector((0,0,1))), spine_sway*math.sin(2*math.pi*t))
        key_all(f)
    arm.animation_data.action=None
    tr=arm.animation_data.nla_tracks.new(); tr.name=name
    st=tr.strips.new(name,1,act); 
    if not oneshot: st.use_animated_influence=False
    return act

def make_attack(name, F):
    clear_pose()
    act=bpy.data.actions.new(name); arm.animation_data.action=act
    for f in range(1,F+1):
        t=(f-1)/(F-1)
        clear_pose()
        # crouch (0-0.35) -> lunge up+fwd (0.35-0.6) -> settle
        crouch = math.sin(min(t,0.35)/0.35*math.pi/2)
        lunge = max(0.0, math.sin((t-0.35)/0.65*math.pi)) if t>0.35 else 0.0
        for L in legs:
            bend = 0.5*crouch - 0.3*lunge
            L['upper'].rotation_quaternion=Quaternion(axis_in_bone(L['upper'],SIDE), (0.5 if L['front'] else -0.4)*lunge)
            if L['lower']: L['lower'].rotation_quaternion=Quaternion(axis_in_bone(L['lower'],SIDE), -bend)
        # body: crouch down then thrust up+forward
        up = -0.06*crouch + 0.10*lunge
        root.location=(arm.matrix_world.inverted().to_3x3() @ (Vector((0,0,1))*up + FWD*0.12*lunge))
        for sp in spine:
            sp.rotation_quaternion=Quaternion(axis_in_bone(sp,SIDE), 0.25*lunge)
        key_all(f)
    arm.animation_data.action=None
    tr=arm.animation_data.nla_tracks.new(); tr.name=name
    tr.strips.new(name,1,act)
    return act

make_clip("idle", 48, math.radians(3), math.radians(4), 0.008, spine_sway=math.radians(2))
make_clip("walk", 24, math.radians(22), math.radians(30), 0.02, spine_sway=math.radians(3))
make_clip("run",  16, math.radians(34), math.radians(46), 0.045, spine_sway=math.radians(5))
make_attack("attack", 20)

# make loop clips cyclic
for tr in arm.animation_data.nla_tracks:
    if tr.name in ("idle","walk","run"):
        for st in tr.strips:
            st.repeat=1.0
sc.frame_start=1; sc.frame_end=24
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT,export_format="GLB",use_selection=True,export_animations=True,export_nla_strips=True)
print("QUADV2 legs=%d spine=%d fwd=%s -> %s" % (len(legs),len(spine),"Y" if FWD.y else "X", OUT.split("/")[-1]))

# optional walk montage render (frames across the walk cycle)
if MONT:
    # set to walk strip: solo it
    for tr in arm.animation_data.nla_tracks: tr.mute = (tr.name!="walk")
    sc.frame_end=24
    env=bpy.data.worlds.new("w");env.use_nodes=True;env.node_tree.nodes["Background"].inputs[0].default_value=(0.14,0.15,0.18,1);sc.world=env
    sd=bpy.data.lights.new("s","SUN");so=bpy.data.objects.new("s",sd);sc.collection.objects.link(so);so.rotation_euler=(0.9,0,0.5);sd.energy=3.2
    mn=Vector((1e9,)*3);mx=-mn
    for m in meshes:
        for c in m.bound_box:
            w=m.matrix_world@Vector(c)
            for k in range(3): mn[k]=min(mn[k],w[k]);mx[k]=max(mx[k],w[k])
    ctr=(mn+mx)/2; lg=max(mx-mn)
    cd=bpy.data.cameras.new("c");co=bpy.data.objects.new("c",cd);sc.collection.objects.link(co);sc.camera=co
    co.location=ctr+Vector((lg*0.6,-lg*2.4,lg*0.5)); co.rotation_euler=(ctr-co.location).to_track_quat('-Z','Y').to_euler()
    sc.render.engine="BLENDER_EEVEE";sc.render.resolution_x=300;sc.render.resolution_y=300
    import os
    for i,fr in enumerate([1,7,13,19]):
        sc.frame_set(fr); sc.render.filepath=MONT.replace(".png","_%d.png"%i); bpy.ops.render.render(write_still=True)
    print("MONTAGE_RENDERED")
