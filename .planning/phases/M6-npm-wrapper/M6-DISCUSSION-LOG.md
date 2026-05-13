# Phase M6: npm Wrapper - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-13
**Phase:** M6-npm-wrapper
**Areas discussed:** Bundling strategy, Python runtime source, Wheel source + version sync, Platform matrix + package name

---

## Bundling strategy

### Q1: Which bundling pattern for `npm i -g voss`?

| Option | Description | Selected |
|--------|-------------|----------|
| optionalDependencies (esbuild pattern) | 5 platform subpackages; main package lists as optionalDeps; offline install; ~10MB resolved per platform | ✓ |
| postinstall download (pyright pattern) | Tiny shim; postinstall downloads Python + wheel from GitHub Release; needs network | |
| Hybrid — optionalDeps with postinstall fallback | Best UX, most code paths to maintain | |

**User's choice:** optionalDependencies (esbuild pattern)
**Notes:** Locks in 5 platform subpackages + offline-install posture. Forks subsequent decisions toward esbuild's reference layout.

### Q2: Bin shim language?

| Option | Description | Selected |
|--------|-------------|----------|
| Node.js JS shim | ~50 LOC; spawn vendored python; forward argv/stdio/exit/signals; cross-platform | ✓ |
| Compiled native shim (Rust/Go) | ~5ms startup vs ~50ms Node; adds compile step + 5 more binaries | |
| Shell script (POSIX + .cmd) | Simplest; fragile around Windows signal forwarding + path quoting | |

**User's choice:** Node.js JS shim
**Notes:** Standard pyright/ts-node pattern; no compile step.

### Q3: Where should the JS / npm package code live?

| Option | Description | Selected |
|--------|-------------|----------|
| `npm/` subdir at repo root | Monorepo; single git tag triggers wheel + npm publish in lockstep | ✓ |
| Separate `voss-npm` repo | Cleaner separation; cross-repo version sync pain | |
| `packages/voss-cli` (pnpm/turbo workspace) | Full JS monorepo overhead for one package | |

**User's choice:** `npm/` subdir at repo root
**Notes:** Mirrors esbuild / turbo / biome repo layout.

---

## Python runtime source

### Q4: Where do per-platform Python interpreters come from?

| Option | Description | Selected |
|--------|-------------|----------|
| python-build-standalone (Astral/Indygreg) | Pre-built portable Python tarballs; same source uv/rye/mise use | ✓ |
| Vendor system Python via pyinstaller/zipapp | Fragile around chromadb/tiktoken/sentence-transformers C extensions | |
| No vendor — require system Python | Smallest npm package; defeats "no Python management" pitch | |

**User's choice:** python-build-standalone
**Notes:** Pin to a specific release tag during planning.

### Q5: Which Python version to pin for v0.1?

| Option | Description | Selected |
|--------|-------------|----------|
| Python 3.12 | Stable; broad C-extension support; full 5-triple PBS coverage | ✓ |
| Python 3.13 | Newest stable; some deps lag on bleeding-edge | |
| Python 3.11 | Mature but older; cuts off perf wins | |

**User's choice:** Python 3.12

### Q6: How to fetch python-build-standalone tarballs at npm-publish time?

| Option | Description | Selected |
|--------|-------------|----------|
| CI download once, vendor into platform packages | GitHub Actions release workflow; reproducible | ✓ |
| Postinstall download | Inconsistent with optionalDependencies choice | |
| Submodule / git LFS | Bloats repo history | |

**User's choice:** CI download once

### Q7: Prune vendored Python, or ship full distribution?

| Option | Description | Selected |
|--------|-------------|----------|
| Light prune | Drop test/, idle/, tkinter/, lib2to3/, ensurepip caches; ~15MB savings | ✓ |
| No prune | ~30MB platform tarball; matches pyright's size | |
| Aggressive prune | Risks runtime ImportError on obscure stdlib modules | |

**User's choice:** Light prune

---

## Wheel source + version sync

### Q8: Where does the npm package get the voss wheel?

| Option | Description | Selected |
|--------|-------------|----------|
| Build wheel in CI at npm-publish time, vendor | Single git tag triggers release; no PyPI dependency | ✓ |
| Pull wheel from PyPI at npm-publish time | Requires PyPI publish first (M5 D-19 deferred) | |
| Both: PyPI publish + npm vendoring in same release | Doubles release surface area | |

**User's choice:** Build wheel in CI

### Q9: How does the JS shim invoke the wheel — pre-installed or lazy?

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-install wheel into vendored site-packages at npm publish time | Zero install-time work; instant first run | ✓ |
| Lazy-install at first invocation | Worst-of-both: bigger than postinstall pattern, still needs network | |
| PEP 723 / pyz / shiv self-contained zipapp | Broken with C-extension deps (chromadb, etc.) | |

**User's choice:** Pre-install at publish time

### Q10: How should npm package version sync with the Python wheel version?

| Option | Description | Selected |
|--------|-------------|----------|
| Single source of truth: `pyproject.toml` | Release script reads version; regenerates all package.json files | ✓ |
| Independent versions, manual sync | Drift risk | |
| Hash-pinned: `0.1.0-g3a1b2c3` | Ugly for stable releases | |

**User's choice:** Single source of truth = pyproject.toml

---

## Platform matrix + package name

### Q11: Which platforms ship in v0.1?

| Option | Description | Selected |
|--------|-------------|----------|
| Full 5: darwin-arm64, darwin-x64, linux-x64, linux-arm64, win32-x64 | Matches ROADMAP capability list; PBS has all 5 | ✓ |
| Drop win32-x64 for v0.1 (mac + linux only) | Less CI to maintain; ROADMAP permits this fallback | |
| Minimal: darwin-arm64 + linux-x64 only | Too narrow; misses x64 Macs + ARM64 Linux | |

**User's choice:** Full 5-platform matrix
**Notes:** Windows is in scope. If vendoring proves expensive, fall back per ROADMAP's permitted drop, not by default.

### Q12: Which npm package name?

| Option | Description | Selected |
|--------|-------------|----------|
| Unscoped `voss` | Cleanest UX; matches Python wheel name; needs reservation | ✓ |
| Scoped `@voss/cli` | Always claimable; two extra chars per command | |
| Unscoped with prefix: `voss-cli` | Diverges from Python wheel name | |

**User's choice:** Unscoped `voss`
**Notes:** Falls back to `@voss/cli` if `npm view voss` shows it's taken — researcher confirms availability in M6-01.

### Q13: Platform subpackage naming convention?

| Option | Description | Selected |
|--------|-------------|----------|
| `@voss/cli-<platform>-<arch>` | Scoped; one org claim unlocks all 5 names; esbuild pattern | ✓ |
| Unscoped `voss-<platform>-<arch>` | 5 separate registry claims; squat risk | |
| `@voss/cli-<node-triple>` | Same as recommended but exact format spelled out | |

**User's choice:** `@voss/cli-<platform>-<arch>`

### Q14: When to reserve npm names?

| Option | Description | Selected |
|--------|-------------|----------|
| Reserve immediately as M6 setup task | First plan publishes 0.0.0 placeholders to claim names | ✓ |
| Reserve at release time | Squat risk; v0.1 already publicly planned | |
| Defer name reservation — prototype under scratch scope first | Adds rename work later | |

**User's choice:** Reserve immediately

---

## Claude's Discretion

- Exact pruning pattern for the vendored Python (D-07 names targets; researcher refines).
- Release CI provider (GitHub Actions is the obvious choice; researcher confirms workflow shape).
- Wheel-SHA verification mechanism (manifest format, signature method).
- Signal-forwarding test approach for the JS shim.
- npm publish credentials handling — GitHub secret name, npm org admin setup.

## Deferred Ideas

- PyPI publish (D-08 deliberate carve-out — v0.1.1 candidate).
- Homebrew formula (DIST-02 in ROADMAP deferred-features).
- Rust shell resurrection — `crates/` stays frozen.
- Signed wheels / sigstore (v0.1.1+ security work).
- Telemetry / install-failure detection (full telemetry deferred from v0.1).
- `npm install voss` without `-g` (local dev-dep use case — revisit if demand surfaces).
- `@voss/sdk` separate package wrapping the Python SDK.
