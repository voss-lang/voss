---
phase: F4
plan_id: F4-04
title: "Status bar toggle + settings persistence + pin IPC + integration verification"
wave: 3
depends_on: [F4-03]
files_modified:
  - apps/voss-app/src/components/StatusBar.tsx
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src-tauri/src/commands.rs
autonomous: true
status: pending
---

<objective>
Complete the F4 feature surface: add a context panel toggle button to the StatusBar, persist panel open/closed state across restarts via settings.json, implement the pin command IPC flow (click pin in ContextPanel -> Tauri command -> write `.voss/context-pins.json`), and verify the full end-to-end integration.

Purpose: Without the status bar toggle, users have no visual affordance for the panel beyond the keyboard shortcut. Without settings persistence, panel state resets on restart. Without pin IPC, the pin buttons in ContextPanel are inert.

Output: StatusBar toggle button, settings read/write for `contextPanel.open`, Tauri command for pin file writes, verified full data flow.
</objective>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| StatusBar click -> App.tsx signal | UI event toggle, same process |
| ContextPanel pin click -> Tauri command -> filesystem | User action writes `.voss/context-pins.json` in the workspace |
| Settings read/write -> `~/.config/voss-app/settings.json` | Persist panel state across app restarts |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-F4-12 | Tampering | context-pins.json write | mitigate | Atomic write (write-then-rename) prevents partial reads. Path validated server-side. |
| T-F4-13 | Tampering | settings.json write | accept | Same trust model as existing settings. Local filesystem only. |
| T-F4-14 | Race | Pin file concurrent write | mitigate | Write-then-rename is atomic on POSIX. Only one writer (ADE) at a time. |
| T-F4-15 | Elevation | Pin path traversal | mitigate | Pin paths validated against ContextData.files (D-22). Tauri command rejects paths not in the current context snapshot. |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add context panel toggle button to StatusBar.tsx</name>
  <files>apps/voss-app/src/components/StatusBar.tsx</files>
  <read_first>
    - apps/voss-app/src/components/StatusBar.tsx (full file — 81 lines)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-09 — status bar right cluster toggle button)
    - .planning/phases/A10-voss-app-status-bar/A10-CONTEXT.md (if exists — status bar right cluster design)
  </read_first>
  <action>
    **Extend `StatusBarProps`** with two new props:
    ```typescript
    contextPanelOpen: boolean;
    onToggleContextPanel: () => void;
    ```

    **Add toggle button** in the right section of the StatusBar (before the git branch display, inside the right `<div>`). The button:
    - Text: a compact icon/label. Use `"Ctx"` or a sidebar icon character. Style as a small pill/button matching the status bar aesthetic.
    - `onClick` calls `props.onToggleContextPanel()`.
    - Visual state: when `props.contextPanelOpen` is true, apply an active/highlighted style (e.g., `color: var(--accent)` or `background: var(--bg-2)`).
    - Style: inline with status bar — 11px font, no border, subtle hover.
    - Title attribute: `"Toggle context panel (Cmd+I)"` for discoverability.

    ```tsx
    <button
      type="button"
      title="Toggle context panel (Cmd+I)"
      onClick={() => props.onToggleContextPanel()}
      style={{
        background: props.contextPanelOpen ? 'var(--bg-2)' : 'transparent',
        color: props.contextPanelOpen ? 'var(--accent)' : 'var(--fg-2)',
        border: 'none',
        'font-family': 'var(--font-mono)',
        'font-size': '11px',
        cursor: 'pointer',
        padding: '0 6px',
        'border-radius': '3px',
        'margin-right': '8px',
      }}
    >
      Ctx
    </button>
    ```
  </action>
  <acceptance_criteria>
    - `grep -c "contextPanelOpen" apps/voss-app/src/components/StatusBar.tsx` returns at least 2 (prop + usage)
    - `grep -c "onToggleContextPanel" apps/voss-app/src/components/StatusBar.tsx` returns at least 2 (prop + handler)
    - Button renders in the status bar right section with correct active/inactive styling
    - `tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Wire StatusBar toggle props in App.tsx</name>
  <files>apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx (lines 992-999 — StatusBar mount)
    - apps/voss-app/src/App.tsx (contextPanelOpen signal from F4-03)
  </read_first>
  <action>
    **Update the StatusBar JSX** (around line 992) to pass the new props:
    ```tsx
    <StatusBar
      workspaceName={...}
      paneCount={paneCount()}
      focusedPaneId={focusedPaneId()}
      gitBranch={activeMounted()?.project()?.gitBranch}
      contextPanelOpen={contextPanelOpen()}
      onToggleContextPanel={() => setContextPanelOpen((prev) => !prev)}
    />
    ```
  </action>
  <acceptance_criteria>
    - `grep -c "contextPanelOpen" apps/voss-app/src/App.tsx` includes the StatusBar prop pass
    - `grep -c "onToggleContextPanel" apps/voss-app/src/App.tsx` returns at least 1
    - Clicking the StatusBar toggle button opens/closes the ContextPanel
    - `tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Settings persistence for contextPanel.open</name>
  <files>apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx (onMount handler around line 817 for existing settings loading patterns)
    - apps/voss-app/src/appearance/settings.ts (pattern reference for settings read/write — loadAppearanceSettings)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-06 — persist in ~/.config/voss-app/settings.json)
    - .planning/phases/F4-visual-context-heatmap/F4-RESEARCH.md (OQ-4 — A9 not executed yet, implement minimal settings)
  </read_first>
  <action>
    **Settings read on mount.** In the `onMount` handler, after existing initialization, add:
    ```typescript
    try {
      const settings = await invoke<Record<string, unknown>>('read_settings_json', {});
      if (settings && typeof settings.contextPanelOpen === 'boolean') {
        setContextPanelOpen(settings.contextPanelOpen);
      }
    } catch { /* settings file missing or unreadable — use default (closed) */ }
    ```

    If a `read_settings_json` Tauri command does not exist, create a minimal Rust command that reads `~/.config/voss-app/settings.json` and returns its contents as a JSON value. Alternatively, use `invoke('read_file', { path: settingsPath })` if such a generic command exists. Check existing commands first.

    **Settings write on toggle.** When `contextPanelOpen` changes, write to settings. Wrap the toggle in a helper:
    ```typescript
    const toggleContextPanel = () => {
      setContextPanelOpen((prev) => {
        const next = !prev;
        void invoke('write_settings_json', { key: 'contextPanelOpen', value: next }).catch(() => {});
        return next;
      });
    };
    ```
    Use `toggleContextPanel` in both the Cmd+I handler and the StatusBar `onToggleContextPanel` prop.

    If `write_settings_json` doesn't exist, implement a minimal Tauri command that reads `~/.config/voss-app/settings.json`, updates the specified key, and writes back atomically. This is forward-compatible with A9 (which will formalize the settings schema).

    **Simpler alternative if no Rust command exists:** Use `localStorage` as a temporary persistence layer. `localStorage.setItem('voss:contextPanelOpen', String(next))` on toggle, `localStorage.getItem('voss:contextPanelOpen') === 'true'` on mount. This avoids new Rust code but doesn't persist across different Tauri windows. Acceptable for F4 MVP; A9 will migrate to proper settings.json.

    Choose the simplest approach: if settings commands already exist, use them. Otherwise use localStorage.
  </action>
  <acceptance_criteria>
    - Panel open/closed state persists across app restart (either via settings.json or localStorage)
    - Both Cmd+I and StatusBar toggle use the same persistence path
    - No crash if settings file is missing or corrupt (graceful fallback to default closed)
    - `tsc --noEmit` exits 0
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Pin command IPC — Tauri command to write context-pins.json</name>
  <files>apps/voss-app/src/components/ContextPanel.tsx, apps/voss-app/src-tauri/src/commands.rs (or appropriate Rust command file)</files>
  <read_first>
    - apps/voss-app/src/components/ContextPanel.tsx (onTogglePin prop from F4-03)
    - crates/voss-app-core/src/pty/commands.rs (existing Tauri command patterns)
    - .planning/phases/F4-visual-context-heatmap/F4-RESEARCH.md (lines 126-137 — file-based pin channel, atomic write)
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (D-19 DEVIATION, D-20, D-21, D-22 — pin behavior)
  </read_first>
  <action>
    **Add a Tauri command `write_context_pins`** in the appropriate Rust command file. The command:
    - Takes `workspace_path: String` and `pinned_paths: Vec<String>` as parameters.
    - Constructs the path: `{workspace_path}/.voss/context-pins.json`.
    - Creates `.voss/` directory if needed (`std::fs::create_dir_all`).
    - Writes JSON atomically: write to `context-pins.json.tmp`, then rename to `context-pins.json`. Format: `{"pinned": ["path1", "path2"]}`.
    - Returns `Ok(())` or error string.

    **Register the command** in the Tauri plugin/builder.

    **Wire ContextPanel pin click** to invoke the Tauri command. In App.tsx (where ContextPanel is mounted), pass the `onTogglePin` handler:
    ```typescript
    onTogglePin={(path, pinned) => {
      const ctx = focusedContext();
      if (!ctx) return;
      // Compute new pinned set
      const currentPinned = ctx.files.filter(f => f.pinned).map(f => f.path);
      const next = pinned
        ? [...new Set([...currentPinned, path])]
        : currentPinned.filter(p => p !== path);
      const wp = workspacePath();
      if (wp) {
        void invoke('write_context_pins', { workspacePath: wp, pinnedPaths: next });
      }
      // Optimistic UI update: toggle pin in local context signal
      setFocusedContext(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          files: prev.files.map(f =>
            f.path === path ? { ...f, pinned } : f
          ),
        };
      });
    }}
    ```

    Pin takes effect next iteration (D-20) — the harness reads the file on next loop entry. The optimistic UI update shows the pin state immediately in the panel. The next context OSC emission from the harness confirms the pin via `pinned: true` in the snapshot (D-27).
  </action>
  <acceptance_criteria>
    - `grep -c "write_context_pins" apps/voss-app/src/App.tsx` returns at least 1
    - Clicking a pin button in ContextPanel invokes the Tauri command with the correct pinned paths
    - Pin file is written atomically (write-then-rename pattern)
    - Optimistic UI update shows pin state toggle immediately
    - `tsc --noEmit` exits 0
    - `cargo build` exits 0 (Rust command compiles)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 5: Full integration verification</name>
  <files>(verification only — no new code)</files>
  <read_first>
    - .planning/phases/F4-visual-context-heatmap/F4-CONTEXT.md (all decisions D-01..D-27)
    - .planning/phases/F4-visual-context-heatmap/F4-RESEARCH.md (test seams T-F4-01..T-F4-14)
  </read_first>
  <action>
    **Run all gate checks:**
    1. `cargo test -p voss-app-core` — all Rust tests pass (F3 budget + F4 context).
    2. `cargo build` — full workspace compiles clean.
    3. `cd apps/voss-app && npx tsc --noEmit` — zero TypeScript errors.
    4. `cd apps/voss-app && npx vitest run` — all frontend tests pass.
    5. `.venv/bin/python -m pytest voss/harness/test_context_osc.py -v` — all Python context tests pass.
    6. `.venv/bin/python -m pytest voss/harness/test_budget_osc.py -v` — F3 budget tests still pass (no regression).

    **Verify D-19 deviation is documented.** Confirm that:
    - No code references "PTY stdin injection" for pin commands.
    - Pin flow uses `.voss/context-pins.json` file-based channel.
    - F4-02 PLAN.md documents the deviation.

    **Verify decision coverage** — spot-check each D-XX decision against the implementation:
    - D-01: Panel toggles via Cmd+I or status bar button.
    - D-02: Panel shows focused pane context, switches on focus change.
    - D-03: Panel overlays grid, grid does not reflow.
    - D-05: Panel is 240px fixed width.
    - D-07: 150ms CSS slide with reduced-motion kill switch.
    - D-08: Empty state for shell panes.
    - D-12: Summary row with progress bar.
    - D-14: Three-state model (full/compressed/dropped).
    - D-15: Sorted by token count descending.
    - D-23: voss-context= OSC type.
    - D-25: Payload matches specified shape.
    - D-26: Full snapshot each emission.
  </action>
  <acceptance_criteria>
    - `cargo test -p voss-app-core` exits 0 with all tests passing
    - `cargo build` exits 0 with no warnings on F4 code
    - `tsc --noEmit` exits 0
    - `vitest run` exits 0 (or no test regressions)
    - `.venv/bin/python -m pytest voss/harness/test_context_osc.py -v` shows all tests passing
    - `.venv/bin/python -m pytest voss/harness/test_budget_osc.py -v` shows no regressions
    - No code references "PTY stdin injection" — only file-based pin channel exists
  </acceptance_criteria>
</task>

</tasks>

<must_haves>
  truths:
    - "StatusBar has a toggle button that opens/closes the ContextPanel (D-09)"
    - "Panel open/closed state persists across app restart (D-06)"
    - "Pin click writes .voss/context-pins.json atomically and shows optimistic UI update"
    - "Pin takes effect next iteration — harness reads file at iteration start (D-20)"
    - "Pin only applies to files already in context (D-22) — enforced both client and server side"
    - "All gate checks pass: cargo test, cargo build, tsc, vitest, pytest"
    - "D-19 deviation documented: file-based pin channel replaces PTY stdin injection"
  artifacts:
    - path: "apps/voss-app/src/components/StatusBar.tsx"
      provides: "Context panel toggle button in right cluster"
      contains: "onToggleContextPanel"
    - path: "apps/voss-app/src/App.tsx"
      provides: "Settings persistence + StatusBar toggle wiring + pin IPC handler"
      contains: "write_context_pins"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/components/StatusBar.tsx"
      via: "contextPanelOpen prop + onToggleContextPanel callback"
      pattern: "contextPanelOpen"
    - from: "apps/voss-app/src/components/ContextPanel.tsx"
      to: "apps/voss-app/src/App.tsx"
      via: "onTogglePin callback -> invoke('write_context_pins')"
      pattern: "write_context_pins"
</must_haves>
