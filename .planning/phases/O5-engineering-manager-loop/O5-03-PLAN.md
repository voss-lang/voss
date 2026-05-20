---
phase: O5-engineering-manager-loop
plan: 03
type: tdd
wave: 3
depends_on:
  - O5-01
files_modified:
  - voss/harness/em/schema.py
  - voss/harness/em/llm.py
  - voss/harness/em/stub.py
  - voss/harness/em/__init__.py
  - tests/harness/em/test_em_schema.py
  - tests/harness/em/test_em_llm.py
  - tests/harness/em/test_em_stub.py
autonomous: true
requirements:
  - OEM-03
  - OEM-04
must_haves:
  truths:
    - "EMPlanResponse is a pydantic BaseModel with model_config=ConfigDict(extra='ignore') — LENIENT per L-01 / RESEARCH Q6"
    - "EMOp is a discriminated union: CreateTicketOp | DispatchCardOp | KillCardOp | RescopeCardOp | SetACOp | SetDoDOp | NoopOp"
    - "Every Op model has `op: Literal[...]` discriminator; pydantic v2 routes on this"
    - "em_plan(...) mirrors judge.judge_run shape: provider.complete(response_format=EMPlanResponse, temperature=0.0); on ParseError or parsed=None returns a Noop fallback (never raises)"
    - "DeterministicEMStub yields scripted EMPlanResponses; zero LLM calls; mirrors O3 DeterministicReviewerStub pattern"
    - "No live LLM call ever in tests — every test uses StubProvider or DeterministicEMStub"
    - "Schema descriptions never contain L2 vocab (model/cost/token/provider) in user-visible text"
  artifacts:
    - path: "voss/harness/em/schema.py"
      provides: "EMPlanResponse + 7 Op pydantic models"
      contains: "class EMPlanResponse"
    - path: "voss/harness/em/llm.py"
      provides: "em_plan(...) async function — provider.complete wrapper"
      contains: "async def em_plan"
    - path: "voss/harness/em/stub.py"
      provides: "DeterministicEMStub for tests"
      contains: "class DeterministicEMStub"
    - path: "tests/harness/em/test_em_schema.py"
      provides: "pydantic LENIENT-posture coverage + Op discrimination tests"
    - path: "tests/harness/em/test_em_llm.py"
      provides: "mocked-provider em_plan call-shape test + ParseError sentinel test"
    - path: "tests/harness/em/test_em_stub.py"
      provides: "DeterministicEMStub queue-based determinism coverage"
  key_links:
    - from: "voss/harness/em/llm.py"
      to: "voss/eval/judge.py"
      via: "structural mirror of judge_run (provider.complete + response_format + ParseError handling)"
      pattern: "provider\\.complete\\("
    - from: "voss/harness/em/stub.py"
      to: "voss/harness/em/schema.py"
      via: "scripted EMPlanResponse queue"
      pattern: "from \\.schema import"
---

<objective>
Land the EM LLM call surface: pydantic v2 LENIENT schema (`EMPlanResponse`
discriminated union of 7 Op models), the async `em_plan(...)` wrapper that
mirrors `voss/eval/judge.py:judge_run`, and the `DeterministicEMStub`
test responder that yields scripted EMPlanResponses with zero live provider
calls.

Purpose: The EM's structured output is a list of typed plan ops the harness
deterministically executes via EMBoardHandle (W2). LENIENT pydantic
(`extra="ignore"`) is the right posture per L-01: hallucinated extra fields
drop silently rather than crashing the loop. STRICT (`extra="forbid"`) is
reserved for harness config files (cognition_schemas.py) where unknowns are
true bugs.

W3 is parallelizable with W2 in principle (no W2 dependency in the schema /
LLM / stub modules themselves), but is scheduled after W2 here for execution
ordering since the W4 loop depends on BOTH. The wave number is 3 to make this
ordering explicit; the only true dependency is W1 (the data records the schema
ops reference by name).

Output: 3 new modules (schema.py + llm.py + stub.py), one __init__.py update,
3 test files covering schema discrimination + LLM call shape + stub
determinism.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/O5-engineering-manager-loop/O5-CONTEXT.md
@.planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md
@.planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md
@.planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md
@.planning/phases/O5-engineering-manager-loop/O5-01-SUMMARY.md
@voss/eval/judge.py
@voss/harness/cognition_schemas.py
@voss/harness/em/tickets.py
@voss/harness/em/errors.py

<interfaces>
<!-- The canonical structured-LLM precedent — MIRROR this -->

From voss/eval/judge.py (LIVE, full module):
```
class Verdict(BaseModel):
    model_config = ConfigDict(extra="ignore")  # LENIENT
    verdict: Literal["pass", "fail"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str

async def judge_run(*, provider, model, task_prompt, final, file_diff, rubric)
    -> tuple[Verdict | None, str]:
    try:
        resp = await provider.complete(
            messages=[...],
            model=model,
            response_format=Verdict,
            temperature=0.0,
        )
    except ParseError:
        return None, "skipped"
    if resp.parsed is None:
        return None, "skipped"
    return resp.parsed, resp.parsed.verdict
```

<!-- Counter-example — DO NOT mirror this posture for LLM output -->

From voss/harness/cognition_schemas.py (LIVE, header):
```
STRICT = {"extra": "forbid"}   # for config files; LLM output uses extra="ignore"
```

<!-- Provider surface -->

From voss_runtime/providers/base.py:
  ModelProvider Protocol: async complete(*, messages, model, response_format,
    temperature, max_tokens=None) -> ProviderResponse
  ProviderResponse dataclass: text, model, prompt_tokens, completion_tokens,
    cost_usd, raw, parsed (Optional[BaseModel])

From voss_runtime/providers/litellm_provider.py:
  ParseError (exception)

<!-- W1 records the schema references by string -->

From voss/harness/em/tickets.py (W1 GREEN):
  Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal frozen records.
  Note: these are dataclasses, NOT pydantic models — the schema Op models
  parallel them by hand (RESEARCH Q6 designs them as fresh pydantic types
  with the discriminator op: Literal[...]).
</interfaces>

<op_inventory>
The 7 op models in EMPlanResponse.ops (RESEARCH Q6):

  CreateTicketOp: op="create_ticket", original_idea, acceptance_criteria,
    dod, worker_role, domain (default "code"), risk_tier (default "med").
  DispatchCardOp: op="dispatch_card", card_id, role_id, task,
    rationale_text, candidates_considered (list[str]), confidence_hint
    (Optional[float], range [0,1]).
  KillCardOp: op="kill_card", card_id, rationale_text.
  RescopeCardOp: op="rescope_card", card_id, new_worker_role,
    new_scope (Optional[str]), new_acceptance (list[str]), rationale_text.
  SetACOp: op="set_ac", card_id, acceptance_criteria (list[str]).
  SetDoDOp: op="set_dod", card_id, dod (list[str]).
  NoopOp: op="noop", reason (str default "").

EMPlanResponse(BaseModel, extra="ignore"):
  ops: list[EMOp] = []   # max_length=20 to bound per-iteration blast radius
  reasoning: str = ""    # free-form EM scratchpad (audit reads, doesn't parse)
</op_inventory>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: RED — schema + LLM + stub test scaffolds</name>
  <files>tests/harness/em/test_em_schema.py, tests/harness/em/test_em_llm.py, tests/harness/em/test_em_stub.py</files>
  <read_first>
    - voss/eval/judge.py (the canonical mirror; copy the structure)
    - voss/harness/cognition_schemas.py (anti-pattern; what NOT to do for LLM output)
    - voss/harness/em/tickets.py (W1 records — naming alignment for Op fields)
    - tests/eval/test_judge_verdict.py (FakeProvider pattern for mocked provider.complete)
    - .planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md §Q6
    - .planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md §"voss/harness/em/llm.py" + §"voss/harness/em/stub.py"
  </read_first>
  <behavior>
    test_em_schema.py — schema behavior:
      - Parsing `{"ops":[{"op":"create_ticket","original_idea":"x",
        "acceptance_criteria":[],"dod":[],"worker_role":"backend"}],
        "reasoning":""}` produces an EMPlanResponse whose ops[0] is a
        CreateTicketOp.
      - Parsing a payload with an unknown TOP-LEVEL field
        (`{"ops":[],"reasoning":"","extend_budget":50000}`) succeeds
        because `extra="ignore"` is LENIENT; the unknown field is dropped.
      - Parsing a payload where the Op carries an unknown field
        (`{"op":"create_ticket",…,"extend_budget":50000}`) also succeeds —
        unknown field dropped from the Op. (The cage is enforced by the
        FACADE — the schema's job is to be tolerant; only the facade can
        refuse a budget extension.)
      - Discriminator routing works: an op with op="kill_card" round-trips
        to a KillCardOp instance.
      - ops field has max_length=20; parsing 21 ops fails ValidationError.
      - confidence_hint on DispatchCardOp rejects out-of-range floats
        (e.g. 1.5) at parse — uses Field(ge=0, le=1).
      - NoopOp default `reason=""` round-trips.

    test_em_llm.py — em_plan call-shape behavior:
      - em_plan(provider, model="…", idea="…", snapshot=…,
        roster_descriptions={…}) calls provider.complete exactly once.
      - The provider.complete call kwargs include:
        response_format=EMPlanResponse, temperature=0.0,
        messages = [system, user] where system is a non-empty string
        starting with the EM_SYSTEM constant and user contains the idea
        verbatim + the snapshot text.
      - When the provider returns ProviderResponse(parsed=EMPlanResponse(
        ops=[CreateTicketOp(...)], reasoning="ok")), em_plan returns that
        EMPlanResponse unchanged.
      - When the provider raises ParseError, em_plan catches and returns
        an EMPlanResponse(ops=[NoopOp(reason="parse_failure")]) — never
        raises.
      - When the provider returns ProviderResponse(parsed=None),
        em_plan returns the same Noop fallback.
      - When the provider raises a generic Exception, em_plan re-raises
        (only ParseError + parsed=None are handled; other failures are
        the loop's responsibility).
      - System prompt + schema description text contain NO L2 vocab
        ("model", "cost", "token", "provider") in user-visible substrings.

    test_em_stub.py — DeterministicEMStub behavior:
      - DeterministicEMStub(scripted=[ep1, ep2]) yields ep1 on the first
        plan(...) call, ep2 on the second, and on the third yields an
        EMPlanResponse(ops=[NoopOp(reason="stub_exhausted")]).
      - Stub.plan(...) is async; signature matches em_plan's behavioral
        contract (same kwarg names for compatibility).
      - Stub records every call's kwargs into a `calls: list[dict]`
        attribute for test introspection.
      - Stub never calls any provider; instantiating without a provider
        succeeds.
  </behavior>
  <action>
    Write three new test files. Mock the provider via a tiny
    `FakeProvider` class with `async complete(...)` configurable per test
    (return a canned ProviderResponse OR raise ParseError). Reuse the
    pattern from tests/eval/test_judge_verdict.py.

    For the system-prompt L2-vocab scan, monkeypatch the import to capture
    the actual messages list em_plan sends, then assert
    `not any(banned in msg["content"].lower() for banned in
    {"model","cost","token","provider"} for msg in messages)`.

    Run pytest; expect ImportError on voss.harness.em.schema /
    voss.harness.em.llm / voss.harness.em.stub.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; .venv/bin/python -m pytest tests/harness/em/test_em_schema.py tests/harness/em/test_em_llm.py tests/harness/em/test_em_stub.py -x -q --tb=short 2>&amp;1 | tee /tmp/o5-03-red.log; grep -qE "(ModuleNotFoundError|ImportError)" /tmp/o5-03-red.log &amp;&amp; echo EM_LLM_RED_OK</automated>
  </verify>
  <acceptance_criteria>
    - 3 new test files collect; every test fails at ImportError stage (modules don't exist).
    - W1 + W2 test suites still pass.
  </acceptance_criteria>
  <done>RED tests committed.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: GREEN — schema, em_plan, DeterministicEMStub</name>
  <files>voss/harness/em/schema.py, voss/harness/em/llm.py, voss/harness/em/stub.py, voss/harness/em/__init__.py</files>
  <read_first>
    - voss/eval/judge.py (full — the structural mirror)
    - voss/harness/em/tickets.py (W1 — naming alignment)
    - tests/harness/em/test_em_schema.py (Task 1 contract)
    - tests/harness/em/test_em_llm.py (Task 1 contract)
    - tests/harness/em/test_em_stub.py (Task 1 contract)
  </read_first>
  <behavior>
    Constraints on the implementation:

    - voss/harness/em/schema.py — pydantic v2.
      - `LENIENT = ConfigDict(extra="ignore")` module-level constant.
      - 7 Op models, each `class XxxOp(BaseModel)` with
        `model_config = LENIENT` and a discriminator `op: Literal[...]`.
      - `EMOp = Annotated[Union[CreateTicketOp, DispatchCardOp, …, NoopOp],
        Field(discriminator="op")]` (pydantic v2 discriminated-union shape).
      - `class EMPlanResponse(BaseModel)`: model_config = LENIENT,
        ops: list[EMOp] = Field(default_factory=list, max_length=20),
        reasoning: str = "".
      - Every Field uses `description=…` so the JSON-schema the LLM sees
        is self-documenting. Descriptions follow L-03 (no L2 vocab).

    - voss/harness/em/llm.py — em_plan async function.
      - Module-level constant EM_SYSTEM (str) — the system prompt. Must
        describe (a) the legal verb set, (b) the cage invariants (cannot
        widen ceiling/p, cannot invent agents, cannot extend budget),
        (c) the audit-bar reminder (original_idea is immutable), (d) the
        Noop op as the legitimate "nothing to do this iteration" escape.
      - `async def em_plan(*, provider, model, idea, snapshot,
        roster_descriptions) -> EMPlanResponse`. Builds the user message
        from snapshot text + idea verbatim + formatted roster. Calls
        `provider.complete(messages=[…], model=model,
        response_format=EMPlanResponse, temperature=0.0)`. On ParseError
        OR parsed is None, returns
        `EMPlanResponse(ops=[NoopOp(op="noop", reason="parse_failure")])`.
        On other exceptions, re-raises (per RESEARCH Q6: only ParseError
        is the sentinel-None contract).
      - Includes a private `_format_snapshot(snapshot)` helper — pure
        function; tests cover it via the snapshot fixture from W2.

    - voss/harness/em/stub.py — DeterministicEMStub.
      - `class DeterministicEMStub`. Constructor:
        `__init__(self, scripted: list[EMPlanResponse])`. Stores a list.
      - `async def plan(self, *, idea, snapshot, **kwargs) -> EMPlanResponse`.
        Pops the next scripted response; on empty, returns the
        Noop("stub_exhausted") fallback. Appends a dict of all kwargs to
        `self.calls`.
      - Class docstring matches the O3 DeterministicReviewerStub posture:
        "Production callers MUST NOT import; tests only."

    - voss/harness/em/__init__.py: extend __all__ to include EMPlanResponse,
      EMOp, CreateTicketOp, DispatchCardOp, KillCardOp, RescopeCardOp,
      SetACOp, SetDoDOp, NoopOp, em_plan, DeterministicEMStub. The stub is
      exported (it's a test fixture, not production — but Python lacks an
      "internal package" marker; the docstring is the contract).

    Iterate until every Task 1 test green. Run the full em/ test suite to
    confirm no regression.
  </behavior>
  <action>
    Implement the three modules per the behavior contract. Use pydantic v2
    syntax (Annotated[Union[…], Field(discriminator="op")]). For the
    system prompt, draft a concise multi-line string covering verbs +
    cage + audit-bar.

    Verify the discriminator routing by constructing
    `EMPlanResponse(ops=[{"op":"kill_card","card_id":"x",
    "rationale_text":"y"}])` and asserting
    `isinstance(plan.ops[0], KillCardOp)`.

    L-03 scan: search EM_SYSTEM + every Field(description=…) string for the
    four banned substrings. Replace any leak with neutral language
    (e.g. "iteration budget" → "iteration ceiling").
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; .venv/bin/python -m pytest tests/harness/em/ -x -q --tb=short &amp;&amp; .venv/bin/python -c "from voss.harness.em import EMPlanResponse, DeterministicEMStub, em_plan, NoopOp, KillCardOp; r = EMPlanResponse.model_validate({'ops':[{'op':'kill_card','card_id':'x','rationale_text':'y'}],'reasoning':'','extra_field':'ignored'}); assert isinstance(r.ops[0], KillCardOp); r2 = EMPlanResponse.model_validate({'ops':[],'reasoning':''}); assert r2.ops == []; import inspect; assert inspect.iscoroutinefunction(em_plan); print('schema ok')" &amp;&amp; echo EM_LLM_STUB_OK</automated>
  </verify>
  <acceptance_criteria>
    - All Task 1 tests GREEN; W1 + W2 still GREEN.
    - EMPlanResponse uses extra="ignore"; unknown fields drop silently.
    - Discriminator union routes ops to the correct subclass.
    - em_plan never raises on ParseError or parsed=None (returns Noop fallback).
    - em_plan calls provider.complete exactly once per invocation.
    - DeterministicEMStub yields scripted responses in order; records all calls.
    - System prompt + schema descriptions contain no L2 vocab.
    - No live LLM call in any test run.
  </acceptance_criteria>
  <done>All tests GREEN; commit references OEM-03, OEM-04.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| EM LLM stdout ↔ EMPlanResponse parse | Hallucinated fields cross this boundary; LENIENT dropping prevents crash but also prevents a confused-deputy attempt to invoke unknown ops. |
| em_plan ↔ provider | ParseError on the provider side must not bubble; the EM loop must stay live. |
| DeterministicEMStub ↔ production code | The stub must never leak into production callers (docstring contract). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O5-01 | Elevation | LLM invents `extend_budget` field on a CreateTicketOp | mitigate | LENIENT pydantic drops the field at parse; the cage is enforced by the W2 facade, not the schema. The schema test pins the drop behavior explicitly. |
| T-O5-02 | Spoofing | LLM emits an unknown `op` value | mitigate | Discriminated union raises pydantic ValidationError on unknown discriminator; em_plan's ParseError path catches and returns Noop. |
| T-O5-05 | Denial of service | LLM returns 100 ops per iteration | mitigate | EMPlanResponse.ops has max_length=20 per iteration; parse fails on overflow → Noop fallback. |
| T-O5-Stub | Tampering | DeterministicEMStub imported in production code path | mitigate | Class docstring + naming convention; W5 integration test asserts it lives behind the test boundary. |
| T-O5-LLM | Repudiation | em_plan raises silently on ParseError, hiding the loop's failure mode | accept | Noop fallback IS the audit signal — the loop continues, and the noop reason="parse_failure" is the audit breadcrumb. RESEARCH Q6 explicit decision. |
</threat_model>

<verification>
.venv/bin/python -m pytest tests/harness/em/ -x -q && .venv/bin/python -c "from voss.harness.em import EMPlanResponse, em_plan, DeterministicEMStub, NoopOp, KillCardOp, CreateTicketOp; r = EMPlanResponse.model_validate({'ops':[{'op':'create_ticket','original_idea':'i','acceptance_criteria':[],'dod':[],'worker_role':'backend'}],'reasoning':'','unknown':1}); assert isinstance(r.ops[0], CreateTicketOp); import inspect; assert inspect.iscoroutinefunction(em_plan)" && echo EM_LLM_STUB_OK
</verification>

<success_criteria>
- voss/harness/em/schema.py + llm.py + stub.py ship.
- 7 op models + EMPlanResponse with pydantic v2 LENIENT.
- em_plan mirrors judge_run shape; ParseError sentinel returns Noop.
- DeterministicEMStub yields scripted responses; zero LLM calls in tests.
- All tests green.
- Closes with the unique tag EM_LLM_STUB_OK.
</success_criteria>

<output>
Create `.planning/phases/O5-engineering-manager-loop/O5-03-SUMMARY.md` when done.
</output>
