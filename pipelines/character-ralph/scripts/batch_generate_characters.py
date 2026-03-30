"""
batch_generate_characters.py
----------------------------
Batch setup and status tracking for all 10 Soapbox Sabotage characters through
the character-ralph -> autorig-ralph pipeline.

This script writes pipeline-state.json files and prints commands.  It does NOT
directly invoke ComfyUI or Blender -- that is handled by ralph.sh reading
PROMPT.md in each iteration.

Usage
-----
  # List all characters
  python pipelines/character-ralph/scripts/batch_generate_characters.py --list

  # Write pipeline-state.json for a single character (no run)
  python pipelines/character-ralph/scripts/batch_generate_characters.py --setup player

  # Write pipeline-state.json for every character
  python pipelines/character-ralph/scripts/batch_generate_characters.py --setup-all

  # Print the ralph.sh command for one character
  python pipelines/character-ralph/scripts/batch_generate_characters.py --character player

  # Print ralph.sh commands to run all characters sequentially
  python pipelines/character-ralph/scripts/batch_generate_characters.py --all

  # Show completion status across all characters
  python pipelines/character-ralph/scripts/batch_generate_characters.py --status
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]  # comfyui-toolchain/
PIPELINE_ROOT = REPO_ROOT / "pipelines" / "character-ralph"
OUTPUT_ROOT = PIPELINE_ROOT / "output"

# ---------------------------------------------------------------------------
# T-pose prompt (proven extreme wide T-pose -- do not change)
# ---------------------------------------------------------------------------

TPOSE_PROMPT = (
    "standing in extreme exaggerated T-pose, arms fully stretched straight out "
    "horizontally at maximum extension from shoulders, palms facing down, fingers "
    "spread wide far away from body, wide power stance with legs spread apart, "
    "significant visible gap of empty space between arms and torso, hands absolutely "
    "nowhere near the legs or body"
)

# ---------------------------------------------------------------------------
# Character definitions
# ---------------------------------------------------------------------------

CHARACTERS = [
    {
        "id": "player",
        "name": "The Rookie",
        "style": "v1_otomo_crumb",
        "color": "orange",
        "description": (
            "Young male racer. Orange racing jacket with black stripes. Aviator goggles "
            "pushed up on forehead. Fingerless brown leather gloves. Dark cargo pants. "
            "Heavy boots. Short messy brown hair. Utility belt with tools. Confident stance."
        ),
    },
    {
        "id": "bones",
        "name": "The Reaper",
        "style": "v6_otomo_zap",
        "color": "bone white",
        "description": (
            "Tall skeletal figure. Bone-white face paint covering entire face. Black leather "
            "vest with skull patches. Torn black jeans. Combat boots with spikes. Mohawk of "
            "bleached white hair. Skull belt buckle. Bandaged forearms."
        ),
    },
    {
        "id": "crank",
        "name": "The Mechanic",
        "style": "v4_wasteland_zap",
        "color": "brass",
        "description": (
            "Stocky male mechanic. Brown oil-stained overalls. Large wrench tucked in belt. "
            "Leather tool apron. Grease stains on face and arms. Flat cap tilted to the side. "
            "Thick work boots. Rolled-up sleeves showing muscular forearms. Handlebar mustache."
        ),
    },
    {
        "id": "grit",
        "name": "The Desert Warrior",
        "style": "v9_crumb_fury",
        "color": "desert tan",
        "description": (
            "Muscular female warrior. Sand-colored desert wrap and hood. Tribal face tattoos "
            "across cheekbones and forehead. Leather armor pieces on shoulders and shins. "
            "Wrapped fists like a fighter. Scarred arms. Braided dark hair pulled back tight."
        ),
    },
    {
        "id": "pip",
        "name": "The Scavenger Kid",
        "style": "v6_otomo_zap",
        "color": "scavenger green",
        "description": (
            "Small thin teenager. Green scavenger vest covered in patches and pockets. "
            "Oversized backpack bulging with scrap parts. Nervously wide eyes. Patched cargo "
            "shorts. Mismatched shoes. Fingerless gloves too big for his hands. Messy red "
            "hair sticking up."
        ),
    },
    {
        "id": "punk_king",
        "name": "The Wasteland Queen",
        "style": "v8_kaneda_comix",
        "color": "royal purple",
        "description": (
            "Imposing female leader. Spiked leather crown worn tilted. Royal purple cape over "
            "a punk vest covered in chains and studs. Torn royal sash across the chest. Spiked "
            "shoulder pads. Combat boots with chrome buckles. Wild dark hair flowing past "
            "shoulders, partially shaved on one side."
        ),
    },
    {
        "id": "rust",
        "name": "The Ironclad",
        "style": "v8_kaneda_comix",
        "color": "rust red-brown",
        "description": (
            "Heavy-set male in rusted metal armor plates bolted directly together over his body. "
            "Welding mask pushed up revealing a scarred weathered face. Thick chain around neck "
            "like a collar. Metal gauntlets. Steel-toed boots. Short cropped hair."
        ),
    },
    {
        "id": "smog",
        "name": "The Chemist",
        "style": "v4_wasteland_zap",
        "color": "toxic green",
        "description": (
            "Lanky figure completely hidden behind a gas mask and hazmat-style coat. Dark green "
            "and grey torn overcoat. Chemical stains on everything. Rubber boots. Thick rubber "
            "gloves. Visible breathing tubes running from mask to canisters on back. Hood up always."
        ),
    },
    {
        "id": "sparks",
        "name": "The Livewire",
        "style": "v1_otomo_crumb",
        "color": "electric blue",
        "description": (
            "Energetic female daredevil. Electric blue jumpsuit with yellow lightning bolt patches "
            "sewn everywhere. Spiky short platinum hair with electric blue tips. Tech goggles with "
            "glowing yellow lenses pushed up on forehead. Wired jacket with exposed copper coils "
            "running along the arms."
        ),
    },
    {
        "id": "soup_box",
        "name": "The Mascot",
        "style": "v1_otomo_crumb",
        "color": "tomato red",
        "description": (
            "Friendly round character wearing a barrel/soapbox as a body with head and limbs "
            "poking out. The soapbox body has racing stripes and dents. Small crude arms and legs "
            "stick out of holes in the barrel. Cheerful round face poking out the top. Tiny "
            "racing helmet."
        ),
    },
]

# Map id -> character dict for fast lookup
CHAR_BY_ID: dict[str, dict] = {c["id"]: c for c in CHARACTERS}

# Style label -> human-readable description (used in negative prompts and logs)
STYLE_LABELS: dict[str, str] = {
    "v1_otomo_crumb": "otomo akira meets R Crumb underground comix, mechanical precision with organic weirdness, clean ink with obsessive detail, post-apocalyptic illustration",
    "v4_wasteland_zap": "wasteland punk illustration, heavy cross-hatching, EC Comics grime, rusted industrial textures, late 70s underground zine art",
    "v6_otomo_zap": "Otomo Katsuhiro angular precision meets Raw Magazine underground, tightly inked post-collapse characters, scavenged tech aesthetic",
    "v8_kaneda_comix": "Kaneda-era Akira energy with underground comix grotesque proportions, chrome and leather and decay, hyper-detailed linework",
    "v9_crumb_fury": "R Crumb fat-line expressionism fused with Mad Max visual fury, bulging muscle detail, tribal mark patterns, dirt and survival texture",
}

SHARED_NEGATIVE_PROMPT = (
    "blurry, low quality, deformed, ugly, photorealistic, 3D render, smooth digital art, "
    "anime, chibi, cute, Disney, Saturday morning cartoon, watermark, text, signature, frame, "
    "border, multiple characters, crowd, black and white, grayscale, monochrome, desaturated, "
    "pencil sketch"
)

# ---------------------------------------------------------------------------
# Pipeline state factory
# ---------------------------------------------------------------------------

CHARACTER_ORDER = [c["id"] for c in CHARACTERS]


def generate_pipeline_state(char: dict) -> dict:
    """Return the initial pipeline-state.json dict for a character."""
    return {
        "project_name": "soapbox-sabotage-characters",
        "character_name": char["name"],
        "character_id": char["id"],
        "description": char["description"],
        "style": "cartoon",
        "current_stage": 1,
        "stages": {
            "1-portrait":   {"status": "pending", "artifacts": [], "gate_passed": False},
            "2-fullbody":   {"status": "pending", "artifacts": [], "gate_passed": False},
            "3-multiview":  {"status": "pending", "artifacts": [], "gate_passed": False},
            "4-3d-convert": {"status": "pending", "artifacts": [], "gate_passed": False},
            "5-rig":        {"status": "pending", "artifacts": [], "gate_passed": False},
            "6-animate":    {"status": "pending", "artifacts": [], "gate_passed": False},
            "7-package":    {"status": "pending", "artifacts": [], "gate_passed": False},
        },
        "iteration": 0,
        "max_iterations": 30,
        "style_config": {
            "art_style": STYLE_LABELS.get(char["style"], char["style"]),
            "lora": "",
            "negative_prompt": SHARED_NEGATIVE_PROMPT,
        },
        "tpose_prompt": TPOSE_PROMPT,
        "batch_config": {
            "intake_source": "pipelines/art-to-rig-ralph/output/intake/characters-intake.json",
            "total_characters": len(CHARACTERS),
            "completed_characters": 0,
            "current_index": CHARACTER_ORDER.index(char["id"]),
            "character_order": CHARACTER_ORDER,
        },
        "rig_config": {
            "body_type": "humanoid",
            "skeleton_type": "unity_mecanim",
            "rig_tool": "unirig",
            "no_fingers": True,
            "no_face_bones": True,
        },
        "completed": False,
    }


# ---------------------------------------------------------------------------
# Output directory helpers
# ---------------------------------------------------------------------------

def char_output_dir(char_id: str) -> Path:
    return OUTPUT_ROOT / char_id


def state_path(char_id: str) -> Path:
    return char_output_dir(char_id) / "pipeline-state.json"


def setup_character(char: dict, force: bool = False) -> Path:
    """Write pipeline-state.json for a character. Returns the path written."""
    out_dir = char_output_dir(char["id"])
    out_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories matching PROMPT.md file conventions
    for sub in ("portrait", "fullbody", "multiview", "3d", "rigged", "animated", "final"):
        (out_dir / sub).mkdir(exist_ok=True)

    path = state_path(char["id"])
    if path.exists() and not force:
        print(f"  [skip] {char['id']}: pipeline-state.json already exists (use --force to overwrite)")
        return path

    state = generate_pipeline_state(char)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"  [ok]   {char['id']}: wrote {path.relative_to(REPO_ROOT)}")
    return path


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

STAGE_KEYS = [
    "1-portrait",
    "2-fullbody",
    "3-multiview",
    "4-3d-convert",
    "5-rig",
    "6-animate",
    "7-package",
]

# Stage display names for the status table
STAGE_SHORT = {
    "1-portrait":   "portrait",
    "2-fullbody":   "fullbody",
    "3-multiview":  "multiview",
    "4-3d-convert": "3d-convert",
    "5-rig":        "rig",
    "6-animate":    "animate",
    "7-package":    "package",
}


def load_state(char_id: str) -> dict | None:
    path = state_path(char_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def stage_symbol(stage_data: dict) -> str:
    """Return a single character representing stage completion state."""
    if stage_data.get("gate_passed"):
        return "v"   # passed
    status = stage_data.get("status", "pending")
    if status == "complete":
        return "~"   # complete but gate not passed (needs review)
    if status == "in_progress":
        return ">"   # currently running
    if status == "failed":
        return "x"   # failed
    return "."       # pending


def print_status() -> None:
    header_stages = "  ".join(f"{STAGE_SHORT[s]:>10}" for s in STAGE_KEYS)
    print(f"\n{'ID':<12}  {'Name':<22}  {header_stages}  {'Done':>4}")
    print("-" * 120)

    total_done = 0
    for char in CHARACTERS:
        state = load_state(char["id"])
        if state is None:
            stage_row = "  ".join(f"{'(no state)':>10}" if i == 0 else f"{'':>10}" for i, _ in enumerate(STAGE_KEYS))
            print(f"{char['id']:<12}  {char['name']:<22}  {stage_row}  {'no':>4}")
            continue

        stages = state.get("stages", {})
        symbols = []
        for sk in STAGE_KEYS:
            # Accept both exact key and legacy key variants that may exist in live state
            data = stages.get(sk, stages.get(sk.split("-", 1)[1], {}))
            symbols.append(stage_symbol(data))

        done = state.get("completed", False)
        if done:
            total_done += 1

        symbol_row = "  ".join(f"{s:>10}" for s in symbols)
        done_str = "YES" if done else f"s{state.get('current_stage', '?')}"
        itr = state.get("iteration", 0)
        print(f"{char['id']:<12}  {char['name']:<22}  {symbol_row}  {done_str:>4}  (iter {itr})")

    print(f"\nCompleted: {total_done}/{len(CHARACTERS)}")
    print("\nLegend:  v=gate passed  ~=complete/gate pending  >=in progress  x=failed  .=pending")


# ---------------------------------------------------------------------------
# Command printing helpers
# ---------------------------------------------------------------------------

def print_ralph_command(char: dict) -> None:
    """Print the ralph.sh command and env setup for one character."""
    out_dir = char_output_dir(char["id"])
    state_file = state_path(char["id"])
    rel_state = state_file.relative_to(REPO_ROOT)

    print(f"\n# --- {char['name']} ({char['id']}) ---")
    print(f"# State file: {rel_state}")
    print(f"# Output dir: {out_dir.relative_to(REPO_ROOT)}")
    print(f"#")
    print(f"# 1. Ensure state is written:")
    print(f"#    python pipelines/character-ralph/scripts/batch_generate_characters.py --setup {char['id']}")
    print(f"#")
    print(f"# 2. Copy state to default location for character-ralph:")
    print(f"#    cp {rel_state} pipelines/character-ralph/output/pipeline-state.json")
    print(f"#")
    print(f"# 3. Run the pipeline (repeat until CHARACTER COMPLETE):")
    print(f"#    bash ralph.sh --preset character")
    print(f"#")
    print(f"# 4. Copy completed state back:")
    print(f"#    cp pipelines/character-ralph/output/pipeline-state.json {rel_state}")


def print_all_commands() -> None:
    print("# Soapbox Sabotage -- full batch run sequence")
    print("# Run each block in order; wait for CHARACTER COMPLETE before the next.\n")
    for i, char in enumerate(CHARACTERS, 1):
        cid = char["id"]
        rel_state = state_path(cid).relative_to(REPO_ROOT)
        print(f"# ---- Character {i}/{len(CHARACTERS)}: {char['name']} ({cid}) ----")
        print(f"python pipelines/character-ralph/scripts/batch_generate_characters.py --setup {cid}")
        print(f"cp {rel_state} pipelines/character-ralph/output/pipeline-state.json")
        print(f"bash ralph.sh --preset character  # repeat until CHARACTER COMPLETE")
        print(f"cp pipelines/character-ralph/output/pipeline-state.json {rel_state}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch setup and status for Soapbox Sabotage character pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--list",
        action="store_true",
        help="List all 10 characters with IDs, names, and styles.",
    )
    group.add_argument(
        "--setup",
        metavar="ID",
        help="Write pipeline-state.json for a single character (no run).",
    )
    group.add_argument(
        "--setup-all",
        action="store_true",
        help="Write pipeline-state.json for all 10 characters.",
    )
    group.add_argument(
        "--character",
        metavar="ID",
        help="Print the ralph.sh command sequence for one character.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Print ralph.sh command sequence for all characters in order.",
    )
    group.add_argument(
        "--status",
        action="store_true",
        help="Show pipeline stage completion status for all characters.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --setup or --setup-all: overwrite existing pipeline-state.json.",
    )

    args = parser.parse_args()

    if args.list:
        print(f"\n{'#':<3}  {'ID':<12}  {'Name':<22}  {'Style':<20}  {'Color'}")
        print("-" * 80)
        for i, char in enumerate(CHARACTERS, 1):
            print(f"{i:<3}  {char['id']:<12}  {char['name']:<22}  {char['style']:<20}  {char['color']}")
        print()

    elif args.setup:
        cid = args.setup
        if cid not in CHAR_BY_ID:
            print(f"Error: unknown character id '{cid}'. Use --list to see valid IDs.", file=sys.stderr)
            sys.exit(1)
        print(f"\nSetting up character: {CHAR_BY_ID[cid]['name']} ({cid})")
        setup_character(CHAR_BY_ID[cid], force=args.force)
        print_ralph_command(CHAR_BY_ID[cid])

    elif args.setup_all:
        print(f"\nSetting up all {len(CHARACTERS)} characters...")
        for char in CHARACTERS:
            setup_character(char, force=args.force)
        print(f"\nAll pipeline-state.json files written to:")
        print(f"  {OUTPUT_ROOT.relative_to(REPO_ROOT)}/<character_id>/pipeline-state.json")
        print(f"\nNext step:")
        print(f"  python pipelines/character-ralph/scripts/batch_generate_characters.py --all")
        print(f"  to see the full run sequence.")

    elif args.character:
        cid = args.character
        if cid not in CHAR_BY_ID:
            print(f"Error: unknown character id '{cid}'. Use --list to see valid IDs.", file=sys.stderr)
            sys.exit(1)
        print_ralph_command(CHAR_BY_ID[cid])

    elif args.all:
        print_all_commands()

    elif args.status:
        print_status()


if __name__ == "__main__":
    main()
