# M6-05 Summary — Smoke Test + README

**Status:** ✅ Tasks 1–3 complete; Task 4 (real v0.1.0 publish) awaiting user gate
**Date:** 2026-05-13
**Plan:** [M6-05-PLAN.md](./M6-05-PLAN.md)
**Operator:** Claude Code (execute-plan)

## What Shipped

### `tests/packaging/test_npm_install.py` (NPM-04 smoke)
3 `@pytest.mark.slow` tests + 5 helpers. Module-level `pytestmark = pytest.mark.skipif(...)` skips cleanly when any of (`node`, `npm`, supported host triple, built `npm/platforms/<triple>/python`) is missing.

| Test | What it covers |
|------|----------------|
| `test_npm_pack_main` | `npm pack npm/` produces `vosslang-cli-*.tgz` |
| `test_npm_install_and_help` | Pack main + host platform → fresh node project → `npm install` both → `node node_modules/@vosslang/cli/bin/voss.js --help` exit 0 |
| `test_npm_smoke_full` | Same setup + `voss doctor` ∈ {0, 1} + `voss check smoke.voss` + `voss compile smoke.voss -o out.py` + `vendored python -c "import voss_runtime"` |

Inline `.voss` fixture body: `fn smoke() -> string { return "ok" }`. RESEARCH §9's suggested `agent SmokeAgent { }` is an early-draft syntax that the M2-final grammar rejects (parse error: expected LPAR, got '{'); the fixture was updated to a minimal `fn` form.

### Smoke run on host (darwin-arm64)
3/3 tests pass in 78.85 s. Full log + RESULT table in `.planning/phases/M6-npm-wrapper/M6-05-smoke-log.txt`. The vendored `python/` tree under `npm/platforms/darwin-arm64/` was built (159 MB) for the smoke and cleaned up afterwards; `.gitignore` ensures it cannot accidentally be committed.

### `README.md` updates (NPM-05)
- **Top-of-README badges added** (per user request for "common statuses"):
  - CI build status (Wineberry-io/Voss `ci.yml`)
  - npm version + npm downloads-per-month for `@vosslang/cli`
  - PyPI version for `voss`
  - Python 3.11+ supported
  - Node 18+ supported
  - MIT license
- **Install section reordered**: npm path is now the primary install. New structure:
  - `### Recommended: npm` → `npm i -g @vosslang/cli` (one-liner)
  - One paragraph describing the vendored Python 3.12 + zero manual Python setup + `voss doctor` first-run.
  - `### Alternative: pip` → `pip install voss` + `pip install 'voss[search]'` for semantic-memory extras (calls out the M6-04 D-3 optionalization).
- "Python harness" framing line, `voss doctor` mention, `samples/` link all preserved (existing test_readme assertions still green).
- Roadmap line updated: `npm i -g voss` → `npm i -g @vosslang/cli` (reflects M6-01 D-1 scope substitution).

### `tests/packaging/test_readme.py` extensions
Added 2 new tests (total 7, all pass in 0.02 s):

| Test | Assertion |
|------|-----------|
| `test_npm_install_voss_cli_present` | README contains `npm i -g @vosslang/cli` OR `npm install -g @vosslang/cli` |
| `test_npm_install_is_primary_over_pip` | npm install string appears at a lower offset than `pip install voss` (npm first in source-text order) |

## Deviations from Plan

| # | Deviation | Reason |
|---|-----------|--------|
| D-1 | `@voss/cli` references substituted to `@vosslang/cli` everywhere (README, tests, badges) | Carried forward from M6-01 D-1 (org `voss` was already claimed on npmjs.com). |
| D-2 | README badges added beyond plan scope | User asked for "statuses that are common in other readmes" during M6-05 execution. Added 7 shields.io / GitHub Actions badges. |
| D-3 | Inline `.voss` fixture body changed from `agent SmokeAgent { }` (RESEARCH §9) to `fn smoke() -> string { return "ok" }` | First fixture failed `voss check` with `parse error: expected LPAR, got character '{'` — bare-block agent syntax was an early draft that did not survive M2's grammar finalization. Documented in M6-05-smoke-log.txt. |
| D-4 | README references `voss extras install search` (implicit, via the friendly ModuleNotFoundError emitted from `voss_runtime/*/semantic.py`) but the actual subcommand does NOT yet exist | This is the v0.1.x follow-up surfaced in M6-04 D-3. The README's `pip install 'voss[search]'` line is the canonical workaround for v0.1; `voss extras install search` will land later. |

## Files Changed

| Status | Path |
|--------|------|
| Added | `tests/packaging/test_npm_install.py` (3 slow tests, 5 helpers) |
| Modified | `tests/packaging/test_readme.py` (2 new assertions; total 7) |
| Modified | `README.md` (7 badges added; Install section reordered; roadmap line updated) |
| Added | `.planning/phases/M6-npm-wrapper/M6-05-smoke-log.txt` |
| Added | `.planning/phases/M6-npm-wrapper/M6-05-SUMMARY.md` |

## Task 4 — [BLOCKING] v0.1.0 Publish Gate

Outstanding decisions for the user before the real `v0.1.0` tag push:

1. **macos-13 runner blocker** (M6-04 D-5). The darwin-x64 runner stalled in the free-tier queue for 20+ minutes during M6-04. Real v0.1.0 ship needs a deterministic publish path for that platform. Options on the table:
   - Wait longer (gambling on queue availability — unsuitable for a tagged release).
   - Drop darwin-x64 from v0.1 matrix; add back in v0.1.x. Loses Intel Mac coverage.
   - Cross-build under Rosetta-on-Linux (CI-side equivalent of the local workaround used in M6-04).
   - Pay for `macos-13-large` minutes.
2. **NPM_TOKEN rotation** (M6-04 D-4). The Bypass-2FA Granular token entered the conversation transcript; revoke at npmjs.com + replace the `NPM_TOKEN` repo secret before tagging v0.1.0.
3. **`latest` tag hygiene**: release.yml currently passes no `--tag` flag, so the v0.1.0 publish will move `latest` from `0.1.0-rc3` → `0.1.0` (desired). Future prereleases (v0.1.0-rc4, v0.2.0-beta1, etc) should use `--tag next` so they don't clobber `latest`. v0.2 work item.
4. **Stale CI runs / npm-version-sync regression**: master is currently at `pyproject.toml = 0.1.0` and all 6 npm manifests at 0.1.0 — `npm-version-sync` ci.yml job should pass. Confirm green on master before tagging.
5. **LICENSE file** still missing at repo root (M6-01 D-X). The README license badge points at `LICENSE` (404 today). Add a real `LICENSE` file (MIT, matching the package.json `license` field across all 6 manifests + `pyproject.toml`-implied license) before tagging.

Reply `publish 0.1.0` to authorize the tag push + workflow trigger, or `hold: <reason>` to close M6 in "Ready to release" state without the real tag.

## Hand-off

Once Task 4 returns `publish 0.1.0` and the workflow goes green, M6 is complete and the v0.1 ship contract from `ROADMAP.md` is honored:

- `npm i -g @vosslang/cli` works on darwin-arm64, darwin-x64, linux-x64, linux-arm64, win32-x64.
- `pip install voss` continues to work via PyPI (once published — separate cadence).
- `voss[search]` optional extra carries the heavy semantic-memory deps; default install is ~159 MB unpacked.
- README's install instructions point users at the npm-first path; test_readme.py pins the docs invariants so drift breaks CI.
- All M6 follow-ups are documented in the per-phase summaries (M6-01..M6-05) for v0.1.x and v0.2 work.

## Task 4 Resolution — v0.1.0 SHIPPED

**Date:** 2026-05-15
**Decision:** Published

### Publish path
- 4/5 platforms published cleanly via CI workflow_dispatch run 25868604410 after NPM_TOKEN rotation to a properly-Bypass-2FA Granular token (3rd attempt; first two were Classic-form with the Bypass-2FA box accidentally off post-form-submit).
- darwin-x64 + publish-main were dispatched twice but the macos-13 free-tier runner queue stalled both times. Cancelled the dispatch and published darwin-x64 + main locally from this dev host:
  - `arch -x86_64 python3 npm/scripts/build_platform.py darwin-x64 --wheel dist/voss-0.1.0-py3-none-any.whl --out npm/platforms/darwin-x64/python` produced a 165 MB site-packages tree under Rosetta in 28.8 s.
  - `cd npm/platforms/darwin-x64 && npm publish --access public` → `+ @vosslang/cli-darwin-x64@0.1.0` (74.5 MB compressed, 228.5 MB unpacked, 13706 files).
  - `cd npm && npm publish --access public` → `+ @vosslang/cli@0.1.0` (1.6 kB).

### Registry state at ship
| Package | Version | Tarball size (gzip) |
|---------|---------|-------|
| @vosslang/cli | 0.1.0 | 1.6 kB |
| @vosslang/cli-darwin-arm64 | 0.1.0 | ~75 MB |
| @vosslang/cli-darwin-x64 | 0.1.0 | 74.5 MB |
| @vosslang/cli-linux-x64 | 0.1.0 | ~75 MB |
| @vosslang/cli-linux-arm64 | 0.1.0 | ~75 MB |
| @vosslang/cli-win32-x64 | 0.1.0 | ~75 MB |

### End-to-end install smoke (darwin-arm64, fresh /tmp project)
```
$ npm install @vosslang/cli@0.1.0
added 2 packages, and audited 3 packages in 4s
found 0 vulnerabilities

$ node node_modules/@vosslang/cli/bin/voss.js --help
Usage: python -m voss.cli [OPTIONS] COMMAND [ARGS]...
  voss — compiler and agent.
  Compiler verbs : compile · run · check · init · ast Agent verbs : do · chat · edit · doctor · tools · config
  ...
$ echo $?
0

$ node node_modules/@vosslang/cli/bin/voss.js doctor
  ✓  project dirs    .voss/, .voss-cache/ creatable
  ✓  harness cache   no harness sources
  ...
$ echo $?
0
```

### Repo state at ship
- Repo: voss-lang/voss (transferred from bm9797/Voss → Wineberry-io/Voss → voss-lang/voss during M6 execution)
- 6 npm manifests have `repository.url = git+https://github.com/voss-lang/voss.git` and matching homepage.
- Branch protection on master (PR required, required CI checks, no force-push, no delete).
- Tag ruleset on v* (no force-push, no deletion; admin bypass).
- LICENSE (MIT) added.
- README badges point at voss-lang/voss (CI, npm version, npm downloads, PyPI version, Python 3.11+, Node 18+, MIT license).

### M6 milestone close-out
All five plans M6-01..M6-05 complete. Names claimed, build pipeline proven, release workflow exercised on rc1/rc2/rc3/v0.1.0 tags, README + tests pinned, real v0.1.0 published, end-to-end install smoke green.

### Open follow-ups (v0.1.x or v0.2)
1. **macos-13 darwin-x64 runner bottleneck**: free-tier queue stalled twice during rc2/v0.1.0 publishes; resolved by Rosetta-on-this-host local publish. Investigate cross-build via Rosetta-on-Linux (osxcross) or accept paid `macos-13-large` minutes for v0.2.
2. **Token hygiene**: the bypass-2fa token used for darwin-x64 + main local publish entered the conversation transcript (90-day expiration). Consider rotating again now that v0.1 is shipped; the npm registry doesn't need it again until v0.1.1.
3. **`latest` tag hygiene**: rc1/rc2/rc3 prereleases each advanced npm `latest`. v0.1.0 ship correctly takes `latest`. Future prereleases (v0.1.0-rc4, v0.2.0-beta1) should use `--tag next` in release.yml so they don't move `latest`.
4. **dev → master merge**: this session's URL fixes + favicon assets + summaries live on `dev`. Merge to `master` via PR once branch protection's required-checks workflow finishes; eventually re-tag if a v0.1.1 cuts the merged history.
5. **`voss extras install search` subcommand**: the friendly ModuleNotFoundError tells users to `pip install 'voss[search]'`, which is awkward on the npm-installed path. A v0.1.x feature to expose `voss extras install search` (uses the vendored pip to extend the vendored python) closes the UX gap.
6. **Other URL references**: Cargo.toml + dist-workspace.toml + generated `site/out/__next._full.txt` still reference older repo URLs; update on the next Rust-spike unfreeze pass.

🚢 v0.1 shipped to npm at @vosslang/cli@0.1.0. Users can now run `npm i -g @vosslang/cli` to get the full Voss CLI with vendored Python and zero manual setup.
