# sagaink_kit — inked material treatment for the GrimForge kits

Re-skins the modular GrimForge building kit in the **sagaink** aesthetic
(`E:\ai-training\flux-output\vibrant_rpg_char\STYLE.md`): a stark high-contrast
black-and-white ink illustration — carved shadows, bold linework, cross-hatching
— that is grayscale everywhere **except one deliberate colour accent** (a window
glow, a forge ember, a rune gem).

This is a **real material treatment baked into the reusable atlas**, not a
full-screen post-process. Every kit piece samples one shared atlas, so re-baking
that atlas re-skins the whole kit at once — with the existing GLB UVs untouched
(no Blender re-export). UVs are normalised into cell rects, so the atlas bakes at
any resolution; the default is **2048** (`SAGAINK_ATLAS_SIZE` env), which keeps
the ink detail (256px material cells, 4:1 from the 1024 source) where the shipped
512 atlas crushed it 12:1. The pieces therefore carry the look
**standalone**, in any engine, with no shader required. A separate optional
Godot NPR shader (`grimforge_playable_demo_v1/shaders/sagaink.gdshader`,
`--sagaink`) exists for a stronger stylised pass, but the kit does not depend on
it.

## Pipeline (three stages)

```bash
PY="D:/Projects/ComfyUI/venv/Scripts/python.exe"   # needs PIL + numpy

# 1. Generate the 5 detailed inked SEAMLESS material textures (ComfyUI: SDXL +
#    SeamlessTile, truly tileable). Needs ComfyUI up on the 3090 Ti.
$PY gen_texture.py all        # -> out/{wood,stone,thatch,plaster,shingle}.png

# 2. Derive tangent-space NORMAL + AO maps from each texture's ink tone
#    (local, no network) so the surfaces carry depth on the mesh.
$PY derive_maps.py all        # -> out/<mat>_n.png, out/<mat>_ao.png

# 3. Bake the sagaink ATLAS SET from the shipped kit atlas layout: material
#    cells get the inked textures (toned to each swatch's own luminance), plain
#    cells desaturate to grayscale, the EMISSION accents keep their colour.
$PY bake_sagaink_atlas.py     # -> out/atlas_sagaink_{color,n,ao}.png
```

Then copy `out/atlas_sagaink_{color,n,ao}.png` into a consumer's kit folder
(e.g. `grimforge_playable_demo_v1/kit/`). The Godot demo applies them via
`env.gd` under the `--sagaink-kit` flag (albedo + normal + AO, tangents
synthesised for the normal map). Verify standalone (no NPR shader):

```bash
godot --path . -- --overview --sagaink-kit --shot=kit_sagaink.png:2 --quit-after=3
```

## How the atlas maps to materials

The atlas is `list(PALETTE)` (from `village_kit/kitlib.py`) in an 8-col grid.
Blender writes `image.pixels` bottom-row-first, so the saved PNG is **vertically
flipped** vs palette order (cell `i=0` = stone = bottom row) — `bake_sagaink_atlas.py`
flips the row index to match. Pattern groups mirror `kitlib._ensure_atlas`:

| group    | palette names                        | sagaink texture |
|----------|--------------------------------------|-----------------|
| planks   | wood, wood_dk, charwood, beam        | wood            |
| brick    | stone, stone_dk / plaster, plaster2  | stone / plaster |
| shingle  | slate, roof_red, shake               | shingle         |
| straw    | thatch, thatch_dk                    | thatch          |
| cobble   | cobble                               | stone           |
| accents  | `EMISSION` set (window/fire/ember/…) | keep colour     |
| (other)  | foliage, cloth, metal, bone, gravel  | desaturate      |

Each material cell is tone-shifted to its swatch's original mean luminance, so
the kit's tonal hierarchy survives (slate stays darker than plaster).

## Style lock ("blend")

`gen_texture.py` `INK` is the locked direction: inked linework **and** carved
tonal mass — bold dark outlines defining every form, cross-hatched shadows in
the recesses, a mid-grey tonal body (not a bimodal barcode, not a thin line
drawing). The sagaink Flux LoRA can't tile, so tiling surfaces get the ink look
by prompting SDXL; Flux+sagaink is reserved for non-tiling hero details.
