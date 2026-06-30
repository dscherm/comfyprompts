"""Rework: windmill (window flush on tapered tower) + much more detailed tower
(stone courses, wooden hoarding gallery, windows, torch, machicolation, banner).
blender -b --python improved4.py"""
import bpy, bmesh, math, mathutils, os, random
D="C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/25899eda-2041-4e64-a0a8-0c83c9100526/scratchpad"
GLB=f"{D}/kit_improved_glb"; os.makedirs(GLB,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
def Hx(h): return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
PAL={"stone":Hx("6f756a"),"stone_dk":Hx("4c5249"),"stone_lt":Hx("868c80"),"slate":Hx("3b434d"),
 "wood":Hx("5a4230"),"wood_dk":Hx("39291b"),"canvas":Hx("d8cdae"),"iron":Hx("3e424a"),
 "iron_dk":Hx("23262b"),"moss":Hx("4f6a37"),"flag":Hx("7a2f2a"),"window":Hx("ffcf6b"),"fire":Hx("ff8a2a")}
EMIT={"window","fire"}
VCOL=bpy.data.materials.new("kit_vcol"); VCOL.use_nodes=True
_b=VCOL.node_tree.nodes["Principled BSDF"]; _b.inputs["Roughness"].default_value=0.9
_vc=VCOL.node_tree.nodes.new("ShaderNodeVertexColor"); _vc.layer_name="Col"
VCOL.node_tree.links.new(_vc.outputs["Color"], _b.inputs["Base Color"])
EMITM={}
for n in EMIT:
    m=bpy.data.materials.new("em_"+n); m.use_nodes=True; b=m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value=(*PAL[n],1); b.inputs["Emission Color"].default_value=(*PAL[n],1)
    b.inputs["Emission Strength"].default_value=2.0; EMITM[n]=m
def flat(o):
    for p in o.data.polygons: p.use_smooth=False
def box(P,sx,sy,sz,loc,c,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot); o=bpy.context.active_object; o.scale=(sx,sy,sz); flat(o); P.append((o,c)); return o
def cyl(P,vn,r,dz,loc,c,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vn,radius=r,depth=dz,location=loc,rotation=rot); o=bpy.context.active_object; flat(o); P.append((o,c)); return o
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
        if col in EMIT: me.materials.clear(); me.materials.append(EMITM[col]); continue
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

def windmill():
    P=[]
    R0,R1,Hh=0.72,0.5,2.0
    cone(P,12,R0,R1,Hh,(0,0,Hh/2),"stone")
    def rad(z): return R0+(R1-R0)*(z/Hh)
    for z in (0.55,1.25): cyl(P,12,rad(z)+0.02,0.07,(0,0,z),"stone_dk")   # courses (match taper)
    cyl(P,12,R1+0.04,0.26,(0,0,Hh+0.13),"wood")        # cap
    cone(P,12,R1+0.08,0,0.5,(0,0,Hh+0.4),"slate")
    # hub + crossed lattice sails
    cyl(P,8,0.13,0.4,(0,-(R1+0.2),Hh),"wood_dk",rot=(math.radians(90),0,0))
    HY=-(R1+0.34)
    for ang in (45,-45):
        a=math.radians(ang); ca=math.cos(a); sa=math.sin(a); r=(0,a,0)
        box(P,0.07,0.06,3.1,(0,HY,Hh),"wood",rot=r); box(P,0.5,0.04,3.0,(0,HY-0.02,Hh),"canvas",rot=r)
        for off in (-0.22,0.22): box(P,0.04,0.05,3.0,(off*ca,HY-0.03,Hh-off*sa),"wood_dk",rot=r)
        for t in (-1.1,-0.55,0.55,1.1): box(P,0.52,0.04,0.05,(t*sa,HY-0.03,Hh+t*ca),"wood_dk",rot=r)
    # door + windows FLUSH on the tapered front face (-Y)
    box(P,0.34,0.07,0.6,(0,-(rad(0.3)-0.01),0.32),"wood_dk")
    box(P,0.2,0.07,0.22,(0,-(rad(1.15)-0.01),1.15),"window")
    box(P,0.16,0.07,0.16,(0.0,-(rad(0.75)-0.01),0.75),"window")
    box(P,0.16,0.07,0.16,(0,(rad(1.0)-0.01),1.0),"window")          # back window
    # base gallery deck
    cyl(P,12,R0+0.06,0.06,(0,0,0.85),"wood")
    for k in range(8):
        an=math.radians(k*45); box(P,0.05,0.05,0.34,(math.cos(an)*(R0+0.02),math.sin(an)*(R0+0.02),1.0),"wood")
    return finalize(P,"windmill")

def tower():
    P=[]
    R0,R1,Hh=0.74,0.58,2.2
    cone(P,10,0.82,0.78,0.25,(0,0,0.12),"stone_dk")     # wider plinth/base
    cone(P,10,R0,R1,Hh,(0,0,Hh/2),"stone")              # battered shaft
    def rad(z): return R0+(R1-R0)*(z/Hh)
    for z in (0.5,1.0,1.5): cyl(P,10,rad(z)+0.02,0.06,(0,0,z),"stone_dk")  # stone courses
    # arrow slits (4 sides, 2 heights)
    for a in (0,90,180,270):
        an=math.radians(a)
        for zz in (0.8,1.3):
            box(P,0.06,0.12,0.34,(math.sin(an)*(rad(zz)-0.0),math.cos(an)*(rad(zz)-0.0),zz),"iron_dk",rot=(0,0,an))
    # door with stone arch frame (flush)
    box(P,0.34,0.07,0.6,(0,-(rad(0.3)-0.01),0.32),"wood_dk")
    for s in (-1,1): box(P,0.06,0.07,0.62,(s*0.2,-(rad(0.3)-0.01),0.32),"stone_lt")
    box(P,0.46,0.07,0.12,(0,-(rad(0.62)-0.01),0.62),"stone_lt")
    box(P,0.24,0.07,0.28,(0,-(rad(1.45)-0.01),1.45),"window")   # glow window (flush)
    # torch bracket (glowing) beside door
    box(P,0.05,0.12,0.05,(0.34,-(rad(0.9)-0.0),0.9),"iron"); cone(P,6,0.08,0,0.18,(0.34,-(rad(0.9)+0.1),1.0),"fire")
    # WOODEN HOARDING gallery near top (defensive timber gallery)
    cyl(P,10,R1+0.22,0.1,(0,0,1.78),"wood")             # gallery floor ring
    for k in range(10):
        an=math.radians(k*36); box(P,0.06,0.06,0.42,(math.cos(an)*(R1+0.2),math.sin(an)*(R1+0.2),2.0),"wood_dk")  # posts
    cyl(P,10,R1+0.26,0.06,(0,0,2.2),"wood_dk")          # gallery rail
    cone(P,10,R1+0.34,R1+0.1,0.18,(0,0,2.32),"slate")   # gallery sloped roof skirt
    # machicolation + battlements on the stone top
    cyl(P,10,R1+0.04,0.7,(0,0,1.9),"stone")             # top stone drum (inside hoarding)
    for k in range(8):
        an=math.radians(k*45); box(P,0.18,0.18,0.3,(math.cos(an)*(R1-0.02),math.sin(an)*(R1-0.02),2.45),"stone")  # merlons
    # banner
    cyl(P,6,0.03,0.85,(0,0,2.75),"wood"); box(P,0.36,0.02,0.24,(0.19,0,2.98),"flag"); box(P,0.04,0.04,0.05,(0,0,3.2),"iron_dk")
    box(P,0.5,0.06,0.05,(0,(R1-0.1),0.05),"moss")
    return finalize(P,"tower")

BUILD=[("windmill",windmill),("tower",tower)]
placed=[]
for i,(nm,fn) in enumerate(BUILD):
    o=fn(); bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.export_scene.gltf(filepath=f"{GLB}/{nm}.glb",export_format='GLB',use_selection=True)
    o.location=(i*3.6-1.8,0,0); placed.append(o)

box([],40,40,0.1,(0,0,-0.06),"moss")
s=bpy.data.objects.new("S",bpy.data.lights.new("S",'SUN')); sc.collection.objects.link(s)
s.data.energy=3.0; s.data.angle=math.radians(4); s.rotation_euler=(math.radians(52),math.radians(8),math.radians(38))
f=bpy.data.objects.new("F",bpy.data.lights.new("F",'SUN')); sc.collection.objects.link(f)
f.data.energy=1.0; f.data.use_shadow=False; f.rotation_euler=(math.radians(62),0,math.radians(220))
sc.world=bpy.data.worlds.new("W"); sc.world.use_nodes=True
bg=sc.world.node_tree.nodes["Background"]; bg.inputs[1].default_value=0.46; bg.inputs[0].default_value=(0.52,0.58,0.66,1)
sc.view_settings.view_transform='Standard'
cam=bpy.data.objects.new("C",bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=8.5; cam.location=(1,-9,5)
look=mathutils.Vector((0,0,1.5))-mathutils.Vector(cam.location); cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
sc.render.engine='BLENDER_EEVEE'
try: sc.eevee.taa_render_samples=64
except Exception: pass
sc.render.resolution_x=1300; sc.render.resolution_y=950; sc.render.filepath=f"{D}/improved4_sheet.png"
bpy.ops.render.render(write_still=True)
print("IMPROVED4 DONE")
