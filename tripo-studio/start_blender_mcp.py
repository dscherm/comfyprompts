import addon_utils, bpy
LOG = r"D:\Projects\comfyui-toolchain\tripo-studio\start_blender_mcp.log"
out = []
try:
    addon_utils.enable("Tripo3d_Blender_Bridge", default_set=False)
    out.append("tripo: session-enabled")
except Exception as e:
    out.append(f"tripo: ERROR {e!r}")
try:
    addon_utils.enable("blender_mcp", default_set=True)
    bpy.ops.wm.save_userpref()
    out.append("blender_mcp: enabled and saved to preferences")
except Exception as e:
    out.append(f"blender_mcp: ERROR {e!r}")
def _start():
    try:
        bpy.ops.blendermcp.start_server()
        out.append("blender_mcp server: start requested on port %d" % bpy.context.scene.blendermcp_port)
    except Exception as e:
        out.append(f"blender_mcp server: ERROR {e!r}")
    open(LOG, "w", encoding="utf-8").write("\n".join(out))
    return None
bpy.app.timers.register(_start, first_interval=2.0)
