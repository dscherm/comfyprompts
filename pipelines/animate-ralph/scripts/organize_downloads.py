"""
Organize downloaded animation references into the reference library.
Parses filenames and source folder structures to categorize animations.

Usage:
    python pipelines/animate-ralph/scripts/organize_downloads.py
"""

import os
import shutil
from pathlib import Path

DL_DIR = Path("C:/Users/scher/Downloads/animation references")
REF_DIR = Path("D:/Projects/comfyui-toolchain/pipelines/animate-ralph/references")

# Category classification by filename keywords
CATEGORY_KEYWORDS = {
    "locomotion": [
        "walk", "run", "jog", "sprint", "strafe", "crouch", "sneak",
        "movement", "tightrope", "stepping",
    ],
    "combat": [
        "fight", "punch", "kick", "sword", "combat", "attack", "block",
        "dodge", "knockout", "boxing", "martial", "rifle", "pistol",
        "gun", "shooting", "musket", "archery", "greatsword", "slash",
        "dying", "death", "explosion", "canon", "kamekame", "assassin",
        "weapon", "halo", "claws", "mutant",
    ],
    "idle": [
        "idle", "breathing", "standing", "sitting", "rise", "stepforward",
        "turn", "light_mixamo", "medium_mixamo", "regular_",
        "foottapping", "typing", "laptop", "computer", "clipboard",
    ],
    "gesture": [
        "wave", "clap", "point", "shrug", "nod", "fistpump", "celebrate",
        "victory", "laugh", "headtilt", "middlefinger", "shouldershimmy",
        "doubletake", "facepalm", "flirty", "burst", "ninja",
        "sitcomcamera", "sitcomintro", "talkinghead", "cellphone",
        "gossip", "host", "contestant", "witness", "lawyer", "judge",
        "shamwow", "comedian", "singer", "documentary", "chef", "juggling",
        "photo", "rescuing", "stomache",
    ],
    "emotion": [
        "happy", "angry", "taunt", "scared", "confident", "zombie",
        "transformation", "superhero", "flying", "landing", "takeoff",
        "lasereye", "telekenisis", "ironman", "hulk", "watchover",
        "hawkeye", "magic", "fireball", "energy", "shield", "wand",
        "drStrange", "forceLevitation", "magicSnap",
    ],
    "driving": [
        "drive", "steer", "brake", "seated", "vehicle", "sitting",
        "sitdown", "laptop", "sittingtalking", "carcrash", "leaning",
        "playingcards", "carosel",
    ],
}


def classify_animation(filename):
    """Classify an animation file into a category based on its name."""
    name_lower = filename.lower().replace("_", "").replace("-", "").replace(" ", "")

    # Check dancing separately (it's a gesture/emotion)
    if "danc" in name_lower or "robot" in name_lower or "twist" in name_lower or "sway" in name_lower:
        return "gesture"

    # Check sports
    if any(s in name_lower for s in ["baseball", "football", "soccer", "golf", "tennis", "sports"]):
        return "gesture"

    # Check music/performance
    if any(s in name_lower for s in ["drum", "guitar", "piano", "saxophone", "trumpet"]):
        return "gesture"

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower().replace("_", "") in name_lower:
                return category

    return "gesture"  # default bucket for misc animations


def organize_rancidmilk():
    """Organize RancidMilk CMU FBX files (2,548 animations)."""
    src = DL_DIR / "Animations_V1_01" / "Packed" / "Animations"
    if not src.exists():
        print("  RancidMilk not found, skipping")
        return 0

    print("\n=== RancidMilk CMU Animations (2,548 FBX) ===")
    print("  These are raw CMU mocap retargeted to a standard humanoid.")
    print("  Copying to mocap_raw/cmu_fbx/ (too many to classify individually)")

    dest = REF_DIR / "mocap_raw" / "cmu_fbx"
    dest.mkdir(parents=True, exist_ok=True)

    count = 0
    for fbx in src.rglob("*.fbx"):
        dst = dest / fbx.name
        if not dst.exists():
            shutil.copy2(fbx, dst)
            count += 1

    # Also copy the index file
    index = DL_DIR / "Animations_V1_01" / "Packed" / "cmu-mocap-index-text(obtained from cgspeed).txt"
    if index.exists():
        shutil.copy2(index, dest / "CMU_INDEX.txt")

    print(f"  Copied {count} FBX files to {dest}")
    return count


def organize_rokoko():
    """Organize Rokoko mocap FBX files -- use Mixamo-rigged versions."""
    # Prefer Mixamo-rigged versions (most compatible with our pipeline)
    src_new = DL_DIR / "Rokoko_Free_Mocap_FBX_263" / "Rokoko Studio (Mocap)"
    src_legacy = DL_DIR / "Rokoko_Free_Mocap_FBX_263" / "Rokoko Studio Legacy Mocap (older)"

    print("\n=== Rokoko Studio Mocap (Mixamo-rigged FBX) ===")

    count = 0

    # New Rokoko Studio files (organized by category)
    if src_new.exists():
        for fbx in src_new.rglob("*_mixamo.fbx"):
            category = classify_animation(fbx.stem)
            dest = REF_DIR / "humanoid" / category
            dest.mkdir(parents=True, exist_ok=True)
            dst_name = f"rokoko_{fbx.stem}.fbx"
            dst = dest / dst_name
            if not dst.exists():
                shutil.copy2(fbx, dst)
                count += 1
                print(f"  {category:12s} <- {fbx.stem}")

    # Legacy Rokoko files (HumanIK versions -- also useful)
    if src_legacy.exists():
        for fbx in src_legacy.rglob("*_HUMANIK_*.fbx"):
            category = classify_animation(fbx.stem)
            dest = REF_DIR / "humanoid" / category
            dest.mkdir(parents=True, exist_ok=True)
            # Shorten the name
            short_name = fbx.stem.split("_HUMANIK")[0].lower().replace(" ", "_")
            dst_name = f"rokoko_legacy_{short_name}.fbx"
            dst = dest / dst_name
            if not dst.exists():
                shutil.copy2(fbx, dst)
                count += 1

    print(f"  Organized {count} Rokoko FBX files")
    return count


def organize_quaternius_ual():
    """Organize Quaternius Universal Animation Library (already partially done)."""
    src = DL_DIR / "Universal Animation Library[Standard]" / "Universal Animation Library[Standard]"

    print("\n=== Quaternius Universal Animation Library ===")

    count = 0
    if not src.exists():
        print("  UAL not found, skipping")
        return 0

    # Copy the GLB for Godot/Unreal (contains all anims)
    glb = src / "Unreal-Godot" / "UAL1_Standard.glb"
    if glb.exists():
        dst = REF_DIR / "humanoid" / "quaternius_ual1_full.glb"
        if not dst.exists():
            shutil.copy2(glb, dst)
            count += 1
            print(f"  Copied UAL1 full GLB")

    # Copy Unity FBX
    fbx = src / "Unity" / "UAL1_Standard.fbx"
    if fbx.exists():
        dst = REF_DIR / "humanoid" / "quaternius_ual1_full.fbx"
        if not dst.exists():
            shutil.copy2(fbx, dst)
            count += 1
            print(f"  Copied UAL1 full FBX")

    print(f"  Organized {count} Quaternius UAL files")
    return count


def organize_mixamo_tools():
    """Copy Mixamo downloader tools for later use."""
    print("\n=== Mixamo Downloader Tools ===")

    for tool_dir in ["mixamo-downloader-main", "mixamo_anims_downloader-master"]:
        src = DL_DIR / tool_dir
        if src.exists():
            dst = REF_DIR.parent / "scripts" / tool_dir
            if not dst.exists():
                shutil.copytree(src, dst)
                print(f"  Copied {tool_dir} to scripts/")
            else:
                print(f"  {tool_dir} already exists in scripts/")

    return 0


def main():
    print("=" * 60)
    print("  ORGANIZING ANIMATION REFERENCES")
    print("=" * 60)

    total = 0

    total += organize_quaternius_ual()
    total += organize_rokoko()
    total += organize_rancidmilk()
    organize_mixamo_tools()

    print(f"\n{'=' * 60}")
    print(f"  Total files organized: {total}")
    print(f"{'=' * 60}")

    # Final scan
    print("\n--- FINAL LIBRARY STATUS ---")
    for category in ["humanoid/locomotion", "humanoid/combat", "humanoid/idle",
                      "humanoid/gesture", "humanoid/driving", "humanoid/emotion",
                      "humanoid/sex", "quadruped/locomotion",
                      "mocap_raw/cmu_bvh", "mocap_raw/cmu_fbx", "retarget_maps"]:
        cat_dir = REF_DIR / category
        if cat_dir.exists():
            files = list(cat_dir.iterdir())
            file_count = len([f for f in files if f.is_file()])
            status = "OK" if file_count > 0 else "EMPTY"
            print(f"  {category:30s}: {file_count:4d} files  [{status}]")
        else:
            print(f"  {category:30s}:    0 files  [EMPTY]")

    # Root humanoid
    root_files = list((REF_DIR / "humanoid").glob("*.glb")) + list((REF_DIR / "humanoid").glob("*.fbx"))
    print(f"  {'humanoid/ (root packs)':30s}: {len(root_files):4d} files")


if __name__ == "__main__":
    main()
