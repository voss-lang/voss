from __future__ import annotations

import asyncio
import json as _json
import re as _re
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
from .session_tree import finalize_node, mutate_envelope
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


_JSON_FENCE = _re.compile(r"```(?:json)?\s*(.*?)```", _re.DOTALL)


def _extract_json(text: str) -> str:
    """Strip a leading/embedded ```json fence; otherwise return the trimmed
    text. The model is asked for bare JSON, but tolerate the common fenced
    form."""
    s = text.strip()
    m = _JSON_FENCE.search(s)
    return m.group(1).strip() if m else s


def validate_subagent_json(text: str, schema: dict[str, Any]) -> str:
    """Parse `text` as JSON and validate against `schema` (JSON Schema).

    Returns canonical JSON on success, or an `<error: ...>` envelope when the
    subagent's output is not valid JSON, fails validation, or the schema itself
    is malformed. Never raises — the agent loop treats the envelope as a tool
    result it can react to.
    """
    import jsonschema

    raw = _extract_json(text)
    try:
        instance = _json.loads(raw)
    except (ValueError, TypeError):
        return f"<error: subagent did not return valid JSON: {text[:200]!r}>"
    try:
        jsonschema.validate(instance, schema)
    except jsonschema.SchemaError as e:
        return f"<error: invalid schema: {e.message}>"
    except jsonschema.ValidationError as e:
        return f"<error: schema validation failed: {e.message}>"
    return _json.dumps(instance)


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
    # [VTREE-04] Pre-emptive spend guard: refuse to begin a call when the
    # node's envelope is exhausted. Pure read of the node's own envelope with
    # no lock and no await between check and return — atomic under asyncio.
    if node is not None and node.envelope["spent"] >= node.envelope["limit"]:
        if not node._finalized:
            finalize_node(
                node,
                exit_reason="budget",
                final="<halted: budget — envelope exhausted>",
                cwd=cwd,
            )
        return "<halted: budget — envelope exhausted>"
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
        # [VTREE-04] Update spent from actual token usage so the pre-emptive
        # guard is live (not dead code). Negative delta increments spent.
        if node and result.run is not None:
            tokens_used = (
                (result.run.iteration_total_prompt_tokens or 0)
                + (result.run.iteration_total_completion_tokens or 0)
            )
            if tokens_used > 0:
                mutate_envelope(node, delta=-tokens_used, cwd=cwd)
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
    except asyncio.TimeoutError:  # [VTREE-07] — must precede except Exception
        if node:
            finalize_node(
                node,
                exit_reason="timeout",
                final="<halted: timeout>",
                cwd=cwd,
            )
        raise  # re-raise — caller defines timeout semantics
    except Exception as exc:  # [VTREE-07]
        if node:
            finalize_node(
                node,
                exit_reason="error",
                final=f"<error: {exc}>",
                cwd=cwd,
            )
        raise
    finally:  # [VTREE-07] safety net — guarantee no open node on any path
        if node is not None and not node._finalized:
            finalize_node(
                node,
                exit_reason="error",
                final="<uncaught>",
                cwd=cwd,
            )


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

    def _pick() -> tuple[Any, str]:
        if smol is not None:
            return smol
        return provider, (model() if callable(model) else model)

    @tool(
        name="subagent_run",
        description="Run a registered Voss subagent on a bounded task.",
    )
    async def subagent_run(agent: str, task: str) -> str:
        picked_provider, picked_model = _pick()
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

    tools["subagent_run"] = ToolEntry(
        descriptor=subagent_run, is_mutating=True, group="review", scope_requirements=("review",)
    )

    @tool(
        name="task",
        description=(
            "Run a registered subagent and return schema-validated JSON. Pass "
            "`schema` (a JSON Schema object); the subagent's final answer is "
            "parsed and validated against it, returning canonical JSON or an "
            "error envelope. Without `schema`, returns the subagent's text."
        ),
    )
    async def task(agent: str, task: str, schema: dict[str, Any] | None = None) -> str:
        sub_task = task
        if schema is not None:
            sub_task = (
                f"{task}\n\nReturn ONLY a JSON value matching this JSON Schema "
                f"(no prose, no code fences):\n{_json.dumps(schema)}"
            )
        picked_provider, picked_model = _pick()
        final = await run_subagent(
            agent_id=agent,
            task=sub_task,
            registry=registry,
            cwd=cwd,
            renderer=renderer,
            provider=picked_provider,
            model=picked_model,
            gate=gate,
            cognition=cognition,
        )
        if schema is None:
            return final
        return validate_subagent_json(final, schema)

    tools["task"] = ToolEntry(
        descriptor=task, is_mutating=True, group="review", scope_requirements=("review",)
    )
