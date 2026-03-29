"""
Download reference rigged meshes for the autorig-ralph pipeline.

Downloads CC0 packs from Quaternius and organizes them by body type.
Mixamo and Sketchfab downloads require manual login -- instructions printed.

Usage:
    python pipelines/autorig-ralph/scripts/download_references.py [--all | --humanoid | --quadruped | --creature]
"""

import argparse
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PIPELINE_DIR / "references"

# Quaternius packs (CC0, direct download from Google Drive / itch.io)
# These URLs may change -- check quaternius.com if they break
QUATERNIUS_PACKS = {
    "universal-base-characters": {
        "url": "https://quaternius.itch.io/universal-base-characters",
        "body_type": "humanoid",
        "description": "6 humanoid base models (Superhero/Regular/Teen x Male/Female), humanoid rig",
        "manual": True,  # itch.io requires browser download
    },
    "universal-animation-library": {
        "url": "https://quaternius.itch.io/universal-animation-library",
        "body_type": "humanoid",
        "description": "120+ retargetable humanoid animations with reference rig",
        "manual": True,
    },
    "ultimate-animated-animals": {
        "url": "https://quaternius.com/packs/ultimateanimatedanimals.html",
        "body_type": "quadruped",
        "description": "12 quadrupeds (wolf, horse, fox, deer, etc.) with 12+ animations each",
        "manual": True,
    },
    "farm-animals": {
        "url": "https://quaternius.com/packs/farmanimal.html",
        "body_type": "quadruped",
        "description": "7 farm animals rigged + animated",
        "manual": True,
    },
    "animated-monster": {
        "url": "https://quaternius.com/packs/animatedmonster.html",
        "body_type": "creature",
        "description": "Dragon, skeleton, bat, slime -- creature reference",
        "manual": True,
    },
    "easy-enemy": {
        "url": "https://quaternius.com/packs/easyenemy.html",
        "body_type": "creature",
        "description": "Bee, wasp, snake, rat, spider, frog -- small creature/insect",
        "manual": True,
    },
    "animated-mech": {
        "url": "https://quaternius.com/packs/animatedmech.html",
        "body_type": "mech",
        "description": "Mechanical biped reference",
        "manual": True,
    },
    "rpg-characters": {
        "url": "https://quaternius.com/packs/rpgcharacter.html",
        "body_type": "humanoid",
        "description": "Wizard, knight, monk, ranger, assassin with armor/weapons (hard-surface ref)",
        "manual": True,
    },
    "animated-dinosaur": {
        "url": "https://quaternius.com/packs/animateddinosaur.html",
        "body_type": "creature",
        "description": "Animated dinosaurs -- large creature reference",
        "manual": True,
    },
}

SKETCHFAB_MODELS = {
    "human-basemesh-pair": {
        "url": "https://sketchfab.com/3d-models/human-models-set-malefemale-rigged-7311fcfdc03e4234900eeced42a1e669",
        "body_type": "humanoid",
        "description": "Male + Female rigged human basemesh (CC-BY)",
        "note": "Can also download via blender-mcp: search_sketchfab / download_sketchfab",
    },
    "humanoid-avatar": {
        "url": "https://sketchfab.com/3d-models/humanoid-avatar-with-rig-995558e2514644909c9037b0e7762855",
        "body_type": "humanoid",
        "description": "Generic humanoid avatar with rig",
    },
    "camel-quadruped": {
        "url": "https://sketchfab.com/3d-models/camel-download-the-original-glb-05a0854fb54d4e34a100016545cc69e5",
        "body_type": "quadruped",
        "description": "Rigged camel in GLB format",
    },
    "animal-basemesh-collection": {
        "url": "https://sketchfab.com/apatel/collections/dl-basemesh-animals-209b4e514f2b42cfae18d7bf03bf47d4",
        "body_type": "quadruped",
        "description": "Multiple animal basemeshes with rigs",
    },
}

MIXAMO_CHARACTERS = {
    "y-bot": {
        "url": "https://www.mixamo.com/#/?page=1&type=Character",
        "body_type": "humanoid",
        "description": "Industry-standard male humanoid skeleton (~65 bones, Mecanim-compatible)",
        "download_steps": [
            "1. Go to https://www.mixamo.com/",
            "2. Sign in with free Adobe account",
            "3. Click 'Characters' tab",
            "4. Select 'Y Bot'",
            "5. Click 'Download' -> Format: FBX Binary, Pose: T-Pose, With Skin",
            "6. Save to pipelines/autorig-ralph/references/humanoid/mixamo_ybot.fbx",
        ],
    },
    "x-bot": {
        "url": "https://www.mixamo.com/#/?page=1&type=Character",
        "body_type": "humanoid",
        "description": "Industry-standard female humanoid skeleton",
        "download_steps": [
            "Same as Y Bot but select 'X Bot'",
            "Save to pipelines/autorig-ralph/references/humanoid/mixamo_xbot.fbx",
        ],
    },
    "paladin": {
        "url": "https://www.mixamo.com/#/?page=1&type=Character",
        "body_type": "humanoid",
        "description": "Humanoid with heavy armor (hard-surface attachment reference)",
        "download_steps": [
            "Same as Y Bot but select 'Paladin J Nordstrom'",
            "Save to pipelines/autorig-ralph/references/humanoid/mixamo_paladin.fbx",
        ],
    },
}


def ensure_dirs():
    """Create reference directory structure."""
    for body_type in ["humanoid", "quadruped", "creature", "mech", "serpentine"]:
        (REFERENCES_DIR / body_type).mkdir(parents=True, exist_ok=True)
    print(f"Reference directories created at: {REFERENCES_DIR}")


def print_manual_downloads(body_type_filter: str | None = None):
    """Print instructions for all manual downloads."""

    print("\n" + "=" * 70)
    print("  REFERENCE MESH DOWNLOAD GUIDE")
    print("=" * 70)

    # --- Quaternius (CC0) ---
    print("\n--- QUATERNIUS (CC0 Public Domain) ---")
    print("All free, no account required. Download the FBX or GLTF version.\n")

    for name, pack in QUATERNIUS_PACKS.items():
        if body_type_filter and pack["body_type"] != body_type_filter:
            continue
        print(f"  [{pack['body_type'].upper()}] {name}")
        print(f"    {pack['description']}")
        print(f"    URL: {pack['url']}")
        dest = REFERENCES_DIR / pack["body_type"]
        print(f"    Save FBX/GLB files to: {dest}/")
        print()

    # --- Mixamo (Free Adobe Account) ---
    if not body_type_filter or body_type_filter == "humanoid":
        print("\n--- MIXAMO (Free Adobe Account Required) ---")
        print("Industry-standard humanoid skeleton. Download as FBX with T-Pose.\n")

        for name, char in MIXAMO_CHARACTERS.items():
            print(f"  [{char['body_type'].upper()}] {name}")
            print(f"    {char['description']}")
            for step in char["download_steps"]:
                print(f"    {step}")
            print()

    # --- Sketchfab (CC-BY / Free) ---
    print("\n--- SKETCHFAB (CC-BY, Free Download) ---")
    print("Download GLB via browser, or use blender-mcp search_sketchfab tool.\n")

    for name, model in SKETCHFAB_MODELS.items():
        if body_type_filter and model["body_type"] != body_type_filter:
            continue
        print(f"  [{model['body_type'].upper()}] {name}")
        print(f"    {model['description']}")
        print(f"    URL: {model['url']}")
        dest = REFERENCES_DIR / model["body_type"]
        print(f"    Save to: {dest}/")
        if "note" in model:
            print(f"    TIP: {model['note']}")
        print()

    # --- Rigify (Built-in) ---
    print("\n--- RIGIFY TEMPLATES (Already in Blender) ---")
    print("No download needed. Generate via blender-mcp execute_blender_code:\n")
    print("  # Human metarig (standard humanoid skeleton)")
    print("  bpy.ops.preferences.addon_enable(module='rigify')")
    print("  bpy.ops.object.armature_human_metarig_add()")
    print()
    print("  # Also available: cat, horse, shark, bird metarigs")
    print("  # via Rigify sample menu in Blender")

    print("\n" + "=" * 70)
    print("  PRIORITY ORDER:")
    print("  1. Quaternius Universal Base Characters (humanoid)")
    print("  2. Mixamo Y Bot + X Bot (humanoid skeleton standard)")
    print("  3. Quaternius Ultimate Animated Animals (quadruped)")
    print("  4. Quaternius Animated Monster Pack (creatures)")
    print("  5. Quaternius RPG Characters (hard-surface reference)")
    print("=" * 70)


def scan_references():
    """Scan what's already downloaded and report coverage."""
    print("\n--- CURRENT REFERENCE LIBRARY ---\n")
    total = 0
    for body_type in ["humanoid", "quadruped", "creature", "mech", "serpentine"]:
        bt_dir = REFERENCES_DIR / body_type
        if bt_dir.exists():
            files = list(bt_dir.glob("*.glb")) + list(bt_dir.glob("*.fbx")) + list(bt_dir.glob("*.gltf"))
            count = len(files)
            total += count
            status = "OK" if count > 0 else "EMPTY"
            print(f"  {body_type:12s}: {count:3d} files  [{status}]")
            for f in files[:5]:
                print(f"    - {f.name}")
            if count > 5:
                print(f"    ... and {count - 5} more")
        else:
            print(f"  {body_type:12s}:   0 files  [MISSING]")

    print(f"\n  Total reference meshes: {total}")
    if total == 0:
        print("  Run this script with no args to see download instructions.")
    return total


def main():
    parser = argparse.ArgumentParser(description="Download reference meshes for autorig-ralph")
    parser.add_argument("--all", action="store_true", help="Show all download instructions")
    parser.add_argument("--humanoid", action="store_true", help="Show humanoid downloads only")
    parser.add_argument("--quadruped", action="store_true", help="Show quadruped downloads only")
    parser.add_argument("--creature", action="store_true", help="Show creature downloads only")
    parser.add_argument("--scan", action="store_true", help="Scan existing reference library")
    args = parser.parse_args()

    ensure_dirs()

    if args.scan:
        scan_references()
        return

    body_filter = None
    if args.humanoid:
        body_filter = "humanoid"
    elif args.quadruped:
        body_filter = "quadruped"
    elif args.creature:
        body_filter = "creature"

    print_manual_downloads(body_filter)
    print()
    scan_references()


if __name__ == "__main__":
    main()
