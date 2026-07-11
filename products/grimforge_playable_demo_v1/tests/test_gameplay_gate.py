"""Gameplay gate for the GrimForge playable demo.

Drives the Godot build headlessly via its CLI harness (--drive/--fire/--quit-after,
see the wiki page godot-headless-cli-test-harness) and asserts on the structured
stdout event log (godot-structured-stdout-observability). This is the pass/fail
gate ralph's smart_gate runs each bridge iteration: it is the game's automated
playtest.

Godot binary: set GODOT_BIN, else falls back to the known local install. Tests
skip (not fail) when the binary is absent, so a checkout without Godot doesn't
hard-fail the suite.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_GODOT = (
    r"C:/Users/scher/Desktop/Godot_v4.6-stable_win64.exe/Godot_v4.6-stable_win64_console.exe"
)
GODOT_BIN = os.environ.get("GODOT_BIN", DEFAULT_GODOT)

# Godot parse/runtime errors surface on these tokens — the GDScript "compile" gate.
ERROR_TOKENS = ("SCRIPT ERROR", "Parser Error", "Invalid call", "nonexistent function")


def _godot_available() -> bool:
    return Path(GODOT_BIN).exists()


def run_demo(user_args: list[str], quit_after: float = 4.0, timeout: float = 45.0) -> str:
    """Run the demo headless with the given CLI harness args; return stdout+stderr."""
    args = [
        GODOT_BIN,
        "--headless",
        "--path",
        str(PROJECT_DIR),
        "--",
        *user_args,
        f"--quit-after={quit_after}",
    ]
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(PROJECT_DIR),
    )
    return proc.stdout + proc.stderr


def assert_no_script_errors(out: str) -> None:
    hits = [tok for tok in ERROR_TOKENS if tok in out]
    assert not hits, f"Godot reported errors {hits}:\n{out[-1500:]}"


pytestmark = pytest.mark.skipif(
    not _godot_available(), reason=f"Godot binary not found at {GODOT_BIN} (set GODOT_BIN)"
)


def test_courtyard_boots_and_combat():
    """Courtyard boots clean and enemies attack the player (spawn + combat AI)."""
    out = run_demo([], quit_after=5.0)
    assert_no_script_errors(out)
    assert "PLAYER_HURT" in out, f"no enemy landed a hit in the courtyard:\n{out[-1500:]}"


def test_interior_world_populated():
    """Keep interior boots clean and is populated by its roster (world distribution)."""
    out = run_demo(["--interior"], quit_after=4.0)
    assert_no_script_errors(out)
    roster = ("bone_golem", "cultist", "necromancer", "skeleton_mage", "lich_king")
    assert any(name in out for name in roster), (
        f"none of the interior roster {roster} appeared:\n{out[-1500:]}"
    )


def test_town_world_populated():
    """Village town boots clean and its roaming quads are present."""
    out = run_demo(["--town"], quit_after=4.0)
    assert_no_script_errors(out)
    roster = ("dire_rat", "hell_hound", "grave_boar")
    assert any(name in out for name in roster), (
        f"none of the town roster {roster} appeared:\n{out[-1500:]}"
    )
