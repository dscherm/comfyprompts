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
    active_checkpoint_family,
    classify,
    detect_base_model,
    detect_lora_base_model,
    load_lora_blocklist,
    lora_path,
)

from tools import lora_metadata  # noqa: E402


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


# --------------------------------------------------------------------------- #
# active_checkpoint_family
# --------------------------------------------------------------------------- #


class _StubDefaults:
    def __init__(self, model):
        self._model = model

    def get_default(self, namespace, key, provided=None):
        return self._model


def test_active_family_env_override(monkeypatch):
    monkeypatch.setenv("COMFY_MCP_CHECKPOINT_FAMILY", "SDXL")
    # Override wins even if defaults would say flux.
    assert active_checkpoint_family(_StubDefaults("flux1-dev.safetensors")) == "sdxl"


def test_active_family_infer_flux(monkeypatch):
    monkeypatch.delenv("COMFY_MCP_CHECKPOINT_FAMILY", raising=False)
    assert active_checkpoint_family(_StubDefaults("flux1-dev-fp8.safetensors")) == "flux"


def test_active_family_infer_sdxl(monkeypatch):
    monkeypatch.delenv("COMFY_MCP_CHECKPOINT_FAMILY", raising=False)
    assert active_checkpoint_family(_StubDefaults("sd_xl_base_1.0.safetensors")) == "sdxl"


def test_active_family_infer_sd15(monkeypatch):
    monkeypatch.delenv("COMFY_MCP_CHECKPOINT_FAMILY", raising=False)
    assert active_checkpoint_family(_StubDefaults("v1-5-pruned.safetensors")) == "sd15"


def test_active_family_unknown_name(monkeypatch):
    monkeypatch.delenv("COMFY_MCP_CHECKPOINT_FAMILY", raising=False)
    assert active_checkpoint_family(_StubDefaults("mystery_checkpoint.safetensors")) == "unknown"


def test_active_family_none_defaults(monkeypatch):
    monkeypatch.delenv("COMFY_MCP_CHECKPOINT_FAMILY", raising=False)
    assert active_checkpoint_family(None) == "unknown"


def test_active_family_defaults_raises(monkeypatch):
    monkeypatch.delenv("COMFY_MCP_CHECKPOINT_FAMILY", raising=False)

    class _Boom:
        def get_default(self, *a, **k):
            raise RuntimeError("boom")

    assert active_checkpoint_family(_Boom()) == "unknown"


# --------------------------------------------------------------------------- #
# load_lora_blocklist (never touch the real user config in tests)
# --------------------------------------------------------------------------- #


def test_blocklist_missing_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(lora_metadata, "BLOCKLIST_FILE", tmp_path / "nope.json")
    monkeypatch.delenv("COMFY_MCP_LORA_BLOCKLIST", raising=False)
    assert load_lora_blocklist() == set()


def test_blocklist_reads_file(monkeypatch, tmp_path):
    f = tmp_path / "lora_blocklist.json"
    f.write_text(json.dumps({"blocked": ["a.safetensors", "style/b.safetensors"]}))
    monkeypatch.setattr(lora_metadata, "BLOCKLIST_FILE", f)
    monkeypatch.delenv("COMFY_MCP_LORA_BLOCKLIST", raising=False)
    assert load_lora_blocklist() == {"a.safetensors", "style/b.safetensors"}


def test_blocklist_reads_env(monkeypatch, tmp_path):
    monkeypatch.setattr(lora_metadata, "BLOCKLIST_FILE", tmp_path / "nope.json")
    monkeypatch.setenv("COMFY_MCP_LORA_BLOCKLIST", "x.safetensors, y.safetensors")
    assert load_lora_blocklist() == {"x.safetensors", "y.safetensors"}


def test_blocklist_merges_file_and_env(monkeypatch, tmp_path):
    f = tmp_path / "lora_blocklist.json"
    f.write_text(json.dumps({"blocked": ["a.safetensors"]}))
    monkeypatch.setattr(lora_metadata, "BLOCKLIST_FILE", f)
    monkeypatch.setenv("COMFY_MCP_LORA_BLOCKLIST", "b.safetensors")
    assert load_lora_blocklist() == {"a.safetensors", "b.safetensors"}


def test_blocklist_bad_json_never_raises(monkeypatch, tmp_path):
    f = tmp_path / "lora_blocklist.json"
    f.write_text("{ not valid json")
    monkeypatch.setattr(lora_metadata, "BLOCKLIST_FILE", f)
    monkeypatch.delenv("COMFY_MCP_LORA_BLOCKLIST", raising=False)
    assert load_lora_blocklist() == set()


# --------------------------------------------------------------------------- #
# list_loras default-prune behavior (integration of the pieces)
# --------------------------------------------------------------------------- #


class _StubClient:
    def __init__(self, names):
        self._names = names

    def get_lora_models(self):
        return list(self._names)


def _build_list_loras(monkeypatch, tmp_path, names, tags, family="flux", blocked=None):
    """Register list_loras against stubbed deps and return the captured callable.

    Patches detection (name -> tag from `tags`), the checkpoint family, the
    loras dir, and the blocklist so no real files/ComfyUI are touched.
    """
    from mcp.server.fastmcp import FastMCP

    from tools import model_management

    monkeypatch.setattr(
        model_management, "detect_lora_base_model", lambda name, d: tags.get(name, "unknown")
    )
    monkeypatch.setattr(model_management, "resolve_loras_dir", lambda: tmp_path)
    monkeypatch.setattr(model_management, "active_checkpoint_family", lambda dm: family)
    monkeypatch.setattr(model_management, "load_lora_blocklist", lambda: set(blocked or []))

    captured = {}

    mcp = FastMCP("test")
    orig_tool = mcp.tool

    def _tool(*a, **k):
        def deco(fn):
            captured[fn.__name__] = fn
            return orig_tool(*a, **k)(fn)

        return deco

    monkeypatch.setattr(mcp, "tool", _tool)
    model_management.register_model_management_tools(
        mcp, _StubClient(names), defaults_manager=object()
    )
    return captured["list_loras"]


def test_list_loras_prunes_mismatched_by_default(monkeypatch, tmp_path):
    names = ["flux_a.safetensors", "sdxl_b.safetensors", "sd15_c.safetensors", "myst.safetensors"]
    tags = {
        "flux_a.safetensors": "flux",
        "sdxl_b.safetensors": "sdxl",
        "sd15_c.safetensors": "sd15",
        "myst.safetensors": "unknown",
    }
    list_loras = _build_list_loras(monkeypatch, tmp_path, names, tags, family="flux")
    result = list_loras()
    assert set(result["loras"]) == {"flux_a.safetensors", "myst.safetensors"}
    assert result["target_family"] == "flux"
    assert result["excluded"] == 2
    assert result["count"] == 2


def test_list_loras_prunes_blocklisted(monkeypatch, tmp_path):
    names = ["flux_a.safetensors", "flux_blocked.safetensors"]
    tags = {"flux_a.safetensors": "flux", "flux_blocked.safetensors": "flux"}
    list_loras = _build_list_loras(
        monkeypatch, tmp_path, names, tags, family="flux", blocked=["flux_blocked.safetensors"]
    )
    result = list_loras()
    assert result["loras"] == ["flux_a.safetensors"]
    assert result["excluded"] == 1


def test_list_loras_include_incompatible_returns_all(monkeypatch, tmp_path):
    names = ["flux_a.safetensors", "sdxl_b.safetensors"]
    tags = {"flux_a.safetensors": "flux", "sdxl_b.safetensors": "sdxl"}
    list_loras = _build_list_loras(
        monkeypatch, tmp_path, names, tags, family="flux", blocked=["sdxl_b.safetensors"]
    )
    result = list_loras(include_incompatible=True)
    assert set(result["loras"]) == {"flux_a.safetensors", "sdxl_b.safetensors"}
    assert result["excluded"] == 0


def test_list_loras_explicit_base_model_flips_filter(monkeypatch, tmp_path):
    names = ["flux_a.safetensors", "sdxl_b.safetensors"]
    tags = {"flux_a.safetensors": "flux", "sdxl_b.safetensors": "sdxl"}
    # Active family is flux, but explicit base_model='sdxl' overrides it.
    list_loras = _build_list_loras(monkeypatch, tmp_path, names, tags, family="flux")
    result = list_loras(base_model="sdxl")
    assert result["loras"] == ["sdxl_b.safetensors"]
    assert result["target_family"] == "sdxl"


def test_list_loras_unknown_family_keeps_all(monkeypatch, tmp_path):
    # When target family is unknown, the architecture filter is a no-op.
    names = ["flux_a.safetensors", "sdxl_b.safetensors"]
    tags = {"flux_a.safetensors": "flux", "sdxl_b.safetensors": "sdxl"}
    list_loras = _build_list_loras(monkeypatch, tmp_path, names, tags, family="unknown")
    result = list_loras()
    assert set(result["loras"]) == {"flux_a.safetensors", "sdxl_b.safetensors"}
    assert result["excluded"] == 0


# --------------------------------------------------------------------------- #
# normalize_model_path_separators (Windows LoRA enum-match bug)
# --------------------------------------------------------------------------- #
#
# ComfyUI enumerates nested model files with the host OS separator and validates
# a submitted lora_name by EXACT STRING MATCH. On Windows a forward-slash
# subfoldered name (e.g. "style/Foo.safetensors") fails against the enum entry
# "style\Foo.safetensors", raising "Prompt outputs failed validation". The
# render chokepoint must rewrite such names to os.sep before submission.

import os as _os  # noqa: E402

from managers.workflow_manager import (  # noqa: E402
    WorkflowManager,
    normalize_model_path_separators,
)
from models.workflow import WorkflowParameter, WorkflowToolDefinition  # noqa: E402


def test_normalize_forward_slash_lora_to_os_sep():
    wf = {
        "2": {
            "class_type": "LoraLoader",
            "inputs": {"lora_name": "style/berserkr_style.safetensors", "model": ["1", 0]},
        }
    }
    normalize_model_path_separators(wf)
    assert wf["2"]["inputs"]["lora_name"] == "style" + _os.sep + "berserkr_style.safetensors"


def test_normalize_backslash_lora_to_os_sep():
    wf = {
        "2": {
            "class_type": "LoraLoader",
            "inputs": {"lora_name": "style\\berserkr_style.safetensors"},
        }
    }
    normalize_model_path_separators(wf)
    assert wf["2"]["inputs"]["lora_name"] == "style" + _os.sep + "berserkr_style.safetensors"


def test_normalize_checkpoint_subfolder():
    wf = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sub/model.safetensors"}}}
    normalize_model_path_separators(wf)
    assert wf["1"]["inputs"]["ckpt_name"] == "sub" + _os.sep + "model.safetensors"


def test_normalize_leaves_node_links_and_plain_names_untouched():
    wf = {
        "2": {
            "class_type": "LoraLoader",
            "inputs": {"lora_name": "Foo.safetensors", "model": ["1", 0], "clip": ["1", 1]},
        }
    }
    normalize_model_path_separators(wf)
    # No separator -> unchanged; node-link lists -> unchanged.
    assert wf["2"]["inputs"]["lora_name"] == "Foo.safetensors"
    assert wf["2"]["inputs"]["model"] == ["1", 0]
    assert wf["2"]["inputs"]["clip"] == ["1", 1]


def test_normalize_ignores_non_model_string_inputs():
    # A subfoldered-looking value under a non-model key must be left alone.
    wf = {"8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "out/run1"}}}
    normalize_model_path_separators(wf)
    assert wf["8"]["inputs"]["filename_prefix"] == "out/run1"


def test_render_workflow_normalizes_param_lora_name():
    """End-to-end: a forward-slash lora_name tool arg is os.sep before submit."""
    template = {
        "2": {
            "class_type": "LoraLoader",
            "inputs": {"lora_name": "PARAM_STR_LORA_NAME", "model": ["1", 0]},
        }
    }
    param = WorkflowParameter(
        name="lora_name",
        placeholder="PARAM_STR_LORA_NAME",
        annotation=str,
        description="LoRA name",
        bindings=[("2", "lora_name")],
        required=True,
    )
    definition = WorkflowToolDefinition(
        workflow_id="generate_image_lora",
        tool_name="generate_image_lora",
        description="test",
        template=template,
        parameters={"lora_name": param},
        output_preferences=("images",),
    )
    mgr = WorkflowManager.__new__(WorkflowManager)  # skip filesystem __init__
    rendered = mgr.render_workflow(definition, {"lora_name": "style/berserkr_style.safetensors"})
    assert rendered["2"]["inputs"]["lora_name"] == "style" + _os.sep + "berserkr_style.safetensors"


def test_render_workflow_normalizes_literal_default_lora_name():
    """Literal (non-PARAM) model names baked in the template are normalized too."""
    template = {
        "2": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "style/PixelArtV3Flux.safetensors",  # hardcoded, no PARAM
                "strength_model": "PARAM_FLOAT_LORA_STRENGTH",
                "model": ["1", 0],
            },
            "_defaults": {"PARAM_FLOAT_LORA_STRENGTH": 0.85},
        }
    }
    strength = WorkflowParameter(
        name="lora_strength",
        placeholder="PARAM_FLOAT_LORA_STRENGTH",
        annotation=float,
        description="strength",
        bindings=[("2", "strength_model")],
        required=False,
        default=0.85,
    )
    definition = WorkflowToolDefinition(
        workflow_id="generate_image_pixelart",
        tool_name="generate_image_pixelart",
        description="test",
        template=template,
        parameters={"lora_strength": strength},
        output_preferences=("images",),
    )
    mgr = WorkflowManager.__new__(WorkflowManager)
    rendered = mgr.render_workflow(definition, {})
    assert rendered["2"]["inputs"]["lora_name"] == "style" + _os.sep + "PixelArtV3Flux.safetensors"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
