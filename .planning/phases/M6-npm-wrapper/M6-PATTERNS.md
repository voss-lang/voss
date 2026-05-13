# Phase M6: npm Wrapper - Pattern Map

**Mapped:** 2026-05-13
**Files analyzed:** 12 new/modified files
**Analogs found:** 7 / 12 (5 greenfield — no in-repo analog exists)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `npm/package.json` | config (npm metadata) | static | none in-repo | none — external ref |
| `npm/bin/voss.js` | utility (bin shim) | request-response | none in-repo | none — external ref (Biome) |
| `npm/platforms/*/package.json` (×5) | config (npm metadata) | static | none in-repo | none — external ref |
| `npm/scripts/bump_version.py` | utility (release helper) | transform | `scripts/dump_python_plan_schema.py` | partial (same script role, json I/O) |
| `npm/scripts/prune_pbs.py` | utility (release helper) | file-I/O | `voss/cli.py` (`_write_text_atomic`) | partial (pathlib/subprocess, same Python script shape) |
| `npm/scripts/build_platform.py` | utility (release helper) | batch | `tests/packaging/test_wheel_install.py` (`_build_wheel`) | role-match (subprocess orchestration) |
| `.github/workflows/release.yml` (new) | config (CI workflow) | batch | `.github/workflows/ci.yml` | role-match (GHA workflow, matrix build) |
| `.github/workflows/release.yml` (old, DELETE) | — | — | n/a — delete entirely | — |
| `.github/workflows/rust.yml` (disable/delete) | — | — | n/a — freeze | — |
| `tests/packaging/test_npm_install.py` | test | batch | `tests/packaging/test_wheel_install.py` | exact (same file, same markers, same subprocess pattern) |
| `tests/packaging/test_readme.py` (extend) | test | transform | `tests/packaging/test_readme.py` | exact (same file, add one assertion) |
| `README.md` (modify) | docs | static | `README.md` (existing) | exact (in-place edit) |

---

## Pattern Assignments

### `npm/package.json` (config, static)

**Analog:** None in-repo. Mirror the esbuild main-package shape from RESEARCH.md §2.

**No code excerpt available from this codebase.** Use the pattern documented in RESEARCH.md §2 verbatim:

```json
{
  "name": "@voss/cli",
  "version": "0.1.0",
  "description": "Voss AI coding harness",
  "bin": { "voss": "bin/voss.js" },
  "optionalDependencies": {
    "@voss/cli-darwin-arm64": "0.1.0",
    "@voss/cli-darwin-x64": "0.1.0",
    "@voss/cli-linux-x64": "0.1.0",
    "@voss/cli-linux-arm64": "0.1.0",
    "@voss/cli-win32-x64": "0.1.0"
  },
  "engines": { "node": ">=18" }
}
```

**M6 differs from esbuild** in that the package name is `@voss/cli` (scoped, because `voss` is taken on npm). The `bin` entry must be `"voss"` so `npx @voss/cli` dispatches as `voss` on PATH.

---

### `npm/bin/voss.js` (utility, request-response)

**Analog:** None in-repo. Mirror the Biome shim pattern from RESEARCH.md §6.

**No code excerpt available from this codebase.** The full ~50 LOC shim is documented in RESEARCH.md §6 and should be copied from there. Key structural points:

- `require('child_process').spawnSync` with `stdio: 'inherit'` and `shell: false`
- Platform dispatch via `PLATFORMS[process.platform]?.[process.arch]`
- Python path branches on `process.platform === 'win32'`: `python/python.exe` vs `python/bin/python3`
- Exit code forwarding: `process.exitCode = result.status`
- Signal exit code: `process.exitCode = 128 + signalNums[result.signal]` on Unix
- Error guard: `if (result.error) throw result.error`

**M6 differs from Biome** in that it spawns Python (`pythonBin`) with `['-m', 'voss.cli', ...process.argv.slice(2)]` rather than a native binary. The platform-dispatch table also differs (5 triples vs Biome's binaries).

---

### `npm/platforms/*/package.json` (×5) (config, static)

**Analog:** None in-repo. Mirror the esbuild/Biome per-platform subpackage shape from RESEARCH.md §2.

```json
{
  "name": "@voss/cli-darwin-arm64",
  "version": "0.1.0",
  "os": ["darwin"],
  "cpu": ["arm64"],
  "files": ["python/"],
  "scripts": {
    "postinstall": "node -e \"const fs=require('fs'); const p=__dirname+'/python/bin/python3'; if(fs.existsSync(p)) fs.chmodSync(p, 0o755);\""
  }
}
```

The `os`/`cpu` values must exactly match Node's `process.platform` and `process.arch` strings. The `postinstall` chmod is a precaution (npm may strip execute bits — see RESEARCH.md §10, Open Question 3). Windows subpackage omits `postinstall` (no chmod on win32) and uses `"cpu": ["x64"]`, `"os": ["win32"]`.

---

### `npm/scripts/bump_version.py` (utility, transform)

**Analog:** `scripts/dump_python_plan_schema.py` (partial match — same script role, same `from __future__ import annotations` + `json` + stdlib pattern; no tomllib use there).

**Imports pattern** (`scripts/dump_python_plan_schema.py` lines 1-12):
```python
from __future__ import annotations

import json
import sys
```

**Core pattern for version-sync** (from RESEARCH.md §8 — no in-repo analog uses `tomllib`):
```python
import sys, json, tomllib, pathlib

ROOT = pathlib.Path(__file__).parent.parent.parent
PYPROJECT = ROOT / "pyproject.toml"
NPM_DIR = ROOT / "npm"

with open(PYPROJECT, "rb") as f:
    version = tomllib.load(f)["project"]["version"]
```

**JSON read-modify-write pattern** (mirror RESEARCH.md §8):
```python
def update_json(path: pathlib.Path, version: str) -> None:
    data = json.loads(path.read_text())
    data["version"] = version
    if "optionalDependencies" in data:
        for k in data["optionalDependencies"]:
            data["optionalDependencies"][k] = version
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Updated {path} -> {version}")
```

**M6 differs from `scripts/` analogs** in that it uses `tomllib` (stdlib since 3.11) and writes back to multiple `package.json` files rather than dumping JSON to stdout.

**pyproject.toml version field location** (`pyproject.toml` lines 6-7):
```toml
[project]
version = "0.1.0"
```
This is the single source of truth the script reads.

---

### `npm/scripts/prune_pbs.py` (utility, file-I/O)

**Analog:** `voss/cli.py` (partial — same Python script idiom, uses `pathlib.Path`, explicit error guards).

**Script structure pattern** (`voss/cli.py` lines 1-9, 65-80):
```python
from __future__ import annotations

import os
import tempfile
from pathlib import Path

def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(...)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
```

**M6 differs from `voss/cli.py`** in that `prune_pbs.py` uses `shutil.rmtree` / `Path.unlink` for directory removal, not atomic-write. The atomic-write idiom is not needed here — prune is destructive and idempotent. The relevant shared pattern is: accept a `Path` argument, guard with `path.exists()` before destructive ops, `path.mkdir(parents=True, exist_ok=True)` for output dirs.

**Prune targets** (RESEARCH.md §4 — no in-repo analog):
```python
import shutil, sys
from pathlib import Path

UNIX_PRUNE = [
    "include",
    "lib/python3.12/idlelib",
    "lib/python3.12/tkinter",
    "lib/python3.12/lib2to3",
    "lib/python3.12/ensurepip",
    "lib/python3.12/turtledemo",
    "share",
]
TCL_GLOBS = ["lib/itcl*", "lib/tcl*", "lib/tk*", "lib/thread*"]
UNIX_BIN_PRUNE = ["bin/2to3", "bin/2to3-3.12", "bin/idle3", "bin/idle3.12",
                  "bin/python3-config", "bin/python3.12-config"]
WIN_PRUNE = ["include", "Lib/idlelib", "Lib/tkinter", "Lib/lib2to3",
             "Lib/turtledemo", "tcl", "pythonw.exe"]
```

---

### `npm/scripts/build_platform.py` (utility, batch)

**Analog:** `tests/packaging/test_wheel_install.py` (role-match — subprocess orchestration, same `_build_wheel` / `_make_venv` helper pattern).

**Subprocess orchestration pattern** (`tests/packaging/test_wheel_install.py` lines 23-41):
```python
def _build_wheel(dist: Path) -> Path:
    """Build the repo wheel into `dist/` and return the wheel path."""
    dist.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(_repo_root())],
        check=True,
        timeout=600,
    )
    wheels = list(dist.glob("voss-*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    return wheels[0]
```

**Repo-root resolution pattern** (`tests/packaging/test_entrypoint.py` line 17):
```python
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
```

**Windows path branch pattern** (`tests/packaging/test_wheel_install.py` lines 51-54):
```python
py = venv_dir / "bin" / "python"
if not py.exists():
    py = venv_dir / "Scripts" / "python.exe"
```

**M6 differs** in that `build_platform.py` also downloads a PBS tarball via `urllib.request` or `curl` subprocess, runs the prune script, and invokes `pip install --no-cache-dir <wheel>` against the vendored Python (not `sys.executable`). It is an orchestration script run by CI, not a test helper.

---

### `.github/workflows/release.yml` (new) (config, batch)

**Analog:** `.github/workflows/ci.yml` (role-match — same GHA workflow with matrix build pattern).

**Trigger pattern** (`.github/workflows/ci.yml` lines 1-9):
```yaml
name: CI

permissions:
  contents: read

on:
  push:
  pull_request:
  workflow_dispatch:
```

**M6 release trigger differs** — fires only on `push: tags: ['v*']`, not on every push:
```yaml
on:
  push:
    tags: ['v*']
```

**Matrix strategy pattern** (`.github/workflows/ci.yml` lines 14-20):
```yaml
jobs:
  stub:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
```

**M6 differs from ci.yml** in that the matrix has named include rows (not a simple list), each specifying `runner`, `npm-platform`, `pbs-triple`, and `python-bin`. The full matrix and step sequence is documented in RESEARCH.md §7 and should be copied from there.

**Step ordering pattern** (mirror ci.yml `- uses: actions/checkout@v4` first):
All jobs begin with `actions/checkout@v4`. The release workflow adds `actions/setup-node@v4` with `registry-url: 'https://registry.npmjs.org'` before publish steps.

**Secret reference pattern** (ci.yml lines 48-50):
```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```
M6 uses: `NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}`

**Job dependency pattern** — release workflow adds `needs: build-platform` on the `publish-main` job (no analog in ci.yml which has no inter-job deps). This is standard GHA and is documented in RESEARCH.md §7.

---

### `.github/workflows/release.yml` (old) — DELETE

This is the cargo-dist workflow. It must be deleted entirely in M6-01, not modified. Content is confirmed dead (RESEARCH.md §11, §7). No patterns to extract.

---

### `.github/workflows/rust.yml` — DISABLE/DELETE

Runs `cargo build --workspace --release` + `cargo test --workspace` on every push to master/main. Since Rust is frozen, change trigger to `workflow_dispatch` only or delete. No patterns to extract — this is a configuration change, not a new file.

**Current trigger** (`.github/workflows/rust.yml` lines 2-5):
```yaml
on:
  push:
    branches: [master, main]
  pull_request:
    branches: [master, main]
```
Change to `on: workflow_dispatch:` to freeze it without deleting.

---

### `tests/packaging/test_npm_install.py` (test, batch)

**Analog:** `tests/packaging/test_wheel_install.py` — exact match. This new test file should mirror the structure of `test_wheel_install.py` line by line.

**Module docstring pattern** (`test_wheel_install.py` lines 1-10):
```python
"""M5 EVAL-05 / D-16: build wheel, install in temp venv, smoke the post-install
CLI surface.

These three tests prove the v0.1 wheel installs cleanly into a fresh, isolated
virtualenv ...  Marked `@pytest.mark.slow` because ...
"""
```
M6 version: `"""M6 NPM-04: pack @voss/cli, install via npm, smoke CLI surface via vendored Python. Marked @pytest.mark.slow ..."""`

**Imports pattern** (`test_wheel_install.py` lines 12-20):
```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.packaging.test_entrypoint import _repo_root
```

**`@pytest.mark.slow` test pattern** (`test_wheel_install.py` lines 64-69, 95-110):
```python
@pytest.mark.slow
def test_wheel_builds(tmp_path):
    """`python -m build --wheel` produces exactly one `voss-*.whl`."""
    dist = tmp_path / "dist"
    wheel = _build_wheel(dist)
    assert wheel.is_file()
```

```python
@pytest.mark.slow
def test_smoke_asserts(tmp_path):
    ...
    r = subprocess.run(
        [str(voss_bin), "--help"], capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0, r.stderr
```

**Doctor exit-code assertion pattern** (`test_wheel_install.py` lines 149-155):
```python
# voss doctor — exit ∈ {0, 1} per M1 D-13
r = subprocess.run(
    [str(voss_bin), "doctor"], capture_output=True, text=True, timeout=30
)
assert r.returncode in {0, 1}, f"voss doctor crashed: {r.stderr}"
```

**M6 differs from `test_wheel_install.py`** in these ways:
1. The invocation is `["node", str(voss_js), ...]` not `[str(voss_bin), ...]`
2. `voss_js` is resolved as `_repo_root() / "npm" / "bin" / "voss.js"` — no pip install path
3. The test skips via `pytest.skip` if `TEST_PBS_EXTRACT` env var is not set (the platform subpackage must be pre-built)
4. The `.voss` fixture is an inline string written to `tmp_path / "smoke.voss"` rather than using `samples/classify.voss` (wheel doesn't ship `samples/`)
5. No venv creation step — the vendored Python is inside the PBS extract

---

### `tests/packaging/test_readme.py` (extend existing file)

**Analog:** `tests/packaging/test_readme.py` itself — exact match. Add one new assertion function to the existing file.

**Existing assertion pattern** (`test_readme.py` lines 21-30):
```python
def test_pip_install_voss_present():
    assert "pip install voss" in _readme()


def test_voss_doctor_first_run_mentioned():
    assert "voss doctor" in _readme()
```

**New assertion to add** (NPM-05):
```python
def test_npm_install_voss_cli_present():
    assert "npm i -g @voss/cli" in _readme() or "npm install -g @voss/cli" in _readme()
```

**M6 also modifies** `test_pip_install_voss_present` — after the README update, `pip install voss` will be secondary. The test may need to weaken to `"pip install"` or be left as-is (the pip path remains documented, just secondary).

---

### `README.md` (modify)

**Analog:** `README.md` itself. Surgical in-place edit — add `npm i -g @voss/cli` as the primary install block above the existing `pip install voss` block. No structural changes to the rest of the file.

**No code excerpt needed.** The edit location is determined at implementation time by reading the current install section.

---

## Shared Patterns

### Python script header (all `npm/scripts/*.py`)

**Source:** `scripts/dump_python_plan_schema.py` lines 1-5 + `tests/packaging/test_entrypoint.py` lines 1-19
**Apply to:** `bump_version.py`, `prune_pbs.py`, `build_platform.py`

```python
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # adjust depth per file
```

All scripts use `Path(__file__).resolve().parents[N]` for repo-root resolution. Never use `os.getcwd()` — scripts may be called from any working directory by CI.

### subprocess with `check=True` + `timeout`

**Source:** `tests/packaging/test_wheel_install.py` lines 27-38
**Apply to:** `build_platform.py`, `test_npm_install.py`

```python
subprocess.run(
    [...],
    check=True,
    timeout=600,
)
```

Always pass `check=True` for build steps that must not silently fail. Always pass `timeout` to prevent CI hangs.

### `@pytest.mark.slow` marker

**Source:** `tests/packaging/test_wheel_install.py` lines 64, 72, 95; `pyproject.toml` lines 54-55
**Apply to:** All tests in `tests/packaging/test_npm_install.py`

```python
@pytest.mark.slow
def test_...(tmp_path):
```

The marker is registered in `pyproject.toml`:
```toml
markers = [
    "slow: takes > 1s",
]
```
No registration change needed. Do not use `@pytest.mark.integration` or any other marker — `slow` is the established convention for packaging tests in this repo.

### `_repo_root()` helper

**Source:** `tests/packaging/test_entrypoint.py` lines 17-18
**Apply to:** `test_npm_install.py`

```python
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
```

Import from `test_entrypoint` (already done in `test_wheel_install.py` line 20):
```python
from tests.packaging.test_entrypoint import _repo_root
```

### Windows path branch for Python binary

**Source:** `tests/packaging/test_wheel_install.py` lines 51-54
**Apply to:** `build_platform.py`, `npm/bin/voss.js`

Python pattern (build_platform.py):
```python
py = venv_dir / "bin" / "python"
if not py.exists():
    py = venv_dir / "Scripts" / "python.exe"
```

JS pattern (voss.js — from RESEARCH.md §6):
```js
const pythonBin = isWindows
  ? path.join(pkgDir, 'python', 'python.exe')
  : path.join(pkgDir, 'python', 'bin', 'python3');
```

### GHA `actions/checkout@v4` + `actions/setup-python@v5`

**Source:** `.github/workflows/ci.yml` lines 23-26
**Apply to:** `.github/workflows/release.yml` (new), all platform build jobs

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
```

Use `python-version: "3.12"` (not `${{ matrix.python-version }}`) in the release workflow — the version is pinned by D-05.

---

## No Analog Found

Files with no close match in the codebase — planner should use RESEARCH.md patterns instead:

| File | Role | Data Flow | Reason | External Reference |
|---|---|---|---|---|
| `npm/package.json` | config | static | No npm packages exist in repo | RESEARCH.md §2; esbuild npm page |
| `npm/bin/voss.js` | utility | request-response | No JS files exist in repo | RESEARCH.md §6; Biome shim GitHub source |
| `npm/platforms/*/package.json` (×5) | config | static | No npm packages exist in repo | RESEARCH.md §2; @esbuild/darwin-arm64 npm page |

For these three, the patterns in RESEARCH.md §2 and §6 are primary references. The planner should treat those sections as the functional equivalent of an analog excerpt.

---

## Metadata

**Analog search scope:** `scripts/`, `tests/packaging/`, `.github/workflows/`, `voss/cli.py`
**Files read:** 10
**Pattern extraction date:** 2026-05-13
