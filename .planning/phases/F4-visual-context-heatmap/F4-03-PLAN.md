---
phase: F4
plan_id: F4-03
title: "Frontend ContextPanel + pty-ipc ContextData type + signal wiring"
wave: 2
depends_on: [F4-01]
files_modified:
  - apps/voss-app/src/pane/pty-ipc.ts
  - apps/voss-app/src/pane/PaneComponent.tsx
  - apps/voss-app/src/components/ContextPanel.tsx
  - apps/voss-app/src/components/ContextPanel.css
  - apps/voss-app/src/App.tsx
autonomous: true
status: pending
---

<objective>
Build the frontend ContextPanel component and wire it to live context data from the PTY channel. Add the `ContextData` TypeScript type and `context_update` event handling to `pty-ipc.ts`, add a context signal to PaneComponent, create the `ContextPanel.tsx` overlay component with file list, summary bar, pin buttons, and empty state, mount it in App.tsx with a Cmd+I toggle keybind, and route the focused pane's context signal to the panel.

Purpose: This is the user-facing surface of F4. Without the panel, context data parsed by F4-01 and emitted by F4-02 has nowhere to display.

Output: `ContextPanel.tsx`, `ContextPanel.css`, pty-ipc ContextData type, PaneComponent context signal, App.tsx panel mount with Cmd+I keybind.
</objective>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Rust PtyEvent::ContextUpdate -> Tauri Channel -> pty-ipc.ts | Typed JSON event deserialized by Tauri runtime |
| ContextPanel pin click -> Tauri invoke -> `.voss/context-pins.json` | User action writes to workspace file (F4-04 implements this IPC) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-F4-09 | Spoofing | pty-ipc context_update handler | accept | Same trust model as budget_update — PTY channel is local, not network-exposed. |
| T-F4-10 | DoS | ContextPanel rendering 200 file rows | mitigate | Virtualized list not needed at 200 items. CSS overflow-y: auto handles scroll. |
| T-F4-11 | XSS | File path rendering in panel | mitigate | Solid.js auto-escapes text content. No `innerHTML`. |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add ContextData type + onContextUpdate to pty-ipc.ts</name>
  <files>apps/voss-app/src/pane/pty-ipc.ts</files>
  <read_first>
    - apps/voss-app/src/pane/pty-ipc.ts (full file — 189 lines)
    - crates/voss-app-core/src/pty/commands.rs (ContextData/FileContextEntry structs from F4-01)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-25 — payload shape)
    - .planning/phases/F4-visual-context-heatmap/F4-PATTERNS.md (Pattern 3 — Tauri Channel to Solid Signal)
  </read_first>
  <action>
    **Add `FileContextEntry` type** after the existing `BudgetState` type (around line 24):
    ```typescript
    export type FileContextEntry = {
      path: string;
      tokens: number;
      state: 'full' | 'compressed' | 'dropped';
      pinned: boolean;
    };
    ```

    **Add `ContextData` type** after `FileContextEntry`:
    ```typescript
    export type ContextData = {
      system_tokens: number;
      conversation_tokens: number;
      total_tokens: number;
      token_limit: number | null;
      files: FileContextEntry[];
    };
    ```

    **Extend the `PtyEvent` union** (line 11-16) with a new member:
    ```typescript
    | { type: 'context_update'; system_tokens: number; conversation_tokens: number; total_tokens: number; token_limit: number | null; files: FileContextEntry[] }
    ```

    **Add `onContextUpdate` to `PtyTransportOpts`** (line 36-45):
    ```typescript
    onContextUpdate?: (data: ContextData) => void;
    ```

    **Add `context_update` case** to the `handle` method switch statement (after the `budget_update` case, around line 113):
    ```typescript
    case 'context_update':
      this.opts.onContextUpdate?.({
        system_tokens: ev.system_tokens,
        conversation_tokens: ev.conversation_tokens,
        total_tokens: ev.total_tokens,
        token_limit: ev.token_limit,
        files: ev.files,
      });
      break;
    ```
  </action>
  <acceptance_criteria>
    - `grep -c "ContextData" apps/voss-app/src/pane/pty-ipc.ts` returns at least 2 (type + opts usage)
    - `grep -c "context_update" apps/voss-app/src/pane/pty-ipc.ts` returns at least 2 (PtyEvent member + case)
    - `grep -c "onContextUpdate" apps/voss-app/src/pane/pty-ipc.ts` returns at least 2 (opts + handler)
    - `tsc --noEmit` exits 0 (from `apps/voss-app/`)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Add context signal to PaneComponent + wire onContextUpdate</name>
  <files>apps/voss-app/src/pane/PaneComponent.tsx</files>
  <read_first>
    - apps/voss-app/src/pane/PaneComponent.tsx (lines 1-10 for imports, lines 99 for budget signal, lines 325-343 for PtyTransport construction)
    - apps/voss-app/src/pane/pty-ipc.ts (ContextData type from Task 1)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-02, D-12 — per-pane scope, local signal)
  </read_first>
  <action>
    **Update import** from `pty-ipc`: add `ContextData` to the import alongside `BudgetState`:
    ```typescript
    import { PtyTransport, type AgentConfig, type BudgetState, type ContextData } from './pty-ipc';
    ```

    **Add context signal** alongside the existing budget signal (around line 99):
    ```typescript
    const [context, setContext] = createSignal<ContextData | null>(null);
    ```

    **Wire onContextUpdate** in the PtyTransport constructor (around line 336, after `onBudgetUpdate`):
    ```typescript
    onContextUpdate: (data) => setContext(data),
    ```

    **Export context signal for App.tsx consumption.** The focused pane's context needs to reach the ContextPanel in App.tsx. PaneComponent already communicates budget via its signal. For context, the simplest approach matching F4-CONTEXT D-02 (per-pane scope, content switches on focus): expose the context getter via PaneProps callback, same pattern as focus/leaf-count callbacks on GridRoot.

    Add to `PaneProps`:
    ```typescript
    onContextChange?: (data: ContextData | null) => void;
    ```

    Add an effect to fire the callback when context changes. After the context signal creation:
    ```typescript
    // (Use createEffect imported from solid-js)
    ```
    Actually, the simplest approach: call `props.onContextChange?.(data)` inside the `onContextUpdate` callback directly:
    ```typescript
    onContextUpdate: (data) => {
      setContext(data);
      props.onContextChange?.(data);
    },
    ```
  </action>
  <acceptance_criteria>
    - `grep -c "ContextData" apps/voss-app/src/pane/PaneComponent.tsx` returns at least 2 (import + signal type)
    - `grep -c "setContext" apps/voss-app/src/pane/PaneComponent.tsx` returns at least 1
    - `grep -c "onContextUpdate" apps/voss-app/src/pane/PaneComponent.tsx` returns at least 1
    - `grep -c "onContextChange" apps/voss-app/src/pane/PaneComponent.tsx` returns at least 2 (prop + usage)
    - `tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Create ContextPanel.tsx component</name>
  <files>apps/voss-app/src/components/ContextPanel.tsx, apps/voss-app/src/components/ContextPanel.css</files>
  <read_first>
    - apps/voss-app/src/grid/BudgetPopover.tsx (pattern reference for data display component)
    - apps/voss-app/src/grid/BudgetBar.tsx (pattern reference for progress bar)
    - apps/voss-app/src/styles/variant-b.css (semantic tokens: --accent, --warning, --error, --text-3, --bg-2)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-01 through D-17 — full panel spec)
  </read_first>
  <action>
    **Create `apps/voss-app/src/components/ContextPanel.tsx`.**

    Props interface:
    ```typescript
    export interface ContextPanelProps {
      open: boolean;
      context: ContextData | null;
      paneIndex?: number;
      paneCwd?: string;
      isAgentPane: boolean;
      onTogglePin?: (path: string, pinned: boolean) => void;
    }
    ```

    Component structure (D-01 through D-17):
    - **Outer wrapper:** Fixed 240px wide (D-05), position absolute, right edge, top to bottom of grid area, z-index below overlays (D-11). CSS `transform: translateX(100%)` when closed, `translateX(0)` when open, `transition: transform 150ms ease-out` (D-07). `prefers-reduced-motion` kill switch removes transition.
    - **Header (D-04):** `"Context"` + dot with pane index + cwd basename. Uses `--text-1` for label, `--text-3` for meta.
    - **Summary row (D-12):** `"X / Yk tokens"` with a progress bar. Bar uses F3 3-tier color thresholds: 0-70% `--accent`, 70-90% `--warning`, 90-100% `--error`. Only shows if `token_limit` is present.
    - **System/conversation rows (D-17):** Two special rows at top: "System prompt" with `system_tokens` count, "Conversation" with `conversation_tokens` count. Different icon/style from file rows (use `--text-3` color, no pin button).
    - **File list (D-13, D-15, D-16):** `<For each={...}>` over `context.files` (already sorted by tokens desc from Python emission). Each row:
      - Left: filename (left-truncated per D-16 — show `...parent/file.ext` if path long). Title attribute = full path.
      - Right: token count formatted as `"1.2k"` for >999.
      - Mini proportional bar (40px wide): fill = `file.tokens / total_tokens`.
      - State indicator: `--accent` dot for "full", `--warning` dot for "compressed", `--text-3` dot for "dropped".
      - Pin button: small icon, toggleable. Calls `onTogglePin(path, !pinned)` on click. Pinned files get subtle `--bg-2` background tint.
    - **Empty state (D-08):** When `!isAgentPane` or `context === null`, show muted text: "No agent context" in `--text-3`.

    **Create `apps/voss-app/src/components/ContextPanel.css`** with styles for:
    - `.context-panel` — the outer container with transform transition
    - `.context-panel-header` — 28px header bar
    - `.context-summary` — summary row with progress bar
    - `.context-file-row` — individual file entry
    - `.context-file-bar` — mini proportional bar per file
    - `.context-pin-btn` — pin toggle button
    - `.context-empty` — empty state message
    - `@media (prefers-reduced-motion: reduce)` — remove transition (D-07)
  </action>
  <acceptance_criteria>
    - `ContextPanel.tsx` exports a default component with the specified props
    - Component renders summary bar, system/conversation rows, file list with pin buttons, and empty state
    - CSS file exists with panel width 240px, 150ms transform transition, and reduced-motion override
    - `tsc --noEmit` exits 0
    - `grep -c "prefers-reduced-motion" apps/voss-app/src/components/ContextPanel.css` returns at least 1
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Mount ContextPanel in App.tsx + Cmd+I keybind + focused pane routing</name>
  <files>apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx (lines 890-1025 — return JSX, StatusBar mount, grid area)
    - apps/voss-app/src/App.tsx (lines 758-812 — onAppKey keydown handler)
    - apps/voss-app/src/App.tsx (lines 227-228 — focusedPaneId signal)
    - apps/voss-app/src/grid/GridRoot.tsx (check if onContextChange callback prop exists or needs threading)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-01, D-02, D-03, D-09 — panel hosting, per-pane scope, overlay, toggle)
  </read_first>
  <action>
    **Add imports:**
    ```typescript
    import ContextPanel from './components/ContextPanel';
    import type { ContextData } from './pane/pty-ipc';
    ```

    **Add panel state signals** (near existing signals like `focusedPaneId`, around line 227):
    ```typescript
    const [contextPanelOpen, setContextPanelOpen] = createSignal(false);
    const [focusedContext, setFocusedContext] = createSignal<ContextData | null>(null);
    const [focusedIsAgent, setFocusedIsAgent] = createSignal(false);
    ```

    **Add Cmd+I keybind** to the `onAppKey` handler. Before the chord-based dispatch (around line 808), add:
    ```typescript
    if (chord === 'Cmd+I') {
      setContextPanelOpen((prev) => !prev);
      e.preventDefault();
      e.stopImmediatePropagation();
      return;
    }
    ```

    **Route focused pane context to panel.** The context data needs to flow from the focused pane's PaneComponent to App.tsx. This requires threading an `onContextChange` callback through GridRoot to PaneComponent. Check if GridRoot already has a callback for this — if not, add a new prop `onContextChange?: (data: ContextData | null) => void` to GridRoot and thread it to PaneComponent for the focused leaf. In the GridRoot `onFocusChange` callback (line 979), also update `focusedIsAgent` based on the focused pane's agent config.

    **Alternative simpler approach (if GridRoot threading is complex):** Use a global signal registry keyed by paneId. When PaneComponent receives context data, it stores in the registry. App.tsx reads from the registry using `focusedPaneId()`. This avoids modifying GridRoot. Implement as a simple module-level `Map<string, ContextData>` with reactive wrapper, same pattern as `procRegistry.ts`.

    Choose the simpler approach that avoids touching GridRoot internals. Create `apps/voss-app/src/pane/contextRegistry.ts`:
    ```typescript
    import { createSignal } from 'solid-js';
    const [store, setStore] = createSignal<Record<string, ContextData>>({});
    export function registerPaneContext(paneId: string, data: ContextData) { ... }
    export function unregisterPaneContext(paneId: string) { ... }
    export function contextByPaneId() { return store(); }
    ```
    PaneComponent calls `registerPaneContext` in `onContextUpdate`. App.tsx reads `contextByPaneId()[focusedPaneId()]`.

    **Mount ContextPanel** in the return JSX. Place it as an absolute-positioned sibling inside the grid area container (D-03 — overlay, not reflow). Position after the `<For each={workspaceIds()}>` block but inside the grid container div:
    ```tsx
    <ContextPanel
      open={contextPanelOpen()}
      context={focusedPaneId() ? contextByPaneId()[focusedPaneId()!] ?? null : null}
      isAgentPane={focusedIsAgent()}
      paneIndex={...}
      paneCwd={...}
    />
    ```

    The grid container div (around line 938) needs `position: relative` for the absolute-positioned panel to anchor to.
  </action>
  <acceptance_criteria>
    - `grep -c "ContextPanel" apps/voss-app/src/App.tsx` returns at least 2 (import + JSX)
    - `grep -c "contextPanelOpen" apps/voss-app/src/App.tsx` returns at least 3 (signal + toggle + prop)
    - `grep -c "Cmd+I" apps/voss-app/src/App.tsx` returns at least 1 (keybind handler)
    - Pressing Cmd+I toggles the context panel open/closed
    - Panel shows focused pane's context data, switching on focus change
    - `tsc --noEmit` exits 0
    - `vitest run` passes (or no test regressions)
  </acceptance_criteria>
</task>

</tasks>

<must_haves>
  truths:
    - "pty-ipc.ts handles context_update events and routes to onContextUpdate callback"
    - "PaneComponent stores context data in a local signal via onContextUpdate"
    - "ContextPanel renders file list sorted by token count with state color indicators"
    - "ContextPanel shows empty state when shell pane is focused or context is null (D-08)"
    - "ContextPanel is 240px fixed width, slides with 150ms CSS transition, respects prefers-reduced-motion (D-05, D-07)"
    - "Cmd+I toggles panel open/closed globally (D-01)"
    - "Panel content switches to focused pane's context on focus change (D-02)"
    - "Panel overlays grid right edge, grid does not reflow (D-03)"
  artifacts:
    - path: "apps/voss-app/src/pane/pty-ipc.ts"
      provides: "ContextData type + FileContextEntry type + context_update PtyEvent case + onContextUpdate callback"
      contains: "context_update"
    - path: "apps/voss-app/src/pane/PaneComponent.tsx"
      provides: "Context signal + onContextUpdate wiring + registry integration"
      contains: "setContext"
    - path: "apps/voss-app/src/components/ContextPanel.tsx"
      provides: "Side panel overlay with file list, summary bar, pin buttons, empty state"
      contains: "ContextPanel"
    - path: "apps/voss-app/src/components/ContextPanel.css"
      provides: "Panel styles: 240px width, transform slide, reduced-motion, state colors"
      contains: "context-panel"
    - path: "apps/voss-app/src/App.tsx"
      provides: "ContextPanel mount + Cmd+I keybind + focused pane context routing"
      contains: "contextPanelOpen"
  key_links:
    - from: "apps/voss-app/src/pane/pty-ipc.ts"
      to: "crates/voss-app-core/src/pty/commands.rs"
      via: "PtyEvent type: context_update mirrors Rust PtyEvent::ContextUpdate serde output"
      pattern: "context_update"
    - from: "apps/voss-app/src/components/ContextPanel.tsx"
      to: "apps/voss-app/src/pane/pty-ipc.ts"
      via: "import { type ContextData, type FileContextEntry }"
      pattern: "ContextData"
</must_haves>
