"""Validate every parametric workflow in workflows/mcp with the workflow validator.

Structural checks (graph integrity, link references, sidecar consistency) run
always — no ComfyUI needed. Full schema validation against the live
/object_info runs only with `-m integration`.
"""

import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / "workflows" / "mcp"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "workflow_validator.py"
COMFYUI_URL = "http://localhost:8188"


def _comfyui_url() -> str:
    return os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")


def _missing_checkpoint_reason(name: str) -> str | None:
    """Why a live test needing checkpoint `name` cannot run here, or None.
    Asks ComfyUI's /object_info for CheckpointLoaderSimple (read-only)."""
    url = f"{_comfyui_url()}/object_info/CheckpointLoaderSimple"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            info = json.loads(resp.read().decode("utf-8"))
        names = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError) as e:
        return f"ComfyUI not reachable at {_comfyui_url()} ({type(e).__name__})"
    if name not in names:
        return f"checkpoint {name} not installed in ComfyUI at {_comfyui_url()}"
    return None


SDXL_CHECKPOINT = "sd_xl_base_1.0.safetensors"
_SDXL_MISSING = _missing_checkpoint_reason(SDXL_CHECKPOINT)
needs_sdxl = pytest.mark.skipif(_SDXL_MISSING is not None, reason=_SDXL_MISSING or "")

# scripts/ is not a package — load the validator module by path
_spec = importlib.util.spec_from_file_location("workflow_validator", VALIDATOR_PATH)
assert _spec is not None and _spec.loader is not None
validator = importlib.util.module_from_spec(_spec)
sys.modules["workflow_validator"] = validator
_spec.loader.exec_module(validator)


def workflow_files() -> list[Path]:
    return sorted(
        f for f in WORKFLOWS_DIR.glob("*.json") if not f.name.endswith(".meta.json")
    )


@pytest.mark.parametrize("workflow_path", workflow_files(), ids=lambda p: p.stem)
def test_workflow_structure(workflow_path: Path):
    """Every workflow parses, links resolve, no cycles, sidecar is consistent."""
    report = validator.validate_workflow(workflow_path, object_info=None)
    assert report.ok, f"{workflow_path.name}:\n" + "\n".join(report.errors)


def test_every_workflow_has_meta_sidecar():
    missing = [
        f.name for f in workflow_files()
        if not (f.parent / f"{f.stem}.meta.json").exists()
    ]
    assert not missing, f"workflows without .meta.json sidecar: {missing}"


@pytest.mark.integration
@needs_sdxl
def test_workflows_against_live_object_info(tmp_path: Path):
    """Full schema validation against the running ComfyUI's /object_info.

    Workflows with a requires_download block in their sidecar pass with
    warnings; everything else must validate clean against installed nodes
    and models.
    """
    try:
        object_info = validator.fetch_object_info(COMFYUI_URL, tmp_path / "object_info.json")
    except (urllib.error.URLError, OSError) as e:
        pytest.skip(f"ComfyUI not reachable at {COMFYUI_URL}: {e}")

    failures = []
    for workflow_path in workflow_files():
        report = validator.validate_workflow(workflow_path, object_info)
        if not report.ok:
            failures.append(f"{workflow_path.name}: " + "; ".join(report.errors))
    assert not failures, "workflows failing live validation:\n" + "\n".join(failures)
