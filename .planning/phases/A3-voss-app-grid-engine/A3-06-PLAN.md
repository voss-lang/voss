---
phase: A3-voss-app-grid-engine
plan: 06
type: execute
wave: 5
depends_on: [A3-04, A3-05]
files_modified:
  - apps/voss-app/src/App.tsx
  - apps/voss-app/e2e/grid-integration.spec.ts
  - apps/voss-app/e2e/grid-perf.spec.ts
  - crates/voss-app-core/src/grid.rs
  - apps/voss-app/src/grid/__tests__/mirror-parity.test.ts
autonomous: false
requirements: [GRD-01, GRD-02, GRD-03, GRD-04, GRD-05, GRD-06, GRD-07, GRD-08]
must_haves:
  truths:
    - "GridRoot is mounted in the app below the A1 titlebar, replacing the single A2 pane"
    - "A 2×2 grid (3 splits) and a ≥6-pane asymmetric tree each run independent shells and are navigable end-to-end"
    - "After every split/fork/close/resize/focus change the voss-app-core Rust mirror matches the Solid tree"
    - "A3 grid operations create no file under .voss/ or anywhere on disk"
    - "With 9 panes, idle/scrolling panes stay ~60fps and a yes-flood in one pane does not freeze or starve the others"
  artifacts:
    - path: "apps/voss-app/src/App.tsx"
      provides: "GridRoot mounted below the titlebar (A1/A2 → A3 integration)"
      contains: "GridRoot"
    - path: "apps/voss-app/e2e/grid-integration.spec.ts"
      provides: "Playwright e2e: 2×2 + ≥6-pane build/navigate/resize/close + no-disk-IO assertion"
      contains: "2x2"
    - path: "apps/voss-app/e2e/grid-perf.spec.ts"
      provides: "9-pane 60fps idle/scroll + one-pane-flood isolation benchmark (D-01 Canvas bar)"
      contains: "flood"
    - path: "apps/voss-app/src/grid/__tests__/mirror-parity.test.ts"
      provides: "Solid-tree ↔ Rust-mirror structural parity after each op"
      contains: "sync_grid"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/grid/GridRoot.tsx"
      via: "render GridRoot below the A1 titlebar"
      pattern: "GridRoot"
    - from: "apps/voss-app/src/grid/__tests__/mirror-parity.test.ts"
      to: "crates/voss-app-core/src/grid.rs"
      via: "assert Rust mirror equals Solid tree after each op"
      pattern: "sync_grid|get_grid"
---

<objective>
Integrate the grid into the app, prove end-to-end correctness for the 2×2 and ≥6-pane
cases, prove Solid↔Rust mirror parity + zero disk I/O, and verify the D-01 Canvas-renderer
9-pane performance bar (idle ~60fps + one-pane-flood isolation).

Purpose: A3-01..05 build the engine in isolation; this plan wires it into the running app
and validates the A3-SPEC acceptance criteria that only hold for the assembled system —
including the perf bar that A3-CONTEXT D-01 flags as a must-verify (research was skipped,
so the benchmark IS the validation contract for the Canvas-per-pane decision).

Output: `App.tsx` integration, Playwright e2e (`grid-integration`, `grid-perf`), a
mirror-parity unit suite, and a `get_grid` read-back command in `grid.rs` for parity
assertion. Closes GRD-01..08 at the system level.
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
<!-- From A3-01..05 (depends_on A3-04, A3-05; transitively A3-01/02/03). -->
From apps/voss-app/src/grid/GridRoot.tsx (A3-04):
  <GridRoot store={...} onCloseRequest={...} />  // the full interactive grid
From apps/voss-app/src/grid/sync.ts (A3-01):
  syncGridToRust / markStructuralChange / markDragSettled → invoke('sync_grid', {newState})
From crates/voss-app-core/src/grid.rs (A3-01):
  GridState; #[tauri::command] sync_grid(state, new_state) — in-memory mirror, no disk I/O

A1/A2 app shell (assumed-present upstream — A3 mounts INTO it, must not re-plan it):
  apps/voss-app/src/App.tsx is the A1/A2 root: A1 custom titlebar at the top; A2 currently
  renders ONE PaneComponent below it. A3's job at integration: replace that single-pane
  region with <GridRoot/> (the grid's leaves ARE A2 PaneComponents). The A1 titlebar
  region and Tauri command registry (where sync_grid must be registered alongside A2's
  pty_* commands) are A1/A2 surfaces consumed as contracts. If App.tsx's exact structure
  differs at execute time, preserve the A1 titlebar untouched and swap only the pane
  region — read App.tsx before editing.
</interfaces>

@.planning/phases/A3-voss-app-grid-engine/A3-SPEC.md
@.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md
@.planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md
@.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md
@.planning/phases/A2-voss-app-pty-pane/A2-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Mount GridRoot in App.tsx + register sync_grid; add get_grid parity command</name>
  <files>apps/voss-app/src/App.tsx, crates/voss-app-core/src/grid.rs, apps/voss-app/src/grid/__tests__/mirror-parity.test.ts</files>
  <read_first>
    - apps/voss-app/src/App.tsx — the A1/A2 root (read fully before editing; preserve the A1 titlebar, swap only the single-pane region for GridRoot)
    - apps/voss-app/src-tauri/src/lib.rs (or main.rs) — the Tauri command registry where A2's pty_* commands are registered; sync_grid/get_grid must be added to the same invoke_handler
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md GRD-08 + acceptance ("Rust mirror matches Solid tree after every change"; "no file under .voss/")
    - .planning/phases/A3-voss-app-grid-engine/A3-PATTERNS.md "### crates/voss-app-core/src/grid.rs" — A4/A6 forward-compat (keep GridState serde-clean) + "Tauri Command/State Seam"
    - crates/voss-app-core/src/grid.rs (A3-01) — existing GridState + sync_grid
  </read_first>
  <action>
    Edit `apps/voss-app/src/App.tsx`: replace the single A2-pane region (below the A1
    titlebar) with `<GridRoot .../>` from `./grid/GridRoot`, creating the grid store via
    `createGridStore()` (A3-01) seeded with the same default cwd/shell A2 uses for its
    initial pane. Preserve the A1 titlebar and any A1/A2 layout shell exactly — read
    `App.tsx` first and change ONLY the pane region. Register the Rust `sync_grid` command
    in the Tauri `invoke_handler` (the same registry where A2's `pty_*` commands live —
    `src-tauri/src/lib.rs` or `main.rs`) and `.manage(Mutex::new(GridState::default()))`
    the mirror state. Add to `crates/voss-app-core/src/grid.rs` a `#[tauri::command] pub
    fn get_grid(state: tauri::State<'_, Mutex<GridState>>) -> GridState` (clone-returns
    the in-memory mirror — read-back ONLY for parity testing; still NO disk I/O, NO
    `std::fs`) and a `Default` impl for `GridState` (single default `PaneLeaf` root) so the
    managed state initializes; register `get_grid` in the handler too. Keep `GridState`
    serde-clean with no `#[serde(skip)]` (A3-PATTERNS A4/A6 forward-compat). Author
    `apps/voss-app/src/grid/__tests__/mirror-parity.test.ts`: with `invoke` mocked to a
    fake in-memory Rust store, run a scripted sequence (split-H, split-V, fork, focus
    change, keyboard resize, close) and after EACH step assert the fake store's structure
    deep-equals the Solid tree (GRD-08 "matches after every structural change") and that
    no `invoke` carried a filesystem path / `.voss` string (GRD-08 no-disk-IO at the
    payload level).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && (cd apps/voss-app && pnpm vitest run mirror-parity --reporter=dot 2>&1 | tail -12 && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && grep -q 'GridRoot' src/App.tsx) && cargo build -p voss-app-core 2>&1 | tail -5 && grep -q 'pub fn get_grid' crates/voss-app-core/src/grid.rs && grep -q 'sync_grid' apps/voss-app/src-tauri/src/lib.rs && ! grep -nE 'std::fs|File::|fs::write|\.voss' crates/voss-app-core/src/grid.rs && echo INTEGRATION_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src/App.tsx` renders `<GridRoot>` in place of the single A2 pane while leaving the A1 titlebar untouched (source assertion).
    - `sync_grid` AND `get_grid` are registered in the Tauri invoke_handler; `cargo build -p voss-app-core` exits 0 (source + build assertion).
    - `pnpm vitest run mirror-parity` exits 0: after split-H/split-V/fork/focus/resize/close the mirror structurally equals the Solid tree (GRD-08); no payload carries a `.voss`/fs path.
    - `grid.rs` still has zero `std::fs`/`File::`/`fs::write`/`.voss` tokens (GRD-08 no-disk-IO grep gate).
    - `pnpm exec tsc --noEmit` exits 0.
  </acceptance_criteria>
  <done>The grid is mounted in the running app; the Rust mirror is registered and structurally tracks the Solid tree with zero disk I/O; parity tests green.</done>
</task>

<task type="auto">
  <name>Task 2: Playwright e2e — 2×2 + ≥6-pane build/navigate/resize/close + 9-pane perf/flood benchmark</name>
  <files>apps/voss-app/e2e/grid-integration.spec.ts, apps/voss-app/e2e/grid-perf.spec.ts</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md "## Acceptance Criteria" — the 13 pass/fail criteria this e2e must exercise (governing contract)
    - .planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md D-01 (Canvas per-pane; "research-validate the perf bar at the 9-pane ceiling with a benchmark" — research was skipped so THIS benchmark is the validation contract; WebGL is NOT to be adopted, only flagged if Canvas fails the bar) + D-02/D-03/D-04
    - apps/voss-app/e2e/ — existing A2 Playwright specs (pty-*.spec.ts) for the harness/launch convention (read for the app-launch + selector idiom; do NOT modify A2 specs)
    - .planning/phases/A3-voss-app-grid-engine/A3-SPEC.md "## Constraints" — N-pane perf bar (~60fps idle/scroll; one-pane flood must not starve others)
  </read_first>
  <action>
    Create `apps/voss-app/e2e/grid-integration.spec.ts` (Playwright, same launch harness
    as A2's `pty-*.spec.ts`) exercising the A3-SPEC acceptance criteria end-to-end against
    the real app: (1) build a 2×2 grid via 3 `⌘\`/`⌘⇧\` splits, assert 4 pane containers
    each with a live shell prompt and distinct PTY (type `echo $$` per pane → 4 distinct
    PIDs); (2) build a ≥6-pane asymmetric tree, assert it renders and every pane is
    `⌘`-numeric/click/`⌘[`/`⌘]`-navigable and `⌘⌥`arrow directional focus lands on the
    expected neighbor; (3) `⌘D` fork → child cwd == parent cwd, child scrollback empty;
    (4) attempt an under-floor split on a deliberately tiny window → tree unchanged
    (silent no-op, GRD-05); (5) drag a border → only the two adjacent panes resize; `⌘=`
    → visually equal; (6) `⌘W` on a pane running `sleep 100` → confirm banner appears,
    "Close anyway" closes it; `⌘W` on an idle prompt → closes with no banner; (7) close
    the last pane → a fresh default pane appears (never empty, D-04); (8) assert exactly
    one pane has the inset-shadow focus class and there is no border-ring style; (9)
    assert no file is created under the project `.voss/` directory during the whole run
    (GRD-08 — snapshot the dir before/after). Create
    `apps/voss-app/e2e/grid-perf.spec.ts` implementing the D-01 Canvas perf bar: spin a
    9-pane grid; (a) idle/scroll: drive scrollback in all 9 panes and sample
    `requestAnimationFrame` frame intervals — assert sustained ~60fps (median frame
    interval ≤ ~20ms, allowing CI headroom; record the actual number in the test output);
    (b) flood isolation: run `yes` in ONE pane while the other 8 are idle and one is being
    interactively scrolled — assert the scrolled/idle panes keep responding (input echo
    latency stays interactive, frame interval does not collapse) i.e. the flood pane does
    NOT freeze or starve the others (A3-SPEC constraint; A2 D-02/D-03 extended to N
    panes). The perf spec MUST print the measured idle FPS and flood-case latency so the
    Task 3 checkpoint can read real numbers. Tag the perf spec so it can run on the dev
    machine (Canvas/GPU realistic) — note in a comment that headless CI numbers are
    advisory and the human checkpoint (Task 3) is the authoritative D-01 sign-off.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm exec tsc --noEmit -p . 2>&1 | tail -5 && test -f e2e/grid-integration.spec.ts && test -f e2e/grid-perf.spec.ts && grep -Eqi '2x2|2×2' e2e/grid-integration.spec.ts && grep -q 'sleep 100' e2e/grid-integration.spec.ts && grep -qi '\.voss' e2e/grid-integration.spec.ts && grep -qi 'flood\|yes' e2e/grid-perf.spec.ts && grep -Eqi 'fps|frame' e2e/grid-perf.spec.ts && (pnpm playwright test grid-integration grid-perf 2>&1 | tail -20 || echo 'E2E_RAN_SEE_CHECKPOINT') && echo SPECS_PRESENT</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/e2e/grid-integration.spec.ts` exercises all 13 A3-SPEC acceptance criteria including the 2×2 distinct-PID check, under-floor no-op, last-pane respawn, single inset-shadow focus, and the `.voss/` no-write snapshot (source + behavior assertions).
    - `apps/voss-app/e2e/grid-perf.spec.ts` runs a 9-pane idle/scroll FPS sample and a one-pane `yes`-flood isolation case and PRINTS the measured idle FPS + flood latency (D-01 Canvas perf bar — the validation contract since research was skipped).
    - `pnpm exec tsc --noEmit` exits 0; both spec files exist and contain the required scenario tokens (grep gates).
    - Playwright run executes the specs; pass/fail of the perf bar is escalated to the Task 3 human checkpoint (the authoritative D-01 sign-off given headless-CI variance).
  </acceptance_criteria>
  <done>End-to-end correctness specs for all 13 acceptance criteria + the 9-pane Canvas perf/flood benchmark exist and run, printing measured numbers.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Human sign-off — 9-pane Canvas perf bar + grid acceptance (D-01 validation)</name>
  <files>none — verification checkpoint, no files modified</files>
  <what-built>
    A3 is fully assembled: the binary-split grid is mounted in the running app, the
    Rust mirror tracks it with zero disk I/O, e2e specs cover all 13 A3-SPEC acceptance
    criteria, and `grid-perf.spec.ts` benchmarks the 9-pane Canvas-per-pane performance
    bar (idle ~60fps + one-pane-flood isolation). Because research was skipped, this
    checkpoint is the authoritative D-01 sign-off: it confirms Canvas-per-pane meets the
    A3-SPEC perf bar at the 9-pane ceiling (the A3-CONTEXT D-01 "research-validate"
    obligation, converted to a benchmark + human gate). WebGL was deliberately NOT
    adopted (A3-CONTEXT D-01 — Canvas avoids the WebGL context-loss bug class); it is
    only to be flagged here IF Canvas fails the bar.
  </what-built>
  <how-to-verify>
    On the dev machine (real GPU/Canvas — not headless CI):
    1. `cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm tauri dev`
    2. Build a 9-pane grid (`⌘\`/`⌘⇧\` × 8). Confirm every pane shows a 22px Variant B
       header with the correct `⌘`-number index, `●` dot, cwd, shell, `⋯` menu.
    3. Idle/scroll: run a long-output command (e.g. `seq 1 100000`) and scroll several
       panes. Watch for stutter. Run `pnpm playwright test grid-perf` and read the
       PRINTED idle FPS — confirm it is at/near 60fps and subjectively smooth.
    4. Flood isolation: in ONE pane run `yes`. While it floods, type in and scroll a
       DIFFERENT pane. Confirm the other panes stay responsive (input echoes promptly,
       no freeze) and read the printed flood-case latency from the spec output.
    5. Spot-check acceptance: `⌘W` on a pane running `sleep 100` → confirm banner with
       `Keep open` / `Close anyway`; `⌘W` on an idle prompt → closes silently; close the
       last pane → a fresh pane appears; exactly one pane has the inset-shadow focus
       treatment; `⌘=` equalizes; `⌘⌥`arrow directional focus is correct.
    6. Confirm NO `.voss/` directory or file was created by any grid operation
       (`ls -la /Users/benjaminmarks/Projects/Voss/.voss 2>/dev/null` — expect absent or
       unchanged).
    Reply `approved` if the 9-pane Canvas perf bar holds and acceptance spot-checks pass.
    If the perf bar FAILS, describe the symptom (which case, measured numbers) — that is
    the documented trigger for the A3-CONTEXT D-01 WebGL-fallback investigation (a
    follow-up, NOT a silent in-plan switch).
  </how-to-verify>
  <resume-signal>Type "approved", or describe the perf/acceptance failure (incl. measured FPS/latency).</resume-signal>
  <action>Checkpoint task — no autonomous implementation. The executor first runs `pnpm tauri dev` and `pnpm playwright test grid-perf` to produce live numbers, then PAUSES for the human to perform the numbered how-to-verify steps and confirm the 9-pane Canvas perf bar (idle ~60fps + one-pane-flood isolation — the D-01 validation contract since research was skipped) plus the grid acceptance spot-checks. Do not proceed past this blocking gate without an explicit "approved".</action>
  <verify><human-check>Human performs the numbered how-to-verify steps on the dev machine (real GPU/Canvas) and replies "approved", or reports the failure with measured FPS/latency.</human-check></verify>
  <done>Human replied "approved": the 9-pane Canvas-per-pane perf bar holds (idle ~60fps + one-pane-flood isolation) and the grid acceptance spot-checks pass. OR: a failure is documented with measured numbers, triggering the A3-CONTEXT D-01 WebGL-fallback follow-up investigation (a documented follow-up, never a silent in-plan renderer switch).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Solid grid → Tauri command registry (`sync_grid`/`get_grid`) | Tree state crosses the webview→native boundary alongside A2's pty_* commands |
| 9 concurrent PTY processes (one possibly flooding) | Multiple shell processes run simultaneously; one may emit unbounded output |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A3-15 | Denial of Service | 9 concurrent PTYs + a `yes`-flood pane starving the UI | mitigate | The flood-isolation benchmark (`grid-perf.spec.ts`) + the human checkpoint explicitly validate that one flooding pane does not freeze the others — this rides A2's D-02 per-PTY rAF-coalesce/backpressure contract (assumed-present) extended to N panes; failure is caught here, not shipped. The 20×5 floor + 9-pane ceiling bound the concurrent PTY count. |
| T-A3-16 | Information Disclosure | `get_grid` read-back exposing tree state | accept | `get_grid` returns only the in-memory layout structure (pane ids, cwd basenames, shell names, ratios) to the same app's own webview — no secrets, no remote exposure, in-memory only (no disk). It exists for parity testing; A4/A6 own any persistence. Accepted for the local single-user model. |
| T-A3-17 | Tampering | `App.tsx` integration disturbing the A1 titlebar / A2 pane internals | mitigate | The integration task is scoped to swap ONLY the single-pane region for `<GridRoot>`; the executor must read `App.tsx` first and leave the A1 titlebar + A2 `src/pane/` untouched (verified by the e2e specs still exercising the A1 titlebar region and A2 PTY behavior). |
| T-A3-SC | Tampering | npm/cargo installs | accept | This plan adds NO new npm or cargo package. Playwright + the Tauri/serde deps are already present from A1/A2 scaffolding. No legitimacy gate required. |
</threat_model>

<verification>
- `pnpm vitest run mirror-parity` green; `cargo build -p voss-app-core` exits 0; `grid.rs` no-disk-IO grep gate passes.
- `apps/voss-app/src/App.tsx` mounts `<GridRoot>`; `sync_grid` + `get_grid` registered.
- `grid-integration.spec.ts` + `grid-perf.spec.ts` exist, type-check, and run; all 13 A3-SPEC acceptance criteria exercised.
- Human checkpoint confirms the 9-pane Canvas perf bar (idle ~60fps + flood isolation — D-01 validation) and acceptance spot-checks, with measured numbers recorded.
</verification>

<success_criteria>
- GRD-01..07: the assembled grid passes all 13 A3-SPEC acceptance criteria end-to-end.
- GRD-08: the Rust mirror structurally matches the Solid tree after every change with zero disk I/O (verified by parity unit test + the e2e `.voss/` snapshot).
- D-01 (validation): the 9-pane Canvas-per-pane perf bar (idle ~60fps + one-pane-flood isolation) is benchmarked and human-signed-off; WebGL remains un-adopted unless this bar fails (documented follow-up trigger, not an in-plan switch).
</success_criteria>

<output>
Create `.planning/phases/A3-voss-app-grid-engine/A3-06-SUMMARY.md` when done.
</output>
