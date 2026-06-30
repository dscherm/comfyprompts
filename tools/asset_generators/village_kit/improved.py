"""Reworked hero pieces + vertex-color gradient shading ("more texture").
Windmill, stone bridge, arched gate+portcullis, graveyard, detailed church.
blender -b --python improved.py"""
import bpy, bmesh, math, mathutils, os, random
D="C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/25899eda-2041-4e64-a0a8-0c83c9100526/scratchpad"
GLB=f"{D}/kit_improved_glb"; os.makedirs(GLB,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
def Hx(h): return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
PAL={"stone":Hx("6f756a"),"stone_dk":Hx("4c5249"),"stone_lt":Hx("868c80"),"plaster":Hx("c9bfa6"),
 "beam":Hx("3a2a1a"),"wood":Hx("5a4230"),"wood_dk":Hx("39291b"),"thatch":Hx("7a6332"),
 "slate":Hx("3b434d"),"iron":Hx("3e424a"),"iron_dk":Hx("2a2d33"),"moss":Hx("4f6a37"),
 "grass":Hx("44602f"),"dirt":Hx("4d3c29"),"canvas":Hx("d8cdae"),"gold":Hx("c8a23a"),
 "bone":Hx("c4bba2"),"window":Hx("ffcf6b"),"glass":Hx("9ec6d8"),"cobble":Hx("5a5a62")}
GLOW={"window","fire"}

# one shared vertex-color material -> "more texture" via baked gradient, no atlas bleed
VCOL=bpy.data.materials.new("kit_vcol"); VCOL.use_nodes=True
_b=VCOL.node_tree.nodes["Principled BSDF"]; _b.inputs["Roughness"].default_value=0.9
_vc=VCOL.node_tree.nodes.new("ShaderNodeVertexColor"); _vc.layer_name="Col"
VCOL.node_tree.links.new(_vc.outputs["Color"], _b.inputs["Base Color"])
GLOWM=bpy.data.materials.new("kit_glow"); GLOWM.use_nodes=True
_g=GLOWM.node_tree.nodes["Principled BSDF"]; _g.inputs["Emission Color"].default_value=(*PAL["window"],1)
_g.inputs["Emission Strength"].default_value=1.8; _g.inputs["Base Color"].default_value=(*PAL["window"],1)

def flat(o):
    for p in o.data.polygons: p.use_smooth=False
def box(P,sx,sy,sz,loc,c,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot); o=bpy.context.active_object; o.scale=(sx,sy,sz); flat(o); P.append((o,c)); return o
def cyl(P,vn,r,dz,loc,c,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vn,radius=r,depth=dz,location=loc,rotation=rot); o=bpy.context.active_object; flat(o); P.append((o,c)); return o
def cone(P,vn,r1,r2,dz,loc,c,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cone_add(vertices=vn,radius1=r1,radius2=r2,depth=dz,location=loc,rotation=rot); o=bpy.context.active_object; flat(o); P.append((o,c)); return o
def ico(P,r,loc,c,sub=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=r,location=loc); o=bpy.context.active_object; flat(o); P.append((o,c)); return o
def gable(P,w,d,h,loc,c,over=0.16):
    w+=over; d+=over; bm=bmesh.new()
    v=[bm.verts.new((-w/2,-d/2,0)),bm.verts.new((w/2,-d/2,0)),bm.verts.new((0,-d/2,h)),
       bm.verts.new((-w/2,d/2,0)),bm.verts.new((w/2,d/2,0)),bm.verts.new((0,d/2,h))]
    for f in [(0,1,2),(5,4,3),(0,2,5,3),(2,1,4,5),(1,0,3,4)]: bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces); me=bpy.data.meshes.new("g"); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new("g",me); sc.collection.objects.link(o); o.location=loc; flat(o); P.append((o,c)); return o

def finalize(P,name):
    for o,_ in P:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    zs=[(o.matrix_world@v.co).z for o,_ in P for v in o.data.vertices]; minz=min(zs); span=max(max(zs)-minz,1e-4)
    rnd=random.Random(hash(name)&0xffff)
    for o,col in P:
        me=o.data
        if col in GLOW:
            me.materials.clear(); me.materials.append(GLOWM); continue
        ca=me.color_attributes.new(name="Col",type='BYTE_COLOR',domain='CORNER')
        base=PAL[col]
        for poly in me.polygons:
            fn=1.0+(rnd.random()-0.5)*0.07   # subtle per-face variation = texture
            for li in poly.loop_indices:
                z=(o.matrix_world@me.vertices[me.loops[li].vertex_index].co).z
                t=(z-minz)/span; f=(0.72+0.52*t)*fn
                ca.data[li].color=(min(base[0]*f,1),min(base[1]*f,1),min(base[2]*f,1),1.0)
        me.materials.clear(); me.materials.append(VCOL)
    bpy.ops.object.select_all(action='DESELECT')
    for o,_ in P: o.select_set(True)
    bpy.context.view_layer.objects.active=P[0][0]; bpy.ops.object.join()
    o=bpy.context.active_object; o.name=name; return o

# ---------------- reworked pieces ----------------
def windmill():
    P=[]
    cone(P,10,0.72,0.5,2.0,(0,0,1.0),"stone")          # tapered tower
    for z in (0.6,1.3): cyl(P,10,0.04+0.0,0.06,(0,0,z),"stone_dk")  # stone bands
    cyl(P,10,0.52,0.25,(0,0,2.05),"wood")              # cap
    cone(P,10,0.55,0,0.45,(0,0,2.35),"slate")
    cyl(P,8,0.13,0.4,(0,-0.7,2.0),"wood_dk",rot=(math.radians(90),0,0))   # hub
    HX,HY,HZ=0,-0.84,2.0
    for ang in (45,-45):                                # two crossed sail arms (X pattern, equal length)
        a=math.radians(ang); ca=math.cos(a); sa=math.sin(a); r=(0,a,0)
        box(P,0.07,0.06,3.1,(HX,HY,HZ),"wood",rot=r)                       # main spar
        box(P,0.5,0.04,3.0,(HX,HY-0.02,HZ),"canvas",rot=r)                 # sail canvas
        for off in (-0.22,0.22):                                          # frame rails (offset across width=X)
            box(P,0.04,0.05,3.0,(HX+off*ca,HY-0.03,HZ-off*sa),"wood_dk",rot=r)
        for t in (-1.1,-0.55,0.55,1.1):                                   # lattice ribs along the sail
            box(P,0.52,0.04,0.05,(HX+t*sa,HY-0.03,HZ+t*ca),"wood_dk",rot=r)
    # door + gallery
    box(P,0.32,0.06,0.55,(0,-0.66,0.3),"wood_dk"); box(P,0.26,0.05,0.22,(0.45,-0.5,1.2),"window")
    box(P,1.0,1.0,0.06,(0,0,0.95),"wood");
    for a in range(8):
        an=math.radians(a*45); box(P,0.05,0.05,0.3,(math.cos(an)*0.5,math.sin(an)*0.5,1.1),"wood")
    return finalize(P,"windmill")

def stone_bridge():
    P=[]
    # wide deck (runs along Y), slightly raised
    box(P,2.0,3.0,0.2,(0,0,0.62),"stone")
    for ry in range(-6,7):                              # cobble surface rows
        for rx in (-0.7,-0.24,0.24,0.7):
            box(P,0.4,0.22,0.05,(rx,ry*0.23,0.73),"cobble")
    # side parapets + posts
    for s in (-1,1):
        box(P,0.18,3.0,0.36,(s*0.95,0,0.88),"stone_dk")
        for py in (-1.2,-0.4,0.4,1.2): box(P,0.24,0.24,0.18,(s*0.95,py,1.1),"stone")
    # clean stone arch underneath: half-cylinder tunnel along X (the water direction)
    cyl(P,20,0.66,2.05,(0,0,0.0),"stone",rot=(0,math.radians(90),0))      # outer arch ring
    cyl(P,20,0.46,2.1,(0,0,0.0),"stone_dk",rot=(0,math.radians(90),0))    # tunnel shadow
    # end abutments (under the deck ends)
    for s in (-1,1): box(P,2.0,0.7,0.9,(0,s*1.35,0.05),"stone")
    return finalize(P,"stone_bridge")

def gate_arch():
    P=[]
    for s in (-1,1):
        box(P,0.55,0.8,2.2,(s*0.95,0,1.1),"stone")     # towers
        for k in range(2): box(P,0.2,0.82,0.26,(s*0.95-0.18+0.36*k,0,2.3),"stone_dk")  # crenellations
    # arch (voussoirs over the opening)
    for a in range(11):
        an=math.radians(a*18); x=math.cos(an)*0.95; z=2.0+math.sin(an)*0.55
        box(P,0.2,0.82,0.22,(x,0,z),"stone",rot=(0,math.radians(-(a-5)*18),0))
    box(P,2.5,0.85,0.3,(0,0,2.75),"stone_dk")          # top lintel
    # FULL portcullis: iron bar grid covering the whole arched opening
    for x in [-0.6,-0.36,-0.12,0.12,0.36,0.6]: box(P,0.05,0.12,2.0,(x,0,1.05),"iron")
    for z in [0.3,0.65,1.0,1.35,1.7]: box(P,1.35,0.12,0.05,(0,0,z),"iron")
    for x in [-0.6,-0.12,0.36]: cone(P,4,0.06,0,0.1,(x,0,0.06),"iron_dk")  # spiked bottoms
    return finalize(P,"gate_arch")

def graveyard():
    P=[]
    box(P,3.0,3.0,0.1,(0,0,0.0),"grass")               # plot
    box(P,2.6,2.6,0.06,(0,0,0.05),"dirt")
    # iron fence perimeter with posts (gap at front for entrance)
    for x in [-1.3,-0.8,-0.3,0.7,1.2]:                 # front rails (gap near 0.2)
        if abs(x-0.2)>0.3: box(P,0.4,0.05,0.4,(x,-1.4,0.25),"iron")
    for x in [-1.3,-0.8,-0.3,0.2,0.7,1.2]: box(P,0.4,0.05,0.4,(x,1.4,0.25),"iron")
    for y in [-1.3,-0.8,-0.3,0.2,0.7,1.2]:
        box(P,0.05,0.4,0.4,(-1.4,y,0.25),"iron"); box(P,0.05,0.4,0.4,(1.4,y,0.25),"iron")
    for cx in (-1.4,1.4):
        for cy in (-1.4,1.4): box(P,0.1,0.1,0.65,(cx,cy,0.32),"iron_dk")  # corner posts
    # gravestones (varied) + mounds
    def cross(x,y,r=0): box(P,0.08,0.08,0.45,(x,y,0.25),"stone"); box(P,0.28,0.08,0.08,(x,y,0.38),"stone")
    def slab(x,y): box(P,0.3,0.1,0.4,(x,y,0.22),"stone_dk"); box(P,0.3,0.12,0.1,(x,y,0.42),"stone")
    def mound(x,y): box(P,0.55,0.32,0.12,(x,y,0.1),"dirt")
    slab(-0.8,0.6); mound(-0.8,0.2); cross(0.0,0.7); mound(0.0,0.3)
    slab(0.8,0.5); mound(0.8,0.1); cross(-0.8,-0.5,0); slab(0.7,-0.5)
    # central tomb + dead tree
    box(P,0.6,0.9,0.3,(0,-0.4,0.15),"stone"); box(P,0.66,0.96,0.08,(0,-0.4,0.32),"stone_dk")
    cross(0,-0.4)
    cyl(P,6,0.08,1.0,(1.0,0.9,0.5),"wood_dk")
    for a in (35,-30): cyl(P,5,0.04,0.4,(1.05,0.9,0.95),"wood_dk",rot=(0,math.radians(a),0))
    return finalize(P,"graveyard")

def church():
    P=[]
    box(P,1.5,3.2,1.1,(0,0.2,0.55),"stone")            # nave
    gable(P,1.5,3.2,0.95,(0,0.2,1.1),"slate",over=0.22)
    box(P,0.5,0.8,1.0,(0,1.9,0.5),"stone")             # apse-ish back
    # buttresses
    for s in (-1,1):
        for by in (-0.9,0.0,0.9):
            box(P,0.18,0.2,0.85,(s*0.78,by,0.42),"stone"); box(P,0.28,0.2,0.18,(s*0.86,by,0.2),"stone_dk")
    # pointed Gothic windows (glass + frame)
    for s in (-1,1):
        for by in (-0.45,0.45):
            box(P,0.04,0.16,0.5,(s*0.76,by,0.65),"glass"); cone(P,3,0.1,0,0.14,(s*0.76,by,0.95),"stone",rot=(0,math.radians(s*90),0))
    # bell tower (front), taller, belfry + spire + bell
    box(P,0.85,0.85,2.3,(0,-1.5,1.15),"stone")
    for s in (-1,1): box(P,0.18,0.18,0.5,(s*0.4,-1.5,2.05),"glass")   # belfry openings
    box(P,0.95,0.95,0.12,(0,-1.5,2.35),"stone_dk")
    cone(P,4,0.62,0,0.9,(0,-1.5,2.9),"slate",rot=(0,0,math.radians(45)))
    cyl(P,6,0.1,0.18,(0,-1.5,2.2),"gold")              # bell
    box(P,0.07,0.07,0.34,(0,-1.5,3.4),"gold"); box(P,0.24,0.07,0.07,(0,-1.5,3.46),"gold")  # cross
    # rose window + arched door + steps
    cyl(P,8,0.18,0.06,(0,-1.93,1.5),"glass",rot=(math.radians(90),0,0))
    box(P,0.4,0.08,0.7,(0,-1.93,0.45),"wood_dk"); cone(P,3,0.22,0,0.2,(0,-1.93,0.8),"stone",rot=(0,math.radians(90),0))
    for i in range(3): box(P,0.7+i*0.12,0.16,0.08,(0,-2.0-i*0.1,0.04+i*0.0),"stone")
    return finalize(P,"church")

def tree_dead():
    P=[]
    cyl(P,7,0.14,1.7,(0,0,0.85),"wood_dk"); cyl(P,6,0.09,0.7,(0,0,1.6),"wood_dk")
    def br(h,deg,axis,L,r=0.055):
        a=math.radians(deg)
        if axis=='y':  cyl(P,5,r,L,(math.sin(a)*L/2,0,h+math.cos(a)*L/2),"wood_dk",rot=(0,a,0))
        else:          cyl(P,5,r,L,(0,math.sin(a)*L/2,h+math.cos(a)*L/2),"wood_dk",rot=(a,0,0))
    br(1.15,42,'y',0.75); br(1.35,-48,'y',0.65); br(1.5,28,'x',0.6); br(0.85,-34,'x',0.55)
    br(1.7,16,'y',0.5,0.04); br(1.62,-22,'x',0.45,0.04); br(1.0,55,'y',0.4,0.04)
    return finalize(P,"tree_dead")

BUILD=[("windmill",windmill),("stone_bridge",stone_bridge),("gate_arch",gate_arch),
       ("graveyard",graveyard),("church",church),("tree_dead",tree_dead)]
placed=[]
for i,(nm,fn) in enumerate(BUILD):
    o=fn(); bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.export_scene.gltf(filepath=f"{GLB}/{nm}.glb",export_format='GLB',use_selection=True)
    o.location=(i*3.5-8.75,0,0); placed.append(o)

box([],40,40,0.1,(0,0,-0.06),"grass")
s1=bpy.data.objects.new("S",bpy.data.lights.new("S",'SUN')); sc.collection.objects.link(s1)
s1.data.energy=3.2; s1.data.angle=math.radians(4); s1.rotation_euler=(math.radians(52),math.radians(8),math.radians(38))
s2=bpy.data.objects.new("F",bpy.data.lights.new("F",'SUN')); sc.collection.objects.link(s2)
s2.data.energy=1.1; s2.data.use_shadow=False; s2.rotation_euler=(math.radians(62),0,math.radians(220))
sc.world=bpy.data.worlds.new("W"); sc.world.use_nodes=True
bg=sc.world.node_tree.nodes["Background"]; bg.inputs[1].default_value=0.55; bg.inputs[0].default_value=(0.6,0.66,0.74,1)
sc.view_settings.view_transform='Standard'
cam=bpy.data.objects.new("C",bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=21; cam.location=(0,-12,8.5)
look=mathutils.Vector((0,0,1.2))-mathutils.Vector(cam.location); cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
sc.render.engine='BLENDER_EEVEE'
try: sc.eevee.taa_render_samples=64
except Exception: pass
sc.render.resolution_x=2100; sc.render.resolution_y=720; sc.render.filepath=f"{D}/improved_sheet.png"
bpy.ops.render.render(write_still=True)
print("IMPROVED DONE")
