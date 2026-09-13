# Standalone ADE Canvas — Product and Engineering Handoff

Date: 2026-09-12  
Source application: `apps/voss-app`  
Source revision observed: `9dc3d944` plus concurrent working-tree edits  
Purpose: deliver a functional, independent desktop canvas for terminals, notes, and files.

This is a handoff, not a declaration that the application is finished. It records
the usable foundation, the intended standalone behavior, and the work needed to
make that behavior reliable. No application code was changed while writing it.

## 1. Product definition

A local desktop workbench where a developer places terminals, notes, and file
views on a persistent, zoomable canvas. The user can run ordinary shell commands
or any installed CLI inside a terminal. The application does not direct that CLI,
choose its model, manage its credentials, or require an account of its own.

The central workflow is:

1. Open the app into a usable terminal, with or without a project folder.
2. Use **+** to add another terminal, a note, or a file view.
3. Place and arrange nodes around the work, then move between them with mouse or keyboard.
4. Switch workspaces without stopping their running shells.
5. Return later to the saved layout, notes, file locations, and available scrollback.

The canvas is the product. It must work independently of an agent backend.

### Scope boundary

| Include | Exclude |
|---|---|
| Local terminals and arbitrary installed CLIs | Voss harness, model calls, provider setup, billing |
| Free-positioned terminal, note, and file nodes | Observe capture, investigations, findings, BOS |
| Workspace/project folders and workspace tabs | Orchestration, swarms, machines, managed tasks, agent roles |
| File navigation, terminal search, copy/paste | Review cockpit, budgets, agent memory/context services |
| Keyboard commands, arrangements, themes, accessibility | Cloud accounts, relays, remote-machine management |
| Local layout/content persistence and safe process lifecycle | Automatic Git changes, code generation, unattended actions |

Running `claude`, `codex`, or another executable manually is ordinary terminal
usage. It does not bring any excluded management feature into scope.

## 2. Current state versus required behavior

| Area | Current evidence | Handoff requirement |
|---|---|---|
| Free canvas | `CanvasRoot`, model/store/geometry, node frames exist | Preserve this working foundation; no redesign requested |
| Add terminal/note | Command registry and placement controller exist | Add an obvious, keyboard-accessible **+** menu |
| Terminal typing | User reports inability to type; investigation incomplete | Reproduce and fix before declaring the app functional |
| Node movement | Drag, resize, snap, selection and arrangements exist | Preserve terminal sessions and selection behavior throughout |
| Zoom/navigation | Camera, fit commands, move mode and minimap exist | Navigation must also leave the intended editor/input usable |
| Notes | CodeMirror Markdown editor and preview exist | Editing and persistence must survive focus and workspace changes |
| Files | CodeMirror file viewer exists; explicitly read-only | Open real workspace files; clearly indicate read-only mode |
| Workspace persistence | Workspace/session storage and v1→v2 migration exist | Verify relaunch and corrupt/missing-file behavior in the native app |
| Standalone operation | Plain-shell PTY path exists | Remove mandatory coupling to excluded services from app boot and interaction |
| Verification | Component/browser/core tests exist | Native typing and session-lifecycle checks remain necessary |

Existing S0–S2 completion labels are historical planning status, not current
release certification. S1 and S2 contain the desktop canvas work. Python-only S0
and the Observe/orchestration phases are not dependencies of this standalone
product contract. Reuse the canvas already built rather than restarting S1/S2.

## 3. Interface and interactions

### App shell

- Top chrome: window/project identity and command access.
- Workspace tabs: activate, create, rename, reorder, and close workspaces.
- Optional collapsible sidebar: project files and a simple list of open nodes.
- Main area: one canvas for the active workspace.
- Canvas controls: **+**, layout controls, and zoom/fit controls; keep them outside
  the transformed plane so they remain readable at every zoom.
- Settings: terminal font, theme, cursor, contrast, bell, motion, and keybindings.
- Status: actual local state such as current workspace, shell/process, and zoom.

There is no task dashboard, global agent prompt, machine selector, agent roster,
or orchestration navigation in this app. A file tree is navigation; files opened
from it become canvas nodes.

### The + menu — next visible feature

Place a persistent **+** button in the canvas toolbar. Accessible name: **Add to canvas**.

| Menu item | Result | Reuse |
|---|---|---|
| New terminal | Enter terminal placement; click to create and focus a shell | `CanvasController.placeNode('terminal')` |
| New note | Enter note placement; click to create and focus an empty Markdown editor | `CanvasController.placeNode('note')` |
| Open file… | Select a file inside the workspace and open/focus its file node | File-selection UI plus `CanvasController.openFile(path, line?)` |

Terminal and note placement already have a cursor-following ghost. Keep that
behavior: click confirms; Escape cancels; cancellation creates no node or process.
The menu closes when a choice is made. Show a short placement hint, then remove it
after placement. Do not create a second creation path just for the button.

Opening an already-open file focuses its node instead of duplicating it. Without
a workspace folder, offer opening a folder before file selection. Keep terminals
and notes available in project-less workspaces.

The button and menu must support Tab, Enter/Space, arrow-key item navigation, Escape,
outside-click dismissal, and predictable focus return. Opening or closing a menu
must not send its keystrokes to a terminal or accidentally begin a canvas drag.

### Node chrome

Each node has a compact header, content area, visible focused state, resize handles,
and an overflow menu. Headers identify the content: shell/cwd for terminals,
note label for notes, file path for file views. Existing terminal headers are 22 px.

Header drag moves a node; content interaction belongs to the terminal/editor.
Overflow controls must not initiate drag. Terminal actions include new adjacent
terminal and close. Note/file menus should use content-appropriate actions rather
than exposing terminal-specific “fork” behavior.

Closing a terminal running a foreground process asks for confirmation. Closing a
node is the destructive lifecycle boundary; dragging, minimizing detail, switching
focus, and changing workspaces are not. Preserve the current last-terminal
replacement behavior unless product requirements explicitly change it.

### Canvas gestures and navigation

| Interaction | Contract |
|---|---|
| Drag header | Move node in world coordinates; keep its process/editor intact |
| Resize edge/corner | Resize node; refit terminal and update PTY rows/columns |
| Snap | Snap edges/centers within 8 world px; show guides; Option disables |
| Shift-click / Shift-drag background | Toggle selection / marquee-select nodes |
| Drag selected header | Move selected nodes together |
| Pan | Background drag and supported middle/right-button gestures; do not intercept content interaction |
| Scroll | Respect terminal/editor scrolling; canvas background can pan |
| Cmd/Ctrl-wheel | Zoom around the pointer |
| Fit / reset | Fit all nodes, focus a node, or restore zoom 1 without replacing nodes |
| Minimap | Show at 3+ nodes; click/drag navigates the viewport |
| Reduced motion | Camera changes are immediate |

The source plan also calls for space-drag and pinch. Audit these independently:
they are requirements in the plan, not verified gestures in this handoff. Space
typed into a terminal must remain a space unless an explicit canvas gesture owns it.

Current constants: zoom 0.25–2.5, node gap 16 px, default terminal 720×440,
note 360×240, and file 640×480. Reuse these rather than introducing a new sizing
system. The minimap is currently 180×120. These are starting implementation values,
not evidence of native usability at every display scale.

### Low-detail terminals

Below zoom 0.6, terminal nodes show a compact chip with process/cwd and recent
lines. Their xterm host detaches; the session stays alive. Returning to normal
detail reuses the same terminal and scrollback.

For the standalone app, omit agent role, cost, and budget decoration. Focusing a
chip for input should reveal its live terminal and transfer input focus. Explicitly
test the first typed character: a camera animation must not silently swallow it
or deliver it to the previously focused terminal.

### Keyboard commands

Use the existing command registry for menu labels, palette entries, and shortcut
dispatch. The defaults below are read from the current registry; profile overrides
can differ. Cmd is the current macOS mapping, not a claim of Windows/Linux parity.

| Action | Default |
|---|---|
| New terminal placement | Cmd+Shift+T |
| New note placement | Cmd+Shift+N |
| Adjacent terminal right / below | Cmd+D / Cmd+Shift+D |
| Close focused node | Cmd+W |
| Focus node by reading order | Cmd+1…9 |
| Next / previous node | Cmd+] / Cmd+[ |
| Directional focus | Cmd+Alt+Arrow |
| Equalize arrangement | Cmd+= |
| Cycle arrangement | Cmd+G |
| Reset zoom / fit all | Cmd+0 / Cmd+Shift+0 |
| Quick open / command palette | Cmd+P / Cmd+Shift+P |
| Terminal find | Cmd+F |
| Cancel placement/menu | Escape |

Move-mode prefix commands are profile-specific. Show the active mode and an
obvious escape path. Legacy layout names such as `swarm` describe geometry in
`arrange.ts`; they do not authorize orchestration features. Present neutral layout
labels in a standalone shell while preserving saved identifiers if needed.

## 4. Terminal correctness: highest-priority repair

**Reported problem:** the user cannot write text into a canvas terminal.
No fix was completed before this documentation request replaced implementation work.

The code currently updates `CanvasState.focusedId` when selecting a node. That
does not itself focus xterm. `adoptPaneSession` mounts and configures the terminal,
but does not focus it. `PaneComponent` has a local focus signal; its outer click
handler updates that signal rather than explicitly focusing xterm. Native xterm
mouse behavior may still focus its textarea, so these observations are a likely
failure path, not a proven explanation for every failed click.

Trace and test the complete path:

```text
click / keyboard navigation / new node
  → canvas focusedId
  → active, mounted PaneComponent
  → xterm textarea owns DOM focus
  → xterm onData
  → PtyTransport.write
  → Tauri pty_write
  → Rust PTY writer
  → shell input and output
```

Required behavior:

1. The initial terminal is ready to type into after its shell is available.
2. Clicking terminal content or choosing its header makes that terminal the input target.
3. Keyboard node switching transfers actual input focus, not only the border.
4. A new terminal accepts input immediately after placement.
5. Returning to a workspace or restoring live detail does not leave focus in a hidden node.
6. Note/file/menu controls retain their own focus; terminal focus never steals their typing.
7. Drag, resize, selection, prefix mode, and application shortcuts consume only
   the events they own. Normal text and Ctrl+C reach the shell.
8. A failed spawn/write shows an actionable local error instead of a dead-looking terminal.

Investigate focus, DOM overlays, key interception, and PTY spawn/write state in
that order with evidence. Avoid a global “focus terminal on every render” fix:
it would break note editing, menus, selection, and hidden workspaces.

## 5. Persistence and process lifetime

The stable identifier is the node/pane ID. Geometry and view state are separate
from the process and xterm instance that ID owns.

| State | Lifetime |
|---|---|
| Node geometry, kind, cwd, shell, file path/line, note text, canvas view | Saved workspace/session state |
| Focused node and workspace selection | Restored through workspace/session machinery |
| Selected group, placement ghost, drag/marquee state, open menus | Transient interaction state |
| xterm, transport, host element, live shell | Session registry for the current app lifetime |
| Saved scrollback | Context on restoration; not proof of a surviving process |

The current implementation uses direct native PTYs. It does not establish
tmux-backed process survival after application exit. Layout/scrollback restoration
and keeping a running process alive are different promises. Do not claim the
latter without a separate durable process host and its verification.

Session version 2 stores canvas nodes/view; legacy version 1 split layouts migrate
into positioned nodes. Keep migration and saved identifiers intact. Test notes
with pending edits at focus loss, workspace switch, and quit; avoid losing a
debounced edit at teardown. Do not execute restored terminal text as commands.

## 6. Implementation map and standalone boundary

The existing stack is SolidJS/TypeScript, Tauri/Rust, xterm 5.5.0, and CodeMirror 6.
Reuse it. No canvas library replacement or new framework is needed.

| Responsibility | Existing source, relative to repo root |
|---|---|
| App composition | `apps/voss-app/src/App.tsx`, `src/app/AppShell.tsx` |
| Workspace ownership | `apps/voss-app/src/app/workspaceHost.ts`, `src/workspaces/` |
| Commands and keyboard dispatch | `apps/voss-app/src/app/keymapHost.ts`, `src/command-palette/` |
| Canvas host/controller | `apps/voss-app/src/canvas/CanvasRoot.tsx` |
| Model and operations | `apps/voss-app/src/canvas/{model,store,geometry,snap,arrange,camera}.ts` |
| Node chrome | `apps/voss-app/src/canvas/{NodeFrame,NodeMenu,NodeCloseBanner}.tsx` |
| Note/file content | `apps/voss-app/src/canvas/{NoteNode,FileNode}.tsx`, `editor.ts`, `markdown.ts` |
| Low-detail view/minimap | `apps/voss-app/src/canvas/{TerminalChip,Minimap}.tsx`, `lod.ts`, `minimapLayout.ts` |
| Terminal UI and adoption | `apps/voss-app/src/pane/PaneComponent.tsx`, `paneSession.ts`, `paneSessionRegistry.ts` |
| PTY transport | `apps/voss-app/src/pane/pty-ipc.ts` |
| Native command boundary | `apps/voss-app/src-tauri/src/lib.rs` |
| Native process/file support | `crates/voss-app-core/src/pty/`, `project.rs` |
| Session/layout persistence | `apps/voss-app/src/canvas/{session,migrate,sync}.ts`, `src/workspaces/workspaceSessionPersist.ts`, `crates/voss-app-core/src/{canvas,session,layouts}.rs` |
| Themes and appearance | `apps/voss-app/src/themes/`, `src/appearance/`, `src/canvas/canvas.css` |

In rows with abbreviated `src/...` entries, those entries remain under
`apps/voss-app/`. Some files still use `grid` in their name despite serving the
canvas. Names alone are not a reason to delete or replace them.

### What must be separated

The source app is not yet a proven standalone composition. Its shell mounts
agent/sidebar/review surfaces, and terminal lifecycle modules import optional
Observe, agent-identity, budget, and live-server code.

For a standalone build, retain the workspace/canvas/terminal ownership above,
and remove excluded behavior from the composition and plain-terminal startup
path. In particular:

- Boot without `liveBoot` requiring the Python sidecar or credentials.
- Do not mount the managed-task composer, board strip, portal surfaces, or agent controls.
- Use only terminal/note/file node kinds; do not expose the native-protocol node path.
- Plain PTY creation must not require agent registration, Observe clients,
  billing/context streams, or `voss shell-init` on PATH.
- Keep the terminal's own cwd/title/process, clipboard, search, resize, and output paths.
- Keep local file access through the native project boundary. Preserve path-escape
  and symlink checks and the current 2 MiB read limit.
- Keep note HTML sanitized. Terminal/file content remains untrusted display content.

A hidden sidebar is not sufficient separation if its services still start.
Verify with Python/Voss absent, no credentials, and no network. This section
specifies the extraction boundary; it does not claim those changes already exist
or authorize deleting unrelated features from the shared application.

## 7. Comparison with 49-IDE / 49 Agents

The reference name is confirmed by the user. The original teardown was not found
in the available repo/vault notes. The table below reconstructs the relevant
comparison from the Canvas plan and the project's public README, checked
2026-09-12. It is not a recovered transcript or an independently tested parity audit.

Source for the reference-product column:
[49 Agents IDE repository and README](https://github.com/alpbahadur/49-IDE).
Local evidence comes from the implementation map above and the S1/S2 plan.

| Dimension | 49-IDE public description | Standalone ADE direction / current gap |
|---|---|---|
| Main surface | Zoomable free-positioned canvas | Same core spatial model; retain current canvas |
| Layout | Drag, resize, persistent positions | Present foundation; add discoverable creation controls |
| Terminals | tmux sessions exposed through ttyd | Native PTYs through Tauri; do not claim restart continuity |
| Navigation | Numbered focus, Tab chords, WASD move mode | Existing numbered/directional focus and profile-based move mode |
| Notes | Markdown notes | Existing editable CodeMirror notes with preview |
| Files | Monaco editor on canvas | CodeMirror 6; current files read-only, not editor parity |
| Multiple projects | Unified spatial workspace | Separate persistent workspace canvases/tabs; intentional choice |
| Broadcast | Multi-terminal input | Not part of this delivery; normal input must work first |
| Remote access | Multiple machines, browser/device access | Local desktop only |
| Additional panels | Git graph, issues, permission signals, usage HUD | Excluded from the standalone canvas baseline |

The relevant lesson is discoverable spatial work: create something, place it,
recognize it, focus it, and keep working. Borrow the interaction principle, not
the reference product's entire service architecture or agent-management surface.

Differences to preserve deliberately: native local PTYs, CodeMirror, workspace
tabs, local settings, and no required backend. Do not expand scope just to match
every reference-product feature. No performance-superiority or full-parity claim
is supported by the evidence available here.

## 8. Delivery order

| Order | Deliverable | Completion evidence |
|---|---|---|
| 1 | Fix terminal input/focus | Native shell receives text in initial, clicked, newly placed, switched, and reattached terminals |
| 2 | Add + menu using existing controller actions | Mouse/keyboard create terminal and note; file opening works; Escape/outside dismissal are correct |
| 3 | Establish standalone app composition | Clean project-less boot and normal usage with excluded services absent |
| 4 | Verify lifecycle and persistence | No PTY respawn during layout/view changes; note/file/layout state restores honestly |
| 5 | Polish navigation and empty/error states | Input focus, keyboard access, readability and local errors behave consistently |
| 6 | Native acceptance and build verification | Checklist below has evidence against the actual delivered revision |

Avoid adding remote hosts, broadcast, editable project files, or new node families
before these six deliverables are complete. The immediate user request is a usable
canvas with creation controls and working terminals.

## 9. Acceptance checklist

### Core workflow

- [ ] Fresh project-less launch opens one terminal; type `printf 'canvas-ok\n'` and see output.
- [ ] Open a project folder; new terminals use its cwd and the user's shell.
- [ ] + → New terminal → place → type: command reaches only that new shell.
- [ ] + → New note → place → type Markdown → blur → preview → refocus → continue editing.
- [ ] + → Open file opens a valid workspace file, shows read-only status, and focuses an existing node on repeat.
- [ ] Escape during placement leaves node count and process count unchanged.
- [ ] The menu works entirely by keyboard and restores focus without emitting terminal input.

### Focus and lifecycle

- [ ] Clicking body/header and keyboard switching focus the intended terminal's real input.
- [ ] Notes, search fields, and menus are never interrupted by terminal autofocus.
- [ ] Ctrl+C interrupts the intended foreground process; copy/paste/search still work.
- [ ] Run a long-lived process, then drag, resize, arrange, zoom, and switch workspaces; PID/session identity stays unchanged.
- [ ] Zoom below 0.6 and back preserves xterm identity and scrollback; input from a chip reaches the intended terminal once.
- [ ] Closing a busy terminal asks first; cancelling leaves its process alive.
- [ ] Hidden workspaces neither consume ordinary typing nor steal focus.

### Persistence, accessibility, and independence

- [ ] Quit/relaunch restores layout/view, notes, file paths/line locations, and saved scrollback; live-process claims match actual behavior.
- [ ] v1 layout migration retains usable nodes; malformed or missing session data has a recoverable outcome.
- [ ] Path traversal, escaping symlinks, and oversize files return understandable errors.
- [ ] Keyboard commands remain reachable; focus is visible; reduced-motion avoids camera animation.
- [ ] Core workflow works with no Voss executable, Python sidecar, provider credentials, or network connection.
- [ ] No excluded service appears in navigation, creation menu, onboarding, status, or startup requirements.

## 10. Verification and handoff evidence

Existing tests are useful starting points, not proof of the fixes requested here:

- `src/canvas/__tests__/CanvasRoot.test.tsx`: geometry, placement, focus state, LOD identity.
- `src/canvas/__tests__/NoteFileNodes.test.tsx`: note/file behavior.
- `src/pane/__tests__/`: terminal session lifecycle, clipboard and PTY transport.
- `e2e/canvas-basics.spec.ts`, `canvas-nodes.spec.ts`: browser interaction through mocked IPC.
- `crates/voss-app-core/src/pty/tests.rs`: native PTY mechanics.
- Native `project.rs` and session/layout tests: filesystem boundaries and persistence.

Run from `apps/voss-app` for the frontend checks:

```sh
pnpm exec vitest run src/canvas/__tests__ src/pane/__tests__
pnpm build
pnpm check:xterm-pin
pnpm exec playwright test e2e/canvas-basics.spec.ts e2e/canvas-nodes.spec.ts
```

Run from the repository root for native checks:

```sh
cargo test -p voss-app-core
cargo check -p voss-app
```

Use the repository Playwright server configuration or `VOSS_APP_URL` pointed at
the correct local app. Mocked IPC checks cannot establish that a real shell
receives typed text. Run the core workflow in the Tauri app and record revision,
OS, shell, action, expected/actual outcome, and focused regression-test names.
Use disposable files and synthetic terminal output for screenshots or fixtures.

Performance baseline: [canvas-perf.md](canvas-perf.md) records 12 mocked flooding
terminals in Chromium. Its zoom-0.5 measurement uses a refresh-adjusted threshold,
not a literal pass under the plan's 8 ms target. It does not certify native
WKWebView performance. Reuse the test and report both the raw numbers and method.

No tests were rerun for this documentation-only handoff. Prior branch-wide CI
was failing; concurrent work has advanced HEAD since that diagnosis. Do not label
the current revision green using earlier results. Capture fresh evidence when
the functional fixes and standalone boundary are actually delivered.

## 11. Source precedence

For this handoff's scope, the user's standalone-canvas request takes precedence.
Use the S1/S2 geometry and lifecycle decisions from
[CANVAS-OBSERVE-INSTRUCTIONS-PLAN.md](../.planning/CANVAS-OBSERVE-INSTRUCTIONS-PLAN.md),
then verify implementation through the source map above.

`apps/voss-app/PRODUCT.md` is an older, broader product contract with grid and
orchestration navigation. It is historical context, not the navigation contract
for this standalone app. `.planning/ADE-REDESIGN.md` contains earlier visual
directions; preserve current working appearance and tokens unless a separate
design change is requested. The 49-IDE comparison informs interaction choices;
it does not override the local-only scope.

Handoff outcome: a reliable spatial terminal workbench with an obvious + menu,
working text input, editable notes, file views, and honest persistence. Everything
needed to use that workbench must stand on its own.
