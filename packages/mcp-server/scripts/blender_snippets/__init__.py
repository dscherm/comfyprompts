"""Blender Python snippets for use with blender-mcp execute_blender_code.

Each module in this package is a standalone Python script that can be executed
inside a live Blender session via blender-mcp's execute_blender_code tool.

Usage from Claude:
    1. Read the snippet file
    2. Substitute parameters (e.g., FILEPATH, RIG_TYPE)
    3. Send via blender-mcp: execute_blender_code(code=snippet)

Snippets are self-contained -- they import only from bpy/mathutils (always
available in Blender's Python) and inline any utility functions they need.
"""

from pathlib import Path

SNIPPETS_DIR = Path(__file__).parent


def load_snippet(name: str) -> str:
    """Load a snippet file by name (without .py extension).

    Args:
        name: Snippet filename without extension (e.g., 'rig_humanoid')

    Returns:
        The snippet source code as a string
    """
    path = SNIPPETS_DIR / f"{name}.py"
    if not path.exists():
        raise FileNotFoundError(f"Snippet not found: {path}")
    return path.read_text(encoding="utf-8")


def list_snippets() -> list[str]:
    """List available snippet names."""
    return sorted(
        p.stem for p in SNIPPETS_DIR.glob("*.py")
        if p.stem != "__init__"
    )
