"""validate_animation_mesh — objective mesh-integrity gate for an animated character.

Catches the two failure classes that pose/travel metrics miss and that gates have
historically rubber-stamped (GS1 2026-07-02):
  - WEIGHT MELTING (unirig-skin-weights-melt-use-accurig): limbs stretch to spikes
    -> per-frame EDGE STRETCH vs rest explodes (healthy deform stays ~<2x; melting
    hits 5-50x).
  - SCRAMBLE/COLLAPSE (crossed skinning, stale locations): body chunks displaced
    -> evaluated BOUNDS blow up or collapse vs the rest mesh.

Method: import the animated file, re-bind armature modifiers (FBX import can drop
them), then at N sampled frames evaluate the skinned mesh (depsgraph) and compare
every edge's length against the REST mesh. Reports p99 and max stretch plus the
bounds ratio, and a hard VERDICT line the batch gate parses.

Thresholds (defaults; override via argv):
  p99 edge stretch  <= 2.0   (worst 1% of edges may stretch 2x)
  bounds ratio      within [0.5, 1.8] of rest diagonal

Prints:  MESH_METRICS frame=<f> p99=<x> max=<x> bounds_ratio=<x>
         MESH_VERDICT OK|MELT p99_worst=<x> max_worst=<x> bounds_worst=<x>

Usage: blender --background --python validate_animation_mesh.py -- \
           <animated.fbx|glb> [n_samples=5] [p99_limit=2.0] [bounds_lo=0.5] [bounds_hi=1.8]
"""
import bpy
import sys

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PATH = a[0]
N = int(a[1]) if len(a) > 1 else 5
P99_LIMIT = float(a[2]) if len(a) > 2 else 2.0
B_LO = float(a[3]) if len(a) > 3 else 0.5
B_HI = float(a[4]) if len(a) > 4 else 1.8

bpy.ops.wm.read_factory_settings(use_empty=True)
if PATH.lower().endswith((".glb", ".gltf")):
    bpy.ops.import_scene.gltf(filepath=PATH)
else:
    bpy.ops.import_scene.fbx(filepath=PATH)

arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
meshes = [o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) > 100]
if not meshes:
    print("MESH_VERDICT NO_MESH")
    sys.exit(1)
obj = max(meshes, key=lambda o: len(o.data.vertices))

# re-bind armature modifier (same fix as render_rootmotion: FBX import can
# leave the modifier unlinked, which silently validates a static rest pose)
if arm is not None:
    bound = False
    for m in obj.modifiers:
        if m.type == "ARMATURE":
            m.object = arm
            bound = True
    if not bound:
        obj.modifiers.new("Armature", "ARMATURE").object = arm

sc = bpy.context.scene
f0, f1 = sc.frame_start, sc.frame_end

# rest-mesh edge lengths + bounds diagonal (obj.data is the bind mesh)
rest = obj.data
rest_len = {}
for e in rest.edges:
    v0, v1 = e.vertices
    d = (rest.vertices[v0].co - rest.vertices[v1].co).length
    if d > 1e-9:
        rest_len[(v0, v1)] = d
bb = [v.co for v in rest.vertices]
rest_min = [min(c[i] for c in bb) for i in range(3)]
rest_max = [max(c[i] for c in bb) for i in range(3)]
rest_diag = sum((rest_max[i] - rest_min[i]) ** 2 for i in range(3)) ** 0.5

frames = sorted({f0 + round(i * (f1 - f0) / max(1, N - 1)) for i in range(N)})
worst_p99 = 0.0
worst_max = 0.0
worst_bounds = 1.0
dg = bpy.context.evaluated_depsgraph_get()
for f in frames:
    sc.frame_set(f)
    dg.update()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    ratios = []
    for (v0, v1), rl in rest_len.items():
        d = (me.vertices[v0].co - me.vertices[v1].co).length
        ratios.append(d / rl)
    ratios.sort()
    p99 = ratios[int(len(ratios) * 0.99)] if ratios else 1.0
    mx = ratios[-1] if ratios else 1.0
    cb = [v.co for v in me.vertices]
    cmin = [min(c[i] for c in cb) for i in range(3)]
    cmax = [max(c[i] for c in cb) for i in range(3)]
    diag = sum((cmax[i] - cmin[i]) ** 2 for i in range(3)) ** 0.5
    bratio = diag / rest_diag if rest_diag > 1e-9 else 1.0
    ev.to_mesh_clear()
    print(f"MESH_METRICS frame={f} p99={p99:.3f} max={mx:.3f} bounds_ratio={bratio:.3f}")
    worst_p99 = max(worst_p99, p99)
    worst_max = max(worst_max, mx)
    if abs(bratio - 1.0) > abs(worst_bounds - 1.0):
        worst_bounds = bratio

ok = worst_p99 <= P99_LIMIT and B_LO <= worst_bounds <= B_HI
print(f"MESH_VERDICT {'OK' if ok else 'MELT'} "
      f"p99_worst={worst_p99:.3f} max_worst={worst_max:.3f} bounds_worst={worst_bounds:.3f}")
