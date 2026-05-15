---
phase: M9
plan: 07
status: implementation-complete-awaiting-human-verify
date: 2026-05-15
---

# M9-07 Summary — Final Integration Wave (TUI-09 / TUI-10)

Wave 7. Flips `make_renderer` default path so a TTY user with adequate
capability gets the new `TextualRenderer` automatically, while `--plain`
and non-TTY callers stay byte-identical to the M9-01 baseline. Wires
`install_tui_permissions` (M9-05) at the do_cmd + _run_repl gates.
Lands `--no-unicode` flag + `VOSS_NO_UNICODE=1` env on glyphs.py.
Lands the Windows-console capability branch in capability.py with the
UI-SPEC-locked stderr notice. Adds three audit test files (accent
allow-list, no-unicode fallback, Windows console strategy) and extends
test_plain_parity with an explicit post-flip parity assertion.

Task 2 (human-verify checkpoint for UI-SPEC Acceptance Visual Checks 1,
8, 9) is OUTSTANDING — see "Human Verification Pending" at the bottom.

## Files Created

| Path | Purpose |
|------|---------|
| `tests/harness/tui/test_accent_allowlist_audit.py` | UI-SPEC Acceptance Visual Check 3 — walks `voss/harness/tui/` and asserts `$accent` / `.accent` / `#5FAFFF` appears only in the 6 allow-listed widgets + `styles.tcss`. |
| `tests/harness/tui/test_no_unicode_fallback.py` | UI-SPEC Check 5 — subprocess invocations verify each of the 11 glyphs swaps to its ASCII fallback when `VOSS_NO_UNICODE=1` is set at module import, and stays at the locked codepoint otherwise. Also verifies `--no-unicode` flag sets the env. |
| `tests/harness/tui/test_windows_console_strategy.py` | Capability branch — win32 + missing `WT_SESSION` → `TUIDecision(activate=False, reason="Windows console missing capability")`. `WT_SESSION` set → branch is a no-op. Non-win32 unaffected. `make_renderer` emits the locked stderr notice and returns `PlainRenderer`. |
| `tests/harness/tui/test_cli_integration.py` | Pins the three contracts: (1) make_renderer factory matrix, (2) `install_tui_permissions` is called exactly once for TextualRenderer and not at all for PlainRenderer, (3) `--no-unicode` flag sets the env before make_renderer fires. |

## Files Modified

| Path | Change |
|------|--------|
| `voss/harness/render.py` | `make_renderer` default-path flip. When capability says yes, returns `TextualRenderer(VossTUIApp())`. Windows-console fallback emits the locked `"voss: Windows console missing capability · using --plain mode"` stderr notice and returns PlainRenderer. Force-tui-too-small still exits 2 with the M9-01 min-size copy. Legacy `TtyRenderer` retained as the non-Windows TTY fallback when capability rejects for any other reason (e.g. `textual not installed`). |
| `voss/harness/tui/capability.py` | New win32 branch BEFORE the size/textual_available checks: `sys.platform == "win32"` AND `WT_SESSION` not set → `TUIDecision(activate=False, reason="Windows console missing capability")`. Fires before the size check (Windows reason wins over below-80x24). |
| `voss/harness/tui/glyphs.py` | Added `NO_UNICODE_FALLBACK` 11-entry mapping. Import-time check on `VOSS_NO_UNICODE=1` swaps every locked module-level constant to its ASCII fallback. `__getattr__` allow-list unchanged. |
| `voss/harness/tui/renderer.py` | Hardened `_header` / `_turn_view` / `_status` / `_input` helpers: return `None` instead of raising when the app isn't mounted yet. Every Renderer-protocol method now bails early when the lookup misses. This keeps the agent loop alive in environments where the Textual app hasn't been started — required because the default-path flip means a TextualRenderer is constructed before any pilot/run_async wrap-up. |
| `voss/harness/cli.py` | Added `--no-unicode` Click flag to `do_cmd`, `chat_cmd`, `edit_cmd`, `resume_cmd` (4 flags total). Each calls `_apply_no_unicode_env(no_unicode)` BEFORE `make_renderer` so the glyphs module's import-time env check sees the flag. Added `_wire_tui_permissions_if_textual(gate, renderer)` helper — deferred-imports `install_tui_permissions` + `TextualRenderer`, fires only when the renderer is a `TextualRenderer`. Helper invoked at the two unique gate-construction sites (`do_cmd` + `_run_repl`); `_run_repl` covers `chat_cmd` + `edit_cmd` + `resume_cmd`. |
| `tests/harness/tui/test_plain_parity.py` | Added `test_default_path_after_flip_matches_baseline` — explicit M9-07 sanity gate: `CliRunner.invoke(do_cmd, [...])` with no `--plain` and no `FORCE_TUI` produces stdout byte-identical to the M9-01 baseline. Locks the contract through Wave 7. |

## Acceptance Grep Counts (all met)

| Check | Path | Required | Actual |
|-------|------|---------:|-------:|
| `install_tui_permissions` | `voss/harness/cli.py` | ≥ 2 | 2 |
| `return TextualRenderer` | `voss/harness/render.py` | ≥ 1 | 2 |
| `VOSS_NO_UNICODE` | `voss/harness/tui/glyphs.py` | ≥ 1 | 4 |
| `NO_UNICODE_FALLBACK` | `voss/harness/tui/glyphs.py` | ≥ 1 | 4 |
| `win32` | `voss/harness/tui/capability.py` | ≥ 1 | 1 |
| `Windows console missing capability` | `capability.py` + `render.py` | ≥ 1 | 3 |
| `no-unicode` | `voss/harness/cli.py` | ≥ 4 | 4 |

## Test Outcome

`pytest tests/harness/tui/ tests/harness/test_cli.py tests/harness/test_permissions_modes.py tests/harness/test_session.py tests/harness/test_session_redaction.py tests/harness/test_happy_path_integration.py -x -q` → 260 passed, 0 failed.

Plain-parity, accent allow-list, no-unicode fallback (subprocess + flag),
and Windows console strategy all green under the post-flip default path.
M9-01 baseline byte-parity is intact. M9-02 zero-total contract intact.
M9-04 W3 SPAWN_TOOL_NAME defensive-import contract intact.

## Threat Model Outcomes

- **T-M9-07-01** (Confused-deputy — TUI permissions bridge bypass): mitigated. `install_tui_permissions` only sets `prompt_fn` / `scope_prompt_fn`; `mode_allows` tier check (permissions.py:49) still runs BEFORE the prompt, so `mode=plan` denies `fs_write` regardless of the TUI being attached. Existing `test_permissions_py_signature_unchanged` test (M9-05) guards against new fields slipping into PermissionGate.
- **T-M9-07-02** (Tampering — `VOSS_NO_UNICODE` env smuggled into piped invocation): accepted. The env var only swaps display glyphs; on-disk session data, stdout-piped JSON, and provider payloads are unaffected.
- **T-M9-07-03** (DoS — Windows console hard-block strands user): mitigated. The Windows branch falls through `make_renderer` to a PlainRenderer with the locked stderr notice; voss remains fully usable in `--plain` mode.
- **T-M9-07-04** (Info disclosure — accent allow-list audit greps test paths into stderr): accepted. Only the offending file paths surface, and only when the test fails locally / in CI.

## Human Verification Pending

UI-SPEC Acceptance Visual Checks 2, 3, 4, 5, 6, 7, 10 are covered by
automated tests (`test_glyph_and_color_contract`,
`test_accent_allowlist_audit`, `test_plain_parity`,
`test_no_unicode_fallback`, `test_no_new_runtime_hooks`, modal tests,
`test_reserved_slash_names`).

Checks 1, 8, 9 require human-eye verification on a real terminal:

- **Check 1 — 80×24 minimum honored.** 79×24 exits 2 with locked stderr;
  80×24 mounts all four regions without truncation.
- **Check 8 — Empty states render.** Fresh repo: main pane heading
  `No turns yet`. `/sessions` empty: heading `No sessions in this repo`.
  No-spawn: side panel collapsed.
- **Check 9 — Help overlay reachable.** `?` opens HelpOverlay; `Esc`
  dismisses.

The phase is implementation-complete; awaiting `approved` (or
`gap: …`) on the M9-07 plan Task 2 checkpoint before
`M9-PHASE-SUMMARY.md` is written.
