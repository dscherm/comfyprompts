"""Blind-TDD contract tests for tools/security/filename_guard.py.

Covers acceptance criteria for task sec-filename-guard-1: a single
validation gate `safe_filename(name, max_length=128)` that returns safe
names unchanged and raises ``ValueError`` on anything unsafe (no
sanitize-and-continue mode).

Modules are loaded by file path (nothing here is pip-installed), mirroring
the convention documented in public_api.md and tests/test_kitlib.py. The
loader raises ``FileNotFoundError`` until the implementation exists, so
every behavioural test fails in the red phase.
"""

import importlib.util
import os
import re
from pathlib import Path

import pytest

# parents[2] from tests/contracts/<this file> == repo root.
_MOD_PATH = (
    Path(__file__).resolve().parents[2] / "tools" / "security" / "filename_guard.py"
)


def load_guard():
    """Load filename_guard from its source path, fresh each call.

    Raises FileNotFoundError while the implementation is missing (red phase).
    """
    spec = importlib.util.spec_from_file_location("filename_guard", _MOD_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # FileNotFoundError until implemented
    return mod


# --------------------------------------------------------------------------
# AC-1 — safe names pass through unchanged
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "grim_forge-kit.v2",
        "asset",
        "Castle_Kit_GrimForge_v1",
        "a.b.c",
        "file-01_final.v3",
        "ABCabc012._-",
    ],
)
def test_safe_names_returned_unchanged(name):
    """Covers: AC-1 — a name of only [A-Za-z0-9._-] is returned verbatim.

    Given a user-supplied asset name consisting only of safe characters,
    when safe_filename is called with it,
    then it returns the exact same string unchanged.
    """
    guard = load_guard()
    assert guard.safe_filename(name) == name


# --------------------------------------------------------------------------
# AC-2 — path separators / traversal sequences are rejected
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "../evil",
        "..\\evil",
        "a/b",
        "C:\\x",
        "/etc/passwd",
    ],
)
def test_path_separators_and_traversal_raise(name):
    """Covers: AC-2 — separators and traversal sequences raise ValueError.

    Given input containing a path separator or traversal sequence,
    when safe_filename is called with it,
    then it raises ValueError and returns no value.
    """
    guard = load_guard()
    with pytest.raises(ValueError):
        guard.safe_filename(name)


# --------------------------------------------------------------------------
# AC-3 — length boundary at max_length (default 128)
# --------------------------------------------------------------------------

def test_name_at_max_length_boundary_passes():
    """Covers: AC-3 — a 128-char safe name returns unchanged.

    Given a name of exactly max_length safe characters,
    when safe_filename is called with the default max_length,
    then it returns the name unchanged.
    """
    guard = load_guard()
    name = "a" * 128
    assert guard.safe_filename(name) == name


def test_name_over_max_length_raises():
    """Covers: AC-3 — a 129-char name exceeds the default limit.

    Given a name one character longer than max_length,
    when safe_filename is called with no max_length argument,
    then it raises ValueError.
    """
    guard = load_guard()
    with pytest.raises(ValueError):
        guard.safe_filename("a" * 129)


def test_custom_max_length_is_honoured():
    """Covers: AC-3 — the max_length argument shifts the boundary.

    Given an explicit max_length of 8,
    when safe_filename is called with a 9-char safe name,
    then it raises ValueError, while an 8-char name passes.
    """
    guard = load_guard()
    assert guard.safe_filename("abcdefgh", max_length=8) == "abcdefgh"
    with pytest.raises(ValueError):
        guard.safe_filename("abcdefghi", max_length=8)


# --------------------------------------------------------------------------
# AC-4 — any character outside [A-Za-z0-9._-], plus empty / dot names
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "a\x00b",  # null byte
        "a b",     # whitespace
        "a*b",     # glob / illegal char
        "",        # empty
        ".",       # bare dot
        "..",      # bare double-dot
    ],
)
def test_illegal_characters_and_dot_names_raise(name):
    """Covers: AC-4 — null bytes, whitespace, out-of-set chars, dot names.

    Given input with a null byte, whitespace, an out-of-set character, or
    the empty / dot-only names,
    when safe_filename is called with it,
    then it raises ValueError.
    """
    guard = load_guard()
    with pytest.raises(ValueError):
        guard.safe_filename(name)


@pytest.mark.parametrize(
    "name",
    ["a\tb", "a\nb", "café", "emoji\U0001f600", "name#1", "a|b", "a:b", "a?b"],
)
def test_more_out_of_set_characters_raise(name):
    """Covers: AC-4 — a broader sweep of out-of-set characters.

    Given input containing tabs, newlines, non-ASCII letters, or shell/glob
    metacharacters,
    when safe_filename is called with it,
    then it raises ValueError.
    """
    guard = load_guard()
    with pytest.raises(ValueError):
        guard.safe_filename(name)


# --------------------------------------------------------------------------
# AC-5 — Windows reserved device names, any casing, any extension
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "CON",
        "con",
        "NUL",
        "aux.txt",
        "LPT1.png",
        "COM1",
        "PRN",
        "Con.jpg",
        "nul.data",
    ],
)
def test_windows_reserved_device_names_raise(name):
    """Covers: AC-5 — reserved device names (bare or with extension) raise.

    Given a Windows reserved device name in any casing, bare or with any
    extension,
    when safe_filename is called with it,
    then it raises ValueError.
    """
    guard = load_guard()
    with pytest.raises(ValueError):
        guard.safe_filename(name)


# --------------------------------------------------------------------------
# AC-6 — oversized input is rejected before processing (security pack)
# --------------------------------------------------------------------------

def test_oversized_input_raises_before_processing():
    """Covers: AC-6 — a 1,000,000-char name is rejected with ValueError.

    Given an input far beyond the documented max_length,
    when safe_filename is called with it,
    then it raises ValueError (the documented validation error).
    """
    guard = load_guard()
    with pytest.raises(ValueError):
        guard.safe_filename("a" * 1_000_000)


# --------------------------------------------------------------------------
# AC-7 — None / wrong-typed arguments are rejected, not coerced (security pack)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad",
    [
        None,
        123,
        12.5,
        b"abc",
        ["a"],
        {"a": 1},
        ("a",),
    ],
)
def test_wrong_typed_name_raises(bad):
    """Covers: AC-7 — a None or wrong-typed name raises, no silent coercion.

    Given a required parameter,
    when safe_filename is called with None or a value of the wrong type,
    then it raises TypeError or ValueError and returns no coerced result.
    """
    guard = load_guard()
    with pytest.raises((TypeError, ValueError)):
        guard.safe_filename(bad)


# --------------------------------------------------------------------------
# AC-8 — injection metacharacters into the filename sink (security pack)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "../etc/passwd",   # traversal
        "a\x00b",          # null byte
        "o'brien",         # single quote
        "<script>",        # markup
        "a;rm -rf b",      # shell separators
        "$(whoami)",       # command substitution
        "a`b`",            # backtick
    ],
)
def test_injection_metacharacters_are_rejected(name):
    """Covers: AC-8 — sink metacharacters never reach the filename as control.

    Given input containing metacharacters for the filename/path sink,
    when safe_filename is called with it,
    then it raises the documented validation error (ValueError); the name is
    never returned as a usable path with the metacharacters intact.
    """
    guard = load_guard()
    with pytest.raises(ValueError):
        guard.safe_filename(name)


# --------------------------------------------------------------------------
# AC-9 — no hardcoded secrets in the implementation source (static scan)
# --------------------------------------------------------------------------

_CREDENTIAL_PATTERNS = [
    re.compile(r"BEGIN RSA PRIVATE KEY"),
    re.compile(r"BEGIN PRIVATE KEY"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]
# password/secret/api_key assigned to a non-empty string literal.
_SECRET_ASSIGN = re.compile(
    r"""(?ix)\b(password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*['"]([^'"]+)['"]"""
)
_PLACEHOLDER_VALUES = {
    "",
    "x",
    "xxx",
    "xxxx",
    "changeme",
    "placeholder",
    "your_key_here",
    "todo",
    "none",
    "example",
    "dummy",
}


def test_implementation_has_no_hardcoded_secrets():
    """Covers: AC-9 — scan impl source text for credential patterns.

    Given the implementation source file,
    when it is read as text and scanned for private-key blocks, AWS access
    keys, and secret assignments to non-placeholder literals,
    then zero credential patterns are found; the test fails before the
    implementation exists because the file it scans is missing.
    """
    assert _MOD_PATH.exists(), f"implementation file missing: {_MOD_PATH}"
    source = _MOD_PATH.read_text(encoding="utf-8")

    for pat in _CREDENTIAL_PATTERNS:
        assert not pat.search(source), f"credential pattern {pat.pattern!r} found"

    for match in _SECRET_ASSIGN.finditer(source):
        value = match.group(2).strip().lower()
        assert value in _PLACEHOLDER_VALUES, (
            f"secret-like assignment to non-placeholder literal: {match.group(0)!r}"
        )


# --------------------------------------------------------------------------
# AC-10 — failures surfaced to the caller leak no internals (security pack)
# --------------------------------------------------------------------------

def test_error_surface_leaks_no_internals(monkeypatch):
    """Covers: AC-10 — surfaced errors carry no traceback / path / env leak.

    Given a failure triggered through the public surface,
    when the ValueError message is inspected,
    then it contains no traceback text, no absolute filesystem path, and no
    environment-variable value.
    """
    guard = load_guard()
    sentinel = "S3CRET_ENV_VALUE_should_not_leak"
    monkeypatch.setenv("FILENAME_GUARD_TEST_SECRET", sentinel)

    with pytest.raises(ValueError) as excinfo:
        guard.safe_filename("bad name!")  # invalid char, contains no path

    message = str(excinfo.value)
    assert "Traceback (most recent call last)" not in message
    assert sentinel not in message
    # No absolute filesystem paths (windows drive root or common unix roots).
    assert not re.search(r"[A-Za-z]:\\", message)
    assert not re.search(r"(?:^|[\s'\"])/(?:home|Users|etc|root|var)/", message)
    assert os.getcwd() not in message


# --------------------------------------------------------------------------
# AC-11 — no dangerous constructs in the implementation source (static scan)
# --------------------------------------------------------------------------

_DANGEROUS_PATTERNS = [
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"\bpickle\.loads\s*\("),
    re.compile(r"\bos\.system\s*\("),
    re.compile(r"shell\s*=\s*True"),
]
_YAML_LOAD = re.compile(r"\byaml\.load\s*\(")


def test_implementation_has_no_dangerous_constructs():
    """Covers: AC-11 — scan impl source text for dangerous constructs.

    Given the implementation source file,
    when it is read as text and scanned for eval/exec/pickle.loads/os.system,
    shell=True, and yaml.load without SafeLoader,
    then zero dangerous constructs are found; the test fails before the
    implementation exists because the file it scans is missing.
    """
    assert _MOD_PATH.exists(), f"implementation file missing: {_MOD_PATH}"
    source = _MOD_PATH.read_text(encoding="utf-8")

    for pat in _DANGEROUS_PATTERNS:
        assert not pat.search(source), f"dangerous construct {pat.pattern!r} found"

    for match in _YAML_LOAD.finditer(source):
        # yaml.load is only safe when an explicit SafeLoader is passed.
        call_tail = source[match.start() : match.start() + 120]
        assert "SafeLoader" in call_tail, "yaml.load without SafeLoader found"
