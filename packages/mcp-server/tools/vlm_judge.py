"""Visual QA of generated images via a local ollama vision model (qwen3-vl).

WHY THIS EXISTS
---------------
Numeric image metrics answer the wrong question. A chroma/histogram metric scores
the WHOLE FRAME and cannot separate a subject from its background — so an image
whose subject is perfectly on-spec, sitting on a flat coloured background, scores
identically to one whose subject is ruined. Measured on a real run: a pixel metric
scored a 10-image batch 3/10 while the batch was ~10/10 by eye, because it was
grading backgrounds. Every "failure" was a false negative.

A vision model can be told "ignore the background, judge the subject", which is
exactly the distinction that matters when judging generation output. On a
hand-labelled 9-image probe (`scripts/vlm_eval/`), qwen3-vl:8b scored 90% of
ground-truth fields and correctly called the hardest case — a monochrome subject on
a flat red field, which the pixel metric had failed. It also caught a real spec
violation that both the metric and a human reviewer had missed.

SCOPE — this is a screen, not an oracle
---------------------------------------
The repo's VL7 probe returned NO-GO for local VLM judging of RIG DEFORMATION: subtle
geometric calls are beyond these models. This tool is for COARSE, ARTICULABLE visual
questions — colour, composition, presence/absence, obvious artifacts. If you cannot
state the criterion in one sentence a person could check at a glance, do not trust
the answer. Prefer it as a gate that flags candidates for human review, not as a
silent auto-accept.

HARDWARE CONTENTION (the trap this tool guards)
-----------------------------------------------
ollama IGNORES CUDA_VISIBLE_DEVICES and loads onto the 3090 Ti — the same card
ComfyUI uses. They do not co-exist:
  * ComfyUI holding a Flux checkpoint leaves ~7GB; qwen3-vl:32b needs ~23GB.
  * torch's caching allocator does NOT return VRAM on model unload alone.
  * At ollama's default num_ctx (32768) the 32b spills across both cards + CPU and
    takes >600s/image instead of ~20s.
So: num_ctx is capped by default, and `free_comfyui_vram=True` asks ComfyUI to
release VRAM (POST /free) before loading the vision model. Call
`unload_vision_model` afterwards to hand the card back to ComfyUI.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger("MCP_Server")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://localhost:8188").rstrip("/")

# Capped deliberately. ollama's 32768 default spills qwen3-vl:32b off-GPU (>600s/image).
DEFAULT_NUM_CTX = 4096
# 8b measured 90% on the probe at 5-24s/image; 32b is slower and needs ~23GB. 8b is
# the right default for a gate that runs on every batch.
DEFAULT_MODEL = "qwen3-vl:8b"

_JSON_INSTRUCTION = (
    "\n\nRespond with EXACTLY one JSON object and nothing else — no markdown fences, "
    'no commentary before or after:\n'
    '{"verdict": "pass"|"fail", "confidence": 0.0-1.0, "reasoning": "<one sentence>", '
    '"observations": {"<field>": "<value>"}}'
)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Find and parse the first balanced {...} block, respecting quoted strings.

    Vision models routinely wrap JSON in prose or markdown fences despite
    instructions, so a naive json.loads on the whole response fails constantly.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth, in_string, escape = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _ollama_reachable() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5)
        return True
    except (urllib.error.URLError, OSError):
        return False


def _list_ollama_models() -> list[dict[str, Any]]:
    with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=10) as resp:
        return json.loads(resp.read().decode()).get("models", [])


def _free_comfyui_vram() -> bool:
    """Ask ComfyUI to unload models and release VRAM. Best-effort."""
    try:
        req = urllib.request.Request(
            f"{COMFYUI_URL}/free",
            data=json.dumps({"unload_models": True, "free_memory": True}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=60)
        return True
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("could not free ComfyUI VRAM: %s", exc)
        return False


def _call_vision_model_once(
    model: str, image_bytes: bytes, prompt: str, num_ctx: int, timeout: float
) -> tuple[str, float]:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [base64.b64encode(image_bytes).decode("ascii")],
            }
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_ctx": num_ctx},
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode())
    return body.get("message", {}).get("content", ""), time.monotonic() - start


def _call_vision_model(
    model: str, image_bytes: bytes, prompt: str, num_ctx: int, timeout: float
) -> tuple[str, float]:
    """Call the model, retrying once on an empty response.

    MEASURED: a cold model load INTERMITTENTLY returns an EMPTY string on the first
    call. Observed on qwen3-vl:8b (33s, loading 6GB) and qwen3-vl:32b (113s, loading
    20GB) — image 1 of 9 came back empty, every later call parsed cleanly — but a
    subsequent cold 8b run did NOT reproduce it. So it is intermittent, not
    deterministic, which is exactly why it needs a retry rather than a warmup call:
    you cannot predict which batch loses its first image.
    """
    raw, latency = _call_vision_model_once(model, image_bytes, prompt, num_ctx, timeout)
    if raw.strip():
        return raw, latency
    logger.info("empty response from %s (likely cold load) — retrying once", model)
    raw2, latency2 = _call_vision_model_once(model, image_bytes, prompt, num_ctx, timeout)
    return raw2, latency + latency2


def _resolve_image(image: str, asset_registry) -> Path:
    """Accept either a filesystem path or an asset_id from the registry."""
    path = Path(image)
    if path.exists():
        return path
    if asset_registry is not None:
        record = None
        try:
            record = asset_registry.get(image)
        except Exception:  # registry APIs vary; fall through to a clear error
            record = None
        if record is not None:
            candidate = Path(getattr(record, "path", "") or "")
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"no image at path or asset_id: {image!r}")


def register_vlm_judge_tools(mcp, asset_registry=None) -> None:
    """Register local-VLM visual QA tools on the FastMCP server."""

    @mcp.tool()
    def judge_image(
        image: str,
        criteria: str,
        model: str = DEFAULT_MODEL,
        free_comfyui_vram: bool = False,
        num_ctx: int = DEFAULT_NUM_CTX,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        """Judge a generated image against stated criteria using a local vision model.

        Use this to CHECK GENERATION OUTPUT instead of assuming it worked. Pixel
        metrics cannot separate a subject from its background; this can, if you say so
        in the criteria.

        Write criteria as a specific, checkable question. Good: "Ignoring the
        background, is the character rendered in monochrome ink with exactly one small
        spot of colour? Report how many distinct accent colours you see." Bad: "Is this
        good?"

        Args:
            image: filesystem path, or an asset_id from the asset registry.
            criteria: what to check. Be specific; state what to IGNORE.
            model: ollama vision model tag (default qwen3-vl:8b; :32b is slower,
                more capable, and needs ~23GB free on the 3090 Ti).
            free_comfyui_vram: ask ComfyUI to release VRAM first. Needed when ComfyUI
                holds a checkpoint and you are loading the 32b. Call
                unload_vision_model afterwards to hand the card back.
            num_ctx: context cap. Do NOT raise to ollama's 32768 default — the 32b
                then spills off-GPU and takes >600s/image.
            timeout: per-request seconds.

        Returns:
            dict with verdict/confidence/reasoning/observations when the model returns
            parseable JSON, plus raw_response, model, latency_s. On unparseable output,
            parse_error=True and raw_response is preserved for inspection.
        """
        if not _ollama_reachable():
            return {
                "error": f"cannot reach ollama at {OLLAMA_URL} — is `ollama serve` running?",
                "parse_error": True,
            }

        try:
            image_path = _resolve_image(image, asset_registry)
        except FileNotFoundError as exc:
            return {"error": str(exc), "parse_error": True}

        if free_comfyui_vram:
            _free_comfyui_vram()

        prompt = criteria.strip() + _JSON_INSTRUCTION
        try:
            raw, latency = _call_vision_model(
                model, image_path.read_bytes(), prompt, num_ctx, timeout
            )
        except (urllib.error.URLError, OSError) as exc:
            return {"error": f"vision model call failed: {exc}", "parse_error": True}

        parsed = _extract_json_object(raw)
        result: dict[str, Any] = {
            "image": str(image_path),
            "model": model,
            "latency_s": round(latency, 2),
            "raw_response": raw,
            "parse_error": parsed is None,
        }
        if parsed is not None:
            result.update(
                {
                    "verdict": parsed.get("verdict"),
                    "confidence": parsed.get("confidence"),
                    "reasoning": parsed.get("reasoning", ""),
                    "observations": parsed.get("observations", {}),
                }
            )
        return result

    @mcp.tool()
    def list_vision_models() -> dict[str, Any]:
        """List local ollama models usable by judge_image, and report VRAM headroom.

        Vision models and ComfyUI compete for the same GPU, so this reports both what
        is installed and whether there is room to load it.
        """
        if not _ollama_reachable():
            return {"error": f"cannot reach ollama at {OLLAMA_URL}", "models": []}

        models = _list_ollama_models()
        vision = [
            {"name": m.get("name"), "size_gb": round(m.get("size", 0) / 2**30, 1)}
            for m in models
            if "-vl" in (m.get("name") or "") or "vision" in (m.get("name") or "")
        ]

        vram: dict[str, Any] = {}
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5) as resp:
                stats = json.loads(resp.read().decode())
            for dev in stats.get("devices", []):
                vram = {
                    "device": dev.get("name"),
                    "free_gb": round(dev.get("vram_free", 0) / 2**30, 1),
                    "total_gb": round(dev.get("vram_total", 0) / 2**30, 1),
                }
                break
        except (urllib.error.URLError, OSError):
            vram = {"note": "ComfyUI unreachable; VRAM headroom unknown"}

        return {
            "vision_models": vision,
            "default": DEFAULT_MODEL,
            "vram": vram,
            "note": (
                "ollama ignores CUDA_VISIBLE_DEVICES and loads on the 3090 Ti. If ComfyUI "
                "holds a checkpoint there is not room for the 32b (~23GB) — pass "
                "free_comfyui_vram=True to judge_image, then call unload_vision_model."
            ),
        }

    @mcp.tool()
    def unload_vision_model(model: str = DEFAULT_MODEL) -> dict[str, Any]:
        """Unload a vision model from VRAM, handing the GPU back to ComfyUI.

        Call this after judging, before further generation — otherwise the vision
        model keeps holding the 3090 Ti and ComfyUI generation slows or OOMs.
        """
        try:
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate",
                data=json.dumps({"model": model, "keep_alive": 0}).encode(),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=30)
            return {"unloaded": model}
        except (urllib.error.URLError, OSError) as exc:
            return {"error": f"could not unload {model}: {exc}"}
