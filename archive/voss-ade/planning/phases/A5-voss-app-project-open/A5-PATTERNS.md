# Phase A5: voss-app Project Open — Pattern Map

**Mapped:** 2026-05-19
**Files analyzed:** 13 (per CONTEXT D-01..D-13)
**Analogs found:** 13 / 13 (every A5 area has a strong in-repo precedent — no "no-analog" gaps)

A5 is almost entirely **a parallel rail next to A4** (layout persistence): the same Rust-module → app-Tauri-wrapper → frontend `invoke()` bridge → App.tsx closure stack, plus one new conditional render branch in `App.tsx` and one new `Titlebar` prop. Treat A4 as the reference implementation.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `crates/voss-app-core/src/project.rs` (NEW) | core module (model + I/O + validation) | request-response + file-I/O | `crates/voss-app-core/src/layouts.rs` | exact |
| `crates/voss-app-core/src/lib.rs` | module export | config | same file, lines 3-11 (module pub use block) | exact |
| `crates/voss-app-core/Cargo.toml` | dependency manifest | config | same file lines 12-23 (workspace deps inheritance) | exact |
| `apps/voss-app/src-tauri/Cargo.toml` | dependency manifest | config | same file line 17 (`tauri-plugin-os = "2.3.2"`) | exact |
| `apps/voss-app/src-tauri/src/lib.rs` (modify) | Tauri command wrappers + plugin registration | request-response | same file lines 166-197 (A4 layout wrappers) + line 202 (plugin builder) | exact |
| `apps/voss-app/src-tauri/capabilities/default.json` | capability config | config | same file lines 5-12 (permission list) | exact |
| `apps/voss-app/src/App.tsx` (modify) | composition root + project signal + setup branch | event-driven (signal) | same file lines 38-39 (`activeLayout` signal), 71-79 (`applyDefaultLayout` closure), 86-111 (Titlebar+GridRoot composition) | exact |
| `apps/voss-app/src/components/titlebar/Titlebar.tsx` (modify) | presentational component, accept `projectName` prop | request-response | same file lines 17-22 (optional prop pattern), 60 (hardcoded `Voss ADE` site) | exact |
| `apps/voss-app/src/components/setup/SetupWindow.tsx` (NEW) | presentational Solid component | request-response | `apps/voss-app/src/components/titlebar/PresetSwitcher.tsx` (controlled component, tokens-only, no local state) | role-match |
| `apps/voss-app/src/project/projectStorage.ts` (NEW) | Tauri `invoke()` wrappers + UI-SPEC copy constants | request-response | `apps/voss-app/src/grid/layoutStorage.ts` | exact |
| `apps/voss-app/src/project/__tests__/projectStorage.test.ts` (NEW) | vitest unit (mocked `invoke`) | test | `apps/voss-app/src/grid/__tests__/layoutStorage.test.ts` | exact |
| `apps/voss-app/src/project/__tests__/SetupWindow.test.tsx` (NEW) | vitest DOM render | test | `apps/voss-app/src/components/titlebar/__tests__/PresetSwitcher.test.tsx` | exact |
| `apps/voss-app/src/grid/operations.ts` (maybe) | grid mutator — accept resolved cwd | event-driven | same file lines 117-127 (`forkFocused` — cwd already threaded via `old.cwd`) | exact |
| `apps/voss-app/src/grid/GridRoot.tsx` (maybe) | grid container — accept `projectCwd` prop | event-driven | same file lines 97-103 (props bag with optional `activeLayout` getter) | exact |

---

## Pattern Assignments

### `crates/voss-app-core/src/project.rs` (NEW) — core module

**Analog:** `crates/voss-app-core/src/layouts.rs` (456 lines, the freshest A4-03 example of the full Rust pattern).

**Module header pattern** (`layouts.rs` lines 1-17): doc comment names the contract (what it owns, what it does not), references CONCEPT/SPEC clauses, and explicitly calls out the **lazy `.voss/` rule**. A5's `project.rs` header must call out the symmetric rule: *open_project never touches `<workspace>/.voss/`*.

**Imports** (`layouts.rs` lines 19-23):
```rust
use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};
use crate::grid::GridState;  // — A5: omit; project.rs has no grid dep
```
A5 adds: `use std::fs;` and (D-08) `use git2;`. Use `dirs::home_dir()` only inside the `default_cwd` helper (matches `lib.rs:25`).

**Typed error pattern** (`layouts.rs` lines 53-69):
```rust
#[derive(Debug, thiserror::Error)]
pub enum LayoutError {
    #[error("layout name cannot contain /, \\ or ..")]
    InvalidName,
    #[error("layout not found")]
    NotFound,
    // …
}
```
A5: `ProjectError { NotADirectory, CanonicalizeFailed, RecentsReadFailed, RecentsWriteFailed }`. Display strings must match A5-UI-SPEC copy verbatim (the post-test in `layouts.rs:430-455` is the contract — A5 mirrors it).

**Versioned on-disk schema** (`layouts.rs` lines 25-50):
```rust
pub const CURRENT_LAYOUT_VERSION: u32 = 1;
#[derive(…)]
#[serde(rename_all = "camelCase")]
pub struct LayoutFile { pub version: u32, /* … */ }
```
A5: `pub const CURRENT_RECENTS_VERSION: u32 = 1;` and `pub struct RecentsFile { pub version: u32, pub recents: Vec<String> }`. Bump version on shape change (CONTEXT D-09).

**Fail-safe load pattern** (`layouts.rs` lines 181-208 — `load_default_layout`): missing → `Ok(None)`, corrupt JSON → log to stderr and return `Ok(None)` (never bubble to UI). A5's `load_recents` returns `Vec<String>` (empty on any error) per CONTEXT D-10.

**Atomic-ish write pattern** (NEW for A5; not in `layouts.rs`): A5 D-10 specifies tmp-file + rename. The closest in-repo idiom is `layouts.rs:113-133` (write JSON to a path, log errors to stderr, never panic). A5 extends with:
```rust
let tmp = path.with_extension("json.tmp");
std::fs::write(&tmp, json).map_err(/* log + ProjectError::RecentsWriteFailed */)?;
std::fs::rename(&tmp, &path).map_err(/* same */)?;
```

**Recents-dedup semantics** (CONTEXT D-09): the closest in-repo precedent for "move to front + cap" is none — this is genuinely new logic, but extremely small (~10 lines). Keep it inline in `open_project`:
```rust
fn promote(recents: &mut Vec<String>, path: &str, cap: usize) {
    recents.retain(|p| p != path);
    recents.insert(0, path.to_string());
    recents.truncate(cap);
}
```

**Git branch read (D-08)**: no in-repo analog yet (A5 introduces `git2`). Pattern:
```rust
fn read_git_branch(path: &Path) -> Option<String> {
    let repo = git2::Repository::discover(path).ok()?;
    let head = repo.head().ok()?;
    head.shorthand().map(|s| s.to_string())
}
```
Detached HEAD, bare repos, non-git directories → `None` (no error bubble). Matches `load_default_layout`'s fail-safe-by-default posture.

**Tests pattern** (`layouts.rs` lines 226-456):
- Uses `tempfile::tempdir()` for filesystem tests (already a workspace dev-dep — `Cargo.toml:55`).
- `#[cfg(test)] mod tests { … }` at the bottom of the file (not in a separate `tests.rs`).
- One test per Ok-path round-trip, one per each error variant, one explicit test for **`.voss/` non-existence after read-only ops** (`layouts.rs:330-344` — the canonical lazy-creation assertion A5 must clone with `<temp>/.voss/` for the open_project read-only proof, SPEC requirement 6).
- One test asserting Display strings match UI-SPEC copy verbatim (`layouts.rs:430-455`).

---

### `crates/voss-app-core/src/lib.rs` — module export

**Analog:** same file, lines 3-11.

**Pattern** (lines 3-11):
```rust
pub mod grid;
pub mod layouts;
pub mod pty;

pub use grid::{sync_grid, GridState};
pub use layouts::{
    load_default_layout, load_layout, save_layout, list_layouts,
    validate_layout_name, LayoutError, LayoutFile, CURRENT_LAYOUT_VERSION,
};
```
A5 adds `pub mod project;` and `pub use project::{open_project, load_recents, default_cwd, ProjectInfo, ProjectError, RecentsFile, CURRENT_RECENTS_VERSION};`. Order modules alphabetically (existing convention).

---

### `crates/voss-app-core/Cargo.toml` — dependency manifest

**Analog:** same file, lines 12-23. Workspace-managed deps inherit via `{ workspace = true }`; explicit deps (Tauri-specific, native-only) are pinned literally.

**Pattern to extend** (line 21 area — append):
```toml
git2 = { version = "0.18", default-features = false, features = ["vendored-openssl"] }
dirs = { workspace = true }
```
`git2` is NOT in `[workspace.dependencies]` (workspace Cargo.toml lines 29-50 confirmed — no git2). Pin it locally with `default-features = false` to avoid pulling system openssl on macOS dev machines. `dirs` IS workspace-managed (workspace Cargo.toml:41) — inherit.

**Landmine:** `voss-app-core/Cargo.toml` does not currently depend on `dirs`. The app crate does (`apps/voss-app/src-tauri/Cargo.toml:20`). If `default_cwd()` lives in `voss-app-core`, the dep must be added there.

---

### `apps/voss-app/src-tauri/Cargo.toml` — add `tauri-plugin-dialog`

**Analog:** same file, line 17 (`tauri-plugin-os = "2.3.2"`).

**Pattern** (line 17, replicate adjacently):
```toml
tauri-plugin-dialog = "2"
```
Pin to a `2.x` minor matching the other Tauri 2 plugin (look up the exact patch via `cargo add` or context7 if needed — do not guess). No feature flags required for `open({directory: true})`.

---

### `apps/voss-app/src-tauri/src/lib.rs` — plugin registration + project commands

**Analog:** same file. Two adjacent patterns to clone.

**Plugin registration pattern** (line 202):
```rust
tauri::Builder::default()
    .plugin(tauri_plugin_os::init())  // existing
    .plugin(tauri_plugin_dialog::init())  // A5: add this line
```

**Cross-crate Tauri command wrapper pattern** (lines 154-197 — the A4-03 layouts block). This is the **exact** pattern A5 must clone for `open_project`, `load_recents`, `default_cwd`. The header comment at lines 154-164 documents *why* wrappers live here (cross-crate `generate_handler!` constraint) — A5's project commands inherit the same constraint and the same comment style.

**Concrete wrapper template** (lines 166-174):
```rust
#[tauri::command]
fn save_layout(
    workspace_path: String,
    name: String,
    layout: LayoutFile,
) -> Result<(), String> {
    layouts::save_layout(Path::new(&workspace_path), &name, &layout)
        .map_err(|e| e.to_string())
}
```
A5:
```rust
#[tauri::command]
fn open_project(path: String) -> Result<ProjectInfo, String> {
    project::open_project(Path::new(&path)).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_recents() -> Vec<String> {
    project::load_recents()  // returns Vec<String> directly — no Result wrapper (D-10 best-effort)
}

#[tauri::command]
fn default_cwd(project_path: Option<String>) -> String {
    project::default_cwd(project_path.as_deref().map(Path::new))
}
```

**Handler registry pattern** (lines 205-220):
```rust
.invoke_handler(tauri::generate_handler![
    get_theme_overrides,
    spawn_pty, …, save_layout, load_layout, list_layouts, load_default_layout,
])
```
A5 appends `open_project, load_recents, default_cwd` inside the macro. Order: keep grouping (PTY block, grid block, layouts block, project block).

**Settings path idiom** (lines 18-30 — `settings_path()`):
```rust
fn settings_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("settings.json")
}
```
**A5 contract: reuse this idiom verbatim** for `recents_path()` (CONTEXT D-09 — `~/.config/voss-app/recents.json`). The inline NOTE comment at lines 19-24 (why NOT `dirs::config_dir()`) MUST be preserved in `recents_path` too — the `~/Library/Application Support` divergence is real and locked by A1 D-08.

---

### `apps/voss-app/src-tauri/capabilities/default.json` — allow dialog permission

**Analog:** same file, lines 5-12 (existing permission array).

**Pattern**: append `"dialog:default"` to the `"permissions"` array. Note: Tauri 2 plugin permissions are usually `<plugin>:default` (allow all default commands). Verify via context7 / `tauri-plugin-dialog` docs before final value — the in-repo convention (line 6 `"core:default"`) supports this guess but should be confirmed at plan time.

---

### `apps/voss-app/src/App.tsx` — project signal + setup branch

**Analog:** same file (entire 112-line file).

**Signal-ownership pattern** (lines 37-44):
```tsx
const [activeLayout, setActiveLayout] = createSignal<ActiveLayout>('custom');
let gridController: GridController | undefined;
const onLayoutSelect = (preset: LayoutPreset) => {
    gridController?.applyPreset(preset);
};
```
A5 adds parallel signals:
```tsx
const [project, setProject] = createSignal<ProjectInfo | null>(null);
const [projectLessAccepted, setProjectLessAccepted] = createSignal(false);
```
Per CONTEXT D-01, D-02: **single signal owned by `App.tsx`**, no separate store module — matches the `activeLayout` ownership pattern verbatim.

**Async closure → Tauri command pattern** (lines 52-79 — `saveCurrentLayout`, `loadLayoutByName`, `applyDefaultLayout`):
```tsx
const applyDefaultLayout = async (workspacePath: string): Promise<boolean> => {
    if (!gridController) return false;
    const file = await loadDefaultLayout(workspacePath);
    if (!file) return false;
    gridController.applyLoadedLayout(file);
    return true;
};
```
A5 adds an `openProject` closure that:
1. Calls Tauri `dialog.open({directory: true, multiple: false})` (frontend-side, per D-05).
2. On non-null path: `await openProject(path)` (the new Tauri command).
3. On success: `setProject(info); setProjectLessAccepted(true); await applyDefaultLayout(info.path);` (CONTEXT D-12 hook).

**Conditional render pattern** — no in-repo precedent for "setup window vs grid root" branching; closest analog is the `<Show when={…}>` pattern in `PresetSwitcher.tsx:42-59`. CONTEXT D-03 specifies the branch logic inline in App.tsx body:
```tsx
{project() === null && !projectLessAccepted() ? (
    <SetupWindow onOpenProject={openProject} onStartProjectLess={() => setProjectLessAccepted(true)} recents={recents()} />
) : (
    <GridRoot
        activeLayout={activeLayout}
        onLayoutChange={(next) => setActiveLayout(next)}
        controllerRef={(c) => { gridController = c; }}
        projectCwd={project()?.path}  // A5 D-11 thread
    />
)}
```
**Titlebar renders always** (D-03 explicit) — pull it out of the conditional.

**Landmine — line 60 in `Titlebar.tsx`**: hardcoded `Voss ADE` text. The A1 placeholder comment at line 43 *names A5 as the seam*. A5 must pass `projectName={project()?.name ?? 'Voss ADE'}` through props (NEXT section).

---

### `apps/voss-app/src/components/titlebar/Titlebar.tsx` — accept `projectName` prop

**Analog:** same file.

**Optional-prop pattern** (lines 17-23):
```tsx
export type TitlebarProps = {
  activeLayout?: ActiveLayout;
  layoutDisabled?: boolean;
  onLayoutSelect?: (preset: LayoutPreset) => void;
};
export default function Titlebar(props: TitlebarProps = {}) { … }
```
A5 adds `projectName?: string;` to the type. **Critical**: the default-empty-props (`= {}`) pattern means existing A1/A3 tests rendering `<Titlebar />` still work. A5 must preserve this — falling back to `'Voss ADE'` when `projectName` is undefined (CONTEXT D-01, CONCEPT §10 Q1: fallback when no project open).

**Display site** (line 60):
```tsx
{/* current */}
Voss ADE
{/* A5 */}
{props.projectName ?? 'Voss ADE'}
```

**Drag-region constraint** (lines 43-46 comment): the `data-tauri-drag-region` on the text div is only safe because the div contains *plain text*. If A5 wraps the name in a branch indicator (a `<span>` for git branch) the drag attr stays on the outer div only — never on a child that could be interactive. A10 owns the actual branch *rendering*; A5 only exposes the data (SPEC boundary).

---

### `apps/voss-app/src/components/setup/SetupWindow.tsx` (NEW)

**Analog:** `apps/voss-app/src/components/titlebar/PresetSwitcher.tsx` (110 lines, the freshest "controlled, no-local-state, tokens-only Solid component" in the repo).

**Props pattern** (`PresetSwitcher.tsx` lines 20-24):
```tsx
export type PresetSwitcherProps = {
  activeLayout: ActiveLayout;
  disabled?: boolean;
  onSelect: (preset: LayoutPreset) => void;
};
export default function PresetSwitcher(props: PresetSwitcherProps) { … }
```
A5:
```tsx
export type SetupWindowProps = {
  recents: string[];
  onOpenProject: () => void;           // App.tsx wires this to the dialog flow
  onOpenRecent: (path: string) => void;
  onStartProjectLess: () => void;
};
```
**No local `createSignal`** — A5 D-02 explicit: `App.tsx` owns all signals. SetupWindow is pure reflection (matches `PresetSwitcher.tsx:14-15` doc comment).

**Token-only styling pattern** (`PresetSwitcher.tsx` lines 18-19, 47-58, 83-100): all colors via `var(--…)` CSS variables (`--bg-0`, `--bg-3`, `--fg-0`, `--fg-2`, `--focus`, `--border`, `--accent-amber`). **No raw hex, no `white`**. The test at `PresetSwitcher.test.tsx:170-182` asserts the rendered style contains no `white` literal — A5's SetupWindow MUST follow this and its test should clone the assertion.

**For/Show iteration pattern** (`PresetSwitcher.tsx` lines 1, 42-59, 69-106): use `<For>` for the recents list, `<Show when={recents.length > 0}>` to hide the recents block when empty.

**aria-label discipline** (`PresetSwitcher.tsx` lines 44, 76): every interactive control has an explicit `aria-label="Switch layout to <preset>"` (the test at `PresetSwitcher.test.tsx:43-47` queries by aria-label). A5: `aria-label="Open project"`, `aria-label="Start without project"`, `aria-label="Open recent: {basename}"`.

---

### `apps/voss-app/src/project/projectStorage.ts` (NEW)

**Analog:** `apps/voss-app/src/grid/layoutStorage.ts` (67 lines — clone the structure verbatim).

**Imports + wire-shape pattern** (`layoutStorage.ts` lines 1-22):
```ts
import { invoke } from '@tauri-apps/api/core';
import type { GridStore } from './tree';
// …
export type LayoutFile = { version: 1; activePreset: LayoutPreset | null; grid: GridStore };
```
A5 type:
```ts
export type ProjectInfo = { path: string; name: string; gitBranch: string | null };
export type RecentsFile = { version: 1; recents: string[] };  // (matches Rust shape per D-09)
```
**Camel-case constraint** (`layoutStorage.ts` line 13-15 comment): "Tauri converts snake_case Rust param names to camelCase on the JS side; payload keys here MUST match the Rust function signatures." A5 must enforce: Rust `open_project(path: String)` → JS `invoke('open_project', { path })`. Rust `default_cwd(project_path: Option<String>)` → JS `invoke('default_cwd', { projectPath })`.

**UI-SPEC copy constants pattern** (`layoutStorage.ts` lines 28-40):
```ts
export const SAVE_LAYOUT_LABEL = 'Save layout as...';
// …
export const SAVE_FAILED = 'could not save layout';
```
A5 should export setup-window copy constants too — once the A5-UI-SPEC nails them down. Provisional from CONTEXT/SPEC:
```ts
export const OPEN_PROJECT_LABEL = 'Open project';
export const START_PROJECT_LESS_LABEL = 'Start without project';
export const RECENTS_HEADING = 'Recent projects';
```
The locking question for the planner: does A5 have a UI-SPEC like A4-UI-SPEC? If not, the planner should either (a) add one, or (b) put copy constants in this file and treat *this file* as the SSOT (matches A4's approach).

**`invoke()` bridge pattern** (`layoutStorage.ts` lines 44-67):
```ts
export async function saveLayout(workspacePath: string, name: string, layout: LayoutFile): Promise<void> {
  await invoke('save_layout', { workspacePath, name, layout });
}
```
A5:
```ts
export async function openProject(path: string): Promise<ProjectInfo> {
  return invoke<ProjectInfo>('open_project', { path });
}
export async function loadRecents(): Promise<string[]> {
  return invoke<string[]>('load_recents');
}
export async function defaultCwd(projectPath: string | null): Promise<string> {
  return invoke<string>('default_cwd', { projectPath });
}
```

---

### `apps/voss-app/src/project/__tests__/projectStorage.test.ts` (NEW)

**Analog:** `apps/voss-app/src/grid/__tests__/layoutStorage.test.ts` (139 lines — clone verbatim, swap names).

**Hoisted invoke mock pattern** (lines 1-4):
```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
const h = vi.hoisted(() => ({ invoke: vi.fn() }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
```
**Copy this idiom verbatim.** The `vi.hoisted` pattern is non-obvious — it lets the mock be in scope before the SUT imports `invoke`.

**Test groupings** (lines 52-138): three `describe` blocks — copy constants, invoke wrappers, error propagation. A5 mirrors:
1. `describe('projectStorage — copy constants')` — assert any exported labels match SPEC verbatim.
2. `describe('projectStorage — Tauri invoke bridges')` — assert each function calls `invoke()` with the expected command name + camelCase payload (the test at `layoutStorage.test.ts:73-83` is the gold standard).
3. `describe('projectStorage — propagates Rust error strings verbatim')` — `h.invoke.mockRejectedValueOnce(...)`; assert the wrapper re-throws unchanged.

---

### `apps/voss-app/src/project/__tests__/SetupWindow.test.tsx` (NEW)

**Analog:** `apps/voss-app/src/components/titlebar/__tests__/PresetSwitcher.test.tsx` (183 lines).

**Mount/dispose pattern** (lines 30-41):
```ts
let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});
```
**Copy verbatim.**

**aria-label query helper pattern** (lines 43-47):
```ts
function presetButton(root: HTMLElement, preset: LayoutPreset): HTMLButtonElement {
  return root.querySelector(`button[aria-label="Switch layout to ${preset}"]`) as HTMLButtonElement;
}
```
A5 clones this pattern for `openButton`, `projectLessButton`, `recentButton(path)`.

**Test cases A5 must include** (mapped to SPEC acceptance criteria):
| SPEC criterion | Test name |
|---|---|
| AC #1 (setup visible on no-project startup) | "renders the open-project and start-without-project actions when no project is active" |
| AC #1, D-03 | "does not render GridRoot inside the setup branch" (negative — SetupWindow alone has no `.grid-root` element) |
| Token discipline | "rendered styles contain no raw 'white' literal" (clone `PresetSwitcher.test.tsx:170-182`) |
| Controlled-component | "clicking Open project calls onOpenProject; does not change DOM by itself" (clone `PresetSwitcher.test.tsx:139-152`) |

---

### `apps/voss-app/src/grid/operations.ts` (maybe modify)

**Analog:** same file, lines 117-127 (`forkFocused`).

**Pattern** (lines 118-127):
```ts
export function forkFocused(store: GridStore, geom?: GridGeom): void {
  const old = findLeaf(store.root, store.focusedId);
  if (!old) return;
  insertSibling(store, 'H', makePane({ cwd: old.cwd, shell: old.shell }), geom);
}
```
**Observation**: `forkFocused` already threads cwd from the focused pane (`old.cwd`). The A5 concern is `splitFocused` (line 109-115) — it calls `makePane()` with no args, so the new pane inherits `tree.ts`'s default cwd. CONTEXT mentions "use resolved default cwd" — the cleanest seam is a `makePane({ cwd: defaultCwd })` call inside `splitFocused`, with the defaultCwd plumbed in from the call site (GridRoot → keymap → operations).

**Plan implication**: this is *optional* (CONTEXT says "maybe"). Cheapest A5 path: thread `projectCwd?: string` through `GridRoot` props → `dispatchKey` already takes scalar args (cw, ch, win — see `GridRoot.tsx:184-211`) → add one more scalar `projectCwd`. If too invasive, defer to A6 (session-restore is the next phase that cares about cwd correctness on respawn).

---

### `apps/voss-app/src/grid/GridRoot.tsx` (maybe modify)

**Analog:** same file, lines 97-103 (props bag).

**Pattern** (lines 97-103):
```tsx
export default function GridRoot(props: {
  onCloseRequest?: (store: GridStore) => void;
  closeUI?: CloseUI;
  activeLayout?: () => ActiveLayout;
  onLayoutChange?: (next: ActiveLayout) => void;
  controllerRef?: (ctrl: GridController) => void;
}) { … }
```
A5 adds: `projectCwd?: string;` (optional, undefined = legacy behavior preserved). Threaded into `dispatchKey` at `GridRoot.tsx:184-211` if `operations.ts` accepts it.

---

## Shared Patterns

### Cross-crate `tauri::generate_handler!` constraint
**Source:** `apps/voss-app/src-tauri/src/lib.rs` lines 56-62, 137-142, 154-164 (comment blocks).
**Apply to:** Every new `#[tauri::command]` in A5 (`open_project`, `load_recents`, `default_cwd`).
**Rule:** core logic lives in `voss-app-core` as plain helpers; **thin app-crate wrappers** with `#[tauri::command]` delegate. Never try to `pub use` a `#[tauri::command]` across crates — the macro doesn't follow re-exports.

### Solid signals = UI SSOT; Rust owns persisted I/O (A1 D-09)
**Source:** CONTEXT line 96.
**Apply to:** `recents.json` reads/writes live in Rust (`project.rs`). Frontend never touches the path. Frontend never calls `dirs.homeDir()`. The frontend never builds an absolute path string (CONTEXT specifics line 119).

### Lazy `.voss/` creation
**Source:** `layouts.rs:111-133` (save) vs. `layouts.rs:152-175` (list — no creation) vs. `layouts.rs:181-208` (load_default — no creation). The proof test at `layouts.rs:330-344`.
**Apply to:** **Every** A5 Rust function. `open_project`, `load_recents`, `default_cwd`, `read_git_branch` MUST NOT call `std::fs::create_dir_all` on `<workspace>/.voss/`. Clone the assertion test for `open_project` (SPEC AC #9, CONTEXT line 117).

### Typed errors with Display matching UI-SPEC verbatim
**Source:** `layouts.rs:53-69` (enum), `layouts.rs:430-455` (verbatim test).
**Apply to:** `ProjectError` Display strings — match whatever A5-UI-SPEC copy says, byte-for-byte. Add a test asserting equality.

### Fail-safe-by-default for non-critical reads
**Source:** `layouts.rs:181-208` (`load_default_layout`).
**Apply to:** `load_recents` (corrupt → empty list, no panic), `read_git_branch` (any error → `None`), `default_cwd` (no HOME → `'/'` per CONTEXT D-11). Log to stderr; never bubble to UI.

### `~/.config/voss-app/` user-config path lock
**Source:** `apps/voss-app/src-tauri/src/lib.rs:18-30` + CONTEXT line 92 (D-08 reuse).
**Apply to:** `recents_path()`. Clone the NOTE comment about why NOT to use `dirs::config_dir()` (macOS `~/Library/Application Support` divergence is locked away by A1 D-08).

### Solid component: controlled, no-local-state, tokens-only
**Source:** `PresetSwitcher.tsx` doc comment lines 8-19.
**Apply to:** `SetupWindow.tsx`. Props in, callbacks out, no `createSignal` inside. All colors via CSS vars.

### Hoisted `vi.mock` for Tauri `invoke`
**Source:** `layoutStorage.test.ts:3-4`.
**Apply to:** `projectStorage.test.ts` and any A5 test that touches `invoke`.

---

## Landmines (existing code A5 must NOT regress)

1. **`Titlebar.tsx:60` hardcodes `"Voss ADE"`.**
   A1 placeholder comment at line 43 calls A5 by name as the seam. A5 must replace with `props.projectName ?? 'Voss ADE'` AND preserve the fallback so pre-A5 tests rendering bare `<Titlebar />` still pass (lines 17-23 default-empty-props pattern). Drag-region constraint at lines 44-46: the drag attr stays on the outer text div only.

2. **`App.tsx:102-108` mounts `<GridRoot>` directly with no setup branch.**
   The unused-suppression at lines 82-84 (`void saveCurrentLayout; void loadLayoutByName; void applyDefaultLayout;`) means A4-04 closures exist but are never called. A5 must wire `applyDefaultLayout(project.path)` on every successful open (CONTEXT D-12) and remove the `void applyDefaultLayout;` line. **Do NOT remove `void saveCurrentLayout;` or `void loadLayoutByName;`** — those are still A7's seam.

3. **`apps/voss-app/src-tauri/capabilities/default.json` has no `dialog:*` permission.**
   Without adding `"dialog:default"` (or the correct fine-grained variant), the frontend's `open()` call will fail at runtime with a Tauri permission error. The capability file is locked-down by default (lines 5-12 only list `core:*` permissions).

4. **No `recents.json` exists yet — but `settings.json` does.**
   `apps/voss-app/src-tauri/src/lib.rs:18-30` (`settings_path`) is the precedent. The `recents.json` parent directory `~/.config/voss-app/` may or may not exist on first run. A5's `save_recents` must `create_dir_all` the parent before write. **But the workspace directory `<workspace>/.voss/`** remains untouched (different rule — see "Lazy `.voss/` creation" shared pattern).

5. **`voss-app-core/Cargo.toml` does NOT depend on `dirs`.**
   `apps/voss-app/src-tauri/Cargo.toml:20` does. If A5 puts `default_cwd()` in `voss-app-core` (cleanest per CONTEXT D-11), add `dirs = { workspace = true }` to `crates/voss-app-core/Cargo.toml`.

6. **`tree.ts`'s `makePane()` likely sets a hardcoded default cwd (likely `''`).**
   Not read in this pass — planner should verify. If `makePane()` defaults cwd to empty string, A5's `default_cwd` flow needs to thread the resolved value into the call site, not into `makePane` itself (changing `makePane`'s default would affect every test fixture).

7. **`Titlebar.tsx` default-empty-props (`= {}` at line 23).**
   This is intentional to keep older tests green. Adding `projectName` as **required** would break the existing test at `Titlebar.test.tsx` (not read but implied by `__tests__` folder presence). Keep `projectName?:` optional.

8. **`tauri::generate_handler!` registry is order-sensitive only insofar as duplicates fail to compile.**
   A5 must add `open_project, load_recents, default_cwd` exactly once. The current registry at lines 205-220 already has 13 commands — A5 brings it to 16.

9. **CONCEPT §10 Q1 fallback rule**: when `project === null` AND user has not yet accepted project-less mode, the setup window shows AND the titlebar still says "Voss ADE" (no project). Once project-less is accepted, **titlebar still says "Voss ADE"** because there's no project name to show. Only an explicitly opened project replaces the fallback. The fallback chain is: `project()?.name ?? 'Voss ADE'`.

10. **CONTEXT D-04: `projectLessAccepted` is session-only, NOT persisted.**
    Don't accidentally save it to `recents.json`, `settings.json`, or any future `session.json` (that's A6's concern, and A6 owns the decision). A relaunch in project-less mode shows the setup window again — this is the intended behavior, not a bug.

11. **CONTEXT D-13: project change must not destroy panes.**
    The cleanest evidence is `GridRoot.tsx:104` — `createGridStore()` is called once on mount. Re-mounting `GridRoot` on every project change would destroy panes. A5 must NOT unmount `GridRoot` when the project signal changes. The conditional render branch in App.tsx (`project() === null && !projectLessAccepted() ? <SetupWindow/> : <GridRoot/>`) is one-way: once the user picks a project OR accepts project-less, the right side mounts permanently for the session, and project-changes happen via signal updates only (titlebar + future-pane cwd), not via Solid component swaps.

---

## No Analog Found

None. Every A5 area has a clear in-repo precedent. The two areas with no exact code precedent are:

| Area | Status | Mitigation |
|---|---|---|
| Recents dedup/cap logic (D-09) | trivial new code (~10 lines), no analog needed | Inline `promote()` helper; write unit tests with 6 inputs and assert truncation + reorder. |
| `git2` git-branch read (D-08) | new dep, no analog | The function is ~5 lines. The pattern doc (Read git branch best-effort) above is the spec. Test with `tempfile::tempdir()` + `git2::Repository::init()` to create an actual repo for the branch-name test, and a plain tempdir for the `None` test. |

---

## Plan Implications (landing order)

The dependency graph forces a strict-ish order. Plans should land in waves:

**Wave 1 — Rust schema + helpers (project.rs):**
- `crates/voss-app-core/Cargo.toml` (add `git2`, `dirs`)
- `crates/voss-app-core/src/project.rs` (NEW) — `ProjectInfo`, `RecentsFile`, `ProjectError`, `open_project`, `load_recents`, `default_cwd`, `read_git_branch` + all unit tests
- `crates/voss-app-core/src/lib.rs` — pub use the new module

**Why first**: every other A5 plan depends on these types and command shapes. The Rust tests can run standalone via `cargo test -p voss-app-core` without any frontend touched.

**Wave 2 — Tauri command wrappers + plugin:**
- `apps/voss-app/src-tauri/Cargo.toml` (add `tauri-plugin-dialog`)
- `apps/voss-app/src-tauri/capabilities/default.json` (add `dialog:default`)
- `apps/voss-app/src-tauri/src/lib.rs` — register dialog plugin + three new `#[tauri::command]` wrappers + extend `generate_handler!`

**Why second**: builds the IPC surface. Frontend wrappers (Wave 3) need these command names + payload shapes to exist on the Rust side or the integration test will fail. (Unit tests can mock `invoke`, but the integration won't.)

**Wave 3 — Frontend invoke wrappers:**
- `apps/voss-app/src/project/projectStorage.ts` (NEW) + its `__tests__/projectStorage.test.ts`

**Why third**: pure typescript layer; only depends on the Wave 2 command names and payload shapes being decided. Can land before SetupWindow because App.tsx will pull both in together.

**Wave 4 — SetupWindow component:**
- `apps/voss-app/src/components/setup/SetupWindow.tsx` (NEW) + its `__tests__/SetupWindow.test.tsx`

**Why fourth**: pure presentational; can render with stub callbacks. Lands before App.tsx composition so App.tsx has something concrete to mount.

**Wave 5 — Composition: App.tsx + Titlebar.tsx:**
- `apps/voss-app/src/components/titlebar/Titlebar.tsx` — add `projectName?: string` prop, route to display site
- `apps/voss-app/src/App.tsx` — add `project` / `projectLessAccepted` signals, conditional render branch, `openProject` closure, call `applyDefaultLayout(project.path)` on success (CONTEXT D-12)

**Why fifth**: integration step. All upstream pieces (Wave 1-4) must exist. The Titlebar prop change is technically independent of App.tsx, but they share a test boundary (the next-to-last A5 acceptance test will render both via App.tsx).

**Wave 6 (OPTIONAL) — Default cwd plumbing:**
- `apps/voss-app/src/grid/operations.ts` — thread `defaultCwd` through `splitFocused` / `forkFocused`
- `apps/voss-app/src/grid/GridRoot.tsx` — add `projectCwd?: string` prop, pass through dispatchKey

**Why last (and optional)**: CONTEXT marks both as "maybe". SPEC AC #4 ("Starting without a project uses home directory as default cwd") could be satisfied by `default_cwd` Tauri command alone (the frontend never builds the path). The grid wiring is an optimization for future pane creation. Defer if time-bound.

**Parallelization**: Waves 3 and 4 can land in parallel (no cross-dependency). Wave 6 can land at any time after Wave 1 (it doesn't depend on the dialog plumbing). The strict serial chokepoints are W1 → W2 → W5.

## Metadata

**Analog search scope:**
- `crates/voss-app-core/src/` (layouts.rs as primary, lib.rs, pty/mod.rs as secondary)
- `apps/voss-app/src-tauri/src/` (lib.rs)
- `apps/voss-app/src-tauri/capabilities/` (default.json)
- `apps/voss-app/src-tauri/Cargo.toml`, `crates/voss-app-core/Cargo.toml`, root `Cargo.toml`
- `apps/voss-app/src/` (App.tsx, components/titlebar/*, grid/layoutStorage.ts, grid/operations.ts, grid/GridRoot.tsx)
- `apps/voss-app/src/**/__tests__/` (layoutStorage.test.ts, PresetSwitcher.test.tsx, operations.test.ts header)

**Files scanned:** 14 (full reads) + ~6 (directory listings)

**Pattern extraction date:** 2026-05-19
