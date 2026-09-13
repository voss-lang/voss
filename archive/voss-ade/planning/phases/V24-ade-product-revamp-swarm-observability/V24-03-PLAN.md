---
phase: V24-ade-product-revamp-swarm-observability
plan: 03
type: execute
wave: 2
depends_on: ["V24-02"]
files_modified:
  - apps/voss-app/src/components/titlebar/TopChrome.tsx
  - apps/voss-app/src/components/titlebar/__tests__/TopChrome.test.tsx
  - apps/voss-app/src/components/titlebar/Titlebar.tsx
  - apps/voss-app/src/portal/PortalRail.tsx
  - apps/voss-app/src/portal/portal.css
  - apps/voss-app/src/App.tsx
autonomous: true
requirements: [VADE2-03]
must_haves:
  truths:
    - "Default top chrome shows project/window identity, command-palette trigger, mode indicator, and live chip only"
    - "Default top chrome contains NO fanout/pipeline/swarm/watchers preset controls and NO raw Plan/Edit/Auto toggle"
    - "The fanout/pipeline/swarm/watchers presets remain reachable from a layout menu in the portal rail / pane control"
  artifacts:
    - path: "apps/voss-app/src/components/titlebar/TopChrome.tsx"
      provides: "Quiet 28px chrome: WindowControls, project name, ⌘K trigger, safety-mode chip, live chip — no PresetSwitcher, no mode toggle"
      contains: "TopChrome"
    - path: "apps/voss-app/src/components/titlebar/__tests__/TopChrome.test.tsx"
      provides: "Source/DOM assertion: no preset and no Plan/Edit/Auto in default chrome"
      contains: "TopChrome"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "TopChrome"
      via: "App mounts <TopChrome> instead of preset-bearing <Titlebar>"
      pattern: "TopChrome"
    - from: "apps/voss-app/src/portal/PortalRail.tsx"
      to: "PresetSwitcher"
      via: "layout menu re-mounts the existing PresetSwitcher component"
      pattern: "PresetSwitcher"
---

<objective>
Make the top chrome quiet (VADE2-03): a new `TopChrome` component retains only
project/window identity, the command-palette (`⌘K`) trigger, a safety-mode
indicator chip, and the existing live chip. The `fanout/pipeline/swarm/watchers`
presets (today's `PresetSwitcher`) and the raw `Plan/Edit/Auto` mode toggle are
removed from top chrome. The presets are demoted to a layout menu reachable from
the portal rail (the `PresetSwitcher` component itself is unchanged — only its
mount point moves).

Purpose: One of the two hard product-failure conditions (from SPEC Interview Log)
is "raw internal labels in default chrome" / "presets-as-navigation". This plan
eliminates both.

Output: `TopChrome.tsx` + its source-assertion test, `Titlebar.tsx` with
PresetSwitcher/mode-toggle removed (or superseded by TopChrome), a layout-menu
mount of PresetSwitcher in the portal rail, and App.tsx swapping `<Titlebar>`→`<TopChrome>`.
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
From apps/voss-app/src/components/titlebar/Titlebar.tsx:
  export type TitlebarProps = { projectName?; liveState?; orgViewOpen?; onOrgViewChange?; ... };
  L102: <PresetSwitcher activeLayout=... disabled=... onSelect=... />  ← REMOVE from chrome
  L112: <div class="titlebar-modetoggle" role="group" aria-label="View mode"> ... </div>  ← REMOVE (Plan/Edit/Auto)
  L131-143: .titlebar-livechip  ← KEEP (reuse as-is)
  L63-95: WindowControls + project name + Voss logo  ← KEEP

From apps/voss-app/src/components/titlebar/PresetSwitcher.tsx:
  Self-contained. Props: { activeLayout; disabled; onSelect }. Component UNCHANGED — only mount point moves.

From apps/voss-app/src/App.tsx:
  L1415: <Titlebar .../>  ← swap to <TopChrome .../>
  activeView/setActiveView signal exists after V24-02.

TopChrome props this plan AUTHORS:
  export type TopChromeProps = {
    projectName?: string;
    liveState?: 'live' | 'snapshot';
    currentSafetyMode?: 'Read only' | 'Can edit' | 'Autopilot';
    onOpenComposer?: () => void;
  };
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Author TopChrome source-assertion test (Wave 0 gap)</name>
  <files>apps/voss-app/src/components/titlebar/__tests__/TopChrome.test.tsx</files>
  <read_first>
    - apps/voss-app/src/org/cockpit/__tests__/a11y.test.tsx (readFileSync + DOM/source assertion analog)
    - apps/voss-app/src/components/titlebar/Titlebar.tsx (what to assert is REMOVED)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§Vitest Test Harness Setup, §a11y CSS source assertion)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§Component Inventory 2 — what stays vs removed)
  </read_first>
  <behavior>
    - Test 1: rendered TopChrome DOM contains no PresetSwitcher controls — no element with the preset labels fanout/pipeline/swarm/watchers.
    - Test 2: rendered TopChrome DOM contains no raw Plan/Edit/Auto mode toggle (no titlebar-modetoggle group, no "Plan"/"Edit"/"Auto" toggle buttons).
    - Test 3: TopChrome renders the ⌘K command-palette trigger and (when currentSafetyMode set) a mode chip showing one of Read only / Can edit / Autopilot.
  </behavior>
  <action>
    Write `TopChrome.test.tsx` using the standard harness (mount/dispose,
    `vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }))`). Render `<TopChrome />` and assert:
    (a) DOM has NO text/aria matching the preset names `fanout`, `pipeline`, `swarm`, `watchers` and no
    `PresetSwitcher`-class element; (b) DOM has NO `titlebar-modetoggle` element and no button labeled
    exactly `Plan`, `Edit`, or `Auto`; (c) with `currentSafetyMode="Read only"`, a chip with text "Read only"
    is present; (d) a ⌘K trigger button (aria-label or text containing "⌘K") is present. Also add a source
    assertion using `readFileSync('src/components/titlebar/TopChrome.tsx','utf8')` that the file does NOT
    import `PresetSwitcher` and contains no `titlebar-modetoggle`. RED until Task 2.
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- TopChrome 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `TopChrome.test.tsx` compiles and runs with the standard tauri-mock harness.
    - Asserts absence of preset names (fanout/pipeline/swarm/watchers) and absence of Plan/Edit/Auto toggle in rendered DOM.
    - Asserts presence of the ⌘K trigger and a safety-mode chip when `currentSafetyMode` is provided.
    - Includes a `readFileSync` source assertion that TopChrome.tsx does not import PresetSwitcher.
  </acceptance_criteria>
  <done>TopChrome contract test exists (RED), pinning the no-preset / no-mode-toggle requirement.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build TopChrome, strip presets from Titlebar, demote presets to layout menu, swap in App</name>
  <files>apps/voss-app/src/components/titlebar/TopChrome.tsx, apps/voss-app/src/components/titlebar/Titlebar.tsx, apps/voss-app/src/portal/PortalRail.tsx, apps/voss-app/src/portal/portal.css, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/components/titlebar/Titlebar.tsx (FULL — copy structure, remove PresetSwitcher L102 + modetoggle L112)
    - apps/voss-app/src/components/titlebar/PresetSwitcher.tsx (props shape; re-mount unchanged in layout menu)
    - apps/voss-app/src/components/titlebar/WindowControls.tsx (keep as-is)
    - apps/voss-app/src/App.tsx (L1415 Titlebar mount; activeView signal from V24-02; the preset/layout state currently passed to Titlebar)
    - apps/voss-app/src/portal/PortalRail.tsx (from V24-02 — add the layout-menu trigger here)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§TopChrome.tsx — structural analog + props shape)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§Component Inventory 2 + Glyph Affordances + Color safety chips)
  </read_first>
  <behavior>
    - The Task 1 TopChrome test passes (GREEN).
    - PresetSwitcher renders inside a layout menu opened from the portal rail (still functional: selecting fanout/pipeline/swarm/watchers drives the same layout state it drove before).
  </behavior>
  <action>
    Build `TopChrome.tsx` (props `TopChromeProps` from interfaces): copy the KEEP structure from
    `Titlebar.tsx` (28px height via `var(--titlebar-height)`, `WindowControls`, drag regions, Voss logo +
    project name truncated 180px, the existing `.titlebar-livechip` reused as-is). ADD a ⌘K command-palette
    trigger button (`onClick={props.onOpenComposer}`, `--font-mono` 11px, `var(--bg-2)` bg, `var(--border)`)
    and a mode-status chip driven by `props.currentSafetyMode` colored per UI-SPEC safety chips
    ("Read only" = muted `--fg-3`/`--bg-3`; "Can edit" = `--accent-amber`; "Autopilot" = `--accent-red`),
    hidden when undefined. Do NOT import PresetSwitcher; do NOT render a Plan/Edit/Auto toggle.
    Edit `Titlebar.tsx`: remove the `<PresetSwitcher>` mount (L102) and the `titlebar-modetoggle` group (L112).
    (Titlebar may remain for legacy A1/A3 tests but must no longer surface presets/mode toggle in its render.)
    Add a "Layout" affordance to `PortalRail.tsx` (a small button in the rail bottom area, distinct from the
    8 nav tabs and the ask trigger) that opens a layout menu/dropdown mounting the UNCHANGED `<PresetSwitcher>`
    with the same `activeLayout`/`disabled`/`onSelect` props it received in Titlebar. Style the menu in
    `portal.css` with tokens only (no raw hex). Lift the preset/layout state and `onSelect` handler that App
    previously passed to `<Titlebar>` so they now flow to PortalRail's layout menu.
    Edit `App.tsx`: replace the `<Titlebar .../>` mount (L1415) with `<TopChrome projectName=... liveState=...
    currentSafetyMode=... onOpenComposer=... />`; route the former preset props to `<PortalRail>`'s layout menu.
    `currentSafetyMode` reflects the most-recently-created Task's safety mode (or undefined when none).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -v node_modules | grep -iE "TopChrome|Titlebar|PortalRail|App.tsx" | head; npm test -- TopChrome 2>&1 | tail -12; grep -L "PresetSwitcher" src/components/titlebar/TopChrome.tsx >/dev/null && echo NO_PRESET_IMPORT</automated>
  </verify>
  <acceptance_criteria>
    - `TopChrome.tsx` exists, does NOT import PresetSwitcher, and renders no Plan/Edit/Auto toggle.
    - `Titlebar.tsx` no longer mounts `<PresetSwitcher>` and no longer renders the `titlebar-modetoggle` group.
    - `PortalRail.tsx` mounts the UNCHANGED `<PresetSwitcher>` inside a layout menu (presets remain reachable).
    - `App.tsx` mounts `<TopChrome>` in place of the preset-bearing `<Titlebar>`; preset state flows to the rail layout menu.
    - `npm test -- TopChrome` passes GREEN; `npx tsc --noEmit` clean for the modified files.
    - All new styles use `var(--*)` tokens; no raw hex (grep portal.css / TopChrome inline styles).
  </acceptance_criteria>
  <done>Default chrome is quiet (identity + ⌘K + mode chip + live chip); presets demoted to the portal layout menu and still functional.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user → chrome controls (Solid signals) | Pure UI; no backend crossing. |
| project name → chrome render | Project name string rendered into DOM (display text). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V24-03-I1 | Information Disclosure | TopChrome render of runId | mitigate | Per D-09, raw `runId`/`RunData` identifiers MUST NOT appear in chrome. The mode chip shows the safety-mode label only, never a run id. Enforced by the no-raw-label requirement. |
| T-V24-03-I2 | Injection | project name text node | mitigate | Project name is rendered as a Solid text child (auto-escaped), never via innerHTML — no DOM injection from a malicious project path/name. |
| T-V24-03-T | Tampering | npm/pip/cargo installs | mitigate | No new packages; PresetSwitcher reused unchanged. Zero install surface. |
| T-V24-03-E | Elevation of Privilege | safety-mode chip | accept | Chip is display-only; it does not grant edit capability. Actual safety enforcement lives in run intake/cage, not the chip. Low risk. |

No HIGH-severity threats.
</threat_model>

<verification>
- `npm test -- TopChrome` GREEN; presets absent from chrome, present in layout menu.
- `npx tsc --noEmit` clean for titlebar/* and App.tsx.
- Full suite green at wave merge: `cd apps/voss-app && npm test`.
</verification>

<success_criteria>
Default top chrome contains no fanout/pipeline/swarm/watchers presets and no Plan/Edit/Auto toggle;
presets remain reachable from a layout menu (VADE2-03 acceptance met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-03-SUMMARY.md` when done.
</output>
