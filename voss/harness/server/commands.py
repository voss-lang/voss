"""Read-only slash commands exposed to remote clients."""
from __future__ import annotations

import asyncio
from itertools import islice
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


class CodeHit(BaseModel):
    file: str
    line: int
    name: str
    language: str
    source: str
    snippet: str


class CodeResults(BaseModel):
    query: str
    items: list[CodeHit]
    truncated: bool


class CommandResult(BaseModel):
    v: int = 1
    stdout: str = ""
    stderr: str = ""
    code: CodeResults | None = None


COMMANDS = (
    CommandInfo(name="/tools", description="list built-in and MCP tools"),
    CommandInfo(name="/skills", description="list registered skills"),
    CommandInfo(name="/agents", description="list registered subagents"),
    CommandInfo(name="/symbol", description="find definitions: /symbol <name>"),
    CommandInfo(name="/refs", description="find references: /refs <name>"),
    CommandInfo(name="/refresh", description="rebuild the workspace code index"),
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
    if request.name in {"/symbol", "/refs", "/refresh"}:
        usage = request.name + (" <name>" if request.name != "/refresh" else "")
        expected = 0 if request.name == "/refresh" else 1
        if len(request.args) != expected or any(not a.strip() or a.startswith("-") for a in request.args):
            return CommandResult(stderr=f"usage: {usage}")
        return await asyncio.to_thread(lambda: asyncio.run(_code(cwd, request)))
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


async def _code(cwd: Path, request: CommandRequest) -> CommandResult:
    from ..code.service import CodeIntelService

    service = CodeIntelService(cwd)
    try:
        if request.name == "/refresh":
            result = await service.code_refresh()
            if result["result"] != "ok":
                return CommandResult(stderr=f"refresh failed: {result['message']}")
            summary = service.get_project_index_summary()
            text = "refreshed code index"
            if summary is not None:
                text += f": {summary.file_count} files, {summary.symbol_count} symbols"
            return CommandResult(stdout=text)

        symbol = request.args[0]
        if request.name == "/symbol":
            result = service.find_symbols(symbol, max_results=51)
        else:
            result = await service.find_references(symbol, max_results=51)
        if result["result"] == "error":
            return CommandResult(stderr=result["message"])

        items = []
        for item in result["items"]:
            path = (cwd / item["file"]).resolve()
            if not path.is_relative_to(cwd.resolve()):
                continue
            snippet = ""
            try:
                with path.open(encoding="utf-8", errors="replace") as source:
                    snippet = next(islice(source, item["line"] - 1, item["line"]), "").rstrip()[:240]
            except OSError:
                pass
            items.append(CodeHit(
                file=str(path.relative_to(cwd.resolve())), line=item["line"],
                name=item.get("name", symbol), language=item.get("language", "unknown"),
                source=item["source"], snippet=snippet,
            ))
        code = CodeResults(query=f"{request.name} {symbol}", items=items[:50], truncated=len(items) > 50)
        lines = [f"{hit.file}:{hit.line}  {hit.name} [{hit.source}]\n  {hit.snippet}" for hit in code.items]
        if code.truncated:
            lines.append("Showing the first 50 matches; refine the query.")
        return CommandResult(stdout="\n".join(lines) or f"no matches for {symbol}", code=code)
    finally:
        await service.aclose()
