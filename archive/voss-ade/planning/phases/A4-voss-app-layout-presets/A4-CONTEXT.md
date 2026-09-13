# Phase A4: voss-app Layout Presets - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

A4 adds **pure-visual layout presets** on top of the A3 binary-split pane-tree engine. Four templates — **fanout** (1 source left, N receivers right column) · **pipeline** (left-to-right equal row) · **swarm** (N×N equal grid, 2×2 default up to 4×4) · **watchers** (main top, 2–3 thin watchers bottom). `⌘G` cycles them. A Variant-B titlebar switcher widget reflects/sets the active preset. Switching a preset **reorders the existing pane tree without ever destroying a pane** (extends A3 D-04). Named layouts save to / load from `.voss/layouts/<name>.json` with a versioned schema; `.voss/layouts/default.json` auto-applies on project open.

**L1 = pure-visual only.** Presets reorder geometry; no behavioral/agent semantics. L2 overlays meaning later — A4 must not couple to it (CONCEPT §10 Q4, LAY-08).

Builds directly on A3's Solid pane-tree (SSOT) + `voss-app-core` Rust mirror. No A2 pane internals touched. Disk I/O for layouts rides the A1 D-09 Rust/Tauri-owns-IO seam.

</domain>

<decisions>
## Implementation Decisions

These are HOW decisions from discussion. Scope (WHAT) is fixed by ROADMAP A4 LAY-01..08 — not re-opened here.

### Preset → pane mapping
- **D-01:** Preset switch fills slots in **A3's stable pane-index order** (left→right, top→bottom — reuse `recomputeIndices()`). Pane **#1 fills the preset's primary slot** (fanout source / watchers main / swarm top-left / pipeline leftmost). Deterministic from tree alone, testable, no focus/spatial state.
- **D-02:** After a remap, **keyboard focus follows the same PTY pane** (content-follows-focus) wherever it landed — not the slot, not the primary. Least disorienting; coheres with "never destroy panes".

### Capacity vs pane count (LAY-05)
- **D-03:** More panes than a preset's natural shape → **grow the preset's flexible region**: fanout/watchers grow receiver/watcher count, pipeline adds columns, swarm grows toward 4×4. Preset silhouette stays recognizable and scales with pane count.
- **D-04:** Hard-cap overflow (swarm past 4×4=16; watchers past its max) → **spill extras by binary-splitting the last region cell** (panes preserved, never destroyed — A3 D-04). Fewer panes than the preset implies → **lay out only the panes that exist** in the first N slots; **no filler/placeholder panes spawned** (respects lazy / never-spawn-unasked model).

### ⌘G cycle + reversibility
- **D-05:** Cycle order is fixed: **fanout → pipeline → swarm → watchers → (wrap) fanout**. From a manually-modified **custom (off-cycle) layout, `⌘G` snaps to fanout** (cycle start). Switcher widget shows a **"custom" state** until `⌘G`/an explicit preset pick is made.
- **D-06:** Preset geometry is **recomputed fresh from pane count on every entry** (stateless — deterministic D-01 rule). Manual size/split tweaks are **transient** and lost when cycling away. **"Save layout" is the only path** to persist a hand-tuned arrangement. No per-preset session geometry cache.

### Save / Load semantics (LAY-06/07)
- **D-07:** A saved `.voss/layouts/<name>.json` captures **tree shape + split ratios + active preset + per-pane cwd + per-pane shell**. It does **NOT** capture scrollback or running processes — that is A6's `session.json` concern. (Matches FEATURES §L1.3.6 "pane tree + cwds + sizes".)
- **D-08:** **"Load layout" remaps the panes already open** onto the saved geometry/preset using the same D-01 index-order rule, and **never kills a running pane** (A3 D-04). Saved cwd/shell are used **only to spawn panes for net-new slots** when the saved layout has more slots than currently-open panes. No kill+respawn, no additive-merge.
- **D-09:** `.voss/layouts/default.json`, **if present, auto-applies on project open** (satisfies ROADMAP A4 success criterion 3). Layout file carries an **integer schema version**; unknown/older version → **best-effort migrate**; migration failure → **ignore the file + log** (never crash, never destroy panes). `.voss/` is lazily created on first layout **write** (CONCEPT §10 Q7).

### Claude's / Planner's Discretion
- Exact tree-construction algorithm mapping each preset shape onto A3's binary-split tree (`SplitNode`/`PaneLeaf`) — planner's call, bounded by D-01..D-04 contracts and A3 D-02's 50/50-split / `⌘=`-global-equalize geometry model.
- Switcher-widget interaction states (hover/active/menu vs. cycle-only), and whether the widget is click-to-pick or display-only — planner/UI, within locked Variant B tokens (no visual re-exploration; A1 D-01/02).
- `⌘G` behavior during an active one-pane flood — inherits A2 D-02/D-03 coalesce contract; correctness (no pane destroyed, geometry settles) is the only hard requirement.
- Layout-name collision policy on "Save layout as…" (overwrite vs. confirm vs. auto-suffix) — planner's call; not a vision decision. Palette command surface itself is A7 (A4 ships the stub/command per LAY-06).
- Versioned-schema concrete shape and migration mechanics — planner/researcher, bounded by D-09 (integer version, best-effort migrate, fail-safe ignore+log).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & cross-A constraints
- `.planning/ROADMAP.md` "### Phase A4: voss-app Layout Presets" (~line 1175) — LAY-01..08, proposed success criteria, cross-cutting constraint (CONCEPT §10 Q4 must hold: L1 visual-only).
- `.planning/ROADMAP.md` "## A-prefixed phases" preamble (~line 1055) — Variant B token-sharing rule, A-track layering, project-wide closed-questions pointer.

### Product concept & cross-layer locked decisions (authority — supersedes assumptions)
- `apps/voss-app/CONCEPT.md` §10 Q4 — **Layout preset semantics = pure visual templates in L1** (L2 overlays behavior; clean layer boundary). Q7 — lazy `.voss/` creation (layout write triggers it).
- `apps/voss-app/FEATURES.md` §L1.3.5 (layout presets — preset shape definitions, `⌘G`, never-kill) + §L1.3.6 (save layout — "pane tree + cwds + sizes" → `.voss/layouts/<name>.json`). §L1.9.2/L1.9.3 — what does NOT persist (delimits A4 vs A6).

### Prior-phase decisions A4 builds on (do not re-litigate)
- `.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md` — D-02 (50/50 split contract, `⌘=` rebalances whole tree), **D-04 (never destroy panes; app never empty)** which A4's LAY-04/05 extends, code_context (A3 in-memory Rust mirror = the serializable shape A4 persists; Solid tree SSOT mirrored to `voss-app-core`).
- `.planning/phases/A3-voss-app-grid-engine/A3-SPEC.md` — locked binary-split-tree model, focus/index semantics, `recomputeIndices()` contract that D-01 reuses.
- `.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md` — D-01/D-02 (Variant B CSS-var token SSOT; titlebar/switcher styling reuses tokens, no re-exploration), **D-09 (Rust/Tauri owns persisted/IO state, exposed to Solid via Tauri command/state — the seam A4 layout file I/O rides)**.

### Reference design (locked aesthetic — do not re-explore)
- `.planning/sketches/001-voss-grid-shell/README.md` + `.planning/sketches/MANIFEST.md` — Variant B "Minimal Tile": titlebar switcher styling, 22px headers, thin borders, no rounding. ⚠ Unpackaged sketch (no findings skill) — non-blocking; `/gsd:sketch --wrap-up` would formalize.

### Source code (A4 substrate)
- `apps/voss-app/src/grid/tree.ts` — A3 pane-tree model: `SplitNode`/`PaneLeaf`/`TreeNode`, `GridStore`, `recomputeIndices()`, `equalizeRatios()`, `collectLeaves()`, `findLeaf()`. A4's preset transforms operate on this; D-01 reuses `recomputeIndices()` ordering.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/voss-app/src/grid/tree.ts` (A3) — binary-split tree model + `recomputeIndices()` / `collectLeaves()` / `equalizeRatios()`. Preset application = a tree-rebuild function over these primitives; index ordering is the D-01 mapping key.
- `crates/voss-app-core` (A1 D-06, A3-populated) — Rust mirror of the pane tree; A4 serializes from/to this shape for `.voss/layouts/<name>.json`. Layout I/O is a new Tauri command on the A1 D-09 seam.
- Variant B CSS-var token system (A1 D-01/02) — titlebar preset switcher consumes existing tokens; no new visual exploration.

### Established Patterns
- **Solid signals = UI SSOT; Rust/Tauri owns persisted/IO state via Tauri command/state** (A1 D-09). A4 layout file read/write rides this exact seam — Solid tree is source of truth, Rust does the disk I/O.
- **Never destroy a running pane; app never empty** (A3 D-04). Every A4 operation (preset switch, overflow spill, load) preserves panes — D-04/D-08 are direct applications.
- **Deterministic, stateless geometry from pane index** (A3 D-02 50/50 + `⌘=` global). A4 extends the same predictability: D-01 index-order mapping, D-06 recompute-fresh.
- **A-track consumes locked Variant B tokens; no per-phase visual re-exploration** (cross-A constraint, A1 D-02).

### Integration Points
- A4 preset transform → operates on A3 Solid pane-tree (`src/grid/`), mirrored into `voss-app-core` per A1 D-09.
- New Tauri command(s): write/read `.voss/layouts/<name>.json` + auto-load `default.json` on project open — `.voss/` lazily created on first write (CONCEPT Q7). Project-open hook integration point is A5's concern; A4 exposes the load entrypoint.
- "Save layout as…/Load layout…" palette entries — palette UI is A7; A4 ships the underlying command + a stub invocation per LAY-06.
- Titlebar switcher widget → A1 titlebar (visual-only slot already reserved in A1 SHL-03).

</code_context>

<specifics>
## Specific Ideas

- Predictability-over-cleverness continues from A3: index-order mapping, stateless recompute, fixed cycle order — all chosen so power users build muscle memory. "Save layout" is the explicit escape hatch for hand-tuned arrangements, not implicit per-preset memory.
- Strong layer-boundary discipline: A4 is purely visual; capturing cwd/shell in saved layouts is the deliberate ceiling — env/scrollback/processes are explicitly A6's `session.json`, not A4, to keep the L1/L2 boundary clean.
- Fail-safe-by-default for layout files: a bad/old/unmigratable `default.json` must never crash the app or destroy panes — degrade to ignore+log.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within A4 scope. Adjacent capabilities are already fenced to their owning phases: scrollback/process restore → A6 (`session.json`); command palette UI → A7; project-open folder picker/recents → A5; status bar → A9; L2 behavioral preset semantics → post-A10.

</deferred>

---

*Phase: A4-voss-app-layout-presets*
*Context gathered: 2026-05-19*
