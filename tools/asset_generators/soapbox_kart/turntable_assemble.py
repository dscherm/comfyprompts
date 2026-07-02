"""Assemble the Soapbox Kart Kit turntables into the product gallery. Reads raw
frames from scratchpad/kart_turntable/<item>/, applies light bloom (only the
glowing pickups/boost pads pop), writes an animated GIF + hero still per item to
products/.../gallery/, and rebuilds a labelled contact-sheet (catalog.png).
Run with a python that has numpy+PIL (ComfyUI venv).
"""
import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

SCR = r"C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/0e5e1c40-e596-49a6-a43d-bfbe573d38ce/scratchpad/kart_turntable"
PROD = r"D:/Projects/comfyui-toolchain/products/soapbox_kart_kit_v1"
GALLERY = os.path.join(PROD, "gallery")
os.makedirs(GALLERY, exist_ok=True)

ORDER = [
    "kart_racer", "kart_rocket", "kart_tub", "kart_crate",
    "track_straight", "track_corner", "track_start", "ramp_up", "jump_ramp",
    "finish_gate", "checkpoint_arch", "banner", "sign_arrow", "flag_pole",
    "cone", "tire_stack", "crate", "barrier", "barrel", "haybale",
    "oil_slick", "puddle", "boost_pad", "pickup_boost", "pickup_shield", "pickup_wrench",
    "mascot_robot", "mascot_frog", "mascot_wizard", "mascot_shark", "mascot_skeleton",
]

THRESH, RADIUS, INTENSITY = 640.0, 5.0, 0.5  # light — only emissive pickups glow


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
    bloomed[0].save(os.path.join(GALLERY, f"{name}.gif"), save_all=True,
                    append_images=bloomed[1:], duration=90, loop=0, optimize=True)
    bloomed[0].save(os.path.join(GALLERY, f"{name}.png"))
    stills[name] = bloomed[0]
    print("GALLERY", name)

COLS = 6
T = 240
LAB = 20
PAD = 8
rows = (len(names) + COLS - 1) // COLS
W = COLS * T + (COLS + 1) * PAD
H = rows * (T + LAB) + (rows + 1) * PAD
card = Image.new("RGB", (W, H), (30, 32, 38))
d = ImageDraw.Draw(card)
for i, name in enumerate(names):
    if name not in stills:
        continue
    c, r = i % COLS, i // COLS
    x = PAD + c * (T + PAD)
    y = PAD + r * (T + LAB + PAD)
    card.paste(stills[name].resize((T, T)), (x, y))
    d.text((x + 4, y + T + 4), name.replace("_", " "), fill=(225, 225, 235))
cat_path = os.path.join(PROD, "catalog.png")
card.save(cat_path)
print("CATALOG ->", cat_path, card.size, "n=", len(stills))
