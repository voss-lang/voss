---
phase: A3-voss-app-grid-engine
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/src/grid/tree.ts
  - apps/voss-app/src/grid/sync.ts
  - apps/voss-app/src/grid/__tests__/tree.test.ts
  - crates/voss-app-core/src/grid.rs
  - crates/voss-app-core/src/lib.rs
  - crates/voss-app-core/Cargo.toml
autonomous: true
requirements: [GRD-01, GRD-08]
must_haves:
  truths:
    - "A binary-split tree data shape holds 1..N pane leaves with H/V split internal nodes and per-split ratios"
    - "Pane indices are stable geometric positions (left-to-right, top-to-bottom inorder), recomputed with no gaps on structural change"
    - "After a structural change the voss-app-core Rust mirror holds a structure matching the Solid tree"
    - "No file is created under .voss/ or elsewhere by the mirror sync path"
  artifacts:
    - path: "apps/voss-app/src/grid/tree.ts"
      provides: "TreeNode/SplitNode/PaneLeaf/GridStore types + Solid store factory + index recompute"
      contains: "createGridStore"
    - path: "apps/voss-app/src/grid/sync.ts"
      provides: "syncGridToRust debounced bridge over the A1 D-09 Tauri seam"
      contains: "sync_grid"
    - path: "crates/voss-app-core/src/grid.rs"
      provides: "Rust mirror structs + sync_grid Tauri command, in-memory only"
      contains: "pub fn sync_grid"
    - path: "apps/voss-app/src/grid/__tests__/tree.test.ts"
      provides: "Vitest coverage of tree shape + index recompute determinism"
      contains: "recomputeIndices"
  key_links:
    - from: "apps/voss-app/src/grid/sync.ts"
      to: "crates/voss-app-core/src/grid.rs"
      via: "invoke('sync_grid', { newState })"
      pattern: "invoke\\(['\"]sync_grid['\"]"
    - from: "crates/voss-app-core/src/lib.rs"
      to: "crates/voss-app-core/src/grid.rs"
      via: "mod grid + re-export"
      pattern: "mod grid"
---

<objective>
Establish the A3 binary-split pane-tree data model as the Solid source of truth and its
in-memory Rust mirror in `voss-app-core`, plus the Tauri sync seam connecting them.

Purpose: Every other A3 plan (operations, focus, resize, render, chrome) builds against
these exact contracts. Defining them first removes the scavenger-hunt anti-pattern — all
downstream executors receive the tree shape and sync signature in their plans.

Output: `tree.ts` (typed Solid store + geometric index recompute), `sync.ts` (debounced
Solid→Rust bridge), `crates/voss-app-core/src/grid.rs` (mirror structs + `sync_grid`
command), wired into `lib.rs`. Implements GRD-01 (binary-split tree model) and the
structural half of GRD-08 (Solid SSOT mirrored to Rust, no disk I/O).
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
<!-- A1 D-09 seam (assumed-present upstream contract — DO NOT re-plan A1). -->
<!-- A1 created crates/voss-app-core as a workspace member with an empty lib.rs; -->
<!-- src-tauri already declares the voss-app-core path dependency. A3 fills the crate body. -->
<!-- Rust/Tauri owns state and exposes it to the Solid webview via #[tauri::command]. -->

Tree data shape (A3-PATTERNS "tree.ts" — REQUIRED fields, exact names):
  SplitNode { kind: "split"; orientation: "H" | "V"; ratio: number; left: TreeNode; right: TreeNode }
  PaneLeaf  { kind: "pane"; id: string; cwd: string; shell: string; index: number }
  TreeNode  = SplitNode | PaneLeaf
  GridStore { root: TreeNode; focusedId: string }
  // orientation "H" = side-by-side (⌘\); "V" = stacked (⌘⇧\). ratio 0.0–1.0.

Rust mirror idiom (A3-PATTERNS — reference-only, from frozen crates/voss-agent/src/plan.rs;
DO NOT edit or copy the spike): #[derive(Clone, Debug, Serialize, Deserialize)],
#[serde(tag = "kind")] discriminated enum, Box<TreeNode> for recursion, serde field names
aligned to the TS types (planner's call — use camelCase via rename_all for clean round-trip).
</interfaces>

@.planning/phases/A3-voss-app-grid-engine/A3-SPEC.md
@.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md
@.planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: TypeScript tree model + Solid store + geometric index recompute</name>
  <files>apps/voss-app/src/grid/tree.ts, apps/voss-app/src/grid/__tests__/tree.test.ts</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### apps/voss-app/src/grid/tree.ts" — data shape contract, 50/50 insertion contract, index recompute contract (governing contract; no code analog exists — greenfield)
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md "## Requirements" GRD-01 + GRD-08 (locked WHAT)
    - .planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md "### Split & Equalize Geometry" D-02 + "Claude's / Planner's Discretion" (index recompute = geometric, no sparse indices)
    - apps/voss-app/src/pane/PaneComponent.tsx — A2 pane unit (consumed as a black box; read only its export signature, do NOT modify in this plan)
  </read_first>
  <behavior>
    - A single PaneLeaf root has index 1 after recomputeIndices.
    - A 2x2 tree built from 3 splits assigns indices 1..4 in inorder (left-to-right, top-to-bottom) traversal order with no gaps.
    - Removing the index-2 leaf and recomputing renumbers remaining leaves 1..3 contiguously (no sparse/gap indices).
    - createGridStore() returns a Solid store whose root is a single default PaneLeaf and whose focusedId equals that leaf's id.
    - A new SplitNode created by the model always has ratio === 0.5.
    - equalizeRatios walks the whole tree and sets every SplitNode.ratio to 0.5 recursively (no node missed at any depth).
  </behavior>
  <action>
    Create `apps/voss-app/src/grid/tree.ts` exporting the discriminated-union types
    `SplitNode`, `PaneLeaf`, `TreeNode`, `GridStore` with the EXACT field names from the
    `<interfaces>` block (GRD-01). Export `createGridStore()` using Solid `createStore`
    (from `solid-js/store`) — root = one default `PaneLeaf` (fresh UUID via
    `crypto.randomUUID()`, cwd/shell from caller-supplied defaults or empty string
    placeholders the render layer fills), `focusedId` = that leaf id. Export
    `recomputeIndices(root: TreeNode): void` performing an inorder traversal (left/top
    subtree, then right/bottom) assigning 1-based `index` to each `PaneLeaf` in encounter
    order — implements the A3-CONTEXT "stable left-to-right, top-to-bottom, no gaps"
    discretion lock. Export `equalizeRatios(root: TreeNode): void` (recursive, every
    SplitNode.ratio = 0.5 per D-02). Export pure helpers `findLeaf(root, id)`,
    `collectLeaves(root): PaneLeaf[]` (inorder), and `makeSplit(orientation, left, right):
    SplitNode` (always `ratio: 0.5`, D-02). No rendering, no Tauri calls, no DOM in this
    file — pure model. Author `apps/voss-app/src/grid/__tests__/tree.test.ts` (Vitest)
    covering every behavior listed above; build the 2x2 and a ≥6-pane asymmetric tree as
    fixtures (mirrors A3-SPEC acceptance criteria 1 + 2 at the model level).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run tree --reporter=dot 2>&1 | tail -12 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'createGridStore' src/grid/tree.ts && grep -q 'recomputeIndices' src/grid/tree.ts && grep -Eq 'ratio:\s*0\.5' src/grid/tree.ts && echo TREE_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src/grid/tree.ts` exports `createGridStore`, `recomputeIndices`, `equalizeRatios`, `findLeaf`, `collectLeaves`, `makeSplit`.
    - `pnpm vitest run tree` exits 0 with all behavior cases green.
    - `pnpm exec tsc --noEmit` exits 0 (types compile against the A3 contract).
    - Building a 2×2 tree (3 splits) and calling `recomputeIndices` yields leaves with indices exactly `[1,2,3,4]` in inorder; no gaps after a mid-tree removal.
    - Every SplitNode produced by `makeSplit` has `ratio === 0.5` (source assertion: `grep -Eq 'ratio:\s*0\.5'`).
    - tree.ts contains no `invoke(` and no DOM/JSX (pure model — behavior assertion).
  </acceptance_criteria>
  <done>Typed Solid tree model + geometric index recompute exist and are unit-tested green; types compile.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rust mirror structs + sync_grid Tauri command in voss-app-core</name>
  <files>crates/voss-app-core/src/grid.rs, crates/voss-app-core/src/lib.rs, crates/voss-app-core/Cargo.toml</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### crates/voss-app-core/src/grid.rs" — Rust struct contract, serialization contract, A4/A6 forward-compat note (governing contract)
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-08 (no disk I/O; mirror matches after every structural change)
    - .planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md D-05/D-06/D-09 (voss-app-core is a workspace member with empty lib.rs; src-tauri path-dep wired; Rust owns state, exposes via Tauri command)
    - crates/voss-app-core/src/lib.rs — current empty placeholder (A1 D-06; confirm it compiles clean before editing)
  </read_first>
  <behavior>
    - GridState round-trips through serde_json: a deserialized-then-reserialized 2x2 GridState equals the original JSON shape.
    - sync_grid replaces the in-memory GridState held behind a Mutex with the payload and returns Ok(()).
    - sync_grid performs no filesystem access (no std::fs, no File, no path writes anywhere in grid.rs).
    - The TreeNode enum tag field name and PaneLeaf/SplitNode field names round-trip cleanly with the tree.ts TypeScript field names.
  </behavior>
  <action>
    Create `crates/voss-app-core/src/grid.rs` with `#[derive(Clone, Debug, Serialize,
    Deserialize)]` on `TreeNode` (serde `#[serde(tag = "kind", rename_all =
    "camelCase")]` enum: `Split(SplitNode)` / `Pane(PaneLeaf)`), `SplitNode`
    (`orientation: Orientation`, `ratio: f32`, `left: Box<TreeNode>`, `right:
    Box<TreeNode>`), `Orientation` enum (`H`/`V`), `PaneLeaf` (`id: String`, `cwd:
    String`, `shell: String`, `index: u32`), and `GridState { root: TreeNode, focused_id:
    String }` (per A3-PATTERNS, GRD-08). Align serde rename so the JSON keys exactly match
    the `tree.ts` field names (`focusedId`, `orientation`, `ratio`, `left`, `right`,
    `id`, `cwd`, `shell`, `index`, `kind`) — pick `rename_all = "camelCase"` consistently
    and document the choice in a top-of-file comment. Add `#[tauri::command] pub fn
    sync_grid(state: tauri::State<'_, std::sync::Mutex<GridState>>, new_state: GridState)
    -> Result<(), String>` that locks the mutex and overwrites the held state — in-memory
    only, NO `std::fs`, NO file path (GRD-08, A3-SPEC "no file is created under .voss/").
    Per the A3-PATTERNS A4/A6 forward-compat note: keep `GridState` Serialize/Deserialize
    clean with NO `#[serde(skip)]` fields. In `lib.rs` add `pub mod grid;` and re-export
    `grid::{GridState, sync_grid}`. Add `serde` (with `derive`), `serde_json`, and the
    `tauri` dependency to `crates/voss-app-core/Cargo.toml` if not already present
    (workspace-inherited versions if the root workspace pins them). Add a `#[cfg(test)]`
    module proving the serde round-trip behavior above (`cargo test`). Do NOT edit any
    frozen `crates/voss-agent|voss-cli|voss-render|...` spike crate — reference idiom only.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core grid 2>&1 | tail -15 && cargo build -p voss-app-core 2>&1 | tail -5 && grep -q 'pub fn sync_grid' crates/voss-app-core/src/grid.rs && grep -q 'mod grid' crates/voss-app-core/src/lib.rs && ! grep -nE 'std::fs|File::|fs::write|\.voss' crates/voss-app-core/src/grid.rs && echo MIRROR_OK</automated>
  </verify>
  <acceptance_criteria>
    - `crates/voss-app-core/src/grid.rs` exports `GridState` and `#[tauri::command] pub fn sync_grid` (source assertion: `grep -q 'pub fn sync_grid'`).
    - `cargo build -p voss-app-core` and `cargo test -p voss-app-core grid` exit 0.
    - `grid.rs` contains no `std::fs`, `File::`, `fs::write`, or `.voss` literal anywhere (behavior assertion: GRD-08 no disk I/O — `! grep -nE 'std::fs|File::|fs::write|\.voss'`).
    - `lib.rs` declares `mod grid` and re-exports `GridState`, `sync_grid`.
    - serde round-trip test green: a 2×2 `GridState` serialized then deserialized is structurally equal.
  </acceptance_criteria>
  <done>Rust mirror structs + in-memory `sync_grid` command exist, round-trip-tested green, with zero filesystem access.</done>
</task>

<task type="auto">
  <name>Task 3: Solid→Rust sync bridge (debounced, structural-immediate / drag-coalesced)</name>
  <files>apps/voss-app/src/grid/sync.ts, apps/voss-app/src/grid/__tests__/tree.test.ts</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### Tauri Command/State Seam (Solid → Rust)" — invoke shape + debounce rule (governing contract)
    - .planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md "Claude's / Planner's Discretion" — mirror sync cadence (structural immediate; drag once on drag-end)
    - apps/voss-app/src/grid/tree.ts — the GridStore shape this bridge serializes (from Task 1)
    - apps/voss-app/src/pane/pty-ipc.ts — A2's existing `invoke` usage convention (read for the import path `@tauri-apps/api/core`; do NOT modify)
  </read_first>
  <action>
    Create `apps/voss-app/src/grid/sync.ts` exporting `syncGridToRust(state: GridStore):
    Promise<void>` that calls `invoke('sync_grid', { newState: serialize(state) })` from
    `@tauri-apps/api/core` — `serialize` deep-clones the reactive store into a plain
    structural object (strip Solid proxies) matching the Rust `GridState` JSON keys
    (A3-PATTERNS seam contract, GRD-08). Export `markStructuralChange(state)` (fires
    `syncGridToRust` immediately — used by split/fork/close/focus/equalize) and
    `markDragSettled(state)` (the drag-end sync site) plus an internal coalescer so
    repeated drag-move calls do NOT invoke during the drag (A3-CONTEXT cadence
    discretion: structural = immediate, drag = once on pointer-up). No return value is
    consumed (A3 has no read-back, no disk I/O). Add Vitest cases to
    `apps/voss-app/src/grid/__tests__/tree.test.ts` (or a co-located block) that mock
    `@tauri-apps/api/core` `invoke` and assert: (a) `markStructuralChange` triggers
    exactly one `invoke('sync_grid', …)` synchronously; (b) N rapid drag-move calls
    followed by one `markDragSettled` produce exactly one `invoke` call total; (c) the
    payload key set matches the Rust field names (`root`, `focusedId`).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run tree --reporter=dot 2>&1 | tail -12 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -Eq "invoke\(['\"]sync_grid['\"]" src/grid/sync.ts && grep -q 'markStructuralChange' src/grid/sync.ts && grep -q 'markDragSettled' src/grid/sync.ts && echo SYNC_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src/grid/sync.ts` exports `syncGridToRust`, `markStructuralChange`, `markDragSettled` and calls `invoke('sync_grid', ...)` (source assertion).
    - `pnpm vitest run tree` exits 0 including the three sync mock cases.
    - Behavior assertion: a structural change triggers exactly one `invoke('sync_grid')`; N drag-move calls + one settle produce exactly one `invoke` total (drag coalesced per A3-CONTEXT cadence).
    - Payload key set is `{ root, focusedId }` — matches Rust `GridState` camelCase keys (round-trip safety).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>Debounced Solid→Rust sync bridge exists; structural changes sync immediately, drag coalesces to one sync on settle; mock-tested green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Solid webview → Tauri command (`sync_grid`) | Tree-state payload crosses from the sandboxed webview into native Rust state |
| Rust in-memory state | `voss-app-core` holds the authoritative mirror; A4/A6 later persist it |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A3-01 | Tampering | `sync_grid` Tauri command payload | mitigate | `GridState` is a closed serde-typed struct (no free-form/path/command fields); serde rejects unknown shapes at the boundary. No `cwd`/`shell` value is executed or used as a filesystem path in this plan — it is opaque display metadata stored in memory only. |
| T-A3-02 | Information Disclosure / Tampering | Disk write via mirror | mitigate | `grid.rs` is grep-gated against `std::fs`/`File::`/`fs::write`/`.voss` (GRD-08 no-disk-I/O — enforced in Task 2 verify). The mirror is in-memory only; A4/A6 own all file I/O. |
| T-A3-03 | Denial of Service | Unbounded recursive `TreeNode` from a hostile payload | accept | A3 is a local single-user desktop app; the only `sync_grid` caller is this app's own Solid store, itself bounded by the 20×5 floor + 9-pane design ceiling (enforced in A3-02/03/04). No remote/network input path exists. Documented as accepted for the local-desktop threat model. |
| T-A3-SC | Tampering | npm/cargo installs | accept | This plan adds NO new npm package. Rust deps (`serde`, `serde_json`, `tauri`) are workspace-pinned and already present from A1/A2 (Cargo workspace). No new third-party dependency is introduced — no legitimacy gate required. |
</threat_model>

<verification>
- `pnpm vitest run tree` green; `pnpm exec tsc --noEmit` exits 0.
- `cargo test -p voss-app-core grid` + `cargo build -p voss-app-core` exit 0.
- `grid.rs` has zero filesystem access tokens (GRD-08 disk-I/O gate).
- Tree shape, geometric index recompute, and the Solid→Rust seam exist as the contracts every downstream A3 plan consumes.
</verification>

<success_criteria>
- GRD-01: a binary-split tree data model (H/V splits + ratio, pane leaves) exists with deterministic geometric indexing.
- GRD-08 (structural half): Solid store is SSOT, mirrored into `voss-app-core` via `sync_grid`, in-memory only, zero disk I/O.
- Contracts (`tree.ts` types, `sync.ts` bridge, `grid.rs` structs/command) are defined and tested for downstream plans to build against.
</success_criteria>

<output>
Create `.planning/phases/A3-voss-app-grid-engine/A3-01-SUMMARY.md` when done.
</output>
