---
phase: M3
plan: 06
status: complete
date: 2026-05-12
---

# M3-06 Summary — D-13 speed gate + D-14 README framing + D-15 voss-vs-python doc

## CHECK_CEILING_SECONDS

Final value: **8.0** (bumped from the 2.0 placeholder M3-01 carried forward).

Rationale: subprocess invocation of `voss check` carries unavoidable Python interpreter startup + `voss.cli` import cost (loads Click + `voss.harness.cli` which imports LiteLLMProvider). Measured baseline on dev machine showed `import voss.cli` alone at 2.6-5.4s wall-clock with high variance. Plan task 1 step 5b explicitly permits bumping the ceiling to a value that still gates D-03 regressions. The pre-fix `voss check samples/support.voss` baseline was ~8.9s (per M3-01 SUMMARY) — an 8.0s ceiling still catches that regression while accommodating subprocess + CI variance.

## Measured warm wall-clock times

Subprocess (post-`run_voss` warmup, second invocation, dev machine):

| Sample | Warm wall-clock (s) |
|--------|---------------------|
| classify | 1.3-4.0 (variable, well under ceiling) |
| support | ~4.4 (was ~8.9 pre-D-03) |
| research | ~1.8 |

In-process (`python3 -c "from voss import parse, analyze; ..."`): ~0.78s for classify. Confirms the analyzer side is fast; bulk of subprocess wall-clock is interpreter + harness import.

`pytest tests/examples/test_check_speed.py -v` → 4 passed in ~48s (1 sentinel + 3 parametrized).

## README.md diff summary

**Removed**:
- `> **Phase 1 status:** runtime library shipped. The compiler does not yet exist — ...` blockquote (was line 5).

**Added**:
- New `## What is .voss` H2 section between H1 + opening paragraph and `## Install`. Section contains:
  - Framing sentence with the literal substring `AI workflow control`.
  - **D-14 negation phrase (verbatim, for the intent-preservation audit)**:
    > "It is a complement to Python, not a replacement: write your data structures, business logic, and integrations in Python as usual, and reach for .voss when you need first-class control over LLM-shaped concerns."

    This explicitly states .voss is not a Python replacement without containing the literal substring "Python replacement" (per the M3-VALIDATION grep contract `! grep -i "Python replacement" README.md`).
  - Bulleted list of first-class primitives: probable values + confidence gates, ctx budgets, semantic routing, agents + spawn + gather, memory primitives, try/catch + use.
  - Closing pointer line linking to [`samples/`](../samples/) and [`docs/voss-vs-python.md`](docs/voss-vs-python.md).
- New bullet in `## Project Docs`: `- [docs/voss-vs-python.md](docs/voss-vs-python.md) — side-by-side .voss vs raw Python with LOC counts`.

Two links to `docs/voss-vs-python.md` total: one inline in `## What is .voss`, one in `## Project Docs`.

## docs/voss-vs-python.md

273 lines. Structure:
- H1 `# Voss vs raw Python`
- Framing paragraph linking back to README + samples + raw_python.
- `## Classify` — commentary paragraph + `samples/classify.voss` fenced block + `examples/raw_python/classify.py` fenced block.
- `## Support` — commentary + paired blocks.
- `## Research` — commentary + paired blocks.
- `## Line counts` table:

| Sample | .voss | raw Python |
| --- | --- | --- |
| classify | 14 | 18 |
| support | 28 | 42 |
| research | 49 | 67 |

Regeneration command embedded: `wc -l samples/*.voss examples/raw_python/*.py`.

## M3-VALIDATION grep contracts — all green

```
$ grep -F "AI workflow control" README.md
.voss is an **AI workflow control** layer that compiles to readable Python. ...

$ grep -c "docs/voss-vs-python.md" README.md
2

$ grep -i "Python replacement" README.md
(empty — exit 1, contract satisfied)

$ grep -F "Phase 1 status" README.md
(empty — exit 1, banner removed)

$ test -f docs/voss-vs-python.md
(exit 0)
```

Sample header em-dash and D-02 banner em-dash checks from M3-04 + M3-02 remain green.

## Full M3 suite status

```
$ VOSS_HERMETIC=1 pytest tests/examples/ tests/parser tests/analyzer tests/codegen tests/cli -m "not live"
275 passed, 2 warnings in 73.46s
```

## M3 phase-verification hand-off

`/gsd-verify-work M3-language-validation` target. Success criterion grid (every LANG-01..10 has automated coverage):

| Requirement | Coverage |
|-------------|----------|
| LANG-01 (framing) | `## What is .voss` in README + `docs/voss-vs-python.md`; greps in M3-VALIDATION |
| LANG-02 (probable values) | `samples/classify.voss` + `tests/parser/test_examples.py` + `tests/integration/test_classify_example.py` |
| LANG-03 (raw-parity readability) | `docs/voss-vs-python.md` LOC table + `tests/examples/test_support_e2e.py` + `tests/examples/test_research_e2e.py` raw-parity asserts |
| LANG-04 (LLM integration) | `examples/raw_python/*.py` hermetic runs; e2e suite under `VOSS_HERMETIC=1` |
| LANG-05 (match similar static) | M3-01 `_visit_match_stmt` gate + `tests/examples/test_check_speed.py` sentinel |
| LANG-06 (agents/spawn/gather) | `samples/research.voss` + `tests/examples/test_research_e2e.py` |
| LANG-07 (memory primitives) | `samples/support.voss` (episodic) + `tests/parser/examples/coverage/memory_{semantic,working}.voss` + `tests/codegen/test_snapshots_coverage.py` |
| LANG-08 (try/catch + use + prompt + tool) | `samples/research.voss` (try/catch + use) + `samples/support.voss` (prompt) + `tests/examples/test_research_e2e.py::test_research_generated_contains_use_and_try_catch_lowerings` |
| LANG-09 (samples fast) | `tests/examples/test_check_speed.py::test_check_speed_under_ceiling` (3 params, ceiling 8s) |
| LANG-10 (voss run hermetic) | M3-02 auto-stub + banner + `tests/cli/test_run_stub_fallback.py` (4 tests) + `tests/examples/test_support_voss_run_matches_compile_python` |

## Acceptance criteria — all met

- `test_check_speed_under_ceiling` parametrized over 3 samples; M3-01 sentinel preserved ✓
- 4 passed in `test_check_speed.py` ✓
- `AI workflow control` literal in README ✓
- 2 links to `docs/voss-vs-python.md` in README ✓
- `Python replacement` literal absent (negation phrased without it) ✓
- `Phase 1 status` banner removed ✓
- Section ordering H1 → What is .voss → Install verified by Python script ✓
- `docs/voss-vs-python.md` exists with H1 + 3 H2 sections + 3 `\`\`\`voss` + 3 `\`\`\`python` blocks + LOC table ✓
- 273 LOC (≥60 required) ✓
- Full M3 suite: 275 passed ✓
