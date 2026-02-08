#!/usr/bin/env python3
"""
ComfyUI Toolchain - Interactive Setup Wizard

Stdlib-only interactive setup for the ComfyUI Toolchain monorepo.
No pip dependencies required to run this script.

Usage:
    python setup_wizard.py          # Full interactive setup
    python setup_wizard.py --check  # Environment check only (no changes)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

_COLOR_SUPPORT = None


def _supports_color():
    global _COLOR_SUPPORT
    if _COLOR_SUPPORT is not None:
        return _COLOR_SUPPORT

    if os.environ.get("NO_COLOR"):
        _COLOR_SUPPORT = False
        return False

    if sys.platform == "win32":
        # Enable ANSI on Windows 10+ by setting console mode
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # STD_OUTPUT_HANDLE = -11
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            _COLOR_SUPPORT = True
        except Exception:
            _COLOR_SUPPORT = False
    else:
        _COLOR_SUPPORT = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    return _COLOR_SUPPORT


def _c(code, text):
    """Wrap *text* in ANSI escape if the terminal supports it."""
    if _supports_color():
        return f"\033[{code}m{text}\033[0m"
    return text


def bold(text):
    return _c("1", text)


def green(text):
    return _c("32", text)


def red(text):
    return _c("31", text)


def yellow(text):
    return _c("33", text)


def cyan(text):
    return _c("36", text)


def dim(text):
    return _c("2", text)


PASS = green("[PASS]")
FAIL = red("[FAIL]")
WARN = yellow("[WARN]")
INFO = cyan("[INFO]")
SKIP = dim("[SKIP]")


def header(title):
    width = 60
    border = "=" * width
    print()
    print(bold(border))
    print(bold(f"  {title}"))
    print(bold(border))


def step_header(number, title):
    print()
    print(bold(f"--- Step {number}: {title} ---"))


def prompt_input(question, default=None):
    """Ask user for input with an optional default value."""
    if default:
        suffix = f" [{default}]: "
    else:
        suffix = ": "
    try:
        answer = input(f"  {question}{suffix}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default or ""
    return answer if answer else (default or "")


def prompt_yes_no(question, default=True):
    """Ask a yes/no question. Returns bool."""
    hint = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"  {question} {hint}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not answer:
        return default
    return answer in ("y", "yes")


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

class Results:
    """Collects pass/fail/skip results for the final summary."""

    def __init__(self):
        self._items = []

    def add(self, name, status, detail=""):
        """status: 'pass', 'fail', 'warn', 'skip'"""
        self._items.append((name, status, detail))

    def print_summary(self):
        header("Summary")
        name_width = max((len(n) for n, _, _ in self._items), default=20)
        for name, status, detail in self._items:
            tag = {"pass": PASS, "fail": FAIL, "warn": WARN, "skip": SKIP}.get(
                status, INFO
            )
            line = f"  {tag} {name:<{name_width}}"
            if detail:
                line += f"  {dim(detail)}"
            print(line)
        print()

    @property
    def has_failures(self):
        return any(s == "fail" for _, s, _ in self._items)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent


def http_get_json(url, timeout=5):
    """GET *url*, return parsed JSON or None on any error."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def run_pip(args, label=None):
    """Run a pip command, return (success, output)."""
    cmd = [sys.executable, "-m", "pip"] + args
    label = label or " ".join(args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Timed out"
    except Exception as exc:
        return False, str(exc)


def run_python_snippet(code, label=""):
    """Run a short Python snippet, return (success, output)."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Step 1: Python version
# ---------------------------------------------------------------------------

def check_python(results):
    step_header(1, "Python Version")
    ver = sys.version_info
    version_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    if ver >= (3, 10):
        print(f"  {PASS} Python {version_str}")
        results.add("Python >= 3.10", "pass", version_str)
    else:
        print(f"  {FAIL} Python {version_str} -- 3.10+ required")
        results.add("Python >= 3.10", "fail", version_str)


# ---------------------------------------------------------------------------
# Step 2: Detect ComfyUI
# ---------------------------------------------------------------------------

def detect_comfyui(results):
    step_header(2, "Detect ComfyUI")
    url = "http://localhost:8188/system_stats"
    data = http_get_json(url)
    if data:
        print(f"  {PASS} ComfyUI detected at localhost:8188")
        results.add("ComfyUI", "pass", "running")
    else:
        print(f"  {WARN} ComfyUI not detected (GET {url} failed)")
        print(f"       Not fatal -- you can set the URL later.")
        results.add("ComfyUI", "warn", "not running")


# ---------------------------------------------------------------------------
# Step 3: Detect Ollama
# ---------------------------------------------------------------------------

def detect_ollama(results):
    step_header(3, "Detect Ollama")
    url = "http://localhost:11434/api/tags"
    data = http_get_json(url)
    if data:
        models = [m.get("name", "?") for m in data.get("models", [])]
        detail = f"{len(models)} model(s)" if models else "running, no models"
        print(f"  {PASS} Ollama detected at localhost:11434 -- {detail}")
        results.add("Ollama", "pass", detail)
    else:
        print(f"  {WARN} Ollama not detected (GET {url} failed)")
        print(f"       Not fatal -- you can set the URL later.")
        results.add("Ollama", "warn", "not running")


# ---------------------------------------------------------------------------
# Step 4: Install packages
# ---------------------------------------------------------------------------

def install_packages(results):
    step_header(4, "Install Packages")

    # Suggest venv if not already in one
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        print(f"  {WARN} You are not inside a virtual environment.")
        print(f"       It is recommended to create one first:")
        print(f"         python -m venv .venv")
        if sys.platform == "win32":
            print(f"         .venv\\Scripts\\activate")
        else:
            print(f"         source .venv/bin/activate")
        print()
        if not prompt_yes_no("Continue installing into current Python anyway?", default=False):
            print(f"  {SKIP} Package installation skipped.")
            results.add("Install packages", "skip", "no venv")
            return

    packages = [
        ("SDK", ["install", "-e", str(ROOT / "packages" / "sdk") + "/"]),
        ("MCP Server", ["install", "-e", str(ROOT / "packages" / "mcp-server") + "/"]),
        ("Prompter", ["install", "-e", str(ROOT / "packages" / "prompter") + "/"]),
        ("Dev extras", ["install", "-e", str(ROOT) + "[dev]"]),
    ]

    all_ok = True
    for label, pip_args in packages:
        print(f"  Installing {label}...", end=" ", flush=True)
        ok, output = run_pip(pip_args, label)
        if ok:
            print(green("OK"))
        else:
            print(red("FAILED"))
            # Show last meaningful line of output
            for line in output.strip().splitlines()[-3:]:
                print(f"    {dim(line)}")
            all_ok = False

    if all_ok:
        results.add("Install packages", "pass")
    else:
        results.add("Install packages", "fail", "see errors above")


# ---------------------------------------------------------------------------
# Step 5: Generate .env
# ---------------------------------------------------------------------------

def generate_env(results):
    step_header(5, "Generate .env")

    env_path = ROOT / ".env"
    if env_path.exists():
        print(f"  {INFO} .env already exists at {env_path}")
        if not prompt_yes_no("Overwrite it?", default=False):
            print(f"  {SKIP} Keeping existing .env")
            results.add(".env file", "skip", "already exists")
            return

    comfyui_url = prompt_input("ComfyUI URL", default="http://localhost:8188")
    ollama_url = prompt_input("Ollama URL", default="http://localhost:11434")

    content = textwrap.dedent(f"""\
        # ComfyUI Toolchain - Environment Configuration
        # Generated by setup_wizard.py

        # ComfyUI server URL
        COMFYUI_URL={comfyui_url}

        # Ollama server URL
        OLLAMA_URL={ollama_url}
    """)

    try:
        env_path.write_text(content, encoding="utf-8")
        print(f"  {PASS} Wrote {env_path}")
        results.add(".env file", "pass", str(env_path))
    except OSError as exc:
        print(f"  {FAIL} Could not write .env: {exc}")
        results.add(".env file", "fail", str(exc))


# ---------------------------------------------------------------------------
# Step 6: Credential setup
# ---------------------------------------------------------------------------

def setup_credentials(results):
    step_header(6, "Credential Setup (optional)")

    # Check if keyring is available
    keyring_available = False
    try:
        import importlib
        importlib.import_module("keyring")
        keyring_available = True
    except ImportError:
        pass

    if not keyring_available:
        print(f"  {WARN} keyring package not available.")
        print(f"       Install it with: pip install keyring")
        print(f"       Skipping credential storage.")
        results.add("Credentials", "skip", "keyring not installed")
        return

    import keyring as kr

    stored_any = False

    # HuggingFace token
    if prompt_yes_no("Store a HuggingFace token?", default=False):
        token = prompt_input("HuggingFace token (hf_...)")
        if token:
            try:
                kr.set_password("comfyui-toolchain", "huggingface_token", token)
                print(f"  {PASS} HuggingFace token stored in keyring.")
                stored_any = True
            except Exception as exc:
                print(f"  {FAIL} Could not store token: {exc}")

    # CivitAI API key
    if prompt_yes_no("Store a CivitAI API key?", default=False):
        key = prompt_input("CivitAI API key")
        if key:
            try:
                kr.set_password("comfyui-toolchain", "civitai_api_key", key)
                print(f"  {PASS} CivitAI API key stored in keyring.")
                stored_any = True
            except Exception as exc:
                print(f"  {FAIL} Could not store key: {exc}")

    if stored_any:
        results.add("Credentials", "pass", "stored in keyring")
    else:
        results.add("Credentials", "skip", "none stored")


# ---------------------------------------------------------------------------
# Step 7: Smoke tests
# ---------------------------------------------------------------------------

def smoke_tests(results):
    step_header(7, "Smoke Tests")

    tests = [
        (
            "SDK import",
            "from comfyui_agent_sdk.client import ComfyUIClient; print('SDK OK')",
        ),
        (
            "Assets import",
            "from comfyui_agent_sdk.assets import AssetRegistry; print('Assets OK')",
        ),
    ]

    all_ok = True
    for label, code in tests:
        ok, output = run_python_snippet(code, label)
        if ok:
            print(f"  {PASS} {label}")
        else:
            print(f"  {FAIL} {label}")
            for line in output.splitlines()[-2:]:
                print(f"    {dim(line)}")
            all_ok = False

    if all_ok:
        results.add("Smoke tests", "pass")
    else:
        results.add("Smoke tests", "fail", "see errors above")


# ---------------------------------------------------------------------------
# Step 8: Next steps
# ---------------------------------------------------------------------------

def print_next_steps():
    step_header(8, "Next Steps")

    print(textwrap.dedent("""\
      Start the MCP server:
        comfyui-mcp
        python packages/mcp-server/server.py

      Start the GUI:
        comfyui-gui
        python packages/prompter/main.py

      Start the API server:
        comfyui-api
        python packages/prompter/api_server.py

      MCP client configuration (e.g. for Claude Desktop):
    """))

    mcp_config = {
        "mcpServers": {
            "comfyui": {
                "command": "comfyui-mcp",
                "env": {
                    "COMFYUI_URL": "http://localhost:8188",
                },
            }
        }
    }
    print(f"    {json.dumps(mcp_config, indent=2)}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ComfyUI Toolchain setup wizard",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Environment check only (no changes)",
    )
    args = parser.parse_args()

    header("ComfyUI Toolchain Setup Wizard")
    if args.check:
        print(f"  Mode: {bold('check only')} (no changes will be made)")
    else:
        print(f"  Mode: {bold('full interactive setup')}")

    results = Results()

    # Steps 1-3 always run
    check_python(results)
    detect_comfyui(results)
    detect_ollama(results)

    if args.check:
        results.print_summary()
        sys.exit(1 if results.has_failures else 0)

    # Steps 4-7 only in full mode
    install_packages(results)
    generate_env(results)
    setup_credentials(results)
    smoke_tests(results)
    print_next_steps()

    results.print_summary()
    sys.exit(1 if results.has_failures else 0)


if __name__ == "__main__":
    main()
