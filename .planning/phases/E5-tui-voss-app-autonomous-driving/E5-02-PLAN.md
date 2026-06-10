---
phase: E5-tui-voss-app-autonomous-driving
plan: 02
type: execute
wave: 2
depends_on: [E5-01]
files_modified:
  - tests/harness/tui/live_driver.py
  - tests/harness/tui/test_e5_live_journeys.py
autonomous: true
requirements: [D-02, D-03, D-07, D-09]
user_setup:
  - "For non-skipped live proof, configure one of: Codex auth at ~/.codex/auth.json, ANTHROPIC_API_KEY, or OPENAI_API_KEY."
must_haves:
  truths:
    - "D-02: Live TUI tests are marked @pytest.mark.live and skip when no live credentials are available"
    - "D-01: Live TUI tests use VossTUIApp.run_test() and the TextualRenderer path, not PTY/pexpect"
    - "D-03: At least three live-marked TUI Pilot journeys exist: prompt/final, slash command, and diff approval"
    - "D-07: At least one live prompt journey reaches a final assistant response through run_turn"
    - "D-09: The live test module follows the existing live marker convention and adds no VOSS_DEV gate"
    - "D-02: Hermetic E5-01 tests still run in the normal non-live suite"
  artifacts:
    - path: "tests/harness/tui/live_driver.py"
      provides: "Test helper that mirrors cli._run_repl Textual dispatch setup without launching a terminal subprocess"
      contains: "install_live_tui_dispatch"
    - path: "tests/harness/tui/test_e5_live_journeys.py"
      provides: "Live-marked TUI Pilot journeys and skip discipline"
      contains: "pytest.mark.live"
  key_links:
    - from: "tests/harness/tui/live_driver.py"
      to: "voss/harness/cli.py _run_repl"
      via: "same TextualRenderer, PermissionGate, provider/model, slash registry, and run_turn dispatch ingredients"
      pattern: "_resolve_run_turn"
    - from: "tests/harness/tui/test_e5_live_journeys.py"
      to: "tests/eval/test_live_signals.py"
      via: "same @pytest.mark.live and credential-gated skip posture"
      pattern: "pytest.mark.live"
---

<objective>
Add the live TUI journey layer for E5 D-02, D-03, D-07, and D-09. The implementation must drive the Textual app in process with Pilot while using the real provider-backed `run_turn` path, and must skip cleanly when live credentials are absent.

Purpose: Produce the local live proof artifact required before E5 closeout without contaminating the hermetic test suite or using PTY driving.
Output: a test-only live dispatch helper and `tests/harness/tui/test_e5_live_journeys.py`.
</objective>

<execution_context>
@$HOME/.codex/get-shit-done/workflows/execute-plan.md
@$HOME/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-CONTEXT.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-RESEARCH.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-UI-SPEC.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-VALIDATION.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-PATTERNS.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-01-SUMMARY.md

@voss/harness/cli.py
@voss/harness/auth.py
@voss/harness/providers.py
@voss/harness/agent.py
@voss/harness/tui/app.py
@voss/harness/tui/renderer.py
@tests/eval/test_live_signals.py
@tests/harness/tui/test_e5_journeys.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create live Textual dispatch helper with credential-gated skip</name>
  <files>tests/harness/tui/live_driver.py</files>
  <read_first>
    - voss/harness/cli.py (read `_run_repl` Textual branch lines around renderer setup, PermissionGate, ReplContext, `_dispatch_tui_turn`)
    - voss/harness/cli.py (read `_resolve_auth_or_die`, `_apply_boot_model`, `_provider_label`, `_resolve_run_turn`, `_run_turn_with_teardown`)
    - tests/eval/test_live_signals.py (read `_has_live_creds` and `pytest.skip` behavior)
    - voss/harness/auth.py (read `load_codex`, env/API-key auth resolution)
    - tests/harness/tui/test_e5_journeys.py (read E5-01 helper style before extending)
  </read_first>
  <action>
    Add `tests/harness/tui/live_driver.py` as test-only support. Export `_has_tui_live_creds()` and `install_live_tui_dispatch(app, *, cwd: Path, mode: str = "plan")`.

    `_has_tui_live_creds()` must return true when any of these are available: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `voss.harness.auth.load_codex()` returns credentials. It must not print credential contents.

    `install_live_tui_dispatch` must mirror the Textual branch of `voss/harness/cli.py::_run_repl` without calling `renderer.app.run_async()` and without creating a subprocess. It should construct or reuse `TextualRenderer(app)`, resolve auth with `_resolve_auth_or_die("auto")` after the caller has checked `_has_tui_live_creds()`, apply `_apply_boot_model(provider, user_explicit=None)`, build `tools = make_toolset(cwd, renderer=renderer, net=_get_net_session(), session_id=record.id)`, create `PermissionGate(mode=mode, store=PermissionStore.load(cwd))`, call `_wire_tui_permissions_if_textual(gate, renderer)`, create `EpisodicMemory(capacity=40)` and `session_store.SessionRecord.new(cwd=cwd, model=get_config().default_model)`, create the normal slash registry with `_build_slash_registry()`, and install an async `_dispatch_tui_turn(line: str)` on `app._turn_dispatch`.

    The dispatch body must handle slash commands through `slash_registry.dispatch(ctx, line)` with stdout/stderr capture exactly like `_run_repl`, and normal prompts through `run_turn(..., renderer=renderer, provider=ctx.provider, model=get_config().default_model, history=ctx.history, permissions=gate, session_id=record.id, cognition=bundle, voss_md_text=ctx.voss_md_text, project_index_text=ctx.project_index_text)`. Reuse `_run_turn_with_teardown` and `_resolve_run_turn(cwd)`; do not duplicate provider API calls.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/tui/test_e5_journeys.py -q -m "not live" && python3 -m py_compile tests/harness/tui/live_driver.py</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/tui/live_driver.py` exports `_has_tui_live_creds` and `install_live_tui_dispatch`.
    - `_has_tui_live_creds` checks `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `auth.load_codex()` without printing token values.
    - The helper imports and calls `_resolve_run_turn`, `_run_turn_with_teardown`, `_build_slash_registry`, and `_wire_tui_permissions_if_textual` from `voss.harness.cli`.
    - The helper never imports `pexpect`, `pty`, or `subprocess`.
    - `python3 -m py_compile tests/harness/tui/live_driver.py` exits 0.
  </acceptance_criteria>
  <done>The live helper installs the real Textual dispatch path into a Pilot-mounted app while preserving D-01's in-process constraint.</done>
</task>

<task type="auto">
  <name>Task 2: Add live-marked TUI journeys and proof command</name>
  <files>tests/harness/tui/test_e5_live_journeys.py</files>
  <read_first>
    - tests/harness/tui/live_driver.py
    - tests/harness/tui/test_e5_journeys.py
    - tests/eval/test_live_signals.py
    - voss/harness/tui/app.py
    - voss/harness/tui/widgets/input_bar.py
  </read_first>
  <action>
    Create `tests/harness/tui/test_e5_live_journeys.py`. At module level, use `pytestmark = pytest.mark.live`. Add a local fixture or helper `require_live_creds()` that calls `_has_tui_live_creds()` and `pytest.skip("live provider credentials not configured")` when false, matching `tests/eval/test_live_signals.py`.

    Add `test_e5_live_prompt_stream_final_quit(tmp_path)` that calls `require_live_creds()`, constructs `VossTUIApp()`, enters `async with app.run_test() as pilot`, calls `install_live_tui_dispatch(pilot.app, cwd=tmp_path, mode="plan")`, submits a short prompt through `InputBar.load_text("Reply with exactly: E5 live TUI proof")` and `await input_bar.action_submit()`, waits for the active turn task to clear with a bounded loop around `await pilot.pause()`, then asserts `pilot.app._last_response_text` is non-empty and that the transcript in `#main` contains either `E5` or `live`.

    Add `test_e5_live_slash_cost_is_local(tmp_path)` that installs the same dispatch, submits `/cost` through the InputBar path, and asserts the transcript or status area contains cost/session output without making a second provider call. This covers the slash-command part of D-03 under live configuration while keeping spend bounded.

    Add `test_e5_live_diff_modal_accept_and_reject(tmp_path)` under the same live marker and credential gate. Use the existing `DiffModal`/`Hunk` pattern from E5-01 and `tests/harness/tui/test_diff_modal.py`; drive accept-all (`a`) and reject-all (`q`) variants with Pilot and assert both decision arrays. This third live-marked journey satisfies D-07's three live TUI journey count while keeping the model spend bounded to the prompt/final test.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/tui/test_e5_live_journeys.py -q -m live</automated>
  </verify>
  <acceptance_criteria>
    - Every test in `test_e5_live_journeys.py` is live-marked by module-level `pytestmark = pytest.mark.live` or per-test `@pytest.mark.live`.
    - Running without `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and Codex auth skips with `live provider credentials not configured`.
    - `rg -n "access_token|authorization|api_key|refresh_token" tests/harness/tui/test_e5_live_journeys.py tests/harness/tui/live_driver.py` returns no secret-printing code.
    - `python3 -m pytest tests/harness/tui/test_e5_journeys.py -q -m "not live"` still exits 0.
    - With live credentials configured, `python3 -m pytest tests/harness/tui/test_e5_live_journeys.py -q -m live` runs at least three tests and exits 0, producing output suitable for the E5 human checkpoint.
  </acceptance_criteria>
  <done>Live TUI proof is available on demand, skips safely without credentials, and leaves the normal suite hermetic.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
| --- | --- |
| local credentials -> live tests | Provider credentials or Codex OAuth are read only to run live-marked tests. |
| live provider -> TUI renderer | A live model response flows through `run_turn` into `TextualRenderer` and the mounted Textual app. |
| slash input -> command registry | Slash commands are dispatched through the same registry as the REPL. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
| --- | --- | --- | --- | --- |
| T-E5-04 | Information Disclosure | live auth | mitigate | Skip helper checks credential presence only; tests and helper never print token fields or auth headers. |
| T-E5-05 | Denial of Service | live model spend/flakiness | mitigate | Tests are `@pytest.mark.live`, on-demand, short-prompt, and excluded from normal `-m "not live"` runs. |
| T-E5-06 | Tampering | PTY layer bypasses Pilot contract | mitigate | Helper mounts `VossTUIApp.run_test()` and imports no PTY/pexpect/subprocess tools. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/tui/test_e5_journeys.py -q -m "not live"` exits 0.
- `python3 -m pytest tests/harness/tui/test_e5_live_journeys.py -q -m live` exits 0 when live credentials are configured, or skips with the exact no-credentials reason otherwise.
- `rg -n "pexpect|pty|subprocess" tests/harness/tui/live_driver.py tests/harness/tui/test_e5_live_journeys.py` returns no matches.
- `rg -n "access_token|authorization|api_key|refresh_token" tests/harness/tui/live_driver.py tests/harness/tui/test_e5_live_journeys.py` shows no secret printing.
</verification>

<success_criteria>
- D-02: live TUI journeys use `@pytest.mark.live`, credential-gated skip, and hermetic twins from E5-01.
- D-03: live-marked prompt/final, slash-command, and diff approve/reject coverage exist; hermetic twins remain green.
- D-07: live pytest output is available for the E5 human checkpoint.
- D-09: the existing live pytest marker convention is reused; no `VOSS_DEV` gate is added for TUI journeys.
</success_criteria>

<output>
Create `.planning/phases/E5-tui-voss-app-autonomous-driving/E5-02-SUMMARY.md` when done.
</output>
