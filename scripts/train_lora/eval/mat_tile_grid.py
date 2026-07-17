"""TX3: generate the mat_tile eval grid through generate_texture_tile.json.

Cells: 4 material prompts x LoRA strengths {0.0 (base), 0.6, 0.8, 1.0}, fixed
seed, plus per-prompt tiling-DISABLED controls at 0.8 (the control must score a
HIGH edge MAD, proving the metric and the seamless nodes both work). Talks to
ComfyUI's REST API directly (urllib only).

Usage:
    python scripts/train_lora/eval/mat_tile_grid.py --out eval/mat_tile_grid
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
WORKFLOW = REPO / "workflows" / "mcp" / "generate_texture_tile.json"
COMFY = "http://localhost:8188"

PROMPT_TMPL = "mat_tile, {material}, seamless texture, even top-down lighting"
MATERIALS = ["red brick wall", "mossy cobblestone", "weathered wood planks", "beach sand"]
STRENGTHS = [0.0, 0.6, 0.8, 1.0]
SEED = 42
NEG = ("blurry, text, watermark, signature, visible seam, harsh shadows, "
       "strong directional light, vignette, perspective distortion, object, border")


def _api(path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{COMFY}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def _resolve_lora_name() -> str:
    info = _api("/object_info/LoraLoader")
    names = info["LoraLoader"]["input"]["required"]["lora_name"][0]
    matches = [n for n in names if "mat_tile" in n]
    if not matches:
        raise SystemExit(f"ERROR: mat_tile LoRA not visible to ComfyUI (have {len(names)} loras)")
    return matches[0]


def _build_graph(lora_name: str, prompt: str, strength: float, tiling: bool) -> dict:
    graph = json.loads(WORKFLOW.read_text())
    subs = {
        "PARAM_STR_CHECKPOINT": "sd_xl_base_1.0.safetensors",
        "PARAM_STR_LORA_NAME": lora_name,
        "PARAM_FLOAT_LORA_STRENGTH": strength,
        "PARAM_INT_WIDTH": 1024, "PARAM_INT_HEIGHT": 1024,
        "PARAM_PROMPT": prompt, "PARAM_NEGATIVE_PROMPT": NEG,
        "PARAM_INT_SEED": SEED, "PARAM_INT_STEPS": 25, "PARAM_FLOAT_CFG": 7.0,
    }
    for node in graph.values():
        node.pop("_defaults", None)
        node.pop("_meta", None)
        for key, val in list(node.get("inputs", {}).items()):
            if isinstance(val, str) and val in subs:
                node["inputs"][key] = subs[val]
    if not tiling:
        graph["9"]["inputs"]["tiling"] = "disable"
        graph["7"]["inputs"]["tiling"] = "disable"
    return graph


def _run(graph: dict, dest: Path, timeout: float = 600.0) -> None:
    pid = _api("/prompt", {"prompt": graph})["prompt_id"]
    start = time.monotonic()
    while True:
        time.sleep(2)
        hist = _api(f"/history/{pid}")
        if pid in hist:
            status = hist[pid].get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error: {json.dumps(status)[:400]}")
            outputs = hist[pid].get("outputs", {})
            images = [img for node in outputs.values() for img in node.get("images", [])]
            if images:
                img = images[0]
                url = (f"{COMFY}/view?filename={urllib.parse.quote(img['filename'])}"
                       f"&subfolder={urllib.parse.quote(img.get('subfolder', ''))}&type={img.get('type', 'output')}")
                with urllib.request.urlopen(url, timeout=120) as resp:
                    dest.write_bytes(resp.read())
                return
        if time.monotonic() - start > timeout:
            raise TimeoutError(f"generation timed out for {dest.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPO / "eval" / "mat_tile_grid")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lora = _resolve_lora_name()
    print(f"LoRA resolved: {lora}")

    cells = []
    for material in MATERIALS:
        slug = material.replace(" ", "_")
        for s in STRENGTHS:
            cells.append((f"{slug}__s{s:0.1f}".replace(".", ""), material, s, True))
        cells.append((f"{slug}__s08_NOTILING", material, 0.8, False))

    for i, (name, material, strength, tiling) in enumerate(cells, start=1):
        dest = args.out / f"{name}.png"
        if dest.exists():
            print(f"[{i}/{len(cells)}] {name} (cached)")
            continue
        print(f"[{i}/{len(cells)}] {name} ...", end=" ", flush=True)
        t0 = time.monotonic()
        graph = _build_graph(lora, PROMPT_TMPL.format(material=material), strength, tiling)
        _run(graph, dest)
        print(f"{time.monotonic()-t0:.0f}s")
    print(f"\n{len(cells)} cells in {args.out}")


if __name__ == "__main__":
    main()
