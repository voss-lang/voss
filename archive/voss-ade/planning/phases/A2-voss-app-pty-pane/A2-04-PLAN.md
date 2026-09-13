---
phase: A2-voss-app-pty-pane
plan: 04
type: execute
wave: 3
depends_on: ["A2-02", "A2-03"]
files_modified:
  - apps/voss-app/src/pane/PaneComponent.tsx
  - apps/voss-app/src/pane/PasteGuard.tsx
  - apps/voss-app/src/pane/FindBar.tsx
  - apps/voss-app/src/pane/ExitBanner.tsx
  - apps/voss-app/src/pane/pane.css
  - apps/voss-app/src/pane/__tests__/PasteGuard.test.tsx
  - apps/voss-app/e2e/pty.spec.ts
autonomous: true
requirements: [PTY-03, PTY-04, PTY-05, PTY-06, PTY-07]
user_setup: []

must_haves:
  truths:
    - "Multi-line paste (≥1 newline) shows the inline non-modal PasteGuard; single-line pastes pass through"
    - "PasteGuard: Enter sends, Esc discards, ⌘⇧V bypasses entirely (literal paste, no banner)"
    - "⌘C with a selection copies; ⌘C with no selection writes \\x03 to the PTY (SIGINT); configurable"
    - "⌘F opens FindBar (SearchAddon next/prev with spec decorations); ⌘⇧K clears scrollback"
    - "OSC 8 links + detected file paths open via Tauri on ⌘+click; only allowed URL schemes"
    - "Header process slot is populated from OSC 0/2 title, falling back to the Rust pgid poll"
    - "Shell exit shows the [exited N] ExitBanner with correct color tier; Restart respawns same $SHELL+cwd"
  artifacts:
    - path: "apps/voss-app/src/pane/PasteGuard.tsx"
      provides: "Inline non-modal multi-line paste banner (D-04/D-05, UI-SPEC §5)"
      contains: "Discard"
    - path: "apps/voss-app/src/pane/FindBar.tsx"
      provides: "⌘F scrollback search overlay (UI-SPEC §8) wired to SearchAddon"
      contains: "findNext"
    - path: "apps/voss-app/src/pane/ExitBanner.tsx"
      provides: "[exited N] banner + Restart (UI-SPEC §4, PTY-07)"
      contains: "exited"
    - path: "apps/voss-app/src/pane/PaneComponent.tsx"
      provides: "⌘C/paste/keymap interception + OSC8 linkHandler + fg-process wiring + banner orchestration"
      contains: "customKeyEventHandler"
  key_links:
    - from: "apps/voss-app/src/pane/PaneComponent.tsx"
      to: "apps/voss-app/src/pane/PasteGuard.tsx"
      via: "render banner on multi-line paste signal"
      pattern: "PasteGuard"
    - from: "apps/voss-app/src/pane/PaneComponent.tsx"
      to: "writePty(\\x03)"
      via: "⌘C no-selection → SIGINT byte"
      pattern: "x03|\\\\u0003"
    - from: "apps/voss-app/src/pane/ExitBanner.tsx"
      to: "spawnPty (restart)"
      via: "onRestart → kill+respawn same $SHELL+cwd"
      pattern: "onRestart|Restart"
---

<objective>
Implement every pane interaction layer on top of the live terminal: the multi-line
paste-guard (D-04/D-05), the ⌘C selection-or-SIGINT semantics (D-06), the ⌘F find bar +
⌘⇧K clear (PTY-03), OSC 8 + file-path link activation (PTY-05), the OSC-0/2 +
pgid-fallback process header (PTY-06/D-07), and the shell-exit banner with Restart
(PTY-07).

Purpose: A2-02/03 deliver a streaming terminal; this plan delivers the human-facing
behaviors that make it the Variant B pane. It turns the A2-01 red `PasteGuard.test.tsx`
green and implements the Playwright specs scaffolded in A2-01.

Output: Fully interactive pane — paste safety, copy/interrupt, search, links, accurate
header, exit/restart — matching the locked UI-SPEC contract.

## Deferred Ideas (tracked debt)

- **xterm v6 / WebGL renderer migration** — A2 is frozen on `@xterm/xterm@5.5.0` +
  `@xterm/addon-canvas@0.7.0` per D-01a (the canvas addon was removed in xterm v6).
  When v6/WebGL is adopted, the CanvasAddon load in `PaneComponent.tsx` and the exact
  pins in `package.json` change. This is acknowledged tracked debt from D-01a; revisit
  at A3 when N panes render concurrently (D-01 explicitly defers the renderer
  reconsideration to A3). NOT in A2 scope — do not implement here.
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
@.planning/phases/A2-voss-app-pty-pane/A2-VALIDATION.md
@.planning/phases/A2-voss-app-pty-pane/A2-03-SUMMARY.md
@.planning/phases/A2-voss-app-pty-pane/A2-02-SUMMARY.md

<interfaces>
<!-- Component contracts copied from A2-PATTERNS.md (exact prop shapes) + UI-SPEC §4/§5/§8. -->

PasteGuardProps (A2-PATTERNS lines 507-513; UI-SPEC §5 lines 341-393):
  { pendingText: string; onSend: () => void; onDiscard: () => void }
  Layout: 56px, absolute bottom:0 (bottom:28px if ExitBanner visible), bg --bg-3,
  border-top 1px --accent-magenta, radius 0, transition none.
  Row1: ⏵(--accent-magenta) + first-line preview(--fg-1, truncate …) + (N lines)(--fg-3 11px)
  Row2: "Send" hint "⏎" + "Discard" hint "Esc" + right "⌘⇧V skips this"(--fg-3 11px)
  Copy is EXACT: button label is "Discard" (NOT "Cancel" — UI-checker lock).

ExitBannerProps (A2-PATTERNS lines 566-571; UI-SPEC §4 lines 295-337):
  { exitCode: number; onRestart: () => void }
  28px, absolute bottom:0, bg --bg-3, border-top 1px --border, radius 0, transition none.
  Dot: --accent-green (0) | --accent-amber (1–127) | --accent-red (>127/signal).
  Copy EXACT: "[exited N]" (brackets literal). Restart btn: --bg-2 bg, --accent-blue
  text, 1px --border, min-w 64px h 22px, radius 0.

FindBar (UI-SPEC §8 lines 437-467): 280px×32px, top:22px right:0, bg --bg-3,
  border-bottom+left 1px --border-bright, placeholder "Find…"(U+2026). SearchAddon
  decorations: current rgba(90,124,255,0.35) / other rgba(90,124,255,0.15).

⌘C / paste / keymap (A2-RESEARCH Pattern 7 lines 549-571, Pitfall 9 lines 666-670):
  customKeyEventHandler intercepts ⌘C: selection exists → copy + clear selection +
  return false; no selection → writePty(Uint8Array [0x03]) (D-06; configurable flag).
  paste DOM listener (capture phase) on container: e.preventDefault(); if
  text.includes("\n") && !bypassFlag → show PasteGuard else send. ⌘⇧V sets one-shot
  bypassFlag. Tauri: invoke('open_url',{url}) / invoke('open_path',{path}); validate
  scheme ∈ {http,https,mailto,file} before opening (T-A2-09).

Process header (UI-SPEC §2 lines 210-214; D-07): primary term.onTitleChange(title)
  → header slot; fallback: if no OSC title within 2s, poll invoke('get_fg_process',
  {sessionId}) every 500ms (A2-02 backend) → header slot. Status dot lifecycle
  UI-SPEC §7 lines 427-431.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: PasteGuard + ExitBanner + FindBar components (UI-SPEC verbatim)</name>
  <files>apps/voss-app/src/pane/PasteGuard.tsx, apps/voss-app/src/pane/ExitBanner.tsx, apps/voss-app/src/pane/FindBar.tsx, apps/voss-app/src/pane/pane.css, apps/voss-app/src/pane/__tests__/PasteGuard.test.tsx</files>
  <read_first>
    - .planning/phases/A2-voss-app-pty-pane/A2-UI-SPEC.md §4 Shell-Exit Banner (lines 295-337), §5 Paste-Guard Banner (lines 341-393), §8 Find Bar (lines 437-467), §9 Copywriting Contract (lines 471-492), §11 Motion (lines 533-549)
    - .planning/phases/A2-voss-app-pty-pane/A2-PATTERNS.md PasteGuard (490-513), FindBar (517-546), ExitBanner (550-571), §No Transition (lines 621-628)
    - apps/voss-app/src/pane/__tests__/PasteGuard.test.tsx (the A2-01 red tests this turns green)
  </read_first>
  <behavior>
    - PasteGuard renders the ⏵ glyph, the first clipboard line truncated with `…`, and
      a `(N lines)` badge equal to the newline count + 1.
    - PasteGuard "Send" button calls `onSend`; "Discard" button calls `onDiscard`;
      button label text is exactly `Send` and `Discard` (never `Cancel`).
    - PasteGuard root has `transition: none` and `border-radius: 0`.
    - ExitBanner shows exactly `[exited 0]`; status dot class maps 0→green,
      1–127→amber, >127→red; Restart button calls `onRestart`.
    - FindBar input placeholder is exactly `Find…` (single U+2026); ↑/↓/✕ controls
      invoke prev/next/close callbacks.
  </behavior>
  <action>
    Implement the three Solid components with the EXACT prop shapes in `<interfaces>`
    and the EXACT visual contract from UI-SPEC §4/§5/§8. All colors via `var(--token)`
    (no raw hex). Add their CSS to `pane.css` (extend, do not rewrite A2-03's rules):
    each banner explicitly `transition: none; border-radius: 0`. Copy strings are
    load-bearing — `Send`, `Discard`, `Esc`, `⏎`, `⌘⇧V skips this`, `[exited N]`,
    `Restart`, `Find…` must match UI-SPEC §9 character-for-character.

    Rewrite `__tests__/PasteGuard.test.tsx` (was red in A2-01) into real green tests:
    render `PasteGuard` with a multi-line `pendingText`; assert the preview shows the
    first line truncated, the `(N lines)` badge is correct, the `Discard` (not
    `Cancel`) label is present, clicking `Send`/`Discard` fires the respective
    callbacks. Use `@testing-library/dom` + solid-js test rendering.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run PasteGuard --reporter=dot 2>&1 | tail -10 && grep -q 'Discard' src/pane/PasteGuard.tsx && ! grep -q 'Cancel' src/pane/PasteGuard.tsx && grep -q 'exited' src/pane/ExitBanner.tsx && echo COMPONENTS_OK</automated>
  </verify>
  <acceptance_criteria>
    - `pnpm vitest run PasteGuard` exits 0 — the A2-01 red tests are now green.
    - `PasteGuard.tsx` contains `Discard` and does NOT contain `Cancel`.
    - `ExitBanner.tsx` renders the literal substring `exited` in `[exited N]` form and
      maps the three exit-code color tiers.
    - `FindBar.tsx` placeholder is exactly `Find…` (one U+2026 char).
    - All three components set `transition: none` and `border-radius: 0` (via pane.css).
  </acceptance_criteria>
  <done>Three spec-exact overlay components exist; PasteGuard unit tests green; copy matches UI-SPEC §9 verbatim.</done>
</task>

<task type="auto">
  <name>Task 2: Wire interactions into PaneComponent (paste-guard, ⌘C/SIGINT, find/clear, OSC8, fg-header, exit/restart)</name>
  <files>apps/voss-app/src/pane/PaneComponent.tsx, apps/voss-app/e2e/pty.spec.ts</files>
  <read_first>
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "## Pattern 7" multi-line paste (549-571), "## Pattern 8" OSC8/file-path (574-597), "## Pattern 5" foreground (489-521), Pitfall 9 ⌘C ordering (666-670)
    - .planning/phases/A2-voss-app-pty-pane/A2-UI-SPEC.md §2 process-slot population (lines 210-219), §3 copy affordance + link handling (lines 279-291), §7 status-dot lifecycle (lines 419-433), §8 ⌘⇧K clear (line 467)
    - apps/voss-app/src/pane/PaneComponent.tsx (the A2-03 base this extends — read its onMount lifecycle)
    - apps/voss-app/e2e/pty.spec.ts (the A2-01 red Playwright specs to implement)
  </read_first>
  <action>
    Extend `PaneComponent.tsx` (do NOT rewrite A2-03's mount logic — add to it):

    1. Paste-guard: add a capture-phase `paste` listener on the xterm container —
       `e.preventDefault()`; read `clipboardData.getData('text')`; if it contains `\n`
       and `bypassFlag` is false, set a `pendingPaste` signal and render `<PasteGuard
       pendingText onSend onDiscard>`; else `writePty(encode(text))`. `onSend` writes
       the pending text then clears the signal; `onDiscard` clears only. Banner is
       non-modal: other keys still reach the terminal.
    2. Keymap via `customKeyEventHandler`: ⌘⇧V → set one-shot `bypassFlag=true`, allow
       paste through (no banner). ⌘C → if `term.hasSelection()` copy selection to
       clipboard, clear selection, return false; else `writePty(new Uint8Array([0x03]))`
       (D-06 SIGINT-via-ETX) — gate behind a `copyMode` setting var defaulting to
       `'smart'` (configurable hook per D-06; A8 surfaces the UI). ⌘F → open FindBar;
       ⌘⇧K → `term.clear()`.
    3. FindBar wiring: render `<FindBar>` on ⌘F; route input → `searchAddon.findNext/
       findPrevious(query, { decorations: {...UI-SPEC §8 colors...} })`; Esc/✕ closes,
       focus returns to terminal.
    4. OSC8 + file paths: set `term.options.linkHandler = { activate: (e,uri) => { if
       (e.metaKey) { validate scheme ∈ {http,https,mailto,file}; invoke('open_url',
       {url:uri}); } }, allowNonHttpProtocols: true }`. Register a custom
       `registerLinkProvider` using the file-path regex from A2-RESEARCH Pattern 8;
       `⌘+click` → `invoke('open_path',{path})`. Reject any other scheme silently.
    5. Process header (D-07): `term.onTitleChange(t => setProcSlot(t))`; start a 500ms
       interval that, only if no OSC title received in the last 2s, calls
       `invoke('get_fg_process',{sessionId})` and sets the slot from the result; clear
       interval on cleanup. Drive the status-dot color per UI-SPEC §7 (loading
       `--fg-3` → running `--accent-green` → exited `--accent-red`).
    6. Exit/restart: on Channel `exit` event set an `exitCode` signal → render
       `<ExitBanner exitCode onRestart>`; pane stays open (never auto-close). `onRestart`
       calls `killPty()` then `spawnPty()` again with the SAME `$SHELL` + `cwd`, clears
       `exitCode`, keeps existing scrollback (do not dispose the Terminal).

    Implement the A2-01 Playwright specs in `e2e/pty.spec.ts` (replace the red bodies):
    `pty-scrollback` (fill 10k lines, ⌘F, assert match on line ~9999),
    `pty-clear` (⌘⇧K → buffer empty), `pty-copy` (select → ⌘C → clipboard),
    `pty-sigint` (run `sleep 999`, ⌘C with no selection, assert `^C` echoed),
    `pty-osc8` (emit OSC 8 escape, ⌘+click → mocked open_url invoked),
    `pty-title` (`printf '\033]0;vim\007'` → header slot shows `vim`),
    `pty-exit-restart` (`exit 0` → `[exited 0]` banner → Restart → fresh prompt).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && pnpm playwright test pty-scrollback pty-clear pty-copy pty-sigint pty-osc8 pty-title pty-exit-restart 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `pnpm exec tsc --noEmit` exits 0.
    - All seven named Playwright specs PASS (`pty-scrollback pty-clear pty-copy
      pty-sigint pty-osc8 pty-title pty-exit-restart`).
    - `PaneComponent.tsx` contains a `customKeyEventHandler`, a capture-phase `paste`
      listener, a `writePty` call with byte `0x03` (or ``), a `linkHandler` with
      a scheme allowlist check, an `onTitleChange` handler, and a `get_fg_process`
      polling interval guarded by a "no OSC within 2s" condition.
    - `pty-sigint` proves no-selection ⌘C interrupts `sleep 999` (`^C` appears).
    - `pty-exit-restart` proves the banner shows `[exited 0]` and Restart respawns the
      shell with scrollback preserved.
  </acceptance_criteria>
  <done>The pane is fully interactive: paste-guard, ⌘C/SIGINT, find/clear, OSC8+file links, accurate header, exit+restart — all Playwright-verified.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PTY output (shell-controlled) → OSC 8 link → Tauri shell open | a hyperlink/URI from terminal output can request an OS open action |
| clipboard → PTY | pasted content (possibly from a malicious source) is written to the shell |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A2-09 | Tampering / Elevation of Privilege | OSC 8 link → `shell.open` with arbitrary URI scheme | mitigate | `linkHandler.activate` and the file-path provider validate the scheme against an allowlist `{http, https, mailto, file}` BEFORE invoking `open_url`/`open_path`; any other scheme is silently rejected (A2-RESEARCH §Known Threat Patterns — webview iframe injection via OSC 8). HIGH-severity arbitrary-scheme open is blocked here |
| T-A2-10 | Tampering | Multi-line clipboard paste injecting commands into the shell unnoticed | mitigate | D-04 PasteGuard forces an explicit Send/Discard decision on any paste containing `\n`; single-line passes through; ⌘⇧V bypass is an explicit user-intent action |
| T-A2-06 | Tampering | OSC/CSI escape sequences in PTY output | accept | xterm.js sanitizes VT internally; OSC title strings set only the header slot text (never eval'd) — same disposition as A2-03 |
| T-A2-11 | Information Disclosure | ⌘C copying selection to OS clipboard | accept | Standard terminal behavior; user-initiated; no sensitive data is auto-copied (selection is explicit) |
</threat_model>

<verification>
- `pnpm vitest run PasteGuard` green (A2-01 red tests resolved).
- Seven Playwright specs pass (scrollback/clear/copy/sigint/osc8/title/exit-restart).
- `pnpm exec tsc --noEmit` exits 0.
- OSC 8 scheme allowlist present; `Discard` (not `Cancel`) label; `[exited N]` copy exact.
- ⌘C no-selection writes 0x03; fg-header uses OSC primary + 500ms pgid fallback.
</verification>

<success_criteria>
- PTY-03: ⌘F search + ⌘⇧K clear over the 10k buffer work (E2E).
- PTY-04: multi-line paste-guard, ⌘⇧V bypass, ⌘C selection-copy / no-selection-SIGINT.
- PTY-05: OSC 8 + file-path links open via Tauri with scheme allowlist.
- PTY-06: header process slot accurate via OSC 0/2 + pgid fallback.
- PTY-07: [exited N] banner + Restart respawns same $SHELL+cwd, scrollback preserved.
</success_criteria>

<output>
Create `.planning/phases/A2-voss-app-pty-pane/A2-04-SUMMARY.md` when done
</output>
