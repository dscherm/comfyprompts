# Public API

Curated surface documentation for blind-TDD gated tasks. The blind test
writer's only view of the codebase beyond the task spec and `tests/`.

## tools/security/filename_guard.py

Validation for user-supplied asset/kit names before they become output
filenames (under `products/` and `output/`). Nothing here exists yet — it is
the surface the current gated task adds.

```
safe_filename(name: str, max_length: int = 128) -> str
```

Returns `name` unchanged when it is a safe filename; raises `ValueError`
otherwise. There is no sanitize-and-continue mode: an unsafe name is an
error, never silently rewritten.

### Import convention

Nothing in this repo is pip-installed (`pyproject.toml` has `packages = []`).
Tests load modules by file path, mirroring `tests/test_kitlib.py`:

```python
import importlib.util
from pathlib import Path

_MOD = Path(__file__).resolve().parents[2] / "tools" / "security" / "filename_guard.py"
spec = importlib.util.spec_from_file_location("filename_guard", _MOD)
filename_guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filename_guard)  # raises FileNotFoundError until implemented
```

(`parents[2]` from a test in `tests/contracts/`.)
