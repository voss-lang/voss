---
phase: E5-tui-voss-app-autonomous-driving
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/harness/tui/test_e5_journeys.py
autonomous: true
requirements: [D-01, D-03]
user_setup: []
must_haves:
  truths:
    - "D-01: Hermetic TUI Pilot journeys run through VossTUIApp().run_test() without PTY or pexpect"
    - "D-01: Prompt submission uses the real InputBar.Submitted -> VossTUIApp._turn_dispatch path"
    - "D-03: A streamed assistant turn appends visible transcript content and records _last_response_text"
    - "D-03: Diff approval has both accept-all and reject-all Pilot coverage"
    - "D-03: Slash command selection dispatches a normalized command string such as /cost or /models"
  artifacts:
    - path: "tests/harness/tui/test_e5_journeys.py"
      provides: "Hermetic E5 Pilot journeys for prompt/stream/final, diff approval, and slash command flow"
      contains: "test_e5_stub_prompt_stream_final_quit"
  key_links:
    - from: "tests/harness/tui/test_e5_journeys.py"
      to: "voss/harness/tui/app.py VossTUIApp.on_input_bar_submitted"
      via: "input_bar.load_text(...) then await input_bar.action_submit()"
      pattern: "_turn_dispatch"
    - from: "tests/harness/tui/test_e5_journeys.py"
      to: "voss/harness/tui/renderer.py TextualRenderer"
      via: "show_user, stream_delta, finalize_stream"
      pattern: "TextualRenderer"
---

<objective>
Create the hermetic Textual Pilot journey harness required by E5 D-01 and D-03. These tests prove full TUI user journeys in-process, using existing widget IDs and renderer methods, with no live provider credentials and no PTY/pexpect layer.

Purpose: Give E5 a normal-suite proof that the TUI can be driven end-to-end before adding live-model coverage.
Output: `tests/harness/tui/test_e5_journeys.py` with prompt/stream/final, diff approve/reject, and slash-command journeys.
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

@voss/harness/tui/app.py
@voss/harness/tui/renderer.py
@voss/harness/tui/widgets/diff_modal.py
@tests/harness/tui/test_full_flow_pilot.py
@tests/harness/tui/test_diff_modal.py
@tests/harness/tui/test_slash_palette_interaction.py
@tests/harness/tui/test_turn_view_streaming.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add prompt -> streamed turn -> final -> quit hermetic journey</name>
  <files>tests/harness/tui/test_e5_journeys.py</files>
  <read_first>
    - tests/harness/tui/test_full_flow_pilot.py (read in full; copy the run_test/InputBar/TextualRenderer idioms)
    - tests/harness/tui/test_turn_view_streaming.py (read stream_delta/finalize_stream assertions)
    - voss/harness/tui/app.py (read VossTUIApp.on_input_bar_submitted, register_turn_task, action_interrupt, compose)
    - voss/harness/tui/renderer.py (read show_user, stream_delta, finalize_stream, show_final)
    - .planning/phases/E5-tui-voss-app-autonomous-driving/E5-UI-SPEC.md (TUI selectors and copy preservation)
  </read_first>
  <action>
    Create `tests/harness/tui/test_e5_journeys.py`. Add `pytest.mark.asyncio` tests and small local helpers only; do not add shared production code in this plan. Implement `test_e5_stub_prompt_stream_final_quit` so it constructs `VossTUIApp()`, enters `async with app.run_test() as pilot`, installs an async `_turn_dispatch` on `pilot.app`, and submits text through `InputBar.load_text("say hello from E5")` plus `await input_bar.action_submit()`.

    The fake dispatch must create `TextualRenderer(pilot.app)`, call `renderer.show_user(line)`, call `renderer.stream_delta("hel")`, call `renderer.stream_delta("lo from E5")`, then call `renderer.finalize_stream(role="assistant", confidence=0.8, cost_usd=0.0, accumulated_text="hello from E5")`. After `await pilot.pause()`, assert the `TurnView` at `#main` contains both `say hello from E5` and `hello from E5`, assert `pilot.app._last_response_text == "hello from E5"`, assert `pilot.app.active_turn_task is None`, then call `pilot.app.action_interrupt()` and assert the app exits or no active task remains.

    Use selectors from the UI-SPEC: `#input`, `#input-textarea`, `#main`, `#status`, and `#header`. Do not add visible testing copy to the TUI. Do not use snapshots as the primary assertion.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/tui/test_e5_journeys.py::test_e5_stub_prompt_stream_final_quit -q -m "not live"</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/tui/test_e5_journeys.py` contains `test_e5_stub_prompt_stream_final_quit`.
    - The test calls `VossTUIApp().run_test()` and never imports `pexpect`, `pty`, or `subprocess`.
    - The prompt is submitted via `InputBar.action_submit()`, not by calling `_turn_dispatch` directly.
    - The test asserts `hello from E5` appears in `TurnView.lines` and `pilot.app._last_response_text`.
    - `python3 -m pytest tests/harness/tui/test_e5_journeys.py::test_e5_stub_prompt_stream_final_quit -q -m "not live"` exits 0.
  </acceptance_criteria>
  <done>The hermetic prompt/stream/final journey proves D-01 and the first D-03 journey through the real Textual Pilot path.</done>
</task>

<task type="auto">
  <name>Task 2: Add diff approve/reject and slash-command journeys</name>
  <files>tests/harness/tui/test_e5_journeys.py</files>
  <read_first>
    - tests/harness/tui/test_diff_modal.py (read HUNKS, _HostApp, accept-all and reject-all patterns)
    - tests/harness/tui/test_slash_palette_interaction.py (read registry, slash keypress, selection spy patterns)
    - tests/harness/tui/test_slash_palette.py (read SlashRegistry/SlashCommand helper patterns)
    - voss/harness/tui/widgets/diff_modal.py (read DiffDecision, DiffModal, Hunk)
    - voss/harness/tui/app.py (read on_slash_palette_palette_submitted)
  </read_first>
  <action>
    In the same file, add `test_e5_diff_modal_accept_and_reject_variants` and `test_e5_slash_command_dispatches_normalized_command`.

    For the diff test, reuse two `Hunk` objects with file names `e5_accept.py` and `e5_reject.py`. Drive one app/modal instance with Pilot key `a` and assert every returned `DiffDecision.decision == "accept"`. Drive a second app/modal instance with Pilot key `q` and assert every returned decision is `"reject"`. This covers D-03's edit/diff approval approve and reject variants using the existing modal contract.

    For the slash test, construct a `SlashRegistry` with `/cost` and `/models` commands. Mount `VossTUIApp(slash_registry=registry)`, spy on `type(app).on_slash_palette_palette_submitted` following `test_slash_palette_interaction.py`, press `slash`, type enough characters to filter to either `cost` or `models`, press `enter`, and assert the submitted command is normalized into the normal input dispatch path as `/cost` or `/models`. Restore the original handler in a `finally` block.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/tui/test_e5_journeys.py tests/harness/tui/test_diff_modal.py tests/harness/tui/test_slash_palette_interaction.py -q -m "not live"</automated>
  </verify>
  <acceptance_criteria>
    - `test_e5_diff_modal_accept_and_reject_variants` asserts both all-accept and all-reject decision arrays.
    - `test_e5_slash_command_dispatches_normalized_command` asserts a submitted command string in `{"/cost", "/models"}`.
    - The slash test restores any monkeypatched class handler in `finally`.
    - `rg -n "pexpect|pty" tests/harness/tui/test_e5_journeys.py` returns no matches.
    - `python3 -m pytest tests/harness/tui/test_e5_journeys.py tests/harness/tui/test_diff_modal.py tests/harness/tui/test_slash_palette_interaction.py -q -m "not live"` exits 0.
  </acceptance_criteria>
  <done>The hermetic journey file covers all D-03 minimum TUI flows with real Pilot interactions and no live credentials.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
| --- | --- |
| Test dispatch -> TUI app | A test-provided async `_turn_dispatch` drives the same app submission path as production but uses deterministic renderer calls. |
| Modal input -> diff decisions | Pilot key presses produce `DiffDecision` values consumed by edit approval code in later live tests. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
| --- | --- | --- | --- | --- |
| T-E5-01 | Spoofing | fake dispatch mistaken for live proof | mitigate | Test file name and assertions are hermetic; live proof is in E5-02 with `@pytest.mark.live`. |
| T-E5-02 | Tampering | tests add visible UI copy/selectors | mitigate | Only test code changes; selectors are existing widget IDs from E5-UI-SPEC. |
| T-E5-03 | Repudiation | empty green journey | mitigate | Tests assert transcript lines, `_last_response_text`, diff decisions, and slash command values. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/tui/test_e5_journeys.py -q -m "not live"` exits 0.
- `python3 -m pytest tests/harness/tui/test_full_flow_pilot.py tests/harness/tui/test_diff_modal.py tests/harness/tui/test_slash_palette_interaction.py -q -m "not live"` exits 0.
- `rg -n "pexpect|pty|subprocess" tests/harness/tui/test_e5_journeys.py` returns no matches.
</verification>

<success_criteria>
- D-01: TUI journeys are Textual Pilot in-process only.
- D-03: prompt/stream/final, diff approve/reject, and slash-command journeys are covered.
- E5-UI-SPEC: no visible UI redesign or new test-only copy is introduced.
</success_criteria>

<output>
Create `.planning/phases/E5-tui-voss-app-autonomous-driving/E5-01-SUMMARY.md` when done.
</output>
