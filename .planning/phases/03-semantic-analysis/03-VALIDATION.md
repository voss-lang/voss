---
phase: 03
slug: semantic-analysis
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-07
---

# Phase 03 - Validation Strategy

Per-phase validation contract for semantic analysis execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/analyzer -q` |
| Full suite command | `pytest tests/parser tests/analyzer -q` |
| Estimated runtime | ~10-30 seconds after parser fixtures exist |

## Sampling Rate

- After every task commit: run `pytest tests/analyzer -q` once analyzer tests exist.
- After every plan wave: run `pytest tests/parser tests/analyzer -q`.
- Before `/gsd-verify-work`: full parser plus analyzer suite must be green.
- Max feedback latency: 60 seconds for default hermetic tests.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | ANLY-01 | T-03-01 | Diagnostics do not execute user code | unit | `pytest tests/analyzer/test_diagnostics.py tests/analyzer/test_probable.py -q` | No | pending |
| 03-02-01 | 02 | 2 | ANLY-02 | T-03-02 | Static estimator avoids provider/API calls | unit | `pytest tests/analyzer/test_ctx_budget.py -q` | No | pending |
| 03-03-01 | 03 | 3 | ANLY-03 | T-03-03 | Index paths remain inside `.voss-cache/` | unit | `pytest tests/analyzer/test_match_index.py -q` | No | pending |
| 03-04-01 | 04 | 4 | ANLY-01..03 | T-03-04 | Analyzer integrates without mutating AST | integration | `pytest tests/parser tests/analyzer -q` | No | pending |

## Wave 0 Requirements

- [ ] `tests/analyzer/test_diagnostics.py` - diagnostic shape, severity, code, span, and formatting coverage.
- [ ] `tests/analyzer/test_probable.py` - unguarded `probable<T>` warnings and confidence-gate narrowing.
- [ ] `tests/analyzer/test_ctx_budget.py` - deterministic static token-budget warnings.
- [ ] `tests/analyzer/test_match_index.py` - hermetic compile-time similar-case index emission.
- [ ] Fake embedding seam or fixture so default tests do not download sentence-transformers models.

## Manual-Only Verifications

All phase behaviors have automated verification. Optional live sentence-transformers smoke tests may be manual or marked slow, but they are not required for default verification.

## Validation Sign-Off

- [x] All tasks have automated verification or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verification.
- [x] Wave 0 covers all missing analyzer test files.
- [x] No watch-mode flags.
- [x] Feedback latency target is below 60 seconds for hermetic tests.
- [x] `nyquist_compliant: true` set in frontmatter.

Approval: approved 2026-05-07
