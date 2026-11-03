import addon_utils, sys
LOG = r"D:\Projects\comfyui-toolchain\tripo-studio\enable_tripo.log"
lines = []
for name in ("Tripo3d_Blender_Bridge",):
    try:
        mod = addon_utils.enable(name, default_set=False)
        lines.append(f"{name}: enabled={mod is not None}")
    except Exception as e:
        lines.append(f"{name}: ERROR {e!r}")
lines.append("blender-mcp-like addons: " + ", ".join(m.__name__ for m in addon_utils.modules() if "mcp" in m.__name__.lower()))
open(LOG, "w", encoding="utf-8").write("\n".join(lines))
