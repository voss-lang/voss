# Phase A6: voss-app Session Persist - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

A6 persists and restores the full pane session across app restart: pane tree geometry, per-pane cwd + shell choice, focused pane, active layout preset, and truncated scrollback (last 2k lines per pane) to `.voss/session.json` (project mode) or `~/.config/voss-app/global-session.json` (project-less mode). Live processes are NOT auto-relaunched in L1 — users re-run commands manually after restore.

A6 builds on A3's binary-split tree (in-memory Solid SSOT + Rust mirror), A4's layout persistence seam (tree+ratios+preset+cwd+shell already serializable via `LayoutFile`/`GridState`), and A5's project-open lifecycle. A6 extends the data A4 saves (geometry) with the data A4 explicitly deferred: scrollback content and session-level state (focused pane, project-less flag).

**Out of scope (fenced to other phases):**
- Layout presets, save/load named layouts — A4 (done)
- Project open/close, setup window, recents — A5
- Command palette — A7
- Workspace tabs, multi-project — A8
- Settings UI, status bar — A9/A10
- L2 process restart, agent pane semantics — post-A10
- SQLite session storage — L2 (PER-05 locks JSON for L1)

</domain>

<decisions>
## Implementation Decisions

Scope (WHAT) is fixed by ROADMAP PER-01..PER-06. These are HOW decisions from discussion.

### Scrollback extraction
- **D-01:** Scrollback extracted **on quit only** — during the Tauri `close-requested` handler, not periodically. No ongoing CPU cost for scrollback snapshots. Crash = scrollback lost (tree/cwd still crash-safe via D-05).
- **D-02:** Scrollback stored as **plain text only** — ANSI escape sequences stripped. Restored panes show monochrome history. Smaller file, simpler parsing, no encoding edge cases.
- **D-03:** Always read from **`buffer.normal`** (not `buffer.alternate`). If an alternate-screen app (vim/htop) was running at quit, saved scrollback = the pre-vim shell history. Restored pane shows useful shell context, not a frozen TUI frame.

### Save trigger & crash safety
- **D-04:** Two-tier save strategy: (a) **tree-only auto-save** triggered by structural changes (split/close/fork/preset-switch/focus-change), debounced ~2s, reusing the A3 `sync.ts` `markStructuralChange` signal — saves tree+cwds+shells+focused+preset without touching xterm buffers; (b) **full save with scrollback** on quit only (D-01). Crash loses scrollback but preserves layout.
- **D-05:** Quit save **blocks the close** — Tauri's `close-requested` event is cancellable. Handler extracts scrollback from all panes, writes `session.json` with portalocker flock (PER-06), then allows the window to close. Brief delay acceptable since user already initiated quit.
- **D-06:** Structural-change auto-save writes the same `session.json` file (tree-only fields populated, scrollback fields empty/null). Portalocker flock on every write (PER-06). No separate "tree-only" file — single `session.json` with optional scrollback arrays.

### Restore banner UX
- **D-07:** New **`RestoreBanner`** component — separate from `ExitBanner`/`CloseConfirmBanner`. Same pane chrome mount point (above terminal content, below PaneHeader). Variant B tokens. Different purpose = different component.
- **D-08:** Banner copy: **"Session restored — N lines"** where N is the actual line count restored (may be < 2,000 if pane had less scrollback). Single line, 22px height matching pane header, Variant B dim fg.
- **D-09:** **Auto-dismiss on first keystroke** — banner disappears as soon as the user types anything in the restored pane. Zero friction. No explicit dismiss button needed.

### Session vs layout restore priority
- **D-10:** **Session wins over layout.** Restore priority chain: `session.json` → `default.json` (A4) → single fresh pane. `session.json` = last actual state; `default.json` only applies on first project open (no session exists yet) or after explicit session reset. Matches "reopen = back where I was" expectation.
- **D-11:** Corrupt/version-unsupported `session.json` → **fall through to `default.json`** (A4 D-09 fail-safe pattern), then fresh pane if that also fails. Log warning to stderr. Never crash, never show error dialog for stale session data. Matches A4 D-09 and A5 D-10 precedent.
- **D-12:** **`projectLessAccepted` persisted in `global-session.json`**. If user was in project-less mode at quit, relaunch restores the project-less session directly (no setup window). Setup window only shows on true first launch (no `global-session.json` exists). Resolves A5 D-04's explicit deferral to A6.

### Claude's / Planner's Discretion
- Exact `session.json` schema shape (field names, nesting) — bounded by: wraps `GridState` like `LayoutFile` does, adds `scrollback: string[] | null` per pane leaf, adds `focusedId`, adds `projectLessAccepted` for global variant. Integer `version` field (PER-04).
- xterm.js buffer extraction implementation (loop over `buffer.normal.getLine()` vs. `serialize` addon) — planner's call; D-02 (plain text) and D-03 (normal buffer) are the contracts.
- Auto-save debounce exact timing (~2s target, planner may adjust).
- RestoreBanner visual layout within the 22px constraint — planner/UI, within Variant B tokens.
- Whether the structural-change auto-save fires on focus-change or only on tree-shape changes — planner's call within D-04 contract ("focus is part of session state worth crash-saving").
- Forward-migration strategy for `session.json` version bumps — bounded by D-11 (fail-safe, never crash), same approach as A4 D-09 integer version + best-effort migrate.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & cross-A constraints
- `.planning/ROADMAP.md` Phase A6 (~line 1251) — PER-01..PER-06, proposed success criteria, cross-cutting constraints (2k scrollback cap, no process restart in L1).

### Product concept (authority — supersedes assumptions)
- `apps/voss-app/CONCEPT.md` §10 Q7 — `.voss/` lazy creation (session write triggers it, just like A4 layout write).
- `apps/voss-app/FEATURES.md` §L1.9.2/L1.9.3 — session persist / restore feature catalog; what persists vs what doesn't.

### Prior-phase decisions A6 builds on (do not re-litigate)
- `.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md` — D-09 (Rust/Tauri owns persisted IO; `~/.config/voss-app/` config path lock for global files).
- `.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md` — D-04 (never destroy panes; app never empty). A3 `sync.ts` `markStructuralChange` signal is the D-04 auto-save trigger.
- `.planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md` — D-07 (layout files save tree+ratios+preset+cwd+shell, NOT scrollback — A6's job), D-09 (versioned schema, fail-safe, lazy `.voss/`).
- `.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md` — D-04 (`projectLessAccepted` session-only, "persisting it is A6's concern" — resolved by D-12), D-09 (recents at `~/.config/voss-app/recents.json`), D-11 (`default_cwd()` Tauri command returns project path or home).

### Source code (A6 substrate)
- `crates/voss-app-core/src/layouts.rs` — `LayoutFile` / `GridState` serialization pattern, `save_layout`/`load_layout`/`load_default_layout` with portalocker-style atomic write + fail-safe load. A6 session persistence follows the same Rust IO pattern.
- `crates/voss-app-core/src/grid.rs` — `GridState` (Rust mirror of the Solid pane tree). A6 session wraps this with scrollback arrays.
- `apps/voss-app/src/grid/sync.ts` — `markStructuralChange` signal. D-04 auto-save hooks into this.
- `apps/voss-app/src/pane/PaneComponent.tsx` — xterm.js `Terminal` instance with `scrollback: 10_000`, `buffer.active.getLine()` usage at line 89. D-01/D-03 extraction reads from `buffer.normal`.
- `apps/voss-app/src/App.tsx` — composition root with `project` signal + `activeLayout` signal + GridRoot. A6 adds session restore logic to the app init path.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `crates/voss-app-core/src/layouts.rs` — `LayoutFile` serialization + `save_layout` atomic write pattern (write-to-tmp, rename). A6 `save_session`/`load_session` follows the same pattern, wrapping `GridState` with scrollback + focus + version.
- `apps/voss-app/src/grid/sync.ts` — `markStructuralChange` / `markDragSettled` signals. D-04 auto-save hooks after `markStructuralChange`.
- `apps/voss-app/src/pane/PaneComponent.tsx:89` — existing `buffer.active.getLine(y - 1)` usage for link detection. Same API reads scrollback for D-01 extraction (but from `buffer.normal`).
- `apps/voss-app/src/pane/ExitBanner.tsx` / `CloseConfirmBanner.tsx` — pane chrome banner precedent. RestoreBanner follows the same mount pattern and 22px height.

### Established Patterns
- **Solid signals = UI SSOT; Rust/Tauri owns persisted IO** (A1 D-09). Session file read/write is Rust-side; frontend sends extracted scrollback via Tauri command.
- **Never destroy panes; app never empty** (A3 D-04). Session restore creates panes from saved state; corrupt session falls through to A4 default layout or fresh pane (D-11).
- **Atomic write + fail-safe load** (A4 layouts.rs). Write to `.tmp`, rename, portalocker flock. Load failures return `Ok(None)` or fall through.
- **`.voss/` lazy on first write** (A4 D-09 / CONCEPT Q7). `save_session` creates `.voss/` if needed.
- **Cross-crate `#[tauri::command]` pattern** (A2-05, A4-03). New session commands go in `voss-app-core` (new module `session.rs`); thin app wrappers in `apps/voss-app/src-tauri/src/lib.rs`.

### Integration Points
- New Rust module `crates/voss-app-core/src/session.rs` — `SessionFile`, `save_session`, `load_session`, portalocker flock.
- New frontend module `apps/voss-app/src/grid/sessionPersist.ts` (or `sessionStorage.ts`) — scrollback extraction from xterm.js instances, Tauri command wrappers, structural-change auto-save listener.
- `apps/voss-app/src/App.tsx` — session restore on init (before GridRoot mounts), quit handler registration.
- New component `apps/voss-app/src/pane/RestoreBanner.tsx` — Variant B, 22px, auto-dismiss on keystroke.
- `apps/voss-app/src/grid/SplitNode.tsx` — conditional RestoreBanner render in leaf mount (same pattern as ExitBanner/CloseConfirmBanner in A3-05).

</code_context>

<specifics>
## Specific Ideas

- **Two-tier save = best crash tradeoff.** Tree structure is cheap to save and most valuable to restore (layout, focus, cwds). Scrollback is expensive to extract and less critical. Separating their save triggers means crashes preserve layout at zero ongoing cost while scrollback gets the thorough on-quit extraction.
- **Plain text scrollback is a deliberate simplification.** ANSI-preserved scrollback would faithfully reproduce colors but introduces encoding complexity, larger files, and potential xterm.js serialization quirks. Plain text matches the "2k lines" cap literally and keeps the session file human-readable.
- **`buffer.normal` always = no frozen TUI frames.** A user quitting during a vim session gets their shell history back on restore, not a meaningless vim screenshot. This is the only sane UX — the alternate-screen process isn't running anyway.
- **Session > layout > fresh = predictable chain.** User always gets "back where I was" unless something is corrupt, then falls through gracefully. Explicit "Reset layout" (future A7 palette command) is the escape hatch.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within A6 scope. Adjacent capabilities are fenced to their owning phases:
- Command palette "Reset layout" / "Clear session" commands → A7
- Multi-workspace session persistence → A8 (UXP-06)
- L2 process restart on restore → post-A10
- SQLite session storage → L2 (PER-05 locks JSON for L1)

</deferred>

---

*Phase: A6-voss-app-session-persist*
*Context gathered: 2026-05-20*
