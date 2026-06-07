---
phase: V11-ade-org-integration
plan: 03
type: execute
wave: 2
depends_on: ["01", "02"]
files_modified:
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/components/StatusBar.tsx
  - apps/voss-app/src/org/OrgViewShell.tsx
  - apps/voss-app/src/org/orgStyles.css
  - apps/voss-app/src/org/panels/RosterPanel.tsx
  - apps/voss-app/src/org/panels/BoardPanel.tsx
  - apps/voss-app/src/org/panels/SessionTreePanel.tsx
  - apps/voss-app/src/org/panels/AuditPanel.tsx
  - apps/voss-app/src/org/panels/VerdictPanel.tsx
  - apps/voss-app/src/org/panels/BudgetPanel.tsx
  - apps/voss-app/src/org/panels/ScopePanel.tsx
  - apps/voss-app/src/org/panels/DiffPanel.tsx
  - apps/voss-app/src/org/panels/BlockedPanel.tsx
  - apps/voss-app/src/org/panels/ReplayPanel.tsx
  - apps/voss-app/src/org/__tests__/orgView.test.tsx
autonomous: true
requirements: [VADE-02]
must_haves:
  truths:
    - "Cmd+Shift+O toggles a dedicated Org/Run view that hosts the 10-tab panel shell"
    - "Toggling to Org view and back does NOT unmount/destroy the terminal grid (display:none, not Show)"
    - "Opening the view auto-loads the most-recent run; a run-picker switches runs"
    - "A view-level loading and error state render without crashing on missing/invalid runs"
    - "An Org toggle button appears in the StatusBar left region with active/inactive styling"
  artifacts:
    - path: "apps/voss-app/src/org/OrgViewShell.tsx"
      provides: "Header (Grid/run-picker/refresh) + 10-tab PanelTabBar + ActivePanelArea routing + loading/error states"
      contains: "PanelTabBar"
    - path: "apps/voss-app/src/org/orgStyles.css"
      provides: "V11 org-panel tokens + .org-* component CSS (Voss Ignite values)"
      contains: "--org-col-blocked"
    - path: "apps/voss-app/src/org/panels/BoardPanel.tsx"
      provides: "Panel stub exporting a Component(props:{data})"
      min_lines: 5
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "OrgViewShell"
      via: "Show when orgViewOpen + display:none on grid area"
      pattern: "OrgViewShell"
    - from: "apps/voss-app/src/org/OrgViewShell.tsx"
      to: "orgStore loadRun/enumerateRuns"
      via: "onMount auto-load most-recent run"
      pattern: "enumerateRuns|loadRun"
---

<objective>
Build the Org/Run view shell (VADE-VIEW): the `⌘⇧O` toggle in App.tsx using `display:none` (NOT `<Show>`, to preserve PTY panes), the StatusBar `Org` button, the `OrgViewShell` with header (← Grid / run-picker / refresh), the 10-tab `PanelTabBar`, panel routing, view-level loading/error states, auto-load-most-recent (D-04), and the V11 token/CSS additions. Create all 10 panel stub files so downstream plans fill them without touching the shell (interface-first: zero shared-file conflict).

Purpose: Wave 2 — the host all panels render into; establishes the contract panels implement.
Output: App.tsx + StatusBar.tsx edits, OrgViewShell.tsx, orgStyles.css, 10 panel stubs, a view-toggle test.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V11-ade-org-integration/V11-SPEC.md
@.planning/phases/V11-ade-org-integration/V11-UI-SPEC.md
@.planning/phases/V11-ade-org-integration/V11-PATTERNS.md
@.planning/phases/V11-ade-org-integration/V11-02-SUMMARY.md

<interfaces>
<!-- Panel component contract ALL 10 panels implement (downstream plans fill stubs): -->
<!--   export default function XPanel(props: { data: RunData | null; ... }): JSX.Element -->
<!-- BoardPanel + DiffPanel also take onCardSelect/selectedCardId. -->
<!-- orgStore (Plan 02): runData, runEntries, loadError, loading, currentRunId, loadRun, enumerateRuns, refreshRun -->

<!-- UI-SPEC contracts (authoritative): -->
<!-- Shell layout: OrgViewHeader 28px (← Grid | Run: <id12> ▾ | ↻ Refresh) → PanelTabBar 36px → ActivePanelArea flex:1 -->
<!-- 10 tab labels EXACTLY: Roster Board Tree Audit Verdict Budget Scope Diff Blocked Replay -->
<!-- Toggle: ⌘⇧O; StatusBar 'Org' button left region; active = --focus text + rgba(255,91,31,0.15) bg + 1px --focus border -->
<!-- View error: heading "Run not found"; body "The run \"{run_id}\" could not be loaded. Check that the run ID is valid and try refreshing." -->
<!-- Loading: ⟳ glyph spin 0.8s linear infinite, --fg-2, no text -->
<!-- Run-picker: --bg-3, role=listbox, rows run_id+status+mtime, empty "No runs found", closes on Escape/outside-click -->

<!-- App.tsx patterns (PATTERNS.md, VERIFIED): -->
<!-- createSignal at App() top ~line 227; onAppKey handler ~947-1018 (add ⌘⇧O after Cmd+B); -->
<!-- workspace CSS toggle ~1183-1213 uses display: ... 'flex'|'none' to KEEP GridRoot mounted (Pitfall 6). -->
<!-- StatusBar agent-count button ~79-104 = the button style analog. -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: orgStyles.css tokens + 10 panel stub files</name>
  <files>apps/voss-app/src/org/orgStyles.css, apps/voss-app/src/org/panels/RosterPanel.tsx, apps/voss-app/src/org/panels/BoardPanel.tsx, apps/voss-app/src/org/panels/SessionTreePanel.tsx, apps/voss-app/src/org/panels/AuditPanel.tsx, apps/voss-app/src/org/panels/VerdictPanel.tsx, apps/voss-app/src/org/panels/BudgetPanel.tsx, apps/voss-app/src/org/panels/ScopePanel.tsx, apps/voss-app/src/org/panels/DiffPanel.tsx, apps/voss-app/src/org/panels/BlockedPanel.tsx, apps/voss-app/src/org/panels/ReplayPanel.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("V11-Specific Token Additions" table + "Token Reference: Voss Ignite" + each panel's empty-state copy)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/orgStyles.css" section — :root token block + .org-tab CSS; "Theme Note: Voss Ignite vs variant-b" — use UI-SPEC Voss Ignite values, scope to .org-view-shell if active theme differs)
    - apps/voss-app/src/styles/variant-b.css, apps/voss-app/src/components/modal/modal.css (CSS-var-only, no raw hex, BEM-like naming)
  </read_first>
  <action>
    `orgStyles.css`: declare the V11-specific tokens from the UI-SPEC additions table (`--org-col-backlog/todo/in-progress/in-review/done/blocked`, `--unsupported-flag`, `--card-risk-low/med/high`, role colors) scoped to `.org-view-shell` (per PATTERNS Theme Note — do not patch global `:root`; the Voss Ignite values from the UI-SPEC govern). Add `.org-tab-bar`, `.org-tab`, `.org-tab--active`, `.org-view-header`, `.org-run-picker`, spinner `@keyframes spin` + `.org-spinner`, `.org-error-state`, and a `@media (prefers-reduced-motion: reduce)` block setting animation durations to 0.01ms (UI-SPEC Motion). All values via CSS vars, no raw hex except inside the V11 token declarations sourced from the UI-SPEC table. Create 10 panel stub files each exporting `export default function <Name>Panel(props: { data: RunData | null }) { ... }` that renders the panel's per-panel empty-state copy from the UI-SPEC (e.g. RosterPanel → "No roster data for this run.") wrapped in a panel container div. BoardPanel and DiffPanel stubs additionally accept `onCardSelect?` / `selectedCardId?` in props. Import `RunData` type from `../types`. These stubs are the contract downstream plans fill — keep each minimal but type-correct.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit && grep -q -- "--org-col-blocked" src/org/orgStyles.css && ls src/org/panels/*.tsx | wc -l | grep -q 10</automated>
  </verify>
  <done>orgStyles.css declares all V11 tokens + .org-* classes + reduced-motion block; 10 panel stubs exist, each typed against RunData, rendering its empty-state copy; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 2: OrgViewShell — header, run-picker, 10-tab bar, routing, loading/error</name>
  <files>apps/voss-app/src/org/OrgViewShell.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Org/Run View — Shell Layout", "Run-picker dropdown", "View-Level States", "Copywriting Contract", "Accessibility" — role=region/tablist/tab/tabpanel/listbox)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/OrgViewShell.tsx" section — component skeleton, tab bar, Show routing, loading/error patterns from AgentLaunchModal)
    - apps/voss-app/src/components/modal/AgentLaunchModal.tsx (tab bar + onMount requestAnimationFrame + Show/For routing analog)
    - apps/voss-app/src/org/orgStore.ts (signals + loadRun/enumerateRuns/refreshRun from Plan 02)
  </read_first>
  <action>
    Implement `OrgViewShell(props: { cwd: string; cliBinary: string; onClose: () => void })`. State: `activeTab` signal (default 'roster'), `pickerOpen` signal. `onMount`: `enumerateRuns(props.cwd)` then auto-`loadRun(entries[0].run_id, cwd, cliBinary)` if any (D-04). Header (28px, class `.org-view-header`, `role="region"` `aria-label="Org/Run view"` on the shell root): left `← Grid` button (calls props.onClose); center run label `Run: <run_id 12-char ellipsis> ▾` button toggling the run-picker; right `↻ Refresh` button calling `refreshRun(cwd, cliBinary)`, spinning + disabled while `loading()`. Run-picker dropdown (`role="listbox"`, `--bg-3`): `For` over `runEntries()` rows (run_id + status badge + mtime), active row `--focus-soft`, empty "No runs found", closes on Escape + outside click. PanelTabBar (`role="tablist"`, 10 tabs with EXACT labels Roster/Board/Tree/Audit/Verdict/Budget/Scope/Diff/Blocked/Replay, each `role="tab"` `aria-selected`). ActivePanelArea (`role="tabpanel"`): `Show`-route each tab to its panel component, passing `data={runData()}` (and BoardPanel `onCardSelect`, DiffPanel `selectedCardId`). View-level loading: centered `.org-spinner` ⟳ when `loading()`. View-level error: when `loadError()`, render `.org-error-state` heading "Run not found" + the exact body copy with the run id + a Refresh button (per UI-SPEC + Copywriting Contract). Import `orgStyles.css`.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit && grep -q 'role="tablist"' src/org/OrgViewShell.tsx && grep -q "Run not found" src/org/OrgViewShell.tsx</automated>
  </verify>
  <done>OrgViewShell renders header + run-picker + 10-tab tablist + routed panel area + loading + error states; auto-loads most-recent run on mount; copy + ARIA roles match the UI-SPEC; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 3: App.tsx ⌘⇧O toggle (display:none) + StatusBar Org button + view-toggle test</name>
  <files>apps/voss-app/src/App.tsx, apps/voss-app/src/components/StatusBar.tsx, apps/voss-app/src/org/__tests__/orgView.test.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx (createSignal block ~227; onAppKey ~947-1018 — Cmd+B insertion point; workspace display-toggle JSX ~1173-1218)
    - apps/voss-app/src/components/StatusBar.tsx (left-region layout + agent-count button style ~79-104)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/App.tsx" section — CSS display toggle MUST be display:none NOT Show; ⌘⇧O handler; StatusBar button style)
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md (Pitfall 6: Show around GridRoot destroys PTY — use display:none)
    - apps/voss-app/src/grid/__tests__/a6-acceptance.test.tsx (vi.mock + mount/render/cleanup test harness)
  </read_first>
  <action>
    In App.tsx: add `const [orgViewOpen, setOrgViewOpen] = createSignal(false)` near the other signals. In `onAppKey`, after the existing Cmd+B branch, add a `⌘⇧O` branch: `if (e.metaKey && e.shiftKey && (e.key === 'o' || e.key === 'O')) { setOrgViewOpen(p => !p); e.preventDefault(); e.stopImmediatePropagation(); return; }`. Wrap the existing workspace `<For>` + `ContextPanel` region in a div whose style sets `display: orgViewOpen() ? 'none' : 'flex'` — CRITICAL: keep the grid MOUNTED via CSS display, do NOT put a `<Show>` around GridRoot (Pitfall 6: destroys PTY). Add `<Show when={orgViewOpen()}><OrgViewShell cwd={workspacePath() ?? ''} cliBinary={/* the configured voss binary path used by spawn_agent */} onClose={() => setOrgViewOpen(false)} /></Show>` as a sibling. Pass `orgViewOpen()` + a toggle callback into StatusBar. In StatusBar.tsx: add an `Org` button in the LEFT region (between workspace info and pane count per UI-SPEC) following the agent-count button style — active state `--focus` text / `rgba(255,91,31,0.15)` bg / `1px solid --focus`; inactive `--fg-3` text / transparent. In `orgView.test.tsx` (`vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }))`): render App (or a minimal harness), assert the grid container is present, simulate `⌘⇧O`, assert OrgViewShell mounts AND the grid container is still in the DOM with `display: none` (proves no unmount — VADE-VIEW acceptance "back restores grid unchanged"). If rendering full App is impractical, test the toggle behavior on a focused harness component that reproduces the display-toggle structure, plus assert the StatusBar Org button toggles class/style.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/orgView.test.tsx && npx tsc --noEmit</automated>
  </verify>
  <done>⌘⇧O toggles the Org view via display:none (grid stays mounted — test asserts grid node persists); StatusBar shows the Org button with active/inactive styling; orgView.test.tsx green; tsc clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| view toggle state | local App.tsx signal; no privilege boundary, but must not destroy PTY sessions |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V11-07 | Denial of Service | grid/PTY destroyed on view toggle (regression) | mitigate | use CSS display:none not <Show> around GridRoot; test asserts grid node persists with display:none (Pitfall 6) |
| T-V11-08 | Information Disclosure | run-picker leaks runs from outside cwd | accept | enumerate_runs (Plan 02) is scoped to <cwd>/.voss/sessions and traversal-guarded; shell only displays |
| T-V11-SC | Tampering | npm/pip/cargo installs | mitigate | No new packages (RESEARCH audit empty) |
</threat_model>

<verification>
- `cd apps/voss-app && npx vitest run && npx tsc --noEmit` green.
- Terminal-grid view does not regress: orgView.test.tsx asserts the grid node remains mounted (display:none) when Org view is active.
- 10 panel stubs + OrgViewShell + tokens present.
</verification>

<success_criteria>
- ⌘⇧O + StatusBar button toggle a dedicated Org/Run view (VADE-VIEW).
- Grid not unmounted on toggle (Pitfall 6 mitigated, test-proven).
- Auto-load most-recent run + run-picker (D-04); view-level loading + error states.
- 10-tab shell with exact labels + ARIA roles; downstream panels fill stubs without touching the shell.
- No new dependencies; existing voss-app tests green.
</success_criteria>

<output>
Create `.planning/phases/V11-ade-org-integration/V11-03-SUMMARY.md` when done.
</output>
