"""Rework: solid connected gate (no gaps/floaters) + stone-block walls (texture).
blender -b --python improved3.py"""
import bpy, bmesh, math, mathutils, os, random
D="C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/25899eda-2041-4e64-a0a8-0c83c9100526/scratchpad"
GLB=f"{D}/kit_improved_glb"; os.makedirs(GLB,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
def Hx(h): return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
PAL={"stone":Hx("6f756a"),"stone_dk":Hx("4c5249"),"stone_lt":Hx("868c80"),"stone_2":Hx("5f655c"),
 "mortar":Hx("3c4039"),"iron":Hx("3e424a"),"iron_dk":Hx("23262b"),"wood_dk":Hx("39291b"),"moss":Hx("4f6a37")}
EMIT=set()
VCOL=bpy.data.materials.new("kit_vcol"); VCOL.use_nodes=True
_b=VCOL.node_tree.nodes["Principled BSDF"]; _b.inputs["Roughness"].default_value=0.9
_vc=VCOL.node_tree.nodes.new("ShaderNodeVertexColor"); _vc.layer_name="Col"
VCOL.node_tree.links.new(_vc.outputs["Color"], _b.inputs["Base Color"])
def flat(o):
    for p in o.data.polygons: p.use_smooth=False
def box(P,sx,sy,sz,loc,c,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot); o=bpy.context.active_object; o.scale=(sx,sy,sz); flat(o); P.append((o,c)); return o
def cone(P,vn,r1,r2,dz,loc,c,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cone_add(vertices=vn,radius1=r1,radius2=r2,depth=dz,location=loc,rotation=rot); o=bpy.context.active_object; flat(o); P.append((o,c)); return o
def finalize(P,name):
    for o,_ in P:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    zs=[(o.matrix_world@v.co).z for o,_ in P for v in o.data.vertices]; minz=min(zs); span=max(max(zs)-minz,1e-4)
    rnd=random.Random(hash(name)&0xffff)
    for o,col in P:
        me=o.data
        ca=me.color_attributes.new(name="Col",type='BYTE_COLOR',domain='CORNER'); base=PAL[col]
        for poly in me.polygons:
            fn=1.0+(rnd.random()-0.5)*0.07
            for li in poly.loop_indices:
                z=(o.matrix_world@me.vertices[me.loops[li].vertex_index].co).z; t=(z-minz)/span; f=(0.72+0.52*t)*fn
                ca.data[li].color=(min(base[0]*f,1),min(base[1]*f,1),min(base[2]*f,1),1.0)
        me.materials.clear(); me.materials.append(VCOL)
    bpy.ops.object.select_all(action='DESELECT')
    for o,_ in P: o.select_set(True)
    bpy.context.view_layer.objects.active=P[0][0]; bpy.ops.object.join()
    o=bpy.context.active_object; o.name=name; return o

SHADES=["stone","stone_lt","stone_2","stone_dk"]
def panel(P,cx,cy,w,d,z0,height,vertical=False):
    """ashlar stone-block panel with mortar backing. vertical=True -> runs along Y (depth=w)."""
    if vertical: box(P,d,w,height,(cx,cy,z0+height/2),"mortar")
    else:        box(P,w,d,height,(cx,cy,z0+height/2),"mortar")
    bw=0.3; rows=max(2,int(round(height/0.22))); rh=height/rows; k=hash((cx,cy))&7
    nb=max(2,int(round(w/bw)))
    for r in range(rows):
        zc=z0+rh/2+r*rh; off=0.5 if r%2 else 0.0
        for j in range(nb):
            u=-w/2+(j+0.5+off)*(w/nb)
            if u>w/2-0.04: continue
            bw_=(w/nb)*0.88; bh_=rh*0.84; sh=SHADES[k%4]; k+=1
            if vertical: box(P,d+0.05,bw_,bh_,(cx,cy+u,zc),sh)
            else:        box(P,bw_,d+0.05,bh_,(cx+u,cy,zc),sh)

def wall():
    P=[]; panel(P,0,0,1.0,0.4,0.0,0.78)
    for x in (-0.34,0.06): box(P,0.24,0.44,0.2,(x,0,0.9),"stone_dk")   # merlons
    box(P,1.02,0.06,0.05,(0,0.21,0.06),"moss")
    return finalize(P,"wall")
def wall_corner():
    P=[]; panel(P,0.0,0.3,0.4,0.4,0.0,0.78,vertical=True); panel(P,0.3,0.0,0.4,0.4,0.0,0.78)
    box(P,0.42,0.42,0.95,(0,0,0.48),"stone_2")                        # corner post
    for s in ((-0.15,0.0),(0.0,-0.15)): box(P,0.18,0.18,0.2,(s[0],s[1],1.0),"stone_dk")
    return finalize(P,"wall_corner")

def gate_arch():
    P=[]; TX=0.9; OW=2*TX-0.5   # opening inner width
    for s in (-1,1):                                  # towers (block-faced)
        panel(P,s*TX,-0.0,0.62,0.85,0.0,2.2)
        for k in range(2): box(P,0.24,0.87,0.3,(s*TX-0.19+k*0.38,0,2.4),"stone")  # crenellations
    box(P,2*TX+0.62,0.85,0.5,(0,0,2.2),"stone")       # solid lintel bridges towers
    for k in range(8): box(P,0.22,0.87,0.3,(-0.77+k*0.22,0,2.55),"stone")          # battlements across
    box(P,OW+0.2,0.22,2.0,(0,0.16,1.0),"iron_dk")     # dark recess behind opening (no see-through)
    R=TX-0.02; n=15                                   # filled overlapping arch (touches towers)
    for a in range(n):
        an=math.radians(a*(180/(n-1))); x=math.cos(an)*R; z=1.72+math.sin(an)*0.5
        box(P,0.27,0.86,0.24,(x,-0.03,z),"stone_lt",rot=(0,math.radians(90-math.degrees(an)),0))
    for x in [i*0.16 for i in range(-4,5)]: box(P,0.05,0.1,1.72,(x,-0.12,0.9),"iron")  # full portcullis
    for z in (0.22,0.56,0.9,1.24,1.58): box(P,OW+0.05,0.1,0.05,(0,-0.12,z),"iron")
    for x in (-0.48,-0.16,0.16,0.48): cone(P,4,0.06,0,0.13,(x,-0.12,0.06),"iron_dk")  # spikes
    return finalize(P,"gate_arch")

BUILD=[("wall",wall),("wall_corner",wall_corner),("gate_arch",gate_arch)]
placed=[]
for i,(nm,fn) in enumerate(BUILD):
    o=fn(); bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.export_scene.gltf(filepath=f"{GLB}/{nm}.glb",export_format='GLB',use_selection=True)
    o.location=(i*3.2-3.2,0,0); placed.append(o)

box([],40,40,0.1,(0,0,-0.06),"moss")
s=bpy.data.objects.new("S",bpy.data.lights.new("S",'SUN')); sc.collection.objects.link(s)
s.data.energy=3.0; s.data.angle=math.radians(4); s.rotation_euler=(math.radians(52),math.radians(8),math.radians(38))
f=bpy.data.objects.new("F",bpy.data.lights.new("F",'SUN')); sc.collection.objects.link(f)
f.data.energy=1.0; f.data.use_shadow=False; f.rotation_euler=(math.radians(62),0,math.radians(220))
sc.world=bpy.data.worlds.new("W"); sc.world.use_nodes=True
bg=sc.world.node_tree.nodes["Background"]; bg.inputs[1].default_value=0.5; bg.inputs[0].default_value=(0.55,0.6,0.66,1)
sc.view_settings.view_transform='Standard'
cam=bpy.data.objects.new("C",bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=10; cam.location=(2,-9,5)
look=mathutils.Vector((1,0,1.0))-mathutils.Vector(cam.location); cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
sc.render.engine='BLENDER_EEVEE'
try: sc.eevee.taa_render_samples=64
except Exception: pass
sc.render.resolution_x=1700; sc.render.resolution_y=850; sc.render.filepath=f"{D}/improved3_sheet.png"
bpy.ops.render.render(write_still=True)
print("IMPROVED3 DONE")
