"""Hot-reload watcher: monitors directories for .blend file changes and
auto-exports to GLB via Blender headless.

Usage:
    python hot_reload_watcher.py --watch-dir /path/to/blends --output-dir /path/to/glbs
    python hot_reload_watcher.py --watch-dir ./models --blender-path "C:/custom/blender.exe"
    python hot_reload_watcher.py --watch-dir ./models --poll-interval 5

Uses os.stat polling (no external dependencies). Skips .blend1/.blend2 temp files.
"""

import argparse
import logging
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

# Default Blender path for this system
DEFAULT_BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("hot_reload_watcher")

# Inline Blender export script passed via --python-expr
BLEND_TO_GLB_SCRIPT = textwrap.dedent("""\
    import bpy, sys
    argv = sys.argv[sys.argv.index("--") + 1:]
    src, dst = argv[0], argv[1]
    bpy.ops.wm.open_mainfile(filepath=src)
    bpy.ops.export_scene.gltf(
        filepath=dst,
        export_format="GLB",
        export_apply=True,
    )
    print("EXPORT_OK: " + dst)
""")


def find_blend_files(watch_dir: Path) -> dict[Path, float]:
    """Scan directory recursively for .blend files, return path -> mtime map."""
    result = {}
    for root, _dirs, files in os.walk(watch_dir):
        for fname in files:
            # Only .blend, skip .blend1 .blend2 etc.
            if fname.endswith(".blend") and not any(
                fname.endswith(f".blend{n}") for n in range(1, 10)
            ):
                p = Path(root) / fname
                try:
                    result[p] = os.stat(p).st_mtime
                except OSError:
                    pass
    return result


def export_blend_to_glb(
    blend_path: Path, output_dir: Path, blender_exe: Path
) -> bool:
    """Run Blender headless to export a .blend file to GLB. Returns True on success."""
    glb_name = blend_path.stem + ".glb"
    out_path = output_dir / glb_name

    logger.info("Exporting: %s -> %s", blend_path.name, out_path)
    start = time.monotonic()

    try:
        proc = subprocess.run(
            [
                str(blender_exe),
                "--background",
                "--python-expr",
                BLEND_TO_GLB_SCRIPT,
                "--",
                str(blend_path),
                str(out_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        logger.error("  Export timed out after 120s: %s", blend_path.name)
        return False

    elapsed = time.monotonic() - start

    if proc.returncode != 0 or "EXPORT_OK" not in proc.stdout:
        logger.error(
            "  Export FAILED (exit %d, %.1fs): %s",
            proc.returncode,
            elapsed,
            blend_path.name,
        )
        if proc.stderr:
            for line in proc.stderr.strip().splitlines()[-5:]:
                logger.error("    %s", line)
        return False

    logger.info("  OK (%.1fs): %s", elapsed, out_path.name)
    return True


def verify_blender(blender_exe: Path) -> bool:
    """Check that the Blender executable exists and can run."""
    if not blender_exe.exists():
        logger.error("Blender not found at: %s", blender_exe)
        return False
    try:
        proc = subprocess.run(
            [str(blender_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0:
            version_line = proc.stdout.strip().splitlines()[0]
            logger.info("Using %s", version_line)
            return True
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.error("Failed to run Blender: %s", e)
    return False


def watch_loop(
    watch_dir: Path, output_dir: Path, blender_exe: Path, poll_interval: float
) -> None:
    """Main polling loop. Tracks mtimes and exports on change."""
    logger.info("Watching: %s", watch_dir)
    logger.info("Output:   %s", output_dir)
    logger.info("Polling every %.1fs", poll_interval)

    # Initial snapshot
    known: dict[Path, float] = find_blend_files(watch_dir)
    logger.info("Found %d .blend file(s)", len(known))

    export_count = 0
    try:
        while True:
            time.sleep(poll_interval)
            current = find_blend_files(watch_dir)

            # Detect new or modified files
            changed: list[Path] = []
            for path, mtime in current.items():
                if path not in known or mtime != known[path]:
                    changed.append(path)

            # Detect deleted files (just log, no action needed)
            for path in set(known) - set(current):
                logger.info("Removed: %s", path.name)

            # Export changed files
            for path in changed:
                if path in known:
                    logger.info("Modified: %s", path.name)
                else:
                    logger.info("New file: %s", path.name)

                if export_blend_to_glb(path, output_dir, blender_exe):
                    export_count += 1

            known = current
    except KeyboardInterrupt:
        logger.info("Stopped. Exported %d file(s) total.", export_count)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch .blend files and auto-export to GLB via Blender headless."
    )
    parser.add_argument(
        "--watch-dir",
        type=Path,
        required=True,
        help="Directory to watch for .blend file changes (recursive).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for exported GLBs. Defaults to --watch-dir.",
    )
    parser.add_argument(
        "--blender-path",
        type=Path,
        default=DEFAULT_BLENDER,
        help=f"Path to Blender executable. Default: {DEFAULT_BLENDER}",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Seconds between polls. Default: 2.",
    )
    args = parser.parse_args()

    watch_dir: Path = args.watch_dir.resolve()
    output_dir: Path = (args.output_dir or args.watch_dir).resolve()
    blender_exe: Path = args.blender_path

    if not watch_dir.is_dir():
        logger.error("Watch directory does not exist: %s", watch_dir)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    if not verify_blender(blender_exe):
        logger.error(
            "Blender is not available. Install Blender or pass --blender-path."
        )
        sys.exit(1)

    watch_loop(watch_dir, output_dir, blender_exe, args.poll_interval)


if __name__ == "__main__":
    main()
