# M6-03 Summary — Build Pipeline

**Status:** ✅ Complete (with size-budget deviation approved by user)
**Date:** 2026-05-13
**Plan:** [M6-03-PLAN.md](./M6-03-PLAN.md)
**Operator:** Claude Code (execute-plan)

## What Shipped

### `npm/scripts/bump_version.py` (~75 LOC, executable)
Version-sync from `pyproject.toml [project].version` into the npm tree. CLI:
- `bump_version.py` — updates all 6 package.jsons + `optionalDependencies` pins in the main package
- `bump_version.py main` — main package only
- `bump_version.py <triple>` — one platform manifest only

2-space indent + trailing newline (matches M6-01 placeholder format).

### `npm/scripts/prune_pbs.py` (~120 LOC, executable)
Auto-detects Unix vs Windows shape from sentinel files (`python/bin/python3` vs `python/python.exe`). Removes RESEARCH §4 targets:
- **Unix**: `include/`, `lib/python3.12/{idlelib,tkinter,lib2to3,ensurepip,turtledemo}`, `share/`, `lib/{itcl,tcl,tk,thread}*`, `bin/{2to3,idle3,python3-config}*`
- **Windows**: `include/`, `Lib/{idlelib,tkinter,lib2to3,turtledemo}`, `tcl/`, `pythonw.exe`

Idempotent. Missing targets are not errors (PBS layout evolves). `--dry-run` supported.

### `npm/scripts/pbs_manifest.json`
Pinned: `pbs_release=20260510`, `python_version=3.12.13`, url_template, 5 triple entries with `pbs_triple` + `sha256`. Host triple (`darwin-arm64`) sha pinned in Task 3 (`55bc1a5edbc8ac4da0081f4f5731ed2d1ed10c57cb37a820b2a0dbc7cad742e9`). 4 other triples remain `PENDING`; M6-04 CI runners capture them on first build.

### `npm/scripts/build_platform.py` (~200 LOC, executable)
9 functions per plan spec: `load_manifest`, `download_pbs`, `verify_sha256`, `extract_pbs`, `run_prune`, `install_wheel`, `measure_site_packages`, `ensure_wheel`, `main`. Wires the full pipeline: build/accept wheel → download PBS → verify sha → extract → prune → pip install → measure → gate on `SIZE_BUDGET_MB`. Emits `SITE_PACKAGES_SIZE_MB=<N>` for CI grep.

### `tests/packaging/test_npm_scripts.py` — 8 fast tests, all pass
| Test | Coverage |
|------|----------|
| `test_bump_all_rewrites_six_files` | full-tree update + optionalDependencies refresh |
| `test_bump_main_only_touches_main_pkg` | scoped update — main |
| `test_bump_single_triple_only_touches_that_platform` | scoped update — single platform |
| `test_bump_uses_two_space_indent_and_trailing_newline` | output format invariants |
| `test_bump_rejects_invalid_target` | CLI validation |
| `test_prune_unix_removes_idlelib_tkinter_include_keeps_site_packages` | Unix prune target set |
| `test_prune_is_idempotent` | re-runs harmless |
| `test_prune_windows_shape_detected_and_targets_removed` | sentinel-file shape detection on a non-Win host |

Total runtime: 0.92 s.

### `.planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt`
Full stdout/stderr of the host build run + structured `## RESULT` table + `## DECISION` block. Captures the PBS sha, all 1133 MB of size-offender breakdown, and the user's option-(c) approval.

## Task 3 — End-to-End Host Build Result

| Field | Value |
|-------|-------|
| Host triple | darwin-arm64 |
| Wall-clock | 69.6 s |
| PBS tarball | 23.8 MB |
| **SITE_PACKAGES_SIZE_MB** | **1133** |
| Vendored `python -m voss.cli --help` | ✅ exit 0 |
| Vendored python isolation | ✅ resolves voss.cli inside vendored site-packages when cwd≠repo |
| `build_platform.py` exit (with original 300 MB cap) | 1 (SIZE_BUDGET_EXCEEDED) |

Top size offenders: `torch 436M`, `transformers 97M`, `scipy 97M`, `litellm 81M`, `sympy 72M`, `onnxruntime 71M`, `chromadb_rust_bindings 49M`, `sklearn 46M`.

## Task 4 — [BLOCKING] Decision

**User selected option (c): raise `SIZE_BUDGET_MB` to 1500 MB and ship as-is.**

Rationale (captured verbatim in the host-build log §DECISION):
- Option (a) infeasible (sentence-transformers requires torch).
- Option (b) reduces to ~400 MB — still over 300; significant refactor for marginal win.
- Option (d) defers complexity into runtime with offline-failure mode.
- Option (c) ships a complete v0.1 with full feature parity at the cost of one-time install latency, which matches NPM-02's stated goal of "one-command install of a complete Voss runtime".

**Code change**: `npm/scripts/build_platform.py` line 38 — `SIZE_BUDGET_MB = 1500` (was 300). Inline comment + module docstring updated to cite the M6-03 §DECISION. Future re-evaluation flagged for v0.2 (move semantic-memory deps behind `voss[search]` extra).

## Deviations from Plan

| # | Deviation | Reason |
|---|-----------|--------|
| D-1 | `SIZE_BUDGET_MB` raised from 300 → 1500 | Task 4 user decision. The plan's static verify checked for the literal `SIZE_BUDGET_MB = 300`; that check is now obsolete. The functional gate still works — exits 1 if size exceeds the (raised) cap. |
| D-2 | Module docstring updated to reference the new cap | Avoid future-reader confusion. The original "300 MB is the hard cap from RESEARCH §5 Risk 2" line is now "1500 is the v0.1 cap raised from RESEARCH §5 Risk 2's original 300 MB target". |
| D-3 | Build run was triggered from the repo root (cwd=repo); during sanity-check, voss.cli initially appeared to resolve to the source tree, not the vendored copy | This was a cwd=repo artifact, not a real isolation breach. Re-running the import test from `cd /tmp` showed voss.cli correctly loaded from `<vendored>/lib/python3.12/site-packages/voss/cli.py`. Documented in §RESULT. No code change. |

## Files Changed

| Status | Path |
|--------|------|
| Added | `npm/scripts/bump_version.py` |
| Added | `npm/scripts/prune_pbs.py` |
| Added | `npm/scripts/build_platform.py` |
| Added | `npm/scripts/pbs_manifest.json` (darwin-arm64 sha pinned; 4 others PENDING) |
| Added | `tests/packaging/test_npm_scripts.py` (8 tests) |
| Added | `.planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt` (with §RESULT + §DECISION) |
| Added | `.planning/phases/M6-npm-wrapper/M6-03-SUMMARY.md` |
| Modified | `npm/package.json` + 5 platform package.jsons (version 0.0.0 → 0.1.0 via bump_version.py — this is the first real version sync, anchoring to `pyproject.toml`'s `0.1.0`) |

## Hand-off to M6-04

M6-04 builds the GitHub Actions release workflow that fans out across 5 platform runners and publishes the real 0.1.0 artifacts. Each runner will:

1. Run `bump_version.py` (idempotent — version already 0.1.0 from this plan, but the workflow re-runs to be defensive).
2. Run `build_platform.py <triple> --out npm/platforms/<triple>/python` — for triples other than darwin-arm64 this will print `SHA256(...)=...` and prompt the developer to update `pbs_manifest.json` BEFORE the workflow can publish. M6-04 needs a CI step that either (a) auto-commits the captured shas back to master via a bot account, or (b) requires the first per-triple build to be run manually by a developer who commits the shas, and subsequent builds verify against them. Recommendation: option (b) for v0.1 — safer.
3. Run `bump_version.py` again post-build (no-op if version is current; defensive).
4. `npm publish --access public` against each `npm/platforms/<triple>` + the main `npm/`.

The placeholder publishes from M6-01 are at 0.0.0; M6-04's real publishes will be at 0.1.0 and will become the `latest` tag automatically.

## Open Follow-Ups (v0.2)

- Optionalize `sentence-transformers`, `chromadb`, `onnxruntime`, `sklearn` behind a `voss[search]` extra; npm wrapper installs the no-extras default. Reset `SIZE_BUDGET_MB` to a sane <500 MB cap.
- Investigate `sentence-transformers-onnx` (no torch dependency) as a drop-in for the embedding pipeline.
- Investigate sqlite-vss as a chromadb replacement.
- Add an `npm pack --dry-run` size sanity check inside `build_platform.py` post-move so the compressed tarball size (which is what end-users actually download) is also visible in CI logs.
