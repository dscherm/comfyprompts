"""
Download CC-licensed models from Sketchfab using their download API.
Models with CC licenses have free download endpoints.
"""
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"
API_BASE = "https://api.sketchfab.com/v3"

# CC-Attribution models found via search (verified downloadable)
CC_MODELS = [
    # Humanoid
    {"uid": "78640adbb65843bca9df0e3a91eb4002", "name": "ps1_male_character", "body": "humanoid",
     "desc": "Male Character PS1-Style (492 verts, CC-BY)"},
    {"uid": "ece576bbf5a0463fb0c61eb25d935a9f", "name": "skeleton_character_psx", "body": "humanoid",
     "desc": "Skeleton Character PSX (855 verts, CC-BY)"},
    {"uid": "4cf10e2dd4ab4f7e965ff9a6a22a3a70", "name": "girl_worker", "body": "humanoid",
     "desc": "Girl with clothes Worker set (1332 verts, CC-BY)"},
    {"uid": "8898a872bfeb4b78b6a1dcce02c3ae2a", "name": "female_secretary_psx", "body": "humanoid",
     "desc": "Female Secretary PSX (476 verts, CC-BY)"},
    {"uid": "8dc8884c35ff493db4606e3ea2adde07", "name": "fuse_orion_male_2", "body": "humanoid",
     "desc": ".Fuse Orion Male Clothes 2 (5202 verts, CC-BY)"},
    {"uid": "82901674cf304685b4a958f9a6e128a6", "name": "fuse_orion_male_1", "body": "humanoid",
     "desc": ".Fuse Orion Male Clothes 1 (4678 verts, CC-BY)"},
    # Quadruped
    {"uid": "39118bd9e5f64e4e83a4b82eadde82f4", "name": "cat_rigged", "body": "quadruped",
     "desc": "Cat Rigged (2754 verts, CC-BY)"},
    # Creature
    {"uid": "82f393a2b2b04ae8afdd8b3b00a73d7e", "name": "european_dragon", "body": "creature",
     "desc": "European Dragon (21225 verts, CC-BY)"},
    {"uid": "0da998921fee41cb908c6f3fe2e9c06a", "name": "animated_kobold", "body": "creature",
     "desc": "Animated Kobold (6506 verts, CC-BY)"},
    {"uid": "2fb96bd764f14be792f3f2b6da7bd4d8", "name": "naga_dragon_serpent", "body": "creature",
     "desc": "Naga Dragon Serpent (39411 verts, CC-BY)"},
    {"uid": "c5224e518bbd402f8b74de2c0c24b58c", "name": "chimera", "body": "creature",
     "desc": "Chimera (21586 verts, CC-BY)"},
    {"uid": "7747294b80b04a088b43cbbbbb7ef8d0", "name": "eel_monster_rigged", "body": "creature",
     "desc": "Eel monster rigged / serpentine (23440 verts, CC-BY)"},
]


def download_model(uid, output_dir, filename):
    """Download a model using Sketchfab's download API."""
    os.makedirs(output_dir, exist_ok=True)
    zip_path = os.path.join(output_dir, f"{filename}.zip")
    glb_path = os.path.join(output_dir, f"{filename}.glb")
    gltf_dir = os.path.join(output_dir, f"{filename}_extracted")

    if os.path.exists(glb_path):
        print(f"    Already exists: {glb_path}")
        return True

    # Check for already extracted gltf
    if os.path.exists(gltf_dir):
        # Look for glb/gltf inside
        for root, dirs, files in os.walk(gltf_dir):
            for f in files:
                if f.endswith(".glb"):
                    os.rename(os.path.join(root, f), glb_path)
                    print(f"    Found existing GLB: {glb_path}")
                    return True

    url = f"{API_BASE}/models/{uid}/download"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "autorig-ralph/1.0 (reference mesh collection)")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())

        # Try GLTF format first (most compatible)
        dl_url = None
        dl_size = 0
        for fmt_key in ["gltf", "glb", "source"]:
            fmt_data = data.get(fmt_key, {})
            if fmt_data and "url" in fmt_data:
                dl_url = fmt_data["url"]
                dl_size = fmt_data.get("size", 0)
                print(f"    Format: {fmt_key}, size: {dl_size:,} bytes")
                break

        if not dl_url:
            print(f"    No download URL available")
            return False

        # Download
        print(f"    Downloading...")
        urllib.request.urlretrieve(dl_url, zip_path)
        actual_size = os.path.getsize(zip_path)
        print(f"    Downloaded: {actual_size:,} bytes")

        # Extract zip
        if zipfile.is_zipfile(zip_path):
            os.makedirs(gltf_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(gltf_dir)
            os.remove(zip_path)

            # Find GLB or GLTF
            for root, dirs, files in os.walk(gltf_dir):
                for f in files:
                    if f.endswith(".glb"):
                        final = os.path.join(output_dir, f"{filename}.glb")
                        os.rename(os.path.join(root, f), final)
                        print(f"    Extracted GLB: {final}")
                        return True
                    elif f.endswith(".gltf"):
                        # Keep the whole directory for GLTF (has external textures)
                        print(f"    Extracted GLTF: {os.path.join(root, f)}")
                        return True

            print(f"    No GLB/GLTF found in zip")
            return False
        else:
            # Not a zip - might be direct GLB
            os.rename(zip_path, glb_path)
            print(f"    Saved as: {glb_path}")
            return True

    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"    Auth required (need Sketchfab token)")
        elif e.code == 403:
            print(f"    Forbidden (not downloadable without account)")
        elif e.code == 404:
            print(f"    Not found / download unavailable")
        else:
            print(f"    HTTP {e.code}: {e.reason}")
        return False
    except Exception as e:
        print(f"    Error: {e}")
        return False


def main():
    print("=" * 60)
    print("  Downloading CC-licensed rigged models from Sketchfab")
    print("=" * 60)

    success = 0
    failed = 0
    skipped = 0

    for model in CC_MODELS:
        body = model["body"]
        name = model["name"]
        desc = model["desc"]
        uid = model["uid"]
        out_dir = str(REFERENCES_DIR / body)

        print(f"\n[{body.upper()}] {desc}")
        result = download_model(uid, out_dir, f"sketchfab_{name}")
        if result:
            success += 1
        else:
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  Results: {success} downloaded, {failed} failed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
