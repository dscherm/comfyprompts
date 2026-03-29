"""
Download free rigged models from Sketchfab API.
Uses the Sketchfab Data API to search and download CC-licensed rigged models.

Usage:
    python download_sketchfab.py [--humanoid] [--quadruped] [--creature]

Note: Downloads are GLB format. Some models require Sketchfab API token for download.
Set SKETCHFAB_TOKEN env var or it will attempt anonymous download.
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path

REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"
API_BASE = "https://api.sketchfab.com/v3"

# Known free downloadable rigged models (verified CC licenses)
KNOWN_MODELS = {
    "humanoid": [
        {
            "uid": "7311fcfdc03e4234900eeced42a1e669",
            "name": "human_basemesh_pair",
            "description": "Male + Female rigged human basemesh (CC-BY)",
        },
        {
            "uid": "995558e2514644909c9037b0e7762855",
            "name": "humanoid_avatar_rig",
            "description": "Generic humanoid avatar with rig",
        },
    ],
    "quadruped": [
        {
            "uid": "05a0854fb54d4e34a100016545cc69e5",
            "name": "camel_rigged",
            "description": "Rigged camel in GLB format",
        },
    ],
}


def search_sketchfab(query, downloadable=True, rigged=True, max_results=5):
    """Search Sketchfab for models matching query."""
    params = {
        "type": "models",
        "q": query,
        "downloadable": str(downloadable).lower(),
        "rigged": str(rigged).lower(),
        "count": str(max_results),
        "sort_by": "-likeCount",
    }
    url = f"{API_BASE}/search?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url)
    req.add_header("User-Agent", "autorig-ralph/1.0")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results", [])
            print(f"  Found {len(results)} models for '{query}'")
            for r in results:
                uid = r.get("uid", "")
                name = r.get("name", "unknown")
                vertex_count = r.get("vertexCount", 0)
                face_count = r.get("faceCount", 0)
                license_info = r.get("license", {})
                license_label = license_info.get("label", "unknown") if license_info else "unknown"
                print(f"    {uid[:8]}... {name} ({vertex_count} verts, {license_label})")
            return results
    except Exception as e:
        print(f"  Search failed: {e}")
        return []


def download_model(uid, output_path, token=None):
    """Download a model from Sketchfab by UID."""
    # Step 1: Get download URL
    url = f"{API_BASE}/models/{uid}/download"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "autorig-ralph/1.0")
    if token:
        req.add_header("Authorization", f"Token {token}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            # Get GLB/GLTF download URL
            gltf = data.get("gltf", {})
            download_url = gltf.get("url")
            if not download_url:
                # Try other formats
                for fmt in ["glb", "source"]:
                    if fmt in data and "url" in data[fmt]:
                        download_url = data[fmt]["url"]
                        break

            if not download_url:
                print(f"  No download URL found for {uid}")
                return False

        # Step 2: Download the file
        print(f"  Downloading {uid[:8]}... to {output_path}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        urllib.request.urlretrieve(download_url, output_path)
        size = os.path.getsize(output_path)
        print(f"  Downloaded: {output_path} ({size:,} bytes)")

        # If it's a zip, extract it
        if output_path.endswith(".zip"):
            import zipfile
            extract_dir = output_path.replace(".zip", "")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(output_path, 'r') as zf:
                zf.extractall(extract_dir)
            print(f"  Extracted to: {extract_dir}")
            # Find GLB/GLTF in extracted files
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith((".glb", ".gltf")):
                        final_path = output_path.replace(".zip", ".glb")
                        os.rename(os.path.join(root, f), final_path)
                        print(f"  Final: {final_path}")
                        break

        return True

    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"  Auth required for {uid} -- set SKETCHFAB_TOKEN env var")
        elif e.code == 403:
            print(f"  Forbidden (model may not be downloadable): {uid}")
        elif e.code == 404:
            print(f"  Model not found or download not available: {uid}")
        else:
            print(f"  HTTP error {e.code} for {uid}: {e.reason}")
        return False
    except Exception as e:
        print(f"  Download failed for {uid}: {e}")
        return False


def download_known_models(body_type=None):
    """Download all known free models."""
    token = os.environ.get("SKETCHFAB_TOKEN")
    if token:
        print(f"Using Sketchfab API token")
    else:
        print("No SKETCHFAB_TOKEN set -- some downloads may fail (auth required)")

    success = 0
    failed = 0

    for bt, models in KNOWN_MODELS.items():
        if body_type and bt != body_type:
            continue
        for model in models:
            out_path = str(REFERENCES_DIR / bt / f"sketchfab_{model['name']}.zip")
            glb_path = str(REFERENCES_DIR / bt / f"sketchfab_{model['name']}.glb")

            if os.path.exists(glb_path):
                print(f"  Already exists: {glb_path}")
                success += 1
                continue

            print(f"\n[{bt.upper()}] {model['name']}: {model['description']}")
            if download_model(model["uid"], out_path, token):
                success += 1
            else:
                failed += 1

    print(f"\nResults: {success} downloaded, {failed} failed")
    return success, failed


def search_and_show(body_type):
    """Search for models and show results (for manual selection)."""
    queries = {
        "humanoid": "rigged humanoid character low poly",
        "quadruped": "rigged quadruped animal",
        "creature": "rigged creature monster dragon",
    }
    query = queries.get(body_type, f"rigged {body_type}")
    print(f"\nSearching Sketchfab for: {query}")
    results = search_sketchfab(query, downloadable=True, rigged=True, max_results=10)
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download rigged models from Sketchfab")
    parser.add_argument("--humanoid", action="store_true")
    parser.add_argument("--quadruped", action="store_true")
    parser.add_argument("--creature", action="store_true")
    parser.add_argument("--search", action="store_true", help="Search only, don't download")
    parser.add_argument("--all", action="store_true", help="Download all known models")
    args = parser.parse_args()

    body_type = None
    if args.humanoid:
        body_type = "humanoid"
    elif args.quadruped:
        body_type = "quadruped"
    elif args.creature:
        body_type = "creature"

    if args.search:
        for bt in (["humanoid", "quadruped", "creature"] if not body_type else [body_type]):
            search_and_show(bt)
    else:
        download_known_models(body_type)


if __name__ == "__main__":
    main()
