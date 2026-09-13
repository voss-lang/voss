---
phase: A3-voss-app-grid-engine
plan: 03
type: execute
wave: 2
depends_on: [A3-01]
files_modified:
  - apps/voss-app/src/grid/focus.ts
  - apps/voss-app/src/grid/resize.ts
  - apps/voss-app/src/grid/__tests__/focus.test.ts
  - apps/voss-app/src/grid/__tests__/resize.test.ts
autonomous: true
requirements: [GRD-03, GRD-04, GRD-05]
must_haves:
  truths:
    - "⌘1–⌘9 focus the pane at that geometric index; indices >9 are reachable only via cycle/click"
    - "⌘⌥arrow moves focus to the nearest neighbor via the i3 edge-midpoint algorithm (deterministic from layout alone)"
    - "click focuses a pane; ⌘[ / ⌘] cycle prev/next in index order with wrap at both ends"
    - "⌘⌥⇧arrow adjusts the focused pane's bounding split ratio by 5%, clamped at the 20×5 floor"
    - "drag-resize reallocates space between the two adjacent subtrees only, clamped at the 20×5 floor; ⌘= equalizes"
  artifacts:
    - path: "apps/voss-app/src/grid/focus.ts"
      provides: "focusByIndex / focusByDirection (i3) / focusByClick / cycleFocus"
      contains: "focusByDirection"
    - path: "apps/voss-app/src/grid/resize.ts"
      provides: "resizeByDrag / resizeByKeyboard with 20×5 clamp"
      contains: "resizeByDrag"
    - path: "apps/voss-app/src/grid/__tests__/focus.test.ts"
      provides: "Vitest coverage of numeric/directional/click/cycle focus"
      contains: "focusByDirection"
    - path: "apps/voss-app/src/grid/__tests__/resize.test.ts"
      provides: "Vitest coverage of drag/keyboard resize + floor clamp"
      contains: "resizeByDrag"
  key_links:
    # resize.ts deliberately does NOT import geometry.ts (A3-02 owns that file in
    # the same wave); it reimplements the 20×5 clamp via a local rectsOf walker for
    # file-ownership isolation. Its only cross-file link is the sync cadence below.
    - from: "apps/voss-app/src/grid/resize.ts"
      to: "apps/voss-app/src/grid/sync.ts"
      via: "markStructuralChange per keyboard step; markDragSettled on drag-end"
      pattern: "markStructuralChange|markDragSettled"
    - from: "apps/voss-app/src/grid/focus.ts"
      to: "apps/voss-app/src/grid/sync.ts"
      via: "markStructuralChange on focus change"
      pattern: "markStructuralChange"
---

<objective>
Implement focus selection (numeric, directional i3, click, cycle) and resize (drag border,
keyboard 5%, equalize) over the A3-01 tree, all clamped to the 20×5 floor.

Purpose: Focus and resize are independent pure logic over the same tree model as
operations — separate file ownership lets this run in parallel with A3-02 in Wave 2.

Output: `focus.ts`, `resize.ts`, and Vitest suites. Implements GRD-03 (focus:
numeric/directional/click/cycle), GRD-04 (resize: drag/keyboard/equalize), and the
resize half of GRD-05 (resize clamps at 20×5).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

<interfaces>
<!-- From A3-01 (depends_on: A3-01). geometry.ts is authored by A3-02 (Wave 2 sibling): -->
<!-- to avoid a cross-plan file-ownership conflict, this plan does NOT edit geometry.ts. -->
<!-- It re-derives the minimal rect math it needs locally, OR (preferred) imports the -->
<!-- pure helpers IF present at execute time. The resize floor clamp is self-contained -->
<!-- here using window dims + cell size — see Task 2 action. -->
From apps/voss-app/src/grid/tree.ts:
  types SplitNode/PaneLeaf/TreeNode/GridStore; collectLeaves(root) (inorder);
  findLeaf(root,id); recomputeIndices(root)
From apps/voss-app/src/grid/sync.ts:
  markStructuralChange(state); markDragSettled(state)  // drag = one sync on pointer-up
</interfaces>

@.planning/phases/A3-voss-app-grid-engine/A3-SPEC.md
@.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md
@.planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md
@.planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Focus — numeric, i3 directional, click, cycle (focus.ts)</name>
  <files>apps/voss-app/src/grid/focus.ts, apps/voss-app/src/grid/__tests__/focus.test.ts</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### apps/voss-app/src/grid/focus.ts" — the four focus operations + i3 edge-midpoint algorithm steps (governing contract; greenfield)
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-03 (numeric ⌘1-9, directional ⌘⌥arrow, click, ⌘[/⌘] cycle wrap; indices >9 cycle/click only) + acceptance
    - .planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md D-03 (i3/sway nearest-to-focused-edge-midpoint tie-break; deterministic from layout, no focus history)
    - apps/voss-app/src/grid/tree.ts (A3-01) — collectLeaves inorder = the index order
  </read_first>
  <behavior>
    - focusByIndex(store, 3) sets focusedId to the leaf whose index === 3; focusByIndex(store, 99) on a 4-pane tree is a no-op (GRD-03: indices >9 / >count not numeric-addressable).
    - focusByClick(store, id) sets focusedId to that id directly.
    - cycleFocus(store, "next") from the highest-index pane wraps to index 1; cycleFocus(store, "prev") from index 1 wraps to the highest index.
    - In a 2×2 grid, focusByDirection from the top-left pane with dir "right" focuses the top-right pane; "down" focuses bottom-left; from a corner the result matches the i3 edge-midpoint nearest-candidate rule.
    - focusByDirection with no candidate in that direction (e.g. "left" from the leftmost pane) is a no-op.
    - Every focus change fires markStructuralChange (GRD-08 — mirror tracks focusedId).
  </behavior>
  <action>
    Create `apps/voss-app/src/grid/focus.ts`. Export `focusByIndex(store: GridStore, n:
    number)` — set `focusedId` to the leaf with `index === n` via `collectLeaves`; no-op
    if none (GRD-03: `⌘`-numbers only 1–9, and only if a pane has that index — indices
    >count never match). Export `focusByClick(store, paneId: string)` — direct set.
    Export `cycleFocus(store, dir: "next" | "prev")` — order leaves by `index`
    (`collectLeaves` is already inorder), move ±1 with modulo wrap at both ends (GRD-03
    wrap). Export `focusByDirection(store, dir: "left"|"right"|"up"|"down", winW:
    number, winH: number)` implementing the i3/sway edge-midpoint algorithm (D-03,
    A3-PATTERNS steps): (1) compute every leaf's rect by walking SplitNodes with ratios
    over `winW`×`winH` (local helper `rectsOf(root,winW,winH)` — pure, self-contained, do
    NOT import or edit A3-02's `geometry.ts` to keep file ownership clean); (2) take the
    focused rect's edge midpoint for the requested direction (e.g. right-edge midpoint for
    "right"); (3) keep candidate leaves strictly on that side that share an overlapping
    perpendicular span; (4) winner = candidate whose nearest edge point is closest to the
    projected midpoint; no-op if no candidate. After ANY successful focus change call
    `markStructuralChange(store)`. Pure logic — no JSX, no DOM events here (the click
    handler lives in the render layer A3-04 and calls `focusByClick`). Author
    `apps/voss-app/src/grid/__tests__/focus.test.ts` with a 2×2 fixture and a ≥6-pane
    asymmetric fixture covering every behavior case (mirrors A3-SPEC acceptance criterion
    for `⌘1-9`, `⌘⌥`arrow corners, click, `⌘[`/`⌘]` wrap).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run focus --reporter=dot 2>&1 | tail -12 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'focusByIndex' src/grid/focus.ts && grep -q 'focusByDirection' src/grid/focus.ts && grep -q 'cycleFocus' src/grid/focus.ts && grep -q 'markStructuralChange' src/grid/focus.ts && echo FOCUS_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src/grid/focus.ts` exports `focusByIndex`, `focusByClick`, `cycleFocus`, `focusByDirection` (source assertion).
    - `pnpm vitest run focus` exits 0 with all behavior cases green.
    - Behavior: in a 2×2 grid `focusByIndex` 1–4 selects expected panes; `focusByDirection` from a corner picks the i3 edge-midpoint-nearest neighbor; `cycleFocus` wraps at both ends; `focusByIndex(store, 99)` is a no-op (GRD-03).
    - `focus.ts` calls `markStructuralChange` on focus change and does not import or modify `geometry.ts` (file-ownership + key-link assertion).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>Numeric, i3-directional, click, and cycling focus exist as pure tree logic, unit-tested green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Resize — drag border + keyboard 5% with 20×5 clamp (resize.ts)</name>
  <files>apps/voss-app/src/grid/resize.ts, apps/voss-app/src/grid/__tests__/resize.test.ts</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### apps/voss-app/src/grid/resize.ts" + "### 20×5 Floor Guard" — resize ops + clamp + mirror cadence (governing contract; greenfield)
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-04 (drag reallocates the two subtrees only; ⌘⌥⇧arrow 5%; ⌘= equalize; all clamp at 20×5) + GRD-05
    - .planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md "## Split Border + Drag Handle Contract" — drag reallocates the two sibling subtrees of that split node only; clamp stops silently (no toast)
    - .planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md "Claude's / Planner's Discretion" — drag-resize sync cadence (once on drag-end via markDragSettled)
    - apps/voss-app/src/grid/tree.ts (A3-01); apps/voss-app/src/grid/sync.ts (A3-01)
  </read_first>
  <behavior>
    - resizeByDrag(store, splitId, newRatio, winW, winH, cw, ch) sets that SplitNode.ratio toward newRatio but clamps so neither child subtree drops any pane below 20 cols × 5 rows; the clamped result never violates the floor.
    - resizeByDrag mutates ONLY the target split node's ratio — sibling subtrees at other split nodes are byte-identical before/after (drag affects only the two adjacent subtrees, GRD-04).
    - resizeByKeyboard(store, "right", winW, winH, cw, ch) finds the split node bounding the focused pane in that axis and adjusts its ratio by +0.05 (5%), clamped at the floor; repeated calls stop at the floor and do not overshoot.
    - resizeByKeyboard is a no-op if no split node exists in that direction from the focused pane (single pane → nothing to resize).
    - Keyboard resize fires markStructuralChange after each 5% step; drag resize fires markDragSettled exactly once on drag-end (NOT per drag-move) — verified via mocked sync.
  </behavior>
  <action>
    Create `apps/voss-app/src/grid/resize.ts`. Export `resizeByDrag(store: GridStore,
    splitNodeId: string, requestedRatio: number, winW: number, winH: number, cw: number,
    ch: number)` — clamp `requestedRatio` to the range where BOTH child subtrees keep
    every pane ≥ 20 cols × 5 rows (GRD-05, A3-PATTERNS clamp): use a local pure
    `rectsOf(root,winW,winH)` walker + `cols=floor(w/cw)`, `rows=floor((h-22)/ch)` (22px
    header per A3-UI-SPEC; self-contained — do NOT import/edit A3-02's `geometry.ts`,
    file-ownership). If the requested ratio would breach the floor, snap to the nearest
    in-bounds ratio and stop (cursor stays, no toast — A3-UI-SPEC "drag stops at the floor
    boundary, movement rejected silently"). `resizeByDrag` is called continuously during a
    drag; it must NOT call sync per move — the drag-end caller (A3-04 DragHandle) calls
    `markDragSettled(store)` once on pointer-up. Export `resizeByKeyboard(store, dir:
    "left"|"right"|"up"|"down", winW, winH, cw, ch)` — walk from the focused leaf up to
    the nearest ancestor SplitNode whose orientation matches the axis of `dir`
    (left/right→`H`, up/down→`V`); adjust its `ratio` by ±0.05 in the direction of `dir`
    (clamp at floor); no-op if no such ancestor; call `markStructuralChange(store)` after a
    successful step (A3-CONTEXT cadence: keyboard = per-step). Export a thin
    `equalizeAllRatios(store)` that delegates to `equalizeRatios` (re-exported for the
    `⌘=` keybinding wiring in A3-04) + `markStructuralChange` — note `operations.ts`
    (A3-02) also exposes `equalizeAll`; this re-export exists only so the resize keymap
    group is cohesive; A3-04 picks ONE (prefer `operations.equalizeAll`) and the executor
    must not double-bind. Pure logic — no DOM/pointer events here (DragHandle in A3-04
    owns pointer capture and feeds `requestedRatio`). Author
    `apps/voss-app/src/grid/__tests__/resize.test.ts` covering every behavior case with a
    2×2 and a deep asymmetric fixture (mirrors A3-SPEC acceptance: drag changes only the
    two adjacent panes; keyboard 5% steps stop at the floor).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run resize --reporter=dot 2>&1 | tail -12 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'resizeByDrag' src/grid/resize.ts && grep -q 'resizeByKeyboard' src/grid/resize.ts && grep -Eq '0\.05' src/grid/resize.ts && grep -q 'markDragSettled' src/grid/resize.ts && ! grep -q "from ['\"].*geometry['\"]" src/grid/resize.ts && echo RESIZE_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src/grid/resize.ts` exports `resizeByDrag`, `resizeByKeyboard`, `equalizeAllRatios` (source assertion).
    - `pnpm vitest run resize` exits 0 with all behavior cases green.
    - Behavior: drag changes only the two adjacent subtrees (other split ratios byte-identical); keyboard resize moves in 5% steps and stops at the 20×5 floor without overshoot (GRD-04/05).
    - Cadence assertion (mocked sync): keyboard fires `markStructuralChange` per step; drag fires `markDragSettled` once on drag-end, never per drag-move (A3-CONTEXT).
    - `resize.ts` does NOT import `geometry.ts` (file-ownership: A3-02 owns that file in the same wave).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>Drag + keyboard resize with the 20×5 clamp and correct mirror cadence exist, unit-tested green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User keystroke / pointer drag → ratio mutation | Local input adjusts split ratios + focus; bounded by the 20×5 clamp |
| Focus/resize change → `sync_grid` | Crosses to the Rust mirror (in-memory, no disk I/O) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A3-07 | Denial of Service | Drag/keyboard resize spam degrading rendering | mitigate | Drag sync is coalesced to a single `markDragSettled` on pointer-up (A3-CONTEXT cadence, verified by mocked-sync test) so a frantic drag cannot flood the Tauri command boundary; the 20×5 clamp bounds the ratio range so resize cannot drive panes to zero. |
| T-A3-08 | Tampering | `focusByDirection`/`resize` consuming `winW`/`winH` | mitigate | Window dimensions are read from the app's own layout (local, trusted); the algorithms are pure functions with no path/command/eval surface. No external input crosses here. |
| T-A3-SC | Tampering | npm/cargo installs | accept | This plan adds NO new npm or cargo package — pure TypeScript over the A3-01 model. No legitimacy gate required. |
</threat_model>

<verification>
- `pnpm vitest run focus` and `pnpm vitest run resize` green; `pnpm exec tsc --noEmit` exits 0.
- 2×2 + ≥6-pane fixtures: numeric/i3-directional/click/cycle focus and drag/keyboard resize behave per A3-SPEC.
- Resize clamps at the 20×5 floor with no overshoot; drag affects only the two adjacent subtrees.
- No `geometry.ts` import in this plan (Wave-2 file-ownership isolation from A3-02).
</verification>

<success_criteria>
- GRD-03: numeric (`⌘1-9`), i3-directional (`⌘⌥`arrow), click, and cycle (`⌘[`/`⌘]` wrap) focus all work; indices >9 cycle/click only.
- GRD-04: drag-border, keyboard-5% (`⌘⌥⇧`arrow), and equalize (`⌘=`) resize work.
- GRD-05 (resize half): every resize path clamps at the 20×5 floor.
</success_criteria>

<output>
Create `.planning/phases/A3-voss-app-grid-engine/A3-03-SUMMARY.md` when done.
</output>
