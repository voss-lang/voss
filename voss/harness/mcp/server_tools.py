"""MCP server tool advertisement and gate-enforced dispatch helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Mapping

from voss.harness.mcp.config import McpConfigError, McpServerExposureConfig

if TYPE_CHECKING:
    from voss.harness.skill_registry import SkillEntry
    from voss.harness.tools import ToolEntry

DEFAULT_LOW_LEVEL_TOOLS = (
    "fs_read",
    "fs_glob",
    "fs_grep",
    "voss_check",
    "git_status",
    "git_diff",
)

CallToolResult = dict[str, Any]


def resolve_tool_names(
    exposure: McpServerExposureConfig | None,
    available_tools: Mapping[str, Any],
) -> list[str]:
    exposed = "*" if exposure is None else exposure.exposed_tools
    if exposed == "*":
        return [name for name in DEFAULT_LOW_LEVEL_TOOLS if name in available_tools]

    names: list[str] = []
    for name in exposed:
        if name not in available_tools:
            raise McpConfigError(f"unknown tool: {name}")
        names.append(name)
    return names


def resolve_skill_ids(
    exposure: McpServerExposureConfig | None,
    skill_registry: Any,
) -> list[str]:
    exposed = "*" if exposure is None else exposure.exposed_skills
    available = set(skill_registry.ids())
    if exposed == "*":
        return skill_registry.ids()

    ids: list[str] = []
    for skill_id in exposed:
        if skill_id not in available:
            raise McpConfigError(f"unknown skill: {skill_id}")
        ids.append(skill_id)
    return ids


def build_tool_descriptors(
    tools: Mapping[str, Any],
    skill_registry: Any,
    exposure: McpServerExposureConfig | None,
) -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = []
    for name in resolve_tool_names(exposure, tools):
        entry: ToolEntry = tools[name]
        descriptors.append(
            {
                "name": entry.descriptor.name,
                "description": entry.description,
                "inputSchema": entry.parameters,
                "annotations": {"destructiveHint": bool(entry.is_mutating)},
            }
        )

    for skill_id in resolve_skill_ids(exposure, skill_registry):
        entry: SkillEntry | None = skill_registry.get(skill_id)
        if entry is None:
            raise McpConfigError(f"unknown skill: {skill_id}")
        descriptors.append(
            {
                "name": entry.id,
                "description": entry.description,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "args": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": [],
                },
                "annotations": {"destructiveHint": bool(entry.mutating)},
            }
        )
    return descriptors


def build_tool_dispatch(
    tools: Mapping[str, Any],
    skill_registry: Any,
    skill_dispatch: Callable[[str, list[str]], Awaitable[str]] | None,
    gate: Any,
) -> Callable[[str, dict[str, Any]], Awaitable[CallToolResult]]:
    async def dispatch(name: str, args: dict[str, Any]) -> CallToolResult:
        if name in tools:
            entry = tools[name]
            is_mutating = bool(entry.is_mutating)
            is_network = bool(entry.is_network)
            allowed, reason = gate.check(
                name, args, is_mutating=is_mutating, is_network=is_network
            )
            if not allowed:
                return _text_result(reason, is_error=True)
            try:
                result = await entry.invoke(**args)
            except Exception as exc:  # noqa: BLE001
                return _text_result(f"<error: {exc}>", is_error=True)
            return _text_result(str(result), is_error=False)

        skill = skill_registry.get(name)
        if skill is None:
            return _text_result(f"unknown tool: {name}", is_error=True)

        allowed, reason = gate.check(
            name, args, is_mutating=bool(skill.mutating), is_network=False
        )
        if not allowed:
            return _text_result(reason, is_error=True)
        if skill_dispatch is None:
            return _text_result("skill dispatch not wired (M12-03)", is_error=True)
        try:
            text = await skill_dispatch(name, _skill_args(args))
        except Exception as exc:  # noqa: BLE001
            return _text_result(f"<error: {exc}>", is_error=True)
        return _text_result(text, is_error=False)

    return dispatch


def _text_result(text: str, *, is_error: bool) -> CallToolResult:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _skill_args(args: Mapping[str, Any]) -> list[str]:
    raw = args.get("args", []) or []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return [str(raw)]
