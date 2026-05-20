"""Frozen value objects for the team / organizational cage (O2).

Implements the structural shell for OTEAM-04 (immutable cage metadata) and
OTEAM-08 (opaque board/ritual carriers). `compile_team` maps `TeamDecl` AST
from O2-01 into immutable `TeamConfig` + `SubagentRegistry`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from voss.ast_nodes import (
    BoardDecl,
    BudgetArg,
    CeilingDecl,
    Identifier,
    ListLit,
    RosterDecl,
    RosterRoleDecl,
    Span,
    StringLit,
    TeamAgentDecl,
    TeamDecl,
)

from .permissions import Mode, PermissionGate
from .skill.scope import _min_mode  # team compile reuse; see skill/scope.py:74
from .subagents import SubagentRegistry, SubagentSpec
from .tools import ToolEntry


class VossTeamConfigError(Exception):
    """Raised when team configuration is invalid or inconsistent (compile phase)."""

    def __init__(
        self,
        message: str,
        *,
        role_span: Span | None = None,
        ceiling_span: Span | None = None,
    ) -> None:
        super().__init__(message)
        self.role_span = role_span
        self.ceiling_span = ceiling_span


DEFAULT_ROSTER: tuple[str, ...] = ("backend", "frontend", "ui", "ai")


def default_team_role_defaults(role_name: str) -> tuple[str, str]:
    """Return `(description, role_prompt)` for a roster role.

    Placeholder defaults; full role prompts owned by O5 (EM loop).

    Built-ins match `DEFAULT_ROSTER`; unknown names use opaque fallbacks (open roster, OQ-02-A).
    """
    builtins: dict[str, tuple[str, str]] = {
        "backend": (
            "Backend engineer",
            "You specialize in APIs, persistence, and server-side logic.",
        ),
        "frontend": (
            "Frontend engineer",
            "You specialize in web clients, routing, and client-side state.",
        ),
        "ui": (
            "UI engineer",
            "You specialize in components, layouts, and design-quality UI.",
        ),
        "ai": (
            "AI / ML engineer",
            "You specialize in models, pipelines, and AI integrations.",
        ),
    }
    if role_name in builtins:
        return builtins[role_name]
    desc = f"Team role `{role_name}`"
    rp = f"You are `{role_name}` on this roster; follow EM instructions and ceiling policy."
    return (desc, rp)


EM_DESCRIPTION: str = "Engineering Manager (orchestrator)"
EM_ROLE_PROMPT: str = "<EM role prompt — populated in O5>"

# OQ-03-A: hybrid alias table (shorthand groups + exact tool names accepted separately).
TOOL_GROUP_ALIASES: dict[str, frozenset[str]] = {
    "fs": frozenset({"fs_read", "fs_write", "fs_edit", "fs_glob", "fs_grep"}),
    "test": frozenset({"shell_run"}),
    "shell": frozenset(
        {"shell_run", "shell_run_background", "shell_monitor", "shell_signal"}
    ),
    "net": frozenset({"web_fetch", "web_search"}),
    "git": frozenset({"git_status", "git_diff"}),
}


def gate_for_role(spec: SubagentSpec, base_gate: PermissionGate) -> PermissionGate:
    """Compile a per-role PermissionGate from a SubagentSpec.

    Cap-not-expand: when ``spec.mode`` is set, it caps ``base_gate.mode`` via
    :func:`voss.harness.skill.scope._min_mode`; it never widens permissions.

    Per-gate network: ``spec.net`` maps to ``allow_net`` explicitly (``True`` or
    ``False``), never ``None``, so specialist roles stay netless even when the
    process is started with ``--allow-net``.

    Subagent sessions do not use :class:`~voss.harness.edit_scope.EditScope`
    in this compile step (O5 may route per-role paths separately); ``edit_scope``
    is therefore always ``None`` here.
    """
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


def filter_toolset_for_role(
    spec: SubagentSpec,
    base_toolset: Mapping[str, ToolEntry],
) -> dict[str, ToolEntry]:
    """Return a subset of *base_toolset* based on ``spec.tools``.

    If ``spec.tools`` is ``None``, returns a shallow copy of the full toolset.

    Otherwise expands :data:`TOOL_GROUP_ALIASES` entries and treats any other
    string as an exact ``make_toolset`` key. ``web_fetch`` / ``web_search``
    appear in the result only when the ``net`` alias is included (or those names
    are listed explicitly).
    """
    if spec.tools is None:
        return dict(base_toolset)
    expanded: set[str] = set()
    for entry in spec.tools:
        if entry in TOOL_GROUP_ALIASES:
            expanded |= set(TOOL_GROUP_ALIASES[entry])
        else:
            expanded.add(entry)
    return {name: te for name, te in base_toolset.items() if name in expanded}


@dataclass(frozen=True, slots=True)
class TeamRoleScope:
    globs: tuple[str, ...]

    def is_contained_in(self, other: TeamRoleScope | None) -> bool:
        """Return True if every glob in *self* is within *other*'s globs.

        **Heuristic (OQ-02-C):** prefix up to the first wildcard character
        (`*`, `?`, `[`). Each role glob's literal prefix must satisfy
        `startswith` some ceiling glob's literal prefix (after stripping
        trailing ``/``).

        **Limitations:** Patterns like ``**/test/**`` vs ``src/**`` are not
        modeled faithfully; containment may disagree with intuitive set
        inclusion. Prefer simple `prefix/**`-style ceilings and roles.
        """
        if other is None:
            return True

        def _prefix(glob: str) -> str:
            for sep in ("*", "?", "["):
                idx = glob.find(sep)
                if idx >= 0:
                    return glob[:idx].rstrip("/")
            return glob.rstrip("/")

        other_ps = [_prefix(o) for o in other.globs]

        for self_g in self.globs:
            self_p = _prefix(self_g)
            if not any(self_p.startswith(op) for op in other_ps):
                return False
        return True


@dataclass(frozen=True, slots=True)
class TeamCeiling:
    budget_tokens: int | None
    scope: TeamRoleScope | None
    latency_seconds: int | None


@dataclass(frozen=True, slots=True)
class TeamPolicy:
    p: object | None


@dataclass(frozen=True, slots=True)
class BoardSpec:
    raw_items: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class RitualSpec:
    name: str
    raw_kvs: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class TeamConfig:
    name: str
    ceiling: TeamCeiling
    policy: TeamPolicy
    em_agent_id: str | None
    roster_ids: frozenset[str]
    board: BoardSpec | None
    rituals: tuple[RitualSpec, ...]


@dataclass(frozen=True, slots=True)
class TeamRunContext:
    """O2→O3 hand-off shape — dataclass shell only."""

    team_config: TeamConfig
    registry: SubagentRegistry
    base_gate: PermissionGate


def _options_dict(opts: Iterable[tuple[str, object]]) -> dict[str, object]:
    return {k: v for k, v in opts}


def _parse_scope_literal(val: object) -> TeamRoleScope | None:
    """Build `TeamRoleScope` from roster/ceiling-style scope value or None."""
    if val is None:
        return None
    if isinstance(val, StringLit):
        return TeamRoleScope((val.value,))
    if isinstance(val, ListLit):
        globs: list[str] = []
        for it in val.items:
            if isinstance(it, StringLit):
                globs.append(it.value)
            else:
                raise VossTeamConfigError(
                    f"scope list entries must be string literals; got {type(it).__name__}"
                )
        return TeamRoleScope(tuple(globs))
    raise VossTeamConfigError(
        f"scope must be a string literal or string list; got {type(val).__name__}"
    )


def _parse_budget_value(val: object, ceiling: TeamCeiling) -> int | None:
    if val is None:
        return None
    if isinstance(val, BudgetArg) and val.unit == "tokens":
        return int(val.value)
    if isinstance(val, StringLit):
        raw = val.value.strip().lower()
        if raw == "ceiling":
            return ceiling.budget_tokens
    raise VossTeamConfigError(
        f"budget must be a token BudgetArg or ceiling string sentinel; got {type(val).__name__}"
    )


def _parse_tools_value(val: object) -> frozenset[str]:
    """Normalize tools to frozenset; accept list literal or single string."""
    if val is None:
        return frozenset()
    names: list[str] = []
    if isinstance(val, ListLit):
        for it in val.items:
            if isinstance(it, StringLit):
                names.append(it.value)
            else:
                raise VossTeamConfigError(
                    f"tools list entries must be string literals; got {type(it).__name__}"
                )
        return frozenset(names)
    if isinstance(val, StringLit):
        return frozenset([val.value])
    raise VossTeamConfigError(
        f"tools must be a string literal or string list; got {type(val).__name__}"
    )


def _parse_mode_value(val: object) -> Mode | None:
    if val is None:
        return None
    if isinstance(val, StringLit):
        m = val.value
        if m not in ("plan", "edit", "auto"):
            raise VossTeamConfigError(
                f"unknown mode '{m}' (expected: plan, edit, auto)",
                role_span=None,
            )
        return m  # type: ignore[return-value]
    raise VossTeamConfigError(f"mode must be a string literal; got {type(val).__name__}")


def _parse_model_value(val: object) -> str | None:
    if val is None:
        return None
    if isinstance(val, StringLit):
        return val.value
    raise VossTeamConfigError(f"model must be a string literal; got {type(val).__name__}")


def subagent_spec_from_role(
    *,
    role_name: str,
    role_decl_span: Span,
    kvs: Mapping[str, object],
    ceiling: TeamCeiling,
    ceiling_ast: CeilingDecl | None,
) -> SubagentSpec:
    parsed_scope_opt = (
        _parse_scope_literal(kvs["scope"]) if "scope" in kvs else None
    )

    scope: TeamRoleScope | None = (
        parsed_scope_opt if parsed_scope_opt is not None else ceiling.scope
    )

    if scope is not None and ceiling.scope is not None:
        if not scope.is_contained_in(ceiling.scope):
            ceil_msg = ceiling.scope.globs
            raise VossTeamConfigError(
                f"role {role_name!r} scope {scope.globs} is outside ceiling scope {ceil_msg}",
                role_span=role_decl_span,
                ceiling_span=ceiling_ast.span if ceiling_ast else None,
            )

    budget_raw = _parse_budget_value(kvs.get("budget"), ceiling) if "budget" in kvs else None
    budget: int | None = budget_raw
    if budget is not None and ceiling.budget_tokens is not None:
        if budget > ceiling.budget_tokens:
            raise VossTeamConfigError(
                f"role {role_name!r} budget {budget} exceeds ceiling "
                f"budget_tokens {ceiling.budget_tokens}",
                role_span=role_decl_span,
                ceiling_span=ceiling_ast.span if ceiling_ast else None,
            )

    tools = _parse_tools_value(kvs["tools"]) if "tools" in kvs else frozenset()
    net = "net" in tools

    model = _parse_model_value(kvs["model"]) if "model" in kvs else None
    mode = _parse_mode_value(kvs["mode"]) if "mode" in kvs else None

    description, rp = default_team_role_defaults(role_name)

    tool_fs = tools if tools else None
    return SubagentSpec(
        id=role_name,
        description=description,
        role_prompt=rp,
        model=model,
        mode=mode,
        scope=scope,
        budget=budget,
        tools=tool_fs,
        net=net,
    )


def subagent_spec_from_agent(
    agent_decl: TeamAgentDecl,
    ceiling: TeamCeiling,
    ceiling_ast: CeilingDecl | None,
) -> SubagentSpec:
    """Build a `SubagentSpec` from a team `agent` block.

    The EM orchestrator receives the ceiling scope envelope: ``scope`` of
    ``"all"`` or a missing scope key is compiled to ``ceiling.scope``.
    Narrower declarative scopes that remain within the ceiling may be stored
    as declared (specialists typically tighten); the EM differs from roster
    roles in that widening to the ceiling is allowed here.
    """
    kvs = _options_dict(agent_decl.options)

    parsed_scope_opt = (
        _parse_scope_literal(kvs["scope"]) if "scope" in kvs else None
    )

    scope: TeamRoleScope | None
    all_sentinel = isinstance(parsed_scope_opt, TeamRoleScope) and (
        len(parsed_scope_opt.globs) == 1
        and parsed_scope_opt.globs[0].strip().lower() == "all"
    )
    if parsed_scope_opt is None or all_sentinel:
        scope = ceiling.scope
    else:
        scope = parsed_scope_opt
        if ceiling.scope is not None and scope is not None:
            if not scope.is_contained_in(ceiling.scope):
                raise VossTeamConfigError(
                    f"agent {agent_decl.name!r} scope {scope.globs} is "
                    f"outside ceiling scope {ceiling.scope.globs}",
                    role_span=agent_decl.span,
                    ceiling_span=ceiling_ast.span if ceiling_ast else None,
                )

    budget_raw = _parse_budget_value(kvs["budget"], ceiling) if "budget" in kvs else None

    budget: int | None = budget_raw
    if budget is not None and ceiling.budget_tokens is not None:
        if budget > ceiling.budget_tokens:
            raise VossTeamConfigError(
                f"agent {agent_decl.name!r} budget {budget} exceeds ceiling "
                f"budget_tokens {ceiling.budget_tokens}",
                role_span=agent_decl.span,
                ceiling_span=ceiling_ast.span if ceiling_ast else None,
            )

    tools = _parse_tools_value(kvs["tools"]) if "tools" in kvs else frozenset()
    net = "net" in tools

    model = _parse_model_value(kvs["model"]) if "model" in kvs else None
    mode = _parse_mode_value(kvs["mode"]) if "mode" in kvs else None

    return SubagentSpec(
        id=agent_decl.name,
        description=EM_DESCRIPTION,
        role_prompt=EM_ROLE_PROMPT,
        model=model,
        mode=mode,
        scope=scope,
        budget=budget,
        tools=tools if tools else None,
        net=net,
    )


def compile_team(decl: TeamDecl) -> tuple[TeamConfig, SubagentRegistry]:
    """Compile parsed `TeamDecl` into frozen runtime config + populated registry."""

    if decl.ceiling is None:
        raise VossTeamConfigError(f"team {decl.name!r} missing ceiling at compile")

    c_ast = decl.ceiling
    ceiling_scope: TeamRoleScope | None = (
        TeamRoleScope(c_ast.scope) if c_ast.scope else None
    )
    ceiling_vo = TeamCeiling(
        budget_tokens=c_ast.budget,
        scope=ceiling_scope,
        latency_seconds=c_ast.latency_seconds,
    )

    registry = SubagentRegistry()

    roster_id_set: set[str] = set()

    em_agent_id: str | None = None
    for agent_decl in decl.agents:
        if em_agent_id is None:
            em_agent_id = agent_decl.name
        spec_a = subagent_spec_from_agent(agent_decl, ceiling_vo, c_ast)
        registry.register(spec_a)
        roster_id_set.add(agent_decl.name)

    for roster in decl.rosters:
        for role in roster.roles:
            ks = _options_dict(role.options)
            spec_r = subagent_spec_from_role(
                role_name=role.name,
                role_decl_span=role.span,
                kvs=ks,
                ceiling=ceiling_vo,
                ceiling_ast=c_ast,
            )
            registry.register(spec_r)
            roster_id_set.add(role.name)

    board_spec: BoardSpec | None = None
    if decl.board is not None:
        bd: BoardDecl = decl.board
        board_spec = BoardSpec(raw_items=bd.items)

    rituals = tuple(RitualSpec(name=r.name, raw_kvs=r.kvs) for r in decl.rituals)

    config = TeamConfig(
        name=decl.name,
        ceiling=ceiling_vo,
        policy=TeamPolicy(p=decl.policy),
        em_agent_id=em_agent_id,
        roster_ids=frozenset(roster_id_set),
        board=board_spec,
        rituals=rituals,
    )

    return config, registry
