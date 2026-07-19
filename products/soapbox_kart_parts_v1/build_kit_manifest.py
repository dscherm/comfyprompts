#!/usr/bin/env python3
"""build_kit_manifest.py — assemble the kart-kit manifest from the socket contract + the
curated part list.

Reads:
  kit_sockets.json                                  (the attachment contract — SPEC §4)
  E:/ai-training/flux-output/soapbox_kart_parts/pipeline/keepers.txt   (curated corpus)

Writes:
  kit.json                    always — the manifest: every swappable part, its plug socket,
                              the sockets it exposes, and its source concept image(s). This
                              is the compatibility graph a loader/assembler consumes.
  meta/<id>.meta.json         only with --emit-meta — per-part sidecars (SPEC §4.2). Mesh-
                              derived fields (bbox, pivot, model paths) are left null: they
                              get filled at P4 from the actual image-to-3D meshes. Emitting
                              them earlier would bake in guessed geometry.

Whole-kart hero shots (kart_*) are NOT parts — they are assembled marketing references, so
they are excluded from the swappable-parts manifest.

Stdlib only. Idempotent.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "kit_sockets.json"
# The rescued curated dataset IS the keeper set (keepers.txt lived on the wiped E: drive).
RESCUE = Path("D:/Projects/comfyui-toolchain/_RESCUE_soapbox_kart_dataset")

# Hand-authored low-poly parts (lp_parts.py) that join the same modular kit.
# id -> (category, plug socket_type). Geometry lives in lowpoly/<id>.glb.
LOWPOLY = {
    "lp_exhaust_stacks": ("tail", "rear_mount"),
    "lp_rollcage":       ("roof", "roof_mount"),
    "lp_spikes":         ("weapon", "wheel_mount"),
    "lp_armor_plate":    ("side", "side_mount"),
    "lp_ram_bar":        ("weapon", "nose_mount"),
    "lp_tesla":          ("weapon", "roof_mount"),
    "lp_nailgun":        ("weapon", "nose_mount"),
    "lp_number_plate":   ("side", "side_mount"),
    "lp_wheel":          ("wheel", "wheel_mount"),
    "lp_grille":         ("nose", "nose_mount"),
    "lp_fueltank":       ("side", "decor_mount"),
    "lp_chassis_rail":   ("chassis", "root"),
    "lp_wheel_slick":    ("wheel", "wheel_mount"),
    "lp_wheel_disc":     ("wheel", "wheel_mount"),
    "lp_tail_fin":       ("tail", "rear_mount"),
    "lp_roof_rack":      ("roof", "roof_mount"),
    "lp_wreckingball":   ("weapon", "rear_mount"),
    "lp_nose_plow":      ("nose", "nose_mount"),
    "lp_chainsaw":       ("weapon", "side_mount"),
    "lp_smoke":          ("weapon", "rear_mount"),
    "lp_oilslick":       ("weapon", "rear_mount"),
    "lp_thunderstick":   ("weapon", "roof_mount"),
    # lp_catapult, lp_molotov, lp_steering_wheel -> sourced from TRELLIS instead (user call)
    # lumber & other-material parts
    "lp_wood_door":      ("side", "side_mount"),
    "lp_wood_roof":      ("roof", "roof_mount"),
    "lp_wood_barrel":    ("side", "decor_mount"),
    "lp_tire_bumper":    ("nose", "nose_mount"),
    "lp_tarp_roof":      ("roof", "roof_mount"),
    "lp_chassis_tub":    ("chassis", "root"),
    "lp_chassis_crate":  ("chassis", "root"),
    "lp_chassis_plank":  ("chassis", "root"),
    "lp_roof_hardtop":   ("roof", "roof_mount"),
    "lp_roof_canopy":    ("roof", "roof_mount"),
    "lp_roof_umbrella":  ("roof", "roof_mount"),
    "lp_sidepipes":      ("side", "side_mount"),
    "lp_tail_stacks":    ("tail", "rear_mount"),
    "lp_wheel_spoked":   ("wheel", "wheel_mount"),
    "lp_wheel_monster":  ("wheel", "wheel_mount"),
    "lp_wheel_wagon":    ("wheel", "wheel_mount"),
}


def part_family(stem: str) -> str:
    """chassis__rail__s42 -> chassis__rail ; kart_player__s19 -> kart_player."""
    return stem.rsplit("__s", 1)[0]


def part_id(family: str) -> str:
    """Manifest id: weapon__wpn_ram -> wpn_ram ; wheel__fat_slick -> wheel_fat_slick."""
    if family.startswith("weapon__"):
        return family[len("weapon__"):]
    return family.replace("__", "_")


def display_name(pid: str) -> str:
    return " ".join(w.capitalize() for w in pid.replace("wpn_", "").split("_")) + \
        (" (weapon)" if pid.startswith("wpn_") else "")


def load_families() -> dict[str, list[str]]:
    """family -> sorted list of source concept filenames (its kept seeds)."""
    fams: dict[str, list[str]] = defaultdict(list)
    for img in RESCUE.glob("*.png"):
        fams[part_family(img.stem)].append(img.name)
    return {k: sorted(v) for k, v in sorted(fams.items())}


def build(contract: dict, families: dict[str, list[str]]) -> tuple[dict, list[dict]]:
    cat_plug = contract["category_plugs"]
    weapon_mounts = contract["weapon_mounts"]
    mirror = contract["category_mirror_x_ok"]
    exposed = contract["exposed_sockets"]

    parts, metas = [], []
    for family, sources in families.items():
        if family.startswith("kart_"):
            continue  # whole-kart hero shot, not a swappable part
        if family.startswith("weapon__"):
            category, socket = "weapon", weapon_mounts.get(part_id(family))
            if socket is None:
                print(f"  WARN no weapon mount for {family}")
                continue
        else:
            category = family.split("__", 1)[0]
            if category == "chassis":
                socket = "root"
            else:
                socket = cat_plug.get(category)
            if socket is None:
                print(f"  WARN no plug socket for category {category} ({family})")
                continue

        pid = part_id(family)
        # sockets this part exposes: chassis exposes the whole chassis layout; seat/roof_rack
        # expose their secondaries; everything else exposes nothing.
        # Family-specific exposure wins (only roof__rack exposes a roof_mount); otherwise
        # fall back to a category-level rule (every seat exposes a steering_mount).
        if category == "chassis":
            exposes = contract["chassis_sockets"]
        else:
            exposes = exposed.get(family, exposed.get(category, []))

        parts.append({
            "id": pid, "category": category, "socket_type": socket,
            "exposes": [s["name"] for s in exposes], "source_2d": sources,
        })
        metas.append({
            "id": pid, "category": category, "display_name": display_name(pid),
            "plug": {"socket_type": socket, "pivot": None, "up": [0, 1, 0],
                     "forward": [0, 0, 1], "mirror_x_ok": mirror.get(category, False)},
            "sockets": exposes,
            "theme": "universal", "signature_color": None, "scale_unit": "kart",
            "bbox": None, "source_2d": sources[0], "source_candidates": sources,
            "models": {"glb": None, "obj": None, "fbx": None, "gltf": None},
            "gen": {"lora": "soapbox_kart", "strength": 1.0},
        })

    # parts regenerated via Tripo Studio (cartoon, textured, decimated to game-ready) —
    # supersede the grey TRELLIS geometry. Auto-detected: any part whose textured GLB is
    # present in models_lowpoly/<id>.glb is a shipped Tripo part. Drop a new decimated GLB
    # there and it registers on the next build — no edit here.
    models_dir = HERE / "models_lowpoly"
    for p in parts:
        if (models_dir / f"{p['id']}.glb").exists():
            p["source"] = "tripo"
            p["textured"] = True
            p["model"] = f"models_lowpoly/{p['id']}.glb"

    # inject the hand-authored low-poly parts (source = lowpoly, not TRELLIS)
    chassis_socket_names = [s["name"] for s in contract["chassis_sockets"]]
    for lid, (cat, socket) in LOWPOLY.items():
        exposes = chassis_socket_names if socket == "root" else []
        parts.append({
            "id": lid, "category": cat, "socket_type": socket,
            "exposes": exposes, "source": "lowpoly", "model": f"lowpoly/{lid}.glb",
        })

    manifest = {
        "kit": "soapbox_kart_parts_v1",
        "version": "1.0",
        "trigger": "soapbox_kart",
        "orientation": contract["orientation"],
        "socket_types": contract["socket_types"],
        "chassis_sockets": contract["chassis_sockets"],
        "parts": parts,
        "counts": {
            "total": len(parts),
            "by_category": dict(sorted(
                ((c, sum(1 for p in parts if p["category"] == c))
                 for c in {p["category"] for p in parts}))),
        },
    }
    return manifest, metas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-meta", action="store_true",
                    help="also write per-part meta/<id>.meta.json stubs (P4).")
    args = ap.parse_args()

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    families = load_families()
    manifest, metas = build(contract, families)

    (HERE / "kit.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote kit.json — {manifest['counts']['total']} parts "
          f"{manifest['counts']['by_category']}")

    if args.emit_meta:
        mdir = HERE / "meta"
        mdir.mkdir(exist_ok=True)
        for m in metas:
            (mdir / f"{m['id']}.meta.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {len(metas)} per-part stubs -> meta/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
