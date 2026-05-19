---
phase: M13-multi-agent-in-chat-caps-01d
type: plan-outline
mode: chunked
created: 2026-05-18
requirements: [MAG-01, MAG-02, MAG-03, MAG-04, MAG-05, MAG-06, MAG-07, MAG-08]
---

# Phase M13 — Multi-agent in Chat (CAPS-01d) — Plan Outline

> Chunked outline pass. No PLAN.md files written this run. Per-plan PLANs are written in subsequent chunked passes.
> Requirements authority: `M13-SPEC.md` (MAG-01..MAG-08). HOW locked by `M13-CONTEXT.md` D-01..D-11. Code anchors verified in `M13-RESEARCH.md` / `M13-PATTERNS.md`. Nyquist map in `M13-VALIDATION.md`.

## Goal (outcome-shaped)

A `voss chat` user's NL request fans out to ≥2 concurrent sub-agents on the hardened `subagent_run` path (harness-local asyncio, NOT `VossAgent.spawn`); each child gets an even-split slice of an M13-local in-memory parent reserve (recursively, depth>1, hard recursive no-oversell); each renders in its own quiet-by-default M9 `SubAgentPanel` (detail revealed by `ctrl+o`, `ctrl+c` stays interrupt); the autonomous parent injects mid-run course-correction into a running child; results gather back into the chat turn with M9-08 region restore.

## Decomposition Strategy

- **Wave 0** = all red test scaffolds + the shared scripted multi-agent provider fixture. Covers every MAG observable signal seam from `M13-VALIDATION.md` (5 new test files + 1 conftest fixture + the keymap-baseline additive rows). Mandatory: recursive no-oversell race + ≥2-concurrent-in-flight proof + back-compat regression guard (`test_subagent_recursion.py` must stay green unmodified — no `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT`).
- **Wave 1** = `multiagent.py` foundation: `M13Allocator` (asyncio.Lock check-and-allocate, exactly-once release, viable-floor denial bounding recursion) + `ChildRegistry`/`ChildHandle`. Pure unit-testable core; greens MAG-03/MAG-04 (non-recursive + exactly-once + race). Resolves RESEARCH Open Question A1 (reserve value + viable-floor threshold) inside the task action.
- **Wave 2** = two parallel tracks, **zero file overlap**:
  - **2A (harness):** non-blocking `subagent_spawn`/`steer`/`status`/`gather` tools + `PanelBridgeRenderer` in `multiagent.py` (extends W1 file → W1 dependency) + the additive `steer_inbox` kwarg & line-830 drain in `agent.py`. Resolves RESEARCH Open Question A2 (steer injection = synthetic next-iteration user message) inside the task action.
  - **2B (TUI):** renderer dead-seam wiring (`renderer.py:203` first caller), `app.action_toggle_subagent_detail` + per-panel detail state, `sub_agent_panel.py` quiet-by-default body toggle, `keymap.py` +1 `ctrl+o` row, `test_keymap_baseline.py` additive rows. Resolves RESEARCH Open Question A3 (`"main"`-context keymap dispatch trace) inside the task action with the traced path documented.
- **Wave 3** = recursion wiring in `multiagent.py` (slice-scoped sub-allocator handed to child toolset; child re-receives the 4 tools). Greens MAG-06. Serial after 2A (same file `multiagent.py`).
- **Wave 4** = chat integration (`cli.py` additive `attach_multiagent_tools` call next to `attach_subagent_tool`) + the headline stub e2e. Greens MAG-08. Serial after 3 + 2B (needs full fan-out + TUI + recursion live).

**File-ownership rationale (parallelism proof):** `multiagent.py` is owned serially by W1 → W2A → W3 (forces those waves sequential). `agent.py` is touched only in W2A. The TUI file set (`renderer.py`, `app.py`, `sub_agent_panel.py`, `keymap.py`, `test_keymap_baseline.py`) has zero intersection with `multiagent.py`/`agent.py`, so W2B runs fully parallel to W2A. `cli.py` + e2e are W4-only. `subagents.py` is never edited (back-compat anchor, byte-stable).

## Plan Table

| Plan ID | Objective | Wave | Depends On | Requirements (MAG-xx) |
|---------|-----------|------|------------|------------------------|
| M13-01 | Wave 0 red scaffolds: shared scripted multi-agent provider conftest fixture (parent + per-child scripts extending `FakeStreamingProvider`); `test_multiagent_fanout.py` (concurrency overlap proof, even-split+rebalance, no-oversell race + exactly-once + depth-bound); `test_multiagent_steer.py` (correction-vs-control); `test_multiagent_recursion.py` (depth-2 nested budget + nested panels + no-leak); `tui/test_subagent_reveal.py` (quiet-by-default + ctrl+o reveal + post-gather region clean); `tests/e2e/test_multiagent_chat_e2e.py` (headline transcript); additive `ctrl+o`/`ctrl+c` rows in `test_keymap_baseline.py`. All red/xfail. Back-compat guard: assert `test_subagent_recursion.py` collects+passes unmodified. | 0 | — | MAG-01, MAG-02, MAG-03, MAG-04, MAG-05, MAG-06, MAG-07, MAG-08 |
| M13-02 | `voss/harness/multiagent.py` foundation (NEW module, additive — keeps `subagents.py` byte-stable): `M13Allocator` (asyncio.Lock check-and-allocate; even-split `_rebalance_locked`; idempotent `release` via `_credited_finished` set = exactly-once; viable-floor denial returning `None` = recursion bound, NO depth constant) + `ChildHandle` dataclass + `ChildRegistry` (in-memory, chat-turn-scoped, `active()`/`all()`). Task action resolves RESEARCH OQ-A1: pick + document the synthetic parent `reserve` default (fraction of the 60_000 default `token_budget`) and the viable-floor threshold (< `reserve // expected_fanout`, low-thousands tokens). Greens fanout allocator/no-oversell/rebalance unit classes. | 1 | M13-01 | MAG-03, MAG-04 |
| M13-03 | Wave 2A harness fan-out: extend `multiagent.py` with non-blocking `subagent_spawn` (allocate → `asyncio.create_task` → return handle immediately, NO await), `subagent_steer` (enqueue to per-child `asyncio.Queue`; no-op to done/unknown child), `subagent_status`, `subagent_gather` (`asyncio.gather(return_exceptions=True)` → release each → aggregate into turn → per-panel `collapse_subagent`) + defensive gather-on-teardown safety net + `attach_multiagent_tools(...)` + `PanelBridgeRenderer`. Add additive keyword-only `steer_inbox: asyncio.Queue \| None = None` to `run_turn`/`_run_turn_exec` and the D-04 drain between `agent.py:830` (`all_iter_records.append`) and `:832` (budget check). Task action resolves RESEARCH OQ-A2: steer injected as a synthetic next-iteration user message (no shared mutable history); document the messages-list landing trace. Greens MAG-01 concurrency overlap + MAG-05 correction-vs-control. | 2 | M13-02 | MAG-01, MAG-05 |
| M13-04 | Wave 2B TUI bridge + reveal (zero overlap with M13-03 files — runs parallel): supply the missing caller for the dead `renderer.py:203` `show_subagent_progress` seam via the bridge contract; add `app.action_toggle_subagent_detail` + per-panel detail-visibility state (iterate `query(SubAgentPanel)`, flip body `Vertical` `.styles.display`) WITHOUT touching `mount_subagent_panel`/`update_subagent`/`collapse_subagent`/`_side_*`; `sub_agent_panel.py` body `Vertical` `display:none` by default (steps still streamed/captured), reveal flips it (BudgetMeter em-dash contract unchanged, no new widget classes); `keymap.py` +1 `Binding("ctrl+o","main","toggle_subagent_detail",…)` (line-37 ctrl+c UNCHANGED). Task action resolves RESEARCH OQ-A3: trace how existing `"main"`-context rows (`keymap.py:29-36`) dispatch given `App.BINDINGS` filters `global\|input\|modal` (read `turn_view.py` BINDINGS / app focus routing), place `ctrl+o` on that same mechanism, and prove resolution via the keymap-baseline assertion. Greens MAG-02 + MAG-07 (TUI reveal + post-gather region-clean). | 2 | M13-02 | MAG-02, MAG-07 |
| M13-05 | Wave 3 recursion: extend `multiagent.py` so each spawned child's toolset re-receives the four tools plus a slice-scoped sub-`M13Allocator(reserve=child.allotment, viable_floor=…)` (D-07); fresh `uuid4().hex[:12]` panel_id per child at every depth (Pitfall 5 collision avoidance); recursive no-oversell holds because each level only divides its own reserve; viable-floor denial alone bounds depth (no `depth`/`max_depth` — `test_subagent_recursion.py` stays green). Greens MAG-06 depth-2 nested budget + nested panels + no-leak. | 3 | M13-03 | MAG-06 |
| M13-06 | Wave 4 chat integration + headline e2e: add `attach_multiagent_tools(tools, registry=…, cwd=…, renderer=…, provider=…, model=lambda: get_config().default_model, gate=gate, cognition=bundle)` in `cli.py` immediately after the existing `attach_subagent_tool(...)` call (~1634, additive; `attach_subagent_tool` + `/agent spawn` + `voss agent spawn` untouched). Bring `tests/e2e/test_multiagent_chat_e2e.py` green: one stub-provider `voss chat` NL request asserting ≥2 concurrent panels, ≥1 budget tick/child, ≥1 applied correction, ≥1 rebalance, aggregated multi-child turn, clean post-gather M9-08 region state. Greens MAG-08. | 4 | M13-04, M13-05 | MAG-08 |

## Wave Structure Summary

| Wave | Plans | Parallel? | Files (ownership) |
|------|-------|-----------|-------------------|
| 0 | M13-01 | n/a (single) | 5 new test files + `tests/harness/conftest.py` fixture + `tests/harness/tui/test_keymap_baseline.py` (additive) |
| 1 | M13-02 | n/a (single) | `voss/harness/multiagent.py` (create) |
| 2 | M13-03 ∥ M13-04 | yes — disjoint file sets | 2A: `multiagent.py` (extend), `agent.py` · 2B: `renderer.py`, `app.py`, `sub_agent_panel.py`, `keymap.py`, `test_keymap_baseline.py` |
| 3 | M13-05 | n/a (single) | `voss/harness/multiagent.py` (extend) — serial after 2A |
| 4 | M13-06 | n/a (single) | `voss/harness/cli.py`, `tests/e2e/test_multiagent_chat_e2e.py` |

## Coverage Audit (every MAG in ≥1 plan)

| Req | Covered By | Headline e2e roll-up |
|-----|------------|----------------------|
| MAG-01 (concurrent fan-out) | M13-01 (red), M13-03 (green) | M13-06 |
| MAG-02 (live quiet panels + ctrl+o) | M13-01 (red), M13-04 (green) | M13-06 |
| MAG-03 (even-split reserve) | M13-01 (red), M13-02 (green) | M13-06 |
| MAG-04 (recursive no-oversell, must-not-happen) | M13-01 (red), M13-02 (green non-recursive+exactly-once+race), M13-05 (depth-bound recursive) | M13-06 |
| MAG-05 (autonomous course-correction) | M13-01 (red), M13-03 (green) | M13-06 |
| MAG-06 (recursive spawn depth>1) | M13-01 (red), M13-05 (green) | M13-06 |
| MAG-07 (gather + clean teardown) | M13-01 (red), M13-04 (green) | M13-06 |
| MAG-08 (headline e2e) | M13-01 (red), M13-06 (green) | M13-06 |

No MAG unplanned. No source-artifact item omitted or simplified. No scope reduction. Boundaries respected: no `VossAgent.spawn` routing, no O1 `SessionTreeManager`, no disk persistence, no child↔child, no human-redirect, no depth constant, `subagents.py`/`/agent spawn`/`voss agent spawn`/`keymap.py:37` byte-stable. The 3 RESEARCH open questions are each pinned to a specific task action (A1→M13-02, A2→M13-03, A3→M13-04) — resolved in-task, not deferred.

## OUTLINE COMPLETE

**Plan count:** 6 plans across 5 waves (W0→W1→W2[2 parallel]→W3→W4). Wave 2 has the only intra-wave parallelism (M13-03 ∥ M13-04, disjoint file sets). Every MAG-01..MAG-08 appears in ≥1 plan's Requirements column.
