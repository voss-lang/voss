---
phase: 06
slug: examples-validation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-08
---

# Phase 06 - Validation Strategy

Per-phase validation contract for proving the three PRD section 7 examples compile, check, run, and match their raw Python equivalents.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest + subprocess + Click/installed CLI smoke |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/examples -q` |
| Full suite command | `pytest tests/parser tests/analyzer tests/codegen tests/cli tests/examples -q` |
| Optional live command | `pytest tests/examples -q -m live` |
| Estimated runtime | ~60-180 seconds for hermetic tests; live provider tests depend on provider latency |

## Sampling Rate

- After every task commit: run the focused example test file for that plan.
- After every plan wave: run `pytest tests/examples -q`.
- Before `/gsd-verify-work`: run full parser/analyzer/codegen/CLI/example suite plus editable-install `voss --help`.
- Max feedback latency: 180 seconds for default hermetic tests, excluding optional live provider checks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-0 | 01 | 1 | EX-01..03 | T-06-01 | Required Phase 1-5 runtime/compiler/CLI contracts exist before example validation starts | preflight | `python3 - <<'PY' ... PY` contract check from `06-01-PLAN.md` | No | pending |
| 06-01-1 | 01 | 1 | EX-01..03 | T-06-01 | Shared helpers execute generated modules hermetically with `StubProvider` and temp cache dirs | unit | `pytest tests/examples/test_helpers.py -q` | No | pending |
| 06-01-2 | 01 | 1 | EX-01 | T-06-01 | `classify.voss` check/compile/run matches raw Python for confident and low-confidence cases | integration | `pytest tests/examples/test_classify_e2e.py -q` | No | pending |
| 06-02-0 | 02 | 2 | EX-02 | T-06-02 | Contract marker is confirmed before support example validation | preflight | marker check or rerun `06-01-0` gate | No | pending |
| 06-02-1 | 02 | 2 | EX-02 | T-06-02 | `support.voss` semantic routing uses fake indexes/encoder and matches raw Python routes | integration | `pytest tests/examples/test_support_e2e.py -q` | No | pending |
| 06-03-0 | 03 | 3 | EX-03 | T-06-03 | Contract marker is confirmed before research example validation | preflight | marker check or rerun `06-01-0` gate | No | pending |
| 06-03-1 | 03 | 3 | EX-03 | T-06-03 | `research.voss` spawn/gather and within/fallback paths match raw Python under stubs | integration | `pytest tests/examples/test_research_e2e.py -q` | No | pending |
| 06-04-0 | 04 | 4 | EX-01..03 | T-06-04 | Contract marker is confirmed before full matrix validation | preflight | marker check or rerun `06-01-0` gate | No | pending |
| 06-04-1 | 04 | 4 | EX-01..03 | T-06-04 | All examples pass `voss check`, `voss compile` + `python3`, and `voss run` through CLI surfaces | integration | `pytest tests/examples/test_cli_matrix.py -q` | No | pending |
| 06-04-2 | 04 | 4 | EX-01..03 | T-06-04 | Optional live-provider tests are marked and skipped unless credentials/config are explicit | live/optional | `pytest tests/examples -q -m live` | No | pending |
| 06-04-3 | 04 | 4 | EX-01..03 | T-06-04 | Full suite and install smoke pass with no repo-local `.voss-cache` or generated artifacts | package smoke | `pytest tests/parser tests/analyzer tests/codegen tests/cli tests/examples -q` | No | pending |

## Wave 0 Requirements

- [ ] `tests/examples/__init__.py` - examples test package marker.
- [ ] `tests/examples/helpers.py` - shared temp-project, CLI, generated-module, stub-provider, and cache-artifact assertions.
- [ ] `tests/examples/test_helpers.py` - helper behavior and no repo-local side effects.
- [ ] `tests/examples/test_classify_e2e.py` - EX-01 confident/low-confidence check/compile/run parity.
- [ ] `tests/examples/test_support_e2e.py` - EX-02 semantic route/fallback parity with fake embeddings/indexes.
- [ ] `tests/examples/test_research_e2e.py` - EX-03 happy path and budget fallback parity with stubs.
- [ ] `tests/examples/test_cli_matrix.py` - all examples through `voss check`, `voss compile`, `python3 generated.py`, and `voss run`.
- [ ] Optional live tests must use `@pytest.mark.live` and skip when provider configuration is absent.

## Manual-Only Verifications

- Running against live Anthropic/OpenAI/Ollama providers is optional for Phase 6 and must never run in the default test path.
- Manual live verification should record provider, model, command, sanitized output summary, and date in the execution summary.

## Validation Sign-Off

- [x] All tasks have automated verification or a preflight gate.
- [x] Sampling continuity: no 3 consecutive tasks without automated verification.
- [x] Wave 0 covers all missing example-validation test files.
- [x] No watch-mode flags.
- [x] Default tests are hermetic and provider-free.
- [x] `nyquist_compliant: true` set in frontmatter.

Approval: approved 2026-05-08
