# Phase T3: Network Surface — Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 21 (new/modified)
**Analogs found:** 18 / 21

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `voss/harness/net.py` | service | request-response | `voss/harness/providers.py` (AnthropicOAuthProvider) | role-match |
| `voss/harness/rate_limit.py` | utility | transform | `voss/harness/telemetry.py` (pure stdlib module) | partial-match |
| `voss/harness/lifecycle.py` | utility | event-driven | `voss/harness/providers.py` (`aclose` pattern) | partial-match |
| `voss/harness/web_search.py` | service | request-response | `voss/harness/providers.py` (BraveBackend mirrors provider shape) | role-match |
| `voss/harness/mcp/__init__.py` | config | — | `voss/harness/mcp/` (no analog — greenfield package) | none |
| `voss/harness/mcp/client.py` | service | event-driven | `voss/harness/tools.py` (`_shell_capture` + `asyncio.create_subprocess_exec`) | partial-match |
| `voss/harness/mcp/config.py` | config | CRUD | `voss/harness/cognition.py` (`_load_yaml` + pydantic) | exact |
| `voss/harness/mcp/registry.py` | utility | transform | `voss/harness/tools.py` (`make_toolset` registration block) | role-match |
| `voss/harness/tools.py` (extend) | utility | transform | self — extend `ToolEntry` + `make_toolset` | self |
| `voss/harness/permissions.py` (extend) | middleware | request-response | self — extend `_check_impl` | self |
| `voss/harness/telemetry.py` (extend) | utility | transform | self — add `redact_url` beside `redact_tool_args` | self |
| `voss/harness/cognition_schemas.py` (extend) | model | CRUD | self — add `mcp: dict` field to `PermissionsConfig` | self |
| `voss_runtime/_config.py` (extend) | config | CRUD | self — add `allow_net: bool` field to `RuntimeConfig` | self |
| `voss/harness/config.py` (extend) | config | CRUD | self — add `[tools]` + `[net.rate_limits]` TOML sections | self |
| `voss/harness/cli.py` (extend) | controller | request-response | `voss/harness/cli.py` `plugin_group` + `do_cmd` | self |
| `tests/harness/test_web_fetch.py` | test | request-response | `tests/harness/test_tools.py` | exact |
| `tests/harness/test_web_search.py` | test | request-response | `tests/harness/test_tools.py` | exact |
| `tests/harness/test_allow_net.py` | test | request-response | `tests/harness/test_permissions_modes.py` | exact |
| `tests/harness/test_net_telemetry.py` | test | transform | `tests/harness/test_telemetry.py` | exact |
| `tests/harness/test_rate_limit.py` | test | transform | `tests/harness/test_agent_config.py` (monkeypatch + warnings pattern) | role-match |
| `tests/harness/mcp/test_mcp_config.py` | test | CRUD | `tests/harness/test_cognition_schemas.py` | exact |
| `tests/harness/mcp/test_mcp_client.py` | test | event-driven | `tests/harness/test_tools.py` (asyncio + subprocess mock) | role-match |
| `tests/harness/mcp/test_mcp_scope.py` | test | request-response | `tests/harness/test_permissions_modes.py` | exact |
| `.github/workflows/mcp-integration.yml` | config | event-driven | `.github/workflows/ci.yml` | exact |

---

## Pattern Assignments

### `voss/harness/net.py` (service, request-response)

**Analog:** `voss/harness/providers.py` — `AnthropicOAuthProvider` and `OpenAIOAuthProvider`

**Imports pattern** (`providers.py` lines 1-19):
```python
from __future__ import annotations

import httpx

# AsyncClient import is direct — no lazy import
```

**Lazy AsyncClient pattern** (`providers.py` lines 162-169, mirrored by OpenAIOAuthProvider lines 469-477):
```python
class AnthropicOAuthProvider:
    def __init__(self, creds, *, client=None, ...):
        self._client = client  # injected for tests; None for production

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
```

**Core pattern for NetSession** — copy the `_http()` / `aclose()` shape exactly. The `NetSession` constructor kwargs differ from providers (add `follow_redirects=True, max_redirects=5` per RESEARCH Pattern 4). Test-injection via `client=` kwarg preserves the pattern.

**Error handling pattern** (`providers.py` lines 265-273):
```python
resp = await _post()
if resp.status_code == 401:
    ...  # refresh
if resp.status_code >= 400:
    raise RuntimeError(f"... [{resp.status_code}]: {resp.text[:500]}")
```
For `web_fetch` the pattern diverges: HTTP 4xx/5xx returns `<error: http {status}: {reason}>` string (no raise). Mirror `tools.py` error-envelope convention, not provider raise convention.

---

### `voss/harness/rate_limit.py` (utility, transform)

**Analog:** `voss/harness/telemetry.py` — pure-stdlib module with no class hierarchy

**Module pattern** (`telemetry.py` lines 1-19):
```python
"""Structured NDJSON telemetry for local harness debugging.
...
"""
from __future__ import annotations

import json
import os
import threading
import uuid
# ... stdlib only
```

`rate_limit.py` follows the same: `from __future__ import annotations`, docstring, stdlib-only imports (`import math`, `import time`, `from dataclasses import dataclass, field`). No external deps.

**Dataclass pattern** — use `@dataclass` with `field(init=False)` for internal state (mirrors `telemetry.py` `ContextVar` pattern of internal state separate from public API). See RESEARCH Pattern 5 for the `TokenBucket` shape.

---

### `voss/harness/lifecycle.py` (utility, event-driven)

**Analog:** `voss/harness/providers.py` `aclose()` (partial) — no exact lifecycle-hook analog in the tree.

**Pattern to pioneer:** Register an `atexit` callback that collects subprocess handles and `NetSession`. The RESEARCH confirms no prior `lifecycle.py` equivalent exists — this is greenfield.

**Closest structural model** — `providers.py` lines 167-170:
```python
async def aclose(self) -> None:
    if self._client is not None:
        await self._client.aclose()
        self._client = None
```

`lifecycle.py` exposes a `register_subprocess(proc: asyncio.subprocess.Process)` and `register_session(session: NetSession)` API, plus a `reap_all()` async coroutine that SIGTERM's registered procs with 5s deadline before SIGKILL, then calls `session.aclose()`. An `atexit` handler runs `asyncio.run(reap_all())`.

---

### `voss/harness/web_search.py` (service, request-response)

**Analog:** `voss/harness/providers.py` — flat class with `__init__(api_key)` and one async method.

**Class shape** (`providers.py` lines 139-148):
```python
class AnthropicOAuthProvider:
    def __init__(
        self,
        creds: auth.AnthropicOAuthCreds,
        *,
        client: Optional[httpx.AsyncClient] = None,
        ...
    ):
        self.creds = creds
        self._client = client
```

`BraveBackend(api_key, *, client=None)` follows the same injectable-client shape. Single public method: `async def search(query: str, count: int) -> list[SearchResult]`. No inheritance, no protocol. See RESEARCH Pattern 3 for request shape.

**Error handling** (`providers.py` lines 269-273 + tools.py error-envelope convention):
- 429: return `<error: rate limit: retry after Ns>` string (not raise)
- Other 4xx/5xx: return `<error: http {status}: {reason}>` string

---

### `voss/harness/mcp/client.py` (service, event-driven)

**Analog:** `voss/harness/tools.py` — `_shell_capture` + `asyncio.create_subprocess_exec` pattern

**asyncio subprocess pattern** (`tools.py` lines 210-228):
```python
async def _shell_capture(cwd: Path, argv: list[str], timeout: float = 30.0) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except OSError as e:
        return f"<error: {e}>"
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return f"<timeout: {timeout}s>"
    text = out.decode("utf-8", errors="replace")
```

**Differences for `McpClient`:** `stderr=subprocess.PIPE` (NOT `STDOUT` — MCP stdout must carry JSON-RPC only). Reads are via `readline()` inside `asyncio.wait_for(..., timeout=30.0)` per line, not `communicate()`. Writes are `proc.stdin.write(...); await proc.stdin.drain()`. See RESEARCH Pattern 1 (handshake) and Code Examples (complete handshake + tools/list).

**Error-envelope convention** (`tools.py` lines 54-56, 96-97):
```python
return f"<error: not found: {path}>"
# and:
return f"<timeout: 30s>"
```
MCP transport errors: `<error: mcp transport: connection lost>`. MCP tool errors: `<error: mcp tool: {server.error.message}>`.

---

### `voss/harness/mcp/config.py` (config, CRUD)

**Analog:** `voss/harness/cognition.py` `_load_yaml` + `cognition_schemas.py` pydantic models

**YAML load pattern** (`cognition.py` lines 176-190):
```python
def _load_yaml(path: Path, model, errors: list[str]):
    if not path.exists():
        return None
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        errors.append(f"{path}: invalid YAML: {e}")
        return None
    try:
        return model.model_validate(raw)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"]) or "<root>"
            errors.append(f"{path}: {loc}: {err['msg']}")
        return None
```

`mcp/config.py` uses this exact shape for `.voss/mcp.yml`. Path: `{cwd}/.voss/mcp.yml`. Returns `McpConfig | None` (no error list — raises `McpConfigError` on parse failure, consistent with D-03 "fail at boot" pattern).

**Pydantic model pattern** (`cognition_schemas.py` lines 51-54):
```python
class PermissionsConfig(BaseModel):
    model_config = STRICT          # {"extra": "forbid"}
    tool_policy: ToolPolicy = Field(default_factory=ToolPolicy)
    path_scopes: list[PathScope] = Field(default_factory=list)
```

`McpServerConfig` and `McpConfig` follow the same `model_config = STRICT` + `Field(default_factory=...)` shape. All four schema features from D-04 (env-var interpolation, `{cwd}`, `timeout_s`, `env` allowlist) are post-load processing steps, not pydantic validators — keep schema simple, transform in the loader.

**Imports pattern** (`cognition_schemas.py` lines 1-13):
```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
STRICT = {"extra": "forbid"}
```

---

### `voss/harness/mcp/registry.py` (utility, transform)

**Analog:** `voss/harness/tools.py` registration block (lines 196-207)

**ToolEntry registration pattern** (`tools.py` lines 196-207):
```python
return {
    "fs_read": ToolEntry(descriptor=fs_read, is_mutating=False),
    "fs_glob": ToolEntry(descriptor=fs_glob, is_mutating=False),
    "fs_write": ToolEntry(descriptor=fs_write, is_mutating=True),
    ...
}
```

`registry.py` builds entries differently — MCP tool descriptors are dicts from the wire, not `@tool`-decorated callables. Pattern:
1. Receive raw `tools/list` response from `McpClient`.
2. For each tool: create a `ToolDescriptor`-compatible wrapper whose `invoke` calls `McpClient.call_tool(server, tool_name, args)`.
3. Set `is_network=True` on every MCP ToolEntry.
4. Set `is_mutating` via `_is_mutating_from_descriptor(tool, scope)` (see RESEARCH Pattern 2).
5. Key = `{server_name}__{tool_name}` (namespace to prevent collision).

**ToolEntry extension** — add `is_network: bool = False` field to the frozen dataclass (preserves all existing positional construction via keyword arg default).

---

### `voss/harness/tools.py` (extend)

**Anchor:** `tools.py` lines 14-44 (ToolEntry) and lines 44-207 (make_toolset)

**ToolEntry extension** (`tools.py` lines 14-23):
```python
@dataclass(frozen=True)
class ToolEntry:
    descriptor: ToolDescriptor
    is_mutating: bool
    # T3: add after is_mutating:
    is_network: bool = False  # new field; default preserves all existing call sites
```

**make_toolset signature extension** (`tools.py` line 44):
```python
# Before:
def make_toolset(cwd: Path) -> dict[str, ToolEntry]:
# After:
def make_toolset(cwd: Path, *, net: "NetSession | None" = None) -> dict[str, ToolEntry]:
```

**New tool body pattern** — copy `fs_read` body shape (`tools.py` lines 52-61), replace with net-disabled-check + `await net.fetch(...)`:
```python
@tool(name="web_fetch", description="Fetch a URL via HTTP GET. Requires --allow-net.")
async def web_fetch(url: str, timeout_s: float = 30.0) -> str:
    if net is None:
        return "<error: net disabled: set tools.allow_net = true in harness.toml or pass --allow-net>"
    return await net.fetch(url, timeout_s=timeout_s)
```

**Registration dict extension** (`tools.py` lines 196-207) — add after existing entries:
```python
"web_fetch": ToolEntry(descriptor=web_fetch, is_mutating=False, is_network=True),
"web_search": ToolEntry(descriptor=web_search, is_mutating=False, is_network=True),
```

---

### `voss/harness/permissions.py` (extend)

**Anchor:** `permissions.py` lines 169-229 (`check` + `_check_impl`)

**`check` signature extension** (`permissions.py` lines 169-185):
```python
def check(self, tool_name: str, args: dict, *, is_mutating: bool = False) -> tuple[bool, str]:
    allowed, why = self._check_impl(tool_name, args, is_mutating=is_mutating)
    # extend to:
def check(self, tool_name: str, args: dict, *, is_mutating: bool = False, is_network: bool = False) -> tuple[bool, str]:
    allowed, why = self._check_impl(tool_name, args, is_mutating=is_mutating, is_network=is_network)
```

Telemetry emission block in `check` (lines 171-184) is unchanged — emits ONLY when the call reaches it. Critically: the net-check in `_check_impl` fires BEFORE the telemetry block would be reached for a network-disabled denial. The denial path returns early from `_check_impl`, `check` receives `(False, "net disabled: ...")`, and the telemetry block still fires with `allowed=False`. This is consistent — the policy is "no `net.request` event", not "no `permission.result` event".

**`_check_impl` net-check insertion** (`permissions.py` lines 187-204) — insert between project-policy deny and mode-tier:
```python
def _check_impl(self, tool_name: str, args: dict, *, is_mutating: bool = False, is_network: bool = False) -> tuple[bool, str]:
    # 0. Project-policy deny (unchanged)
    if self.project_policy is not None:
        if tool_name in self.project_policy.tool_policy.deny:
            return False, "denied by .voss/permissions.yml"

    # 0.5. Network gate — fires before mode-tier (D-10)
    if is_network:
        from voss_runtime._config import get_config
        if not get_config().allow_net:
            return False, (
                "net disabled: set tools.allow_net = true in harness.toml or pass --allow-net"
            )

    # 1. Mode-tier (unchanged from today)
    allowed, why = mode_allows(self.mode, tool_name, is_mutating)
    if not allowed:
        return False, why
    # ... rest unchanged
```

---

### `voss/harness/telemetry.py` (extend)

**Anchor:** `telemetry.py` lines 87-112 (`redact_tool_args`)

**Peer pure-function pattern** (`telemetry.py` lines 87-91):
```python
def redact_tool_args(args: dict[str, Any]) -> dict[str, Any]:
    """Shallow redaction for tool argument telemetry."""
    verbose = os.environ.get("VOSS_LOG_VERBOSE", "").strip().lower() in (...)
    ...
```

Add `redact_url` immediately after `redact_tool_args` (same file, same section):
```python
def redact_url(url: str) -> str:
    """Strip query string, fragment, and userinfo from a URL.

    Preserves scheme, host, and path. Telemetry-safe.
    """
    try:
        from urllib.parse import urlparse, urlunparse
        p = urlparse(url)
        netloc = p.hostname or ""
        if p.port:
            netloc = f"{netloc}:{p.port}"
        clean = p._replace(query="", fragment="", netloc=netloc)
        return urlunparse(clean)
    except Exception:
        return "<redacted-url>"
```

`urllib.parse` is stdlib — import locally inside the function (or at top of file) per project style (note `agent.py` does local imports for circular avoidance).

---

### `voss/harness/cognition_schemas.py` (extend)

**Anchor:** `cognition_schemas.py` lines 39-54 (`PermissionsConfig`)

**Existing model** (`cognition_schemas.py` lines 51-54):
```python
class PermissionsConfig(BaseModel):
    model_config = STRICT
    tool_policy: ToolPolicy = Field(default_factory=ToolPolicy)
    path_scopes: list[PathScope] = Field(default_factory=list)
```

**Extension** — add `McpScope` literal and `mcp` field:
```python
McpScope = Literal["plan", "edit", "auto"]

class PermissionsConfig(BaseModel):
    model_config = STRICT
    tool_policy: ToolPolicy = Field(default_factory=ToolPolicy)
    path_scopes: list[PathScope] = Field(default_factory=list)
    mcp: dict[str, McpScope] = Field(default_factory=dict)   # T3: per-server MCP scope
```

`model_config = STRICT` must remain — the `extra: "forbid"` mode means this is a backward-compat risk if old `permissions.yml` files happen to have an `mcp` key. Since no existing `.voss/permissions.yml` files contain `mcp`, additive-field default is safe.

---

### `voss_runtime/_config.py` (extend)

**Anchor:** `_config.py` lines 7-19 (`RuntimeConfig` dataclass)

**Existing pattern** (`_config.py` lines 17-19):
```python
    # T1-04: agent iteration-loop cap. Default 8 per SPEC ITER-01; overridable
    # via [agent] max_iterations in ~/.config/voss/config.toml. T1-05 reads
    # this field at loop entry; cli boot wires the TOML override via configure.
    max_iterations: int = 8
```

**Extension** — add after `max_iterations`, matching the inline-comment convention:
```python
    # T3: network access opt-in gate. Default False (network off). Set via
    # [tools] allow_net = true in ~/.config/voss/config.toml or --allow-net CLI
    # flag. PermissionGate.check reads this via get_config().allow_net before
    # mode-tier. CLI flag takes precedence over config file.
    allow_net: bool = False
```

**configure()** (`_config.py` lines 30-34) is already generic via `dataclasses.replace(**kwargs)` — no change needed; `configure(allow_net=True)` works immediately.

---

### `voss/harness/config.py` (extend)

**Anchor:** `config.py` lines 25-86 (TOML block parsing pattern)

**Existing block regex pattern** (`config.py` lines 25-27):
```python
_HARNESS_BLOCK = re.compile(r"^\[harness\][^\[]*", re.MULTILINE)
_AGENT_BLOCK = re.compile(r"^\[agent\][^\[]*", re.MULTILINE)
_KV = re.compile(r'^\s*(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)
```

**Extension** — add three new regex constants and two new functions:
```python
_TOOLS_BLOCK = re.compile(r"^\[tools\][^\[]*", re.MULTILINE)
_NET_RATE_BLOCK = re.compile(r"^\[net\.rate_limits\][^\[]*", re.MULTILINE)  # note: escaped dot
_KV_BOOL = re.compile(r'^\s*allow_net\s*=\s*(true|false)\s*$', re.MULTILINE)
_KV_RATE_STR = re.compile(r'^\s*(\w+)\s*=\s*"(\d+)/min"\s*$', re.MULTILINE)
_KV_RATE_TABLE = re.compile(r'^\s*(\w+)\s*=\s*\{[^}]+\}', re.MULTILINE)
```

**`get_allow_net()` pattern** — mirrors `get_max_iterations()` (`config.py` lines 70-86):
```python
def get_allow_net() -> bool:
    """Resolve tools.allow_net, falling back to RuntimeConfig default (False)."""
    default = RuntimeConfig().allow_net
    p = config_path()
    if not p.exists():
        return default
    try:
        text = p.read_text()
    except OSError:
        return default
    m = _TOOLS_BLOCK.search(text)
    if not m:
        return default
    block = m.group(0)
    bm = _KV_BOOL.search(block)
    if not bm:
        return default
    return bm.group(1) == "true"
```

**PITFALL:** `[net.rate_limits]` has a dot — `_NET_RATE_BLOCK` must use `r"^\[net\.rate_limits\][^\[]*"` (escaped dot). The unescaped version matches `[netXrate_limits]` etc. Test the regex against a fixture TOML before shipping.

---

### `voss/harness/cli.py` (extend — `mcp` group + `--allow-net` flag)

**Analog:** `plugin_group` + `plugin_enable_cmd` pattern (`cli.py` lines 1621-1637)

**Click group pattern** (`cli.py` lines 1621-1637):
```python
@click.group("plugin")
def plugin_group() -> None:
    """Manage plugin manifest enablement."""

@plugin_group.command("enable")
@click.argument("plugin_id")
def plugin_enable_cmd(plugin_id: str) -> None:
    path = set_plugin_enabled(plugin_id, True)
    click.echo(f"plugin {plugin_id} enabled: {path}")
```

**`mcp` group extension** — follows exact same pattern:
```python
@click.group("mcp")
def mcp_group() -> None:
    """Inspect and debug MCP server connections."""

@mcp_group.command("list")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="Emit machine-readable JSON.")
def mcp_list_cmd(cwd_str: str, json_mode: bool) -> None:
    """List configured MCP servers and their advertised tools."""
    ...

@mcp_group.command("call")
@click.argument("server")
@click.argument("tool_name")
@click.option("--arg", "args", multiple=True, help="key=value argument (repeatable).")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def mcp_call_cmd(server: str, tool_name: str, args: tuple[str, ...], cwd_str: str) -> None:
    """Call an MCP tool directly (bypasses PermissionGate — developer tool)."""
    ...
```

**`--allow-net` flag on `do_cmd`** — mirrors `--yes` flag (`cli.py` lines 922-929):
```python
@click.option("--yes", "yes_to_all", is_flag=True, help="Skip permission prompts.")
# add:
@click.option("--allow-net", "allow_net", is_flag=True, help="Enable network tools for this session.")
```

Inside `do_cmd` body — add after `_resolve_default_model(model)`:
```python
if allow_net:
    configure(allow_net=True)
```

---

## Shared Patterns

### Error Envelope Convention
**Source:** `voss/harness/tools.py` lines 54-56, 96-97
**Apply to:** All new tool bodies (`web_fetch`, `web_search`, MCP tool wrappers)
```python
return f"<error: not found: {path}>"        # existing pattern
return f"<timeout: 30s>"                     # existing pattern
# T3 extensions follow same format:
return "<error: net disabled: set tools.allow_net = true in harness.toml or pass --allow-net>"
return f"<error: http {status}: {reason}>"
return f"<error: rate limit: retry after {N}s>"
return f"<error: web_search disabled: set BRAVE_SEARCH_API_KEY env var>"
return "<error: mcp transport: connection lost>"
return f"<error: mcp tool: {server_error_message}>"
return f"<error: denied by mcp scope: {server} at {scope}, requires edit>"
```

### `asyncio.create_subprocess_exec` Pattern
**Source:** `voss/harness/tools.py` lines 82-98 (`shell_run`) and lines 210-228 (`_shell_capture`)
**Apply to:** `voss/harness/mcp/client.py`
```python
proc = await asyncio.create_subprocess_exec(
    *argv,
    cwd=str(cwd),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,   # MCP: PIPE not STDOUT — keep stderr separate
)
# timeout pattern:
out, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
```
MCP difference: read/write line-by-line with `readline()` + `stdin.write()` + `stdin.drain()`, NOT `communicate()`.

### Telemetry Emit Pattern
**Source:** `voss/harness/agent.py` (call sites), `voss/harness/telemetry.py` lines 150-183
**Apply to:** `voss/harness/net.py` (NetSession emit wrappers)
```python
from . import telemetry
if telemetry.enabled():
    telemetry.emit(
        "net.request",
        "info",
        data={
            "tool": tool_name,
            "url": telemetry.redact_url(url),
            "method": "GET",
            "started_at": started_at,
        },
    )
```
The `telemetry.emit` call is cheap when disabled (`enabled()` short-circuits). Always guard with `enabled()` to avoid arg construction cost.

### `@pytest.fixture` + `monkeypatch` + `xdg` Pattern
**Source:** `tests/harness/test_harness_config.py` lines 11-14, `tests/harness/test_agent_config.py` lines 12-14
**Apply to:** All new tests that touch TOML config
```python
@pytest.fixture
def xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path

@pytest.fixture(autouse=True)
def _reset_runtime():
    reset_config()
    yield
    reset_config()
```

### `asyncio.run()` Wrapper for Sync Test Invocation
**Source:** `tests/harness/test_tools.py` lines 17-18
```python
def _run(coro):
    return asyncio.run(coro)
```
**Apply to:** `test_web_fetch.py`, `test_web_search.py`, `test_mcp_client.py` — all async tool invocation tests.
Note: `pyproject.toml` sets `asyncio_mode = "auto"` — test functions declared `async def` run automatically. Use `async def test_*` for async tests; `_run()` wrapper is needed only when calling from sync context.

### Pydantic Schema with STRICT + Field defaults
**Source:** `voss/harness/cognition_schemas.py` lines 51-54
**Apply to:** `voss/harness/mcp/config.py` (`McpServerConfig`, `McpConfig`)
```python
STRICT = {"extra": "forbid"}

class McpServerConfig(BaseModel):
    model_config = STRICT
    command: list[str]                           # required
    args: list[str] = Field(default_factory=list)
    timeout_s: float = 30.0
    env: list[str] | None = None                 # None = inherit full parent env
```

### PermissionGate Structural Denial Test Pattern
**Source:** `tests/harness/test_permissions_modes.py` lines 43-53
**Apply to:** `tests/harness/test_allow_net.py`, `tests/harness/mcp/test_mcp_scope.py`
```python
def _fail_prompt(*_args, **_kwargs) -> str:
    pytest.fail("prompt called — structural denial should bypass prompting")

def test_net_gate_denies_before_prompt(tmp_path: Path) -> None:
    gate = PermissionGate(mode="edit", store=PermissionStore(cwd=tmp_path))
    gate.prompt_fn = _fail_prompt
    allowed, why = gate.check("web_fetch", {"url": "https://x.com"}, is_mutating=False, is_network=True)
    assert allowed is False
    assert "net disabled" in why
```

### CI Workflow Job Pattern
**Source:** `.github/workflows/ci.yml` lines 32-49
**Apply to:** `.github/workflows/mcp-integration.yml`
```yaml
jobs:
  stub:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: pyproject.toml
      - run: pip install -e ".[dev]"
      - run: pytest -q -m "not live" ...
```
`mcp-integration.yml` adds a `actions/setup-node@v4` step before `pytest` to make `npx` available. The integration test is triggered separately (not in the matrix) and uses `pytest -m "mcp_integration"` or a direct shell command to invoke `voss mcp call`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `voss/harness/lifecycle.py` | utility | event-driven | No atexit/shutdown hook module exists. Greenfield. Pioneer the pattern; MCP and LSP (M10) will both use it. |
| `voss/harness/mcp/__init__.py` | package init | — | No existing subpackage in `voss/harness/`. Empty `__init__.py` or minimal re-export. |

---

## Metadata

**Analog search scope:** `voss/harness/`, `voss_runtime/`, `tests/harness/`, `.github/workflows/`
**Files scanned:** 14 source + 8 test + 1 CI workflow
**Key finding — CLI uses click, not argparse:** Despite RESEARCH Pattern 7 mentioning argparse, the actual `cli.py` uses `click`. All `mcp` group additions must use `@click.group` / `@click.command` decorators. Do NOT introduce argparse.
**Key finding — asyncio_mode = "auto":** Tests declared `async def test_*` run automatically without `@pytest.mark.asyncio`. No decorator needed.
**Key finding — pyyaml confirmed in tree:** `voss/harness/cognition.py` imports `yaml` directly — pyyaml is a confirmed project dependency. No `pyproject.toml` change needed for `mcp/config.py`.
**Pattern extraction date:** 2026-05-15
