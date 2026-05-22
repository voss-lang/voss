# Phase F4: Visual Context Heatmap - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Collapsible side panel in voss-app ADE showing which files are in the focused agent pane's LLM context window, their compression state (full/compressed/dropped), token usage per file, and manual pinning to protect files from compression. Data flows from the Voss harness process via custom `voss-context=` OSC escape sequences (extending the F3 `voss-budget=` pattern). Reverse channel for pin commands uses PTY stdin injection. Shell panes show empty state. Panel persists open/closed across restarts.

</domain>

<decisions>
## Implementation Decisions

### Panel Hosting
- **D-01:** **Collapsible right-side panel (~240px).** Toggle via ⌘I or status bar button. Persistent when open — slides in/out. Matches IDE sidebar pattern, closes the "terminal spawner" gap.
- **D-02:** **Per-pane scope.** Panel shows context for the focused pane only. Content switches on focus change. Each agent has its own context window — showing one at a time is honest.
- **D-03:** **Outside grid (overlay).** Panel overlays the right edge of the app. Grid does not reflow when panel opens/closes. No grid model changes needed.
- **D-04:** **Panel header = "Context — ●3 ~/project".** Pane index dot + cwd, matching PaneHeader style. Updates on focus change.
- **D-05:** **Fixed 240px width.** No drag-resize. Consistent.
- **D-06:** **Persist open/closed in settings.json.** `~/.config/voss-app/settings.json` (A9 settings file). Reopens on launch if was open.
- **D-07:** **150ms CSS slide transition.** `transform: translateX()` with 150ms ease-out. `prefers-reduced-motion` kill switch per A8 D-11.
- **D-08:** **Empty state with muted hint when shell pane focused.** "No agent context — focus an agent pane" in `--text-3`. Panel stays mounted.
- **D-09:** **Status bar toggle button (A10 right cluster).** ⌘I keybind always works. Button gives visual affordance.
- **D-10:** **No search/filter in F4.** Scroll suffices for typical file lists (<50). Defer search to later.
- **D-11:** **Panel z-layer below overlays.** Same z-tier as grid. Command palette, popovers, dot menus render on top.
- **D-12:** **Compact summary row at panel top.** "1,248 / 200k tokens" with progress bar. Quick orientation before file list.

### Data Granularity
- **D-13:** **Per-file rows.** Each row = one file path with token count + state indicator. User thinks in files.
- **D-14:** **3-state model — full (green) / compressed (yellow) / dropped (gray).** Covers real file lifecycle in context. Pinned is a modifier (pin icon overlays any state), not a fourth state.
- **D-15:** **Sort by token count descending.** Biggest context consumers at top. Hot items first — natural for a "heatmap."
- **D-16:** **Row = filename (left-truncated) + token count + mini proportional bar.** Hover tooltip shows full relative path + compression ratio. Fits 240px panel width.
- **D-17:** **System prompt + conversation as special rows at top.** Different icon/style from file rows. Full picture of what's eating context — files aren't the only consumers.

### Pinning & Reverse Channel
- **D-18:** **Ship with pinning.** Full interactive feature — heatmap display + manual pin/unpin. Pinning is the core differentiator.
- **D-19:** **PTY stdin injection for pin commands.** ADE writes `ESC]1337;voss-pin={json}BEL` into PTY stdin via existing `pty_write` Tauri command. Harness stdin parser strips before echo. No new IPC channel.
- **D-20:** **Pin takes effect next iteration.** Pin command queued. Applied when composing next LLM request. No mid-turn context mutation.
- **D-21:** **Pinned = immune to compression.** Full fidelity always. Compressor skips pinned files. User accepts the token cost.
- **D-22:** **Pin only existing context files.** Can't pin arbitrary paths. "Protect what's there" not "add new things." Adding files to context is the agent's job.

### Emission & Payload
- **D-23:** **New `voss-context=` OSC type.** `ESC]1337;voss-context={json}BEL`. Separate from `voss-budget=`. New `PtyEvent::ContextUpdate(ContextData)` variant in Rust. Same parser infrastructure, different event.
- **D-24:** **Emit per-iteration, after budget emission.** Same cadence as F3. At `end_iteration()` in `recorder.py`. Context state changes per-iteration.
- **D-25:** **Payload per file = `{path, tokens, state, pinned}`.** Top-level: `{system_tokens, conversation_tokens, total_tokens, token_limit, files: [{path, tokens, state, pinned}, ...]}`. Minimal and complete for 3-state + pin model.
- **D-26:** **Full snapshot each emission.** Idempotent, same pattern as F3 D-03. ~4KB at 50 files × ~80 bytes/entry. No diffing complexity.
- **D-27:** **Pin ack via next context emission.** No special ack message. `pinned:true` appears in next snapshot. Self-healing via full snapshot pattern.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### PTY Backend (OSC parsing + Channel events)
- `crates/voss-app-core/src/pty/reader.rs` — PTY reader loop, `Channel<PtyEvent>`. F4 adds `voss-context=` OSC parsing + `ContextUpdate` event variant (same pattern as F3 `voss-budget=`).
- `crates/voss-app-core/src/pty/commands.rs` — `PtyEvent` enum + `BudgetData` struct. F4 adds `ContextUpdate(ContextData)` variant + `ContextData`/`FileContextEntry` structs.
- `crates/voss-app-core/src/pty/mod.rs` — PtySession, PtyRegistry. Context for reader architecture.

### F3 Budget Visualization (pattern source)
- `.planning/phases/F3-budget-token-visualization/F3-CONTEXT.md` — D-01..D-14. F4 extends the same OSC 1337 namespace and per-pane signal pattern. F3 specifics already reserved `voss-context=`.

### Pane & Grid (integration points)
- `apps/voss-app/src/pane/PaneComponent.tsx` — PTY event handler. F4 adds `ContextUpdate` event routing to local signal.
- `apps/voss-app/src/grid/PaneHeader.tsx` — A3-05 22px Variant B header. Panel is adjacent to grid, not inside it.
- `apps/voss-app/src/grid/BudgetBar.tsx` — F3 budget display. Pattern reference for streaming data → Solid signal → reactive render.
- `apps/voss-app/src/grid/BudgetPopover.tsx` — F3 popover detail. Pattern reference for Popover usage.

### Harness Context Tracking (emission source)
- `voss/harness/recorder.py` — `end_iteration()` with cost/budget. F4 adds `_emit_context_osc()` call alongside F3's `_emit_budget_osc()`.
- `voss/harness/agent.py` — Agent loop, context composition, `_run_turn_exec()`. Source of file-in-context state.
- `voss_runtime/context.py` — `ContextScope` with per-slot token counts and compression state. Source of compression metadata.
- `voss/harness/session.py` — `IterationRecord`, `RunRecord.inspected[]`/`changed[]`. File tracking data source.

### Variant B Token System
- `apps/voss-app/src/styles/variant-b.css` — Semantic tokens (`--accent`, `--warning`, `--text-2`, `--text-3`, `--bg-2`). Panel uses these. D-14 state colors map to existing tokens.

### Settings Persistence (panel state)
- `.planning/phases/A9-voss-app-settings-theme/A9-CONTEXT.md` — D-01..D-16. Panel open/closed state persists in settings.json (D-06).

### Status Bar (toggle button host)
- `.planning/phases/A10-voss-app-status-bar/A10-CONTEXT.md` — D-01..D-11. Status bar right cluster hosts panel toggle button (D-09).

### F1 Agent Identity (agent pane detection)
- `.planning/phases/F1-durable-session-persistence/F1-CONTEXT.md` — D-06 `agentConfig` prop on PaneComponent. F4 uses this to distinguish agent panes from shell panes (D-08 empty state).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PtyEvent` enum in `commands.rs` — add `ContextUpdate(ContextData)` variant alongside existing `Data`/`Exit`/`BudgetUpdate`
- F3 OSC 1337 parser in `reader.rs` — extend to handle `voss-context=` prefix using same extraction pattern
- `pty_write` Tauri command — existing stdin write path for PTY. Reuse for pin command injection (D-19)
- `Channel<PtyEvent>` — established streaming IPC from Rust reader to frontend. Context events flow through same channel
- `BudgetBar`/`BudgetPopover` — pattern reference for streaming data → Solid signal → component render
- `ContextScope` in `voss_runtime/context.py` — per-slot token counts and compression state, source for context emission payload

### Established Patterns
- **Per-pane PTY Channel:** Each pane has independent `Channel<PtyEvent>`. Context events are per-pane by default — no routing needed.
- **OSC 1337 namespace:** `voss-budget=` (F3), `voss-context=` (F4), extensible to `voss-confidence=`, `voss-status=`.
- **Full snapshot emission:** F3 D-03 idempotent cumulative pattern. F4 reuses for context state (D-26).
- **CSS transitions:** A8 D-11 convention: 150ms/200ms with `prefers-reduced-motion` kill switch.
- **Semantic color tokens:** `--accent`/`--warning`/`--error`/`--text-3`/`--bg-2` already in Variant B for state signaling.

### Integration Points
- **Rust reader.rs:** Parse `ESC]1337;voss-context=...BEL` from PTY byte stream, emit `PtyEvent::ContextUpdate`. Strip OSC from display bytes.
- **Rust reader.rs (reverse):** Parse `ESC]1337;voss-pin=...BEL` from PTY stdin write, pass through to harness process stdin.
- **PaneComponent PTY event handler:** Route `ContextUpdate` events to local `context` Solid signal.
- **App.tsx or new ContextPanel.tsx:** New overlay component, sibling to grid container. Reads focused pane's context signal.
- **Harness recorder.py:** Add `_emit_context_osc()` at `end_iteration()`, after `_emit_budget_osc()`.
- **Harness agent.py stdin:** Add OSC pin command parser. Queue pin requests for next iteration context composition.
- **Status bar (A10):** Add toggle button to right cluster for ⌘I panel toggle.
- **Settings (A9):** Add `contextPanel.open` boolean to settings schema.

</code_context>

<specifics>
## Specific Ideas

- OSC 1337 namespace allows future extension: `voss-confidence=`, `voss-status=` — same parser, different event variants.
- Panel summary bar reuses F3 3-tier color thresholds (D-08: 0-70% accent, 70-90% warning, 90-100% error) for the total context usage bar.
- File state colors: full = `--accent` (green), compressed = `--warning` (yellow), dropped = `--text-3` (gray/muted). Consistent with F3 budget severity progression.
- Pin icon: small 📌 or `⊕` glyph overlaid on file row, toggleable on click. Pinned files get subtle background tint.
- Left-truncated filenames: `...src/auth/middleware.rs` — show filename + enough parent dirs to disambiguate. Same truncation as PaneHeader cwd.
- Mini proportional bar per file: 40-60px wide, fill = file tokens / total tokens. Same bar component pattern as F3 BudgetBar but inline.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: F4-visual-context-heatmap*
*Context gathered: 2026-05-22*
