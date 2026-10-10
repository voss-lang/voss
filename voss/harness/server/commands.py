"""Read-only slash commands exposed to remote clients."""
from __future__ import annotations

import asyncio
from itertools import islice
from pathlib import Path

from pydantic import BaseModel, Field

from .. import session as session_store
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


class InspectionResult(BaseModel):
    title: str
    text: str


class CommandResult(BaseModel):
    v: int = 1
    stdout: str = ""
    stderr: str = ""
    code: CodeResults | None = None
    inspection: InspectionResult | None = None


COMMANDS = (
    CommandInfo(name="/tools", description="list built-in and MCP tools"),
    CommandInfo(name="/skills", description="list registered skills"),
    CommandInfo(name="/agents", description="list registered subagents"),
    CommandInfo(name="/symbol", description="find definitions: /symbol <name>"),
    CommandInfo(name="/refs", description="find references: /refs <name>"),
    CommandInfo(name="/refresh", description="rebuild the workspace code index"),
    CommandInfo(name="/probable", description="inspect recorded decisions: /probable [session] [--decision N]"),
    CommandInfo(name="/btrace", description="inspect recorded budget timeline: /btrace [session]"),
    CommandInfo(name="/vdiff", description="show source vs generated Python: /vdiff <file.voss>"),
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


async def execute(cwd: Path, request: CommandRequest, *, record: session_store.SessionRecord) -> CommandResult:
    if request.name not in {command.name for command in COMMANDS}:
        raise ValueError("Unknown command. Use /help for available commands.")
    if request.name in {"/probable", "/btrace", "/vdiff"}:
        return await asyncio.to_thread(_inspect, cwd, request, record)
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


def _inspect(cwd: Path, request: CommandRequest, record: session_store.SessionRecord) -> CommandResult:
    from voss.codegen import CodegenError
    from voss.exceptions import VossParseError

    from ..voss_diff import render_voss_py_diff
    from ..voss_inspect import render_budget_timeline, render_decision_sequence

    name, args = request.name, list(request.args)
    usage = {
        "/probable": "usage: /probable [session] [--decision N]",
        "/btrace": "usage: /btrace [session]",
        "/vdiff": "usage: /vdiff <file.voss>",
    }[name]
    decision_index = None
    if name == "/probable" and "--decision" in args:
        index = args.index("--decision")
        if index + 1 == len(args):
            return CommandResult(stderr=usage)
        try:
            decision_index = int(args[index + 1])
        except ValueError:
            return CommandResult(stderr="--decision must be an integer")
        if decision_index < 0:
            return CommandResult(stderr="--decision must be non-negative")
        del args[index:index + 2]
    if len(args) > 1 or any(not a.strip() or a.startswith("-") for a in args) or (name == "/vdiff" and not args):
        return CommandResult(stderr=usage)

    try:
        if name == "/vdiff":
            title = "Voss / Python"
            text = render_voss_py_diff(cwd / args[0], cwd=cwd)
        else:
            if args and args[0] != record.id:
                record, _ = session_store.load(args[0], cwd=cwd)
                if Path(record.cwd).resolve() != cwd.resolve():
                    raise ValueError("session belongs to a different workspace")
            title = "Probable decision" if name == "/probable" else "Budget trace"
            if not record.runs:
                text = "No recorded runs. Run a task first."
            elif name == "/probable":
                text = render_decision_sequence(record.runs[-1], decision_index=decision_index)
            else:
                text = render_budget_timeline(record.runs[-1])
    except (OSError, ValueError, IndexError, VossParseError, CodegenError) as exc:
        return CommandResult(stderr=f"{name} failed: {exc}")
    return CommandResult(stdout=text, inspection=InspectionResult(title=title, text=text))


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
