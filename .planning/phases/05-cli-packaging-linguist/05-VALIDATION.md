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
| Quick run command | `pytest tests/cli tests/tooling -q` |
| Full suite command | `pytest tests/parser tests/analyzer tests/codegen tests/cli tests/tooling -q` |
| Estimated runtime | ~30-90 seconds; editable-install smoke may be slower |

## Sampling Rate

- After every task commit: run the focused CLI/tooling test file for that plan.
- After every plan wave: run `pytest tests/cli tests/tooling -q`.
- Before `/gsd-verify-work`: run full parser/analyzer/codegen/CLI/tooling suite plus editable-install smoke.
- Max feedback latency: 90 seconds for default hermetic tests, excluding optional isolated-venv install checks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-00 | 01 | 1 | CLI-01..06, TOOL-01..03 | T-05-01 | Required parser/analyzer/codegen contracts exist before CLI work starts | preflight | `python3 - <<'PY' ... PY` contract check from `05-01-PLAN.md` | No | pending |
| 05-01-01 | 01 | 1 | CLI-01, CLI-06 | T-05-01 | Installed `voss` entrypoint exposes stable help without compiler fallbacks | unit/package | `pytest tests/cli/test_help.py tests/packaging/test_entrypoint.py -q` | No | pending |
| 05-02-01 | 02 | 2 | CLI-03, CLI-05 | T-05-02 | `check` and `ast` are read-only and preserve diagnostic/span fidelity | unit | `pytest tests/cli/test_check.py tests/cli/test_ast.py -q` | No | pending |
| 05-03-01 | 03 | 3 | CLI-01, CLI-02 | T-05-03 | `compile` and `run` orchestrate public APIs and isolate generated execution | unit/integration | `pytest tests/cli/test_compile.py tests/cli/test_run.py -q` | No | pending |
| 05-04-01 | 04 | 4 | CLI-04, TOOL-02 | T-05-04 | `init` writes valid scaffolds without overwriting user files accidentally | unit | `pytest tests/cli/test_init.py -q` | No | pending |
| 05-05-01 | 05 | 5 | TOOL-01, TOOL-03 | T-05-05 | Linguist assets and samples are internally consistent and representative | unit | `pytest tests/tooling/test_linguist_assets.py -q` | No | pending |
| 05-06-01 | 06 | 6 | CLI-01..06, TOOL-01..03 | T-05-06 | Editable install exposes console script and package data works outside repo layout | package smoke | `python3 -m pip install -e . && voss --help` | No | pending |

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
