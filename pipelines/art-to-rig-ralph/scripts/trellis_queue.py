"""trellis_queue — queue a TRELLIS.2 example workflow via the ComfyUI API.

Converts a ComfyUI *UI-format* workflow JSON (the files shipped in
ComfyUI-Trellis2/example_workflows/) into API format using the live
/object_info schemas, applies character-pipeline overrides, queues it, and
waits for completion.

Overrides applied automatically:
  - Trellis2LoadModel: backend=sdpa, sparse_backend=xformers (flash_attn is
    NOT installed on this box — see memory project_comfyui_torch_xformers_pin)
  - Trellis2LoadImageWithTransparency: first loader -> --front, second -> --back
  - Trellis2LoadMesh: --mesh (texturing workflows)
  - Trellis2ExportMesh: filename_prefix = --prefix
  - Preview/Note nodes are dropped (headless)

Usage (SINGLE view — MULTIVIEW DOES NOT WORK; MeshOnly_MultiView needs a matching
back image, corrupts geometry from two separate gens, and its 2nd loader errors on
a stale default when only --front is given):
  python trellis_queue.py --workflow MeshOnly --front A_front.png \
      --prefix Rookie [--mesh path.glb] [--seed N] \
      [--dry-run] [--comfy http://localhost:8188]

Prints QUEUED <prompt_id>, then OUTPUT <path> on success (newest file in the
ComfyUI output dir matching the prefix). Exit 0 on success.
Works with any Python 3.10+ (urllib only).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import urllib.request
import uuid

SKIP_TYPES = {"Preview3D", "PreviewImage", "Note", "MarkdownNote", "Reroute"}
CONTROL_WORDS = {"fixed", "randomize", "increment", "decrement"}
WORKFLOW_DIR = "D:/Projects/ComfyUI/custom_nodes/ComfyUI-Trellis2/example_workflows"
OUTPUT_DIR = "D:/Projects/ComfyUI/output"


def get_json(url: str):
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def ui_to_api(wf: dict, object_info: dict) -> dict:
    """Convert UI-format workflow (nodes+links) to API prompt format."""
    links = {}  # link_id -> (from_node, from_slot)
    for ln in wf.get("links", []):
        links[ln[0]] = (str(ln[1]), ln[2])

    api = {}
    for node in wf["nodes"]:
        ntype = node["type"]
        if ntype in SKIP_TYPES:
            continue
        schema = object_info.get(ntype)
        if schema is None:
            raise SystemExit(f"unknown node type {ntype} — is the node pack installed?")

        conn = {}  # input name -> [from_node, from_slot]
        for inp in node.get("inputs", []):
            if inp.get("link") is not None and inp["link"] in links:
                conn[inp["name"]] = list(links[inp["link"]])

        widgets = list(node.get("widgets_values") or [])
        wi = 0
        inputs = {}
        ordered = list(schema["input"].get("required", {}).items()) + \
                  list(schema["input"].get("optional", {}).items())
        for name, spec in ordered:
            typ = spec[0]
            is_widget_type = isinstance(typ, list) or typ in (
                "STRING", "INT", "FLOAT", "BOOLEAN")
            widget_val = None
            if is_widget_type and wi < len(widgets):
                # widget-type inputs ALWAYS own a widgets_values slot, even when
                # converted to a socket and linked (the placeholder remains)
                widget_val = widgets[wi]
                wi += 1
                # skip the control_after_generate companion widget after seeds
                if name in ("seed", "noise_seed") and wi < len(widgets) \
                        and isinstance(widgets[wi], str) and widgets[wi] in CONTROL_WORDS:
                    wi += 1
            if name in conn:
                inputs[name] = conn[name]
            elif is_widget_type and widget_val is not None:
                inputs[name] = widget_val
            # unconnected pure-socket inputs (e.g. optional left/right images): omit
        api[str(node["id"])] = {"class_type": ntype, "inputs": inputs}

    # drop dangling links to skipped nodes (e.g. Preview3D consumers are gone;
    # producers referenced by skipped nodes are fine)
    return api


def apply_overrides(api: dict, args) -> None:
    loaders = [nid for nid, n in sorted(api.items(), key=lambda kv: int(kv[0]))
               if n["class_type"] == "Trellis2LoadImageWithTransparency"]
    if args.front and loaders:
        api[loaders[0]]["inputs"]["image"] = args.front
    if args.back and len(loaders) > 1:
        api[loaders[1]]["inputs"]["image"] = args.back
    for n in api.values():
        ct = n["class_type"]
        if ct == "Trellis2LoadModel":
            n["inputs"]["backend"] = "sdpa"
            n["inputs"]["sparse_backend"] = "xformers"
        elif ct == "Trellis2LoadMesh" and args.mesh:
            n["inputs"]["glb_path"] = args.mesh
        elif ct == "Trellis2ExportMesh" and args.prefix:
            n["inputs"]["filename_prefix"] = args.prefix
        elif ct == "Trellis2PreProcessImage" and args.remove_bg:
            n["inputs"]["remove_background"] = True
        if args.seed is not None and "seed" in n["inputs"] \
                and not isinstance(n["inputs"]["seed"], list):
            n["inputs"]["seed"] = args.seed
    # PrimitiveString prefix feeds ExportMesh in some example workflows
    if args.prefix:
        for n in api.values():
            if n["class_type"] == "PrimitiveString" \
                    and isinstance(n["inputs"].get("value"), str) \
                    and n["inputs"]["value"] in ("MV", "Textured", "3D/Trellis2"):
                n["inputs"]["value"] = args.prefix


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True,
                    help="example workflow name (no .json) or a path")
    ap.add_argument("--front", help="front image (must exist in ComfyUI/input)")
    ap.add_argument("--back", help="back image")
    ap.add_argument("--mesh", help="glb path for texturing workflows")
    ap.add_argument("--prefix", help="output filename prefix")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--remove-bg", action="store_true", default=True,
                    help="remove background in preprocess (needed for RGB inputs)")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--comfy", default="http://localhost:8188")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    wf_path = args.workflow if os.path.isfile(args.workflow) \
        else f"{WORKFLOW_DIR}/{args.workflow}.json"
    wf = json.load(open(wf_path, encoding="utf-8"))
    object_info = get_json(f"{args.comfy}/object_info")

    api = ui_to_api(wf, object_info)
    apply_overrides(api, args)

    if args.dry_run:
        print(json.dumps(api, indent=1))
        return 0

    req = urllib.request.Request(
        f"{args.comfy}/prompt",
        data=json.dumps({"prompt": api, "client_id": str(uuid.uuid4())}).encode(),
        headers={"Content-Type": "application/json"})
    resp = json.load(urllib.request.urlopen(req))
    if resp.get("node_errors"):
        print("NODE_ERRORS", json.dumps(resp["node_errors"])[:800])
        return 1
    pid = resp["prompt_id"]
    print(f"QUEUED {pid}")

    t0 = time.time()
    while time.time() - t0 < args.timeout:
        time.sleep(10)
        hist = get_json(f"{args.comfy}/history/{pid}")
        if pid not in hist:
            continue
        rec = hist[pid]
        status = rec["status"]["status_str"]
        if status == "success":
            print("STATUS success")
            if args.prefix:
                matches = sorted(glob.glob(f"{OUTPUT_DIR}/{args.prefix}*"),
                                 key=os.path.getmtime)
                if matches:
                    print(f"OUTPUT {matches[-1]}")
            return 0
        if status == "error":
            for m in rec["status"].get("messages", []):
                if m[0] == "execution_error":
                    print("ERROR node", m[1].get("node_id"), m[1].get("node_type"),
                          str(m[1].get("exception_message"))[:300])
            return 1
    print("TIMEOUT")
    return 2


if __name__ == "__main__":
    sys.exit(main())
