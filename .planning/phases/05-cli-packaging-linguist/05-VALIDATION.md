---
phase: 05
slug: cli-packaging-linguist
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-08
---

# Phase 05 - Validation Strategy

Per-phase validation contract for Voss CLI, packaging, scaffolding, and Linguist assets.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest + Click CliRunner + subprocess |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/cli -q` through Wave 4; `pytest tests/cli tests/tooling -q` after Wave 5 creates `tests/tooling/` |
| Full suite command | `pytest tests/parser tests/analyzer tests/codegen tests/cli tests/tooling -q` |
| Estimated runtime | ~30-90 seconds; editable-install smoke may be slower |

## Sampling Rate

- After every task commit: run the focused CLI/tooling test file for that plan.
- After Waves 1-4: run `pytest tests/cli -q`.
- After Waves 5-6: run `pytest tests/cli tests/tooling -q`.
- Before `/gsd-verify-work`: run full parser/analyzer/codegen/CLI/tooling suite plus editable-install smoke.
- Max feedback latency: 90 seconds for default hermetic tests, excluding optional isolated-venv install checks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-0 | 01 | 1 | CLI-01..06, TOOL-01..03 | T-05-01 | Required parser/analyzer/codegen contracts exist before CLI work starts | preflight | `python3 - <<'PY' ... PY` contract check from `05-01-PLAN.md` | No | pending |
| 05-01-1 | 01 | 1 | CLI-01, CLI-06 | T-05-01 | Help and packaging tests are created before implementation | unit/package | `pytest tests/cli/test_help.py tests/packaging/test_entrypoint.py -q` | No | pending |
| 05-01-2 | 01 | 1 | CLI-01, CLI-06 | T-05-01 | Click shell imports without provider/compiler side effects | unit | `pytest tests/cli/test_help.py -q` | No | pending |
| 05-01-3 | 01 | 1 | CLI-06 | T-05-01 | Console-script metadata targets `voss.cli:main` | package | `pytest tests/cli/test_help.py tests/packaging/test_entrypoint.py -q` | No | pending |
| 05-02-0 | 02 | 2 | CLI-03, CLI-05 | T-05-02 | Contract marker is confirmed before read-only commands are edited | preflight | marker check or rerun `05-01-0` gate | No | pending |
| 05-02-1 | 02 | 2 | CLI-05 | T-05-02 | `ast` test proves JSON output and no cache/output writes | unit | `pytest tests/cli/test_ast.py -q` | No | pending |
| 05-02-2 | 02 | 2 | CLI-03 | T-05-02 | `check` test proves diagnostics, warning policy, and no cache writes | unit | `pytest tests/cli/test_check.py -q` | No | pending |
| 05-02-3 | 02 | 2 | CLI-03, CLI-05 | T-05-02 | `ast` and `check` remain read-only and avoid execution | unit | `pytest tests/cli/test_ast.py tests/cli/test_check.py -q` | No | pending |
| 05-03-0 | 03 | 3 | CLI-01, CLI-02 | T-05-03 | Contract marker is confirmed before write/execute commands are edited | preflight | marker check or rerun `05-01-0` gate | No | pending |
| 05-03-1 | 03 | 3 | CLI-01 | T-05-03 | `compile` writes only after parse/analyze/codegen success | unit | `pytest tests/cli/test_compile.py -q` | No | pending |
| 05-03-2 | 03 | 3 | CLI-02 | T-05-03 | `run` uses subprocess and forwards status/output | unit | `pytest tests/cli/test_run.py -q` | No | pending |
| 05-03-3 | 03 | 3 | CLI-01, CLI-02 | T-05-03 | Compile/run commands have no in-process generated-code execution | unit/integration | `pytest tests/cli/test_compile.py tests/cli/test_run.py -q` | No | pending |
| 05-04-0 | 04 | 4 | CLI-04, TOOL-02 | T-05-04 | Contract marker is confirmed before scaffold edits | preflight | marker check or rerun `05-01-0` gate | No | pending |
| 05-04-1 | 04 | 4 | CLI-04, TOOL-02 | T-05-04 | Init tests cover scaffold, `.gitattributes`, and overwrite safety | unit | `pytest tests/cli/test_init.py -q` | No | pending |
| 05-04-2 | 04 | 4 | CLI-04, TOOL-02, CLI-06 | T-05-04 | Templates are package data and parseable | unit/package | `pytest tests/cli/test_init.py -q` | No | pending |
| 05-04-3 | 04 | 4 | CLI-04, TOOL-02 | T-05-04 | Init command writes only project-local scaffold files | unit | `pytest tests/cli/test_init.py -q` | No | pending |
| 05-05-0 | 05 | 5 | TOOL-01, TOOL-03 | T-05-05 | Contract marker is confirmed before Linguist asset edits | preflight | marker check or rerun `05-01-0` gate | No | pending |
| 05-05-1 | 05 | 5 | TOOL-01, TOOL-03 | T-05-05 | Tooling tests cover `.gitattributes`, samples, metadata, and fallback fields | unit | `pytest tests/tooling/test_linguist_assets.py -q` | No | pending |
| 05-05-2 | 05 | 5 | TOOL-01 | T-05-05 | Repo `.gitattributes` contains the exact Voss Linguist line | unit | `python3 - <<'PY' ... PY` gitattributes check | No | pending |
| 05-05-3 | 05 | 5 | TOOL-03 | T-05-05 | Representative samples parse without provider/runtime execution | unit | `python3 - <<'PY' ... PY` sample parse check | No | pending |
| 05-05-4 | 05 | 5 | TOOL-01, TOOL-03 | T-05-05 | Metadata declares draft status plus Python fallback metadata without overclaiming support | unit | `python3 - <<'PY' ... PY` metadata check | No | pending |
| 05-06-0 | 06 | 6 | CLI-01..06, TOOL-01..03 | T-05-06 | Contract marker is confirmed before integration/package smoke | preflight | marker check or rerun `05-01-0` gate | No | pending |
| 05-06-1 | 06 | 6 | CLI-06 | T-05-06 | Editable install exposes console script and package data | package smoke | `pytest tests/packaging/test_entrypoint.py -q` | No | pending |
| 05-06-2 | 06 | 6 | CLI-01..05, TOOL-01..02 | T-05-06 | Full CLI smoke covers init/ast/check/compile/run hermetically | integration | `pytest tests/cli/test_integration.py -q` | No | pending |
| 05-06-3 | 06 | 6 | CLI-01..06, TOOL-01..03 | T-05-06 | Package/integration fixes stay inside Phase 5 surfaces | integration/package | `pytest tests/packaging/test_entrypoint.py tests/cli/test_integration.py -q` | No | pending |
| 05-06-4 | 06 | 6 | CLI-01..06, TOOL-01..03 | T-05-06 | Full Phase 5 suite and install smoke pass with no repo-local cache artifacts | package smoke | `python3 -m pip install -e . && voss --help` | No | pending |

## Wave 0 Requirements

- [ ] `tests/cli/test_help.py` - root/subcommand help and Click command discovery.
- [ ] `tests/cli/test_ast.py` - `voss ast` JSON output via `to_dict`.
- [ ] `tests/cli/test_check.py` - analyzer diagnostic display, `ANLY001`, warning/error exits, no cache writes.
- [ ] `tests/cli/test_compile.py` - parse/analyze/generate/write pipeline and analyzer-error blocking.
- [ ] `tests/cli/test_run.py` - subprocess execution and exit-code forwarding.
- [ ] `tests/cli/test_init.py` - scaffold files, `.gitattributes`, non-empty-dir safety, scaffold parsing.
- [ ] `tests/tooling/test_linguist_assets.py` - repo `.gitattributes`, `samples/*.voss`, local language metadata.
- [ ] `tests/packaging/test_entrypoint.py` - entrypoint/import/package-data smoke.

## Manual-Only Verifications

Full wheel/sdist publishing is out of scope for Phase 5. Editable install and package-data smoke tests are required; wheel/sdist checks can be added if packaging defects appear.

## Validation Sign-Off

- [x] All tasks have automated verification or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verification.
- [x] Wave 0 covers all missing CLI/tooling/packaging test files.
- [x] No watch-mode flags.
- [x] Feedback latency target is below 90 seconds for default hermetic tests.
- [x] `nyquist_compliant: true` set in frontmatter.

Approval: approved 2026-05-08
