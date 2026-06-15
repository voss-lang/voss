---
phase: V24-ade-product-revamp-swarm-observability
plan: 04
type: execute
wave: 3
depends_on: ["V24-03"]
files_modified:
  - apps/voss-app/src/composer/VossComposer.tsx
  - apps/voss-app/src/composer/composer.css
  - apps/voss-app/src/composer/__tests__/VossComposer.test.tsx
  - apps/voss-app/src/App.tsx
autonomous: true
requirements: [VADE2-04]
must_haves:
  truths:
    - "A global 'Ask Voss to…' composer is reachable from any surface (⌘K and the portal rail ask trigger)"
    - "On open the composer shows only the ask field + a safety-mode control defaulted to 'Read only'"
    - "Scope, agent target, team, budget, and attached context are hidden until 'Advanced' is expanded"
    - "No raw internal labels (Plan/Edit/Auto, runId) are shown by default"
  artifacts:
    - path: "apps/voss-app/src/composer/VossComposer.tsx"
      provides: "Modal <dialog> composer; ask + safety (Read only default); Advanced-collapsed; reuses assembleRunSpec; safety→RunMode mapping"
      contains: "VossComposer"
    - path: "apps/voss-app/src/composer/__tests__/VossComposer.test.tsx"
      provides: "Default-state + Advanced-collapsed + Read-only-default assertions"
      contains: "VossComposer"
  key_links:
    - from: "apps/voss-app/src/composer/VossComposer.tsx"
      to: "apps/voss-app/src/org/cockpit/runIntake.ts"
      via: "assembleRunSpec(state) on Create Task; safety mode → RunMode"
      pattern: "assembleRunSpec"
    - from: "apps/voss-app/src/App.tsx"
      to: "VossComposer"
      via: "⌘K and rail ask trigger open the global composer dialog"
      pattern: "VossComposer"
---

<objective>
Build the global, always-present "Ask Voss to…" composer (VADE2-04). It is a
modal `<dialog>` reachable from any surface via `⌘K` and the portal-rail ask
trigger. On open it shows only the ask field and a safety-mode control that
defaults to "Read only" (D-04). Scope, agent target, team, budget, and attached
context are collapsed behind "Advanced" (D-05). The composer replaces the
exposed `RunCommandBar` Plan/Edit/Auto + target/budget clutter but reuses the
existing `runIntake.ts` `assembleRunSpec` assembler — the safety-mode labels map
to the internal `RunMode` (Read only→Plan, Can edit→Edit, Autopilot→Auto), code
identifiers unchanged (D-09).

Purpose: Humane, progressive intake that hides internal plumbing by default —
directly answers the "no raw internal labels in default chrome" product-failure bar.

Output: `VossComposer.tsx`, `composer.css`, the Wave-0 composer test, and App.tsx
wiring (open state + ⌘K + rail-trigger → composer; `currentSafetyMode` chip source).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-SPEC.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-RESEARCH.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md
@apps/voss-app/PRODUCT.md

<interfaces>
<!-- Verified from codebase 2026-06-14. -->
From apps/voss-app/src/org/cockpit/runIntake.ts:
  export type RunMode = 'Plan' | 'Edit' | 'Auto';
  export type RunTarget = 'native' | 'terminal';
  export interface RunIntakeState { goal; mode; target; team?; scope?; budget?; ... }
  export interface RunSpec { ... }
  export function assembleRunSpec(state: RunIntakeState): RunSpec;
  export function validateAutoStart(...): ...;   // gate before Autopilot

Safety-mode → RunMode mapping (UI-SPEC §Composer / PATTERNS §VossComposer):
  'Read only' → 'Plan'   (DEFAULT)
  'Can edit'  → 'Edit'
  'Autopilot' → 'Auto'

From apps/voss-app/src/App.tsx (after V24-02/03):
  activeView/setActiveView signal exists; <TopChrome onOpenComposer=...> and <PortalRail onOpenComposer=...> expect a handler.

VossComposer props this plan AUTHORS:
  export interface VossComposerProps { open: boolean; onClose: () => void; onCreated?: (spec: RunSpec) => void; }
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Author composer default-state test (Wave 0 gap)</name>
  <files>apps/voss-app/src/composer/__tests__/VossComposer.test.tsx</files>
  <read_first>
    - apps/voss-app/src/org/cockpit/__tests__/cockpit.test.tsx (invoke mock + render + assertion analog)
    - apps/voss-app/src/org/cockpit/runIntake.ts (RunMode/RunIntakeState/assembleRunSpec to integrate against)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§VossComposer.test.tsx)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§Component Inventory 3 + §Copywriting + §Interaction Contracts Composer)
  </read_first>
  <behavior>
    - Test 1: on open, the composer shows a textarea (ask field) and a control with aria-label "Safety mode"; the Advanced panel is NOT visible (absent or aria-expanded="false").
    - Test 2: the safety-mode control's default value is "Read only".
    - Test 3: the default view shows no scope/agent/team/budget/context fields and no Plan/Edit/Auto labels.
    - Test 4: clicking "Advanced ▸" reveals the advanced fields (aria-expanded flips to true; scope/budget inputs appear).
  </behavior>
  <action>
    Write `VossComposer.test.tsx` using the standard tauri-mock harness. Render `<VossComposer open={true}
    onClose={()=>{}} />` and assert: a `textarea` (ask field) exists; a `[aria-label="Safety mode"]` control
    exists with value/selected "Read only"; `#advanced-panel` is absent or `aria-expanded="false"`; no element
    with text exactly "Plan"/"Edit"/"Auto" and no scope/budget input present in the default view. Then simulate a
    click on the Advanced toggle and assert the advanced fields appear and `aria-expanded` becomes "true".
    RED until Task 2.
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- VossComposer 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - Test asserts default open state = ask field + safety control only, Advanced collapsed.
    - Test asserts safety default = "Read only".
    - Test asserts no Plan/Edit/Auto labels and no advanced fields visible by default.
    - Test asserts Advanced toggle reveals advanced fields (aria-expanded true).
    - Uses the standard harness; compiles and runs.
  </acceptance_criteria>
  <done>Composer default-state contract test exists (RED), pinning VADE2-04 behavior.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build VossComposer and wire it globally into App.tsx</name>
  <files>apps/voss-app/src/composer/VossComposer.tsx, apps/voss-app/src/composer/composer.css, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/org/cockpit/runIntake.ts (assembleRunSpec, RunIntakeState, validateAutoStart — reuse)
    - apps/voss-app/src/org/cockpit/RunCommandBar (existing intake control shape being replaced — what fields exist)
    - apps/voss-app/src/org/cockpit/cockpitStyles.css (panel expand + token styling analog)
    - apps/voss-app/src/App.tsx (activeView signal; TopChrome/PortalRail onOpenComposer handlers to connect)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§VossComposer.tsx — dialog ARIA, advanced collapse, runIntake reuse, focus-trap note)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§Component Inventory 3 — geometry/copy/ARIA, §Interaction Contracts Composer ⌘Enter, Escape)
  </read_first>
  <behavior>
    - Task 1 test passes (GREEN): default state = ask + safety (Read only) only; Advanced collapsed; Advanced expands on toggle.
    - "Create Task" assembles a RunSpec via assembleRunSpec with the safety→RunMode mapping; Autopilot passes validateAutoStart before starting.
    - Opening focuses the ask textarea; Escape closes and restores focus; ⌘Enter creates the Task.
  </behavior>
  <action>
    Build `VossComposer.tsx` as a modal `<dialog aria-label="Ask Voss to create a Task" aria-modal="true"
    open={props.open} onClose={props.onClose}>`. Default view: a full-width ask `<textarea aria-required="true"
    placeholder="Describe what you want Voss to do...">`, a safety-mode control `aria-label="Safety mode"` with
    options "Read only" | "Can edit" | "Autopilot" defaulting to "Read only" (D-04), an `Advanced ▸/▾` toggle
    button (`aria-expanded` + `aria-controls="advanced-panel"`), and a `Create Task` button (disabled when ask
    is empty; `var(--focus)` fill, weight 600). Advanced panel (`<Show when={advancedOpen()}>`, id
    `advanced-panel`): scope text input, agent target dropdown ("Any available"), team dropdown ("Solo"),
    budget number input ($, tabular-nums), attach-context input — these map to `RunIntakeState` fields.
    On Create: map safety mode → `RunMode` (Read only→Plan, Can edit→Edit, Autopilot→Auto), build a
    `RunIntakeState`, call `assembleRunSpec(state)`; for Autopilot run `validateAutoStart` first and block on
    failure with an inline error (`--accent-red`, 11px). Focus management: on open `createEffect(() => { if
    (props.open) askRef?.focus(); })`; set the background `inert` so Tab cannot escape to xterm (Pitfall 7);
    on close restore focus to the trigger. `⌘Enter` submits; bare Enter does NOT (terminal-dense app); Escape closes.
    Copy uses PRODUCT.md vocabulary exactly ("Ask Voss to…" with the Unicode ellipsis, "Create Task", safety labels).
    Write `composer.css` (modal centered, min-width 560 / max-width 720, `var(--bg-2)`, border `var(--border-bright)`,
    backdrop dim, 120ms ease open/close wrapped in the A8 reduced-motion double-guard) — tokens only, no raw hex.
    Edit `App.tsx`: add `const [composerOpen, setComposerOpen] = createSignal(false)`; pass
    `onOpenComposer={() => setComposerOpen(true)}` to `<TopChrome>` and `<PortalRail>`; mount `<VossComposer
    open={composerOpen()} onClose={() => setComposerOpen(false)} onCreated={...} />` above all layers; bind a
    global `⌘K` keydown to toggle the composer (without clobbering existing pane shortcuts). Feed the created
    Task's safety mode into the TopChrome `currentSafetyMode` chip source.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -v node_modules | grep -iE "composer|App.tsx" | head; npm test -- VossComposer 2>&1 | tail -12; grep -q "assembleRunSpec" src/composer/VossComposer.tsx && echo REUSES_INTAKE</automated>
  </verify>
  <acceptance_criteria>
    - `VossComposer.tsx` is a `<dialog aria-modal="true">` showing only ask + safety (default "Read only") on open; Advanced collapsed by default.
    - Advanced toggle reveals scope/agent/team/budget/context mapped to `RunIntakeState`.
    - Create Task calls `assembleRunSpec`; safety→RunMode mapping applied; Autopilot gated by `validateAutoStart`.
    - Focus lands on the ask field on open; Escape closes; ⌘Enter submits; background is `inert` while open.
    - `App.tsx` mounts the composer globally; ⌘K and the rail ask trigger open it; `onOpenComposer` wired to TopChrome + PortalRail.
    - `npm test -- VossComposer` passes GREEN; `npx tsc --noEmit` clean for composer/* and App.tsx.
    - `composer.css` uses tokens only; any open/close animation is inside the A8 double-guard; copy matches PRODUCT.md vocabulary.
  </acceptance_criteria>
  <done>Global Read-only-default composer is reachable from any surface, hides advanced controls by default, and reuses the run-intake assembler.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user ask text → assembleRunSpec → harness | The ask/scope/budget become a RunSpec dispatched to the harness (orchestration source of truth). |
| safety mode → RunMode | Composer safety control governs the agent's edit capability (cage posture). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V24-04-E | Elevation of Privilege | safety-mode default | mitigate | Default is "Read only" (least privilege, D-04). Autopilot ("Auto") MUST pass `validateAutoStart` before dispatch — the composer cannot silently start an edit/auto run. The UI maps to RunMode but does not bypass the harness/cage enforcement. |
| T-V24-04-I | Information Disclosure | composer + Tab focus | mitigate | Background set `inert` while open so Tab cannot reach a focused xterm pane behind the modal (prevents typed secrets leaking into a terminal). Ask text is not persisted to `.voss/` by the composer (no hidden writes on open). |
| T-V24-04-I2 | Injection | ask/scope text rendered back | mitigate | Composer echoes input via Solid-controlled inputs (value bindings), never innerHTML — no markup injection. The RunSpec is structured data, not interpolated shell. |
| T-V24-04-T | Tampering | npm/pip/cargo installs | mitigate | No new packages; reuses runIntake.ts. Zero install surface. |

No HIGH-severity threats. The privilege row (Read-only default + Autopilot gate) is the load-bearing mitigation.
</threat_model>

<verification>
- `npm test -- VossComposer` GREEN (default state, Read-only default, Advanced collapse).
- `npx tsc --noEmit` clean for composer/* and App.tsx.
- Full suite green at wave merge.
</verification>

<success_criteria>
The composer is reachable from any surface; on open shows only the prompt + a Read-only-defaulted safety
control; scope/agent/team/budget/context are hidden until Advanced (VADE2-04 acceptance met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-04-SUMMARY.md` when done.
</output>
