# Phase A3: voss-app Grid Engine - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

A3 replaces the single self-contained A2 PTY pane with a **binary-split pane-tree engine**: splits (`⌘\`/`⌘⇧\`), fork (`⌘D`), close (`⌘W`), focus (numeric/directional/click/cycle), resize (drag/keyboard/equalize) with a 20×5 floor, the Variant B per-pane header (index + `⋯` menu), inset-shadow focus treatment, and a Solid→`voss-app-core` Rust mirror. **No disk persistence in A3** — the Rust mirror is the in-memory substrate A4 (named layouts) and A6 (session restore) build file I/O on. The A2 pane is consumed as a black-box tile; A3 only adds the header index segment + `⋯` menu hook.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked.** See `A3-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `A3-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Binary-split pane-tree model — Solid signals as source of truth, mirrored to voss-app-core Rust structs
- Split-H (`⌘\`), Split-V (`⌘⇧\`), Fork (`⌘D` — inherit cwd+shell, fresh scrollback), Close (`⌘W` — confirm-if-running via A2 D-07)
- Focus: `⌘1`-`⌘9` numeric, `⌘⌥`arrow directional, click, `⌘[`/`⌘]` cycle (wrap)
- Resize: drag border, `⌘⌥⇧`arrow 5%, `⌘=` equalize — all clamped to 20×5
- Per-pane minimum size 20 cols × 5 rows (splits rejected, resize clamped, window-shrink stops)
- Per-pane 22px Variant B header — reuse A2 header + add index segment + `⋯` menu
- Inset-shadow + bg-lift focus treatment; single focused pane; no border ring
- N-pane perf bar (~60fps idle/scroll + one-pane-flood does not starve others)
- Correctness designed + tested up to 9 panes (2×2 case AND a ≥6-pane tree)

**Out of scope (from SPEC.md):**
- Disk persistence of layout (no file write/read) — A6 owns `session.json` restore; A4 owns named-layout save/load
- Layout presets (fanout/pipeline/swarm/watchers, `⌘G`) — A4
- "Save layout as…/Load layout…" + command-palette entries — A4 (palette itself A7)
- Scrollback persistence across restart — A6 (A2 provides only the in-session buffer)
- Status bar (pane count / cost) — A9
- Tauri shell scaffold, titlebar, theme tokens — A1 (assumed present)
- A2 pane internals (PTY/xterm/scrollback/copy-paste/OSC/foreground detection) — A2; A3 reuses A2's foreground detection only for close-confirm
- `⌘`-number shortcuts above 9 — out (cycle/click only above 9; tree still supports >9 panes)
- L2 agent semantics on panes or presets — post-A10

</spec_lock>

<decisions>
## Implementation Decisions

These are HOW decisions made during discussion. They do not re-open SPEC.md's locked WHAT.

### Renderer (N-pane)
- **D-01:** **Canvas per-pane.** Keep A2 D-01's xterm.js Canvas renderer for every pane — continuity with A2, and it sidesteps the WebGL GPU/VM context-loss bug class (blank/white panes on some machines) that A2 D-01 deliberately chose Canvas to avoid. **Research directive:** gsd-phase-researcher MUST validate the SPEC perf bar (~60fps idle/scroll + one-pane-flood does not starve others) at the 9-pane ceiling with a benchmark, and document a WebGL-addon fallback **only if** Canvas-per-pane fails that bar. WebGL is not adopted preemptively.

### Split & Equalize Geometry
- **D-02:** New `⌘\`/`⌘⇧\` sibling always takes **exactly 50%** of the split-from pane's space. `⌘=` equalize **rebalances the whole tree** — every split node reset to even (tmux `select-layout even-*` / i3 default). Chosen for predictability and the power-user mental model the Variant B sketch targets. `⌘D` fork uses the same 50/50 sibling insertion as `⌘\` (SPEC GRD-02: split direction for fork is planner's call within this 50/50 contract).

### Directional Focus
- **D-03:** `⌘⌥`arrow tie-break = **i3/sway "nearest to focused pane's edge-midpoint"** algorithm: project the focused pane's relevant edge-midpoint onto candidate panes' shared edges; the nearest candidate wins. Deterministic from layout alone (testable), well-known behavior, no focus-history state required.

### Close Behavior
- **D-04:** On `⌘W` close, focus moves to **the sibling subtree that expands to fill** the freed space. Closing the **last remaining pane auto-spawns a fresh default pane** — the app is never empty; a terminal is always present (Warp/tmux-window feel). No quit-on-last-close (avoids accidental-quit on a stray `⌘W`), no empty-state surface in A3.

### Claude's / Planner's Discretion
- Pane index recompute on close/structure change — GRD-03 locks "stable left-to-right, top-to-bottom"; combined with D-04, indices are recomputed by geometric position (no sparse/gap indices). Exact algorithm = planner.
- Drag-resize debounce, PTY `SIGWINCH`/winsize ioctl timing, scrollback reflow on resize — already A2 Claude-discretion; A3 inherits. Correctness (apps see correct cols/rows; 20×5 clamp holds) is the only hard requirement.
- Solid→Rust mirror sync cadence — SPEC GRD-08 requires the mirror match after every structural change; debounce/coalescing **during an active drag** (mirror once on drag-end vs. throttled mid-drag) is planner's call, bounded by "matches after the change settles."
- Tauri command vs. event-stream mechanism for the mirror — ride the A1 D-09 seam (Rust owns state, exposes to webview); exact command shape = planner/researcher.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements (read FIRST)
- `.planning/phases/A3-voss-app-grid-engine/A3-SPEC.md` — **Locked requirements, boundaries, acceptance criteria — MUST read before planning.** 8 reqs GRD-01..08, 13 acceptance criteria, binary-split-tree + 20×5 + 9-pane + N-pane-perf constraints.

### Product concept & cross-layer locked decisions (authority — supersedes assumptions)
- `apps/voss-app/CONCEPT.md` §6 — locked stack (Tauri + Solid + xterm.js + portable-pty; pnpm + Cargo workspace). §8 — monorepo layout contract (`apps/voss-app/src/grid/`, `crates/voss-app-core/`). §10 — closed decisions log (Q4 presets pure-visual L1 → A4 not A3).
- `apps/voss-app/FEATURES.md` §L1.3 — Grid Layout Engine feature catalog (pane model, split ops, navigation, resize) mapped to L1.

### Phase requirements & cross-A constraints
- `.planning/ROADMAP.md` "### Phase A3: voss-app Grid Engine" (~line 1098) — GRD-01..08, proposed success criteria, cross-cutting (grid-model decision closes at SPEC, no presets in A3).
- `.planning/ROADMAP.md` "## A-prefixed phases" preamble (~line 1019) — Variant B token-sharing rule, cross-A constraints, project-wide closed-questions pointer.

### Prior-phase decisions A3 builds on (do not re-litigate)
- `.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md` — D-01/D-02 (CSS-var Variant B token SSOT; focus = inset-shadow ring, 22px header), D-05/D-06 (`crates/voss-app-core` is a workspace member, empty `lib.rs`, src-tauri path-dep wired — **A3 fills the grid model into voss-app-core**), **D-09 (Rust/Tauri owns state + exposes to Solid via Tauri command/state — the GRD-08 mirror seam)**.
- `.planning/phases/A2-voss-app-pty-pane/A2-CONTEXT.md` — D-01 (xterm.js Canvas renderer; "**revisit renderer choice at A3 when N panes render concurrently**" — resolved by A3 D-01), D-02/D-03 (flood coalesce-per-frame, drop intermediate, 60fps — SPEC extends to N panes), D-07 (foreground-command detection: OSC-title primary + PTY pgid fallback — A3 reuses for close-confirm), Integration Points (A2 pane is self-contained, no grid awareness — A3 tiles it as a black box).

### Reference design (locked aesthetic — do not re-explore)
- `.planning/sketches/001-voss-grid-shell/README.md` + `.planning/sketches/MANIFEST.md` — Variant B "Minimal Tile" winner: tmux density, thin 1px borders, no rounding, 22px single-line headers, focused cell = inset-shadow + bg-lift (no border ring), glyph prefixes. ⚠ Unpackaged sketch (no findings skill) — `/gsd:sketch --wrap-up` would formalize; non-blocking.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **A2 PTY pane component** (built in A2, not yet executed) — the tileable unit. Owns its PTY, xterm.js Canvas instance, scrollback, and Variant B header. A3 instantiates N of these and arranges them; only additive changes allowed (header index segment, `⋯` menu hook).
- **A2 foreground-command detection** (A2 D-07) — reused verbatim to decide `⌘W` close-confirm ("running" = foreground process other than the bare interactive shell).
- **`crates/voss-app-core`** (created empty in A1 D-06, workspace member, src-tauri path-dep wired) — A3 populates it with the Rust-side pane-tree mirror structs.
- **Variant B CSS-var token system** (A1 D-01/D-02) — focus treatment, 22px header, borders, glyphs already tokenized; A3 consumes tokens, never redefines them.

### Established Patterns
- **Solid signals = UI source of truth; Rust/Tauri owns persisted/IO state, exposed via Tauri command/state** (A1 D-09). GRD-08 mirror rides this exact seam — Solid tree is SSOT, mirrored into voss-app-core on structural change.
- **A-track consumes locked Variant B tokens; no per-phase visual re-exploration** (cross-A constraint, A1 D-02).
- **Frozen `crates/` spike is reference-only** — `voss-app-core` is the new crate; do not edit spike crates.
- **PTY flood contract** (A2 D-02/D-03): coalesce per animation frame, drop intermediate frames, never block the UI — SPEC A3 extends this to N concurrent panes (flood in one pane must not starve others).

### Integration Points
- A2 pane component → tiled as leaves of the A3 binary-split tree (`apps/voss-app/src/grid/`).
- Solid grid signals → `voss-app-core` Rust structs via Tauri command/state (A1 D-09 seam) — GRD-08, no disk I/O in A3.
- A3 in-memory Rust mirror → consumed later by A4 (named-layout save/load file I/O) and A6 (session.json restore) — A3 must expose a clean serializable shape without persisting it.
- Header index segment + `⋯` menu → additive edits to the A2 pane header (only A2-touching change permitted).

</code_context>

<specifics>
## Specific Ideas

- Renderer risk preference is explicit: the user values A2's deliberate avoidance of the WebGL context-loss bug class over preemptive perf headroom. WebGL is a documented fallback gated on a failed 9-pane benchmark, not a default.
- "App is never empty" is a deliberate product stance (D-04) — closing the last pane respawns a fresh one rather than quitting or showing an empty state. Stray-`⌘W`-safety + always-a-terminal feel.
- Predictability over cleverness across the board: 50/50 splits, global `⌘=`, deterministic i3 directional focus — all chosen because the Variant B sketch targets power users who build muscle memory.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within A3 scope. Adjacent capabilities are already SPEC-fenced to their owning phases (presets/save-load → A4, session restore → A6, status bar → A9, command palette → A7).

</deferred>

---

*Phase: A3-voss-app-grid-engine*
*Context gathered: 2026-05-18*
