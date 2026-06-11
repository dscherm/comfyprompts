"""Analyze material deduplication potential across GLB model files.

Scans all GLB files in a directory tree, extracts material properties using
pygltflib, groups materials by similarity, and reports deduplication potential.

Usage:
    python dedup_materials.py [--models-dir PATH] [--threshold FLOAT]

Defaults to scanning:
    D:/Projects/berserkr-godot/games/berserkr/assets/models/
"""

import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

try:
    import pygltflib
except ImportError:
    print("ERROR: pygltflib is required. Install with: pip install pygltflib")
    sys.exit(1)


DEFAULT_MODELS_DIR = r"D:\Projects\berserkr-godot\games\berserkr\assets\models"
COLOR_THRESHOLD = 0.05  # Max per-channel difference to consider colors "same"


@dataclass
class MaterialInfo:
    """Extracted material properties from a GLB."""
    file_path: str
    material_index: int
    name: str
    base_color_factor: tuple  # (r, g, b, a)
    metallic_factor: float
    roughness_factor: float
    base_color_texture_idx: int | None  # index into gltf.images
    metallic_roughness_texture_idx: int | None
    normal_texture_idx: int | None
    emissive_texture_idx: int | None
    emissive_factor: tuple  # (r, g, b)
    alpha_mode: str
    double_sided: bool
    # For grouping: image sizes/hashes when available
    base_color_image_size: int = 0  # bytes in buffer
    base_color_image_mime: str = ""


@dataclass
class MaterialGroup:
    """A group of similar materials."""
    canonical: MaterialInfo  # representative material
    members: list = field(default_factory=list)

    @property
    def count(self):
        return len(self.members)

    @property
    def files(self):
        return sorted(set(m.file_path for m in self.members))


def _get_texture_image_index(gltf, texture_info):
    """Resolve a textureInfo to an image index, or None."""
    if texture_info is None:
        return None
    tex_idx = texture_info.index
    if tex_idx is None or not gltf.textures or tex_idx >= len(gltf.textures):
        return None
    tex = gltf.textures[tex_idx]
    return tex.source


def _get_image_buffer_size(gltf, image_idx):
    """Get the byte size of an embedded image buffer, or 0."""
    if image_idx is None or not gltf.images:
        return 0
    if image_idx >= len(gltf.images):
        return 0
    img = gltf.images[image_idx]
    if img.bufferView is None:
        return 0
    if not gltf.bufferViews or img.bufferView >= len(gltf.bufferViews):
        return 0
    bv = gltf.bufferViews[img.bufferView]
    return bv.byteLength or 0


def _get_image_mime(gltf, image_idx):
    """Get the MIME type of an embedded image, or empty string."""
    if image_idx is None or not gltf.images:
        return ""
    if image_idx >= len(gltf.images):
        return ""
    img = gltf.images[image_idx]
    return img.mimeType or ""


def extract_materials(glb_path):
    """Extract all materials from a GLB file.

    Returns a list of MaterialInfo, or empty list on error.
    """
    try:
        gltf = pygltflib.GLTF2().load(str(glb_path))
    except Exception as e:
        print(f"  WARNING: Failed to load {glb_path}: {e}")
        return []

    if not gltf.materials:
        return []

    materials = []
    for idx, mat in enumerate(gltf.materials):
        pbr = mat.pbrMetallicRoughness

        # Base color
        if pbr and pbr.baseColorFactor:
            bcf = tuple(pbr.baseColorFactor)
        else:
            bcf = (1.0, 1.0, 1.0, 1.0)

        # Metallic / roughness
        metallic = pbr.metallicFactor if pbr and pbr.metallicFactor is not None else 1.0
        roughness = pbr.roughnessFactor if pbr and pbr.roughnessFactor is not None else 1.0

        # Texture indices (resolved to image indices)
        base_tex = _get_texture_image_index(
            gltf, pbr.baseColorTexture if pbr else None
        )
        mr_tex = _get_texture_image_index(
            gltf, pbr.metallicRoughnessTexture if pbr else None
        )
        normal_tex = _get_texture_image_index(
            gltf, mat.normalTexture
        )
        emissive_tex = _get_texture_image_index(
            gltf, mat.emissiveTexture
        )

        # Emissive factor
        ef = tuple(mat.emissiveFactor) if mat.emissiveFactor else (0.0, 0.0, 0.0)

        # Alpha mode
        alpha_mode = mat.alphaMode or "OPAQUE"
        double_sided = bool(mat.doubleSided)

        # Image metadata for base color
        bc_img_size = _get_image_buffer_size(gltf, base_tex)
        bc_img_mime = _get_image_mime(gltf, base_tex)

        info = MaterialInfo(
            file_path=str(glb_path),
            material_index=idx,
            name=mat.name or f"material_{idx}",
            base_color_factor=bcf,
            metallic_factor=metallic,
            roughness_factor=roughness,
            base_color_texture_idx=base_tex,
            metallic_roughness_texture_idx=mr_tex,
            normal_texture_idx=normal_tex,
            emissive_texture_idx=emissive_tex,
            emissive_factor=ef,
            alpha_mode=alpha_mode,
            double_sided=double_sided,
            base_color_image_size=bc_img_size,
            base_color_image_mime=bc_img_mime,
        )
        materials.append(info)

    return materials


def _color_distance(a, b):
    """Euclidean distance between two color tuples."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _material_signature(mat, color_threshold=COLOR_THRESHOLD):
    """Create a grouping signature for a material.

    Materials with the same signature are considered duplicates.
    Colors are quantized to the threshold grid.
    """
    # Quantize color channels to threshold steps
    def quantize(v, step):
        if step <= 0:
            return round(v, 4)
        return round(round(v / step) * step, 4)

    bc = tuple(quantize(c, color_threshold) for c in mat.base_color_factor)
    metallic = quantize(mat.metallic_factor, 0.05)
    roughness = quantize(mat.roughness_factor, 0.05)
    emissive = tuple(quantize(c, color_threshold) for c in mat.emissive_factor)

    # Texture presence flags (we can't compare actual pixel data across GLBs
    # without extracting buffers, so we use size + mime as a proxy)
    has_base_tex = mat.base_color_texture_idx is not None
    has_mr_tex = mat.metallic_roughness_texture_idx is not None
    has_normal_tex = mat.normal_texture_idx is not None
    has_emissive_tex = mat.emissive_texture_idx is not None

    sig = (
        bc,
        metallic,
        roughness,
        emissive,
        mat.alpha_mode,
        mat.double_sided,
        has_base_tex,
        has_mr_tex,
        has_normal_tex,
        has_emissive_tex,
        mat.base_color_image_size,
        mat.base_color_image_mime,
    )
    return sig


def scan_directory(models_dir, color_threshold=COLOR_THRESHOLD):
    """Scan all GLBs in directory, extract and group materials.

    Returns (all_materials, groups_by_signature).
    """
    models_dir = Path(models_dir)
    glb_files = sorted(
        p for p in models_dir.rglob("*.glb")
        if "_backup" not in str(p)
    )

    print(f"Found {len(glb_files)} GLB files in {models_dir}")
    print()

    all_materials = []
    files_scanned = 0
    files_with_errors = 0

    for glb_path in glb_files:
        mats = extract_materials(glb_path)
        if mats:
            all_materials.extend(mats)
        else:
            # Could be error or genuinely no materials
            pass
        files_scanned += 1

    # Group by signature
    groups = defaultdict(list)
    for mat in all_materials:
        sig = _material_signature(mat, color_threshold)
        groups[sig].append(mat)

    # Convert to MaterialGroup
    material_groups = {}
    for sig, members in groups.items():
        material_groups[sig] = MaterialGroup(
            canonical=members[0],
            members=members,
        )

    return all_materials, material_groups, files_scanned


def _format_color(c):
    """Format a color tuple nicely."""
    return f"({', '.join(f'{v:.3f}' for v in c)})"


def _estimate_material_memory(mat):
    """Estimate memory footprint of a material's textures in bytes."""
    # Each material's main cost is its textures. We use the embedded image
    # buffer size as a proxy for the base color texture. For a rough estimate,
    # multiply by 2 (other textures like normal/MR tend to be similar size).
    base = mat.base_color_image_size
    if base > 0:
        # Assume MR + normal are similar size when present
        multiplier = 1
        if mat.metallic_roughness_texture_idx is not None:
            multiplier += 1
        if mat.normal_texture_idx is not None:
            multiplier += 1
        if mat.emissive_texture_idx is not None:
            multiplier += 1
        return base * multiplier
    else:
        # Flat color material: negligible memory (~100 bytes for parameters)
        return 100


def generate_report(all_materials, groups, files_scanned, color_threshold):
    """Print the deduplication analysis report."""
    total_mats = len(all_materials)
    unique_patterns = len(groups)
    duplicate_patterns = sum(1 for g in groups.values() if g.count > 1)
    singleton_patterns = unique_patterns - duplicate_patterns

    # Files contributing materials
    all_files = sorted(set(m.file_path for m in all_materials))

    # Top duplicated groups
    sorted_groups = sorted(groups.values(), key=lambda g: g.count, reverse=True)

    # Memory estimation
    total_memory = 0
    deduped_memory = 0
    for g in groups.values():
        per_mat_mem = _estimate_material_memory(g.canonical)
        total_memory += per_mat_mem * g.count
        deduped_memory += per_mat_mem  # Only keep one copy

    savings = total_memory - deduped_memory

    # Materials by category (based on directory)
    category_counts = defaultdict(int)
    for mat in all_materials:
        rel = os.path.relpath(mat.file_path, DEFAULT_MODELS_DIR)
        parts = Path(rel).parts
        if len(parts) >= 2:
            category_counts[f"{parts[0]}/{parts[1]}"] += 1
        elif len(parts) >= 1:
            category_counts[parts[0]] += 1

    # Textured vs flat materials
    textured = sum(1 for m in all_materials if m.base_color_texture_idx is not None)
    flat = total_mats - textured

    # ======== Print Report ========

    print("=" * 72)
    print("  MATERIAL DEDUPLICATION ANALYSIS REPORT")
    print("=" * 72)
    print()

    print(f"  Files scanned:          {files_scanned}")
    print(f"  Files with materials:   {len(all_files)}")
    print(f"  Color threshold:        {color_threshold}")
    print()

    print("-" * 72)
    print("  MATERIAL COUNTS")
    print("-" * 72)
    print(f"  Total materials:        {total_mats}")
    print(f"  Unique patterns:        {unique_patterns}")
    print(f"  Duplicate patterns:     {duplicate_patterns} (appearing 2+ times)")
    print(f"  Singleton patterns:     {singleton_patterns}")
    print(f"  Textured materials:     {textured}")
    print(f"  Flat color materials:   {flat}")
    print()

    if total_mats > 0:
        dup_ratio = (total_mats - unique_patterns) / total_mats * 100
        print(f"  Deduplication ratio:    {dup_ratio:.1f}% of materials are duplicates")
    print()

    print("-" * 72)
    print("  MATERIALS BY CATEGORY")
    print("-" * 72)
    for cat in sorted(category_counts.keys()):
        print(f"  {cat:40s} {category_counts[cat]:4d}")
    print()

    print("-" * 72)
    print("  MEMORY ESTIMATE")
    print("-" * 72)
    print(f"  Total texture memory:   {total_memory / (1024*1024):.2f} MB")
    print(f"  After deduplication:    {deduped_memory / (1024*1024):.2f} MB")
    print(f"  Estimated savings:      {savings / (1024*1024):.2f} MB ({savings / max(total_memory, 1) * 100:.1f}%)")
    print()

    print("-" * 72)
    print("  TOP 10 MOST-DUPLICATED MATERIAL PATTERNS")
    print("-" * 72)
    for rank, group in enumerate(sorted_groups[:10], 1):
        mat = group.canonical
        print(f"\n  #{rank}  ({group.count} instances across {len(group.files)} files)")
        print(f"      Name example:   {mat.name}")
        print(f"      Base color:     {_format_color(mat.base_color_factor)}")
        print(f"      Metallic:       {mat.metallic_factor:.3f}")
        print(f"      Roughness:      {mat.roughness_factor:.3f}")
        print(f"      Emissive:       {_format_color(mat.emissive_factor)}")
        print(f"      Alpha mode:     {mat.alpha_mode}")
        print(f"      Double-sided:   {mat.double_sided}")
        tex_status = []
        if mat.base_color_texture_idx is not None:
            tex_status.append(f"baseColor({mat.base_color_image_size}B)")
        if mat.metallic_roughness_texture_idx is not None:
            tex_status.append("metallicRoughness")
        if mat.normal_texture_idx is not None:
            tex_status.append("normal")
        if mat.emissive_texture_idx is not None:
            tex_status.append("emissive")
        print(f"      Textures:       {', '.join(tex_status) if tex_status else 'none (flat color)'}")

        # Show which files
        if group.count <= 6:
            for fp in group.files:
                print(f"        - {os.path.basename(fp)}")
        else:
            for fp in group.files[:4]:
                print(f"        - {os.path.basename(fp)}")
            print(f"        ... and {len(group.files) - 4} more files")
    print()

    # Additional: materials that appear in many files (cross-file sharing candidates)
    print("-" * 72)
    print("  CROSS-FILE SHARING CANDIDATES")
    print("  (Material patterns appearing in 3+ different files)")
    print("-" * 72)
    cross_file = [
        g for g in sorted_groups
        if len(g.files) >= 3
    ]
    if cross_file:
        for g in cross_file[:15]:
            mat = g.canonical
            has_tex = mat.base_color_texture_idx is not None
            print(f"  [{g.count} mats, {len(g.files)} files] "
                  f"\"{mat.name}\" "
                  f"color={_format_color(mat.base_color_factor)} "
                  f"{'textured' if has_tex else 'flat'}")
    else:
        print("  No material patterns found in 3+ files.")
    print()

    # Flat color duplicates (easy wins for .tres sharing in Godot)
    print("-" * 72)
    print("  EASY WINS: FLAT COLOR DUPLICATES")
    print("  (No textures -- trivially shareable as .tres resources)")
    print("-" * 72)
    flat_dups = [
        g for g in sorted_groups
        if g.count > 1 and g.canonical.base_color_texture_idx is None
    ]
    if flat_dups:
        for g in flat_dups[:15]:
            mat = g.canonical
            print(f"  [{g.count}x] \"{mat.name}\" "
                  f"color={_format_color(mat.base_color_factor)} "
                  f"metallic={mat.metallic_factor:.2f} "
                  f"rough={mat.roughness_factor:.2f}")
    else:
        print("  No flat color duplicates found.")
    print()

    print("=" * 72)
    print("  END OF REPORT")
    print("=" * 72)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze material deduplication potential across GLB files."
    )
    parser.add_argument(
        "--models-dir",
        default=DEFAULT_MODELS_DIR,
        help=f"Root directory to scan (default: {DEFAULT_MODELS_DIR})",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=COLOR_THRESHOLD,
        help=f"Color channel similarity threshold (default: {COLOR_THRESHOLD})",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.models_dir):
        print(f"ERROR: Directory not found: {args.models_dir}")
        sys.exit(1)

    all_materials, groups, files_scanned = scan_directory(
        args.models_dir, args.threshold
    )

    if not all_materials:
        print("No materials found in any GLB files.")
        sys.exit(0)

    generate_report(all_materials, groups, files_scanned, args.threshold)


if __name__ == "__main__":
    main()
