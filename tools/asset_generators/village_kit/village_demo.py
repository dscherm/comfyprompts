"""Import kit GLBs -> readable catalog render + assembled village hero render."""
import bpy, math, os, mathutils
D="C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/25899eda-2041-4e64-a0a8-0c83c9100526/scratchpad"
G=f"{D}/kit_glb"
def Hx(h): return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1.0,)

def imp(name,loc,rot=0):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f"{G}/{name}.glb")
    new=[o for o in bpy.data.objects if o not in before]
    for r in [o for o in new if not o.parent]:
        r.location=loc; r.rotation_euler.z=math.radians(rot)
    return new

def groundbox(size,loc,rgb):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.active_object
    o.scale=(size[0],size[1],size[2]); m=bpy.data.materials.new("g"); m.use_nodes=True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=rgb
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=1.0
    o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth=False
    return o

def setup_world(amb,col):
    sc=bpy.context.scene; sc.world=bpy.data.worlds.new("W"); sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes["Background"]; bg.inputs[1].default_value=amb; bg.inputs[0].default_value=col
    sc.view_settings.view_transform='Standard'
def sun(energy,rot,col=(1,1,1),shadow=True):
    s=bpy.data.objects.new("S",bpy.data.lights.new("S",'SUN')); bpy.context.scene.collection.objects.link(s)
    s.data.energy=energy; s.data.angle=math.radians(5); s.data.color=col[:3]; s.data.use_shadow=shadow
    s.rotation_euler=(math.radians(rot[0]),math.radians(rot[1]),math.radians(rot[2])); return s
def plight(loc,col,e):
    l=bpy.data.lights.new("P",'POINT'); l.color=col; l.energy=e
    o=bpy.data.objects.new("P",l); o.location=loc; bpy.context.scene.collection.objects.link(o)
def isocam(scale,loc,target=(0,0,0.4)):
    sc=bpy.context.scene; c=bpy.data.objects.new("C",bpy.data.cameras.new("C")); sc.collection.objects.link(c); sc.camera=c
    c.data.type='ORTHO'; c.data.ortho_scale=scale; c.location=loc
    look=mathutils.Vector(target)-mathutils.Vector(loc); c.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
def render(path,x=1500,y=1100):
    sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE'
    try: sc.eevee.taa_render_samples=48
    except Exception: pass
    sc.render.resolution_x=x; sc.render.resolution_y=y; sc.render.filepath=path
    bpy.ops.render.render(write_still=True)

NAMES=["cottage","house_small","house_tall","tavern","church","barn","tower","blacksmith",
 "wall","wall_gate","wall_corner","ground_grass","ground_dirt","path_straight","path_corner",
 "well","market_stall","barrel","crate","fence","tree","tree_dead","lamppost","brazier",
 "signpost","cart","haystack","gravestone"]

# ============ CATALOG ============
bpy.ops.wm.read_factory_settings(use_empty=True)
groundbox((40,40,0.1),(0,0,-0.06),Hx("3a3f44"))
for i,nm in enumerate(NAMES):
    col=i%7; row=i//7; imp(nm,(col*2.3-7, -row*2.3+5, 0))
setup_world(0.55,(0.5,0.55,0.62,1)); sun(3.0,(52,10,35)); sun(1.1,(62,0,215),shadow=False)
isocam(17,(0,-12,16),(0,0,0))
render(f"{D}/kit_catalog_clean.png",1600,1000)

# ============ VILLAGE HERO ============
bpy.ops.wm.read_factory_settings(use_empty=True)
groundbox((22,22,0.2),(0,0,-0.1),Hx("3e5226"))      # grass
groundbox((11,11,0.2),(0,0,-0.06),Hx("4d3c29"))     # dirt plaza
# perimeter wall (back + sides) with gate at front
for x in range(-4,5):
    imp("wall",(x,5,0),0)
for y in range(-4,5):
    imp("wall",(-5,y,0),90); imp("wall",(5,y,0),90)
imp("wall_corner",(-5,5,0),0); imp("wall_corner",(5,5,0),270)
imp("wall_gate",(0,-5,0),0)
# path from gate
for y in range(-4,3): imp("path_straight",(0,y,0),0)
# buildings around
imp("cottage",(-3.2,2.6,0),20); imp("tavern",(3.0,2.8,0),-25)
imp("church",(-3.3,-1.2,0),90); imp("blacksmith",(3.4,-1.0,0),-90)
imp("house_tall",(-3.4,0.8,0),95); imp("house_small",(3.4,1.0,0),-95)
imp("barn",(0,3.6,0),0)
# plaza props
imp("brazier",(0,0,0)); imp("well",(-1.6,-0.6,0)); imp("market_stall",(1.7,-0.4,0),200)
imp("cart",(1.4,-2.2,0),30); imp("barrel",(-0.9,-2.6,0)); imp("crate",(-1.3,-2.6,0))
imp("haystack",(2.4,-2.6,0))
# greenery & detail
for p,r in [((-4.3,4.2),0),((4.3,4.2),0),((-4.4,-3.6),0),((4.4,-3.4),0)]: imp("tree",(p[0],p[1],0),r)
imp("tree_dead",(-2.4,-3.4,0)); imp("gravestone",(-4.0,-1.6,0)); imp("gravestone",(-3.6,-1.9,0))
imp("lamppost",(-1.0,-4.0,0)); imp("lamppost",(1.0,-4.0,0))
imp("signpost",(1.4,-4.2,0),20)
for x in (-1.0,1.0): imp("fence",(x,-4.6,0),0)
# dusk mood + glows
setup_world(0.32,(0.10,0.12,0.17,1))
sun(2.4,(46,10,42),col=(0.96,0.88,0.80))
sun(1.0,(60,0,225),col=(0.6,0.7,0.95),shadow=False)
plight((0,0,0.9),(1.0,0.5,0.16),300)
plight((-3.2,1.9,0.8),(1.0,0.6,0.25),50); plight((3.0,2.0,0.8),(1.0,0.6,0.25),50)
plight((-1.0,-4.0,1.3),(1.0,0.65,0.3),25); plight((1.0,-4.0,1.3),(1.0,0.65,0.3),25)
isocam(15,(13,-13,12),(0,-0.3,0.6))
render(f"{D}/village_hero2.png",1500,1150)
print("DONE")
