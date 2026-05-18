---
phase: A2-voss-app-pty-pane
plan: 03
type: execute
wave: 2
depends_on: ["A2-01"]
files_modified:
  - apps/voss-app/src/pane/PaneComponent.tsx
  - apps/voss-app/src/pane/pty-ipc.ts
  - apps/voss-app/src/pane/pane.css
  - apps/voss-app/src/pane/__tests__/pty-ipc.test.ts
autonomous: true
requirements: [PTY-02, PTY-03, PTY-08]
user_setup: []

must_haves:
  truths:
    - "xterm.js Terminal mounts once in onMount with the exact UI-SPEC theme + Canvas renderer loaded AFTER term.open()"
    - "PTY output streams into xterm via per-requestAnimationFrame coalescing (D-02 frontend half)"
    - "Watermark backpressure (HIGH=100KB/LOW=10KB) invokes pty_pause/pty_resume through the write callback"
    - "Keystrokes (term.onData) are sent to the PTY via pty_write"
    - "Container resize is 150ms-debounced → fitAddon.fit() + pty_resize; scrollback survives resize"
    - "10k-line scrollback configured; alt-screen apps render (TERM=xterm-256color)"
    - "Terminal + child reaped on onCleanup (no leaked PTY)"
  artifacts:
    - path: "apps/voss-app/src/pane/PaneComponent.tsx"
      provides: "Solid pane: xterm mount, lifecycle, onData→pty_write, ResizeObserver, header shell"
      min_lines: 60
    - path: "apps/voss-app/src/pane/pty-ipc.ts"
      provides: "Channel wrapper, rAF coalescing, watermark backpressure, spawn/write/resize/kill wrappers"
      contains: "requestAnimationFrame"
    - path: "apps/voss-app/src/pane/pane.css"
      provides: "Variant B pane container + header + scrollbar tokens (transition:none, radius:0)"
      contains: "var(--bg-"
    - path: "apps/voss-app/src/pane/__tests__/pty-ipc.test.ts"
      provides: "Unit tests for coalescing + watermark threshold logic"
      contains: "watermark"
  key_links:
    - from: "apps/voss-app/src/pane/PaneComponent.tsx"
      to: "apps/voss-app/src/pane/pty-ipc.ts"
      via: "import spawnPty/writePty + Channel onmessage → term.write"
      pattern: "from ['\"]\\./pty-ipc"
    - from: "apps/voss-app/src/pane/pty-ipc.ts"
      to: "@tauri-apps/api/core"
      via: "invoke + Channel"
      pattern: "@tauri-apps/api"
    - from: "apps/voss-app/src/pane/PaneComponent.tsx"
      to: "@xterm/addon-canvas"
      via: "loadAddon(new CanvasAddon()) after term.open()"
      pattern: "CanvasAddon"
---

<objective>
Implement the Solid frontend pane: an xterm.js Terminal (v5.5.0 + Canvas) mounted to the
Variant B chrome, wired bidirectionally to the A2-02 Rust PTY backend over a Tauri
Channel, with the D-02 flood-contract frontend mechanisms (per-rAF coalescing AND
watermark backpressure — both required).

Purpose: This is the rendering + transport half of the pane. Satisfies PTY-02 (frontend
render + bidirectional stream), PTY-03 scrollback capacity (10k lines; ⌘F/⌘⇧K UI is
A2-04), and PTY-08 (alt-screen apps render via TERM=xterm-256color). The D-02 contract
is only met when this plan's rAF+watermark pair runs on top of A2-02's pause/resume.

Output: A live terminal pane that paints `$SHELL`, echoes input, and survives a flood
without freezing — making the D-02 frontend logic testable for A2-05.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/A2-voss-app-pty-pane/A2-CONTEXT.md
@.planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md
@.planning/phases/A2-voss-app-pty-pane/A2-PATTERNS.md
@.planning/phases/A2-voss-app-pty-pane/A2-UI-SPEC.md
@.planning/sketches/themes/default.css

<interfaces>
<!-- xterm Terminal options: copy VERBATIM from A2-UI-SPEC.md §3 lines 229-263. -->
<!-- Do NOT hardcode hex in TSX elsewhere — use var(--token) (A2-PATTERNS §Token Convention). -->

Rust PtyEvent the Channel receives (from A2-02, serde tag="type", snake_case):
  { type: "data", bytes: number[] }
  { type: "exit", code: number }
  { type: "fg_process", name: string }

Rust commands callable via invoke (A2-02 signatures):
  invoke('spawn_pty', { onData: Channel, rows, cols, cwd? }) -> string (session UUID)
  invoke('pty_write',  { sessionId, data: number[] }) -> void
  invoke('pty_resize', { sessionId, rows, cols }) -> void
  invoke('pty_pause',  { sessionId }) -> void
  invoke('pty_resume', { sessionId }) -> void
  invoke('pty_kill',   { sessionId }) -> void

D-02 frontend contract (A2-RESEARCH Patterns 1+2 — BOTH required, complementary):
  rAF coalescing: pendingData[].push(chunk); 1 requestAnimationFrame → term.write(merged)
  watermark: HIGH=100_000 LOW=10_000; term.write(chunk, cb) decrements; >HIGH→pty_pause,
             <LOW→pty_resume

Solid lifecycle (A2-RESEARCH Pattern 3, A2-PATTERNS PaneComponent section):
  onMount: new Terminal(...) -> loadAddon(fit/search/webLinks) -> term.open(ref)
           -> loadAddon(new CanvasAddon())  // MUST be after open() — Pitfall 2
           -> fitAddon.fit() ; onCleanup: term.dispose() + invoke('pty_kill')
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: pty-ipc.ts — Channel transport, rAF coalescing, watermark backpressure</name>
  <files>apps/voss-app/src/pane/pty-ipc.ts, apps/voss-app/src/pane/__tests__/pty-ipc.test.ts</files>
  <read_first>
    - .planning/phases/A2-voss-app-pty-pane/A2-PATTERNS.md "### apps/voss-app/src/pane/pty-ipc.ts" (lines 436-486) — the three concrete patterns to assemble
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "## Pattern 1" frontend coalescing (lines 319-338) + "## Pattern 2" watermark (lines 342-369)
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "### D-02 Flood Performance Assertion" (lines 861-873) — the contract this code must satisfy
  </read_first>
  <action>
    Create `pty-ipc.ts` exporting a `PtyTransport` factory/class that owns the D-02
    frontend mechanisms. Construct a `Channel` (from `@tauri-apps/api/core`). The
    Channel `onmessage` switches on `event.type`:
    - `data`: convert `bytes` (number[]) to `Uint8Array`, push to a `pendingData`
      array; if no rAF scheduled, schedule one `requestAnimationFrame` that merges all
      pending chunks into one buffer, calls the injected `write(merged, cb)`, then
      clears `pendingData` and the rAF flag (Pattern 1 coalescing).
    - watermark: maintain a `watermark` byte counter. On each merged write, add merged
      length; pass a completion callback that subtracts the length and, when
      `watermark < LOW (10_000)`, `invoke('pty_resume', {sessionId})`. After scheduling
      a write, if `watermark > HIGH (100_000)`, `invoke('pty_pause', {sessionId})`.
      HIGH/LOW are module constants exactly 100_000 / 10_000 (D-02 lock).
    - `exit`: invoke a registered `onExit(code)` callback.
    - `fg_process`: invoke a registered `onFgProcess(name)` callback.
    Export `spawnPty(opts)` (invoke `spawn_pty`, store sessionId), `writePty(bytes)`
    (invoke `pty_write` with `Array.from(bytes)`), `resizePty(rows,cols)`, `killPty()`.
    Keep the Terminal write function injected (decoupled from xterm for unit testing).

    Create `__tests__/pty-ipc.test.ts` (Vitest): mock `@tauri-apps/api/core` invoke +
    Channel and a fake `write(chunk, cb)`; assert (a) N `data` events within one frame
    produce exactly ONE merged write (coalescing), (b) pushing >100_000 bytes without
    invoking the write callback triggers `pty_pause`, (c) draining below 10_000 via the
    callback triggers `pty_resume`. Use a controllable rAF stub.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run pty-ipc --reporter=dot 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `pnpm vitest run pty-ipc` exits 0 with the three named assertions green.
    - `pty-ipc.ts` contains the literal constants `100_000` and `10_000` (or `100000`
      / `10000`) AND a `requestAnimationFrame` call AND `invoke('pty_pause'` and
      `invoke('pty_resume'` calls.
    - Coalescing test proves N data events in one frame ⇒ exactly 1 `write` call.
    - No watch-mode flags; test file uses no `.skip`.
  </acceptance_criteria>
  <done>Transport layer assembles rAF coalescing + watermark backpressure with unit-proven thresholds, decoupled from xterm for testability.</done>
</task>

<task type="auto">
  <name>Task 2: PaneComponent.tsx — xterm mount, Variant B chrome, bidirectional wiring, resize</name>
  <files>apps/voss-app/src/pane/PaneComponent.tsx, apps/voss-app/src/pane/pane.css</files>
  <read_first>
    - .planning/phases/A2-voss-app-pty-pane/A2-UI-SPEC.md §1 Pane Container (lines 157-178), §2 Pane Header (lines 181-219), §3 Terminal Body incl. verbatim Terminal options (lines 222-291), §6 Focus (lines 396-415), §11 Motion (lines 533-549)
    - .planning/phases/A2-voss-app-pty-pane/A2-PATTERNS.md "### apps/voss-app/src/pane/PaneComponent.tsx" (lines 348-432) — Solid lifecycle + Terminal init + ResizeObserver excerpts
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md Pitfall 2 (Canvas after open, lines 624-628), Pitfall 5 (DPR/Retina, lines 642-646), "## Pattern 6" resize (lines 525-545)
    - .planning/sketches/themes/default.css (the canonical token values to import/reference)
  </read_first>
  <action>
    Create `pane.css` defining the Variant B chrome from UI-SPEC §1/§2/§3/§6/§11 using
    `var(--token)` references only (NO hardcoded hex — A2-PATTERNS §Token Convention):
    pane container (unfocused `--bg-1` + 1px `--border`; focused `--bg-2` +
    `box-shadow: inset 0 0 0 2px var(--focus-glow)`, border unchanged), 22px header
    (`--bg-3`, 8px h-padding, Inter 12px), the webkit scrollbar block from UI-SPEC §3
    (lines 270-275), and an explicit `transition: none` on container + header
    (UI-SPEC §11). `border-radius: 0` everywhere. Ensure the theme token file is
    imported globally (import the `themes/default.css` token set into the app — if A1
    already wired tokens, reference them; otherwise add the import and note it in the
    SUMMARY as an A1-gap fill).

    Create `PaneComponent.tsx` (Solid). In `onMount`: construct `new Terminal({...})`
    with the options copied VERBATIM from UI-SPEC §3 lines 229-263 (scrollback 10_000,
    the full 16-color theme, `cursorBlink:true`, `macOptionIsMeta:true`,
    `rightClickSelectsWord:false`, `allowProposedApi:false`). `loadAddon` FitAddon,
    SearchAddon, WebLinksAddon; `term.open(containerRef)`; THEN
    `term.loadAddon(new CanvasAddon())` (Pitfall 2 — strictly after open);
    `fitAddon.fit()`. Build the `PtyTransport` from A2-03 Task 1 with `write` bound to
    `term.write`. Call `spawnPty({rows:term.rows, cols:term.cols, cwd})`. Wire
    `term.onData(d => writePty(new TextEncoder().encode(d)))` for keystrokes. Render the
    22px header DOM per UI-SPEC §2 element order (status dot `●`, index `1`, `·`
    separators, cwd basename truncated at 24 chars + `…`, `$SHELL` basename, process
    slot placeholder, flex spacer, `⋯` stub button) — the live process slot + status-dot
    lifecycle wiring is A2-04; this plan renders the static structure with the loading
    `--fg-3` dot. ResizeObserver with a 150ms debounce → `fitAddon.fit()` +
    `resizePty(term.rows, term.cols)` (Pattern 6). Add a `matchMedia` DPR-change
    listener that re-calls `fitAddon.fit()` (Pitfall 5). Pane container click sets
    focused state (single pane = always focused in A2; implement the bg-lift + inset
    shadow toggle so A3 inherits it). `onCleanup`: `term.dispose()` + `killPty()`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm exec tsc --noEmit -p . 2>&1 | tail -10 && grep -q 'CanvasAddon' src/pane/PaneComponent.tsx && grep -q 'scrollback' src/pane/PaneComponent.tsx && grep -Eq 'var[(]--bg-' src/pane/pane.css && grep -Eq 'transition: *none' src/pane/pane.css && echo PANE_OK</automated>
  </verify>
  <acceptance_criteria>
    - `pnpm exec tsc --noEmit` exits 0 (PaneComponent type-checks against A2-01 deps).
    - `PaneComponent.tsx` loads `CanvasAddon` AFTER `term.open(` (grep: `term.open(`
      appears before `new CanvasAddon(` in file order — verify by reading the file).
    - `PaneComponent.tsx` sets `scrollback` to 10_000 and imports from `./pty-ipc`.
    - `pane.css` uses `var(--bg-*)` tokens (no raw hex), sets `transition: none` on
      container + header, and `border-radius: 0`.
    - `term.onData` is wired to `writePty`; `onCleanup` calls `killPty()`.
  </acceptance_criteria>
  <done>Live xterm pane renders Variant B chrome, streams bidirectionally via the A2-02 backend, debounced-resizes, and cleans up on unmount.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PTY output bytes → xterm.js renderer | shell-controlled bytes incl. VT/OSC sequences enter the webview |
| webview → Tauri command | keystroke + resize payloads cross from JS to native (validated in A2-02) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A2-06 | Tampering | Malicious VT/OSC/CSI escape sequences in PTY output | mitigate | All PTY bytes flow through `term.write` — xterm.js sanitizes VT internally; OSC strings are never `eval`'d as JS (A2-RESEARCH §Security Domain). `allowProposedApi:false` set per UI-SPEC |
| T-A2-08 | Denial of Service | Unbounded frontend write queue under flood (UI freeze) | mitigate | rAF coalescing caps write frequency to 1/frame AND watermark backpressure (HIGH=100KB/LOW=10KB) bounds queue by invoking pty_pause; BOTH required (D-02 contract) |
| T-A2-04 | Denial of Service | pty_write flood from frontend keystroke loop | transfer | Payload validation + 1MB cap enforced on the Rust side (A2-02 T-A2-04); frontend sends only real `onData` keystrokes |
</threat_model>

<verification>
- `pnpm vitest run pty-ipc` green: coalescing + pause + resume threshold assertions.
- `pnpm exec tsc --noEmit` exits 0.
- CanvasAddon loaded strictly after `term.open()`; scrollback = 10_000.
- `pane.css` uses only `var(--token)`, `transition: none`, `border-radius: 0`.
- onData→pty_write wired; onCleanup→killPty.
</verification>

<success_criteria>
- PTY-02 (frontend half): xterm renders PTY output, keystrokes stream back.
- PTY-03 (capacity): 10k-line scrollback configured (search/clear UI in A2-04).
- PTY-08: alt-screen apps render via TERM=xterm-256color + native xterm alt-screen.
- D-02 frontend half (rAF + watermark) implemented and unit-proven.
</success_criteria>

<output>
Create `.planning/phases/A2-voss-app-pty-pane/A2-03-SUMMARY.md` when done
</output>
