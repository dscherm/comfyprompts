"""LoRA base-model detection via safetensors header inspection.

LoRAs are architecture-specific: an SDXL or SD1.5 LoRA loaded onto a FLUX
checkpoint is silently ignored by ComfyUI's ``LoraLoader`` and produces a
pixel-identical (no-effect) image while the tool reports success. This module
tags each LoRA with its base model family by reading ONLY the safetensors
header (the first few KB), never the multi-gigabyte tensor body.

The flux-vs-not-flux distinction is the load-bearing one and is reliable;
sdxl-vs-sd15 is best-effort. Anything we cannot confidently classify is
returned as ``"unknown"`` and treated as always-compatible so we never hide a
LoRA we simply failed to read.
"""

from __future__ import annotations

import json
import logging
import os
import struct
from pathlib import Path

logger = logging.getLogger("MCP_Server")

# Max bytes we are willing to read for a safetensors header. Real LoRA headers
# are a few KB; a multi-MB "header length" almost certainly means the file is
# not a safetensors file (or is corrupt), so we refuse to read it.
_MAX_HEADER_BYTES = 32 * 1024 * 1024

# Cache: path -> (mtime, base_model). Keyed by mtime so an updated file is
# re-read, but repeated list_loras calls don't re-parse unchanged headers.
_cache: dict[str, tuple[float, str]] = {}


def classify(header: dict) -> str:
    """Classify a parsed safetensors header dict into a base-model family.

    Returns one of ``'flux'``, ``'sdxl'``, ``'sd15'``, or ``'unknown'``.

    The flux-vs-not-flux line is the critical one; sdxl-vs-sd15 is best-effort.
    """
    md = header.get("__metadata__", {}) or {}
    base = (
        md.get("ss_base_model_version") or md.get("modelspec.architecture") or ""
    ).lower()
    keys = [k for k in header if k != "__metadata__"]
    blob = " ".join(keys)

    if "flux" in base or "double_blocks" in blob or "single_blocks" in blob:
        return "flux"

    has_te2 = any("lora_te2" in k or ".te2_" in k for k in keys)
    if "xl" in base or has_te2:
        return "sdxl"

    if (
        "down_blocks" in blob
        or "up_blocks" in blob
        or "lora_te_" in blob
        or "input_blocks" in blob
    ):
        return "sd15"

    return "unknown"


def _read_safetensors_header(path: str) -> dict | None:
    """Read and parse just the JSON header of a safetensors file.

    Returns the parsed header dict, or ``None`` on any error.
    """
    try:
        with open(path, "rb") as f:
            length_bytes = f.read(8)
            if len(length_bytes) < 8:
                return None
            (header_len,) = struct.unpack("<Q", length_bytes)
            if header_len <= 0 or header_len > _MAX_HEADER_BYTES:
                return None
            header_bytes = f.read(header_len)
            if len(header_bytes) < header_len:
                return None
        header = json.loads(header_bytes.decode("utf-8"))
        if not isinstance(header, dict):
            return None
        return header
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def detect_base_model(path: str) -> str:
    """Detect the base-model family of a LoRA safetensors file.

    Reads only the safetensors header (never the tensor body). On ANY error
    (missing, unreadable, not a safetensors file, bad header) returns
    ``'unknown'`` rather than raising.

    Args:
        path: Absolute path to the ``.safetensors`` file.

    Returns:
        One of ``'flux'``, ``'sdxl'``, ``'sd15'``, or ``'unknown'``.
    """
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return "unknown"

    cached = _cache.get(path)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    header = _read_safetensors_header(path)
    if header is None:
        result = "unknown"
    else:
        try:
            result = classify(header)
        except Exception:
            logger.debug("classify() failed for %s", path, exc_info=True)
            result = "unknown"

    _cache[path] = (mtime, result)
    return result


def resolve_loras_dir() -> Path | None:
    """Resolve the local ComfyUI ``loras`` directory.

    Resolution order:
      1. ``COMFYUI_MODELS_ROOT`` env var, joined with ``loras``.
      2. ``COMFYUI_PATH`` env var, joined with ``models/loras``.
      3. A sensible default: ``D:/Projects/ComfyUI/models/loras``.

    Returns the first existing directory, or ``None`` if none exist. When this
    returns ``None``, base-model tagging degrades to ``'unknown'`` for every
    LoRA and nothing breaks.
    """
    candidates: list[Path] = []

    models_root = os.getenv("COMFYUI_MODELS_ROOT")
    if models_root:
        candidates.append(Path(models_root) / "loras")

    comfyui_path = os.getenv("COMFYUI_PATH")
    if comfyui_path:
        candidates.append(Path(comfyui_path) / "models" / "loras")

    candidates.append(Path("D:/Projects/ComfyUI/models/loras"))

    for candidate in candidates:
        try:
            if candidate.is_dir():
                return candidate
        except OSError:
            continue

    return None


def lora_path(lora_name: str, loras_dir: Path | None) -> Path | None:
    """Map a LoRA name to its file path under the loras directory.

    ComfyUI reports LoRA names relative to the loras dir, optionally including
    a subfolder (e.g. ``style\\Foo.safetensors`` or ``style/Foo.safetensors``).
    Returns the resolved path if it exists, else ``None``.

    Args:
        lora_name: The LoRA name as reported by ComfyUI.
        loras_dir: The resolved loras directory (or ``None``).
    """
    if not loras_dir or not lora_name:
        return None
    # Normalize Windows-style separators so pathlib resolves subfolders on any OS.
    normalized = lora_name.replace("\\", "/")
    candidate = loras_dir / normalized
    try:
        if candidate.is_file():
            return candidate
    except OSError:
        return None
    return None


def detect_lora_base_model(lora_name: str, loras_dir: Path | None) -> str:
    """Resolve a LoRA name to a base-model tag.

    Convenience wrapper combining :func:`lora_path` and
    :func:`detect_base_model`. Returns ``'unknown'`` if the file can't be
    located or read.
    """
    path = lora_path(lora_name, loras_dir)
    if path is None:
        return "unknown"
    return detect_base_model(str(path))


# --------------------------------------------------------------------------- #
# Active checkpoint family resolution (for the default prune in list_loras)
# --------------------------------------------------------------------------- #


def _infer_family_from_name(name: str) -> str:
    """Infer a base-model family from a checkpoint filename. Best-effort."""
    lowered = name.lower()
    if "flux" in lowered:
        return "flux"
    if "xl" in lowered:
        return "sdxl"
    if "sd15" in lowered or "1-5" in lowered or "v1-5" in lowered:
        return "sd15"
    return "unknown"


def active_checkpoint_family(defaults_manager) -> str:
    """Resolve the architecture family of the active image checkpoint.

    Resolution order:
      1. ``COMFY_MCP_CHECKPOINT_FAMILY`` env var (explicit override, lowercased).
      2. Infer from the default image checkpoint name via
         ``defaults_manager.get_default("image", "model", None)``.
      3. ``'unknown'`` if nothing resolves.

    Defensive: if ``defaults_manager`` is ``None`` or raises, returns
    ``'unknown'`` rather than propagating.

    Returns one of ``'flux'``, ``'sdxl'``, ``'sd15'``, or ``'unknown'``.
    """
    override = os.getenv("COMFY_MCP_CHECKPOINT_FAMILY")
    if override:
        return override.strip().lower()

    if defaults_manager is None:
        return "unknown"

    try:
        model = defaults_manager.get_default("image", "model", None)
    except Exception:
        logger.debug("defaults_manager.get_default failed", exc_info=True)
        return "unknown"

    if not model or not isinstance(model, str):
        return "unknown"

    return _infer_family_from_name(model)


# --------------------------------------------------------------------------- #
# Manual blocklist (static override)
# --------------------------------------------------------------------------- #

# Reuse the SDK DefaultsManager config dir so the blocklist lives alongside
# config.json (~/.config/comfy-mcp/lora_blocklist.json) and is user-editable.
try:
    from comfyui_agent_sdk.defaults.manager import CONFIG_DIR as _CONFIG_DIR
except Exception:  # pragma: no cover - SDK should always be importable in-server
    _CONFIG_DIR = Path.home() / ".config" / "comfy-mcp"

BLOCKLIST_FILE = _CONFIG_DIR / "lora_blocklist.json"


def load_lora_blocklist() -> set[str]:
    """Load the manual LoRA blocklist as a set of exact lora_name strings.

    Union of two sources, either of which may be absent:
      1. JSON file at ``~/.config/comfy-mcp/lora_blocklist.json`` with the shape
         ``{"blocked": ["name1", "name2", ...]}``.
      2. ``COMFY_MCP_LORA_BLOCKLIST`` env var (comma-separated names).

    Names must match the exact string ComfyUI reports (subfolders may use
    forward slashes). Missing file/env yields an empty set. Never raises.
    """
    blocked: set[str] = set()

    try:
        if BLOCKLIST_FILE.is_file():
            data = json.loads(BLOCKLIST_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                names = data.get("blocked", [])
                if isinstance(names, list):
                    blocked.update(str(n) for n in names if n)
    except (OSError, ValueError, json.JSONDecodeError):
        logger.debug("Failed to read LoRA blocklist file", exc_info=True)

    env_value = os.getenv("COMFY_MCP_LORA_BLOCKLIST")
    if env_value:
        blocked.update(part.strip() for part in env_value.split(",") if part.strip())

    return blocked
