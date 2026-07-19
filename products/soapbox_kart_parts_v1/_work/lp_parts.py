"""lp_parts.py — procedurally author clean low-poly junkyard kart parts.

Hand-built companions to the TRELLIS-reconstructed set: crisp, game-ready topology
(hundreds of tris, not the ~1M TRELLIS gives), for the simpler geometric pieces where
photogrammetry-style reconstruction is overkill. Same modular kit / socket vocabulary,
same welded-scrap aesthetic (chunky primitives, bolts, clamps, dents).

Each builder returns one joined object; main() exports each to lowpoly/<id>.glb and clay-
renders 3 views to _work/review_lp/. Geometry-only (grey); color/material is a later pass.

Run with Blender's Python:
  blender --background --python lp_parts.py -- [--only lp_spikes lp_rollcage]
"""
import bpy, bmesh, math, sys, os, mathutils

ROOT = "D:/Projects/comfyui-toolchain/products/soapbox_kart_parts_v1"
LP_DIR = ROOT + "/lowpoly"
REVIEW = ROOT + "/_work/review_lp"


# ---------- primitive helpers ----------
def _mesh(name):
    me = bpy.data.meshes.new(name); ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob); return ob


def box(sx, sy, sz, loc=(0, 0, 0), name="box"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.scale = (sx, sy, sz); o.name = name
    bpy.ops.object.transform_apply(scale=True); return o


def cyl(r, h, loc=(0, 0, 0), verts=10, rot=(0, 0, 0), name="cyl"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; return o


def cone(r, h, loc=(0, 0, 0), verts=8, rot=(0, 0, 0), name="cone"):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=0, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; return o


def sphere(r, loc=(0, 0, 0), segs=10, rings=6, name="sphere"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=r, location=loc)
    o = bpy.context.active_object; o.name = name; return o


def torus(maj, minr, loc=(0, 0, 0), rot=(0, 0, 0), majs=12, mins=6, name="torus"):
    bpy.ops.mesh.primitive_torus_add(major_radius=maj, minor_radius=minr, major_segments=majs,
                                     minor_segments=mins, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; return o


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = name
    return o


def bolts(around_r, z, n=8, r=0.02, name="bolts"):
    bs = []
    for i in range(n):
        a = 2 * math.pi * i / n
        bs.append(cyl(r, 0.03, (around_r * math.cos(a), around_r * math.sin(a), z), 6, (math.pi / 2, 0, a)))
    return bs


# ---------- part builders ----------
def lp_exhaust_stacks():
    """rear_mount — twin scrap exhaust stacks on a manifold."""
    parts = [box(0.42, 0.20, 0.14, (0, 0, 0.07), "manifold")]
    for sx in (-0.11, 0.11):
        parts.append(cyl(0.06, 0.72, (sx, 0, 0.5), 10))          # pipe
        parts.append(cyl(0.095, 0.22, (sx, 0, 0.32), 10))        # muffler can
        parts.append(cyl(0.075, 0.04, (sx, 0, 0.62), 10))        # clamp ring
        parts.append(cyl(0.085, 0.10, (sx, 0, 0.88), 10))        # flared tip
    parts.append(box(0.10, 0.10, 0.08, (0, 0, 0.03), "dent"))
    return join(parts, "lp_exhaust_stacks")


def lp_rollcage():
    """roof_mount — welded tube roll cage."""
    R = 0.045; s = 0.42; h = 0.62; parts = []
    for (x, y) in [(-s, -s), (s, -s), (-s, s), (s, s)]:
        parts.append(cyl(R, h, (x, y, h / 2), 6))                # posts
    for y in (-s, s):                                            # side top rails
        parts.append(cyl(R, 2 * s, (0, y, h), 6, (0, math.pi / 2, 0)))
    for x in (-s, s):                                            # front/back top rails
        parts.append(cyl(R, 2 * s, (x, 0, h), 6, (math.pi / 2, 0, 0)))
    parts.append(cyl(R, 2 * s * 1.41, (0, 0, h), 6, (math.pi / 2, 0, math.pi / 4)))  # cross brace
    parts.append(cyl(R, 2 * s, (0, 0, h * 0.5), 6, (0, math.pi / 2, 0)))             # mid support
    return join(parts, "lp_rollcage")


def lp_spikes():
    """wheel_mount — spinning hub-spike weapon."""
    parts = [cyl(0.16, 0.12, (0, 0, 0), 12, (math.pi / 2, 0, 0), "hub"),
             cyl(0.06, 0.16, (0, 0, 0), 8, (math.pi / 2, 0, 0), "axle")]
    n = 10
    for i in range(n):
        a = 2 * math.pi * i / n
        parts.append(cone(0.045, 0.22, (0.26 * math.cos(a), 0, 0.26 * math.sin(a)),
                          7, (0, 0, 0) if False else (0, math.pi / 2 - a, 0) if False else (math.pi / 2, 0, 0),
                          "spike"))
        parts[-1].location = (0.24 * math.cos(a), 0, 0.24 * math.sin(a))
        parts[-1].rotation_euler = (0, math.pi / 2 - a, 0)
    return join(parts, "lp_spikes")


def lp_armor_plate():
    """side_mount — bolted scrap armor panel."""
    p = box(0.52, 0.04, 0.62, (0, 0, 0.31), "plate")
    parts = [p]
    for (x, z) in [(-0.22, 0.06), (0.22, 0.06), (-0.22, 0.56), (0.22, 0.56)]:
        parts.append(cyl(0.03, 0.05, (x, -0.02, z), 6, (math.pi / 2, 0, 0), "bolt"))
    parts.append(box(0.5, 0.05, 0.09, (0.0, -0.01, 0.31), "weldstrip"))  # diagonal band
    parts[-1].rotation_euler = (0, math.radians(22), 0)
    parts.append(box(0.14, 0.05, 0.10, (0.13, -0.02, 0.20), "dent"))
    return join(parts, "lp_armor_plate")


def lp_ram_bar():
    """nose_mount — welded battering ram bumper (faces -Y = kart front)."""
    parts = [box(0.66, 0.10, 0.14, (0, 0.06, 0.30), "beam")]        # horizontal bumper beam
    for sx in (-0.28, 0.28):
        # forward-pointing push pads (along -Y), so it reads as a ram not a table
        parts.append(cyl(0.09, 0.22, (sx, -0.14, 0.30), 8, (math.pi / 2, 0, 0), "pad"))
        parts.append(cone(0.075, 0.14, (sx, -0.30, 0.30), 8, (-math.pi / 2, 0, 0), "spike"))
        # rear-angled brace struts back toward the chassis mount
        b = cyl(0.04, 0.34, (sx * 0.7, 0.22, 0.20), 6, name="brace")
        b.rotation_euler = (math.radians(-38), 0, 0)
        parts.append(b)
    parts.append(box(0.14, 0.16, 0.16, (0, 0.16, 0.14), "mountboss"))  # chassis attach boss
    parts.append(cyl(0.05, 0.60, (0, -0.02, 0.30), 6, (0, math.pi / 2, 0), "crossbar"))
    parts.append(box(0.10, 0.05, 0.10, (0.16, 0.06, 0.30), "dent"))
    return join(parts, "lp_ram_bar")


def lp_tesla():
    """roof_mount — scrap tesla-coil weapon."""
    parts = [box(0.24, 0.20, 0.16, (0, 0, 0.08), "battery")]        # battery box base
    parts.append(cyl(0.05, 0.55, (0, 0, 0.42), 8, name="pole"))     # telescoping pole
    parts.append(cyl(0.035, 0.30, (0, 0, 0.80), 6, name="pole2"))
    for i, zr in enumerate([(0.34, 0.11), (0.44, 0.09), (0.53, 0.07)]):  # stacked coil rings
        z, rr = zr
        parts.append(cyl(rr, 0.03, (0, 0, z), 10, name=f"coil{i}"))
    parts.append(cyl(0.10, 0.03, (0, 0, 0.95), 12, name="topplate"))     # antenna terminal
    parts.append(cone(0.03, 0.14, (0, 0, 1.03), 6, name="tip"))
    parts.append(box(0.05, 0.05, 0.10, (0.10, 0.06, 0.06), "cable"))
    return join(parts, "lp_tesla")


def lp_nailgun():
    """nose_mount — scrap nail-gun weapon."""
    parts = [box(0.20, 0.34, 0.22, (0, 0, 0.14), "body")]           # gun body
    parts.append(cyl(0.045, 0.40, (0, -0.30, 0.16), 8, (math.pi / 2, 0, 0), "barrel"))
    parts.append(cyl(0.02, 0.36, (0, -0.30, 0.16), 6, (math.pi / 2, 0, 0), "muzzle"))
    parts.append(cyl(0.08, 0.26, (0.0, 0.16, 0.30), 10, name="tank"))   # air tank on top
    parts.append(cyl(0.085, 0.03, (0.0, 0.16, 0.44), 10, name="tankcap"))
    parts.append(box(0.06, 0.10, 0.20, (0, 0.10, -0.02), "grip"))       # grip
    parts.append(cyl(0.03, 0.16, (0.0, -0.02, 0.02), 6, (0, math.radians(30), 0), "hose"))
    return join(parts, "lp_nailgun")


def lp_number_plate():
    """side_mount / decor — race number panel."""
    parts = [box(0.46, 0.05, 0.56, (0, 0, 0.28), "panel")]
    parts.append(box(0.30, 0.03, 0.40, (0, -0.03, 0.28), "raised"))     # raised number field
    for (x, z) in [(-0.19, 0.05), (0.19, 0.05), (-0.19, 0.51), (0.19, 0.51)]:
        parts.append(cyl(0.028, 0.05, (x, -0.02, z), 6, (math.pi / 2, 0, 0), "bolt"))
    parts.append(box(0.5, 0.03, 0.06, (0, -0.01, 0.10), "tape"))        # duct-tape strip
    return join(parts, "lp_number_plate")


def lp_wheel():
    """wheel_mount — clean low-poly knobby tire (axle along X; hand-modeled beats a
    decimated TRELLIS wheel, which loses its roundness)."""
    RX = (0, math.pi / 2, 0)  # cylinder axis -> X
    parts = [cyl(0.50, 0.34, (0, 0, 0), 20, RX, "tire"),
             cyl(0.31, 0.36, (0, 0, 0), 14, RX, "rim"),
             cyl(0.11, 0.42, (0, 0, 0), 10, RX, "hub"),
             cyl(0.05, 0.46, (0, 0, 0), 8, RX, "axle")]
    for i in range(6):                                  # lug bolts on the rim face
        a = 2 * math.pi * i / 6
        parts.append(cyl(0.025, 0.38, (0, 0.20 * math.cos(a), 0.20 * math.sin(a)), 6, RX, "lug"))
    n = 14                                              # chunky tread lugs around the tyre
    for i in range(n):
        a = 2 * math.pi * i / n
        lug = box(0.36, 0.07, 0.11, (0, 0.50 * math.cos(a), 0.50 * math.sin(a)), "tread")
        lug.rotation_euler = (a, 0, 0)
        parts.append(lug)
    return join(parts, "lp_wheel")


def lp_grille():
    """nose_mount — radiator grille nose with headlights + bumper."""
    parts = [box(0.50, 0.14, 0.46, (0, 0, 0.30), "radiator")]
    for x in [i * 0.09 - 0.18 for i in range(5)]:       # vertical grille slats
        parts.append(box(0.03, 0.06, 0.40, (x, -0.08, 0.30), "slat"))
    for sx in (-0.20, 0.20):                            # headlights
        parts.append(cyl(0.07, 0.10, (sx, -0.10, 0.50), 10, (math.pi / 2, 0, 0), "light"))
    parts.append(box(0.58, 0.08, 0.09, (0, -0.05, 0.08), "bumper"))
    parts.append(box(0.12, 0.06, 0.10, (0.10, -0.09, 0.22), "dent"))
    return join(parts, "lp_grille")


def lp_fueltank():
    """decor_mount / side — scrap fuel tank (mounts almost anywhere)."""
    parts = [cyl(0.18, 0.62, (0, 0, 0.31), 14, name="tank")]
    parts.append(cyl(0.19, 0.04, (0, 0, 0.08), 14, name="band1"))     # straps
    parts.append(cyl(0.19, 0.04, (0, 0, 0.54), 14, name="band2"))
    parts.append(cyl(0.06, 0.08, (0.0, 0.0, 0.66), 10, name="cap"))   # filler cap
    parts.append(cyl(0.025, 0.24, (0.10, -0.10, 0.20), 6, (math.radians(50), 0, 0), "fuel_line"))
    parts.append(box(0.10, 0.05, 0.08, (0.14, 0.02, 0.40), "dent"))
    return join(parts, "lp_fueltank")


def lp_chassis_rail():
    """root — tubular hot-rod kart chassis; the base every other part mounts to."""
    parts = [box(0.28, 1.30, 0.05, (0, 0, 0.14), "floorpan")]           # floor pan
    for sx in (-0.30, 0.30):                                            # side rails
        parts.append(cyl(0.045, 1.30, (sx, 0, 0.18), 8, (math.pi / 2, 0, 0), "rail"))
    for sy in (-0.55, 0.0, 0.55):                                       # cross members
        parts.append(cyl(0.04, 0.62, (0, sy, 0.18), 8, (0, math.pi / 2, 0), "cross"))
    for (sx, sy) in [(-0.34, 0.66), (0.34, 0.66), (-0.34, -0.66), (0.34, -0.66)]:
        parts.append(cyl(0.05, 0.16, (sx, sy, 0.13), 8, (0, math.pi / 2, 0), "axlestub"))
    parts.append(box(0.20, 0.16, 0.16, (0, 0.60, 0.24), "cowl"))       # front cowl
    parts.append(cyl(0.05, 0.30, (0, -0.62, 0.30), 6, name="mount"))   # rear mount post
    return join(parts, "lp_chassis_rail")


def lp_wheel_slick():
    """wheel_mount — smooth racing slick on a mag rim."""
    RX = (0, math.pi / 2, 0)
    parts = [cyl(0.50, 0.40, (0, 0, 0), 22, RX, "tire"),
             cyl(0.30, 0.42, (0, 0, 0), 16, RX, "rim"),
             cyl(0.10, 0.46, (0, 0, 0), 10, RX, "hub")]
    for i in range(5):                                                  # 5-spoke mag
        a = 2 * math.pi * i / 5
        sp = box(0.10, 0.05, 0.40, (0, 0.15 * math.cos(a), 0.15 * math.sin(a)), "spoke")
        sp.rotation_euler = (a, 0, 0); parts.append(sp)
    return join(parts, "lp_wheel_slick")


def lp_wheel_disc():
    """wheel_mount — solid riveted steel disc wheel."""
    RX = (0, math.pi / 2, 0)
    parts = [cyl(0.50, 0.30, (0, 0, 0), 20, RX, "tire"),
             cyl(0.40, 0.06, (0, 0.0, 0), 20, RX, "disc"),
             cyl(0.08, 0.34, (0, 0, 0), 10, RX, "hub")]
    for i in range(10):                                                 # rivets on the disc
        a = 2 * math.pi * i / 10
        parts.append(cyl(0.02, 0.10, (0, 0.32 * math.cos(a), 0.32 * math.sin(a)), 6, RX, "rivet"))
    return join(parts, "lp_wheel_disc")


def lp_steering_wheel():
    """steering_mount — junkyard steering wheel on a column."""
    parts = [torus(0.18, 0.028, (0, 0, 0.66), (math.pi / 2, 0, 0), 14, 6, "ring"),
             cyl(0.05, 0.60, (0, 0, 0.32), 8, name="column"),
             cyl(0.09, 0.06, (0, 0, 0.62), 10, name="boss")]
    for a in (0, math.pi * 2 / 3, math.pi * 4 / 3):                     # spokes
        parts.append(box(0.16, 0.03, 0.03, (0.08 * math.cos(a), 0, 0.66 + 0.08 * math.sin(a)),
                         "spoke"))
        parts[-1].rotation_euler = (a, 0, 0)
    parts.append(box(0.14, 0.14, 0.06, (0, 0, 0.03), "base"))
    return join(parts, "lp_steering_wheel")


def lp_tail_fin():
    """rear_mount — tall scrap tail fin."""
    fin = box(0.05, 0.30, 0.55, (0, 0, 0.32), "fin")
    # taper the top-front into a fin profile
    bm = bmesh.new(); bm.from_mesh(fin.data)
    for v in bm.verts:
        if v.co.z > 0:                                                  # top edge -> slant back
            v.co.y += 0.18 * (v.co.z)
    bm.to_mesh(fin.data); bm.free()
    parts = [fin, box(0.10, 0.34, 0.06, (0, 0, 0.05), "foot")]
    for sy in (-0.10, 0.10):
        parts.append(cyl(0.02, 0.40, (0, sy, 0.30), 6, name="rib"))
    return join(parts, "lp_tail_fin")


def lp_roof_rack():
    """roof_mount — welded scrap-pipe roof luggage rack."""
    R = 0.03; sx, sy = 0.42, 0.36; parts = []
    for x in (-sx, sx):
        parts.append(cyl(R, 2 * sy, (x, 0, 0.06), 6, (math.pi / 2, 0, 0), "siderail"))
    for y in (-sy, sy):
        parts.append(cyl(R, 2 * sx, (0, y, 0.06), 6, (0, math.pi / 2, 0), "endrail"))
    for y in (-0.18, 0.18):                                             # cross slats
        parts.append(cyl(0.02, 2 * sx, (0, y, 0.06), 6, (0, math.pi / 2, 0), "slat"))
    for (x, y) in [(-sx, -sy), (sx, -sy), (-sx, sy), (sx, sy)]:         # short legs
        parts.append(cyl(R, 0.12, (x, y, 0.0), 6, name="leg"))
    return join(parts, "lp_roof_rack")


def lp_wreckingball():
    """rear_mount — wrecking-ball weapon: ball on a chain and arm."""
    parts = [sphere(0.20, (0, -0.35, 0.20), 12, 8, "ball"),
             cyl(0.05, 0.55, (0, 0.10, 0.45), 6, (math.radians(60), 0, 0), "arm"),
             box(0.12, 0.12, 0.12, (0, 0.30, 0.20), "mount")]
    for i in range(4):                                                  # chain links
        t = i / 4.0
        parts.append(torus(0.04, 0.015, (0, -0.10 - t * 0.18, 0.42 - t * 0.15),
                           (0, math.pi / 2 * (i % 2), 0), 8, 4, "link"))
    return join(parts, "lp_wreckingball")


def lp_nose_plow():
    """nose_mount — angled scrap plow blade."""
    blade = box(0.60, 0.06, 0.34, (0, -0.10, 0.34), "blade")
    blade.rotation_euler = (math.radians(-28), 0, 0)
    parts = [blade, box(0.60, 0.05, 0.05, (0, -0.02, 0.16), "edge")]
    for sx in (-0.22, 0.22):
        b = cyl(0.03, 0.30, (sx, 0.06, 0.20), 6); b.rotation_euler = (math.radians(35), 0, 0)
        parts.append(b)
    parts.append(box(0.14, 0.14, 0.12, (0, 0.14, 0.10), "mount"))
    return join(parts, "lp_nose_plow")


def lp_wood_door():
    """side_mount — planked wooden door with a Z-brace, hinges and handle."""
    parts = []
    for x in (-0.18, -0.09, 0.0, 0.09, 0.18):
        parts.append(box(0.085, 0.04, 0.58, (x, 0, 0.30), "plank"))
    parts.append(box(0.42, 0.05, 0.06, (0, -0.01, 0.14), "brace_lo"))
    parts.append(box(0.42, 0.05, 0.06, (0, -0.01, 0.46), "brace_hi"))
    zb = box(0.52, 0.05, 0.06, (0, -0.01, 0.30), "zbrace"); zb.rotation_euler = (0, math.radians(38), 0)
    parts.append(zb)
    for z in (0.16, 0.44):
        parts.append(cyl(0.03, 0.06, (-0.22, 0.0, z), 6, (math.pi / 2, 0, 0), "hinge"))
    parts.append(cyl(0.025, 0.10, (0.16, -0.05, 0.30), 6, (math.pi / 2, 0, 0), "handle"))
    return join(parts, "lp_wood_door")


def lp_wood_roof():
    """roof_mount — planked wooden roof on corner posts."""
    parts = []
    for y in (-0.30, -0.18, -0.06, 0.06, 0.18, 0.30):
        parts.append(box(0.72, 0.10, 0.05, (0, y, 0.60), "plank"))
    for (x, y) in [(-0.32, -0.30), (0.32, -0.30), (-0.32, 0.30), (0.32, 0.30)]:
        parts.append(box(0.05, 0.05, 0.58, (x, y, 0.30), "post"))
    parts.append(box(0.06, 0.68, 0.05, (0, 0, 0.64), "ridge"))
    return join(parts, "lp_wood_roof")


def lp_wood_barrel():
    """decor_mount — wooden barrel (faceted staves + iron hoops)."""
    parts = [cyl(0.20, 0.56, (0, 0, 0.30), 12, name="staves")]
    for z in (0.10, 0.30, 0.50):
        parts.append(cyl(0.21, 0.03, (0, 0, z), 14, name="hoop"))
    parts.append(cyl(0.06, 0.06, (0, 0, 0.60), 8, name="bung"))
    return join(parts, "lp_wood_barrel")


def lp_tire_bumper():
    """nose_mount — stacked-tire bumper (rubber)."""
    parts = [box(0.60, 0.08, 0.08, (0, 0.06, 0.20), "bar")]
    for x in (-0.22, 0.0, 0.22):
        parts.append(torus(0.14, 0.06, (x, -0.06, 0.20), (math.pi / 2, 0, 0), 12, 6, "tire"))
    parts.append(box(0.14, 0.12, 0.10, (0, 0.12, 0.14), "mount"))
    return join(parts, "lp_tire_bumper")


def lp_tarp_roof():
    """roof_mount — canvas tarp roof (peaked cover on poles)."""
    parts = []
    for (x, y) in [(-0.34, -0.30), (0.34, -0.30), (-0.34, 0.30), (0.34, 0.30)]:
        parts.append(cyl(0.03, 0.55, (x, y, 0.28), 6, name="pole"))
    cover = box(0.78, 0.70, 0.03, (0, 0, 0.56), "cover")
    bm = bmesh.new(); bm.from_mesh(cover.data)
    for v in bm.verts:                                     # peak the centre, droop the edges
        v.co.z += 0.12 * (0.42 - math.hypot(v.co.x, v.co.y))
    bm.to_mesh(cover.data); bm.free()
    parts.append(cover)
    parts.append(cyl(0.02, 0.74, (0, 0, 0.60), 4, (0, math.pi / 2, 0), "ridgepole"))
    return join(parts, "lp_tarp_roof")


def _chassis_frame():
    """shared hot-rod frame: floor pan, rails, cross members, 4 axle stubs, rear mount."""
    parts = [box(0.28, 1.30, 0.05, (0, 0, 0.14), "floorpan")]
    for sx in (-0.30, 0.30):
        parts.append(cyl(0.045, 1.30, (sx, 0, 0.18), 8, (math.pi / 2, 0, 0), "rail"))
    for sy in (-0.55, 0.0, 0.55):
        parts.append(cyl(0.04, 0.62, (0, sy, 0.18), 8, (0, math.pi / 2, 0), "cross"))
    for (sx, sy) in [(-0.34, 0.66), (0.34, 0.66), (-0.34, -0.66), (0.34, -0.66)]:
        parts.append(cyl(0.05, 0.16, (sx, sy, 0.13), 8, (0, math.pi / 2, 0), "axlestub"))
    parts.append(cyl(0.05, 0.30, (0, -0.62, 0.30), 6, name="mount"))
    return parts


def lp_chassis_tub():
    """root — bathtub-style kart chassis."""
    parts = _chassis_frame()
    tub = box(0.34, 1.00, 0.32, (0, 0, 0.36), "tub")
    bm = bmesh.new(); bm.from_mesh(tub.data)                          # flare the rim outward
    for v in bm.verts:
        if v.co.z > 0.30:
            v.co.x *= 1.25
    bm.to_mesh(tub.data); bm.free()
    parts.append(tub)
    parts.append(box(0.46, 1.04, 0.05, (0, 0, 0.52), "rim"))          # rim lip
    parts.append(cyl(0.05, 0.06, (0, 0.44, 0.40), 8, (math.pi / 2, 0, 0), "drainbolt"))
    return join(parts, "lp_chassis_tub")


def lp_chassis_crate():
    """root — wooden-crate kart chassis."""
    parts = _chassis_frame()
    parts.append(box(0.36, 0.90, 0.34, (0, 0, 0.37), "crate"))
    for z in (0.24, 0.37, 0.50):                                      # plank slat lines
        for sx in (-0.185, 0.185):
            parts.append(box(0.02, 0.90, 0.04, (sx, 0, z), "slat"))
    for sy in (-0.46, 0.46):
        parts.append(box(0.36, 0.02, 0.34, (0, sy, 0.37), "endslat"))
    return join(parts, "lp_chassis_crate")


def lp_chassis_plank():
    """root — barebones plank kart chassis."""
    parts = _chassis_frame()
    parts.append(box(0.30, 1.30, 0.06, (0, 0, 0.24), "plank"))
    parts.append(box(0.32, 0.16, 0.10, (0, 0.5, 0.30), "footrest"))
    parts.append(box(0.10, 0.10, 0.14, (0, -0.4, 0.30), "seatpost"))
    return join(parts, "lp_chassis_plank")


def lp_roof_hardtop():
    """roof_mount — riveted sheet-metal hardtop canopy."""
    top = box(0.74, 0.72, 0.06, (0, 0, 0.60), "roofpanel")
    bm = bmesh.new(); bm.from_mesh(top.data)                          # taper the front down
    for v in bm.verts:
        if v.co.y < 0:
            v.co.z -= 0.10
    bm.to_mesh(top.data); bm.free()
    parts = [top]
    for (x, y) in [(-0.32, -0.30), (0.32, -0.30), (-0.32, 0.30), (0.32, 0.30)]:
        parts.append(cyl(0.035, 0.58, (x, y, 0.30), 6, name="post"))
    for i in range(6):                                                # rivets
        parts.append(cyl(0.015, 0.08, (-0.30 + i * 0.12, 0.34, 0.60), 5, name="rivet"))
    return join(parts, "lp_roof_hardtop")


def lp_roof_canopy():
    """roof_mount — cracked bubble canopy dome."""
    dome = sphere(0.42, (0, 0, 0.30), 14, 8, "dome")
    dome.scale = (1, 1, 0.85)
    bpy.ops.object.select_all(action="DESELECT"); dome.select_set(True)
    bpy.context.view_layer.objects.active = dome
    bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new(); bm.from_mesh(dome.data)                         # cut bottom hemisphere
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < 0.30], context="VERTS")
    bm.to_mesh(dome.data); bm.free()
    parts = [dome, torus(0.42, 0.03, (0, 0, 0.30), (0, 0, 0), 14, 5, "ring")]
    parts.append(cyl(0.05, 0.16, (0, 0.30, 0.30), 6, (math.pi / 2, 0, 0), "hinge"))
    return join(parts, "lp_roof_canopy")


def lp_roof_umbrella():
    """roof_mount — tattered umbrella roof on a pole."""
    canopy = cone(0.52, 0.26, (0, 0, 0.66), 10, name="canopy")
    parts = [canopy, cyl(0.03, 0.66, (0, 0, 0.33), 6, name="pole"),
             box(0.16, 0.16, 0.06, (0, 0, 0.03), "base"),
             cyl(0.05, 0.05, (0, 0, 0.80), 6, name="finial")]
    for i in range(8):                                                # rib tips
        a = 2 * math.pi * i / 8
        parts.append(cyl(0.012, 0.30, (0.24 * math.cos(a), 0.24 * math.sin(a), 0.60), 4,
                         (math.radians(70) * math.cos(a + math.pi / 2), math.radians(70) * math.sin(a + math.pi / 2), 0), "rib"))
    return join(parts, "lp_roof_umbrella")


def lp_sidepipes():
    """side_mount — side exhaust pipes running along the body."""
    RY = (math.pi / 2, 0, 0)  # cylinder axis -> Y (runs front-back along the kart side)
    parts = []
    for z in (0.16, 0.30):
        parts.append(cyl(0.05, 0.86, (0, 0, z), 10, RY, "pipe"))
        for sy in (-0.30, 0.0, 0.30):                                 # clamps
            parts.append(cyl(0.06, 0.04, (0, sy, z), 10, RY, "clamp"))
    parts.append(cyl(0.08, 0.16, (0, 0.44, 0.16), 10, RY, "muffler"))
    parts.append(box(0.06, 0.20, 0.30, (-0.06, 0.0, 0.23), "mountplate"))
    return join(parts, "lp_sidepipes")


def lp_tail_stacks():
    """rear_mount — tall twin turnout exhaust stacks."""
    parts = [box(0.34, 0.14, 0.10, (0, 0, 0.05), "base")]
    for sx in (-0.12, 0.12):
        parts.append(cyl(0.055, 0.66, (sx, 0, 0.40), 10, name="stack"))
        parts.append(cyl(0.07, 0.05, (sx, 0, 0.20), 10, name="clampring"))
        tip = cyl(0.07, 0.20, (sx, -0.08, 0.72), 10, (math.radians(55), 0, 0), "turnout")
        parts.append(tip)
    return join(parts, "lp_tail_stacks")


def lp_wheel_spoked():
    """wheel_mount — thin spoked vintage wheel."""
    RX = (0, math.pi / 2, 0)
    parts = [torus(0.46, 0.06, (0, 0, 0), RX, 20, 6, "tyre"),
             cyl(0.09, 0.16, (0, 0, 0), 10, RX, "hub")]
    for i in range(10):                                               # thin spokes
        a = 2 * math.pi * i / 10
        sp = cyl(0.015, 0.80, (0, 0.23 * math.cos(a), 0.23 * math.sin(a)), 4, RX, "spoke")
        sp.rotation_euler = (a, math.pi / 2, 0)
        parts.append(sp)
    return join(parts, "lp_wheel_spoked")


def lp_wheel_monster():
    """wheel_mount — huge oversized monster tyre."""
    RX = (0, math.pi / 2, 0)
    parts = [cyl(0.62, 0.46, (0, 0, 0), 22, RX, "tyre"),
             cyl(0.30, 0.48, (0, 0, 0), 12, RX, "rim"),
             cyl(0.10, 0.52, (0, 0, 0), 10, RX, "hub")]
    n = 16
    for i in range(n):                                                # big chunky treads
        a = 2 * math.pi * i / n
        lug = box(0.48, 0.10, 0.16, (0, 0.62 * math.cos(a), 0.62 * math.sin(a)), "tread")
        lug.rotation_euler = (a, 0, 0); parts.append(lug)
    return join(parts, "lp_wheel_monster")


def lp_wheel_wagon():
    """wheel_mount — wooden wagon wheel (thick spokes, wood rim)."""
    RX = (0, math.pi / 2, 0)
    parts = [torus(0.48, 0.05, (0, 0, 0), RX, 16, 6, "rim"),
             cyl(0.44, 0.10, (0, 0, 0), 16, RX, "band"),
             cyl(0.11, 0.20, (0, 0, 0), 10, RX, "hub")]
    for i in range(8):                                                # thick wooden spokes
        a = 2 * math.pi * i / 8
        sp = box(0.10, 0.06, 0.36, (0, 0.24 * math.cos(a), 0.24 * math.sin(a)), "spoke")
        sp.rotation_euler = (a, 0, 0); parts.append(sp)
    return join(parts, "lp_wheel_wagon")


def lp_chainsaw():
    """side_mount — chainsaw-arm weapon."""
    parts = [box(0.20, 0.24, 0.20, (0, 0, 0.10), "engine"),
             box(0.55, 0.03, 0.12, (0.38, 0, 0.10), "bar"),          # guide bar (along +X)
             cyl(0.05, 0.10, (0.10, -0.14, 0.10), 10, (math.pi / 2, 0, 0), "pullstart"),
             box(0.05, 0.08, 0.16, (-0.10, 0.0, 0.22), "grip")]
    for i in range(9):                                               # chain teeth on the bar
        x = 0.16 + i * 0.06
        parts.append(box(0.03, 0.04, 0.03, (x, 0, 0.17), "tooth"))
        parts.append(box(0.03, 0.04, 0.03, (x, 0, 0.03), "tooth"))
    return join(parts, "lp_chainsaw")


def lp_molotov():
    """side_mount — molotov-cocktail throwing arm."""
    parts = [box(0.16, 0.16, 0.10, (0, 0, 0.05), "base"),
             cyl(0.04, 0.40, (0, -0.10, 0.22), 6, (math.radians(55), 0, 0), "arm")]
    parts.append(cyl(0.05, 0.14, (0, -0.28, 0.42), 8, (math.radians(55), 0, 0), "bottle"))
    parts.append(cone(0.03, 0.08, (0, -0.34, 0.50), 6, (math.radians(-125), 0, 0), "neck"))
    parts.append(torus(0.06, 0.015, (0, -0.20, 0.30), (math.radians(55), 0, 0), 8, 4, "cradle"))
    return join(parts, "lp_molotov")


def lp_smoke():
    """rear_mount — smoke-screen blower."""
    parts = [cyl(0.18, 0.24, (0, 0, 0.18), 12, (math.pi / 2, 0, 0), "housing"),
             box(0.24, 0.20, 0.10, (0, 0, 0.05), "base")]
    for sx in (-0.08, 0.0, 0.08):                                    # exhaust vent pipes
        parts.append(cyl(0.04, 0.22, (sx, 0.18, 0.30), 6, (math.radians(60), 0, 0), "vent"))
    parts.append(cyl(0.12, 0.04, (0, -0.14, 0.18), 10, (math.pi / 2, 0, 0), "fanguard"))
    return join(parts, "lp_smoke")


def lp_oilslick():
    """rear_mount — oil-slick drum sprayer (drum on its side)."""
    parts = [cyl(0.20, 0.50, (0, 0, 0.22), 14, (0, math.pi / 2, 0), "drum"),
             cyl(0.205, 0.05, (-0.12, 0, 0.22), 14, (0, math.pi / 2, 0), "rib1"),
             cyl(0.205, 0.05, (0.12, 0, 0.22), 14, (0, math.pi / 2, 0), "rib2"),
             box(0.54, 0.20, 0.08, (0, 0, 0.03), "cradle")]
    parts.append(cyl(0.03, 0.30, (0.22, -0.10, 0.20), 6, (math.radians(50), 0, 0), "hose"))
    parts.append(cyl(0.05, 0.06, (0, 0, 0.42), 8, name="cap"))
    return join(parts, "lp_oilslick")


def lp_thunderstick():
    """roof_mount — thunderstick spear launcher."""
    parts = [cyl(0.07, 0.44, (0, -0.05, 0.30), 10, (math.radians(70), 0, 0), "tube"),
             box(0.14, 0.14, 0.14, (0, 0.12, 0.10), "breach"),
             cyl(0.025, 0.40, (0, -0.20, 0.44), 6, (math.radians(70), 0, 0), "spear")]
    parts.append(cone(0.03, 0.10, (0, -0.34, 0.52), 6, (math.radians(-110), 0, 0), "tip"))
    for a in (0, math.pi * 2 / 3, math.pi * 4 / 3):                  # tail fins
        f = box(0.02, 0.10, 0.06, (0.03 * math.cos(a), 0.02, 0.14 + 0.03 * math.sin(a)), "fin")
        parts.append(f)
    return join(parts, "lp_thunderstick")


def lp_catapult():
    """rear_mount — junk catapult."""
    parts = [box(0.30, 0.34, 0.08, (0, 0, 0.04), "base"),
             box(0.05, 0.05, 0.30, (0, 0.10, 0.20), "pivotpost")]
    arm = box(0.05, 0.46, 0.05, (0, -0.05, 0.30), "arm"); arm.rotation_euler = (math.radians(-35), 0, 0)
    parts.append(arm)
    parts.append(cyl(0.09, 0.10, (0, -0.24, 0.46), 8, name="basket"))   # launch cup
    parts.append(torus(0.05, 0.02, (0, 0.02, 0.16), (math.pi / 2, 0, 0), 8, 4, "spring"))
    parts.append(box(0.34, 0.05, 0.05, (0, 0.16, 0.06), "crossbar"))
    return join(parts, "lp_catapult")


BUILDERS = {
    "lp_wood_door": lp_wood_door,
    "lp_wood_roof": lp_wood_roof,
    "lp_wood_barrel": lp_wood_barrel,
    "lp_tire_bumper": lp_tire_bumper,
    "lp_tarp_roof": lp_tarp_roof,
    "lp_chassis_tub": lp_chassis_tub,
    "lp_chassis_crate": lp_chassis_crate,
    "lp_chassis_plank": lp_chassis_plank,
    "lp_roof_hardtop": lp_roof_hardtop,
    "lp_roof_canopy": lp_roof_canopy,
    "lp_roof_umbrella": lp_roof_umbrella,
    "lp_sidepipes": lp_sidepipes,
    "lp_tail_stacks": lp_tail_stacks,
    "lp_wheel_spoked": lp_wheel_spoked,
    "lp_wheel_monster": lp_wheel_monster,
    "lp_wheel_wagon": lp_wheel_wagon,
    "lp_chainsaw": lp_chainsaw,
    "lp_molotov": lp_molotov,
    "lp_smoke": lp_smoke,
    "lp_oilslick": lp_oilslick,
    "lp_thunderstick": lp_thunderstick,
    "lp_catapult": lp_catapult,
    "lp_chassis_rail": lp_chassis_rail,
    "lp_wheel_slick": lp_wheel_slick,
    "lp_wheel_disc": lp_wheel_disc,
    "lp_steering_wheel": lp_steering_wheel,
    "lp_tail_fin": lp_tail_fin,
    "lp_roof_rack": lp_roof_rack,
    "lp_wreckingball": lp_wreckingball,
    "lp_nose_plow": lp_nose_plow,
    "lp_wheel": lp_wheel,
    "lp_grille": lp_grille,
    "lp_fueltank": lp_fueltank,
    "lp_exhaust_stacks": lp_exhaust_stacks,
    "lp_rollcage": lp_rollcage,
    "lp_spikes": lp_spikes,
    "lp_armor_plate": lp_armor_plate,
    "lp_ram_bar": lp_ram_bar,
    "lp_tesla": lp_tesla,
    "lp_nailgun": lp_nailgun,
    "lp_number_plate": lp_number_plate,
}


# ---------- finalize / export / render ----------
def finalize(obj):
    # merge, recalc normals, shade flat (low-poly look), center on origin
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data); bm.free()
    me = obj.data
    bb = [v.co for v in me.vertices]
    c = mathutils.Vector(((min(p.x for p in bb) + max(p.x for p in bb)) / 2,
                          (min(p.y for p in bb) + max(p.y for p in bb)) / 2,
                          (min(p.z for p in bb) + max(p.z for p in bb)) / 2))
    for v in me.vertices:
        v.co -= c
    me.update()
    return [max(p[i] for p in bb) - min(p[i] for p in bb) for i in range(3)]


def render(obj, name, dims):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
    sc.display.shading.single_color = (0.62, 0.62, 0.64); sc.display.shading.show_cavity = True
    sc.render.resolution_x = 512; sc.render.resolution_y = 512
    os.makedirs(REVIEW, exist_ok=True)
    r = max(dims) * 2.0 or 2.0
    cam_d = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_d)
    bpy.context.collection.objects.link(cam); sc.camera = cam
    for nm, ang in {"front": 0, "tq": 45, "side": 90}.items():
        a = math.radians(ang)
        cam.location = (math.sin(a) * r, -math.cos(a) * r, max(dims) * 0.5)
        d = mathutils.Vector((0, 0, 0)) - cam.location
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(REVIEW, f"{name}_{nm}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = argv[argv.index("--only") + 1:] if "--only" in argv else list(BUILDERS)
    os.makedirs(LP_DIR, exist_ok=True)
    for name in only:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = BUILDERS[name]()
        dims = finalize(obj)
        bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True)
        out = os.path.join(LP_DIR, f"{name}.glb")
        bpy.ops.export_scene.gltf(filepath=out, use_selection=True, export_format="GLB",
                                  export_materials="NONE")
        tris = sum((len(p.vertices) - 2) for p in obj.data.polygons)
        print(f"BUILT {name}  tris={tris}  bbox={[round(d,2) for d in dims]}  -> {out}", flush=True)
        render(obj, name, dims)
    print("LP_DONE", flush=True)


if __name__ == "__main__":
    main()
