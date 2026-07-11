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

import math
import os
import re
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


def test_enemies_navigate_around_building():
    """Enemies path around building footprints via the runtime-baked navmesh.

    Drive the knight northwest until he tucks against the great-hall/stable
    cluster (settles near x=-2.5, z=0). The ghoul spawns right beside those
    buildings, so to reach the knight it must route around the building/wall
    footprints the navmesh carves out — a naive straight-line chaser would jam
    against the collider. Assert the navmesh baked and an enemy still landed a
    hit (routed around the obstacle and reached the player). Timing-tolerant:
    the long quit-after gives the pathing enemies time to arrive.
    """
    out = run_demo(["--drive=up:6"], quit_after=14.0, timeout=60.0)
    assert_no_script_errors(out)
    assert "NAV_BAKED" in out, f"navmesh never baked:\n{out[-1500:]}"
    assert "PLAYER_HURT" in out, (
        f"no enemy navigated around the buildings to reach the knight:\n{out[-1500:]}"
    )


def test_enemy_stats_from_resources():
    """Damage now comes from the EnemyDef .tres resources, not hardcoded dicts.

    Drive the courtyard so the ghoul (dmg 12) reaches the knight, and the town so
    the dire_rat (dmg 6) does. Each enemy prints its own damage in the PLAYER_HURT
    line, so the exact tokens '-12' and '-6' prove those creatures' resource values
    flow through unchanged — the test fails if the refactor silently altered them.
    """
    court = run_demo(["--drive=up:6"], quit_after=14.0, timeout=60.0)
    assert_no_script_errors(court)
    assert "PLAYER_HURT -12" in court, (
        f"ghoul's resource damage (12) did not reach the knight:\n{court[-1500:]}"
    )

    town = run_demo(["--town", "--drive=left:5"], quit_after=14.0, timeout=60.0)
    assert_no_script_errors(town)
    assert "PLAYER_HURT -6" in town, (
        f"dire_rat's resource damage (6) did not reach the knight:\n{town[-1500:]}"
    )


def test_player_locomotion_animtree():
    """Locomotion is driven by the AnimationTree state machine (G3).

    Drive the knight and assert the state machine actually animates and moves
    him: the run boots without a script/parse error, the structured log shows a
    'walk' (or 'run') locomotion state, and PLAYER_POS advances well clear of
    spawn — proving the AnimationTree replaced the manual _ap.play() calls
    without freezing movement.
    """
    out = run_demo(["--drive=up:4"], quit_after=6.0, timeout=45.0)
    assert_no_script_errors(out)

    positions = [
        (float(m.group(1)), float(m.group(2)))
        for m in re.finditer(r"PLAYER_POS (-?\d+\.\d+),(-?\d+\.\d+)", out)
    ]
    assert len(positions) >= 2, f"no PLAYER_POS telemetry to measure movement:\n{out[-1500:]}"
    spawn = positions[0]
    moved = max(math.hypot(px - spawn[0], pz - spawn[1]) for px, pz in positions)
    assert moved > 0.5, f"knight barely moved under drive ({moved:.2f} units):\n{out[-1500:]}"

    assert ("state=walk" in out) or ("state=run" in out), (
        f"no walk/run locomotion state in the log — state machine not driving:\n{out[-1500:]}"
    )
