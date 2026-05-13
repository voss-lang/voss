# Phase M6: npm Wrapper - Research

**Researched:** 2026-05-13
**Domain:** npm package distribution with vendored Python interpreter (esbuild optionalDependencies pattern)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** esbuild-pattern optionalDependencies. Main `voss` package + 5 platform subpackages under `@voss/cli-<triple>`. All 5 listed as `optionalDependencies`; npm resolves exactly one at install time.
- **D-02:** Bin shim = Node.js JS at `npm/bin/voss.js` (~50 LOC). Spawns vendored `python -m voss.cli`, forwards argv/stdio/exit code/SIGINT/SIGTERM.
- **D-03:** Layout = `npm/` subdir at repo root. `npm/package.json`, `npm/bin/voss.js`, `npm/platforms/<triple>/`, `npm/scripts/`.
- **D-04:** Python runtime source = python-build-standalone (Astral/Indygreg).
- **D-05:** Python 3.12 pinned.
- **D-06:** CI downloads PBS tarballs once at release time; no download at install time.
- **D-07:** Light prune of vendored Python — drop `idlelib/`, `tkinter/`, `lib2to3/`, `ensurepip/`, `turtledemo/` before tarballing. Keep stdlib + pip.
- **D-08:** Build wheel in CI at npm-publish time; no PyPI dependency.
- **D-09:** Pre-install wheel into vendored Python's site-packages at publish time. Zero pip work at install time for end user.
- **D-10:** Single source of truth = `pyproject.toml`. Release script regenerates all `package.json` files.
- **D-11:** Full 5-platform matrix: `darwin-arm64`, `darwin-x64`, `linux-x64`, `linux-arm64`, `win32-x64`.
- **D-12:** Main package name = unscoped `voss`. Fallback: `@voss/cli` if taken.
- **D-13:** Platform subpackages = `@voss/cli-darwin-arm64`, `@voss/cli-darwin-x64`, `@voss/cli-linux-x64`, `@voss/cli-linux-arm64`, `@voss/cli-win32-x64`.
- **D-14:** Reserve npm names IMMEDIATELY as the first M6 task.

### Claude's Discretion

- Exact pruning pattern for the vendored Python (D-07 names targets; researcher refines rm-list based on actual PBS layout).
- Release CI provider shape (GitHub Actions is the obvious choice; researcher picks the exact workflow file shape).
- Wheel-SHA verification mechanism (manifest format, signature method).
- Signal-forwarding test approach for the JS shim.
- npm publish credentials handling (GitHub secret name, scope, npm org admin setup).

### Deferred Ideas (OUT OF SCOPE)

- PyPI publish — v0.1.1 candidate.
- Homebrew formula — DIST-02, deferred.
- Rust shell — frozen spike, do not touch.
- Signed wheels / sigstore — v0.1.1+ security work.
- Telemetry / install-failure detection.
- `npm install voss` without `-g` (project-local dep).
- `@voss/sdk` npm package.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NPM-01 | Package `voss` (or `@voss/cli`) publishable + installable via `npm i -g voss` / `npx voss` | Name conflict confirmed: `voss` is taken on npm; must use `@voss/cli`. `@voss/cli-*` subpackages are all available. See §NPM-01. |
| NPM-02 | Package vendors per-platform Python interpreter + voss wheel for 5 platforms via optionalDependencies | PBS 20260510 release confirmed for all 5 triples. install_only_stripped variant recommended. Layout verified. See §NPM-02. |
| NPM-03 | `voss` bin shim forwards all CLI argv to vendored `python -m voss.cli` preserving exit codes, stdio, signals | Biome shim pattern verified (`spawnSync` with `stdio: "inherit"`, `process.exitCode = result.status`). Windows signal semantics documented. See §NPM-03. |
| NPM-04 | Packaging smoke test verifies fresh Node project install + `npx voss` commands exit 0 | Recommend pytest `@pytest.mark.slow` test using `npm pack` + local install in tmpdir. Design documented. See §NPM-04. |
| NPM-05 | README primary install = `npm i -g voss`; `pip install voss` secondary; v0.1 framing preserved | Single README.md edit after names are reserved and published. See §NPM-05. |
</phase_requirements>

---

## Summary

M6 publishes the existing Python `voss` harness as an npm package by wrapping it in a Node.js JS shim that resolves to a vendored Python 3.12 interpreter (from python-build-standalone) with the v0.1 wheel pre-installed in site-packages. This is a pure distribution engineering phase — the Python code under `voss/`, `voss_runtime/`, and `voss/harness/` is entirely unchanged.

The pattern mirrors what esbuild, Biome, oxlint, and similar tools do: publish one "meta" npm package that lists 5 platform subpackages as `optionalDependencies`, letting npm's resolver automatically install exactly the right one for the target platform. Each platform subpackage is ~30-90MB (PBS interpreter + voss wheel + its C-extension deps) before prune. The JS shim in the main package resolves the local platform, finds the vendored Python, and invokes `python -m voss.cli` with full arg/stdio/exit-code forwarding.

**Critical blocker discovered in research:** The unscoped `voss` package name on npm.js is already taken by a React components library (published April 2023, maintainer `shawn_xu`). D-14 (reserve names as first M6 task) will find this conflict immediately. The fallback from D-12 applies: the main package must be `@voss/cli`. The `@voss` org and all 5 `@voss/cli-*` platform subpackage names are available as of 2026-05-13. D-12's fallback is now the operative decision.

**Primary recommendation:** Proceed with `@voss/cli` as the main package name and `@voss/cli-{platform}-{arch}` subpackages. Claim the `@voss` npm org in M6-01. The bin shim uses `spawnSync` with `stdio: "inherit"` (Biome pattern), which handles signal forwarding correctly on Unix. Windows needs a SIGINT workaround due to Win32 signal semantics.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Platform resolution | Node.js shim | — | `process.platform` + `process.arch` determine which subpackage was installed |
| Python interpreter | Platform subpackage (`@voss/cli-<platform>-<arch>`) | — | Each subpackage vendors a complete PBS extract per platform |
| Python dependency resolution | CI release runner (native per platform) | — | `pip install voss-wheel` on the CI runner's native arch installs correct C-extension wheels |
| CLI entry point | npm main package (`@voss/cli`) | — | `npm/bin/voss.js` is the registered `bin` entry |
| Voss wheel | CI build + platform subpackage | — | Wheel built in CI at tag time, vendored into each platform subpackage's site-packages |
| Version sync | `npm/scripts/` release helper | pyproject.toml (source of truth) | Script reads pyproject.toml, writes all package.json files |
| npm publish | GitHub Actions release workflow | — | One workflow replaces the cargo-dist `release.yml` |
| Smoke testing | pytest (`@pytest.mark.slow`) | — | Reuses existing test infrastructure via `npm pack` + local install |

---

## 1. npm Name Availability (NPM-01 / D-12 / D-14)

### Finding: `voss` is taken

`npm view voss` returns:

```
name: voss
latest: 0.1.1
maintainer: shawn_xu (272887214@qq.com)
description: React components library named voss
published: 2023-04-04
```

[VERIFIED: npm registry, 2026-05-13]

The package is inactive (no updates since April 2023, placeholder-quality README pointing to `github.com/xxx/xxx`), but it is not abandoned in the npm registry's sense — it has a published version. npm does not transfer squatted names automatically. Options:

1. **File a trademark/squatting claim with npm** — possible but takes weeks and requires documentation of prior use. Not suitable for M6 timeline.
2. **Use the D-12 fallback: `@voss/cli`** — available immediately. All `@voss/cli-*` subpackage names are also available. [VERIFIED: npm registry, 2026-05-13]

**Resolution:** D-12 fallback is now the operative decision. Main package = `@voss/cli`. Scoped packages always require `--access public` for `npm publish` (default is restricted for orgs).

### Available names confirmed

| npm name | Status |
|----------|--------|
| `voss` | TAKEN (React lib, shawn_xu) |
| `@voss/cli` | AVAILABLE |
| `@voss/cli-darwin-arm64` | AVAILABLE |
| `@voss/cli-darwin-x64` | AVAILABLE |
| `@voss/cli-linux-x64` | AVAILABLE |
| `@voss/cli-linux-arm64` | AVAILABLE |
| `@voss/cli-win32-x64` | AVAILABLE |

[VERIFIED: npm registry 404s for all @voss/* names, 2026-05-13]

### Org creation

Claiming `@voss/cli` requires creating the `@voss` npm organization. This is a manual step on npmjs.com (requires an npm account). Once the org exists, all `@voss/*` package names are automatically scoped to it and can be published with `NPM_TOKEN` from that org.

---

## 2. esbuild / Biome Pattern Analysis (NPM-01 / NPM-02)

### What the pattern looks like

[VERIFIED: npm registry + GitHub source, 2026-05-13]

#### Main package (`@voss/cli`) `package.json` keys

```json
{
  "name": "@voss/cli",
  "version": "0.1.0",
  "description": "Voss AI coding harness",
  "bin": {
    "voss": "bin/voss.js"
  },
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

#### Platform subpackage (`@voss/cli-darwin-arm64`) `package.json` keys

```json
{
  "name": "@voss/cli-darwin-arm64",
  "version": "0.1.0",
  "os": ["darwin"],
  "cpu": ["arm64"],
  "files": ["python/"]
}
```

The `os` + `cpu` fields are how npm's resolver selects which optional dependency to install. npm skips any optional dep where `os` or `cpu` doesn't match the install host.

#### Comparison: what they do vs. what we do

| Aspect | esbuild / Biome (Go native binary) | Voss (PBS Python + wheel) |
|--------|------------------------------------|-----------------------------|
| Platform subpackage content | Single ~4-10MB compiled binary | Full PBS Python tree ~20-90MB (post-prune) |
| Shim resolves | `require.resolve('@esbuild/darwin-arm64/bin/esbuild')` | `require.resolve('@voss/cli-darwin-arm64')` + path join to `python/bin/python3` |
| Shim invocation | `spawnSync(binaryPath, argv)` | `spawnSync(pythonPath, ['-m', 'voss.cli', ...argv])` |
| Install-time work | None | None (wheel pre-installed in site-packages) |
| Total install size | ~4-10MB | ~20-90MB per platform (see §3) |

---

## 3. python-build-standalone Release Selection (NPM-02 / D-04 / D-05)

### Recommended release and variant

**Tag:** `20260510` (latest stable as of research date)
**Python version:** `3.12.13`
**Variant:** `install_only_stripped` (not `install_only`)

[VERIFIED: GitHub releases API, astral-sh/python-build-standalone, 2026-05-13]

The `install_only_stripped` variant has dramatically smaller tarballs than `install_only` for Linux (32MB vs 105MB for linux-x64), with no functional difference for our use case (stripped debug symbols are not needed at runtime).

### Tarball sizes per platform

| npm/D-13 name | PBS triple | Tarball (stripped) | Post-extract (estimated) |
|---------------|------------|--------------------|--------------------------|
| `cli-darwin-arm64` | `aarch64-apple-darwin` | 23MB | ~96MB |
| `cli-darwin-x64` | `x86_64-apple-darwin` | 23MB | ~96MB |
| `cli-linux-x64` | `x86_64-unknown-linux-gnu` | 32MB | ~120MB |
| `cli-linux-arm64` | `aarch64-unknown-linux-gnu` | 27MB | ~100MB |
| `cli-win32-x64` | `x86_64-pc-windows-msvc` | 20MB | ~75MB |

[VERIFIED: GitHub releases API asset sizes, 2026-05-13]

**Note:** macOS stripped vs non-stripped are the same size (23MB) because macOS tarballs are always stripped by the dylib linker. Linux stripped saves ~70MB; Windows saves ~23MB.

### Tarball URLs (pinned to 20260510)

```
https://github.com/astral-sh/python-build-standalone/releases/download/20260510/cpython-3.12.13+20260510-aarch64-apple-darwin-install_only_stripped.tar.gz
https://github.com/astral-sh/python-build-standalone/releases/download/20260510/cpython-3.12.13+20260510-x86_64-apple-darwin-install_only_stripped.tar.gz
https://github.com/astral-sh/python-build-standalone/releases/download/20260510/cpython-3.12.13+20260510-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz
https://github.com/astral-sh/python-build-standalone/releases/download/20260510/cpython-3.12.13+20260510-aarch64-unknown-linux-gnu-install_only_stripped.tar.gz
https://github.com/astral-sh/python-build-standalone/releases/download/20260510/cpython-3.12.13+20260510-x86_64-pc-windows-msvc-install_only_stripped.tar.gz
```

---

## 4. PBS Post-Prune Layout

### Unix layout (darwin/linux) — verified against `aarch64-apple-darwin`

[VERIFIED: extracted and inspected live tarball, 2026-05-13]

```
python/
├── bin/
│   ├── python          # symlink -> python3
│   ├── python3         # the interpreter
│   ├── python3.12      # versioned
│   ├── pip, pip3, pip3.12   # already installed
│   ├── 2to3, 2to3-3.12      # PRUNE (bin symlinks to idlelib scripts)
│   ├── idle3, idle3.12      # PRUNE
│   ├── pydoc3, pydoc3.12    # PRUNE (optional, saves 1KB)
│   ├── python3-config        # PRUNE (only needed for C extension dev)
│   └── python3.12-config     # PRUNE
├── include/            # C headers — PRUNE (not needed for runtime)
├── lib/
│   ├── libpython3.12.dylib   # KEEP — needed for C extensions (chromadb etc)
│   ├── python3.12/
│   │   ├── site-packages/    # KEEP (pip here; voss wheel goes here)
│   │   ├── idlelib/          # PRUNE (1.1MB)
│   │   ├── tkinter/          # PRUNE (0.35MB)
│   │   ├── lib2to3/          # PRUNE (0.30MB)
│   │   ├── ensurepip/        # PRUNE — safe because pip already installed
│   │   ├── turtledemo/       # PRUNE (0.06MB)
│   │   └── [stdlib]          # KEEP everything else
│   ├── itcl4.3.5/     # PRUNE (Tcl extension, 0.61MB)
│   ├── tcl9/, tcl9.0/ # PRUNE (Tcl runtime, 2.11MB combined)
│   ├── tk9.0/         # PRUNE (Tk runtime, 0.77MB)
│   └── thread3.0.4/   # PRUNE (Tcl threading, 0.29MB)
└── share/             # PRUNE (man pages, 0.04MB)
```

**Why `ensurepip/` is safe to prune:** PBS `install_only` ships with pip already installed into `lib/python3.12/site-packages/` and `bin/pip*`. `ensurepip/` is only used to bootstrap pip into a fresh Python install from scratch — unnecessary here.

**Critical: do NOT prune `lib/libpython3.12.dylib`** (macOS) or `lib/libpython3.12.so.1.0` (Linux). All C extension modules (`chromadb`, `tiktoken`, `onnxruntime`) require it at runtime.

**Critical: do NOT prune `lib/python3.12/site-packages/`** — this is where pip lives (pre-PBS) and where the voss wheel will be installed.

### Unix prune script (shell, idempotent)

```bash
PYDIR="python"  # root of extracted PBS
rm -rf "$PYDIR/include"
rm -rf "$PYDIR/lib/python3.12/idlelib"
rm -rf "$PYDIR/lib/python3.12/tkinter"
rm -rf "$PYDIR/lib/python3.12/lib2to3"
rm -rf "$PYDIR/lib/python3.12/ensurepip"
rm -rf "$PYDIR/lib/python3.12/turtledemo"
rm -rf "$PYDIR/lib/itcl"* "$PYDIR/lib/tcl"* "$PYDIR/lib/tk"* "$PYDIR/lib/thread"*
rm -rf "$PYDIR/share"
# Bin symlinks for pruned tools (harmless but clean)
rm -f "$PYDIR/bin/2to3" "$PYDIR/bin/2to3-3.12"
rm -f "$PYDIR/bin/idle3" "$PYDIR/bin/idle3.12"
rm -f "$PYDIR/bin/python3-config" "$PYDIR/bin/python3.12-config"
```

Estimated prune savings: **~8-9MB per Unix platform** (from 96MB to ~87MB uncompressed).

### Windows layout (x86_64-pc-windows-msvc)

[VERIFIED: extracted and inspected live tarball, 2026-05-13]

```
python/
├── python.exe          # THE INTERPRETER (not bin/python3)
├── pythonw.exe         # PRUNE (Windows GUI launcher, not needed)
├── DLLs/               # KEEP — C extension PYDs (asyncio, ssl, ctypes, etc)
├── Lib/
│   ├── site-packages/  # KEEP (pip here; voss wheel goes here)
│   ├── idlelib/        # PRUNE (90 files)
│   ├── tkinter/        # PRUNE (14 files)
│   ├── lib2to3/        # PRUNE (75 files)
│   ├── turtledemo/     # PRUNE (22 files)
│   └── [stdlib]        # KEEP
├── Scripts/            # KEEP — pip.exe, voss console scripts here post-wheel-install
├── include/            # PRUNE (C headers)
├── libs/               # KEEP — python312.lib (needed for C ext linking)
├── tcl/                # PRUNE (Tcl/Tk support)
├── python3.dll         # KEEP — C runtime shared lib
├── python312.dll       # KEEP — C extension dependency
└── vcruntime140.dll    # KEEP — MSVC runtime
```

**Key Windows path difference:** The Python interpreter is at `python/python.exe`, NOT `python/bin/python3`. The bin shim must branch on `process.platform === 'win32'`.

**Windows Scripts/ directory:** After `pip install voss-wheel`, console scripts appear in `python/Scripts/voss.exe`. The shim does NOT use this path — it always invokes `python.exe -m voss.cli` for cross-platform consistency and to avoid depending on the console script symlink.

---

## 5. Wheel Pre-install Mechanics (NPM-02 / D-09)

### Command sequence (per platform, in CI)

```bash
# Unix
PYTHON="$PBS_EXTRACT_DIR/python/bin/python3"
WHEEL="dist/voss-0.1.0-py3-none-any.whl"
"$PYTHON" -m pip install --no-cache-dir "$WHEEL"

# Windows (PowerShell)
$PYTHON = "$PBS_EXTRACT_DIR\python\python.exe"
$WHEEL = "dist\voss-0.1.0-py3-none-any.whl"
& $PYTHON -m pip install --no-cache-dir $WHEEL
```

**Do NOT use `--target` or `--prefix`.** Using `pip install` without either installs into the interpreter's default `site-packages`, which is what we want (`python/lib/python3.12/site-packages/` on Unix, `python/Lib/site-packages/` on Windows). The interpreter already knows its own site-packages location.

**Do NOT use `--no-deps`.** Voss has 11 declared dependencies. All of them must be installed into the vendored site-packages.

### C-extension dependency matrix

[VERIFIED: PyPI JSON API, 2026-05-13]

| Dependency | Wheel type | linux-arm64 available? | Notes |
|------------|-----------|------------------------|-------|
| `chromadb` | Native (C extensions via onnxruntime) | Yes — `manylinux_2_17_aarch64` | Transitive dep on onnxruntime |
| `sentence-transformers` | Pure Python | N/A (py3-none-any) | No C extension in the package itself |
| `tiktoken` | Native (Rust extension) | Yes — `manylinux_2_28_aarch64` | Releases for all 5 targets |
| `onnxruntime` | Native | Yes — `manylinux_2_27_aarch64` | Required by chromadb; arm64 wheels exist for cp312 |
| `lark` | Pure Python | N/A | py3-none-any |
| `litellm` | Pure Python | N/A | py3-none-any |
| `pydantic` | Pure Python | N/A | py3-none-any (v2 core is Rust but pydantic ships as pure-py wrapper) |
| `anthropic` | Pure Python | N/A | py3-none-any |
| `openai` | Pure Python | N/A | py3-none-any |
| `click` | Pure Python | N/A | py3-none-any |
| `rich` | Pure Python | N/A | py3-none-any |
| `pyyaml` | Native | Yes — `manylinux` + `macosx` | Native for speed; pure-py fallback exists |

**Conclusion:** All 5 platforms have compatible PyPI wheels for all voss dependencies. Running `pip install` on the **native** CI runner for each platform (e.g., `ubuntu-24.04-arm` for linux-arm64) will automatically download and install the correct platform wheel. No cross-compilation or special handling needed.

**The voss wheel itself** (`voss-0.1.0-py3-none-any.whl`) is pure Python (no C extensions). One wheel works for all 5 platforms.

### Post-install site-packages contents (estimate)

After `pip install voss-wheel` on a fresh PBS extract, `lib/python3.12/site-packages/` will contain approximately:
- pip, setuptools (already present in PBS)
- voss package tree + voss_runtime (~300KB source)
- lark, click, rich, pyyaml, pydantic (~50MB total — pydantic is large)
- litellm, anthropic, openai, httpx, httpcore (~80MB total)
- chromadb, onnxruntime (~200MB total — onnxruntime is large)
- sentence-transformers, huggingface-hub, torch [ASSUMED — sentence-transformers may pull in torch transitively; size impact unknown without a real install]
- tiktoken (~5MB)

**Estimated total subpackage size post-install:** 400-600MB uncompressed per platform. npm publish will compress this to ~100-200MB per platform tarball.

This is large but comparable to electron's platform packages (~120-200MB). npm does not impose per-package size limits that would block publish, but `npm pack` output size will be significant.

**[ASSUMED] Size risk:** If sentence-transformers pulls in full PyTorch (~800MB), the subpackage becomes impractically large for npm. The planner should add a CI step that prints the site-packages total size after `pip install` so the actual size is known before publish. If PyTorch is pulled in, we may need to pin sentence-transformers without the `torch` extra or strip torch afterwards.

---

## 6. Bin Shim Design (NPM-03 / D-02)

### Canonical pattern: Biome shim (verified)

[VERIFIED: GitHub source biomejs/biome main branch, 2026-05-13]

Biome's `bin/biome` is the closest published reference to what we need. Key implementation:

```js
const result = require("child_process").spawnSync(binaryPath, process.argv.slice(2), {
  shell: false,
  stdio: "inherit",
  env: { ...env },
});
if (result.error) { throw result.error; }
process.exitCode = result.status;
```

`spawnSync` with `stdio: "inherit"` is the canonical pattern for CLI wrappers because:
- stdin/stdout/stderr are inherited directly (no piping, no buffering)
- The parent Node process blocks until the child exits
- `result.status` is the child's exit code (1 on `voss doctor` no-creds)
- `result.signal` captures termination-by-signal

**Our shim differs from Biome** in that we spawn Python, not a native binary. Python is an executable at a known path within the subpackage.

### Our shim: `npm/bin/voss.js`

```js
#!/usr/bin/env node
'use strict';

const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const PLATFORMS = {
  darwin: { arm64: '@voss/cli-darwin-arm64', x64: '@voss/cli-darwin-x64' },
  linux:  { arm64: '@voss/cli-linux-arm64',  x64: '@voss/cli-linux-x64' },
  win32:  { x64:   '@voss/cli-win32-x64' },
};

function findPlatformPackage() {
  const { platform, arch } = process;
  const pkg = PLATFORMS[platform]?.[arch];
  if (!pkg) {
    process.stderr.write(`voss: unsupported platform: ${platform} ${arch}\n`);
    process.exit(1);
  }
  try {
    return require.resolve(`${pkg}/package.json`).replace('/package.json', '');
  } catch {
    process.stderr.write(
      `voss: platform package ${pkg} not installed.\n` +
      `Try: npm install ${pkg}\n`
    );
    process.exit(1);
  }
}

const pkgDir = findPlatformPackage();
const isWindows = process.platform === 'win32';
const pythonBin = isWindows
  ? path.join(pkgDir, 'python', 'python.exe')
  : path.join(pkgDir, 'python', 'bin', 'python3');

if (!fs.existsSync(pythonBin)) {
  process.stderr.write(`voss: vendored Python not found at ${pythonBin}\n`);
  process.exit(1);
}

const result = spawnSync(pythonBin, ['-m', 'voss.cli', ...process.argv.slice(2)], {
  shell: false,
  stdio: 'inherit',
  env: process.env,
});

if (result.error) throw result.error;
process.exitCode = result.status;
```

### Signal forwarding semantics

**Unix (darwin, linux):** `spawnSync` with `stdio: 'inherit'` correctly forwards Ctrl-C (SIGINT) to the Python child process. When the user presses Ctrl-C, the terminal sends SIGINT to the **process group**, which includes both the Node.js shim and the Python subprocess. Python's default SIGINT handler raises `KeyboardInterrupt`, which typically terminates cleanly. The Node shim then gets `result.signal = 'SIGINT'` and `result.status = null`; we should set `process.exitCode = 130` (SIGINT convention). [VERIFIED: Node.js `spawnSync` docs semantics]

**Windows:** Ctrl-C on Windows sends `CTRL_C_EVENT` to the console process group. `spawnSync` on Windows does not automatically relay this to the child process in all cases. The canonical workaround for Python subprocess wrappers is to NOT use `shell: false` on Windows — or to explicitly re-send the signal. However, `spawnSync` with `stdio: 'inherit'` on Windows does share the console, so `CTRL_C_EVENT` propagates naturally when the parent and child share a console window (the normal case for CLI use). For npm-global usage (`voss` as a CLI), the console is always shared, so this is not a practical problem. [ASSUMED: Win32 signal forwarding via shared console is sufficient for CLI use; test on Windows CI]

**Final shim signal handling addition for Unix:**

```js
if (result.signal) {
  // Re-exit with the standard signal exit code (128 + signal number)
  const signalNums = { SIGINT: 2, SIGTERM: 15 };
  process.exitCode = 128 + (signalNums[result.signal] || 0);
}
```

---

## 7. Release Workflow (GitHub Actions)

### Pre-existing `release.yml` must be REPLACED

The current `.github/workflows/release.yml` is a cargo-dist-generated workflow for the Rust `crates/` binaries. It references `axodotdev/cargo-dist`, builds Rust artifacts, creates GitHub Releases, and publishes a Homebrew formula. **This entire file is dead as of the Rust frozen-spike decision and must be deleted as M6-01's first task.** Preserving any of its content would cause cargo-dist to run on npm-publish tags and fail. [VERIFIED: read .github/workflows/release.yml]

There is also `.github/workflows/rust.yml` which may run Rust CI. Check whether this also needs to be deleted or just disabled.

### New release workflow shape

The new `release.yml` fires on `push: tags: ['v*']`. It runs in matrix mode across 5 OS/arch combinations, one job per platform subpackage, then a final job to publish the main `@voss/cli` package.

**GitHub Actions runner mapping (all free-tier, no Depot required):**

| npm platform | GHA runner | Available |
|-------------|-----------|-----------|
| `darwin-arm64` | `macos-latest` (Apple Silicon, macos-14) | Yes |
| `darwin-x64` | `macos-13` (Intel) | Yes |
| `linux-x64` | `ubuntu-24.04` | Yes |
| `linux-arm64` | `ubuntu-24.04-arm` | Yes (GA since 2024) |
| `win32-x64` | `windows-latest` | Yes |

[VERIFIED: GitHub runner images API, 2026-05-13]

**`ubuntu-24.04-arm` is a standard GitHub-hosted runner** available to public repos at no extra cost. No Depot account or self-hosted runner needed.

### Workflow structure

```yaml
name: Release

on:
  push:
    tags: ['v*']

jobs:
  build-platform:
    name: Build ${{ matrix.npm-platform }}
    strategy:
      matrix:
        include:
          - npm-platform: darwin-arm64
            runner: macos-latest
            pbs-triple: aarch64-apple-darwin
            python-bin: python/bin/python3
          - npm-platform: darwin-x64
            runner: macos-13
            pbs-triple: x86_64-apple-darwin
            python-bin: python/bin/python3
          - npm-platform: linux-x64
            runner: ubuntu-24.04
            pbs-triple: x86_64-unknown-linux-gnu
            python-bin: python/bin/python3
          - npm-platform: linux-arm64
            runner: ubuntu-24.04-arm
            pbs-triple: aarch64-unknown-linux-gnu
            python-bin: python/bin/python3
          - npm-platform: win32-x64
            runner: windows-latest
            pbs-triple: x86_64-pc-windows-msvc
            python-bin: python/python.exe
    runs-on: ${{ matrix.runner }}
    steps:
      - uses: actions/checkout@v4
      # 1. Extract version from pyproject.toml
      - name: Read version
        id: ver
        run: python3 -c "import tomllib,sys; d=tomllib.load(open('pyproject.toml','rb')); print('VERSION='+d['project']['version'])" >> $GITHUB_ENV
      # 2. Build the voss wheel (same path M5-06 smoke-tests)
      - run: pip install build
      - run: python -m build --wheel --outdir dist/
      # 3. Download PBS tarball
      - name: Download PBS
        run: |
          PBS_TAG=20260510
          PBS_VER=3.12.13
          curl -fsSL "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PBS_VER}+${PBS_TAG}-${{ matrix.pbs-triple }}-install_only_stripped.tar.gz" -o pbs.tar.gz
          tar -xzf pbs.tar.gz
      # 4. Prune
      - name: Prune PBS
        run: python3 npm/scripts/prune_pbs.py python/
      # 5. Pre-install voss wheel into vendored site-packages
      - name: Install wheel
        run: ${{ matrix.python-bin }} -m pip install --no-cache-dir dist/voss-*.whl
      # 6. Generate platform package.json from version
      - name: Generate package.json
        run: python3 npm/scripts/bump_version.py ${{ matrix.npm-platform }}
      # 7. Pack and publish
      - name: Publish platform package
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
        run: |
          cd npm/platforms/${{ matrix.npm-platform }}
          cp -r ../../../python ./
          npm publish --access public

  publish-main:
    needs: build-platform
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate main package.json
        run: python3 npm/scripts/bump_version.py main
      - uses: actions/setup-node@v4
        with:
          registry-url: 'https://registry.npmjs.org'
      - name: Publish @voss/cli
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
        run: |
          cd npm
          npm publish --access public
```

### npm authentication

`NPM_TOKEN` must be an npm **Automation token** (not a Publish token) created in the `@voss` org settings on npmjs.com. Automation tokens bypass 2FA for CI. Store as a GitHub Actions secret named `NPM_TOKEN`.

---

## 8. Version-Sync Script (D-10)

### `npm/scripts/bump_version.py`

Reads `[project] version` from `pyproject.toml` via stdlib `tomllib` (Python 3.11+), writes the version to all `package.json` files:

```python
#!/usr/bin/env python3
"""Read version from pyproject.toml and regenerate all npm package.json files.

Usage:
  python3 npm/scripts/bump_version.py          # update all
  python3 npm/scripts/bump_version.py main     # update npm/package.json only
  python3 npm/scripts/bump_version.py darwin-arm64  # update one platform
"""
import sys, json, tomllib, pathlib

ROOT = pathlib.Path(__file__).parent.parent.parent
PYPROJECT = ROOT / "pyproject.toml"
NPM_DIR = ROOT / "npm"

with open(PYPROJECT, "rb") as f:
    version = tomllib.load(f)["project"]["version"]

PLATFORMS = ["darwin-arm64", "darwin-x64", "linux-x64", "linux-arm64", "win32-x64"]

def update_json(path: pathlib.Path, version: str) -> None:
    data = json.loads(path.read_text())
    data["version"] = version
    # Also update optionalDependencies versions for main package
    if "optionalDependencies" in data:
        for k in data["optionalDependencies"]:
            data["optionalDependencies"][k] = version
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Updated {path} -> {version}")

target = sys.argv[1] if len(sys.argv) > 1 else "all"
if target in ("all", "main"):
    update_json(NPM_DIR / "package.json", version)
for plat in PLATFORMS:
    if target in ("all", plat):
        update_json(NPM_DIR / "platforms" / plat / "package.json", version)
```

### CI version-sync check (pre-publish gate)

Add a step in the release workflow that verifies `npm/package.json` version matches `pyproject.toml` version. This catches cases where the release script was not run before tagging:

```yaml
- name: Verify version sync
  run: |
    PYVER=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
    NPMVER=$(node -e "console.log(require('./npm/package.json').version)")
    if [ "$PYVER" != "$NPMVER" ]; then
      echo "VERSION MISMATCH: pyproject.toml=$PYVER npm/package.json=$NPMVER"
      echo "Run: python3 npm/scripts/bump_version.py"
      exit 1
    fi
```

---

## 9. NPM-04 Smoke Test Design

### Recommendation: pytest `@pytest.mark.slow` test using `npm pack`

This integrates naturally with the existing test suite and reuses the `@pytest.mark.slow` marker from M5-06. The test does NOT require a live npm registry — `npm pack` produces a local tarball.

**Location:** `tests/packaging/test_npm_install.py`

**Test structure:**

```python
@pytest.mark.slow
def test_npm_pack_and_install(tmp_path):
    """Pack the @voss/cli main package, install into fresh tmpdir, verify CLI works."""
    repo = _repo_root()
    # 1. Pack (creates @voss-cli-0.1.0.tgz or similar)
    subprocess.run(["npm", "pack", str(repo / "npm")], check=True, cwd=tmp_path, timeout=60)
    tarball = next(tmp_path.glob("*.tgz"))
    
    # 2. Create a fresh Node project
    pkg_dir = tmp_path / "test_project"
    pkg_dir.mkdir()
    (pkg_dir / "package.json").write_text('{"name":"test","version":"1.0.0"}')
    
    # 3. Install local platform subpackage first (simulate optionalDependencies)
    # On CI, only the current platform subpackage is available;
    # install it by path so require.resolve works
    
    # 4. Run voss commands via node npm/bin/voss.js
    voss_js = repo / "npm" / "bin" / "voss.js"
    
    # --help exits 0
    r = subprocess.run(["node", str(voss_js), "--help"], ...)
    assert r.returncode == 0
    
    # doctor exits 0 or 1 (M1 D-13)
    r = subprocess.run(["node", str(voss_js), "doctor"], ...)
    assert r.returncode in {0, 1}
    
    # check + compile need a .voss file — use inline fixture
    voss_file = tmp_path / "smoke.voss"
    voss_file.write_text('agent SmokeAgent { }')
    r = subprocess.run(["node", str(voss_js), "check", str(voss_file)], ...)
    assert r.returncode == 0
```

**Key design decisions:**

1. **Use `npm pack` + local install, not a live registry publish.** This works pre-publish and in CI.
2. **Embed a tiny `.voss` fixture in the test** rather than depending on `samples/` being at repo root (the M6 context notes that the wheel doesn't ship `samples/`).
3. **Accept `voss doctor` exit 0 or 1** (M1 D-13 contract preserved).
4. **Add as `@pytest.mark.slow`** alongside `test_wheel_install.py`. CI slow suite runs both.
5. **The test must have the platform subpackage available** — in the full test, this means either (a) the subpackage is built and installed locally before running the test, or (b) the test sets `PYTHONPATH` or `VOSS_PYTHON_BIN` to the already-built PBS extract from an environment variable. The simplest approach: require a pre-built PBS extract in a known location (`TEST_PBS_EXTRACT` env var) and skip the test if not set.

---

## 10. Cross-Platform Gotchas

### Windows

1. **Python path:** `python/python.exe` not `python/bin/python3`. Shim must branch on `process.platform === 'win32'`.
2. **Shebang in bin:** The shim file must have `#!/usr/bin/env node` — npm handles this correctly on Windows via `voss.cmd` wrapper auto-generated at install time.
3. **Line endings:** PBS Windows tarball uses CRLF for `.py` files in `Lib/` — but Python handles this correctly at the interpreter level. No special handling needed.
4. **vcruntime140.dll:** PBS Windows ships `vcruntime140.dll` and `vcruntime140_1.dll` at `python/`. These must NOT be pruned — they are required by Python and C extension modules. Some Windows systems already have these in System32, but including them in the package ensures compatibility.
5. **CTRL_C_EVENT:** `spawnSync` with `stdio: 'inherit'` on Windows shares the console process group, so Ctrl-C propagates to the Python child naturally. However, if the user is running in a non-console environment (e.g., wrapped by another process without a console), signal forwarding may fail silently. [ASSUMED: acceptable limitation for v0.1]
6. **`Scripts/` vs `bin/`:** Windows console scripts go in `python/Scripts/voss.exe` after wheel install. The shim ignores this and uses `-m voss.cli` directly.

### npm optionalDependencies

- **npm lockfile semantics:** `optionalDependencies` that fail to install (wrong `os`/`cpu`) are recorded in `package-lock.json` as `"optional": true` with the install omitted. This is correct behavior — `npm ci` on linux-x64 will not fail because `@voss/cli-darwin-arm64` was skipped.
- **`npm install --ignore-optional`:** If a user runs this, no platform package is installed and the shim will fail at runtime. The shim's error message should direct them to install the specific `@voss/cli-<platform>-<arch>` package manually.
- **Yarn / pnpm compatibility:** Both honor `os`/`cpu` fields in optionalDependencies. [ASSUMED: tested in esbuild/biome which use the same pattern; should work for voss]
- **`os`/`cpu` field values:** Use exactly Node's `process.platform` and `process.arch` strings (`darwin`, `linux`, `win32`; `arm64`, `x64`). These must match the `os`/`cpu` arrays in the platform `package.json`.

### npm package size

npm does not impose a hard size limit on published packages, but very large packages (>500MB) may time out during `npm publish` or trigger a 413 from the registry. The voss platform packages will be ~100-200MB **compressed** (tarballs), which is within the practical range. No special handling is needed, but the planner should be aware that `npm publish` for large packages takes ~1-3 minutes per platform.

### File permissions (Unix)

The PBS `python3` binary must be executable (`chmod +x`). PBS tarballs preserve Unix permissions correctly, so extracting the tarball in CI already sets the right modes. However, npm `pack`/`publish` may strip execute bits from non-`.js` files in some npm versions. The safest fix: add a `postinstall` script to the platform package that `chmod +x` the Python binary. This is a 1-line package.json addition:

```json
{
  "scripts": {
    "postinstall": "node -e \"const fs=require('fs'); const p=__dirname+'/python/bin/python3'; if(fs.existsSync(p)) fs.chmodSync(p, 0o755);\""
  }
}
```

[ASSUMED: npm does strip execute bits; verify during M6 build. If npm preserves them, postinstall can be omitted.]

---

## 11. Existing `release.yml` Deletion

[VERIFIED: read .github/workflows/release.yml]

The current `.github/workflows/release.yml` is a **full cargo-dist generated workflow** with approximately 200 lines including:
- `cargo-dist plan` job
- `build-local-artifacts` matrix (Rust targets)
- `build-global-artifacts` job
- `host` job
- `publish-homebrew-formula` job (references `bm9797/homebrew-voss` repo)
- `announce` job

**All of this is dead.** The Rust frozen-spike decision means no Rust artifacts will be built. If this file is not deleted, pushing a `v*` tag will trigger cargo-dist to run, fail (no Rust targets build), and create a broken GitHub Release.

**Action for M6-01:** Delete `.github/workflows/release.yml` and replace with the new npm-publish workflow. Also check `.github/workflows/rust.yml` — if it runs `cargo build` or `cargo test`, it should either be deleted or have its trigger changed to `workflow_dispatch` only (to freeze it alongside the spike).

---

## 12. Recommended Wave Breakdown

This is the researcher's suggestion to the planner. D-14 ordering (name reservation first) is a hard constraint.

| Wave | Plan | Content | Gate |
|------|------|---------|------|
| W0 | M6-01 | **npm name reservation + repo/org scaffolding.** Create `@voss` npm org, publish `0.0.0` placeholders for `@voss/cli` + 5 platform subpackages. Delete old `release.yml`. Create `npm/` directory structure with stubs. | All 6 npm packages reserved |
| W1 | M6-02 | **PBS download, prune, and pre-install script.** `npm/scripts/prune_pbs.py`, `npm/scripts/build_platform.py` that downloads PBS, prunes, runs `pip install voss-wheel`, outputs to `npm/platforms/<triple>/python/`. Tested against one platform locally. | `python/bin/python3 -c "import voss.cli"` exits 0 in vendored env |
| W1 | M6-03 | **Bin shim + version-sync script.** `npm/bin/voss.js` (50 LOC, Biome pattern), `npm/scripts/bump_version.py` (reads pyproject.toml, regenerates all package.json). Manual test: `node npm/bin/voss.js --help` with one platform built. | `node npm/bin/voss.js --help` exits 0 |
| W2 | M6-04 | **Release workflow.** New `.github/workflows/release.yml` for 5-platform matrix build + 6 npm publishes. Test against a `v0.0.1-test` tag to verify matrix and authenticate NPM_TOKEN. | Workflow runs green in CI; all 6 packages publish to registry |
| W3 | M6-05 | **NPM-04 smoke test + README update (NPM-05).** `tests/packaging/test_npm_install.py` (`@pytest.mark.slow`). README.md: update primary install to `npm i -g @voss/cli`. | Smoke test passes; `pytest -m slow tests/packaging/test_npm_install.py` exits 0 |

---

## 13. Files M6 Will Create / Modify / Delete

### Create (new)

```
npm/
├── package.json                      # @voss/cli main package
├── bin/
│   └── voss.js                       # Node bin shim (~50 LOC)
├── platforms/
│   ├── darwin-arm64/
│   │   └── package.json             # @voss/cli-darwin-arm64 stub
│   ├── darwin-x64/
│   │   └── package.json
│   ├── linux-x64/
│   │   └── package.json
│   ├── linux-arm64/
│   │   └── package.json
│   └── win32-x64/
│       └── package.json
└── scripts/
    ├── bump_version.py              # D-10 version-sync
    ├── prune_pbs.py                 # D-07 prune logic
    └── build_platform.py           # PBS download + prune + pip install orchestration

tests/
└── packaging/
    └── test_npm_install.py         # NPM-04 smoke test

.github/workflows/
└── release.yml                     # NEW (npm publish; replaces cargo-dist version)
```

### Modify

```
README.md                           # NPM-05: promote npm i -g @voss/cli to primary
```

### Delete

```
.github/workflows/release.yml      # OLD cargo-dist workflow (replaced entirely)
```

### Conditionally delete / modify

```
.github/workflows/rust.yml          # Freeze or delete if it runs cargo build
dist-workspace.toml                 # cargo-dist config; safe to delete or leave (Rust frozen)
```

---

## 14. Open Questions (RESOLVED)

1. **PyTorch transitive dependency from sentence-transformers**
   - What we know: `sentence-transformers==5.5.0` is pure-Python. But it depends on `torch` transitively (via its optional extras).
   - What's unclear: Does `pip install voss-0.1.0.whl` pull in PyTorch? If so, the npm subpackage would be ~800MB+ — impractical.
   - Recommendation: In M6-02's build script, print `du -sh python/lib/python3.12/site-packages/` after install. If >300MB, pin `sentence-transformers` without the `torch` extra or use `pip install --no-deps` for sentence-transformers and manually install its non-torch deps.
   - [ASSUMED: sentence-transformers does NOT pull torch by default for inference-only usage; verify in W1]
   - **RESOLVED:** M6-03 Task 3 (host build) and Task 4 (cross-platform CI build via M6-04) BLOCK on `du -sh python/lib/python3.12/site-packages/` size verification; an >300MB result halts the build and surfaces the failure before publish. Assumption stays ASSUMED until the size gate runs green; the gate itself is the resolution mechanism.

2. **npm package file size after compression**
   - What we know: Uncompressed PBS (~87-120MB) + site-packages (unknown, likely 200-500MB).
   - What's unclear: Compressed tarball size for npm publish. npm compresses with gzip.
   - Recommendation: Run `npm pack --dry-run` in M6-04 to see the package size before committing to publish.
   - **RESOLVED:** M6-04 release workflow runs `npm pack --dry-run` per platform subpackage and surfaces tarball size in the workflow log before any `npm publish` step. Registry rejection at publish time is a non-silent failure mode.

3. **`file:` permissions on npm-published Python binary**
   - What we know: npm may strip execute bits from non-JS files.
   - What's unclear: Does current npm (v10) preserve the executable bit on `python/bin/python3`?
   - Recommendation: Test in M6-04 by installing the packed tarball on macOS/Linux and running `ls -la python/bin/python3`. If stripped, add postinstall chmod.
   - **RESOLVED:** M6-01 Task 2 ships a `postinstall` chmod script in all 4 Unix platform package.json manifests (darwin-arm64/x64, linux-arm64/x64). M6-04 verification step packs the tarball and asserts the executable bit survives. The chmod is unconditional — runs whether npm strips the bit or not, so the question's answer (whether npm v10 preserves the bit) becomes irrelevant to correctness.

4. **`@voss` org creation logistics**
   - What we know: Requires a manual npmjs.com account + org creation step.
   - What's unclear: Does Ben have an npm account? Is `voss` the right org name?
   - Recommendation: M6-01 is blocked until the npm account + org exist. This is a human task, not an automated one.
   - **RESOLVED:** M6-01 Task 0 is a [BLOCKING] `checkpoint:human-action` that pauses the entire phase until the user confirms the `@voss` org exists, the Automation token is generated, and `NPM_TOKEN` is set as a GitHub Actions secret. No automated task in M6 runs until this lands.

5. **`ubuntu-24.04-arm` billing for private repos**
   - What we know: The Voss GitHub repo is currently public (`bm9797/Voss` in `Cargo.toml`).
   - What's unclear: If the repo is ever made private, arm64 runners may count double against GitHub Actions minutes.
   - Recommendation: No action for v0.1 (repo is public). Note for future.
   - **RESOLVED:** No action needed for v0.1. The Voss repo is public (`bm9797/Voss`), so arm64 runner minutes do not double-bill. If the repo is later made private, M6-04's workflow can be revisited; out of scope for M6.

6. **`dist-workspace.toml` and `Cargo.lock` / `Cargo.toml` fate**
   - What we know: These are cargo-dist and Rust workspace config files, no longer needed.
   - What's unclear: Whether deleting them causes any non-Rust tooling to break (e.g., does any CI job reference them?).
   - Recommendation: Delete `dist-workspace.toml`. Leave `Cargo.toml` and `Cargo.lock` in place (they define the frozen spike workspace; deleting them is fine but a separate decision from M6's scope).
   - **RESOLVED:** M6-01 Task 1 deletes `.github/workflows/release.yml` (the cargo-dist file). `dist-workspace.toml`, `Cargo.toml`, and `Cargo.lock` stay untouched per PROJECT.md's frozen-Rust-spike decision. M6-01 Task 1's acceptance criteria explicitly forbid touching them.

---

## Risks + Landmines

### Risk 1: `voss` npm name is taken (CONFIRMED BLOCKER)

**Severity:** High — must resolve before M6-01 can complete.
**What happens:** `npm publish voss` returns 403. Users cannot `npm i -g voss`.
**Mitigation:** Use `@voss/cli` (D-12 fallback, already decided). Update all references in npm/package.json, README.md, and documentation.
**Warning sign:** D-14 task immediately discovers this in M6-01.

### Risk 2: Platform subpackage too large for practical npm publish

**Severity:** Medium.
**What happens:** `npm publish` times out or registry rejects >500MB tarball.
**Root cause:** sentence-transformers pulling PyTorch, or chromadb's full onnxruntime stack.
**Mitigation:** Print site-packages size in CI build script. If >300MB uncompressed, trim PyTorch from the install (see Open Question 1). The voss package itself is tiny — the risk comes purely from transitive deps.
**Warning sign:** M6-02 build script output shows site-packages >500MB.

### Risk 3: C extension mismatch on `linux-arm64`

**Severity:** Medium.
**What happens:** After installing on a `linux-arm64` machine, `import chromadb` or `import tiktoken` fails with `ImportError` because the `.so` files were compiled for a different glibc.
**Root cause:** PyPI `manylinux_2_17_aarch64` wheels may not be compatible with the system glibc on older arm64 distros.
**Mitigation:** The PBS interpreter ships its own glibc-agnostic Python; C extension `.so` files are linked against system glibc. Use PBS tarballs, not custom builds. Test on `ubuntu-22.04-arm` (older glibc) as well as `ubuntu-24.04-arm`.
**Warning sign:** `import chromadb` fails in the NPM-04 smoke test on linux-arm64.

### Risk 4: Windows signal forwarding in non-console environments

**Severity:** Low (v0.1 CLI use case is always a console).
**What happens:** Ctrl-C does not interrupt `voss` on Windows when invoked from certain environments (e.g., VS Code integrated terminal in some configurations, MinGW).
**Mitigation:** Document known limitation. Add explicit `process.on('SIGINT', ...)` handler in the Node shim that kills the child process.
**Warning sign:** Manual test on Windows: Ctrl-C during `voss do "long task"` does not terminate Python.

### Risk 5: `release.yml` not deleted before first tag push

**Severity:** High.
**What happens:** Cargo-dist runs on the `v0.1.0` tag, fails because Rust crates don't build, and creates a broken GitHub Release.
**Mitigation:** M6-01 must delete `.github/workflows/release.yml` before any test tags are pushed.
**Warning sign:** Release workflow run shows cargo-dist failures.

### Risk 6: npm org `@voss` requires manual human action before M6-01 can run

**Severity:** Medium (blocks M6-01 on a human task).
**What happens:** The npm org cannot be created by CI — it requires browser login and human confirmation.
**Mitigation:** Ben creates the `@voss` org before M6 execution begins. Flag this as a prerequisite in M6-01.
**Warning sign:** M6-01 plan cannot proceed without the org existing.

---

## External References

| Resource | URL | What it proves |
|----------|-----|----------------|
| esbuild npm package | https://www.npmjs.com/package/esbuild | optionalDependencies shape, bin entry pattern |
| @esbuild/darwin-arm64 | https://www.npmjs.com/package/@esbuild/darwin-arm64 | os/cpu fields, per-platform subpackage shape |
| Biome bin shim (GitHub) | https://github.com/biomejs/biome/blob/main/npm/biome/bin/biome | Canonical spawnSync shim with platform dispatch |
| @biomejs/biome | https://www.npmjs.com/package/@biomejs/biome | optionalDependencies + bin pattern cross-validation |
| PBS releases (GitHub) | https://github.com/astral-sh/python-build-standalone/releases | Tarball names, sizes, all 5 target triples |
| PBS release 20260510 | https://github.com/astral-sh/python-build-standalone/releases/tag/20260510 | Python 3.12.13, all 5 stripped install_only tarballs verified |
| Node.js spawnSync docs | https://nodejs.org/api/child_process.html#child_processspawnsynccommand-args-options | stdio: 'inherit', signal/status semantics |
| npm optionalDependencies | https://docs.npmjs.com/cli/v10/configuring-npm/package-json#optionaldependencies | os/cpu resolution, lockfile semantics |
| GitHub ubuntu-24.04-arm | https://github.com/actions/runner-images | Confirms arm64 runner available for public repos |
| PyPI chromadb | https://pypi.org/pypi/chromadb/json | Platform wheel availability for linux-arm64 |
| PyPI tiktoken | https://pypi.org/pypi/tiktoken/json | Platform wheel availability for linux-arm64 |
| PyPI onnxruntime | https://pypi.org/pypi/onnxruntime/json | Platform wheel availability, cp312 arm64 confirmed |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | sentence-transformers does not pull PyTorch as a required transitive dep for inference-only usage | §5, Risk 2 | Platform packages would be 800MB+ — impractical for npm |
| A2 | npm v10 preserves Unix execute bits on non-JS files in published tarballs | §10, Open Question 3 | Python binary not executable after install; postinstall chmod needed |
| A3 | Ctrl-C signal forwarding via shared console process group works on Windows CLI | §6, Risk 4 | Windows users cannot interrupt long-running voss sessions |
| A4 | `ubuntu-24.04-arm` is available on GitHub free tier for public repos | §7 | Linux arm64 CI build impossible; need Depot or self-hosted runner |
| A5 | The `voss` npm package owner will not respond to a squatting claim | §1 | Could reclaim unscoped name after weeks-long process |
| A6 | pydantic v2 ships as pure-Python (its Rust core `pydantic-core` is compiled but the pydantic package itself is py3-none-any) | §5 | pydantic-core wheel needed per platform; check during M6-02 |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (existing) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest -q -m "not slow and not live"` |
| Full suite command | `pytest -q -m "not live"` (includes slow) |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NPM-01 | `@voss/cli` package publishable with correct metadata | Manual (npm publish is a release gate, not a test) | N/A | N/A |
| NPM-02 | Platform packages vendor PBS + voss wheel for all 5 platforms | Slow integration | `pytest -m slow tests/packaging/test_npm_install.py::test_platform_package_builds` | ❌ Wave 0 |
| NPM-03 | Bin shim forwards argv/stdio/exit code/signals | Slow integration | `pytest -m slow tests/packaging/test_npm_install.py::test_shim_forwarding` | ❌ Wave 0 |
| NPM-04 | Fresh Node project: `npx voss --help`, `doctor`, `check`, `compile` exit 0 | Slow smoke | `pytest -m slow tests/packaging/test_npm_install.py::test_npm_smoke` | ❌ Wave 0 |
| NPM-05 | README has `npm i -g @voss/cli` as primary install | Fast content assertion | `pytest tests/packaging/test_readme.py` (extend existing) | ✅ (extend) |

### Sampling Rate

- **Per task commit:** `pytest -q -m "not slow and not live"` (fast suite, <30s)
- **Per wave merge:** `pytest -q -m "not live"` (includes slow packaging tests)
- **Phase gate:** Full slow suite green before tagging v0.1.0

### Wave 0 Gaps

- [ ] `tests/packaging/test_npm_install.py` — covers NPM-02, NPM-03, NPM-04
- [ ] `tests/packaging/test_readme.py` needs one additional assertion for `npm i -g @voss/cli` (NPM-05)
- [ ] Platform build infrastructure must exist before tests can run (M6-02 prereq for NPM-02/03/04 tests)

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V5 Input Validation | Partial | Shim passes argv as-is to Python; Python CLI validates. No shim-level injection risk because shell:false. |
| V6 Cryptography | No | — |

| Threat Pattern | STRIDE | Mitigation |
|----------------|--------|------------|
| Supply chain: PBS tarball tampering | Tampering | Pin PBS tarball to a specific release tag + SHA (store SHA in `npm/scripts/pbs_checksums.json`). Verify with `sha256sum` before extracting. |
| Supply chain: voss wheel substitution | Tampering | Wheel is built in-CI from the tagged git commit; `python -m build` runs from checkout. No PyPI dependency. |
| Path traversal in shim | Tampering | Not applicable — `require.resolve` resolves to a package directory, not user input. |
| npm token exposure | Information Disclosure | `NPM_TOKEN` is a GitHub Actions secret; never logged or echoed. |

---

## Sources

### Primary (HIGH confidence)
- npm registry (`npm view esbuild`, `npm view @esbuild/darwin-arm64`, `npm view @biomejs/biome`, `npm view @biomejs/cli-darwin-arm64`, `npm view voss`) — package structures, optionalDependencies shape, os/cpu fields, voss name conflict
- `github.com/astral-sh/python-build-standalone/releases` API — tarball names, file sizes, all 5 target triples confirmed
- `github.com/biomejs/biome` — `npm/biome/bin/biome` source: canonical spawnSync shim
- Live tarball extraction: `cpython-3.12.13+20260510-aarch64-apple-darwin-install_only_stripped.tar.gz` and `cpython-3.12.13+20260510-x86_64-pc-windows-msvc-install_only_stripped.tar.gz` — exact PBS directory layout, bin paths, prune candidates, sizes
- PyPI JSON API (`chromadb`, `tiktoken`, `onnxruntime`, `sentence-transformers`, `litellm`, `lark`, `pydantic`) — wheel availability per platform

### Secondary (MEDIUM confidence)
- GitHub runner images API release listing — confirms `ubuntu-24.04-arm` exists in runner images
- `esbuild` `lib/npm/node-platform.ts` (GitHub source) — platform dispatch table showing `process.platform + os.arch() + os.endianness()` key pattern

### Tertiary (LOW confidence / ASSUMED)
- sentence-transformers PyTorch transitive dep behavior — assumed non-required for inference; needs M6-02 verification
- npm v10 execute bit preservation — assumed needs M6-04 verification

---

## Metadata

**Confidence breakdown:**
- npm name conflict (voss taken): HIGH — confirmed via live registry query
- PBS layout and sizes: HIGH — confirmed via live tarball extract
- Biome shim pattern: HIGH — confirmed via live GitHub source
- C-extension wheel availability: HIGH — confirmed via PyPI JSON API
- Site-packages total size post-install: LOW — depends on sentence-transformers/torch dep tree
- Windows signal forwarding: MEDIUM — spawnSync shared console propagation is documented behavior but untested on this specific setup

**Research date:** 2026-05-13
**Valid until:** 2026-06-13 (PBS releases monthly; re-pin before publishing if >30 days pass)

---

## RESEARCH COMPLETE
