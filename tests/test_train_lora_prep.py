"""Unit tests for scripts/train_lora/prep_dataset.py — runs on a tiny synthetic
fixture set, no external services or GPU needed."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
_PREP = REPO_ROOT / "scripts" / "train_lora" / "prep_dataset.py"

# Load the module directly (scripts/ is not a package).
_spec = importlib.util.spec_from_file_location("prep_dataset", _PREP)
prep_dataset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prep_dataset)  # type: ignore[union-attr]


@pytest.fixture
def fixture_src(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    # two distinct solid-colour RGB images
    Image.new("RGB", (100, 80), (200, 30, 30)).save(src / "red.png")
    Image.new("RGB", (90, 120), (30, 200, 30)).save(src / "green.png")
    # an RGBA image (alpha must be flattened, not skipped)
    Image.new("RGBA", (64, 64), (0, 0, 255, 128)).save(src / "blue_rgba.png")
    # an exact duplicate of red.png -> should be deduped by pixel hash
    Image.new("RGB", (100, 80), (200, 30, 30)).save(src / "red_copy.png")
    # a corrupt "image" -> should be skipped as unreadable
    (src / "broken.png").write_bytes(b"not a real png")
    return src


def test_dedup_corrupt_and_alpha(fixture_src: Path, tmp_path: Path):
    out = tmp_path / "out"
    stats = prep_dataset.prep_dataset([str(fixture_src)], out)

    assert stats["scanned"] == 5
    assert stats["included"] == 3            # red, green, blue_rgba
    assert stats["skipped_duplicate"] == 1   # red_copy
    assert stats["skipped_unreadable"] == 1  # broken.png

    pngs = sorted(p.name for p in out.glob("*.png"))
    assert len(pngs) == 3
    assert (out / "manifest.json").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert len(manifest["images"]) == 3

    # every output is RGB (alpha flattened)
    for p in out.glob("*.png"):
        with Image.open(p) as im:
            assert im.mode == "RGB"


def test_max_edge_downscale(fixture_src: Path, tmp_path: Path):
    out = tmp_path / "out"
    stats = prep_dataset.prep_dataset([str(fixture_src)], out, max_edge=50)
    # red (100) and green (120) exceed 50; blue (64) exceeds too -> all 3 resized
    assert stats["resized"] == 3
    for p in out.glob("*.png"):
        with Image.open(p) as im:
            assert max(im.size) <= 50


def test_max_images_cap(fixture_src: Path, tmp_path: Path):
    out = tmp_path / "out"
    stats = prep_dataset.prep_dataset([str(fixture_src)], out, max_images=2)
    assert stats["included"] == 2
    assert len(list(out.glob("*.png"))) == 2


def test_list_file_input(fixture_src: Path, tmp_path: Path):
    out = tmp_path / "out"
    listing = tmp_path / "files.txt"
    listing.write_text(
        f"# a couple of paths\n{fixture_src / 'red.png'}\n{fixture_src / 'green.png'}\n",
        encoding="utf-8",
    )
    stats = prep_dataset.prep_dataset([], out, list_file=str(listing))
    assert stats["included"] == 2
