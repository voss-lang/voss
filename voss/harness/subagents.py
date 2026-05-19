from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from voss_runtime import EpisodicMemory, tool
from voss_runtime.exceptions import BudgetExceededError

from .agent import run_turn
from .permissions import PermissionGate
from .render import Renderer
from .session_tree import finalize_node
from .tools import ToolEntry, make_toolset

if TYPE_CHECKING:
    from .session_tree import SessionTreeNode


# Single source of truth for the spawn tool name; consumed by the TUI
# renderer (M9-04) to detect subagent dispatch in show_tool_call without
# hardcoding the string. Must equal the literal passed to attach_subagent_tool
# below.
SPAWN_TOOL_NAME: str = "subagent_run"


@dataclass(frozen=True)
class SubagentSpec:
    id: str
    description: str
    role_prompt: str


class SubagentRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, SubagentSpec] = {}

    def register(self, spec: SubagentSpec) -> None:
        self._entries[spec.id] = spec

    def get(self, agent_id: str) -> SubagentSpec | None:
        return self._entries.get(agent_id)

    def ids(self) -> list[str]:
        return sorted(self._entries)

    def entries(self) -> list[SubagentSpec]:
        return [self._entries[k] for k in self.ids()]


def default_subagent_registry() -> SubagentRegistry:
    registry = SubagentRegistry()
    registry.register(
        SubagentSpec(
            id="explorer",
            description="Inspect code and return concise findings.",
            role_prompt="You are a read-heavy code explorer. Inspect first, avoid edits unless explicitly required.",
        )
    )
    registry.register(
        SubagentSpec(
            id="worker",
            description="Carry out a bounded implementation task.",
            role_prompt="You are an implementation worker. Keep changes scoped and verify the result.",
        )
    )
    registry.register(
        SubagentSpec(
            id="reviewer",
            description="Review code for bugs, regressions, and missing tests.",
            role_prompt="You are a code reviewer. Prioritize concrete findings over summaries.",
        )
    )
    return registry


def agent_task(spec: SubagentSpec, task: str) -> str:
    return f"Subagent role:\n{spec.role_prompt}\n\nTask:\n{task}"


async def run_subagent(
    *,
    agent_id: str,
    task: str,
    registry: SubagentRegistry,
    cwd: Path,
    renderer: Renderer,
    provider: Any,
    model: str,
    gate: PermissionGate,
    cognition: Any = None,
    node: SessionTreeNode | None = None,
    reserve: int = 0,
) -> str:
    spec = registry.get(agent_id)
    if spec is None:
        return f"<error: unknown subagent {agent_id!r}>"
    spendable = (node.envelope["limit"] - reserve) if node else None
    child_tools = make_toolset(cwd, renderer=renderer)
    scope = (
        node._budget
        if node and node._budget
        else nullcontext()
    )
    try:
        async with scope:
            if node is not None:
                result = await run_turn(
                    agent_task(spec, task),
                    tools=child_tools,
                    cwd=cwd,
                    renderer=renderer,
                    model=model,
                    provider=provider,
                    history=EpisodicMemory(capacity=20),
                    permissions=gate,
                    cognition=cognition,
                    token_budget=spendable,
                )
            else:
                result = await run_turn(
                    agent_task(spec, task),
                    tools=child_tools,
                    cwd=cwd,
                    renderer=renderer,
                    model=model,
                    provider=provider,
                    history=EpisodicMemory(capacity=20),
                    permissions=gate,
                    cognition=cognition,
                )
        if node and result.run and result.run.exit_reason == "budget":
            finalize_node(
                node,
                exit_reason="budget",
                final=result.final,
                cwd=cwd,
            )
        elif node:
            finalize_node(
                node,
                exit_reason="done",
                final=result.final,
                cwd=cwd,
            )
        return result.final
    except BudgetExceededError:
        if node:
            finalize_node(
                node,
                exit_reason="budget",
                final="<halted: budget>",
                cwd=cwd,
            )
        return "<halted: budget>"


def attach_subagent_tool(
    tools: dict[str, ToolEntry],
    *,
    registry: SubagentRegistry,
    cwd: Path,
    renderer: Renderer,
    provider: Any,
    model: str | Callable[[], str],
    gate: PermissionGate,
    cognition: Any = None,
) -> None:
    @tool(
        name="subagent_run",
        description="Run a registered Voss subagent on a bounded task.",
    )
    async def subagent_run(agent: str, task: str) -> str:
        picked_model = model() if callable(model) else model
        return await run_subagent(
            agent_id=agent,
            task=task,
            registry=registry,
            cwd=cwd,
            renderer=renderer,
            provider=provider,
            model=picked_model,
            gate=gate,
            cognition=cognition,
        )

    tools["subagent_run"] = ToolEntry(descriptor=subagent_run, is_mutating=True)
