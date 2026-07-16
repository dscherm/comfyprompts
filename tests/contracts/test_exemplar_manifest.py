"""Contract tests for the Tier-2 exemplar corpus (eval/exemplars/manifest.json).

The manifest is the ground-truth binding the VL judge work (VL5-VL8) builds on,
so its shape is pinned here: every criterion binds >=1 good and >=1 bad exemplar
that exist on disk, every pair isolates exactly one variable, and both rig
families (humanoid + quadruped) are represented.

No Blender, no network — pure file/JSON checks against the committed corpus.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "eval" / "exemplars" / "manifest.json"


@pytest.fixture(scope="module")
def manifest() -> dict:
    if not MANIFEST_PATH.exists():
        pytest.skip("exemplar corpus not built (eval/exemplars/manifest.json missing)")
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_every_criterion_has_good_and_bad_pairs(manifest):
    assert manifest["criteria"], "manifest has no criteria"
    for criterion in manifest["criteria"]:
        assert criterion["pairs"], f"criterion {criterion['id']} has no pairs"
        for pair in criterion["pairs"]:
            assert pair["good"] != pair["bad"]


def test_all_referenced_images_exist(manifest):
    missing = [
        pair[key]
        for criterion in manifest["criteria"]
        for pair in criterion["pairs"]
        for key in ("good", "bad")
        if not (REPO_ROOT / pair[key]).exists()
    ]
    assert not missing, f"manifest references missing files: {missing}"


def test_pairs_declare_the_single_differing_variable(manifest):
    for criterion in manifest["criteria"]:
        for pair in criterion["pairs"]:
            assert pair["differing_variable"], (
                f"pair {pair['pose']} in {criterion['id']} does not declare "
                "its differing variable"
            )


def test_rig_deformation_covers_humanoid_and_quadruped(manifest):
    melt = next(
        c for c in manifest["criteria"] if c["id"] == "rig_deformation_melt"
    )
    covered = {pair["project_type"] for pair in melt["pairs"]}
    assert {"humanoid", "quadruped"} <= covered
    assert set(melt["project_types"]) == covered


def test_source_assets_exist_and_live_under_products(manifest):
    for criterion in manifest["criteria"]:
        for pair in criterion["pairs"]:
            src = Path(pair["source_asset"])
            assert not src.is_absolute(), "source_asset must be repo-relative"
            assert src.parts[0] == "products", (
                "exemplars must derive from shipped products/ assets"
            )
            assert (REPO_ROOT / src).exists(), f"source asset missing: {src}"


def test_exemplar_images_live_under_eval(manifest):
    for criterion in manifest["criteria"]:
        for pair in criterion["pairs"]:
            for key in ("good", "bad"):
                assert Path(pair[key]).parts[0] == "eval", (
                    "generated exemplars must live under eval/, never products/"
                )
