"""Validate GLB model files for material, UV, and texture integrity.

Can run in three modes depending on available libraries:
    1. bpy (Blender Python) -- full validation of materials, UVs, textures
    2. pygltflib -- structural validation without Blender
    3. Fallback -- basic file size / header checks only

Usage as module:
    from validate_glb import validate_glb
    report = validate_glb("/path/to/model.glb")
    if report["warnings"]:
        for w in report["warnings"]:
            print(f"  WARNING: {w}")

Usage standalone:
    python validate_glb.py model.glb [model2.glb ...]

Returns a report dict:
    {
        "path": str,
        "valid": bool,           # False only if file is unreadable / corrupt
        "file_size_bytes": int,
        "warnings": [str, ...],  # Non-fatal issues found
        "errors": [str, ...],    # Fatal issues
        "meshes": int,
        "materials": int,
        "textures": int,
        "has_armature": bool,
        "backend": "bpy" | "pygltflib" | "fallback",
    }
"""

import os
import struct
import sys


# ============================================================
# Backend detection
# ============================================================

_BACKEND = "fallback"

try:
    import bpy
    _BACKEND = "bpy"
except ImportError:
    pass

if _BACKEND == "fallback":
    try:
        import pygltflib
        _BACKEND = "pygltflib"
    except ImportError:
        pass


# ============================================================
# GLB header validation (works without any dependencies)
# ============================================================

_GLB_MAGIC = 0x46546C67  # 'glTF' in little-endian


def _validate_glb_header(path):
    """Check GLB magic number and version. Returns (ok, version, length, error_msg)."""
    try:
        with open(path, "rb") as f:
            header = f.read(12)
    except OSError as e:
        return False, 0, 0, f"Cannot read file: {e}"

    if len(header) < 12:
        return False, 0, 0, "File too small to be a valid GLB (< 12 bytes)"

    magic, version, length = struct.unpack("<III", header)
    if magic != _GLB_MAGIC:
        return False, 0, 0, f"Bad GLB magic: 0x{magic:08X} (expected 0x{_GLB_MAGIC:08X})"

    if version not in (1, 2):
        return False, version, length, f"Unknown glTF version: {version}"

    return True, version, length, ""


# ============================================================
# Fallback validator (no dependencies)
# ============================================================

def _validate_fallback(path):
    """Basic validation using only file size and GLB header."""
    report = _make_report(path, "fallback")

    file_size = os.path.getsize(path)
    report["file_size_bytes"] = file_size

    ok, version, length, err = _validate_glb_header(path)
    if not ok:
        report["errors"].append(err)
        report["valid"] = False
        return report

    if file_size < 1024:
        report["warnings"].append(f"GLB is suspiciously small ({file_size} bytes)")

    if file_size != length:
        report["warnings"].append(
            f"GLB header says {length} bytes but file is {file_size} bytes"
        )

    report["warnings"].append(
        "Limited validation (no bpy or pygltflib): cannot check materials, UVs, or textures"
    )
    return report


# ============================================================
# pygltflib validator
# ============================================================

def _validate_pygltflib(path):
    """Structural validation using pygltflib (no Blender needed)."""
    report = _make_report(path, "pygltflib")
    report["file_size_bytes"] = os.path.getsize(path)

    ok, version, length, err = _validate_glb_header(path)
    if not ok:
        report["errors"].append(err)
        report["valid"] = False
        return report

    try:
        gltf = pygltflib.GLTF2().load(path)
    except Exception as e:
        report["errors"].append(f"pygltflib failed to parse: {e}")
        report["valid"] = False
        return report

    # Count meshes
    mesh_count = len(gltf.meshes) if gltf.meshes else 0
    report["meshes"] = mesh_count
    if mesh_count == 0:
        report["warnings"].append("No meshes found in GLB")

    # Count materials
    mat_count = len(gltf.materials) if gltf.materials else 0
    report["materials"] = mat_count
    if mat_count == 0:
        report["warnings"].append("No materials defined")

    # Count textures
    tex_count = len(gltf.textures) if gltf.textures else 0
    report["textures"] = tex_count

    # Count images
    image_count = len(gltf.images) if gltf.images else 0

    # Check for armature (skins)
    has_skin = bool(gltf.skins) and len(gltf.skins) > 0
    report["has_armature"] = has_skin

    # Validate meshes have materials and UV maps
    if gltf.meshes:
        for mesh_idx, mesh in enumerate(gltf.meshes):
            mesh_name = mesh.name or f"mesh_{mesh_idx}"
            has_material = False
            has_uvs = False

            if mesh.primitives:
                for prim_idx, prim in enumerate(mesh.primitives):
                    if prim.material is not None:
                        has_material = True

                    # Check for TEXCOORD_0 attribute (UV map)
                    if prim.attributes and hasattr(prim.attributes, 'TEXCOORD_0'):
                        if prim.attributes.TEXCOORD_0 is not None:
                            has_uvs = True

            if not has_material:
                report["warnings"].append(f"Mesh '{mesh_name}' has no material assigned")

            if has_material and not has_uvs:
                # Only warn about missing UVs if the mesh has a textured material
                if tex_count > 0:
                    report["warnings"].append(
                        f"Mesh '{mesh_name}' has materials but no UV map (TEXCOORD_0)"
                    )

    # Validate textures reference valid images
    if gltf.textures:
        for tex_idx, tex in enumerate(gltf.textures):
            if tex.source is not None:
                if tex.source < 0 or tex.source >= image_count:
                    report["warnings"].append(
                        f"Texture {tex_idx} references invalid image index {tex.source}"
                    )

    # Validate images have data
    if gltf.images:
        for img_idx, img in enumerate(gltf.images):
            if img.bufferView is None and img.uri is None:
                report["warnings"].append(
                    f"Image {img_idx} ('{img.name or '?'}') has no data source"
                )

    return report


# ============================================================
# bpy (Blender Python) validator -- most thorough
# ============================================================

def _validate_bpy(path):
    """Full validation using Blender's Python API."""
    report = _make_report(path, "bpy")
    report["file_size_bytes"] = os.path.getsize(path)

    ok, version, length, err = _validate_glb_header(path)
    if not ok:
        report["errors"].append(err)
        report["valid"] = False
        return report

    # Import into a clean scene
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=path)
    except Exception as e:
        report["errors"].append(f"Blender failed to import GLB: {e}")
        report["valid"] = False
        return report

    # Gather objects
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']

    report["meshes"] = len(meshes)
    report["materials"] = len(bpy.data.materials)
    report["textures"] = len(bpy.data.images)
    report["has_armature"] = len(armatures) > 0

    if len(meshes) == 0:
        report["warnings"].append("No mesh objects found in GLB")

    if len(bpy.data.materials) == 0:
        report["warnings"].append("No materials defined")

    # Validate each mesh
    for mesh_obj in meshes:
        mesh_data = mesh_obj.data
        mesh_name = mesh_obj.name

        # Check materials
        if len(mesh_obj.material_slots) == 0:
            report["warnings"].append(f"Mesh '{mesh_name}' has no material slots")
        else:
            for slot_idx, slot in enumerate(mesh_obj.material_slots):
                if slot.material is None:
                    report["warnings"].append(
                        f"Mesh '{mesh_name}' slot {slot_idx} has empty material"
                    )

        # Check UV maps
        uv_layers = mesh_data.uv_layers
        has_uvs = len(uv_layers) > 0

        # Check if mesh has textured materials (needs UVs)
        has_textured_mat = False
        for slot in mesh_obj.material_slots:
            if slot.material and slot.material.use_nodes:
                for node in slot.material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        has_textured_mat = True
                        break

        if has_textured_mat and not has_uvs:
            report["warnings"].append(
                f"Mesh '{mesh_name}' has textured materials but no UV maps"
            )

        # Check UV layer data isn't all zeros
        if has_uvs:
            for uv_layer in uv_layers:
                all_zero = True
                sample_size = min(100, len(uv_layer.data))
                for j in range(sample_size):
                    uv = uv_layer.data[j].uv
                    if abs(uv[0]) > 1e-6 or abs(uv[1]) > 1e-6:
                        all_zero = False
                        break
                if all_zero and len(uv_layer.data) > 0:
                    report["warnings"].append(
                        f"Mesh '{mesh_name}' UV layer '{uv_layer.name}' appears to be all zeros"
                    )

        # Check vertex count
        if len(mesh_data.vertices) == 0:
            report["warnings"].append(f"Mesh '{mesh_name}' has 0 vertices")

        # Check for degenerate faces
        if len(mesh_data.polygons) == 0:
            report["warnings"].append(f"Mesh '{mesh_name}' has 0 polygons")

    # Validate textures have non-zero dimensions
    for img in bpy.data.images:
        if img.size[0] == 0 or img.size[1] == 0:
            report["warnings"].append(
                f"Texture '{img.name}' has zero dimensions ({img.size[0]}x{img.size[1]})"
            )
        elif img.size[0] < 4 or img.size[1] < 4:
            report["warnings"].append(
                f"Texture '{img.name}' is very small ({img.size[0]}x{img.size[1]})"
            )

    # Check armature details if present
    for arm_obj in armatures:
        bone_count = len(arm_obj.data.bones)
        if bone_count == 0:
            report["warnings"].append(
                f"Armature '{arm_obj.name}' has 0 bones"
            )
        elif bone_count < 5:
            report["warnings"].append(
                f"Armature '{arm_obj.name}' has very few bones ({bone_count})"
            )

    return report


# ============================================================
# Report helper
# ============================================================

def _make_report(path, backend):
    """Create an empty report dict."""
    return {
        "path": str(path),
        "valid": True,
        "file_size_bytes": 0,
        "warnings": [],
        "errors": [],
        "meshes": 0,
        "materials": 0,
        "textures": 0,
        "has_armature": False,
        "backend": backend,
    }


# ============================================================
# Public API
# ============================================================

def validate_glb(path):
    """Validate a GLB file and return a report dict.

    Automatically selects the best available backend:
        bpy > pygltflib > fallback (header + size only)

    Args:
        path: Path to a .glb file.

    Returns:
        Report dict with keys: path, valid, file_size_bytes, warnings,
        errors, meshes, materials, textures, has_armature, backend.
    """
    path = str(path)

    if not os.path.exists(path):
        report = _make_report(path, _BACKEND)
        report["errors"].append(f"File not found: {path}")
        report["valid"] = False
        return report

    if _BACKEND == "bpy":
        return _validate_bpy(path)
    elif _BACKEND == "pygltflib":
        return _validate_pygltflib(path)
    else:
        return _validate_fallback(path)


def validate_glb_batch(paths):
    """Validate multiple GLB files. Returns list of report dicts.

    Continues on failure so one bad file does not block the rest.
    """
    reports = []
    for path in paths:
        try:
            report = validate_glb(path)
        except Exception as e:
            report = _make_report(path, _BACKEND)
            report["errors"].append(f"Unexpected error: {e}")
            report["valid"] = False
        reports.append(report)
    return reports


# ============================================================
# CLI entry point
# ============================================================

def main():
    """Validate GLB files from command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python validate_glb.py <file.glb> [file2.glb ...]")
        print(f"  Backend: {_BACKEND}")
        sys.exit(1)

    paths = sys.argv[1:]
    total_warnings = 0
    total_errors = 0

    for path in paths:
        report = validate_glb(path)
        status = "OK" if report["valid"] and not report["warnings"] else "WARN" if report["valid"] else "FAIL"
        size_kb = report["file_size_bytes"] / 1024

        print(f"\n[{status}] {path} ({size_kb:.1f} KB, backend={report['backend']})")
        print(f"  Meshes: {report['meshes']}  Materials: {report['materials']}  "
              f"Textures: {report['textures']}  Armature: {report['has_armature']}")

        for err in report["errors"]:
            print(f"  ERROR: {err}")
            total_errors += 1

        for warn in report["warnings"]:
            print(f"  WARNING: {warn}")
            total_warnings += 1

    print(f"\n{'=' * 50}")
    print(f"Validated {len(paths)} file(s): {total_errors} error(s), {total_warnings} warning(s)")

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
