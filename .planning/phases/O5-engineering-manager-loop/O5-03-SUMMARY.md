---
phase: O5-engineering-manager-loop
plan: 03
status: complete
completed_at: 2026-05-20
commits: []
depends_on: [O5-01]
requirements: [OEM-03, OEM-04]
---

# O5-03 Summary — LLM Schema + Stub (Wave 3)

## Objective

Land the EM LLM call surface: pydantic v2 LENIENT schema (`EMPlanResponse` with 7 Op discriminated union), the async `em_plan(...)` wrapper mirroring `judge_run`, and `DeterministicEMStub` for deterministic testing with zero live LLM calls.

## Files changed

- `voss/harness/em/schema.py` -- **new** (92 lines): `LENIENT = ConfigDict(extra="ignore")`, 7 Op models (CreateTicketOp, DispatchCardOp, KillCardOp, RescopeCardOp, SetACOp, SetDoDOp, NoopOp) with `op: Literal[...]` discriminators, `EMOp` discriminated union via `Annotated[Union[...], Field(discriminator="op")]`, `EMPlanResponse` with `ops: list[EMOp]` (max_length=20).
- `voss/harness/em/llm.py` -- **new** (81 lines): `EM_SYSTEM` system prompt constant, `async def em_plan(*, provider, model, idea, snapshot, roster_descriptions) -> EMPlanResponse`. On ParseError or parsed=None, returns Noop fallback. On other exceptions, re-raises.
- `voss/harness/em/stub.py` -- **new** (34 lines): `DeterministicEMStub` with scripted queue, `async plan(*, idea, snapshot, **kwargs)`, exhaustion returns Noop("stub_exhausted"), records all calls in `self.calls`.
- `voss/harness/em/__init__.py` -- extended: re-exports all Op types, EMPlanResponse, EMOp, em_plan, DeterministicEMStub.
- `tests/harness/em/test_em_schema.py` -- **new** (14 tests): LENIENT extra-field dropping (top-level + per-op), discriminator routing, max_length=20 enforcement, confidence_hint range validation, NoopOp default round-trip.
- `tests/harness/em/test_em_llm.py` -- **new** (7 tests): provider.complete call shape (response_format, temperature), ParseError sentinel returns Noop, parsed=None returns Noop, generic Exception re-raises, system prompt L2-vocab scan.
- `tests/harness/em/test_em_stub.py` -- **new** (5 tests): scripted queue yields in order, exhaustion returns Noop, call recording, async signature, no-provider instantiation.

## Test counts

| File | Tests |
|------|-------|
| `test_em_schema.py` | 14 |
| `test_em_llm.py` | 7 |
| `test_em_stub.py` | 5 |
| **Total (new)** | **26** |

## Key facts

- **Pydantic posture (L-01):** `extra="ignore"` (LENIENT) on every Op and on EMPlanResponse. Hallucinated LLM fields (e.g. `extend_budget`) drop silently at parse. The cage is enforced by EMBoardHandle (W2), not the schema.
- **Discriminated union:** pydantic v2 routes on the `op` field. Unknown op values raise ValidationError at parse; `em_plan` catches this via the ParseError path and returns Noop.
- **max_length=20:** Bounds per-iteration blast radius. A 21-op response fails ValidationError at parse.
- **em_plan mirrors judge_run:** Same structural pattern -- `provider.complete(response_format=..., temperature=0.0)`, ParseError sentinel catch, parsed=None catch.
- **EM_SYSTEM prompt:** Describes legal verbs, cage rules (cannot change ceiling/thresholds, cannot invent agents, cannot extend budget), audit-bar reminder (original idea is immutable), noop escape. Contains no L2 vocab.
- **DeterministicEMStub:** Scripted queue with exhaustion fallback. `plan()` is async with matching kwarg names for compatibility with `em_plan`. Records all calls for test introspection. Docstring marks it as test-only.

## Deviations from plan

- **Schema test count higher than plan implied:** Plan described ~7 schema behaviors; execution expanded to 14 tests for finer-grained coverage.
- **em_plan snapshot parameter is `str` not `BoardSnapshot`:** The function accepts the snapshot as pre-formatted text, not the W2 BoardSnapshot object. The loop (W4) converts snapshot to text before calling em_plan.

## Unchanged

- `voss/eval/judge.py` -- structural mirror only; no modifications.
- `voss/harness/cognition_schemas.py` -- anti-pattern reference; no modifications.
- W1 + W2 tests -- all still green.

## Next

W4 lands em_loop -- the autonomous plan-and-tick coroutine.
