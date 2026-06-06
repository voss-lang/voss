from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, FrozenSet, Optional

import yaml

from voss_runtime import EpisodicMemory, tool
from voss_runtime.exceptions import BudgetExceededError

from .agent import run_turn
from .permissions import Mode, PermissionGate
from .render import Renderer
from .session_tree import finalize_node
from .tools import ToolEntry, make_toolset

if TYPE_CHECKING:
    from .session_tree import SessionTreeNode
    from .team import TeamRoleScope


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
    # O2 additions; all optional / defaulted for back-compat.
    model: Optional[str] = None
    mode: Optional[Mode] = None
    scope: "TeamRoleScope | None" = None
    budget: Optional[int] = None
    tools: Optional[FrozenSet[str]] = None
    net: bool = False
    confidence_threshold: Optional[float] = None  # H5.2: per-agent gate


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


# ---------------------------------------------------------------------------
# H5.4 — custom agents from `.voss/agents/*.md` (markdown + YAML frontmatter)
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split `---\\n<yaml>\\n---\\n<body>` into (meta, body). Lenient."""
    if not text.lstrip().startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), parts[2].strip()


def _as_float(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _as_int(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def load_agent_specs(cwd: Path) -> list[SubagentSpec]:
    """Load custom agent definitions from `<cwd>/.voss/agents/*.md`.

    Frontmatter keys (all optional except an implicit id from the filename):
    id, description, mode (plan|edit|auto), model, tools (list), budget,
    net, confidence_threshold. The markdown body is the role prompt.
    """
    agents_dir = Path(cwd) / ".voss" / "agents"
    specs: list[SubagentSpec] = []
    if not agents_dir.is_dir():
        return specs
    for path in sorted(agents_dir.glob("*.md")):
        try:
            text = path.read_text()
        except OSError:
            continue
        meta, body = _parse_frontmatter(text)
        mode = meta.get("mode")
        if mode not in ("plan", "edit", "auto"):
            mode = None
        tools = meta.get("tools")
        tools_fs = frozenset(str(t) for t in tools) if isinstance(tools, list) else None
        specs.append(
            SubagentSpec(
                id=str(meta.get("id") or path.stem),
                description=str(meta.get("description") or ""),
                role_prompt=body,
                model=meta.get("model"),
                mode=mode,
                budget=_as_int(meta.get("budget")),
                tools=tools_fs,
                net=bool(meta.get("net", False)),
                confidence_threshold=_as_float(meta.get("confidence_threshold")),
            )
        )
    return specs


def register_agent_files(registry: SubagentRegistry, cwd: Path) -> int:
    """Register every `.voss/agents/*.md` spec into `registry`. Returns count."""
    count = 0
    for spec in load_agent_specs(cwd):
        registry.register(spec)
        count += 1
    return count


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
    # Resolve the `smol` role once: cheap-subagent chain when configured, else
    # the parent provider. Network-free unless [harness.roles.smol] is set.
    from . import roles

    try:
        smol = roles.build_role_provider("smol")
    except Exception:  # noqa: BLE001 — never block subagent setup on catalog issues
        smol = None

    @tool(
        name="subagent_run",
        description="Run a registered Voss subagent on a bounded task.",
    )
    async def subagent_run(agent: str, task: str) -> str:
        if smol is not None:
            picked_provider, picked_model = smol
        else:
            picked_provider = provider
            picked_model = model() if callable(model) else model
        return await run_subagent(
            agent_id=agent,
            task=task,
            registry=registry,
            cwd=cwd,
            renderer=renderer,
            provider=picked_provider,
            model=picked_model,
            gate=gate,
            cognition=cognition,
        )

    tools["subagent_run"] = ToolEntry(descriptor=subagent_run, is_mutating=True)
