"""Batch Stage-1 generation for the low-poly skill: read a roster JSON + the
2-LoRA workflow template, substitute PARAM_* placeholders per piece, and queue
each generation on ComfyUI SEQUENTIALLY (one at a time — parallel Flux gens on
one GPU cause VRAM contention / hangs). Polls /history for completion and copies
each result to <out>/<piece>.png.

    python batch_gen.py <roster.json> <workflow.json> <out_dir> [--views front,side,back]

Default: one "review" view per piece (biped=front, quad=side). Prints GEN/DONE
per piece and BATCH_COMPLETE at the end so a monitor can track progress.
"""
import json
import os
import shutil
import sys
import time
import urllib.request

COMFY = "http://localhost:8188"
COMFY_OUT = r"D:/Projects/ComfyUI/output"
PER_GEN_TIMEOUT = 240


def post_prompt(graph):
    data = json.dumps({"prompt": graph, "client_id": "lowpoly-batch"}).encode()
    req = urllib.request.Request(f"{COMFY}/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]


def wait(prompt_id):
    t0 = time.time()
    while time.time() - t0 < PER_GEN_TIMEOUT:
        try:
            resp = urllib.request.urlopen(f"{COMFY}/history/{prompt_id}", timeout=15)
            h = json.loads(resp.read())
        except Exception:
            time.sleep(2)
            continue
        if prompt_id in h:
            entry = h[prompt_id]
            status = entry.get("status", {})
            if status.get("completed") or entry.get("outputs"):
                for node in entry.get("outputs", {}).values():
                    for im in node.get("images", []):
                        return im["filename"], im.get("subfolder", "")
                return None, None  # completed but no image (error)
        time.sleep(2)
    raise TimeoutError(f"gen {prompt_id} exceeded {PER_GEN_TIMEOUT}s")


def substitute(template, m):
    """Deep-copy the workflow, replacing exact PARAM_* string values from map m."""
    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str) and x in m:
            return m[x]
        return x
    return walk(template)


def main():
    roster_path, wf_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    views_arg = None
    if "--views" in sys.argv:
        views_arg = sys.argv[sys.argv.index("--views") + 1].split(",")
    R = json.load(open(roster_path, encoding="utf-8"))
    WF = json.load(open(wf_path, encoding="utf-8"))
    os.makedirs(out_dir, exist_ok=True)

    sc, st, gen = R["scaffold"], R["strength"], R["gen"]
    pieces = R["pieces"]
    review_view = gen.get("review_view", {"biped": "front view", "quad": "side view"})

    jobs = []
    for i, p in enumerate(pieces):
        prefix = sc["biped_prefix"] if p["type"] == "biped" else sc["quad_prefix"]
        pose_lora = R["loras"][p["type"]]["pose"]
        style_lora = R["loras"][p["type"]]["style"]
        views = views_arg if views_arg else [review_view[p["type"]].split()[0]]
        for v in views:
            view_txt = {"front": "front view", "side": "side view", "back": "back view"}.get(v, v)
            prompt = prefix.replace("PARAM_VIEW", view_txt) + p["subject"] + sc["suffix"]
            name = p["name"] if len(views) == 1 else f"{p['name']}_{v}"
            jobs.append((name, p, prompt, pose_lora, style_lora, 1000 + i * 13 + len(jobs)))

    print(f"BATCH_START {len(jobs)} jobs -> {out_dir}", flush=True)
    done = 0
    for j, (name, p, prompt, pose_lora, style_lora, seed) in enumerate(jobs, 1):
        m = {
            "PARAM_STR_LORA_NAME": pose_lora, "PARAM_FLOAT_LORA_STRENGTH": st["pose"],
            "PARAM_STR_LORA2_NAME": style_lora, "PARAM_FLOAT_LORA2_STRENGTH": st["style"],
            "PARAM_PROMPT": prompt, "PARAM_NEGATIVE_PROMPT": sc["negative"],
            "PARAM_INT_WIDTH": gen["width"], "PARAM_INT_HEIGHT": gen["height"],
            "PARAM_INT_SEED": seed, "PARAM_INT_STEPS": 20, "PARAM_FLOAT_CFG": 1.0,
            "PARAM_STR_SAMPLER_NAME": "euler", "PARAM_STR_SCHEDULER": "simple",
            "PARAM_FLOAT_DENOISE": 1.0,
        }
        graph = substitute(WF, m)
        print(f"GEN {j}/{len(jobs)} {name} ({p['type']})", flush=True)
        try:
            pid = post_prompt(graph)
            fn, sub = wait(pid)
            if not fn:
                print(f"FAIL {name}: no image (validation/exec error)", flush=True)
                continue
            src = os.path.join(COMFY_OUT, sub, fn)
            dst = os.path.join(out_dir, f"{name}.png")
            shutil.copy2(src, dst)
            done += 1
            print(f"DONE {name} -> {dst}", flush=True)
        except Exception as e:
            print(f"FAIL {name}: {str(e)[:120]}", flush=True)
    print(f"BATCH_COMPLETE {done}/{len(jobs)}", flush=True)


if __name__ == "__main__":
    main()
