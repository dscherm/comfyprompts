"""soapbox_racers — write CLEAN per-character captions (no Florence).

The v1 run went cartoonish because Florence auto-captions labeled nearly every
image "cartoon/animated/anime" (52/30/5 occurrences) AND the to3d source art is
chibi game-mascot proportions. This retrain fixes BOTH: train on the gritty
character_variations, and caption from the user's character brief with a gritty
comic vocabulary — never "cartoon"/"animated"/"anime".

Keys each image to a character by filename substring, writes <stem>.txt.
    python soapbox_racers_caption.py <dataset_dir>
"""
import os
import sys

TRIGGER = "soapbox_racers"
STYLE = ("gritty comic book illustration, heavy black ink, bold outlines, crosshatching, "
         "detailed line art, dramatic, wasteland racer, full body")

# character -> short descriptive phrase (from the user's brief)
CHARS = {
    "bones": "a tall skeletal reaper with bone-white face paint, black leather vest with skull patches, bleached white mohawk",
    "crank": "a stocky grease-stained mechanic in brown oil-stained overalls, flat cap, handlebar mustache, big wrench",
    "grit": "a muscular female desert warrior in a sand-colored wrap and hood, tribal face tattoos, leather armor, braided hair",
    "pip": "a small thin scavenger teenager in a green patched vest, oversized scrap backpack, messy red hair, wide eyes",
    "punk_king": "an imposing wasteland queen in a spiked leather crown and royal purple cape, punk vest with chains and studs, wild dark hair",
    "punk": "an imposing wasteland queen in a spiked leather crown and royal purple cape, punk vest with chains and studs, wild dark hair",
    "rust": "a heavy-set ironclad racer in bolted rusted metal armor plates, welding mask, rust red-brown color scheme",
    "smog": "a lanky chemist hidden behind a gas mask and dark green torn hazmat overcoat, breathing tubes, hood up",
    "soup_box": "a hulking wasteland brawler racer in heavy overalls",
    "soup": "a hulking wasteland brawler racer in heavy overalls",
    "sparks": "an electric livewire woman in a blue bodysuit with lightning-yellow accents, goggles, wild light-blue hair",
    "rookie": "the rookie, a young male racer in an orange racing jacket with black stripes, aviator goggles on his forehead, messy brown hair",
    "player": "the rookie, a young male racer in an orange racing jacket with black stripes, aviator goggles on his forehead, messy brown hair",
}
ORDER = ["punk_king", "soup_box", "rookie", "bones", "crank", "grit", "pip", "punk",
         "rust", "smog", "soup", "sparks", "player"]  # longest/most-specific first


def caption_for(fname: str) -> str | None:
    low = fname.lower()
    for key in ORDER:
        if key in low:
            return f"{TRIGGER}, {STYLE}, {CHARS[key]}"
    return None


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "E:/ai-training/datasets/soapbox_racers_gritty"
    n = miss = 0
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith(".png"):
            continue
        cap = caption_for(f)
        if not cap:
            print("  ? no character match:", f)
            miss += 1
            continue
        open(os.path.join(d, f[:-4] + ".txt"), "w", encoding="utf-8").write(cap)
        n += 1
    print(f"CAPTIONS WRITTEN: {n} (unmatched: {miss}) -> {d}")


if __name__ == "__main__":
    main()
