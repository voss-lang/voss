---
phase: T1-iteration-loop-streaming-interrupt
plan: 07
type: execute
wave: 5
depends_on: [T1-01, T1-02, T1-03, T1-04, T1-05, T1-06]
files_modified:
  - tests/harness/test_t1_acceptance.py
  - tests/eval/test_golden_2_one_shot.py
  - tests/harness/test_substitute_placeholders_gone.py
  - .github/workflows/test.yml
autonomous: false
requirements: [ITER-01, ITER-02, ITER-03, ITER-04, ITER-05, ITER-06]
must_haves:
  truths:
    - "A single pytest file asserts ALL 12 SPEC acceptance checkboxes in deterministic, replay-driven test cases"
    - "A grep-gate test asserts grep -rn '_substitute_placeholders' voss/ returns zero matches and fails if anyone re-introduces it"
    - "M5 golden task #2 (rename-symbol) completes in ONE voss do invocation, exercised via a stubbed-provider test that simulates a 3-iter rename flow"
    - "First-token latency test asserts TurnView.stream_delta is called within 500ms of the simulated provider HTTP 200 timestamp"
    - "Exit-reason matrix test covers all four values: done, max-iter, budget, interrupt — each via a dedicated fixture"
    - "First-token + 100ms-finalize quantitative thresholds are asserted with time.monotonic() deltas"
    - "A CI workflow step runs the grep gate before pytest, failing the build if _substitute_placeholders re-appears"
    - "test_permission_gate_fresh_per_iteration asserts the injected PermissionGate.prompt_fn is invoked exactly twice across a 2-iter run with identical fs_edit calls (per CONTEXT.md per-iter fresh check invariant)"
  artifacts:
    - path: "tests/harness/test_t1_acceptance.py"
      provides: "Single file with one test function per SPEC acceptance checkbox + exit-reason matrix + latency thresholds + per-iter PermissionGate fresh-check regression"
      contains: "def test_iter_01\\|def test_iter_02\\|def test_iter_03\\|def test_iter_04\\|def test_iter_05\\|def test_iter_06\\|def test_exit_reason_matrix\\|def test_permission_gate_fresh_per_iteration"
    - path: "tests/harness/test_substitute_placeholders_gone.py"
      provides: "Grep-gate test asserting zero matches in voss/"
      contains: "_substitute_placeholders"
    - path: "tests/eval/test_golden_2_one_shot.py"
      provides: "M5 golden #2 rename-symbol completes in one voss do without user re-prompt (stubbed-provider end-to-end)"
      contains: "rename"
    - path: ".github/workflows/test.yml"
      provides: "CI step running the grep gate before pytest"
      contains: "_substitute_placeholders"
  key_links:
    - from: "tests/harness/test_t1_acceptance.py"
      to: "all six ITER requirements"
      via: "one parametrized or explicit test function per requirement"
      pattern: "ITER-0[1-6]"
    - from: ".github/workflows/test.yml"
      to: "tests/harness/test_substitute_placeholders_gone.py"
      via: "explicit step running the grep before pytest"
      pattern: "grep -rn"
---

<objective>
Land the SPEC acceptance test suite + the M5 golden #2 one-shot proof +
the CI grep gate. After this plan, every one of the 12 SPEC acceptance
checkboxes is exercised by a named test, and the build refuses to ship
if anyone re-introduces _substitute_placeholders.

Purpose: SPEC's 12 acceptance checkboxes and 4 quantitative thresholds
are the ultimate goal-backward truth set. T1-05 and T1-06 wrote unit
tests for individual mechanisms; this plan ships the integration suite
that ties them together and proves the phase complete. The M5 golden
#2 unblock is the user-visible win and the v0.2 bump justification.

This plan contains a `checkpoint:human-verify` task because the M5
golden #2 test asserts user-visible behavior on a real-ish provider
run that benefits from a developer eyeballing the resulting telemetry
JSONL + RunRecord JSON for sanity.

Output: tests/harness/test_t1_acceptance.py (single file, 12-ish tests,
one per acceptance checkbox), tests/eval/test_golden_2_one_shot.py,
tests/harness/test_substitute_placeholders_gone.py, CI workflow update,
and a human-verify checkpoint at the end that confirms phase completion.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md
@voss/harness/agent.py
@voss/harness/providers.py
@voss/harness/recorder.py
@voss/harness/session.py
@voss/harness/tui/app.py
</context>

<interfaces>
SPEC's 12 Acceptance Criteria checkboxes (literal quote from SPEC line
96-107):

1. _run_turn_exec is a while-loop that exits on done, max-iter, or budget.
2. Iteration N+1 receives iteration N's plan + tool_results in its
   messages payload (verified via pytest).
3. grep -r _substitute_placeholders voss/ returns zero matches.
4. AnthropicOAuthProvider.stream() and OpenAIOAuthProvider.stream()
   both exist and pass a recorded-fixture parity test.
5. First TurnView token visible ≤ 500ms after provider HTTP 200 in a
   measured test.
6. action_interrupt cancels the active task, sets RunRecord.exit_reason
   = "interrupt", finalizes recorder within 100ms.
7. Confidence < threshold on a non-terminating iteration does NOT
   trigger clarify; on the terminating iteration it DOES.
8. Telemetry JSONL contains one iteration.end event per loop iteration,
   with monotonic iteration_index.
9. note_turn and RunRecord carry iteration_count and exit_reason ∈
   {"done","max-iter","budget","interrupt"}.
10. harness.toml agent.max_iterations defaults to 8 and is honored at
    runtime.
11. M5 golden task #2 (rename-symbol) completes in one voss do without
    user re-prompt.
12. Max-iter cap produces a final string containing "halted: max-iter"
    — not a RuntimeError.

Quantitative thresholds (4):
- ≤500ms first-token (criterion 5)
- ≤100ms interrupt finalize (criterion 6)
- Default max_iterations = 8 (criterion 10)
- Exact substring "halted: max-iter" (criterion 12)

Earlier plan tests covered some of these as side effects (T1-01 covered
criterion 9 partially, T1-04 covered criterion 10, T1-03 covered
criterion 4, T1-05 covered criteria 1/2/3/5/7/8/9/12, T1-06 covered
criterion 6). This plan does NOT redo those tests; it adds an
ACCEPTANCE-LEVEL test file that asserts the contract from the SPEC's
checkbox perspective, in case earlier plans' tests are refactored later.
Think of it as "the acceptance contract" vs "the implementation tests".

M5 golden #2 rename-symbol scenario: per ROADMAP M5 phase + SPEC's
"M5 golden task #2", this is a multi-step coding task that pre-T1
requires the user to re-prompt because the agent can't see test
failures and re-plan. The T1-built loop should fix this. Test
implementation: stub provider that produces a 3-iteration sequence:
  iter 0: plan = read file + grep for old symbol name; tool results
          come back with locations
  iter 1: plan = fs_edit each location; tool results show success
  iter 2: plan = run tests; tool results show pass; plan emits
          steps=[] with final_when_done="renamed FooBar to BarBaz
          across 5 occurrences, tests pass"
The test asserts: only ONE call to run_turn() (not three separate user
prompts), TurnResult.run.iteration_count == 3, TurnResult.run.exit_reason
== "done", TurnResult.final contains "renamed" + "tests pass".

If a real M5 golden fixture file exists (look under tests/eval/golden/
or tests/eval/), reference it. If not, build the stub-provider scenario
inline.

CI workflow gate: locate the existing CI workflow file
(`ls .github/workflows/`). Most likely there's a `test.yml` or
`ci.yml`. Add a step BEFORE the pytest step:
```yaml
- name: grep-gate _substitute_placeholders
  run: |
    if grep -rn "_substitute_placeholders" voss/ ; then
      echo "::error::T1 forbids _substitute_placeholders; re-introduction blocked."
      exit 1
    fi
```
The grep returns success (exit 0) when matches found, which the `if`
treats as truthy → the exit 1 fires. When no matches found, grep
returns exit 1 → `if` is falsy → step passes.

Human-verify checkpoint at the end: developer runs `uv run pytest
tests/harness/test_t1_acceptance.py -v` locally, eyeballs the test
output to confirm all 12 acceptance criteria PASS, then approves.
This is NOT a decision checkpoint — it's verification that the auto-
mation actually proved phase completion.
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: SPEC acceptance test suite + grep-gate test + exit-reason matrix</name>
  <files>tests/harness/test_t1_acceptance.py, tests/harness/test_substitute_placeholders_gone.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (lines 96-107 — the 12 checkboxes — and lines 111-117 — the 4 quantitative thresholds)
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Specifics section — exact strings, 0-based iter index, exit-reason precedence)
    - voss/harness/agent.py (after T1-05 + T1-06 — the loop body, HALTED_MAX_ITER_FINAL constant)
    - voss/harness/recorder.py (after T1-01)
    - voss/harness/session.py (after T1-01 — EXIT_REASONS frozenset)
    - voss/harness/providers.py (after T1-03 — both stream() impls)
    - tests/harness/test_agent_loop.py (T1-05 — reuse the FakeStreamingProvider fixture if exported; if it lives inside test_agent_loop.py, lift it into a conftest.py in this task)
    - voss/harness/permissions.py (line 145 PermissionGate dataclass; line 149 `prompt_fn: Optional[Callable] = None  # injected for tests`; line 169 check() method — used by test_permission_gate_fresh_per_iteration)
  </read_first>
  <behavior>
    - test_iter_01_while_loop_exits_on_done: 2-iter scenario, run.exit_reason == "done"
    - test_iter_01_while_loop_exits_on_max_iter: max_iterations=3 scenario, never-done provider, run.exit_reason == "max-iter", run.iteration_count == 3
    - test_iter_01_while_loop_exits_on_budget: ContextScope budget hit on iter 1, run.exit_reason == "budget"
    - test_iter_02_iter_n_plus_one_receives_prior_results: spy on provider.stream() messages; iter 1 call's messages includes prior iter's tool_results in a user message
    - test_iter_03_grep_substitute_placeholders_returns_zero: subprocess.run(["grep","-rn","_substitute_placeholders","voss/"]).returncode != 0 (grep returns 1 on no match)
    - test_iter_03_first_token_under_500ms: simulate provider stream that emits its first TextDelta after T_open=10ms; spy on renderer.stream_delta call timestamp; assert (stream_delta_t0 - http_200_t0) <= 0.5s. Use synthetic provider that exposes both timestamps. Use a generous threshold (0.5s) to tolerate CI noise; the real budget is much lower.
    - test_iter_04_anthropic_openai_stream_exist: hasattr(AnthropicOAuthProvider, "stream") and hasattr(OpenAIOAuthProvider, "stream"); isinstance(provider, StreamingProvider) for both with stub creds
    - test_iter_04_interrupt_finalizes_within_100ms: cancel task mid-stream; assert (finalize_t - cancel_t) <= 0.1s; assert run.exit_reason == "interrupt"
    - test_iter_05_mid_loop_low_confidence_no_clarify: 3-iter fixture, iter 0 conf=0.40 (non-terminating), iter 1 conf=0.40 (non-terminating), iter 2 conf=0.80 (done) — outcome NOT clarify
    - test_iter_05_terminating_low_confidence_does_clarify: 1-iter fixture, conf=0.30 with steps=[] — outcome IS clarify, run is None
    - test_iter_06_one_iter_end_event_per_iter: 3-iter run, collect telemetry events (use telemetry capture fixture — `grep -rn "telemetry" tests/harness/conftest.py` to find pattern), assert exactly 3 "iteration.end" events with iteration_index 0, 1, 2 in order
    - test_iter_06_note_turn_carries_iteration_count_and_exit_reason: spy on telemetry.note_turn calls; assert kwargs include iteration_count and exit_reason
    - test_iter_06_runrecord_exit_reason_validated: RunRecord(..., exit_reason="quit") raises ValueError; RunRecord(..., exit_reason="done") succeeds
    - test_default_max_iterations_is_8: get_config().max_iterations == 8 when no TOML override
    - test_exact_halted_max_iter_string: cap-exit scenario, "halted: max-iter" in TurnResult.final exactly (use `in` not `==`)
    - test_no_runtime_error_on_cap: cap scenario does NOT raise RuntimeError (pytest.raises with RuntimeError negated)
    - test_exit_reason_matrix_all_four_reachable: four scenarios in one test, asserting all four exit_reasons reach a finalized RunRecord
    - test_permission_gate_fresh_per_iteration: 2-iteration run where iter 0 plan contains ToolCall(name="fs_edit", args={"path":"foo.py","old":"x","new":"y"}) (gate approves via injected prompt_fn that records call count and returns True) and iter 1 plan contains the IDENTICAL fs_edit call. Assert the injected prompt_fn was invoked EXACTLY TWICE (once per iteration). This proves no session-cached approvals — each iter sees a fresh PermissionGate.check() prompt. Source-of-truth: CONTEXT.md "per-iter fresh permission check stays" + SPEC.md ITER-04 "Permission gate per-iter behavior unchanged — each tool call still goes through PermissionGate fresh on every iteration (no session-cached approvals)".
  </behavior>
  <action>
    Create `tests/harness/conftest.py` if it doesn't exist (check via
    `ls tests/harness/conftest.py`); if it does, ADD to it. Lift the
    FakeStreamingProvider fixture from T1-05's test file into conftest
    so test_t1_acceptance can reuse it. Also add a `capture_telemetry`
    fixture that monkeypatches voss.harness.telemetry.emit / note_turn
    to record calls in a list returned to the test.

    Create `tests/harness/test_t1_acceptance.py` with one test function
    per behavior bullet above. Order tests by SPEC checkbox number for
    readability. Use pytest markers (`@pytest.mark.acceptance`,
    `@pytest.mark.t1`) so this suite can be run in isolation via
    `uv run pytest -m t1`.

    Create `tests/harness/test_substitute_placeholders_gone.py`:
    ```
    import subprocess
    from pathlib import Path

    def test_substitute_placeholders_fully_removed():
        repo_root = Path(__file__).resolve().parents[2]
        voss_dir = repo_root / "voss"
        result = subprocess.run(
            ["grep", "-rn", "_substitute_placeholders", str(voss_dir)],
            capture_output=True, text=True,
        )
        # grep returns 0 on match, 1 on no match. We want NO match.
        assert result.returncode != 0, (
            "_substitute_placeholders is forbidden (T1 ITER-02). "
            f"Matches found:\n{result.stdout}"
        )
    ```
    Keep this in its OWN file (not folded into test_t1_acceptance) so
    the grep gate can be run as a standalone selector in CI.

    For test_permission_gate_fresh_per_iteration: instantiate PermissionGate
    with `auto_yes=False, mode="edit"` and inject a Recording `prompt_fn`
    via the `prompt_fn` field (see voss/harness/permissions.py:149 — the
    dataclass exposes `prompt_fn: Optional[Callable] = None  # injected for tests`).
    The Recording prompt_fn appends to a list each call and returns True
    (approve). Wire the gate into the FakeStreamingProvider-backed
    run_turn invocation via the `permissions=` kwarg. After the run
    completes, assert `len(recorded_prompt_calls) == 2` AND that both
    recorded calls reference the same tool name (`fs_edit`) and the same
    args dict (proving each iter re-prompted rather than reusing a cached
    approval). DO NOT modify PermissionGate source — this test is
    pure regression against the unchanged per-iter behavior.

    Do NOT introduce new production code. Pure test additions.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_t1_acceptance.py tests/harness/test_substitute_placeholders_gone.py -v 2>&amp;1 | tail -40</automated>
  </verify>
  <acceptance_criteria>
    - file assertion: `wc -l tests/harness/test_t1_acceptance.py` > 220 (file should contain ~17+ test functions with setup/teardown)
    - source assertion: `grep -cE "^def test_iter_0[1-6]" tests/harness/test_t1_acceptance.py` >= 6 (one per ITER req at minimum)
    - source assertion: `grep -F 'halted: max-iter' tests/harness/test_t1_acceptance.py` returns >= 1 match (exact-string check)
    - source assertion: `grep -F "0.1\|0.5\|100\|500" tests/harness/test_t1_acceptance.py` returns >= 2 matches (latency thresholds present)
    - source assertion: `grep -F "exit_reason" tests/harness/test_t1_acceptance.py | wc -l` >= 8 (matrix coverage)
    - per-iter-permission assertion: `grep -n "test_permission_gate_fresh_per_iteration" tests/harness/test_t1_acceptance.py` returns 1 match; the test passes with `len(recorded_prompt_calls) == 2`
    - grep gate assertion: `grep -rn "_substitute_placeholders" voss/ ; test $? -eq 1` (in shell — returns 0 if grep found nothing)
    - behavior assertion: all tests in test_t1_acceptance.py pass; test_substitute_placeholders_gone passes
    - test command: `uv run pytest tests/harness/test_t1_acceptance.py tests/harness/test_substitute_placeholders_gone.py -v`
    - CLI output: pytest exit code 0; all 17+ tests show PASSED
  </acceptance_criteria>
  <done>tests/harness/test_t1_acceptance.py exercises all 12 SPEC checkboxes + 4 quantitative thresholds + exit_reason matrix; tests/harness/test_substitute_placeholders_gone.py is a standalone grep gate; both pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: M5 golden #2 rename-symbol one-shot test + CI grep gate workflow step</name>
  <files>tests/eval/test_golden_2_one_shot.py, .github/workflows/test.yml</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (Success Criterion 1 from ROADMAP + acceptance criterion 11)
    - .planning/ROADMAP.md (M5 section — see lines around the M5 phase block; `grep -n "^### Phase M5" .planning/ROADMAP.md` to locate)
    - tests/eval/ (look for existing golden fixtures: `ls tests/eval/`; if a tests/eval/golden/02-rename-symbol/ directory exists, use its task.toml)
    - .github/workflows/ (look for existing CI workflow: `ls .github/workflows/`)
    - tests/harness/test_t1_acceptance.py (just-written sibling — reuse FakeStreamingProvider conftest fixture)
  </read_first>
  <behavior>
    - test_golden_2_rename_completes_in_one_run: a single call to
      run_turn(task="Rename FooBar to BarBaz across the repo and verify
      tests pass", ...) using a scripted FakeStreamingProvider that
      produces a 3-iteration sequence (read+grep -> edit all -> run
      tests -> done) returns a TurnResult with iteration_count == 3,
      exit_reason == "done", final containing both "renamed" and a
      success-shaped substring like "tests pass" / "passed" / "ok"
    - The test does NOT call run_turn() a second time (no
      user-re-prompt simulation)
    - The test exercises the ACTUAL agent.py iteration loop (not a
      mock of _run_turn_exec) — i.e., FakeStreamingProvider is the
      only stub; tools are wrapped no-op stubs returning canned text
    - If tests/eval/golden/02-rename-symbol/task.toml exists, the test
      reads `task` from that file; otherwise the task string is
      hardcoded in the test with a comment noting the M5 fixture
      should be re-recorded after T1 ships per CONTEXT.md "M5 fixture
      compatibility = hard break"
    - The CI workflow gains a `grep-gate-substitute-placeholders` step
      that runs `if grep -rn "_substitute_placeholders" voss/; then
      exit 1; fi` BEFORE the pytest step
    - The CI workflow change does not break any unrelated step (the
      addition is purely additive; no existing step gets removed or
      reordered destructively)
  </behavior>
  <action>
    Create `tests/eval/test_golden_2_one_shot.py`. Use the
    FakeStreamingProvider from tests/harness/conftest.py (Task 1
    lifted it there). Script three iterations:

    Iter 0:
      Plan(rationale="Find all FooBar occurrences",
           steps=[ToolCall(name="fs_grep", args={"pattern": "FooBar"})],
           confidence=0.85, final_when_done="")
      Tool result: "src/foo.py:10: class FooBar:\nsrc/foo.py:25:    FooBar()\nsrc/bar.py:5: import FooBar"

    Iter 1:
      Plan(rationale="Edit each occurrence",
           steps=[
             ToolCall(name="fs_edit", args={"path": "src/foo.py", "old": "FooBar", "new": "BarBaz"}),
             ToolCall(name="fs_edit", args={"path": "src/bar.py", "old": "FooBar", "new": "BarBaz"}),
           ],
           confidence=0.85, final_when_done="")
      Tool results: ["edited", "edited"]

    Iter 2:
      Plan(rationale="Run tests to verify",
           steps=[ToolCall(name="shell_run", args={"cmd": "pytest"})],
           confidence=0.85, final_when_done="")
      Tool result: "[exit 0] 5 passed"

    Iter 3 (terminating):
      Plan(rationale="All done",
           steps=[],
           confidence=0.90,
           final_when_done="renamed FooBar to BarBaz across 3 occurrences; tests pass (5 passed)")

    Wait — that's 4 iterations. Reorganize to 3 iters by combining the
    edits into the same iter as the tests (iter 1 does all edits, iter 2
    runs tests AND emits done with steps=[]). Final script:

    Iter 0: fs_grep only.
    Iter 1: fs_edit * 2, then in the SAME plan also include
            shell_run pytest as step 3. (No — better to keep iters
            granular.)

    Actually keep 4 iters: fs_grep / fs_edit*2 / shell_run / done. The
    SPEC acceptance criterion 11 says "completes in one voss do" —
    that's about run_turn invocations, NOT iterations. Iterations
    are internal; the user only sees one run_turn call. Update the
    test to verify iteration_count == 4 (or whatever the scripted
    flow uses) and outcome is success.

    Final scripted iter count: 4. iter 0 = grep, iter 1 = edits,
    iter 2 = run tests, iter 3 = done with steps=[] and final
    populated.

    Use no-op stubs for the actual tools — register a tools dict with
    fs_grep / fs_edit / shell_run pointing to async stub functions that
    return the canned strings above. The point is to exercise the loop,
    not the tool internals.

    Assert:
      assert result.run.iteration_count == 4
      assert result.run.exit_reason == "done"
      assert "renamed" in result.final.lower()
      assert "pass" in result.final.lower() or "ok" in result.final.lower()
      # And the most important assertion: ONE call to run_turn
      assert mock_run_turn_call_count == 1

    Locate the existing CI workflow: `cat .github/workflows/test.yml`
    (or whatever exists in .github/workflows/). Add a step before
    the pytest step:

    ```yaml
        - name: T1 grep gate — _substitute_placeholders is deleted (SPEC ITER-02)
          run: |
            if grep -rn "_substitute_placeholders" voss/ ; then
              echo "::error::_substitute_placeholders re-introduced — forbidden by T1 ITER-02"
              exit 1
            fi
    ```

    If the workflow file doesn't exist (look in `.github/workflows/`),
    note that in the SUMMARY and create a minimal new workflow file —
    BUT FIRST check (per CLAUDE.md "Surgical Changes"); creating a new
    CI file is OUT of surgical scope. If no workflow exists, the grep
    gate lives only in `tests/harness/test_substitute_placeholders_
    gone.py` (which already runs in pytest), and the SUMMARY notes
    "no CI workflow found; gate enforced via pytest". Add a follow-up
    note for future CI setup.
  </action>
  <verify>
    <automated>uv run pytest tests/eval/test_golden_2_one_shot.py -v 2>&amp;1 | tail -30 &amp;&amp; bash -c 'if grep -rn "_substitute_placeholders" voss/ ; then exit 1; fi'</automated>
  </verify>
  <acceptance_criteria>
    - file assertion: `test -f tests/eval/test_golden_2_one_shot.py` succeeds
    - source assertion: `grep -F "iteration_count" tests/eval/test_golden_2_one_shot.py` >= 1 match
    - source assertion: `grep -F "exit_reason" tests/eval/test_golden_2_one_shot.py | grep -F "done"` >= 1 match
    - source assertion: `grep -F "renamed" tests/eval/test_golden_2_one_shot.py` >= 2 matches (in plan script + assertion)
    - CI assertion: if .github/workflows/ exists with at least one workflow file, `grep -rn "_substitute_placeholders\|T1 grep gate" .github/workflows/` returns >= 1 match
    - shell assertion: `bash -c 'if grep -rn _substitute_placeholders voss/; then exit 1; else exit 0; fi'` returns 0
    - behavior assertion: pytest test_golden_2_rename_completes_in_one_run passes
    - test command: `uv run pytest tests/eval/test_golden_2_one_shot.py tests/harness/test_substitute_placeholders_gone.py tests/harness/test_t1_acceptance.py -v`
    - CLI output: pytest exit code 0
  </acceptance_criteria>
  <done>M5 golden #2 rename-symbol test runs the actual agent loop with a scripted provider and asserts one-shot completion; CI gate (workflow step OR pytest-based) blocks _substitute_placeholders re-introduction.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Phase-final verification by developer</name>
  <what-built>
    All 6 plans T1-01 through T1-06 are implemented; T1-07 Tasks 1-2 produced:
      - tests/harness/test_t1_acceptance.py exercising all 12 SPEC acceptance checkboxes
      - tests/harness/test_substitute_placeholders_gone.py grep gate
      - tests/eval/test_golden_2_one_shot.py M5 rename-symbol one-shot
      - CI grep-gate step (or pytest-based fallback if no workflow exists)

    The full T1 phase is now end-to-end runnable: voss do "..." enters
    a streaming iteration loop, Ctrl-C cancels cleanly, the recorder
    finalizes with the correct exit_reason, and _substitute_placeholders
    no longer exists in voss/.
  </what-built>
  <how-to-verify>
    1. Run the full T1 acceptance suite:
       `uv run pytest tests/harness/test_t1_acceptance.py tests/harness/test_substitute_placeholders_gone.py tests/eval/test_golden_2_one_shot.py -v`
       Expected: all tests PASS, exit code 0.

    2. Spot-check the grep gate by hand:
       `grep -rn "_substitute_placeholders" voss/`
       Expected: no output, exit code 1 (grep convention for no match).

    3. Run a live `voss do "say hello and stop"` against a real provider
       (or stub-provider mode if preferred):
       Expected: text streams character-by-character into the TUI / stdout;
       the run completes; .voss/sessions/&lt;id&gt;.json has a top-level
       `iterations: [...]` array on the latest RunRecord and an
       `exit_reason: "done"` field.

    4. Inspect the latest telemetry JSONL:
       `tail -20 .voss/telemetry/*.jsonl | grep iteration.end`
       Expected: one iteration.end event per iteration, with monotonic
       iteration_index starting at 0.

    5. (Optional but recommended) Run a live `voss do` and Ctrl-C
       mid-stream. Expected: text shows "[interrupted]"; the run finalizes;
       the RunRecord has exit_reason: "interrupt".

    6. Confirm the M5 fixture re-record follow-up is tracked:
       The CONTEXT.md says "M5 fixture compatibility = hard break.
       Pre-T1 single-shot fixtures get re-recorded in M5 after T1 ships."
       Make sure that follow-up exists as a tracked task (e.g., a TODO
       in the SUMMARY or an entry in .planning/notes/).

    7. Approve or surface issues with specific failing test names / output.
  </how-to-verify>
  <resume-signal>Type "approved" to mark T1 complete and ship-ready, or describe specific failures / regressions found during verification.</resume-signal>
</task>

</tasks>

<verification>
- `uv run pytest tests/harness/test_t1_acceptance.py tests/harness/test_substitute_placeholders_gone.py tests/eval/test_golden_2_one_shot.py -v` passes
- `grep -rn "_substitute_placeholders" voss/` returns empty + exit code 1
- All 6 SPEC ITER-XX requirement IDs have ≥1 test in test_t1_acceptance.py
- All four exit_reasons (done, max-iter, budget, interrupt) reachable per test_exit_reason_matrix
- CI workflow (if present) has the grep gate as an explicit step
- Phase-final human-verify checkpoint approved
</verification>

<success_criteria>
- 12 of 12 SPEC acceptance checkboxes covered by named tests in test_t1_acceptance.py
- 4 of 4 quantitative thresholds asserted with time.monotonic deltas or exact strings
- M5 golden #2 rename-symbol completes in one run_turn call (mock_run_turn_call_count == 1)
- CI grep gate blocks _substitute_placeholders re-introduction (workflow step OR pytest test)
- Phase verification checkpoint reaches "approved" state
</success_criteria>

<output>
Create `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-07-SUMMARY.md` when done with: SPEC-checkbox-to-test-function mapping table (12 rows), measured latency from the first-token test, measured latency from the interrupt-finalize test, M5 follow-up tracking note (re-record fixtures), and the approve-signal from the human-verify checkpoint.
</output>
