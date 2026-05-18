# Phase A3: voss-app Grid Engine — Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 11 new/modified files
**Analogs found:** 0 / 11 — fully greenfield (no source code exists in `apps/voss-app/` yet)

> **Critical grounding:** `apps/voss-app/` contains only `CONCEPT.md` + `FEATURES.md`. A1 and A2
> are PLANNED but NOT executed. No Solid, Rust/Tauri, or CSS source exists anywhere in the repo
> outside of the frozen `crates/` spike, which is reference-only (do not edit). Every A3 file is
> greenfield. Pattern assignments therefore map each file to its **governing contract** (spec
> section, prior-phase context decision, UI-spec excerpt) rather than to an in-repo code analog.
> The frozen spike is cited once where its Rust struct idiom genuinely informs the mirror design,
> clearly labeled "reference-only idiom, do not copy."

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `apps/voss-app/src/grid/tree.ts` | model/store | event-driven (Solid signals) | none — greenfield | no analog |
| `apps/voss-app/src/grid/operations.ts` | service/utility | transform (tree mutations) | none — greenfield | no analog |
| `apps/voss-app/src/grid/focus.ts` | service/utility | event-driven (focus state) | none — greenfield | no analog |
| `apps/voss-app/src/grid/resize.ts` | service/utility | event-driven (ratio mutations) | none — greenfield | no analog |
| `apps/voss-app/src/grid/GridRoot.tsx` | component | request-response (layout render) | none — greenfield | no analog |
| `apps/voss-app/src/grid/SplitNode.tsx` | component | request-response (recursive render) | none — greenfield | no analog |
| `apps/voss-app/src/grid/DragHandle.tsx` | component | event-driven (pointer events) | none — greenfield | no analog |
| `apps/voss-app/src/grid/PaneHeader.tsx` | component | event-driven (additive A2 edit) | none — greenfield | no analog |
| `apps/voss-app/src/grid/DotMenu.tsx` | component | request-response (`⋯` popup) | none — greenfield | no analog |
| `apps/voss-app/src/grid/CloseConfirmBanner.tsx` | component | event-driven (confirm inline) | none — greenfield | no analog |
| `crates/voss-app-core/src/grid.rs` | model/state | CRUD (Rust mirror structs) | none — greenfield | no analog |

---

## Pattern Assignments

### `apps/voss-app/src/grid/tree.ts` (model/store, event-driven)

**Analog:** none — greenfield.
**Governing contracts:** A3-SPEC GRD-01 + GRD-08; A3-CONTEXT D-02 (50/50 split); A1-CONTEXT D-09 (Solid = source of truth; Rust/Tauri owns persisted state).

**Data shape contract (from A3-SPEC GRD-01 + GRD-08):**

The store holds a discriminated-union binary tree. Internal nodes carry orientation + ratio; leaf nodes carry pane identity. Solid `createStore` or nested `createSignal` wrapping this shape is the implementation mechanism. Exact signal shape is planner's call; the required fields are:

```
type SplitNode = {
  kind: "split";
  orientation: "H" | "V";   // H = side-by-side (⌘\); V = stacked (⌘⇧\)
  ratio: number;             // 0.0–1.0, clamped so neither child falls below 20×5 floor
  left: TreeNode;            // left / top subtree
  right: TreeNode;           // right / bottom subtree
};

type PaneLeaf = {
  kind: "pane";
  id: string;                // stable UUID per pane instance
  cwd: string;               // current working directory
  shell: string;             // shell binary (basename of $SHELL)
  index: number;             // 1-based geometric index (left-to-right, top-to-bottom)
};

type TreeNode = SplitNode | PaneLeaf;

type GridStore = {
  root: TreeNode;
  focusedId: string;         // id of the currently focused PaneLeaf
};
```

**50/50 insertion contract (A3-CONTEXT D-02):**
New splits ALWAYS set `ratio: 0.5`. `⌘=` equalize resets ALL split nodes in the tree to `ratio: 0.5` recursively.

**Mirror sync contract (A3-SPEC GRD-08; A3-CONTEXT "Solid→Rust mirror sync cadence"):**
After every structural change (split, fork, close, equalize) call a Tauri command to sync the Rust mirror. During an active drag, debounce is acceptable — fire once on drag-end. The Rust mirror must match after the change settles. No disk I/O in A3 (the Tauri command writes to in-memory state only).

**Index recompute contract (A3-CONTEXT "Pane index recompute"):**
Indices are stable geometric positions, not sparse IDs. Recompute on every structural change by walking the tree left-to-right, top-to-bottom (inorder traversal of the binary tree). No gaps.

---

### `apps/voss-app/src/grid/operations.ts` (service/utility, transform)

**Analog:** none — greenfield.
**Governing contracts:** A3-SPEC GRD-02 (split/fork/close behavior); A3-SPEC GRD-05 (20×5 floor); A3-CONTEXT D-04 (close → sibling expands; last pane respawns).

**Operations required:**

```
splitFocused(store, orientation: "H" | "V") → void
  // Insert a new PaneLeaf sibling of the focused leaf at ratio 0.5.
  // REJECT (no-op, silent) if the split would force any pane below 20 cols × 5 rows.

forkFocused(store) → void
  // Same insertion as splitFocused("H") but the new leaf inherits
  // focused pane's cwd + shell and starts with empty scrollback.
  // Subject to same 20×5 rejection guard.

closeFocused(store) → void
  // Remove the focused leaf. Sibling subtree expands to fill the freed space (D-04).
  // If this is the last pane: auto-spawn a fresh default pane (D-04 — app is never empty).
  // Focus moves to the sibling that expanded (D-04).
  // Close is gated on foreground detection (A2 D-07) at the call site — this function
  // executes the structural change unconditionally; the confirm-banner component handles gating.

equalizeAll(store) → void
  // Walk the entire tree; set every SplitNode's ratio to 0.5 recursively.
```

**Floor guard contract (A3-SPEC GRD-05):**
Before executing any split/fork, compute whether the resulting geometry places any pane below 20 columns × 5 rows given the current window dimensions. If yes, return early — no toast, no banner, no error UI (A3-UI-SPEC "Error state: silent no-op").

---

### `apps/voss-app/src/grid/focus.ts` (service/utility, event-driven)

**Analog:** none — greenfield.
**Governing contracts:** A3-SPEC GRD-03 (numeric/directional/click/cycle); A3-CONTEXT D-03 (i3 edge-midpoint tie-break).

**Focus operations:**

```
focusByIndex(store, n: number) → void
  // Set focusedId to the pane with index n (1-based geometric).
  // No-op if no pane has that index (n > pane count).

focusByDirection(store, dir: "left" | "right" | "up" | "down") → void
  // i3/sway "nearest to focused pane's edge-midpoint" algorithm (A3-CONTEXT D-03):
  // 1. Compute the focused pane's bounding rect from the tree + window size.
  // 2. Project the relevant edge midpoint (e.g. right edge midpoint for "right").
  // 3. For every other pane, test if it shares an edge in the requested direction.
  // 4. Winner = the candidate whose shared edge is nearest to the projected midpoint.
  // Deterministic from layout geometry alone — no focus-history state.

focusByClick(store, paneId: string) → void
  // Direct set — called from PaneLeaf click handler.

cycleFocus(store, dir: "next" | "prev") → void
  // Move focus to the next/prev pane in geometric index order. Wraps at both ends.
```

---

### `apps/voss-app/src/grid/resize.ts` (service/utility, event-driven)

**Analog:** none — greenfield.
**Governing contracts:** A3-SPEC GRD-04 (drag, keyboard 5%, equalize, 20×5 clamp); A3-UI-SPEC "Drag Handle Contract".

**Resize operations:**

```
resizeByDrag(store, splitNodeId: string, newRatio: number) → void
  // Called continuously during drag. Clamp newRatio so neither child subtree
  // falls below the 20×5 floor. If clamped, stop — cursor stays, no toast.

resizeByKeyboard(store, dir: "left" | "right" | "up" | "down") → void
  // Find the split node bounding the focused pane in the given direction.
  // Adjust its ratio by ±0.05 (5%). Clamp at the 20×5 floor. No-op if no
  // split node exists in that direction from the focused pane.
```

**Mirror sync cadence (A3-CONTEXT "Solid→Rust mirror sync cadence"):**
Keyboard resize: sync Rust mirror after each 5% step.
Drag resize: sync once on drag-end (pointer-up), not on every pointer-move. Coalesce mid-drag.

---

### `apps/voss-app/src/grid/GridRoot.tsx` (component, request-response)

**Analog:** none — greenfield.
**Governing contracts:** A3-UI-SPEC "Grid Layout Architecture" + "Container Hierarchy"; A1-UI-SPEC Token System (Tailwind utility classes).

**Container contract (A3-UI-SPEC verbatim):**

```tsx
// GridRoot fills the window minus the A1 titlebar.
// CSS classes use A1 Tailwind utilities only — no inline hex, no new tokens.

<div class="grid-root bg-bg-0 w-full h-full overflow-hidden">
  {/* Recursive SplitNode renders the tree */}
  <SplitNode node={store.root} ... />
</div>
```

**Keyboard handler registration:** GridRoot is the correct mount point for all global keyboard shortcuts (`⌘1`-`⌘9`, `⌘[`/`⌘]`, `⌘\`, `⌘⇧\`, `⌘D`, `⌘W`, `⌘=`, `⌘⌥`-arrows, `⌘⌥⇧`-arrows). Use `onKeyDown` on the grid container or `window` `keydown` event listener mounted in `onMount` / cleaned up in `onCleanup`.

**Background visibility:** `--bg-0` fills gaps momentarily visible during drag or close animation. Never visible in steady state.

---

### `apps/voss-app/src/grid/SplitNode.tsx` (component, request-response)

**Analog:** none — greenfield.
**Governing contracts:** A3-UI-SPEC "Grid Layout Architecture" + "Split Border + Drag Handle Contract"; A3-SPEC GRD-01 (binary-split tree).

**Render contract:**

```tsx
// SplitNode is recursive. Base case: PaneLeaf wraps the A2 pane component.
// Internal case: renders two children + a DragHandle.

// For a horizontal split (orientation = "H", left = left pane, right = right pane):
<div style={{ display: "flex", flexDirection: "row", width: "100%", height: "100%" }}>
  <div style={{ width: `${ratio * 100}%`, position: "relative" }}>
    <SplitNode node={left} ... />
    {/* 1px right border — using A1 token */}
    {/* border-right: 1px solid var(--border) */}
  </div>
  <DragHandle orientation="H" onDrag={...} />
  <div style={{ width: `${(1 - ratio) * 100}%` }}>
    <SplitNode node={right} ... />
  </div>
</div>

// For a vertical split (orientation = "V", left = top, right = bottom):
// Same structure, flexDirection: "column", heights instead of widths,
// border-bottom instead of border-right.
```

**Leaf case (PaneLeaf):** render the A2 pane component with:
- Focus state: `box-shadow: inset 0 0 0 1px var(--focus)` when `pane.id === store.focusedId`
- Header bg-lift: pass `focused` prop so `PaneHeader` applies `bg-bg-2` vs `bg-bg-1`
- Click handler: call `focusByClick(store, pane.id)`
- `onMount`: pass pixel dimensions to the A2 pane so xterm can size correctly

**Token usage (A3-UI-SPEC "Token Inheritance Contract"):**
Only Tailwind utilities generated by A1: `bg-bg-0`, `bg-bg-1`, `bg-bg-2`, `bg-bg-3`, `border-border`, `border-border-bright`. No `border-radius`. No CSS transitions on focus change (A3-UI-SPEC "Anti-Patterns").

---

### `apps/voss-app/src/grid/DragHandle.tsx` (component, event-driven)

**Analog:** none — greenfield.
**Governing contracts:** A3-UI-SPEC "Drag Handle" subsection; A3-SPEC GRD-04.

**Visual + interaction contract (A3-UI-SPEC verbatim):**

```tsx
// Transparent 6px overlay centered on the 1px split border.
// No visible track, thumb, or glyph — cursor change is the only affordance.

// For a vertical border (H split — left/right panes):
<div
  style={{
    position: "absolute",
    width: "6px",
    top: 0,
    bottom: 0,
    left: "calc(100% - 3px)",   // centered on the 1px right border of the left child
    cursor: "col-resize",
    background: "transparent",
    zIndex: /* above pane content, below ⋯ menu */
  }}
  onPointerDown={startDrag}
/>

// For a horizontal border (V split — top/bottom panes):
// height: "6px", width: "100%", cursor: "row-resize", top: "calc(100% - 3px)"
```

**Hover state (A3-UI-SPEC):** on `onMouseEnter`, change the adjacent border color to `var(--border-bright)` via signal. Instant — no CSS transition.

**Drag behavior:** use `setPointerCapture` on `pointerdown`; compute new ratio from pointer position delta; call `resizeByDrag`; release on `pointerup`. The `resizeByDrag` function handles the 20×5 clamp silently.

---

### `apps/voss-app/src/grid/PaneHeader.tsx` (component, event-driven — ADDITIVE A2 EDIT)

**Analog:** none — greenfield (A2 header not yet written).
**Governing contracts:** A3-UI-SPEC "Pane Header Contract" (GRD-06); A3-SPEC GRD-06; A2-CONTEXT Integration Points ("only additive changes permitted").

**Critical rule:** A3's only permitted changes to the A2 header are adding the index segment and adding the `⋯` menu trigger. All other segments (dot, cwd, shell, process indicator) come from A2 and are consumed unchanged.

**Header layout contract (A3-UI-SPEC verbatim):**

```
[ ● dot ] [ │ ] [ index ] [ │ ] [ cwd basename ] [ │ ] [ shell ] [ │ ] [ process ] [ flex spacer ] [ ⋯ ]
```

**Index segment (A3-UI-SPEC):**
- Content: `1`..`9`+ (numeric digit, computed from geometric position)
- Color (focused): `--fg-1` (`text-fg-1`)
- Color (unfocused): `--fg-3` (`text-fg-3`)
- Font: 10px / weight 400 (metadata role — smaller than 11px header text)
- Width: auto (content-driven, no fixed badge box)

**`⋯` trigger (A3-UI-SPEC):**
- Content: `⋯` (U+22EF)
- Color: `--fg-2` (rest, focused) / `--fg-3` (rest, unfocused) / `--fg-0` (hover)
- Cursor: `default` (not `pointer` — terminal aesthetic)
- `aria-label="Pane menu"` (assistive-only, not rendered)
- Click: toggle `DotMenu` visibility

**Focus state on the header `<div>` (A3-UI-SPEC):**
- Focused: `background: var(--bg-2)` (`bg-bg-2`)
- Unfocused: `background: var(--bg-1)` (`bg-bg-1`)
- Transition: NONE — instant repaint (A3-UI-SPEC "Anti-Patterns: CSS transition on focus change")

**Overflow policy (A3-UI-SPEC):** truncate in this order if pane is narrow:
1. Process indicator (hide first)
2. cwd basename (truncate with `…` from right)
3. Shell name (hide if critically narrow)
4. Index and dot are NEVER truncated

---

### `apps/voss-app/src/grid/DotMenu.tsx` (component, request-response)

**Analog:** none — greenfield.
**Governing contracts:** A3-UI-SPEC "`⋯` Menu Contract" (GRD-06); A3-SPEC GRD-06 boundaries ("exactly 5 items — 4 actions + 1 separator").

**Menu container styling (A3-UI-SPEC verbatim):**

```css
background:    var(--bg-3)          /* bg-bg-3 */
border:        1px solid var(--border)
border-radius: 0px                  /* Variant B absolute rule */
width:         128px (fixed)
box-shadow:    0 4px 12px rgba(0,0,0,0.4)
position:      absolute
top:           22px                 /* flush below the 22px header */
right:         0
z-index:       above pane body, below A1 titlebar
```

**Menu items (A3-UI-SPEC, locked to exactly these 5):**

| Item | Copy | Color | Notes |
|------|------|-------|-------|
| Fork pane | `Fork pane` | `text-fg-0` | `⌘D` shortcut right-aligned in `text-fg-3` 10px |
| Split right | `Split right` | `text-fg-0` | `⌘\` shortcut |
| Split below | `Split below` | `text-fg-0` | `⌘⇧\` shortcut |
| separator | 1px `border-border` | — | `margin: 0`, flush |
| Close pane | `Close pane` | `text-accent-red` | `⌘W` shortcut; destructive |

**Each item:** 22px height, `padding: 0 16px`, `font-family: var(--font-mono)`, 11px/400.
**Hover per item:** `background: var(--bg-2)` (`bg-bg-2`) — neutral lift, no accent.
**Close:** opens `CloseConfirmBanner` if foreground process detected (A2 D-07); else closes immediately.
**Dismiss:** item selection, `Escape`, click outside, or pane blur.

---

### `apps/voss-app/src/grid/CloseConfirmBanner.tsx` (component, event-driven)

**Analog:** none — greenfield.
**Governing contracts:** A3-UI-SPEC "Close Confirm Contract" (GRD-02 + A2 D-07); A3-SPEC GRD-02.

**When shown:** only when `⌘W` / "Close pane" is triggered AND A2 D-07 foreground detection returns a running foreground process other than the bare interactive shell.

**Banner geometry (A3-UI-SPEC verbatim):**

```css
background:    var(--bg-3)
border-bottom: 1px solid var(--border)
height:        22px         /* one-line, matches header height */
padding:       0 10px       /* base token */
font-family:   var(--font-mono)
font-size:     11px
font-weight:   400
/* Positioned: full-width, top of pane body, flush to header bottom edge */
```

**Banner content (A3-UI-SPEC):**

```
[ ● accent-red ] [ "vim" is running. Close anyway? ] [ flex: 1 ] [ Keep open ] [ Close anyway ]
```

**Button styling:** `background: transparent; border: none; padding: 0 8px; cursor: default` — pure text buttons.
- `Keep open`: `text-fg-0`, `Escape` key equivalent, dismisses banner.
- `Close anyway`: `text-accent-red`, `Enter`/`Return` key equivalent, executes close.

**Auto-dismiss:** if the foreground process exits while the banner is showing, dismiss automatically. No timeout auto-dismiss.
**Non-modal:** other keys pass through to the PTY while the banner is visible.

---

### `crates/voss-app-core/src/grid.rs` (model/state, CRUD — Rust mirror)

**Analog:** none — greenfield. `crates/voss-app-core/` has an empty `lib.rs` (A1 D-06 placeholder).
**Governing contracts:** A3-SPEC GRD-08; A1-CONTEXT D-05/D-06/D-09; A3-CONTEXT "Solid→Rust mirror".
**Reference-only idiom (do NOT copy into; do NOT edit the frozen spike):** `crates/voss-agent/src/plan.rs` shows the project's Rust struct idiom: `#[derive(Clone, Debug, Serialize, Deserialize)]`, `serde` field names match the wire protocol, `Option<T>` for optional fields, `#[serde(default)]` for defaultable fields.

**Rust mirror structs required (A3-SPEC GRD-08):**

```rust
// crates/voss-app-core/src/grid.rs
// NO disk I/O in A3 — this is an in-memory mirror only.
// A4 and A6 build file I/O on top of this serializable shape.

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum TreeNode {
    Split(SplitNode),
    Pane(PaneLeaf),
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SplitNode {
    pub orientation: Orientation,   // "H" or "V"
    pub ratio: f32,                 // 0.0–1.0
    pub left: Box<TreeNode>,
    pub right: Box<TreeNode>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Orientation { H, V }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PaneLeaf {
    pub id: String,     // stable UUID matching the Solid store's pane id
    pub cwd: String,
    pub shell: String,
    pub index: u32,     // 1-based geometric index
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GridState {
    pub root: TreeNode,
    pub focused_id: String,
}

// Tauri command (in lib.rs or commands.rs) — exact function signature is planner's call.
// Must satisfy A1-CONTEXT D-09: Rust/Tauri owns state, exposes to webview.
// #[tauri::command]
// pub fn sync_grid(state: tauri::State<Mutex<GridState>>, new_state: GridState) -> Result<(), String>
```

**Serialization contract:** use `serde_json`. Field names must round-trip cleanly with the Solid TypeScript types (use `rename_all = "camelCase"` or align field names to TypeScript — planner's call, must be consistent).

**A4/A6 forward-compatibility note:** keep `GridState` `Serialize`/`Deserialize` clean with no non-serializable fields. A4 will add `name: Option<String>` to `GridState`; A6 will serialize the whole struct to `session.json`. Do not add any `#[serde(skip)]` fields that A4/A6 would need.

---

## Shared Patterns

### Token Usage (all Solid components)
**Source:** A1-UI-SPEC.md, A3-UI-SPEC.md "Token Inheritance Contract"
**Apply to:** `GridRoot.tsx`, `SplitNode.tsx`, `DragHandle.tsx`, `PaneHeader.tsx`, `DotMenu.tsx`, `CloseConfirmBanner.tsx`

```
RULE: Only use Tailwind utility classes generated by A1's @theme inline block.
NEVER use inline style="color: #..." (except in the existing applyThemeOverrides function).
NEVER add new entries to tailwind.config or @theme (Tailwind v4 uses @theme inline only).

Available utilities (from A1-UI-SPEC CSS Variable to Tailwind Mapping Contract):
  bg-bg-0, bg-bg-1, bg-bg-2, bg-bg-3
  border-border, border-border-bright
  text-fg-0, text-fg-1, text-fg-2, text-fg-3
  text-accent-green, text-accent-red
  shadow-[inset_0_0_0_1px_var(--focus)]   ← focused pane container only
  font-mono
```

### No-Rounding Rule (all A3 components)
**Source:** A1-UI-SPEC "Named Spacing Exceptions" + A3-UI-SPEC "Anti-Patterns"
**Apply to:** every component in `apps/voss-app/src/grid/`

```
border-radius: 0px everywhere in A3 grid chrome.
The ONLY carve-outs (inherited from A1, not added in A3):
  - macOS traffic-light circles: border-radius: 50% (A1 component)
  - Scrollbar thumb: border-radius: 4px (global CSS, A1)
No new exceptions in A3.
```

### No-Transition Rule (all A3 components)
**Source:** A3-UI-SPEC "Performance + Visual Budget" + "Anti-Patterns"
**Apply to:** every component in `apps/voss-app/src/grid/`

```
No CSS transition or animation on any of:
  - box-shadow (focus change)
  - background-color (header bg-lift on focus)
  - border-color (drag handle hover)
  - ⋯ menu open/close (instant appear)
Instant repaint only. This enforces the 60fps budget and the Variant B density aesthetic.
```

### Tauri Command/State Seam (Solid → Rust)
**Source:** A1-CONTEXT D-09; A3-CONTEXT "Solid→Rust mirror sync cadence"
**Apply to:** any Solid code that calls `sync_grid` and `crates/voss-app-core/src/grid.rs`

```typescript
// Solid side — call after each structural tree change:
import { invoke } from "@tauri-apps/api/core";

async function syncGridToRust(newState: GridState): Promise<void> {
  await invoke("sync_grid", { newState });
  // No return value consumed in A3 (no disk I/O, no read-back needed).
}

// Debounce rule (A3-CONTEXT):
// - Structural changes (split/fork/close/focus/equalize): sync immediately.
// - Drag resize: sync once on pointer-up, not on every pointer-move.
```

### 20×5 Floor Guard (all mutation operations)
**Source:** A3-SPEC GRD-05; A3-UI-SPEC "Error state: silent no-op"
**Apply to:** `operations.ts` (split/fork), `resize.ts` (drag/keyboard)

```
Before ANY tree mutation that changes pane geometry:
1. Compute the resulting pixel dimensions of every affected pane
   given current window width/height (minus 22px header per pane).
2. If any pane would be < (20 cols × charWidth) OR < (5 rows × charHeight + 22px):
   → RETURN EARLY. No mutation. No toast. No banner. No error.
   → Cursor stays in place during drag (movement rejected silently).
Columns/rows derived from pane pixel size using xterm.js character cell dimensions.
```

### A2 Foreground Detection Reuse
**Source:** A2-CONTEXT D-07; A3-SPEC GRD-02; A3-UI-SPEC "Close Confirm Contract"
**Apply to:** close path in `operations.ts` + `CloseConfirmBanner.tsx`

```
Foreground detection is A2's responsibility and is consumed as a black box by A3.
A3 calls A2's detection API (exposed by the pane component or via Tauri command —
exact interface is A2's to define) to determine:
  "Is there a foreground process other than the bare interactive shell?"
  → Yes: show CloseConfirmBanner before executing closeFocused()
  → No: execute closeFocused() immediately, no confirm

Detection algorithm (A2 D-07, for awareness only — A3 does not reimplement):
  Primary: OSC 0 / OSC 2 title sequence
  Fallback: poll PTY foreground process group (tcgetpgrp + libproc/procfs)
```

---

## No Analog Found

All A3 files have no close in-repo match. The full list:

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `apps/voss-app/src/grid/tree.ts` | model/store | event-driven | No Solid signal store exists anywhere in repo |
| `apps/voss-app/src/grid/operations.ts` | service | transform | No tree mutation service exists in repo |
| `apps/voss-app/src/grid/focus.ts` | service | event-driven | No focus management exists in repo |
| `apps/voss-app/src/grid/resize.ts` | service | event-driven | No resize logic exists in repo |
| `apps/voss-app/src/grid/GridRoot.tsx` | component | request-response | No Solid components exist in repo |
| `apps/voss-app/src/grid/SplitNode.tsx` | component | request-response | No Solid components exist in repo |
| `apps/voss-app/src/grid/DragHandle.tsx` | component | event-driven | No Solid components exist in repo |
| `apps/voss-app/src/grid/PaneHeader.tsx` | component | event-driven | No Solid components exist in repo; A2 header is planned but not written |
| `apps/voss-app/src/grid/DotMenu.tsx` | component | request-response | No Solid components exist in repo |
| `apps/voss-app/src/grid/CloseConfirmBanner.tsx` | component | event-driven | No Solid components exist in repo |
| `crates/voss-app-core/src/grid.rs` | model/state | CRUD | `voss-app-core` has only an empty `lib.rs` placeholder; frozen spike is reference-only |

The frozen `crates/voss-agent/src/plan.rs` (struct idiom: `#[derive(Clone, Debug, Serialize, Deserialize)]`, serde field mapping) is the single closest reference for Rust struct style, but it is **reference-only — do not edit, do not copy file structure directly**. It informs the derive macro and serde attribute pattern only.

---

## Metadata

**Analog search scope:** `apps/voss-app/`, `crates/voss-app-core/`, `crates/voss-agent/src/`, `crates/voss-cli/src/`, `crates/voss-render/src/`
**Files scanned:** 2 documentation files in `apps/voss-app/`; ~25 frozen Rust spike source files (reference-only, not editing targets)
**Pattern extraction date:** 2026-05-18

**Governing contract files (planner MUST read):**
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/A3-voss-app-grid-engine/A3-SPEC.md` — locked requirements GRD-01..08
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md` — D-01..D-04, integration points
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md` — full visual + interaction contract
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md` — token system A3 consumes verbatim
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/A2-voss-app-pty-pane/A2-CONTEXT.md` — A2 pane boundary, D-07 foreground detection
