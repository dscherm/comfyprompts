"""
Download animation reference files for the animate-ralph pipeline.

Prints download instructions and organizes files by category.
Most sources require browser download (Mixamo login, itch.io, etc).

Usage:
    python pipelines/animate-ralph/scripts/download_animation_refs.py [--scan]
"""

import argparse
import os
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REFERENCES_DIR = PIPELINE_DIR / "references"


def ensure_dirs():
    """Create reference directory structure."""
    dirs = [
        "humanoid/locomotion", "humanoid/combat", "humanoid/idle",
        "humanoid/gesture", "humanoid/driving", "humanoid/emotion", "humanoid/sex",
        "quadruped/locomotion", "mocap_raw/cmu_bvh", "retarget_maps",
    ]
    for d in dirs:
        (REFERENCES_DIR / d).mkdir(parents=True, exist_ok=True)


def print_download_guide():
    print("=" * 70)
    print("  ANIMATION REFERENCE DOWNLOAD GUIDE")
    print("=" * 70)

    print("""
--- PHASE 1: CORE LIBRARY (download these first) ---

[1] QUATERNIUS UNIVERSAL ANIMATION LIBRARY 2 (CC0, 130+ animations)
    URL: https://quaternius.itch.io/universal-animation-library-2
    Click "Download Now" (free). Save FBX/GLB files to:
      references/humanoid/locomotion/ (walk, run, strafe files)
      references/humanoid/combat/    (attack, block, combo files)
      references/humanoid/idle/      (idle, fidget files)
      references/humanoid/gesture/   (wave, celebrate files)

[2] RANCIDMILK CMU CONVERSION (Free, 2,000+ animations in GLB)
    URL: https://rancidmilk.itch.io/free-character-animations
    Click "Download Now". This is a HUGE pack -- organize into subfolders.
    Best: bulk copy all GLBs to references/humanoid/ subfolders by name.

[3] MIXAMO ESSENTIALS (~40 key animations, free Adobe account)
    URL: https://www.mixamo.com/
    Sign in, go to "Animations" tab. For each:
    - Search name, select, click Download
    - Format: FBX Binary, Skin: Without Skin, FPS: 30
    - Save to appropriate subfolder

    LOCOMOTION (references/humanoid/locomotion/):
      Walking, Running, Sprinting, Left Strafe Walking,
      Right Strafe Walking, Crouch Walking, Sneaking, Jogging

    COMBAT (references/humanoid/combat/):
      Cross Punch, Roundhouse Kick, Sword And Shield Slash,
      Standing React, Left Dodge, Hit Reaction,
      Dying Forward, Dying Backward

    IDLE (references/humanoid/idle/):
      Idle, Breathing Idle, Looking Around, Idle Fidget,
      Sitting Idle, Sitting Talking

    GESTURE (references/humanoid/gesture/):
      Waving, Victory, Clapping, Pointing, Shrug

    EMOTION (references/humanoid/emotion/):
      Taunting, Angry Gesture, Happy

    DRIVING (references/humanoid/driving/):
      Sitting Idle, Sitting Reaching Forward, Fist Pump, Head Nod Yes

--- PHASE 2: EXTENDED LIBRARY ---

[4] ROKOKO FREE MOTION LIBRARY (150 studio-quality animations)
    URL: https://www.rokoko.com/products/motion-library
    Requires free Rokoko Studio account. Export as FBX.

[5] CMU FULL DATASET AS FBX (2,548 motions)
    URL: https://huggingface.co/datasets/gbionics/cmu-fbx
    Large download. Save BVH/FBX to references/mocap_raw/

[6] MIXAMO BULK DOWNLOAD (remaining 2,400+ animations)
    Use: https://github.com/juanjo4martinez/mixamo-downloader
    Python GUI tool that automates downloading from Mixamo.

--- PHASE 3: RETARGETING TOOLS ---

[7] KEEMAP BLENDER ADDON (free, saves reusable bone mappings)
    URL: https://github.com/nkeeline/Keemap-Blender-Rig-ReTargeting-Addon
    Install in Blender: Edit > Preferences > Add-ons > Install from Disk

[8] RETARGET BLENDER EXTENSION (Blender 5+ compatible)
    URL: https://extensions.blender.org/add-ons/retarget/
    Has built-in presets for Mixamo, Unreal, VRoid, MMD

--- OTHER USEFUL LINKS ---

    Mixamo Downloader GUI:
      https://github.com/juanjo4martinez/mixamo-downloader
    Mixamo API Downloader:
      https://github.com/gnuton/mixamo_anims_downloader
    CMU BVH (cgspeed):
      https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture
    Rokoko Blender Plugin:
      https://github.com/Rokoko/rokoko-studio-live-blender
    Blender Animation Retargeting:
      https://github.com/Mwni/blender-animation-retargeting
    ReNim (node-based retargeting):
      https://github.com/anasrar/ReNim
""")


def scan_references():
    """Scan what's already downloaded."""
    print("\n--- CURRENT ANIMATION REFERENCE LIBRARY ---\n")
    total = 0
    for category in ["humanoid/locomotion", "humanoid/combat", "humanoid/idle",
                      "humanoid/gesture", "humanoid/driving", "humanoid/emotion",
                      "quadruped/locomotion", "mocap_raw/cmu_bvh", "retarget_maps"]:
        cat_dir = REFERENCES_DIR / category
        if cat_dir.exists():
            files = list(cat_dir.glob("*.glb")) + list(cat_dir.glob("*.fbx")) + \
                    list(cat_dir.glob("*.bvh")) + list(cat_dir.glob("*.json"))
            count = len(files)
            total += count
            status = "OK" if count > 0 else "EMPTY"
            print(f"  {category:30s}: {count:3d} files  [{status}]")
            for f in sorted(files)[:3]:
                print(f"    - {f.name}")
            if count > 3:
                print(f"    ... and {count - 3} more")
        else:
            print(f"  {category:30s}:   0 files  [MISSING]")

    # Also check root humanoid dir for bulk files
    root_files = list((REFERENCES_DIR / "humanoid").glob("*.glb")) + \
                 list((REFERENCES_DIR / "humanoid").glob("*.fbx"))
    if root_files:
        total += len(root_files)
        print(f"  {'humanoid/ (root)':30s}: {len(root_files):3d} files  [OK]")
        for f in sorted(root_files)[:3]:
            print(f"    - {f.name}")

    print(f"\n  Total animation references: {total}")
    if total < 10:
        print("  Run without --scan for download instructions.")


def main():
    parser = argparse.ArgumentParser(description="Animation reference download guide")
    parser.add_argument("--scan", action="store_true", help="Scan existing library")
    args = parser.parse_args()

    ensure_dirs()

    if args.scan:
        scan_references()
    else:
        print_download_guide()
        scan_references()


if __name__ == "__main__":
    main()
