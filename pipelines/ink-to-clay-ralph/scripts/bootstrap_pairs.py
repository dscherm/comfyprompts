"""bootstrap_pairs — Stage 1 of ink-to-clay-ralph: free aligned (ink, clay) pairs.

Generates, for each subject, the SAME subject at the SAME seed twice via the
already-deployed soapbox_char_final_v1 (+ mv_ortho) FLUX LoRAs:

  - clay (target) = mv_ortho@0.85 + char@0.65, plain neutral-grey bg, even light.
  - ink  (input)  = char@0.9 (no mv_ortho), heavy black ink linework, white bg.

Same seed → an aligned pair. Written with MATCHED filenames to
  E:/ai-training/datasets/ink_to_clay_v1/{ink,clay}/<id>.png

so Stage 4 (Kontext paired-edit) can consume them and the clay halves alone are
the Approach-A style set. Resumable: a subject whose ink+clay both already exist
is skipped, so a long 50-150 subject run can be re-invoked freely.

Drives ComfyUI directly over HTTP (stdlib urllib only — no torch, any py3.10+).
Generation only: ComfyUI must be UP on the 3090 Ti (`run_3090ti.ps1`); it does
NOT train, so it needs no GPU-free training gate. `ollama stop` first if ollama
is holding VRAM.

Usage:
  python bootstrap_pairs.py                        # full default subject set
  python bootstrap_pairs.py --limit 3              # first 3 subjects (smoke)
  python bootstrap_pairs.py --subjects subs.txt    # one "slug: description" per line
  python bootstrap_pairs.py --dry-run              # build+print workflows, no ComfyUI
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

COMFY = "http://localhost:8188"
CKPT = "flux1-dev-fp8.safetensors"
# ComfyUI lists loras with the OS separator (Windows backslash); these are deployed.
LORA_CHAR = "style\\soapbox_char_final_v1.safetensors"
LORA_MV = "style\\mv_ortho.safetensors"
OUT_ROOT = Path("E:/ai-training/datasets/ink_to_clay_v1")

NEG = "blurry, low quality, extra limbs, deformed, multiple subjects, watermark, text, photograph"
# Clay adds shadow/ground suppressors — TRELLIS wants the subject isolated, no ground plane.
CLAY_NEG = (NEG + ", cast shadow, drop shadow, ground shadow, floor, ground plane, "
            "pedestal, base, reflection")

# Prompt scaffolds (intent from lora-ink-to-clay-spec.md). BOTH share the same pose
# framing so a shared seed keeps the two renders' composition aligned (Option 1).
POSE = "front view, full body, A/T-pose"


def clay_prompt(subject: str) -> str:
    return (f"mv_ortho, {POSE}, {subject}, gritty_comic, smooth matte 3d render, "
            "isolated on a plain flat neutral-grey backdrop, floating, no ground, "
            "orthographic, soft even studio lighting, no cast shadow")


def ink_prompt(subject: str) -> str:
    return (f"gritty_comic, {POSE}, {subject}, heavy black ink linework, cel shading, "
            "flat 2D comic illustration, plain white background")


# Varied starter subjects (chars + creatures + props + objects) for generalization.
# Override/extend with --subjects (one "slug: description" per line). ~48 here;
# the spec wants 50-150, so add real ink drawings + more subjects before training.
SUBJECTS: list[tuple[str, str]] = [
    ("knight", "an armored knight warrior holding a sword"),
    ("barbarian", "a muscular barbarian with an axe"),
    ("wizard", "an old wizard in robes holding a staff"),
    ("rogue", "a hooded rogue with two daggers"),
    ("archer", "an elf archer with a bow"),
    ("paladin", "a paladin in heavy plate with a shield"),
    ("necromancer", "a necromancer in dark robes"),
    ("berserker", "a fur-clad berserker roaring"),
    ("dwarf", "a stout dwarf with a warhammer"),
    ("valkyrie", "a winged valkyrie with a spear"),
    ("dragon", "a small horned dragon standing"),
    ("goblin", "a sneaky goblin with a crude knife"),
    ("skeleton", "a skeleton warrior with a rusty sword"),
    ("ghoul", "a hunched ghoul creature"),
    ("golem", "a stone golem with heavy fists"),
    ("slime", "a round blob slime creature"),
    ("wolf", "a snarling grey wolf"),
    ("bear", "a large brown bear standing"),
    ("frog", "a big cartoon frog"),
    ("owl", "a round owl with big eyes"),
    ("bat", "a small winged bat"),
    ("spider", "a chunky cartoon spider"),
    ("sword", "a single broadsword weapon"),
    ("axe", "a single battle axe weapon"),
    ("shield", "a round wooden shield"),
    ("bow", "a curved wooden longbow"),
    ("staff", "a wizard staff topped with a crystal"),
    ("potion", "a round potion bottle with a cork"),
    ("chest", "a wooden treasure chest with iron bands"),
    ("barrel", "a wooden barrel"),
    ("crate", "a wooden crate"),
    ("lantern", "a metal hanging lantern"),
    ("torch", "a wooden torch with a flame"),
    ("key", "a large ornate iron key"),
    ("crown", "a golden crown with gems"),
    ("book", "a thick leather spellbook"),
    ("scroll", "a rolled parchment scroll"),
    ("gem", "a large faceted crystal gem"),
    ("coin", "a stack of gold coins"),
    ("helmet", "a horned viking helmet"),
    ("boot", "a single leather boot"),
    ("mushroom", "a large toadstool mushroom"),
    ("tree", "a small stylized pine tree"),
    ("rock", "a cluster of grey boulders"),
    ("tent", "a small camping tent"),
    ("cart", "a two-wheeled wooden cart"),
    ("anvil", "a heavy iron blacksmith anvil"),
    ("skull", "a single human skull"),
]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def build_workflow(prompt: str, seed: int, size: int, prefix: str,
                   loras: list[tuple[str, float]], neg: str = NEG) -> dict:
    """FLUX graph: checkpoint -> chained LoraLoader(s) -> CLIP/KSampler -> save.

    `loras` is applied in order; each LoraLoader consumes the previous node's
    (model, clip). The clay path passes two (mv_ortho, char); ink passes one.
    """
    wf: dict = {
        "1": {"inputs": {"ckpt_name": CKPT}, "class_type": "CheckpointLoaderSimple"},
    }
    src = "1"  # node whose [*,0]=model, [*,1]=clip feed the next loader
    node = 10
    for name, strength in loras:
        nid = str(node)
        wf[nid] = {"inputs": {"lora_name": name, "strength_model": strength,
                              "strength_clip": strength,
                              "model": [src, 0], "clip": [src, 1]},
                   "class_type": "LoraLoader"}
        src = nid
        node += 1
    wf["3"] = {"inputs": {"width": size, "height": size, "batch_size": 1},
               "class_type": "EmptySD3LatentImage"}
    wf["4"] = {"inputs": {"text": prompt, "clip": [src, 1]}, "class_type": "CLIPTextEncode"}
    wf["5"] = {"inputs": {"text": neg, "clip": [src, 1]}, "class_type": "CLIPTextEncode"}
    wf["6"] = {"inputs": {"seed": seed, "steps": 22, "cfg": 1.0, "sampler_name": "euler",
                          "scheduler": "beta", "denoise": 1.0, "model": [src, 0],
                          "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["3", 0]},
               "class_type": "KSampler"}
    wf["7"] = {"inputs": {"samples": ["6", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"}
    wf["8"] = {"inputs": {"filename_prefix": prefix, "images": ["7", 0]},
               "class_type": "SaveImage"}
    return wf


def _comfy_up() -> bool:
    try:
        urllib.request.urlopen(f"{COMFY}/system_stats", timeout=5).read()
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def queue(wf: dict) -> str:
    data = json.dumps({"prompt": wf}).encode()
    req = urllib.request.Request(f"{COMFY}/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]


def wait(pid: str, timeout: int = 300) -> dict | None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            h = json.loads(urllib.request.urlopen(f"{COMFY}/history/{pid}", timeout=15).read())
            if pid in h and h[pid].get("outputs"):
                imgs = h[pid]["outputs"].get("8", {}).get("images", [])
                if imgs:
                    return imgs[0]
        except urllib.error.URLError:
            pass
        time.sleep(2)
    return None


def fetch(img: dict, dest: Path) -> None:
    url = (f"{COMFY}/view?filename={img['filename']}"
           f"&subfolder={img.get('subfolder', '')}&type={img.get('type', 'output')}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())


def gen_one(prompt: str, seed: int, size: int, prefix: str,
            loras: list[tuple[str, float]], dest: Path, neg: str = NEG) -> bool:
    pid = queue(build_workflow(prompt, seed, size, prefix, loras, neg))
    img = wait(pid)
    if not img:
        print(f"    FAIL {dest.name} (no image)")
        return False
    fetch(img, dest)
    return True


def load_subjects(path: str | None) -> list[tuple[str, str]]:
    if not path:
        return SUBJECTS
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        slug, _, desc = line.partition(":")
        desc = desc.strip() or slug.strip()
        out.append((_slug(slug), desc))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_ROOT), help="dataset root (holds ink/ + clay/).")
    ap.add_argument("--subjects", default=None, help="file of 'slug: description' lines.")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--start-seed", type=int, default=90210)
    ap.add_argument("--seed-step", type=int, default=137)
    ap.add_argument("--limit", type=int, default=0, help="only the first N subjects (0=all).")
    ap.add_argument("--dry-run", action="store_true",
                    help="build + validate the clay/ink workflows for subject 0; no ComfyUI.")
    a = ap.parse_args()

    subjects = load_subjects(a.subjects)
    if a.limit:
        subjects = subjects[:a.limit]
    out = Path(a.out)
    ink_dir, clay_dir = out / "ink", out / "clay"

    if a.dry_run:
        slug, desc = subjects[0]
        clay = build_workflow(clay_prompt(desc), a.start_seed, a.size, f"i2c_clay_{slug}",
                              [(LORA_MV, 0.85), (LORA_CHAR, 0.65)], CLAY_NEG)
        ink = build_workflow(ink_prompt(desc), a.start_seed, a.size, f"i2c_ink_{slug}",
                             [(LORA_CHAR, 0.9)])
        json.dumps(clay)  # must serialize for the ComfyUI /prompt API
        json.dumps(ink)
        clay_loras = [b["inputs"]["lora_name"] for b in clay.values()
                      if b["class_type"] == "LoraLoader"]
        ink_loras = [b["inputs"]["lora_name"] for b in ink.values()
                     if b["class_type"] == "LoraLoader"]
        ksamp_src = clay["6"]["inputs"]["model"][0]
        print(f"DRY-RUN subject[0] = {slug}: {desc}")
        print(f"  clay: {len(clay_loras)} LoRAs -> KSampler.model from node {ksamp_src}")
        print(f"        {clay_loras}")
        print(f"  ink : {len(ink_loras)} LoRA  {ink_loras}")
        print(f"  clay pos: {clay['4']['inputs']['text'][:70]}...")
        print(f"  ink  pos: {ink['4']['inputs']['text'][:70]}...")
        print(f"  {len(subjects)} subjects -> {len(subjects) * 2} images at {out}")
        print("OK (dry-run) — workflows build + serialize; run live when ComfyUI is up.")
        return 0

    if not _comfy_up():
        print(f"ComfyUI not reachable at {COMFY}. Start it (run_3090ti.ps1) and retry.")
        return 1

    done = skipped = 0
    for i, (slug, desc) in enumerate(subjects):
        _id = f"{i:03d}_{slug}"
        ink_dst, clay_dst = ink_dir / f"{_id}.png", clay_dir / f"{_id}.png"
        if ink_dst.exists() and clay_dst.exists():
            skipped += 1
            continue
        seed = a.start_seed + i * a.seed_step
        print(f"[{i + 1}/{len(subjects)}] {_id} (seed {seed})", flush=True)
        ok_clay = gen_one(clay_prompt(desc), seed, a.size, f"i2c_clay_{slug}",
                          [(LORA_MV, 0.85), (LORA_CHAR, 0.65)], clay_dst, CLAY_NEG)
        ok_ink = gen_one(ink_prompt(desc), seed, a.size, f"i2c_ink_{slug}",
                         [(LORA_CHAR, 0.9)], ink_dst)
        if ok_clay and ok_ink:
            done += 1
        else:  # keep pairs aligned — drop a half-made pair so the gate's match check stays true
            for p in (ink_dst, clay_dst):
                p.unlink(missing_ok=True)
            print(f"    dropped incomplete pair {_id}")
    print(f"\nDONE: {done} new pair(s), {skipped} already present -> {out}")
    print("Next: build a curation montage and get human approval (gate-01-dataset).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
