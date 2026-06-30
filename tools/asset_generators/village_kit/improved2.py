"""Rework: authentic Tudor framing on houses, detailed tower, stained-glass church.
blender -b --python improved2.py"""
import bpy, bmesh, math, mathutils, os, random
D="C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/25899eda-2041-4e64-a0a8-0c83c9100526/scratchpad"
GLB=f"{D}/kit_improved_glb"; os.makedirs(GLB,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
def Hx(h): return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
PAL={"stone":Hx("6f756a"),"stone_dk":Hx("4c5249"),"stone_lt":Hx("868c80"),"plaster":Hx("cabf9f"),
 "beam":Hx("352519"),"wood":Hx("5a4230"),"wood_dk":Hx("39291b"),"thatch":Hx("7a6332"),
 "slate":Hx("3b434d"),"iron":Hx("3e424a"),"iron_dk":Hx("23262b"),"moss":Hx("4f6a37"),
 "gold":Hx("c8a23a"),"flag":Hx("7a2f2a"),"window":Hx("ffcf6b"),
 "sg_blue":Hx("2c4f9e"),"sg_red":Hx("9e2c34"),"sg_gold":Hx("c79a2e"),"sg_green":Hx("2c7a52")}
# emissive (glow) color names
EMIT={"window","sg_blue","sg_red","sg_gold","sg_green"}
VCOL=bpy.data.materials.new("kit_vcol"); VCOL.use_nodes=True
_b=VCOL.node_tree.nodes["Principled BSDF"]; _b.inputs["Roughness"].default_value=0.9
_vc=VCOL.node_tree.nodes.new("ShaderNodeVertexColor"); _vc.layer_name="Col"
VCOL.node_tree.links.new(_vc.outputs["Color"], _b.inputs["Base Color"])
EMITM={}
for n in EMIT:
    m=bpy.data.materials.new("em_"+n); m.use_nodes=True; b=m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value=(*PAL[n],1); b.inputs["Emission Color"].default_value=(*PAL[n],1)
    b.inputs["Emission Strength"].default_value=1.6 if n=="window" else 2.2; EMITM[n]=m
def flat(o):
    for p in o.data.polygons: p.use_smooth=False
def box(P,sx,sy,sz,loc,c,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot); o=bpy.context.active_object; o.scale=(sx,sy,sz); flat(o); P.append((o,c)); return o
def cyl(P,vn,r,dz,loc,c,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vn,radius=r,depth=dz,location=loc,rotation=rot); o=bpy.context.active_object; flat(o); P.append((o,c)); return o
def cone(P,vn,r1,r2,dz,loc,c,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cone_add(vertices=vn,radius1=r1,radius2=r2,depth=dz,location=loc,rotation=rot); o=bpy.context.active_object; flat(o); P.append((o,c)); return o
def gable(P,w,d,h,loc,c,over=0.16):
    w+=over; d+=over; bm=bmesh.new()
    v=[bm.verts.new((-w/2,-d/2,0)),bm.verts.new((w/2,-d/2,0)),bm.verts.new((0,-d/2,h)),
       bm.verts.new((-w/2,d/2,0)),bm.verts.new((w/2,d/2,0)),bm.verts.new((0,d/2,h))]
    for f in [(0,1,2),(5,4,3),(0,2,5,3),(2,1,4,5),(1,0,3,4)]: bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces); me=bpy.data.meshes.new("g"); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new("g",me); sc.collection.objects.link(o); o.location=loc; flat(o); P.append((o,c)); return o
def brace(P,y,x0,z0,x1,z1,c="beam",t=0.045):
    dx=x1-x0; dz=z1-z0; L=math.hypot(dx,dz); ang=math.atan2(dx,dz)
    box(P,t,0.05,L,((x0+x1)/2,y,(z0+z1)/2),c,rot=(0,ang,0))

def tudor(P,w,fy,z0,h,studs=4):
    """authentic half-timber framing on a wall face at y=fy (timbers protrude outward)."""
    y=fy
    box(P,w,0.05,0.07,(0,y,z0+0.035),"beam")          # bottom sill
    box(P,w,0.05,0.06,(0,y,z0+h*0.52),"beam")         # mid rail
    box(P,w,0.05,0.07,(0,y,z0+h-0.035),"beam")        # top plate
    for s in (-1,1): box(P,0.07,0.055,h,(s*(w/2-0.035),y,z0+h/2),"beam")  # corner posts
    for i in range(1,studs):                          # evenly spaced studs
        box(P,0.05,0.05,h,(-w/2+i*(w/studs),y,z0+h/2),"beam")
    # diagonal braces in each corner panel (classic Tudor)
    pw=w/studs
    brace(P,y,-w/2+0.04,z0+0.05,-w/2+pw-0.04,z0+h*0.5)
    brace(P,y, w/2-0.04,z0+0.05, w/2-pw+0.04,z0+h*0.5)
    brace(P,y,-w/2+0.04,z0+h-0.05,-w/2+pw-0.04,z0+h*0.52)
    brace(P,y, w/2-0.04,z0+h-0.05, w/2-pw+0.04,z0+h*0.52)

def finalize(P,name):
    for o,_ in P:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    zs=[(o.matrix_world@v.co).z for o,_ in P for v in o.data.vertices]; minz=min(zs); span=max(max(zs)-minz,1e-4)
    rnd=random.Random(hash(name)&0xffff)
    for o,col in P:
        me=o.data
        if col in EMIT:
            me.materials.clear(); me.materials.append(EMITM[col]); continue
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

def house(name,W=1.35,Dd=1.15,floors=1,jetty=True,roof="slate"):
    P=[]; bh=0.55
    box(P,W,Dd,bh,(0,0,bh/2),"stone")
    UW,UD=(W+0.22,Dd+0.22) if jetty else (W,Dd); z=bh
    for fl in range(floors):
        box(P,UW,UD,0.6,(0,0,z+0.3),"plaster")
        if jetty and fl==0: box(P,UW+0.02,UD+0.02,0.05,(0,0,z),"beam")
        tudor(P,UW,-UD/2-0.025,z,0.6)                 # front framing
        tudor(P,UW, UD/2+0.025,z,0.6)                 # back framing
        for sx in (-UW/2-0.025,UW/2+0.025):           # side framing (rotated -> along depth)
            for zz in (z+0.035,z+0.32,z+0.565): box(P,0.05,UD,0.05,(sx,0,zz),"beam")
            box(P,0.06,0.055,0.6,(sx,-UD/2+0.04,z+0.3),"beam"); box(P,0.06,0.055,0.6,(sx,UD/2-0.04,z+0.3),"beam")
        for wx in (-0.32,0.32):
            box(P,0.22,0.05,0.24,(wx,-UD/2-0.04,z+0.32),"beam"); box(P,0.15,0.05,0.17,(wx,-UD/2-0.06,z+0.32),"window")
        z+=0.6
    box(P,0.26,0.05,0.46,(0,-Dd/2-0.02,0.23),"wood_dk"); box(P,0.18,0.05,0.36,(0,-Dd/2-0.04,0.2),"wood")
    gable(P,UW,UD,0.7,(0,0,z),roof,over=0.2); box(P,0.08,UD+0.4,0.07,(0,0,z+0.7),"wood_dk")
    box(P,0.2,0.2,z+0.5,(W*0.42,0.34,(z+0.5)/2),"stone"); box(P,0.26,0.26,0.08,(W*0.42,0.34,z+0.5),"stone_dk")
    return finalize(P,name)

def tower():
    P=[]
    cone(P,8,0.7,0.56,2.2,(0,0,1.1),"stone")          # battered (tapered) shaft
    for z in (0.55,1.2,1.85): cyl(P,8,0.6,0.05,(0,0,z),"stone_dk")   # stone courses
    for a in (0,90,180,270):                          # arrow-slit windows x2 heights
        an=math.radians(a)
        for zz in (0.85,1.5): box(P,0.06,0.12,0.32,(math.sin(an)*0.6,math.cos(an)*0.6,zz),"iron_dk",rot=(0,0,an))
    box(P,0.34,0.06,0.6,(0,-0.6,0.3),"wood_dk")       # door
    for s in (-1,1): box(P,0.06,0.06,0.62,(s*0.2,-0.62,0.3),"stone_lt")  # door jambs
    box(P,0.46,0.06,0.12,(0,-0.62,0.62),"stone_lt")
    box(P,0.24,0.05,0.28,(0,-0.6,1.55),"window")      # glow window
    cyl(P,16,0.74,0.16,(0,0,2.18),"stone")            # machicolation overhang
    for k in range(8):                                # battlements (merlons)
        a=math.radians(k*45); box(P,0.2,0.2,0.3,(math.cos(a)*0.6,math.sin(a)*0.6,2.4),"stone")
    cyl(P,6,0.03,0.8,(0,0,2.75),"wood"); box(P,0.34,0.02,0.22,(0.18,0,2.95),"flag")  # banner
    return finalize(P,"tower")

def sg_window(P,cx,fy,cz,w=0.36,h=0.6,r=(0,0,0)):
    """leaded stained-glass: stone frame + grid of colored emissive panes."""
    box(P,w+0.08,0.05,h+0.08,(cx,fy+0.02,cz),"stone_dk",rot=r)   # frame
    cols=["sg_blue","sg_red","sg_gold","sg_green","sg_red","sg_blue"]
    k=0
    for gy in (-h/4,h/4):
        for gx in (-w/3,0,w/3):
            box(P,w/3.4,0.04,h/2.4,(cx+gx,fy,cz+gy),cols[k%len(cols)],rot=r); k+=1
    cone(P,3,w/1.8,0,h*0.35,(cx,fy,cz+h/2+0.05),"stone_dk",rot=(0,0,0))  # pointed arch top

def church():
    P=[]
    box(P,1.5,3.2,1.1,(0,0.2,0.55),"stone")
    gable(P,1.5,3.2,0.95,(0,0.2,1.1),"slate",over=0.22)
    box(P,0.55,0.85,1.05,(0,1.95,0.52),"stone")
    for s in (-1,1):
        for by in (-0.9,0.0,0.9):
            box(P,0.18,0.2,0.85,(s*0.78,by,0.42),"stone"); box(P,0.28,0.2,0.18,(s*0.86,by,0.2),"stone_dk")
    for s in (-1,1):                                   # side stained-glass windows
        for by in (-0.55,0.55):
            sg_window(P,0,0,0.7,w=0.3,h=0.55,r=(0,math.radians(s*90),0))  # placeholder replaced below
    # (place side windows properly on the side walls)
    for s in (-1,1):
        for by in (-0.55,0.55):
            x=s*0.78
            box(P,0.05,0.34,0.6,(x,by,0.72),"stone_dk")
            kk=0; cols=["sg_blue","sg_gold","sg_red"]
            for pz in (0.58,0.86):
                box(P,0.045,0.26,0.22,(x+s*0.01,by,pz),cols[kk%3],rot=(0,0,0)); kk+=1
    # bell tower + spire + bell + cross
    box(P,0.9,0.9,2.4,(0,-1.55,1.2),"stone")
    for s in (-1,1): box(P,0.18,0.2,0.5,(s*0.42,-1.55,2.1),"sg_gold")
    box(P,1.0,1.0,0.12,(0,-1.55,2.45),"stone_dk")
    cone(P,4,0.66,0,0.95,(0,-1.55,3.0),"slate",rot=(0,0,math.radians(45)))
    cyl(P,6,0.1,0.18,(0,-1.55,2.3),"gold")
    box(P,0.07,0.07,0.36,(0,-1.55,3.55),"gold"); box(P,0.26,0.07,0.07,(0,-1.55,3.62),"gold")
    # front: big stained rose window + arched door + steps
    cyl(P,12,0.26,0.05,(0,-2.0,1.55),"stone_dk",rot=(math.radians(90),0,0))   # rose frame
    for k in range(6):
        a=math.radians(k*60); col=["sg_blue","sg_red","sg_gold"][k%3]
        box(P,0.13,0.04,0.13,(math.cos(a)*0.13,-2.01,1.55+math.sin(a)*0.13),col)
    box(P,0.09,0.04,0.09,(0,-2.01,1.55),"sg_gold")
    box(P,0.42,0.08,0.7,(0,-2.0,0.45),"wood_dk"); cone(P,3,0.24,0,0.22,(0,-2.0,0.82),"stone",rot=(0,math.radians(90),0))
    for i in range(3): box(P,0.7+i*0.14,0.16,0.08,(0,-2.05-i*0.1,0.05),"stone")
    return finalize(P,"church")

BUILD=[("cottage",lambda:house("cottage")),("tavern",lambda:house("tavern",W=1.6,Dd=1.3,roof="thatch")),
       ("house_small",lambda:house("house_small",jetty=False,roof="thatch")),
       ("house_tall",lambda:house("house_tall",W=1.1,Dd=1.0,floors=2)),
       ("tower",tower),("church",church)]
placed=[]
for i,(nm,fn) in enumerate(BUILD):
    o=fn(); bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.export_scene.gltf(filepath=f"{GLB}/{nm}.glb",export_format='GLB',use_selection=True)
    o.location=(i*3.4-8.5,0,0); placed.append(o)

box([],40,40,0.1,(0,0,-0.06),"grass")
s=bpy.data.objects.new("S",bpy.data.lights.new("S",'SUN')); sc.collection.objects.link(s)
s.data.energy=3.0; s.data.angle=math.radians(4); s.rotation_euler=(math.radians(52),math.radians(8),math.radians(38))
f=bpy.data.objects.new("F",bpy.data.lights.new("F",'SUN')); sc.collection.objects.link(f)
f.data.energy=1.0; f.data.use_shadow=False; f.rotation_euler=(math.radians(62),0,math.radians(220))
sc.world=bpy.data.worlds.new("W"); sc.world.use_nodes=True
bg=sc.world.node_tree.nodes["Background"]; bg.inputs[1].default_value=0.45; bg.inputs[0].default_value=(0.5,0.56,0.64,1)
sc.view_settings.view_transform='Standard'
cam=bpy.data.objects.new("C",bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=20; cam.location=(0,-12,7)
look=mathutils.Vector((0,0,1.3))-mathutils.Vector(cam.location); cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
sc.render.engine='BLENDER_EEVEE'
try: sc.eevee.taa_render_samples=64
except Exception: pass
sc.render.resolution_x=2100; sc.render.resolution_y=720; sc.render.filepath=f"{D}/improved2_sheet.png"
bpy.ops.render.render(write_still=True)
print("IMPROVED2 DONE")
