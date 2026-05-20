# Phase O4: Reviewer A/B Split — Pattern Map

**Mapped:** 2026-05-19
**Files analyzed:** 5 new files (2 source, 3 test)
**Analogs found:** 5 / 5 (all have role-match or exact analogs)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `voss/harness/board/reviewer_a.py` | service | request-response (async agent loop) | `voss/harness/subagents.py` (`run_subagent`) | role-match |
| `voss/harness/board/reviewer_b.py` | service | request-response (single structured call) | `voss/eval/judge.py` (`judge_run`) | exact |
| `tests/harness/board/test_reviewer_a.py` | test | — | `tests/eval/test_judge_verdict.py` + `tests/harness/test_agent_integration.py` | role-match |
| `tests/harness/board/test_reviewer_b.py` | test | — | `tests/eval/test_judge_verdict.py` | exact |
| `tests/harness/board/test_reviewer_integration.py` | test (integration) | — | `tests/harness/test_agent_integration.py` | role-match |

---

## Pattern Assignments

---

### `voss/harness/board/reviewer_b.py` (service, single structured call)

**Analog:** `voss/eval/judge.py` — exact match. Reviewer-B is a single `provider.complete()` call with structured output, identical to `judge_run`. The only differences are the system prompt, the input fields, and the output type (`ReviewerVerdict` instead of `Verdict`).

**Imports pattern** (`voss/eval/judge.py` lines 1-9):
```python
"""LLM-as-judge scorer (M5 D-08, D-09)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from voss_runtime.providers.base import ModelProvider
from voss_runtime.providers.litellm_provider import ParseError
```

For `reviewer_b.py`, adapt as:
```python
from __future__ import annotations

from typing import Literal

from voss_runtime.providers.base import ModelProvider
from voss_runtime.providers.litellm_provider import ParseError

from voss.harness.board.verdict import ReviewerVerdict, Reviewer
```

**Core pattern — single structured `provider.complete()` call** (`voss/eval/judge.py` lines 29-59):
```python
async def judge_run(
    *,
    provider: ModelProvider,
    model: str,
    task_prompt: str,
    final: str,
    file_diff: str,
    rubric: str,
) -> tuple[Verdict | None, str]:
    """Return (Verdict, judge_verdict_str). On ParseError, returns (None, "skipped")."""
    user_msg = (
        f"## Task prompt\n{task_prompt}\n\n"
        f"## Agent final\n{final}\n\n"
        f"## File diff\n{file_diff}\n\n"
        f"## Rubric\n{rubric}\n"
    )
    try:
        resp = await provider.complete(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
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

For `reviewer_b.py`, map fields as follows:
- `JUDGE_SYSTEM` → `REVIEWER_B_SYSTEM` (declares isolation + Residual-2 authority)
- `response_format=Verdict` → `response_format=ReviewerVerdict`
- User message sections: `original_idea`, `acceptance`, `artifact`, `repo_summary`, `a_verification_summary`
- Return type: `ReviewerVerdict` directly (not a tuple — the Protocol returns `ReviewerVerdict`)
- `ParseError` handling: re-raise or return a blocking `ReviewerVerdict` with `verdict="block"` and low `conf` — do NOT swallow silently

**System prompt constant pattern** (`voss/eval/judge.py` lines 22-26):
```python
JUDGE_SYSTEM = """You are an evaluator. Given a task prompt, the agent's final
answer, an optional file diff, and a rubric, decide if the run passed or failed.
Return ONLY a JSON object: {"verdict": "pass"|"fail", "confidence": 0.0-1.0,
"rationale": "<one paragraph>"}.
"""
```

Copy this constant pattern for:
```python
REVIEWER_B_SYSTEM = """You are Reviewer-B, an independent judge.
...
Return a JSON object matching the ReviewerVerdict schema.
"""
```

**Tiered model selection pattern** — there is no direct existing analog in the codebase for tier switching. Use a simple string parameter (caller selects before the call). See `voss_runtime/_config.py` line 8 for the default model anchor:
```python
# voss_runtime/_config.py line 8
default_model: str = "claude-sonnet-4-5"
```

The `ReviewerB` class should accept `fast_model: str` and `strong_model: str` as constructor kwargs so tests can inject stubs without real model names.

**`ModelProvider` Protocol shape** (`voss_runtime/providers/base.py` lines 26-39):
```python
@runtime_checkable
class ModelProvider(Protocol):
    async def complete(
        self,
        *,
        messages: list[dict],
        model: str,
        response_format: Optional[type] = None,
        tools: Optional[list[dict]] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> ProviderResponse: ...

    def count_tokens(self, *, text: str, model: str) -> int: ...
```

`resp.parsed` gives the structured output; `resp.parsed is None` means the provider failed to parse. Mirror `judge_run`'s `ParseError` guard exactly.

---

### `voss/harness/board/reviewer_a.py` (service, async agent loop)

**Analog:** `voss/harness/subagents.py` (`run_subagent`, lines 90-164) — role-match. Reviewer-A calls `run_turn` with a fresh `EpisodicMemory(capacity=20)` per card, identical to how `run_subagent` does it. The second analog for the AI-card path is `voss/eval/judge.py:judge_run`.

**Imports pattern** (`voss/harness/subagents.py` lines 1-16):
```python
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, FrozenSet, Optional

from voss_runtime import EpisodicMemory, tool
from voss_runtime.exceptions import BudgetExceededError

from .agent import run_turn
from .permissions import Mode, PermissionGate
from .render import Renderer
from .session_tree import finalize_node
from .tools import ToolEntry, make_toolset
```

For `reviewer_a.py`, adapt as:
```python
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

from voss_runtime import EpisodicMemory
from voss_runtime.providers.base import ModelProvider

from voss.eval.judge import judge_run, Verdict
from voss.harness.agent import run_turn
from voss.harness.render import Renderer
from voss.harness.team import gate_for_role, filter_toolset_for_role
from voss.harness.tools import make_toolset
from voss.harness.board.verdict import ReviewerVerdict, Reviewer
```

**Core pattern — `run_turn` with fresh `EpisodicMemory` per call** (`voss/harness/subagents.py` lines 115-140):
```python
result = await run_turn(
    agent_task(spec, task),
    tools=child_tools,
    cwd=cwd,
    renderer=renderer,
    model=model,
    provider=provider,
    history=EpisodicMemory(capacity=20),   # fresh per call — critical
    permissions=gate,
    cognition=cognition,
    token_budget=spendable,
)
```

For `reviewer_a.py`, the call becomes:
```python
result = await run_turn(
    _reviewer_a_task(original_idea=original_idea, artifact_path=artifact_path),
    tools=filter_toolset_for_role(reviewer_a_spec, make_toolset(cwd, renderer=renderer)),
    cwd=cwd,
    renderer=renderer,
    model=model,
    provider=provider,
    history=EpisodicMemory(capacity=20),   # NEW per review() call — never in __init__
    permissions=gate_for_role(reviewer_a_spec, base_gate),
    session_id=str(uuid.uuid4()),           # fresh session — no shared session id
)
```

**Critical:** `EpisodicMemory(capacity=20)` must be constructed inside `review()`, NOT in `__init__`. Constructing it once on the class causes cross-card memory bleed (RESEARCH Pitfall 2).

**AI-card eval gate — online reuse of `judge_run`** (`voss/eval/judge.py` lines 29-59, full file already shown above):
```python
verdict, judge_str = await judge_run(
    provider=provider,
    model=judge_model,
    task_prompt=original_idea,       # idea is the task prompt
    final=artifact_text,
    file_diff=file_diff,
    rubric=a_authored_rubric,        # Reviewer-A's rubric from bar derivation
)
# verdict is Verdict(verdict="pass"|"fail", confidence=float, rationale=str)
```

Import `from voss.eval.judge import judge_run` directly. Never import `from voss.eval.runner import run_suite` — that is the offline batch runner (RESEARCH Pitfall 3).

**`gate_for_role` pattern** (`voss/harness/team.py` lines 98-125):
```python
def gate_for_role(spec: SubagentSpec, base_gate: PermissionGate) -> PermissionGate:
    if spec.mode is None:
        effective_mode = base_gate.mode
    else:
        effective_mode = _min_mode(base_gate.mode, spec.mode)
    return PermissionGate(
        mode=effective_mode,
        store=None,
        auto_yes=True,
        prompt_fn=None,
        edit_scope=None,
        scope_prompt_fn=None,
        project_policy=base_gate.project_policy,
        allow_net=True if spec.net else False,
    )
```

**`filter_toolset_for_role` pattern** (`voss/harness/team.py` lines 128-149):
```python
def filter_toolset_for_role(
    spec: SubagentSpec,
    base_toolset: Mapping[str, ToolEntry],
) -> dict[str, ToolEntry]:
    if spec.tools is None:
        return dict(base_toolset)
    expanded: set[str] = set()
    for entry in spec.tools:
        if entry in TOOL_GROUP_ALIASES:
            expanded |= set(TOOL_GROUP_ALIASES[entry])
        else:
            expanded.add(entry)
    return {name: te for name, te in base_toolset.items() if name in expanded}
```

**`Verdict` → `ReviewerVerdict` translation pattern:**

`judge_run` returns `Verdict(verdict, confidence, rationale)`. O4 must translate to `ReviewerVerdict(conf, source, tier, verdict, notes, evidence_refs)`. The translation is a local helper inside `reviewer_a.py`:
```python
def _verdict_from_judge(v: Verdict, rubric_id: str) -> ReviewerVerdict:
    return ReviewerVerdict(
        conf=v.confidence,
        source="A",
        tier="strong",          # A's determination is always "strong" (deterministic)
        verdict=v.verdict,      # "pass" or "fail" — no "block" from A
        notes=v.rationale,
        evidence_refs=(rubric_id,),
    )
```

---

### `tests/harness/board/test_reviewer_b.py` (test, unit)

**Analog:** `tests/eval/test_judge_verdict.py` (lines 1-67) — exact match for the fake provider + `provider.complete()` call pattern.

**`FakeJudgeProvider` pattern to copy** (`tests/eval/test_judge_verdict.py` lines 9-23):
```python
class FakeJudgeProvider:
    def __init__(self, verdict: Verdict | None):
        self.verdict = verdict

    async def complete(self, *, messages, model, response_format=None, **kw):
        text = self.verdict.model_dump_json() if self.verdict else "{}"
        return ProviderResponse(
            text=text,
            model=model,
            prompt_tokens=1,
            completion_tokens=1,
            cost_usd=0.0,
            raw={},
            parsed=self.verdict,
        )

    def count_tokens(self, *, text, model):
        return 1
```

Adapt as `FakeReviewerBProvider` that returns a canned `ReviewerVerdict` (or `None` for ParseError path). Capture `messages` list in `self.calls` to assert isolation (ORVW-04).

**Test structure pattern** (`tests/eval/test_judge_verdict.py` lines 29-67):
```python
def test_judge_returns_verdict():
    fp = FakeJudgeProvider(Verdict(verdict="pass", confidence=0.9, rationale="ok"))
    verdict, verdict_str = asyncio.run(
        judge_run(
            provider=fp,
            model="m",
            task_prompt="t",
            final="f",
            file_diff="",
            rubric="r",
        )
    )
    assert verdict_str == "pass"
    assert verdict is not None
    assert verdict.confidence == 0.9
```

Note: `asyncio_mode = "auto"` is set in `pyproject.toml` line 81, so test functions can be `async def` directly — no `asyncio.run()` required in new tests. Existing `test_judge_verdict.py` uses `asyncio.run()` directly (pre-asyncio_mode convention); new O4 tests should use `async def test_...()` natively.

**ParseError test pattern** (`tests/eval/test_judge_verdict.py` lines 47-67):
```python
class RaisingProvider:
    async def complete(self, **kw):
        raise ParseError("bad json")

    def count_tokens(self, **kw):
        return 1
```

Use the same pattern to test B's error handling path.

**Message isolation assertion pattern** (new — no existing analog, use `FakeProvider.calls` from `tests/harness/test_agent_integration.py` lines 50-61):
```python
async def complete(self, *, messages, model, response_format=None, **kw):
    self.calls.append({"messages": messages, "model": model})
    ...
```

Then assert:
```python
assert not any(
    "em_plan" in str(msg) or "EM" in str(msg)
    for call in provider.calls
    for msg in call["messages"]
)
```

---

### `tests/harness/board/test_reviewer_a.py` (test, unit)

**Analog:** `tests/harness/test_agent_integration.py` (lines 1-147) — role-match. Uses `FakeProvider` to script agent loop responses without real API calls. Combined with `FakeJudgeProvider` from `tests/eval/test_judge_verdict.py` for the AI-card path.

**`FakeProvider` pattern** (`tests/harness/test_agent_integration.py` lines 30-101):
```python
class FakeProvider:
    def __init__(self, plan: Plan, cost: float = 0.001):
        self.plan = plan
        self.cost = cost
        self.calls: list[dict] = []
        self._stream_index = 0

    async def complete(self, *, messages, model, response_format=None, **kw) -> ProviderResponse:
        self.calls.append({"model": model, "messages": messages, "schema": response_format})
        text = self.plan.model_dump_json()
        return ProviderResponse(
            text=text, model=model, prompt_tokens=50, completion_tokens=50,
            cost_usd=self.cost, raw={"fake": True},
            parsed=self.plan if response_format is Plan else None,
        )

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)
```

**Fresh memory test approach:** Call `reviewer_a.review(card_1)` then `reviewer_a.review(card_2)` with a recording provider. Assert that `card_2`'s `messages[]` contain no text from `card_1`'s artifact. This directly exercises ORVW-08.

**Protocol conformance test pattern** (`tests/harness/test_subagent_recursion.py` lines 23-30):
```python
import inspect
from voss.harness import subagents

def test_run_subagent_has_no_depth_parameter() -> None:
    sig = inspect.signature(subagents.run_subagent)
    params = set(sig.parameters)
    assert "depth" not in params
```

Adapt for ORVW-09:
```python
import inspect
from voss.harness.board.reviewer_a import ReviewerA
from voss.harness.board.reviewer_b import ReviewerB
from voss.harness.board.verdict import Reviewer

def test_reviewer_a_implements_protocol():
    assert isinstance(ReviewerA(...), Reviewer)  # runtime_checkable Protocol

def test_reviewer_b_implements_protocol():
    assert isinstance(ReviewerB(...), Reviewer)
```

---

### `tests/harness/board/test_reviewer_integration.py` (test, integration)

**Analog:** `tests/harness/test_agent_integration.py` — role-match. Uses `FakeProvider` + scripted plan sequence to exercise a full loop without real providers.

**Integration test structure** (`tests/harness/test_agent_integration.py` lines 1-19):
```python
"""End-to-end agent loop tests with a fake provider.

Verifies plan -> tool exec -> final assembly without API keys.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from voss_runtime import EpisodicMemory
from voss_runtime.providers.base import ProviderResponse

from voss.harness.agent import Plan, ToolCall, run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset
```

The integration test (ORVW-10) will need a `DeterministicReviewerStub` (shipped by O3) in place of real `ReviewerA`/`ReviewerB` to drive a card through the full board lifecycle. It is a structural test verifying the Protocol contract, not an LLM call test.

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** Every file in `voss/harness/` and `voss/eval/`
**Apply to:** All new O4 source files (`reviewer_a.py`, `reviewer_b.py`)

All harness modules start with `from __future__ import annotations` (deferred evaluation). Copy this unconditionally.

### `provider.complete()` + `resp.parsed` + `ParseError` guard
**Source:** `voss/eval/judge.py` lines 45-58
```python
try:
    resp = await provider.complete(
        messages=[...],
        model=model,
        response_format=SomeModel,
        temperature=0.0,
    )
except ParseError:
    return None, "skipped"   # or raise — decide per caller contract
if resp.parsed is None:
    return None, "skipped"
return resp.parsed, resp.parsed.verdict
```
**Apply to:** `reviewer_b.py` — exact copy, substituting `ReviewerVerdict` for `Verdict`.

Note: Unlike `judge_run` which swallows `ParseError` gracefully, `reviewer_b.py` must decide whether `ParseError` produces a `block` verdict or propagates. Research recommends re-raise (gate failure is safer than a missed block) — but confirm at SPEC.

### `EpisodicMemory(capacity=20)` — fresh per call
**Source:** `voss/harness/subagents.py` lines 124, 137
```python
history=EpisodicMemory(capacity=20),
```
**Apply to:** `reviewer_a.py` — inside `review()` body, never in `__init__`.

### `asyncio_mode = "auto"` — test functions are `async def`
**Source:** `pyproject.toml` line 81
**Apply to:** All new test files. Write `async def test_...()` without `asyncio.run()`. The pre-O4 eval tests use `asyncio.run()` because they predate the `asyncio_mode = "auto"` setting being active in that suite — O4 tests in `tests/harness/board/` use `async def` natively.

### `ProviderResponse` fake constructor
**Source:** `tests/eval/test_judge_verdict.py` lines 15-23
```python
return ProviderResponse(
    text=text,
    model=model,
    prompt_tokens=1,
    completion_tokens=1,
    cost_usd=0.0,
    raw={},
    parsed=self.verdict,
)
```
**Apply to:** All fake provider classes in O4 tests. All 7 fields (text, model, prompt_tokens, completion_tokens, cost_usd, raw, parsed) are required.

### Import `verdict.py` from `voss.harness.board.verdict` — one direction only
**Source:** O3-CONTEXT.md + RESEARCH Pitfall 4
**Apply to:** `reviewer_a.py` and `reviewer_b.py` — both import FROM `verdict.py`; `verdict.py` imports from nothing in harness. Never modify `verdict.py` from O4.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `REVIEWER_B_SYSTEM` constant | — | — | No existing system-prompt-as-constant for a structured-output-only reviewer exists; use `JUDGE_SYSTEM` in `judge.py` (lines 22-26) as the formatting template, swap content |
| Tiered model selector (`fast_model` / `strong_model`) | — | — | No tier-switching exists anywhere in harness; implement as two injectable constructor kwargs |
| `Verdict` → `ReviewerVerdict` translator | — | — | No type-translation helper exists; implement as a private `_verdict_from_judge()` function in `reviewer_a.py` |

---

## Metadata

**Analog search scope:** `voss/eval/`, `voss/harness/`, `voss_runtime/`, `tests/eval/`, `tests/harness/`
**Key files read:** `voss/eval/judge.py`, `voss/eval/suite.py`, `voss/harness/subagents.py`, `voss/harness/team.py`, `voss/harness/agent.py` (lines 412-480), `voss_runtime/providers/base.py`, `voss_runtime/_config.py`, `tests/eval/test_judge_verdict.py`, `tests/eval/test_judge_skipped.py`, `tests/harness/test_agent_integration.py`, `tests/harness/test_subagent_recursion.py`
**Pattern extraction date:** 2026-05-19

### Critical constraint: O3 hard gate
`voss/harness/board/verdict.py` does NOT exist yet — O3 has not been executed. O4 plan Wave 0 must include a preflight check that `voss.harness.board.verdict` imports cleanly before any O4 code runs. All `from voss.harness.board.verdict import ReviewerVerdict, Reviewer` imports in O4 source files will fail until O3 ships.
