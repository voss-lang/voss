# Plan: Warp-Style Pane Drag-Rearrange (voss-app grid)

**Captured:** 2026-06-09
**Status:** ready to implement
**Scope:** `apps/voss-app/src/grid/` + small touches in `src/index.css`
**Goal:** Drag a pane by its header to rearrange the grid — drop on another pane's
edge to re-split there, drop on its center to swap — matching Warp's pane-move UX
(shipped in Warp Feb 2024, see warpdotdev/Warp#623).

---

## 0. What already exists (do NOT rebuild)

| Capability | Where | Notes |
|---|---|---|
| Divider drag-resize | `src/grid/DragHandle.tsx` | 6px hit strip on every split border, pointer capture, live ratio update via `resizeByDrag`, 20×5 floor clamp, coalesced sync on pointer-up |
| Keyboard resize | `keymap.ts` (⌘⌥⇧arrow) | 5% steps |
| Split / fork / close / equalize | `operations.ts` | All run `recomputeIndices` + `balanceRatios` + `markStructuralChange` |
| Pixel geometry + floor guard | `geometry.ts` | `computePaneRects`, `wouldViolateFloor`, `simulateSplitViolates`, proxy-safe `cloneTree` |
| Path addressing of splits | `resize.ts` | `""` = root, `"L"`/`"R"` per descent |
| Solid→Rust mirror sync | `sync.ts` | `markStructuralChange` (immediate), `markDragMove`/`markDragSettled` (coalesced) |
| xterm resize debounce | `pane/PaneComponent.tsx:497-505` | ResizeObserver → 150ms debounced `fit()` + `pty_resize`. Rearrange gets this for free — pane containers resize, observer fires |
| Session/layout persistence | `sessionStorage.ts`, `layoutCommands.ts` | Serialize `GridStore` verbatim; tree shape unchanged by this feature ⇒ zero persistence work |

**The ONLY missing piece is drag-to-rearrange.** This plan adds it.

---

## 1. Target UX (Warp parity)

- **Drag handle = pane header** (the 22px `PaneHeader` strip). Pane body is the live
  terminal and must stay interactive — never a drag surface.
- **Drag threshold:** drag begins only after pointer moves >5px from pointerdown.
  Below threshold, pointerup = normal click (focus pane). Headers stay clickable.
- **5-zone drop model** on the hovered target pane:
  - Pointer in outer 25% band of an edge → **edge drop** → re-split target on that
    side (left/right = H split, top/bottom = V split), dragged pane takes that side.
  - Pointer in inner region → **center drop** → **swap** the two leaves in place
    (ratios untouched — every leaf is exactly one terminal, swap is the right
    semantic; i3 does the same).
- **Visual feedback during drag:**
  - Semi-transparent accent overlay covering the would-be region (half the target
    pane for edge zones, whole pane for center).
  - Small ghost chip following the cursor (pane index + cwd), `translate3d` only.
  - Global `cursor: grabbing`.
  - **No live re-layout during drag.** Tree mutates exactly once, on drop.
- **Cancel:** `Escape` or `pointercancel` aborts with no mutation.
- **No-ops:** drop on self, drop outside any pane, single-pane grid (drag never
  starts when `leafCount(root) === 1`).
- **Focus:** dragged pane is focused on drop (both edge and swap).
- Mouse-only. No keyboard pane-move (Warp parity — Warp staff confirmed mouse-only).

---

## 2. Architecture decisions (locked)

1. **Hand-rolled pointer events. No library.**
   - `@thisbeyond/solid-dnd`: stale ~2yr, element-droppable model, fights 5-zone math.
   - HTML5 DnD API: broken/unstylable in Tauri WKWebView. Never.
   - `setPointerCapture` on the header element routes every `pointermove`/`pointerup`
     to it for the whole drag — xterm canvases never see events mid-drag, **no
     event-blocking overlay needed**. (Same mechanism `DragHandle.tsx` already uses.)
2. **Visual overlay is `pointer-events: none`** — purely cosmetic (ghost + highlight),
   mounted under `GridRoot`, fixed inset-0.
3. **Rect snapshot once at drag start.** Locked tiling ⇒ grid cannot change mid-drag.
   Snapshot via DOM: `document.querySelectorAll('[data-pane-id]')` →
   `getBoundingClientRect()`. Avoids per-move layout reads AND avoids having to
   translate `computePaneRects` grid-local coords to client space.
4. **Hit-test + zone math from cached rects** against `e.clientX/Y` per move. Update
   two signals only (`ghost`, `dropTarget`). Grid tree untouched until drop ⇒ zero
   grid re-render during drag.
5. **Binary tree stays binary.** The "insert sibling, don't nest" advice from
   n-ary implementations (react-mosaic) does NOT apply — the wire contract with
   the Rust mirror (`grid.rs`) is a binary `SplitNode {left, right}`. Nesting is
   how this tree expresses 3+ siblings; `balanceRatios` normalizes the visual
   geometry regardless of spine shape. `splitFocused` already nests. Accept it.
6. **Sync cadence:** exactly one `markStructuralChange(store)` on successful drop.
   Nothing during the drag (no tree mutation happens, so nothing to coalesce).
7. **Mutation pattern:** identical to `operations.ts` — pure-ish functions that
   mutate the passed `GridStore` draft, called inside `setStore(produce(...))`.
8. **No `structuredClone` anywhere** — `produce` draft proxies throw
   DATA_CLONE_ERR (memory: voss-app-solid-produce-no-structuredclone). Reuse the
   hand-walk clone pattern; `geometry.ts` `cloneTree` is private, so `rearrange.ts`
   carries its own (or export `cloneTree` — see §4.4).

---

## 3. New files

```
src/grid/dropZone.ts            pure zone math (no DOM, no Solid)
src/grid/rearrange.ts           pure tree mutations + floor pre-flight
src/grid/paneDrag.ts            drag controller (signals + pointer handler factory)
src/grid/PaneDragLayer.tsx      overlay visuals (ghost + drop highlight)
src/grid/__tests__/dropZone.test.ts
src/grid/__tests__/rearrange.test.ts
```

Modified files:

```
src/grid/SplitNode.tsx          wire header pointerdown → drag controller
src/grid/GridRoot.tsx           own the controller, mount <PaneDragLayer/>
src/index.css                   .pane-drag-* styles
```

---

## 4. Module specs

### 4.1 `dropZone.ts` — pure zone math

```ts
import type { Rect } from './geometry';

export type DropZone = 'left' | 'right' | 'top' | 'bottom' | 'center';

export const EDGE_FRAC = 0.25; // Zed's drop_target_size; outer quarter = edge

/** Zone for a pointer at (x, y) inside rect. Caller guarantees containment. */
export function zoneAt(rect: Rect, x: number, y: number): DropZone {
  const rx = (x - rect.x) / rect.w;   // 0..1
  const ry = (y - rect.y) / rect.h;
  // distance to each edge in normalized space
  const d: [number, DropZone][] = [
    [rx, 'left'],
    [1 - rx, 'right'],
    [ry, 'top'],
    [1 - ry, 'bottom'],
  ];
  d.sort((a, b) => a[0] - b[0]);
  return d[0][0] < EDGE_FRAC ? d[0][1] : 'center';
}

/** First rect containing (x, y), or null. rects = drag-start snapshot. */
export function hitTest(
  rects: ReadonlyMap<string, Rect>,
  x: number,
  y: number,
): string | null {
  for (const [id, r] of rects) {
    if (x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h) return id;
  }
  return null;
}

/** Highlight rect for a zone: half the pane for edges, whole pane for center. */
export function highlightRect(rect: Rect, zone: DropZone): Rect {
  switch (zone) {
    case 'left':   return { ...rect, w: rect.w / 2 };
    case 'right':  return { ...rect, x: rect.x + rect.w / 2, w: rect.w / 2 };
    case 'top':    return { ...rect, h: rect.h / 2 };
    case 'bottom': return { ...rect, y: rect.y + rect.h / 2, h: rect.h / 2 };
    case 'center': return rect;
  }
}
```

Notes:
- `Rect` here is in **client/viewport coordinates** (from `getBoundingClientRect`),
  reusing the `Rect` shape from `geometry.ts` for the field names only.
- Tie-break on equal distances is fine via sort stability — corner behavior just
  needs to be deterministic, not "correct".

### 4.2 `rearrange.ts` — pure tree mutations

Signatures + algorithms. Follows `operations.ts` conventions exactly: mutate the
passed store, call `markStructuralChange` on success, take optional `GridGeom`
for floor pre-flight, silent no-op on guard failure.

```ts
import {
  type GridStore, type PaneLeaf, type TreeNode,
  balanceRatios, collectLeaves, findLeaf, recomputeIndices,
} from './tree';
import { wouldViolateFloor } from './geometry';
import type { GridGeom } from './operations';
import { markStructuralChange } from './sync';
import type { DropZone } from './dropZone';
```

**`detachLeaf(node, id): { root: TreeNode | null; leaf: PaneLeaf | null }`**
(module-private) — like `operations.ts` `closeLeaf` but returns the removed leaf
instead of discarding it. Sibling subtree expands in place (parent split collapses
to the sibling). Returns `root: null` when `id` is the only pane. Implementation:
copy `closeLeaf`'s structure (operations.ts:50-73), additionally capturing
`{ ...foundLeaf }` on the way out. Do **not** export `closeLeaf` from operations —
the focus-return contract differs; keep them separate.

**`swapPanes(root, idA, idB): void`** (exported, pure on the tree)
- Find both leaves; if either missing or `idA === idB`, no-op.
- Swap the **payload fields** in place: `cwd`, `shell`, `id` — i.e. write A's
  `{id, cwd, shell}` into B's tree slot and vice versa. Equivalent to swapping
  the leaf objects, but in-place field writes are friendlier to the `produce`
  draft. Ratios untouched.
- Then `recomputeIndices(root)` — indices are geometric (inorder), so the two
  panes exchange index numbers automatically.

**`movePane(store, dragId, targetId, zone, geom?): boolean`** (exported — the
single entry point the drag controller calls on drop; returns true if mutated)

```
if dragId === targetId → return false
if zone === 'center':
    swapPanes(store.root, dragId, targetId)
    store.focusedId = dragId
    markStructuralChange(store)
    return true
// edge drop:
if geom && simulateMoveViolates(store.root, dragId, targetId, zone, geom) →
    return false                       // GRD-05 silent no-op
const { root, leaf } = detachLeaf(store.root, dragId)
if (!root || !leaf) return false       // dragId was the only pane / not found
// target still exists in `root` because target ≠ drag
const orientation = (zone === 'left' || zone === 'right') ? 'H' : 'V'
const dragFirst   = (zone === 'left' || zone === 'top')
const target = findLeaf(root, targetId);  if (!target) return false
store.root = replaceLeaf(root, targetId, makeSplit(
    orientation,
    dragFirst ? leaf : { ...target },
    dragFirst ? { ...target } : leaf,
))
recomputeIndices(store.root)
balanceRatios(store.root)              // Warp auto-equalize, same as split/close
store.focusedId = dragId
markStructuralChange(store)
return true
```

`replaceLeaf` is private in `operations.ts` (lines 32-43) — either export it
from there or duplicate the 10 lines in `rearrange.ts`. **Decision: export from
operations.ts** (it's the canonical spine-rebuild; two copies will drift).

**`simulateMoveViolates(root, dragId, targetId, zone, geom): boolean`** (exported)
- Mirror of `geometry.ts` `simulateSplitViolates`: hand-clone the tree
  (`{...n, left: clone, right: clone}` walk — add a local `cloneTree` or export
  the one in geometry.ts; **decision: export `cloneTree` from geometry.ts**),
  run the detach + re-split steps above on the clone, `balanceRatios`, then
  `wouldViolateFloor(clone, geom.winW, geom.winH, geom.cw, geom.ch)`.
- Only edge drops need this. **Swap never changes geometry** ⇒ no pre-flight.
- Note: a move keeps pane count constant but CAN violate the floor (e.g. dropping
  a third pane into a narrow column's vertical stack ⇒ rows < 5).

### 4.3 `paneDrag.ts` — drag controller

One factory, owned by `GridRoot`, threaded to leaves via props (same pattern as
`dims`/`closeUI`).

```ts
export interface PaneDragState {
  paneId: string;                       // dragged pane
  ghost: { x: number; y: number };      // cursor pos, client coords
  header: { cwd: string; index: number };
  target: { paneId: string; zone: DropZone } | null;  // null = no valid drop
}

export interface PaneDragController {
  state: Accessor<PaneDragState | null>;        // null = no drag in progress
  rects: Accessor<ReadonlyMap<string, Rect>>;   // drag-start snapshot (for layer)
  /** Attach to the pane-header wrapper's onPointerDown. */
  onHeaderPointerDown: (e: PointerEvent, paneId: string) => void;
}

export function createPaneDrag(
  store: Store<GridStore>,
  setStore: SetStoreFunction<GridStore>,
  dims: () => Dims,                     // GridRoot's existing dims()
): PaneDragController
```

Behavior:

1. **`onHeaderPointerDown(e, paneId)`**
   - Ignore unless `e.button === 0`.
   - Ignore if `(e.target as HTMLElement).closest('button')` — the `⋯` menu
     trigger must keep working.
   - Ignore if `leafCount(store.root) === 1` — nothing to rearrange.
   - Record `{ paneId, startX, startY, el: e.currentTarget }` as a *candidate*.
     Do **not** capture or preventDefault yet — a plain click must still reach
     the leaf wrapper's `onClick` (focus).
   - Add `pointermove`/`pointerup`/`pointercancel` listeners on the element
     (or use JSX handlers on the wrapper + the candidate flag — either works;
     JSX handlers are the existing house style, see DragHandle).
2. **Threshold check** in pointermove while candidate:
   `Math.hypot(dx, dy) > 5` → begin drag:
   - `el.setPointerCapture(e.pointerId)` (now events follow us everywhere —
     terminals never see them).
   - Snapshot rects: walk `document.querySelectorAll('[data-pane-id]')`,
     build `Map<paneId, DOMRect→Rect>`. (Leaf wrappers already carry
     `data-pane-id`, SplitNode.tsx:103.)
   - Set drag state signal; add `keydown` listener on `window` for Escape.
   - `document.body.classList.add('pane-dragging')` (cursor + user-select).
3. **pointermove while dragging:**
   - `setGhost({x: e.clientX, y: e.clientY})`.
   - `hit = hitTest(rects, x, y)`; if `hit === dragPaneId` or null → `target = null`;
     else `target = { paneId: hit, zone: zoneAt(rects.get(hit), x, y) }`.
   - Only signal writes. No store writes.
4. **pointerup:**
   - If dragging and `target !== null`:
     `setStore(produce(s => movePane(s, dragId, target.paneId, target.zone, dims())))`.
   - Cleanup (release capture, clear signals, remove class + key listener).
   - If never crossed threshold: do nothing — the click already focused the pane.
5. **Escape / pointercancel:** cleanup, no mutation.

Edge details:
- `e.preventDefault()` on pointerdown of the *candidate* would kill text-ellipsis
  click behavior nothing depends on — but DO `preventDefault` once the drag
  starts, and set `touch-action: none` on the header wrapper via CSS to be safe.
- `dims()` already exists on GridRoot (GridRoot.tsx:171) — pass through for the
  floor pre-flight.

### 4.4 Required exports (tiny diffs to existing files)

- `operations.ts`: `export function replaceLeaf(...)` (currently private, line 32).
- `geometry.ts`: `export function cloneTree(...)` (currently private, line 88).
- No behavior changes — export keyword only. Existing tests unaffected.

### 4.5 `PaneDragLayer.tsx` — overlay visuals

```tsx
export default function PaneDragLayer(props: { drag: PaneDragController }) {
  // <Show when={props.drag.state()}>
  //   fixed inset-0, z-index 50, pointer-events: none
  //   1. drop highlight: <Show when={state.target}>
  //        absolutely positioned div at highlightRect(rects.get(target.paneId), target.zone)
  //        class="pane-drag-highlight"
  //   2. ghost chip: div at translate3d(ghost.x + 8px, ghost.y + 8px, 0)
  //        class="pane-drag-ghost"  content: `{index} │ {cwd || shell}`
  // </Show>
}
```

- Highlight rect positions come straight from the snapshot map + `highlightRect()`.
  Client coords ⇒ `position: fixed` works directly.
- Ghost transform bound to the `ghost` signal — one DOM node updates per move,
  grid untouched (Solid fine-grained reactivity does this for free).

CSS (`src/index.css`, token-only per A8 house rules):

```css
.pane-drag-overlay { position: fixed; inset: 0; z-index: 50; pointer-events: none; }
.pane-drag-highlight {
  position: fixed;
  background: color-mix(in srgb, var(--focus) 18%, transparent);
  border: 1px solid var(--focus);
}
.pane-drag-ghost {
  position: fixed; top: 0; left: 0;
  padding: 2px 8px;
  font-family: var(--font-mono); font-size: 11px;
  background: var(--bg-2); color: var(--fg-1);
  border: 1px solid var(--border-bright);
  white-space: nowrap;
  will-change: transform;
}
body.pane-dragging { cursor: grabbing !important; user-select: none; }
body.pane-dragging * { cursor: grabbing !important; }
```

### 4.6 Wiring (`SplitNode.tsx`, `GridRoot.tsx`)

`SplitNode.tsx` leaf branch:
- New optional prop `paneDrag?: PaneDragController`, threaded recursively like
  `agentConfigByPaneId` (both `<SplitNodeView>` recursions + GridRoot call site).
- Wrap `<PaneHeader .../>` in a div (or put handler on the existing leaf wrapper —
  **no**: body must not drag; use a dedicated header wrapper):

```tsx
<div
  data-pane-header-grab
  style={{ 'touch-action': 'none' }}
  onPointerDown={(e) => props.paneDrag?.onHeaderPointerDown(e, asLeaf().id)}
>
  <PaneHeader ... />
</div>
```

`PaneHeader.tsx` itself: **unchanged** (stays presentational).

`GridRoot.tsx`:
- `const paneDrag = createPaneDrag(store, setStore, dims)` next to the existing
  store creation (~line 150).
- Pass `paneDrag={paneDrag}` into the root `<SplitNodeView>` (~line 418).
- Render `<PaneDragLayer drag={paneDrag} />` as a sibling after the grid container.

Conflict check — header drag vs existing handlers:
- Leaf wrapper `onClick={focus}` (SplitNode.tsx:109): pointerdown-candidate that
  never crosses threshold doesn't preventDefault ⇒ click fires ⇒ focus works. ✔
- After a real drag, suppress the trailing click (it would re-focus — harmless
  since we set `focusedId = dragId` anyway, but cleanliness): set a
  `justDragged` flag in the controller, and in the same wrapper add
  `onClickCapture` guard OR simply accept the redundant focus call (it's
  idempotent). **Decision: accept it** — `focusByClick` on the dragged pane is
  a no-op-equivalent.
- `⋯` button: excluded via `closest('button')`. ✔
- DragHandle dividers: live on split children, not headers — no overlap. During
  a pane drag, pointer capture means dividers get no events. ✔

---

## 5. Invariants that MUST survive (test contracts)

1. `recomputeIndices` runs after every structural mutation — indices stay 1-based,
   contiguous, inorder (existing contract, tree.ts:70).
2. `balanceRatios` runs after every **edge move** (Warp equalize, same as
   split/fork/close). Runs NOT after swap (geometry unchanged by design).
3. Pane `id`s are never destroyed or regenerated by rearrange — PTY sessions and
   scrollback are keyed by pane id; the existing preset/layout machinery already
   relies on this (D-04). `detachLeaf` + re-insert moves the same id.
4. Wire shape unchanged: `SplitNode {kind, orientation, ratio, left, right}` /
   `PaneLeaf {kind, id, cwd, shell, index}` — `sync_grid` and session/layout
   serialization need zero changes. Do not add fields to tree nodes.
5. Exactly one `markStructuralChange` per successful drop; zero syncs during drag.
6. GRD-05: edge move pre-flights `simulateMoveViolates`; on violation, silent
   no-op (no toast, no partial mutation). `simulateMoveViolates` must not mutate
   its input (clone first — assert via test).
7. Last-pane rule untouched: drag can't start at `leafCount === 1`, and
   `detachLeaf` on a 2-pane tree leaves a valid 1-leaf root mid-operation before
   re-insert (never expose that intermediate state — it all happens inside one
   `produce` frame).
8. No `structuredClone`. No `Date.now()`-dependent logic in pure modules.

---

## 6. Implementation order (each step verifiable)

Suggested commits in order. Run `pnpm vitest run` in `apps/voss-app` after each.

**Step 1 — pure math: `dropZone.ts` + tests**
- `zoneAt`: center hit, each edge band, corner determinism, exact-boundary (0.25).
- `hitTest`: inside/outside/edge-exclusive (x < x+w half-open).
- `highlightRect`: all 5 zones.
- Verify: new tests green, nothing else touched.

**Step 2 — exports: `replaceLeaf` (operations.ts), `cloneTree` (geometry.ts)**
- Keyword-only diff. Verify: full suite still green (sentinel risk: none — no
  schema/shape change).

**Step 3 — `rearrange.ts` + tests** (the core; biggest test surface)
- `swapPanes`:
  - 2-pane H tree: swap exchanges ids/cwd/shell across slots, ratio untouched,
    indices re-assigned (pane that was 1 is now 2).
  - Deep tree: swap across different subtrees.
  - Self-swap / missing id: no-op, tree deep-equal unchanged.
- `movePane` center: delegates to swap, sets `focusedId = dragId`, returns true.
- `movePane` edge — table-test all 4 zones on a 2-pane tree:
  - `[A│B]`, drag A onto B/'right' → `[B│A]` (H split, target first).
  - `[A│B]`, drag A onto B/'bottom' → `[B over A]` (V).
  - Orientation + child order assertions per zone (left/top ⇒ drag first).
- `movePane` edge on 3-pane tree: detach collapses old parent (the remaining
  sibling expands), target re-splits, `balanceRatios` re-equalizes
  (assert ratios = leaves(left)/leaves(node) throughout), indices contiguous.
- `movePane` drag === target: false, untouched.
- Floor: craft geom where the move violates 20×5 → returns false, tree
  deep-equal unchanged; generous geom → mutates. `simulateMoveViolates` does
  not mutate input (deep-equal before/after).
- Sync cadence: mock `./sync` (existing tests do this — see tree.test.ts
  pattern), assert exactly one `markStructuralChange` per successful drop,
  zero on no-ops.

**Step 4 — `paneDrag.ts` controller + `PaneDragLayer.tsx` + CSS**
- Controller unit-testable headless-ish: export internals or test through
  dispatched PointerEvents on a fake header element (jsdom supports
  `setPointerCapture` stubs — stub if missing:
  `el.setPointerCapture ??= () => {}`).
- Tests: threshold (4px move ⇒ no drag state; 6px ⇒ drag state), button-child
  pointerdown ignored, single-pane ignored, Escape clears without store write,
  drop with target calls `movePane` once with right args, drop with null target
  mutates nothing.

**Step 5 — wire `SplitNode.tsx` + `GridRoot.tsx`**
- Thread `paneDrag` prop, header grab wrapper, mount layer.
- Extend an acceptance test (pattern: `__tests__/a*-acceptance.test.tsx`):
  render GridRoot, split twice, simulate header pointerdown→move(>5px over
  another pane's center)→up, assert tree swapped + focus moved + one sync.

**Step 6 — manual verify in dev app**
- `pnpm tauri dev` → split 3-4 panes → drag by header:
  - ghost follows, highlight shows correct half/whole region
  - edge drop re-splits, center drop swaps, Warp-equalized sizes after edge drop
  - Escape cancels; click (no move) still focuses; ⋯ menu still opens
  - terminals keep their PTY content across moves (id preservation — content
    survives because PaneComponent remount re-attaches by pane id, same
    mechanism as preset apply)
  - resize storm check: hold a drop on edge repeatedly — xterm refits once per
    move (150ms debounce in PaneComponent), no jank

---

## 7. Known risks / watch items

- **PaneComponent remount on tree mutation.** Edge moves rebuild the spine
  (`replaceLeaf` creates new node objects), so Solid will re-create leaf views
  along the changed path — same as existing split/close behavior. PTY survives
  (keyed by pane id) but scrollback repaint behavior should match what ⌘D/⌘W
  already do. If split/close don't flash, rearrange won't either. Verify in
  Step 6; if flash appears, it's pre-existing behavior, not a regression — note
  it, don't fix in this phase.
- **jsdom pointer-capture gaps.** `setPointerCapture`/`releasePointerCapture`
  may be undefined in jsdom — stub in test setup, don't branch in prod code.
- **Concurrent auto-commit** (memory: voss-app-concurrent-autocommit): verify
  work landed via `git log`, not `git status`.
- **Sentinel tests** (memory: voss-stale-sentinel-tests): if unrelated sentinel
  pins fail mid-work, read the full FAILED list and bisect before touching them.
- **Header grab vs future header content:** anything interactive added to
  PaneHeader later must either be a `<button>` or get added to the
  pointerdown exclusion check.

---

## 8. Explicitly OUT of scope

- Keyboard pane-move shortcuts (Warp doesn't have them; add later if wanted).
- Drag pane to tab bar / tear-out to new window (Warp has it; Voss has no
  multi-tab grid yet).
- Live re-layout preview during drag (nobody ships this; overlay only).
- Divider polish (double-click divider to equalize, body-level cursor during
  divider drag) — nice-to-haves, separate micro-task if desired.
- n-ary tree refactor — binary is the wire contract.

---

## Appendix: research sources

- Warp pane rearrangement: https://github.com/warpdotdev/Warp/issues/623 (shipped
  v0.2024.02.06; drag by header, drop targets, mouse-only — staff confirmed)
- Warp split panes docs: https://docs.warp.dev/terminal/windows/split-panes
- VS Code DnD (5-zone overlay model): https://deepwiki.com/microsoft/vscode/4.6-drag-and-drop-system
- Zed `drop_target_size: 0.25`: https://zed.dev/docs/reference/all-settings
- i3 swap semantics: https://i3wm.org/docs/userguide.html
- Pointer capture: https://developer.mozilla.org/en-US/docs/Web/API/Element/setPointerCapture
- xterm fit debounce pitfall: https://github.com/xtermjs/xterm.js/issues/3584
  (already handled in PaneComponent.tsx:497-505)
- solid-dnd (evaluated, rejected): https://github.com/thisbeyond/solid-dnd
- corvu Resizable (evaluated, rejected for tree-driven layout): https://corvu.dev/docs/primitives/resizable/
