import bpy, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=sys.argv[-1])
o = [x for x in bpy.context.scene.objects if x.type == "MESH"][0]
me = o.data
print("DIAG color_attributes:", [(a.name, a.domain, a.data_type) for a in me.color_attributes])
print("DIAG attributes:", [(a.name, a.domain, a.data_type) for a in me.attributes])
print("DIAG has_legacy_vertex_colors:", hasattr(me, "vertex_colors") and len(me.vertex_colors) if hasattr(me, "vertex_colors") else "n/a")
print("DIAG materials:", [m.name if m else None for m in me.materials])
# sample first color if any color-typed attribute exists
for a in me.attributes:
    if a.data_type in ("FLOAT_COLOR", "BYTE_COLOR"):
        print("DIAG sample", a.name, a.domain, "->", tuple(round(c, 3) for c in a.data[0].color))
        break
