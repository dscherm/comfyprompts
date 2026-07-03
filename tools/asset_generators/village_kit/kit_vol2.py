"""GrimForge Village Vol.2 expansion: ~22 new procedural pieces, same style.
blender -b --python kit_vol2.py"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit_tiles import ALL_TILES  # noqa: E402
from kitlib import Kit  # noqa: E402  (sys.path tweak above)

TITLE = "GrimForge Village Vol.2 — Medieval Expansion Kit (35 pieces)"
AESTHETIC = "medieval"
# Vol.2 used a lighter "bone" (d8d0bc vs the canonical c4bba2) and a brighter
# emissive "window" (2.0 vs the default 1.5); both are preserved as spec overrides
# so regenerated assets are byte-stable. kit_pipeline/productize apply these when
# constructing the Kit.
PALETTE_OVERRIDE = {"bone": "d8d0bc"}
EMISSION_OVERRIDE = {"fire": 2.0, "window": 2.0}

# The primitive helpers are bound to a Kit at build time — by productize/
# kit_pipeline through the PIECES spec adapter (_bind), or by the standalone
# __main__ path below — so every builder call site stays unchanged as bare
# ``box(...)`` / ``join(...)``.
box = cyl = cone = ico = gable = join = None


def _bind(kit):
    """Point the module-level primitive helpers at ``kit``'s bound methods."""
    global box, cyl, cone, ico, gable, join
    box, cyl, cone, ico, gable, join = (
        kit.box, kit.cyl, kit.cone, kit.ico, kit.gable, kit.join
    )


def _crown(P, r, z, n=12, cx=0.0, cy=0.0):
    """Connected round tower-top (QUALITY_RUBRIC §4c): a flared corbel course that
    grows out of the wall, corbel ribs, a recessed wall-walk POCKET, a continuous
    parapet ring, and same-stone merlons with embrasures. Nothing floats."""
    ro = r + 0.09
    m = max(16, n * 2)
    cone(P, m, ro + 0.02, r - 0.01, 0.15, (cx, cy, z + 0.075), "stone")   # flared corbel course
    for i in range(n):                                                   # corbel ribs
        a = math.radians(i * 360 / n)
        rx, ry = cx + math.cos(a) * (ro - 0.04), cy + math.sin(a) * (ro - 0.04)
        box(P, 0.06, 0.11, 0.13, (rx, ry, z + 0.085), "stone", rot=(0, 0, a))
    cyl(P, m, ro - 0.08, 0.05, (cx, cy, z + 0.18), "stone")              # pocket floor
    seg = 2 * math.pi * ro / m * 1.5
    for i in range(m):                                                   # parapet ring
        a = math.radians(i * 360 / m)
        px, py = cx + math.cos(a) * ro, cy + math.sin(a) * ro
        box(P, seg, 0.08, 0.14, (px, py, z + 0.27), "stone", rot=(0, 0, a))
    seg2 = 2 * math.pi * ro / n * 0.52
    for i in range(n):                                                   # merlons
        a = math.radians(i * 360 / n)
        px, py = cx + math.cos(a) * ro, cy + math.sin(a) * ro
        box(P, seg2, 0.1, 0.14, (px, py, z + 0.41), "stone", rot=(0, 0, a))


def _crown_sq(P, w, d, z, cx=0.0, cy=0.0):
    """Connected square tower-top: continuous sill frame with same-stone merlons;
    the tower-box top is the recessed wall-walk pocket (§4c)."""
    for sy in (-1, 1):
        box(P, w + 0.14, 0.12, 0.13, (cx, cy + sy * d / 2, z + 0.065), "stone")
    for sx in (-1, 1):
        box(P, 0.12, d + 0.14, 0.13, (cx + sx * w / 2, cy, z + 0.065), "stone")
    nx = max(3, int(round(w / 0.26)))
    for i in range(0, nx + 1, 2):
        x = -w / 2 + i * w / nx
        for sy in (-1, 1):
            box(P, 0.15, 0.13, 0.16, (cx + x, cy + sy * d / 2, z + 0.205), "stone")
    nd = max(3, int(round(d / 0.26)))
    for i in range(2, nd, 2):
        y = -d / 2 + i * d / nd
        for sx in (-1, 1):
            box(P, 0.13, 0.15, 0.16, (cx + sx * w / 2, cy + y, z + 0.205), "stone")

def windmill():
    P=[]; cyl(P,8,0.6,1.8,(0,0,0.9),"stone"); cyl(P,8,0.5,0.4,(0,0,1.9),"stone_dk")
    cone(P,8,0.62,0,0.5,(0,0,2.25),"shake")               # wood-boarded mill cap
    # sail hub + four LATTICE sails (X, flat/vertical) with white sailcloth,
    # on an axle anchored into the tower (mirrors the kit_village_v1 windmill)
    hz = 1.7
    hub = (0.0, -0.7, hz)
    R = 1.5                                                # sail radius
    box(P,0.1,0.5,0.1,(0,-0.45,hz),"wood_dk")             # axle beam into tower
    cyl(P,8,0.11,0.16,(0,-0.62,hz),"wood_dk",rot=(math.radians(90),0,0))  # hub
    for deg in (45,135):
        an=math.radians(deg)
        sdx,sdz=math.sin(an),math.cos(an)                 # spar direction (XZ)
        box(P,0.05,0.05,R,hub,"wood_dk",rot=(0,an,0))     # central spar
        box(P,0.4,0.02,R*0.92,(hub[0],hub[1]-0.03,hub[2]),"bone",rot=(0,an,0))  # white sailcloth
        for fr in (-0.8,-0.55,-0.3,0.3,0.55,0.8):         # sail battens
            box(P,0.44,0.02,0.04,
                (hub[0]+fr*sdx*(R/2),hub[1]-0.05,hub[2]+fr*sdz*(R/2)),
                "wood_dk",rot=(0,math.radians(deg+90),0))
    box(P,0.3,0.05,0.5,(0,-0.6,0.25),"wood_dk")           # door
    return join(P,"windmill")
def ruined_house():
    P=[]; box(P,1.3,1.1,0.2,(0,0,0.1),"stone")           # floor slab
    box(P,1.3,0.18,0.9,(0,-0.55,0.45),"stone")           # front wall (tall-ish)
    box(P,0.18,1.1,0.7,(-0.6,0,0.35),"stone")            # left wall
    box(P,0.18,0.6,0.4,(0.6,-0.2,0.2),"stone_dk")        # right wall (broken low)
    box(P,0.5,0.18,0.45,(0.2,0.5,0.22),"stone")          # back partial
    for r in [(-0.3,0.2),(0.3,-0.1),(0.0,0.3)]: box(P,0.18,0.18,0.16,(r[0],r[1],0.18),"stone_dk")  # rubble
    box(P,0.5,0.5,0.05,(0.2,0.1,0.06),"moss")
    return join(P,"ruined_house")
def stable():
    P=[]; box(P,1.6,1.1,0.7,(0,0.2,0.35),"wood")
    for x in (-0.7,0.7): box(P,0.1,0.1,0.85,(x,-0.5,0.42),"wood_dk")
    box(P,1.7,1.3,0.5,(0,0,0.85),"thatch"); box(P,1.7,1.3,0.06,(0,0,1.07),"thatch_dk")
    box(P,0.5,0.4,0.4,(0,0.3,0.7),"thatch_dk")           # hay loft hint
    return join(P,"stable")
def guard_tower():
    P=[]
    cyl(P,12,0.55,2.35,(0,0,1.18),"stone")                # round tower body
    cyl(P,12,0.63,0.35,(0,0,0.17),"stone_dk")             # battered foot
    for zz in (0.95,1.6):                                 # arrow-slit windows
        for an in (0,90,180,270):
            a=math.radians(an)
            box(P,0.05,0.12,0.42,(math.cos(a)*0.56,math.sin(a)*0.56,zz),"soot",rot=(0,0,a))
    _crown(P, 0.55, 2.28, n=12)                           # connected crown + guard pocket
    box(P,0.32,0.08,0.6,(0,-0.6,0.3),"wood_dk")           # tower door
    return join(P,"guard_tower")
def stone_bridge():
    P=[]; box(P,1.0,1.6,0.18,(0,0,0.5),"stone")
    for s in (-1,1): box(P,0.12,1.6,0.22,(s*0.44,0,0.62),"stone_dk")   # rails
    cyl(P,12,0.5,1.0,(0,0,0.0),"stone",rot=(math.radians(90),0,0))     # arch under (half buried)
    box(P,1.0,1.0,0.5,(0,0,-0.25),"water")                            # water below
    return join(P,"stone_bridge")
def portcullis():
    """A castle gatehouse: two flanking towers, an arched central gateway with a
    lowered portcullis, machicolations, and a crenellated parapet all across."""
    P=[]
    for s in (-1,1):                                       # two flanking square towers
        box(P,0.6,0.7,2.4,(s*0.82,0,1.2),"stone")
        _crown_sq(P, 0.6, 0.7, 2.4, cx=s*0.82)            # connected crown + guard pocket
    box(P,1.28,0.62,0.9,(0,0,1.75),"stone")               # central gate block (over the opening)
    _crown_sq(P, 1.28, 0.56, 2.2)                          # wall-walk parapet linking the towers
    box(P,0.7,0.66,1.3,(0,0,0.65),"soot")                  # dark gateway passage
    for s in (-1,1):
        box(P,0.12,0.66,1.3,(s*0.41,0,0.65),"stone_dk")    # gateway jambs
    box(P,0.94,0.66,0.14,(0,0,1.3),"stone_dk")             # lintel over the jambs
    for s in (-1,1):                                       # arched (chamfered) head
        box(P,0.26,0.66,0.26,(s*0.29,0,1.2),"stone_dk",rot=(0,math.radians(s*45),0))
    for x in (-0.26,-0.09,0.09,0.26): box(P,0.05,0.06,1.15,(x,-0.28,0.7),"iron")  # portcullis bars
    for z in (0.22,0.6,1.0,1.28): box(P,0.6,0.06,0.05,(0,-0.28,z),"iron")         # grille rails
    return join(P,"portcullis")
def wall_ruined():
    P=[]; box(P,1.0,0.4,0.5,(0,0,0.25),"stone")
    box(P,0.5,0.4,0.35,(-0.25,0,0.6),"stone")            # remaining higher chunk
    for r in [(0.35,0.1),(0.2,-0.1),(0.45,0.0)]: box(P,0.16,0.16,0.14,(r[0],r[1],0.1),"stone_dk")
    box(P,0.9,0.42,0.04,(0,0,0.02),"moss")
    return join(P,"wall_ruined")
def palisade():
    P=[]; box(P,1.0,0.18,0.7,(0,0,0.35),"wood")
    for x in [-0.4,-0.2,0,0.2,0.4]: cone(P,6,0.09,0.0,0.25,(x,0,0.82),"wood_dk")  # spikes
    box(P,1.0,0.06,0.06,(0,0.08,0.5),"wood_dk")
    return join(P,"palisade")
def fountain():
    P=[]; cyl(P,8,0.6,0.3,(0,0,0.15),"stone"); cyl(P,8,0.5,0.06,(0,0,0.3),"water")
    cyl(P,8,0.16,0.6,(0,0,0.55),"stone_dk"); cyl(P,8,0.26,0.08,(0,0,0.8),"stone")
    cyl(P,6,0.06,0.1,(0,0,0.9),"water")
    return join(P,"fountain")
def wood_pile():
    P=[]
    for i,(y,z) in enumerate([(-0.2,0.12),(0,0.12),(0.2,0.12),(-0.1,0.32),(0.1,0.32),(0,0.5)]):
        cyl(P,8,0.12,0.7,(0,y,z),"wood" if i%2 else "wood_dk",rot=(0,math.radians(90),0))
    return join(P,"wood_pile")
def torch():
    P=[]; cyl(P,6,0.05,1.2,(0,0,0.6),"wood"); cyl(P,8,0.12,0.14,(0,0,1.22),"iron")
    cone(P,6,0.1,0,0.22,(0,0,1.36),"fire")
    return join(P,"torch")
def banner():
    P=[]; cyl(P,6,0.05,1.6,(0,0,0.8),"wood"); box(P,0.04,0.04,0.04,(0,0,1.6),"gold")
    box(P,0.35,0.03,0.7,(0.2,0,1.2),"flag"); box(P,0.18,0.04,0.18,(0.2,0,1.25),"gold")
    return join(P,"banner")
def stocks():
    P=[]
    for x in (-0.35,0.35): box(P,0.08,0.12,0.7,(x,0,0.35),"wood")
    box(P,0.8,0.14,0.12,(0,0,0.6),"wood_dk"); box(P,0.8,0.14,0.06,(0,0,0.5),"wood")
    for hx in (-0.18,0,0.18): cyl(P,8,0.06,0.16,(hx,0,0.55),"wood_dk",rot=(math.radians(90),0,0))
    return join(P,"stocks")
def anvil():
    P=[]; cyl(P,8,0.2,0.3,(0,0,0.15),"wood")             # block
    box(P,0.18,0.34,0.1,(0,0,0.35),"iron"); box(P,0.1,0.5,0.08,(0,0,0.43),"iron")
    cone(P,8,0.08,0.0,0.14,(0,-0.28,0.5),"iron",rot=(math.radians(90),0,0))  # horn
    return join(P,"anvil")
def trough():
    P=[]; box(P,0.9,0.4,0.3,(0,0,0.15),"wood")
    box(P,0.8,0.32,0.06,(0,0,0.27),"water")
    for x in (-0.42,0.42): box(P,0.08,0.4,0.34,(x,0,0.17),"wood_dk")
    return join(P,"trough")
def weapon_rack():
    P=[]; box(P,0.7,0.18,0.1,(0,0,0.05),"wood")
    for x in (-0.28,0.28): box(P,0.06,0.06,0.9,(x,0,0.45),"wood")
    box(P,0.7,0.06,0.06,(0,0,0.85),"wood_dk")
    for x in (-0.18,0.0,0.18): cyl(P,6,0.02,0.9,(x,0,0.45),"iron")     # spears
    for x in (-0.18,0.0,0.18): cone(P,6,0.04,0,0.12,(x,0,0.92),"iron")
    return join(P,"weapon_rack")
def gibbet():
    P=[]; cyl(P,6,0.06,1.8,(0,0,0.9),"wood_dk"); box(P,0.7,0.08,0.08,(0.25,0,1.78),"wood_dk")
    for z in (1.0,1.3,1.6): box(P,0.3,0.3,0.04,(0.4,0,z),"iron")
    for c in [(-0.13,-0.13),(0.13,-0.13),(-0.13,0.13),(0.13,0.13)]: box(P,0.04,0.04,0.6,(0.4+c[0],c[1],1.3),"iron")
    return join(P,"gibbet")
def bone_pile():
    P=[]
    for p in [(-0.15,0,0.1),(0.15,0.05,0.1),(0,-0.1,0.12),(0.05,0.12,0.22)]: ico(P,0.11,p,"bone")
    for r in [(-0.2,0.1,40),(0.18,-0.05,-30)]: cyl(P,6,0.03,0.4,(r[0],r[1],0.06),"bone",rot=(0,math.radians(r[2]),math.radians(20)))
    return join(P,"bone_pile")
def crypt():
    P=[]; box(P,1.2,1.0,0.7,(0,0,0.35),"stone")
    box(P,0.5,0.2,0.6,(0,-0.5,0.3),"stone_dk")           # doorway frame
    box(P,0.34,0.1,0.5,(0,-0.52,0.25),"wood_dk")         # door
    cone(P,4,0.45,0,0.3,(0,0,0.85),"stone_dk",rot=(0,0,math.radians(45)))
    box(P,0.06,0.06,0.3,(0,0,0.98),"stone"); box(P,0.18,0.06,0.06,(0,0,1.06),"stone")  # cross
    box(P,0.7,0.5,0.05,(0,0.2,0.05),"moss")
    return join(P,"crypt")
def pine():
    P=[]; cyl(P,6,0.08,0.5,(0,0,0.25),"wood_dk")
    cone(P,8,0.45,0,0.55,(0,0,0.6),"pine"); cone(P,8,0.34,0,0.5,(0,0,0.95),"pine"); cone(P,8,0.22,0,0.45,(0,0,1.3),"pine")
    return join(P,"pine")
def stump():
    P=[]; cyl(P,8,0.22,0.35,(0,0,0.17),"wood"); cyl(P,8,0.2,0.05,(0,0,0.36),"wood_dk")
    cyl(P,6,0.05,0.4,(0.18,0.08,0.2),"wood_dk",rot=(0,math.radians(60),0))
    return join(P,"stump")
def rocks():
    P=[]; ico(P,0.3,(0,0,0.18),"stone"); ico(P,0.2,(0.3,0.1,0.12),"stone_dk"); ico(P,0.16,(-0.22,0.18,0.1),"stone")
    return join(P,"rocks")
def bush():
    P=[]
    for c,r in [((-0.12,0,0.16),0.18),((0.12,0.05,0.16),0.18),((0,0.1,0.2),0.2)]: ico(P,r,c,"leaf")
    ico(P,0.1,(0,-0.05,0.28),"leaf_dk")
    return join(P,"bush")

BUILD=[("windmill",windmill),("ruined_house",ruined_house),("stable",stable),("guard_tower",guard_tower),
 ("stone_bridge",stone_bridge),("portcullis",portcullis),("wall_ruined",wall_ruined),("palisade",palisade),
 ("fountain",fountain),("wood_pile",wood_pile),("torch",torch),("banner",banner),("stocks",stocks),
 ("anvil",anvil),("trough",trough),("weapon_rack",weapon_rack),("gibbet",gibbet),("bone_pile",bone_pile),
 ("crypt",crypt),("pine",pine),("stump",stump),("rocks",rocks),("bush",bush)]

def _piece(fn):
    """Adapt a zero-arg BUILD builder into a spec builder ``fn(kit) -> obj``."""
    def build(kit):
        _bind(kit)
        return fn()
    return build


#: Spec interface consumed by kit_pipeline.py / productize.py — expansion pieces
#: plus the shared grid-modular tile set (ground / paths / roads).
PIECES = [(nm, _piece(fn)) for nm, fn in BUILD] + ALL_TILES


def _main():
    """Standalone catalog build (``blender -b --python kit_vol2.py -- <dir>``)."""
    import bpy
    import mathutils
    from kitlib import PALETTE
    from kitlib import hex_to_rgba as Hx

    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    D = argv[0] if argv else os.path.dirname(os.path.abspath(__file__))
    glbdir = f"{D}/kit2_glb"
    os.makedirs(glbdir, exist_ok=True)
    k = Kit(
        palette={**PALETTE, **PALETTE_OVERRIDE},
        emission={"fire": 2.0, "window": 2.0, **EMISSION_OVERRIDE},
        reset_scene=True,
    )
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
        o.location = (col * 2.4 - 6, -row * 2.4 + 4, 0)
        placed.append(o)

    box([], 40, 40, 0.1, (0, 0, -0.06), "stone_dk")
    sun = bpy.data.objects.new("S", bpy.data.lights.new("S", "SUN"))
    sc.collection.objects.link(sun)
    sun.data.energy = 3.0
    sun.data.angle = math.radians(5)
    sun.rotation_euler = (math.radians(52), math.radians(10), math.radians(35))
    fl = bpy.data.objects.new("F", bpy.data.lights.new("F", "SUN"))
    sc.collection.objects.link(fl)
    fl.data.energy = 1.1
    fl.data.use_shadow = False
    fl.rotation_euler = (math.radians(62), 0, math.radians(215))
    sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[1].default_value = 0.55
    bg.inputs[0].default_value = Hx("8a96a2")
    sc.view_settings.view_transform = "Standard"
    cam = bpy.data.objects.new("C", bpy.data.cameras.new("C"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 16
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
    sc.render.filepath = f"{D}/kit2_catalog.png"
    bpy.ops.render.render(write_still=True)
    print("VOL2 DONE pieces:", len(BUILD))


if __name__ == "__main__":
    _main()
