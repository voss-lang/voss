---
phase: A1-voss-app-tauri-shell
plan: 03
type: execute
wave: 3
depends_on: ["A1-02"]
files_modified:
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/components/titlebar/Titlebar.tsx
  - apps/voss-app/src/components/titlebar/WindowControls.tsx
  - apps/voss-app/src/components/titlebar/PresetSwitcher.tsx
autonomous: false
requirements: [SHL-03, SHL-04]
must_haves:
  truths:
    - "A 22px custom titlebar renders at the top of the window with project-name placeholder 'Voss ADE' and a 4-button preset switcher"
    - "On macOS, three traffic-light circles (close/minimize/zoom) render and each operates only the app's own window"
    - "Close quits, minimize minimizes, zoom toggles fullscreen"
    - "Dragging an empty titlebar area moves the window; clicking a control button does NOT drag the window"
    - "No cost-meter slot / model indicator / token count appears anywhere in the titlebar"
    - "The window body below the titlebar is empty solid --bg-0"
  artifacts:
    - path: "apps/voss-app/src/components/titlebar/Titlebar.tsx"
      provides: "22px flex titlebar with drag-region spacers + 3 regions"
      contains: "data-tauri-drag-region"
    - path: "apps/voss-app/src/components/titlebar/WindowControls.tsx"
      provides: "Platform-switched controls: MacTrafficLights | StubControls"
      contains: "getCurrentWindow"
    - path: "apps/voss-app/src/components/titlebar/PresetSwitcher.tsx"
      provides: "Visual-only 4-preset switcher (fanout/pipeline/swarm/watchers)"
      contains: "pipeline"
    - path: "apps/voss-app/src/App.tsx"
      provides: "Root layout: Titlebar over empty --bg-0 body"
      contains: "Titlebar"
  key_links:
    - from: "apps/voss-app/src/components/titlebar/WindowControls.tsx"
      to: "@tauri-apps/api/window"
      via: "getCurrentWindow().close/minimize/setFullscreen"
      pattern: "getCurrentWindow\\(\\)"
    - from: "apps/voss-app/src/components/titlebar/WindowControls.tsx"
      to: "@tauri-apps/plugin-os"
      via: "platform() gate -> macos|stub"
      pattern: "platform\\(\\)"
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/components/titlebar/Titlebar.tsx"
      via: "import + render above empty body"
      pattern: "import Titlebar"
---

<objective>
Build the custom window chrome (D-03, D-04): a 22px Variant B titlebar with macOS traffic-light controls (fully implemented + verified on macOS), a platform-abstracted control boundary so linux/win is a `StubControls` fill-in, a project-name placeholder, and a visual-only layout-preset switcher. Wire it into `App.tsx` above the empty body.

Purpose: SHL-03 (custom titlebar: project-name placeholder + visual-only preset switcher, NO cost-meter slot) and SHL-04 (window controls: traffic lights mac / stub elsewhere / zoom / fullscreen / multi-monitor). `decorations: false` (set in Plan A1-01's tauri.conf) means voss-app owns all window chrome.

Output: Hand-rolled Solid titlebar + window controls + preset switcher consuming Variant B tokens; functional macOS window management; the abstraction seam linux/win completes in A10.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md
@.planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md
@.planning/phases/A1-voss-app-tauri-shell/A1-PATTERNS.md
@.planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md
@.planning/phases/A1-voss-app-tauri-shell/A1-02-SUMMARY.md

<interfaces>
<!-- All titlebar files are greenfield — no in-repo analog. The authoritative
     component bodies are in A1-PATTERNS.md; the visual contract is A1-UI-SPEC.md. -->

Tauri JS window API (from @tauri-apps/api/window, present via Plan A1-01 deps):
  const win = getCurrentWindow();
  win.close()              -> needs core:window:allow-close
  win.minimize()           -> needs core:window:allow-minimize
  win.toggleMaximize()     -> needs core:window:allow-toggle-maximize
  win.setFullscreen(bool)  -> needs core:window:allow-set-fullscreen
  win.isFullscreen()       -> needs core:window:allow-is-fullscreen
(data-tauri-drag-region    -> needs core:window:allow-start-dragging)
All 7 permissions were written to src-tauri/capabilities/default.json in
Plan A1-01 — do NOT re-edit capabilities here; just consume them.

Platform gate (from @tauri-apps/plugin-os, present via Plan A1-01 deps;
tauri_plugin_os::init() registered in lib.rs by Plan A1-02):
  import { platform } from '@tauri-apps/plugin-os';
  await platform() === 'macos'  -> render <MacTrafficLights/>, else <StubControls/>

From Plan A1-02: App.tsx currently is a single full-viewport div with
  background var(--bg-0) (no Titlebar yet). This plan REPLACES App.tsx with
  the Titlebar-over-empty-body layout from A1-PATTERNS.md.

macOS traffic-light colors are OS-convention hardcoded values (NOT theme
tokens): close #ff5f57, minimize #febc2e, zoom #28c840. Sole exception to
the "no raw hex in components" rule (A1-UI-SPEC "macOS Traffic-Light Colors").
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: WindowControls (platform-switched) + PresetSwitcher (visual-only)</name>
  <files>apps/voss-app/src/components/titlebar/WindowControls.tsx, apps/voss-app/src/components/titlebar/PresetSwitcher.tsx</files>
  <read_first>
    - .planning/phases/A1-voss-app-tauri-shell/A1-PATTERNS.md ("apps/voss-app/src/components/titlebar/WindowControls.tsx", "apps/voss-app/src/components/titlebar/PresetSwitcher.tsx" sections — exact component bodies)
    - .planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md ("Window Controls Contract", "Titlebar Contract" preset-switcher styling, "Named Spacing Exceptions" table, "macOS Traffic-Light Colors")
    - .planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md ("Pattern 2: Tauri 2 Custom Titlebar", Open Question 2 — @tauri-apps/plugin-os platform())
  </read_first>
  <action>
    Create `WindowControls.tsx` with three parts per A1-PATTERNS.md: (a) `MacTrafficLights` — a `display:flex; gap:6px; align-items:center; padding-left:12px` row of three 12px `border-radius:50%` buttons (close `#ff5f57`, minimize `#febc2e`, zoom `#28c840` — hardcoded OS-convention hex, the sole raw-hex exception); close calls `getCurrentWindow().close()`, minimize calls `.minimize()`, zoom maintains a `createSignal<boolean>` initialized via `await win.isFullscreen()` in `onMount` and toggles `win.setFullscreen(next)`; `title` attrs `"close"`/`"minimize"`/`"zoom"`; hover `opacity:0.8`. (b) `StubControls` — returns `null` (linux/win deferred to A10 per D-04; the abstraction boundary must exist now). (c) default-export `WindowControls` — `createSignal` for os, `onMount` sets `await platform()` (try/catch -> `'unknown'`), renders `<Show when={os()==='macos'} fallback={<StubControls/>}><MacTrafficLights/></Show>`. The 6px gap and 12px offset are named spacing exceptions (A1-UI-SPEC Dimension 5) — do NOT snap to a 4px grid.

    Create `PresetSwitcher.tsx` per A1-PATTERNS.md: a `For`-mapped row over `['fanout','pipeline','swarm','watchers']`, container `display:flex; border:1px solid var(--border); overflow:hidden` with `border-radius:0` (Variant B — the sketch's rounded preset is sketch-convenience CSS only; A1 uses 0 radius per D-02), each button `background: active? var(--focus): transparent`, `color: active? white: var(--fg-2)`, `padding:4px 10px`, `font-family:var(--font-mono)`, `font-size:11px`, inter-button `border-right:1px solid var(--border)` except the last. Default active = `'pipeline'` (matches sketch default, A1-UI-SPEC). Clicking only updates the active signal — VISUAL ONLY, no layout geometry, no callback (D-04; behavior is A4/L2). Use `var(--token)` for all colors (no raw hex — preset switcher is theme-driven, unlike the OS traffic lights).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -q 'getCurrentWindow' apps/voss-app/src/components/titlebar/WindowControls.tsx && grep -q "from '@tauri-apps/plugin-os'" apps/voss-app/src/components/titlebar/WindowControls.tsx && grep -q 'function StubControls' apps/voss-app/src/components/titlebar/WindowControls.tsx && grep -q 'setFullscreen' apps/voss-app/src/components/titlebar/WindowControls.tsx && grep -q '#ff5f57' apps/voss-app/src/components/titlebar/WindowControls.tsx && grep -q 'pipeline' apps/voss-app/src/components/titlebar/PresetSwitcher.tsx && grep -q 'fanout' apps/voss-app/src/components/titlebar/PresetSwitcher.tsx && ! grep -E '#[0-9a-fA-F]{6}' apps/voss-app/src/components/titlebar/PresetSwitcher.tsx && ! grep -iq 'cost' apps/voss-app/src/components/titlebar/PresetSwitcher.tsx && pnpm -C apps/voss-app build 2>&1 | tail -1</automated>
  </verify>
  <done>
    `WindowControls.tsx` exports a platform-switched component (MacTrafficLights with the 3 OS-hex circles + Tauri window calls; StubControls returns null; platform() gate); `PresetSwitcher.tsx` is a 4-preset visual-only switcher using only `var(--token)` colors, default `pipeline`, no cost element; `pnpm build` exits 0.
  </done>
</task>

<task type="auto">
  <name>Task 2: Titlebar assembly + App.tsx root layout</name>
  <files>apps/voss-app/src/components/titlebar/Titlebar.tsx, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx (the file being replaced — current empty-body div from Plan A1-02)
    - .planning/phases/A1-voss-app-tauri-shell/A1-PATTERNS.md ("apps/voss-app/src/components/titlebar/Titlebar.tsx", "apps/voss-app/src/App.tsx" sections — exact bodies; "data-tauri-drag-region Placement" shared pattern)
    - .planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md ("Titlebar Contract" — dimensions, layout regions, drag-region rule, project-name placeholder, explicit NON-inclusion of cost meter; "Empty Body Contract")
    - .planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md ("Pitfall 1: data-tauri-drag-region not propagating to children", "Pitfall 2: sharp corners intentional")
  </read_first>
  <action>
    Create `Titlebar.tsx` per A1-PATTERNS.md / A1-UI-SPEC.md Titlebar Contract: an outer `<div>` `display:flex; align-items:center; height:var(--titlebar-height)` (22px, D-02 locked) `flex-shrink:0; background:var(--bg-0); border-bottom:1px solid var(--border); overflow:hidden`. Children left-to-right exactly: `<WindowControls/>`, a left spacer `<div data-tauri-drag-region style="flex:1">`, the project-name placeholder `<div>` ("Voss ADE", `color:var(--fg-1); font-size:11px; font-family:var(--font-mono); pointer-events:none`), a right spacer `<div data-tauri-drag-region style="flex:1">`, `<PresetSwitcher/>`. CRITICAL (RESEARCH Pitfall 1, A1-PATTERNS "data-tauri-drag-region Placement"): `data-tauri-drag-region` goes ONLY on the two spacer divs — NEVER on the outer container; window controls and preset switcher are siblings of the spacers, never children of a drag region (otherwise button clicks drag the window). No cost-meter slot, no model indicator, no token count anywhere (A1-UI-SPEC explicit NON-inclusion, Q6).

    Replace `apps/voss-app/src/App.tsx` per A1-PATTERNS.md: an outer flex-column `<div>` `height:100vh; width:100vw; overflow:hidden` containing `<Titlebar/>` then an empty body `<div style="flex:1; background:var(--bg-0)">` (Empty Body Contract — no content, no placeholder text, no loading state; grid/PTY are A2/A3).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -q 'data-tauri-drag-region' apps/voss-app/src/components/titlebar/Titlebar.tsx && [ "$(grep -c 'data-tauri-drag-region' apps/voss-app/src/components/titlebar/Titlebar.tsx)" -eq 2 ] && grep -q 'var(--titlebar-height)' apps/voss-app/src/components/titlebar/Titlebar.tsx && grep -q 'Voss ADE' apps/voss-app/src/components/titlebar/Titlebar.tsx && grep -q 'WindowControls' apps/voss-app/src/components/titlebar/Titlebar.tsx && grep -q 'PresetSwitcher' apps/voss-app/src/components/titlebar/Titlebar.tsx && ! grep -iqE 'cost|model-indicator|token.?count' apps/voss-app/src/components/titlebar/Titlebar.tsx && grep -q 'import Titlebar' apps/voss-app/src/App.tsx && pnpm -C apps/voss-app build 2>&1 | tail -1</automated>
  </verify>
  <done>
    `Titlebar.tsx` is a 22px flex titlebar with EXACTLY 2 `data-tauri-drag-region` spacer divs (none on the outer container), the "Voss ADE" placeholder, WindowControls + PresetSwitcher as siblings, and no cost/model/token element; `App.tsx` renders Titlebar over an empty `var(--bg-0)` body; `pnpm build` exits 0.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Verify custom chrome — controls, drag, no cost slot, typography distinctness</name>
  <files>(none — verification-only checkpoint; observes Task 1+2 output, modifies nothing)</files>
  <read_first>
    - .planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md ("Titlebar Contract", "Window Controls Contract", "Typography" HiDPI verification note, "Anti-Patterns")
    - .planning/phases/A1-voss-app-tauri-shell/A1-VALIDATION.md ("Manual-Only Verifications", "Per-Task Verification Map" SHL-03/04 rows)
  </read_first>
  <action>Pause for the human to run `pnpm tauri dev` and exercise the custom chrome per &lt;how-to-verify&gt;: window controls (close/minimize/zoom), drag-to-move without button-drag bleed, absence of any cost/model/token slot, visual-only preset switching, and 11px titlebar legibility on the target Retina display. No code is written; this checkpoint validates Task 1 + Task 2 and the T-A1-01 capability-gating + RESEARCH Pitfall 1 mitigations.</action>
  <verify>Human types "approved" after confirming all controls work, drag works without button-drag bleed, no cost slot exists, preset switcher is visual-only, and titlebar typography is legible.</verify>
  <done>Custom chrome behavior confirmed by the human across all checklist items; explicit approval recorded.</done>
  <what-built>
    The full custom titlebar: macOS traffic-light cluster (functional close/minimize/zoom), project-name placeholder "Voss ADE", visual-only 4-preset switcher, drag-to-move via spacer regions, over an empty Variant B body. linux/win render `StubControls` (null) — deferred to A10.
  </what-built>
  <how-to-verify>
    1. `cd apps/voss-app && pnpm tauri dev`.
    2. Titlebar: confirm a thin (~22px) bar with three colored circles (red/yellow/green) at the left, the text "Voss ADE" centered-ish, and a 4-button switcher (fanout · pipeline · swarm · watchers) at the right with `pipeline` highlighted by default.
    3. Click each preset button — confirm only the highlighted button changes (no layout/window change). Confirm there is NO cost meter, NO model indicator, NO token count anywhere on the bar.
    4. Click the green (zoom) circle — window toggles fullscreen; click again — restores. Click yellow — window minimizes (restore from Dock). Click red LAST — window closes (app quits).
    5. Relaunch. Drag an empty area of the titlebar (between the name and the controls) — the window moves. Then click a traffic-light/preset button — confirm the window does NOT drag while clicking (RESEARCH Pitfall 1 mitigation).
    6. Typography distinctness (A1-UI-SPEC HiDPI note, Dimension 4): on this Apple Silicon Retina display confirm the 11px titlebar text and the (future) 11.5px body delta is acceptable; for A1 specifically confirm the titlebar text is crisp and legible at 11px mono.
    7. Multi-monitor (if a second display is available): drag the window to the other monitor and confirm controls still operate the correct window; otherwise note "single monitor only — multi-monitor unverified".
  </how-to-verify>
  <resume-signal>Type "approved" if all controls work, drag works, no cost slot exists, and titlebar typography is legible — or describe the deviation.</resume-signal>
  <acceptance_criteria>
    - macOS: close quits, minimize minimizes, zoom toggles fullscreen — each acts only on the app window (T-A1-01)
    - Dragging an empty titlebar area moves the window; clicking a button does NOT drag (RESEARCH Pitfall 1)
    - No cost-meter / model / token element anywhere in the titlebar (SHL-03, Q6)
    - Preset switcher is visual-only (click changes highlight only, no layout change)
    - Titlebar 11px mono text renders legibly on the target Retina display
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Webview titlebar → Tauri window API | Button clicks invoke native window operations via the capability-gated JS API |
| Webview → @tauri-apps/plugin-os | platform() reads OS identity (no untrusted input) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A1-01 | Elevation of Privilege | Window control calls | mitigate | All window ops go through `@tauri-apps/api/window` which is gated by `capabilities/default.json` (close/minimize/toggle-maximize/set-fullscreen/is-fullscreen/start-dragging only — written in Plan A1-01). No raw OS call; calls affect only the current window |
| T-A1-02 | Spoofing | Drag region clickjacking | accept | The titlebar is 100% voss-app-owned content — no iframe, no external/remote content, no embedded webview. `data-tauri-drag-region` is confined to inert spacer divs (RESEARCH Pitfall 1 placement enforced). Low risk, no user-data surface in A1 |
| T-A1-03 | Tampering | Hardcoded traffic-light hex bypassing token system | accept | Intentional, documented exception: `#ff5f57`/`#febc2e`/`#28c840` are OS-convention colors deliberately NOT token-driven (A1-UI-SPEC). Not a security issue; logged here to record the deliberate carve-out so a checker does not flag it |
</threat_model>

<verification>
- `WindowControls.tsx`: platform-switched, MacTrafficLights with 3 OS-hex circles + Tauri window calls, StubControls returns null, `platform()` gate.
- `PresetSwitcher.tsx`: 4 presets, default `pipeline`, only `var(--token)` colors, no cost element.
- `Titlebar.tsx`: 22px, EXACTLY 2 `data-tauri-drag-region` spacers (none on outer div), "Voss ADE" placeholder, no cost/model/token.
- `App.tsx` imports + renders Titlebar over an empty `var(--bg-0)` body.
- `pnpm -C apps/voss-app build` exits 0.
- Human checkpoint: controls functional, drag works without button-drag bleed, no cost slot, legible 11px titlebar.
</verification>

<success_criteria>
- Custom 22px Variant B titlebar with project-name placeholder + visual-only preset switcher, NO cost-meter slot (SHL-03).
- macOS traffic-light controls functional (close/minimize/zoom-fullscreen); platform abstraction so linux/win is a StubControls fill-in (SHL-04, D-04).
- Drag-to-move works via spacer regions without button-drag bleed.
- Body below titlebar is empty solid `--bg-0`.
</success_criteria>

<output>
Create `.planning/phases/A1-voss-app-tauri-shell/A1-03-SUMMARY.md` when done.
</output>
