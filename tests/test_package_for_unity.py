"""Regression tests for pipelines/animate-ralph/scripts/package_for_unity.py.

GS6: every barbarian clip must import as a CreateFromThisModel Humanoid avatar.
The earlier package made the 8 non-idle clips CopyFromOther idle's avatar, which
the live Unity editor rejected with "Copied Avatar Rig Configuration mis-match:
Transform Armature not found in HumanDescription" (the retarget FBX has an extra
'Armature' transform above 'hips' that a copied, empty-skeleton HumanDescription
can't account for). These tests lock in the CreateFromThisModel-for-every-clip fix.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "pipelines" / "animate-ralph" / "scripts" / "package_for_unity.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("package_for_unity", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pfu():
    return _load_module()


@pytest.mark.parametrize("clip", ["idle", "attack", "walk", "celebrate"])
def test_every_clip_is_create_from_this_model(pfu, clip):
    """No clip may be CopyFromOther — that is the import error GS6 fixes."""
    meta = pfu.fbx_meta(clip, pfu.guid(f"barbarian/Animations/{clip}.fbx"))
    assert "avatarSetup: 1" in meta, f"{clip} must be CreateFromThisModel (avatarSetup: 1)"
    assert "avatarSetup: 2" not in meta, f"{clip} must NOT be CopyFromOther (avatarSetup: 2)"
    assert "animationType: 3" in meta, f"{clip} must import as Humanoid (animationType: 3)"


@pytest.mark.parametrize("clip", ["idle", "attack", "walk", "celebrate"])
def test_no_copied_avatar_reference(pfu, clip):
    """A CopyFromOther avatar ref (fileID 9000000) is what triggers the Armature mismatch."""
    meta = pfu.fbx_meta(clip, pfu.guid(f"barbarian/Animations/{clip}.fbx"))
    assert "lastHumanDescriptionAvatarSource: {instanceID: 0}" in meta
    assert f"fileID: {pfu.UNITY_AVATAR_FILEID}" not in meta, (
        f"{clip} must not reference a copied avatar"
    )


def test_explicit_human_bone_map_present(pfu):
    """The 15 required Mecanim human bones must be written explicitly (no name-guessing)."""
    meta = pfu.fbx_meta("idle", pfu.guid("barbarian/Animations/idle.fbx"))
    for human_name in ("Hips", "Spine", "Head", "LeftHand", "RightHand",
                       "LeftFoot", "RightFoot", "LeftUpperLeg", "RightUpperLeg"):
        assert f"humanName: {human_name}" in meta, f"missing bone map for {human_name}"


def test_all_nine_clips_create_from_this_model(pfu):
    """Across the full clip set, all metas are CreateFromThisModel — none CopyFromOther."""
    setups = [
        pfu.fbx_meta(name, pfu.guid(f"barbarian/Animations/{name}.fbx")).count("avatarSetup: 1")
        for name, *_ in pfu.CLIPS
    ]
    assert len(pfu.CLIPS) == 9
    assert all(s == 1 for s in setups)
