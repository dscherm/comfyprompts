"""Godot import stage: land a GLB in a Godot project under that project's import
contract and check the result.

    python pipelines/godot_import.py <asset.glb> <godot_project_dir> [--kit KIT] [--config CFG]

The contract is `<project>/import_rules.json` (see import_rules.schema.json),
merged with `<kit>/import_overrides.json` when the kit has one (the kit wins
key by key). The stage

1. copies the GLB under the rules' `land_in` folder, with a `.import` file that
   sets Godot's root scale to the rules' `scale`;
2. runs Godot headless with `--import`;
3. runs Godot windowed on godot_import_probe.gd, which wraps the imported scene
   with the collision the rules ask for, saves it as `<stem>.tscn` beside the
   GLB, reloads that saved scene, measures it, and screenshots it into
   `<project>/_shots/` (the projects' `--shot` convention);
4. checks scale, collision kind, animation names and material slots.

It returns, and `main` prints as JSON, a gate dict
`{ok, checks: [{name, ok, detail}], shot}`. The Godot binary is
`tools.godot_bin` in schermness.config.json; without it the stage refuses,
names that key, and writes nothing into the project.
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "schermness.config.json"
PROBE = Path(__file__).resolve().parent / "godot_import_probe.gd"
CONFIG_KEY = "tools.godot_bin"
COLLISION_KINDS = ("none", "box", "convex", "trimesh")
SHAPE_CLASS = {"box": "BoxShape3D", "convex": "ConvexPolygonShape3D",
               "trimesh": "ConcavePolygonShape3D"}
DEFAULTS = {"scale": 1.0, "scale_tolerance": 0.05, "collision": "none",
            "material_slots": None, "animation_names": [], "land_in": "res://imported/"}
IMPORT_TIMEOUT = 300
PROBE_TIMEOUT = 180


class ConfigError(RuntimeError):
    """The config lacks a value the stage needs (message names the key)."""


class RulesError(ValueError):
    """import_rules.json / import_overrides.json is missing or malformed."""


def godot_bin(config_path: str | Path | None = None) -> str:
    """`tools.godot_bin` from the config, or ConfigError naming the key."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"{CONFIG_KEY} is not set: config file {path.name} not found") from None
    value = (cfg.get("tools") or {}).get("godot_bin") if isinstance(cfg, dict) else None
    if not value:
        raise ConfigError(f"{CONFIG_KEY} is not set in {path.name}; add the Godot console "
                          f"executable under \"tools\": {{\"godot_bin\": ...}}")
    if not Path(value).is_file():
        raise ConfigError(f"{CONFIG_KEY} points at a file that does not exist "
                          f"({Path(value).name}); fix it in {path.name}")
    return str(value)


def _read_json(path: Path, what: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RulesError(f"{what} {path.name} is not valid JSON: {e}") from None
    if not isinstance(data, dict):
        raise RulesError(f"{what} {path.name} must be a JSON object")
    return data


def _validate(rules: dict) -> dict:
    unknown = sorted(set(rules) - set(DEFAULTS))
    if unknown:
        raise RulesError(f"unknown import rule key(s): {', '.join(unknown)}")
    for key in ("scale", "scale_tolerance"):
        v = rules[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
            raise RulesError(f"'{key}' must be a positive number, got {v!r}")
    if rules["collision"] not in COLLISION_KINDS:
        raise RulesError(f"'collision' must be one of {', '.join(COLLISION_KINDS)}, "
                         f"got {rules['collision']!r}")
    slots = rules["material_slots"]
    if slots is not None and (isinstance(slots, bool) or not isinstance(slots, int) or slots < 0):
        raise RulesError(f"'material_slots' must be a non-negative integer or null, got {slots!r}")
    names = rules["animation_names"]
    if not isinstance(names, list) or not all(isinstance(n, str) and n for n in names):
        raise RulesError("'animation_names' must be a list of non-empty strings")
    land = rules["land_in"]
    if (not isinstance(land, str) or not land.startswith("res://")
            or ".." in Path(land[6:]).parts or "\\" in land or "\x00" in land):
        raise RulesError(f"'land_in' must be a res:// folder inside the project, got {land!r}")
    return rules


def _kit_dir(project: Path, kit: str | Path) -> Path:
    k = Path(kit)
    for cand in (k, project / k, REPO_ROOT / "products" / k):
        if cand.is_dir():
            return cand
    raise RulesError(f"kit folder not found: {Path(kit).name}")


def load_rules(project_dir: str | Path, kit: str | Path | None = None) -> dict:
    """The effective import contract: defaults <- project import_rules.json <-
    kit import_overrides.json. `kit` is a kit folder (or its name under the
    project or products/); a kit without import_overrides.json changes nothing."""
    _need_path(project_dir, "project_dir")
    _need_path(kit, "kit", optional=True)
    project = Path(project_dir)
    rules_file = project / "import_rules.json"
    if not rules_file.is_file():
        raise RulesError(f"{project.name} has no import_rules.json")
    rules = {**DEFAULTS, **_read_json(rules_file, "import rules")}
    rules["source"] = ["import_rules.json"]
    if kit is not None:
        over = _kit_dir(project, kit) / "import_overrides.json"
        if over.is_file():
            rules.update(_read_json(over, "kit overrides"))
            rules["source"].append(f"{Path(kit).name}/import_overrides.json")
    source = rules.pop("source")
    _validate(rules)
    rules["source"] = source
    return rules


def glb_extent(path: str | Path) -> float:
    """Longest side of the GLB's mesh bounds, from the POSITION accessors'
    min/max (mesh space; node transforms are not applied)."""
    data = Path(path).read_bytes()
    if data[:4] != b"glTF":
        raise ValueError(f"not a GLB: {Path(path).name}")
    (jlen,) = struct.unpack_from("<I", data, 12)
    doc = json.loads(data[20:20 + jlen])
    lo, hi = [float("inf")] * 3, [float("-inf")] * 3
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            acc = doc["accessors"][prim["attributes"]["POSITION"]]
            if "min" in acc and "max" in acc:
                lo = [min(a, b) for a, b in zip(lo, acc["min"])]
                hi = [max(a, b) for a, b in zip(hi, acc["max"])]
    if lo[0] == float("inf"):
        return 0.0
    return max(h - low for h, low in zip(hi, lo))


def _need_path(value, what: str, optional: bool = False) -> None:
    if value is None and optional:
        return
    if isinstance(value, bytes) or not isinstance(value, (str, Path)):
        raise TypeError(f"{what} must be a str or Path, got {type(value).__name__}")
    if "\x00" in str(value):
        raise ValueError(f"{what} contains a NUL byte")


def _res_to_path(project: Path, res: str) -> Path:
    return project.joinpath(*Path(res[len("res://"):]).parts)


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def _run(cmd: list[str], log: Path, timeout: int) -> int:
    # Output goes to a file: a windowed Godot whose stdout is a pipe nobody
    # drains can hang.
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        try:
            return subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            fh.write(f"\nTIMEOUT after {timeout}s\n")
            return -1


def import_glb(glb: str | Path, project_dir: str | Path, kit: str | Path | None = None,
               config_path: str | Path | None = None) -> dict:
    """Run the import stage and return the gate dict {ok, checks, shot, ...}.
    Raises ConfigError (before touching the project) when tools.godot_bin is unset."""
    _need_path(glb, "glb")
    _need_path(project_dir, "project_dir")
    _need_path(kit, "kit", optional=True)
    _need_path(config_path, "config_path", optional=True)
    exe = godot_bin(config_path)
    glb, project = Path(glb), Path(project_dir).resolve()
    if not glb.is_file():
        raise FileNotFoundError(f"GLB not found: {glb.name}")
    if not (project / "project.godot").is_file():
        raise RulesError(f"{project.name} is not a Godot project (no project.godot)")
    rules = load_rules(project, kit)

    land_res = rules["land_in"].rstrip("/") + "/"
    dest_dir = _res_to_path(project, land_res)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / glb.name
    shutil.copyfile(glb, dest)
    (dest_dir / (glb.name + ".import")).write_text(
        '[remap]\n\nimporter="scene"\ntype="PackedScene"\n\n[params]\n\n'
        f'nodes/root_scale={float(rules["scale"])}\nnodes/apply_root_scale=true\n',
        encoding="utf-8")
    glb_res = land_res + glb.name
    scene_res = land_res + glb.stem + ".tscn"
    shot = project / "_shots" / f"{glb.stem}_import.png"
    if shot.exists():
        shot.unlink()

    checks: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="godot_import_") as tmp:
        tmpd = Path(tmp)
        rc = _run([exe, "--headless", "--path", str(project), "--import"],
                  tmpd / "import.log", IMPORT_TIMEOUT)
        report_path = tmpd / "report.json"
        _run([exe, "--path", str(project), "--resolution", "960x720", "--script", str(PROBE),
              "--", f"--glb={glb_res}", f"--collision={rules['collision']}",
              f"--out-scene={scene_res}", f"--report={report_path}", f"--shot={shot}",
              "--shot-delay=0.5"], tmpd / "probe.log", PROBE_TIMEOUT)
        report = (json.loads(report_path.read_text(encoding="utf-8"))
                  if report_path.is_file() else {})
        probe_log = (tmpd / "probe.log").read_text(encoding="utf-8", errors="replace")

    if not report.get("ok"):
        why = report.get("error") or f"probe wrote no report (import exit {rc})"
        tail = "\n".join(probe_log.strip().splitlines()[-8:])
        checks.append(_check("import", False, f"{why}\n{tail}".strip()))
        return {"ok": False, "checks": checks, "shot": None, "rules": rules, "glb": glb_res}
    checks.append(_check("import", True, f"{glb_res} imported and saved as {scene_res}"))

    native = glb_extent(glb)
    measured = max(report["extent"])
    ratio = measured / native if native else 0.0
    want, tol = float(rules["scale"]), float(rules["scale_tolerance"])
    checks.append(_check("scale", native > 0 and abs(ratio - want) <= tol * want,
                         f"scale {ratio:.4f} (want {want} ±{tol * 100:.0f}%; "
                         f"longest side {measured:.4f} in Godot vs {native:.4f} in the GLB)"))

    kind = rules["collision"]
    shapes = report["collision_shapes"]
    if kind == "none":
        ok, detail = not shapes, "collision: none" + (f" (found {shapes})" if shapes else "")
    else:
        want_cls = SHAPE_CLASS[kind]
        ok = bool(shapes) and all(s == want_cls for s in shapes)
        detail = f"collision: {kind} ({len(shapes)} x {want_cls})" if ok else \
            f"collision: want {kind} ({want_cls}), found {shapes or 'no CollisionShape3D'}"
    checks.append(_check("collision", ok, detail))

    have = report["animations"]
    for name in rules["animation_names"]:
        checks.append(_check(f"animation:{name}", name in have,
                             f"animation '{name}' " + ("present" if name in have else
                                                       f"missing (AnimationPlayer has {have})")))

    if rules["material_slots"] is not None:
        n = report["material_slots"]
        checks.append(_check("material_slots", n == rules["material_slots"],
                             f"{n} material slot(s), want {rules['material_slots']}"))

    has_shot = shot.is_file() and shot.stat().st_size > 0
    checks.append(_check("shot", has_shot, str(shot) if has_shot else
                         "no screenshot written (windowed Godot could not render?)"))
    return {"ok": all(c["ok"] for c in checks), "checks": checks,
            "shot": str(shot) if has_shot else None, "rules": rules, "glb": glb_res,
            "scene": scene_res}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="godot_import.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("glb")
    ap.add_argument("project")
    ap.add_argument("--kit")
    ap.add_argument("--config")
    a = ap.parse_args(argv)
    try:
        gate = import_glb(a.glb, a.project, a.kit, a.config)
    except (ConfigError, RulesError, FileNotFoundError, TypeError, ValueError) as e:
        print(f"godot_import: {e}", file=sys.stderr)
        return 2
    print(json.dumps(gate, indent=2))
    return 0 if gate["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
