# Phase F3: Budget & Token Visualization - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Live HUD in voss-app showing token budget consumption and cost accumulation for agent panes. Budget/cost data flows from the Voss harness process (running inside a PTY pane) to the ADE UI via custom OSC escape sequences in the PTY stream. Per-pane display in the 22px Variant B header; click-to-popover for detail. Shell panes show nothing.

</domain>

<decisions>
## Implementation Decisions

### Data Pipeline — harness → ADE
- **D-01:** **OSC escape sequences in PTY stream.** Harness emits custom OSC codes interleaved with terminal output. Rust PTY reader (`reader.rs`) parses them out before forwarding display bytes. Zero new IPC — reuses existing `Channel<PtyEvent>` with a new `BudgetUpdate` variant. Same pattern as OSC title (already parsed in A2).
- **D-02:** **OSC 1337 with `voss-budget=` prefix.** Format: `ESC]1337;voss-budget={json}BEL`. Extensible namespace for future Voss OSC types (`voss-context=`, `voss-confidence=`, etc.). 1337 range widely used for terminal extensions (iTerm2, WezTerm, Kitty).
- **D-03:** **Cumulative totals payload.** Each OSC emission contains `tokens_used`, `token_limit`, `cost_usd`, `iteration`, `model`. Frontend renders latest values — no accumulation logic needed. Idempotent: missed messages are harmless, next one has full state.
- **D-04:** **Emit after each LLM response.** One emission per agent iteration, at the `end_iteration()` call site in `recorder.py`. Natural cadence — 1-2 emissions per agent turn.

### HUD Placement & Display
- **D-05:** **Per-pane header bar.** Budget meter lives in the 22px PaneHeader (A3-05 Variant B chrome). Each agent pane shows its own budget/cost inline. Shell panes show nothing.
- **D-06:** **Right-aligned cost + mini progress bar.** Cost text (`$0.08`) + mini progress bar (8-10 chars wide) right-aligned before the `⋯` menu. Uses semantic token colors: `--text-2` for cost, `--accent` for bar fill, `--bg-2` for bar track.
- **D-07:** **Cost-only when no budget limit.** Show just `$0.08` with no progress bar when `token_limit` is absent/unlimited. Bar only appears when a budget cap exists. Cost always shows for agent panes.
- **D-08:** **3-tier color thresholds.** 0-70% = `--accent` (normal), 70-90% = `--warning` (yellow), 90-100% = `--error` (red). Same semantic tokens used across Variant B.

### Metrics Scope & Detail
- **D-09:** **Cost + budget bar in header; detail in popover.** Always-visible: cost + progress bar. Click budget segment → popover card with tokens (used/limit), model name, iteration count, full cost, expanded progress bar.
- **D-10:** **Click-to-popover detail.** Reuses A10 `<Popover>` component pattern (A10 D-04). Dismiss on click-outside/Esc. One popover at a time (matches A10 D-01).
- **D-11:** **No ADE-side budget persistence.** Budget display resets on restart. F1 restarts the agent CLI; first OSC emission from the resumed harness repopulates the HUD with cumulative totals (D-03 self-heal). Brief blank between mount and first emission (seconds) is acceptable.

### Update Cadence & Performance
- **D-12:** **Per-pane local signal, no global store.** Each PaneComponent owns its budget state via a local Solid signal. N panes = N independent stores. No cross-pane coordination, no global budget store.
- **D-13:** **150ms CSS transition on bar width.** Bar fill animates via CSS `transition: width 150ms ease-out`. Cost text updates instantly. `prefers-reduced-motion` kill switch applies (A8 D-11).
- **D-14:** **No debounce in Rust reader.** Budget OSC emissions are per-LLM-response (~once every 2-30 seconds). No rapid-fire scenario. Each pane has its own `Channel<PtyEvent>`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### PTY Backend (OSC parsing + Channel events)
- `crates/voss-app-core/src/pty/reader.rs` — PTY reader loop, `Channel<PtyEvent>`. F3 adds OSC 1337 parsing + `BudgetUpdate` event variant here.
- `crates/voss-app-core/src/pty/commands.rs` — `PtyEvent` enum definition. F3 adds `BudgetUpdate(BudgetData)` variant.
- `crates/voss-app-core/src/pty/mod.rs` — PtySession, PtyRegistry. Context for reader architecture.

### Pane Header (HUD integration point)
- `apps/voss-app/src/grid/PaneHeader.tsx` — A3-05 22px Variant B header. F3 adds budget segment (cost + bar) right-aligned before `⋯` menu.
- `apps/voss-app/src/grid/DotMenu.tsx` — `⋯` menu. Budget segment sits to the left of this.
- `apps/voss-app/src/pane/PaneComponent.tsx` — PTY event handler. F3 adds `BudgetUpdate` event routing to local signal.

### Harness Budget/Cost Tracking (emission source)
- `voss/harness/recorder.py` — `end_iteration()` with `cost_usd`. F3 adds OSC emission call here.
- `voss/harness/agent.py` — Agent loop, `token_budget`, `_run_turn_exec()`. Context for emission timing.
- `voss/harness/session.py` — `IterationRecord.cost_usd`, `SessionSummary.total_cost_usd`. Payload field sources.

### Variant B Token System
- `apps/voss-app/src/styles/variant-b.css` — Semantic tokens (`--accent`, `--warning`, `--error`, `--text-2`, `--bg-2`). F3 budget bar uses these.
- `apps/voss-app/src/index.css` — Tailwind v4 `@theme inline` map.

### A10 Popover Component (reuse target)
- `.planning/phases/A10-voss-app-status-bar/A10-CONTEXT.md` — D-04 generic `<Popover>` component. F3 reuses for budget detail.

### F1 Agent Identity (agent pane detection)
- `.planning/phases/F1-durable-session-persistence/F1-CONTEXT.md` — D-06 `agentConfig` prop on PaneComponent. F3 uses this to distinguish agent panes from shell panes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PtyEvent` enum in `commands.rs` — add `BudgetUpdate` variant alongside existing `Data`/`Exit` variants
- A2 OSC title parsing in `PaneComponent` — A2 already handles `OSC 0/2` for window title. F3 adds 1337 budget parsing in the same layer (but in Rust reader, not frontend)
- `Channel<PtyEvent>` — established streaming IPC from Rust reader to frontend. Budget events flow through same channel
- A10 `<Popover>` component — generic anchor-positioned popover with click-outside/Esc dismiss. Budget detail reuses this
- `BudgetMeter` / `ConfidenceBar` TUI widgets in harness — design reference for bar visual language (not code-reusable, wrong framework)

### Established Patterns
- **Per-pane PTY Channel:** Each pane has independent `Channel<PtyEvent>`. Budget events are per-pane by default — no routing needed.
- **Variant B 22px header:** PaneHeader renders dot/index/cwd/shell/process/`⋯`. F3 inserts budget segment between process and `⋯`.
- **CSS transitions:** A8 D-11 established 150ms/200ms transitions with `prefers-reduced-motion` kill switch. Budget bar follows same convention.
- **Semantic color tokens:** `--accent`, `--warning`, `--error` already in token system for exactly this kind of progressive-severity signaling.

### Integration Points
- **Rust reader.rs:** Parse `ESC]1337;voss-budget=...BEL` from PTY byte stream, emit `PtyEvent::BudgetUpdate`. Strip OSC from display bytes.
- **PaneComponent PTY event handler:** Route `BudgetUpdate` events to local `budget` signal.
- **PaneHeader render:** Conditionally render `<BudgetBar>` when `budget()` signal is non-null (agent panes only).
- **Harness recorder.py:** Add `_emit_budget_osc()` call at `end_iteration()`.

</code_context>

<specifics>
## Specific Ideas

- OSC 1337 namespace allows future extension: `voss-context=`, `voss-confidence=`, `voss-status=` — same parser, different event variants.
- Budget popover card layout: tokens (used/limit), model, iterations, cost, expanded progress bar — read-only informational, matches A10 D-03 pane detail card pattern.
- Cost format: `$X.XX` for < $1, `$X.XXXX` for < $0.01 (4 decimal places for small amounts, consistent with harness TUI `turn_view.py` formatting).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: F3-budget-token-visualization*
*Context gathered: 2026-05-21*
