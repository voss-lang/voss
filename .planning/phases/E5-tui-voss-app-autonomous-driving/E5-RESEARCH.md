# Phase E5: TUI + voss-app Autonomous Driving - Research

**Researched:** 2026-06-10
**Domain:** Autonomous driving for Textual TUI journeys and voss-app desktop e2e contracts
**Confidence:** HIGH for TUI Pilot and existing app contract mapping; MEDIUM for final Linux tauri-driver workflow details until run on CI.

---

## Summary

E5 should be planned as an internal proof phase, not a product UI redesign. The phase proves that the interactive surfaces can be driven end-to-end:

- Textual TUI: in-process `VossTUIApp().run_test()` journeys using `pilot.press`, `InputBar.action_submit`, `TextualRenderer`, modal interactions, and live-marked provider-backed runs.
- voss-app: manual-dispatch Linux GitHub Actions workflow that builds the Tauri app, runs `tauri-driver` with WebKitWebDriver, and un-skips a small stable subset of existing Playwright contracts.

The safest split is four execution plans:

1. TUI hermetic journey harness and stub twins.
2. TUI live-marked journeys using existing credential/auth conventions.
3. voss-app e2e un-skip scaffolding and the first 3 stable contracts.
4. Linux `tauri-driver` workflow plus artifact/human-checkpoint closeout.

`E5-SPEC.md` does not exist yet, so EVUI requirement IDs are not minted. Until that is corrected, downstream plans must trace to `E5-CONTEXT.md` decisions D-01..D-09 and should either create/consume `E5-SPEC.md` before execution or explicitly record the context-decision mapping in plan frontmatter.

---

## User Constraints

### Locked Decisions

- **D-01:** TUI journeys use Textual Pilot in-process (`app.run_test()` plus `pilot.press/click` and state/snapshot assertions). No PTY/pexpect layer in E5.
- **D-02:** Live-model TUI journeys are `@pytest.mark.live` tests. They run on demand, are credential-gated, and each has a hermetic stub twin in the normal suite.
- **D-03:** Minimum TUI journeys: boot -> prompt -> streamed turn -> final rendered -> quit; edit flow with diff-approval modal approve/reject variants; slash command flow such as `/cost` or `/models`.
- **D-04:** voss-app route is a manual Linux CI `tauri-driver` job using WebKitWebDriver. It is not scheduled and not a PR gate.
- **D-05:** Keep the existing 11 `apps/voss-app/e2e/*.spec.ts` contracts and un-skip incrementally. E5 target is at least 3 green contracts; perf-heavy contracts are deferred.
- **D-06:** voss-native panes in CI use `VOSS_SERVE_FAKE_TURN=1`. No live subscription credentials in desktop CI.
- **D-07:** Phase closeout requires live TUI proof output, CI run link, and human checkpoint review.
- **D-08:** Manual desktop CI does not violate the E-track no-CI posture because it is not scheduled, not blocking, and runs no live models.
- **D-09:** TUI pytest journeys reuse existing `@pytest.mark.live` and credential-gated skip conventions.

### Deferred

- PTY/pexpect terminal driving for TUI.
- Remaining 8 Playwright contracts, especially flood/grid/10k scrollback perf.
- Live-model desktop driving.
- Scheduled or PR-gated desktop e2e workflow.

---

## Architecture Findings

### TUI Surface

Core files:

- `voss/harness/tui/app.py` defines `VossTUIApp`, `register_turn_task`, `_turn_dispatch`, modal actions, slash dispatch, and app-owned live state.
- `voss/harness/tui/renderer.py` maps agent events into `TurnView`, `StatusLine`, `DiffModal`, `BudgetExhaustedModal`, and related widgets.
- `voss/harness/cli.py` wires Textual mode inside `_run_repl`; when `make_renderer()` returns `TextualRenderer`, it sets `renderer.app._turn_dispatch` and runs `renderer.app.run_async()`.
- `tests/harness/tui/test_full_flow_pilot.py` already proves basic user/plan/final rendering through `TextualRenderer`.
- `tests/harness/tui/test_permission_modal.py`, `test_diff_modal.py`, `test_slash_palette_interaction.py`, `test_turn_view_streaming.py`, and `test_input_bar_textarea.py` are the closest local Pilot patterns.

Best implementation approach:

- Add a focused TUI journey file, likely `tests/harness/tui/test_e5_journeys.py`, rather than spreading E5 coverage across existing component tests.
- Build a reusable journey fixture that constructs `VossTUIApp(history=..., slash_registry=...)`, mounts via `app.run_test()`, and injects either a fake `_turn_dispatch` or the real `_dispatch_tui_turn` path depending on test tier.
- Stub twins should exercise widget behavior and renderer side effects without live auth.
- Live journeys should be explicitly marked `@pytest.mark.live` and skipped unless provider credentials or Codex auth are available.

Important TUI pitfall:

- `_run_repl()` owns the real `_dispatch_tui_turn` closure. Pure `VossTUIApp().run_test()` does not automatically install the real harness dispatch. If E5 wants a true live turn through `run_turn`, it needs either a small helper that exposes the Textual REPL wiring for tests, or a subprocess/live test that starts `voss chat` in Textual mode. The context locks "no PTY/pexpect", so the better path is a test helper that builds the same app/renderer/tool/gate/provider wiring as `_run_repl()` without starting a second terminal process.

### Live Auth Surface

Existing patterns:

- `tests/eval/test_live_signals.py` uses `@pytest.mark.live`, `_has_live_creds()`, and `pytest.skip(...)` when no `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` exists.
- `voss/harness/auth.py` can resolve Codex OAuth from `~/.codex/auth.json`, and `voss/harness/cli.py` accepts `--auth=codex`.
- `voss/harness/providers.py` has Codex OAuth handling and documented backend quirks around model defaults.

Recommendation:

- Use a slightly broader `_has_tui_live_creds()` helper for E5 that accepts `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or usable Codex credentials via `auth_mod.load_codex()`.
- Keep live test count low: one boot/prompt/stream/final journey, one diff approval live journey, and one slash-command live journey. The slash-command live journey may not need a provider call if it is purely local; if so, keep it hermetic and reserve live budget for real model turns.

### voss-app Surface

Core files:

- `apps/voss-app/playwright.config.ts` is minimal and currently only points at `e2e`.
- `apps/voss-app/e2e/command-palette.spec.ts`, `project-open.spec.ts`, and `themes.spec.ts` are the lightest candidate contracts named in E5 context.
- `apps/voss-app/e2e/pane-drag-rearrange.spec.ts` already runs against Vite with a mocked Tauri IPC layer and does not need `tauri-driver`; it is useful as a browser-contract pattern but does not satisfy the live Tauri driver requirement by itself.
- `apps/voss-app/src/org/live/__tests__/acSpawn.ts` and `liveSpine.ac.test.ts` already prove the `VOSS_SERVE_FAKE_TURN=1` server seam and process reaping in a gated Vitest AC suite.
- `apps/voss-app/src-tauri/src/lib.rs` and `crates/voss-app-core/src/sidecar.rs` contain the live sidecar lifecycle used by V15.

Best implementation approach:

- Add a dedicated Playwright project/config path for live Tauri e2e if needed, rather than making every existing e2e spec assume an app URL.
- Preserve existing contract names and comments. Convert selected `test.skip(...)` blocks to real tests behind `TAURI_E2E=1` or a Playwright project that only runs in the manual Linux workflow.
- Start with contracts that can use existing JS/Tauri seams:
  - `themes.spec.ts`: can assert DOM state and CSS variables once app is loaded.
  - `command-palette.spec.ts`: can assert palette opening/search/dispatch using keyboard only.
  - `project-open.spec.ts`: useful but blocked by native folder dialog unless the test build mocks `@tauri-apps/plugin-dialog` at the JS boundary.
- If project-open needs too much dialog mocking, replace it with `workspaces.spec.ts` for the third E5 contract. The E5 context says command-palette/project-open/themes are recommended, not mandatory.

### CI Surface

Existing workflow patterns:

- `.github/workflows/ci.yml` and `.github/workflows/rust.yml` use tag-pinned actions and `permissions: contents: read`.
- Linux desktop deps already appear in `.github/workflows/rust.yml`: `libwebkit2gtk-4.1-dev`, `libxdo-dev`, `libayatana-appindicator3-dev`, `librsvg2-dev`, and related build packages.

Recommended workflow:

- Add `.github/workflows/voss-app-e2e.yml` with only `workflow_dispatch`.
- Use `ubuntu-latest`, `permissions: contents: read`, `actions/checkout`, setup Node, setup Python, Rust toolchain/cache if needed, install Linux desktop deps, install app deps, install Playwright browser deps, install/run `tauri-driver`, then run a targeted e2e command from `apps/voss-app/`.
- Set `VOSS_SERVE_FAKE_TURN=1`, `VOSS_HERMETIC=1`, `LITELLM_LOCAL_MODEL_COST_MAP=true`, `TAURI_E2E=1`, and no provider secrets.
- Upload Playwright traces/screenshots and, if available, the Tauri app logs as artifacts.

Open workflow detail to validate during execution:

- Exact `tauri-driver` install path/version for Tauri v2. The plan should include an early CI smoke task that runs `tauri-driver --version` and fails fast before app build/test time is spent.

---

## Package Legitimacy Audit

No new project runtime dependencies are required for planning.

Already present:

- Python: `textual>=0.58,<9.0`, `pytest-asyncio`, `pytest-textual-snapshot`, `pytest` live marker.
- Desktop app: `@playwright/test@1.60.0`, `@tauri-apps/cli@2.11.2`, `@tauri-apps/api@2.11.0`, Tauri Rust crates.
- Server seam: FastAPI/SSE dependencies under the Python `server` extra and current dev install.

Possible CI-only tool:

- `tauri-driver` should be installed in the GitHub Actions job as a tool, not added as a repository dependency, unless execution proves a repo-local pin is necessary.

---

## Validation Architecture

### Automated tiers

| Tier | Purpose | Command |
|---|---|---|
| TUI hermetic | Stub journey twins and component regressions | `python3 -m pytest tests/harness/tui/test_e5_journeys.py tests/harness/tui/test_full_flow_pilot.py tests/harness/tui/test_diff_modal.py tests/harness/tui/test_slash_palette_interaction.py -q -m "not live"` |
| TUI live | On-demand live proof through Textual journey path | `python3 -m pytest tests/harness/tui/test_e5_live_journeys.py -q -m live` |
| voss-app unit/build | App contract sanity before e2e | `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build` |
| voss-app targeted e2e | Local/browser contract subset if Vite-mocked | `pnpm --dir apps/voss-app exec playwright test e2e/command-palette.spec.ts e2e/themes.spec.ts --reporter=list` |
| Linux Tauri e2e | Manual CI proof under `tauri-driver` | `gh workflow run voss-app-e2e.yml` then inspect linked run artifacts |

### Sampling

- After TUI task commits: run the TUI hermetic command.
- After voss-app e2e task commits: run `pnpm --dir apps/voss-app test` plus the targeted Playwright subset when locally possible.
- After workflow task commits: run YAML/source checks locally and let the manual workflow be the phase closeout proof.
- Before phase verification: run TUI hermetic, app build/tests, TUI live proof locally, and manual workflow dispatch on Linux.

### Manual-only

- Human checkpoint must review the live TUI pytest output and GitHub Actions run link.
- Tauri/WebKit behavior itself is manual-dispatch CI evidence; macOS local dev cannot run the target driver.

---

## Threat Model

| Threat | Risk | Mitigation |
|---|---|---|
| Live tests silently run in normal suite | Unexpected provider spend or flaky CI | `@pytest.mark.live`, strict skip helper, normal-suite stub twins |
| Desktop CI accidentally uses live credentials | Secrets exposure or spend | `VOSS_SERVE_FAKE_TURN=1`, no provider secrets in workflow, assert fake-turn env in tests |
| Tauri app e2e leaves orphan sidecar/server processes | CI flake and local resource leaks | Reuse AC spawn/kill patterns; Playwright teardown kills child processes; workflow timeout |
| Un-skipped specs become empty green shells | False-positive E5 closeout | Each un-skipped contract must assert visible DOM state or protocol/event outcome, not `page.evaluate(() => void 0)` |
| Native folder picker blocks project-open | Hanging test | Mock dialog at JS boundary or choose a different third contract for E5 |
| CI job drifts into required PR gate | Violates E-track posture | `workflow_dispatch` only, no `pull_request`, no `push`, document non-blocking intent |

---

## Planning Recommendation

Plan E5 only after the UI-SPEC gate is handled. Because E5 changes tests and CI more than product UI, the practical choices are:

1. Run `$gsd-ui-phase E5` and make the UI contract explicitly say "no visual redesign; preserve existing TUI/voss-app appearance while adding autonomous driving hooks and selectors."
2. Re-run `$gsd-plan-phase E5 --skip-ui` if the operator decides a UI design contract is unnecessary for a proof/testing phase.

If planning proceeds, use four serial-ish plans:

- **E5-01:** TUI hermetic journey harness and stub twins.
- **E5-02:** TUI live journey layer and proof command.
- **E5-03:** voss-app e2e contract un-skip subset and test-build seams.
- **E5-04:** Linux manual `tauri-driver` workflow, artifacts, and human checkpoint.

## RESEARCH COMPLETE
