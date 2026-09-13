---
phase: A3-voss-app-grid-engine
plan: 04
type: execute
wave: 3
depends_on: [A3-01, A3-02, A3-03]
files_modified:
  - apps/voss-app/src/grid/GridRoot.tsx
  - apps/voss-app/src/grid/SplitNode.tsx
  - apps/voss-app/src/grid/DragHandle.tsx
  - apps/voss-app/src/grid/keymap.ts
  - apps/voss-app/src/grid/__tests__/keymap.test.ts
  - apps/voss-app/src/grid/__tests__/GridRoot.test.tsx
autonomous: true
requirements: [GRD-01, GRD-03, GRD-04, GRD-07]
must_haves:
  truths:
    - "The binary-split tree renders recursively: H splits side-by-side, V splits stacked, each leaf wrapping the A2 pane component"
    - "The full keymap (⌘\\ ⌘⇧\\ ⌘D ⌘W ⌘1–9 ⌘[ ⌘] ⌘⌥arrow ⌘⌥⇧arrow ⌘=) dispatches to the A3-02/03 operations"
    - "Dragging a split border resizes the two adjacent subtrees and syncs the Rust mirror once on pointer-up"
    - "Clicking an unfocused pane focuses it"
    - "Exactly one pane shows the inset-shadow focus treatment; no border ring; focus repaint is instant"
  artifacts:
    - path: "apps/voss-app/src/grid/GridRoot.tsx"
      provides: "Grid container + global keymap mount + window-resize floor handling"
      contains: "grid-root"
    - path: "apps/voss-app/src/grid/SplitNode.tsx"
      provides: "Recursive split/leaf renderer with focus treatment"
      contains: "SplitNode"
    - path: "apps/voss-app/src/grid/DragHandle.tsx"
      provides: "6px transparent drag overlay with pointer capture"
      contains: "setPointerCapture"
    - path: "apps/voss-app/src/grid/keymap.ts"
      provides: "Keystroke → grid-operation dispatch table"
      contains: "dispatchKey"
  key_links:
    - from: "apps/voss-app/src/grid/keymap.ts"
      to: "apps/voss-app/src/grid/operations.ts"
      via: "dispatch ⌘\\ ⌘⇧\\ ⌘D ⌘W ⌘= to split/fork/close/equalize"
      pattern: "splitFocused|forkFocused|closeFocused|equalizeAll"
    - from: "apps/voss-app/src/grid/DragHandle.tsx"
      to: "apps/voss-app/src/grid/resize.ts"
      via: "pointer-move → resizeByDrag; pointer-up → markDragSettled"
      pattern: "resizeByDrag"
    - from: "apps/voss-app/src/grid/SplitNode.tsx"
      to: "apps/voss-app/src/grid/focus.ts"
      via: "leaf click → focusByClick"
      pattern: "focusByClick"
---

<objective>
Render the binary-split tree and wire every keyboard shortcut and the drag handles to the
A3-02/A3-03 operations — turning the model into an interactive multi-pane grid with the
locked Variant B focus treatment.

Purpose: This is where the engine becomes visible and usable. It composes the four logic
modules behind the A3-UI-SPEC visual contract.

Output: `GridRoot.tsx` (container + global keymap + window-resize floor handling),
`SplitNode.tsx` (recursive renderer + focus treatment), `DragHandle.tsx` (6px overlay),
`keymap.ts` (dispatch table). Implements GRD-01 render, GRD-03/04 input wiring, GRD-07
focus treatment.
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
<!-- From A3-01/02/03 (depends_on). Consume directly — no codebase exploration. -->
From apps/voss-app/src/grid/tree.ts:
  types TreeNode/SplitNode/PaneLeaf/GridStore; createGridStore(); collectLeaves; findLeaf
From apps/voss-app/src/grid/operations.ts:
  splitFocused(store,"H"|"V"); forkFocused(store); closeFocused(store); equalizeAll(store)
From apps/voss-app/src/grid/focus.ts:
  focusByIndex(store,n); focusByClick(store,id); cycleFocus(store,"next"|"prev");
  focusByDirection(store,dir,winW,winH)
From apps/voss-app/src/grid/resize.ts:
  resizeByDrag(store,splitId,ratio,winW,winH,cw,ch); resizeByKeyboard(store,dir,winW,winH,cw,ch)
From apps/voss-app/src/grid/sync.ts:
  markDragSettled(store)   // call once on pointer-up

A2 pane unit (assumed-present upstream — DO NOT modify A2 internals):
  apps/voss-app/src/pane/PaneComponent.tsx — the tileable leaf. SplitNode wraps it,
  passes pixel dimensions on mount + a `focused` boolean. The PaneHeader index segment
  + ⋯ menu are A3-05 (next wave); in THIS plan render PaneComponent as-is and leave a
  clearly-marked mount point for A3-05's PaneHeader/DotMenu/CloseConfirmBanner overlay.

A1 token system (assumed-present upstream — consume verbatim, never redefine):
  Tailwind utilities from A1: bg-bg-0/1/2/3, border-border, border-border-bright,
  text-fg-0..3, font-mono; focused container shadow class
  shadow-[inset_0_0_0_1px_var(--focus)]. NO border-radius, NO CSS transitions.
</interfaces>

@.planning/phases/A3-voss-app-grid-engine/A3-SPEC.md
@.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md
@.planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md
@.planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md
@.planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Keymap dispatch table (keymap.ts)</name>
  <files>apps/voss-app/src/grid/keymap.ts, apps/voss-app/src/grid/__tests__/keymap.test.ts</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-02/03/04 — the exact chord set (⌘\ ⌘⇧\ ⌘D ⌘W ⌘1-9 ⌘[ ⌘] ⌘⌥arrow ⌘⌥⇧arrow ⌘=) and what each does (governing contract)
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### apps/voss-app/src/grid/GridRoot.tsx" — keyboard handler registration guidance
    - apps/voss-app/src/grid/operations.ts (A3-02), focus.ts + resize.ts (A3-03) — the dispatch targets
  </read_first>
  <behavior>
    - dispatchKey(store, evt, winW, winH, cw, ch) maps `Meta+\` → splitFocused("H"); `Meta+Shift+\` → splitFocused("V"); `Meta+d` → forkFocused; `Meta+w` → closeFocused (gated callback — see action); `Meta+=` → equalizeAll.
    - `Meta+1`..`Meta+9` → focusByIndex(1..9); `Meta+[` → cycleFocus("prev"); `Meta+]` → cycleFocus("next").
    - `Meta+Alt+ArrowLeft/Right/Up/Down` → focusByDirection(left/right/up/down); `Meta+Alt+Shift+Arrow*` → resizeByKeyboard(same dir).
    - A chord that matches calls evt.preventDefault() and returns true; an unmatched chord returns false and does not preventDefault (keystroke passes through to the focused PTY pane).
    - `Meta+0` and `Meta+Alt` alone are unmatched (no-op, returns false).
  </behavior>
  <action>
    Create `apps/voss-app/src/grid/keymap.ts` exporting `dispatchKey(store: GridStore,
    evt: KeyboardEvent, winW: number, winH: number, cw: number, ch: number, onCloseRequest:
    (store: GridStore) => void): boolean`. Build the chord→action table EXACTLY per
    A3-SPEC GRD-02/03/04 (chords listed in `<behavior>`). Distinguish `⌘\` vs `⌘⇧\` via
    `evt.shiftKey`; distinguish `⌘⌥`arrow (focus) vs `⌘⌥⇧`arrow (resize) via
    `evt.shiftKey`. For `⌘W` do NOT call `closeFocused` directly — call the injected
    `onCloseRequest(store)` (A3-05 supplies the foreground-detection-gated close; until
    A3-05 lands, GridRoot passes `closeFocused` as a default so the chord still works and
    A3-05 swaps it — keeps the close-confirm gate as the A3-PATTERNS-mandated separate
    concern). On a matched chord call `evt.preventDefault()` and return `true`; on no match
    return `false` WITHOUT preventing default (so unmatched keystrokes reach the focused
    A2 PTY — terminal must stay usable). Pure dispatch — no DOM listener registration here
    (GridRoot owns the `window` listener). Author
    `apps/voss-app/src/grid/__tests__/keymap.test.ts` with synthetic `KeyboardEvent`s
    asserting each mapping + the pass-through (return false, no preventDefault) for
    unmatched chords.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run keymap --reporter=dot 2>&1 | tail -12 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'dispatchKey' src/grid/keymap.ts && grep -q 'splitFocused' src/grid/keymap.ts && grep -q 'forkFocused' src/grid/keymap.ts && grep -q 'focusByDirection' src/grid/keymap.ts && grep -q 'resizeByKeyboard' src/grid/keymap.ts && grep -q 'onCloseRequest' src/grid/keymap.ts && echo KEYMAP_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src/grid/keymap.ts` exports `dispatchKey` and references `splitFocused`, `forkFocused`, `focusByDirection`, `resizeByKeyboard`, `onCloseRequest` (source assertion).
    - `pnpm vitest run keymap` exits 0 with every chord mapping + pass-through case green.
    - Behavior: matched chord returns true + preventDefault; unmatched chord returns false + NO preventDefault (PTY pass-through preserved).
    - `⌘W` routes through the injected `onCloseRequest` callback, not a direct `closeFocused` (separation-of-concern key-link assertion).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>The full A3 keymap dispatches to operations/focus/resize and lets unmatched keys reach the PTY; unit-tested green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Recursive renderer + drag handle (SplitNode.tsx, DragHandle.tsx)</name>
  <files>apps/voss-app/src/grid/SplitNode.tsx, apps/voss-app/src/grid/DragHandle.tsx, apps/voss-app/src/grid/__tests__/GridRoot.test.tsx</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### apps/voss-app/src/grid/SplitNode.tsx" + "### apps/voss-app/src/grid/DragHandle.tsx" — render contract + drag contract (governing contracts; greenfield)
    - .planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md "## Split Border + Drag Handle Contract" + "## Focus Visual Treatment" + "## Grid Layout Architecture" — 1px border, 6px handle, inset-shadow focus, NO border ring, NO transition
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-01 (binary tree render) + GRD-07 (inset-shadow + bg-lift, no border ring)
    - apps/voss-app/src/grid/resize.ts (A3-03) + focus.ts (A3-03) + sync.ts (A3-01)
    - apps/voss-app/src/pane/PaneComponent.tsx — A2 leaf component (consume as black box; read its prop signature only)
  </read_first>
  <behavior>
    - SplitNode given a PaneLeaf renders the A2 PaneComponent inside a container; the container carries `shadow-[inset_0_0_0_1px_var(--focus)]` iff `leaf.id === store.focusedId`, else no shadow (GRD-07; exactly one focused).
    - SplitNode given an "H" SplitNode renders a row: left child at `ratio*100%` width, right at `(1-ratio)*100%`, a 1px `border-border` divider, and a DragHandle; "V" renders a column with `border-bottom`.
    - Rendering a 2×2 tree (3 splits) produces exactly 4 PaneComponent mounts; a ≥6-pane tree renders without error.
    - Clicking a leaf container calls focusByClick(store, leaf.id).
    - No element in the rendered output has a border-radius utility or any CSS transition on box-shadow/background (Variant B + perf budget).
  </behavior>
  <action>
    Create `apps/voss-app/src/grid/SplitNode.tsx` (Solid) — a recursive component:
    PaneLeaf case wraps `<PaneComponent .../>` (A2, imported from
    `../pane/PaneComponent`) in a relatively-positioned container, applying
    `shadow-[inset_0_0_0_1px_var(--focus)]` ONLY when `leaf.id === store.focusedId`
    (GRD-07 inset shadow inside the 1px border — NEVER an `outline`/`border` ring;
    A3-UI-SPEC "No border ring rule"), an `onClick` calling `focusByClick(store,
    leaf.id)` (A3-03), and passing the leaf's computed pixel size + a `focused` prop to
    PaneComponent so xterm sizes correctly. Leave an explicit
    `{/* A3-05 mount: PaneHeader index + ⋯ menu + CloseConfirmBanner overlay here */}`
    comment at the top of the leaf container (next-wave seam — do NOT implement chrome
    here). SplitNode case: `H` → flex row with `width: ratio*100% / (1-ratio)*100%` +
    `border-right: 1px solid var(--border)` on the first child + a `<DragHandle
    orientation="H" .../>`; `V` → flex column with heights + `border-bottom`. Use ONLY A1
    Tailwind utilities (`bg-bg-*`, `border-border`, `border-border-bright`) — NO
    `border-radius`, NO CSS `transition` on focus/bg (A3-UI-SPEC Anti-Patterns; perf
    budget). Create `apps/voss-app/src/grid/DragHandle.tsx` — a transparent 6px overlay
    centered on the divider (`width:6px` + `cursor:col-resize` for `H`; `height:6px` +
    `cursor:row-resize` for `V`; A3-UI-SPEC "Drag Handle"). `onPointerDown`:
    `setPointerCapture`; `onPointerMove`: compute requested ratio from pointer delta vs
    the split node's pixel span, call `resizeByDrag(store, splitId, ratio, winW, winH, cw,
    ch)` (A3-03 — it clamps at the 20×5 floor silently); `onPointerEnter`/`Leave`: toggle
    the adjacent divider to `border-border-bright` via a signal (instant, NO transition);
    `onPointerUp`: release capture + call `markDragSettled(store)` (A3-01 — single mirror
    sync on drag-end per A3-CONTEXT cadence). Author
    `apps/voss-app/src/grid/__tests__/GridRoot.test.tsx` using `@solidjs/testing-library`
    rendering a 2×2 and a ≥6-pane fixture, asserting 4 (resp. ≥6) pane mounts, exactly one
    focused container with the inset-shadow class, click-to-focus, and zero
    `rounded`/`transition` classes in the tree (Variant B). Mock `../pane/PaneComponent`
    with a lightweight stub so the test does not boot a real PTY.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run GridRoot --reporter=dot 2>&1 | tail -15 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'setPointerCapture' src/grid/DragHandle.tsx && grep -q 'markDragSettled' src/grid/DragHandle.tsx && grep -q 'focusByClick' src/grid/SplitNode.tsx && grep -q 'inset_0_0_0_1px_var(--focus)' src/grid/SplitNode.tsx && ! grep -nE 'rounded|transition:|transition ' src/grid/SplitNode.tsx src/grid/DragHandle.tsx && ! grep -nE 'outline|border-.*focus|ring' src/grid/SplitNode.tsx && echo RENDER_OK</automated>
  </verify>
  <acceptance_criteria>
    - `SplitNode.tsx` recursively renders H rows / V columns wrapping `PaneComponent` leaves; `DragHandle.tsx` uses `setPointerCapture` and calls `resizeByDrag` + `markDragSettled` (source assertions).
    - `pnpm vitest run GridRoot` exits 0: a 2×2 tree mounts exactly 4 panes; a ≥6-pane tree renders without error (GRD-01).
    - Behavior: exactly one leaf container has `shadow-[inset_0_0_0_1px_var(--focus)]`; clicking a leaf calls `focusByClick`; NO `outline`/border-ring on the pane boundary (GRD-07 — grep gate).
    - No `rounded` and no `transition` token in `SplitNode.tsx`/`DragHandle.tsx` (Variant B + perf budget — grep gate).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>The tree renders recursively with the locked focus treatment and draggable borders; component tests green; Variant B grep gates pass.</done>
</task>

<task type="auto">
  <name>Task 3: GridRoot container — keymap mount + window-resize floor handling</name>
  <files>apps/voss-app/src/grid/GridRoot.tsx, apps/voss-app/src/grid/__tests__/GridRoot.test.tsx</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### apps/voss-app/src/grid/GridRoot.tsx" — container contract + keyboard handler registration + background visibility (governing contract)
    - .planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md "## Grid Layout Architecture" — grid-root fills window minus titlebar, bg-bg-0
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-05 (OS-window shrink that would violate 20×5 stops shrinking affected panes)
    - apps/voss-app/src/grid/keymap.ts (Task 1), SplitNode.tsx (Task 2), tree.ts (A3-01)
  </read_first>
  <action>
    Create `apps/voss-app/src/grid/GridRoot.tsx` (Solid). Render `<div class="grid-root
    bg-bg-0 w-full h-full overflow-hidden">` containing `<SplitNode node={store.root}
    store={store} .../>` (A3-UI-SPEC container hierarchy; `--bg-0` visible only mid-drag,
    never steady state). Own the global keyboard listener: in `onMount` add a `window`
    `keydown` listener calling `dispatchKey(store, evt, winW(), winH(), cw, ch,
    onCloseRequest)` (Task 1); `onCleanup` removes it. Track window size with a signal
    updated from a `window` `resize` listener; derive `cw`/`ch` (xterm cell px) from the
    A2 pane's reported cell metrics (read-only — A2 owns the value; if not yet exposed,
    use the documented A2 default cell size and add a TODO referencing the A2 metric
    source — do NOT modify A2). On window resize, recompute layout; per GRD-05, if
    shrinking would push any pane below 20×5, stop shrinking the affected panes (clamp the
    effective layout so no pane renders < 20 cols × 5 rows — implement by flooring the
    per-pane allocated px at the 20×5 minimum and letting `--bg-0` show rather than
    sub-floor a pane). Provide `onCloseRequest` as a prop with a default of
    `closeFocused` (A3-02) so `⌘W` works now; A3-05 will pass the
    foreground-detection-gated variant. Mount-point note: GridRoot is what `App.tsx`
    (A1/A2 territory) renders below the titlebar — add a one-line export comment stating
    the integration contract; do NOT edit A1's `App.tsx` here (out of A3 file ownership —
    the integration wiring is verified in A3-06). Extend the existing
    `__tests__/GridRoot.test.tsx` with: a key event reaching `dispatchKey` (spy), and a
    simulated narrow window asserting no pane rect drops below the 20×5 px floor.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run GridRoot --reporter=dot 2>&1 | tail -15 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'grid-root' src/grid/GridRoot.tsx && grep -q 'bg-bg-0' src/grid/GridRoot.tsx && grep -Eq "addEventListener\(['\"]keydown" src/grid/GridRoot.tsx && grep -q 'dispatchKey' src/grid/GridRoot.tsx && grep -q 'onCleanup' src/grid/GridRoot.tsx && echo GRIDROOT_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src/grid/GridRoot.tsx` renders `.grid-root.bg-bg-0` wrapping `SplitNode` and registers a `window` keydown listener calling `dispatchKey`, cleaned up in `onCleanup` (source assertions).
    - `pnpm vitest run GridRoot` exits 0 including the keydown-reaches-dispatch spy and the narrow-window floor case (no pane rect < 20×5 — GRD-05 window-shrink stop).
    - `onCloseRequest` defaults to `closeFocused` so `⌘W` works pre-A3-05 (behavior assertion).
    - GridRoot does not edit A1's `App.tsx` (file-ownership: integration wiring verified in A3-06).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>GridRoot hosts the grid, owns the global keymap, and clamps window-shrink at the 20×5 floor; tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| OS keyboard / pointer events → grid operations | Untrusted-timing local input drives split/fork/close/focus/resize |
| Unmatched keystrokes → focused A2 PTY | Keys not consumed by the keymap pass through to a shell process |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A3-09 | Elevation of Privilege / Tampering | Keystroke pass-through to the focused PTY | mitigate | `dispatchKey` consumes (preventDefault) ONLY the explicit A3 chord set and returns false otherwise; it never rewrites or injects PTY input — pass-through is the raw unmodified event to the A2 pane, whose own input handling (A2, assumed-present) owns shell-input safety. A3 adds no new command-execution path. |
| T-A3-10 | Denial of Service | `⌘D`/`⌘\` key-spam fork-bomb via the keymap | mitigate | Keymap routes to `splitFocused`/`forkFocused` which are hard-gated by the 20×5 floor (A3-02); the dispatcher adds no bypass. The 9-pane numeric-nav ceiling + floor guard bound the live PTY set; window-shrink clamp (Task 3) prevents sub-floor pane proliferation. |
| T-A3-11 | Tampering | `cw`/`ch` cell metrics read from the A2 pane | accept | Cell metrics are read-only numeric values from the app's own A2 component (local, trusted). Worst case of a wrong value is a cosmetic mis-layout, not a security event. Accepted for the local-desktop model. |
| T-A3-SC | Tampering | npm/cargo installs | mitigate | This plan adds NO new runtime npm package. `@solidjs/testing-library` may be needed as a devDependency for component tests — it is the official Solid testing library (verify on npmjs.com/package/@solidjs/testing-library before install). If it is already present from A1/A2 scaffolding, no install occurs. No cargo changes. |
</threat_model>

<verification>
- `pnpm vitest run keymap` + `pnpm vitest run GridRoot` green; `pnpm exec tsc --noEmit` exits 0.
- 2×2 (4 panes) and ≥6-pane trees render; exactly one inset-shadow-focused pane; no border ring; no rounded/transition.
- Every A3 chord dispatches correctly; unmatched keys pass through to the PTY.
- Window-shrink stops at the 20×5 floor.
</verification>

<success_criteria>
- GRD-01: the binary-split tree renders recursively (H side-by-side, V stacked) with A2 panes as leaves.
- GRD-03/04: all keyboard shortcuts + click + drag wired to the A3-02/03 operations.
- GRD-07: exactly one pane shows inset-shadow + bg-lift, no border ring, instant repaint.
</success_criteria>

<output>
Create `.planning/phases/A3-voss-app-grid-engine/A3-04-SUMMARY.md` when done.
</output>
