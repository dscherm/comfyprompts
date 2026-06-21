"""Unit tests for scripts/train_lora/caption.py — the file-writing/idempotency
logic, with the ComfyUI REST layer monkeypatched out (no server needed)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_CAP = REPO_ROOT / "scripts" / "train_lora" / "caption.py"

_spec = importlib.util.spec_from_file_location("tl_caption", _CAP)
caption = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(caption)  # type: ignore[union-attr]


@pytest.fixture
def imgdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "ds"
    d.mkdir()
    for n in ("a", "b"):
        (d / f"{n}.png").write_bytes(b"\x89PNG\r\n")  # content irrelevant (upload mocked)
    # stub the whole REST layer
    monkeypatch.setattr(caption, "preflight", lambda: None)
    monkeypatch.setattr(caption, "load_workflow", lambda name: {})
    monkeypatch.setattr(caption, "upload_local", lambda p: p.name)
    monkeypatch.setattr(caption, "run_caption",
                        lambda name, wf, model, task, timeout=180: "a fierce  norse warrior\n")
    return d


def test_prepend_trigger_and_clean(imgdir: Path):
    stats = caption.caption_dir(imgdir, "brsk_style")
    assert stats == {"images": 2, "captioned": 2, "skipped_existing": 0, "failed": 0}
    for n in ("a", "b"):
        txt = (imgdir / f"{n}.txt").read_text(encoding="utf-8")
        assert txt == "brsk_style, a fierce norse warrior"  # whitespace collapsed


def test_idempotent_skip(imgdir: Path):
    caption.caption_dir(imgdir, "brsk_style")
    stats = caption.caption_dir(imgdir, "brsk_style")
    assert stats["skipped_existing"] == 2
    assert stats["captioned"] == 0


def test_append_position(imgdir: Path):
    caption.caption_dir(imgdir, "brsk_style", position="append")
    txt = (imgdir / "a.txt").read_text(encoding="utf-8")
    assert txt.endswith(", brsk_style")


def test_failure_writes_no_txt(imgdir: Path, monkeypatch: pytest.MonkeyPatch):
    def boom(*a, **k):
        raise RuntimeError("execution failed")
    monkeypatch.setattr(caption, "run_caption", boom)
    stats = caption.caption_dir(imgdir, "brsk_style")
    assert stats["failed"] == 2
    assert stats["captioned"] == 0
    assert not list(imgdir.glob("*.txt"))  # no partial sidecars
