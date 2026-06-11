"""Flask backend for the ComfyUI Toolchain web UI.

Serves a single-page app with two functions:
- Generate: run any parametric workflow from workflows/mcp (forms are built
  client-side from the parameter schemas this API exposes)
- Create: clone/edit/validate/register new workflows, or queue a natural-
  language workflow request for a Claude Code session to build
  (the "interactive bridge")

Everything is local: ComfyUI REST + the repo's WorkflowManager and validator.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import re
import sys
import time
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory

from comfyui_agent_sdk.client import ComfyUIClient
from managers.workflow_manager import WorkflowManager

logger = logging.getLogger("webui")

PARAM_RE = re.compile(r"PARAM_[A-Z0-9_]+")
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Safe values for standard knobs left unfilled after meta/schema defaults.
# Keyed by placeholder stem (type-hint prefix stripped). Content-bearing
# params (PROMPT, TEXT, IMAGE...) are deliberately absent — those must come
# from the user.
FALLBACK_DEFAULTS = {
    "NEGATIVE_PROMPT": "text, watermark",
    "DENOISE": 1.0,
    "SAMPLER_NAME": "euler",
    "SCHEDULER": "normal",
    "CFG": 7.0,
    "STEPS": 20,
    "WIDTH": 512,
    "HEIGHT": 512,
    "BATCH_SIZE": 1,
    "FILENAME_PREFIX": "webui",
}


def param_stem(placeholder: str) -> str:
    stem = placeholder.removeprefix("PARAM_")
    for hint in ("STR_", "STRING_", "TEXT_", "INT_", "FLOAT_", "BOOL_"):
        stem = stem.removeprefix(hint)
    return stem


def fill_fallbacks(rendered: dict) -> None:
    """Replace leftover standard-knob placeholders in a rendered workflow."""
    import random

    for node in rendered.values():
        if not isinstance(node, dict):
            continue
        for key, value in list(node.get("inputs", {}).items()):
            if isinstance(value, str) and PARAM_RE.fullmatch(value.strip()):
                stem = param_stem(value.strip())
                if stem == "SEED":
                    node["inputs"][key] = random.randint(0, 2**31 - 1)
                elif stem in FALLBACK_DEFAULTS:
                    node["inputs"][key] = FALLBACK_DEFAULTS[stem]


def find_repo_root() -> Path:
    """Walk up from this file until workflows/mcp is found."""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "workflows" / "mcp").is_dir():
            return parent
    raise RuntimeError("could not locate repo root (workflows/mcp)")


REPO_ROOT = find_repo_root()
WORKFLOWS_DIR = REPO_ROOT / "workflows" / "mcp"
OBJECT_INFO_CACHE = REPO_ROOT / "scripts" / "cache" / "object_info.json"
BRIDGE_DIR = REPO_ROOT / ".omc" / "webui-requests"


def load_validator():
    """Load scripts/workflow_validator.py as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location(
        "workflow_validator", REPO_ROOT / "scripts" / "workflow_validator.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["workflow_validator"] = module
    spec.loader.exec_module(module)
    return module


validator = load_validator()
app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
client = ComfyUIClient()
manager = WorkflowManager(WORKFLOWS_DIR)


def read_meta(workflow_id: str) -> dict:
    meta_path = WORKFLOWS_DIR / f"{workflow_id}.meta.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_object_info(refresh: bool = False) -> dict | None:
    """Cached /object_info; refresh from the live server when asked."""
    if refresh or not OBJECT_INFO_CACHE.exists():
        try:
            return validator.fetch_object_info(client.base_url, OBJECT_INFO_CACHE)
        except Exception as e:
            logger.warning("object_info fetch failed: %s", e)
    if OBJECT_INFO_CACHE.exists():
        return json.loads(OBJECT_INFO_CACHE.read_text(encoding="utf-8"))
    return None


# ---------------------------------------------------------------- pages

@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


# ---------------------------------------------------------------- status

@app.get("/api/status")
def api_status():
    info = client.check_connection()
    try:
        queue = requests.get(f"{client.base_url}/queue", timeout=5).json()
        info["queue_running"] = len(queue.get("queue_running", []))
        info["queue_pending"] = len(queue.get("queue_pending", []))
    except Exception:
        info["queue_running"] = info["queue_pending"] = None
    info["workflow_count"] = len(manager.tool_definitions)
    return jsonify(info)


# ---------------------------------------------------------------- catalog

@app.get("/api/workflows")
def api_workflows():
    items = []
    for defn in manager.tool_definitions:
        meta = read_meta(defn.workflow_id)
        meta_params = meta.get("parameters", {}) if isinstance(meta.get("parameters"), dict) else {}
        params = []
        for name, p in defn.parameters.items():
            mp = meta_params.get(name, {}) if isinstance(meta_params.get(name), dict) else {}
            entry = {
                "name": name,
                "type": p.annotation.__name__,
                "required": p.required,
                "default": meta.get("defaults", {}).get(name, mp.get("default", p.default)),
                "description": mp.get("description", p.description),
            }
            if isinstance(mp.get("options"), list) and mp["options"]:
                entry["options"] = mp["options"]  # frontend renders a dropdown
            params.append(entry)
        items.append({
            "id": defn.workflow_id,
            "tool_name": defn.tool_name,
            "name": meta.get("name", defn.workflow_id.replace("_", " ").title()),
            "description": meta.get("description", defn.description),
            "category": meta.get("category", "other"),
            "tags": meta.get("tags", []),
            "requires_download": bool(meta.get("requires_download")),
            "requires_download_detail": meta.get("requires_download") or None,
            "output_type": meta.get("output", {}).get("type"),
            "parameters": params,
        })
    return jsonify(sorted(items, key=lambda i: (i["category"], i["id"])))


# ---------------------------------------------------------------- generate

@app.post("/api/generate")
def api_generate():
    body = request.get_json(force=True)
    workflow_id = body.get("workflow_id", "")
    params = body.get("params", {}) or {}

    defn = next((d for d in manager.tool_definitions if d.workflow_id == workflow_id), None)
    if defn is None:
        return jsonify({"error": f"unknown workflow: {workflow_id}"}), 404

    # Fill omitted optional params from sidecar/schema defaults so the API
    # accepts the same minimal payloads a human would expect to work
    meta_defaults = read_meta(workflow_id).get("defaults", {})
    for name, p in defn.parameters.items():
        if name not in params:
            default = meta_defaults.get(name, p.default)
            if default is not None:
                params[name] = default

    try:
        rendered = manager.render_workflow(defn, params)
    except Exception as e:
        return jsonify({"error": f"parameter rendering failed: {e}"}), 400

    fill_fallbacks(rendered)
    leftover = sorted(set(PARAM_RE.findall(json.dumps(rendered))))
    if leftover:
        return jsonify({"error": "missing parameters", "missing": leftover}), 400

    resp = client.queue_prompt(rendered)
    if not resp or "prompt_id" not in resp:
        return jsonify({"error": "ComfyUI rejected the job", "detail": resp}), 502
    return jsonify({"prompt_id": resp["prompt_id"]})


OUTPUT_KEYS = ("images", "gifs", "videos", "video", "audio", "audios", "mesh", "files")


@app.get("/api/job/<prompt_id>")
def api_job(prompt_id: str):
    status = client.get_job_status(prompt_id)
    outputs = []
    if status.get("status") == "completed":
        # Build rich output records from raw history — the SDK flattens to
        # bare path strings, which loses subfolder/type needed for /view
        history = client.get_history(prompt_id).get(prompt_id, {})
        for node_out in history.get("outputs", {}).values():
            if not isinstance(node_out, dict):
                continue
            for key in OUTPUT_KEYS:
                for item in node_out.get(key, []):
                    if isinstance(item, dict) and item.get("filename"):
                        qs = (
                            f"filename={item['filename']}"
                            f"&subfolder={item.get('subfolder', '')}"
                            f"&type={item.get('type', 'output')}"
                        )
                        outputs.append({
                            "filename": item["filename"],
                            "subfolder": item.get("subfolder", ""),
                            "type": item.get("type", "output"),
                            "url": f"/api/view?{qs}",
                        })
                    elif isinstance(item, str):
                        outputs.append({"filename": item, "url": None})
    # "unknown" = dequeue->history transition window; clients should keep polling
    state = status.get("status")
    if state == "unknown":
        state = "pending"
    return jsonify({
        "status": state,
        "progress": status.get("progress"),
        "error": status.get("error") if state == "error" else None,
        "outputs": outputs,
    })


@app.get("/api/view")
def api_view():
    """Proxy output files from ComfyUI so the browser stays on one origin."""
    upstream = requests.get(
        f"{client.base_url}/view", params=request.args.to_dict(), timeout=60, stream=True
    )
    if upstream.status_code != 200:
        return jsonify({"error": "file not found"}), upstream.status_code
    return app.response_class(
        upstream.iter_content(chunk_size=65536),
        content_type=upstream.headers.get("Content-Type", "application/octet-stream"),
    )


@app.post("/api/upload")
def api_upload():
    f = request.files.get("image")
    if f is None:
        return jsonify({"error": "no file field 'image'"}), 400
    result = client.upload_image(f.read(), f.filename or "upload.png")
    return jsonify(result)


# ---------------------------------------------------------------- authoring

@app.get("/api/author/workflow/<workflow_id>")
def api_author_get(workflow_id: str):
    wf_path = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not wf_path.exists() or workflow_id.endswith(".meta"):
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": workflow_id,
        "workflow": json.loads(wf_path.read_text(encoding="utf-8-sig")),
        "meta": read_meta(workflow_id),
    })


def validate_pair(workflow: dict, meta: dict | None, refresh: bool = False) -> dict:
    """Run the repo validator on an in-memory workflow+meta pair."""
    import tempfile

    object_info = get_object_info(refresh=refresh)
    with tempfile.TemporaryDirectory() as tmp:
        wf_path = Path(tmp) / "candidate.json"
        wf_path.write_text(json.dumps(workflow), encoding="utf-8")
        if meta:
            (Path(tmp) / "candidate.meta.json").write_text(json.dumps(meta), encoding="utf-8")
        report = validator.validate_workflow(wf_path, object_info)
    return {
        "ok": report.ok,
        "errors": report.errors,
        "warnings": report.warnings,
        "params_found": sorted(report.params),
        "checked_against_live_nodes": object_info is not None,
    }


@app.post("/api/author/validate")
def api_author_validate():
    body = request.get_json(force=True)
    workflow = body.get("workflow")
    if not isinstance(workflow, dict):
        return jsonify({"error": "body.workflow must be a workflow JSON object"}), 400
    return jsonify(validate_pair(workflow, body.get("meta"), bool(body.get("refresh"))))


@app.post("/api/author/save")
def api_author_save():
    global manager
    body = request.get_json(force=True)
    workflow_id = str(body.get("id", "")).strip()
    workflow = body.get("workflow")
    meta = body.get("meta") or {}

    if not re.fullmatch(r"[a-z0-9_]{3,64}", workflow_id):
        return jsonify({"error": "id must be snake_case, 3-64 chars"}), 400
    if not isinstance(workflow, dict):
        return jsonify({"error": "body.workflow must be a workflow JSON object"}), 400

    wf_path = WORKFLOWS_DIR / f"{workflow_id}.json"
    if wf_path.exists() and not body.get("overwrite"):
        return jsonify({"error": f"{workflow_id} already exists (pass overwrite:true)"}), 409

    result = validate_pair(workflow, meta)
    if not result["ok"]:
        return jsonify({"error": "validation failed", **result}), 422

    wf_path.write_text(json.dumps(workflow, indent=2), encoding="utf-8")
    (WORKFLOWS_DIR / f"{workflow_id}.meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    manager = WorkflowManager(WORKFLOWS_DIR)  # re-discover so it shows up immediately
    return jsonify({"saved": workflow_id, **result,
                    "note": "restart comfyui-mcp to expose it as an MCP tool"})


# ------------------------------------------------- interactive bridge

@app.post("/api/author/request")
def api_author_request():
    """Queue a natural-language workflow request for a Claude Code session."""
    body = request.get_json(force=True)
    title = str(body.get("title", "")).strip()
    spec = str(body.get("spec", "")).strip()
    if not title or not spec:
        return jsonify({"error": "title and spec are required"}), 400

    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "request"
    fname = f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}.md"
    (BRIDGE_DIR / fname).write_text(
        f"# Workflow request: {title}\n\n"
        f"Requested via webui at {time.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
        f"## Spec\n\n{spec}\n\n"
        f"## How to fulfill\n\n"
        f"In a Claude Code session, run: `/comfy-create-workflow` with this spec, or ask:\n"
        f'"Build the workflow requested in .omc/webui-requests/{fname}".\n'
        f"Delete this file once the workflow is registered.\n",
        encoding="utf-8",
    )
    return jsonify({"queued": fname})


@app.get("/api/author/requests")
def api_author_requests():
    if not BRIDGE_DIR.is_dir():
        return jsonify([])
    items = []
    for f in sorted(BRIDGE_DIR.glob("*.md"), reverse=True):
        first = f.read_text(encoding="utf-8").splitlines()[0] if f.stat().st_size else ""
        items.append({"file": f.name, "title": first.removeprefix("# Workflow request:").strip()})
    return jsonify(items)


# ---------------------------------------------------------------- entry

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ComfyUI Toolchain web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5055)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger.info("workflows: %s (%d loaded)", WORKFLOWS_DIR, len(manager.tool_definitions))
    logger.info("ComfyUI:   %s", client.base_url)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
