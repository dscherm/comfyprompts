"""sl8_color_sword — assign steel-grey blade + brown grip to a low-poly sword (SL8).

TRELLIS geometry is monochrome. This detects the sword's long axis + the crossguard
(the widest cross-section on the handle half), then paints the narrow band just below
the guard BROWN (the grip) and everything else steel-grey — matching the other weapons
in lowpoly_flat (grey head + brown handle). Position-based, no UVs needed.

Headless Blender:
  blender --background --factory-startup --python sl8_color_sword.py -- <in.glb> <out.glb>
"""
import sys
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
IN, OUT = argv[0], argv[1]
# optional manual grip band (length-fractions from the handle end) overrides
# auto-detection for awkward geometry: ... -- in.glb out.glb <grip_lo> <grip_hi>
OVR = (float(argv[2]), float(argv[3])) if len(argv) > 3 else None

STEEL = (0.55, 0.57, 0.60, 1.0)
BROWN = (0.22, 0.13, 0.06, 1.0)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=IN)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
me = obj.data

# world-space vert coords
co = [obj.matrix_world @ v.co for v in me.vertices]
mn = Vector((min(c[i] for c in co) for i in range(3)))
mx = Vector((max(c[i] for c in co) for i in range(3)))
dims = mx - mn
L = max(range(3), key=lambda i: dims[i])      # long axis (blade length)
perp = [i for i in range(3) if i != L]
span = dims[L] or 1.0

def tpos(c):
    return (c[L] - mn[L]) / span              # 0..1 along the length

NB = 40

def widths(T):
    """max lateral extent per bin, using length-fraction fn T."""
    bw = [0.0] * NB; bc = [[0.0, 0.0] for _ in range(NB)]; bn = [0] * NB
    for c in co:
        b = min(NB - 1, int(T(c) * NB))
        bc[b][0] += c[perp[0]]; bc[b][1] += c[perp[1]]; bn[b] += 1
    for b in range(NB):
        if bn[b]:
            bc[b][0] /= bn[b]; bc[b][1] /= bn[b]
    for c in co:
        b = min(NB - 1, int(T(c) * NB))
        dd = ((c[perp[0]] - bc[b][0]) ** 2 + (c[perp[1]] - bc[b][1]) ** 2) ** 0.5
        bw[b] = max(bw[b], dd)
    return bw, bc

bw0, _ = widths(tpos)
# Orient so the HANDLE (non-tapering) end is at low t: the blade tip end tapers to
# ~zero lateral width, so the extreme bin with the LARGER width is the handle end.
if bw0[NB - 1] > bw0[0]:
    def tpos2(c):
        return 1.0 - (c[L] - mn[L]) / span
else:
    tpos2 = tpos
binw, binc = widths(tpos2)

# guard = widest bin within the HANDLE HALF (bottom 50%); grip is the narrow band
# just below it (with a gap so the guard itself isn't painted).
lower = [b for b in range(NB) if (b + 0.5) / NB < 0.35]
guard_b = max(lower, key=lambda b: binw[b])
guard_t = (guard_b + 0.5) / NB
guard_w = binw[guard_b] or 1.0
if OVR:
    grip_lo, grip_hi = OVR
else:
    grip_hi = guard_t - 0.04
    grip_lo = max(0.02, guard_t - 0.20)

steel = bpy.data.materials.new("steel"); steel.use_nodes = True
steel.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = STEEL
brown = bpy.data.materials.new("grip"); brown.use_nodes = True
brown.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = BROWN
me.materials.clear(); me.materials.append(steel); me.materials.append(brown)

wm = obj.matrix_world
grip_faces = 0
for poly in me.polygons:
    cen = wm @ poly.center
    t = tpos2(cen)
    b = min(NB - 1, int(t * NB))
    lat = ((cen[perp[0]] - binc[b][0]) ** 2 + (cen[perp[1]] - binc[b][1]) ** 2) ** 0.5
    # grip = in the band below the guard AND narrow (excludes the wide guard wings)
    is_grip = (grip_lo <= t <= grip_hi) and (lat < 0.5 * guard_w)
    poly.material_index = 1 if is_grip else 0
    if is_grip:
        grip_faces += 1

for p in me.polygons:
    p.use_smooth = False
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True); bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True,
                          export_animations=False)
print("COLORED %s  guard_t=%.2f grip=[%.2f,%.2f] grip_faces=%d" % (OUT, guard_t, grip_lo, grip_hi, grip_faces))
