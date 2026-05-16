---
phase: T3-network-surface
plan: 07
type: execute
wave: 2
depends_on: [T3-01, T3-02, T3-03]
files_modified:
  - voss/harness/mcp/__init__.py
  - voss/harness/mcp/config.py
  - voss/harness/mcp/client.py
  - voss/harness/mcp/registry.py
  - voss/harness/cognition_schemas.py
  - voss/harness/tools.py
  - tests/harness/mcp/test_mcp_config.py
  - tests/harness/mcp/test_mcp_client.py
  - tests/harness/mcp/test_mcp_scope.py
autonomous: true
requirements: [NET-03, NET-04, NET-06]
must_haves:
  truths:
    - "voss/harness/mcp/__init__.py exists as a package init (re-exports McpClient, McpServerConfig, load_mcp_config, register_mcp_tools)"
    - "voss/harness/mcp/config.py defines pydantic McpServerConfig and McpConfig with model_config = STRICT; loads .voss/mcp.yml via yaml.safe_load + model_validate"
    - ".voss/mcp.yml loader supports ${VAR} env-var interpolation in command/args (raises McpConfigError if required var is unset); {cwd} templating substituted by Path.cwd() at launch time; per-server timeout_s default 30.0; per-server env: list[str] | None allowlist"
    - "voss/harness/mcp/client.py defines McpClient.ensure_launched(server_name) that asyncio.create_subprocess_exec's the server with stdin/stdout/stderr=PIPE; runs the three-step handshake (initialize → server response → notifications/initialized) targeting protocolVersion '2025-11-25'; then sends tools/list and caches the response"
    - "McpClient registers each spawned subprocess with lifecycle.register_subprocess for SIGTERM+5s+SIGKILL reap"
    - "voss/harness/mcp/registry.py defines register_mcp_tools(config, permissions, mcp_client) -> dict[str, ToolEntry] that calls tools/list on each configured server, wraps each advertised tool as a ToolEntry with namespaced key '{server}__{tool}', is_network=True, and is_mutating sourced from annotations.destructiveHint OR True (safe default) per D-11"
    - "MCP per-server scope: PermissionsConfig gains mcp: dict[str, McpScope] field (McpScope = Literal['plan','edit','auto']); under 'plan' (default), all MCP tools register as is_mutating=False; under 'edit'/'auto', is_mutating reads from destructiveHint with absent → True fallback"
    - "Each MCP tool invocation emits mcp.request before and mcp.response after; tool args redacted via redact_tool_args; transport errors return '<error: mcp transport: connection lost>'; server-side tool errors return '<error: mcp tool: {message}>'"
    - "NET-03a/b/c + NET-04a/b/c/d acceptance tests all pass (7 mcp tests un-skipped from T3-01 placeholders)"
  artifacts:
    - path: "voss/harness/mcp/__init__.py"
      provides: "Re-exports of McpClient, McpServerConfig, McpConfig, load_mcp_config, register_mcp_tools, McpConfigError"
      contains: "from voss.harness.mcp"
    - path: "voss/harness/mcp/config.py"
      provides: "Pydantic McpServerConfig (command, args, timeout_s, env) + McpConfig (servers: dict[str, McpServerConfig]) + load_mcp_config(cwd) -> McpConfig | None; ${VAR} + {cwd} substitution"
      contains: "class McpServerConfig"
    - path: "voss/harness/mcp/client.py"
      provides: "class McpClient with ensure_launched, call_tool, _handshake; registers subprocess with lifecycle"
      contains: "class McpClient"
    - path: "voss/harness/mcp/registry.py"
      provides: "register_mcp_tools(config, permissions, mcp_client) returns dict[str, ToolEntry] with namespaced keys; _is_mutating_from_descriptor(tool, scope) helper"
      contains: "def register_mcp_tools"
    - path: "voss/harness/cognition_schemas.py"
      provides: "McpScope = Literal['plan','edit','auto']; PermissionsConfig.mcp: dict[str, McpScope] = Field(default_factory=dict)"
      contains: "McpScope"
    - path: "voss/harness/tools.py"
      provides: "make_toolset returns dict merged with register_mcp_tools(config, permissions, mcp_client) output (when net is provided and mcp_config exists)"
      contains: "register_mcp_tools"
  key_links:
    - from: "voss/harness/mcp/client.py:ensure_launched"
      to: "voss/harness/lifecycle.py:register_subprocess"
      via: "after asyncio.create_subprocess_exec succeeds, call lifecycle.register_subprocess(proc) so reap_all() handles termination"
      pattern: "lifecycle\\.register_subprocess"
    - from: "voss/harness/mcp/registry.py:_is_mutating_from_descriptor"
      to: "PermissionsConfig.mcp scope value"
      via: "plan scope → is_mutating=False; edit/auto scope → annotations.destructiveHint (absent → True)"
      pattern: "destructiveHint"
    - from: "voss/harness/mcp/client.py:_handshake"
      to: "MCP protocol 2025-11-25"
      via: "initialize → server response with protocolVersion check → notifications/initialized → tools/list"
      pattern: "2025-11-25|notifications/initialized"
---

<objective>
Land the MCP stdio client subsystem (NET-03 + NET-04) — the third and largest network surface. Three files under voss/harness/mcp/ per D-01 (client.py, config.py, registry.py) plus __init__.py. Lift the asyncio.subprocess JSON-RPC pattern from T3-RESEARCH Pattern 1 (newline-delimited JSON-RPC 2.0 over stdin/stdout). Wire MCP-discovered tools as is_network=True ToolEntry records with namespaced keys (`{server}__{tool}`) and is_mutating sourced from the destructiveHint annotation per D-11. Extend PermissionsConfig with the `mcp:` scope dict (NET-04). Seven acceptance tests un-skipped.

Purpose: MCP is the third leg of the network surface stool. T3-05/T3-06 exercise the web tools through NetSession; T3-07 exercises a completely different transport (stdio subprocess vs. httpx) but reuses the same gate (allow_net), the same telemetry primitives (redact_url applied to any URL fields), and the same lifecycle hook (register_subprocess + SIGTERM+5s+SIGKILL reap). After T3-07, the agent loop can call MCP tools as if they were native — namespaced by server prefix. T3-08 builds the CLI surface on top (voss mcp list/call). T3-09 validates end-to-end against the pinned reference filesystem server.

Output: 4 new files under voss/harness/mcp/; PermissionsConfig.mcp field; tools.py make_toolset merges MCP tools; 7 mcp/ tests un-skipped covering config load, lazy launch + handshake, SIGTERM reap, all 4 NET-04 scope cases.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T3-network-surface/T3-SPEC.md
@.planning/phases/T3-network-surface/T3-CONTEXT.md
@.planning/phases/T3-network-surface/T3-RESEARCH.md
@.planning/phases/T3-network-surface/T3-PATTERNS.md
@voss/harness/cognition.py
@voss/harness/cognition_schemas.py
@voss/harness/tools.py
@voss/harness/permissions.py
@voss/harness/lifecycle.py
@voss/harness/telemetry.py
</context>

<interfaces>
File: voss/harness/mcp/__init__.py — re-exports:
```
from voss.harness.mcp.config import McpServerConfig, McpConfig, load_mcp_config, McpConfigError
from voss.harness.mcp.client import McpClient
from voss.harness.mcp.registry import register_mcp_tools
__all__ = ["McpServerConfig", "McpConfig", "load_mcp_config", "McpConfigError", "McpClient", "register_mcp_tools"]
```

File: voss/harness/mcp/config.py — schema + loader (per T3-PATTERNS section "voss/harness/mcp/config.py" + RESEARCH Pattern + D-04):
```
from __future__ import annotations
import os, re
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field, ValidationError

STRICT = {"extra": "forbid"}

class McpConfigError(Exception): ...

class McpServerConfig(BaseModel):
    model_config = STRICT
    command: list[str]                       # required; ${VAR} and {cwd} substituted at launch
    args: list[str] = Field(default_factory=list)
    timeout_s: float = 30.0
    env: Optional[list[str]] = None          # None = inherit full parent env; [] = empty env

class McpConfig(BaseModel):
    model_config = STRICT
    servers: dict[str, McpServerConfig] = Field(default_factory=dict)

_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

def _substitute(s: str, *, cwd: Path) -> str:
    # Replace ${VAR} with env value; raise McpConfigError if any var is unset.
    # Replace {cwd} with str(cwd).
    def repl(m):
        var = m.group(1)
        val = os.environ.get(var)
        if val is None:
            raise McpConfigError(f"required env var {var!r} is unset")
        return val
    s = _VAR_RE.sub(repl, s)
    s = s.replace("{cwd}", str(cwd))
    return s

def substitute_server(config: McpServerConfig, *, cwd: Path) -> McpServerConfig:
    # Return a new McpServerConfig with command/args substituted; env unchanged (it's a key allowlist)
    new_cmd = [_substitute(c, cwd=cwd) for c in config.command]
    new_args = [_substitute(a, cwd=cwd) for a in config.args]
    return McpServerConfig(command=new_cmd, args=new_args, timeout_s=config.timeout_s, env=config.env)

def load_mcp_config(cwd: Path) -> "McpConfig | None":
    # Reads {cwd}/.voss/mcp.yml; returns None if absent.
    # On parse/validate failure: raise McpConfigError with the underlying message.
    path = cwd / ".voss" / "mcp.yml"
    if not path.exists():
        return None
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise McpConfigError(f"{path}: invalid YAML: {e}") from e
    try:
        return McpConfig.model_validate(raw)
    except ValidationError as e:
        raise McpConfigError(f"{path}: validation error: {e}") from e
```

File: voss/harness/mcp/client.py — stdio JSON-RPC client. Lift T3-RESEARCH Code Examples "Complete MCP handshake + tools/list". Class:
```
import asyncio, json, subprocess, time
from voss.harness import lifecycle, telemetry

class McpClient:
    def __init__(self, config: McpConfig) -> None:
        self._config = config
        self._procs: dict[str, asyncio.subprocess.Process] = {}
        self._tools_cache: dict[str, list[dict]] = {}
        self._next_id = 1
        self._cwd: Path = Path.cwd()

    def set_cwd(self, cwd: Path) -> None:
        self._cwd = cwd

    async def ensure_launched(self, server_name: str) -> asyncio.subprocess.Process:
        # Idempotent: if already launched and alive, return cached proc.
        if server_name in self._procs:
            proc = self._procs[server_name]
            if proc.returncode is None:
                return proc
            # process died; restart
            del self._procs[server_name]
        if server_name not in self._config.servers:
            raise McpConfigError(f"unknown MCP server: {server_name!r}")
        server = substitute_server(self._config.servers[server_name], cwd=self._cwd)
        # Build env per allowlist
        env = None if server.env is None else {k: os.environ[k] for k in server.env if k in os.environ}
        proc = await asyncio.create_subprocess_exec(
            *server.command, *server.args,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(self._cwd), env=env,
        )
        # Handshake: initialize → server response → initialized notification → tools/list
        await self._handshake(proc, server.timeout_s)
        tools = await self._tools_list(proc, server.timeout_s)
        self._tools_cache[server_name] = tools
        self._procs[server_name] = proc
        lifecycle.register_subprocess(proc)  # for SIGTERM+5s+SIGKILL reap on shutdown
        return proc

    async def list_tools(self, server_name: str) -> list[dict]:
        await self.ensure_launched(server_name)
        return self._tools_cache[server_name]

    async def call_tool(self, server_name: str, tool_name: str, args: dict) -> dict:
        proc = await self.ensure_launched(server_name)
        msg_id = self._next_id; self._next_id += 1
        req = {"jsonrpc": "2.0", "id": msg_id, "method": "tools/call",
               "params": {"name": tool_name, "arguments": args}}
        # emit mcp.request
        if telemetry.enabled():
            telemetry.emit("mcp.request", "info", data={
                "server": server_name, "tool": tool_name,
                "args": telemetry.redact_tool_args(args), "started_at": time.monotonic()
            })
        started = time.monotonic()
        try:
            await self._write(proc, req)
            resp = await self._read(proc, timeout=self._config.servers[server_name].timeout_s)
        except Exception as e:
            duration_ms = int((time.monotonic() - started) * 1000)
            if telemetry.enabled():
                telemetry.emit("mcp.response", "warn", data={
                    "server": server_name, "tool": tool_name, "status": "error",
                    "duration_ms": duration_ms, "error": str(e)
                })
            return {"isError": True, "content": [{"type": "text", "text": f"<error: mcp transport: {type(e).__name__}: {e}>"}]}
        duration_ms = int((time.monotonic() - started) * 1000)
        if "error" in resp:
            err_msg = resp["error"].get("message", "unknown")
            if telemetry.enabled():
                telemetry.emit("mcp.response", "warn", data={
                    "server": server_name, "tool": tool_name, "status": "error",
                    "duration_ms": duration_ms, "error": err_msg
                })
            return {"isError": True, "content": [{"type": "text", "text": f"<error: mcp tool: {err_msg}>"}]}
        if telemetry.enabled():
            telemetry.emit("mcp.response", "info", data={
                "server": server_name, "tool": tool_name, "status": "ok",
                "duration_ms": duration_ms, "error": None
            })
        return resp.get("result", {})

    async def _handshake(self, proc, timeout_s: float) -> None:
        init_req = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "voss-harness", "version": "0.2"}
        }}
        await self._write(proc, init_req)
        resp = await self._read(proc, timeout=timeout_s)
        # Protocol-version sanity check (warn but proceed if mismatch — many servers negotiate down)
        if resp.get("result", {}).get("protocolVersion") != "2025-11-25":
            # Permissive: log via stderr or telemetry; don't fail handshake
            pass
        # Step 2: initialized notification
        await self._write(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    async def _tools_list(self, proc, timeout_s: float) -> list[dict]:
        req = {"jsonrpc": "2.0", "id": 99999, "method": "tools/list", "params": {}}
        await self._write(proc, req)
        resp = await self._read(proc, timeout=timeout_s)
        return resp.get("result", {}).get("tools", [])

    async def _write(self, proc, msg: dict) -> None:
        line = json.dumps(msg, separators=(",", ":")) + "\n"
        proc.stdin.write(line.encode("utf-8"))
        await proc.stdin.drain()

    async def _read(self, proc, *, timeout: float) -> dict:
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
        if not line:
            raise McpConfigError("MCP server closed stdout unexpectedly")
        return json.loads(line.decode("utf-8"))
```

File: voss/harness/mcp/registry.py — adapter (D-11):
```
from voss.harness.tools import ToolEntry, ToolDescriptor

def _is_mutating_from_descriptor(tool: dict, scope: str) -> bool:
    """Per D-11: plan scope → False; edit/auto → annotations.destructiveHint (absent → True)."""
    if scope == "plan":
        return False
    annotations = tool.get("annotations") or {}
    return annotations.get("destructiveHint", True)  # safe default: True

def register_mcp_tools(
    config: "McpConfig",
    permissions_mcp: dict[str, str],  # the mcp: block from PermissionsConfig; missing key → "plan"
    mcp_client: "McpClient",
) -> dict[str, ToolEntry]:
    """Walk every configured server, list tools, wrap each as a namespaced ToolEntry.
    Server launch is lazy: we read from mcp_client._tools_cache which is populated on first
    ensure_launched. To populate without launching, the caller drives ensure_launched explicitly
    or accepts the lazy semantics (tools register only after first server contact)."""
    entries: dict[str, ToolEntry] = {}
    for server_name, server_config in config.servers.items():
        scope = permissions_mcp.get(server_name, "plan")
        tools = mcp_client._tools_cache.get(server_name, [])
        for tool in tools:
            tool_name = tool["name"]
            key = f"{server_name}__{tool_name}"
            is_mutating = _is_mutating_from_descriptor(tool, scope)
            # Build a ToolDescriptor wrapper whose invoke calls mcp_client.call_tool
            descriptor = _make_mcp_descriptor(server_name, tool_name, tool, mcp_client)
            entries[key] = ToolEntry(descriptor=descriptor, is_mutating=is_mutating, is_network=True)
    return entries
```

`_make_mcp_descriptor` builds a ToolDescriptor with appropriate name/description/parameters/invoke pointing at `mcp_client.call_tool(server, tool, args)`. Read voss/harness/tools.py for the ToolDescriptor constructor signature — `grep -n "class ToolDescriptor\|@tool" voss/harness/tools.py` to confirm shape. The `invoke` returns the text content from result["content"] OR an error envelope from `result["isError"]==True`.

Edit voss/harness/cognition_schemas.py (line 51 PermissionsConfig):
```
McpScope = Literal["plan", "edit", "auto"]

class PermissionsConfig(BaseModel):
    model_config = STRICT
    tool_policy: ToolPolicy = Field(default_factory=ToolPolicy)
    path_scopes: list[PathScope] = Field(default_factory=list)
    mcp: dict[str, McpScope] = Field(default_factory=dict)  # T3-07 / NET-04
```

Edit voss/harness/tools.py: extend make_toolset to merge MCP-discovered tools when net is provided AND .voss/mcp.yml exists. The merge happens after the static dict is constructed:
```
def make_toolset(cwd: Path, *, net: "NetSession | None" = None) -> dict[str, ToolEntry]:
    # ... existing tool definitions ...
    result = { ... existing entries ... }  # T3-05/T3-06 added web_fetch, web_search
    # T3-07: MCP merge — lazy, only if net is provided (which signals real runtime not unit test)
    if net is not None:
        try:
            from voss.harness.mcp import load_mcp_config, McpClient, register_mcp_tools
            from voss.harness.cognition import load_permissions
            mcp_config = load_mcp_config(cwd)
            if mcp_config is not None and mcp_config.servers:
                permissions = load_permissions(cwd)  # existing loader; returns PermissionsConfig
                mcp_scope_block = permissions.mcp if permissions else {}
                client = McpClient(mcp_config)
                client.set_cwd(cwd)
                # Eager launch each server to populate _tools_cache so register_mcp_tools sees them
                # PER D-02 lazy semantics: only launch servers that the agent will actually call.
                # CHOICE: populate cache on first invocation via ToolEntry wrapper; do NOT eagerly launch here.
                # That means register_mcp_tools is called only AFTER the first call_tool happens for a server.
                # SIMPLER for v1: eagerly launch all configured servers at make_toolset time.
                # PICK: eagerly launch (simpler; matches D-02 spirit since make_toolset itself is lazy
                # at agent boot — only happens once per session).
                import asyncio
                async def _launch_all():
                    for server_name in mcp_config.servers:
                        try:
                            await client.ensure_launched(server_name)
                        except Exception:
                            pass  # log via telemetry; do not block startup
                asyncio.run(_launch_all())  # synchronous boundary at make_toolset boundary
                mcp_entries = register_mcp_tools(mcp_config, mcp_scope_block, client)
                result.update(mcp_entries)
        except Exception as e:
            # MCP failure is non-fatal — log and continue with base toolset
            from voss.harness import telemetry as _tel
            if _tel.enabled():
                _tel.emit("mcp.boot_error", "warn", data={"error": f"{type(e).__name__}: {e}"})
    return result
```

NOTE on `asyncio.run` inside `make_toolset`: this only works if make_toolset is called from a synchronous context. If called from inside an async context, `asyncio.run` raises. Read voss/harness/cli.py and voss/harness/agent.py to confirm make_toolset's call context. If it's already async, switch to `await client.ensure_launched(...)` and make make_toolset async-only. This is a non-trivial signature change — check call sites first. SIMPLEST FALLBACK: make_toolset stays sync; MCP launch happens in a separate `bootstrap_mcp(toolset, cwd, net)` helper that the CLI bootstrap calls explicitly in an async context BEFORE the agent loop starts. Executor must read call-site context and pick the path; document the choice in SUMMARY.

The "expected tool name" pitfall (RESEARCH Common Pitfall 4): server-filesystem 2026.1.14 uses `read_text_file` not `read_file`. T3-07's tests use mocks that advertise whichever names the test specifies — no live server. T3-09's CI integration is what actually pins names against the real npm server.
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Create mcp/config.py + mcp/__init__.py + extend cognition_schemas.PermissionsConfig with mcp field + NET-03a + NET-04a/b tests</name>
  <files>voss/harness/mcp/__init__.py, voss/harness/mcp/config.py, voss/harness/cognition_schemas.py, tests/harness/mcp/test_mcp_config.py, tests/harness/mcp/test_mcp_scope.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-03 first paragraph + acceptance a; NET-04 full text + acceptance a/b)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-01 — three files; D-04 — schema features; D-11 — scope at registration time)
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Pattern 2 — destructiveHint mapping; server-filesystem tool table)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (sections "voss/harness/mcp/config.py" + "voss/harness/cognition_schemas.py (extend)")
    - voss/harness/cognition.py lines 176-190 (_load_yaml pattern to mirror)
    - voss/harness/cognition_schemas.py lines 51-54 (PermissionsConfig to extend)
    - tests/harness/test_cognition_schemas.py (existing pydantic-validation test pattern — `grep -n "model_validate\|STRICT" tests/harness/test_cognition_schemas.py | head -10`)
    - tests/harness/mcp/test_mcp_config.py (T3-01 placeholder — test_loader_parses_fixture)
    - tests/harness/mcp/test_mcp_scope.py (T3-01 placeholders — 4 scope tests)
  </read_first>
  <action>
    Create voss/harness/mcp/__init__.py with the re-exports block from the interfaces section. This file lives in the same module path as future siblings (client.py, registry.py); the __init__.py is the package's public surface.

    Create voss/harness/mcp/config.py with the schema + loader per the interfaces section above. Use exact field types (command: list[str] required, args/timeout_s/env with defaults), STRICT model_config, _substitute helper with the regex ${VAR} pattern, McpConfigError class, load_mcp_config(cwd) function. The substitute_server helper returns a NEW McpServerConfig (don't mutate the input — pydantic models are not frozen but treat as immutable).

    Edit voss/harness/cognition_schemas.py:
    - Add `McpScope = Literal["plan", "edit", "auto"]` near the existing Literal definitions (line 1-13 has STRICT + imports — add McpScope near the other Literal types if any).
    - In PermissionsConfig (line 51), add the line: `mcp: dict[str, McpScope] = Field(default_factory=dict)`. PRESERVE the model_config = STRICT line; default factory ensures the field is omittable in old permissions.yml files.

    Edit tests/harness/mcp/test_mcp_config.py — replace pytest.skip from test_loader_parses_fixture and add 3 more tests:

    - `test_loader_parses_fixture(tmp_path)` (NET-03a): write `(tmp_path / ".voss").mkdir(); (tmp_path / ".voss" / "mcp.yml").write_text("servers:\n  filesystem:\n    command: [npx, '-y', '@modelcontextprotocol/server-filesystem', '{cwd}']\n    timeout_s: 30.0\n")`. Call `config = load_mcp_config(tmp_path)`. Assert `config is not None`; assert `"filesystem" in config.servers`; assert `config.servers["filesystem"].command == ["npx", "-y", "@modelcontextprotocol/server-filesystem", "{cwd}"]` (unsubstituted at load time — substitution is at launch time); assert `config.servers["filesystem"].timeout_s == 30.0`.

    - `test_loader_returns_none_when_absent(tmp_path)`: no .voss/mcp.yml. Assert `load_mcp_config(tmp_path) is None`.

    - `test_var_substitution_raises_on_unset(tmp_path, monkeypatch)`: write a config that uses `${VOSS_TEST_TOKEN}` in command. monkeypatch.delenv("VOSS_TEST_TOKEN", raising=False). Load + call `substitute_server(config.servers["test"], cwd=tmp_path)`. Use `pytest.raises(McpConfigError, match="VOSS_TEST_TOKEN")`. Then `monkeypatch.setenv("VOSS_TEST_TOKEN", "abc"); result = substitute_server(...); assert "abc" in result.command`.

    - `test_cwd_substitution(tmp_path)`: write `command: [echo, '{cwd}']`. After substitute_server with cwd=tmp_path, assert the second element of command equals str(tmp_path).

    Edit tests/harness/mcp/test_mcp_scope.py — replace pytest.skip in `test_default_plan_scope` and `test_edit_scope`. (test_scope_denial and test_auto_does_not_override_scope require McpClient + registry — those are in Task 2.)

    - `test_default_plan_scope`: validate `PermissionsConfig.model_validate({}).mcp == {}` (default empty dict). Validate `PermissionsConfig.model_validate({"mcp": {"filesystem": "plan"}}).mcp == {"filesystem": "plan"}`.

    - `test_edit_scope`: validate `PermissionsConfig.model_validate({"mcp": {"filesystem": "edit"}}).mcp == {"filesystem": "edit"}`. Validate that invalid scope value raises: `with pytest.raises(ValidationError): PermissionsConfig.model_validate({"mcp": {"filesystem": "delete"}})` (delete is not a valid McpScope literal). Validate that adding an `mcp` block to an existing permissions.yml-shaped dict doesn't break the rest: `PermissionsConfig.model_validate({"tool_policy": {"allow": [], "deny": []}, "mcp": {"x": "auto"}})`.

    Confirm `grep -c "pytest.skip" tests/harness/mcp/test_mcp_config.py tests/harness/mcp/test_mcp_scope.py` is 2 (test_mcp_config.py = 0 skips after this task; test_mcp_scope.py still has 2 skips for test_scope_denial + test_auto_does_not_override_scope).
  </action>
  <verify>
    <automated>uv run pytest tests/harness/mcp/test_mcp_config.py tests/harness/mcp/test_mcp_scope.py -x -q -k "loader_parses or absent or substitution or default_plan_scope or edit_scope" 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `test -f voss/harness/mcp/__init__.py && test -f voss/harness/mcp/config.py`
    - exports assertion: `python -c "from voss.harness.mcp import McpServerConfig, McpConfig, load_mcp_config, McpConfigError; print('OK')"` prints OK
    - schema strictness: `python -c "from voss.harness.mcp.config import McpServerConfig; import pytest; from pydantic import ValidationError\ntry: McpServerConfig(command=['x'], unknown_field='no')\nexcept ValidationError as e: print('strict-ok')"` prints `strict-ok`
    - permissions field: `python -c "from voss.harness.cognition_schemas import PermissionsConfig; p = PermissionsConfig.model_validate({'mcp': {'filesystem': 'plan'}}); print(p.mcp)"` prints `{'filesystem': 'plan'}`
    - McpScope validation: `python -c "from voss.harness.cognition_schemas import PermissionsConfig; from pydantic import ValidationError\ntry: PermissionsConfig.model_validate({'mcp': {'x': 'delete'}})\nexcept ValidationError: print('rejected')"` prints `rejected`
    - behavior: all 5 tests pass (4 mcp_config + 2 mcp_scope replacing skips, minus overlap)
    - regression: `uv run pytest tests/harness/test_cognition_schemas.py tests/harness/test_cognition.py -x -q` exits 0 (no existing pydantic test breaks)
  </acceptance_criteria>
  <done>voss/harness/mcp/{__init__,config}.py exist; pydantic schema with STRICT validates command-required + ${VAR} interpolation + {cwd} substitution + env allowlist; McpConfigError raised on missing env var; PermissionsConfig.mcp dict[str, McpScope] field added; 4 NET-03a + 2 NET-04a/b tests un-skipped and green.</done>
</task>

<task type="auto">
  <name>Task 2: Create mcp/client.py with handshake + asyncio.subprocess + lifecycle wire + 2 NET-03 tests</name>
  <files>voss/harness/mcp/client.py, tests/harness/mcp/test_mcp_client.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-03 acceptance b — launch + tools/list discovery; NET-03 acceptance c — SIGTERM reap)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-02 — lazy launch; D-03 — lifecycle.py reap hook)
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Pattern 1 — full handshake spec; Code Examples — Complete MCP handshake + tools/list; Anti-Patterns list — no readline-without-timeout)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (section "voss/harness/mcp/client.py")
    - voss/harness/lifecycle.py (T3-01 — register_subprocess signature)
    - voss/harness/telemetry.py (T3-03 — emit/redact_tool_args/event-shape docstring)
    - voss/harness/tools.py lines 210-228 (_shell_capture asyncio.subprocess pattern)
    - tests/harness/mcp/test_mcp_client.py (T3-01 placeholders — test_lazy_launch + test_sigterm_reap)
  </read_first>
  <action>
    Create voss/harness/mcp/client.py per the interfaces section. Implementation notes:
    - Imports: `from __future__ import annotations; import asyncio, json, os, subprocess, time; from pathlib import Path; from voss.harness import lifecycle, telemetry; from voss.harness.mcp.config import McpConfig, McpConfigError, substitute_server`.
    - All readline calls go through `_read(proc, *, timeout)` which wraps `asyncio.wait_for(proc.stdout.readline(), timeout=timeout)` (Anti-Pattern: never call readline without timeout).
    - All writes go through `_write(proc, msg)` which does `proc.stdin.write(json.dumps(msg, separators=(",", ":")).encode() + b"\n"); await proc.stdin.drain()`.
    - Handshake sequence is the hardcoded 3-step: initialize → read response → notifications/initialized (no response read for notification). Then tools/list separately.
    - Protocol version mismatch: log via telemetry.emit("mcp.protocol_warning", "warn", ...) but do NOT raise — many servers negotiate down per RESEARCH State of the Art.
    - ensure_launched is idempotent and self-restarts dead processes (proc.returncode is not None → respawn).
    - lifecycle.register_subprocess is called ONLY after handshake succeeds — failed launches should not register zombies.

    Replace tests/harness/mcp/test_mcp_client.py placeholders. Mock the subprocess via a stub asyncio.subprocess.Process replacement. Two options:

    Option A — real subprocess with a tiny Python "mock MCP server" launched per test. The mock server is a small script that reads JSON-RPC lines, responds with hardcoded fixtures.

    Option B — monkeypatch asyncio.create_subprocess_exec to return an in-process duck-type with .stdin / .stdout / .stderr / .wait / .terminate / .kill / .returncode. Simpler but more fragile.

    Pick OPTION A — robustness + cleaner round-trip. Write the mock server inline as a Python heredoc:

    ```
    MOCK_SERVER_SRC = textwrap.dedent('''
        import sys, json
        # Read initialize
        line = sys.stdin.readline()
        req = json.loads(line)
        # Respond
        resp = {"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":"2025-11-25","capabilities":{"tools":{}},"serverInfo":{"name":"mock","version":"1"}}}
        sys.stdout.write(json.dumps(resp) + "\\n"); sys.stdout.flush()
        # Read initialized notification (no response)
        sys.stdin.readline()
        # Read tools/list
        line = sys.stdin.readline()
        req = json.loads(line)
        tools = [
            {"name":"read_text_file","description":"Read text","inputSchema":{"type":"object"},"annotations":{"readOnlyHint":True,"destructiveHint":False}},
            {"name":"write_file","description":"Write","inputSchema":{"type":"object"},"annotations":{"readOnlyHint":False,"destructiveHint":True}},
        ]
        resp = {"jsonrpc":"2.0","id":req["id"],"result":{"tools":tools}}
        sys.stdout.write(json.dumps(resp) + "\\n"); sys.stdout.flush()
        # tools/call loop
        while True:
            line = sys.stdin.readline()
            if not line: break
            req = json.loads(line)
            resp = {"jsonrpc":"2.0","id":req["id"],"result":{"content":[{"type":"text","text":"mock-result"}],"isError":False}}
            sys.stdout.write(json.dumps(resp) + "\\n"); sys.stdout.flush()
    ''')
    ```

    Write MOCK_SERVER_SRC to a tmp_path file once per test; reference that file in command.

    - `async def test_lazy_launch(tmp_path)` (NET-03b): Write MOCK_SERVER_SRC to `tmp_path/mock_server.py`. Build `config = McpConfig(servers={"mock": McpServerConfig(command=[sys.executable, str(tmp_path/'mock_server.py')])})`. `client = McpClient(config); client.set_cwd(tmp_path)`. Call `await client.ensure_launched("mock")`. Assert subprocess is running (`proc.returncode is None`). Assert `client._tools_cache["mock"]` has 2 tools with names `"read_text_file"` and `"write_file"`. Call `result = await client.call_tool("mock", "read_text_file", {"path": "x"})`. Assert `result["content"][0]["text"] == "mock-result"`. Clean up: `lifecycle.reset_for_tests()` (T3-01 helper) AND explicitly terminate the subprocess to avoid orphan in CI: `await client._procs["mock"].wait()` after the test calls .terminate(). Use fixture autouse=True for lifecycle reset.

    - `async def test_sigterm_reap(tmp_path)` (NET-03c): Same setup. After ensure_launched, capture the proc handle. Verify `lifecycle._SUBPROCESSES` (or however T3-01 exposes the registry — `reset_for_tests` is the public escape, but for test introspection peek via `lifecycle.register_subprocess` count or capture the proc directly). Call `await lifecycle.reap_all()`. Assert proc.returncode is not None (process terminated). Assert wall time elapsed < 5.0 seconds (mock server exits cleanly on EOF, so SIGTERM should succeed under the deadline).

    Bonus tests if budget permits:
    - `test_handshake_fails_on_short_stdout`: server that exits immediately. ensure_launched should raise McpConfigError "MCP server closed stdout unexpectedly".
    - `test_call_tool_error_response`: server that returns `{"error": {"code": -32602, "message": "Unknown tool"}}` for tools/call. Assert call_tool returns `{"isError": True, "content": [{"type":"text","text":"<error: mcp tool: Unknown tool>"}]}`.

    Confirm `grep -c "pytest.skip" tests/harness/mcp/test_mcp_client.py` is 0.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/mcp/test_mcp_client.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "^class McpClient" voss/harness/mcp/client.py` returns 1 match
    - source assertion: `grep -cE "2025-11-25" voss/harness/mcp/client.py` returns >= 1 match
    - source assertion: `grep -cE "notifications/initialized" voss/harness/mcp/client.py` returns 1 match
    - source assertion: `grep -cE "lifecycle\.register_subprocess" voss/harness/mcp/client.py` returns 1 match
    - source assertion: `grep -cE "asyncio\.wait_for" voss/harness/mcp/client.py` returns >= 1 (no readline-without-timeout per Anti-Patterns)
    - source assertion: `grep -cE "telemetry\.emit\(.mcp\." voss/harness/mcp/client.py` returns >= 2 (mcp.request + mcp.response)
    - skip removed: `grep -c "pytest.skip" tests/harness/mcp/test_mcp_client.py` returns 0
    - behavior: test_lazy_launch and test_sigterm_reap pass; bonus tests pass if added
    - regression: `uv run pytest tests/harness/test_lifecycle.py tests/harness/mcp/ -x -q` exits 0
  </acceptance_criteria>
  <done>McpClient ships with ensure_launched + call_tool + _handshake + _tools_list + _write/_read; 2025-11-25 protocol version targeted; SIGTERM reap via lifecycle.register_subprocess; mcp.request and mcp.response telemetry emitted; mock-server-based tests prove lazy launch and SIGTERM reap deadline.</done>
</task>

<task type="auto">
  <name>Task 3: Create mcp/registry.py + integrate into make_toolset + 2 NET-04 scope-denial tests</name>
  <files>voss/harness/mcp/registry.py, voss/harness/mcp/__init__.py, voss/harness/tools.py, tests/harness/mcp/test_mcp_scope.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-04 acceptance c — denied by mcp scope envelope; d — auto does not override scope)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-11 — scope at registration time + destructiveHint fallback; D-12 — denial UX)
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Pattern 2 — _is_mutating_from_descriptor full mapping table)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (section "voss/harness/mcp/registry.py")
    - voss/harness/tools.py (post T3-05/T3-06 — make_toolset shape with web_fetch/web_search merged; need to extend the merge block)
    - voss/harness/cognition.py (locate the load_permissions function — `grep -n "def load_permissions\|PermissionsConfig" voss/harness/cognition.py`)
    - voss/harness/permissions.py (PermissionGate — does NOT need MCP-aware logic per D-11; scope is applied at REGISTRATION time)
    - voss/harness/mcp/client.py (just created — _tools_cache dict shape)
    - tests/harness/mcp/test_mcp_scope.py (post Task 1 — still has 2 skips: test_scope_denial, test_auto_does_not_override_scope)
  </read_first>
  <action>
    Create voss/harness/mcp/registry.py:
    - Imports: `from __future__ import annotations; from typing import TYPE_CHECKING; from voss.harness.tools import ToolEntry`. TYPE_CHECKING block: `from voss.harness.mcp.client import McpClient; from voss.harness.mcp.config import McpConfig`.
    - `def _is_mutating_from_descriptor(tool: dict, scope: str) -> bool` per the interfaces block. Edge cases: when annotations exists but destructiveHint is explicitly False, return False even at edit/auto scope (the server declares the tool non-destructive). When annotations is absent or None, fallback per scope rule (plan → False; edit/auto → True).
    - `def _make_mcp_descriptor(server_name, tool_name, tool_metadata, mcp_client)` — returns a ToolDescriptor-shape that the existing toolset honors. Need to know voss/harness/tools.py's ToolDescriptor shape:
      - `grep -n "class ToolDescriptor\|@tool" voss/harness/tools.py` first; the @tool decorator builds a ToolDescriptor with name, description, parameters, invoke. For MCP tools, build a manual ToolDescriptor with:
        - name = f"{server_name}__{tool_name}"
        - description = tool_metadata.get("description", "")
        - parameters = tool_metadata.get("inputSchema", {"type": "object"})  # MCP inputSchema → JSON Schema compatible with tools.py
        - invoke = async callable that calls `mcp_client.call_tool(server_name, tool_name, kwargs)` and returns the text-content from result, OR the error envelope from result["isError"].
      - The exact ToolDescriptor signature must match existing tools.py — read first.
    - `def register_mcp_tools(config, permissions_mcp, mcp_client)` per the interfaces block. For each server: read `mcp_client._tools_cache.get(server_name, [])`. For each tool, compute is_mutating + build descriptor + append ToolEntry with namespaced key.

    Update voss/harness/mcp/__init__.py to export register_mcp_tools.

    Edit voss/harness/tools.py make_toolset:
    - After the existing T3-05/T3-06 entries register in the result dict, add the MCP merge block per the interfaces section. Decision point: `asyncio.run` inside make_toolset works only from sync context. Read voss/harness/cli.py call sites: `grep -n "make_toolset" voss/harness/cli.py` returns the site. If cli.py calls `make_toolset(cwd, net=...)` from sync context (likely — it's inside a click command body which is sync), asyncio.run works. If from async, switch to a separate `async def bootstrap_mcp_tools(toolset, cwd, net) -> None` helper that the CLI awaits explicitly. PICK: try asyncio.run first; if it raises RuntimeError("asyncio.run() cannot be called from a running event loop"), fall back to the bootstrap_mcp_tools async helper. Document choice in SUMMARY.

    Implementation:
    ```
    if net is not None:
        try:
            from voss.harness.mcp import load_mcp_config, McpClient, register_mcp_tools
            from voss.harness.cognition import load_permissions
            mcp_config = load_mcp_config(cwd)
            if mcp_config is not None and mcp_config.servers:
                permissions = load_permissions(cwd)  # check existing function signature; pass cwd or errors-list as needed
                mcp_scope_block = permissions.mcp if permissions is not None else {}
                client = McpClient(mcp_config)
                client.set_cwd(cwd)
                async def _launch_all():
                    for server_name in mcp_config.servers:
                        try:
                            await client.ensure_launched(server_name)
                        except Exception as ex:
                            # log but continue
                            from voss.harness import telemetry as _tel
                            if _tel.enabled():
                                _tel.emit("mcp.launch_error", "warn", data={"server": server_name, "error": f"{type(ex).__name__}: {ex}"})
                try:
                    asyncio.run(_launch_all())
                except RuntimeError:
                    # Called from inside event loop — caller must invoke bootstrap_mcp explicitly
                    pass
                mcp_entries = register_mcp_tools(mcp_config, mcp_scope_block, client)
                result.update(mcp_entries)
        except Exception as e:
            from voss.harness import telemetry as _tel
            if _tel.enabled():
                _tel.emit("mcp.boot_error", "warn", data={"error": f"{type(e).__name__}: {e}"})
    ```

    Edit tests/harness/mcp/test_mcp_scope.py — replace remaining 2 skips.

    Test setup helper (reuse the mock-server script from Task 2 OR build a unit-test-only direct registry test that doesn't need a real subprocess):

    SIMPLER PATH: test_scope_denial and test_auto_does_not_override_scope can be unit tests that construct a fake McpClient with a pre-populated _tools_cache, then call register_mcp_tools directly. This avoids spinning up subprocesses for scope logic.

    ```
    class FakeMcpClient:
        def __init__(self):
            self._tools_cache = {
                "filesystem": [
                    {"name": "read_text_file", "description": "Read", "inputSchema": {"type":"object"}, "annotations": {"readOnlyHint": True, "destructiveHint": False}},
                    {"name": "write_file", "description": "Write", "inputSchema": {"type":"object"}, "annotations": {"readOnlyHint": False, "destructiveHint": True}},
                ]
            }
        async def call_tool(self, server, tool, args):
            return {"content": [{"type":"text","text":"fake"}], "isError": False}
    ```

    - `test_scope_denial(tmp_path)` (NET-04c): config = McpConfig(servers={"filesystem": McpServerConfig(command=["x"])}). client = FakeMcpClient(). permissions_mcp = {} (default → plan scope). Call `entries = register_mcp_tools(config, permissions_mcp, client)`. Assert `entries["filesystem__write_file"].is_mutating is False` (plan scope forces False per D-11). Now build a PermissionGate with mode="plan" and call `gate.check("filesystem__write_file", {"path":"x"}, is_mutating=False, is_network=True)`. With allow_net=True configured, the gate sees is_mutating=False so it allows. THIS IS THE TRICKY PART: under D-11, mutation is denied because the tool *should be* mutating but is registered as non-mutating under plan scope; the SPEC envelope `<error: denied by mcp scope: filesystem at plan, requires edit>` requires SOMETHING in the registration or invocation path to know "this would be mutating under edit scope".

    Resolution: re-read SPEC NET-04 acceptance c: "calling filesystem__write_file under default scope returns `<error: denied by mcp scope: filesystem at plan, requires edit>`". This means the tool's INVOKE wrapper itself returns this string when called under plan scope on a server-declared-destructive tool. The descriptor's invoke must close over scope+destructiveHint and return the envelope when (scope==plan AND destructiveHint==True). Update `_make_mcp_descriptor`:
    ```
    def _make_mcp_descriptor(server_name, tool_name, tool_metadata, mcp_client, scope):
        annotations = tool_metadata.get("annotations") or {}
        is_destructive = annotations.get("destructiveHint", True)  # safe default
        async def invoke(**kwargs):
            if scope == "plan" and is_destructive:
                return f"<error: denied by mcp scope: {server_name} at plan, requires edit>"
            result = await mcp_client.call_tool(server_name, tool_name, kwargs)
            if result.get("isError"):
                return result.get("content", [{}])[0].get("text", "<error: mcp tool: unknown>")
            content = result.get("content", [])
            return content[0].get("text", "") if content else ""
        # Build ToolDescriptor with this invoke...
    ```

    Then register_mcp_tools passes scope to _make_mcp_descriptor.

    Update test_scope_denial: directly invoke `entries["filesystem__write_file"].invoke_dict({"path": "x"})` and assert the result string equals exactly `"<error: denied by mcp scope: filesystem at plan, requires edit>"`.

    - `test_auto_does_not_override_scope(tmp_path)` (NET-04d): permissions_mcp = {"filesystem": "plan"} (explicit plan even though agent is in auto). Register with config. Build PermissionGate with mode="auto" and call `gate.check("filesystem__write_file", {}, is_mutating=False, is_network=True)`. With allow_net=True, mode=auto would normally allow everything mutating, BUT the tool was registered as is_mutating=False (because plan scope was active at registration). The denial happens at INVOKE time inside the closure (just like test_scope_denial above): invoke returns the same envelope. Assert that calling `await entries["filesystem__write_file"].invoke_dict({})` returns the denial envelope. This proves `mode=auto + mcp scope=plan` still denies — the agent's overall mode doesn't override per-server scope (D-11 invariant).

    Bonus test test_destructive_hint_absent_defaults_to_true: build a fake tool with NO annotations field at all. Under edit scope, assert is_mutating is True (safe default).

    Confirm `grep -c "pytest.skip" tests/harness/mcp/test_mcp_scope.py` returns 0.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/mcp/ -x -q 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "def register_mcp_tools|def _is_mutating_from_descriptor|def _make_mcp_descriptor" voss/harness/mcp/registry.py | wc -l` returns 3
    - source assertion: `grep -cE "destructiveHint" voss/harness/mcp/registry.py` returns >= 1
    - source assertion: `grep -cE "denied by mcp scope" voss/harness/mcp/registry.py` returns 1 (the envelope literal lives in the invoke closure)
    - integration: `grep -nE "register_mcp_tools" voss/harness/tools.py | wc -l` >= 1 (make_toolset merges MCP entries)
    - exports: `python -c "from voss.harness.mcp import register_mcp_tools, McpClient; print('OK')"` prints OK
    - skip removed: `grep -c "pytest.skip" tests/harness/mcp/test_mcp_scope.py tests/harness/mcp/test_mcp_client.py tests/harness/mcp/test_mcp_config.py` returns 0 across all three
    - behavior: all 4 NET-04 scope tests pass + 2 NET-03 client tests pass + 4 NET-03a config tests pass (from Task 1)
    - regression: `uv run pytest tests/harness/ -k "mcp or lifecycle or web_fetch or web_search or allow_net or rate_limit or telemetry" -x -q` exits 0
  </acceptance_criteria>
  <done>mcp/registry.py + _make_mcp_descriptor with scope-aware invoke closure; make_toolset merges MCP-discovered tools at registration time; PermissionsConfig.mcp drives is_mutating at registration AND the invoke closure denies destructive tools under plan scope; auto mode does not override per-server scope; 4 NET-04 + 2 NET-03 + 4 NET-03 config tests all pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| voss → MCP subprocess via stdio | Subprocess can be arbitrary code (npx-fetched npm packages, user-authored scripts). voss treats stdout as protocol input — corrupt stdout = crashed session. |
| MCP subprocess → voss agent | Tool descriptors from tools/list, results from tools/call. Untrusted; consumed by agent. destructiveHint informs scope but is voluntarily declared by the server. |
| User `.voss/mcp.yml` → spawned subprocess argv + env | User authors command + ${VAR} + env allowlist. Trusted (user owns the file) but malformed entries must fail gracefully. |
| User `.voss/permissions.yml` → MCP scope at registration | `mcp: { filesystem: edit }` directly controls whether mutating MCP tools register as is_mutating=True. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T3-05 | DoS | MCP subprocess leak on crash | mitigate | lifecycle.register_subprocess(proc) called after handshake; reap_all() on atexit SIGTERMs then SIGKILLs (test_sigterm_reap proves; bounded ≤5s) |
| T-T3-06 | Elevation | MCP server with destructive tools registered as non-mutating | mitigate | _is_mutating_from_descriptor at edit/auto scope reads annotations.destructiveHint with absent → True (safe default). Plan scope additionally short-circuits all destructive invocations at the invoke closure (denied-by-mcp-scope envelope) (test_scope_denial proves). |
| T-T3-07 | Tampering | mcp.yml env var interpolation could leak secrets via error messages | mitigate | _substitute raises McpConfigError(f"required env var {var!r} is unset") — the VARIABLE NAME is in the error, never the value. test_var_substitution_raises_on_unset proves. |
| T-T3-07-01 | Info Disclosure | MCP subprocess inherits full parent env including secrets | mitigate | per-server env: list[str] allowlist (D-04). When set, subprocess starts with empty env + only listed vars passed through. When omitted, parent env inherited (back-compat default — explicit opt-in to allowlist mode). |
| T-T3-07-02 | DoS | MCP subprocess writes to stdout outside protocol → JSON parse crash | mitigate | RESEARCH Common Pitfall 1; server stderr is captured (PIPE) so logging mistakes appear on stderr not stdout. T3-09 CI integration with real reference server validates this at the system level. |
| T-T3-07-03 | Tampering | mcp.yml `command` execs arbitrary binary | accept | command is list[str] (argv form, no shell expansion); user authored the file — same trust level as their own dotfiles. ${VAR} interpolation uses env values only. No mitigation needed beyond making this an explicit user-authored config file. |
| T-T3-02 (reaffirm) | Info Disclosure | MCP tool args contain secrets | mitigate | mcp.request emit redacts args via telemetry.redact_tool_args before payload construction |
</threat_model>

<verification>
- `uv run pytest tests/harness/mcp/ -x -q` exits 0 (all mcp tests pass — at minimum 4 config + 2 client + 4 scope = 10 tests un-skipped)
- `grep -c "pytest.skip" tests/harness/mcp/test_mcp_config.py tests/harness/mcp/test_mcp_client.py tests/harness/mcp/test_mcp_scope.py` returns 0 across all three files
- `python -c "from voss.harness.mcp import McpClient, McpConfig, McpServerConfig, load_mcp_config, register_mcp_tools, McpConfigError; print('OK')"` prints OK
- `python -c "from voss.harness.cognition_schemas import PermissionsConfig, McpScope; p = PermissionsConfig.model_validate({'mcp': {'fs': 'plan'}}); print(p.mcp)"` prints `{'fs': 'plan'}`
- `grep -cE "2025-11-25|notifications/initialized" voss/harness/mcp/client.py` returns >= 2
- agent.py audit reaffirmed: `grep -cE "gate\.check.*is_network" voss/harness/agent.py` >= 1 (T3-05 wired this; T3-07 doesn't undo it)
</verification>

<success_criteria>
- voss/harness/mcp/ package with __init__.py + config.py + client.py + registry.py
- Pydantic schema with ${VAR} interpolation + {cwd} substitution + per-server env allowlist
- McpClient with 2025-11-25 protocol handshake + lazy launch + asyncio.subprocess.PIPE stdin/stdout/stderr
- SIGTERM+5s+SIGKILL reap via lifecycle.register_subprocess
- mcp.request / mcp.response telemetry emitted with redact_tool_args
- MCP tools register with namespaced `{server}__{tool}` keys, is_network=True
- destructiveHint drives is_mutating under edit/auto scope; plan scope forces False + invoke closure denies destructive
- 4 NET-03 config + 2 NET-03 client + 4 NET-04 scope tests all green
</success_criteria>

<output>
Create `.planning/phases/T3-network-surface/T3-07-SUMMARY.md` when done: report 4-file mcp/ package layout + line counts; cite the handshake sequence step numbers from RESEARCH; document the asyncio.run-vs-async-helper decision made in make_toolset; pytest output for 10+ mcp tests; note that T3-08 (voss mcp CLI) reuses McpClient.list_tools + McpClient.call_tool directly; T3-09 CI integration will tools/list against the real npm reference server to pin the actual tool names.
</output>
