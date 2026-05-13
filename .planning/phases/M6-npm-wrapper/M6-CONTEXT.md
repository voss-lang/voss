# Phase M6: npm Wrapper - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

<domain>
## Phase Boundary

M6 publishes `voss` as an npm package that vendors a pinned Python interpreter
plus the v0.1 voss wheel, so JS-ecosystem developers can run `npm i -g voss`
(or `npx voss`) and use the full Python harness with **zero manual Python
setup**. M6 is pure distribution — no JS reimplementation of the harness,
compiler, or runtime. Python code under `voss/`, `voss_runtime/`, and
`voss/harness/` is unchanged.

The published surface:
- One unscoped npm package `voss` (~5KB JS shim + dispatch logic).
- Five scoped platform subpackages `@voss/cli-{darwin-arm64, darwin-x64,
  linux-x64, linux-arm64, win32-x64}`, each ~30-50MB containing a pruned
  python-build-standalone interpreter with the voss wheel pre-installed into
  site-packages.
- npm `optionalDependencies` lets each install resolve exactly one platform
  subpackage (esbuild / swc / biome pattern).
- A Node bin shim (`bin/voss.js`) spawns the vendored Python and forwards
  argv, stdio, exit code, and signals.

Post-install user surface (NPM-01..05): `npm i -g voss` → `voss --help`,
`voss doctor`, `voss check <file>`, `voss compile <file>`, `voss do "<task>"`
all work without invoking pip or installing Python separately.

M6 is **distribution work, NOT reimplementation**. Rust `crates/` stays a
frozen spike — not on the v0.1 ship path. PyPI publish remains deferred
(D-19 from M5) — the npm package vendors a freshly-built wheel at release
time, decoupled from any PyPI dependency.

</domain>

<decisions>
## Implementation Decisions

### Bundling strategy

- **D-01:** **esbuild-pattern optionalDependencies.** Publish one main `voss`
  package + 5 platform subpackages under `@voss/cli-<triple>`. Main package
  lists all 5 as `optionalDependencies`; npm resolves exactly one based on
  `process.platform` + `process.arch` of the install host. Rejected:
  pyright-style postinstall download (breaks offline / corporate-proxy
  installs), hybrid (overkill for v0.1).

- **D-02:** **Bin shim = Node.js JS** at `npm/bin/voss.js` (~50 LOC). Spawns
  the vendored `python` with `-m voss.cli`, forwards argv, stdio (inherit),
  exit code, and SIGINT/SIGTERM. Cross-platform, no compile step. Rejected:
  compiled Rust/Go shim (marginal ~50ms gain dwarfed by Python startup),
  shell scripts (fragile around Windows signal forwarding).

- **D-03:** **Layout = `npm/` subdir at repo root.** Monorepo structure:
  `npm/package.json` (main), `npm/bin/voss.js` (shim), `npm/platforms/<triple>/`
  (per-platform subpackage sources before publish), `npm/scripts/`
  (release helpers). Single git tag triggers wheel build + 6 npm publishes
  in lockstep. Rejected: separate `voss-npm` repo (version-sync pain),
  pnpm/turbo workspace (overkill).

### Python runtime source

- **D-04:** **python-build-standalone (Astral/Indygreg)** prebuilt tarballs.
  Same source `uv`/`rye`/`mise` use. Pin to a specific release tag (researcher
  picks the latest stable matching D-05 version). Rejected: pyinstaller
  (fragile around chromadb/tiktoken/sentence-transformers C extensions),
  system-Python (defeats the "no Python management" pitch).

- **D-05:** **Python 3.12** pinned for v0.1. Satisfies pyproject `>=3.11`,
  has broad C-extension support, full 5-triple coverage in PBS. Rejected:
  3.13 (free-threaded experimental, some deps lag), 3.11 (cuts off perf
  wins; only use if 3.12 surfaces compat issues).

- **D-06:** **CI downloads PBS tarballs once at release time** and vendors
  the extracted interpreter into each `@voss/cli-<triple>` subpackage. No
  download at install time. Reproducible across releases via pinned PBS
  release tag. Rejected: install-time download (breaks offline use),
  submodule/git-LFS (repo bloat).

- **D-07:** **Light prune** of vendored Python — drop `test/`, `idle/`,
  `tkinter/`, `lib2to3/`, `ensurepip` caches before tarballing. Saves
  ~15MB per platform. Keep stdlib + pip (D-08 uses pip to install wheel
  into site-packages). Rejected: no-prune (~30MB platform tarball acceptable
  but unnecessary), aggressive prune (risks runtime ImportError on obscure
  stdlib modules).

### Wheel source + version sync

- **D-08:** **Build wheel in CI at npm-publish time, vendor into subpackages.**
  Release workflow: runs `python -m build --wheel` (same path M5-06 already
  smoke-tests), bundles the resulting wheel into each
  `@voss/cli-<triple>` subpackage. No PyPI dependency, independent ship
  cadence. Wheel SHA recorded in a per-release manifest for audit.
  Rejected: pull-from-PyPI (forces PyPI publish prereq), both-PyPI-and-npm
  (doubles release surface; revisit for v0.1.1).

- **D-09:** **Pre-install wheel into vendored Python's site-packages at
  npm publish time.** Release workflow runs
  `<vendored-python>/bin/pip install <wheel>` once per platform before
  tarballing. End user gets zero install-time pip work — `npx voss --help`
  exits instantly post-install. Rejected: lazy install at first run
  (slow first-run, needs network), PEP-723/shiv/zipapp (broken with native
  C-extension deps).

- **D-10:** **Single source of truth for version = `pyproject.toml`.** A
  release script (`npm/scripts/bump-version.py` or similar) reads the voss
  version from pyproject.toml and regenerates `npm/package.json` plus the
  5 platform `package.json` files with matching version. Manual `bump`
  edits pyproject.toml only; npm versions follow automatically. Single git
  tag triggers single coordinated release. Rejected: independent versions
  (drift risk), hash-pinned (`0.1.0-g3a1b2c3`) — ugly for stable.

### Platform matrix + naming

- **D-11:** **Full 5-platform matrix** ships in v0.1: `darwin-arm64`,
  `darwin-x64`, `linux-x64`, `linux-arm64`, `win32-x64`. PBS covers all 5.
  Windows pain (path quoting, signal forwarding) is real but tractable
  for a JS shim that delegates to Python. ROADMAP M6 explicitly permits
  dropping `win32-x64` if vendoring proves expensive — that's the v0.1
  fallback, not the v0.1 plan. Rejected: minimal mac+linux-only.

- **D-12:** **Main package name = unscoped `voss`.** Cleanest UX:
  `npm i -g voss`, `npx voss`. Matches the Python wheel name 1:1. Requires
  npm registry name reservation per D-14. If `npm view voss` returns
  "taken" or namesquatted, fall back to scoped `@voss/cli` (researcher
  flags this at the planning step; M6-01 sets it).

- **D-13:** **Platform subpackages = scoped `@voss/cli-<platform>-<arch>`**
  using literal Node `process.platform-process.arch` strings:
  `@voss/cli-darwin-arm64`, `@voss/cli-darwin-x64`, `@voss/cli-linux-x64`,
  `@voss/cli-linux-arm64`, `@voss/cli-win32-x64`. Matches esbuild's
  `@esbuild/<triple>` pattern. Single org claim unlocks all 5 names.
  Rejected: unscoped `voss-<triple>` (5 separate name claims, squat risk).

- **D-14:** **Reserve npm names IMMEDIATELY as the first M6 task.** First
  M6 plan runs `npm view voss` + `npm view @voss/cli-darwin-arm64`; if
  available, publishes `0.0.0` placeholders to claim. Surfaces collisions
  early when there's still time to pivot to `@voss/cli`. Rejected:
  reserve-at-release (squat risk), prototype-under-scratch-scope (adds
  rename work).

### Claude's Discretion

- Exact pruning pattern for the vendored Python (D-07 names the targets;
  researcher refines the rm-list based on actual PBS layout).
- Release CI provider (GitHub Actions is the obvious choice; researcher
  picks the exact workflow file shape).
- Wheel-SHA verification mechanism (manifest format, signature method —
  researcher proposes; not gating ship).
- Signal-forwarding test approach for the JS shim (testing strategies vary;
  researcher picks).
- npm publish credentials handling — GitHub secret name, scope, npm
  org admin setup (logistical; researcher proposes).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v0.1 scope and product framing
- `.planning/PROJECT.md` — v0.1 harness-led; Rust = frozen spike; npm is the
  canonical distribution path for v0.1.
- `.planning/REQUIREMENTS.md` §NPM-01..05 — M6 acceptance contract.
- `.planning/ROADMAP.md` §"Phase M6: npm Wrapper" (lines ~274-311) — goal,
  required commands, success criteria, cross-cutting constraints.
- `.planning/HARNESS-PLAN.md` §0.2 + §M5/M6 — Rust deferred status, npm
  positioning.

### M5 outputs M6 depends on
- `.planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md` §D-16..D-19
  — wheel-smoke contract, README install-path lock, PyPI deferral rationale.
- `.planning/phases/M5-eval-and-distribution-prep/M5-06-SUMMARY.md` — proves
  the wheel builds + installs in a clean tempvenv; documents the packaging
  bug fixed (find-packages + `harness/agent/*.voss` package-data).
- `tests/packaging/test_wheel_install.py` — 3 @pytest.mark.slow tests; M6
  release pipeline should reuse the same `python -m build --wheel` invocation.

### Source-of-truth files M6 touches
- `pyproject.toml` — version source-of-truth (D-10). M6 release script reads
  the `voss` version here.
- `README.md` — already polished by M5-06 to the v0.1 framing; M6 promotes
  `npm i -g voss` to primary install once published.

### External references researcher MUST validate
- `https://github.com/astral-sh/python-build-standalone` — PBS source. Pick
  a release tag with all 5 target triples for the chosen Python version.
- esbuild npm package layout (`npm view esbuild` + read its source) —
  canonical reference for the optionalDependencies + per-platform-subpackage
  pattern. Mirror it.
- biome / swc / turbo npm package layouts — same pattern, useful for
  cross-checking edge cases (Windows path quoting, etc.).
- pyright npm package — alternative pattern (postinstall download). Useful
  as a contrast, not a model.

### Prior phase decisions (carry forward)
- M1 D-13 — `voss doctor` exit-code contract (0 or 1, never crash). M6
  smoke test must accept this window.
- M2 D-13/D-14 — `RunRecord.cost_usd` shape; npm wrapper does not touch.
- M4 — `voss check/compile voss/harness/agent/` directory-walk; the wheel
  ships `harness/agent/*.voss` as package-data (M5-06 fix). M6 must
  verify the compiled-harness opt-in (`VOSS_HARNESS=compiled`) still works
  post-`npm i`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `tests/packaging/test_wheel_install.py` — already proves the wheel builds +
  installs into a clean venv. M6 release CI can reuse this script's
  `_build_wheel` / `_make_venv` helpers (or call the test as a release-gate).
  The `cwd=repo` + `-o <tmp>` patterns are the right reference for any
  cross-cwd smoke.

- `pyproject.toml` — `[project.scripts] voss = "voss.cli:main"` is the only
  entry point. JS shim's spawn target is exactly `python -m voss.cli` (use
  the module form so it works even if console-script symlink is missing).

- `voss/cli.py:main` — Click group; supports `--help` at every level. M6
  smoke can test any subcommand's `--help` for zero-exit-code health.

- `voss/harness/diagnostics.py` `aggregate_exit_code` — returns 0 or 1
  (M1 D-13). The JS shim must preserve this exit code.

### Established Patterns

- **Monorepo with python source-of-truth** — `voss/`, `voss_runtime/`,
  `tests/` already live at repo root with `pyproject.toml`. Adding `npm/`
  as a peer subdir is consistent with this layout.

- **Atomic-write idiom in voss/cli.py:_write_text_atomic** — useful pattern
  if the release script needs to regenerate per-platform `package.json`
  files without races.

- **Test markers `slow` + `live`** are declared in `pyproject.toml`. M6's
  packaging-smoke test (NPM-04) should reuse `@pytest.mark.slow` so it
  participates in the existing fast/slow split.

### Integration Points

- **CI (`.github/workflows/ci.yml`)** — currently runs the fast Python test
  suite + `voss check` on harness sources. M6 adds a release-only workflow
  that fires on git tags (matches M5-06 wheel-smoke contract).

- **`.github/workflows/release.yml`** — this file currently triggers
  cargo-dist for the Rust binary release. **Critical: M6 must replace this
  workflow** with a Python-wheel-build + 6-npm-package-publish workflow.
  The Rust release workflow can be deleted or moved aside (matches the
  Rust=frozen-spike decision in PROJECT.md / STATE.md).

- **`samples/` directory** — required by `voss check`/`voss compile`
  smoke tests. The wheel doesn't ship `samples/`, so smoke tests inside the
  npm package must either embed a tiny `.voss` fixture in the test harness
  or run against an inline `<<EOF` string. (M5-06 test ran samples via
  `cwd=repo`; M6 npm smoke can't assume a repo cwd.)

</code_context>

<specifics>
## Specific Ideas

- The user explicitly said "if we have to register the npm package, so be it"
  — green light to claim `voss` (and `@voss` org) on npm immediately.
- The user wants installation to be **simple** — npm-only path with no Python
  prerequisite. The "feels installed" bar is `npm i -g voss && voss --help`
  exiting 0 in under 5 seconds on a machine that has never seen Python.
- esbuild was named as a reference pattern (esbuild-style optionalDependencies)
  earlier in the discussion. Mirror its package layout when in doubt.
- Pyright was named as the alternative pattern (postinstall download) and
  explicitly rejected for v0.1 — reference it only as a foil.

</specifics>

<deferred>
## Deferred Ideas

- **PyPI publish** — explicitly out of M6 scope per D-08. v0.1.1 candidate.
  When it lands, npm wrapper can optionally pull from PyPI instead of
  building wheel at release (D-08 path stays the default).
- **Homebrew formula** — DIST-02 in ROADMAP deferred-features list.
  Trigger: macOS install friction surfaces despite npm wrapper.
- **Rust shell resurrection** — `crates/` stays frozen. Trigger: real
  dogfood signal that bundled-Python startup latency or wheel size hurts
  users.
- **Signed wheels / sigstore** — security posture work for v0.1.1+.
- **Telemetry / install-failure detection** — out of v0.1 scope (full
  telemetry deferred).
- **`npm install voss` without `-g` use case** — running voss as a project-
  local dev dep. Not in NPM-01..05; revisit if real demand surfaces.
- **`@voss/sdk`** — separate npm package wrapping the Python SDK. Out of
  v0.1; revisit if JS embedders ask for a library API.

</deferred>

---

*Phase: M6-npm-wrapper*
*Context gathered: 2026-05-13*
