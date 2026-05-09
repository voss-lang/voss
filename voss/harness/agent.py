"""Agent loop for `voss do` and the REPL.

This is a Python skeleton. Phase H3 ports it to .voss; the structure here
mirrors the constructs that will be lowered: ContextScope (token budget),
ProbableValue<Plan> (confidence-gated planning), gather (later, parallel
sub-agents), within/fallback (later, model tier-down).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field

from voss_runtime import (
    ContextScope,
    EpisodicMemory,
    ProbableValue,
    ToolDescriptor,
    get_config,
)
from voss_runtime.providers import get as get_provider
from voss_runtime.providers.base import ModelProvider

from .permissions import PermissionGate
from .render import Renderer

# ---------------------------------------------------------------------------
# Plan schema — what the model must return
# ---------------------------------------------------------------------------


class ToolCall(BaseModel):
    name: str = Field(description="Tool name from the available tool list.")
    args: dict[str, Any] = Field(default_factory=dict, description="Keyword arguments.")
    why: str = Field(default="", description="One-line rationale for this call.")


class Plan(BaseModel):
    rationale: str = Field(description="One-paragraph reasoning for the chosen approach.")
    steps: list[ToolCall] = Field(default_factory=list, description="Sequential tool calls.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Self-rated confidence the plan resolves the user's task. 0.0-1.0.",
    )
    open_question: str | None = Field(
        default=None,
        description="If confidence is low, the clarifying question to ask the user.",
    )
    final_when_done: str = Field(
        default="",
        description="The answer to surface to the user once tools have run. May reference results.",
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


PLAN_SYSTEM = """You are Voss, a coding agent running in a terminal.

You receive a task and a list of tools. Produce a Plan: rationale, sequential
tool calls, self-rated confidence (0.0-1.0), and the final answer to surface
to the user once tools have run.

Confidence rubric:
- 0.95+: trivial, deterministic, single-step
- 0.80-0.94: clear path, normal risk
- 0.60-0.79: ambiguity present; consider asking
- below 0.60: unclear; populate open_question and leave steps empty

Only call tools from the provided list. Reference tool result placeholders
({{step_0}}, {{step_1}}, ...) inside `final_when_done` if the answer depends
on them. Keep `final_when_done` short — under 200 words.
"""


@dataclass
class TurnResult:
    plan: Plan
    confidence: float
    final: str
    tool_results: list[str]
    cost_usd: float


def _format_tools(tools: dict[str, ToolDescriptor]) -> str:
    lines = []
    for name, td in tools.items():
        params = td.parameters.get("properties", {})
        sig = ", ".join(f"{k}: {v.get('type', 'any')}" for k, v in params.items())
        lines.append(f"- {name}({sig}) — {td.description}")
    return "\n".join(lines)


async def run_turn(
    task: str,
    *,
    tools: dict[str, ToolDescriptor],
    cwd: Path,
    renderer: Renderer,
    confidence_threshold: float = 0.60,
    token_budget: int = 60_000,
    model: str | None = None,
    provider: ModelProvider | None = None,
    history: EpisodicMemory | None = None,
    permissions: PermissionGate | None = None,
) -> TurnResult:
    """Run one agent turn.

    Mirrors the planned .voss loop:

        ctx(budget: token_budget) {
            let plan: probable<Plan> = ask(...)
            if plan @ p >= threshold {
                for step in plan.steps: tool.invoke(step)
                yield review(results)
            } else {
                yield clarify(plan.open_question)
            }
        }
    """
    cfg = get_config()
    model = model or cfg.default_model
    if provider is None:
        provider = get_provider(model)

    history_block = ""
    if history is not None:
        recent = history.last(6)
        if recent:
            history_block = "\n\nRecent conversation:\n" + "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent
            )

    user_prompt = (
        f"Task:\n{task}\n\n"
        f"Working directory: {cwd}\n\n"
        f"Available tools:\n{_format_tools(tools)}{history_block}\n"
    )

    if history is not None:
        history.add(task, role="user")

    renderer.show_thinking("planning")
    async with ContextScope(
        token_budget=token_budget, model=model, provider=provider
    ) as _ctx:
        resp = await provider.complete(
            messages=[
                {"role": "system", "content": PLAN_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
            response_format=Plan,
            temperature=0.2,
        )

    if resp.parsed is None:
        raise RuntimeError(f"provider returned no parsed Plan; raw text: {resp.text[:300]}")
    plan: Plan = resp.parsed
    probable_plan = ProbableValue(value=plan, confidence=plan.confidence)
    renderer.show_plan(plan, cost_usd=resp.cost_usd)

    # Confidence gate. Mirrors `if plan @ p >= threshold` in .voss.
    if probable_plan.confidence < confidence_threshold:
        question = plan.open_question or "I'm not confident enough — can you clarify the task?"
        renderer.show_clarify(question, plan.confidence)
        return TurnResult(
            plan=plan,
            confidence=plan.confidence,
            final=question,
            tool_results=[],
            cost_usd=resp.cost_usd,
        )

    # Execute steps sequentially. Phase H3 will lower this to `gather(spawn ...)`.
    gate = permissions or PermissionGate(auto_yes=True)
    results: list[str] = []
    for i, step in enumerate(plan.steps):
        td = tools.get(step.name)
        if td is None:
            results.append(f"<error: unknown tool {step.name!r}>")
            renderer.show_tool_call(step.name, step.args, "<unknown tool>", "error")
            continue
        allowed, why = gate.check(step.name, step.args)
        if not allowed:
            text = f"<denied: {why}>"
            renderer.show_tool_call(step.name, step.args, text, "error")
            results.append(text)
            continue
        renderer.show_tool_call(step.name, step.args, "running…", "pending")
        try:
            res = await td.invoke(**step.args)
            text = str(res)
        except Exception as e:  # noqa: BLE001 — catch all to surface, not crash
            text = f"<error: {e}>"
            renderer.show_tool_call(step.name, step.args, text, "error")
            results.append(text)
            continue
        renderer.show_tool_call(step.name, step.args, _summarize(text), "ok")
        results.append(text)

    final = plan.final_when_done or "(no final answer)"
    for i, r in enumerate(results):
        final = final.replace(f"{{{{step_{i}}}}}", r)

    if history is not None:
        history.add(final, role="assistant")

    total_tokens = resp.prompt_tokens + resp.completion_tokens
    ctx_pct = total_tokens / token_budget if token_budget else 0.0
    renderer.status(
        model=model,
        tokens=total_tokens,
        cost_usd=resp.cost_usd,
        ctx_pct=ctx_pct,
    )

    return TurnResult(
        plan=plan,
        confidence=plan.confidence,
        final=final,
        tool_results=results,
        cost_usd=resp.cost_usd,
    )


def _summarize(text: str, limit: int = 80) -> str:
    first = text.splitlines()[0] if text else ""
    if len(first) > limit:
        return first[: limit - 1] + "…"
    return first or f"({len(text)}B)"
