---
phase: O5
slug: engineering-manager-loop
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-20
---

# Phase O5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (asyncio_mode=auto, configured in pyproject.toml) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/em/ -x -q --tb=short` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/em/ tests/integration/harness/ tests/harness/test_session_redaction.py -v --tb=long` |
| **Estimated runtime** | ~20 seconds (unit + integration, no live LLM) |

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/harness/em/ -x -q --tb=short`
- **After every plan wave:** `.venv/bin/python -m pytest tests/harness/em/ tests/integration/harness/ -x -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite green (`tests/harness/em/ + tests/integration/harness/ + tests/harness/test_session_redaction.py`)
- **Max feedback latency:** 20 seconds

---

## Requirement → Plan Coverage Matrix

| Requirement ID | Description | Plan(s) | Wave | Verify Command | Unique Tag | Status |
|----------------|-------------|---------|------|----------------|------------|--------|
| OEM-01 | Ticket / KillRecord / RescopeRecord / RoutingRationale / RunFinal frozen records; `kind: Literal["em.*"]` discriminator | O5-01 | 1 | `.venv/bin/python -m pytest tests/harness/em/test_em_tickets.py tests/harness/em/test_em_lineage.py -x -q` | `EM_DATAMODEL_OK` | ⬜ pending |
| OEM-02 | `EMBoardHandle` cage-bounded facade — legal verbs only; refuses ceiling/p/budget/non-roster writes with typed `EMCageViolation` | O5-02 | 2 | `.venv/bin/python -m pytest tests/harness/em/test_em_handle.py tests/harness/em/test_em_handle_cage.py -x -q` | `EM_HANDLE_OK` | ⬜ pending |
| OEM-03 | EM LLM call wrapper `em_plan(...)`; structured `EMPlanResponse` schema (pydantic BaseModel, `extra="ignore"`, `temperature=0.0`, sentinel-None on ParseError per judge.py) | O5-03 | 3 | `.venv/bin/python -m pytest tests/harness/em/test_em_schema.py tests/harness/em/test_em_llm.py -x -q` | `EM_LLM_STUB_OK` | ⬜ pending |
| OEM-04 | `DeterministicEMStub` for tests; zero LLM calls (mirrors O3 `DeterministicReviewerStub`) | O5-03 | 3 | `.venv/bin/python -m pytest tests/harness/em/test_em_stub.py -x -q` | `EM_LLM_STUB_OK` | ⬜ pending |
| OEM-05 | EM loop driver — idea → plan → dispatch → tick → terminate; uses harness scheduler (not voss_runtime.spawn/gather) per RESEARCH Q1 | O5-04 | 4 | `.venv/bin/python -m pytest tests/harness/em/test_em_loop.py tests/harness/em/test_em_loop_termination.py -x -q` | `EM_LOOP_OK` | ⬜ pending |
| OEM-06 | Specialist dispatch — read O2 `SubagentRegistry`; call `run_subagent(spec, node=..., reserve=...)` with per-role `gate_for_role` / `filter_toolset_for_role`; never construct SubagentSpec | O5-02 + O5-04 | 2, 4 | `.venv/bin/python -m pytest tests/harness/em/test_em_handle_dispatch.py tests/harness/em/test_em_loop_dispatch_path.py -x -q` | `EM_HANDLE_OK` + `EM_LOOP_OK` | ⬜ pending |
| OEM-07 | Kill / rescope lineage — append KillRecord / RescopeRecord to node side-table; new node linked via `lineage_parent_id`; bidirectional pointers; NEVER delete nodes | O5-01 + O5-02 + O5-05 | 1, 2, 5 | `.venv/bin/python -m pytest tests/harness/em/test_em_lineage.py tests/integration/harness/test_em_kill_rescope_lineage.py -x -q` | `EM_DATAMODEL_OK` + `EM_HANDLE_OK` + `O5_FULL_GREEN` | ⬜ pending |
| OEM-08 | Routing rationale audit — every dispatch emits a `RoutingRationale`; first-class for O6 surface | O5-02 + O5-05 | 2, 5 | `.venv/bin/python -m pytest tests/harness/em/test_em_handle_dispatch.py tests/integration/harness/test_em_misroute_audit.py -x -q` | `EM_HANDLE_OK` + `O5_FULL_GREEN` | ⬜ pending |
| OEM-09 | Misroute audit data — emit data O6's sign-off forcing function needs (CONTEXT decision #20 + RESEARCH Q8); cross-phase coordination C-02 flagged for O4 to add `ReviewerVerdict.domain_inferred` | O5-05 | 5 | `.venv/bin/python -m pytest tests/integration/harness/test_em_misroute_audit.py -x -q` | `O5_FULL_GREEN` | ⬜ pending |
| OEM-10 | `EXIT_REASONS` additive: `"killed"` joins existing set (cross-phase coordination C-03 with O3's `"timeout"`) | O5-01 + O5-05 | 1, 5 | `.venv/bin/python -m pytest tests/harness/em/test_em_exit_reasons.py tests/harness/test_session_redaction.py -x -q` | `EM_DATAMODEL_OK` + `O5_FULL_GREEN` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Every OEM-01..OEM-10 requirement appears in ≥1 plan. Reverse check: every plan
declares its OEM coverage in `requirements:` frontmatter, validated by the
GSD plan-structure check at planning time.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| O5-00-01 | O5-00 | 0 | — (gate) | T-O5-W0-01..03 | O1/O2 live probes + O3/O4 paper audit | checkpoint:human-verify | `.venv/bin/python -c "from voss.harness.session_tree import SessionTreeManager; from voss.harness.team import gate_for_role; from voss.harness.subagents import run_subagent; print('ok')"` | ❌ W0 | ⬜ pending |
| O5-01-01 | O5-01 | 1 | OEM-01, OEM-07, OEM-10 | T-O5-01..06 | RED scaffolds for tickets/lineage/EXIT_REASONS | tdd | `.venv/bin/python -m pytest tests/harness/em/test_em_tickets.py tests/harness/em/test_em_lineage.py tests/harness/em/test_em_exit_reasons.py --collect-only` | ❌ W0 | ⬜ pending |
| O5-01-02 | O5-01 | 1 | OEM-01, OEM-07, OEM-10 | T-O5-01..06 | Implementation GREEN | tdd | `.venv/bin/python -m pytest tests/harness/em/ tests/harness/test_session_redaction.py -x -q` | ❌ W0 | ⬜ pending |
| O5-02-01 | O5-02 | 2 | OEM-02, OEM-06, OEM-07, OEM-08 | T-O5-01..06 | RED scaffolds for handle/cage/dispatch | tdd | `.venv/bin/python -m pytest tests/harness/em/test_em_handle*.py --collect-only` | ❌ W0 | ⬜ pending |
| O5-02-02 | O5-02 | 2 | OEM-02, OEM-06, OEM-07, OEM-08 | T-O5-01..06 | Handle implementation GREEN | tdd | `.venv/bin/python -m pytest tests/harness/em/ -x -q` | ❌ W0 | ⬜ pending |
| O5-03-01 | O5-03 | 3 | OEM-03, OEM-04 | T-O5-01..LLM | RED scaffolds for schema/llm/stub | tdd | `.venv/bin/python -m pytest tests/harness/em/test_em_schema.py tests/harness/em/test_em_llm.py tests/harness/em/test_em_stub.py --collect-only` | ❌ W0 | ⬜ pending |
| O5-03-02 | O5-03 | 3 | OEM-03, OEM-04 | T-O5-01..LLM | Schema + LLM + stub GREEN; LENIENT pydantic | tdd | `.venv/bin/python -m pytest tests/harness/em/ -x -q` | ❌ W0 | ⬜ pending |
| O5-04-01 | O5-04 | 4 | OEM-05, OEM-06 | T-O5-03, T-O5-Loop-01..05 | RED scaffolds for loop happy path / termination / dispatch | tdd | `.venv/bin/python -m pytest tests/harness/em/test_em_loop*.py --collect-only` | ❌ W0 | ⬜ pending |
| O5-04-02 | O5-04 | 4 | OEM-05, OEM-06 | T-O5-03, T-O5-Loop-01..05 | em_loop GREEN; cage-violation continues; budget force-finalizes | tdd | `.venv/bin/python -m pytest tests/harness/em/ -x -q` | ❌ W0 | ⬜ pending |
| O5-05-01 | O5-05 | 5 | OEM-08, OEM-09, OEM-10 | T-O5-04..XPhase | Integration test scaffolds + conftest | tdd | `.venv/bin/python -m pytest tests/integration/harness/ --collect-only` | ❌ W0 | ⬜ pending |
| O5-05-02 | O5-05 | 5 | OEM-08, OEM-09, OEM-10 | T-O5-04..XPhase | Full e2e GREEN (misroute xfail-strict); coordination + validation docs ship | tdd | `.venv/bin/python -m pytest tests/harness/em/ tests/integration/harness/ -q && test -f .planning/phases/O5-engineering-manager-loop/O5-CROSS-PHASE-COORDINATION.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave Structure

| Wave | Plans | Autonomous | Files Modified |
|------|-------|------------|----------------|
| 0 | O5-00 | no (substrate gate, blocking-human) | SUMMARY only (no code) |
| 1 | O5-01 | yes | voss/harness/em/__init__.py, tickets.py, errors.py; voss/harness/session.py (additive); tests/harness/em/ |
| 2 | O5-02 | yes | voss/harness/em/handle.py, protocols.py; tests/harness/em/ |
| 3 | O5-03 | yes | voss/harness/em/schema.py, llm.py, stub.py; tests/harness/em/ |
| 4 | O5-04 | yes | voss/harness/em/loop.py; tests/harness/em/ |
| 5 | O5-05 | yes | tests/integration/harness/; planning artifacts |

Wave 3 is theoretically parallelizable with Wave 2 (depends only on Wave 1)
but is scheduled sequentially for execution-budget safety. Promote to
parallel if the executor has headroom.

---

## Wave 0 Requirements

- [ ] `.planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md` exists ending with `EM_SUBSTRATE_READY`.
- [ ] Live-substrate probes (O1 + O2 + run_subagent signature) pass.
- [ ] Paper interface audit for O3-SPEC (9 items) and O4-CONTEXT (4 items) recorded with file:line citations.
- [ ] Coordination_Asks C-01 / C-02 / C-03 recorded verbatim.
- [ ] Landmines L-01..L-05 recorded verbatim.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | O5 is fully automatable | — |

---

## Cross-Phase Coordination Tripwires

These are tracked in `O5-CROSS-PHASE-COORDINATION.md` (ships with O5-05) and
referenced from xfail-strict assertions where applicable:

- **C-01** (Reviewer signature) — manual O3 SPEC amendment; no test tripwire.
- **C-02** (`ReviewerVerdict.domain_inferred`) — xfail-strict in `tests/integration/harness/test_em_misroute_audit.py`; flips to XPASS when O4 lands the field.
- **C-03** (`EXIT_REASONS` additive ordering) — git-merge concern only; no test tripwire (both additions are commutative).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (substrate-gate scope only — no source files)
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] Every OEM-01..OEM-10 appears in ≥1 plan
- [x] Every plan declares OEM coverage in `requirements:` frontmatter

**Approval:** pending — flips to `approved` when all 11 task rows show ✅ green and O5-05-SUMMARY.md ends with `O5_FULL_GREEN`.
