"""Unit tests for scripts/train_lora/launch_train.py config generation.
Pure config-building — no GPU, no ai-toolkit deps, no training."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_LT = REPO_ROOT / "scripts" / "train_lora" / "launch_train.py"

_spec = importlib.util.spec_from_file_location("launch_train", _LT)
launch_train = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(launch_train)  # type: ignore[union-attr]


def test_build_config_structure(tmp_path: Path):
    ds = tmp_path / "ds"
    ds.mkdir()
    cfg = launch_train.build_config(
        dataset=str(ds), name="berserkr_style", trigger="brsk_style",
        steps=1500, rank=16, resolutions=[512, 768, 1024],
        output=r"E:\ai-training\flux-output", base="black-forest-labs/FLUX.1-dev",
    )
    # ai-toolkit's preprocess_config requires these top-level keys
    assert cfg["job"] == "extension"
    assert cfg["config"]["name"] == "berserkr_style"
    proc = cfg["config"]["process"][0]
    assert proc["type"] == "sd_trainer"
    assert proc["device"] == "cuda:0"  # CUDA_VISIBLE_DEVICES hides all but target
    assert proc["trigger_word"] == "brsk_style"
    assert proc["network"] == {"type": "lora", "linear": 16, "linear_alpha": 16}
    assert proc["train"]["steps"] == 1500
    assert proc["train"]["gradient_checkpointing"] is True
    assert proc["model"]["name_or_path"] == "black-forest-labs/FLUX.1-dev"
    assert proc["model"]["is_flux"] is True
    # dataset path is absolute (ai-toolkit resolves relative to cwd otherwise)
    assert Path(proc["datasets"][0]["folder_path"]).is_absolute()
    assert proc["datasets"][0]["resolution"] == [512, 768, 1024]
    # sample prompts carry the [trigger] token
    assert any("[trigger]" in p for p in proc["sample"]["prompts"])


def test_config_is_json_serializable(tmp_path: Path):
    ds = tmp_path / "ds"; ds.mkdir()
    cfg = launch_train.build_config(
        dataset=str(ds), name="x", trigger="t", steps=10, rank=8,
        resolutions=[512], output="o", base="b",
    )
    s = json.dumps(cfg)               # must not raise
    assert json.loads(s)["config"]["name"] == "x"


def test_rank_and_steps_parameterized(tmp_path: Path):
    ds = tmp_path / "ds"; ds.mkdir()
    cfg = launch_train.build_config(
        dataset=str(ds), name="x", trigger="t", steps=999, rank=32,
        resolutions=[768], output="o", base="b",
    )
    proc = cfg["config"]["process"][0]
    assert proc["network"]["linear"] == 32
    assert proc["network"]["linear_alpha"] == 32
    assert proc["train"]["steps"] == 999
