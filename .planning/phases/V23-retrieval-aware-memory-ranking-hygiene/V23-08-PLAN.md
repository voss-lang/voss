---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 08
type: execute
wave: 6
depends_on: ["V23-02", "V23-03", "V23-04", "V23-05", "V23-06", "V23-07"]
files_modified:
  - tests/memory/test_retrieval_ranking.py
autonomous: true
requirements: [VRNK-08]

must_haves:
  truths:
    - "Full existing memory + code_recall test suites stay green"
    - "The rescore-off byte-identical baseline test exists and passes"
    - "voss recall cross-corpus fusion (cli.py:4811) works unchanged with floors applied per-store"
    - "No frozen-schema drift"
  artifacts:
    - path: "tests/memory/test_retrieval_ranking.py"
      provides: "any final byte-identical / cross-corpus coherence assertions confirmed GREEN"
      contains: "byte_identical"
  key_links:
    - from: "tests/memory/test_retrieval_ranking.py"
      to: "full memory + code_recall suites"
      via: "regression gate"
      pattern: "test_"
---

<objective>
Implement VRNK-08 regression + coherence guard: prove the whole V23 surface is internally coherent, existing consumers are unbroken, the rescore-off path is byte-identical, and `voss recall` cross-corpus fusion still works with floors applied per-store. This is the phase closeout — it turns no new features on; it locks the off-path and runs the full regression battery.

Purpose: V23 touched the recall hot path that M8/V19 (and V21-planned) surfaces depend on. This plan is the proof-of-no-harm gate before /gsd-verify-work.
Output: full-suite green confirmation, byte-identical baseline locked, cross-corpus `voss recall` coherence asserted, frozen-schema drift check clean.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-SPEC.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-VALIDATION.md

<interfaces>
From voss/harness/cli.py:
- recall_cmd (line 4811) — voss recall cross-corpus verb; MemoryStore(cwd).recall(...) at 4835; fuses code + memory via MemoryStore._rrf_merge (V19). NO-TOUCH path — floors apply per-store upstream, no telemetry recorded here.

Full suites (V23-VALIDATION.md):
- Quick: .venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py -x -q
- Full: .venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py tests/code_recall -q
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Cross-corpus coherence + byte-identical lock assertions</name>
  <read_first>
    - tests/memory/test_retrieval_ranking.py (the scaffold — confirm byte-identical + any cross-corpus tests; add coverage if the cross-corpus voss-recall path is not yet asserted)
    - voss/harness/cli.py:4811-4840 (recall_cmd cross-corpus fusion — confirm floors apply per-store and no telemetry recorded)
    - tests/code_recall/test_recall_cli.py (existing voss recall CLI test analog)
    - V23-RESEARCH.md:61-64 (VRNK-08 target: suites green + byte-identical baseline + voss recall works with floors per-store), :64 (cli.py:4835 no-touch)
    - V23-SPEC.md VRNK-08 acceptance + Acceptance Criteria checklist (lines 97-109)
  </read_first>
  <action>
    Ensure tests/memory/test_retrieval_ranking.py contains (add if missing — most should already be GREEN from prior plans):
    1. The rescore-off byte-identical baseline test (`test_rescore_off_byte_identical`) — confirm it asserts locator order + scores + excerpts equal a captured pre-V23 baseline. This is the hard gate.
    2. A cross-corpus coherence test for `voss recall`: assert the CLI verb (cli.py recall_cmd) still fuses code + memory and that memory-side floors apply per-store WITHOUT recording telemetry (retrieval_count stays 0 after a `voss recall` invocation — reuse the VRNK-01 no-touch assertion against the CLI path). Use CliRunner against `recall_cmd` or the existing tests/code_recall/test_recall_cli.py harness pattern. If an equivalent assertion already exists in tests/code_recall, reference it rather than duplicating — note that in the SUMMARY.
    Do NOT modify production code in this plan — VRNK-08 is a guard, not a feature. If a coherence test reveals a real regression, STOP and surface it (it belongs to the owning plan, not here). Add only test assertions.
  </action>
  <acceptance_criteria>
    - `grep -c 'byte_identical' tests/memory/test_retrieval_ranking.py` >= 1
    - Byte-identical + cross-corpus tests pass: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "byte_identical or cross or recall" -q` GREEN
    - voss recall CLI test stays green: `.venv/bin/python -m pytest tests/code_recall/test_recall_cli.py -q` GREEN
    - No production source file modified in this plan: `git diff --name-only` shows only tests/memory/test_retrieval_ranking.py (plus the SUMMARY)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "byte_identical or recall" -q tests/code_recall/test_recall_cli.py -q 2>&1 | tail -6</automated>
  </verify>
  <done>Byte-identical off-path locked; voss recall cross-corpus fusion proven unchanged with floors per-store and no telemetry; no production code touched.</done>
</task>

<task type="auto">
  <name>Task 2: Full regression battery + frozen-schema drift check</name>
  <read_first>
    - V23-VALIDATION.md:22-24 (full suite command), :48-49 (VRNK-08 regression row)
    - V23-SPEC.md:64 + Acceptance Criteria (pytest tests/memory tests/harness/test_memory_*.py tests/code_recall green; byte-identical baseline; no frozen-schema drift)
    - .planning/STATE.md (frozen-schema drift convention — V-track phases verify zero schema drift)
  </read_first>
  <action>
    Run the full V23 regression battery and confirm GREEN: `.venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py tests/code_recall -q`. Confirm the complete VRNK-01..08 set in tests/memory/test_retrieval_ranking.py is GREEN (and the single V21-gated global-pin test is still a clean XFAIL, not a failure or surprise XPASS — note its status in the SUMMARY). Verify no frozen-schema drift: V23 added no new contract/schema substrate (RESEARCH: extension-only, no new store type) — confirm no edits to any frozen schema/contract file appear in `git diff` for the phase (check against the project's frozen-schema list; if a schema parity gate command exists, run it). Record the final suite counts (passed/skipped/xfailed) in the SUMMARY. If anything is RED, do not paper over it — surface the failing test and the owning plan.
  </action>
  <acceptance_criteria>
    - Full suite GREEN: `.venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py tests/code_recall -q` exit 0
    - All VRNK-01..08 feature tests pass; ≤1 XFAIL (the V21-gated global-pin stub), 0 unexpected XPASS, 0 failures
    - No frozen-schema/contract file in the phase git diff (extension-only confirmed)
    - SUMMARY records final passed/skipped/xfailed counts
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py tests/code_recall -q 2>&1 | tail -8</automated>
  </verify>
  <done>Full memory + code_recall suites green; VRNK-01..08 covered; one clean V21-gated XFAIL; no frozen-schema drift; phase ready for /gsd-verify-work.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none new) | Regression/guard plan; adds test assertions only, no runtime surface |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V23-08-01 | Tampering | regression hidden by a false-green skip/xfail | mitigate | acceptance caps XFAIL at 1 (V21-gated) with 0 unexpected XPASS; full-suite exit 0 required; no production code edits allowed |
| T-V23-08-02 | Repudiation | undetected frozen-schema drift ships | mitigate | explicit git-diff frozen-schema check; extension-only confirmed against RESEARCH |
| T-V23-08-SC | Tampering | npm/pip/cargo installs | accept | No installs; zero new packages (RESEARCH audit) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py tests/code_recall -q` exit 0
- Byte-identical baseline GREEN; voss recall cross-corpus GREEN
- No frozen-schema file in phase git diff
</verification>

<success_criteria>
VRNK-08 GREEN; full regression battery passes; off-path byte-identical locked; cross-corpus recall coherent; one clean V21-gated XFAIL; no schema drift; phase ready to verify.
</success_criteria>

<output>
Create `.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-08-SUMMARY.md` when done.
</output>
