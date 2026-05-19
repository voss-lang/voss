# Phase M13: Multi-agent in Chat (CAPS-01d) — Specification

**Created:** 2026-05-18
**Ambiguity score:** 0.17 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

A `voss chat` user's natural-language request causes the parent chat agent to autonomously delegate work to **concurrent** sub-agents on the hardened `subagent_run` path — each sub-agent gets an even-split slice of a parent budget reserve (recursively, depth > 1), renders in its own quiet-by-default M9 `SubAgentPanel` (live state revealable with Ctrl+C, Claude-Code-style), the parent can inject mid-run course-correction into a running child, and results are gathered back into the chat turn — with a hard no-budget-oversell invariant.

## Background

Two **disconnected** spawn systems exist today:

- `voss_runtime/agent.py` — `VossAgent.spawn` → `AgentHandle`, `gather()`. Concurrent-capable runtime/`.voss` primitive. **NOT** wired into chat.
- `voss/harness/subagents.py` — `SubagentSpec`/`SubagentRegistry`/`default_subagent_registry()` (explorer/worker/reviewer), `run_subagent()` (lines 76–103), `attach_subagent_tool()` → `subagent_run` tool. **This is what `voss chat` attaches** (`cli.py:1634`). It is **serial, blocking, single-child**, runs `run_turn` with a fresh `Renderer` that has no bridge back to the parent panel.

M9 scaffolded the UI but the data flow is incomplete:
- `SubAgentPanel` widget exists (`tui/widgets/sub_agent_panel.py`) with header + embedded `BudgetMeter` + body + `append_body`/`update_budget`.
- Renderer detects `subagent_run` (`SPAWN_TOOL_NAME`) → `show_subagent_start` on tool call, `show_subagent_end` on result. **`show_subagent_progress` is defined (`renderer.py:203`) but never called** — the panel shows start → collapse with nothing in between.
- `SubAgentPanel.budget_total` is fed `0` → `BudgetMeter` shows the em-dash placeholder always. **No `BudgetScope` / partition logic exists** in `subagents.py` or `agent.py`.
- **No message bus / child-input channel exists** anywhere in the codebase.
- `/agent spawn <id> <task>` slash + `voss agent spawn` CLI exist but are serial single-child.

M13 is a **wiring + orchestration phase** on the `subagent_run` path — not a greenfield engine and not a rewrite onto `VossAgent.spawn`. O1 (Session-Tree Substrate, planned) explicitly *builds on* M13's raw fan-out; M13 must therefore keep its budget/fan-out logic M13-local and in-memory, not pre-adopt O1's `SessionTreeManager` or disk persistence.

## Requirements

1. **Concurrent fan-out (subagent_run path)**: The chat agent can have ≥2 sub-agents in flight simultaneously via the `subagent_run` surface.
   - Current: `subagent_run` `await`s a single `run_subagent` to completion before returning — serial, one child, blocking the parent turn.
   - Target: A fan-out form on the `subagent_run` path schedules multiple children concurrently (harness-local asyncio fan-out — NOT `VossAgent.spawn`), parent turn continues while children run.
   - Acceptance: A test asserts ≥2 children are observably in-flight at the same instant (overlapping run windows), not awaited one-by-one.

2. **Live, quiet-by-default panels**: Each running child has its own `SubAgentPanel` whose state is live but visually quiet until the user expands it.
   - Current: `show_subagent_progress`/`update_subagent` are wired end-to-end but never invoked; panel goes start → collapse with no body and an em-dash budget meter.
   - Target: Child steps stream into the panel's backing state and the budget meter ticks live; by default the panel stays compact (no per-step body flood); a user keypress (user-specified Ctrl+C, Claude-Code-style expand) reveals the streamed per-child step detail.
   - Acceptance: During a child run, its panel's budget meter moves off the em-dash placeholder and increases ≥1 time before collapse; default view does not render the verbose step body; the reveal keybinding toggles a detailed step view containing ≥1 streamed child step.

3. **Even-split reserve budget partitioning**: The parent's budget reserve is divided evenly across active children and rebalanced as children finish.
   - Current: No budget partition; `run_subagent` runs the child with no budget scope; `SubAgentPanel.budget_total` is `0`.
   - Target: An M13-local even-split allocator carves a parent reserve, divides it evenly across currently-active children, and rebalances the freed slice when a child finishes — surfaced live in each panel's `BudgetMeter`.
   - Acceptance: With a reserve R and N concurrent children, each child's allotment ≈ R/N; when one child finishes, a still-running child's allotment increases on rebalance; panel meters reflect the change.

4. **No-oversell invariant (recursive)**: Total allocated child budget never exceeds the parent's reserve, at any nesting depth.
   - Current: No allocation accounting exists, so no oversell guard exists.
   - Target: A check-and-allocate guard (race-safe) ensures Σ(active child allotments) ≤ parent reserve at every level; rebalance never double-counts a finished child's freed budget; a child is denied a spawn when its allocatable slice falls below a viable floor (this also bounds recursion).
   - Acceptance: A concurrent-allocation test proves Σ child budgets ≤ reserve under racing spawns; a rebalance test proves a finished child's freed budget is credited exactly once; a depth>1 test proves a grandchild's allotment is bounded by its parent-child's slice.

5. **Autonomous-parent course-correction**: The parent chat agent can inject mid-run guidance into a still-running child; the child observably acts on it.
   - Current: No child-input channel; once `run_subagent` starts, the child cannot receive new instructions.
   - Target: A parent-callable harness tool injects a guidance message into a targeted running child via a harness-mediated channel (parent → child only; no human-in-loop trigger, no child → child). The child consumes it before finishing.
   - Acceptance: A test with a scripted parent injects a correction into a running child and asserts the child's subsequent behavior/output observably changes versus the no-correction control.

6. **Recursive spawn (depth > 1)**: A sub-agent may itself spawn sub-agents; nested budget and nested panels behave correctly.
   - Current: Single flat level only; children have no `subagent_run` in their toolset wired for nesting/budget.
   - Target: Children can invoke `subagent_run`; nested children get an even-split of their parent-child's allotment (Req 3 recursively) and render nested `SubAgentPanel`s; the no-oversell invariant (Req 4) holds at every depth.
   - Acceptance: A depth-2 test spawns parent → child → grandchild; grandchild budget ≤ child slice; nested panels mount and collapse without leaking; no-oversell holds across all 3 levels.

7. **Gather + clean teardown**: Concurrent children are gathered back into the chat turn and the side region is restored cleanly.
   - Current: `collapse_subagent` removes the panel and posts `"✓ gathered · N results"`; only the single serial child is handled.
   - Target: All concurrent children are awaited/gathered, each result aggregated into the parent turn; on final gather every `SubAgentPanel` is removed and the side region pin/owner state is restored (CodeIntelPanel or hidden per existing M9-08 contract).
   - Acceptance: After a multi-child fan-out completes, the turn contains an aggregated result referencing all children; zero `SubAgentPanel` instances remain mounted; `_side_owner`/`_side_pinned` match the pre-spawn contract.

8. **Headline e2e transcript**: One end-to-end test proves the full scenario.
   - Current: No multi-agent chat e2e exists.
   - Target: A stub-provider `voss chat` e2e where one NL request fans to ≥2 concurrent `SubAgentPanel`s (live progress + budget), the parent injects ≥1 mid-run course-correction into a child, the even-split reserve rebalances when a child finishes, and `gather` aggregates results into the turn — all asserted in one test.
   - Acceptance: The e2e passes deterministically under the stub provider and asserts: ≥2 concurrent panels, ≥1 budget tick per child, ≥1 applied correction, ≥1 rebalance event, aggregated multi-child turn output, clean post-gather region state.

## Boundaries

**In scope:**
- Concurrent fan-out on the hardened `subagent_run` path (harness-local asyncio)
- Live per-child `SubAgentPanel` state; quiet-by-default; Ctrl+C-style reveal of streamed child steps
- M13-local even-split-of-reserve budget allocator with rebalance-on-finish
- Recursive no-oversell invariant + viable-floor spawn denial
- Autonomous-parent → running-child course-correction channel (a parent tool)
- Recursive spawn depth > 1 (nested panels + nested even-split budget)
- `gather` aggregation into the chat turn + post-gather region/panel cleanup
- One stub-provider headline e2e transcript test

**Out of scope:**
- Wiring `voss_runtime/agent.py` `VossAgent.spawn`/`gather` as the chat surface — chose to harden `subagent_run`; the runtime primitive stays a `.voss`-workflow concern
- Child → child direct messaging — all routing is parent-mediated (orchestrator model)
- User-driven / human-in-loop course-correction — autonomous parent only
- Disk persistence of sub-agent sessions (`.voss/sessions/` tree) — that is O1's SessionTree substrate
- Reusing or pre-adopting O1's `SessionTreeManager` / fan-out cage — O1 builds on M13, not the reverse; M13 budget/fan-out stays M13-local + in-memory
- Cross-machine / distributed agents — deferred beyond v0.2 (ROADMAP)
- Multi-agent memory partitioning beyond per-agent budgets — ROADMAP out-of-scope

## Constraints

- The chat fan-out mechanism MUST be on the `subagent_run` path using harness-local concurrency (asyncio); it MUST NOT route through `voss_runtime` `VossAgent.spawn`/`gather`.
- The even-split-reserve allocator MUST be M13-local and in-memory for the chat turn; it MUST NOT depend on or anticipate O1's `SessionTreeManager` or any disk-backed session tree.
- The no-oversell guard MUST be race-safe under concurrent spawns and hold recursively at every nesting depth (O1 precedent: allocator-level `asyncio.Lock`, no oversell — M13 implements its own minimal version).
- Course-correction is **autonomous-parent-triggered only** (the parent LLM decides, via a tool call); there is no human-redirect path and no child→child path.
- Reuse the existing M9 `SubAgentPanel` / `BudgetMeter` widgets and the renderer's existing `show_subagent_start`/`_progress`/`_end` + `app.update_subagent`/`collapse_subagent` seams. No new panel widget types unless nesting strictly requires it.
- Panels are quiet by default (no per-step body flood); the reveal binding the user specified is **Ctrl+C** (Claude-Code-style expand). Ctrl+C collides with SIGINT/interrupt convention — resolving the exact keybinding and interrupt semantics is a **discuss-phase (HOW) decision**, not a SPEC change.
- Determinism: the headline e2e and all budget/concurrency tests MUST pass under the stub provider with no live network.

## Acceptance Criteria

- [ ] ≥2 sub-agents run concurrently from a single chat request (overlapping in-flight windows proven, not serial)
- [ ] Each running child's `SubAgentPanel` budget meter leaves the em-dash placeholder and increments ≥1 time before collapse
- [ ] Panel is compact by default (no verbose per-step body); the reveal keybinding toggles a detailed view containing ≥1 streamed child step
- [ ] With reserve R and N concurrent children, each allotment ≈ R/N; a still-running child's allotment increases when another child finishes (rebalance observed in the meter)
- [ ] Σ(active child budgets) ≤ parent reserve under racing concurrent spawns (no oversell)
- [ ] A finished child's freed budget is credited exactly once on rebalance (no double-count)
- [ ] Depth-2 spawn (parent→child→grandchild): grandchild allotment ≤ child slice; no-oversell holds at all 3 levels; nested panels mount and collapse without leaking
- [ ] A scripted-parent correction injected into a running child observably changes that child's behavior vs the no-correction control
- [ ] After gather, the turn output aggregates all children's results; zero `SubAgentPanel`s remain mounted; side-region pin/owner state matches the pre-spawn M9-08 contract
- [ ] One stub-provider headline e2e asserts all of: ≥2 concurrent panels, ≥1 budget tick/child, ≥1 applied correction, ≥1 rebalance, aggregated multi-child turn, clean post-gather region

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                            |
|--------------------|-------|------|--------|------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Surface, concurrency, budget, correction, depth, UX all locked   |
| Boundary Clarity   | 0.82  | 0.70 | ✓      | Runtime spawn/gather, child↔child, disk, O1 cage explicitly out  |
| Constraint Clarity | 0.80  | 0.65 | ✓      | M13-local even-split, recursive no-oversell, autonomous-only     |
| Acceptance Criteria| 0.74  | 0.70 | ✓      | 10 pass/fail checkboxes; Ctrl+C-binding deferred to discuss      |
| **Ambiguity**      | 0.17  | ≤0.20| ✓      |                                                                  |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                                 |
|-------|-------------------|---------------------------------------------------|---------------------------------------------------------------------------------|
| 1     | Researcher        | Which spawn surface — runtime vs subagent_run?    | Harden `subagent_run`; `voss_runtime` spawn/gather stays out of chat            |
| 1     | Researcher        | Concurrency model?                                | Concurrent children + gather (not serial)                                       |
| 1     | Researcher        | What is the "message bus"?                         | Parent-orchestrator delegation (parent-mediated, not pub/sub, not child↔child)  |
| 2     | Simplifier        | Orchestrator-intervention powers?                 | Full course-correct — parent injects mid-run guidance into a running child      |
| 2     | Researcher        | Budget split model?                               | Even-split of a parent reserve, rebalanced as children finish                   |
| 2     | Simplifier        | Irreducible MVP core?                              | Orchestrator NL-delegation UX is the core; raw concurrency secondary            |
| 3     | Boundary Keeper   | Correction trigger?                               | Autonomous parent only (LLM via tool); no human-redirect, no child↔child        |
| 3     | Boundary Keeper   | Confirm out-of-scope?                              | Disk persistence OUT (→ O1); runtime spawn/gather + child↔child already OUT      |
| 3     | Boundary Keeper   | Headline "done" scenario?                          | Single e2e: fan-out + mid-run correction + budget rebalance + gather transcript  |
| 4     | Failure Analyst   | Recursive spawn allowed?                           | Yes — depth > 1; nested even-split + nested panels; no-oversell holds recursively|
| 4     | Failure Analyst   | Minimum "live progress" bar?                       | Steps streamed, panels quiet by default, Ctrl+C reveals detail (Claude-Code-style)|
| 4     | Failure Analyst   | Must-not-happen rejection guard?                   | Budget oversell — recursive no-oversell invariant test mandatory                |

---

*Phase: M13-multi-agent-in-chat-caps-01d*
*Spec created: 2026-05-18*
*Next step: /gsd:discuss-phase M13 — implementation decisions (Ctrl+C-vs-SIGINT binding, asyncio fan-out shape, child-input channel design, nested-panel rendering)*
