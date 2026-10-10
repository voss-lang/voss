"""Read-only slash commands exposed to remote clients."""
from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from ..skill_registry import default_skill_registry
from ..subagents import default_subagent_registry, register_agent_files
from ..tools import attach_mcp_tools, make_toolset


class CommandInfo(BaseModel):
    name: str
    description: str


class CommandCatalog(BaseModel):
    v: int = 1
    commands: list[CommandInfo]


class CommandRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    args: list[str] = Field(default_factory=list, max_length=100)


class CommandResult(BaseModel):
    v: int = 1
    stdout: str = ""
    stderr: str = ""


COMMANDS = (
    CommandInfo(name="/tools", description="list built-in and MCP tools"),
    CommandInfo(name="/skills", description="list registered skills"),
    CommandInfo(name="/agents", description="list registered subagents"),
)


def _skills(cwd: Path) -> str:
    lines = []
    for entry in default_skill_registry(cwd).entries():
        kind = "local" if entry.instruction_path else "mut" if entry.mutating else "read"
        lines.append(f"  {entry.id:<16} {kind:<4} {entry.description}")
    return "\n".join(lines) or "(no skills)"


def _agents(cwd: Path) -> str:
    registry = default_subagent_registry()
    register_agent_files(registry, cwd)
    return "\n".join(f"  {spec.id:<16} {spec.description}" for spec in registry.entries()) or "(no agents)"


async def execute(cwd: Path, request: CommandRequest) -> CommandResult:
    if request.name not in {command.name for command in COMMANDS}:
        raise ValueError("Unknown command. Use /help for available commands.")
    if request.args:
        return CommandResult(stderr=f"usage: {request.name}")
    if request.name == "/skills":
        return CommandResult(stdout=await asyncio.to_thread(_skills, cwd))
    if request.name == "/agents":
        return CommandResult(stdout=await asyncio.to_thread(_agents, cwd))
    tools = await asyncio.to_thread(make_toolset, cwd, background_indexing=False)
    client = await attach_mcp_tools(tools, cwd)
    try:
        return CommandResult(stdout="\n".join(
            f"  {name} — {entry.description}" for name, entry in tools.items()
        ) or "(no tools)")
    finally:
        if client is not None:
            await client.aclose()
