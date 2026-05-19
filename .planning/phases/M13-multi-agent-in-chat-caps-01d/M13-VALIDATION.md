---
phase: M13
slug: multi-agent-in-chat-caps-01d
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-18
---

# Phase M13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: M13-RESEARCH.md §"Validation Architecture" + §"Security Domain". Requirements authority: M13-SPEC.md (MAG-01..MAG-08).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8+ with pytest-asyncio (`asyncio_mode="auto"` — no `@pytest.mark.asyncio` needed) |
| **Config file** | `pyproject.toml` (`asyncio_mode = "auto"`) — already present |
| **Quick run command** | `pytest tests/harness/test_multiagent_fanout.py -x -q` |
| **Full suite command** | `pytest tests/harness/ tests/harness/tui/ tests/e2e/test_multiagent_chat_e2e.py -x -q` |
| **Estimated runtime** | ~30–60 seconds (hermetic stub provider, no live network) |
| **Provider posture** | Hermetic `FakeStreamingProvider` (test_agent_loop.py:77) — scripted per-agent `stream()`/`complete()`; NO live network (D-11) |
| **TUI posture** | `VossTUIApp().run_test()` + `pilot.pause()` (test_live_visualization.py precedent) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/harness/test_multiagent_fanout.py -x -q` (+ the specific new file the task touched)
- **After every plan wave:** Run `pytest tests/harness/ -x -q && pytest tests/harness/test_subagent_recursion.py -x -q` (back-compat pinning test MUST stay green)
- **Before `/gsd:verify-work`:** `pytest tests/harness/ tests/harness/tui/ tests/e2e/test_multiagent_chat_e2e.py -x -q` fully green
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

Plan/Wave/Task-ID columns are filled by the planner. Requirement → observable-signal/test-seam mapping is locked here from RESEARCH.

| Req | Plan | Wave | Observable signal / test seam | Threat Ref | Test Type | Automated Command | File Exists | Status |
|-----|------|------|-------------------------------|------------|-----------|-------------------|-------------|--------|
| MAG-01 | TBD | TBD | ≥2 children observably in-flight same instant: each child stub records wall-clock window, assert overlap (not serial); spy `ChildRegistry.active()` ≥ 2 between spawn and gather | — | unit/concurrency | `pytest tests/harness/test_multiagent_fanout.py::TestConcurrentInFlight -x` | ❌ W0 | ⬜ pending |
| MAG-02 | TBD | TBD | (a) `SubAgentPanel` `BudgetMeter` leaves em-dash + `update_budget` ≥1×/child before collapse (`meter.total>0`, `used` increments); (b) body `Vertical` `display==none` default; after `action_toggle_subagent_detail` contains ≥1 streamed-step Static | — | TUI (pilot) | `pytest tests/harness/tui/test_subagent_reveal.py -x` | ❌ W0 | ⬜ pending |
| MAG-03 | TBD | TBD | Reserve R, N children: each `allocator.snapshot()[h] ≈ R//N`; after one child `release()`, survivor allotment strictly increases; panel `BudgetMeter` reflects new total | T-M13 oversell | unit | `pytest tests/harness/test_multiagent_fanout.py::TestEvenSplitRebalance -x` | ❌ W0 | ⬜ pending |
| MAG-04 **(must-not-happen)** | TBD | TBD | Recursive no-oversell race: `asyncio.gather(*[allocate(h) for h in many])` vs R → `sum(snapshot.values()) <= R` + denied-count matches floor math. Exactly-once: double `release(h)` → no double-credit, Σ ≤ R. Depth-bound: grandchild ≤ child slice | T-M13 oversell | unit/concurrency | `pytest tests/harness/test_multiagent_fanout.py::TestNoOversell -x` | ❌ W0 | ⬜ pending |
| MAG-05 | TBD | TBD | Scripted parent `subagent_steer` mid-run; child stub BRANCHES on guidance presence; child output WITH correction != no-correction control; steer consumed at line-832 drain (≥2 child iterations) | T-M13 mis-steer | unit | `pytest tests/harness/test_multiagent_steer.py::TestCorrectionChangesBehavior -x` | ❌ W0 | ⬜ pending |
| MAG-06 | TBD | TBD | Depth-2 parent→child→grandchild: (a) 3 distinct `panel_id`s mounted concurrently; (b) grandchild ≤ child slice ≤ parent reserve all 3 levels; (c) post-gather zero `SubAgentPanel` (no leak) | T-M13 recursion-DoS | unit + TUI | `pytest tests/harness/test_multiagent_recursion.py::TestDepth2 -x` | ❌ W0 | ⬜ pending |
| MAG-07 | TBD | TBD | Post fan-out+gather: parent turn result references all child handles/results; `len(app.query(SubAgentPanel))==0`; `app._side_owner`/`_side_pinned` match pre-spawn snapshot (M9-08) | T-M13 orphan | TUI (pilot) | `pytest tests/harness/tui/test_subagent_reveal.py::TestPostGatherRegionClean -x` | ❌ W0 | ⬜ pending |
| MAG-08 | TBD | TBD | One stub `voss chat` e2e: 1 NL request → ≥2 concurrent panels, ≥1 budget tick/child, ≥1 applied correction, ≥1 rebalance, aggregated multi-child turn, clean post-gather region — ALL in one test | — | e2e | `pytest tests/e2e/test_multiagent_chat_e2e.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/test_multiagent_fanout.py` — concurrency proof (MAG-01), even-split+rebalance (MAG-03), no-oversell race + exactly-once + depth-bound (MAG-04)
- [ ] `tests/harness/test_multiagent_steer.py` — correction-changes-behavior vs control (MAG-05)
- [ ] `tests/harness/test_multiagent_recursion.py` — depth-2 nested budget + nested panels + no-leak (MAG-06)
- [ ] `tests/harness/tui/test_subagent_reveal.py` — quiet-by-default + ctrl+o reveal (MAG-02), post-gather region clean (MAG-07)
- [ ] `tests/e2e/test_multiagent_chat_e2e.py` — headline transcript (MAG-08); model on `tests/e2e/test_chat_e2e.py` (stdin-script) + `tests/e2e/runner.py` `CliRunner`
- [ ] Shared fixture: scripted multi-agent provider (parent script + per-child scripts) extending `FakeStreamingProvider` (test_agent_loop.py:77) — new conftest fixture in `tests/harness/`
- [ ] Regression guard: `tests/harness/test_subagent_recursion.py` MUST pass unmodified (no `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` added)
- [ ] Keymap baseline: extend `tests/harness/tui/test_keymap_baseline.py` — `ctrl+o → toggle_subagent_detail` resolves AND `ctrl+c` still → `interrupt`

*Framework already present (pytest + pytest-asyncio + Textual pilot). All gaps are new test files, not infra.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Subjective "quiet by default feels right" | MAG-02 | Aesthetic judgment beyond the automatable `display==none` assertion | Optional human spot-check in a real `voss chat`; NOT a phase gate (automated assertion is the gate) |

*All MAG pass/fail behaviors have automated verification. The row above is advisory only.*

---

## Security Domain (ASVS L1)

`security_enforcement` not disabled — section retained. M13 adds **no auth/session/crypto/network/persistence surface**; it is in-memory orchestration of an already-trusted local agent. Each PLAN.md MUST carry a `<threat_model>` block (block on `high`).

| Threat (STRIDE) | Ref | Mitigation (locked) | Test Seam |
|-----------------|-----|---------------------|-----------|
| Unbounded recursive spawn → resource exhaustion (DoS) | T-M13 recursion-DoS | Viable-budget-floor denial in `M13Allocator.allocate` (D-07) — recursion bounded WITHOUT a depth constant | MAG-04 depth-bound + MAG-06 |
| Budget oversell race (Tampering) | T-M13 oversell | `asyncio.Lock` check-and-allocate (D-06, O1-proven) | MAG-04 race test (mandatory) |
| Orphaned child tasks after parent turn ends (DoS) | T-M13 orphan | Defensive gather/cancel-on-teardown safety net (Pitfall 1) | MAG-07 post-gather region-clean |
| Steer to wrong/finished child (Tampering) | T-M13 mis-steer | `ChildRegistry.get(handle)` validates; steer to `done` child = no-op | MAG-05 steer test (negative case) |
| Cross-thread UI corruption (Tampering) | T-M13 ui-thread | Children stay asyncio tasks (NOT threads); `renderer._post` main-thread-safe | MAG-02/MAG-07 TUI pilot tests |
| Privilege escalation via child (EoP) | T-M13 priv | Child reuses parent `PermissionGate` unchanged (no broader scope) — same posture as existing `run_subagent` | Assert child gate identity in fan-out test |

No new secret material, no new network egress, no new persisted data. Blast radius = in-memory + UI only.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (7 new test files/fixtures above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] Back-compat regression (`test_subagent_recursion.py`) green unmodified
- [ ] `nyquist_compliant: true` set in frontmatter (after planner fills Plan/Wave/Task-ID columns)

**Approval:** pending
