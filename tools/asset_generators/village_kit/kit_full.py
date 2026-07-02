"""Full GrimForge medieval village kit: ~24 procedural pieces, solid colors,
Tudor detail. Builds each, exports GLB, lays out a catalog, renders it.
blender -b --python kit_full.py"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit_tiles import ALL_TILES  # noqa: E402
from kitlib import Kit  # noqa: E402  (sys.path tweak above)

TITLE = "GrimForge Village Vol.1 — Medieval Village Kit (40 pieces)"
AESTHETIC = "medieval"

# The GrimForge primitive vocabulary lives in kitlib. kit_full uses the canonical
# palette + default emission (fire=2.0, window=1.5) verbatim, so regenerated
# assets are identical to the originals. The primitive helpers are bound to a Kit
# at build time — by productize/kit_pipeline through the PIECES spec adapter
# (_bind), or by the standalone __main__ path below — so every builder call site
# stays unchanged as bare ``box(...)`` / ``join(...)``.
box = cyl = cone = gable = join = None


def _bind(kit):
    """Point the module-level primitive helpers at ``kit``'s bound methods."""
    global box, cyl, cone, gable, join
    box, cyl, cone, gable, join = kit.box, kit.cyl, kit.cone, kit.gable, kit.join

# ---------- builders ----------
def house(name,W=1.35,Dd=1.15,floors=1,jetty=True,roof="slate",wall="plaster",framing=True,chim=True,sign=None):
    P=[]; bh=0.55
    box(P,W,Dd,bh,(0,0,bh/2),"stone")
    UW,UD=(W+0.22,Dd+0.22) if jetty else (W,Dd)
    z=bh
    for fl in range(floors):
        box(P,UW,UD,0.55,(0,0,z+0.275),wall)
        if jetty and fl==0: box(P,UW+0.02,UD+0.02,0.05,(0,0,z),"beam")
        fy=-UD/2-0.01
        if framing:
            for x in (-UW/2+0.06,0,UW/2-0.06): box(P,0.05,0.04,0.5,(x,fy,z+0.27),"beam")
            box(P,UW,0.04,0.05,(0,fy,z+0.5),"beam"); box(P,UW,0.04,0.05,(0,fy,z+0.05),"beam")
            for s in (-1,1): box(P,0.05,0.04,0.32,(s*UW*0.26,fy,z+0.2),"beam",rot=(0,math.radians(s*32),0))
        for wx in (-0.3,0.3):
            box(P,0.2,0.05,0.2,(wx,fy+0.01,z+0.3),"wood_dk"); box(P,0.14,0.05,0.14,(wx,fy+0.03,z+0.3),"window")
        z+=0.55
    box(P,0.26,0.05,0.46,(0,-Dd/2-0.01,0.23),"wood_dk"); box(P,0.18,0.05,0.36,(0,-Dd/2-0.02,0.2),"wood")
    gable(P,UW,UD,0.7,(0,0,z),roof,over=0.18)
    box(P,0.08,UD+0.36,0.07,(0,0,z+0.7),"wood_dk")   # ridge (along Y - fixed)
    if chim:
        box(P,0.2,0.2,z+0.5,(W*0.42,0.34,(z+0.5)/2),"stone"); box(P,0.26,0.26,0.08,(W*0.42,0.34,z+0.5),"stone_dk")
    if sign:
        box(P,0.04,0.04,0.3,(W*0.5,-Dd*0.4,0.95),"beam"); box(P,0.28,0.04,0.18,(W*0.5+0.16,-Dd*0.4,0.78),sign)
    return join(P,name)
def church():
    P=[]; box(P,1.3,2.2,0.9,(0,0,0.45),"stone")
    gable(P,1.3,2.2,0.85,(0,0,0.9),"slate",over=0.2)
    box(P,0.55,0.55,1.9,(0,-1.0,0.95),"stone")           # tower
    cone(P,4,0.42,0,0.6,(0,-1.0,2.2),"slate",rot=(0,0,math.radians(45)))
    box(P,0.06,0.06,0.34,(0,-1.0,2.6),"gold"); box(P,0.22,0.06,0.06,(0,-1.0,2.66),"gold")  # cross
    for yy in (-0.2,0.5,1.0): box(P,0.18,0.05,0.5,(0.66,yy,0.7),"window")
    box(P,0.3,0.06,0.55,(0,1.11,0.5),"wood_dk")
    return join(P,"church")
def barn():
    P=[]; box(P,1.7,2.4,1.1,(0,0,0.55),"wood")
    for x in (-0.7,0,0.7): box(P,0.08,2.42,0.08,(x,0,0.8),"wood_dk")
    gable(P,1.7,2.4,0.95,(0,0,1.1),"thatch",over=0.2)
    box(P,0.9,0.06,1.0,(0,-1.21,0.5),"wood_dk")          # big doors
    return join(P,"barn")
def tower():
    P=[]; cyl(P,8,0.6,2.1,(0,0,1.05),"stone")
    for k in range(8):
        a=math.radians(k*45+22.5); box(P,0.2,0.2,0.28,(math.cos(a)*0.55,math.sin(a)*0.55,2.2),"stone_dk")
    box(P,0.28,0.05,0.32,(0,-0.6,1.2),"window"); box(P,0.3,0.06,0.5,(0,-0.6,0.25),"wood_dk")
    return join(P,"tower")
def blacksmith():
    P=[]; box(P,1.3,1.2,0.75,(0,0,0.375),"stone")
    box(P,1.3,1.2,0.4,(0,0,0.95),"wood")
    gable(P,1.3,1.2,0.5,(0,0,1.15),"slate",over=0.16)
    box(P,0.32,0.32,1.7,(0.5,0.4,0.85),"stone"); box(P,0.2,0,0.3,(0.5,0.4,1.75),"fire")  # forge chimney glow
    box(P,0.3,0.5,0.3,(0,-0.5,0.9),"iron")              # forge opening side
    cyl(P,8,0.12,0.16,(-0.45,-0.5,0.55),"iron"); box(P,0.18,0.32,0.1,(-0.45,-0.5,0.68),"iron")  # anvil
    return join(P,"blacksmith")

def wall_seg():
    P=[]; box(P,1.0,0.4,0.9,(0,0,0.45),"stone")           # wall body
    box(P,1.0,0.4,0.06,(0,0,0.93),"stone_dk")             # walkway cap course
    for sy in (-1,1):                                     # crenellated parapet on BOTH edges
        for mx in (-0.34,0.0,0.34):
            box(P,0.22,0.08,0.22,(mx,sy*0.16,1.05),"stone_dk")   # merlons (gaps between)
    return join(P,"wall")
def wall_gate():
    P=[]
    for s in (-1,1):                                      # two gate towers
        box(P,0.5,0.6,1.9,(s*0.7,0,0.95),"stone")
        box(P,0.56,0.66,0.06,(s*0.7,0,1.93),"stone_dk")   # tower cap course
        for mx in (-0.15,0.0,0.15):                       # tower-top merlons (stonework)
            box(P,0.13,0.16,0.2,(s*0.7+mx,0,2.06),"stone_dk")
    box(P,1.5,0.62,0.3,(0,0,1.55),"stone")                # lintel spanning tower to tower
    box(P,1.5,0.66,0.06,(0,0,1.72),"stone_dk")            # lintel cap course
    for mx in (-0.5,-0.25,0.0,0.25,0.5):                  # battlement over the gate
        box(P,0.16,0.16,0.18,(mx,0,1.83),"stone_dk")
    box(P,0.9,0.32,1.35,(0,0,0.675),"wood_dk")            # timber gate (under the lintel)
    for gz in (0.35,0.85,1.2): box(P,0.94,0.34,0.05,(0,0,gz),"iron")  # iron braces
    return join(P,"wall_gate")
def wall_corner():
    P=[]
    box(P,0.4,1.0,0.9,(0.3,0,0.45),"stone")               # arm along Y
    box(P,1.0,0.4,0.9,(0,0.3,0.45),"stone")               # arm along X
    box(P,0.5,0.5,1.15,(0,0,0.575),"stone")               # corner tower
    box(P,0.56,0.56,0.06,(0,0,1.18),"stone_dk")           # tower cap
    for mx,my in ((-0.15,-0.15),(0.15,-0.15),(-0.15,0.15),(0.15,0.15)):
        box(P,0.14,0.14,0.2,(mx,my,1.3),"stone_dk")       # corner-tower merlons
    for yy in (-0.3,0.0,0.3):                             # parapet along the +Y arm outer edge
        box(P,0.1,0.18,0.2,(0.46,yy,1.05),"stone_dk")
    for xx in (0.0,0.3):                                  # parapet along the +X arm outer edge
        box(P,0.18,0.1,0.2,(xx,0.46,1.05),"stone_dk")
    return join(P,"wall_corner")

def tile(name,c,h=0.1):
    P=[]; box(P,1.0,1.0,h,(0,0,h/2-h),c); return join(P,name)
def path_straight():
    P=[]; box(P,1.0,1.0,0.08,(0,0,-0.04),"dirt")
    for y in (-0.3,0.0,0.3): box(P,0.5,0.22,0.05,(0,y,0.0),"cobble")
    return join(P,"path_straight")
def path_corner():
    P=[]; box(P,1.0,1.0,0.08,(0,0,-0.04),"dirt")
    for a,b in [(-0.3,0),(0,0),(0,-0.3)]: box(P,0.34,0.34,0.05,(a,b,0.0),"cobble")
    return join(P,"path_corner")

def well():
    P=[]; cyl(P,8,0.5,0.5,(0,0,0.25),"stone"); cyl(P,8,0.36,0.04,(0,0,0.5),"stone_dk")
    cyl(P,12,0.3,0.16,(0,0,0.43),"soot")                 # black shaft hole (always black)
    for s in (-1,1): box(P,0.08,0.08,0.85,(s*0.42,0,0.65),"wood")
    box(P,0.95,0.08,0.08,(0,0,1.08),"wood"); cyl(P,6,0.05,0.5,(0,0,0.95),"wood",rot=(math.radians(90),0,0))
    gable(P,1.0,0.7,0.34,(0,0,1.12),"thatch",over=0.14); box(P,0.14,0.14,0.16,(0,0,0.66),"wood_dk")
    return join(P,"well")
def market_stall():
    P=[]
    for sx in (-0.5,0.5):
        for sy in (-0.35,0.35): box(P,0.07,0.07,0.78,(sx,sy,0.39),"wood")
    box(P,1.12,0.46,0.12,(0,0.16,0.56),"wood")
    box(P,1.3,0.9,0.06,(0,-0.05,0.95),"cloth_r",rot=(math.radians(14),0,0))
    for x in (-0.42,-0.14,0.14,0.42): box(P,0.12,0.9,0.06,(x,-0.05,0.96),"cloth")
    box(P,0.2,0.2,0.2,(-0.3,0.18,0.72),"wood_dk"); cyl(P,8,0.16,0.34,(0.4,0.18,0.69),"wood_dk")
    return join(P,"market_stall")
def barrel():
    P=[]; cyl(P,10,0.22,0.5,(0,0,0.25),"wood"); cyl(P,10,0.24,0.06,(0,0,0.13),"iron"); cyl(P,10,0.24,0.06,(0,0,0.37),"iron")
    return join(P,"barrel")
def crate():
    P=[]; box(P,0.4,0.4,0.4,(0,0,0.2),"wood")
    for e in [(-0.2,0,0.2),(0.2,0,0.2)]: box(P,0.04,0.42,0.42,e,"wood_dk")
    box(P,0.42,0.42,0.04,(0,0,0.4),"wood_dk")
    return join(P,"crate")
def fence():
    P=[]
    for x in (-0.4,0.4): box(P,0.08,0.08,0.6,(x,0,0.3),"wood")
    for z in (0.2,0.45): box(P,0.9,0.05,0.06,(0,0,z),"wood_dk")
    return join(P,"fence")
def tree():
    P=[]; cyl(P,6,0.1,0.7,(0,0,0.35),"wood")
    cone(P,7,0.5,0,0.7,(0,0,0.95),"leaf"); cone(P,7,0.38,0,0.55,(0,0,1.35),"leaf_dk")
    return join(P,"tree")
def tree_dead():
    P=[]; cyl(P,6,0.11,1.3,(0,0,0.65),"wood_dk")
    for s,zz,an in [(-1,1.0,40),(1,0.8,-35),(-1,1.3,25)]:
        cyl(P,5,0.05,0.5,(s*0.18,0,zz),"wood_dk",rot=(0,math.radians(an),0))
    return join(P,"tree_dead")
def lamppost():
    P=[]; cyl(P,6,0.05,1.3,(0,0,0.65),"iron"); box(P,0.18,0.18,0.18,(0,0,1.35),"iron"); box(P,0.12,0.12,0.12,(0,0,1.35),"window")
    return join(P,"lamppost")
def brazier():
    P=[]; cone(P,6,0.2,0.1,0.6,(0,0,0.3),"iron"); cyl(P,8,0.27,0.16,(0,0,0.62),"iron")
    cone(P,6,0.2,0,0.34,(0,0,0.82),"fire"); cone(P,5,0.11,0,0.26,(0.06,0,0.9),"fire")
    return join(P,"brazier")
def signpost():
    P=[]; cyl(P,6,0.05,1.0,(0,0,0.5),"wood"); box(P,0.4,0.05,0.18,(0.15,0,0.85),"wood_dk")
    return join(P,"signpost")
def cart():
    P=[]; box(P,0.9,0.5,0.18,(0,0,0.32),"wood"); box(P,0.9,0.5,0.22,(0,0,0.45),"wood_dk")
    for sx in (-0.32,0.32): cyl(P,10,0.22,0.08,(sx,-0.28,0.22),"wood_dk",rot=(math.radians(90),0,0))
    box(P,0.06,0.5,0.06,(0.0,0.4,0.5),"wood")
    return join(P,"cart")
def haystack():
    P=[]; cyl(P,8,0.5,0.5,(0,0,0.25),"thatch"); cone(P,8,0.5,0,0.5,(0,0,0.7),"thatch_dk")
    return join(P,"haystack")
def gravestone():
    P=[]; box(P,0.34,0.1,0.5,(0,0,0.25),"stone_dk"); box(P,0.34,0.12,0.12,(0,0,0.48),"stone")
    return join(P,"gravestone")

BUILD=[
 ("cottage",lambda:house("cottage")),
 ("house_small",lambda:house("house_small",jetty=False,roof="thatch",chim=True)),
 ("house_tall",lambda:house("house_tall",W=1.1,Dd=1.0,floors=2,roof="slate")),
 ("tavern",lambda:house("tavern",W=1.6,Dd=1.3,roof="thatch",sign="gold")),
 ("church",church),("barn",barn),("tower",tower),("blacksmith",blacksmith),
 ("wall",wall_seg),("wall_gate",wall_gate),("wall_corner",wall_corner),
 ("ground_grass",lambda:tile("ground_grass","grass")),("ground_dirt",lambda:tile("ground_dirt","dirt")),
 ("path_straight",path_straight),("path_corner",path_corner),
 ("well",well),("market_stall",market_stall),("barrel",barrel),("crate",crate),
 ("fence",fence),("tree",tree),("tree_dead",tree_dead),("lamppost",lamppost),
 ("brazier",brazier),("signpost",signpost),("cart",cart),("haystack",haystack),("gravestone",gravestone),
]

def _piece(fn):
    """Adapt a zero-arg BUILD builder into a spec builder ``fn(kit) -> obj``."""
    def build(kit):
        _bind(kit)
        return fn()
    return build


#: Spec interface consumed by kit_pipeline.py / productize.py. The BUILD kit
#: plus the shared grid-modular tile set (ground / paths / roads).
PIECES = [(nm, _piece(fn)) for nm, fn in BUILD] + ALL_TILES


def _main():
    """Standalone catalog build (``blender -b --python kit_full.py -- <dir>``)."""
    import bpy
    import mathutils

    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    D = argv[0] if argv else os.path.dirname(os.path.abspath(__file__))
    glbdir = f"{D}/kit_glb"
    os.makedirs(glbdir, exist_ok=True)
    k = Kit(reset_scene=True)
    sc = k.scene
    _bind(k)
    placed = []
    for i, (nm, fn) in enumerate(BUILD):
        o = fn()
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.export_scene.gltf(
            filepath=f"{glbdir}/{nm}.glb", export_format="GLB", use_selection=True
        )
        col, row = i % 6, i // 6
        o.location = (col * 2.4 - 6, -row * 2.4 + 5, 0)
        placed.append(o)

    box([], 40, 40, 0.1, (0, 0, -0.06), "dirt")   # catalog ground + lighting
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sc.collection.objects.link(sun)
    sun.data.energy = 3.0
    sun.data.angle = math.radians(5)
    sun.rotation_euler = (math.radians(52), math.radians(10), math.radians(35))
    fill = bpy.data.objects.new("F", bpy.data.lights.new("F", "SUN"))
    sc.collection.objects.link(fill)
    fill.data.energy = 1.1
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(62), 0, math.radians(215))
    sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[1].default_value = 0.55
    bg.inputs[0].default_value = (0.55, 0.6, 0.66, 1)
    sc.view_settings.view_transform = "Standard"
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 17
    cam.location = (0, -12, 16)
    look = mathutils.Vector((0, 0, 0)) - mathutils.Vector(cam.location)
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    sc.render.engine = "BLENDER_EEVEE"
    try:
        sc.eevee.taa_render_samples = 48
    except Exception:
        pass
    sc.render.resolution_x = 1500
    sc.render.resolution_y = 1100
    sc.render.filepath = f"{D}/kit_catalog.png"
    bpy.ops.render.render(write_still=True)
    print("DONE pieces:", len(BUILD))


if __name__ == "__main__":
    _main()
