"""build_tile_topdown_dataset — curate the CC0 tile_topdown training set (Task TX5).

Takes the license-verified CC0 downloads under E:/ai-training/_raw/tile_topdown/
(each source page independently confirmed CC0 — see the manifest), applies a
hand-curated selection (drops level mockups, framed/bordered slabs, tiny
spritesheets, and near-duplicate flats), encodes the terrain family in each
filename, then runs the trainer-agnostic prep_dataset.py to normalize into
E:/ai-training/datasets/tile_topdown (max-edge 1024, RGB). Finally writes the
short SDXL tag captions and the provenance manifest.

Caption template (tile_loras_spec.md §3):
    tile_topdown, <terrain> tile, top-down RPG tileset, seamless texture, even lighting

Run with the project venv (Pillow):
    "D:/Projects/ComfyUI/venv/Scripts/python.exe" scripts/train_lora/build_tile_topdown_dataset.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = Path("E:/ai-training/_raw/tile_topdown")
CURATED = Path("E:/ai-training/_raw/tile_topdown_curated")
OUT = Path("E:/ai-training/datasets/tile_topdown")
PREP = HERE / "prep_dataset.py"

# Curated selection: (relative path under RAW, terrain family, caption terrain phrase).
# Rationale for exclusions is in the manifest; this list is the curation decision.
CURATED_SELECTION: list[tuple[str, str, str]] = [
    # grass
    ("oga_ground_textures_forkotlow/grass_1_0.png", "grass", "grass"),
    ("oga_ground_textures_forkotlow/grass_2.jpg", "grass", "grass"),
    ("oga_ground_textures_forkotlow/dry_grass.jpg", "grass", "dry grass"),
    ("oga_n4_seamless_pattern/grass.png", "grass", "grass"),
    # dirt
    ("oga_tileable_dirt_cethiel/Dirt_01.png", "dirt", "dirt"),
    ("oga_tileable_dirt_cethiel/Dirt_02.png", "dirt", "dirt"),
    ("oga_tileable_dirt_cethiel/Dirt_03.png", "dirt", "plowed dirt"),
    ("oga_tileable_dirt_cethiel/Dirt_04.png", "dirt", "dry dirt"),
    ("oga_rubberduck_grassland/sources_ground__dirt_ground.png", "dirt", "dirt"),
    ("oga_rubberduck_grassland/sources_ground__dirt_ground_v2.png", "dirt", "dirt"),
    ("oga_rubberduck_grassland/sources_ground__dirt_ground_v3.png", "dirt", "dark dirt"),
    ("oga_n4_seamless_pattern/dirt.png", "dirt", "red dirt"),
    ("oga_dirt_sand_luminousdragon/Dirt_2.png", "dirt", "dirt"),
    # sand
    ("oga_desert_sand_txturs/sand_1.jpg", "sand", "desert sand"),
    ("oga_n4_seamless_pattern/beach_sand.png", "sand", "beach sand"),
    ("oga_n4_seamless_pattern/sand.png", "sand", "sand"),
    ("oga_dirt_sand_luminousdragon/Sand1.png", "sand", "sand"),
    ("oga_rubberduck_grassland/sources_ground__sand.png", "sand", "sand"),
    # water (TX5 water/stone boost added the GGBotNet tile)
    ("oga_seamless_water_hazmatharry/dark_water.jpg", "water", "deep water"),
    ("oga_seamless_water_hazmatharry/light_water.jpg", "water", "shallow water"),
    ("oga_y2k_water_ggbotnet/y2k_water_texture.png", "water", "water"),
    # path
    ("oga_cobblestone_hellgate/cobblestone_diffuse.png", "path", "cobblestone path"),
    ("oga_n4_seamless_pattern/cobblestone.png", "path", "cobblestone path"),
    ("oga_n4_seamless_pattern/gravel_512x512_00.png", "path", "gravel path"),
    ("oga_n4_seamless_pattern/gravel_512x512_02.png", "path", "gravel path"),
    ("oga_ground_textures_forkotlow/ground_0.jpg", "path", "gravel ground"),
    # stone floor (TX5 boost: 3 genuine floors replace the marginal n4 snow-ish "stone")
    ("oga_floor_tile_ravaen/floortiles_0.png", "stone", "stone floor"),
    ("oga_floor_sbs/Rectangle_Marble_Tile_01-512x512.png", "stone", "tiled stone floor"),
    ("oga_floor_sbs/Rectangle_Marble_Tile_03-512x512.png", "stone", "tiled stone floor"),
]

# Files present in RAW but deliberately EXCLUDED, with reasons (for the manifest).
EXCLUSIONS: list[tuple[str, str]] = [
    ("oga_grass_beach_water_impossiblerealms/terrain_1.png",
     "level mockup (a composed scene with a cross-shaped pond), not a seamless terrain tile"),
    ("oga_grass_beach_water_impossiblerealms/terrain_tiles24.png",
     "tiny 256px spritesheet with magenta transparency key — not a usable tile"),
    ("oga_stone_floor_ogreofwart/floor1.png",
     "single slab with a dark border frame — would teach the LoRA to draw tile borders (not seamless)"),
    ("oga_stone_floor_ogreofwart/floor2.png",
     "3x3 grid of framed slabs (spritesheet) — not a seamless full-frame tile"),
    ("oga_dirt_sand_luminousdragon/Dirt_3.png", "near-duplicate flat ochre dirt (kept Dirt_2 as the representative)"),
    ("oga_dirt_sand_luminousdragon/Dirt_4.png", "near-duplicate flat ochre dirt"),
    ("oga_dirt_sand_luminousdragon/Dirt_5.png", "near-duplicate flat ochre dirt"),
    ("oga_dirt_sand_luminousdragon/Dirt_6.png", "near-duplicate flat ochre dirt"),
    ("oga_dirt_sand_luminousdragon/Dirt_7.png", "near-duplicate flat ochre dirt"),
    ("oga_dirt_sand_luminousdragon/Dirt_8.png", "near-duplicate flat ochre dirt"),
    ("oga_dirt_sand_luminousdragon/Dirt_9.png", "near-duplicate flat ochre dirt"),
    ("oga_dirt_sand_luminousdragon/Dirt_10.png", "near-duplicate flat ochre dirt"),
    ("oga_dirt_sand_luminousdragon/Sand2.png", "near-duplicate flat ochre sand (kept Sand1)"),
    ("oga_n4_seamless_pattern/gravel_512x512_01.png", "near-duplicate grey gravel (kept _00 and _02)"),
    ("oga_n4_seamless_pattern/gravel_512x512_03.png", "near-duplicate grey gravel"),
    ("oga_n4_seamless_pattern/stone.png",
     "dropped in the TX5 boost — reads as snow/plaster, not stone floor; replaced by 3 genuine CC0 stone floors (Ravaen + 2 Screaming Brain rectangle tiles)"),
    ("oga_floor_sbs/Rectangle_Marble_Tile_05-512x512.png", "black marble — too dark for an even-lit terrain tile"),
    ("oga_floor_sbs/WO_Marble_Tile_01-512x512.png", "high-contrast checker pattern — decorative, not terrain-like"),
]


def slugify(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s.lower()).strip("_")


def main() -> int:
    prov = json.loads((RAW / "_provenance.json").read_text(encoding="utf-8"))
    acc = prov if isinstance(prov, list) else (prov.get("accepted") or prov.get("assets"))
    by_file = {a["file"]: a for a in acc if isinstance(a, dict) and a.get("file")}

    if CURATED.exists():
        shutil.rmtree(CURATED)
    CURATED.mkdir(parents=True, exist_ok=True)

    # Copy the curated selection, encoding terrain family + phrase in the stem so
    # prep_dataset (which preserves stems) yields self-labeling output filenames.
    picked: list[dict] = []
    for rel, family, phrase in CURATED_SELECTION:
        src = RAW / rel
        if not src.exists():
            print(f"  ! MISSING (skipped): {rel}", file=sys.stderr)
            continue
        stem = Path(rel).stem
        dst = CURATED / f"{family}__{slugify(phrase)}__{stem}{src.suffix}"
        shutil.copy2(src, dst)
        meta = by_file.get(rel, {})
        picked.append({
            "raw": rel, "curated": dst.name, "family": family, "phrase": phrase,
            "source_page": meta.get("source_page", "?"), "author": meta.get("author", "?"),
            "license": meta.get("license", "?"),
        })
    print(f"Curated {len(picked)} images -> {CURATED}")

    # Normalize with the trainer-agnostic prep_dataset.py (acceptance criterion).
    if OUT.exists():
        shutil.rmtree(OUT)
    cmd = [sys.executable, str(PREP), "--src", str(CURATED), "--out", str(OUT), "--max-edge", "1024"]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    # Write short SDXL captions, matching each prepped PNG back to its terrain phrase.
    prepped = sorted(p for p in OUT.glob("*.png"))
    phrase_by_stem = {f"{p['family']}__{slugify(p['phrase'])}__{Path(p['raw']).stem}": p for p in picked}
    captioned = 0
    fam_counts: dict[str, int] = {}
    for png in prepped:
        rec = phrase_by_stem.get(png.stem)
        if not rec:
            print(f"  ? no terrain match for {png.name}", file=sys.stderr)
            continue
        caption = (f"tile_topdown, {rec['phrase']} tile, top-down RPG tileset, "
                   f"seamless texture, even lighting")
        png.with_suffix(".txt").write_text(caption + "\n", encoding="utf-8")
        captioned += 1
        fam_counts[rec["family"]] = fam_counts.get(rec["family"], 0) + 1
    print(f"Wrote {captioned} captions. Family counts: {fam_counts}")

    # Emit a small JSON the manifest builder / contact sheet can read.
    (OUT / "_curation.json").write_text(json.dumps(
        {"picked": picked, "exclusions": EXCLUSIONS, "family_counts": fam_counts,
         "count": captioned}, indent=2), encoding="utf-8")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
