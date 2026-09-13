# A5-06 Summary

**Date:** 2026-05-20

## Result

A5-06 added the requirement-level closure artifacts:

- `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx`
- `apps/voss-app/e2e/project-open.spec.ts`
- `.planning/phases/A5-voss-app-project-open/A5-VALIDATION.md`

The automated A5 gate passed and printed `A5_FULL_GREEN`. The manual visual checkpoint is still pending human approval.

## Final Test Counts

| Gate | Result |
|---|---|
| `cargo test -p voss-app-core project:: --quiet` | 24 passed |
| `cargo test --workspace --quiet` | passed; one macOS Keychain test intentionally ignored |
| `cargo build -p voss-app --quiet` | passed |
| `pnpm --filter voss-app test` | 20 files / 224 tests passed |
| `pnpm --filter voss-app exec tsc --noEmit -p .` | passed |
| `pnpm --filter voss-app build` | passed |
| `pnpm playwright test project-open` | 7 skipped, spec loaded successfully |

## Validation Snapshot

`A5-VALIDATION.md` now maps:

| Area | Status |
|---|---|
| WS-01 folder picker/open path | green, with `Cmd+O` deferred to A7 |
| WS-02 recents cap/dedupe | green via Rust project tests + JS wrapper acceptance |
| WS-03 lazy `.voss/` on open | green via Rust filesystem test |
| WS-04 project metadata + git branch | green via Rust tests + JS ProjectInfo assertion |
| WS-05 project-less mode | green via App/acceptance tests |
| WS-06 Rust-resolved cwd seam | green for `default_cwd` and `GridRoot projectCwd`; operation-level consumption deferred |
| WS-07 project switch path | green for open-recent project change + pane preservation; palette UI deferred to A7 |
| L2 vocab gate | green for SetupWindow + Titlebar chrome, excluding user-supplied project names |
| E2E intent | green as a skipped macOS-deferred spec; future Linux CI un-skip required |

## Visual Checkpoint

| Checkpoint | Status |
|---|---|
| (a) no-project launch shows SetupWindow and `Voss ADE` | automated DOM coverage green; human visual pending |
| (b) Open project native picker | human visual pending |
| (c) setup disappears, grid mounts, titlebar swaps to basename | automated DOM coverage green; human visual pending |
| (d) opened temp project does not create `.voss/` | Rust filesystem coverage green; human spot-check pending |
| (e) second project preserves pane/scrollback | automated pane identity coverage green; human scrollback visual pending |
| (f) project-less path mounts grid and keeps fallback title | automated DOM coverage green; human visual pending |
| (g) relaunch after project-less shows setup again | design covered by session-only signal; human relaunch pending |
| (h) git repo project exposes `gitBranch` metadata | Rust coverage green; UI does not render branch in A5 |
| (i) SetupWindow visual token discipline | automated DOM/source coverage green; human visual pending |
| (j) no L2 vocab in chrome | automated acceptance gate green |

Screenshot links: none captured in this run. The plan requires a human visual sign-off in the live Tauri app before phase verification can be called fully complete.

## Follow-Ups

| Item | Owner |
|---|---|
| Thread `projectCwd` into `splitFocused` / `forkFocused` pane creation | A6 follow-up |
| Add `Cmd+O` accelerator and palette project commands | A7 |
| Drag-drop folder onto app icon | A11 or later polish |
| Un-skip project-open e2e with a JS dialog mock on Linux CI | A10 / CI |

## Commands Run

```bash
cd apps/voss-app && pnpm vitest run src/project/__tests__/a5-acceptance.test.tsx --reporter=dot
cd apps/voss-app && pnpm playwright test project-open
cargo test -p voss-app-core project:: --quiet
cargo test --workspace --quiet
cargo build -p voss-app --quiet
pnpm --filter voss-app test
pnpm --filter voss-app exec tsc --noEmit -p .
pnpm --filter voss-app build
```

Sentinels printed:

```text
A5_ACCEPTANCE_OK
A5_E2E_SPEC_OK
A5_FULL_GREEN
```
