# Phase M13: Multi-agent in Chat (CAPS-01d) - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire + orchestrate concurrent sub-agents into `voss chat` on the **hardened `subagent_run` path** (NOT `voss_runtime` `VossAgent.spawn`/`gather`). The parent chat agent autonomously delegates an NL request to concurrent children; each child gets an even-split slice of an in-memory parent budget reserve (recursively, depth > 1); each renders in its own quiet-by-default M9 `SubAgentPanel` (detail revealable, key bound to **Ctrl+O**); the parent can autonomously inject mid-run course-correction into a running child; results gather back into the turn — with a hard recursive **no-budget-oversell** invariant.

Requirements are LOCKED in `M13-SPEC.md` (MAG-01..08, ambiguity 0.17). This CONTEXT covers HOW only.

**Out of scope (LOCKED — from SPEC, do not reopen):**
- `voss_runtime/agent.py` `VossAgent.spawn`/`gather` as the chat surface — harden `subagent_run` instead; runtime primitive stays a `.voss`-workflow concern.
- Child → child direct messaging — all routing parent-mediated.
- User-driven / human-in-loop course-correction — autonomous parent only.
- Disk persistence of sub-agent sessions — O1 SessionTree substrate owns that.
- Reusing/pre-adopting O1's `SessionTreeManager` / fan-out cage — **O1 builds on M13, not the reverse**. M13 budget + fan-out stays M13-local + in-memory.
- Cross-machine agents; memory partitioning beyond per-agent budgets — ROADMAP out.

</domain>

<decisions>
## Implementation Decisions

### Fan-out shape (MAG-01)
- **D-01:** **Non-blocking** spawn. Add a fan-out tool on the `subagent_run` path that schedules each child as an `asyncio` task and **returns child handle id(s) immediately** — the parent turn continues while children run. Concurrency = harness-local `asyncio` (`create_task`/`gather`), explicitly **not** `VossAgent.spawn`. Forced by MAG-05: autonomous mid-run correction requires the parent active *between* spawn and gather, which a blocking batch-gather tool cannot provide.
- **D-02:** Children tracked in an **in-memory `ChildRegistry`** keyed by handle, scoped to the chat turn. No disk (O1 owns persistence). Existing serial `subagent_run` + `/agent spawn` slash stay as-is for back-compat (single-shot convenience); the new non-blocking tools are additive.

### Steering channel (MAG-05)
- **D-03:** Per-child **`asyncio.Queue` inbox**. Parent calls a `subagent_steer(handle, guidance)` tool; guidance is enqueued to the targeted child. Parent → child only, harness-mediated. Trigger is **autonomous parent (LLM) only** — no human-redirect path, no child↔child.
- **D-04:** **Steer cadence = between agent iterations.** The child's `run_turn` loop drains its inbox at the loop boundary (after a tool round, before the next model call) and injects drained guidance as a steering message into the child's next iteration. No mid-tool-call preemption/cancellation. Deterministic + stub-testable.

### Budget partitioning (MAG-03 / MAG-04 / MAG-06)
- **D-05:** **M13-local even-split-of-reserve allocator, in-memory.** A parent reserve is carved, divided evenly across currently-active children, and rebalanced when a child finishes (freed slice credited **exactly once**). Surfaced live in each panel's `BudgetMeter`. Not O1's `SessionTreeManager`.
- **D-06:** **No-oversell guard** = `asyncio.Lock`-guarded check-and-allocate at the single spawn site (O1 precedent: allocator-level lock, race-safe). Σ(active child allotments) ≤ parent reserve at **every nesting depth**.
- **D-07:** **Recursion** (depth > 1, MAG-06): a child's toolset gets the same spawn/steer/gather tools plus a **sub-allocator scoped to that child's own slice**. Recursion is bounded naturally by a **viable-budget floor** — a spawn is denied when its allocatable slice falls below the floor. No separate hard depth cap.

### Live panel + reveal UX (MAG-02)
- **D-08:** Wire the **currently-dead `show_subagent_progress` / `app.update_subagent` seam** (`renderer.py:203`, never called today). Each child's `Renderer` is wrapped with a bridge that posts per-step lines + budget ticks to that child's `SubAgentPanel` via `parent_id`. Reuse the existing M9 `SubAgentPanel` / `BudgetMeter` widgets — no new panel widget types unless nesting strictly requires it.
- **D-09:** Panel is **quiet by default** (compact: header + `BudgetMeter` + mini-status; no per-step body flood). Detail/streamed-step view is **revealed by Ctrl+O** (Claude-Code "expand" convention). **Ctrl+C stays interrupt** (`keymap.py:37` global `interrupt`, unchanged). Add a single new `ctrl+o` binding to `keymap.py` — additive only (T8 precedent: keymap is M9 single-source-of-truth, never rewritten).

### Gather + teardown (MAG-07)
- **D-10:** A `subagent_gather` tool awaits all outstanding handles, aggregates each child result into the parent turn, then triggers the existing `app.collapse_subagent` cleanup so every `SubAgentPanel` is removed and the side-region pin/owner state is restored per the existing **M9-08** contract (`app.py:184`).

### Test posture (MAG-08)
- **D-11:** Deterministic + hermetic, **stub provider, no live network** (T7/T8 precedent). The headline e2e + no-oversell race test + correction-changes-behavior test + concurrency-proof + depth-2 test + post-gather region-clean assertion all run under the stub.

### Claude's Discretion
- Exact tool names (`subagent_spawn`/`subagent_steer`/`subagent_status`/`subagent_gather` are working names — planner finalizes, consistent with `SPAWN_TOOL_NAME` detection in `renderer.py`).
- `ChildRegistry` data structure + handle id scheme.
- Renderer-bridge wiring technique (how the child Renderer posts to `parent_id` panel without cross-thread hazards — note renderer thread-safety comment `renderer.py:7`).
- `gather` aggregation output format in the turn.
- Exact viable-budget-floor threshold value (sensible default; must bound recursion).
- Reveal/detail view layout inside the expanded panel.
- Whether the new non-blocking tools subsume or sit beside `subagent_run` internally (back-compat of `/agent spawn` slash is the only hard constraint).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements (LOCKED — primary contract)
- `.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-SPEC.md` — MAG-01..08, boundaries, constraints, 10 acceptance checkboxes, ambiguity report. **This is the authority; CONTEXT only adds HOW.**
- `.planning/ROADMAP.md` §"Phase M13: Multi-agent in Chat (CAPS-01d)" (~line 590) — goal narrative, headline deliverables, cross-cutting (depends on M9 SubAgentPanel; compounds with M4 dogfood), ROADMAP out-of-scope.
- `.planning/seeds/agent-capability-surface.md` §capability 4 — original intent (spawn/gather to chat, sub-agent message bus visible, M4 dogfood compounds).

### Spawn infra (the path M13 hardens)
- `voss/harness/subagents.py` — `SubagentSpec`/`SubagentRegistry`/`default_subagent_registry()` (explorer/worker/reviewer), `run_subagent()` (76–103, currently serial/blocking/fresh-Renderer), `attach_subagent_tool()` → `subagent_run`, `SPAWN_TOOL_NAME = "subagent_run"`.
- `voss/harness/cli.py` — chat wiring: `attach_subagent_tool` (~1634), `/agents` + `/agent spawn` slash (~1206), `voss agent spawn` CLI (~2430). Back-compat anchor.
- `voss_runtime/agent.py` — `VossAgent.spawn`/`AgentHandle`/`gather`. **Reference only — explicitly NOT the chat surface (LOCKED out). Read to confirm M13 does not route through it.**

### M9 TUI seams (M13 wires the dead ones; reuses, never redesigns)
- `voss/harness/tui/widgets/sub_agent_panel.py` — `SubAgentPanel` (header + embedded `BudgetMeter` + body; `append_body`/`update_budget`; em-dash on `budget_total<=0`).
- `voss/harness/tui/renderer.py` — `show_subagent_start`/`_progress`(**dead, line 203**)/`_end`; `SPAWN_TOOL_NAME` detection (~170); thread-safety note (line 7, subagents run in worker threads).
- `voss/harness/tui/app.py` — `mount_subagent_panel`/`update_subagent`/`collapse_subagent` + M9-08 pin/region-share (`show_subagent_panel`/`pin_side_panel`/`restore_code_intel_panel`, ~169–249).
- `voss/harness/tui/keymap.py` — M9 single-source keymap (contexts global|input|main|modal); `ctrl+c→global interrupt` (line 37, **unchanged**). M13 adds one `ctrl+o` binding only.

### O1 relationship boundary (do NOT pre-adopt — O1 builds on M13)
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-SPEC.md` + `O1-CONTEXT.md` — O1 owns `SessionTreeManager`, disk-persisted session tree, the budget fan-out cage. Read to confirm M13's allocator stays M13-local + in-memory and does not duplicate or depend on O1. (O1 RESEARCH precedent reused: `asyncio.Lock` at allocator, no-oversell race, reserve-carve.)

### Test posture precedent
- `.planning/phases/T7-skills-bootstrap/T7-CONTEXT.md` D-09..D-11; `.planning/phases/T8-input-bar-ergonomics-v0-2/T8-CONTEXT.md` D-06/keymap-additive — deterministic/hermetic stub-provider posture; keymap is additive-only.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SubAgentPanel` + `BudgetMeter` — render target; reuse as-is (em-dash zero-total contract already correct).
- `show_subagent_progress`/`update_subagent`/`collapse_subagent` — full seam exists, only `_progress`/`update_subagent` is uncalled; M13 supplies the missing caller.
- `run_subagent()` + `attach_subagent_tool()` — the path to harden; child `run_turn` loop is where the steer-inbox drain (D-04) hooks.
- O1 RESEARCH/PATTERNS — `asyncio.Lock` no-oversell allocator pattern is directly liftable (M13-local copy, not an O1 import).

### Established Patterns
- M9-08 side-region pin/owner contract — gather teardown must honor it (restore CodeIntelPanel or hide per `_side_pinned`/`_side_owner`).
- Keymap region tables, additive-only (T8) — `ctrl+o` added, never a rewrite.
- Stub-provider hermetic tests (T7/T8) — scripted parent drives autonomous spawn/steer deterministically.
- Renderer worker-thread note (`renderer.py:7`) — bridge posts must respect existing thread-safe `_post` mechanism, not direct widget mutation.

### Integration Points
- New non-blocking spawn/steer/status/gather tools (subagent_run path) ↔ `ChildRegistry` (in-memory) ↔ per-child `asyncio.Queue` ↔ child `run_turn` loop drain ↔ M13-local even-split allocator (`asyncio.Lock`) ↔ child `Renderer` bridge → `SubAgentPanel` (via `parent_id`) ↔ `app.collapse_subagent` + M9-08 restore.
- Recursion: child toolset re-receives spawn/steer/gather + a slice-scoped sub-allocator (D-07).
- `ctrl+o` (new keymap binding) ↔ `app` SubAgentPanel detail toggle (D-09).

</code_context>

<specifics>
## Specific Ideas

- Reveal/expand UX explicitly modeled on **Claude Code**: quiet panels by default, a key (Ctrl+O) expands to see streamed sub-agent steps. Ctrl+C must remain interrupt (user-confirmed deviation from the literal SPEC "Ctrl+C reveals" wording).
- Parent is an **orchestrator**: delegates, decides tasks, "keeps subagents in their lanes", deals with issues via autonomous mid-run steering — not a generic pub/sub bus.
- No-oversell is the **must-not-happen** rejection guard (Failure Analyst round) — the recursive Σ ≤ reserve invariant test is mandatory, not optional.

</specifics>

<deferred>
## Deferred Ideas

- O1 Session-Tree substrate (disk-persisted tree, generalized fan-out cage) — O1 builds *on* M13's raw in-memory fan-out; M13 must stay minimal so O1 has a clean substrate to wrap.
- User-driven manual child redirect — considered, rejected for M13 (autonomous-parent only). Candidate for a later UX phase if demand surfaces.
- Mid-tool-call preemptive cancellation of a child — considered, rejected (steer cadence is between-iterations only); revisit only if reaction latency proves unacceptable.

</deferred>

---

*Phase: M13-multi-agent-in-chat-caps-01d*
*Context gathered: 2026-05-18*
*Next step: /gsd:plan-phase M13 (SPEC + CONTEXT both locked; researcher reads canonical_refs, planner treats D-01..D-11 as fixed)*
