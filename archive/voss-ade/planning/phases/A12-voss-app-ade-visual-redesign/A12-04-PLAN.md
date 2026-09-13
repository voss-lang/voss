---
phase: A12-voss-app-ade-visual-redesign
plan: 04
type: execute
wave: 3
depends_on:
  - A12-03
files_modified:
  - apps/voss-app/src/components/modal/AgentLaunchModal.tsx
  - apps/voss-app/src/components/modal/modal.css
  - apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx
  - apps/voss-app/src/components/sidebar/AgentContextMenu.tsx
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src-tauri/src/lib.rs
autonomous: true
requirements:
  - ADE-04

must_haves:
  truths:
    - "Clicking + Agent button opens a centered modal overlay"
    - "Modal shows 6 CLI preset tabs: Claude, Codex, Antigravity, OpenCode, Voss, Custom"
    - "Selecting Claude/Codex/Antigravity/OpenCode shows generic agent config panel"
    - "Selecting Voss shows Voss-specific config panel (command/mode/auth/task)"
    - "Selecting Custom shows name + command inputs for custom CLI registration"
    - "Launch Agent button spawns agent by splitting from focused pane"
    - "Escape dismisses modal"
    - "Ctrl+Enter submits the modal"
    - "Right-click on agent item shows context menu with Stop/Restart/Detach/Copy cost/Focus pane"
    - "Custom CLIs are persisted in settings.json via Tauri commands"
  artifacts:
    - path: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      provides: "Agent launch modal with 6 CLI presets and context-sensitive config panels"
      exports: ["AgentLaunchModal"]
    - path: "apps/voss-app/src/components/modal/modal.css"
      provides: "Modal overlay styles"
    - path: "apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx"
      provides: "Modal unit tests"
    - path: "apps/voss-app/src/components/sidebar/AgentContextMenu.tsx"
      provides: "Agent right-click context menu with 5 actions per D-23"
      exports: ["AgentContextMenu"]
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      via: "Show when agentModalOpen"
      pattern: "<AgentLaunchModal"
    - from: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      to: "apps/voss-app/src/App.tsx"
      via: "onLaunch callback with spawn config"
      pattern: "onLaunch"
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/components/sidebar/AgentContextMenu.tsx"
      via: "onAgentContextMenu callback renders menu"
      pattern: "<AgentContextMenu"
    - from: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      to: "apps/voss-app/src-tauri/src/lib.rs"
      via: "invoke save_custom_agents on Custom tab submit"
      pattern: "save_custom_agents"
---

<objective>
Build the Agent Launch Modal with 6 CLI presets, context-sensitive config panels (generic vs Voss-specific vs Custom), and wire it into App.tsx via the + Agent button callback. Agent spawns by splitting from the focused pane. Add right-click context menu on agent items (D-23). Persist custom CLIs in settings.json (D-21).

Purpose: This is the primary UX for starting new agent sessions — the agent launch flow that makes Voss an ADE rather than a terminal multiplexer.
Output: AgentLaunchModal.tsx, modal.css, AgentContextMenu.tsx, Rust persistence commands, tests, App.tsx wiring.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-CONTEXT.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-03-SUMMARY.md

<interfaces>
<!-- Existing spawn_agent Tauri command (from App.tsx context) -->
invoke<void>('spawn_agent', { paneId, cliBinary, cliArgs, cwd, workspacePath })
- cliBinary: string (e.g. "claude", "codex")
- cliArgs: string[] (e.g. ["--model", "opus", "--task", "fix the bug"])
- The existing split flow: gridController().splitFocused('H') creates a new pane, then spawn_agent is called for that pane

<!-- Voss CLI commands from crates/voss-cli/src/lib.rs -->
Cmd enum: Chat (default), Do { task, mode, yes, auth }, Agent { cmd: AgentCmd::Spawn }, Skill { cmd: SkillCmd::Run }, Resume { id }
- Relevant for modal: chat, do, agent spawn, resume
- Sessions/Plugins/Skills are listing commands, not user tasks

<!-- CommandPalette.tsx pattern for modal overlay -->
Fixed position overlay, backdrop rgba(0,0,0,0.6), panel ref for click-outside, role="dialog" aria-modal="true", Escape handler, focus trap via onMount

<!-- Popover.tsx pattern for context menu (from grid/) -->
Popover(props: { anchor: HTMLElement, onClose: () => void, children: JSX.Element })
- Fixed position, anchored below + left-aligned to anchor element
- Document click-outside handler (captures), Escape handler
- z-index 20, --bg-3 background, --border border, 11px font

<!-- Existing SettingsFile struct (src-tauri/src/lib.rs) -->
struct SettingsFile { theme: Option<HashMap<String, String>> }
- settings_path() resolves to ~/.config/voss-app/settings.json
- get_theme_overrides reads theme from SettingsFile

<!-- Existing Tauri commands for killing agents -->
invoke('pty_kill', { id: paneId }) - kills the PTY process
invoke('mark_agent_stopped', { ... }) - marks agent as stopped in SQLite registry
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create AgentLaunchModal component with config panels</name>
  <files>
    apps/voss-app/src/components/modal/AgentLaunchModal.tsx,
    apps/voss-app/src/components/modal/modal.css
  </files>
  <read_first>
    apps/voss-app/src/command-palette/CommandPalette.tsx (modal overlay pattern),
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md (Agent Launch Modal contract),
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-CONTEXT.md (D-14 through D-21),
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md (Finding 9: Voss CLI Cmd enum)
  </read_first>
  <action>
    1. Create apps/voss-app/src/components/modal/modal.css:
       - .modal-backdrop: fixed inset 0, background rgba(0,0,0,0.6), z-index 100, display flex, align-items center, justify-content center
       - .modal-panel: width 480px, max-height 80vh, background var(--bg-3), border 1px solid var(--border-bright), border-radius 0 (panel style per UI-SPEC), overflow hidden, display flex, flex-direction column
       - .modal-panel--enter: opacity 0, transform scale(0.96); transition 150ms ease-out
       - .modal-panel--visible: opacity 1, transform scale(1)
       - .modal-header: height 48px, display flex, align-items center, padding 0 16px, border-bottom 1px solid var(--border)
       - .modal-tabs: display flex, gap 0, padding 0 16px, border-bottom 1px solid var(--border), overflow-x auto
       - .modal-tab: padding 8px 12px, font-family Inter, font-size 11px, font-weight 500, color var(--fg-2), cursor pointer, border none, background transparent, border-bottom 2px solid transparent, white-space nowrap
       - .modal-tab--active: color var(--fg-0), border-bottom-color var(--focus)
       - .modal-body: padding 16px, overflow-y auto, flex 1
       - .modal-footer: display flex, align-items center, justify-content space-between, padding 12px 16px, border-top 1px solid var(--border)
       - .modal-field: width 100%, padding 8px, background var(--bg-2), border 1px solid var(--border), color var(--fg-0), font-family Inter, font-size 12px; focus: outline none, border-color var(--focus), box-shadow 0 0 0 2px var(--focus-glow)
       - .modal-field--mono: font-family var(--font-mono)
       - .modal-textarea: min-height 64px, resize vertical
       - .modal-btn-primary: background var(--focus), color white, border none, padding 6px 16px, font-family var(--font-display), font-size 13px, font-weight 500, cursor pointer; border-radius 3px via inline style; hover background var(--focus-hover)
       - .modal-segmented: display flex, gap 0; child buttons get --bg-2 background, --fg-2 color, active gets --focus background, --fg-0 color
       All border-radius on interactive elements via inline style (per RESEARCH Finding 10 -- global reset).

    2. Create apps/voss-app/src/components/modal/AgentLaunchModal.tsx:

       Props: onDismiss callback, onLaunch callback (config: { cliBinary: string, cliArgs: string[], taskPrompt: string }), customAgents (array of { name: string, command: string }), onSaveCustomAgent callback (agent: { name: string, command: string })

       State signals:
       - activeTab: createSignal of 'claude' | 'codex' | 'antigravity' | 'opencode' | 'voss' | 'custom' (default 'claude')
       - model: createSignal string (default empty for auto-detect)
       - effort: createSignal 'low' | 'medium' | 'high' (default 'medium')
       - planMode: createSignal boolean (default false)
       - skipPermissions: createSignal boolean (default false)
       - taskPrompt: createSignal string (default empty)
       - vossCommand: createSignal 'chat' | 'do' | 'resume' | 'agent' (default 'chat')
       - vossMode: createSignal 'edit' | 'plan' (default 'edit')
       - vossAuth: createSignal string (default empty)
       - customName: createSignal string (default empty)
       - customCommand: createSignal string (default empty)

       Layout:
       - Backdrop div with .modal-backdrop, onClick on backdrop (not panel) calls onDismiss per D-14
       - Panel div with .modal-panel, ref for click-outside, role="dialog", aria-modal="true", aria-labelledby="modal-title"
       - Header: "New Agent Session" title in Poppins 600 16px --fg-0, dismiss X button top-right with aria-label="Dismiss"
       - Tab row: 6 tabs (Claude, Codex, Antigravity, OpenCode, Voss, Custom) -- each gets .modal-tab, active gets .modal-tab--active per D-15
       - Body: conditionally render panel based on activeTab:
         * claude/codex/antigravity/opencode -> GenericAgentPanel: model selector button group (for Claude: opus/sonnet/haiku; Codex: default; others: default), effort segmented control (low/medium/high), Plan Mode toggle, Skip Permissions toggle, task prompt textarea with placeholder "Describe the task (optional -- leave blank for interactive mode)" per D-16/D-17/D-18
         * voss -> VossAgentPanel: command segmented (chat/do/resume/agent), mode segmented (edit/plan), auth field, task prompt textarea per D-16
         * custom -> CustomPanel: name input (placeholder "e.g. my-agent"), command input (JetBrains Mono, placeholder "e.g. /usr/local/bin/my-agent") per D-21. On submit, call props.onSaveCustomAgent to persist in settings per D-21.
       - Footer: left "Press Ctrl+Enter to start" hint (Inter 11px --fg-3), right "Launch Agent" primary button (.modal-btn-primary)

       Key handling:
       - Escape -> onDismiss per D-14
       - Ctrl+Enter -> submit (build config and call onLaunch)

       Submit logic (buildLaunchConfig):
       - For generic tabs: cliBinary = tab name (claude/codex/gemini for antigravity/opencode), cliArgs built from model (--model X), effort, planMode (--plan), skipPermissions (--dangerously-skip-permissions for Claude, --skip-review for others). Task prompt appended as positional arg if non-empty per D-18.
       - For voss tab: cliBinary = 'voss', cliArgs built from vossCommand (do/chat/resume/agent spawn) + vossMode + vossAuth + task
       - For custom tab: cliBinary = customCommand, cliArgs = [] (or split command string into binary + args), name stored for future reference per D-21. Call onSaveCustomAgent({ name: customName(), command: customCommand() }) to persist.
       - SECURITY: cliBinary and cliArgs passed as separate values to the onLaunch callback -- NEVER joined into a single shell string. spawn_agent already takes them separately (RESEARCH Security Domain).

       Focus trap: onMount focus the first tab button. Tab/Shift+Tab cycle within modal panel.
       Animation: .modal-panel--enter on mount, requestAnimationFrame to add .modal-panel--visible. Respects prefers-reduced-motion (inherited from global index.css kill switch per RESEARCH Finding 8).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <acceptance_criteria>
    - AgentLaunchModal.tsx renders 6 tabs per D-15
    - Generic panel shows model selector, effort, plan mode, skip permissions, task prompt per D-16/D-17
    - Voss panel shows command/mode/auth/task per D-16
    - Custom panel shows name + command inputs per D-21
    - Custom tab submit calls onSaveCustomAgent to persist per D-21
    - Escape dismisses, Ctrl+Enter submits
    - Submit builds cliBinary + cliArgs as separate values (never shell string)
    - Modal has role="dialog", aria-modal="true", aria-labelledby, dismiss aria-label
    - TypeScript compiles
  </acceptance_criteria>
  <done>AgentLaunchModal component with 6 tabs, context-sensitive panels, keyboard handling, accessibility, and custom CLI save callback.</done>
</task>

<task type="auto">
  <name>Task 2: Wire modal into App.tsx and add tests</name>
  <files>
    apps/voss-app/src/App.tsx,
    apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx
  </files>
  <read_first>
    apps/voss-app/src/App.tsx,
    apps/voss-app/src/components/modal/AgentLaunchModal.tsx,
    apps/voss-app/src/grid/__tests__/GridRoot.test.tsx (test patterns)
  </read_first>
  <action>
    1. In App.tsx:
       - Add createSignal for agentModalOpen (default false)
       - Import AgentLaunchModal from './components/modal/AgentLaunchModal'
       - Update the onLaunchAgent callback passed to AgentSidebar: () => setAgentModalOpen(true)
       - Add handleLaunchAgent function: receives config from modal, calls setAgentModalOpen(false), then calls gridController()?.splitFocused('H') to create a new pane per D-19, then invokes spawn_agent Tauri command with the config (cliBinary, cliArgs, cwd from workspacePath)
       - Render AgentLaunchModal inside Show(when=agentModalOpen()) at the same level as CommandPalette (after ToastStack), with onDismiss={() => setAgentModalOpen(false)} and onLaunch={handleLaunchAgent}

    2. Create apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx:
       - Test: "renders 6 CLI preset tabs" -- render modal, query for tab buttons, assert 6 found with text Claude/Codex/Antigravity/OpenCode/Voss/Custom
       - Test: "Escape calls onDismiss" -- render, dispatch Escape keydown, assert onDismiss called
       - Test: "switching to Voss tab shows Voss config" -- render, click Voss tab, assert command selector visible (chat/do/resume/agent text)
       - Test: "switching to Custom tab shows name and command inputs" -- render, click Custom tab, assert inputs with placeholder text present
       - Test: "Launch Agent button calls onLaunch" -- render, click Launch Agent button, assert onLaunch called with config object containing cliBinary and cliArgs
       - Test: "modal has correct ARIA attributes" -- assert role="dialog", aria-modal="true", aria-labelledby present
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run --grep "AgentLaunchModal" 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - App.tsx renders AgentLaunchModal when agentModalOpen is true
    - + Agent button in sidebar sets agentModalOpen(true)
    - Modal dismiss sets agentModalOpen(false)
    - Launch Agent triggers splitFocused('H') + spawn_agent per D-19
    - All modal tests pass
    - Full test suite passes
  </acceptance_criteria>
  <done>Agent launch modal wired into App.tsx. Spawns agents by splitting from focused pane. Tests pass.</done>
</task>

<task type="auto">
  <name>Task 3: Create AgentContextMenu with 5 actions (D-23)</name>
  <files>
    apps/voss-app/src/components/sidebar/AgentContextMenu.tsx,
    apps/voss-app/src/App.tsx
  </files>
  <read_first>
    apps/voss-app/src/grid/Popover.tsx (existing popover pattern),
    apps/voss-app/src/grid/DotMenu.tsx (menu item pattern),
    apps/voss-app/src/components/sidebar/AgentItem.tsx (context menu anchor),
    apps/voss-app/src/components/sidebar/AgentSidebar.tsx (onAgentContextMenu prop),
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-CONTEXT.md (D-23)
  </read_first>
  <action>
    1. Create apps/voss-app/src/components/sidebar/AgentContextMenu.tsx:

       Props interface AgentContextMenuProps:
       - anchor: HTMLElement (the element the menu is anchored to)
       - paneId: string (the agent pane this menu acts on)
       - costUsd: number (for Copy cost action)
       - onClose: () => void
       - onFocusPane: (paneId: string) => void
       - onStopAgent: (paneId: string) => void
       - onRestartAgent: (paneId: string) => void
       - onDetachAgent: (paneId: string) => void

       Use the existing Popover.tsx pattern from grid/. Import Popover from '../../grid/Popover'. Render Popover with anchor and onClose props. Inside, render a list of 5 menu action rows per D-23:

       a) "Stop" -- icon: square stop icon (CSS or Unicode). onClick: call onStopAgent(paneId), then onClose(). Invokes pty_kill for the pane.
       b) "Restart" -- icon: circular arrow. onClick: call onRestartAgent(paneId), then onClose(). Re-spawns the same agent CLI in the same pane.
       c) "Detach" -- icon: unlink/detach. onClick: call onDetachAgent(paneId), then onClose(). Marks pane as regular shell (removes from agent tracking).
       d) "Copy cost" -- icon: clipboard. onClick: navigator.clipboard.writeText("$" + costUsd.toFixed(2)), then onClose().
       e) "Focus pane" -- icon: target/crosshair. onClick: call onFocusPane(paneId), then onClose(). Calls gridController().focusPaneById(paneId).

       Each row: display flex, align-items center, padding 6px 12px, gap 8px, cursor pointer, color var(--fg-1), hover background var(--bg-2). Font Inter 11px. Border-radius 0 (inside popover). Separator line (1px --border) between "Detach" and "Copy cost" (actions vs info).

    2. In App.tsx, wire the context menu:
       - Add createSignal for contextMenuState: { paneId: string, anchor: HTMLElement, costUsd: number } | null (default null)
       - Update the onAgentContextMenu callback passed to AgentSidebar (currently a no-op stub from A12-03):
         (paneId: string, e: MouseEvent) => { e.preventDefault(); setContextMenuState({ paneId, anchor: e.currentTarget as HTMLElement, costUsd: budgetByPaneId()[paneId]?.cost_usd ?? 0 }); }
       - Render AgentContextMenu inside Show(when=contextMenuState()) with:
         anchor={contextMenuState()!.anchor}
         paneId={contextMenuState()!.paneId}
         costUsd={contextMenuState()!.costUsd}
         onClose={() => setContextMenuState(null)}
         onFocusPane={(id) => gridController()?.focusPaneById(id)}
         onStopAgent={(id) => invoke('pty_kill', { id })}
         onRestartAgent={(id) => { /* invoke pty_kill then re-spawn same agent config */ }}
         onDetachAgent={(id) => { /* remove from agentConfigByPaneId tracking */ }}
       - The AgentItem rows in AgentSidebar already have an onContextMenu prop passed from AgentSidebar's onAgentContextMenu; this wires the right-click event to the context menu state.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <acceptance_criteria>
    - Right-click on agent item in sidebar shows AgentContextMenu popover per D-23
    - Menu shows 5 actions: Stop, Restart, Detach, Copy cost, Focus pane
    - Stop invokes pty_kill for the agent pane
    - Copy cost writes formatted cost to clipboard
    - Focus pane calls gridController().focusPaneById
    - Menu dismisses on action click, click-outside, or Escape (Popover handles latter two)
    - TypeScript compiles
  </acceptance_criteria>
  <done>Agent context menu with 5 actions wired into sidebar per D-23.</done>
</task>

<task type="auto">
  <name>Task 4: Add custom CLI persistence to Rust settings (D-21)</name>
  <files>
    apps/voss-app/src-tauri/src/lib.rs,
    apps/voss-app/src/App.tsx
  </files>
  <read_first>
    apps/voss-app/src-tauri/src/lib.rs (SettingsFile struct, settings_path(), get_theme_overrides pattern),
    apps/voss-app/src/components/modal/AgentLaunchModal.tsx (onSaveCustomAgent callback)
  </read_first>
  <action>
    1. In src-tauri/src/lib.rs:
       a) Add a CustomAgent struct:
          #[derive(Debug, Deserialize, Serialize, Clone)]
          struct CustomAgent { name: String, command: String }

       b) Extend SettingsFile:
          struct SettingsFile {
              theme: Option<HashMap<String, String>>,
              custom_agents: Option<Vec<CustomAgent>>,
          }
          The Option + serde default ensures existing settings.json files without custom_agents parse correctly.

       c) Add load_custom_agents Tauri command:
          #[tauri::command]
          fn load_custom_agents() -> Vec<CustomAgent> {
              let path = settings_path();
              if !path.exists() { return Vec::new(); }
              let raw = match std::fs::read_to_string(&path) {
                  Ok(s) => s,
                  Err(_) => return Vec::new(),
              };
              let settings: SettingsFile = match serde_json::from_str(&raw) {
                  Ok(s) => s,
                  Err(_) => return Vec::new(),
              };
              settings.custom_agents.unwrap_or_default()
          }

       d) Add save_custom_agents Tauri command:
          #[tauri::command]
          fn save_custom_agents(agents: Vec<CustomAgent>) -> Result<(), String> {
              let path = settings_path();
              // Read existing settings to preserve theme and other fields
              let mut settings: SettingsFile = if path.exists() {
                  std::fs::read_to_string(&path)
                      .ok()
                      .and_then(|raw| serde_json::from_str(&raw).ok())
                      .unwrap_or_default()
              } else { SettingsFile::default() };
              settings.custom_agents = Some(agents);
              // Ensure parent directory exists
              if let Some(parent) = path.parent() {
                  std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
              }
              let json = serde_json::to_string_pretty(&settings).map_err(|e| e.to_string())?;
              std::fs::write(&path, json).map_err(|e| e.to_string())?;
              Ok(())
          }

       e) Register both commands in tauri::generate_handler![...]:
          Add load_custom_agents and save_custom_agents to the handler list (after write_context_pins).

    2. In App.tsx:
       - Add a createSignal for customAgents: { name: string, command: string }[] (default [])
       - On mount (onMount or createEffect), call invoke('load_custom_agents') and populate the signal
       - Create handleSaveCustomAgent function: receives { name, command }, appends to customAgents signal, then calls invoke('save_custom_agents', { agents: [...customAgents(), newAgent] })
       - Pass customAgents() and onSaveCustomAgent={handleSaveCustomAgent} to AgentLaunchModal
       - This ensures custom CLI entries persist across app restarts per D-21
  </action>
  <verify>
    <automated>cd apps/voss-app && cargo build --manifest-path src-tauri/Cargo.toml 2>&1 | tail -10 && npx tsc --noEmit 2>&1 | head -10</automated>
  </verify>
  <acceptance_criteria>
    - SettingsFile struct has custom_agents: Option<Vec<CustomAgent>> field
    - load_custom_agents reads from ~/.config/voss-app/settings.json and returns Vec<CustomAgent>
    - save_custom_agents writes updated custom_agents to settings.json, preserving existing theme data
    - Both commands registered in generate_handler
    - App.tsx loads custom agents on mount and saves on modal submit
    - Existing settings.json files without custom_agents field parse without error
    - Cargo builds without errors
    - TypeScript compiles
  </acceptance_criteria>
  <done>Custom CLIs persisted in settings.json via load_custom_agents/save_custom_agents Tauri commands per D-21.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User input -> Tauri spawn_agent | Custom CLI command field crosses trust boundary to OS process spawn |
| User input -> settings.json | Custom agent name/command written to disk |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-A12-04a | Tampering | Custom CLI command field (D-21) | mitigate | Pass cliBinary and cliArgs as separate Vec<String> to spawn_agent; never concatenate into shell string. spawn_agent already takes them separately. |
| T-A12-04b | Tampering | Custom agent persistence (D-21) | mitigate | CustomAgent struct has only name and command fields; serde_json serialization prevents injection into settings.json. |
| T-A12-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan |
</threat_model>

<verification>
pnpm --filter voss-app test -- all tests green.
npx tsc --noEmit -- zero type errors.
cargo build --manifest-path apps/voss-app/src-tauri/Cargo.toml -- compiles.
</verification>

<success_criteria>
1. Modal opens via + Agent button per D-14/D-20.
2. Six CLI presets visible per D-15.
3. Context-sensitive panels per D-16/D-17.
4. Task prompt optional per D-18.
5. Agent spawns by splitting focused pane per D-19.
6. Custom CLI binary/args separated per security requirements.
7. Custom CLIs persisted in settings.json per D-21.
8. Right-click context menu with 5 actions per D-23.
9. Escape dismisses, Ctrl+Enter submits.
10. All tests pass. Cargo builds.
</success_criteria>

<output>
Create `.planning/phases/A12-voss-app-ade-visual-redesign/A12-04-SUMMARY.md` when done
</output>
