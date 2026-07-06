"""Safe output-filename validation for user-supplied asset and kit names.

User- and pipeline-supplied names become output filenames under ``products/``
and ``output/``. ``safe_filename`` is the single gate they pass through: a safe
name is returned unchanged, anything unsafe raises ``ValueError``. There is no
sanitize-and-continue mode — rewriting a hostile name into a "close enough"
one is how traversal and device-name bugs slip through, so an unsafe name is
always an error.

Safe means: only characters in ``[A-Za-z0-9._-]``, within the length limit,
not an empty or dot-only name, and not a Windows reserved device name. That
allowlist (not a blocklist) is what makes this robust against path separators,
null bytes, whitespace, Unicode look-alikes, and shell/glob metacharacters in
one rule, on every platform.
"""

from __future__ import annotations

import re

__all__ = ["safe_filename"]

# Allowlist: one or more of letters, digits, dot, underscore, hyphen. Anything
# outside this set — separators, spaces, control chars, Unicode, metacharacters
# — fails to match and is rejected.
_ALLOWED = re.compile(r"\A[A-Za-z0-9._-]+\Z")

# Names that are not usable filenames even though they pass the charset rule.
_DOT_NAMES = frozenset({".", ".."})

# Windows reserved device names. Reserved bare or with any extension, in any
# casing, so the check is against the upper-cased stem before the first dot.
_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def safe_filename(name: str, max_length: int = 128) -> str:
    """Return ``name`` unchanged if it is a safe filename, else raise ValueError.

    Args:
        name: the candidate filename. Must be a ``str``; any other type raises
            ``TypeError`` (no silent coercion).
        max_length: inclusive upper bound on length (default 128).

    Raises:
        TypeError: if ``name`` is not a ``str``.
        ValueError: if ``name`` is empty, too long, contains a character
            outside ``[A-Za-z0-9._-]``, is a dot-only name, or is a Windows
            reserved device name. The message describes the rule violated and
            deliberately does not echo the input or any environment/path
            detail.
    """
    if not isinstance(name, str):
        raise TypeError(f"name must be str, got {type(name).__name__}")

    # Length first — reject oversized input before any scanning.
    if len(name) > max_length:
        raise ValueError(f"name exceeds max_length of {max_length}")
    if not name:
        raise ValueError("name must not be empty")

    if _ALLOWED.match(name) is None:
        raise ValueError("name contains characters outside [A-Za-z0-9._-]")

    if name in _DOT_NAMES:
        raise ValueError("name must not be a dot-only name")

    stem = name.split(".", 1)[0].upper()
    if stem in _RESERVED:
        raise ValueError("name is a reserved device name")

    return name
