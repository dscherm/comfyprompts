"""Soapbox Kart Kit — procedural low-poly racing kit (karts, track, hazards, pickups).
Flat-shaded solid cartoon colors, grid-modular (2u track tiles). Look locked to the
soapbox_style hero concept (red soapbox racers, cones, tire walls, checkered gates).
Headless: blender --background --python build_pieces.py

Mascot racer characters are produced separately (mascot_to_3d.py -> Hunyuan3D).
"""
import bpy, math, os

OUT = r"D:/Projects/comfyui-toolchain/products/soapbox_kart_kit_v1"
for sub in ("models_glb", "models_obj", "models_fbx"):
    os.makedirs(f"{OUT}/{sub}", exist_ok=True)

# bright cartoon racing palette
RED="D2372C"; ORANGE="F07B24"; YELLOW="F5C518"; TEAL="17A5B5"; WHITE="EFEAE0"
BLACK="15151C"; BROWN="8A5A2B"; GREY="8A9099"; DKGREY="4A4E57"; GREEN="3FA34D"; TAN="D8B36A"


def Hx(h, a=1.0):
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4)) + (a,)


def mat(name, rgb, emit=None, es=0.0, rough=0.8, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgb
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit is not None:
        b.inputs["Emission Color"].default_value = emit
        b.inputs["Emission Strength"].default_value = es
    return m


def M(key):
    d = {
        "red": (RED, None, 0, 0.55, 0.0), "orange": (ORANGE, None, 0, 0.6, 0.0),
        "yellow": (YELLOW, None, 0, 0.5, 0.0), "teal": (TEAL, None, 0, 0.5, 0.0),
        "white": (WHITE, None, 0, 0.7, 0.0), "black": (BLACK, None, 0, 0.7, 0.0),
        "brown": (BROWN, None, 0, 0.85, 0.0), "grey": (GREY, None, 0, 0.4, 0.6),
        "dkgrey": (DKGREY, None, 0, 0.5, 0.3), "green": (GREEN, None, 0, 0.7, 0.0),
        "tan": (TAN, None, 0, 0.9, 0.0),
        "chrome": (GREY, None, 0, 0.2, 0.85),
        "glowY": (YELLOW, YELLOW, 5, 0.4, 0.0), "glowT": (TEAL, TEAL, 5, 0.4, 0.0),
        "glowO": (ORANGE, ORANGE, 4, 0.4, 0.0),
        "asphalt": ("32333B", None, 0, 0.9, 0.0),
    }[key]
    return mat(key, Hx(d[0]), Hx(d[1]) if d[1] else None, d[2], d[3], d[4])


def box(sx, sy, sz, loc, m, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.scale = (sx, sy, sz); o.data.materials.append(m)
    if rot: o.rotation_euler = tuple(math.radians(a) for a in rot)
    for p in o.data.polygons: p.use_smooth = False
    return o


def cyl(r, d, loc, m, v=10, rot=None, smooth=False):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, location=loc, vertices=v)
    o = bpy.context.active_object; o.data.materials.append(m)
    if rot: o.rotation_euler = tuple(math.radians(a) for a in rot)
    for p in o.data.polygons: p.use_smooth = smooth
    return o


def cone(r1, r2, d, loc, m, v=10, rot=None):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=d, location=loc, vertices=v)
    o = bpy.context.active_object; o.data.materials.append(m)
    if rot: o.rotation_euler = tuple(math.radians(a) for a in rot)
    for p in o.data.polygons: p.use_smooth = False
    return o


def sphere(r, loc, m, sc=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=12, ring_count=8)
    o = bpy.context.active_object; o.scale = sc; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = True
    return o


def torus(R, r, loc, m, maj=14, mino=8, rot=None):
    bpy.ops.mesh.primitive_torus_add(location=loc, major_radius=R, minor_radius=r,
                                     major_segments=maj, minor_segments=mino)
    o = bpy.context.active_object; o.data.materials.append(m)
    if rot: o.rotation_euler = tuple(math.radians(a) for a in rot)
    for p in o.data.polygons: p.use_smooth = True
    return o


def wheel(loc, r=0.34, w=0.24):
    # tire rolls forward (+Y): axle along X -> rotate cylinder 90° about Y
    cyl(r, w, loc, M("black"), v=12, rot=(0, 90, 0))
    cyl(r * 0.45, w + 0.02, loc, M("grey"), v=8, rot=(0, 90, 0))   # hub


# ---------------- KARTS (face +Y forward; no driver) ----------------
def _kart_base(body_mat):
    # low tub chassis + wedge nose + seat back; 4 wheels
    box(0.9, 1.5, 0.34, (0, 0, 0.42), body_mat)                     # tub
    box(0.78, 0.5, 0.26, (0, 0.95, 0.5), body_mat, rot=(18, 0, 0))  # sloped nose
    cone(0.34, 0.12, 0.5, (0, 1.25, 0.42), body_mat, v=4, rot=(90, 0, 0))  # pointed prow
    box(0.82, 0.5, 0.5, (0, -0.55, 0.62), body_mat)                # seat back
    box(0.7, 0.44, 0.08, (0, -0.05, 0.58), M("dkgrey"))            # seat pad
    box(0.96, 1.55, 0.06, (0, 0, 0.24), M("dkgrey"))               # floor pan
    for sx in (-0.55, 0.55):                                        # wheels
        wheel((sx, 0.75, 0.34)); wheel((sx, -0.75, 0.34))
    cyl(0.03, 0.5, (0, 0.15, 0.72), M("dkgrey"), v=6, rot=(60, 0, 0))  # steering column
    cyl(0.18, 0.05, (0, 0.36, 0.98), M("black"), v=10, rot=(70, 0, 0))  # steering wheel
    box(0.2, 0.2, 0.16, (0, 1.05, 0.62), M("yellow"))              # headlight block
    return body_mat


def kart_racer():
    _kart_base(M("red"))
    box(0.5, 0.04, 0.16, (0, -0.2, 0.95), M("white"))              # number plate on seat


def kart_rocket():
    _kart_base(M("teal"))
    for sx in (-0.3, 0.3):                                          # twin rear rockets
        cyl(0.16, 0.5, (sx, -0.95, 0.55), M("grey"), v=10, rot=(90, 0, 0))
        cyl(0.17, 0.12, (sx, -1.22, 0.55), M("glowO"), v=10, rot=(90, 0, 0))
    box(0.5, 0.3, 0.3, (0, -0.5, 1.0), M("teal"))                  # spoiler wing riser
    box(0.9, 0.08, 0.1, (0, -0.62, 1.16), M("yellow"))


def kart_tub():
    # bathtub soapbox — rounded barrel body
    cyl(0.55, 1.4, (0, 0, 0.55), M("orange"), v=14, rot=(90, 0, 0))
    box(0.9, 1.5, 0.06, (0, 0, 0.16), M("dkgrey"))                 # floor
    box(0.5, 0.4, 0.4, (0, 0.85, 0.55), M("orange"), rot=(20, 0, 0))  # nose
    for sx in (-0.55, 0.55):
        wheel((sx, 0.7, 0.34)); wheel((sx, -0.7, 0.34))
    cyl(0.16, 0.05, (0, 0.3, 0.82), M("black"), v=10, rot=(70, 0, 0))  # wheel
    box(0.6, 0.5, 0.5, (0, -0.5, 0.7), M("orange"))               # seat back
    box(0.62, 0.04, 0.3, (0, 0.72, 0.7), M("white"))              # racing stripe front


def kart_crate():
    # wooden crate racer
    box(0.9, 1.3, 0.6, (0, 0, 0.55), M("brown"))
    for ex in (-0.46, 0.46):                                       # plank edges
        box(0.04, 1.3, 0.6, (ex, 0, 0.55), M("tan"))
    for ey in (-0.66, 0.66):
        box(0.9, 0.04, 0.6, (0, ey, 0.55), M("tan"))
    box(0.5, 0.4, 0.3, (0, 0.8, 0.5), M("brown"), rot=(20, 0, 0))  # nose
    box(0.94, 1.34, 0.06, (0, 0, 0.22), M("dkgrey"))
    for sx in (-0.55, 0.55):
        wheel((sx, 0.7, 0.34)); wheel((sx, -0.7, 0.34))
    box(0.6, 0.3, 0.02, (0, 0.2, 0.86), M("red"))                 # number placard


# ---------------- TRACK (modular 2u) ----------------
def _tile(mat=None):
    box(2.0, 2.0, 0.12, (0, 0, 0.06), mat or M("asphalt"))


def track_straight():
    _tile()
    for i in (-1, 0, 1):                                            # dashed centre line
        box(0.12, 0.4, 0.02, (0, i * 0.6, 0.13), M("yellow"))
    for ex in (-0.95, 0.95):                                        # kerb edges (red/white)
        for j in range(5):
            box(0.1, 0.4, 0.1, (ex, -0.8 + j * 0.4, 0.17), M("red" if j % 2 else "white"))


def track_corner():
    _tile()
    for k in range(7):                                             # quarter-arc centre dashes
        a = (k / 6.0) * (math.pi / 2)
        box(0.12, 0.12, 0.02, (-0.85 + 0.95 * math.cos(a), -0.85 + 0.95 * math.sin(a), 0.13), M("yellow"))
    for k in range(6):                                             # outer kerb arc
        a = (k / 5.0) * (math.pi / 2)
        box(0.14, 0.14, 0.1, (-0.9 + 1.75 * math.cos(a), -0.9 + 1.75 * math.sin(a), 0.17),
            M("red" if k % 2 else "white"))


def track_start():
    _tile()
    for r in range(4):                                            # checkered start stripe
        for c in range(8):
            if (r + c) % 2 == 0:
                box(0.24, 0.16, 0.02, (-0.84 + c * 0.24, -0.3 + r * 0.16, 0.13), M("white"))
            else:
                box(0.24, 0.16, 0.02, (-0.84 + c * 0.24, -0.3 + r * 0.16, 0.13), M("black"))


def ramp_up():
    box(2.0, 2.0, 0.5, (0, 0, 0.25), M("asphalt"), rot=(9, 0, 0))  # inclined slab
    for ex in (-0.95, 0.95):
        box(0.1, 2.0, 0.14, (ex, 0, 0.42), M("yellow"))
    box(2.0, 0.3, 0.12, (0, -0.95, 0.06), M("dkgrey"))            # base lip


def jump_ramp():
    # kicker launch ramp
    box(1.6, 1.2, 0.1, (0, -0.2, 0.4), M("red"), rot=(28, 0, 0))
    box(1.7, 0.5, 0.7, (0, -0.85, 0.35), M("dkgrey"))            # back support
    for ex in (-0.85, 0.85):
        box(0.08, 1.3, 0.5, (ex, -0.2, 0.5), M("yellow"), rot=(28, 0, 0))
    box(1.7, 0.3, 0.12, (0, 0.5, 0.06), M("white"))              # takeoff lip


def finish_gate():
    for ex in (-1.1, 1.1):                                        # posts
        box(0.24, 0.24, 2.4, (ex, 0, 1.2), M("red"))
    box(2.6, 0.4, 0.5, (0, 0, 2.55), M("white"))                 # banner
    for c in range(10):                                          # checkered banner
        if c % 2 == 0:
            box(0.24, 0.42, 0.36, (-1.08 + c * 0.24, 0, 2.55), M("black"))
    box(2.2, 0.1, 0.28, (0, 0, 3.0), M("yellow"))                # "FINISH" strip


def checkpoint_arch():
    for ex in (-1.1, 1.1):
        cyl(0.14, 2.2, (ex, 0, 1.1), M("teal"), v=8)
    torus(1.1, 0.14, (0, 0, 2.2), M("teal"), maj=12, mino=6, rot=(90, 0, 0))
    for ex in (-1.1, 1.1):                                        # corner flags
        box(0.35, 0.02, 0.24, (ex + (0.2 if ex < 0 else -0.2), 0, 2.5), M("yellow"))
    box(0.9, 0.06, 0.3, (0, 0, 2.25), M("glowT"))                # glowing checkpoint bar


# ---------------- HAZARDS / PROPS ----------------
def traffic_cone():
    cone(0.28, 0.06, 0.7, (0, 0, 0.35), M("orange"), v=12)
    cyl(0.34, 0.06, (0, 0, 0.03), M("orange"), v=12)             # base
    cyl(0.22, 0.1, (0, 0, 0.42), M("white"), v=12)               # reflective band


def tire_stack():
    for i, R in enumerate((0.5, 0.46, 0.42)):
        torus(R, 0.2, (0, 0, 0.22 + i * 0.42), M("black"), maj=16, mino=8)
    cyl(0.2, 1.3, (0, 0, 0.65), M("dkgrey"), v=8)                # centre post


def crate():
    box(0.8, 0.8, 0.8, (0, 0, 0.4), M("brown"))
    for ex in (-0.41, 0.41):
        box(0.02, 0.8, 0.8, (ex, 0, 0.4), M("tan")); box(0.8, 0.02, 0.8, (0, ex, 0.4), M("tan"))
    for ez in (-0.41, 0.41):
        box(0.8, 0.8, 0.02, (0, 0, 0.4 + ez), M("tan"))
    box(0.5, 0.5, 0.02, (0, 0.41, 0.4), M("yellow"), rot=(90, 0, 0))  # hazard label


def barrier():
    box(2.0, 0.16, 0.7, (0, 0, 0.5), M("white"))                 # A-frame board
    for c in range(6):                                          # diagonal hazard stripes
        if c % 2 == 0:
            box(0.28, 0.18, 0.66, (-0.85 + c * 0.34, 0, 0.5), M("red"))
    for ex in (-0.8, 0.8):                                       # legs
        box(0.1, 0.5, 0.16, (ex, 0, 0.08), M("dkgrey"))


def oil_slick():
    cyl(0.85, 0.04, (0, 0, 0.03), M("black"), v=16)
    cyl(0.5, 0.05, (0.15, 0.1, 0.04), M("dkgrey"), v=14)         # sheen blob
    sphere(0.12, (-0.2, -0.15, 0.05), M("glowT"), (1, 1, 0.3))   # toxic glint


def boost_pad():
    box(1.0, 1.4, 0.06, (0, 0, 0.05), M("dkgrey"))
    for j in range(3):                                          # glowing forward chevrons
        z = 0.09
        box(0.5, 0.12, 0.03, (0, -0.4 + j * 0.4, z), M("glowY"), rot=(0, 0, 0))
        box(0.36, 0.12, 0.03, (0.28, -0.5 + j * 0.4, z), M("glowY"), rot=(0, 0, -35))
        box(0.36, 0.12, 0.03, (-0.28, -0.5 + j * 0.4, z), M("glowY"), rot=(0, 0, 35))


def barrel():
    cyl(0.32, 0.9, (0, 0, 0.45), M("red"), v=14)
    for z in (0.2, 0.45, 0.7):
        cyl(0.34, 0.05, (0, 0, z), M("dkgrey"), v=14)
    box(0.24, 0.24, 0.02, (0, 0.33, 0.5), M("yellow"), rot=(90, 0, 0))


def haybale():
    cyl(0.55, 1.0, (0, 0, 0.5), M("tan"), v=14, rot=(0, 90, 0))
    for a in range(4):                                          # binding twine
        cyl(0.56, 0.03, (-0.3 + a * 0.2, 0, 0.5), M("brown"), v=14, rot=(0, 90, 0))


def sign_arrow():
    cyl(0.06, 1.4, (0, 0, 0.7), M("dkgrey"), v=6)
    box(0.7, 0.08, 0.4, (0, 0, 1.3), M("yellow"))
    cone(0.3, 0.0, 0.35, (0.5, 0, 1.3), M("yellow"), v=3, rot=(0, 90, 90))  # arrowhead


def flag_pole():
    cyl(0.05, 2.0, (0, 0, 1.0), M("grey"), v=6)
    for r in range(3):                                          # checkered flag
        for c in range(4):
            m = M("black") if (r + c) % 2 else M("white")
            box(0.16, 0.02, 0.14, (0.13 + c * 0.16, 0, 1.75 - r * 0.14), m)


def banner():
    for ex in (-1.0, 1.0):
        cyl(0.05, 1.6, (ex, 0, 0.8), M("brown"), v=6)
    box(1.9, 0.05, 0.5, (0, 0, 1.4), M("red"))                  # sponsor board
    box(1.5, 0.06, 0.24, (0, -0.03, 1.4), M("white"))
    for c in range(7):                                          # bunting flags
        cone(0.1, 0.0, 0.18, (-0.9 + c * 0.3, 0, 1.05), M("teal" if c % 2 else "yellow"), v=3, rot=(180, 0, 0))


def puddle():
    cyl(0.8, 0.04, (0, 0, 0.03), M("teal"), v=16)
    cyl(0.5, 0.05, (0.1, 0.05, 0.04), M("white"), v=14)


# ---------------- PICKUPS (floating icons) ----------------
def _pickup_base():
    cyl(0.5, 0.05, (0, 0, 0.02), M("dkgrey"), v=14)             # ground marker
    torus(0.42, 0.05, (0, 0, 0.75), M("glowT"), maj=16, mino=6)  # floating ring


def pickup_boost():
    _pickup_base()
    for j in (-0.12, 0.12):                                     # double chevron (lightning)
        box(0.22, 0.08, 0.22, (0, j, 0.75), M("glowY"), rot=(0, 45, 0))


def pickup_shield():
    _pickup_base()
    box(0.3, 0.06, 0.34, (0, 0, 0.78), M("glowT"))
    cone(0.21, 0.0, 0.2, (0, 0, 0.58), M("glowT"), v=3, rot=(180, 0, 0))


def pickup_wrench():
    _pickup_base()
    cyl(0.06, 0.42, (0, 0, 0.75), M("glowO"), v=8, rot=(0, 0, 35))  # handle
    torus(0.11, 0.05, (0.14, 0, 0.9), M("glowO"), maj=10, mino=5)   # jaw
    torus(0.11, 0.05, (-0.14, 0, 0.6), M("glowO"), maj=10, mino=5)


PIECES = {
    "kart_racer": kart_racer, "kart_rocket": kart_rocket, "kart_tub": kart_tub, "kart_crate": kart_crate,
    "track_straight": track_straight, "track_corner": track_corner, "track_start": track_start,
    "ramp_up": ramp_up, "jump_ramp": jump_ramp, "finish_gate": finish_gate, "checkpoint_arch": checkpoint_arch,
    "cone": traffic_cone, "tire_stack": tire_stack, "crate": crate, "barrier": barrier, "oil_slick": oil_slick,
    "boost_pad": boost_pad, "barrel": barrel, "haybale": haybale, "sign_arrow": sign_arrow,
    "flag_pole": flag_pole, "banner": banner, "puddle": puddle,
    "pickup_boost": pickup_boost, "pickup_shield": pickup_shield, "pickup_wrench": pickup_wrench,
}


def export_piece(name):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=f"{OUT}/models_glb/{name}.glb", use_selection=True, export_format='GLB')
    try:
        bpy.ops.wm.obj_export(filepath=f"{OUT}/models_obj/{name}.obj", export_selected_objects=True)
    except Exception:
        pass
    try:
        bpy.ops.export_scene.fbx(filepath=f"{OUT}/models_fbx/{name}.fbx", use_selection=True)
    except Exception:
        pass


n = 0
for name, fn in PIECES.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fn()
    export_piece(name)
    n += 1
    print(f"  built+exported {name}", flush=True)
print(f"SOAPBOX KART PIECES DONE: {n} pieces -> {OUT}")
