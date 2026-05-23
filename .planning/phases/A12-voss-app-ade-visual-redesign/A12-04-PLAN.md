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
  - apps/voss-app/src/App.tsx
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
  artifacts:
    - path: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      provides: "Agent launch modal with 6 CLI presets and context-sensitive config panels"
      exports: ["AgentLaunchModal"]
    - path: "apps/voss-app/src/components/modal/modal.css"
      provides: "Modal overlay styles"
    - path: "apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx"
      provides: "Modal unit tests"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      via: "Show when agentModalOpen"
      pattern: "<AgentLaunchModal"
    - from: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      to: "apps/voss-app/src/App.tsx"
      via: "onLaunch callback with spawn config"
      pattern: "onLaunch"
---

<objective>
Build the Agent Launch Modal with 6 CLI presets, context-sensitive config panels (generic vs Voss-specific vs Custom), and wire it into App.tsx via the + Agent button callback. Agent spawns by splitting from the focused pane.

Purpose: This is the primary UX for starting new agent sessions — the agent launch flow that makes Voss an ADE rather than a terminal multiplexer.
Output: AgentLaunchModal.tsx, modal.css, tests, App.tsx wiring.
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
       All border-radius on interactive elements via inline style (per RESEARCH Finding 10 — global reset).

    2. Create apps/voss-app/src/components/modal/AgentLaunchModal.tsx:

       Props: onDismiss callback, onLaunch callback (config: { cliBinary: string, cliArgs: string[], taskPrompt: string })

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
       - Tab row: 6 tabs (Claude, Codex, Antigravity, OpenCode, Voss, Custom) — each gets .modal-tab, active gets .modal-tab--active per D-15
       - Body: conditionally render panel based on activeTab:
         * claude/codex/antigravity/opencode → GenericAgentPanel: model selector button group (for Claude: opus/sonnet/haiku; Codex: default; others: default), effort segmented control (low/medium/high), Plan Mode toggle, Skip Permissions toggle, task prompt textarea with placeholder "Describe the task (optional — leave blank for interactive mode)" per D-16/D-17/D-18
         * voss → VossAgentPanel: command segmented (chat/do/resume/agent), mode segmented (edit/plan), auth field, task prompt textarea per D-16
         * custom → CustomPanel: name input (placeholder "e.g. my-agent"), command input (JetBrains Mono, placeholder "e.g. /usr/local/bin/my-agent") per D-21
       - Footer: left "Press Ctrl+Enter to start" hint (Inter 11px --fg-3), right "Launch Agent" primary button (.modal-btn-primary)

       Key handling:
       - Escape → onDismiss per D-14
       - Ctrl+Enter → submit (build config and call onLaunch)

       Submit logic (buildLaunchConfig):
       - For generic tabs: cliBinary = tab name (claude/codex/gemini for antigravity/opencode), cliArgs built from model (--model X), effort, planMode (--plan), skipPermissions (--dangerously-skip-permissions for Claude, --skip-review for others). Task prompt appended as positional arg if non-empty per D-18.
       - For voss tab: cliBinary = 'voss', cliArgs built from vossCommand (do/chat/resume/agent spawn) + vossMode + vossAuth + task
       - For custom tab: cliBinary = customCommand, cliArgs = [] (or split command string into binary + args), name stored for future reference per D-21
       - SECURITY: cliBinary and cliArgs passed as separate values to the onLaunch callback — NEVER joined into a single shell string. spawn_agent already takes them separately (RESEARCH Security Domain).

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
    - Escape dismisses, Ctrl+Enter submits
    - Submit builds cliBinary + cliArgs as separate values (never shell string)
    - Modal has role="dialog", aria-modal="true", aria-labelledby, dismiss aria-label
    - TypeScript compiles
  </acceptance_criteria>
  <done>AgentLaunchModal component with 6 tabs, context-sensitive panels, keyboard handling, and accessibility.</done>
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
       - Test: "renders 6 CLI preset tabs" — render modal, query for tab buttons, assert 6 found with text Claude/Codex/Antigravity/OpenCode/Voss/Custom
       - Test: "Escape calls onDismiss" — render, dispatch Escape keydown, assert onDismiss called
       - Test: "switching to Voss tab shows Voss config" — render, click Voss tab, assert command selector visible (chat/do/resume/agent text)
       - Test: "switching to Custom tab shows name and command inputs" — render, click Custom tab, assert inputs with placeholder text present
       - Test: "Launch Agent button calls onLaunch" — render, click Launch Agent button, assert onLaunch called with config object containing cliBinary and cliArgs
       - Test: "modal has correct ARIA attributes" — assert role="dialog", aria-modal="true", aria-labelledby present
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

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User input -> Tauri spawn_agent | Custom CLI command field crosses trust boundary to OS process spawn |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-A12-04 | Tampering | Custom CLI command field (D-21) | mitigate | Pass cliBinary and cliArgs as separate Vec<String> to spawn_agent; never concatenate into shell string. spawn_agent already takes them separately. |
| T-A12-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan |
</threat_model>

<verification>
pnpm --filter voss-app test — all tests green.
npx tsc --noEmit — zero type errors.
</verification>

<success_criteria>
1. Modal opens via + Agent button per D-14/D-20.
2. Six CLI presets visible per D-15.
3. Context-sensitive panels per D-16/D-17.
4. Task prompt optional per D-18.
5. Agent spawns by splitting focused pane per D-19.
6. Custom CLI binary/args separated per D-21 and security requirements.
7. Escape dismisses, Ctrl+Enter submits.
8. All tests pass.
</success_criteria>

<output>
Create `.planning/phases/A12-voss-app-ade-visual-redesign/A12-04-SUMMARY.md` when done
</output>
