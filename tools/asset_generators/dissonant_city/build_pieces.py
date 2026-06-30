"""DissonantCity kit (L0.3) — build the modular piece library, export GLB/OBJ/FBX.
Procedural flat-shaded low-poly, DissonantDreams palette + neon. Grid-modular (2u tiles).
Headless: blender --background --python build_pieces.py
"""
import bpy, math, os

OUT = r"D:/Projects/comfyui-toolchain/products/dissonant_city_v1"
for sub in ("models_glb", "models_obj", "models_fbx"):
    os.makedirs(f"{OUT}/{sub}", exist_ok=True)

PINK="E8186C"; CYAN="1BC6D6"; BLACK="0D0D18"; CREAM="EDE3C4"; PURPLE="3A1E5C"; CHROME="8FA6BC"


def Hx(h, a=1.0):
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4)) + (a,)


def mat(name, rgb, emit=None, es=0.0, rough=0.85, metal=0.0):
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
        "dark": (BLACK, None, 0, 0.9, 0.0), "purple": (PURPLE, None, 0, 0.95, 0.0),
        "pink": (PINK, None, 0, 0.6, 0.0), "cyan": (CYAN, None, 0, 0.6, 0.0),
        "cream": (CREAM, None, 0, 0.8, 0.0), "chrome": (CHROME, None, 0, 0.3, 0.5),
        "neonP": (PINK, PINK, 7, 0.4, 0.0), "neonC": (CYAN, CYAN, 7, 0.4, 0.0),
        "win": (CREAM, "FFE9B0", 4, 0.5, 0.0), "wgrid": (CYAN, CYAN, 3, 0.5, 0.0),
        "navy": ("10122A", None, 0, 0.85, 0.0),
    }[key]
    return mat(key, Hx(d[0]), Hx(d[1]) if d[1] else None, d[2], d[3], d[4])


def box(sx, sy, sz, loc, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.scale = (sx, sy, sz); o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = False
    return o


def cyl(r, d, loc, m, v=8, smooth=False):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, location=loc, vertices=v)
    o = bpy.context.active_object; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = smooth
    return o


def cone(r1, r2, d, loc, m, v=8):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=d, location=loc, vertices=v)
    o = bpy.context.active_object; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = False
    return o


def sphere(r, loc, m, sc=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=12, ring_count=6)
    o = bpy.context.active_object; o.scale = sc; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = True
    return o


# ---- piece builders (each builds at origin, z>=0) ----
def tower_tall(body, band):       # body kept for lambda signature (now always dark)
    _edge_tower(1.7, 7.0, band)

def tower_short(body, band):
    _edge_tower(1.8, 4.4, band)

def dome_building():
    body, ac, wn = M("navy"), M("neonC"), M("wgrid")
    cyl(2.6, 2.4, (0, 0, 1.2), body, 12)                         # dark drum
    cyl(2.66, 0.14, (0, 0, 0.1), M("neonP"), 12); cyl(2.66, 0.12, (0, 0, 2.4), ac, 12)  # base/top rings
    for i in range(12):                                          # vertical neon strips
        a = (i / 12.0) * 2 * math.pi
        s = box(0.08, 0.08, 2.4, (2.62 * math.cos(a), 2.62 * math.sin(a), 1.2), ac); s.rotation_euler.z = a
    for rz in (0.6, 1.2, 1.8):                                   # window grid
        for i in range(10):
            a = (i / 10.0) * 2 * math.pi + 0.15
            w = box(0.3, 0.05, 0.22, (2.63 * math.cos(a), 2.63 * math.sin(a), rz), wn); w.rotation_euler.z = a
    cyl(2.72, 0.2, (0, 0, 2.5), M("neonP"), 12)                  # dome ring
    sphere(2.3, (0, 0, 2.5), M("chrome"), (1, 1, 0.55))          # chrome dome

def slab_shop(c, sign):
    body, ac, wn = M("navy"), M(sign), M("wgrid")
    box(4.0, 2.4, 1.5, (0, 0, 0.75), body); hx, hy = 2.0, 1.2
    for ex in (-1, 1):                                           # vertical edges
        for ey in (-1, 1): box(0.06, 0.06, 1.5, (ex * hx, ey * hy, 0.75), ac)
    for z, m in ((0.05, M("neonC")), (1.5, ac)):                # base/top trim
        box(4.06, 0.05, 0.05, (0, hy, z), m); box(4.06, 0.05, 0.05, (0, -hy, z), m)
    for i in (-1, 0, 1): box(0.9, 0.04, 0.7, (i * 1.3, -hy - 0.01, 0.7), wn)   # glowing storefront
    box(2.0, 0.12, 0.6, (0, hy + 0.04, 2.0), ac); box(0.1, 0.1, 0.85, (0, hy + 0.02, 1.5), M("chrome"))  # rooftop sign

def ziggurat():
    body, ac, edge = M("navy"), M("neonC"), M("neonP")
    for i, w in enumerate((3.4, 2.6, 1.8, 1.0)):
        z0 = 0.4 + i * 0.8; zt = 0.8 + i * 0.8; h = w / 2
        box(w, w, 0.8, (0, 0, z0), body)                         # dark tier
        for s in (-1, 1):                                        # neon top trim
            box(w + 0.05, 0.05, 0.05, (0, s * h, zt), ac); box(0.05, w + 0.05, 0.05, (s * h, 0, zt), ac)
        for ex in (-1, 1):                                       # vertical edge accents
            for ey in (-1, 1): box(0.06, 0.06, 0.8, (ex * h, ey * h, z0), edge)
        for col in (-1, 1):                                      # window slits per tier face
            box(0.5, 0.04, 0.3, (col * w * 0.22, h + 0.01, z0), M("wgrid"))
            box(0.04, 0.5, 0.3, (h + 0.01, col * w * 0.22, z0), M("wgrid"))
    cone(0.5, 0.05, 1.0, (0, 0, 3.7), edge, 6)

def cyl_tower():
    # round counterpart of the neon tower: dark body, vertical neon strips,
    # window grid, base/tier rings, crown + antenna.
    sides = 14
    body, ac, wn, cy = M("navy"), M("neonP"), M("wgrid"), M("neonC")
    mh, sh, R = 5.4, 1.6, 1.6
    cyl(R, mh, (0, 0, mh / 2), body, sides); cyl(R * 0.78, sh, (0, 0, mh + sh / 2), body, sides)
    cyl(R + 0.18, 0.18, (0, 0, 0.09), cy, sides)        # base glow ring
    cyl(R + 0.06, 0.12, (0, 0, mh), ac, sides); cyl(R * 0.78 + 0.06, 0.1, (0, 0, mh + sh), ac, sides)
    for i in range(10):                                   # vertical neon strips
        a = (i / 10.0) * 2 * math.pi
        s = box(0.08, 0.08, mh, (R * 1.01 * math.cos(a), R * 1.01 * math.sin(a), mh / 2), ac)
        s.rotation_euler.z = a
    r = 0                                                 # window grid
    while 0.5 + r * 0.7 < mh - 0.3:
        wz = 0.5 + r * 0.7; r += 1
        for i in range(9):
            a = (i / 9.0) * 2 * math.pi + 0.2
            w = box(0.3, 0.05, 0.2, (R * 1.02 * math.cos(a), R * 1.02 * math.sin(a), wz), wn)
            w.rotation_euler.z = a
    cyl(R * 0.7, 0.22, (0, 0, mh + sh + 0.1), M("chrome"), sides)
    cyl(0.05, 1.6, (0, 0, mh + sh + 1.0), M("chrome"), 4); cone(0.1, 0.0, 0.3, (0, 0, mh + sh + 1.9), cy, 6)

def arcology():
    body, ac, wn = M("navy"), M("neonP"), M("wgrid")
    box(3.4, 3.4, 2.0, (0, 0, 1.0), body); h = 1.7
    for ex in (-1, 1):                                           # vertical edges
        for ey in (-1, 1): box(0.08, 0.08, 2.0, (ex * h, ey * h, 1.0), ac)
    for z, m in ((0.08, M("neonC")), (2.0, ac)):                # base/top trim
        for s in (-1, 1):
            box(3.5, 0.06, 0.06, (0, s * h, z), m); box(0.06, 3.5, 0.06, (s * h, 0, z), m)
    for rz in (0.6, 1.4):                                        # window grid
        for col in (-1, 0, 1):
            box(0.4, 0.04, 0.3, (col * 0.95, h + 0.01, rz), wn); box(0.4, 0.04, 0.3, (col * 0.95, -h - 0.01, rz), wn)
            box(0.04, 0.4, 0.3, (h + 0.01, col * 0.95, rz), wn); box(0.04, 0.4, 0.3, (-h - 0.01, col * 0.95, rz), wn)
    cyl(2.4, 0.16, (0, 0, 2.1), M("neonC"), 12)                 # dome ring
    sphere(2.1, (0, 0, 2.1), M("chrome"), (1, 1, 0.7))

def skybridge():
    # detailed enclosed walkway: floor + neon strip + railings w/ posts + underside trusses
    chrome, c, dark = M("chrome"), M("neonC"), M("navy")
    box(0.75, 4.0, 0.16, (0, 0, 3.4), chrome)                    # walkway floor
    box(0.8, 4.1, 0.04, (0, 0, 3.5), c)                          # glowing floor strip
    for s in (-1, 1):                                            # side railings
        box(0.05, 4.0, 0.34, (s * 0.36, 0, 3.6), dark)
        box(0.06, 4.0, 0.04, (s * 0.36, 0, 3.79), c)
        for y in (-1.5, -0.5, 0.5, 1.5): box(0.06, 0.06, 0.3, (s * 0.36, y, 3.58), chrome)
    for y in (-1.3, 0, 1.3): box(0.55, 0.12, 0.3, (0, y, 3.18), dark)   # underside trusses
    box(0.12, 4.0, 0.1, (0, 0, 3.08), chrome)                    # spine beam
    box(0.14, 0.5, 0.14, (0, 1.9, 3.4), c); box(0.14, 0.5, 0.14, (0, -1.9, 3.4), c)  # end caps

def bridge_support():
    cyl(0.5, 3.4, (0, 0, 1.7), M("chrome"), 8); box(0.7, 0.7, 0.2, (0, 0, 3.4), M("neonC"))

def road_straight():
    box(2.0, 2.0, 0.15, (0, 0, 0.075), M("dark"))
    box(0.1, 2.0, 0.04, (-0.7, 0, 0.16), M("neonC")); box(0.1, 2.0, 0.04, (0.7, 0, 0.16), M("neonC"))
    box(0.12, 0.5, 0.04, (0, 0, 0.16), M("neonP"))

def road_corner():
    box(2.0, 2.0, 0.15, (0, 0, 0.075), M("dark"))
    box(0.1, 1.4, 0.04, (-0.7, 0.3, 0.16), M("neonC")); box(1.4, 0.1, 0.04, (0.3, -0.7, 0.16), M("neonC"))

def road_junction():
    box(2.0, 2.0, 0.15, (0, 0, 0.075), M("dark"))
    for s in (-0.7, 0.7):
        box(0.1, 2.0, 0.04, (s, 0, 0.16), M("neonC")); box(2.0, 0.1, 0.04, (0, s, 0.16), M("neonP"))

def plaza_tile():
    box(2.0, 2.0, 0.15, (0, 0, 0.075), M("purple"))
    box(1.7, 1.7, 0.04, (0, 0, 0.16), M("dark")); box(0.4, 0.4, 0.06, (0, 0, 0.18), M("neonC"))

def streetlight():
    cyl(0.12, 3.0, (0, 0, 1.5), M("dark"), 6); box(0.6, 0.14, 0.5, (0, 0, 2.8), M("neonP"))

def billboard():
    # framed glowing screen on supports + neon frame + content bars + top sign (ref billboards)
    dark, screen, p, c = M("navy"), M("wgrid"), M("neonP"), M("neonC")
    for s in (-1, 1): cyl(0.1, 2.6, (s * 1.15, 0, 1.3), dark, 6)   # support legs
    box(2.5, 0.12, 0.1, (0, 0, 1.0), dark)                         # cross brace
    box(2.9, 0.2, 1.7, (0, 0, 2.7), dark)                          # screen backing
    box(2.55, 0.06, 1.4, (0, -0.13, 2.7), screen)                 # glowing screen
    box(2.75, 0.06, 0.07, (0, -0.14, 3.45), p); box(2.75, 0.06, 0.07, (0, -0.14, 1.95), p)  # frame top/bot
    box(0.07, 0.06, 1.55, (1.38, -0.14, 2.7), c); box(0.07, 0.06, 1.55, (-1.38, -0.14, 2.7), c)  # frame sides
    for k, z in enumerate((2.3, 2.6, 2.9, 3.2)):                   # content "text" bars
        box(1.9, 0.02, 0.1, (0, -0.17, z), c if k % 2 else p)
    box(1.1, 0.12, 0.45, (0.6, 0, 3.78), p); box(0.7, 0.13, 0.3, (-0.7, 0, 3.72), c)  # top signs

def hover_car():
    # sleek long-low hover-car (ref car1): wedge nose + sloped windshield + spoiler + thrusters
    hull, glow, canopy, hot = M("navy"), M("neonC"), M("wgrid"), M("neonP")
    box(1.9, 0.64, 0.16, (0, 0, 0.46), hull)                    # long low hull
    nose = cone(0.4, 0.0, 0.85, (1.18, 0, 0.44), hull, 4)       # long pointed nose
    nose.rotation_euler = (0, math.radians(90), math.radians(45))
    box(0.62, 0.5, 0.14, (0.0, 0, 0.6), canopy)                 # cabin (glowing)
    ws = cone(0.34, 0.0, 0.5, (0.55, 0, 0.58), canopy, 4)       # sloped windshield wedge
    ws.rotation_euler = (0, math.radians(90), math.radians(45))
    box(0.5, 0.6, 0.12, (-0.82, 0, 0.48), hull)                # rear taper
    box(0.55, 0.66, 0.035, (-0.9, 0, 0.62), hull)              # rear spoiler
    for s in (-1, 1): box(1.7, 0.03, 0.05, (0, s * 0.33, 0.5), glow)    # side accent lines
    box(1.55, 0.46, 0.05, (0, 0, 0.3), glow)                    # underglow
    for s in (-1, 1): cyl(0.16, 0.14, (-1.12, s * 0.2, 0.46), glow, 10)  # twin rear thrusters
    box(0.05, 0.34, 0.08, (1.34, 0, 0.46), hot)                # headlights

def hover_car2():
    # retro DeLorean-style with glowing cyan wheels (ref car2)
    body, wheel, canopy, accent, hot = M("navy"), M("neonC"), M("wgrid"), M("neonC"), M("neonP")
    box(1.5, 0.7, 0.28, (0, 0, 0.55), body)                     # boxy body
    box(0.9, 0.66, 0.26, (0.05, 0, 0.82), canopy)              # angular glowing cabin
    box(0.95, 0.68, 0.05, (0.05, 0, 0.95), body)               # roof
    box(0.5, 0.72, 0.12, (-0.7, 0, 0.62), body)                # rear deck
    for sx in (0.55, -0.55):                                     # 4 glowing wheels
        for sy in (-1, 1):
            w = cyl(0.22, 0.16, (sx, sy * 0.42, 0.3), wheel, 10); w.rotation_euler.x = math.radians(90)
    for s in (-1, 1): box(1.3, 0.04, 0.05, (0, s * 0.36, 0.55), accent)  # side trim
    box(0.06, 0.42, 0.12, (0.82, 0, 0.55), hot)                # front light bar

def neon_arch():
    for s in (-1, 1): box(0.2, 0.2, 2.0, (s * 1.4, 0, 1.0), M("chrome"))
    box(3.2, 0.2, 0.2, (0, 0, 2.1), M("neonP")); box(2.8, 0.24, 0.12, (0, 0, 2.1), M("neonC"))

def antenna():
    cyl(0.4, 2.0, (0, 0, 1.0), M("dark"), 6); cone(0.4, 0.04, 2.4, (0, 0, 3.2), M("chrome"), 6)
    for z in (2.4, 3.2, 4.0): box(1.0, 0.05, 0.05, (0, 0, z), M("neonC"))

def holo_pylon():
    cyl(0.5, 0.3, (0, 0, 0.15), M("dark"), 8); box(0.3, 0.3, 2.4, (0, 0, 1.4), M("neonC")); sphere(0.5, (0, 0, 2.8), M("neonP"))

def fountain_pad():
    cyl(1.8, 0.3, (0, 0, 0.15), M("purple"), 12); cyl(1.4, 0.1, (0, 0, 0.32), M("neonC"), 12)
    cone(0.6, 0.1, 1.2, (0, 0, 0.9), M("chrome"), 8); sphere(0.4, (0, 0, 1.6), M("neonP"))

def crystals():
    for x, y, h, mm in [(-0.4, 0, 1.4, "neonC"), (0.4, 0.2, 1.0, "neonP"), (0.0, -0.4, 0.7, "neonC")]:
        cone(0.25, 0.0, h, (x, y, h / 2), M(mm), 6)

def palm_retro():
    cyl(0.18, 2.4, (0, 0, 1.2), M("chrome"), 6)
    for a in range(0, 360, 60):
        c = cone(0.5, 0.0, 1.4, (0.7 * math.cos(math.radians(a)), 0.7 * math.sin(math.radians(a)), 2.6), M("neonC"), 4)
        c.rotation_euler = (math.radians(50), 0, math.radians(a))

def barrier():
    box(2.0, 0.2, 0.5, (0, 0, 0.25), M("dark")); box(2.0, 0.24, 0.08, (0, 0, 0.4), M("neonP"))

def tower_spiral():
    # central cylinder shaft + neon rings + cap/spire
    cyl(1.3, 6.0, (0, 0, 3.0), M("purple"), 12)
    for z in (1.5, 3.0, 4.5): cyl(1.36, 0.14, (0, 0, z), M("neonC"), 12)
    cyl(1.5, 0.4, (0, 0, 6.15), M("chrome"), 12); cone(0.45, 0.04, 1.3, (0, 0, 7.0), M("neonP"), 6)
    # spiraling walkway (Archimedes screw): tangent box segments along a 3-turn helix
    R, turns, seg, ztop = 1.85, 3, 54, 5.2
    for i in range(seg):
        a = (i / seg) * turns * 2 * math.pi
        z = 0.5 + (i / seg) * ztop
        wk = box(0.95, 0.4, 0.12, (R * math.cos(a), R * math.sin(a), z), M("chrome"))
        wk.rotation_euler.z = a + math.pi / 2
        ne = box(0.42, 0.05, 0.09, ((R + 0.42) * math.cos(a), (R + 0.42) * math.sin(a), z + 0.11), M("neonP"))
        ne.rotation_euler.z = a + math.pi / 2
        if i % 3 == 0:  # railing posts
            rp = box(0.06, 0.06, 0.5, ((R + 0.42) * math.cos(a), (R + 0.42) * math.sin(a), z + 0.3), M("neonC"))
            rp.rotation_euler.z = a + math.pi / 2

def tower_prism():
    # tall rectangular prism, dark-purple body (more depth than near-black)
    box(2.0, 2.0, 6.0, (0, 0, 3.0), M("purple")); box(1.7, 1.7, 1.4, (0, 0, 6.4), M("purple"))
    cyl(0.8, 0.3, (0, 0, 7.2), M("chrome"), 4); cone(0.5, 0.04, 1.2, (0, 0, 7.9), M("neonC"), 4)
    # glowing triangular features: chevron neon triangles up each face (3-vert flat cones)
    faces = [(0, -1.02, 0), (0, 1.02, 0), (1.02, 0, 90), (-1.02, 0, 90)]
    for fx, fy, frot in faces:
        for k, z in enumerate((1.2, 2.6, 4.0, 5.2)):
            tri = cone(0.55, 0.0, 0.12, (fx, fy, z), M("neonP" if k % 2 == 0 else "neonC"), 3)
            tri.rotation_euler = (math.radians(90), 0, math.radians(frot + (180 if k % 2 else 0)))

def _edge_tower(W, H, accent, footprint=True):
    # dark-body neon tower: edge outlines + window grid (lit setback, no dark top).
    body, ac, wn, cy = M("navy"), M(accent), M("wgrid"), M("neonC")
    mh = H * 0.70; sh = H * 0.26; sw = W * 0.78
    box(W, W, mh, (0, 0, mh / 2), body); box(sw, sw, sh, (0, 0, mh + sh / 2), body)
    hx = W / 2; sx2 = sw / 2
    for ex in (-1, 1):
        for ey in (-1, 1):
            box(0.07, 0.07, mh, (ex * hx, ey * hx, mh / 2), ac)              # main edges
            box(0.06, 0.06, sh, (ex * sx2, ey * sx2, mh + sh / 2), ac)        # setback edges
    def ring(w, z, m):
        h = w / 2
        for s in (-1, 1):
            box(w + 0.06, 0.05, 0.05, (0, s * h, z), m); box(0.05, w + 0.06, 0.05, (s * h, 0, z), m)
    ring(W, 0.1, cy); ring(W, mh, ac); ring(sw, mh + sh, ac)
    # window grid on main mass
    r = 0
    while 0.5 + r * 0.72 < mh - 0.3:
        wz = 0.5 + r * 0.72; r += 1
        for col in (-1, 0, 1):
            box(0.32, 0.04, 0.2, (col * W * 0.28, hx + 0.01, wz), wn)
            box(0.32, 0.04, 0.2, (col * W * 0.28, -hx - 0.01, wz), wn)
            box(0.04, 0.32, 0.2, (hx + 0.01, col * W * 0.28, wz), wn)
            box(0.04, 0.32, 0.2, (-hx - 0.01, col * W * 0.28, wz), wn)
    # lit setback window band (kills the dark top)
    for fy in (1, -1):
        box(sw * 0.66, 0.04, 0.42, (0, fy * (sx2 + 0.01), mh + sh * 0.5), wn)
        box(0.04, sw * 0.66, 0.42, (fy * (sx2 + 0.01), 0, mh + sh * 0.5), wn)
    if footprint:
        for s in (-1, 1):
            box(0.08, W + 0.6, 0.04, (s * (hx + 0.3), 0, 0.02), ac)
            box(W + 0.6, 0.08, 0.04, (0, s * (hx + 0.3), 0.02), ac)
    box(sw * 0.6, sw * 0.6, 0.22, (0, 0, mh + sh + 0.1), M("chrome"))
    cyl(0.05, 1.6, (0, 0, mh + sh + 1.0), M("chrome"), 4)
    cone(0.1, 0.0, 0.3, (0, 0, mh + sh + 1.9), cy, 6)

def tower_neon():
    _edge_tower(1.7, 7.2, "neonP")
    # hero extras: bright vertical neon SIGN strips
    box(0.05, 0.34, 3.2, (0.9, 0.45, 2.7), M("neonP"))
    box(0.05, 0.18, 1.6, (0.9, -0.55, 4.4), M("neonC"))


PIECES = {
    "tower_tall_cyan": lambda: _edge_tower(1.4, 8.4, "neonC"),     # slim + tall, cyan edges
    "tower_tall_purple": lambda: _edge_tower(2.1, 6.2, "neonP"),   # wide + medium, pink edges
    "tower_short_pink": lambda: _edge_tower(2.1, 4.0, "neonP"),    # short + wide, pink edges
    "tower_cyl": cyl_tower, "tower_spiral": tower_spiral, "tower_prism": tower_prism,
    "tower_neon": tower_neon,
    "dome_building": dome_building, "arcology": arcology,
    "ziggurat": ziggurat,
    "slab_shop_pink": lambda: slab_shop("pink", "neonC"),
    "slab_shop_cyan": lambda: slab_shop("cyan", "neonP"),
    "skybridge": skybridge, "bridge_support": bridge_support,
    "road_straight": road_straight, "road_corner": road_corner,
    "road_junction": road_junction, "plaza_tile": plaza_tile,
    "streetlight": streetlight, "billboard": billboard, "neon_arch": neon_arch,
    "hover_car": hover_car, "hover_car2": hover_car2,
    "antenna": antenna, "holo_pylon": holo_pylon, "fountain_pad": fountain_pad,
    "crystals": crystals, "palm_retro": palm_retro, "barrier": barrier,
}


def export_piece(name):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=f"{OUT}/models_glb/{name}.glb", use_selection=True,
                              export_format='GLB')
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
print(f"DISSONANT CITY PIECES DONE: {n} pieces -> {OUT}")
