# Phase E5 Pattern Map: TUI + voss-app Autonomous Driving

## Purpose

E5 has no product UI redesign. The implementation should extend existing test, selector, and CI patterns until the two interactive surfaces can be driven by automation.

## Pattern Matrix

| E5 area | Files to read first | Existing pattern to reuse |
| --- | --- | --- |
| TUI Pilot shell | `voss/harness/tui/app.py`, `tests/harness/tui/test_app_shell.py`, `tests/harness/tui/test_full_flow_pilot.py` | Use `VossTUIApp().run_test()` and mounted IDs `#header`, `#main`, `#status`, `#input`, `#input-textarea`. Install `_turn_dispatch` on the app for prompt submission tests. |
| TUI renderer assertions | `voss/harness/tui/renderer.py`, `tests/harness/tui/test_turn_view_streaming.py`, `tests/harness/tui/test_live_visualization.py` | Use `TextualRenderer(pilot.app)` to call `show_user`, `stream_delta`, `finalize_stream`, `show_final`, and then inspect `TurnView.lines` plus app state such as `_last_response_text`. |
| TUI diff approval | `tests/harness/tui/test_diff_modal.py`, `voss/harness/tui/widgets/diff_modal.py`, `voss/harness/tui/renderer.py` | Reuse `Hunk`, `DiffModal`, `DiffDecision`, and Pilot key presses `a`, `q`, `y`, `n`, `escape`. Tests must prove both approve and reject variants. |
| TUI slash command | `tests/harness/tui/test_slash_palette_interaction.py`, `voss/harness/tui/widgets/slash_palette.py`, `voss/harness/cli.py` `_build_slash_registry` | Press `/`, filter, navigate, press `enter`, and assert the submitted value is normalized into the normal input dispatch path, e.g. `/cost` or `/models`. |
| Live TUI harness | `voss/harness/cli.py` `_run_repl`, `_resolve_auth_or_die`, `_run_turn_with_teardown`, `tests/eval/test_live_signals.py` | Mirror `_run_repl`'s Textual branch in a test helper: same `TextualRenderer`, provider/model, `PermissionGate`, slash registry, `run_turn`, and live-marker skip discipline. Do not use PTY/pexpect. |
| voss-app setup/project path | `apps/voss-app/src/App.tsx`, `src/project/projectStorage.ts`, `src/components/setup/SetupWindow.tsx`, `src/project/__tests__/a5-acceptance.test.tsx` | Preserve copy constants `Open project`, `Start without project`, `Choose a project`. Add non-visual test hooks only where needed. Mock native folder picking behind an explicit Tauri e2e test seam. |
| voss-app command palette | `apps/voss-app/src/command-palette/CommandPalette.tsx`, `src/command-palette/__tests__/CommandPalette.test.tsx`, `e2e/command-palette.spec.ts` | Reuse `data-testid="command-palette"`, `palette-input`, `palette-row`, `palette-empty`, and keyboard paths for quick/full palette modes. |
| voss-app themes | `apps/voss-app/src/themes/themeRuntime.ts`, `src/themes/themeCatalog.ts`, `src/appearance/settings.ts`, `e2e/themes.spec.ts` | Assert CSS variables and `document.documentElement.dataset.highContrast`; do not add new theme tokens. Current catalog tests say 13 bundled themes, so e2e must read the catalog rather than hardcode the older 12-theme comment. |
| Tauri-driver CI | `.github/workflows/rust.yml`, official Tauri WebDriver docs | Use `webkit2gtk-driver`, `xvfb`, `cargo install tauri-driver --locked`, and a WebDriver client. Keep the E5 workflow `workflow_dispatch` only with `permissions: contents: read`. |

## Locked Pitfalls

- Playwright is not the Tauri-driver client. Preserve the existing Playwright files as contract references, but drive the Linux Tauri app through a WebDriver runner unless an implementation task proves a direct Playwright adapter.
- No empty green tests: an un-skipped or ported contract must assert visible DOM state, CSS state, protocol state, or app lifecycle state.
- No provider credentials in desktop CI. Desktop proof uses `VOSS_SERVE_FAKE_TURN=1`.
- Live TUI tests must be `@pytest.mark.live`, skip without credentials, and never run in the normal hermetic suite.
- Do not add visible UI copy for tests. Use stable IDs/data attributes when a selector is missing.

## PATTERN MAPPING COMPLETE
