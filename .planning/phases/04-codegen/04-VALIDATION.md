---
phase: 04
slug: codegen
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-07
---

# Phase 04 - Validation Strategy

Per-phase validation contract for Voss code generation.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/codegen -q` |
| Full suite command | `pytest tests/parser tests/analyzer tests/codegen -q` |
| Estimated runtime | ~15-45 seconds with hermetic stubs |

## Sampling Rate

- After every task commit: run the focused `tests/codegen/*` file for that plan.
- After every plan wave: run `pytest tests/codegen -q`.
- Before `/gsd-verify-work`: run `pytest tests/parser tests/analyzer tests/codegen -q`.
- Max feedback latency: 60 seconds for default hermetic codegen tests.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-00 | 01 | 1 | GEN-01..05 | T-04-01 | Required Phase 2/3 contracts exist before codegen work starts | preflight | `python - <<'PY' ... PY` contract check from `04-01-PLAN.md` | No | pending |
| 04-01-01 | 01 | 1 | GEN-01, GEN-02 | T-04-01 | Writer and imports produce deterministic readable Python | unit | `pytest tests/codegen/test_writer.py tests/codegen/test_imports.py -q` | No | pending |
| 04-02-01 | 02 | 2 | GEN-01, GEN-02 | T-04-02 | Expression and basic statement lowering never executes user code | unit | `pytest tests/codegen/test_expressions.py tests/codegen/test_statements.py -q` | No | pending |
| 04-03-01 | 03 | 3 | GEN-01, GEN-03 | T-04-03 | Runtime primitive lowering targets async runtime APIs correctly | unit | `pytest tests/codegen/test_runtime_constructs.py -q` | No | pending |
| 04-04-01 | 04 | 4 | GEN-01, GEN-04 | T-04-04 | Semantic routing and user imports use declared/indexed dependencies only | unit | `pytest tests/codegen/test_semantic_match.py tests/codegen/test_imports.py -q` | No | pending |
| 04-05-01 | 05 | 5 | GEN-01, GEN-05 | T-04-05 | Agents, tools, prompts, classes generate readable executable Python | unit | `pytest tests/codegen/test_agents_tools_prompts.py -q` | No | pending |
| 04-06-01 | 06 | 6 | GEN-01..05 | T-04-06 | PRD examples compile, parse as Python, and run with deterministic stubs | integration | `pytest tests/codegen/test_examples.py -q` | No | pending |

## Wave 0 Requirements

- [ ] `tests/codegen/test_writer.py` - indentation, blank-line, and `ast.parse` checks.
- [ ] `tests/codegen/test_imports.py` - minimal deterministic imports and `use foo::bar` lowering.
- [ ] `tests/codegen/test_expressions.py` - literals, calls, members, indexes, lambdas, spawn, gather.
- [ ] `tests/codegen/test_statements.py` - `fn`, `let`, `return`, `if`, top-level async `main`.
- [ ] `tests/codegen/test_runtime_constructs.py` - `ctx`, `within/fallback`, `try/catch`, memory declarations.
- [ ] `tests/codegen/test_semantic_match.py` - Phase 3 index-manifest consumption without recomputing embeddings.
- [ ] `tests/codegen/test_agents_tools_prompts.py` - `agent`, `spawn/gather`, `@tool`, prompts, Pydantic classes.
- [ ] `tests/codegen/test_examples.py` - PRD example codegen and semantic-equivalence coverage.

## Manual-Only Verifications

All default Phase 4 behaviors have automated verification. Live provider/model execution is out of scope for Phase 4 and should remain manual or deferred to later example-validation phases.

## Validation Sign-Off

- [x] All tasks have automated verification or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verification.
- [x] Wave 0 covers all missing codegen test files.
- [x] No watch-mode flags.
- [x] Feedback latency target is below 60 seconds for hermetic tests.
- [x] `nyquist_compliant: true` set in frontmatter.

Approval: approved 2026-05-07
