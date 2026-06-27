"""render_rootmotion.py — headless proof-frame renderer for an animated character FBX.

Imports an animated FBX (e.g. a retarget_mocap.py output), auto-frames it across the
WHOLE clip so forward root-motion travel stays in view, gives the (material-less
UniRig) mesh a visible matte material, and renders a handful of frames to PNG.

Bakes in the gotchas root-caused during the walk validation (see validation/VALIDATION.md):
- **mesh-deform fix:** an imported mesh that lost its Armature modifier renders as a
  static rest pose; this re-binds each mesh's Armature modifier to the imported
  armature so the body actually deforms per frame.
- **framing fix:** the character imports at UniRig bind scale and *translates* with
  root motion, so a naive camera frames empty space or loses the subject mid-clip.
  We sweep every frame's evaluated mesh bounds and fit an ortho camera to that volume.
- **visibility fix:** UniRig output drops materials → low-contrast render; we assign a
  force-opaque matte material.

Also prints HIP_TRAVEL (hips world displacement over the clip) so root motion is
measurable, not just visible.

Usage (headless):
    blender --background --python render_rootmotion.py -- <animated.fbx> <out_dir> [frames_csv] [view]
      view: ortho34 (default, gait) | front | top (root-motion travel)
"""
import bpy, sys, os, math
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FBX, OUTDIR = a[0], a[1]
FRAMES = [int(x) for x in a[2].split(",")] if len(a) > 2 and a[2] else None
VIEW = a[3] if len(a) > 3 else "ortho34"
os.makedirs(OUTDIR, exist_ok=True)


def set_engine():
    """EEVEE across Blender versions (4.2+/5.0 = BLENDER_EEVEE_NEXT)."""
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            bpy.context.scene.render.engine = eng
            return eng
        except (TypeError, ValueError):
            continue
    return bpy.context.scene.render.engine


def main():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    bpy.ops.import_scene.fbx(filepath=FBX)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']

    # mesh-deform fix + visibility: re-bind armature modifier, assign a matte material
    mat = bpy.data.materials.new("proof"); mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.62, 0.46, 0.36, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.7
    for m in meshes:
        mod = next((md for md in m.modifiers if md.type == 'ARMATURE'), None)
        if mod is None:
            mod = m.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        m.data.materials.clear(); m.data.materials.append(mat)

    scene = bpy.context.scene
    f0, f1 = scene.frame_start, scene.frame_end
    frames = FRAMES or [f0, (f0 + f1) // 4, (f0 + f1) // 2, (3 * (f0 + f1)) // 4, f1]

    # sweep evaluated mesh bounds across the whole clip (subject moves with root motion)
    mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
    hip = arm.pose.bones.get("hips")
    hip0 = hipN = None
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for m in meshes:
            me = m.evaluated_get(dg)
            mw = me.matrix_world
            for v in me.data.vertices:
                w = mw @ v.co
                for i in range(3):
                    mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
        if hip is not None:
            p = (arm.matrix_world @ hip.matrix).translation.copy()
            if f == f0:
                hip0 = p
            hipN = p
    center = (mn + mx) * 0.5
    size = mx - mn
    ext = max(size.x, size.y, size.z, 1e-3)

    if hip0 is not None:
        tr = hipN - hip0
        print(f"HIP_TRAVEL total={tr.length:.4f} vec=({tr.x:.3f},{tr.y:.3f},{tr.z:.3f})")
        print("HAS_ROOT_MOTION" if tr.length > 0.02 * ext else "NO_ROOT_MOTION")

    # camera (ortho, fit to swept volume)
    cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam); scene.camera = cam
    dist = ext * 3.0 + 1.0
    if VIEW == "top":
        cam.location = center + Vector((0, 0, dist))
    elif VIEW == "front":
        cam.location = center + Vector((0, -dist, 0))
    else:  # ortho34
        cam.location = center + Vector((dist * 0.7, -dist * 0.7, dist * 0.45))
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = ext * 1.25

    # lighting: sun + ambient world so unlit sides aren't black
    ld = bpy.data.lights.new("sun", 'SUN'); ld.energy = 4.0
    lo = bpy.data.objects.new("sun", ld); scene.collection.objects.link(lo)
    lo.rotation_euler = (math.radians(55), 0.0, math.radians(35))
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world; world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.18, 0.19, 0.21, 1.0)
        bg.inputs[1].default_value = 0.6

    eng = set_engine()
    scene.render.resolution_x = scene.render.resolution_y = 720
    scene.render.film_transparent = False
    base = os.path.splitext(os.path.basename(FBX))[0]
    for f in frames:
        scene.frame_set(f)
        scene.render.filepath = os.path.join(OUTDIR, f"{base}_{VIEW}_f{f:03d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"RENDERED f{f}")
    print(f"RENDER_DONE engine={eng} view={VIEW} frames={frames}")


main()
