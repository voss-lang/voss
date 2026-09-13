---
phase: A3-voss-app-grid-engine
plan: 02
type: execute
wave: 2
depends_on: [A3-01]
files_modified:
  - apps/voss-app/src/grid/operations.ts
  - apps/voss-app/src/grid/geometry.ts
  - apps/voss-app/src/grid/__tests__/operations.test.ts
autonomous: true
requirements: [GRD-02, GRD-05]
must_haves:
  truths:
    - "⌘\\ inserts a horizontal sibling of the focused pane (new pane right) at 50%; ⌘⇧\\ a vertical sibling (new pane below) at 50%"
    - "⌘D forks the focused pane: child inherits parent cwd + shell, fresh scrollback, same 50/50 sibling insertion"
    - "A split or fork that would force any resulting pane below 20 cols × 5 rows is a silent no-op (tree unchanged)"
    - "⌘W close removes the focused pane; the sibling subtree expands to fill and receives focus"
    - "Closing the last remaining pane spawns a fresh default pane (the app is never empty)"
  artifacts:
    - path: "apps/voss-app/src/grid/operations.ts"
      provides: "splitFocused / forkFocused / closeFocused / equalizeAll tree mutations"
      contains: "splitFocused"
    - path: "apps/voss-app/src/grid/geometry.ts"
      provides: "20×5 floor predicate from tree + window dimensions"
      contains: "wouldViolateFloor"
    - path: "apps/voss-app/src/grid/__tests__/operations.test.ts"
      provides: "Vitest coverage of split/fork/close + floor rejection + last-pane respawn"
      contains: "wouldViolateFloor"
  key_links:
    - from: "apps/voss-app/src/grid/operations.ts"
      to: "apps/voss-app/src/grid/geometry.ts"
      via: "floor guard before every split/fork mutation"
      pattern: "wouldViolateFloor"
    - from: "apps/voss-app/src/grid/operations.ts"
      to: "apps/voss-app/src/grid/sync.ts"
      via: "markStructuralChange after each mutation"
      pattern: "markStructuralChange"
---

<objective>
Implement the structural tree mutations — split-H, split-V, fork, close, equalize — with
the 20×5 hard-floor guard and the D-04 close behavior (sibling expands + focus moves;
last-pane auto-respawn).

Purpose: These are the verbs the keyboard and `⋯`-menu layers call. Isolating them from
rendering keeps them pure and unit-testable against the A3-SPEC acceptance criteria.

Output: `operations.ts` (the four mutations), `geometry.ts` (the floor predicate), and a
Vitest suite. Implements GRD-02 (split/fork/close behavior) and GRD-05 (per-pane 20×5
minimum, splits rejected).
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
<!-- From A3-01 (depends_on: A3-01) — consume these directly, no exploration. -->
From apps/voss-app/src/grid/tree.ts:
  types SplitNode/PaneLeaf/TreeNode/GridStore; createGridStore();
  recomputeIndices(root); equalizeRatios(root); findLeaf(root,id);
  collectLeaves(root): PaneLeaf[] (inorder); makeSplit(orientation,left,right) (ratio 0.5)
From apps/voss-app/src/grid/sync.ts:
  markStructuralChange(state)  // fires sync_grid immediately

A2 pane unit (assumed-present upstream — DO NOT modify A2):
  apps/voss-app/src/pane/PaneComponent.tsx is the tileable leaf; a PaneLeaf only needs
  id/cwd/shell/index — the render layer (A3-04/05) instantiates the actual component.
  Fork inheriting "cwd + shell + empty scrollback" = a NEW PaneLeaf with parent's
  cwd/shell and a fresh id (fresh id ⇒ fresh PTY ⇒ empty scrollback by construction).
</interfaces>

@.planning/phases/A3-voss-app-grid-engine/A3-SPEC.md
@.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md
@.planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 20×5 floor predicate (geometry.ts)</name>
  <files>apps/voss-app/src/grid/geometry.ts, apps/voss-app/src/grid/__tests__/operations.test.ts</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### 20×5 Floor Guard (all mutation operations)" — exact predicate contract (governing contract; greenfield, no analog)
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-05 (20 cols × 5 rows hard floor; splits rejected, resize clamped, window-shrink stops) + "## Constraints"
    - .planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md "## Grid Layout Architecture" — pane body = total pane height minus 22px header (the per-pane geometry input)
    - apps/voss-app/src/grid/tree.ts — tree shape + collectLeaves (A3-01)
  </read_first>
  <behavior>
    - Given a window of W×H px and xterm cell size (cw, ch), computePaneRects(root, W, H) returns one rect per leaf whose union tiles the full area (minus 1px borders).
    - A pane rect of (20*cw) px wide and (5*ch + 22) px tall is exactly at the floor (not violating).
    - wouldViolateFloor returns true iff any leaf rect is < 20 cols (rect.w/cw) OR < 5 rows ((rect.h - 22)/ch).
    - Simulating a horizontal split of a pane already only 30 cols wide (child gets ~15 cols) reports a violation.
  </behavior>
  <action>
    Create `apps/voss-app/src/grid/geometry.ts`. Export `computePaneRects(root: TreeNode,
    winW: number, winH: number): Map<string, {x,y,w,h}>` — recursively allocate pixel
    rectangles by walking SplitNodes (`H` splits width by `ratio`/`1-ratio`, `V` splits
    height), subtracting the 1px split border per A3-UI-SPEC "Split Border" and the 22px
    header is INSIDE each pane (do not subtract it from allocation — it is subtracted only
    when converting to terminal rows). Export `paneColsRows(rect, cw, ch): {cols, rows}`
    where `cols = floor(rect.w / cw)`, `rows = floor((rect.h - 22) / ch)` (22px header per
    A3-UI-SPEC). Export `wouldViolateFloor(root, winW, winH, cw, ch): boolean` — true iff
    ANY leaf has `cols < 20` OR `rows < 5` (GRD-05 floor; A3-PATTERNS predicate). Export
    `simulateSplitViolates(root, focusedId, orientation, winW, winH, cw, ch): boolean` —
    build the post-split tree shape in a clone, run `wouldViolateFloor`, return the
    result WITHOUT mutating the input (this is the pre-flight guard split/fork call).
    Pure functions only — no DOM, no Solid store, no Tauri. Add the listed behavior cases
    to `apps/voss-app/src/grid/__tests__/operations.test.ts`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run operations --reporter=dot 2>&1 | tail -12 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'wouldViolateFloor' src/grid/geometry.ts && grep -Eq '20|< *20' src/grid/geometry.ts && grep -q 'simulateSplitViolates' src/grid/geometry.ts && echo GEOMETRY_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src/grid/geometry.ts` exports `computePaneRects`, `paneColsRows`, `wouldViolateFloor`, `simulateSplitViolates` (source assertion).
    - `pnpm vitest run operations` exits 0 including the floor-predicate behavior cases.
    - Behavior assertion: a pane at exactly 20 cols × 5 rows does NOT violate; a simulated split of a 30-col pane DOES violate (GRD-05).
    - `geometry.ts` is pure — contains no `invoke(`, no JSX, no `document.` (behavior assertion).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>The 20×5 floor predicate + pre-split simulation exist and are unit-tested green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Tree mutations — split / fork / close / equalize with floor guard + D-04</name>
  <files>apps/voss-app/src/grid/operations.ts, apps/voss-app/src/grid/__tests__/operations.test.ts</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### apps/voss-app/src/grid/operations.ts" — operations contract + floor guard contract (governing contract)
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-02 (split/fork/close behavior + acceptance) + GRD-05
    - .planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md D-02 (50/50 insertion; ⌘D uses same 50/50 as ⌘\) + D-04 (close → sibling expands + focus; last-pane respawn)
    - apps/voss-app/src/grid/tree.ts (A3-01) + apps/voss-app/src/grid/geometry.ts (Task 1) + apps/voss-app/src/grid/sync.ts (A3-01)
  </read_first>
  <behavior>
    - splitFocused(store, "H") replaces the focused PaneLeaf with a makeSplit("H", oldLeaf, newLeaf) at ratio 0.5; new leaf is right sibling; indices recomputed; markStructuralChange fired.
    - splitFocused(store, "V") same with orientation "V" (new leaf below).
    - forkFocused(store) inserts a sibling via the same 50/50 H insertion (D-02); the new leaf's cwd and shell EQUAL the focused leaf's cwd and shell; new leaf has a fresh id distinct from the parent (⇒ fresh PTY ⇒ empty scrollback).
    - If simulateSplitViolates reports true, splitFocused/forkFocused make NO change (tree deep-equal to before) and do NOT fire markStructuralChange (GRD-05 silent no-op).
    - closeFocused(store) removes the focused leaf; its sibling subtree replaces the parent split (sibling "expands to fill"); focusedId becomes a leaf within that expanded sibling (D-04); indices recomputed; markStructuralChange fired.
    - closeFocused on the only remaining pane results in a tree with exactly one fresh default PaneLeaf focused (D-04 last-pane respawn — never empty).
    - equalizeAll(store) sets every SplitNode.ratio to 0.5 recursively and fires markStructuralChange.
  </behavior>
  <action>
    Create `apps/voss-app/src/grid/operations.ts` exporting `splitFocused(store:
    GridStore, orientation: "H" | "V")`, `forkFocused(store)`, `closeFocused(store)`,
    `equalizeAll(store)` operating on the A3-01 Solid store via `solid-js/store`
    `produce`/`reconcile` (do not replace the store reference — mutate through the setter).
    `splitFocused`: locate `store.focusedId` leaf; FIRST call
    `simulateSplitViolates(...)` (Task 1) — if it returns true, RETURN immediately (silent
    no-op, no toast, no banner, no sync — GRD-05 / A3-UI-SPEC "Error state: silent
    no-op"); else replace the leaf with `makeSplit(orientation, oldLeaf, newLeaf)` (ratio
    0.5, D-02; new leaf right/below = `right` child), call `recomputeIndices`, set
    `focusedId` to the new leaf, call `markStructuralChange(store)`. `forkFocused`: same as
    `splitFocused("H")` BUT the new `PaneLeaf` inherits the focused leaf's `cwd` + `shell`
    and gets a fresh `crypto.randomUUID()` id (fresh id ⇒ fresh PTY ⇒ empty scrollback —
    D-02/GRD-02; subject to the same floor guard). `closeFocused`: find the focused leaf's
    parent split; replace that split node with the focused leaf's SIBLING subtree (sibling
    expands to fill — D-04); set `focusedId` to the first leaf of that expanded sibling
    (inorder); `recomputeIndices`; `markStructuralChange`. If the focused leaf IS the root
    (last pane): replace root with a fresh default `PaneLeaf` and focus it (D-04 — app
    never empty, no quit, no empty state). `equalizeAll`: call `equalizeRatios(store.root)`
    + `markStructuralChange`. Close gating on a running foreground process is NOT done here
    — `closeFocused` executes the structural change unconditionally; the confirm-banner
    component (A3-05) decides whether to call it (A3-PATTERNS operations contract). Extend
    `apps/voss-app/src/grid/__tests__/operations.test.ts` with every behavior case above,
    including the 2×2-built-from-3-splits fixture and a ≥6-pane asymmetric tree (mirrors
    A3-SPEC acceptance criteria 1, 2, 3, 4, 5).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run operations --reporter=dot 2>&1 | tail -15 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'splitFocused' src/grid/operations.ts && grep -q 'forkFocused' src/grid/operations.ts && grep -q 'closeFocused' src/grid/operations.ts && grep -q 'simulateSplitViolates' src/grid/operations.ts && grep -q 'markStructuralChange' src/grid/operations.ts && echo OPERATIONS_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src/grid/operations.ts` exports `splitFocused`, `forkFocused`, `closeFocused`, `equalizeAll` (source assertion).
    - `pnpm vitest run operations` exits 0 with all behavior cases green.
    - Behavior: `⌘\`/`⌘⇧\` create correctly-oriented 50/50 siblings; `⌘D` child has parent's cwd+shell and a distinct fresh id; an under-floor split leaves the tree deep-equal-unchanged and fires no sync (GRD-05); closing the last pane yields exactly one fresh default leaf focused (D-04).
    - `operations.ts` calls `simulateSplitViolates` before mutating in `splitFocused`/`forkFocused` and `markStructuralChange` after every successful mutation (key-link assertion).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>Split/fork/close/equalize mutations exist with the 20×5 guard and D-04 close behavior, all unit-tested green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User keystroke / `⋯` menu → tree mutation | Local user input triggers split/fork/close; each fork/split spawns a new A2 PTY leaf |
| Tree mutation → `sync_grid` | Structural change crosses to the Rust mirror (no disk I/O) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A3-04 | Denial of Service | Fork-bomb via `⌘D`/`⌘\` key-spam → unbounded PTY processes | mitigate | The 20×5 floor guard (`simulateSplitViolates`, Task 1+2) makes split/fork a hard silent no-op once panes would shrink below floor — at typical window sizes this caps live panes well below any resource-exhaustion threshold and the 9-pane numeric-nav ceiling reinforces the intended working set. Each new leaf reuses the A2-bounded PTY (A2 D-02 backpressure already governs per-PTY resource use). |
| T-A3-05 | Tampering | `cwd`/`shell` inheritance on `⌘D` fork | mitigate | `forkFocused` copies the parent leaf's `cwd`/`shell` STRINGS verbatim into the new leaf — no shell-string concatenation, no command construction, no path interpolation in this layer. The actual PTY spawn (A2, assumed-present) owns shell execution and its own input validation; A3 only carries opaque metadata. |
| T-A3-06 | Tampering | Close path bypassing the running-process confirm | accept | `closeFocused` deliberately executes unconditionally; the confirm gate lives in A3-05's `CloseConfirmBanner` (A2 D-07 foreground detection). Splitting the gate from the mutation is the locked A3-PATTERNS contract; the only caller of bare `closeFocused` without the gate is a test. Accepted as designed. |
| T-A3-SC | Tampering | npm/cargo installs | accept | This plan adds NO new npm or cargo package — pure TypeScript over the A3-01 model. No legitimacy gate required. |
</threat_model>

<verification>
- `pnpm vitest run operations` green; `pnpm exec tsc --noEmit` exits 0.
- 2×2 (3-split) and ≥6-pane asymmetric fixtures construct, split, fork, close correctly.
- Under-floor split/fork is a verified silent no-op (tree deep-equal, no sync fired) — GRD-05.
- Last-pane close yields exactly one fresh default pane focused — D-04.
</verification>

<success_criteria>
- GRD-02: `⌘\`/`⌘⇧\` 50/50 siblings, `⌘D` fork inherits cwd+shell with fresh scrollback, `⌘W` close removes + sibling expands + focus moves.
- GRD-05: split/fork that would breach 20×5 is a silent no-op; the floor predicate is the single guard.
- D-04: closing the last pane respawns a fresh default pane (app never empty).
</success_criteria>

<output>
Create `.planning/phases/A3-voss-app-grid-engine/A3-02-SUMMARY.md` when done.
</output>
