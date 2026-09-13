# Phase A3: voss-app Grid Engine — Specification

**Created:** 2026-05-18
**Ambiguity score:** 0.15 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

Replace the single static A2 pane with a binary-split pane tree (1..N panes, up to 9 numerically navigable) supporting split/fork/close, numeric + directional + click + cycle focus, drag + keyboard resize with a 20×5 floor, the Variant B per-pane header, and a Solid→Rust-core in-memory mirror — with **zero disk persistence** in this phase.

## Background

`apps/voss-app/` currently contains documentation only (`CONCEPT.md`, `FEATURES.md`); no source code exists. A1 (Tauri shell) is fully planned (4 plans + context/research/patterns/validation/UI-spec) but not executed. A2 (PTY pane) is context-gathered but not planned or executed; by explicit design (A2-CONTEXT line 71) A2 produces ONE self-contained pane that owns its PTY, xterm instance, scrollback, and header with **zero grid awareness** — built to be tiled by A3. The frozen `crates/` Rust spike is reference-only; `crates/voss-app-core/` is the new crate created under A1.

No pane-tree model, split/focus/resize/close logic, or Solid↔Rust layout mirror exists today. ROADMAP defines GRD-01..08 as *proposed*; `REQUIREMENTS.md` has zero GRD entries. This SPEC locks them. ROADMAP A3 cross-cutting requires the grid-model decision (binary-tree vs css-grid vs flex) to close here — CONCEPT §6 and FEATURES L1.3.1 already lock "binary-split tree, same model as tmux/i3", so this SPEC records it as a constraint.

## Requirements

1. **Pane tree model**: A binary-split tree holds 1..N independent A2 panes.
   - Current: No tree model. A2 yields one pane filling the window minus titlebar; no grid awareness.
   - Target: Internal nodes are H or V splits with a ratio; leaves are A2 panes (each its own PTY/shell). Solid signal store is source of truth.
   - Acceptance: Programmatic 2×2 tree (3 splits) yields 4 panes each with an independent PTY/shell; a ≥6-pane asymmetric tree constructs and renders without error.

2. **Split / fork / close**: `⌘\` split-H, `⌘⇧\` split-V, `⌘D` fork, `⌘W` close.
   - Current: No split/fork/close — single static pane.
   - Target: `⌘\` inserts a horizontal sibling of the focused pane (new pane right), `⌘⇧\` a vertical sibling (new pane below), `⌘D` forks the focused pane (new sibling inheriting cwd + shell, empty scrollback), `⌘W` closes the focused pane. A split/fork that would force ANY resulting pane below 20×5 is rejected as a no-op. `⌘W` confirms iff the pane has a foreground process other than the bare interactive shell (reuse A2 D-07 detection); idle shell closes with no confirm.
   - Acceptance: `⌘\`/`⌘⇧\` create correctly-oriented siblings; `⌘D` child starts in parent's cwd with parent's shell and empty scrollback; under-floor split leaves the tree unchanged; `⌘W` on a pane running `sleep 100` prompts, on an idle prompt does not.

3. **Focus**: numeric, directional, click, cycle.
   - Current: No focus model — the single pane is implicitly always focused.
   - Target: Exactly one pane focused at all times. `⌘1`..`⌘9` focus the pane at that index (stable left-to-right, top-to-bottom order); `⌘⌥←/→/↑/↓` move focus to the nearest neighbor in that direction; click focuses a pane; `⌘[`/`⌘]` cycle prev/next in index order with wrap. Indices >9 reachable only via cycle/click.
   - Acceptance: In a 2×2 grid `⌘1`-`⌘4` select the expected panes; `⌘⌥`arrow from a corner moves to the correct adjacent pane; clicking an unfocused pane focuses it; `⌘]`/`⌘[` wrap at the ends.

4. **Resize**: drag border, keyboard 5%, equalize.
   - Current: No resize — single pane fills the window.
   - Target: Dragging a split border reallocates space between its two subtrees; `⌘⌥⇧←/→/↑/↓` adjusts the focused pane's bounding split ratio by 5% per press; `⌘=` resets all split ratios so sibling subtrees are equal. Every resize path clamps at the 20×5 floor.
   - Acceptance: Drag changes only the two adjacent panes; keyboard resize moves in 5% steps and stops at the floor; `⌘=` produces visually equal splits at every tree level.

5. **Per-pane minimum size**: 20 cols × 5 rows hard floor.
   - Current: No min-size concept.
   - Target: No pane ever renders below 20 cols × 5 rows. Splits/forks whose result would violate it are rejected; resize clamps at it; OS-window shrink that would violate it stops shrinking affected panes.
   - Acceptance: A split is rejected when it would drop a pane <20×5; keyboard/drag resize cannot push below 20×5; shrinking the OS window renders no pane below 20×5.

6. **Variant B per-pane header**: 22px, `●` · index · cwd basename · shell · process indicator · `⋯` menu.
   - Current: A2 builds a single-pane Variant B header (dot, cwd basename, shell, foreground-process indicator); no pane index, no `⋯` menu.
   - Target: Every pane shows a 22px Variant B header reusing the A2 header component, with an added numeric-index segment and a `⋯` menu exposing at least close + fork.
   - Acceptance: In a ≥4-pane grid every header shows the correct index matching `⌘`-number nav; `⋯` close/fork act on that pane; header height is 22px.

7. **Focus visual treatment**: inset shadow + bg lift, no border ring.
   - Current: A2's single pane has the inset-shadow focus treatment but focus never changes.
   - Target: The single focused pane renders the Variant B inset-shadow + background-lift; all unfocused panes render without it; no border ring is used. Focus change repaints both old and new focused panes.
   - Acceptance: Exactly one pane shows inset-shadow+bg-lift at any time; switching focus (any method) moves the treatment; no border-ring style present.

8. **Solid→Rust mirror (no disk I/O)**: layout state in Solid signals, mirrored to voss-app-core.
   - Current: No layout state; `crates/voss-app-core/` has no grid structs.
   - Target: Pane tree (structure, split orientations + ratios, per-pane cwd/shell, focused-pane id) lives in Solid signals as source of truth and is mirrored into voss-app-core Rust structs (via Tauri commands) on every structural change. A3 writes NO file and reads none back — the Rust mirror is the in-memory substrate A4 (named layouts) and A6 (session restore) build file I/O on.
   - Acceptance: After each split/fork/close/resize/focus change the Rust core returns a structure matching the Solid tree; no file is created under `.voss/` (or elsewhere) by A3 grid operations.

## Boundaries

**In scope:**
- Binary-split pane-tree model — Solid signals as source of truth, mirrored to voss-app-core Rust structs
- Split-H (`⌘\`), Split-V (`⌘⇧\`), Fork (`⌘D` — inherit cwd+shell, fresh scrollback), Close (`⌘W` — confirm-if-running via A2 D-07)
- Focus: `⌘1`-`⌘9` numeric, `⌘⌥`arrow directional, click, `⌘[`/`⌘]` cycle (wrap)
- Resize: drag border, `⌘⌥⇧`arrow 5%, `⌘=` equalize — all clamped to 20×5
- Per-pane minimum size 20 cols × 5 rows (splits rejected, resize clamped, window-shrink stops)
- Per-pane 22px Variant B header — reuse A2 header + add index segment + `⋯` menu
- Inset-shadow + bg-lift focus treatment; single focused pane; no border ring
- N-pane perf bar (~60fps idle/scroll + one-pane-flood does not starve others)
- Correctness designed + tested up to 9 panes (2×2 case AND a ≥6-pane tree)

**Out of scope:**
- Disk persistence of layout (no file write/read) — A6 owns `session.json` restore; A4 owns named-layout save/load
- Layout presets (fanout/pipeline/swarm/watchers, `⌘G`) — A4
- "Save layout as…/Load layout…" + command-palette entries — A4 (palette itself A7)
- Scrollback persistence across restart — A6 (A2 provides only the in-session buffer)
- Status bar (pane count / cost) — A9
- Tauri shell scaffold, titlebar, theme tokens — A1 (assumed present)
- A2 pane internals (PTY/xterm/scrollback/copy-paste/OSC/foreground detection) — A2; A3 consumes the A2 pane as a black-box tile and reuses its foreground detection only for close-confirm
- `⌘`-number shortcuts above 9 — out (cycle/click only above 9; the tree still supports >9 panes)
- L2 agent semantics on panes or presets — post-A10 (clean layer boundary)

## Constraints

- **Grid model is locked to a binary-split tree (tmux/i3 model)** — NOT css-grid, NOT a flat flexbox of N. Closes the ROADMAP A3 cross-cutting "grid model decision"; consistent with CONCEPT §6 and FEATURES L1.3.1.
- Minimum pane size **20 cols × 5 rows** — hard floor for all split/fork/resize/window-shrink paths.
- Pane-count design + test ceiling = **9** (`⌘1`-`⌘9`). Trees may exceed 9 but only indices 1–9 get numeric shortcuts; A3 acceptance tests target the 2×2 case and a ≥6-pane tree.
- **N-pane performance bar:** idle/scrolling panes sustain ~60fps; an output flood (`yes`, multi-MB `cat`) in one pane must not freeze or drop other panes below interactive responsiveness. This extends A2 D-02 (coalesce-per-frame, drop intermediate) and D-03 (60fps) to N concurrent panes. The renderer mechanism (Canvas vs WebGL vs DOM — A2 D-01 deferred this decision to A3) is a discuss-phase/HOW choice bounded by this constraint, not locked here.
- A3 consumes the A2 pane as a self-contained unit; the only A2-touching changes permitted are adding the header index segment and the `⋯` menu hook. Depends on A1 (Tauri shell) and A2 (PTY pane) existing.
- Variant B aesthetic tokens are reused from A1 — no per-phase visual re-exploration (cross-A constraint).
- `crates/` frozen Rust spike is reference-only; the mirror target is the new `crates/voss-app-core/` crate, not the spike.

## Acceptance Criteria

- [ ] 2×2 grid created via 3 splits; each of 4 panes runs an independent shell with its own PTY
- [ ] A ≥6-pane asymmetric binary-split tree constructs, renders, and is navigable
- [ ] `⌘\` creates a horizontal sibling and `⌘⇧\` a vertical sibling of the focused pane
- [ ] `⌘D` forks the focused pane: child inherits cwd + shell and starts with empty scrollback
- [ ] A split/fork that would force any pane below 20 cols × 5 rows is rejected and the tree is unchanged
- [ ] `⌘W` on a pane running a foreground process (e.g. `sleep 100`) prompts to confirm; `⌘W` on an idle shell prompt closes with no confirm (A2 D-07 detection)
- [ ] `⌘1`–`⌘9` focus the pane at that index; click focuses a pane; `⌘[`/`⌘]` cycle with wrap; `⌘⌥`arrow moves focus to the correct directional neighbor
- [ ] Drag a split border resizes only the two adjacent subtrees; `⌘⌥⇧`arrow resizes in 5% steps; `⌘=` equalizes; all clamp at the 20×5 floor
- [ ] Exactly one pane shows the Variant B inset-shadow + bg-lift focus treatment at all times; no border ring; treatment follows focus changes
- [ ] Every pane header is 22px and shows `●` dot · index · cwd basename · shell · foreground-process indicator · `⋯` menu (close + fork act on that pane)
- [ ] After every split/fork/close/resize/focus change the voss-app-core Rust mirror matches the Solid tree
- [ ] A3 grid operations create no file on disk (nothing written under `.voss/`)
- [ ] With a 9-pane grid, idle/scrolling panes stay ~60fps and a `yes` flood in one pane does not freeze or drop other panes below interactive responsiveness

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                        |
|--------------------|-------|------|--------|--------------------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | ROADMAP goal + GRD-01..08 + interview locks                  |
| Boundary Clarity   | 0.82  | 0.70 | ✓      | No disk I/O in A3; fork=A3; presets=A4; restore=A6           |
| Constraint Clarity | 0.86  | 0.65 | ✓      | Binary-tree locked, 20×5 floor, 9-pane ceiling, N-pane perf |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 13 pass/fail criteria                                        |
| **Ambiguity**      | 0.15  | ≤0.20| ✓      |                                                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective              | Question summary                                  | Decision locked                                                                 |
|-------|--------------------------|---------------------------------------------------|---------------------------------------------------------------------------------|
| 1     | Researcher + Boundary Keeper | A3 persistence scope? `⌘D` fork home? Close-confirm definition? | A3 = in-mem Solid tree + Rust mirror, **no disk I/O**; `⌘D` = A3 sibling-split inheriting cwd+shell, fresh scrollback; close-confirm reuses A2 D-07 foreground detection |
| 2     | Researcher + Simplifier  | N-pane perf bar? Min-size numbers? Pane-count target? | All panes ~60fps + one-pane-flood isolation (A2 D-02/D-03 extended); 20 cols × 5 rows floor; design+test up to 9 panes (2×2 AND ≥6-pane tree) |

---

*Phase: A3-voss-app-grid-engine*
*Spec created: 2026-05-18*
*Next step: /gsd:discuss-phase A3 — implementation decisions (renderer choice, Solid↔Rust mirror mechanism, directional-focus geometry, drag transport)*
