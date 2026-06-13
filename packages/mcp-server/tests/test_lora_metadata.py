"""Unit tests for LoRA base-model detection (tools/lora_metadata.py).

Pure unit tests: synthetic safetensors headers (8-byte length prefix + JSON
header, no real tensor data), no GPU, no ComfyUI, no real weights.
"""

import json
import struct
import sys
from pathlib import Path

import pytest

# Ensure the mcp-server package root is importable (tools/ is a top-level pkg).
_MCP_ROOT = Path(__file__).resolve().parents[1]
if str(_MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(_MCP_ROOT))

from tools.lora_metadata import (  # noqa: E402
    classify,
    detect_base_model,
    detect_lora_base_model,
    lora_path,
)


def _write_safetensors(path: Path, header: dict) -> None:
    """Write a minimal valid safetensors file: 8-byte LE length + JSON header.

    No tensor body is written; the body is irrelevant to header-only detection.
    """
    header_bytes = json.dumps(header).encode("utf-8")
    with open(path, "wb") as f:
        f.write(struct.pack("<Q", len(header_bytes)))
        f.write(header_bytes)


# --------------------------------------------------------------------------- #
# classify()
# --------------------------------------------------------------------------- #


def test_classify_flux_by_double_blocks():
    assert classify({"double_blocks.0.lora_up.weight": [1]}) == "flux"


def test_classify_flux_by_single_blocks():
    assert classify({"single_blocks.3.lora_down.weight": [1]}) == "flux"


def test_classify_flux_by_metadata():
    header = {"__metadata__": {"ss_base_model_version": "flux1"}, "some.key": [1]}
    assert classify(header) == "flux"


def test_classify_sdxl_by_te2():
    assert classify({"lora_te2_text_model.weight": [1]}) == "sdxl"


def test_classify_sdxl_by_metadata_xl():
    header = {"__metadata__": {"modelspec.architecture": "stable-diffusion-xl"}, "k": [1]}
    assert classify(header) == "sdxl"


def test_classify_sd15_by_down_blocks_and_te():
    header = {"lora_te_text_model.weight": [1], "down_blocks.0.weight": [1]}
    assert classify(header) == "sd15"


def test_classify_sd15_by_input_blocks():
    assert classify({"input_blocks.1.weight": [1]}) == "sd15"


def test_classify_unknown():
    assert classify({"mystery.tensor": [1]}) == "unknown"


def test_classify_empty_metadata():
    assert classify({"__metadata__": None, "mystery.tensor": [1]}) == "unknown"


# --------------------------------------------------------------------------- #
# detect_base_model() against synthetic files
# --------------------------------------------------------------------------- #


def test_detect_flux_file(tmp_path):
    f = tmp_path / "flux_lora.safetensors"
    _write_safetensors(f, {"double_blocks.0.lora_up.weight": [1]})
    assert detect_base_model(str(f)) == "flux"


def test_detect_sdxl_file(tmp_path):
    f = tmp_path / "sdxl_lora.safetensors"
    _write_safetensors(f, {"lora_te2_text_model.weight": [1]})
    assert detect_base_model(str(f)) == "sdxl"


def test_detect_sd15_file(tmp_path):
    f = tmp_path / "sd15_lora.safetensors"
    _write_safetensors(f, {"lora_te_text_model.weight": [1], "down_blocks.0.weight": [1]})
    assert detect_base_model(str(f)) == "sd15"


def test_detect_garbage_file(tmp_path):
    f = tmp_path / "garbage.safetensors"
    f.write_bytes(b"this is not a safetensors file at all, just junk bytes")
    assert detect_base_model(str(f)) == "unknown"


def test_detect_truncated_header(tmp_path):
    # Declares a header length far larger than the actual remaining bytes.
    f = tmp_path / "truncated.safetensors"
    with open(f, "wb") as fh:
        fh.write(struct.pack("<Q", 10_000))
        fh.write(b"{}")  # only 2 bytes, not 10000
    assert detect_base_model(str(f)) == "unknown"


def test_detect_absurd_header_length(tmp_path):
    # Header length claims gigabytes -> refuse to read, return unknown.
    f = tmp_path / "absurd.safetensors"
    with open(f, "wb") as fh:
        fh.write(struct.pack("<Q", 10 * 1024 * 1024 * 1024))
    assert detect_base_model(str(f)) == "unknown"


def test_detect_too_short_for_length_prefix(tmp_path):
    f = tmp_path / "tiny.safetensors"
    f.write_bytes(b"abc")  # fewer than 8 bytes
    assert detect_base_model(str(f)) == "unknown"


def test_detect_missing_file(tmp_path):
    assert detect_base_model(str(tmp_path / "does_not_exist.safetensors")) == "unknown"


def test_detect_non_json_header(tmp_path):
    f = tmp_path / "badjson.safetensors"
    bad = b"not json at all"
    with open(f, "wb") as fh:
        fh.write(struct.pack("<Q", len(bad)))
        fh.write(bad)
    assert detect_base_model(str(f)) == "unknown"


def test_detect_caches_by_mtime(tmp_path):
    f = tmp_path / "cached.safetensors"
    _write_safetensors(f, {"double_blocks.0.weight": [1]})
    assert detect_base_model(str(f)) == "flux"
    # Repeat call should hit the cache and still return the same result.
    assert detect_base_model(str(f)) == "flux"


# --------------------------------------------------------------------------- #
# lora_path() and detect_lora_base_model()
# --------------------------------------------------------------------------- #


def test_lora_path_none_dir():
    assert lora_path("Foo.safetensors", None) is None


def test_lora_path_resolves_subfolder(tmp_path):
    sub = tmp_path / "style"
    sub.mkdir()
    target = sub / "Foo.safetensors"
    target.write_bytes(b"x")
    # ComfyUI may report Windows-style backslash separators.
    assert lora_path("style\\Foo.safetensors", tmp_path) == target
    assert lora_path("style/Foo.safetensors", tmp_path) == target


def test_lora_path_missing_returns_none(tmp_path):
    assert lora_path("nope.safetensors", tmp_path) is None


def test_detect_lora_base_model_via_subfolder(tmp_path):
    sub = tmp_path / "style"
    sub.mkdir()
    _write_safetensors(sub / "PixelArt.safetensors", {"single_blocks.0.weight": [1]})
    assert detect_lora_base_model("style\\PixelArt.safetensors", tmp_path) == "flux"


def test_detect_lora_base_model_missing_returns_unknown(tmp_path):
    assert detect_lora_base_model("ghost.safetensors", tmp_path) == "unknown"


# --------------------------------------------------------------------------- #
# list_loras base_model filter logic
# --------------------------------------------------------------------------- #


def _filter_tagged(tagged: list[dict], base_model: str | None) -> list[dict]:
    """Mirror of the filter logic in list_loras for isolated unit testing."""
    if not base_model:
        return tagged
    target = base_model.lower()
    return [
        e for e in tagged if e["base_model"] == target or e["base_model"] == "unknown"
    ]


def test_filter_flux_includes_unknown():
    tagged = [
        {"name": "a", "base_model": "flux"},
        {"name": "b", "base_model": "sdxl"},
        {"name": "c", "base_model": "unknown"},
        {"name": "d", "base_model": "sd15"},
    ]
    result = _filter_tagged(tagged, "flux")
    names = {e["name"] for e in result}
    assert names == {"a", "c"}  # flux + unknown, sdxl/sd15 excluded


def test_filter_none_returns_all():
    tagged = [{"name": "a", "base_model": "flux"}, {"name": "b", "base_model": "sdxl"}]
    assert _filter_tagged(tagged, None) == tagged


def test_filter_case_insensitive():
    tagged = [{"name": "a", "base_model": "flux"}]
    assert _filter_tagged(tagged, "FLUX") == tagged


# --------------------------------------------------------------------------- #
# _lora_mismatch_warning (generate_image_lora guard)
# --------------------------------------------------------------------------- #


def test_warning_for_sdxl_lora_on_flux(tmp_path, monkeypatch):
    from tools import generation

    _write_safetensors(tmp_path / "sdxl.safetensors", {"lora_te2_x.weight": [1]})
    monkeypatch.setattr(generation, "resolve_loras_dir", lambda: tmp_path)

    warning = generation._lora_mismatch_warning(
        "generate_image_lora", {"lora_name": "sdxl.safetensors"}
    )
    assert warning is not None
    assert "SDXL" in warning
    assert "FLUX" in warning


def test_no_warning_for_flux_lora_on_flux(tmp_path, monkeypatch):
    from tools import generation

    _write_safetensors(tmp_path / "flux.safetensors", {"double_blocks.0.weight": [1]})
    monkeypatch.setattr(generation, "resolve_loras_dir", lambda: tmp_path)

    warning = generation._lora_mismatch_warning(
        "generate_image_lora", {"lora_name": "flux.safetensors"}
    )
    assert warning is None


def test_no_warning_for_unknown_lora(tmp_path, monkeypatch):
    from tools import generation

    monkeypatch.setattr(generation, "resolve_loras_dir", lambda: tmp_path)
    # Missing file -> 'unknown' -> must pass silently.
    warning = generation._lora_mismatch_warning(
        "generate_image_lora", {"lora_name": "ghost.safetensors"}
    )
    assert warning is None


def test_no_warning_for_non_lora_workflow():
    from tools import generation

    warning = generation._lora_mismatch_warning(
        "generate_image", {"lora_name": "anything.safetensors"}
    )
    assert warning is None


def test_no_warning_when_lora_name_absent():
    from tools import generation

    assert generation._lora_mismatch_warning("generate_image_lora", {}) is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
