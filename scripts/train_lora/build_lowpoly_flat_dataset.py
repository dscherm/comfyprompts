"""build_lowpoly_flat_dataset — flat-shaded low-poly render dataset (Task SL5).

Renders a curated, IP-clean set of OWNED grimforge/soapbox low-poly meshes as
flat-shaded, evenly-lit, neutral-background views (the `lowpoly_flat` LoRA's
training aesthetic), then writes filename-derived captions + a manifest.

Rendering goes through **blender-mcp** (render_multiview.py, `--flat`): the live
Blender GUI's EEVEE, which uses the display GL context = the RTX 3070, NOT the
3090 Ti. Blender must be open with the MCP addon on :9876. Captions are derived
from the mesh filename (subject) + the view suffix — deterministic and IP-clean,
so NO Florence-2 / ComfyUI is needed (that would load the 3090 Ti).

Run (Blender open, MCP addon serving):
    "D:/Projects/ComfyUI/venv/Scripts/python.exe" scripts/train_lora/build_lowpoly_flat_dataset.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import render_multiview as rmv  # noqa: E402

STAGE = Path("E:/ai-training/_raw/lowpoly_flat/meshes")
RENDERS = Path("E:/ai-training/_raw/lowpoly_flat/renders")
OUT = Path("E:/ai-training/datasets/lowpoly_flat")
PREP = HERE / "prep_dataset.py"
ANGLES = ["front", "front_left", "front_right"]
# Long/thin (blades) and end-on-ambiguous (anvil) subjects read as flat cutouts /
# unrecognizable blobs from the straight-on front; elevated 3/4 hero angles give
# them dimension and show their silhouette. (User feedback, 2026-07-17.)
HERO_SUBJECTS = {"anvil", "battleaxe", "halberd", "scythe", "spear",
                 "arming_sword", "saber", "dagger"}
HERO_ANGLES = ["three_quarter_left", "three_quarter", "hero_right"]
VIEW_PHRASE = {"front": "front view", "front_left": "three-quarter view",
               "front_right": "three-quarter view", "three_quarter": "three-quarter view",
               "three_quarter_left": "three-quarter view", "hero_right": "three-quarter view"}

# SL8: clean low-poly swords GENERATED to replace the arsenal sword/greatsword
# (whose shared blade mesh had a baked dark-fuller stripe). Pipeline: Flux concept
# (sl8_gen_sword_concepts.py) -> TRELLIS.2 image-to-3D -> weld/decimate
# (sl8_lowpoly_sword.py) -> steel blade + brown grip (sl8_color_sword.py). Regen
# those before a from-scratch rebuild, or these paths will be missing.
GEN = Path("E:/ai-training/_raw/lowpoly_flat_swords/meshes_colored")
VIL = REPO / "products/village_kit_grimforge_v2/examples/godot_village/models"
ARS = REPO / "products/arsenal_kit_grimforge_v1/models_glb"
SOA = REPO / "products/soapbox_kart_kit_v1/models_glb"
MAS = REPO / "products/soapbox_kart_kit_v1/mascots"
BES = REPO / "products/grimforge_bestiary_v1/_mesh"

# Curated, diverse, IP-clean set (all our own generated grimforge/soapbox assets).
# (source file, subject tag, kit label)
CURATED: list[tuple[Path, str, str]] = [
    # architecture / structures (village)
    (VIL / "windmill.glb", "windmill", "village"),
    (VIL / "guard_tower.glb", "guard tower", "village"),
    (VIL / "ruined_house.glb", "ruined house", "village"),
    (VIL / "fountain.glb", "fountain", "village"),
    (VIL / "stone_bridge.glb", "stone bridge", "village"),
    (VIL / "crypt.glb", "crypt", "village"),
    # props (village)
    (VIL / "anvil.glb", "anvil", "village"),
    (VIL / "torch.glb", "torch", "village"),
    (VIL / "weapon_rack.glb", "weapon rack", "village"),
    (VIL / "wood_pile.glb", "wood pile", "village"),
    # nature (village)
    (VIL / "pine.glb", "pine tree", "village"),
    (VIL / "rocks.glb", "rocks", "village"),
    (VIL / "stump.glb", "tree stump", "village"),
    # weapons / arsenal
    # NOTE: sword + greatsword EXCLUDED — they share one blade mesh whose baked
    # dark-fuller stripe + spade tip read as a "split/broken" blade (not a render
    # bug: flat and smooth shading are identical). Deferred: regenerate cleaner
    # low-poly sword meshes and swap them in (see plan.md follow-up). User call,
    # 2026-07-17.
    (ARS / "battleaxe.glb", "battleaxe", "arsenal"),
    (ARS / "warhammer.glb", "warhammer", "arsenal"),
    (ARS / "spear.glb", "spear", "arsenal"),
    (ARS / "halberd.glb", "halberd", "arsenal"),
    (ARS / "scythe.glb", "scythe", "arsenal"),
    (ARS / "wizard_staff.glb", "wizard staff", "arsenal"),
    (ARS / "potion_red.glb", "potion bottle", "arsenal"),
    (ARS / "spellbook.glb", "spellbook", "arsenal"),
    (ARS / "chest.glb", "treasure chest", "arsenal"),
    (ARS / "lantern.glb", "lantern", "arsenal"),
    # props / vehicles / characters (soapbox)
    (SOA / "barrel.glb", "barrel", "soapbox"),
    (SOA / "crate.glb", "crate", "soapbox"),
    (SOA / "kart_racer.glb", "kart racer", "soapbox"),
    (MAS / "robot.glb", "robot", "soapbox"),
    (MAS / "frog.glb", "frog", "soapbox"),
    (MAS / "skeleton.glb", "skeleton", "soapbox"),
    # SL8 generated clean swords (steel blade + brown grip). broadsword was tried
    # but its geometry defeated the grip auto-colour, so it was dropped.
    (GEN / "arming_sword.glb", "arming sword", "generated"),
    (GEN / "saber.glb", "saber", "generated"),
    (GEN / "dagger.glb", "dagger", "generated"),
    # NOTE: the bestiary creatures are intentionally EXCLUDED. Their `_lp` low-poly
    # meshes are untextured (UniRig drops materials) so they render as near-white
    # ghosts on the grey bg; their `_tex` variants ARE textured but read as
    # detailed/near-realistic models, off the clean flat-shaded low-poly aesthetic
    # this LoRA teaches. Character variety is covered by the soapbox mascots
    # (frog/robot/skeleton). Re-add textured creatures only if a mixed look is wanted.
]


def slug(s: str) -> str:
    return s.replace(" ", "_")


def check_sources() -> list[tuple[Path, str, str]]:
    present, missing = [], []
    for path, subject, kit in CURATED:
        (present if path.exists() else missing).append((path, subject, kit))
    if missing:
        print("MISSING source meshes:", file=sys.stderr)
        for p, s, _ in missing:
            print(f"  ! {s}: {p}", file=sys.stderr)
    return present


def main() -> int:
    present = check_sources()
    print(f"{len(present)}/{len(CURATED)} curated meshes present.")
    # Stage with unique subject-slug names so render output filenames don't collide.
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True, exist_ok=True)
    subj_by_stem = {}
    for path, subject, kit in present:
        dst = STAGE / f"{slug(subject)}.glb"
        shutil.copy2(path, dst)
        try:
            src = str(path.relative_to(REPO))
        except ValueError:
            src = str(path)  # generated meshes live off-repo (E:)
        subj_by_stem[slug(subject)] = {"subject": subject, "kit": kit, "src": src}

    # Render flat-shaded, neutral-grey, even-lit views via blender-mcp (3070, not 3090 Ti).
    rmv.preflight()  # SystemExit with a clear message if Blender/MCP is not open
    if RENDERS.exists():
        shutil.rmtree(RENDERS)
    RENDERS.mkdir(parents=True, exist_ok=True)
    rendered = 0
    for i, path in enumerate(sorted(STAGE.glob("*.glb")), 1):
        angles = HERO_ANGLES if path.stem in HERO_SUBJECTS else ANGLES
        res = rmv.render_mesh(path, RENDERS, angles, res=768, margin=1.15,
                              transparent=False, flat=True)
        if res.get("error"):
            print(f"  ! [{i}] {path.stem}: {res['error']}", file=sys.stderr)
            continue
        n = len(res.get("rendered", []))
        rendered += n
        print(f"  + [{i}/{len(present)}] {path.stem}: {n} view(s)", flush=True)
    print(f"Rendered {rendered} views -> {RENDERS}")
    if not rendered:
        raise SystemExit("no views rendered — aborting before prep")

    # Normalize with the trainer-agnostic prep_dataset.py.
    if OUT.exists():
        shutil.rmtree(OUT)
    subprocess.run([sys.executable, str(PREP), "--src", str(RENDERS), "--out", str(OUT),
                    "--max-edge", "1024"], check=True)

    # Filename-derived captions (no vision model / no 3090 Ti).
    captioned = 0
    kit_counts: dict[str, int] = {}
    for png in sorted(OUT.glob("*.png")):
        if "__" not in png.stem:
            continue
        stem, view = png.stem.rsplit("__", 1)
        rec = subj_by_stem.get(stem)
        if not rec:
            print(f"  ? no subject for {png.name}", file=sys.stderr)
            continue
        caption = (f"lowpoly_flat, {rec['subject']}, low-poly, flat shading, "
                   f"{VIEW_PHRASE.get(view, 'view')}, neutral background, even lighting")
        png.with_suffix(".txt").write_text(caption + "\n", encoding="utf-8")
        captioned += 1
        kit_counts[rec["kit"]] = kit_counts.get(rec["kit"], 0) + 1
    (OUT / "_curation.json").write_text(json.dumps(
        {"subjects": subj_by_stem, "kit_counts": kit_counts, "count": captioned,
         "angles": ANGLES}, indent=2), encoding="utf-8")
    print(f"Captioned {captioned}. Kit counts: {kit_counts}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
