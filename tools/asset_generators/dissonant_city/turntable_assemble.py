"""Assemble the DissonantCity per-piece turntables into the product gallery.
Reads raw frames from scratchpad/turntable/<piece>/, applies neon bloom to every
frame, writes an animated GIF + a hero still per piece to products/.../gallery/,
and rebuilds a clean labeled contact-sheet (catalog.png) from the stills.
Run with a python that has numpy+PIL (ComfyUI venv).
"""
import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

SCR = r"C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/0e5e1c40-e596-49a6-a43d-bfbe573d38ce/scratchpad/turntable"
PROD = r"D:/Projects/comfyui-toolchain/products/dissonant_city_v1"
GALLERY = os.path.join(PROD, "gallery")
os.makedirs(GALLERY, exist_ok=True)

# catalog piece order (big/hero pieces first), stragglers appended
ORDER = [
    "tower_neon", "tower_tall_cyan", "tower_tall_purple", "tower_spiral", "tower_prism", "tower_cyl",
    "tower_short_pink", "arcology", "ziggurat", "dome_building", "skybridge", "bridge_support",
    "slab_shop_pink", "slab_shop_cyan", "neon_arch", "billboard", "hover_car", "hover_car2",
    "holo_pylon", "antenna", "streetlight", "fountain_pad", "palm_retro", "crystals",
    "barrier", "road_junction", "road_straight", "road_corner", "plaza_tile",
]

THRESH, RADIUS, INTENSITY = 420.0, 8.0, 1.0


def bloom(arr):
    lum = arr.sum(axis=2)
    bright = (arr * (lum > THRESH)[..., None]).astype(np.uint8)
    glow = np.asarray(Image.fromarray(bright).filter(ImageFilter.GaussianBlur(RADIUS))).astype(np.float32) * INTENSITY
    glow = np.clip(glow, 0, 255)
    res = 255.0 - (255.0 - arr) * (255.0 - glow) / 255.0
    return np.clip(res, 0, 255).astype(np.uint8)


present = [d for d in os.listdir(SCR) if os.path.isdir(os.path.join(SCR, d))]
names = [n for n in ORDER if n in present] + sorted(set(present) - set(ORDER))

stills = {}
for name in names:
    fdir = os.path.join(SCR, name)
    frame_files = sorted(f for f in os.listdir(fdir) if f.startswith("frame_") and f.endswith(".png"))
    if not frame_files:
        print("SKIP (no frames)", name)
        continue
    bloomed = [Image.fromarray(bloom(np.asarray(Image.open(os.path.join(fdir, f)).convert("RGB")).astype(np.float32)))
               for f in frame_files]
    # animated turntable GIF
    gif_path = os.path.join(GALLERY, f"{name}.gif")
    bloomed[0].save(gif_path, save_all=True, append_images=bloomed[1:], duration=90, loop=0, optimize=True)
    # hero still (frame 0 = canonical 3/4)
    still_path = os.path.join(GALLERY, f"{name}.png")
    bloomed[0].save(still_path)
    stills[name] = bloomed[0]
    print("GALLERY", name, "gif+png")

# rebuilt labeled catalog from the isolated per-piece stills (far cleaner than the grid)
COLS = 6
T = 240
LAB = 20
PAD = 8
rows = (len(names) + COLS - 1) // COLS
W = COLS * T + (COLS + 1) * PAD
H = rows * (T + LAB) + (rows + 1) * PAD
card = Image.new("RGB", (W, H), (12, 12, 20))
d = ImageDraw.Draw(card)
for i, name in enumerate(names):
    if name not in stills:
        continue
    c, r = i % COLS, i // COLS
    x = PAD + c * (T + PAD)
    y = PAD + r * (T + LAB + PAD)
    card.paste(stills[name].resize((T, T)), (x, y))
    d.text((x + 4, y + T + 4), name.replace("_", " "), fill=(210, 210, 225))
cat_path = os.path.join(PROD, "catalog.png")
card.save(cat_path)
print("CATALOG (turntable stills) ->", cat_path, card.size, "n=", len(stills))
