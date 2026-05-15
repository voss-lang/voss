---
phase: T1-iteration-loop-streaming-interrupt
plan: 05
type: execute
wave: 3
depends_on: [T1-01, T1-02, T1-03, T1-04]
files_modified:
  - voss/harness/agent.py
autonomous: true
requirements: [ITER-01, ITER-02, ITER-05, ITER-06]
must_haves:
  truths:
    - "_run_turn_exec is a while-loop that calls provider.stream() per iteration and exits on (a) plan.steps == [] with plan.final_when_done set, (b) iteration count reaches get_config().max_iterations, or (c) ContextScope.budget_exhausted"
    - "Iteration N+1's messages payload contains a serialized representation of iteration N's plan + tool_results"
    - "_substitute_placeholders function and all its call sites are deleted from voss/"
    - "PLAN_LOOP_SYSTEM is the system prompt for iteration calls; it explicitly mentions iteration N of M, the steps:[] + final_when_done done convention, and the per-iter rider context"
    - "Confidence gate fires only on the terminating iteration (the one that returned plan.steps == []); mid-loop low confidence triggers another iteration"
    - "RunRecorder.begin_iteration / end_iteration is called once per loop iteration; finalize is called once at loop exit with the correct exit_reason"
    - "Hit-cap (max-iter) exit produces a final string containing the exact substring 'halted: max-iter'; NEVER raises RuntimeError"
    - "Budget exhaustion exit_reason is 'budget'; cap exit_reason is 'max-iter'; agent-done exit_reason is 'done'"
    - "Telemetry emits iteration.start + iteration.end per iteration with 0-based monotonic iteration_index; note_turn payload includes iteration_count and exit_reason"
  artifacts:
    - path: "voss/harness/agent.py"
      provides: "PLAN_LOOP_SYSTEM constant; rewritten _run_turn_exec body using stream() + while-loop; removed _substitute_placeholders"
      contains: "PLAN_LOOP_SYSTEM = \\|while iteration_index <"
  key_links:
    - from: "voss/harness/agent.py:_run_turn_exec"
      to: "voss/harness/providers.py:StreamingProvider.stream"
      via: "async for event in provider.stream(...)"
      pattern: "async for .* in .*provider\\.stream\\("
    - from: "voss/harness/agent.py:_run_turn_exec"
      to: "voss/harness/recorder.py:RunRecorder.begin_iteration"
      via: "called at the top of each iteration body"
      pattern: "rec\\.begin_iteration"
    - from: "voss/harness/agent.py:_run_turn_exec"
      to: "voss_runtime._config.get_config"
      via: "reads get_config().max_iterations once before entering the loop"
      pattern: "get_config\\(\\)\\.max_iterations"
---

<objective>
Rewrite _run_turn_exec as a while-loop that streams each iteration's plan
via provider.stream(), feeds prior iteration's plan + tool_results into
the next iteration's messages, exits on done/max-iter/budget, moves the
confidence gate to the terminating iteration only, and emits per-iteration
telemetry. Delete _substitute_placeholders and all its call sites.

Purpose: This plan is the core behavior change of phase T1. It is the
"breaking behavior change that justifies v0.2" called out in SPEC line 27.
T1-01 supplied the schema, T1-02/03 supplied the streaming contract,
T1-04 supplied the TurnView delta hook + config knob; this plan composes
them into the new turn loop. Interrupt wiring lives in T1-06 (which
adds the CancelledError handler around this loop's body).

Output: voss/harness/agent.py with a while-loop _run_turn_exec body,
PLAN_LOOP_SYSTEM prompt + per-iter rider builder, deleted
_substitute_placeholders (and grep-verified zero remaining call sites),
new telemetry events iteration.start / iteration.end, and pytest coverage
for ITER-01/02/05/06 acceptance criteria.
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
@voss_runtime/_config.py
</context>

<interfaces>
After T1-01/02/03/04:
- voss/harness/session.py: IterationRecord, RunRecord.iterations,
  RunRecord.iteration_count, RunRecord.exit_reason, EXIT_REASONS frozenset
- voss/harness/recorder.py: RunRecorder.begin_iteration() ->
  IterationRecord; RunRecorder.end_iteration(*, plan, tool_results,
  cost_usd, prompt_tokens, completion_tokens, exit_reason=None) -> None;
  RunRecorder.finalize(cwd, cost_usd, *, exit_reason=None) -> RunRecord
- voss/harness/providers.py: ProviderStreamEvent union (TextDelta,
  ToolUseStart, ToolUseDelta, ToolUseEnd, Usage, Done, ParsedPlan);
  AnthropicOAuthProvider.stream / OpenAIOAuthProvider.stream
- voss/harness/tui/widgets/turn_view.py: TurnView.stream_delta(text),
  TurnView.finalize_stream(*, role, confidence, cost_usd, timestamp)
- voss/harness/config.py: get_max_iterations()
- voss_runtime/_config.py: RuntimeConfig.max_iterations = 8

Existing agent.py members (lines from file):
- PLAN_SYSTEM (line 193) — old static prompt; KEEP for non-loop callers
  but the loop uses a new PLAN_LOOP_SYSTEM
- Plan (line 153) — DON'T modify; locked in CONTEXT.md as "no schema
  migration"; the done signal is `plan.steps == [] AND plan.final_when_done
  is set`
- TurnResult (line 220) — DON'T modify field shape; existing callers
  unpack .plan / .confidence / .final / .tool_results / .cost_usd / .run
- _run_turn_exec (line 305) — REWRITE body
- _run_step_loop (line 507) — REUSED inside the loop body, unchanged
- _substitute_placeholders (line 601) — DELETE
- _make_turn_result (line 607), _compose_run_transcript (line 623),
  _record_run_call — REUSED, unchanged
- _compose_cognition_prompt / _compose_prior_context_block — REUSED,
  unchanged
- ProbableValue + confidence threshold check (line 426) — RELOCATE to
  terminating-iteration-only gate
- ContextScope (line 384) — RELOCATE to wrap the while-loop body so
  budget accumulates across iters

Existing _run_step_loop signature returns a `list[str]` of tool result
text. The IterationRecord.tool_results field is typed list[dict] in T1-01.
Wire mapping: for each iteration, after _run_step_loop returns
`results: list[str]`, build `tool_results = [{"name": step.name, "args":
step.args, "result": text} for step, text in zip(plan.steps, results)]`
and pass that to rec.end_iteration. Per-step args may include large
content (e.g., file edits) — truncate args["content"] to 4096 chars in
the per-iter record if present, matching the existing FAILURE_TRUNC
philosophy in recorder.py.

The message-chain for iteration N+1:
- system: same combined sys_prompt as iter 1 BUT swap PLAN_SYSTEM for
  PLAN_LOOP_SYSTEM (+ voss_md_block + cognition_text + prior_context_text)
- system rider (per-iter): a small additional system message string built
  by _build_iter_rider(iteration_index, max_iterations, prior_summaries).
  This is appended as an extra system message AFTER the cacheable
  sys_prompt — preserves stable prefix for T4 caching.
- user: original task user prompt (iter 1's user prompt) — kept stable so
  cache key is stable
- assistant + tool_result messages: serialized prior iterations.
  Format per CONTEXT.md "Each iteration's provider.complete (or stream)
  call receives prior iteration's plan + tool_results in messages":
    For each prior iter i in 0..N:
      assistant message with content = json.dumps({"rationale": plan.rationale,
                                                    "steps": [s.model_dump() for s in plan.steps],
                                                    "final_when_done": plan.final_when_done})
      user message with content = "Tool results for iteration {i}:\n" +
                                  "\n".join(f"- {step.name}({step.args}) -> {result[:400]}"
                                            for step, result in zip(plan.steps, results))

Why JSON-encoded assistant messages? Both providers accept arbitrary
string assistant content. We avoid the complication of replaying real
tool_use blocks (Anthropic-specific format) — pure-text replay works
for both providers and is sufficient for "tool_results feed back" per
ITER-02. Document this in T1-05-SUMMARY.md as a deliberate choice.

PLAN_LOOP_SYSTEM exact prose (planner-written, CONTEXT.md requires "the
done convention" be explicit):

```
You are Voss, a coding agent running in a terminal. You operate in an
iterative plan→execute→re-plan loop.

You receive a task and a list of tools. On each iteration:
- Review prior iterations' plans and tool results (in messages above).
- Produce a Plan: rationale, sequential tool calls for THIS iteration,
  self-rated confidence (0.0-1.0), and the final answer ONCE you are done.

To signal "done", return a Plan with:
  - steps: []  (empty list)
  - final_when_done: <the user-facing answer, fully realized, NO
    placeholders like {{step_0}}>

If you still need tool calls, return a non-empty `steps` list and the
loop will execute them and call you again on the next iteration.

You have at most {max_iterations} iterations. Use them frugally.

Confidence rubric:
- 0.95+: trivial, deterministic, single-step
- 0.80-0.94: clear path, normal risk
- 0.60-0.79: ambiguity present; consider asking — but ONLY on the done
  iteration. Mid-loop low confidence is fine; just keep iterating.
- below 0.60 on the done iteration: populate open_question and leave
  steps empty.

Only call tools from the provided list.
```

Per-iter rider format (separate system message, appended per call):
```
Iteration {index + 1} of {max_iterations}. Tokens used so far: {tokens_used}/{token_budget}.
{summary_of_prior_iters_or_empty_string}
```
where summary_of_prior_iters is "" on iter 0 and otherwise a one-liner
per prior iter: `- Iter {i}: {step_count} steps, {tool_call_count} tools,
{first_60_chars_of_final_or_rationale}`.

Cancel-point discipline (locked in CONTEXT.md "Cancel-point discipline"):
- Cancel-aware point A: at iteration boundary (before next
  provider.stream() call). The natural CancelledError propagation through
  `async for event in provider.stream(...)` handles this.
- Cancel-aware point B: immediately before each tool dispatch inside
  _run_step_loop (already exists in current impl).
T1-06 wraps the entire _run_turn_exec body in `try/except
asyncio.CancelledError` to set exit_reason="interrupt"; this plan must
LEAVE THAT WRAPPING POINT exposed (clear placement of recorder finalize
before any potential cancel) but does NOT add the except clause itself —
T1-06 owns that.
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add PLAN_LOOP_SYSTEM + rider builder + iteration helpers (no behavior change yet)</name>
  <files>voss/harness/agent.py, tests/harness/test_agent_loop_helpers.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-02 + ITER-05)
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Done signal mechanism + PLAN_LOOP_SYSTEM Claude's-Discretion item, ~lines 36-44 + 89)
    - voss/harness/agent.py (lines 193-227 — PLAN_SYSTEM, RECORD_RUN_SYSTEM, TurnResult)
    - voss/harness/agent.py (lines 305-498 — current _run_turn_exec body)
    - voss/harness/session.py (after T1-01 — IterationRecord)
  </read_first>
  <behavior>
    - PLAN_LOOP_SYSTEM is a module-level constant containing the prose
      from the &lt;interfaces&gt; section above, with the placeholder
      `{max_iterations}` (curly braces literal — `_compose_loop_system`
      function fills it via str.replace, NOT f-string, so the string is
      a static cacheable prefix until rendered)
    - _compose_loop_system(max_iterations: int) -> str returns
      PLAN_LOOP_SYSTEM.replace("{max_iterations}", str(max_iterations))
    - _build_iter_rider(*, index: int, max_iterations: int, tokens_used:
      int, token_budget: int, prior_iters: list[IterationRecord]) -> str
      returns the per-iter rider string. For index=0 and empty prior_iters
      the trailing summary line is the empty string. For index=2 with two
      prior records the returned string includes "Iteration 3 of 8" and
      two "- Iter 0:" / "- Iter 1:" lines.
    - _serialize_iter_for_replay(iter_rec: IterationRecord) -> tuple[dict,
      dict] returns (assistant_message, user_message) where
      assistant_message["role"]=="assistant" and
      assistant_message["content"] is a JSON string containing rationale/
      steps/final_when_done from iter_rec.plan, and user_message["role"]
      == "user" and user_message["content"] starts with "Tool results
      for iteration {i}:".
    - _is_done_plan(plan: Plan) -> bool returns True iff plan.steps == []
      AND plan.final_when_done.strip() != "". Returns False if steps is
      non-empty OR final_when_done is empty/whitespace-only.
    - HALTED_MAX_ITER_FINAL = "halted: max-iter" is a module-level
      constant (no prefix/suffix change permitted without updating tests
      and SPEC). Used by T1-05 Task 2 in the cap-exit branch.
    - HALTED_BUDGET_FINAL = "halted: budget" — additive companion for
      symmetry with budget exit.
  </behavior>
  <action>
    Add the following to `voss/harness/agent.py` after the existing
    PLAN_SYSTEM and RECORD_RUN_SYSTEM constants:

    1. `PLAN_LOOP_SYSTEM` constant — the prose block from the
       &lt;interfaces&gt; section (preserve newlines + the
       `{max_iterations}` placeholder).
    2. `HALTED_MAX_ITER_FINAL = "halted: max-iter"` constant.
    3. `HALTED_BUDGET_FINAL = "halted: budget"` constant.
    4. `def _compose_loop_system(max_iterations: int) -> str:` — one
       liner using `.replace("{max_iterations}", str(max_iterations))`.
    5. `def _build_iter_rider(*, index: int, max_iterations: int,
       tokens_used: int, token_budget: int, prior_iters: list) ->
       str:` — produces the rider per the contract above. The
       prior_iters list contains IterationRecord instances; for each,
       render `f"- Iter {ir.index}: {step_count} steps, {tool_call_count}
       tools, {short(ir.plan.get('final_when_done') or ir.plan.get
       ('rationale'))}"` where step_count = len(ir.plan.get("steps", []))
       and tool_call_count = len(ir.tool_results) and short() truncates
       to 60 chars.
    6. `def _serialize_iter_for_replay(iter_rec) -> tuple[dict, dict]:` —
       returns (assistant, user) messages per the contract. Use
       json.dumps for the assistant content. The user content includes
       a per-step line: `"- {step['name']}({short_args}) -> {result_text
       [:400]}"`. Truncate args at 400 chars too. Mark step args via
       redact_tool_args from voss.harness.telemetry to keep secrets
       out of the message chain.
    7. `def _is_done_plan(plan) -> bool:` — pure predicate.

    Do NOT yet modify _run_turn_exec body. Do NOT delete
    _substitute_placeholders (Task 2 of this plan owns the rewrite +
    deletion).

    Write `tests/harness/test_agent_loop_helpers.py` with seven test
    functions covering the seven behavior bullets. Use plain dataclass
    construction for IterationRecord (imported from voss.harness.session).
    Use SimpleNamespace for Plan stubs where needed for _is_done_plan.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_agent_loop_helpers.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "^PLAN_LOOP_SYSTEM\|^HALTED_MAX_ITER_FINAL\|^HALTED_BUDGET_FINAL" voss/harness/agent.py` returns >= 3 matches
    - exact-string assertion: `grep -F 'halted: max-iter' voss/harness/agent.py` returns >= 1 match (the constant) — this is the EXACT substring required by SPEC's hit-cap criterion
    - source assertion: `grep -n "def _compose_loop_system\|def _build_iter_rider\|def _serialize_iter_for_replay\|def _is_done_plan" voss/harness/agent.py` returns 4 matches
    - behavior assertion: all 7 helper tests pass
    - regression assertion: `uv run pytest tests/harness/ -k agent -x -q` passes (helpers don't disturb the existing _run_turn_exec behavior; old tests still pass)
    - test command: `uv run pytest tests/harness/test_agent_loop_helpers.py tests/harness/ -k agent -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>Five new module-level constants + four helper functions land in agent.py; HALTED_MAX_ITER_FINAL is the exact lowercase-hyphenated string SPEC requires; helpers are pure, deterministic, and unit-tested; _run_turn_exec body is unchanged in this task.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewrite _run_turn_exec as while-loop, delete _substitute_placeholders, emit per-iter telemetry</name>
  <files>voss/harness/agent.py, tests/harness/test_agent_loop.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-01 + ITER-02 + ITER-05 + ITER-06 acceptance criteria including ALL 12 checkboxes — esp. items 1-3, 7-12)
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Done signal + Iteration sub-record schema + Specifics "Exit reason precedence" + "halted: max-iter exact string")
    - voss/harness/agent.py (lines 305-498 — the entire _run_turn_exec function as it stands today)
    - voss/harness/agent.py (lines 507-598 — _run_step_loop, reused inside the new loop)
    - voss/harness/agent.py (line 601-604 — _substitute_placeholders, to be deleted)
    - voss/harness/agent.py (helpers added in Task 1 of this plan)
    - voss/harness/providers.py (after T1-03 — stream() implementations)
    - voss/harness/recorder.py (after T1-01 — begin_iteration/end_iteration)
    - voss/harness/telemetry.py (current note_turn signature + emit() — `grep -n "def note_turn\|def emit" voss/harness/telemetry.py`)
  </read_first>
  <behavior>
    - Given a FakeStreamingProvider that emits one Plan with non-empty
      steps on iter 0 and an `is_done` Plan (steps=[], final_when_done
      set) on iter 1, _run_turn_exec returns TurnResult.run with
      run.iteration_count == 2, run.exit_reason == "done",
      len(run.iterations) == 2
    - Given a provider that always emits non-done plans, _run_turn_exec
      with max_iterations=3 returns TurnResult whose .final contains the
      exact substring "halted: max-iter" and run.exit_reason == "max-iter"
      and run.iteration_count == 3. NO RuntimeError is raised.
    - Given a provider that always emits non-done plans AND a
      ContextScope whose budget is exhausted on iter 1, _run_turn_exec
      returns with run.exit_reason == "budget" and run.final contains
      "halted: budget"
    - Iteration N+1's provider.stream() call's messages list contains
      both an assistant message whose content has iteration N's
      rationale AND a user message whose content starts with "Tool
      results for iteration 0:" — assertable by spying on the
      FakeStreamingProvider.stream() invocation kwargs
    - Confidence gate fixture: 3-iteration run where iter 0 confidence
      = 0.40 (steps non-empty), iter 1 confidence = 0.40 (steps
      non-empty), iter 2 confidence = 0.80 (steps=[], final set) —
      TurnResult.final == iter 2's final_when_done, NOT a clarify
      question; run.exit_reason == "done"
    - Confidence gate clarify fixture: 1-iteration run where iter 0
      confidence = 0.30 AND steps=[] (terminating immediately) — outcome
      is clarify: TurnResult.final == plan.open_question (or default
      clarify string), telemetry.note_turn called with outcome="clarify",
      and run is None (matches current clarify codepath)
    - For a 3-iteration done run, telemetry emits exactly 3
      "iteration.start" events AND 3 "iteration.end" events; the
      "iteration.end" events have iteration_index = 0, 1, 2 in order
    - telemetry.note_turn is called with kwargs that include
      `iteration_count=N` and `exit_reason=&lt;value&gt;` for every
      non-clarify outcome
    - TurnView.stream_delta is called at least once per iteration's
      TextDelta event (verifiable by passing a spying renderer that
      records calls); TurnView.finalize_stream is called once per
      iteration after the iteration's stream completes
    - `grep -rn "_substitute_placeholders" voss/` returns ZERO matches
      after this task completes
    - The function uses get_config().max_iterations (or the harness TOML
      override resolved at cli.py boot — read the value once at function
      top and cap the loop)
    - Per-iteration RunRecorder.begin_iteration is called immediately
      after iteration-start telemetry; RunRecorder.end_iteration is
      called immediately before iteration-end telemetry
  </behavior>
  <action>
    Rewrite the body of `_run_turn_exec` in voss/harness/agent.py.
    Preserve the function signature exactly (callers in run_turn pass
    these kwargs positionally and by name). Keep the existing
    pre-loop setup: cfg/model resolution, history_block,
    user_prompt build, history.add(task), rec = RunRecorder.start(),
    cognition/prior_context/voss_md_block composition. SWAP `PLAN_SYSTEM`
    for `_compose_loop_system(max_iterations)` where max_iterations =
    `get_config().max_iterations` (resolved once into a local
    `max_iterations: int`).

    Then enter the new while-loop. Structure:

    ```
    iteration_index: int = 0
    exit_reason: str | None = None
    final_plan: Plan | None = None
    total_cost_usd: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    accumulated_text_buffer: list[str] = []  # cleared per iter
    all_iter_records: list[IterationRecord] = []

    async with ContextScope(token_budget=token_budget, model=model,
                             provider=provider) as ctx:
        while iteration_index < max_iterations:
            iter_rec = rec.begin_iteration()
            telemetry.emit("iteration.start", "info", data={
                "iteration_index": iteration_index,
                "max_iterations": max_iterations,
            })

            # Build messages for THIS iter:
            rider = _build_iter_rider(
                index=iteration_index,
                max_iterations=max_iterations,
                tokens_used=total_prompt_tokens + total_completion_tokens,
                token_budget=token_budget,
                prior_iters=all_iter_records,
            )
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "system", "content": rider},
                {"role": "user", "content": user_prompt},
            ]
            for prior in all_iter_records:
                a_msg, u_msg = _serialize_iter_for_replay(prior)
                messages.append(a_msg)
                messages.append(u_msg)

            # Stream the iter:
            renderer.show_thinking(f"planning iter {iteration_index + 1}/{max_iterations}")
            iter_t0 = time.monotonic()
            this_iter_plan: Plan | None = None
            this_iter_usage: Usage | None = None
            this_iter_stop: str = "end_turn"
            accumulated_text_buffer.clear()

            async for event in provider.stream(
                messages=messages,
                model=model,
                response_format=Plan,
                temperature=0.2,
                max_tokens=cfg.max_output_tokens,
            ):
                if isinstance(event, TextDelta):
                    accumulated_text_buffer.append(event.text)
                    renderer.stream_delta(event.text)  # NEW renderer surface
                elif isinstance(event, ParsedPlan):
                    this_iter_plan = event.plan
                elif isinstance(event, Usage):
                    this_iter_usage = event
                elif isinstance(event, Done):
                    this_iter_stop = event.stop_reason
                # ToolUseStart/Delta/End: ignored at agent level; provider
                # accumulates them into ParsedPlan

            renderer.finalize_stream(
                role="assistant",
                confidence=(this_iter_plan.confidence if this_iter_plan else None),
                cost_usd=(this_iter_usage.cost_usd if this_iter_usage else 0.0),
                timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )

            if this_iter_plan is None:
                # Parser regress / provider error → halt with budget-style cap
                # but flag a clarify-shaped exit. Pragmatic: treat as done
                # with raw text as final.
                final_text = "".join(accumulated_text_buffer)[:1000] or "(provider returned no parsed plan)"
                this_iter_plan = Plan(rationale="(unparsed)", steps=[], confidence=0.0, final_when_done=final_text)

            # Telemetry / record this iter's provider call:
            telemetry.emit("provider.response", "info", data={
                "phase": "plan",
                "model": model,
                "iteration_index": iteration_index,
                "latency_ms": int((time.monotonic() - iter_t0) * 1000),
                "prompt_tokens": this_iter_usage.prompt_tokens if this_iter_usage else 0,
                "completion_tokens": this_iter_usage.completion_tokens if this_iter_usage else 0,
                "cost_usd": this_iter_usage.cost_usd if this_iter_usage else 0.0,
            })
            renderer.show_plan(this_iter_plan, cost_usd=this_iter_usage.cost_usd if this_iter_usage else 0.0)
            telemetry.emit("plan.parsed", "info", data={
                "iteration_index": iteration_index,
                "confidence": this_iter_plan.confidence,
                "steps": len(this_iter_plan.steps),
            })

            # Done check BEFORE executing steps:
            if _is_done_plan(this_iter_plan):
                # Confidence gate applies HERE, only on terminating iter
                if this_iter_plan.confidence < confidence_threshold:
                    question = this_iter_plan.open_question or "I'm not confident enough — can you clarify the task?"
                    renderer.show_clarify(question, this_iter_plan.confidence)
                    telemetry.note_turn(
                        cost_usd=total_cost_usd + (this_iter_usage.cost_usd if this_iter_usage else 0.0),
                        outcome="clarify",
                        confidence=this_iter_plan.confidence,
                        iteration_count=iteration_index + 1,
                        exit_reason="done",
                    )
                    # End the open iter as 'done' (clarify is a done-shaped exit)
                    rec.end_iteration(
                        plan=this_iter_plan,
                        tool_results=[],
                        cost_usd=this_iter_usage.cost_usd if this_iter_usage else 0.0,
                        prompt_tokens=this_iter_usage.prompt_tokens if this_iter_usage else 0,
                        completion_tokens=this_iter_usage.completion_tokens if this_iter_usage else 0,
                        exit_reason="done",
                    )
                    telemetry.emit("iteration.end", "info", data={
                        "iteration_index": iteration_index,
                        "cost_usd": this_iter_usage.cost_usd if this_iter_usage else 0.0,
                        "prompt_tokens": this_iter_usage.prompt_tokens if this_iter_usage else 0,
                        "completion_tokens": this_iter_usage.completion_tokens if this_iter_usage else 0,
                        "exit_reason": "done",
                    })
                    return TurnResult(
                        plan=this_iter_plan,
                        confidence=this_iter_plan.confidence,
                        final=question,
                        tool_results=[],
                        cost_usd=total_cost_usd + (this_iter_usage.cost_usd if this_iter_usage else 0.0),
                        run=None,
                    )

                exit_reason = "done"
                final_plan = this_iter_plan
                # End this iter as terminating
                rec.end_iteration(
                    plan=this_iter_plan,
                    tool_results=[],
                    cost_usd=this_iter_usage.cost_usd if this_iter_usage else 0.0,
                    prompt_tokens=this_iter_usage.prompt_tokens if this_iter_usage else 0,
                    completion_tokens=this_iter_usage.completion_tokens if this_iter_usage else 0,
                    exit_reason="done",
                )
                telemetry.emit("iteration.end", "info", data={
                    "iteration_index": iteration_index,
                    "cost_usd": this_iter_usage.cost_usd if this_iter_usage else 0.0,
                    "exit_reason": "done",
                })
                # Accumulate and break:
                if this_iter_usage:
                    total_cost_usd += this_iter_usage.cost_usd
                    total_prompt_tokens += this_iter_usage.prompt_tokens
                    total_completion_tokens += this_iter_usage.completion_tokens
                all_iter_records.append(rec._iterations[-1])
                break

            # Execute the steps for this iter (non-terminating):
            results = await _run_step_loop(
                this_iter_plan.steps,
                tools,
                permissions,
                renderer,
                recorder=rec,
            )
            tool_results_for_iter = [
                {"name": s.name, "args": telemetry.redact_tool_args(dict(s.args)),
                 "result": r[:4096]}
                for s, r in zip(this_iter_plan.steps, results)
            ]

            rec.end_iteration(
                plan=this_iter_plan,
                tool_results=tool_results_for_iter,
                cost_usd=this_iter_usage.cost_usd if this_iter_usage else 0.0,
                prompt_tokens=this_iter_usage.prompt_tokens if this_iter_usage else 0,
                completion_tokens=this_iter_usage.completion_tokens if this_iter_usage else 0,
                exit_reason=None,  # non-terminating
            )
            telemetry.emit("iteration.end", "info", data={
                "iteration_index": iteration_index,
                "cost_usd": this_iter_usage.cost_usd if this_iter_usage else 0.0,
                "exit_reason": None,
            })
            if this_iter_usage:
                total_cost_usd += this_iter_usage.cost_usd
                total_prompt_tokens += this_iter_usage.prompt_tokens
                total_completion_tokens += this_iter_usage.completion_tokens
            all_iter_records.append(rec._iterations[-1])

            # Budget exhaustion check (ContextScope tracks via ctx):
            if ctx.exhausted:
                exit_reason = "budget"
                break

            iteration_index += 1
        # End while

        if exit_reason is None:
            # Loop exited because iteration_index == max_iterations
            exit_reason = "max-iter"
    # End ContextScope async-with

    # Build final string:
    if exit_reason == "done":
        final = final_plan.final_when_done or "(no final answer)"
    elif exit_reason == "max-iter":
        final = HALTED_MAX_ITER_FINAL  # exact string "halted: max-iter"
        final_plan = final_plan or all_iter_records[-1].plan  # for record_run input
    elif exit_reason == "budget":
        final = HALTED_BUDGET_FINAL
        final_plan = final_plan or (all_iter_records[-1].plan if all_iter_records else Plan(rationale="(no plan)", steps=[], confidence=0.0, final_when_done=""))

    # Build transcript across ALL iterations for the closing record_run call:
    transcript = _compose_run_transcript(task, final_plan if isinstance(final_plan, Plan) else this_iter_plan,
                                          [r["result"] for r in (all_iter_records[-1].tool_results if all_iter_records else [])],
                                          rec)
    semantics = await _record_run_call(provider, model, transcript)
    if semantics is not None:
        rec.absorb(semantics, final_plan if isinstance(final_plan, Plan) else this_iter_plan)
    else:
        rec.goal = "(record_run failed)"
        rec.plan = (final_plan.model_dump() if isinstance(final_plan, Plan) else (this_iter_plan.model_dump() if this_iter_plan else {}))

    run = rec.finalize(cwd, cost_usd=total_cost_usd, exit_reason=exit_reason)

    if run.decisions:
        try:
            write_decisions_md(cwd, run, session_id or "(no-session)")
        except OSError as exc:
            import click as _click
            _click.echo(f"warning: failed to mirror decisions: {exc}", err=True)

    if history is not None:
        history.add(final, role="assistant")

    total_tokens = total_prompt_tokens + total_completion_tokens
    ctx_pct = total_tokens / token_budget if token_budget else 0.0
    renderer.status(model=model, tokens=total_tokens, cost_usd=total_cost_usd, ctx_pct=ctx_pct)

    telemetry.note_turn(
        cost_usd=total_cost_usd,
        outcome="complete",
        step_count=sum(len((ir.plan or {}).get("steps", [])) for ir in all_iter_records),
        tool_calls=sum(len(ir.tool_results) for ir in all_iter_records),
        total_tokens=total_tokens,
        iteration_count=len(all_iter_records),
        exit_reason=exit_reason,
    )

    return TurnResult(
        plan=final_plan if isinstance(final_plan, Plan) else this_iter_plan,
        confidence=(final_plan.confidence if isinstance(final_plan, Plan) else 0.0),
        final=final,
        tool_results=[r["result"] for ir in all_iter_records for r in ir.tool_results],
        cost_usd=total_cost_usd,
        run=run,
    )
    ```

    DELETE `_substitute_placeholders` function (lines 601-604) AND grep
    `voss/` for any remaining call sites (`grep -rn "_substitute_placeholders"
    voss/`) — the rewrite above does NOT call it; if anything else does
    (unlikely — confirm via grep), remove that call too.

    Add the renderer protocol methods `stream_delta` and `finalize_stream`
    to Renderer (voss/harness/renderer.py — locate via `grep -rn "class Renderer\|class .*Renderer" voss/harness/renderer.py`).
    The protocol gets two new methods with no-op default impls so legacy
    renderer impls (e.g., the plain-text Renderer used in voss do
    non-TUI mode) don't crash; the TextualRenderer subclass forwards to
    TurnView.stream_delta / finalize_stream. Locate TextualRenderer
    (`grep -rn "class TextualRenderer" voss/harness/`) and add the two
    delegating methods.

    Update `voss.harness.telemetry.note_turn` signature to accept new
    kwargs `iteration_count: int = 0` and `exit_reason: str | None =
    None` and persist them in the emitted event. Read
    `voss/harness/telemetry.py` first; if note_turn is defined there
    with a fixed kwarg list, add the two kwargs and forward them into
    the event payload. If note_turn already uses **kwargs, simply
    document that the loop now passes the two new keys.

    Write `tests/harness/test_agent_loop.py` covering the eleven
    behavior bullets above. Use a `FakeStreamingProvider` async-iterable
    helper that yields a scripted ProviderStreamEvent sequence per
    call. Spy on TurnView via a Recording renderer. Stub
    _record_run_call to return None or a minimal SimpleNamespace so the
    test doesn't fan out to a real provider.

    Do NOT modify Plan, ToolCall, RunSemantics, _run_step_loop,
    _compose_run_transcript, _record_run_call, _format_tools,
    _make_turn_result. Do NOT touch run_turn (line 238) — it forwards
    into _run_turn_exec unchanged.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_agent_loop.py tests/harness/test_agent_loop_helpers.py -x -q 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - source assertion (grep gate for SPEC ITER-02): `grep -rn "_substitute_placeholders" voss/` returns ZERO matches
    - source assertion: `grep -n "while iteration_index <\|async for .* in provider\\.stream" voss/harness/agent.py` returns >= 2 matches
    - source assertion: `grep -c "rec.begin_iteration\|rec.end_iteration" voss/harness/agent.py` >= 4 (one of each in done branch + one of each in non-terminating branch)
    - exact-string assertion: `grep -F 'halted: max-iter' voss/harness/agent.py` returns >= 1 (the constant from Task 1)
    - exit-reason-vocabulary assertion: `grep -nE 'exit_reason\s*=\s*"(done|max-iter|budget|interrupt)"' voss/harness/agent.py` — at least three of the four reachable in this file (interrupt comes from T1-06)
    - behavior assertion: all eleven pytest behaviors pass
    - parity assertion: the parity test from T1-03 still passes (regression check)
    - regression assertion: `uv run pytest tests/harness/ -k "agent or recorder or session" -x -q` passes
    - test command: `uv run pytest tests/harness/test_agent_loop.py tests/harness/test_agent_loop_helpers.py tests/harness/ -k "agent or recorder or session or provider_stream" -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>_run_turn_exec is a while-loop calling provider.stream() per iteration; _substitute_placeholders is gone (zero matches in voss/); the three non-interrupt exit_reasons reach their branches with correct final-strings; per-iteration telemetry emits iteration.start/end with 0-based monotonic iteration_index; note_turn carries iteration_count + exit_reason; renderer.stream_delta is called on every TextDelta; confidence gate fires only on the terminating iteration.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/harness/test_agent_loop.py tests/harness/test_agent_loop_helpers.py -x -q` passes
- `grep -rn "_substitute_placeholders" voss/` returns ZERO matches
- `grep -F 'halted: max-iter' voss/harness/agent.py` >= 1 match
- `uv run pytest tests/harness/ -k "agent or recorder or session or provider_stream or turn_view" -x -q` passes
- Telemetry JSONL spy from test fixture asserts: 3-iter run -> exactly 3 iteration.end events with iteration_index 0, 1, 2
</verification>

<success_criteria>
- _run_turn_exec is a while-loop that reaches all three non-interrupt exit_reasons (done / max-iter / budget) via dedicated test fixtures
- Iteration N+1 receives a serialized assistant+user pair for iteration N's plan and tool_results (ITER-02 acceptance)
- _substitute_placeholders is fully deleted from voss/ (SPEC ITER-02 acceptance)
- Hit-cap final string contains exact substring "halted: max-iter" (SPEC quantitative + exact-string criterion)
- Confidence gate moved to terminating-iteration-only (ITER-05 acceptance both fixtures)
- Telemetry emits iteration.start/iteration.end per iter with 0-based monotonic iteration_index; note_turn carries iteration_count + exit_reason (ITER-06 acceptance)
- TurnView streams deltas live (ITER-03 acceptance pre-empts T1-06's interrupt path)
</success_criteria>

<output>
Create `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-05-SUMMARY.md` when done with: line-count delta on agent.py, list of removed call sites of _substitute_placeholders (should be exactly one — the in-function call on line 468 of the old impl), exact PLAN_LOOP_SYSTEM final text shipped, the messages-replay format chosen (assistant+user pair per prior iter), and any signature change to renderer protocol or telemetry.note_turn.
</output>
