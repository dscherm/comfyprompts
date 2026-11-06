"""Blind-TDD contract tests for pipelines/godot_import.py (task AP-2).

The Godot import stage lands a GLB in a Godot 4 project under the project's
import contract (<project>/import_rules.json, merged key-by-key with
<kit>/import_overrides.json) and checks it. Surface (from public_api.md):

    class ConfigError(RuntimeError)
    class RulesError(ValueError)
    load_rules(project_dir, kit=None) -> dict
    import_glb(glb, project_dir, kit=None, config_path=None) -> dict
        # {"ok": bool, "checks": [{"name", "ok", "detail"}, ...], "shot": str|None}
    main(argv=None) -> int   # 0 ok, 1 a check failed, 2 refused (stderr)

The module is loaded by file path (nothing here is pip-installed). The loader
raises FileNotFoundError until the implementation exists, so every behavioural
test errors in the red phase; the static scans fail on the "implementation
file exists" assertion.

Live tests (AC-1, AC-2, AC-3) run real Godot through the repo-root
schermness.config.json `tools.godot_bin` (config_path=None). Each scenario runs
the stage exactly once (module-scoped fixture or a single test), ~10 s each.
"""

import importlib.util
import itertools
import json
import os
import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

# parents[2] from tests/contracts/<this file> == repo root.
_REPO = Path(__file__).resolve().parents[2]
_MOD_PATH = _REPO / "pipelines" / "godot_import.py"

# Implementation files named by the task (static scans read these as text).
_IMPL_FILES = [_MOD_PATH]

_DEFAULT_GLB = Path(
    "D:/Projects/comfyui-toolchain/products/grimforge_bestiary_v1/_quadrig/dire_rat_v2.glb"
)

_PROJECT_GODOT = 'config_version=5\n\n[application]\nconfig/name="t"\n'

_load_counter = itertools.count()


def load_stage():
    """Load a FRESH copy of pipelines/godot_import.py from its source path.

    Raises FileNotFoundError while the implementation is missing (red phase).
    """
    name = f"godot_import_under_test_{next(_load_counter)}"
    spec = importlib.util.spec_from_file_location(name, _MOD_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # FileNotFoundError until implemented
    return mod


def _fixture_glb() -> Path:
    return Path(os.environ.get("GRIMFORGE_CREATURE_GLB", str(_DEFAULT_GLB)))


def _require_fixture() -> Path:
    src = _fixture_glb()
    if not src.is_file():
        pytest.skip(f"GrimForge fixture GLB not found: {src}")
    return src


def _make_project(root: Path, rules: dict | None) -> Path:
    """A minimal Godot 4 project: project.godot (+ import_rules.json)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "project.godot").write_text(_PROJECT_GODOT, encoding="utf-8")
    if rules is not None:
        (root / "import_rules.json").write_text(json.dumps(rules), encoding="utf-8")
    return root


def _make_kit(root: Path, overrides: dict | None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    if overrides is not None:
        (root / "import_overrides.json").write_text(json.dumps(overrides), encoding="utf-8")
    return root


def _snapshot(directory: Path) -> list[tuple[str, int]]:
    """Recursive (relative path, size) listing; dirs have size -1."""
    out = []
    for p in sorted(directory.rglob("*")):
        rel = p.relative_to(directory).as_posix()
        out.append((rel, p.stat().st_size if p.is_file() else -1))
    return out


def _write_config(path: Path, content: dict) -> Path:
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


# ---- GLB helpers (binary glTF: 12-byte header, JSON chunk, optional BIN) ----

def _read_glb(path: Path) -> tuple[dict, bytes]:
    data = Path(path).read_bytes()
    magic, version, _length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF" and version == 2, f"{path} is not a GLB v2"
    chunk_len, chunk_type = struct.unpack_from("<I4s", data, 12)
    assert chunk_type == b"JSON"
    doc = json.loads(data[20 : 20 + chunk_len].decode("utf-8"))
    rest = data[20 + chunk_len :]  # remaining chunks (BIN), untouched
    return doc, rest


def _write_glb(path: Path, doc: dict, rest: bytes) -> None:
    js = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)  # JSON chunk padded with spaces
    body = struct.pack("<I4s", len(js), b"JSON") + js + rest
    header = struct.pack("<4sII", b"glTF", 2, 12 + len(body))
    Path(path).write_bytes(header + body)


def _animation_names(path: Path) -> list[str]:
    doc, _ = _read_glb(path)
    return [a.get("name", "") for a in doc.get("animations", [])]


def _check(result: dict, name: str) -> dict:
    matches = [c for c in result["checks"] if c["name"] == name]
    assert len(matches) == 1, (
        f"expected exactly one check named {name!r}; checks: "
        f"{[c['name'] for c in result['checks']]}"
    )
    return matches[0]


def _assert_gate_shape(result: dict) -> None:
    assert isinstance(result, dict)
    assert isinstance(result["ok"], bool)
    assert isinstance(result["checks"], list) and result["checks"]
    for c in result["checks"]:
        assert isinstance(c["name"], str)
        assert isinstance(c["ok"], bool)
        assert isinstance(c["detail"], str)
    assert "shot" in result


class _PopenSpy:
    """Records any attempt to launch a process; never launches one."""

    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        raise FileNotFoundError("process launch blocked by test spy")


@pytest.fixture
def popen_spy(monkeypatch):
    """Patch subprocess.Popen (subprocess.run uses it) before the module loads."""
    spy = _PopenSpy()
    monkeypatch.setattr(subprocess, "Popen", spy)
    return spy


# --------------------------------------------------------------------------
# Module-scoped live runs (real Godot, repo-root config)
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ac1_run(tmp_path_factory):
    """One real stage run on the AC-1 project (convex, idle+walk)."""
    src = _require_fixture()
    base = tmp_path_factory.mktemp("ac1")
    glb = base / "src" / src.name
    glb.parent.mkdir()
    shutil.copy2(src, glb)
    project = _make_project(
        base / "project",
        {"scale": 1.0, "collision": "convex", "animation_names": ["idle", "walk"]},
    )
    stage = load_stage()
    result = stage.import_glb(glb, project, kit=None, config_path=None)
    return result, project


@pytest.fixture(scope="module")
def ac3_run(tmp_path_factory):
    """One real stage run: project says convex, kit override says box."""
    src = _require_fixture()
    base = tmp_path_factory.mktemp("ac3")
    glb = base / "src" / src.name
    glb.parent.mkdir()
    shutil.copy2(src, glb)
    project = _make_project(base / "project", {"scale": 1.0, "collision": "convex"})
    kit = _make_kit(base / "kit_box", {"collision": "box"})
    stage = load_stage()
    result = stage.import_glb(glb, project, kit=kit, config_path=None)
    return result, project


# --------------------------------------------------------------------------
# AC-1 — matching GLB + rules: ok, every check ok, shot PNG exists
# --------------------------------------------------------------------------

def test_matching_glb_passes_every_check_and_writes_shot(ac1_run):
    """Covers: AC-1 — rules {scale 1.0, convex, [idle, walk]} on the creature.

    Given a temp Godot project with import_rules.json {scale: 1.0,
    collision: convex, animation_names: [idle, walk]} and the GrimForge
    creature GLB (which has both clips),
    when import_glb runs with the repo config,
    then ok is true, every check is ok, the documented checks are present
    (import, scale, collision naming convex, animation:idle, animation:walk,
    shot; no material_slots check since that rule is unset), and the shot is
    an existing PNG under <project>/_shots/.
    """
    result, project = ac1_run
    _assert_gate_shape(result)

    failing = [c for c in result["checks"] if not c["ok"]]
    assert failing == [], f"checks failed: {failing}"
    assert result["ok"] is True

    names = {c["name"] for c in result["checks"]}
    for required in ("import", "scale", "collision", "animation:idle",
                     "animation:walk", "shot"):
        assert required in names, f"missing check {required!r}; have {sorted(names)}"
    assert "material_slots" not in names, "material_slots is checked only when set"
    assert "convex" in _check(result, "collision")["detail"]

    shot = result["shot"]
    assert isinstance(shot, str)
    shot_path = Path(shot)
    assert shot_path.is_absolute(), f"shot is not absolute: {shot}"
    assert shot_path.is_file(), f"shot PNG does not exist: {shot}"
    assert shot_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "shot is not a PNG"
    assert (project / "_shots").resolve() in shot_path.resolve().parents


def test_matching_glb_is_landed_under_default_land_in(ac1_run):
    """Covers: AC-1 — the GLB is copied under land_in (default res://imported/).

    Given the AC-1 run (rules without land_in),
    when the stage has run,
    then a .glb file exists under <project>/imported/.
    """
    _result, project = ac1_run
    landed = list((project / "imported").rglob("*.glb"))
    assert landed, "no GLB landed under <project>/imported/"


# --------------------------------------------------------------------------
# AC-2 — required clip missing: ok false, failing check names 'attack'
# --------------------------------------------------------------------------

def test_missing_attack_clip_fails_naming_attack(tmp_path, capsys):
    """Covers: AC-2 — rules require 'attack', the GLB lacks it.

    Given a copy of the creature GLB with its 'attack' animation removed
    (verified by parsing the GLB) and rules animation_names [idle, attack],
    when the CLI main([glb, project]) runs,
    then it returns 1, prints the gate dict as JSON on stdout with ok false,
    the failing check's name and detail both contain 'attack', and the
    control clip's check (animation:idle) is ok — so the failure is about the
    missing clip, not a broken stage.
    """
    src = _require_fixture()
    doc, rest = _read_glb(src)
    anims = doc.get("animations", [])
    kept = [a for a in anims if "attack" not in a.get("name", "").lower()]
    assert len(kept) < len(anims), (
        f"fixture has no 'attack' animation to strip: {[a.get('name') for a in anims]}"
    )
    doc["animations"] = kept
    glb = tmp_path / "src" / "no_attack.glb"
    glb.parent.mkdir()
    _write_glb(glb, doc, rest)
    names_after = _animation_names(glb)
    assert not any("attack" in n.lower() for n in names_after)
    assert any("idle" in n.lower() for n in names_after)

    project = _make_project(
        tmp_path / "project", {"animation_names": ["idle", "attack"]}
    )
    stage = load_stage()
    capsys.readouterr()
    rc = stage.main([str(glb), str(project)])
    out = capsys.readouterr().out

    assert rc == 1, f"expected exit 1 (a check failed), got {rc}"
    result = json.loads(out)
    _assert_gate_shape(result)
    assert result["ok"] is False

    failing = [c for c in result["checks"] if not c["ok"]]
    attack_fail = [c for c in failing if "attack" in c["name"]]
    assert attack_fail, f"no failing check names 'attack': {failing}"
    assert "attack" in attack_fail[0]["detail"]
    assert _check(result, "animation:idle")["ok"] is True


# --------------------------------------------------------------------------
# AC-3 — kit override collision: box replaces the project's convex
# --------------------------------------------------------------------------

def test_kit_override_replaces_project_collision_in_load_rules(tmp_path):
    """Covers: AC-3 — load_rules merges import_overrides.json key by key.

    Given a project whose import_rules.json says collision convex (scale 2.0)
    and a kit folder whose import_overrides.json says collision box,
    when load_rules(project) and load_rules(project, kit) are called,
    then without the kit collision is convex (control); with the kit it is
    box, the project's other keys survive (scale 2.0), and source names both
    files.
    """
    project = _make_project(tmp_path / "project", {"scale": 2.0, "collision": "convex"})
    kit = _make_kit(tmp_path / "kit_box", {"collision": "box"})
    stage = load_stage()

    base = stage.load_rules(project)
    assert base["collision"] == "convex"

    merged = stage.load_rules(project, kit)
    assert merged["collision"] == "box"
    assert merged["scale"] == pytest.approx(2.0)
    joined = " ".join(str(s) for s in merged["source"])
    assert "import_rules.json" in joined
    assert "import_overrides.json" in joined


def test_kit_without_overrides_changes_nothing(tmp_path):
    """Covers: AC-3 — a kit folder without import_overrides.json is a no-op.

    Given a project saying convex and an empty kit folder,
    when load_rules(project, kit) is called,
    then collision stays convex.
    """
    project = _make_project(tmp_path / "project", {"collision": "convex"})
    kit = _make_kit(tmp_path / "kit_empty", None)
    stage = load_stage()
    assert stage.load_rules(project, kit)["collision"] == "convex"


def test_kit_override_collision_check_reports_box_not_convex(ac3_run):
    """Covers: AC-3 — the live collision check reports the kit's box.

    Given a project saying collision convex and a kit overriding it to box,
    when import_glb runs with that kit,
    then the collision check is ok and its detail names box and not convex.
    """
    result, _project = ac3_run
    _assert_gate_shape(result)
    check = _check(result, "collision")
    assert "box" in check["detail"]
    assert "convex" not in check["detail"]
    assert check["ok"] is True, f"collision check failed: {check}"


# --------------------------------------------------------------------------
# AC-4 — no tools.godot_bin: exits non-zero naming it, writes nothing
# --------------------------------------------------------------------------

_NO_GODOT_CONFIGS = [
    ({}, "no-tools"),
    ({"tools": {}}, "no-key"),
    ({"tools": {"godot_bin": ""}}, "empty-value"),
    ({"tools": {"blender_bin": "blender.exe"}}, "sibling-only"),
]


@pytest.mark.parametrize(
    "content", [c for c, _ in _NO_GODOT_CONFIGS], ids=[i for _, i in _NO_GODOT_CONFIGS]
)
def test_main_without_godot_bin_exits_nonzero_and_writes_nothing(
    tmp_path, capsys, popen_spy, content
):
    """Covers: AC-4 — CLI refuses without tools.godot_bin.

    Given a config JSON without (or with an empty) tools.godot_bin,
    when main([glb, project, "--config", cfg]) runs,
    then it returns non-zero (documented: 2), stderr names tools.godot_bin,
    no process is launched, and the project's file listing is unchanged.
    """
    src = _require_fixture()
    glb = tmp_path / "src" / src.name
    glb.parent.mkdir()
    shutil.copy2(src, glb)
    project = _make_project(
        tmp_path / "project", {"collision": "convex", "animation_names": ["idle"]}
    )
    (tmp_path / "cfg").mkdir()
    cfg = _write_config(tmp_path / "cfg" / "schermness.config.json", content)
    before = _snapshot(project)

    stage = load_stage()
    capsys.readouterr()
    rc = stage.main([str(glb), str(project), "--config", str(cfg)])
    err = capsys.readouterr().err

    assert rc != 0
    assert rc == 2, f"documented refusal exit code is 2, got {rc}"
    assert "tools.godot_bin" in err
    assert popen_spy.calls == [], f"a process launch was attempted: {popen_spy.calls}"
    assert _snapshot(project) == before, "the project directory was modified"


def test_import_glb_without_godot_bin_raises_config_error(tmp_path, popen_spy):
    """Covers: AC-4 — import_glb raises ConfigError naming tools.godot_bin.

    Given a config with tools but no godot_bin,
    when import_glb(..., config_path=cfg) is called,
    then it raises ConfigError (a RuntimeError) whose message contains
    'tools.godot_bin', launches nothing, and leaves the project unchanged.
    """
    src = _require_fixture()
    project = _make_project(tmp_path / "project", {"collision": "convex"})
    cfg = _write_config(tmp_path / "schermness.config.json", {"tools": {}})
    before = _snapshot(project)

    stage = load_stage()
    assert issubclass(stage.ConfigError, RuntimeError)
    with pytest.raises(stage.ConfigError) as excinfo:
        stage.import_glb(src, project, config_path=cfg)

    assert "tools.godot_bin" in str(excinfo.value)
    assert popen_spy.calls == []
    assert _snapshot(project) == before


# --------------------------------------------------------------------------
# AC-6 — wrong-typed / bad-valued inputs raise documented errors
# --------------------------------------------------------------------------

def test_load_rules_fills_defaults_for_minimal_rules(tmp_path):
    """Covers: AC-6 — control for the refusal tests below.

    Given an import_rules.json of {} (all keys optional),
    when load_rules(project) is called,
    then every documented key comes back with its default — so a refusal
    below is about the bad value, not a stage that refuses everything.
    """
    project = _make_project(tmp_path / "project", {})
    rules = load_stage().load_rules(project)
    assert rules["scale"] == pytest.approx(1.0)
    assert rules["scale_tolerance"] == pytest.approx(0.05)
    assert rules["collision"] == "none"
    assert rules["material_slots"] is None
    assert rules["animation_names"] == []
    assert rules["land_in"] == "res://imported/"
    assert isinstance(rules["source"], list) and rules["source"]


@pytest.mark.parametrize(
    "rules",
    [
        {"scale": "1.0"},
        {"scale": 0},
        {"scale": -1.0},
        {"scale_tolerance": "0.05"},
        {"collision": "sphere"},
        {"collision": None},
        {"material_slots": -1},
        {"material_slots": "1"},
        {"animation_names": "idle"},
        {"animation_names": [1, 2]},
        {"land_in": 5},
        {"no_such_key": True},
    ],
    ids=["scale-str", "scale-zero", "scale-neg", "tol-str", "collision-unknown",
         "collision-null", "slots-neg", "slots-str", "anims-str", "anims-ints",
         "land_in-int", "unknown-key"],
)
def test_load_rules_rejects_bad_values(tmp_path, rules):
    """Covers: AC-6 — a bad rule value raises RulesError (a ValueError).

    Given an import_rules.json with one wrong-typed / out-of-range value or
    an unknown key,
    when load_rules(project) is called,
    then it raises RulesError and returns no coerced rules.
    """
    project = _make_project(tmp_path / "project", rules)
    stage = load_stage()
    assert issubclass(stage.RulesError, ValueError)
    with pytest.raises(stage.RulesError):
        stage.load_rules(project)


def test_load_rules_missing_rules_file_raises(tmp_path):
    """Covers: AC-6 — a project without import_rules.json raises RulesError."""
    project = _make_project(tmp_path / "project", None)
    stage = load_stage()
    with pytest.raises(stage.RulesError):
        stage.load_rules(project)


@pytest.mark.parametrize(
    "bad", [None, 123, 4.5, ["a"], {"p": 1}], ids=["none", "int", "float", "list", "dict"]
)
def test_load_rules_wrong_typed_project_dir_raises(bad):
    """Covers: AC-6 — load_rules(project_dir=<not a path>) raises.

    When load_rules is called with None or a non-path value,
    then it raises TypeError or ValueError (RulesError is a ValueError).
    """
    stage = load_stage()
    with pytest.raises((TypeError, ValueError)):
        stage.load_rules(bad)


@pytest.mark.parametrize(
    "which,bad",
    [("glb", None), ("glb", 123), ("glb", ["x.glb"]),
     ("project", None), ("project", 123), ("project", {"p": 1})],
    ids=["glb-none", "glb-int", "glb-list", "project-none", "project-int", "project-dict"],
)
def test_import_glb_wrong_typed_args_raise_without_launching(tmp_path, popen_spy, which, bad):
    """Covers: AC-6 — import_glb with None / wrong-typed glb or project_dir.

    Given a valid project and GLB-shaped file for the other argument and the
    repo config,
    when import_glb is called with a None or non-path glb / project_dir,
    then it raises TypeError or ValueError and no Godot process is launched.
    """
    project = _make_project(tmp_path / "project", {"collision": "box"})
    glb = tmp_path / "x.glb"
    glb.write_bytes(b"glTF")
    args = {"glb": glb, "project": project}
    args[which] = bad
    stage = load_stage()
    with pytest.raises((TypeError, ValueError)):
        stage.import_glb(args["glb"], args["project"])
    assert popen_spy.calls == []


# --------------------------------------------------------------------------
# AC-7 — land_in is a file-path sink: traversal / null byte / absolute refused
# --------------------------------------------------------------------------

def test_load_rules_accepts_nested_res_land_in(tmp_path):
    """Covers: AC-7 — control: a legitimate nested res:// land_in loads.

    Given land_in 'res://assets/creatures/',
    when load_rules runs,
    then it is accepted and returned as a res:// folder naming assets/creatures.
    """
    project = _make_project(tmp_path / "project", {"land_in": "res://assets/creatures/"})
    land_in = load_stage().load_rules(project)["land_in"]
    assert land_in.startswith("res://")
    assert "assets/creatures" in land_in


_EVIL_LAND_IN = [
    "res://../outside/",
    "res://imported/../../outside/",
    "../outside/",
    "C:/Windows/Temp/",
    "/tmp/outside/",
    "res://imported\x00/evil/",
    "user://imported/",
]


@pytest.mark.parametrize(
    "land_in", _EVIL_LAND_IN,
    ids=["res-dotdot", "res-nested-dotdot", "bare-dotdot", "abs-windows",
         "abs-posix", "null-byte", "not-res"],
)
def test_load_rules_rejects_escaping_land_in(tmp_path, land_in):
    """Covers: AC-7 — land_in outside the project is a bad value.

    Given land_in containing '../', a null byte, an absolute path, or a
    non-res:// scheme,
    when load_rules runs,
    then it raises RulesError.
    """
    project = _make_project(tmp_path / "project", {"land_in": land_in})
    stage = load_stage()
    with pytest.raises(stage.RulesError):
        stage.load_rules(project)


def test_import_glb_with_escaping_land_in_touches_nothing(tmp_path, popen_spy):
    """Covers: AC-7 — a traversal land_in writes no file anywhere.

    Given a project whose land_in is 'res://../outside/' inside a sandbox dir,
    when import_glb runs (repo config),
    then it raises RulesError, launches no process, and neither the project
    nor its parent sandbox changes (no 'outside' folder appears). The GLB is
    the real fixture, so land_in is the only bad input.
    """
    glb = _require_fixture()
    sandbox = tmp_path / "sandbox"
    project = _make_project(sandbox / "project", {"land_in": "res://../outside/"})
    before = _snapshot(sandbox)

    stage = load_stage()
    with pytest.raises(stage.RulesError):
        stage.import_glb(glb, project)
    assert popen_spy.calls == []
    assert _snapshot(sandbox) == before
    assert not (sandbox / "outside").exists()


# --------------------------------------------------------------------------
# AC-8 — no hardcoded secrets in the implementation source (static scan)
# --------------------------------------------------------------------------

_CREDENTIAL_PATTERNS = [
    re.compile(r"BEGIN RSA PRIVATE KEY"),
    re.compile(r"BEGIN PRIVATE KEY"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]
_SECRET_ASSIGN = re.compile(
    r"""(?ix)\b(password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*['"]([^'"]+)['"]"""
)
_PLACEHOLDER_VALUES = {
    "", "x", "xxx", "xxxx", "changeme", "placeholder", "your_key_here",
    "todo", "none", "example", "dummy",
}


def test_implementation_has_no_hardcoded_secrets():
    """Covers: AC-8 — scan pipelines/godot_import.py for credential patterns.

    Given the implementation file behind the public surface,
    when it is read as text and scanned for private-key blocks, AWS access
    keys, and secret assignments to non-placeholder literals,
    then zero matches are found; fails red because the file is missing.
    """
    for path in _IMPL_FILES:
        assert path.is_file(), f"implementation file missing: {path}"
    for path in _IMPL_FILES:
        source = path.read_text(encoding="utf-8")
        for pat in _CREDENTIAL_PATTERNS:
            assert not pat.search(source), f"{path.name}: credential pattern {pat.pattern!r}"
        for match in _SECRET_ASSIGN.finditer(source):
            value = match.group(2).strip().lower()
            assert value in _PLACEHOLDER_VALUES, (
                f"{path.name}: secret-like literal assignment {match.group(0)!r}"
            )


# --------------------------------------------------------------------------
# AC-9 — surfaced errors leak no traceback / absolute path / env value
# --------------------------------------------------------------------------

_ABS_PATH = re.compile(r"(?:[A-Za-z]:[\\/])|(?:(?:^|[\s'\"(])/(?:home|Users|etc|root|var|tmp)/)")
_SENTINEL = "S3CRET_ENV_VALUE_should_not_leak"


def _assert_clean(message: str, tmp_path: Path) -> None:
    assert "Traceback (most recent call last)" not in message
    assert _SENTINEL not in message
    assert str(tmp_path) not in message
    assert not _ABS_PATH.search(message), f"absolute path in message: {message!r}"


def test_config_error_and_cli_refusal_leak_no_internals(tmp_path, capsys, popen_spy, monkeypatch):
    """Covers: AC-9 — the godot_bin refusal carries no internals.

    Given a config lacking tools.godot_bin and a sentinel env var,
    when import_glb raises ConfigError and main() refuses on stderr,
    then both messages name tools.godot_bin but contain no traceback text,
    no absolute filesystem path, and no env-var value.
    """
    monkeypatch.setenv("GODOT_IMPORT_TEST_SECRET", _SENTINEL)
    glb = _require_fixture()
    project = _make_project(tmp_path / "project", {"collision": "box"})
    cfg = _write_config(tmp_path / "schermness.config.json", {"tools": {}})
    stage = load_stage()

    with pytest.raises(stage.ConfigError) as excinfo:
        stage.import_glb(glb, project, config_path=cfg)
    message = str(excinfo.value)
    assert "tools.godot_bin" in message
    _assert_clean(message, tmp_path)

    capsys.readouterr()
    rc = stage.main([str(glb), str(project), "--config", str(cfg)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "tools.godot_bin" in err
    _assert_clean(err, tmp_path)


def test_rules_error_message_leaks_no_internals(tmp_path, monkeypatch):
    """Covers: AC-9 — a RulesError for a bad value carries no internals.

    Given import_rules.json with collision 'sphere' and a sentinel env var,
    when load_rules raises RulesError,
    then its message names the bad key or value but has no traceback text,
    no absolute path, and no env-var value.
    """
    monkeypatch.setenv("GODOT_IMPORT_TEST_SECRET", _SENTINEL)
    project = _make_project(tmp_path / "project", {"collision": "sphere"})
    stage = load_stage()
    with pytest.raises(stage.RulesError) as excinfo:
        stage.load_rules(project)
    message = str(excinfo.value)
    assert "collision" in message or "sphere" in message
    _assert_clean(message, tmp_path)


# --------------------------------------------------------------------------
# AC-10 — no dangerous constructs in the implementation source (static scan)
# --------------------------------------------------------------------------

_DANGEROUS_PATTERNS = [
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"\bpickle\.loads\s*\("),
    re.compile(r"\bos\.system\s*\("),
    re.compile(r"shell\s*=\s*True"),
]
_YAML_LOAD = re.compile(r"\byaml\.load\s*\(")


def test_implementation_has_no_dangerous_constructs():
    """Covers: AC-10 — scan pipelines/godot_import.py for dangerous constructs.

    Given the implementation file behind the public surface,
    when it is read as text and scanned for eval/exec/pickle.loads/os.system,
    shell=True, and yaml.load without SafeLoader,
    then zero matches are found; fails red because the file is missing.
    """
    for path in _IMPL_FILES:
        assert path.is_file(), f"implementation file missing: {path}"
    for path in _IMPL_FILES:
        source = path.read_text(encoding="utf-8")
        for pat in _DANGEROUS_PATTERNS:
            assert not pat.search(source), f"{path.name}: dangerous construct {pat.pattern!r}"
        for match in _YAML_LOAD.finditer(source):
            tail = source[match.start() : match.start() + 120]
            assert "SafeLoader" in tail, f"{path.name}: yaml.load without SafeLoader"
