---
phase: M3
slug: language-validation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-11
---

# Phase M3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: derived from `M3-RESEARCH.md §Validation Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x (auto mode) — pyproject.toml:25-26, 39-46 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]` block at line 39) |
| **Quick run command** | `pytest tests/examples -q` |
| **Per-test run** | `pytest tests/examples/test_check_speed.py -q` |
| **Full suite command** | `pytest tests/examples tests/parser tests/analyzer tests/codegen tests/cli -q -m "not live"` |
| **Subprocess CLI** | `python -m voss.cli {check\|compile\|run} ...` (via `tests/examples/helpers.py:60-69`) |
| **Estimated runtime** | ~30-60s after D-03 lands (currently dominated by the ~13s cold HF load that D-03 eliminates from `voss check`) |

---

## Sampling Rate

- **After every task commit:** `pytest tests/examples -q`
- **After every plan wave:** `pytest tests/examples tests/parser tests/analyzer tests/codegen tests/cli -q -m "not live"`
- **Before `/gsd-verify-work`:** Full suite green + `voss --help` works + `time python3 -m voss.cli check samples/{classify,support,research}.voss` each report <2s
- **Max feedback latency:** 60 seconds (quick), 180 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| Wave-0 sentinel | 00 | 0 | LANG-05 / D-03 | — | `voss check` must not load HF encoder | unit | `pytest tests/examples/test_check_speed.py::test_check_does_not_load_hf_encoder -q` | ❌ W0 | ⬜ pending |
| analyzer-guard | 01 | 1 | LANG-05 / D-03 | — | `Analyzer._visit_match_stmt` early-returns when `emit_indexes=False` so SemanticMatcher is never instantiated at check time | unit | `pytest tests/analyzer/ -q -k match_static` | ❌ W0 | ⬜ pending |
| stub-fallback | 02 | 2 | D-01 | — | `voss run` auto-registers `__stub__` when `auth.resolve()` returns `source=none` OR `VOSS_HERMETIC=1` | unit | `pytest tests/cli/test_run_stub_fallback.py -q -k auto_register` | ❌ W0 | ⬜ pending |
| stub-banner | 02 | 2 | D-02 | — | Stderr emits banner `voss: no provider creds detected — using __stub__ (deterministic fake responses)` on every stub-fallback invocation | unit | `pytest tests/cli/test_run_stub_fallback.py -q -k banner` | ❌ W0 | ⬜ pending |
| sample-support | 03 | 3 | LANG-07 / D-05 | — | `samples/support.voss` parses + analyzes + codegens + runs against StubProvider after adding `memory.episodic` recall | e2e | `pytest tests/examples/test_support_e2e.py -q` | ✓ (update) | ⬜ pending |
| sample-research | 03 | 3 | LANG-08 / D-06 | — | `samples/research.voss` parses + analyzes + codegens + runs after adding `try/catch` around `webSearch` + `use voss_runtime::tools::tool` | e2e | `pytest tests/examples/test_research_e2e.py -q` | ✓ (update) | ⬜ pending |
| raw-parity-support | 03 | 3 | LANG-03 / D-12 | — | Generated python from `samples/support.voss` matches `examples/raw_python/support.py` stdout under same StubProvider seed | e2e | `pytest tests/examples/test_support_e2e.py::test_support_voss_run_matches_raw -q` | ✓ (update) | ⬜ pending |
| raw-parity-research | 03 | 3 | LANG-03 / D-12 | — | Generated python from `samples/research.voss` matches `examples/raw_python/research.py` stdout under same StubProvider seed | e2e | `pytest tests/examples/test_research_e2e.py::test_research_voss_run_matches_raw -q` | ✓ (update) | ⬜ pending |
| sample-header-classify | 03 | 3 | LANG-01 / D-14 | — | `samples/classify.voss` opens with a header comment naming the primitives demonstrated | grep | `grep -E '^# classify.voss — probable' samples/classify.voss` | ⬜ pending |
| sample-header-support | 03 | 3 | LANG-01 / D-14 | — | `samples/support.voss` opens with a header comment naming the primitives | grep | `grep -E '^# support.voss — ' samples/support.voss` | ⬜ pending |
| sample-header-research | 03 | 3 | LANG-01 / D-14 | — | `samples/research.voss` opens with a header comment naming the primitives | grep | `grep -E '^# research.voss — ' samples/research.voss` | ⬜ pending |
| tests-repoint | 04 | 4 | LANG-09 / D-09 | — | `tests/examples/helpers.example_source` points to `samples/` (not `tests/parser/examples/`) so test suite validates the canonical samples | unit | `pytest tests/examples/ -q -k cli_matrix` | ✓ (update) | ⬜ pending |
| tests-slim | 04 | 4 | D-09 | — | `tests/examples/test_helpers.py` and `tests/examples/test_live_examples.py` removed | grep | `! test -f tests/examples/test_helpers.py && ! test -f tests/examples/test_live_examples.py` | ⬜ pending |
| speed-gate-classify | 05 | 5 | D-13 / LANG-09 | — | `voss check samples/classify.voss` wall-clock ≤ 2s (or tuned ceiling) | speed | `pytest tests/examples/test_check_speed.py::test_check_speed_classify -q` | ❌ W0 | ⬜ pending |
| speed-gate-support | 05 | 5 | D-13 / LANG-09 | — | `voss check samples/support.voss` wall-clock ≤ 2s | speed | `pytest tests/examples/test_check_speed.py::test_check_speed_support -q` | ❌ W0 | ⬜ pending |
| speed-gate-research | 05 | 5 | D-13 / LANG-09 | — | `voss check samples/research.voss` wall-clock ≤ 2s | speed | `pytest tests/examples/test_check_speed.py::test_check_speed_research -q` | ❌ W0 | ⬜ pending |
| coverage-fixtures-parser | 06 | 6 | LANG-07 / LANG-08 / D-07 | — | `memory.semantic` and `memory.working` parse cleanly via golden fixtures under `tests/parser/examples/coverage/` | unit | `pytest tests/parser/test_examples.py -q -k coverage` | ❌ W0 | ⬜ pending |
| coverage-fixtures-analyzer | 06 | 6 | LANG-07 / D-07 | — | Coverage fixtures analyze without errors | unit | `pytest tests/analyzer/ -q -k coverage` | ❌ W0 | ⬜ pending |
| coverage-fixtures-codegen | 06 | 6 | LANG-07 / D-07 | — | Coverage fixtures codegen to working Python (snapshot) | unit | `pytest tests/codegen/ -q -k coverage` | ❌ W0 | ⬜ pending |
| framing-readme | 07 | 7 | LANG-01 / LANG-05 / D-14 | — | README.md contains "What is .voss" section with AI-workflow-control framing; not "Python replacement" | grep | `grep -F "AI workflow control" README.md && ! grep -i "Python replacement" README.md` | ⬜ pending |
| framing-vs-python-doc | 07 | 7 | LANG-01 / D-15 | — | `docs/voss-vs-python.md` exists; per-sample side-by-side w/ LOC + commentary; linked from README | grep | `test -f docs/voss-vs-python.md && grep -F "docs/voss-vs-python.md" README.md` | ❌ W0 | ⬜ pending |
| lang-10-contract | 07 | 7 | LANG-10 / D-04 | — | At least one sample runs `voss run` to exit 0 + non-empty stdout under StubProvider | integration | `pytest tests/examples/test_classify_e2e.py::test_classify_voss_run_matches_compile_python -q` | ✓ | ⬜ pending |

*Status: ⬜ pending · ✓ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `tests/examples/test_check_speed.py` — D-03 sentinel (no HF encoder load) + D-13 per-sample wall-clock ceiling
- [ ] `tests/cli/test_run_stub_fallback.py` — D-01 auto-register + D-02 banner (or extend existing `tests/cli/test_run.py`)
- [ ] `tests/parser/examples/coverage/memory_semantic.voss` + `memory_working.voss` — D-07 fixtures
- [ ] `tests/analyzer/examples/coverage/` mirror fixtures + parametrized test runner (if not auto-discovered)
- [ ] `tests/codegen/snapshots/coverage/` mirror fixtures + snapshot files
- [ ] `docs/voss-vs-python.md` — D-15 deliverable scaffold (content lands later in the plan)
- [ ] **Deletions:** `tests/examples/test_helpers.py` + `tests/examples/test_live_examples.py` (D-09)
- [ ] **Repoint:** `tests/examples/helpers.py:example_source` → `samples/` (was `tests/parser/examples/`)

*(No framework install needed — pytest + pytest-asyncio already pinned in `[project.optional-dependencies].dev` at pyproject.toml:25-26.)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generated Python "reads readably" | LANG-03 | Subjective readability beyond stdout-parity assertion | Reviewer inspects `.voss-cache/*.py` for each sample; compares to `examples/raw_python/*.py`; confirms idiomatic Python (no obvious leaked AST node names, no dead branches). |
| "AI workflow control" framing is clear and accurate in README + docs/voss-vs-python.md | LANG-01 / LANG-05 | Editorial judgment | Reviewer reads README's "What is .voss" section and docs/voss-vs-python.md end-to-end; confirms positioning is not "Python replacement"; confirms `.voss` strengths are illustrated. |
| Optional live-provider e2e | LANG-10 | Real-provider runs cost money and require creds; default tests stay hermetic per cross-cutting constraint | Manual: `VOSS_PROVIDER=anthropic ANTHROPIC_API_KEY=... voss run samples/classify.voss`; record provider, model, sanitized output, date. |

---

## Validation Sign-Off

- [x] All tasks have automated verification or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every wave has a unit/e2e/speed assertion)
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency target < 60s quick / < 180s full
- [x] Default tests hermetic and provider-free (StubProvider + VOSS_HERMETIC=1 in env)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-11
