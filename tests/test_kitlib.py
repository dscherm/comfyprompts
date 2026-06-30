"""Unit tests for the GrimForge kit DSL (tools/asset_generators/village_kit/kitlib.py).

These cover the pure, Blender-free surface so they run in plain CI. The
``Kit`` class needs ``bpy`` and is exercised separately by the Blender smoke
test (kitlib_smoke.py); here we only assert it refuses to construct without
Blender, and skip if ``bpy`` happens to be importable.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_KITLIB = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "asset_generators"
    / "village_kit"
    / "kitlib.py"
)


def _load_kitlib():
    spec = importlib.util.spec_from_file_location("kitlib", _KITLIB)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


kitlib = _load_kitlib()


def test_module_imports_without_blender():
    """The pure surface must import even though bpy is absent in CI."""
    assert "bpy" not in sys.modules or sys.modules["bpy"] is not None
    assert hasattr(kitlib, "Kit")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("000000", (0.0, 0.0, 0.0, 1.0)),
        ("ffffff", (1.0, 1.0, 1.0, 1.0)),
        ("#ff8a2a", (1.0, 138 / 255, 42 / 255, 1.0)),
        ("6f756a", (0x6F / 255, 0x75 / 255, 0x6A / 255, 1.0)),
    ],
)
def test_hex_to_rgba_values(value, expected):
    result = kitlib.hex_to_rgba(value)
    assert result == pytest.approx(expected)
    assert result[3] == 1.0


@pytest.mark.parametrize("bad", ["", "fff", "12345", "1234567", "gggggg", "ff 8a2a"])
def test_hex_to_rgba_rejects_malformed(bad):
    with pytest.raises(ValueError):
        kitlib.hex_to_rgba(bad)


def test_palette_is_all_valid_hex():
    for name, value in kitlib.PALETTE.items():
        rgba = kitlib.hex_to_rgba(value)
        assert len(rgba) == 4
        assert all(0.0 <= c <= 1.0 for c in rgba), name


def test_palette_has_core_and_expansion_keys():
    # Vol.1 staples + Vol.2 additions must both survive the merge.
    for key in ("stone", "wood", "thatch", "slate", "fire", "window"):
        assert key in kitlib.PALETTE
    for key in ("pine", "water", "flag", "bone", "bone_pale"):
        assert key in kitlib.PALETTE


def test_bone_conflict_preserved():
    # The two kits disagreed on "bone"; both values must be reachable so
    # existing assets reproduce exactly.
    assert kitlib.PALETTE["bone"] == "c4bba2"
    assert kitlib.PALETTE["bone_pale"] == "d8d0bc"


def test_emission_names_are_in_palette():
    for name in kitlib.EMISSION:
        assert name in kitlib.PALETTE
    assert kitlib.EMISSION["fire"] == 2.0
    assert kitlib.EMISSION["window"] == 1.5


def test_occult_palette_and_emissives():
    # dark-fantasy sub-palette additions (incl. LoRA-derived accents)
    for key in ("charwood", "soot", "ash", "shroud", "rot", "blood", "gore",
                "crimson", "gunmetal", "steel"):
        assert key in kitlib.PALETTE
    # occult glow accents must be both in the palette and emissive
    for key in ("ember", "amber", "gem", "witchlight", "ghostfire", "rune"):
        assert key in kitlib.PALETTE
        assert key in kitlib.EMISSION
        assert kitlib.EMISSION[key] > 0


def test_validate_palette_passes():
    kitlib.validate_palette()  # must not raise


def test_validate_palette_catches_bad_entry(monkeypatch):
    monkeypatch.setitem(kitlib.PALETTE, "_broken", "nothex")
    try:
        with pytest.raises(ValueError):
            kitlib.validate_palette()
    finally:
        kitlib.PALETTE.pop("_broken", None)


def test_kit_requires_blender():
    """Without bpy installed, constructing Kit raises ImportError."""
    if importlib.util.find_spec("bpy") is not None:
        pytest.skip("bpy available (running inside Blender) — see kitlib_smoke.py")
    with pytest.raises(ModuleNotFoundError):
        kitlib.Kit()
