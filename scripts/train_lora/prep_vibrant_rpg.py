"""Prep the Vibrant RPG Characters dataset for a Flux style LoRA.

Flattens/sanitizes E:/Vibrant RPG Characters into a FLAT dataset dir and writes
deterministic captions. Same-name characters get mechanical V1/V2/... version tags
(user requirement); single-image characters get none. No ComfyUI needed.
    python prep_vibrant_rpg.py
"""
import collections
import glob
import os
import re
import shutil

SRC = r"E:/Vibrant RPG Characters"
DST = r"E:/ai-training/datasets/vibrant_rpg_char"
TRIGGER = "vibrant_rpg_char"
STYLE = ("vibrant RPG character illustration, dramatic lighting, bold saturated color "
         "background, painterly fantasy art, highly detailed")


def base_name(path):
    n = os.path.splitext(os.path.basename(path))[0]
    n = re.sub(r"^Berserkr_(Creature|Fullbody|Portrait)_", "", n)
    n = re.sub(r"^v2_", "", n)
    n = re.sub(r"_\d{5}_?$", "", n)          # trailing _00001_
    n = re.sub(r"\s*\(\d+\)$", "", n)         # " (1)" duplicate suffix
    return n.strip().lower()


def main():
    os.makedirs(DST, exist_ok=True)
    for f in glob.glob(DST + "/*"):
        if os.path.isfile(f):
            os.remove(f)
    fs = [f for f in glob.glob(SRC + "/*.*")
          if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    groups = collections.defaultdict(list)
    for f in sorted(fs):
        groups[base_name(f)].append(f)

    n = 0
    manifest = []
    for char, files in sorted(groups.items()):
        versioned = len(files) > 1
        for i, f in enumerate(sorted(files)):
            ver = f" V{i + 1}" if versioned else ""
            safe = re.sub(r"[^a-z0-9]+", "_", char).strip("_")
            if versioned:
                safe += f"_v{i + 1}"
            stem = f"{safe}_{n:03d}"
            shutil.copy2(f, f"{DST}/{stem}.png")
            cap = f"{TRIGGER}, a {char.replace('_', ' ')}{ver}, {STYLE}"
            with open(f"{DST}/{stem}.txt", "w", encoding="utf-8") as fh:
                fh.write(cap)
            manifest.append((stem, char, ver.strip()))
            n += 1

    print(f"PREPPED {n} images -> {DST}")
    print(f"characters: {len(groups)}  (versioned: {sum(1 for c in groups if len(groups[c])>1)})")
    print("sample captions:")
    for stem, char, ver in manifest[:6]:
        print(f"  {stem}: a {char.replace('_',' ')} {ver}")


if __name__ == "__main__":
    main()
