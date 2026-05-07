---
phase: 01-runtime-library
plan: 05
subsystem: runtime
tags: [python, integration-tests, examples, prd-acceptance, asyncio]

requires:
  - phase: 01-runtime-library/01-04
    provides: VossAgent, AgentHandle, gather, @tool, run_with_budget
  - phase: 01-runtime-library/01-03
    provides: SemanticMatcher, EpisodicMemory, SemanticMemory, WorkingMemory
  - phase: 01-runtime-library/01-02
    provides: ProbableValue, ContextScope, BudgetScope
provides:
  - PRD §7.1/§7.2/§7.3 examples expressed as raw Python via voss_runtime
  - Three end-to-end integration tests gating Phase 1 acceptance
  - Top-level README.md
  - Phase 1 closure
affects: [phase 02 grammar, phase 04 codegen target output, phase 06 example validation]

tech-stack:
  added: []
  patterns:
    - "Module-level encoder construction guarded by monkeypatched _encode in tests — keeps examples idiomatic without forcing dependency injection"
    - "StubProvider re-registered as `__stub__` per test with default_response — fingerprint lookup handled by provider, no per-test fingerprint computation"
    - "Timeout fallback test pattern: monkeypatch run_with_budget alias inside example module to inject a tiny latency_ms — exercises BudgetExceededError catch path without slowing the suite"

key-files:
  created:
    - examples/raw_python/__init__.py
    - examples/raw_python/classify.py
    - examples/raw_python/support.py
    - examples/raw_python/research.py
    - tests/integration/__init__.py
    - tests/integration/test_classify_example.py
    - tests/integration/test_support_example.py
    - tests/integration/test_research_example.py
    - README.md

key-decisions:
  - "Examples imported by tests use module-level state (matcher, agent classes) — tests monkeypatch SemanticMatcher._encode at class level BEFORE first import to avoid sentence-transformers download, then sys.modules.pop on teardown"
  - "ProbableValue confidence heuristic in ContextScope.ask (0.9 if non-empty, 0.0 if empty) is the gate the classify example tests against — empty stub response → confidence 0.0 → 'unknown'"
  - "research.py timeout fallback test patches the `run_with_budget` symbol imported into the example module rather than the source — preserves the example's exact code while injecting test-only latency"
  - "semantic.py coverage at 84% is intentional — uncovered lines are SentenceTransformer load + encoder.encode paths, exercised only under `-m live`. Stub-mode coverage stays hermetic, no model download in CI"
  - "Phase 1 acceptance gate met: all three PRD §7 examples run end-to-end against StubProvider deterministically; live-mode CI job (Plan 01-01) covers real-provider validation nightly"

patterns-established:
  - "Examples live under `examples/raw_python/`; future codegen output (Phase 4) targets identical semantics, allowing diff-based regression"
  - "Integration tests register StubProvider per-test and tear down via reset_config — no global test state leakage"

requirements-completed:
  - RUN-11

duration: ~6min
completed: 2026-05-07
---

# Phase 01 Plan 05: PRD §7 Examples + Acceptance Gate Summary

**All three PRD §7 example programs run as raw Python against `voss_runtime` with deterministic StubProvider integration tests — Phase 1 runtime contract proven.**

## Performance

- **Tasks:** 4
- **Files created:** 9
- **Tests added:** 8 (2 classify + 4 support + 2 research)
- **Suite total:** 77 passing under `arch -arm64 python3 -m pytest -q -m "not live"`, 5 deselected (live-marked)
- **Coverage:** 91.81% total (`fail_under = 90` gate met)

## Per-module coverage (stub mode)

| Module | Cover | Note |
|---|---|---|
| probable.py | 100% | pure logic |
| _config.py | 100% | pure logic |
| exceptions.py | 100% | pure logic |
| memory/working.py | 100% | pure logic |
| providers/base.py | 100% | Protocol + dataclass |
| providers/stub.py | 100% | |
| providers/__init__.py | 100% | registry |
| memory/episodic.py | 98% | StubProvider-driven |
| tools.py | 98% | |
| budget.py | 96% | |
| context.py | 94% | |
| agent.py | 91% | |
| providers/litellm_provider.py | 91% | network paths uncovered |
| semantic.py | 84% | encoder load paths live-only (intentional) |
| memory/semantic.py | 58% | source-ingest + OpenAI branch live-only |

Pure-logic modules (probable, budget, semantic, memory.episodic, memory.working, tools) all ≥ 84% with the only sub-90 entry being `semantic.py` whose uncovered lines are the live-only SentenceTransformer load (PRD acceptance allows this — D-17).

## Accomplishments
- `examples/raw_python/classify.py` — confidence-gated classification, runs end-to-end
- `examples/raw_python/support.py` — semantic routing + ContextScope fallback
- `examples/raw_python/research.py` — agent swarm, gather, run_with_budget timeout fallback
- Integration tests cover happy path + fallback + semantic routing + agent gather + timeout
- README.md ties PRD, examples, ROADMAP together
- Full Phase 1 stub-mode suite green at 77 tests, 91.81% coverage

## Verification
- `pytest -q -m "not live"` → 77 passed
- `pytest -q -m "not live" --cov=voss_runtime` → 91.81% (≥ 90% gate)
- All PRD §7 examples runnable via `python -m examples.raw_python.<name>` (asyncio.run wrapper)
- Live-mode CI job (Plan 01-01) gates real-provider validation; manual dispatch verification step open before phase merge

## Phase 1 Closure
- All RUN-01..11 requirements implemented and tested
- Provider seam locked, scope/budget primitives stable, memory primitives + agents + tools shipped
- PRD §7 examples are now the diff-target for Phase 4 codegen output

## Next
Phase 2 — Lark grammar + AST + transformer parses every PRD §7 example into a Voss AST.
