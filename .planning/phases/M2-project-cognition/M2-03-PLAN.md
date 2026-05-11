---
phase: M2
plan: 03
type: execute
wave: 2
depends_on: [M1, M2-00, M2-01, M2-02]
files_modified:
  - voss/harness/agent.py
  - voss/harness/tools.py
  - voss/harness/recorder.py
  - voss/harness/cli.py
  - tests/harness/test_agent_integration.py
  - tests/harness/test_recorder.py
  - tests/harness/test_cognition.py
autonomous: true
requirements:
  - COG-06
  - COG-08
tags:
  - harness
  - agent
  - recorder
  - decisions

must_haves:
  truths:
    - "run_turn integrates RunRecorder: observe() is called after every tool step (5 dispatch branches); finalize() runs at turn end and the resulting RunRecord is appended to record.runs as a dict."
    - "After a successful turn (confidence above threshold), the harness dispatches a privileged record_run LLM call producing a RunSemantics object; semantic fields populate via RunRecorder.absorb."
    - "If the privileged call fails (exception or resp.parsed is None), the RunRecord persists with mechanical-only data and goal='(record_run failed)' — the turn never crashes."
    - "When the RunRecord has at least one decision, the harness writes one `.voss/decisions/YYYY-MM-DD-<slug>.md` per decision with required frontmatter; collisions append `-2, -3` via reserve_filename."
    - "tools.py registers a `record_run` ToolDescriptor for symmetry but it is dispatched by the harness, never present in plan.steps."
  artifacts:
    - path: "voss/harness/agent.py"
      provides: "RunSemantics pydantic model; _record_run_call helper; RunRecorder integration in run_turn; TurnResult.run field; decisions write hook"
      contains: "class RunSemantics"
    - path: "voss/harness/tools.py"
      provides: "record_run tool descriptor (privileged, is_mutating=True)"
      contains: "record_run"
    - path: "voss/harness/recorder.py"
      provides: "absorb() now copies semantic fields and write_decisions_md(cwd, run, session_id) helper"
      contains: "def write_decisions_md"
    - path: "tests/harness/test_agent_integration.py"
      provides: "FakeProviderWithSemantics + 2 integration tests for record_run path + 1 cognition-injection placeholder"
      contains: "class FakeProviderWithSemantics"
    - path: "tests/harness/test_recorder.py"
      provides: "test_decisions_mirror_to_markdown unskipped"
      contains: "def test_decisions_mirror_to_markdown"
    - path: "tests/harness/test_cognition.py"
      provides: "test_decision_frontmatter unskipped"
      contains: "def test_decision_frontmatter"
  key_links:
    - from: "voss/harness/agent.py::run_turn"
      to: "voss/harness/recorder.py::RunRecorder"
      via: "rec = RunRecorder.start(); rec.observe(...) in 5 branches; rec.finalize(cwd, cost)"
      pattern: "rec\\.observe\\|rec\\.finalize"
    - from: "voss/harness/agent.py::_record_run_call"
      to: "provider.complete"
      via: "second LLM call with response_format=RunSemantics, temperature=0.0, max_tokens=800"
      pattern: "RunSemantics"
    - from: "voss/harness/agent.py::run_turn"
      to: ".voss/decisions/*.md"
      via: "write_decisions_md(cwd, run, session_id) after rec.finalize when run.decisions non-empty"
      pattern: "write_decisions_md\\|\\.voss/decisions"
---

<objective>
Wire `RunRecorder` into `agent.py:run_turn` (mechanical observation at every tool branch), add the privileged closing `record_run` LLM call that populates semantic fields (D-15, RESEARCH Pattern 4), and ship the `decisions/*.md` mirror per D-08. Also register the `record_run` tool descriptor for symmetry (M1-05 is_mutating=True).

Purpose: M2-02 shipped RunRecord + RunRecorder mechanical capture in isolation. This plan wires them into the agent's turn lifecycle and closes the COG-08 contract by adding the semantic half. The decisions mirror lands here because it is the post-turn side-effect that consumes RunRecord.decisions. After this plan, every successful agent turn produces a full RunRecord persisted into the session JSON and writes any decisions to `.voss/decisions/`.

Output:
- `voss/harness/agent.py` — RunSemantics pydantic model; `_compose_run_transcript(...)` helper; `_record_run_call(provider, model, transcript) -> RunSemantics | None`; integration into `run_turn`; new `TurnResult.run: RunRecord | None`; decisions mirror call site.
- `voss/harness/tools.py` — `record_run` tool descriptor (privileged, never appears in plan.steps, `is_mutating=True`).
- `voss/harness/recorder.py` — `absorb()` fully wired; new `write_decisions_md(cwd, run: RunRecord, session_id: str) -> list[Path]` helper.
- `_run_repl` in cli.py persists `result.run` into `record.runs` and calls the session save path each turn (small integration tweak).
- 2 new integration tests + 2 unskipped tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M2-project-cognition/M2-CONTEXT.md
@.planning/phases/M2-project-cognition/M2-RESEARCH.md
@.planning/phases/M2-project-cognition/M2-PATTERNS.md
@voss/harness/agent.py
@voss/harness/tools.py
@voss/harness/recorder.py
@voss/harness/session.py
@voss/harness/cognition.py
@tests/harness/test_agent_integration.py

<interfaces>
From voss/harness/agent.py (current run_turn shape, lines 100-231 — five tool-dispatch branches that need rec.observe insertions):
    Branch A — unknown tool: results.append(f"<error: unknown tool {step.name!r}>"); show_tool_call(...,"error"); continue
    Branch B — denied:        text = f"<denied: {why}>"; ...; results.append(text); continue
    Branch C — exception:     text = f"<error: {e}>"; ...; results.append(text); continue
    Branch D — ok:            results.append(text); show_tool_call(...,"ok")
    (Branch B/C/D each get rec.observe(name, args, text, ok=False/False/True).)
    Branch A: ok=False, error text.

From voss/harness/recorder.py (M2-02):
    RunRecorder.start() -> RunRecorder
    RunRecorder.observe(tool_name, args, result, ok)
    RunRecorder.absorb(semantics, plan)  # stub from M2-02 — this plan fills it in
    RunRecorder.finalize(cwd, cost_usd) -> RunRecord

From voss/harness/session.py (M2-02):
    RunRecord dataclass with 16 fields incl. decisions: list[dict]
    SessionRecord.runs: list[dict] = field(default_factory=list)

From voss/harness/cognition.py (M2-01):
    slug(title: str) -> str
    reserve_filename(dir_: Path, base: str, ext: str=".md") -> Path
    voss_dir(cwd) -> Path  # returns cwd/.voss

From tests/harness/test_agent_integration.py (existing FakeProvider):
    class FakeProvider:
        def __init__(self, plan: Plan, cost: float = 0.001): ...
        async def complete(self, *, messages, model, response_format=None, **kw) -> ProviderResponse: ...
            # returns ProviderResponse(parsed=self.plan if response_format is Plan else None, ...)

Pydantic v2 BaseModel signature for RunSemantics (RESEARCH Pattern 4):
    class RunSemantics(BaseModel):
        goal: str
        avoided: list[dict] = []
        assumptions: list[str] = []
        decisions: list[dict] = []
        risks: list[str] = []
        follow_ups: list[str] = []

Frontmatter shape for decisions/*.md (D-08):
    ---
    id: YYYY-MM-DD-<slug>
    status: active
    related_session: <session_id>
    confidence: <0..1 float>
    created_at: <ISO timestamp>
    ---
    # <title>

    <body>
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1a: Wire RunRecorder into run_turn (mechanical observe hooks + recorder.absorb fill-in)</name>
  <files>voss/harness/agent.py, voss/harness/recorder.py</files>
  <read_first>
    - voss/harness/agent.py (entire file — focus on lines 100-231 run_turn body, 82-88 TurnResult)
    - voss/harness/recorder.py (M2-02 just-shipped — absorb() needs filling in)
    - voss/harness/session.py (M2-02) — RunRecord dataclass for finalize return type
    - .planning/phases/M2-project-cognition/M2-RESEARCH.md (§Pattern 3 — RunRecorder absorb shape; §Pitfall 1 — failure mode handling)
    - .planning/phases/M2-project-cognition/M2-PATTERNS.md (§voss/harness/agent.py MODIFIED — 5 insertion points)
  </read_first>
  <behavior>
    - test_run_turn_finalizes_recorder: with a plain FakeProvider (no semantics call yet — Task 1b adds the privileged call), run_turn returns TurnResult.run with run.inspected populated from any fs_read step and run.changed populated from any fs_write step. run.goal == "" and run.decisions == [] (semantic fields untouched in 1a — Task 1b populates them).
    - test_observe_called_per_branch (recorder-side; lives in test_recorder.py as a small unit): manually construct a RunRecorder; call observe with each of (unknown, denied, exception, success) — asserts absorb is a no-op when invoked with semantics=None.
    - test_recorder_absorb_copies_semantic_fields: build a stub object with goal/avoided/assumptions/decisions/risks/follow_ups; call rec.absorb(stub, plan=None); assert all six fields copied verbatim onto rec.
    - (Pre-existing tests must stay green; cognition=None default means M1-style turns unchanged.)
  </behavior>
  <action>
    1. Edit voss/harness/recorder.py: implement `absorb(semantics, plan)` per RESEARCH Pattern 3 — copy each of (goal, avoided, assumptions, decisions, risks, follow_ups) from semantics onto self; if plan is not None set self.plan = plan.model_dump() (pydantic v2 dump). Tolerate semantics being a duck-typed object (use getattr with defaults so the stub-tests in 1b can pass a SimpleNamespace).
    2. Edit voss/harness/agent.py.
    3. Add at the top imports: `from .recorder import RunRecorder`; `from .session import RunRecord`. (`write_decisions_md` import is added in 1b.)
    4. Modify TurnResult dataclass: add `run: RunRecord | None = None` as the last field. Default None preserves existing callers.
    5. Modify run_turn signature: add keyword arg `session_id: str | None = None` (used by decisions writes in 1b). Add `cognition=None` as well (placeholder for M2-05; M2-03 must accept but not act on it). Both default None so all existing callers keep working.
    6. Inside run_turn, immediately before `renderer.show_thinking("planning")`, instantiate `rec = RunRecorder.start()`.
    7. In each of the 4 tool-dispatch branches in the for-loop (lines ~185-207), add a single `rec.observe(step.name, step.args, <result-or-error-text>, ok=<True|False>)` call after the existing show_tool_call:
        - unknown tool: rec.observe(step.name, step.args, "<unknown tool>", ok=False)
        - denied: rec.observe(step.name, step.args, text, ok=False)
        - exception: rec.observe(step.name, step.args, text, ok=False)
        - success: rec.observe(step.name, step.args, text, ok=True)
        (The "running…" pending state is not observed.)
    8. After the for-loop, before computing `final`, call `run = rec.finalize(cwd, cost_usd=resp.cost_usd)`. In 1a there is NO privileged record_run call yet — semantic fields stay at their defaults. (1b inserts the absorb step ahead of finalize.)
    9. On the confidence-clarify early-return path, return TurnResult with `run=None` (RESEARCH spec: "skip on confidence-clarify exit"). On the normal terminal path, return TurnResult with `run=run`.
    10. In tests/harness/test_recorder.py: add `test_recorder_absorb_copies_semantic_fields` (1a-owned; the existing Wave-1 mechanical-observe tests already shipped in M2-02 so don't re-add). Leave `test_decisions_mirror_to_markdown` skipped — 1b owns it.
  </action>
  <verify>
    <automated>pytest tests/harness/test_recorder.py tests/harness/test_agent_integration.py tests/harness/test_session_redaction.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "rec\.observe" voss/harness/agent.py` returns at least 4 (one per dispatch branch).
    - `grep -c "rec\.finalize" voss/harness/agent.py` returns at least 1.
    - `grep -c "def absorb" voss/harness/recorder.py` returns 1; body copies the six semantic fields (verified by test_recorder_absorb_copies_semantic_fields).
    - `grep -c "session_id\|cognition" voss/harness/agent.py` returns at least 2 (signature kwargs present even though unused in 1a).
    - `pytest tests/harness/test_recorder.py -v` exits 0 with `test_recorder_absorb_copies_semantic_fields` passing alongside the M2-02 Wave-1 tests.
    - `pytest tests/harness/test_agent_integration.py -v` exits 0 with no regression (existing tests still green; 1b adds the semantics tests).
    - Behavior: every successful turn now returns TurnResult.run != None; on confidence-clarify, run is None.
  </acceptance_criteria>
  <done>RunRecorder is instantiated and observes every tool branch; rec.finalize runs at turn end and TurnResult.run carries mechanical-only data. absorb() is wired but not yet called.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 1b: Add RunSemantics + privileged record_run dispatch + decisions/*.md mirror + cli.py persistence</name>
  <files>voss/harness/agent.py, voss/harness/tools.py, voss/harness/recorder.py, voss/harness/cli.py</files>
  <read_first>
    - voss/harness/agent.py (just-modified by 1a — RunRecorder is already wired; this task adds the semantic dispatch + decisions write)
    - voss/harness/tools.py (lines 1-170; specifically the @tool decorator pattern around fs_write at lines 60-65 and the dict-returning factory at 139-149)
    - voss/harness/recorder.py (just-modified by 1a — absorb() is filled in; this task adds write_decisions_md)
    - voss/harness/cognition.py (M2-01) — slug() + reserve_filename() to import for decisions writes
    - voss/harness/cli.py (lines 280-320 _run_repl — the asyncio.run(run_turn(...)) call site to add session_id= kwarg + record.runs.append)
    - .planning/phases/M2-project-cognition/M2-RESEARCH.md (§Pattern 4 — privileged record_run dispatch; §Pitfall 1 — failure mode handling)
    - .planning/phases/M2-project-cognition/M2-PATTERNS.md (§tools.py MODIFIED — record_run descriptor shape)
  </read_first>
  <behavior>
    - test_record_run_populates_semantic_fields: FakeProviderWithSemantics returns plan + RunSemantics(goal="summarize", decisions=[{"title":"chose X","body":"because Y","confidence":0.9}]); run_turn returns TurnResult.run with run.goal=="summarize" and run.decisions[0]["title"]=="chose X". (Test body lives in Task 2.)
    - test_record_run_failure_persists_mechanical: FakeProviderFailingSemantics raises on the second complete() call OR returns parsed=None; run_turn still returns TurnResult.run with run.goal=="(record_run failed)" and run.inspected/changed populated from any tool steps that ran. (Test body lives in Task 2.)
    - test_decisions_mirror_to_markdown (in test_recorder.py): build a RunRecord with decisions=[{"title":"choose pydantic","body":"strict over advisory","confidence":0.85}]; write_decisions_md(tmp_path, run, session_id="abc123") writes exactly one file tmp_path/.voss/decisions/YYYY-MM-DD-choose-pydantic.md with the 5 required frontmatter keys.
    - test_decision_frontmatter (in test_cognition.py): given a written decisions/*.md file, parse its frontmatter and assert keys exactly include {id, status, related_session, confidence, created_at}; status == "active"; related_session == "abc123"; 0 <= confidence <= 1.
    - test_cli_persists_run_to_session: stub-provider end-to-end through one /turn in _run_repl; after the turn, record.runs has exactly one entry whose top-level keys equal the 16 RunRecord fields.
  </behavior>
  <action>
    1. Edit voss/harness/agent.py.
    2. Update the import added in 1a to also pull in write_decisions_md: `from .recorder import RunRecorder, write_decisions_md`.
    3. Define `class RunSemantics(BaseModel)` immediately after `class Plan` definition (line ~56). Fields: goal (str), avoided (list[dict] = []), assumptions (list[str] = []), decisions (list[dict] = []), risks (list[str] = []), follow_ups (list[str] = []). Use `model_config = {"extra": "ignore"}` (lenient — LLM output may include extras).
    4. Define module-level constant `RECORD_RUN_SYSTEM` per RESEARCH Pattern 4 prose ("You are closing out an agent turn. Summarize it as a RunSemantics object. ...").
    5. Helper `_compose_run_transcript(task, plan, results, rec) -> str` builds a short text block: original task, plan rationale, each step name+args+truncated_result (≤200 chars/step), mechanical observations summary ("inspected: a, b; changed: c"). Cap total at ~3000 chars to keep the closing call cheap.
    6. Helper `async def _record_run_call(provider, model, transcript) -> RunSemantics | None`:
       ```
       try:
           resp = await provider.complete(
               messages=[{"role":"system","content":RECORD_RUN_SYSTEM},
                         {"role":"user","content":transcript}],
               model=model, response_format=RunSemantics,
               temperature=0.0, max_tokens=800,
           )
       except Exception:
           return None
       if resp.parsed is None: return None
       return resp.parsed
       ```
    7. In run_turn, insert the privileged close call between the for-loop end and the 1a-installed `rec.finalize(...)`:
       ```
       transcript = _compose_run_transcript(task, plan, results, rec)
       semantics = await _record_run_call(provider, model, transcript)
       if semantics is not None:
           rec.absorb(semantics, plan)
       else:
           rec.goal = "(record_run failed)"
           rec.plan = plan.model_dump()
       ```
       Then call the existing `run = rec.finalize(cwd, cost_usd=resp.cost_usd)` from 1a. (Confidence-clarify early-return still skips this block; run stays None on that path.)
    8. After rec.finalize: if `run.decisions` is non-empty, call `write_decisions_md(cwd, run, session_id or "(no-session)")`. Wrap in try/except OSError; on failure call `click.echo(f"warning: failed to mirror decisions: {exc}", err=True)`. Do NOT call renderer.show_warning — added cleanly in M2-05 (W9).
    9. Add `write_decisions_md(cwd, run, session_id) -> list[Path]` to voss/harness/recorder.py:
        - If not run.decisions: return [].
        - decisions_dir = cwd / ".voss" / "decisions"
        - decisions_dir.mkdir(parents=True, exist_ok=True)
        - paths = []
        - For each d in run.decisions:
            - title = d.get("title") or "untitled"
            - body = d.get("body", "")
            - conf = float(d.get("confidence", 0.0))
            - from voss.harness.cognition import slug, reserve_filename
            - path = reserve_filename(decisions_dir, slug(title))
            - id_str = path.stem  # YYYY-MM-DD-slug
            - created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            - content = (
                "---
"
                f"id: {id_str}
"
                "status: active
"
                f"related_session: {session_id}
"
                f"confidence: {conf:.2f}
"
                f"created_at: {created_at}
"
                "---

"
                f"# {title}

"
                f"{body}
"
              )
            - path.write_text(content)
            - paths.append(path)
        - return paths
    10. Edit voss/harness/tools.py: in make_toolset, add a `record_run` tool. Use the @tool decorator. name="record_run", description="(privileged) Close the current turn with semantic fields. Dispatched by the harness; never include in plan steps." Parameters mirror RunSemantics fields. Body returns "ok" — it's a stub; the actual semantics come from the privileged provider.complete call in agent.py. Add to the returned dict. M1-05 introduces `is_mutating: bool` on ToolDescriptor (CONTEXT.md A4 / PATTERNS.md ASSUMPTION) — if `is_mutating` exists on the descriptor by the time M2 runs, set it True on record_run. If `is_mutating` field is not yet present in voss_runtime.tools.ToolDescriptor when this plan executes, file a one-line note in M2-03-SUMMARY.md flagging that M1-05 must land first and the field must be wired in a follow-up; do NOT block on this — the tool descriptor still works without it.
    11. Update voss/harness/cli.py _run_repl: after `result = asyncio.run(run_turn(...))` (line ~318), if `result.run is not None` append `asdict(result.run)` (using dataclasses.asdict) to `record.runs` so the next /save persists it. Add `from dataclasses import asdict` and `from voss.harness.session import RunRecord` if not present. Pass `session_id=record.id` into the run_turn call.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_agent_integration.py tests/harness/test_recorder.py tests/harness/test_session_redaction.py tests/harness/test_cli.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^class RunSemantics" voss/harness/agent.py` returns 1.
    - `grep -c "_record_run_call" voss/harness/agent.py` returns at least 2 (definition + call site).
    - `grep -c "record_run" voss/harness/tools.py` returns at least 2 (descriptor name + key in returned dict).
    - `grep -c "def write_decisions_md" voss/harness/recorder.py` returns 1.
    - `grep -v '^#' voss/harness/cli.py | grep -c "record\.runs\.append"` returns at least 1 (per-turn persistence wired; comments excluded per self-invalidating-grep-gate rule).
    - `grep -v '^#' voss/harness/cli.py | grep -c "session_id=record\.id\|session_id=record_id"` returns at least 1.
    - `pytest tests/harness/test_recorder.py::test_decisions_mirror_to_markdown -v` exits 0.
    - `pytest tests/harness/test_cognition.py::test_decision_frontmatter -v` exits 0.
    - `pytest tests/harness/test_agent_integration.py -v` exits 0 with the 2 new tests from Task 2 passing (test_record_run_populates_semantic_fields, test_record_run_failure_persists_mechanical).
    - `pytest tests/harness/test_session_redaction.py -v` exits 0 (no regression: extended redaction test still passes after RunRecord.decisions starts carrying agent-authored content).
    - Behavior: TurnResult.run.goal is the agent-reported goal on success; "(record_run failed)" on closing-call failure.
  </acceptance_criteria>
  <done>RunSemantics + privileged record_run dispatch + decisions/*.md mirror + cli.py persistence all wired; record_run tool descriptor exists; turn never crashes on closing-call failure.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend FakeProvider for record_run tests + unskip test_decision_frontmatter + assert decisions in session JSON</name>
  <files>tests/harness/test_agent_integration.py, tests/harness/test_cognition.py</files>
  <read_first>
    - tests/harness/test_agent_integration.py (entire file — FakeProvider lines 21-53; existing test_turn_runs_simple_plan and friends)
    - voss/harness/agent.py (just-modified: RunSemantics + run_turn integration)
    - voss/harness/recorder.py (just-modified: write_decisions_md)
    - .planning/phases/M2-project-cognition/M2-PATTERNS.md (§tests/harness/test_agent_integration.py EXTENDED — FakeProviderWithSemantics shape)
  </read_first>
  <behavior>
    - FakeProviderWithSemantics returns Plan on the first complete() call (response_format=Plan) and RunSemantics on the second (response_format=RunSemantics). Tracks call_count.
    - test_record_run_populates_semantic_fields: build a Plan with one fs_read step + a RunSemantics with goal="summarize repo" and one decision; run_turn(...); assert result.run.goal=="summarize repo", result.run.decisions[0]["title"] is set.
    - test_record_run_failure_persists_mechanical: FakeProviderFailingSemantics returns Plan first, then raises on the second call (or returns ProviderResponse with parsed=None); run_turn completes; result.run.goal=="(record_run failed)"; result.run.inspected contains the file the plan read.
    - (Optional sanity) test_decisions_written_to_disk: same as test_record_run_populates_semantic_fields but additionally asserts at least one file appears under <cwd>/.voss/decisions/ matching `*-summarize-repo*.md` OR the decision's slug; frontmatter contains related_session matching the session id passed in.
    - test_decision_frontmatter (in test_cognition.py): call write_decisions_md directly with a synthetic RunRecord + session_id; parse the resulting file's frontmatter via yaml.safe_load on the block between `---` lines; assert keys = {id, status, related_session, confidence, created_at}; status == "active"; related_session == "abc123"; 0 <= confidence <= 1.
  </behavior>
  <action>
    1. Add `class FakeProviderWithSemantics(FakeProvider)` per M2-PATTERNS.md verbatim shape — overrides `complete` to return parsed=RunSemantics when response_format is RunSemantics, otherwise delegates to super().
    2. Add `class FakeProviderFailingSemantics(FakeProvider)` — first call returns the plan; second call raises RuntimeError or returns parsed=None.
    3. Add `test_record_run_populates_semantic_fields` and `test_record_run_failure_persists_mechanical` per <behavior>.
    4. Optionally add `test_decisions_written_to_disk` if it makes test_decisions_mirror_to_markdown's contract clearer in an end-to-end setting (skip if already covered by the recorder-side test).
    5. In tests/harness/test_cognition.py: remove the @pytest.mark.skip on `test_decision_frontmatter`. Implement: build a RunRecord with decisions=[{"title":"choose X","body":"because Y","confidence":0.85}]; call write_decisions_md(tmp_path, run, session_id="abc123"); read the resulting file; split frontmatter via the FRONTMATTER_RE pattern (or just slice between `---` markers); yaml.safe_load it; assert the 5 keys are present and have the right shapes.
    6. The cognition-injection placeholder test (`test_turn_injects_cognition`) stays skipped or is added as a placeholder in test_agent_integration.py with `@pytest.mark.skip(reason="Wave 3 M2-05 wires cognition injection")`. Do NOT implement it here.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_agent_integration.py tests/harness/test_cognition.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "class FakeProviderWithSemantics\\|class FakeProviderFailingSemantics" tests/harness/test_agent_integration.py` returns at least 2.
    - `grep -c "def test_record_run_populates_semantic_fields\\|def test_record_run_failure_persists_mechanical" tests/harness/test_agent_integration.py` returns 2.
    - `pytest tests/harness/test_agent_integration.py -v` exits 0 with the 2 new tests passing and pre-existing tests still green.
    - `pytest tests/harness/test_cognition.py::test_decision_frontmatter -v` exits 0.
    - `pytest tests/harness/test_cognition.py -v` reports the previously-passing 8 plus this 1 = 9 passing tests (Wave-2/3/4 stubs still skipped).
  </acceptance_criteria>
  <done>Two integration tests prove the record_run path (success + failure); decision frontmatter test locks the COG-06 file format.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/ -x` exits 0; record_run integration tests pass, redaction CI still green, decisions mirror exercised.
- Manual: `python -c "from voss.harness.agent import RunSemantics, run_turn; from voss.harness.recorder import RunRecorder, write_decisions_md"` succeeds.
- Manual: inspect a freshly-saved session JSON after running a stub-provider turn — confirm a `runs` array entry exists with both mechanical (inspected/changed) and semantic (goal/decisions) data.
</verification>

<success_criteria>
- COG-08 semantic half complete: every successful turn's RunRecord has agent-reported goal/decisions/risks/follow_ups OR the documented failure sentinel.
- COG-06 satisfied: when the agent reports a decision, a markdown mirror appears under `.voss/decisions/` with required frontmatter, addressable from anywhere via git.
- record_run privileged call is failure-tolerant (Pitfall 1) — turn never crashes due to closing-call provider errors.
- record_run tool descriptor exists for discovery symmetry; never present in plan.steps.
- Per-turn session.runs persistence is wired in _run_repl so /save (and the auto-save in M2-06) captures the new record shape.
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| provider.complete (semantics call) → RunRecord | second LLM call returns structured object that becomes persisted state |
| RunRecord.decisions[].body → disk | agent free-form prose lands in a committed markdown file |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M2-09 | Information Disclosure | decisions[].body contains user-pasted secret quoted back by the agent | accept | Acknowledged carve-out (M1 D-17 TestUserPromptsArePassthrough; M2-RESEARCH §Security Domain row 6). User-typed content is intentionally not redacted. Documented in session.py docstring already. |
| T-M2-10 | Denial of Service | privileged record_run provider call hangs / errors and crashes the turn | mitigate | try/except wraps the await; on failure returns None; rec.goal set to sentinel; turn completes (Pitfall 1). |
| T-M2-11 | Tampering | RunSemantics with extra fields (LLM hallucinates fields) breaks pydantic parsing | mitigate | `model_config = {"extra": "ignore"}` on RunSemantics (lenient — LLM output). Distinct from cognition_schemas which use forbid. |
| T-M2-12 | Tampering | malicious title in decisions[].title triggers path traversal via slug | mitigate | `slug()` (M2-01) strips non-alphanumeric to `-`; cannot produce `..` or `/`. reserve_filename joins to a fixed parent. |
</threat_model>

<output>
After completion, create `.planning/phases/M2-project-cognition/M2-03-SUMMARY.md` documenting: (1) the run_turn integration map (which line each rec.observe insertion happened at, before/after), (2) RunSemantics schema + the system prompt verbatim, (3) record_run failure-mode contract (when goal becomes "(record_run failed)"), (4) decisions/*.md frontmatter contract (the 5 required keys + status enum), (5) the M1-05 is_mutating follow-up flag if applicable.
</output>
