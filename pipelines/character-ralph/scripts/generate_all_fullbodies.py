"""
Generate exaggerated T-pose fullbody images for all Soapbox Sabotage characters.

Submits jobs directly to ComfyUI's REST API using the berserkr_chargen_fullbody workflow.
Each character gets a 768x768 wide T-pose image suitable for Hunyuan3D conversion.

Usage:
    python pipelines/character-ralph/scripts/generate_all_fullbodies.py [--character ID] [--all]
"""

import json
import os
import random
import sys
import time
import urllib.request
from pathlib import Path

COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://localhost:8188")
REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / "workflows" / "mcp" / "berserkr_chargen_fullbody.json"
OUTPUT_ROOT = REPO_ROOT / "pipelines" / "character-ralph" / "output"

TPOSE_PROMPT = (
    "standing in extreme exaggerated T-pose, arms fully stretched straight out "
    "horizontally at maximum extension from shoulders, palms facing down, fingers "
    "spread wide far away from body, wide power stance with legs spread apart, "
    "significant visible gap of empty space between arms and torso, hands absolutely "
    "nowhere near the legs or body"
)

STYLE_LABELS = {
    "v1_otomo_crumb": (
        "Katsuhiro Otomo meets R. Crumb underground comix, exaggerated grotesque proportions, "
        "huge hands and feet, oversized heads, obsessively detailed mechanical parts, wobbly organic "
        "linework mixed with precise technical cross-hatching, ugly-beautiful character design, "
        "underground zine print quality, NOT realistic NOT pretty NOT clean NOT digital"
    ),
    "v4_wasteland_zap": (
        "1970s underground comix wasteland punk, Vaughn Bode meets Tank Girl, exaggerated squat "
        "chunky proportions, impossibly thick limbs, heavy black outlines, EC Comics horror grime, "
        "scratchy cross-hatching texture everywhere, rusted corroded industrial decay, yellowed "
        "newsprint zine aesthetic, NOT realistic NOT smooth NOT digital NOT clean"
    ),
    "v6_otomo_zap": (
        "Katsuhiro Otomo AKIRA-era angular precision, sharp geometric anatomy with exaggerated "
        "proportions, elongated limbs, angular jaw and cheekbones, meets Raw Magazine underground "
        "comix grit, tightly inked with visible brushstroke texture, post-apocalyptic scavenger "
        "aesthetic, NOT realistic NOT smooth NOT pretty NOT 3d render"
    ),
    "v8_kaneda_comix": (
        "AKIRA Kaneda motorcycle gang energy, exaggerated heroic proportions with massive shoulders "
        "and narrow waist, chrome and leather fetish detail, underground comix grotesque facial "
        "features with heavy brow and angular jaw, Robert Crumb body exaggeration meets Otomo "
        "mechanical precision, punk decay and industrial grime, NOT realistic NOT pretty NOT Disney"
    ),
    "v9_crumb_fury": (
        "Robert Crumb fat-line expressionism at maximum exaggeration, impossibly bulging muscles and "
        "thick limbs, giant hands and feet, sweaty glistening skin texture, obsessive cross-hatching "
        "on every surface, Mad Max tribal fury, crude powerful ugly-beautiful anatomy, underground "
        "comix printing with visible ink bleed, NOT realistic NOT clean NOT digital NOT smooth"
    ),
}

CHARACTERS = [
    {"id": "bones", "name": "The Reaper", "style": "v6_otomo_zap", "color": "bone white",
     "description": (
         "Impossibly tall gaunt skeletal figure with elongated limbs. Bone-white face paint covering "
         "entire angular face with sunken cheeks. Black leather vest with crudely sewn skull patches. "
         "Torn black jeans hanging off bony frame. Combat boots with oversized spikes. Towering mohawk "
         "of bleached white hair. Massive skull belt buckle. Bandaged forearms with veins showing through."
     )},
    {"id": "crank", "name": "The Mechanic", "style": "v4_wasteland_zap", "color": "brass",
     "description": (
         "Squat barrel-chested mechanic built like a fire hydrant, absurdly thick forearms. Brown "
         "oil-stained overalls stretched tight over massive gut. Wrench tucked in belt at hip not in "
         "hands, both hands open and empty with palms facing down. Leather tool apron. Grease smeared "
         "across broad flat face. Tiny flat cap perched on huge round head. Enormous thick work boots. "
         "Rolled-up sleeves showing forearms thicker than his head. Ridiculous handlebar mustache "
         "curling past his ears."
     )},
    {"id": "grit", "name": "The Desert Warrior", "style": "v9_crumb_fury", "color": "desert tan",
     "description": (
         "Massively muscular female warrior with impossibly thick arms and legs, Crumb-style exaggerated "
         "powerful build. Sand-colored desert wrap and hood framing fierce angular face. Bold tribal "
         "tattoos across cheekbones and forehead. Oversized leather armor plates on huge shoulders and "
         "thick shins. Wrapped fists like boxing gloves on giant hands. Battle-scarred bulging arms. "
         "Braided dark hair pulled back tight."
     )},
    {"id": "pip", "name": "The Scavenger Kid", "style": "v6_otomo_zap", "color": "scavenger green",
     "description": (
         "Scrawny tiny teenager facing directly toward camera front view, huge nervous eyes and "
         "oversized round head on a stick-thin body. Green scavenger vest covered in patches and "
         "stuffed pockets. Small backpack worn tight flat against back not overlapping arms. Patched "
         "cargo shorts on stick-thin legs. Mismatched oversized shoes. Both hands open and empty with "
         "palms facing down fingers spread wide. Fingerless gloves comically too big for his tiny "
         "hands. Wild messy red hair sticking up in every direction."
     )},
    {"id": "punk_king", "name": "The Wasteland Queen", "style": "v8_kaneda_comix", "color": "royal purple",
     "description": (
         "T-POSE CHARACTER REFERENCE SHEET, arms stretched fully horizontal straight out from "
         "shoulders palms down. Imposing towering female leader with exaggerated heroic proportions, "
         "massive shoulders tapering to narrow waist, facing directly toward camera front view. "
         "Spiked leather crown worn tilted on huge angular head. Leopard print fur collar around neck "
         "only. Punk vest covered in chains and studs showing bare muscular arms. Small spiked studs "
         "on shoulders. NO CAPE NO CLOAK NO DRAPING FABRIC NO FLOWING CLOTH NO LARGE SHOULDER PADS. "
         "Combat boots with chrome buckles up to the knee. Short spiky dark hair, half shaved showing "
         "tattoo on scalp."
     )},
    {"id": "rust", "name": "The Ironclad", "style": "v8_kaneda_comix", "color": "rust red-brown",
     "description": (
         "Massive heavy-set male built like a tank, exaggerated wide body. Dark rust-brown and "
         "red-brown rusted corroded metal armor plates bolted directly onto his body, oxidized patina "
         "color not orange not clean. Armor tight to body not extending past arms. Welding mask pushed "
         "up revealing scarred weathered face with heavy brow. Thick chain around tree-trunk neck. "
         "Oversized dark metal gauntlets on huge fists with both hands open and empty palms down. "
         "Steel-toed boots like cinder blocks. Short cropped hair on a tiny head atop enormous body."
     )},
    {"id": "smog", "name": "The Chemist", "style": "v4_wasteland_zap", "color": "toxic green",
     "description": (
         "Absurdly lanky stick-figure proportions like a praying mantis, impossibly elongated thin "
         "spindly limbs, comically small torso. Grotesquely oversized gas mask with enormous bulging "
         "round bug-eye lenses three times too big for the tiny head. Dark green and grey torn fitted "
         "coat tight to skeletal thin body. Neon toxic chemical stains glowing on everything. "
         "Ridiculously oversized rubber boots on stick-thin legs like stilts. Thick rubber gloves on "
         "impossibly long spindly arms like spider legs. Tiny canisters strapped flat against back. "
         "Hood pulled up over grotesque gas mask. Underground comix grotesque insect-like proportions."
     )},
    {"id": "sparks", "name": "The Livewire", "style": "v1_otomo_crumb", "color": "electric blue",
     "description": (
         "Wiry energetic female daredevil with exaggerated angular Otomo-style proportions. Electric "
         "blue jumpsuit with crudely sewn yellow lightning bolt patches everywhere. Spiky short platinum "
         "hair with electric blue tips standing straight up. Oversized tech goggles with glowing yellow "
         "lenses pushed up on forehead. Fitted jacket with exposed copper coils running along the arms, "
         "jacket tight to body. Giant boots with visible wiring."
     )},
    {"id": "soup_box", "name": "The Mascot", "style": "v1_otomo_crumb", "color": "tomato red",
     "description": (
         "Absurdly short and round character, huge cheerful head with tiny body. Wearing a dented "
         "tomato-red racing barrel as a vest with racing stripes and sponsor stickers, barrel is short "
         "and ends at the waist not covering arms or legs. Stubby thick arms and chunky legs fully "
         "visible and separate from barrel body. Enormous goofy grin on oversized round face. Tiny "
         "racing helmet perched on top of huge head. Comically small feet."
     )},
]


def build_prompt(char: dict) -> str:
    """Build the full Flux prompt for a character fullbody.

    Style goes FIRST so Flux weights it heavily. Character description second.
    T-pose instruction and technical requirements last.
    """
    style = STYLE_LABELS.get(char["style"], "underground comix illustration")
    return (
        f"{style}, "
        f"HEAVY BLACK INK illustration, extreme high contrast black and white with "
        f"selective bold color accents of {char['color']}, "
        f"full body character design sheet of {char['name']}, "
        f"{char['description']}, "
        f"{TPOSE_PROMPT}, "
        f"full body visible head to feet, character design reference sheet, "
        f"stark dramatic noir shadows, thick aggressive ink brushstrokes and splatter, "
        f"exaggerated cartoon proportions, ugly-beautiful underground comix aesthetic"
    )


def submit_workflow(char: dict) -> dict:
    """Submit a ComfyUI workflow for one character."""
    with open(WORKFLOW_PATH) as f:
        workflow = json.load(f)

    seed = random.randint(1, 2**31)
    prompt_text = build_prompt(char)
    prefix = f"Berserkr_{char['id']}_fullbody"

    # Fill in parameters
    workflow["2"]["inputs"]["width"] = 768
    workflow["2"]["inputs"]["height"] = 768
    workflow["3"]["inputs"]["text"] = prompt_text
    workflow["5"]["inputs"]["seed"] = seed
    workflow["7"]["inputs"]["filename_prefix"] = prefix

    # Submit to ComfyUI
    payload = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())

    # Save seed for reproducibility
    out_dir = OUTPUT_ROOT / char["id"] / "fullbody"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "fullbody-seed.txt").write_text(str(seed))

    print(f"  [{char['id']}] Submitted prompt_id={result.get('prompt_id', '?')}, seed={seed}")
    return result


def wait_for_completion(prompt_id: str, timeout: int = 300) -> bool:
    """Poll ComfyUI history until the prompt completes."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                if outputs:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def copy_output(prompt_id: str, char_id: str) -> str | None:
    """Find the generated image in ComfyUI output and copy it."""
    resp = urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}")
    history = json.loads(resp.read())

    if prompt_id not in history:
        return None

    outputs = history[prompt_id].get("outputs", {})
    for node_id, node_out in outputs.items():
        images = node_out.get("images", [])
        for img in images:
            filename = img["filename"]
            subfolder = img.get("subfolder", "")

            # Download from ComfyUI
            params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": "output"})
            img_resp = urllib.request.urlopen(f"{COMFYUI_URL}/view?{params}")
            img_data = img_resp.read()

            # Save to character output
            dest = OUTPUT_ROOT / char_id / "fullbody" / "fullbody.png"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(img_data)
            print(f"  [{char_id}] Saved {dest} ({len(img_data):,} bytes)")
            return str(dest)

    return None


import urllib.parse


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--character", help="Generate one character by ID")
    parser.add_argument("--all", action="store_true", help="Generate all 9 remaining characters")
    parser.add_argument("--list", action="store_true", help="List characters")
    args = parser.parse_args()

    if args.list:
        for c in CHARACTERS:
            print(f"  {c['id']:12s} {c['name']}")
        return

    chars = CHARACTERS
    if args.character:
        chars = [c for c in CHARACTERS if c["id"] == args.character]
        if not chars:
            print(f"Unknown character: {args.character}")
            sys.exit(1)

    if not args.all and not args.character:
        parser.print_help()
        return

    print(f"Generating fullbody T-poses for {len(chars)} character(s)...")

    for char in chars:
        print(f"\n--- {char['name']} ({char['id']}) ---")
        result = submit_workflow(char)
        prompt_id = result.get("prompt_id")
        if not prompt_id:
            print(f"  [{char['id']}] FAILED to submit")
            continue

        print(f"  [{char['id']}] Waiting for generation...")
        if wait_for_completion(prompt_id, timeout=300):
            copy_output(prompt_id, char["id"])
        else:
            print(f"  [{char['id']}] TIMEOUT after 300s")

    print("\nDone!")


if __name__ == "__main__":
    main()
