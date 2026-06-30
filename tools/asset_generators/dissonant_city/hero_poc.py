"""DissonantDreams retro-futurist city kit — HERO PoC (lock the look).
Procedural flat-shaded low-poly, DissonantDreams palette (hot pink / cyan / black /
cream) + neon emissive + dusk mood. Headless Blender (blender-mcp is down).
Run: blender --background --python hero_poc.py
"""
import bpy, math, mathutils

OUT = r"C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/0e5e1c40-e596-49a6-a43d-bfbe573d38ce/scratchpad/dissonant_city_hero.png"

# --- DissonantDreams palette ---
PINK   = "E8186C"; CYAN = "1BC6D6"; BLACK = "0D0D18"; CREAM = "EDE3C4"
DPINK  = "8A1247"; DCYAN= "0E6B75"; ORANGE= "FF8A3C"; PURPLE = "3A1E5C"


def Hx(h, a=1.0):
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4)) + (a,)


def mat(name, rgb, emit=None, emit_str=0.0, rough=0.85, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgb
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit is not None:
        b.inputs["Emission Color"].default_value = emit
        b.inputs["Emission Strength"].default_value = emit_str
    return m


def box(sx, sy, sz, loc, m, smooth=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.scale = (sx, sy, sz)
    o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = smooth
    return o


def cyl(r, depth, loc, m, verts=8, smooth=False):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, vertices=verts)
    o = bpy.context.active_object; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = smooth
    return o


def cone(r1, r2, depth, loc, m, verts=8):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, location=loc, vertices=verts)
    o = bpy.context.active_object; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = False
    return o


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# materials
M_DARK = mat("dark", Hx(BLACK), rough=0.9)
M_SLAB = mat("slab", Hx(PURPLE), rough=0.95)
M_PINK = mat("pink", Hx(PINK), rough=0.6)
M_CYAN = mat("cyan", Hx(CYAN), rough=0.6)
M_CREAM = mat("cream", Hx(CREAM), rough=0.8)
M_CHROME = mat("chrome", Hx("C8CEDA"), rough=0.18, metal=1.0)
M_NEON_P = mat("neonP", Hx(PINK), emit=Hx(PINK), emit_str=14, rough=0.4)
M_NEON_C = mat("neonC", Hx(CYAN), emit=Hx(CYAN), emit_str=14, rough=0.4)
M_WIN = mat("win", Hx(CREAM), emit=Hx("FFE9B0"), emit_str=6, rough=0.5)

# ground plaza (dark) + neon grid stripes
box(24, 24, 0.2, (0, 0, -0.1), M_DARK)
for x in range(-9, 10, 3):
    box(0.06, 22, 0.02, (x, 0, 0.01), M_NEON_C)
for y in range(-9, 10, 3):
    box(22, 0.06, 0.02, (0, y, 0.01), M_NEON_P)

# --- PIECE TYPES (the kit candidates) ---
# 1. Tapered tower (cyan body, pink neon bands, chrome cap)
def tower(loc, h=8, body=M_CYAN, band=M_NEON_P):
    x, y, _ = loc
    box(2.2, 2.2, h*0.5, (x, y, h*0.25), body)
    box(1.6, 1.6, h*0.28, (x, y, h*0.5 + h*0.14), body)
    for i in range(1, 4):
        box(2.35, 2.35, 0.12, (x, y, h*0.5 * i/3.2), band)
    cyl(1.0, 0.5, (x, y, h*0.64), M_CHROME)
    cone(0.9, 0.05, 1.6, (x, y, h*0.64 + 1.0), M_NEON_C)        # spire
    # window slits
    for zz in (1.2, 2.6, 4.0):
        box(2.25, 0.5, 0.35, (x, y, zz), M_WIN)
tower((-6, 5, 0), h=9, body=M_CYAN, band=M_NEON_P)
tower((6, 4, 0), h=7, body=M_SLAB, band=M_NEON_C)

# 2. Domed building (cream slab + chrome dome + pink ring)
def dome(loc):
    x, y, _ = loc
    cyl(3.0, 2.0, (x, y, 1.0), M_CREAM, verts=10)
    cyl(3.15, 0.2, (x, y, 2.0), M_NEON_P, verts=10)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=2.6, location=(x, y, 2.0), segments=12, ring_count=6)
    d = bpy.context.active_object; d.scale = (1, 1, 0.55); d.data.materials.append(M_CHROME)
    for p in d.data.polygons: p.use_smooth = True
    for ang in range(0, 360, 45):
        bx = x + 2.7*math.cos(math.radians(ang)); by = y + 2.7*math.sin(math.radians(ang))
        box(0.3, 0.3, 1.8, (bx, by, 0.9), M_DARK)
dome((0, 6.5, 0))

# 3. Low retro slab building w/ neon sign + curved front
def slabbldg(loc, w=4, c=M_PINK, sign=M_NEON_C):
    x, y, _ = loc
    box(w, 2.6, 1.5, (x, y, 0.75), c)
    box(w*0.92, 2.4, 0.3, (x, y, 1.5), M_DARK)        # roof lip
    for i in range(-1, 2):                              # window band
        box(0.9, 0.05, 0.8, (x + i*1.3, y - 1.32, 0.9), M_WIN)
    box(w*0.5, 0.12, 0.7, (x, y + 1.34, 2.1), sign)   # rooftop neon sign
    box(0.12, 0.12, 0.9, (x, y + 1.34, 1.5), M_CHROME)
slabbldg((-4, -1, 0), w=4.5, c=M_PINK, sign=M_NEON_C)
slabbldg((4.5, -1.5, 0), w=3.5, c=M_SLAB, sign=M_NEON_P)

# 4. Skybridge between the two towers
box(0.4, 9.0, 0.4, (0, 4.5, 5.0), M_CHROME)
box(0.5, 9.2, 0.1, (0, 4.5, 5.22), M_NEON_C)

# 5. Hover-cars (chrome capsule + neon underglow)
def car(loc, rot=0, glow=M_NEON_P):
    x, y, _ = loc
    o = box(1.2, 0.55, 0.35, (x, y, 0.5), M_CHROME)
    o.rotation_euler.z = math.radians(rot)
    g = box(1.0, 0.4, 0.05, (x, y, 0.32), glow); g.rotation_euler.z = math.radians(rot)
    w = box(0.7, 0.45, 0.18, (x, y, 0.66), M_WIN); w.rotation_euler.z = math.radians(rot)
car((-1.5, 1.0, 0), 20, M_NEON_C)
car((2.0, 1.6, 0), -30, M_NEON_P)
car((0.4, -3.0, 0), 80, M_NEON_C)

# 6. Street pylons / neon posts
for p, gm in [((-2.0, 2.0), M_NEON_P), ((2.0, 2.0), M_NEON_C), ((-2.0, -2.5), M_NEON_C), ((2.0, -2.5), M_NEON_P)]:
    cyl(0.12, 2.4, (p[0], p[1], 1.2), M_DARK)
    box(0.5, 0.12, 0.5, (p[0], p[1], 2.2), gm)

# --- DUSK / NEON MOOD ---
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = Hx("17091F"); bg.inputs[1].default_value = 0.25
# big cream sun low on the horizon
bpy.ops.mesh.primitive_circle_add(radius=7, fill_type='NGON', location=(0, 22, 7),
                                  rotation=(math.radians(90), 0, 0))
sun_disc = bpy.context.active_object
sun_disc.data.materials.append(mat("sun", Hx(CREAM), emit=Hx("FFD27A"), emit_str=8))

sc.view_settings.view_transform = 'Standard'

def sun_lamp(e, rot, c, sh=True):
    s = bpy.data.objects.new("S", bpy.data.lights.new("S", 'SUN')); sc.collection.objects.link(s)
    s.data.energy = e; s.data.angle = math.radians(6); s.data.color = c; s.data.use_shadow = sh
    s.rotation_euler = tuple(math.radians(a) for a in rot)
sun_lamp(2.0, (62, 8, 8), (1.0, 0.78, 0.62))         # warm key
sun_lamp(1.4, (58, 0, 210), (0.45, 0.85, 0.95), False)  # cyan fill
sun_lamp(1.0, (50, 0, 30), (1.0, 0.35, 0.7), False)     # pink rim

cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 22; cam.location = (17, -17, 13)
look = mathutils.Vector((0, 1.0, 2.0)) - mathutils.Vector(cam.location)
cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()

for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng; break
    except Exception:
        continue
try:
    sc.eevee.taa_render_samples = 64
except Exception:
    pass
sc.render.resolution_x = 1500; sc.render.resolution_y = 1100
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("DISSONANT CITY HERO DONE ->", OUT)
