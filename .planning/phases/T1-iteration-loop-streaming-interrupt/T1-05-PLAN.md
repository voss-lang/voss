---
phase: T1-iteration-loop-streaming-interrupt
plan: 05
type: execute
wave: 3
depends_on: [T1-01, T1-02, T1-03, T1-04]
files_modified:
  - voss/harness/agent.py
  - voss/harness/render.py
  - voss/harness/tui/renderer.py
  - voss/harness/telemetry.py
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
    - "Renderer Protocol gains stream_delta(text: str) and finalize_stream(*, role, confidence, cost_usd, timestamp); all four concrete renderer impls (TtyRenderer, PlainRenderer, JsonRenderer, TextualRenderer) implement both methods"
    - "telemetry.note_turn already accepts arbitrary kwargs via **fields (telemetry.py line 80) — no signature change required; calling convention adds iteration_count + exit_reason keys exercised by tests"
  artifacts:
    - path: "voss/harness/agent.py"
      provides: "PLAN_LOOP_SYSTEM constant; rewritten _run_turn_exec body using stream() + while-loop; removed _substitute_placeholders"
      contains: "PLAN_LOOP_SYSTEM = \\|while iteration_index <"
    - path: "voss/harness/render.py"
      provides: "Renderer Protocol gains stream_delta + finalize_stream; TtyRenderer/PlainRenderer/JsonRenderer get concrete impls"
      contains: "def stream_delta"
    - path: "voss/harness/tui/renderer.py"
      provides: "TextualRenderer.stream_delta forwards to TurnView.stream_delta; TextualRenderer.finalize_stream forwards to TurnView.finalize_stream"
      contains: "def stream_delta"
    - path: "voss/harness/telemetry.py"
      provides: "Calling-convention only — note_turn(**fields) already accepts iteration_count + exit_reason; zero source diff"
      contains: "note_turn"
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
    - from: "voss/harness/tui/renderer.py:TextualRenderer.stream_delta"
      to: "voss/harness/tui/widgets/turn_view.py:TurnView.stream_delta"
      via: "_safe + _post forwarding pattern (same shape as show_plan at line 143)"
      pattern: "TurnView.*stream_delta"
---

<objective>
Rewrite _run_turn_exec as a while-loop that streams each iteration's plan
via provider.stream(), feeds prior iteration's plan + tool_results into
the next iteration's messages, exits on done/max-iter/budget, moves the
confidence gate to the terminating iteration only, and emits per-iteration
telemetry. Delete _substitute_placeholders. Wire the new
renderer.stream_delta / renderer.finalize_stream methods through every
existing Renderer impl so the loop can call them unconditionally.

Purpose: This plan is the core behavior change of phase T1. It is the
"breaking behavior change that justifies v0.2" called out in SPEC line 27.
T1-01 supplied the schema, T1-02/03 supplied the streaming contract,
T1-04 supplied the TurnView delta hook + config knob; this plan composes
them into the new turn loop. Interrupt wiring lives in T1-06.

Output: voss/harness/agent.py with a while-loop _run_turn_exec body,
PLAN_LOOP_SYSTEM prompt + per-iter rider builder, deleted
_substitute_placeholders (and grep-verified zero remaining call sites),
new telemetry events iteration.start / iteration.end; voss/harness/render.py
+ voss/harness/tui/renderer.py with the new renderer methods on every
implementation class; pytest coverage for ITER-01/02/05/06 acceptance
criteria.

Task split (per plan-checker W6): Task 2a rewrites agent.py only;
Task 2b adds renderer methods + confirms telemetry.note_turn passthrough.
Both Wave 3; 2a and 2b touch disjoint files so they can execute in
parallel within Wave 3.
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
@voss/harness/render.py
@voss/harness/tui/renderer.py
@voss/harness/telemetry.py
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

Existing renderer classes (CONFIRMED via reads):
- voss/harness/render.py line 27: `class Renderer(Protocol)` — the
  Protocol class. Existing methods: show_user, show_thinking, show_plan,
  show_tool_call, show_clarify, show_final, status, show_cognition,
  show_cognition_overflow, show_warning. THIS PLAN ADDS: stream_delta,
  finalize_stream.
- voss/harness/render.py line 126: `class TtyRenderer` — Rich-backed
  terminal renderer (uses self.console).
- voss/harness/render.py line 237: `class PlainRenderer` — plain stderr
  fallback (uses print to stderr for metadata, stdout for content).
- voss/harness/render.py line 294: `class JsonRenderer` — NDJSON-on-stdout
  emitter (--json mode).
- voss/harness/tui/renderer.py line 43: `class TextualRenderer` — the
  Textual TUI surface; methods use the `_safe(widget_fn, attr, *args,
  **kwargs)` forwarding pattern defined at lines 70-90; see existing
  `show_plan` at line 143 for the template.

Existing telemetry surface (CONFIRMED via read of voss/harness/telemetry.py
lines 80-85):

  def note_turn(**fields: Any) -> None:
      """Attach keys merged into turn.end (e.g. cost_usd, step_count)."""
      cur = dict(_turn_meta.get() or {})
      cur.update({k: v for k, v in fields.items() if v is not None})
      _turn_meta.set(cur)

note_turn already accepts arbitrary kwargs via **fields and merges them
into _turn_meta. No signature change required to add iteration_count and
exit_reason. Listed in files_modified for audit-trail completeness but
the source diff in telemetry.py is zero lines. Task 2b includes one
regression test asserting both new keys land in _turn_meta.

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

The message-chain for iteration N+1:
- system: combined sys_prompt swapping PLAN_SYSTEM for PLAN_LOOP_SYSTEM
- system rider (per-iter): a small additional system message string built
  by _build_iter_rider(iteration_index, max_iterations, prior_summaries),
  appended AFTER the cacheable sys_prompt
- user: original task user prompt (iter 1's user prompt) — kept stable
- assistant + tool_result messages: serialized prior iterations as a JSON
  blob in an assistant message + a "Tool results for iteration {i}:"
  user message per prior iter.

PLAN_LOOP_SYSTEM exact prose (preserve verbatim — the {max_iterations}
placeholder is filled via str.replace, NOT f-string, so the prefix stays
stable for future T4 caching):

  You are Voss, a coding agent running in a terminal. You operate in an
  iterative plan-then-execute-then-re-plan loop.

  You receive a task and a list of tools. On each iteration:
  - Review prior iterations' plans and tool results (in messages above).
  - Produce a Plan: rationale, sequential tool calls for THIS iteration,
    self-rated confidence (0.0-1.0), and the final answer ONCE you are
    done.

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

Renderer methods to ADD to the Protocol + every impl class:
- `def stream_delta(self, text: str) -> None` — receive a chunk of
  streaming assistant text; render incrementally
- `def finalize_stream(self, *, role: str, confidence: float | None = None,
   cost_usd: float | None = None, timestamp: str | None = None) -> None`
   — seal the streamed block with header metadata

Per-renderer behavior (each class's existing output channel is preserved):
- Renderer (Protocol, line 27 of render.py): add the two method
  signatures as `...` ellipsis stubs alongside existing show_* methods.
- TtyRenderer (line 126): stream_delta -> self.console.print(text,
  end="", soft_wrap=True). finalize_stream -> self.console.print()
  (newline) then a metadata footer formatted like the existing
  show_final visual style.
- PlainRenderer (line 237): stream_delta -> sys.stdout.write(text) +
  sys.stdout.flush(). finalize_stream -> sys.stdout.write("\n") plus a
  one-line metadata footer to sys.stderr.
- JsonRenderer (line 294): stream_delta -> emit one NDJSON event
  {"type":"stream.delta","text":text} on stdout. finalize_stream ->
  emit {"type":"stream.finalize","role":role,"confidence":conf,
  "cost_usd":cost,"timestamp":ts}.
- TextualRenderer (tui/renderer.py line 43): stream_delta forwards to
  TurnView.stream_delta via the _safe(lambda: ..., "turn", ...) pattern
  visible in show_plan at line 143; finalize_stream forwards to
  TurnView.finalize_stream via the same pattern.
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
      and SPEC). Used by Task 2a in the cap-exit branch.
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
       render a per-iter line with the format `- Iter {ir.index}:
       {step_count} steps, {tool_call_count} tools, {first_60_chars}`
       where step_count = len(ir.plan.get("steps", [])) and
       tool_call_count = len(ir.tool_results) and the trailing 60-char
       snippet is the first 60 chars of ir.plan.get("final_when_done")
       or, when that is empty, ir.plan.get("rationale").
    6. `def _serialize_iter_for_replay(iter_rec) -> tuple[dict, dict]:`
       — returns (assistant, user) messages per the contract. Use
       json.dumps for the assistant content. The user content includes
       a per-step line: `- {step['name']}({short_args}) -> {result_text
       truncated to 400 chars}`. Truncate args at 400 chars too. Apply
       redact_tool_args from voss.harness.telemetry to keep secrets
       out of the message chain.
    7. `def _is_done_plan(plan) -> bool:` — pure predicate.

    Do NOT yet modify _run_turn_exec body. Do NOT delete
    _substitute_placeholders (Task 2a owns the rewrite + deletion).
    Do NOT modify Renderer protocol or telemetry.py here (Task 2b
    owns those).

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
  <name>Task 2a: Rewrite _run_turn_exec as while-loop + delete _substitute_placeholders</name>
  <files>voss/harness/agent.py, tests/harness/test_agent_loop.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-01 + ITER-02 + ITER-05 + ITER-06 acceptance criteria including ALL 12 checkboxes — esp. items 1-3, 7-9, 11, 12)
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Done signal + Iteration sub-record schema + Specifics "Exit reason precedence" + "halted: max-iter exact string")
    - voss/harness/agent.py (lines 305-498 — the entire _run_turn_exec function as it stands today)
    - voss/harness/agent.py (lines 507-598 — _run_step_loop, reused inside the new loop)
    - voss/harness/agent.py (line 601-604 — _substitute_placeholders, to be deleted)
    - voss/harness/agent.py (helpers added in Task 1 of this plan)
    - voss/harness/providers.py (after T1-03 — stream() implementations)
    - voss/harness/recorder.py (after T1-01 — begin_iteration/end_iteration)
    - the &lt;reference_scaffold&gt; block in this PLAN file (below the &lt;tasks&gt; block) — pseudocode for the rewritten function body
  </read_first>
  <behavior>
    - Given a FakeStreamingProvider that emits one Plan with non-empty
      steps on iter 0 and an is-done Plan (steps=[], final_when_done
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
      iteration_count=N and exit_reason=&lt;value&gt; for every
      non-clarify outcome
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
    pre-loop setup: cfg/model resolution, history_block, user_prompt
    build, history.add(task), `rec = RunRecorder.start()`,
    cognition/prior_context/voss_md_block composition. SWAP `PLAN_SYSTEM`
    for `_compose_loop_system(max_iterations)` where max_iterations =
    `get_config().max_iterations` (resolved once into a local
    `max_iterations: int`).

    Follow the &lt;reference_scaffold&gt; block below (after the
    &lt;tasks&gt; block) as the structural blueprint. Concretely the
    new body must:

    1. Establish loop-scoped locals: `iteration_index = 0`,
       `exit_reason: str | None = None`, `final_plan: Plan | None =
       None`, accumulators for cost_usd / prompt_tokens /
       completion_tokens, an `all_iter_records: list[IterationRecord]`
       list, and an `accumulated_text_buffer: list[str]` reset per iter.
    2. Open `async with ContextScope(token_budget=token_budget,
       model=model, provider=provider) as ctx:`.
    3. Enter `while iteration_index < max_iterations:`. At iter top
       call `iter_rec = rec.begin_iteration()` then emit
       `telemetry.emit("iteration.start", "info", data={"iteration_index":
       iteration_index, "max_iterations": max_iterations})`.
    4. Build the per-iter messages list: one system entry with the
       static sys_prompt (PLAN_LOOP_SYSTEM-derived), one system entry
       with the rider string from `_build_iter_rider(...)`, one user
       entry with the task user_prompt, then a (assistant, user) pair
       per prior iter via `_serialize_iter_for_replay(prior)`.
    5. Call `provider.stream(messages=messages, model=model,
       response_format=Plan, temperature=0.2, max_tokens=cfg.max_output_tokens)`
       and consume the async iterator. On `TextDelta`: append to
       `accumulated_text_buffer` and call `renderer.stream_delta(event.text)`.
       On `ParsedPlan`: capture `this_iter_plan`. On `Usage`: capture
       `this_iter_usage`. On `Done`: capture `this_iter_stop`. Ignore
       `ToolUseStart`/`ToolUseDelta`/`ToolUseEnd` (the provider already
       accumulates these into the ParsedPlan event).
    6. After the async-for completes, call
       `renderer.finalize_stream(role="assistant",
       confidence=this_iter_plan.confidence if this_iter_plan else None,
       cost_usd=this_iter_usage.cost_usd if this_iter_usage else 0.0,
       timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"))`.
    7. If `this_iter_plan is None`: fall back to a synthetic Plan
       constructed from `"".join(accumulated_text_buffer)` truncated to
       1000 chars; rationale="(unparsed)", steps=[], confidence=0.0.
    8. Emit `provider.response` + `plan.parsed` telemetry events
       carrying the new `iteration_index` key.
    9. If `_is_done_plan(this_iter_plan)`: apply the confidence gate
       HERE (not at iter 1). If `this_iter_plan.confidence <
       confidence_threshold`: call renderer.show_clarify(question, conf),
       call telemetry.note_turn with the clarify-shaped kwargs (must
       include iteration_count and exit_reason="done"), close the open
       iter via rec.end_iteration(..., exit_reason="done"), emit
       iteration.end telemetry, and `return TurnResult(...)` with
       run=None. Otherwise set `exit_reason = "done"`, set
       `final_plan = this_iter_plan`, close the open iter with
       exit_reason="done", emit iteration.end, accumulate totals,
       append the iter record to `all_iter_records`, and `break`.
    10. Else (non-terminating iter): call `_run_step_loop(this_iter_plan.steps,
        tools, permissions, renderer, recorder=rec)` -> list[str] results.
        Build `tool_results_for_iter` as a list of `{"name": s.name,
        "args": telemetry.redact_tool_args(dict(s.args)), "result":
        r[:4096]}` dicts. Call rec.end_iteration(plan=this_iter_plan,
        tool_results=tool_results_for_iter, cost_usd=..., prompt_tokens=...,
        completion_tokens=..., exit_reason=None). Emit iteration.end
        with exit_reason=None. Append the iter record to
        all_iter_records. If ctx.exhausted: set
        `exit_reason = "budget"` and break. Otherwise increment
        iteration_index and continue.
    11. After the while loop: if exit_reason is still None, the loop
        exited because iteration_index reached max_iterations -> set
        exit_reason = "max-iter".
    12. After the ContextScope async-with: build the user-facing final
        string per exit_reason — "done" -> final_plan.final_when_done
        or "(no final answer)"; "max-iter" -> HALTED_MAX_ITER_FINAL;
        "budget" -> HALTED_BUDGET_FINAL. Build the run transcript via
        _compose_run_transcript using the exit-iter plan and its
        results, call _record_run_call, call rec.absorb if semantics
        non-None or fall back to the synthetic goal "(record_run failed)"
        path, then call rec.finalize(cwd, cost_usd=total_cost_usd,
        exit_reason=exit_reason) -> run. Call write_decisions_md if
        run.decisions is non-empty, then history.add(final,
        role="assistant"), renderer.status(...), telemetry.note_turn
        with kwargs including iteration_count + exit_reason +
        outcome="complete", and finally return TurnResult.

    DELETE `_substitute_placeholders` (def at line 601 and its inline
    call site around line 468 inside the old _run_turn_exec body —
    the rewrite naturally eliminates that call site). Confirm via
    `grep -rn "_substitute_placeholders" voss/` returning zero matches.

    This task ASSUMES the renderer.stream_delta + renderer.finalize_stream
    methods exist on every Renderer impl. Task 2b adds them. Wave 3
    schedules 2a and 2b in parallel; tests in this task use a Recording
    stub renderer (defined inline in the test file) that exposes
    stream_delta + finalize_stream as no-op recorders, so this task's
    pytest does NOT depend on Task 2b landing first.

    Do NOT modify Plan, ToolCall, RunSemantics, _run_step_loop,
    _compose_run_transcript, _record_run_call, _format_tools,
    _make_turn_result. Do NOT touch run_turn (line 238) — it forwards
    into _run_turn_exec unchanged. Do NOT modify the Renderer Protocol
    or any concrete renderer class here (Task 2b owns that).

    Write `tests/harness/test_agent_loop.py` covering the ten behavior
    bullets above. Use a `FakeStreamingProvider` async-iterable helper
    that yields a scripted ProviderStreamEvent sequence per call. Use
    a `RecordingRenderer` test-double class implementing all Renderer
    Protocol methods including stream_delta + finalize_stream as
    list-append recorders. Stub `_record_run_call` to return None or a
    minimal SimpleNamespace so the test doesn't fan out to a real
    provider.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_agent_loop.py tests/harness/test_agent_loop_helpers.py -x -q 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - source assertion (grep gate for SPEC ITER-02): `grep -rn "_substitute_placeholders" voss/` returns ZERO matches
    - source assertion: `grep -n "while iteration_index <\|async for .* in provider\\.stream" voss/harness/agent.py` returns >= 2 matches
    - source assertion: `grep -c "rec\\.begin_iteration\|rec\\.end_iteration" voss/harness/agent.py` >= 4 (one of each in done branch + one of each in non-terminating branch)
    - exact-string assertion: `grep -F 'halted: max-iter' voss/harness/agent.py` returns >= 1 (the constant from Task 1)
    - exit-reason-vocabulary assertion: `grep -nE 'exit_reason\s*=\s*"(done|max-iter|budget|interrupt)"' voss/harness/agent.py` — at least three of the four reachable in this file (interrupt comes from T1-06)
    - behavior assertion: all ten pytest behaviors pass
    - parity assertion: the parity test from T1-03 still passes (regression check)
    - regression assertion: `uv run pytest tests/harness/ -k "agent or recorder or session" -x -q` passes
    - test command: `uv run pytest tests/harness/test_agent_loop.py tests/harness/test_agent_loop_helpers.py tests/harness/ -k "agent or recorder or session or provider_stream" -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>_run_turn_exec is a while-loop calling provider.stream() per iteration; _substitute_placeholders is gone (zero matches in voss/); the three non-interrupt exit_reasons reach their branches with correct final-strings; per-iteration telemetry emits iteration.start/end with 0-based monotonic iteration_index; note_turn carries iteration_count + exit_reason; renderer.stream_delta is called on every TextDelta (using a stub renderer in test fixtures); confidence gate fires only on the terminating iteration.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2b: Add Renderer.stream_delta + finalize_stream to Protocol and all four impls</name>
  <files>voss/harness/render.py, voss/harness/tui/renderer.py, tests/harness/test_renderer_streaming.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-03 — TurnView renders incremental deltas)
    - voss/harness/render.py (entire file — Renderer Protocol at line 27, TtyRenderer at line 126, PlainRenderer at line 237, JsonRenderer at line 294)
    - voss/harness/tui/renderer.py (line 43 TextualRenderer + line 70-90 _safe helper + line 143-165 show_plan as the _safe-pattern template)
    - voss/harness/tui/widgets/turn_view.py (after T1-04 — TurnView.stream_delta + TurnView.finalize_stream)
    - voss/harness/telemetry.py (lines 80-85 — note_turn signature confirms **kwargs already accepted, no change required)
  </read_first>
  <behavior>
    - Renderer Protocol (render.py line 27) declares two new ellipsis
      methods: `def stream_delta(self, text: str) -> None: ...` and
      `def finalize_stream(self, *, role: str, confidence: float | None
      = None, cost_usd: float | None = None, timestamp: str | None =
      None) -> None: ...` — placed adjacent to show_final
    - TtyRenderer.stream_delta(text) prints the chunk via
      `self.console.print(text, end="", soft_wrap=True)` (no newline
      per chunk).
    - TtyRenderer.finalize_stream(...) prints a newline then a single
      `show_final`-style metadata line (role/cost/conf if provided).
      Safe to call without any preceding stream_delta.
    - PlainRenderer.stream_delta(text) writes text to sys.stdout and
      flushes; finalize_stream writes a newline to stdout and a
      one-line metadata footer to stderr.
    - JsonRenderer.stream_delta(text) emits one NDJSON event with
      shape `{"type":"stream.delta","text":text}` on stdout; emits a
      flush. finalize_stream emits `{"type":"stream.finalize",
      "role":role,"confidence":confidence,"cost_usd":cost_usd,
      "timestamp":timestamp}`. Both events conform to the existing
      JsonRenderer per-line emit pattern.
    - TextualRenderer.stream_delta(text) follows the EXACT pattern of
      its existing `show_plan` (line 143): uses `_safe(lambda:
      self.app.query_one("#turn", TurnView), "turn", ...)` plus the
      inner forwarding call. Inspect the existing _safe signature in
      tui/renderer.py lines 70-90 to confirm the argument order; the
      call shape MUST be a direct delegate to TurnView.stream_delta(text).
    - TextualRenderer.finalize_stream(*, role, confidence, cost_usd,
      timestamp) follows the same `_safe`-based forwarding pattern,
      delegating to TurnView.finalize_stream with the same kwargs.
    - For test coverage: a renderer-streaming pytest file calls
      stream_delta + finalize_stream on TtyRenderer, PlainRenderer,
      JsonRenderer, and a mock TextualRenderer where `_safe` is
      monkeypatched to a Recording function; asserts each impl's
      side-effect channel (Rich console capture / stdout capture /
      stderr capture / forwarded-call list) shows the expected output.
    - telemetry.note_turn already accepts arbitrary kwargs via
      **fields (confirmed at telemetry.py line 80). A regression
      test confirms `telemetry.note_turn(iteration_count=3,
      exit_reason="done", cost_usd=0.1, outcome="complete")` succeeds
      and the resulting _turn_meta dict contains all four keys.
  </behavior>
  <action>
    In `voss/harness/render.py`:

    1. Add two methods to the `class Renderer(Protocol)` block at line
       27 — placed adjacent to `show_final` (line 34). The two methods
       use ellipsis (`...`) bodies, matching the existing pattern of
       the other Protocol methods. The exact signatures:
       - `def stream_delta(self, text: str) -> None: ...`
       - `def finalize_stream(self, *, role: str, confidence: float |
         None = None, cost_usd: float | None = None, timestamp: str |
         None = None) -> None: ...`

    2. In `class TtyRenderer` (line 126), add:
       - `def stream_delta(self, text: str) -> None:` body calls
         `self.console.print(text, end="", soft_wrap=True)`. Existing
         self.console is set in __post_init__ at line 130.
       - `def finalize_stream(self, *, role, confidence=None,
         cost_usd=None, timestamp=None) -> None:` body calls
         `self.console.print()` (newline) then prints a one-line
         metadata footer formatted like the existing show_final
         header (uses `[dim]{role}[/dim]  ·  conf {confidence:.2f}
         · ${cost_usd:.4f}` shape when fields are present; skip a
         field if None). Match the existing show_final visual style.

    3. In `class PlainRenderer` (line 237), add:
       - `def stream_delta(self, text: str) -> None:` body calls
         `sys.stdout.write(text); sys.stdout.flush()`.
       - `def finalize_stream(self, *, role, confidence=None,
         cost_usd=None, timestamp=None) -> None:` body calls
         `sys.stdout.write("\n"); sys.stdout.flush()` then writes a
         one-line metadata footer to sys.stderr using print (matches
         existing PlainRenderer.show_final/show_warning convention of
         stderr for metadata, stdout for content).

    4. In `class JsonRenderer` (line 294), add:
       - `def stream_delta(self, text: str) -> None:` body emits a
         JSON line on stdout following the existing JsonRenderer
         per-event emit helper (read lines 294-360 in render.py for
         the existing helper name; if there's an internal `_emit`
         method or similar, call that; otherwise json.dumps + print
         + flush directly). Event payload: `{"type": "stream.delta",
         "text": text}`.
       - `def finalize_stream(self, *, role, confidence=None,
         cost_usd=None, timestamp=None) -> None:` emits one JSON line
         on stdout with shape `{"type": "stream.finalize", "role":
         role, "confidence": confidence, "cost_usd": cost_usd,
         "timestamp": timestamp}`.

    In `voss/harness/tui/renderer.py`:

    5. In `class TextualRenderer` (line 43), add two methods. Pattern:
       read the existing `show_plan` at line 143-165 to identify the
       `_safe(lambda: self.app.query_one("#turn", TurnView), "turn",
       <fn>, <args>)` call shape (the exact arg layout of `_safe` lives
       at lines 70-90; read those to confirm). Then:
       - `def stream_delta(self, text: str) -> None:` forwards to
         `TurnView.stream_delta(text)` via the same _safe lookup +
         _post forwarding shape used by show_plan. The forwarding
         closure passes `text` to the widget's stream_delta(text).
       - `def finalize_stream(self, *, role, confidence=None,
         cost_usd=None, timestamp=None) -> None:` forwards to
         `TurnView.finalize_stream(role=role, confidence=confidence,
         cost_usd=cost_usd, timestamp=timestamp)` via the same _safe
         lookup + _post forwarding shape.

    Do NOT modify telemetry.py source — it already accepts **kwargs
    (telemetry.py line 80). The test file in this task includes one
    note_turn-kwargs regression test to confirm the new keys land in
    _turn_meta. List telemetry.py in files_modified for audit-trail
    completeness; the actual diff in that file is zero lines.

    Write `tests/harness/test_renderer_streaming.py` covering nine
    behavior bullets. Use capsys / capfd fixtures for
    PlainRenderer/JsonRenderer stdout/stderr capture. Use a
    rich.console.Console with `file=io.StringIO()` for TtyRenderer
    capture. For TextualRenderer, monkeypatch the _safe method to a
    Recording function that captures (widget_factory, attr, method_name,
    *args) tuples; assert the recorded calls show the expected
    delegation. One additional test asserts
    `telemetry.note_turn(iteration_count=3, exit_reason="done")`
    succeeds and the meta dict contains both keys (reset _turn_meta
    via telemetry.clear_turn between tests if needed — read
    telemetry.py lines 65-78 for the existing turn-lifecycle helpers).
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_renderer_streaming.py -x -q 2>&amp;1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -cE "def stream_delta|def finalize_stream" voss/harness/render.py` >= 8 (1 Protocol pair + 3 impl class pairs = 2*4 = 8 method defs)
    - source assertion: `grep -cE "def stream_delta|def finalize_stream" voss/harness/tui/renderer.py` == 2 (the TextualRenderer impls)
    - source assertion: TextualRenderer's delegation to TurnView visible — `grep -n "TurnView" voss/harness/tui/renderer.py` shows the query_one reference (existing pattern) and the new methods route through it
    - behavior assertion: all 9 pytest behaviors pass (3 renderer classes + TextualRenderer mock + note_turn-kwargs regression)
    - regression assertion: `uv run pytest tests/harness/ -k "render or renderer or tui" -x -q` passes
    - telemetry-passthrough assertion: pytest test_note_turn_accepts_iteration_count_and_exit_reason asserts both keys appear in _turn_meta after a single note_turn call with both kwargs
    - test command: `uv run pytest tests/harness/test_renderer_streaming.py tests/harness/ -k "render or renderer or tui" -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>Renderer Protocol gains stream_delta + finalize_stream; all four concrete renderer classes (TtyRenderer, PlainRenderer, JsonRenderer, TextualRenderer) implement both methods following each class's existing output channel convention; TextualRenderer delegates to TurnView via the established _safe forwarding pattern; telemetry.note_turn confirmed to already accept iteration_count + exit_reason via **kwargs.</done>
</task>

</tasks>

<reference_scaffold>

This block is referenced by Task 2a's `<read_first>` list. It is pseudocode
for the rewritten `_run_turn_exec` body — the executor reads this as
structural guidance, NOT as code to paste verbatim. The local-variable
names (`this_iter_plan`, `this_iter_usage`, `this_iter_stop`,
`accumulated_text_buffer`, `all_iter_records`, `iteration_index`,
`exit_reason`, `final_plan`, `total_cost_usd`, `total_prompt_tokens`,
`total_completion_tokens`, `tool_results_for_iter`) are locked. The
control-flow structure (ContextScope async-with around the while-loop,
done-branch returns or breaks, non-terminating-branch appends to
all_iter_records and increments iteration_index) is locked. Telemetry
event names (`iteration.start`, `iteration.end`, `provider.response`,
`plan.parsed`) are locked. Constants HALTED_MAX_ITER_FINAL and
HALTED_BUDGET_FINAL come from Task 1.

```python
# Pseudocode — NOT for verbatim paste. Read for control-flow; adapt
# to the existing file's imports and surrounding context.

max_iterations: int = get_config().max_iterations  # T1-04 added this field
iteration_index: int = 0
exit_reason: str | None = None
final_plan: Plan | None = None
total_cost_usd: float = 0.0
total_prompt_tokens: int = 0
total_completion_tokens: int = 0
all_iter_records: list[IterationRecord] = []
this_iter_plan: Plan | None = None
this_iter_usage = None

sys_prompt = "\n\n".join(
    s for s in (voss_md_block, cognition_text, prior_context_text,
                _compose_loop_system(max_iterations)) if s
)

async with ContextScope(token_budget=token_budget, model=model,
                         provider=provider) as ctx:
    while iteration_index < max_iterations:
        iter_rec = rec.begin_iteration()
        telemetry.emit("iteration.start", "info", data={
            "iteration_index": iteration_index,
            "max_iterations": max_iterations,
        })

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

        renderer.show_thinking(f"planning iter {iteration_index + 1}/{max_iterations}")
        iter_t0 = time.monotonic()
        this_iter_plan = None
        this_iter_usage = None
        this_iter_stop = "end_turn"
        accumulated_text_buffer: list[str] = []

        async for event in provider.stream(
            messages=messages,
            model=model,
            response_format=Plan,
            temperature=0.2,
            max_tokens=cfg.max_output_tokens,
        ):
            if isinstance(event, TextDelta):
                accumulated_text_buffer.append(event.text)
                renderer.stream_delta(event.text)
            elif isinstance(event, ParsedPlan):
                this_iter_plan = event.plan
            elif isinstance(event, Usage):
                this_iter_usage = event
            elif isinstance(event, Done):
                this_iter_stop = event.stop_reason

        renderer.finalize_stream(
            role="assistant",
            confidence=(this_iter_plan.confidence if this_iter_plan else None),
            cost_usd=(this_iter_usage.cost_usd if this_iter_usage else 0.0),
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        if this_iter_plan is None:
            final_text = "".join(accumulated_text_buffer)[:1000] or "(provider returned no parsed plan)"
            this_iter_plan = Plan(rationale="(unparsed)", steps=[], confidence=0.0, final_when_done=final_text)

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

        if _is_done_plan(this_iter_plan):
            # Confidence gate fires HERE only (terminating iter):
            if this_iter_plan.confidence < confidence_threshold:
                question = this_iter_plan.open_question or "I'm not confident enough — can you clarify the task?"
                renderer.show_clarify(question, this_iter_plan.confidence)
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
                telemetry.note_turn(
                    cost_usd=total_cost_usd + (this_iter_usage.cost_usd if this_iter_usage else 0.0),
                    outcome="clarify",
                    confidence=this_iter_plan.confidence,
                    iteration_count=iteration_index + 1,
                    exit_reason="done",
                )
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
                "exit_reason": "done",
            })
            if this_iter_usage:
                total_cost_usd += this_iter_usage.cost_usd
                total_prompt_tokens += this_iter_usage.prompt_tokens
                total_completion_tokens += this_iter_usage.completion_tokens
            all_iter_records.append(rec._iterations[-1])
            break

        # Non-terminating: execute steps then loop.
        results = await _run_step_loop(
            this_iter_plan.steps, tools, permissions, renderer, recorder=rec,
        )
        tool_results_for_iter = [
            {"name": s.name,
             "args": telemetry.redact_tool_args(dict(s.args)),
             "result": r[:4096]}
            for s, r in zip(this_iter_plan.steps, results)
        ]
        rec.end_iteration(
            plan=this_iter_plan,
            tool_results=tool_results_for_iter,
            cost_usd=this_iter_usage.cost_usd if this_iter_usage else 0.0,
            prompt_tokens=this_iter_usage.prompt_tokens if this_iter_usage else 0,
            completion_tokens=this_iter_usage.completion_tokens if this_iter_usage else 0,
            exit_reason=None,
        )
        telemetry.emit("iteration.end", "info", data={
            "iteration_index": iteration_index,
            "exit_reason": None,
        })
        if this_iter_usage:
            total_cost_usd += this_iter_usage.cost_usd
            total_prompt_tokens += this_iter_usage.prompt_tokens
            total_completion_tokens += this_iter_usage.completion_tokens
        all_iter_records.append(rec._iterations[-1])

        if getattr(ctx, "exhausted", False):
            exit_reason = "budget"
            break

        iteration_index += 1
    # End while

    if exit_reason is None:
        exit_reason = "max-iter"
# End ContextScope async-with

# Build final string per exit_reason:
if exit_reason == "done":
    final = final_plan.final_when_done or "(no final answer)"
elif exit_reason == "max-iter":
    final = HALTED_MAX_ITER_FINAL  # exact "halted: max-iter"
    final_plan = final_plan or (all_iter_records[-1].plan if all_iter_records else None)
elif exit_reason == "budget":
    final = HALTED_BUDGET_FINAL
    final_plan = final_plan or (all_iter_records[-1].plan if all_iter_records else None)

# Closing record_run + finalize (UNCHANGED structurally from pre-T1):
transcript = _compose_run_transcript(task, final_plan if isinstance(final_plan, Plan) else this_iter_plan,
                                      [r["result"] for r in (all_iter_records[-1].tool_results if all_iter_records else [])],
                                      rec)
semantics = await _record_run_call(provider, model, transcript)
if semantics is not None:
    rec.absorb(semantics, final_plan if isinstance(final_plan, Plan) else this_iter_plan)
else:
    rec.goal = "(record_run failed)"
    rec.plan = (final_plan.model_dump() if isinstance(final_plan, Plan)
                else (this_iter_plan.model_dump() if this_iter_plan else {}))

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

End of reference_scaffold.
</reference_scaffold>

<verification>
- `uv run pytest tests/harness/test_agent_loop.py tests/harness/test_agent_loop_helpers.py tests/harness/test_renderer_streaming.py -x -q` passes
- `grep -rn "_substitute_placeholders" voss/` returns ZERO matches
- `grep -F 'halted: max-iter' voss/harness/agent.py` >= 1 match
- `uv run pytest tests/harness/ -k "agent or recorder or session or provider_stream or turn_view or render or renderer or tui" -x -q` passes
- Telemetry JSONL spy from test fixture asserts: 3-iter run -> exactly 3 iteration.end events with iteration_index 0, 1, 2
- `grep -cE "def stream_delta|def finalize_stream" voss/harness/render.py` >= 8
- `grep -cE "def stream_delta|def finalize_stream" voss/harness/tui/renderer.py` == 2
</verification>

<success_criteria>
- _run_turn_exec is a while-loop that reaches all three non-interrupt exit_reasons (done / max-iter / budget) via dedicated test fixtures
- Iteration N+1 receives a serialized assistant+user pair for iteration N's plan and tool_results (ITER-02 acceptance)
- _substitute_placeholders is fully deleted from voss/ (SPEC ITER-02 acceptance)
- Hit-cap final string contains exact substring "halted: max-iter" (SPEC quantitative + exact-string criterion)
- Confidence gate moved to terminating-iteration-only (ITER-05 acceptance both fixtures)
- Telemetry emits iteration.start/iteration.end per iter with 0-based monotonic iteration_index; note_turn carries iteration_count + exit_reason (ITER-06 acceptance) — note_turn signature unchanged (already **kwargs)
- Renderer Protocol + all four concrete renderers expose stream_delta + finalize_stream
- TurnView delta render path live end-to-end (TextualRenderer.stream_delta -> TurnView.stream_delta via _safe)
</success_criteria>

<output>
Create `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-05-SUMMARY.md` when done with: line-count delta on agent.py + render.py + tui/renderer.py, list of removed call sites of _substitute_placeholders (should be exactly one — the in-function call on line 468 of the old impl), exact PLAN_LOOP_SYSTEM final text shipped, the messages-replay format chosen (assistant+user pair per prior iter), and confirmation that telemetry.note_turn was NOT modified (already accepts **kwargs).
</output>
