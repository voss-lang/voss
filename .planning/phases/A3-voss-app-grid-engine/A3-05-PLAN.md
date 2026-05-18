---
phase: A3-voss-app-grid-engine
plan: 05
type: execute
wave: 4
depends_on: [A3-02, A3-04]
files_modified:
  - apps/voss-app/src/grid/PaneHeader.tsx
  - apps/voss-app/src/grid/DotMenu.tsx
  - apps/voss-app/src/grid/CloseConfirmBanner.tsx
  - apps/voss-app/src/grid/SplitNode.tsx
  - apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx
autonomous: true
requirements: [GRD-02, GRD-06, GRD-07]
must_haves:
  truths:
    - "Every pane header is 22px and shows ● dot · index · cwd basename · shell · process · ⋯ menu"
    - "The pane index segment matches the ⌘-number that focuses that pane"
    - "The ⋯ menu shows exactly 5 items (Fork pane, Split right, Split below, separator, Close pane) acting on that pane"
    - "⌘W / Close pane on a pane running a foreground process shows the inline confirm banner; an idle shell closes with no confirm"
    - "Header bg lifts to --bg-2 on the focused pane and reverts to --bg-1 unfocused, instant repaint, no border ring"
  artifacts:
    - path: "apps/voss-app/src/grid/PaneHeader.tsx"
      provides: "22px Variant B header: A2 segments + index + ⋯ trigger"
      contains: "aria-label=\"Pane menu\""
    - path: "apps/voss-app/src/grid/DotMenu.tsx"
      provides: "128px 5-item ⋯ popup (fork/split/split/sep/close)"
      contains: "Close pane"
    - path: "apps/voss-app/src/grid/CloseConfirmBanner.tsx"
      provides: "22px inline running-process confirm banner"
      contains: "Close anyway"
    - path: "apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx"
      provides: "Vitest coverage of header/menu/confirm + close-gating"
      contains: "Close anyway"
  key_links:
    - from: "apps/voss-app/src/grid/CloseConfirmBanner.tsx"
      to: "apps/voss-app/src/grid/operations.ts"
      via: "Close anyway → closeFocused"
      pattern: "closeFocused"
    - from: "apps/voss-app/src/grid/DotMenu.tsx"
      to: "apps/voss-app/src/grid/operations.ts"
      via: "menu items → forkFocused/splitFocused; close → gated close"
      pattern: "forkFocused|splitFocused"
    - from: "apps/voss-app/src/grid/SplitNode.tsx"
      to: "apps/voss-app/src/grid/PaneHeader.tsx"
      via: "leaf overlay mounts PaneHeader at the A3-05 seam"
      pattern: "PaneHeader"
---

<objective>
Build the per-pane Variant B chrome: the 22px header (A2 segments + new index segment +
`⋯` trigger), the 5-item `⋯` menu, and the running-process close-confirm banner — wiring
the foreground-detection close gate.

Purpose: This completes the user-facing pane surface and the only A2-touching change
permitted (additive header index + `⋯` hook). It depends on A3-04 (the leaf mount seam)
and A3-02 (`closeFocused`/`forkFocused`/`splitFocused`).

Output: `PaneHeader.tsx`, `DotMenu.tsx`, `CloseConfirmBanner.tsx`, and the A3-04 seam
filled in `SplitNode.tsx`. Implements GRD-06 (22px Variant B header + `⋯` menu), the
close-confirm half of GRD-02, and GRD-07 header bg-lift.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

<interfaces>
<!-- From A3-02/A3-04 (depends_on). Consume directly. -->
From apps/voss-app/src/grid/operations.ts:
  forkFocused(store); splitFocused(store,"H"|"V"); closeFocused(store)
From apps/voss-app/src/grid/tree.ts:
  PaneLeaf { id; cwd; shell; index }; GridStore { root; focusedId }

A2 pane unit + foreground detection (assumed-present upstream — DO NOT modify A2 internals;
only the two additive header changes below are permitted):
  apps/voss-app/src/pane/PaneComponent.tsx renders A2's own header segments:
    ● status dot · cwd basename · shell · foreground-process indicator.
  A2 foreground detection (A2 D-07): A2 exposes the running foreground command via the
  PTY Channel event { type: "fg_process", name: string } AND a Rust command
  invoke('get_fg_process', { sessionId }) -> string|null (A2-02/A2-04 contract).
  A3 consumes this as a BLACK BOX to answer "is a foreground process other than the bare
  interactive shell running?" — A3 does NOT reimplement detection (A3-PATTERNS
  "### A2 Foreground Detection Reuse").
  Permitted A2-touching change: add the numeric index segment + the ⋯ trigger to the
  header. Everything else in the A2 header is consumed unchanged.

A1 token system (assumed-present upstream — verbatim, never redefine):
  Tailwind: bg-bg-1/2/3, border-border, text-fg-0/1/2/3, text-accent-red,
  text-accent-green, font-mono. NO border-radius, NO CSS transition.
</interfaces>

@.planning/phases/A3-voss-app-grid-engine/A3-SPEC.md
@.planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md
@.planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md
@.planning/phases/A2-voss-app-pty-pane/A2-CONTEXT.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: PaneHeader.tsx — 22px header with index segment + ⋯ trigger</name>
  <files>apps/voss-app/src/grid/PaneHeader.tsx, apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md "## Pane Header Contract (GRD-06)" — segment order, colors (focused/unfocused), 22px height, 10px index metadata role, overflow policy, aria-labels (governing contract — exact values locked)
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### apps/voss-app/src/grid/PaneHeader.tsx" — additive-edit rule (only index + ⋯ may be added)
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-06 + GRD-07 (header bg-lift on focus, no border ring)
    - apps/voss-app/src/pane/PaneComponent.tsx — A2 header segments consumed unchanged (read prop/segment shape only; do NOT modify A2 internals)
  </read_first>
  <behavior>
    - PaneHeader renders, left-to-right: ● dot, │, index digit, │, cwd basename, │, shell, │, process, flex spacer, ⋯ trigger.
    - The index segment renders the leaf's `index` as a plain digit at the 10px metadata role; focused color = text-fg-1, unfocused = text-fg-3.
    - Header container height is exactly 22px and padding is 0 10px.
    - Focused header background is bg-bg-2; unfocused is bg-bg-1; no CSS transition on the change (instant repaint — GRD-07 / perf budget).
    - The ⋯ trigger carries aria-label="Pane menu" and the ● dot carries aria-label "Shell running" / "Shell exited" by state (assistive-only, not visually rendered as text).
    - The process segment is absent (empty string → hidden, not a dash) when there is no foreground process.
    - Clicking the ⋯ trigger toggles a `menuOpen` signal/callback passed from the parent.
  </behavior>
  <action>
    Create `apps/voss-app/src/grid/PaneHeader.tsx` (Solid) implementing the A3-UI-SPEC
    "Pane Header Contract" VERBATIM: a single `display:flex; align-items:center` row, 22px
    height, `padding: 0 10px`, segment order `● │ index │ cwd │ shell │ process │ spacer
    │ ⋯` with the `│` (U+2502) separators at `text-fg-3`. Consume A2's existing header
    segment values (dot state, cwd basename, shell, foreground process) via the props A2's
    `PaneComponent` already surfaces — render them with the A3-UI-SPEC focused/unfocused
    color tiers (focused: cwd/process `text-fg-0`, shell/index/⋯ `text-fg-1`; unfocused:
    primary `text-fg-2`, index/⋯ `text-fg-3`). ADD the two permitted segments only: the
    numeric `index` (props in: the leaf's geometric `index`; 10px metadata role per
    A3-UI-SPEC Typography) and the `⋯` trigger (U+22EF, `aria-label="Pane menu"`,
    `cursor: default` not pointer, `onClick` → parent-supplied `onToggleMenu`). The `●`
    dot gets `aria-label="Shell running"` / `"Shell exited"` per A2's shell-state prop
    (assistive-only — NOT rendered as visible text; visual density unchanged). Header
    background: `bg-bg-2` when `focused` prop true else `bg-bg-1`, NO CSS transition
    (A3-UI-SPEC Anti-Patterns). Implement the overflow policy (hide process → truncate
    cwd with `…` → hide shell → never truncate index/dot). NO `border-radius`, NO
    `outline`/border-ring (GRD-07). Use ONLY A1 Tailwind utilities. Author
    `apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx` (`@solidjs/testing-library`)
    asserting: 22px height, segment order, index digit + tier colors, focused vs
    unfocused bg class, aria-labels present, process hidden when empty, no
    rounded/transition class.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run PaneChrome --reporter=dot 2>&1 | tail -12 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'aria-label="Pane menu"' src/grid/PaneHeader.tsx && grep -Eq 'aria-label="Shell (running|exited)"|Shell running' src/grid/PaneHeader.tsx && grep -Eq '22px|h-\[22px\]' src/grid/PaneHeader.tsx && grep -q 'bg-bg-2' src/grid/PaneHeader.tsx && grep -q 'bg-bg-1' src/grid/PaneHeader.tsx && ! grep -nE 'rounded|transition:|transition |outline|ring' src/grid/PaneHeader.tsx && echo HEADER_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src/grid/PaneHeader.tsx` renders the locked segment order with a 22px container, `aria-label="Pane menu"` on `⋯`, and shell-state aria-label on `●` (source assertions).
    - `pnpm vitest run PaneChrome` exits 0: index digit at the metadata tier; focused header `bg-bg-2`, unfocused `bg-bg-1`; process hidden when empty (GRD-06/07).
    - Only the index segment and `⋯` trigger are additive; all other segments consume A2 values unchanged (behavior assertion — additive-edit rule).
    - No `rounded`/`transition`/`outline`/`ring` token in `PaneHeader.tsx` (grep gate — Variant B + GRD-07 no border ring).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>The 22px Variant B per-pane header with the added index segment and `⋯` trigger exists and is tested green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: DotMenu.tsx (5-item ⋯ popup) + CloseConfirmBanner.tsx + foreground-gated close</name>
  <files>apps/voss-app/src/grid/DotMenu.tsx, apps/voss-app/src/grid/CloseConfirmBanner.tsx, apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md "## `⋯` Menu Contract (GRD-06)" + "## Close Confirm Contract (GRD-02, A2 D-07)" — 128px width, exactly 5 items, copy strings, banner geometry, keyboard (Enter=confirm, Esc=keep), auto-dismiss (governing contract — copy is character-exact)
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### apps/voss-app/src/grid/DotMenu.tsx" + "### CloseConfirmBanner.tsx" + "### A2 Foreground Detection Reuse" (governing contracts)
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-02 (close confirm iff foreground process other than bare shell; idle = no confirm) + GRD-06 (menu items)
    - .planning/phases/A2-voss-app-pty-pane/A2-CONTEXT.md D-07 + Integration Points — foreground detection is A2's, consumed as a black box
    - apps/voss-app/src/grid/operations.ts (A3-02) — forkFocused/splitFocused/closeFocused
  </read_first>
  <behavior>
    - DotMenu renders exactly 5 rows in order: "Fork pane", "Split right", "Split below", a 1px flush separator, "Close pane" (accent-red). No 6th item ever.
    - Menu container is 128px wide, bg-bg-3, 1px border-border, border-radius 0, positioned top:22px right:0.
    - Each item shows its keyboard equivalent right-aligned dim (⌘D / ⌘\ / ⌘⇧\ / ⌘W); item height 22px; hover bg-bg-2 (no accent bg).
    - "Fork pane" → forkFocused; "Split right" → splitFocused("H"); "Split below" → splitFocused("V"). Menu closes on selection, Escape, outside-click, or pane blur.
    - Selecting "Close pane" (or ⌘W via the GridRoot onCloseRequest hook) checks A2 foreground detection: if a foreground process other than the bare interactive shell is running → show CloseConfirmBanner; else call closeFocused immediately (no banner) — GRD-02.
    - CloseConfirmBanner: 22px, bg-bg-3, content `● "<proc>" is running. Close anyway? [spacer] Keep open  Close anyway`; "Close anyway" (accent-red) and Enter → closeFocused; "Keep open" and Escape → dismiss, pane stays, focus stays.
    - Banner auto-dismisses if the foreground process exits while it is showing; it is non-modal (other keys pass through to the PTY); no timeout auto-dismiss.
  </behavior>
  <action>
    Create `apps/voss-app/src/grid/DotMenu.tsx` (Solid) per the A3-UI-SPEC "`⋯` Menu
    Contract" VERBATIM: a 128px absolute popup (`top:22px; right:0`, `bg-bg-3`, `1px
    border-border`, radius 0, the locked box-shadow), EXACTLY the 5 items in order — "Fork
    pane" (`text-fg-0` → `forkFocused`), "Split right" (`text-fg-0` →
    `splitFocused("H")`), "Split below" (`text-fg-0` → `splitFocused("V")`), a flush
    `margin:0` 1px `border-border` separator, "Close pane" (`text-accent-red` → the gated
    close described below). Each item: 22px tall, `padding:0 16px`, font-mono 11px/400,
    hover `bg-bg-2`, keyboard-equivalent shown right-aligned in `text-fg-3` 10px (⌘D, ⌘\,
    ⌘⇧\, ⌘W). NEVER add a 6th item (A3-UI-SPEC "L1 item scope" / Anti-Pattern). Menu
    dismisses on item-select, `Escape`, outside-click, or pane blur. Create
    `apps/voss-app/src/grid/CloseConfirmBanner.tsx` per "Close Confirm Contract" VERBATIM:
    a 22px full-width banner at the top of the pane body flush to the header bottom,
    `bg-bg-3`, `border-bottom 1px border-border`, content `● (accent-red) │ "<process>"
    is running. Close anyway? │ flex spacer │ Keep open │ Close anyway`; copy
    CHARACTER-EXACT from A3-UI-SPEC Copywriting Contract ("Keep open", "Close anyway",
    `"<process>" is running. Close anyway?`). "Close anyway" (`text-accent-red`) and the
    `Enter`/`Return` key call `closeFocused(store)` (A3-02); "Keep open" (`text-fg-0`) and
    `Escape` dismiss the banner (pane stays, focus stays). Banner is non-modal — other
    keys pass through to the PTY; it auto-dismisses if the watched process exits (subscribe
    to A2's foreground signal/`fg_process` channel — consume A2 detection as a BLACK BOX,
    do NOT reimplement; A3-PATTERNS "A2 Foreground Detection Reuse"); NO timeout
    dismiss. Export a `requestCloseGated(store, paneId, isForegroundRunning: () =>
    Promise<boolean> | boolean, showBanner: () => void)` helper encoding the GRD-02 gate:
    if foreground process other than the bare shell running → `showBanner()` else
    `closeFocused(store)` immediately. Wire this as the `onCloseRequest` passed to
    GridRoot/keymap (replacing A3-04's default `closeFocused`) and as the "Close pane"
    menu action. NO `border-radius`, NO transition (Variant B / perf). Extend
    `__tests__/PaneChrome.test.tsx`: 5-item menu order + no 6th; each action calls the
    right operation; gated close shows banner when foreground running and closes directly
    when idle; banner Enter→close, Esc→keep; auto-dismiss on process-exit signal.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run PaneChrome --reporter=dot 2>&1 | tail -15 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'Fork pane' src/grid/DotMenu.tsx && grep -q 'Split right' src/grid/DotMenu.tsx && grep -q 'Split below' src/grid/DotMenu.tsx && grep -q 'Close pane' src/grid/DotMenu.tsx && grep -q 'Keep open' src/grid/CloseConfirmBanner.tsx && grep -q 'Close anyway' src/grid/CloseConfirmBanner.tsx && grep -q 'closeFocused' src/grid/CloseConfirmBanner.tsx && grep -c 'class="' src/grid/DotMenu.tsx >/dev/null && ! grep -nE 'rounded|transition:|transition ' src/grid/DotMenu.tsx src/grid/CloseConfirmBanner.tsx && echo MENU_OK</automated>
  </verify>
  <acceptance_criteria>
    - `DotMenu.tsx` renders exactly the 5 locked items in order with the correct copy and keyboard equivalents; never a 6th (source + behavior assertion — A3-SPEC boundary "More than 5 items forbidden").
    - `CloseConfirmBanner.tsx` renders the character-exact `Keep open` / `Close anyway` / `"<process>" is running. Close anyway?` copy and calls `closeFocused` on confirm (source assertion).
    - `pnpm vitest run PaneChrome` exits 0: gated close shows the banner when a foreground process runs and closes immediately when idle (GRD-02, A2 D-07 black-box reuse); Enter→close, Esc→keep; auto-dismiss on process-exit.
    - A3 does not reimplement foreground detection — it consumes A2's signal/command (behavior assertion — A2 boundary respected).
    - No `rounded`/`transition` token in `DotMenu.tsx`/`CloseConfirmBanner.tsx`; `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>The 5-item `⋯` menu and the foreground-gated close-confirm banner exist with character-exact copy, tested green.</done>
</task>

<task type="auto">
  <name>Task 3: Mount chrome into the A3-04 leaf seam (SplitNode.tsx)</name>
  <files>apps/voss-app/src/grid/SplitNode.tsx, apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx</files>
  <read_first>
    - apps/voss-app/src/grid/SplitNode.tsx (A3-04) — the leaf container + the explicit `{/* A3-05 mount: ... */}` seam comment left by A3-04 Task 2
    - .planning/phases/A3-voss-app-grid-engine/A3-UI-SPEC.md "## Grid Layout Architecture" + "## Pane Header Contract" — header sits at the top of the leaf; PTY canvas fills body below the 22px header
    - apps/voss-app/src/grid/PaneHeader.tsx + DotMenu.tsx + CloseConfirmBanner.tsx (Tasks 1–2)
    - apps/voss-app/src/grid/keymap.ts (A3-04) — the `onCloseRequest` injection point
  </read_first>
  <action>
    Edit ONLY the leaf branch of `apps/voss-app/src/grid/SplitNode.tsx` at the explicit
    A3-04 seam comment: mount `<PaneHeader>` at the top of the leaf container (passing the
    leaf's `index`, `focused = leaf.id === store.focusedId`, the A2-surfaced dot/cwd/shell/
    process values, and an `onToggleMenu` signal), conditionally render `<DotMenu>` when
    that pane's menu is open (wiring its actions to `forkFocused`/`splitFocused` and the
    `requestCloseGated` close helper from Task 2), and conditionally render
    `<CloseConfirmBanner>` flush below the header when a gated close is pending. Pass the
    composed `requestCloseGated`-based handler up so `GridRoot`/`keymap` (`A3-04`) use it
    as `onCloseRequest` instead of the bare `closeFocused` default (this replaces, does
    not duplicate, the A3-04 default — verify no double close-binding). Do NOT alter the
    split-node (non-leaf) branch, the DragHandle wiring, or the focus-treatment shadow
    from A3-04 — this task is purely additive at the seam. Do NOT modify any file under
    `apps/voss-app/src/pane/` (A2 territory — the only A2-touching change, the header
    index + `⋯`, lives in `PaneHeader.tsx`, not in the A2 component). Extend
    `__tests__/PaneChrome.test.tsx` with an integration render of a 2-pane tree asserting:
    each leaf has a 22px PaneHeader with the correct index; opening the `⋯` menu on pane 2
    and choosing "Fork pane" calls `forkFocused`; `⌘W` on a pane reports through the gated
    close path (spy on `requestCloseGated`).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run PaneChrome --reporter=dot 2>&1 | tail -15 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'PaneHeader' src/grid/SplitNode.tsx && grep -q 'DotMenu' src/grid/SplitNode.tsx && grep -q 'CloseConfirmBanner' src/grid/SplitNode.tsx && ! grep -rnE '\.\./pane/PaneComponent' src/grid/PaneHeader.tsx && echo SEAM_OK</automated>
  </verify>
  <acceptance_criteria>
    - `SplitNode.tsx` leaf branch mounts `PaneHeader`, conditionally `DotMenu`, and conditionally `CloseConfirmBanner` at the A3-04 seam (source assertion).
    - `pnpm vitest run PaneChrome` exits 0: a 2-pane render shows correct per-pane indices; `⋯` "Fork pane" calls `forkFocused`; `⌘W` routes through the gated close (behavior assertion).
    - No file under `apps/voss-app/src/pane/` is modified (A2 boundary — file-ownership assertion).
    - The A3-04 split-node/DragHandle/focus-shadow code is unchanged (additive-only at the seam).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>Per-pane chrome is mounted in the leaf seam; the foreground-gated close replaces the A3-04 default; integration tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| A2 foreground-detection signal/command → A3 close gate | A2-owned process-name data crosses into A3's close decision |
| `⋯` menu / banner actions → tree mutations | Local clicks trigger fork/split/close on a PTY-bearing pane |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A3-12 | Spoofing / Tampering | A2 `fg_process` name displayed in the confirm banner | mitigate | The process name is rendered as TEXT only (quoted in the warning copy) — never executed, never used as a path or command. A2 (assumed-present) owns detection and its own sanitization; A3 treats the value as an opaque display string and applies no `eval`/path/command construction to it. |
| T-A3-13 | Repudiation / Tampering | Close gate bypass losing an in-flight foreground process | mitigate | `requestCloseGated` is the SINGLE close entry point for both `⌘W` (via the GridRoot/keymap `onCloseRequest` injection) and the `⋯` "Close pane" item; bare `closeFocused` is reachable only from tests and the confirmed "Close anyway" path. The banner is the explicit user confirmation, satisfying GRD-02. |
| T-A3-14 | Denial of Service | Menu/banner re-render churn under rapid open/close | accept | Instant repaint with no CSS transitions (Variant B / perf budget) keeps re-render cost minimal; the menu is a single 5-item popup. Local single-user interaction; accepted for the desktop model. |
| T-A3-SC | Tampering | npm/cargo installs | accept | This plan adds NO new runtime npm or cargo package — pure Solid components over A3-02/04. `@solidjs/testing-library` (if used) was vetted/added in A3-04. No legitimacy gate required. |
</threat_model>

<verification>
- `pnpm vitest run PaneChrome` green; `pnpm exec tsc --noEmit` exits 0.
- Every pane header is 22px with the locked segment order + correct geometric index + `⋯`.
- `⋯` menu = exactly 5 items, character-exact copy, correct actions; never a 6th.
- Close-confirm shows iff a foreground process (A2 D-07) is running; idle shell closes with no confirm; banner copy character-exact; Enter=close, Esc=keep, auto-dismiss on exit.
- No A2 `src/pane/` file modified; no rounded/transition/border-ring in A3 chrome.
</verification>

<success_criteria>
- GRD-06: 22px Variant B per-pane header reusing A2 segments + added index + 5-item `⋯` menu acting on that pane.
- GRD-02 (close-confirm half): `⌘W`/Close confirms iff a foreground process runs (A2 D-07 black-box reuse); idle shell closes silently.
- GRD-07 (header half): focused header bg-lift to `--bg-2`, unfocused `--bg-1`, instant, no border ring.
</success_criteria>

<output>
Create `.planning/phases/A3-voss-app-grid-engine/A3-05-SUMMARY.md` when done.
</output>
