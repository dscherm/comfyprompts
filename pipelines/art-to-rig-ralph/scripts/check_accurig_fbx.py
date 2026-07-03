"""check_accurig_fbx — verify an AccuRIG FBX export before Unity import.

Asserts (learned the hard way; see memory project-accurig-input-format):
  - the skinned mesh binds in the ARMATURE's space (no shredding)
  - character height ~1.5-2.2m world (cm-unit input was read correctly)
  - a real UV layer (>100 distinct coords — degenerate = all-zeros layer)
  - vertex groups present (skinning)

Prints CHECK lines + a final ACCURIG_FBX OK|FAIL. Exit 0 on OK.

Usage: blender --background --python check_accurig_fbx.py -- <rig.fbx>
"""
import bpy
import sys

path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=path)
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
mesh = max((o for o in bpy.data.objects if o.type == "MESH"),
           key=lambda o: len(o.data.vertices), default=None)
ok = True

if arm is None or mesh is None:
    print("CHECK missing armature or mesh")
    ok = False
else:
    mw = mesh.matrix_world
    zs = [(mw @ v.co).z for v in mesh.data.vertices]
    ys = [(mw @ v.co).y for v in mesh.data.vertices]
    height = max(max(zs) - min(zs), max(ys) - min(ys))  # FBX may be Y-up or Z-up
    print(f"CHECK height={height:.2f}m verts={len(mesh.data.vertices)} "
          f"vgs={len(mesh.vertex_groups)}")
    if not 1.4 <= height <= 2.3:
        print("CHECK FAIL height out of range — wrong input units (OBJ must be cm)")
        ok = False
    if len(mesh.vertex_groups) < 15:
        print("CHECK FAIL too few vertex groups — skinning missing?")
        ok = False

    uvs = mesh.data.uv_layers
    if not uvs:
        print("CHECK FAIL no UV layer — UV-unwrap the mesh BEFORE AccuRIG")
        ok = False
    else:
        data = uvs[0].data
        distinct = len({(round(d.uv[0], 3), round(d.uv[1], 3)) for d in data[:5000]})
        print(f"CHECK uv_distinct={distinct}")
        if distinct < 100:
            print("CHECK FAIL degenerate UVs (all-zero layer) — "
                  "UV-unwrap the mesh BEFORE AccuRIG")
            ok = False

    # bind sanity: at rest the armature deform must be RIGID. A rigid offset
    # (Y-up conventions) is fine; SHREDDING (axis-baggage input) stretches
    # edges — measure per-edge stretch, same principle as the animation gate.
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg).to_mesh()
    ratios = []
    for e in list(mesh.data.edges)[::5]:
        v0, v1 = e.vertices
        rl = (mesh.data.vertices[v0].co - mesh.data.vertices[v1].co).length
        if rl > 1e-9:
            el = (ev.vertices[v0].co - ev.vertices[v1].co).length
            ratios.append(el / rl)
    mesh.evaluated_get(dg).to_mesh_clear()
    ratios.sort()
    p50 = ratios[len(ratios) // 2] if ratios else 1.0
    p99 = ratios[int(len(ratios) * 0.99)] if ratios else 1.0
    spread = p99 / p50 if p50 > 1e-9 else 999.0
    # a uniform scale (armature/mesh unit conventions) is shape-preserving and
    # a small tail of rest-pose deviation is normal on AccuRIG twist bones.
    # Calibrated on ground truths (2026-07-03): GOOD Rookie rig spread=1.97,
    # axis-baggage SHREDDED export spread=18.7 -> threshold 4.0.
    print(f"CHECK bind_edge_stretch p50={p50:.3f} p99={p99:.3f} spread={spread:.2f}")
    if spread > 4.0:
        print("CHECK FAIL non-rigid bind (mesh binds in a different frame than "
              "the armature; axis-baggage input?) — re-export from a plain OBJ")
        ok = False

print("ACCURIG_FBX", "OK" if ok else "FAIL")
sys.exit(0 if ok else 1)
