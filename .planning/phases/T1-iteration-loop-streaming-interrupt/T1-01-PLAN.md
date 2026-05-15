---
phase: T1-iteration-loop-streaming-interrupt
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/session.py
  - voss/harness/recorder.py
autonomous: true
requirements: [ITER-01, ITER-06]
must_haves:
  truths:
    - "RunRecord.iterations is a list[IterationRecord] defaulting to empty"
    - "Old pre-T1 RunRecord JSON parses cleanly through the new pydantic/dataclass shape"
    - "RunRecorder exposes begin_iteration/end_iteration that append a fully-populated IterationRecord on the active record"
    - "RunRecord.exit_reason is a string field constrained to one of done|max-iter|budget|interrupt"
    - "RunRecord.iteration_count is an int derived from len(iterations) on finalize"
  artifacts:
    - path: "voss/harness/session.py"
      provides: "IterationRecord dataclass + RunRecord.iterations + RunRecord.exit_reason + RunRecord.iteration_count"
      contains: "class IterationRecord"
    - path: "voss/harness/recorder.py"
      provides: "RunRecorder.begin_iteration / RunRecorder.end_iteration"
      contains: "def begin_iteration"
  key_links:
    - from: "voss/harness/recorder.py:RunRecorder.finalize"
      to: "voss/harness/session.py:RunRecord"
      via: "passes iterations + exit_reason + iteration_count to RunRecord constructor"
      pattern: "iterations=list\\("
---

<objective>
Land the additive-only schema substrate the iteration loop will write to. No
behavior change yet; this plan exists so T1-02..T1-06 have a concrete record
shape to populate.

Purpose: CONTEXT.md locks "additive Optional only — no schema_version bump"
and "voss resume behavior unchanged from v0.1." This plan delivers exactly
that: new fields default to empty/None so pre-T1 fixtures round-trip without
migration, and resume code paths keep reading top-level fields only.

Output: Updated `voss/harness/session.py` (IterationRecord + RunRecord
additive fields) and `voss/harness/recorder.py` (begin_iteration /
end_iteration API + finalize wiring), with regression test asserting old
fixtures still parse.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md
@voss/harness/session.py
@voss/harness/recorder.py
</context>

<interfaces>
Current `RunRecord` is a `@dataclass` in `voss/harness/session.py` (line 70-87).
Fields today: id, started_at, ended_at, goal, plan, inspected, changed,
avoided, assumptions, decisions, risks, validation, failures, diff_summary,
follow_ups, cost_usd.

Current `RunRecorder` is a `@dataclass` in `voss/harness/recorder.py` (line
27-119). `RunRecorder.finalize(cwd, cost_usd)` returns a `RunRecord`.

`_hydrate` in `session.py` filters unknown keys via `_SESSION_FIELDS`. Same
pattern must apply to RunRecord on read so old JSON loads.

Exit reason vocabulary (locked in SPEC ITER-06): exactly the four strings
`"done"`, `"max-iter"`, `"budget"`, `"interrupt"`. No others permitted.

IterationRecord shape from CONTEXT.md Iteration sub-record schema section:
index (int, 0-based), plan (dict — serialized Plan), tool_results
(list[ToolResult] — keep as list[dict] to match existing JSON shape used in
RunRecord.validation/failures), cost_usd (float), prompt_tokens (int),
completion_tokens (int), started_at (str — ISO8601, matches RunRecord
convention), ended_at (str — ISO8601), exit_reason (str | None — only set
on terminating iter).
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add IterationRecord + additive RunRecord fields</name>
  <files>voss/harness/session.py, tests/harness/test_session_iterations.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-06 acceptance criteria + lines 86-92 schema additive constraint)
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Iteration sub-record schema section, ~lines 47-65)
    - voss/harness/session.py (entire file — dataclass + _hydrate + _SESSION_FIELDS pattern)
    - voss/harness/recorder.py (lines 99-119, finalize signature + RunRecord construction)
    - tests/harness/test_session_redaction.py (so the new fields don't trip the credential-shape redaction guard)
  </read_first>
  <behavior>
    - IterationRecord(index=0, plan={}, tool_results=[], cost_usd=0.0,
      prompt_tokens=0, completion_tokens=0, started_at="2026-01-01T00:00:00+00:00",
      ended_at="2026-01-01T00:00:01+00:00", exit_reason=None) constructs without error
    - RunRecord(id="x", started_at="...", ended_at="...") still constructs
      with no positional kwargs — all new fields default
    - RunRecord(...).iterations == [] when not provided
    - RunRecord(...).iteration_count == 0 when not provided
    - RunRecord(...).exit_reason is None when not provided
    - dataclasses.asdict(record) on a record with one IterationRecord
      produces nested dict (not the dataclass instance) — JSON-safe
    - Old fixture parsing: given pre-T1 JSON dict missing the four new
      fields, RunRecord(**filtered) succeeds — defaults kick in
  </behavior>
  <action>
    Add a new `@dataclass` `IterationRecord` to `voss/harness/session.py`
    above the existing `RunRecord` declaration, with exactly these fields and
    defaults: index (int, no default — required), plan (dict, default_factory
    dict), tool_results (list[dict], default_factory list), cost_usd (float,
    default 0.0), prompt_tokens (int, default 0), completion_tokens (int,
    default 0), started_at (str, default ""), ended_at (str, default ""),
    exit_reason (Optional[str], default None).

    Add four additive Optional/default fields to the existing `RunRecord`
    dataclass (after `cost_usd` to preserve field-order compatibility for any
    positional callers — though scan shows all callers use kwargs):
      iterations: list[IterationRecord] = field(default_factory=list)
      iteration_count: int = 0
      exit_reason: Optional[str] = None
      iteration_total_prompt_tokens: int = 0
      iteration_total_completion_tokens: int = 0
    Do NOT bump any schema_version constant. Do NOT add `schema_version`.

    Add a module-level constant `EXIT_REASONS: frozenset[str] =
    frozenset({"done", "max-iter", "budget", "interrupt"})` and use it in
    a `__post_init__` on RunRecord that, when exit_reason is not None,
    asserts it is in EXIT_REASONS (raise ValueError otherwise). This is the
    enforcement point for SPEC ITER-06's "exit_reason ∈ {done,max-iter,
    budget,interrupt}" criterion. Do NOT add __post_init__ to IterationRecord
    — its exit_reason is also constrained but enforcement at the RunRecord
    level is sufficient (terminating-iter exit_reason mirrors RunRecord).

    Write the new test file `tests/harness/test_session_iterations.py`
    covering the six behavior bullets above plus one extra test:
    `test_runrecord_rejects_invalid_exit_reason` — calling
    `RunRecord(id="x", started_at="a", ended_at="b", exit_reason="quit")`
    raises ValueError mentioning the four valid values.

    Also add one regression test in the same file
    `test_runrecord_old_fixture_roundtrip`: build a dict matching a pre-T1
    RunRecord (id, started_at, ended_at, goal, plan, inspected, changed,
    cost_usd — no iterations/exit_reason keys), then pass through
    `RunRecord(**old_dict)` and assert iterations == [] and exit_reason is
    None and iteration_count == 0.

    Do NOT touch SessionRecord. Do NOT touch _hydrate. Do NOT touch any
    other field on RunRecord. Surgical add only.
  </behavior>
  <verify>
    <automated>uv run pytest tests/harness/test_session_iterations.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "^class IterationRecord\|@dataclass$" voss/harness/session.py` shows IterationRecord declared before RunRecord
    - source assertion: `grep -n "iterations:\s*list\[IterationRecord\]\|exit_reason:\s*Optional\[str\]" voss/harness/session.py` returns at least 2 matches
    - source assertion: `grep -c "EXIT_REASONS" voss/harness/session.py` >= 2 (constant + __post_init__ use)
    - behavior assertion: pytest collects and passes all tests in tests/harness/test_session_iterations.py
    - regression assertion: existing `uv run pytest tests/harness/test_session_redaction.py -x` still passes (new fields don't carry credentials)
    - test command: `uv run pytest tests/harness/test_session_iterations.py tests/harness/test_session_redaction.py -x -q`
    - CLI output: pytest exit code 0, all tests pass
  </acceptance_criteria>
  <done>IterationRecord dataclass exists; RunRecord has five new additive fields with safe defaults; EXIT_REASONS frozenset enforces vocabulary; old-fixture round-trip test passes; redaction test still passes.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire RunRecorder.begin_iteration / end_iteration</name>
  <files>voss/harness/recorder.py, tests/harness/test_recorder_iterations.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-06)
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Iteration sub-record schema + Recorder finalization on cancel, ~lines 67-79)
    - voss/harness/recorder.py (entire file)
    - voss/harness/session.py (after Task 1 — IterationRecord + RunRecord.iterations)
  </read_first>
  <behavior>
    - rec.begin_iteration() returns an IterationRecord-shaped object with
      index = len(rec._iterations) (0 for first call), started_at populated
      with current UTC ISO timestamp, ended_at empty string
    - Calling begin_iteration twice without end_iteration appends two
      records and the second one's index == 1
    - rec.end_iteration(plan=plan_obj, tool_results=[{"tool":"fs_read",...}],
      cost_usd=0.012, prompt_tokens=100, completion_tokens=50,
      exit_reason=None) populates the most recent open iteration's fields
      and sets ended_at to a non-empty ISO timestamp
    - After begin_iteration + end_iteration + finalize(cwd, cost_usd=0.012),
      the returned RunRecord.iterations has length 1 and
      RunRecord.iteration_count == 1
    - finalize accepts new kwargs `exit_reason: str` and propagates to
      RunRecord.exit_reason; it also accepts `iteration_total_prompt_tokens`
      and `iteration_total_completion_tokens` (defaulted from sum of
      self._iterations) so M5/M2 callers can read aggregated counts
    - finalize(..., exit_reason="quit") raises ValueError (delegated to
      RunRecord __post_init__)
  </behavior>
  <action>
    Add a private `_iterations: list[IterationRecord] = field(default_factory=list)`
    to the `RunRecorder` dataclass. Import IterationRecord from `.session`.

    Add method `begin_iteration(self) -> IterationRecord` that builds an
    IterationRecord with index=len(self._iterations), started_at=
    datetime.now(timezone.utc).isoformat(timespec="seconds"), other fields
    at their defaults, appends it to self._iterations, and returns it.

    Add method `end_iteration(self, *, plan, tool_results, cost_usd,
    prompt_tokens, completion_tokens, exit_reason=None) -> None` that
    locates the most recent record with empty ended_at and writes the
    provided fields onto it (serialize plan via plan.model_dump() if it
    has that attr; otherwise store as-is). Set ended_at to current UTC ISO
    timestamp. Validate exit_reason against EXIT_REASONS imported from
    session.py if not None — raise ValueError on mismatch.

    Extend `RunRecorder.finalize(cwd, cost_usd, *, exit_reason=None)`:
    after the existing cost/diff lines, sum prompt/completion tokens
    across self._iterations into two locals. Build RunRecord with the
    existing kwargs PLUS: iterations=list(self._iterations),
    iteration_count=len(self._iterations), exit_reason=exit_reason,
    iteration_total_prompt_tokens=&lt;sum&gt;,
    iteration_total_completion_tokens=&lt;sum&gt;. Preserve every other
    existing kwarg unchanged. Callers in agent.py that pass only
    (cwd, cost_usd=X) keep working because exit_reason defaults to None
    (which becomes RunRecord.exit_reason=None — pre-T1 records have no
    exit_reason so this matches the additive-Optional invariant).

    Write `tests/harness/test_recorder_iterations.py` covering all six
    behavior bullets. Use a tmp_path fixture for cwd. Use a minimal
    SimpleNamespace plan stub: `SimpleNamespace(model_dump=lambda:
    {"rationale":"r","steps":[],"confidence":0.9,"final_when_done":"f"})`.
    Do NOT call any provider. Do NOT depend on git.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_recorder_iterations.py tests/harness/test_session_iterations.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "def begin_iteration\|def end_iteration" voss/harness/recorder.py` returns exactly 2 matches
    - source assertion: `grep -n "exit_reason" voss/harness/recorder.py` >= 2 (finalize signature + RunRecord construction)
    - behavior assertion: all six pytest behaviors pass
    - regression assertion: existing `uv run pytest tests/harness/test_recorder*.py -x -q` (any existing recorder tests) still pass
    - test command: `uv run pytest tests/harness/test_recorder_iterations.py tests/harness/test_session_iterations.py -x -q && uv run pytest tests/harness/ -k "recorder or session_redaction" -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>RunRecorder gains begin_iteration/end_iteration; finalize forwards exit_reason + iteration aggregates to RunRecord; six behavior tests pass; existing recorder/redaction tests still pass.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/harness/test_session_iterations.py tests/harness/test_recorder_iterations.py -x -q` passes
- `uv run pytest tests/harness/test_session_redaction.py -x -q` still passes (no new credential-shaped fields)
- `grep -rn "_substitute_placeholders" voss/` count is unchanged (this plan does not touch it — T1-04 deletes it)
- Pre-existing M2/M9 recorder tests still pass
</verification>

<success_criteria>
- IterationRecord dataclass exists in session.py and is JSON-serializable via dataclasses.asdict
- RunRecord has five additive fields (iterations, iteration_count, exit_reason, iteration_total_prompt_tokens, iteration_total_completion_tokens), all with safe defaults
- EXIT_REASONS frozenset is the single source of truth for exit_reason vocabulary; RunRecord rejects other values
- RunRecorder.begin_iteration / end_iteration brackets one iteration's data; finalize forwards to RunRecord without breaking existing callers
- Pre-T1 RunRecord JSON round-trips cleanly (regression test passes)
</success_criteria>

<output>
Create `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-01-SUMMARY.md` when done with: files changed, IterationRecord field list, RunRecord new fields, the EXIT_REASONS frozenset definition, and any deviations from this plan.
</output>
