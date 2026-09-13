---
phase: A2-voss-app-pty-pane
plan: 05
type: execute
wave: 4
depends_on: ["A2-04"]
files_modified:
  - apps/voss-app/scripts/test-flood-perf.ts
  - apps/voss-app/e2e/flood-perf.spec.ts
  - apps/voss-app/src/pane/PaneComponent.tsx
autonomous: false
requirements: [PTY-02, PTY-08]
user_setup: []

must_haves:
  truths:
    - "Under a `yes` flood the rAF p95 delta stays < 33ms (automated, not a manual checkbox)"
    - "Under `cat /dev/urandom | strings` the pane does not freeze and keystrokes echo < 200ms"
    - "The flood-perf assertion fails the build if either p95 < 33ms OR echo < 200ms is violated"
    - "vim / htop / tmux / less alt-screen apps render correctly and exit cleanly (PTY-08 manual)"
  artifacts:
    - path: "apps/voss-app/scripts/test-flood-perf.ts"
      provides: "D-02 flood perf harness — real assertions (replaces A2-01 red scaffold)"
      contains: "33"
    - path: "apps/voss-app/e2e/flood-perf.spec.ts"
      provides: "Playwright driver: starts flood, measures rAF p95 + echo latency"
      contains: "requestAnimationFrame"
  key_links:
    - from: "apps/voss-app/scripts/test-flood-perf.ts"
      to: "apps/voss-app/e2e/flood-perf.spec.ts"
      via: "script invokes the Playwright perf driver"
      pattern: "playwright|flood-perf"
    - from: "apps/voss-app/e2e/flood-perf.spec.ts"
      to: "PaneComponent rAF + watermark"
      via: "drives a live pane, measures frame deltas under yes/cat"
      pattern: "yes|/dev/urandom"
---

<objective>
Make the D-02 flood-performance contract a real, automated, build-failing acceptance
gate (not a manual checkbox), and run the PTY-08 alt-screen manual verification matrix.

Purpose: D-02 is a HARD contract per CONTEXT and the phase-specific constraints — "UI
must never freeze under `yes`/`cat`" must be proven by measurement. This plan finalizes
`scripts/test-flood-perf.ts` (red since A2-01) into an assertion that fails the build
when rAF p95 ≥ 33ms or keystroke echo ≥ 200ms under flood, exercising the combined
A2-02 backpressure + A2-03 rAF/watermark path. It also closes PTY-08 (alt-screen apps),
which A2-VALIDATION.md designates manual.

Output: A green, build-gating D-02 perf assertion + a signed-off PTY-08 alt-screen
checklist. This is the final phase gate before `/gsd:verify-work`.
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
@.planning/phases/A2-voss-app-pty-pane/A2-VALIDATION.md
@.planning/phases/A2-voss-app-pty-pane/A2-03-SUMMARY.md
@.planning/phases/A2-voss-app-pty-pane/A2-04-SUMMARY.md

<interfaces>
<!-- D-02 contract — exact thresholds (A2-RESEARCH lines 861-873, A2-VALIDATION lines 63-73). -->

Metric: while `yes` OR `cat /dev/urandom | strings` floods the PTY:
  - measured requestAnimationFrame delta p95 < 33ms  (≤ 2× the 60fps 16.67ms budget)
  - keystroke injected via pty_write during flood echoes back within 200ms

Required implementation (both, complementary — one alone FAILS under cat /dev/urandom):
  - A2-03 per-rAF coalescing (1 term.write per frame)
  - A2-03 watermark backpressure HIGH=100_000 / LOW=10_000 → A2-02 pty_pause/pty_resume

VALIDATION command strings this plan must satisfy:
  pnpm tsx scripts/test-flood-perf.ts          (yes flood)
  pnpm tsx scripts/test-flood-perf.ts --cat     (cat /dev/urandom flood)

PTY-08 manual matrix (A2-VALIDATION §Manual-Only): vim, htop, tmux, less —
  alt-screen renders, TTY signals work, clean exit. TERM=xterm-256color (A2-02).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: D-02 flood-perf assertion — real, build-failing</name>
  <files>apps/voss-app/scripts/test-flood-perf.ts, apps/voss-app/e2e/flood-perf.spec.ts, apps/voss-app/src/pane/PaneComponent.tsx</files>
  <read_first>
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "### D-02 Flood Performance Assertion" (lines 861-873) — exact metric + procedure
    - .planning/phases/A2-voss-app-pty-pane/A2-VALIDATION.md "## D-02 Flood Performance Assertion" (lines 63-73) — procedure + the two command strings
    - apps/voss-app/scripts/test-flood-perf.ts (the A2-01 red scaffold to finalize)
    - apps/voss-app/src/pane/pty-ipc.ts + PaneComponent.tsx (the rAF/watermark path under test — read to confirm a frame-delta hook can be observed)
  </read_first>
  <action>
    Add a minimal, test-only instrumentation hook to `PaneComponent.tsx`: when
    `import.meta.env.MODE === 'test'` (or a `data-perf` query flag), expose a
    `window.__vossPerf` object that records (a) each `requestAnimationFrame` delta into
    a ring buffer and (b) a timestamp map for injected probe keystrokes so echo latency
    is measurable. This hook is inert in production builds (guarded by the env check) —
    do not alter the normal render path.

    Implement `e2e/flood-perf.spec.ts` (Playwright, Tauri target): launch the app, wait
    for the shell prompt, then:
    - Run `yes\n` (default) or `cat /dev/urandom | strings\n` (when `--cat`/PERF_CAT
      env set) in the PTY via `pty_write` to start an infinite flood.
    - Sample `window.__vossPerf` rAF deltas for ≥ 3 seconds; compute p95.
    - Mid-flood, inject a unique probe string via `pty_write`; record the time until it
      appears in the xterm buffer (echo latency).
    - Stop the flood (write `\x03`). Return `{ p95Ms, echoMs }`.

    Finalize `scripts/test-flood-perf.ts`: parse `--cat` (and pass through as env),
    invoke the Playwright perf spec, read back `{p95Ms, echoMs}`, then assert
    `p95Ms < 33` AND `echoMs < 200`. On violation, print the measured values and
    `process.exit(1)`; on pass print `D-02 PASS p95=<>ms echo=<>ms` and exit 0. Run
    BOTH modes (`yes` and `--cat`) — the `cat /dev/urandom` mode is the one that fails
    if watermark backpressure is missing, so both must pass.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm tsx scripts/test-flood-perf.ts 2>&1 | tail -5 && pnpm tsx scripts/test-flood-perf.ts --cat 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `pnpm tsx scripts/test-flood-perf.ts` exits 0 and prints `D-02 PASS` with a
      measured `p95` < 33 (ms) and `echo` < 200 (ms) under the `yes` flood.
    - `pnpm tsx scripts/test-flood-perf.ts --cat` exits 0 and prints `D-02 PASS` under
      the `cat /dev/urandom | strings` flood.
    - The script `process.exit(1)`s (build fails) if either threshold is violated —
      verified by reading the assertion (`p95Ms < 33` and `echoMs < 200` literals
      present, no `|| true` masking, no `.skip`).
    - The `window.__vossPerf` hook is guarded by a test-mode env check (grep confirms
      the guard) so production render is unaffected.
  </acceptance_criteria>
  <done>D-02 is an automated build-failing gate proven under both `yes` and `cat /dev/urandom`; the A2-01 red scaffold is now a real assertion.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: PTY-08 alt-screen manual verification matrix</name>
  <read_first>
    - .planning/phases/A2-voss-app-pty-pane/A2-VALIDATION.md "## Manual-Only Verifications" (lines 89-95)
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md Pitfall 8 (alt-screen scrollback contamination — accepted cosmetic defect, lines 660-664)
    - .planning/phases/A2-voss-app-pty-pane/A2-UI-SPEC.md §3 alt-screen note (line 291)
  </read_first>
  <what-built>
    A2-02/03/04 deliver a streaming pane with TERM=xterm-256color and native xterm
    alt-screen support. PTY-08 (alt-screen apps render correctly) is designated
    manual-only by A2-VALIDATION.md — alt-screen + TUI fidelity is not reliably
    assertable headless. The D-02 perf gate (Task 1) is already automated and green.
  </what-built>
  <how-to-verify>
    Launch the app (`pnpm tauri dev` from `apps/voss-app`). In the pane, run each and
    confirm:
    1. `vim test.txt` — enters alt-screen, cursor + colors correct, type + `:q!`
       exits cleanly back to the shell prompt.
    2. `htop` — TUI renders with colors/layout, responds to input, `q` exits cleanly.
    3. `tmux` then (inside) `tmux` status bar renders; detach with `Ctrl-b d`; clean.
    4. `less /etc/hosts` (or any file) — pager renders, arrow scroll works, `q` exits.
    Known accepted cosmetic defect (NOT a failure): exiting an alt-screen app may leave
    duplicate lines in normal scrollback (xterm.js #802, Pitfall 8) — record but do not
    block on it.
  </how-to-verify>
  <acceptance_criteria>
    - User confirms all four apps render in alt-screen and exit cleanly, OR reports a
      specific rendering/signal defect (a gap closure plan would follow).
    - The xterm.js #802 scrollback-duplication cosmetic issue, if observed, is recorded
      as accepted (not a blocker).
  </acceptance_criteria>
  <resume-signal>Type "approved" (all four render + exit clean) or describe the defect</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| flood PTY output → frontend render path | sustained adversarial-volume byte stream tests the DoS-resistance boundary |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A2-08 | Denial of Service | UI freeze under sustained PTY flood (D-02) | mitigate | This plan converts the D-02 mitigation (A2-03 rAF coalescing + A2-02/03 watermark backpressure) into a measured, build-failing assertion under both `yes` and `cat /dev/urandom` — the DoS mitigation is now continuously verified, not assumed |
| T-A2-12 | Tampering | Test-only perf hook (`window.__vossPerf`) exposed in production | mitigate | The hook is guarded by a test-mode env check (`import.meta.env.MODE === 'test'`/perf flag); verify asserts the guard exists so no debug surface ships in the production bundle |
</threat_model>

<verification>
- `pnpm tsx scripts/test-flood-perf.ts` AND `--cat` both exit 0 with `D-02 PASS`.
- Assertion literals `p95Ms < 33` / `echoMs < 200` present, no masking, no skip.
- `window.__vossPerf` guarded by test-mode env check (production unaffected).
- PTY-08 manual matrix (vim/htop/tmux/less) signed off by the user.
</verification>

<success_criteria>
- D-02 flood contract is an automated build-failing gate, green under yes + cat.
- PTY-02 (perf half): UI stays responsive + input echoes < 200ms under flood.
- PTY-08: alt-screen apps render + exit cleanly (manual sign-off).
- Phase A2 ready for `/gsd:verify-work`.
</success_criteria>

<output>
Create `.planning/phases/A2-voss-app-pty-pane/A2-05-SUMMARY.md` when done
</output>
