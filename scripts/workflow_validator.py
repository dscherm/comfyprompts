"""Validate ComfyUI API-format workflow JSON files.

Validates structure (graph integrity, link references) offline, and optionally
validates node classes, required inputs, types, and enum values against a live
ComfyUI server's /object_info or a cached copy.

Designed as the deterministic backbone for agent-driven workflow authoring:
an agent drafts a workflow, this script proves it will load before anything
is queued on the GPU.

Stdlib only — runs with any Python 3.10+, no venv required.

Usage:
    # Structural checks only (no ComfyUI needed)
    python workflow_validator.py path/to/workflow.json

    # Full validation against live ComfyUI
    python workflow_validator.py workflow.json --url http://localhost:8188

    # Fetch and cache object_info for offline use
    python workflow_validator.py --fetch --url http://localhost:8188

    # Full validation against cached object_info
    python workflow_validator.py workflow.json --object-info scripts/cache/object_info.json

    # Validate every workflow in a directory
    python workflow_validator.py workflows/mcp --object-info scripts/cache/object_info.json

Exit codes: 0 = all valid, 1 = errors found, 2 = usage/IO error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_CACHE = Path(__file__).resolve().parent / "cache" / "object_info.json"
PARAM_RE = re.compile(r"PARAM_[A-Z0-9_]+")

# Type names ComfyUI uses for primitive widget inputs.
PRIMITIVE_TYPES = {"INT", "FLOAT", "STRING", "BOOLEAN"}

MODEL_FILE_EXTS = (".safetensors", ".ckpt", ".pth", ".pt", ".sft", ".gguf", ".bin", ".onnx")


def looks_like_model_ref(value: object) -> bool:
    """True if a value appears to name a model file (downloadable asset)."""
    return isinstance(value, str) and (
        value.lower().endswith(MODEL_FILE_EXTS) or "/" in value or "\\" in value
    )


class Report:
    """Collects errors and warnings for one workflow file."""

    def __init__(self, label: str):
        self.label = label
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.params: set[str] = set()
        # Set when the .meta.json sidecar declares a requires_download block:
        # missing models/nodes are then documented gaps, not validation failures.
        self.deferred_download = False

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def deferrable_error(self, msg: str) -> None:
        """Error that downgrades to a warning when requires_download is declared."""
        if self.deferred_download:
            self.warnings.append(f"(deferred download) {msg}")
        else:
            self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self, verbose: bool = False) -> str:
        lines = [f"{'PASS' if self.ok else 'FAIL'}  {self.label}"]
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  warn:  {w}")
        if verbose and self.params:
            lines.append(f"  params: {', '.join(sorted(self.params))}")
        return "\n".join(lines)


def fetch_object_info(url: str, cache_path: Path) -> dict:
    """Fetch /object_info from a running ComfyUI and cache it to disk."""
    endpoint = url.rstrip("/") + "/object_info"
    with urllib.request.urlopen(endpoint, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data), encoding="utf-8")
    return data


def load_object_info(args: argparse.Namespace) -> dict | None:
    """Resolve object_info from --url (live), --object-info (file), or None."""
    if args.url:
        try:
            return fetch_object_info(args.url, DEFAULT_CACHE)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            print(f"warning: could not fetch object_info from {args.url}: {e}", file=sys.stderr)
            if DEFAULT_CACHE.exists():
                print(f"warning: falling back to cache {DEFAULT_CACHE}", file=sys.stderr)
                return json.loads(DEFAULT_CACHE.read_text(encoding="utf-8"))
            return None
    if args.object_info:
        path = Path(args.object_info)
        if not path.exists():
            print(f"error: object_info file not found: {path}", file=sys.stderr)
            sys.exit(2)
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def is_link(value: object) -> bool:
    """A node link is [node_id, output_index]."""
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], (str, int))
        and isinstance(value[1], int)
    )


def is_param(value: object) -> bool:
    return isinstance(value, str) and bool(PARAM_RE.fullmatch(value.strip()))


def input_spec_entries(node_info: dict) -> dict[str, tuple[object, bool]]:
    """Flatten object_info input spec to {input_name: (type_spec, required)}."""
    entries: dict[str, tuple[object, bool]] = {}
    spec = node_info.get("input", {})
    for section, required in (("required", True), ("optional", False)):
        for name, type_spec in spec.get(section, {}).items():
            entries[name] = (type_spec, required)
    return entries


def has_default(type_spec: object) -> bool:
    """True if the input spec carries a default value (so omission is safe)."""
    return (
        isinstance(type_spec, (list, tuple))
        and len(type_spec) > 1
        and isinstance(type_spec[1], dict)
        and "default" in type_spec[1]
    )


def check_value_against_spec(name: str, value: object, type_spec: object, report: Report) -> None:
    """Validate a widget (non-link) value against its object_info type spec."""
    if isinstance(value, str) and is_param(value):
        report.params.add(value.strip())
        return
    if isinstance(value, str) and PARAM_RE.search(value):
        # Embedded placeholder inside a longer string (e.g. filename prefix)
        report.params.update(PARAM_RE.findall(value))
        return

    base = type_spec[0] if isinstance(type_spec, (list, tuple)) and type_spec else type_spec

    if isinstance(base, list):
        # Combo/enum input — value must be one of the listed options
        if base and value not in base:
            preview = ", ".join(str(v) for v in base[:5])
            msg = (
                f"input '{name}': value {value!r} not in allowed options "
                f"[{preview}{', ...' if len(base) > 5 else ''}] ({len(base)} options)"
            )
            # Missing model files are deferrable; bad non-model enum values are not
            if looks_like_model_ref(value) or any(looks_like_model_ref(o) for o in base[:3]):
                report.deferrable_error(msg)
            else:
                report.error(msg)
        return

    if base == "INT" and not isinstance(value, int):
        report.error(f"input '{name}': expected INT, got {type(value).__name__} ({value!r})")
    elif base == "FLOAT" and not isinstance(value, (int, float)):
        report.error(f"input '{name}': expected FLOAT, got {type(value).__name__} ({value!r})")
    elif base == "STRING" and not isinstance(value, str):
        report.error(f"input '{name}': expected STRING, got {type(value).__name__} ({value!r})")
    elif base == "BOOLEAN" and not isinstance(value, bool):
        report.error(f"input '{name}': expected BOOLEAN, got {type(value).__name__} ({value!r})")


def validate_workflow(path: Path, object_info: dict | None) -> Report:
    report = Report(str(path))

    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        report.error(f"cannot parse JSON: {e}")
        return report

    if not isinstance(workflow, dict) or not workflow:
        report.error("workflow must be a non-empty JSON object (API format, not UI format)")
        return report

    if "nodes" in workflow and "links" in workflow:
        report.error(
            "this is UI-format JSON (has 'nodes'/'links'); export with "
            "'Save (API Format)' or convert before validating"
        )
        return report

    # Keys starting with "_" are comment entries by convention, not nodes
    workflow = {k: v for k, v in workflow.items() if not k.startswith("_")}

    # Pass 1: structural — every node well-formed, every link resolvable
    for node_id, node in workflow.items():
        prefix = f"node {node_id}"
        if not isinstance(node, dict):
            report.error(f"{prefix}: must be an object")
            continue
        class_type = node.get("class_type")
        if not class_type or not isinstance(class_type, str):
            report.error(f"{prefix}: missing 'class_type'")
            continue
        inputs = node.get("inputs")
        if inputs is None:
            report.warn(f"{prefix} ({class_type}): no 'inputs' key")
            inputs = {}
        if not isinstance(inputs, dict):
            report.error(f"{prefix} ({class_type}): 'inputs' must be an object")
            continue

        for in_name, value in inputs.items():
            if is_link(value):
                src_id = str(value[0])
                if src_id not in workflow:
                    report.error(
                        f"{prefix} ({class_type}): input '{in_name}' links to "
                        f"missing node '{src_id}'"
                    )
            elif isinstance(value, str) and is_param(value):
                report.params.add(value.strip())

    if report.errors:
        return report  # structural failures make deeper checks meaningless

    # Pass 2: graph sanity — cycles
    _check_cycles(workflow, report)

    # A sidecar requires_download block marks missing models/nodes as documented
    # gaps (warnings) rather than failures — workflow is valid once assets arrive
    meta_path = path.parent / (path.stem + ".meta.json")
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
            report.deferred_download = bool(meta.get("requires_download"))
        except (json.JSONDecodeError, OSError):
            pass  # sidecar parse errors reported in pass 4

    # Pass 3: schema validation against object_info
    if object_info is not None:
        _check_against_object_info(workflow, object_info, report)

    # Pass 4: meta.json sidecar consistency
    _check_meta_sidecar(path, report)

    return report


def _check_cycles(workflow: dict, report: Report) -> None:
    edges: dict[str, list[str]] = {nid: [] for nid in workflow}
    for node_id, node in workflow.items():
        for value in node.get("inputs", {}).values():
            if is_link(value):
                edges[node_id].append(str(value[0]))

    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(workflow, WHITE)

    def visit(nid: str, stack: list[str]) -> bool:
        color[nid] = GRAY
        for dep in edges.get(nid, []):
            if color.get(dep) == GRAY:
                report.error(f"cycle detected: {' -> '.join(stack + [nid, dep])}")
                return True
            if color.get(dep) == WHITE and visit(dep, stack + [nid]):
                return True
        color[nid] = BLACK
        return False

    for nid in workflow:
        if color[nid] == WHITE and visit(nid, []):
            return


def _check_against_object_info(workflow: dict, object_info: dict, report: Report) -> None:
    for node_id, node in workflow.items():
        class_type = node["class_type"]
        prefix = f"node {node_id} ({class_type})"
        node_info = object_info.get(class_type)
        if node_info is None:
            report.deferrable_error(
                f"{prefix}: node class not installed on this ComfyUI "
                "(check custom_nodes or fix the class name)"
            )
            continue

        spec = input_spec_entries(node_info)
        inputs = node.get("inputs", {})

        # Unknown inputs
        for in_name in inputs:
            if in_name not in spec:
                report.warn(f"{prefix}: input '{in_name}' not in node spec (may be ignored)")

        # Missing required inputs. ComfyUI's API validation demands every
        # required input be present — spec defaults are a UI affordance only
        for in_name, (type_spec, required) in spec.items():
            if required and in_name not in inputs:
                hint = ""
                if has_default(type_spec) and isinstance(type_spec, (list, tuple)):
                    hint = f" (spec default: {type_spec[1]['default']!r})"
                report.error(f"{prefix}: missing required input '{in_name}'{hint}")

        # Value/type/enum checks and link output validation
        outputs_by_node = {nid: n_info for nid, n_info in workflow.items()}
        for in_name, value in inputs.items():
            if in_name not in spec:
                continue
            type_spec, _ = spec[in_name]
            if is_link(value):
                src_id, out_idx = str(value[0]), value[1]
                src_class = outputs_by_node[src_id]["class_type"]
                src_info = object_info.get(src_class)
                if src_info is None:
                    continue  # already reported above
                src_outputs = src_info.get("output", [])
                if out_idx >= len(src_outputs):
                    report.error(
                        f"{prefix}: input '{in_name}' links to {src_class} output "
                        f"{out_idx}, but it only has {len(src_outputs)} outputs"
                    )
                    continue
                expected = type_spec[0] if isinstance(type_spec, (list, tuple)) else type_spec
                actual = src_outputs[out_idx]
                if (
                    isinstance(expected, str)
                    and expected not in PRIMITIVE_TYPES
                    and expected != "*"
                    and actual != "*"
                    and actual != expected
                ):
                    report.error(
                        f"{prefix}: input '{in_name}' expects type {expected} but "
                        f"{src_class} output {out_idx} produces {actual}"
                    )
            else:
                check_value_against_spec(in_name, value, type_spec, report)


def _check_meta_sidecar(path: Path, report: Report) -> None:
    meta_path = path.parent / (path.stem + ".meta.json")
    if not meta_path.exists():
        if report.params:
            report.warn(f"has PARAM_* placeholders but no sidecar {meta_path.name}")
        return
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError) as e:
        report.error(f"sidecar {meta_path.name} is not valid JSON: {e}")
        return

    declared: set[str] = set()
    params_section = meta.get("parameters", {})
    if isinstance(params_section, dict):
        declared = set(params_section.keys())
    elif isinstance(params_section, list):
        declared = {p.get("name", "") for p in params_section if isinstance(p, dict)}

    def normalize(name: str) -> str:
        """PARAM_STR_IMAGE_PATH, PARAM_IMAGE_PATH, image_path → IMAGE_PATH."""
        n = name.upper()
        n = n.removeprefix("PARAM_")
        for hint in ("STR_", "STRING_", "TEXT_", "INT_", "FLOAT_", "BOOL_"):
            n = n.removeprefix(hint)
        return n

    normalized_declared = {normalize(d) for d in declared}
    found = {normalize(p) for p in report.params}
    undeclared = found - normalized_declared
    if undeclared and declared:
        report.warn(
            f"placeholders not declared in {meta_path.name}: {', '.join(sorted(undeclared))}"
        )
    # Params referenced by a prompt_template ({name} syntax) are consumed by the
    # tool layer when composing PARAM_PROMPT — not unused
    template = meta.get("prompt_template", "")
    template_refs = (
        {normalize(m) for m in re.findall(r"\{(\w+)\}", template)}
        if isinstance(template, str)
        else set()
    )
    unused = normalized_declared - found - template_refs
    if unused and report.params:
        report.warn(f"declared in {meta_path.name} but unused: {', '.join(sorted(unused))}")


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("paths", nargs="*", help="workflow JSON file(s) or directory")
    parser.add_argument("--url", help="live ComfyUI URL to fetch object_info from")
    parser.add_argument("--object-info", help="path to cached object_info JSON")
    parser.add_argument("--fetch", action="store_true", help="fetch+cache object_info and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="show PARAM_* found")
    args = parser.parse_args()

    if args.fetch:
        url = args.url or "http://localhost:8188"
        data = fetch_object_info(url, DEFAULT_CACHE)
        print(f"cached {len(data)} node classes to {DEFAULT_CACHE}")
        return 0

    if not args.paths:
        parser.print_usage()
        return 2

    object_info = load_object_info(args)
    if object_info is None:
        print("note: no object_info — structural checks only", file=sys.stderr)

    files: list[Path] = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(
                f for f in sorted(p.glob("*.json")) if not f.name.endswith(".meta.json")
            )
        elif p.exists():
            if not p.name.endswith(".meta.json"):
                files.append(p)
        else:
            print(f"error: not found: {p}", file=sys.stderr)
            return 2

    failed = 0
    for f in files:
        report = validate_workflow(f, object_info)
        print(report.render(verbose=args.verbose))
        if not report.ok:
            failed += 1

    total = len(files)
    print(f"\n{total - failed}/{total} workflows valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
