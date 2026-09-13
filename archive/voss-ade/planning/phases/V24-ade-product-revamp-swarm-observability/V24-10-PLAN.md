---
phase: V24-ade-product-revamp-swarm-observability
plan: 10
type: execute
wave: 7
depends_on: ["V24-02", "V24-09"]
autonomous: true
requirements: [VADE2-10]
files_modified:
  - apps/voss-app/src/portal/PortalShell.tsx
  - apps/voss-app/src/surfaces/context/ContextSurface.tsx
  - apps/voss-app/src/surfaces/settings/SettingsSurface.tsx
  - apps/voss-app/src/surfaces/memory/MemorySurface.tsx
  - apps/voss-app/src/surfaces/settings/__tests__/SettingsSurface.test.tsx
  - apps/voss-app/src/surfaces/context/__tests__/ContextSurface.test.tsx
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/__tests__/portalA11y.test.tsx
  - apps/voss-app/PRODUCT.md
  - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md
must_haves:
  truths:
    - "Selecting Context, Settings, or Memory in the portal renders a real surface — NOT the 'Coming in a later V24 plan' placeholder. That stale string is removed from the codebase."
    - "Context surface reuses the existing ContextPanel component fed by the same focusedPaneId()/contextByPaneId() data as the F4 drawer (no re-derivation, passed via a contextSlot thunk like reviewSlot)."
    - "Settings surface renders real, persisted controls (theme, font size, high contrast, bell, cursor) backed by the existing appearance store (loadAppearanceSettings/saveAppearanceSettings/applyAppearanceSettings) — changing a control persists and applies it."
    - "Memory surface renders an HONEST state: memory is harness-backed (the /memory slash command + memory CLI), not yet exposed over the server HTTP API, so the app has no live memory data to show. Copy says exactly that — it does NOT claim a feature is coming, and does NOT synthesize fake memory rows."
    - "The full apps/voss-app vitest suite + portalA11y a11y gate stay green; tsc --noEmit clean."
  artifacts:
    - path: "apps/voss-app/src/surfaces/settings/SettingsSurface.tsx"
      provides: "Settings surface wired to the appearance store: theme/font/contrast/bell/cursor controls that persist via saveAppearanceSettings + apply via applyAppearanceSettings"
      contains: "appearance"
    - path: "apps/voss-app/src/surfaces/context/ContextSurface.tsx"
      provides: "Full-canvas Context surface wrapping the existing ContextPanel, fed by the active pane's ContextData"
      contains: "ContextPanel"
    - path: "apps/voss-app/src/surfaces/memory/MemorySurface.tsx"
      provides: "Honest memory surface: explains harness-backed memory + no in-app data yet; no fake rows"
      contains: "tabpanel"
    - path: "apps/voss-app/src/portal/PortalShell.tsx"
      provides: "Match arms for 'context' (contextSlot thunk), 'settings' (SettingsSurface), 'memory' (MemorySurface); SurfacePlaceholder + its stale V24 copy deleted"
      contains: "SettingsSurface"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/surfaces/context/ContextSurface.tsx"
      via: "contextSlot={() => <ContextSurface context={...} isAgentPane={...} onTogglePin={...} />} passed to PortalShell (mirrors reviewSlot)"
      pattern: "contextSlot"
    - from: "apps/voss-app/src/surfaces/settings/SettingsSurface.tsx"
      to: "apps/voss-app/src/appearance/settings.ts"
      via: "subscribeAppearanceSettings/getCommittedAppearanceSettings read; saveAppearanceSettings + applyAppearanceSettings on change"
      pattern: "AppearanceSettings"
---

<objective>
Close the V24 SPEC gap. `V24-SPEC.md` (lines 41, 86, 91) required Review, Context,
Memory, and Settings to **"wire to existing V14/panels/drawers as-is"** in this
phase. Only **Review** was wired (reviewSlot). Context, Memory, and Settings still
fall through `PortalShell`'s `<Switch>` fallback to `SurfacePlaceholder`, which
hardcodes the now-false string **"Coming in a later V24 plan."** V24 is closed; no
later plan targets them. This is an incomplete-implementation gap, not a deferral.

Wire the three remaining portal items to real surfaces, honestly:

1. **Context** — a full-canvas surface reusing the EXISTING `ContextPanel`
   component (today only reachable as the F4 side drawer), fed by the SAME
   `focusedPaneId()` / `contextByPaneId()` data via a `contextSlot` thunk, exactly
   mirroring how `reviewSlot` already passes the OrgViewShell. No re-derivation, no
   new data path.
2. **Settings** — a real settings surface backed by the EXISTING appearance store
   (`appearance/settings.ts`: load/save/apply/subscribe). The current
   `appearanceCommands` palette entries are stubs whose handlers just re-open the
   palette (`App.tsx:1258-1261`); this surface gives the persisted appearance
   settings (theme, font size, high contrast, bell, cursor) an actual home.
3. **Memory** — an HONEST surface. Memory is real but lives in the harness
   (`voss/harness/memory_store.py`, `memory_cli.py`, the `/memory` slash command);
   it is **not** exposed over the server HTTP API the app talks to (routes are
   session/cost/permission/doctor only — verified). So there is no live memory data
   to render in-app yet. The surface states that plainly and links the user to the
   slash command. It renders NO synthesized rows (honest-signal discipline, same as
   the Swarm Map). Exposing memory over HTTP is tracked as a separate backend
   requirement (see Deferred), out of scope for this frontend wiring plan.

Delete `SurfacePlaceholder` and its stale copy: after this plan every portal item
routes to a real surface, so the fallback is dead.

Output: Context/Settings/Memory portal surfaces wired (two functional, one honest),
the stale "later V24 plan" string gone, contracts updated, full suite green.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@apps/voss-app/PRODUCT.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-SPEC.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md

<interfaces>
<!-- Verified from codebase 2026-06-16. -->

PortalShell (src/portal/PortalShell.tsx) ground truth:
- A `<Switch fallback={<SurfacePlaceholder view={props.activeView} />}>` with Match
  arms for review (reviewSlot thunk), overview, tasks, agents, swarm-map.
- `SurfacePlaceholder` (lines 41-51) renders `.portal-placeholder__hint` with the
  literal "Coming in a later V24 plan". context/memory/settings hit this fallback.
- Props already carry `reviewSlot?: () => JSX.Element` (lazy thunk, only built when
  active). ADD a parallel `contextSlot?: () => JSX.Element` for the same reason
  (Context needs App-local pane data, like Review needs App-local client state).
- The header comment (lines 8-13) is now WRONG (says these wire "in a later plan");
  rewrite it to describe the three new arms.

Context data + ContextPanel (the thing to reuse):
- `src/components/ContextPanel.tsx`: `export default function ContextPanel(props:
  ContextPanelProps)`. Props: `open: boolean`, `context: ContextData | null`,
  `paneIndex?`, `paneCwd?`, `isAgentPane: boolean`,
  `onTogglePin?: (path, pinned) => void`. Renders the token heatmap + file list.
- In `App.tsx` (~1620) ContextPanel is mounted as the F4 drawer with:
  `context = (() => { const id = focusedPaneId(); return id ? contextByPaneId()[id]
  ?? null : null; })()`, `isAgentPane` from `activeMounted()?.agentConfigByPaneId()`,
  and an `onTogglePin` that calls `invoke('write_context_pins', …)`. Reuse this
  EXACT derivation for the surface slot — do not duplicate the pin logic; extract a
  shared `togglePin(path, pinned)` closure in App and pass it to both the drawer and
  the slot if convenient, else inline the same body.
- ContextSurface should render `<ContextPanel open={true} … />` inside a
  `<div class="surface" role="tabpanel" aria-label="Context">` wrapper. `open` is
  always true in surface context (the canvas-swap Show already gates mounting).

Settings / appearance store (src/appearance/settings.ts) ground truth:
- `getCommittedAppearanceSettings(): AppearanceSettings` — current applied settings.
- `subscribeAppearanceSettings(fn): () => void` — change subscription (unsub on cleanup).
- `saveAppearanceSettings(settings): Promise<void>` — persists (tauri save_appearance_settings).
- `applyAppearanceSettings(settings): void` — applies live (DOM/theme effects).
- `AppearanceSettings` (src/appearance/types.ts): font size (clampFontSize, MIN_FONT_SIZE),
  high-contrast flag, bell behavior, cursor shape/blink, reduced motion. `BellBehavior`,
  `CursorShape`, `CursorBlink` enums in appearance/profiles.ts.
- Theme list: there is an existing theme registry the palette's switchTheme uses
  (`save_active_theme_id` tauri cmd, `appearance/profiles.ts`). The settings surface
  may present theme as a select; if the theme catalog is not trivially importable,
  scope this surface to the AppearanceSettings fields (font/contrast/bell/cursor/
  reduced-motion) and add theme/font-family in a follow-up (record the decision in
  the SUMMARY). Persisted + applied is the bar; breadth of fields is secondary.

Memory (backend reality, verified):
- `voss/harness/memory_store.py`, `voss/harness/memory_cli.py`, `voss_runtime/memory/*`
  exist; tests under `tests/memory/` + `tests/harness/test_slash_memory.py`.
- `voss/harness/server/app.py` routes: /session, /sessions/saved, /session/{id},
  message, abort, cost, permission, /doctor. **No /memory route.** So the app has no
  HTTP surface to read memory. MemorySurface must NOT fabricate data.

Surface pattern (copy this shape): `src/surfaces/tasks/TasksSurface.tsx` —
`<div class="surface" role="tabpanel" aria-label="…"><div class="surface__header">
…</div><div class="surface__body">…</div></div>`, styles in `surfaces/surfaces.css`.
Empty/honest states use `.surface-empty` (`.surface-empty__title` + `__hint`).
SurfaceHeader (`surfaces/SurfaceHeader.tsx`) is available if a project header is wanted.

App wiring (src/App.tsx):
- PortalShell mounted ~1656 with reviewSlot. ADD `contextSlot={() => <ContextSurface … />}`
  alongside it, reading the same focusedPaneId/contextByPaneId/onTogglePin used at ~1620.
- No new state needed; Settings/Memory surfaces are prop-less (read their own stores).

Test harness analogs:
  src/surfaces/tasks/__tests__/TasksSurface.test.tsx (mount/dispose, prop-less surface)
  src/__tests__/portalA11y.test.tsx (V24-08/09 a11y gate — extend; tauri-mock harness)
  src/components/__tests__ ContextPanel coverage (reuse for ContextSurface assertions)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Settings surface on the appearance store (RED → GREEN)</name>
  <files>apps/voss-app/src/surfaces/settings/SettingsSurface.tsx, apps/voss-app/src/surfaces/settings/__tests__/SettingsSurface.test.tsx</files>
  <read_first>
    - apps/voss-app/src/appearance/settings.ts (load/save/apply/subscribe/get API)
    - apps/voss-app/src/appearance/types.ts + profiles.ts (AppearanceSettings fields + enums)
    - apps/voss-app/src/surfaces/tasks/TasksSurface.tsx (surface shell pattern)
  </read_first>
  <action>
    RED (SettingsSurface.test.tsx, tauri-mock + mount/dispose):
    - Renders `<div role="tabpanel" aria-label="Settings">`.
    - Renders a labelled control for each scoped AppearanceSettings field (at minimum:
      font size, high contrast toggle, bell behavior, cursor shape) with the current
      committed value reflected.
    - Changing a control calls `saveAppearanceSettings` (mock) with the updated field
      AND `applyAppearanceSettings` so the change is live (assert both invoked).
    GREEN (SettingsSurface.tsx):
    - Prop-less `Component`. Initialize from `getCommittedAppearanceSettings()`, keep a
      local signal, `subscribeAppearanceSettings` to external changes (unsub onCleanup).
    - On any control change: compute next settings, call `applyAppearanceSettings(next)`
      then `void saveAppearanceSettings(next)` (mirror how the app persists elsewhere).
    - Use real labelled inputs (`<label>`+control); group under `.surface__body`.
    - Scope to AppearanceSettings fields; if theme catalog import is non-trivial, defer
      theme/font-family and note it in the SUMMARY (functional-persist is the bar).
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- SettingsSurface 2>&1 | tail -15; npx tsc --noEmit 2>&1 | tail -6 && echo TSC_OK</automated>
  </verify>
  <acceptance_criteria>
    - SettingsSurface renders persisted appearance controls reflecting committed values.
    - A control change invokes applyAppearanceSettings + saveAppearanceSettings with the new value.
    - role="tabpanel" aria-label="Settings"; tsc clean.
  </acceptance_criteria>
  <done>Settings is a real, persisted surface — not a placeholder.</done>
</task>

<task type="auto">
  <name>Task 2: Context surface reusing ContextPanel (RED → GREEN)</name>
  <files>apps/voss-app/src/surfaces/context/ContextSurface.tsx, apps/voss-app/src/surfaces/context/__tests__/ContextSurface.test.tsx</files>
  <read_first>
    - apps/voss-app/src/components/ContextPanel.tsx (props + render)
    - apps/voss-app/src/App.tsx ~1620 (the F4 ContextPanel mount + data derivation to reuse)
  </read_first>
  <action>
    RED (ContextSurface.test.tsx):
    - `<div role="tabpanel" aria-label="Context">` wrapping a ContextPanel.
    - Given a ContextData prop with files, the panel renders those file rows (reuse the
      ContextPanel render assertions); given `context={null}` it renders an honest
      empty state (no crash) — e.g. "No context for the focused pane yet."
    - `onTogglePin` passed through is invoked when a pin control is toggled.
    GREEN (ContextSurface.tsx):
    - `Component<{ context: ContextData | null; isAgentPane: boolean;
      onTogglePin?: (path, pinned) => void; paneCwd?: string }>`.
    - Render `<div class="surface" role="tabpanel" aria-label="Context">` →
      `<ContextPanel open={true} context={props.context} isAgentPane={props.isAgentPane}
      onTogglePin={props.onTogglePin} paneCwd={props.paneCwd} />`. Add a `.surface-empty`
      branch (or rely on ContextPanel's own empty handling — verify which).
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- ContextSurface 2>&1 | tail -15; npx tsc --noEmit 2>&1 | tail -6 && echo TSC_OK</automated>
  </verify>
  <acceptance_criteria>
    - ContextSurface wraps ContextPanel, renders file rows from ContextData, honest empty state on null.
    - onTogglePin passes through; role="tabpanel" aria-label="Context"; tsc clean.
  </acceptance_criteria>
  <done>Context is a full-canvas surface reusing the shipped ContextPanel + its real data.</done>
</task>

<task type="auto">
  <name>Task 3: Memory honest surface (RED → GREEN)</name>
  <files>apps/voss-app/src/surfaces/memory/MemorySurface.tsx</files>
  <read_first>
    - apps/voss-app/src/surfaces/tasks/TasksSurface.tsx (.surface-empty pattern)
    - voss/harness/server/app.py (confirm no /memory route — honest copy basis)
  </read_first>
  <action>
    GREEN (MemorySurface.tsx), prop-less `Component`:
    - `<div class="surface" role="tabpanel" aria-label="Memory">` with a `.surface__header`
      ("Memory") and a `.surface-empty` body stating the TRUTH: Voss memory is managed by
      the harness and reachable today via the `/memory` slash command in a Voss session;
      it is not yet surfaced as live data in the app. Render NO fabricated rows.
    - Mention the concrete entry point (the `/memory` slash command) so the user has a
      real action. Keep copy aligned with PRODUCT.md vocabulary.
    NOTE: no test file required beyond the portalA11y gate (Task 4) covering its tabpanel
    role + accessible name — it is static honest copy. Do not invent a data fetch.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | tail -6 && echo TSC_OK; grep -L "fabricat\|TODO\|fake" src/surfaces/memory/MemorySurface.tsx >/dev/null && echo NO_FAKE</automated>
  </verify>
  <acceptance_criteria>
    - MemorySurface renders an honest, accurate state (harness-backed, /memory slash command, no in-app data yet).
    - No synthesized memory rows; role="tabpanel" aria-label="Memory"; tsc clean.
  </acceptance_criteria>
  <done>Memory tells the truth instead of "coming in a later V24 plan."</done>
</task>

<task type="auto">
  <name>Task 4: Wire arms into PortalShell + App, delete stale placeholder, a11y gate + docs</name>
  <files>apps/voss-app/src/portal/PortalShell.tsx, apps/voss-app/src/App.tsx, apps/voss-app/src/__tests__/portalA11y.test.tsx, apps/voss-app/PRODUCT.md, .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md</files>
  <read_first>
    - apps/voss-app/src/portal/PortalShell.tsx (Switch + SurfacePlaceholder to remove)
    - apps/voss-app/src/App.tsx ~1656 (PortalShell mount + reviewSlot — add contextSlot beside it)
    - apps/voss-app/src/__tests__/portalA11y.test.tsx (gate to extend)
  </read_first>
  <action>
    PortalShell.tsx:
    - Import SettingsSurface, MemorySurface. Add Match arms:
      `context` → `props.contextSlot ? props.contextSlot() : <MemorySurface/>-style honest
      fallback` (prefer: if no contextSlot, render an honest "no focused pane" note — but
      App always passes it). `settings` → `<SettingsSurface/>`. `memory` → `<MemorySurface/>`.
    - Add `contextSlot?: () => JSX.Element` to PortalShellProps.
    - DELETE `SurfacePlaceholder` and the "Coming in a later V24 plan" string entirely
      (now no item falls through). Keep `<Switch>` but its fallback can be a minimal
      honest "Unknown surface" guard OR removed if all PortalView values are matched —
      verify the union is exhaustively matched (grid short-circuits via the outer Show).
    - Rewrite the file header comment (lines 8-13) to reflect that all surfaces are wired.
    App.tsx:
    - Pass `contextSlot={() => <ContextSurface context={…} isAgentPane={…}
      onTogglePin={…} paneCwd={…} />}` using the SAME derivation as the F4 ContextPanel
      (~1620). Extract a shared `togglePin` if it reduces duplication; otherwise inline.
    portalA11y.test.tsx:
    - Assert that selecting context/settings/memory renders a `role="tabpanel"` with the
      right `aria-label`, and that NONE of them contains the text "Coming in a later V24 plan".
      Add a guard asserting that string is absent from the rendered portal entirely.
    Docs:
    - PRODUCT.md §Information Architecture: Context/Settings/Memory now route to real
      surfaces (Context = the token/file panel; Settings = appearance settings; Memory =
      harness-backed, slash-command entry, no in-app data yet). Remove any "placeholder"
      language for these three.
    - V24-UI-SPEC.md: replace the placeholder note for Context/Memory/Settings with the
      wired contract (Context reuses ContextPanel; Settings = appearance store; Memory =
      honest no-data state). Cross-reference the SPEC lines 41/86/91 this closes.
    Run FULL suite + tsc. Create V24-10-SUMMARY.md.
  </action>
  <verify>
    <automated>cd apps/voss-app && grep -rn "Coming in a later V24 plan" src && echo "STALE_STRING_PRESENT (FAIL)" || echo "STALE_STRING_GONE"; npm test -- portalA11y 2>&1 | tail -12; npm test 2>&1 | tail -20; npx tsc --noEmit 2>&1 | tail -5 && echo TSC_OK</automated>
  </verify>
  <acceptance_criteria>
    - context/settings/memory each render their real surface; the "Coming in a later V24 plan" string is gone from src (grep returns nothing → STALE_STRING_GONE).
    - portalA11y asserts the three tabpanels' accessible names and the absence of the stale string.
    - PRODUCT.md + UI-SPEC reflect the wired surfaces; SPEC 41/86/91 gap closed.
    - npm test full suite green; tsc --noEmit clean.
  </acceptance_criteria>
  <done>All eight portal items route to real surfaces; the stale deferral copy is deleted; contracts match the build.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| appearance store → persisted config | SettingsSurface writes appearance settings via saveAppearanceSettings (tauri save_appearance_settings). |
| pane context data → Context surface | ContextSurface renders ContextData for the focused pane (same data as the F4 drawer). |
| harness memory → app | MemorySurface deliberately renders NO live memory data (no HTTP route exists); it must not fabricate. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V24-10-FS | Verification integrity (fake signal) | MemorySurface | mitigate | MemorySurface renders only honest static copy about harness-backed memory; it performs no data fetch and synthesizes no rows. A grep guard (`NO_FAKE`) + the portalA11y "no stale string" assertion enforce honesty. Same discipline as the Swarm Map's missing-signal handling. |
| T-V24-10-CP | Tampering (config write) | saveAppearanceSettings from SettingsSurface | accept | SettingsSurface writes only AppearanceSettings fields through the existing validated save/apply path (same one the palette + PaneComponent already use). No new persistence surface or schema. |
| T-V24-10-CS | Canvas-swap integrity | new Match arms in PortalShell | mitigate | New surfaces mount inside the existing `<Show when={activeView!=='grid'}>` canvas-swap region; GridRoot stays mounted (Pitfall 1 unchanged). swarmPortal canvas-swap + pane-identity tests must stay green (full suite in Task 4). |

No HIGH-severity threats. No new dependency, no new tauri command, no new network surface.
</threat_model>

<verification>
- `grep -rn "Coming in a later V24 plan" apps/voss-app/src` → no matches (STALE_STRING_GONE).
- `npm test` full suite green, including new SettingsSurface + ContextSurface tests and the extended portalA11y gate; swarmPortal canvas-swap/pane-identity tests stay green.
- `npx tsc --noEmit` → 0 errors.
- Manual: selecting Context shows the token/file panel for the focused pane; Settings changes persist across reload; Memory shows the honest harness-backed state.
</verification>

<success_criteria>
All four SPEC-required wirings (Review already done; Context, Settings, Memory added here)
route to real surfaces: Context reuses the shipped ContextPanel with live pane data,
Settings is a persisted appearance-settings surface, and Memory honestly states it is
harness-backed with no in-app data yet (no fabricated rows). The "Coming in a later V24
plan" placeholder and its SurfacePlaceholder component are deleted. PRODUCT.md and
V24-UI-SPEC.md reflect the wired surfaces and note this closes the V24-SPEC §41/86/91 gap.
Full vitest suite + portalA11y gate + tsc are green (VADE2-10 met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-10-SUMMARY.md` when done.

## Deferred (out of scope — new requirement, not this plan)
Exposing harness memory over the server HTTP API (a `/memory` route in
`voss/harness/server/app.py` + a typed app client + a real MemorySurface data view) is
backend work. Track as a follow-up requirement (suggest **VADE2-11** or a V21/V23 memory
phase) so a future plan can upgrade MemorySurface from honest-empty to live data.

## Manual smoke (post-build, not a blocking checkpoint)
`npm run tauri dev`: click Context (see focused-pane token heatmap), Settings (toggle high
contrast / change font size, reload, confirm it stuck), Memory (read the honest state, no
fake rows). Confirm no surface shows "Coming in a later V24 plan."
</output>
