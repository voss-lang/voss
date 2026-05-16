# Phase T3: Network Surface (WebFetch + WebSearch + MCP client) — Research

**Researched:** 2026-05-15
**Domain:** httpx async HTTP · MCP JSON-RPC stdio · Brave Search API · Token bucket rate limiting · asyncio subprocess
**Confidence:** HIGH (all primary claims verified via official docs, registry, or live introspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01** Module layout: `voss/harness/mcp/{client,config,registry}.py` (3 files)
- **D-02** Lazy-launch: server subprocess spawns on first tool call via `McpClient.ensure_launched`
- **D-03** Reap-on-exit: new `voss/harness/lifecycle.py`; SIGTERM with 5s deadline before SIGKILL
- **D-04** `.voss/mcp.yml` schema: `${VAR}` env-var interpolation, `{cwd}` templating, per-server `timeout_s`, per-server `env` allowlist
- **D-05** Single shared `httpx.AsyncClient` for web_fetch + web_search, lazy-constructed, closed via lifecycle.py hook
- **D-06** `NetSession` lives in new `voss/harness/net.py`; tests at `tests/harness/test_net.py`
- **D-07** `BraveBackend(api_key)` class in flat `voss/harness/web_search.py`; no protocol abstraction in T3
- **D-08** `make_toolset(cwd, *, net: NetSession | None = None)`; backward-compatible; net=None → disabled-error envelope
- **D-09** `is_network: bool = False` stored field on `ToolEntry` dataclass (mirrors `is_mutating`)
- **D-10** `PermissionGate.check` order: `auto_yes → net-check (before mode-tier) → mode-tier → deny-rules → prompt/diff`; net denial emits no telemetry
- **D-11** MCP scope re-classification at registration time in `registry.py`; uses `destructiveHint` from tool descriptor; absent → `is_mutating=True` (safe default)
- **D-12** Denial UX: `<error: net disabled: ...>` string in tool result; no new exception type
- **D-13** CLI: click sub-group `voss mcp {list,call}`; `list` defaults pretty, `--json` flag; `call` bypasses PermissionGate. *(Corrected from "argparse subparser" — PATTERNS.md confirms cli.py is click-based at lines 1621-1637.)*
- **D-14** `--arg key=value` repeatable; JSON-typed when parseable, string fallback
- **D-15** `redact_url(url: str) -> str` in `voss/harness/telemetry.py` alongside `redact_tool_args`
- **D-16** `NetSession.acquire(tool_name)` → `AcquireResult`; defaults: web_fetch 30/min burst 30, web_search 10/min burst 10; MCP tools skip; per-`[net.rate_limits]` override

### Claude's Discretion

- Exact MCP JSON-RPC protocol version (latest stable = 2025-11-25)
- Exact `httpx.AsyncClient` constructor kwargs
- `voss mcp list --json` exact JSON shape
- Placement of rate-limit deterministic-clock tests (`tests/harness/test_rate_limit.py` recommended)
- Whether `redact_url` strips userinfo — recommend YES
- Whether `web_search` deduplicates result URLs — recommend YES (dedup-by-url, first-occurrence wins)

### Deferred Ideas (OUT OF SCOPE)

- Tavily search backend
- HTTP MCP transport
- Per-host rate limiting
- Streaming web_fetch / SSE / WebSocket
- Response caching
- POST/PUT/DELETE web_fetch
- MCP tool descriptor caching
- Reload permissions.yml mid-session
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NET-01 | `web_fetch(url, timeout_s)` HTTP GET via httpx, is_network=True, 1 MB cap, clamp [1,120]s | httpx.AsyncClient verified; truncation marker pattern from shell_run established |
| NET-02 | `web_search(query, count)` Brave backend, BRAVE_SEARCH_API_KEY, count clamp [1,20] | Brave endpoint and response schema verified; result bundle format pinned |
| NET-03 | MCP stdio client: `voss/harness/mcp/{client,config,registry}.py`; lazy launch; SIGTERM reap | MCP protocol 2025-11-25 framing verified; initialize/tools/list shapes pinned |
| NET-04 | MCP permission scopes: `PermissionsConfig.mcp: dict[str, McpScope]`; `destructiveHint` → `is_mutating` | ToolAnnotations schema verified; filesystem server tool annotations pinned |
| NET-05 | `allow_net: bool = False` default; CLI `--allow-net`; config `[tools] allow_net`; gate integration | Existing config pattern (config.py `_parse_agent_section`) reusable verbatim |
| NET-06 | `net.request`/`net.response`/`mcp.request`/`mcp.response` telemetry; `redact_url` | telemetry.emit pattern fully understood; redact_url is pure stdlib |
| NET-07 | Per-tool `TokenBucket(rate_per_min, burst)` in `rate_limit.py`; MCP unlimited | Pure stdlib implementation pattern verified; monotonic clock test pattern researched |
</phase_requirements>

---

## Summary

Phase T3 wires three network-capable tool surfaces through a single opt-in gate. The research confirms all locked decisions are well-supported by current upstream specs and the existing codebase patterns. No locked decision requires reconsideration.

The MCP stdio framing is newline-delimited JSON-RPC 2.0 (one message per line, UTF-8, no embedded newlines). The protocol version to target is **2025-11-25** — the current stable spec. The initialize → initialized → tools/list handshake is a strict three-step sequence before any tool calls. The `destructiveHint` field lives in the `annotations` sub-object of the Tool descriptor (not at the top level).

The Brave Search API endpoint is `https://api.search.brave.com/res/v1/web/search` with `X-Subscription-Token: <key>` header. The `count` parameter max is 20 (matches SPEC clamp). Results come back in `response.web.results[].{title, url, description}`.

The existing `voss/harness/config.py` regex-based TOML parser is the exact pattern to extend for `[tools]` and `[net.rate_limits]` sections. The `make_toolset` backward-compat extension with `*, net=None` kwarg is clean. Critically: **no existing `atexit`/lifecycle hook exists** — T3 pioneers `lifecycle.py`, and the planner must treat this as a greenfield module with no predecessor to mirror.

**Primary recommendation:** Implement in wave order: (1) rate_limit.py + net.py skeleton + telemetry.redact_url [pure stdlib, testable in isolation], (2) web_fetch + web_search + PermissionGate net-check [httpx mock transport], (3) mcp/client.py + mcp/config.py + mcp/registry.py [asyncio.subprocess], (4) CLI + config loader extensions, (5) CI integration job.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| web_fetch tool body | API/Tool layer (`voss/harness/net.py`) | — | Tool dispatch; httpx async client owned by NetSession |
| web_search tool body | API/Tool layer (`voss/harness/web_search.py`) | — | BraveBackend owns HTTP; NetSession owns session/rate-limiting |
| MCP subprocess launch | API/Tool layer (`voss/harness/mcp/client.py`) | — | asyncio.subprocess; not a network layer |
| MCP tool registration | Tool registry (`voss/harness/mcp/registry.py`) | — | ToolEntry adapter; scope classification at registration time |
| Rate limiting | `voss/harness/rate_limit.py` | `voss/harness/net.py` | TokenBucket owned by rate_limit; NetSession.acquire() is the call site |
| Permission gate net-check | `voss/harness/permissions.py` | — | Net-check inserted in PermissionGate._check_impl before mode-tier |
| URL telemetry redaction | `voss/harness/telemetry.py` | — | Pure function alongside redact_tool_args |
| Config loading | `voss/harness/config.py` | `voss_runtime/_config.py` | config.py: TOML parser for [tools]/[net.rate_limits]; _config.py: RuntimeConfig dataclass |
| Subprocess lifecycle reap | `voss/harness/lifecycle.py` (greenfield) | — | Shared hook for MCP subprocesses + NetSession.aclose() |
| CLI subcommands | `voss/harness/cli.py` | — | click sub-group added to existing main cli group (see cli.py:1621-1637 analog) |

---

## Standard Stack

### Core (already vendored — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | 0.28.1 (installed) | HTTP GET for web_fetch; Brave API calls for web_search | Already vendored in voss/harness; AsyncClient pattern established in providers.py |
| `asyncio` | stdlib | MCP stdio subprocess I/O | SPEC constraint: no external MCP SDK; asyncio.subprocess is the stdlib primitive |
| `time` (monotonic) | stdlib | Token bucket clock source | monotonic is test-mockable; immune to system clock adjustments |
| `pyyaml` | project dep (check) | `.voss/mcp.yml` loader | YAML is the established `.voss/` config format |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `urllib.parse` | stdlib | `redact_url` — parse + strip query/fragment | Pure stdlib; `urlparse` + `urlunparse` cover this exactly |
| `subprocess` | stdlib | `asyncio.create_subprocess_exec` kwargs | Already used in tools.py `_shell_capture` |

**No new external Python dependencies are added in T3.** httpx is already vendored. All other components use stdlib.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw asyncio subprocess JSON-RPC | `mcp` Python SDK | SDK adds an external dep; SPEC explicitly forbids new external deps |
| `urllib.parse` for redact_url | `yarl` or `furl` | External dep; urllib.parse handles scheme+netloc+path+query+fragment exactly |
| `time.monotonic` for bucket | `trio` clock / `asyncio.get_event_loop().time()` | monotonic is simpler and directly mockable in tests via monkeypatch |

**Installation:** No new packages required. Verify pyyaml is in pyproject.toml:

```bash
grep pyyaml /Users/benjaminmarks/Projects/Voss/pyproject.toml
```

---

## Package Legitimacy Audit

No new external Python packages are introduced in T3. httpx (0.28.1) is already installed and vendored. All other components are Python stdlib.

For the CI integration job, `@modelcontextprotocol/server-filesystem@2026.1.14` is invoked via `npx -y` — it is not a Python dependency.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `httpx` | PyPI | ~6 yrs | Very high (already installed) | github.com/encode/httpx | N/A — already vendored | Approved (pre-existing) |
| `@modelcontextprotocol/server-filesystem` | npm | Jan 2026 (v2026.1.14 published 2026-01-14) | Authoritative Anthropic package | github.com/modelcontextprotocol/servers | N/A — CI-only, not installed | Approved for CI fixture |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck not run (no new packages to check). All existing vendored packages pre-approved.*

---

## Architecture Patterns

### System Architecture Diagram

```
Agent loop
    │
    ├─► PermissionGate.check(tool_entry)
    │       │
    │       ├── [is_network=True AND allow_net=False] ──► <error: net disabled: ...>  (no telemetry)
    │       └── [pass] ──► mode-tier check ──► deny-rules ──► prompt/auto
    │
    ├─► web_fetch(url, timeout_s)
    │       │
    │       ├── NetSession.acquire("web_fetch") ──► [rate limited] ──► <error: rate limit: ...>
    │       ├── telemetry.emit("net.request", url=redact_url(url))
    │       ├── httpx.AsyncClient.get(url, timeout=timeout_s)
    │       │       └── [response] ──► truncate at 1 MB if needed
    │       └── telemetry.emit("net.response", status=..., bytes=...)
    │
    ├─► web_search(query, count)
    │       │
    │       ├── [BRAVE_SEARCH_API_KEY unset] ──► <error: web_search disabled: ...>
    │       ├── NetSession.acquire("web_search")
    │       ├── BraveBackend.search(query, count)
    │       │       └── GET https://api.search.brave.com/res/v1/web/search
    │       │               X-Subscription-Token: <key>
    │       │               ?q=<query>&count=<count>
    │       └── format results as numbered bundle
    │
    └─► filesystem__read_file(path=...)    [MCP tool, namespaced key]
            │
            ├── McpClient.ensure_launched("filesystem")  [lazy spawn if not running]
            │       └── asyncio.create_subprocess_exec(["npx","-y","@mcp/server-filesystem","{cwd}"])
            │           handshake: initialize → initialized → tools/list
            │
            ├── telemetry.emit("mcp.request", server="filesystem", tool="read_file")
            ├── JSON-RPC write to subprocess stdin: tools/call {"name":"read_file","arguments":{...}}
            ├── JSON-RPC read from subprocess stdout (newline-delimited)
            └── telemetry.emit("mcp.response", ...)

Lifecycle reap (on session exit):
    lifecycle.py ──► SIGTERM all MCP subprocesses (5s deadline)
                 └── NetSession.aclose() ──► httpx.AsyncClient.aclose()
```

### Recommended Project Structure

```
voss/harness/
├── net.py                    # NetSession, lazy AsyncClient, redact_url calls, telemetry wrappers
├── rate_limit.py             # TokenBucket(rate_per_min, burst) + AcquireResult
├── lifecycle.py              # greenfield: shared reap hook (MCP subprocesses + NetSession)
├── web_search.py             # BraveBackend(api_key).search(query, count) -> list[SearchResult]
├── mcp/
│   ├── __init__.py
│   ├── client.py             # McpClient: asyncio.subprocess JSON-RPC, ensure_launched
│   ├── config.py             # .voss/mcp.yml schema (McpServerConfig) + loader
│   └── registry.py          # MCP ToolEntry adapter; is_mutating from destructiveHint
├── tools.py                  # extended: is_network field on ToolEntry; make_toolset(cwd, *, net=None)
├── permissions.py            # extended: net-check in _check_impl before mode_allows
├── cognition_schemas.py      # extended: PermissionsConfig.mcp: dict[str, McpScope]
├── telemetry.py              # extended: redact_url pure function
└── config.py                 # extended: [tools] + [net.rate_limits] TOML sections

tests/harness/
├── test_web_fetch.py         # NET-01 acceptance cases
├── test_web_search.py        # NET-02 acceptance cases
├── mcp/
│   ├── test_mcp_config.py    # NET-03: config loader
│   ├── test_mcp_client.py    # NET-03: asyncio subprocess mock
│   └── test_mcp_scope.py     # NET-04: permission scope enforcement
├── test_allow_net.py         # NET-05: gate integration, zero-socket invariant
├── test_net_telemetry.py     # NET-06: redact_url unit, event emission
└── test_rate_limit.py        # NET-07: TokenBucket unit, monotonic mock

.voss/
└── mcp.yml                   # project MCP server config (example fixture)

.github/workflows/
└── mcp-integration.yml       # CI job: npx @mcp/server-filesystem end-to-end
```

### Pattern 1: MCP stdio JSON-RPC framing

**What:** Newline-delimited JSON-RPC 2.0 over stdin/stdout subprocess pipes. One complete JSON object per line. Server stderr is available for logging and MUST NOT contain JSON-RPC messages.

**When to use:** All communication with any MCP server subprocess.

**Full handshake sequence (MUST complete before tools/list):**

```python
# Source: https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
# Source: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

# Step 1: Client sends initialize request
initialize_req = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {
            "name": "voss-harness",
            "version": "0.2"
        }
    }
}
# Write: json.dumps(initialize_req) + "\n" → proc.stdin

# Step 2: Server responds with its capabilities
# Read one line from proc.stdout, json.loads() it
# result.capabilities.tools confirms server supports tools

# Step 3: Client sends initialized notification (no response expected)
initialized_notif = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
}
# Write: json.dumps(initialized_notif) + "\n" → proc.stdin

# Step 4: Now safe to send tools/list
tools_list_req = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}
# Read response: result.tools = list of Tool objects
```

**asyncio subprocess pattern (stdlib only):**

```python
# Source: [ASSUMED] — derived from asyncio docs + tools.py _shell_capture pattern
import asyncio
import json
import subprocess

proc = await asyncio.create_subprocess_exec(
    *command_argv,  # e.g. ["npx", "-y", "@modelcontextprotocol/server-filesystem", str(cwd)]
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,  # capture to avoid pollution; log if VOSS_LOG enabled
    env=filtered_env,  # per D-04: env allowlist or full parent env
    cwd=str(launch_cwd),
)

async def _write_msg(proc, msg: dict) -> None:
    line = json.dumps(msg, separators=(",", ":")) + "\n"
    proc.stdin.write(line.encode("utf-8"))
    await proc.stdin.drain()

async def _read_msg(proc) -> dict:
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=30.0)
    return json.loads(line.decode("utf-8"))
```

**tools/call request shape:**

```python
# Source: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
tools_call_req = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "read_file",           # bare MCP tool name (not namespaced)
        "arguments": {"path": "./README.md"}
    }
}
# Response result.content = [{"type": "text", "text": "..."}]
# Response result.isError = False (or True on tool-level error)
```

**JSON-RPC error response shape:**

```python
# Protocol error (bad tool name, malformed request):
# {"jsonrpc": "2.0", "id": 3, "error": {"code": -32602, "message": "Unknown tool: foo"}}
# Tool execution error (server-side failure):
# {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type":"text","text":"..."}], "isError": true}}
```

### Pattern 2: Tool descriptor `annotations.destructiveHint`

**What:** The MCP Tool object has an optional `annotations` sub-object with boolean hint fields. `destructiveHint=true` signals the tool may make destructive changes.

**Tool object shape (from tools/list response):**

```python
# Source: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
# ToolAnnotations (all fields optional boolean):
#   readOnlyHint    — true → does not modify environment
#   destructiveHint — true → may perform destructive updates (only meaningful when readOnlyHint=false)
#   idempotentHint  — true → repeated calls with same args have no additional effect
#   openWorldHint   — true → may interact with external/open-world systems

tool_obj = {
    "name": "write_file",
    "description": "...",
    "inputSchema": {...},
    "annotations": {
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
    }
}

# registry.py mapping (D-11):
def _is_mutating_from_descriptor(tool: dict, scope: str) -> bool:
    if scope in ("plan",):
        return False  # all MCP tools read-only under plan scope
    annotations = tool.get("annotations") or {}
    # absent destructiveHint → safe default True
    return annotations.get("destructiveHint", True)
```

**@modelcontextprotocol/server-filesystem tool annotations:**

| Tool | readOnlyHint | destructiveHint | idempotentHint | `is_mutating` at plan scope | `is_mutating` at edit scope |
|------|-------------|----------------|----------------|------------------------------|------------------------------|
| `read_file` (alias: `read_text_file`) | true | false | — | False | False |
| `read_multiple_files` | true | false | — | False | False |
| `list_directory` | true | false | — | False | False |
| `directory_tree` | true | false | — | False | False |
| `search_files` | true | false | — | False | False |
| `get_file_info` | true | false | — | False | False |
| `list_allowed_directories` | true | false | — | False | False |
| `create_directory` | false | false | true | False | False |
| `write_file` | false | true | true | False | True |
| `edit_file` | false | true | false | False | True |
| `move_file` | false | true | false | False | True |

**Note on tool name version:** The 2026.1.14 package uses `read_text_file` as the canonical name, but CI fixture must verify actual tool names by calling `tools/list` against the pinned version and hardcoding the names in test assertions. Do not assume `read_file` is present — verify at pin time.

### Pattern 3: Brave Search API

**Endpoint:** `GET https://api.search.brave.com/res/v1/web/search` [VERIFIED via official docs]

**Request shape:**

```python
# Source: https://api-dashboard.search.brave.com/app/documentation/web-search/get-started
headers = {
    "X-Subscription-Token": api_key,
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
}
params = {
    "q": query,           # required
    "count": count,       # 1..20 (default 20 per API; SPEC clamps to 20)
}
resp = await client.get(
    "https://api.search.brave.com/res/v1/web/search",
    headers=headers,
    params=params,
    timeout=30.0,
)
```

**Response shape (relevant fields):**

```json
{
  "query": {
    "original": "python asyncio",
    "more_results_available": true
  },
  "web": {
    "results": [
      {
        "title": "Asyncio — Python Documentation",
        "url": "https://docs.python.org/3/library/asyncio.html",
        "description": "Library to write concurrent code..."
      }
    ]
  }
}
```

**Deterministic bundle format (NET-02 SPEC):**

```
1. Asyncio — Python Documentation
   https://docs.python.org/3/library/asyncio.html
   Library to write concurrent code...

2. ...
```

**429 rate-limit handling:**

```python
if resp.status_code == 429:
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        return f"<error: rate limit: retry after {retry_after}s>"
    return "<error: http 429: rate limited by backend>"
```

### Pattern 4: httpx.AsyncClient constructor for NetSession

**What:** Shared lazy client for web_fetch + web_search. Mirrors providers.py pattern.

```python
# Source: live introspection of httpx 0.28.1 (installed)
# httpx.AsyncClient defaults verified:
#   http2=False, follow_redirects=False, verify=True, timeout=Timeout(5.0), max_redirects=20

class NetSession:
    _client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                follow_redirects=True,   # D-deferred: max 5 hops, locked by deferred section
                max_redirects=5,
                verify=True,
                timeout=httpx.Timeout(30.0),  # tool-level override passed per-call
                http2=False,             # h2 adds dependency complexity; not needed for docs fetching
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
```

**Per-call timeout override:**

```python
# For web_fetch with custom timeout_s (clamped to [1, 120]):
resp = await self._http().get(url, timeout=clamped_timeout_s)
```

**MockTransport for zero-socket test:**

```python
# Source: [ASSUMED] — httpx MockTransport pattern for NET-05 AC(f)
import httpx

class _CountingTransport(httpx.MockTransport):
    calls: int = 0
    def handle_async_request(self, request):
        self.calls += 1
        return httpx.Response(200, text="mock")

transport = _CountingTransport()
client = httpx.AsyncClient(transport=transport)
# After test: assert transport.calls == 0  (zero-socket invariant)
```

### Pattern 5: TokenBucket — pure stdlib

**What:** Per-tool rate limiter, `rate_per_min` tokens refilled per minute, `burst` capacity.

```python
# Source: [ASSUMED] — standard token bucket algorithm; time.monotonic is stdlib
import math
import time
from dataclasses import dataclass, field

@dataclass
class TokenBucket:
    rate_per_min: int
    burst: int
    _tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = float(self.burst)
        self._last = time.monotonic()

    def acquire(self) -> tuple[bool, float]:
        """Returns (ok, retry_after_seconds). ok=False means rate limited."""
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        # Refill tokens: rate_per_min tokens per 60 seconds
        self._tokens = min(
            float(self.burst),
            self._tokens + elapsed * (self.rate_per_min / 60.0)
        )
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True, 0.0
        # Seconds until next token
        retry_after = (1.0 - self._tokens) / (self.rate_per_min / 60.0)
        return False, retry_after
```

**Deterministic-clock test pattern:**

```python
# Source: [ASSUMED] — monkeypatch time.monotonic for deterministic tests
def test_token_bucket_replenish(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("voss.harness.rate_limit.time.monotonic", lambda: clock[0])
    bucket = TokenBucket(rate_per_min=60, burst=60)
    for _ in range(60):
        ok, _ = bucket.acquire()
        assert ok
    ok, retry = bucket.acquire()
    assert not ok
    # Advance 1 second: 1 token refilled
    clock[0] += 1.0
    ok, _ = bucket.acquire()
    assert ok
```

**Config parsing for `[net.rate_limits]`:**

```toml
# ~/.config/voss/config.toml
[net.rate_limits]
web_fetch = "60/min"
web_search = "10/min"
# or table form:
# web_fetch = { rate = 60, burst = 120 }
```

```python
# Parsing pattern (extend voss/harness/config.py):
_NET_RATE_BLOCK = re.compile(r"^\[net\.rate_limits\][^\[]*", re.MULTILINE)
_KV_RATE = re.compile(r'^\s*(\w+)\s*=\s*"(\d+)/min"\s*$', re.MULTILINE)
_KV_RATE_TABLE = re.compile(r'^\s*(\w+)\s*=\s*\{[^}]+\}', re.MULTILINE)
```

### Pattern 6: `redact_url` implementation

**What:** Strip `?query` and `#fragment`; preserve scheme + netloc + path. Optional: strip userinfo (recommended).

```python
# Source: [ASSUMED] — urllib.parse is stdlib; behavior is straightforward
from urllib.parse import urlparse, urlunparse

def redact_url(url: str) -> str:
    """Strip query string, fragment, and optionally userinfo from a URL.

    Preserves scheme, host, and path. Telemetry-safe.
    """
    try:
        p = urlparse(url)
        # Strip userinfo (user:pass@host → host)
        netloc = p.hostname or ""
        if p.port:
            netloc = f"{netloc}:{p.port}"
        clean = p._replace(query="", fragment="", netloc=netloc)
        return urlunparse(clean)
    except Exception:
        return "<redacted-url>"
```

**Test assertions (NET-06 AC):**

```python
assert redact_url("https://x.com/p?k=v#f") == "https://x.com/p"
assert redact_url("https://x.com/p") == "https://x.com/p"
assert redact_url("https://user:pass@host/path") == "https://host/path"
```

### Pattern 7: `[tools] allow_net` config extension

**What:** Extend `voss/harness/config.py` with a `[tools]` section parser, following the exact `_AGENT_BLOCK` pattern used for `max_iterations`.

```python
# Source: voss/harness/config.py — existing pattern replicated
_TOOLS_BLOCK = re.compile(r"^\[tools\][^\[]*", re.MULTILINE)
_KV_BOOL = re.compile(r'^\s*allow_net\s*=\s*(true|false)\s*$', re.MULTILINE)

def get_allow_net() -> bool:
    """Resolve tools.allow_net, falling back to RuntimeConfig default (False)."""
    p = config_path()
    if not p.exists():
        return False
    try:
        text = p.read_text()
    except OSError:
        return False
    m = _TOOLS_BLOCK.search(text)
    if not m:
        return False
    block = m.group(0)
    bm = _KV_BOOL.search(block)
    if not bm:
        return False
    return bm.group(1) == "true"
```

**RuntimeConfig extension (`voss_runtime/_config.py`):**

```python
# Add field (mirrors max_iterations from T1-04):
allow_net: bool = False
```

**CLI `--allow-net` flag (argparse, mirrors existing click/argparse hybrid):**

The CLI uses `click` (confirmed in cli.py imports). Add `--allow-net` as a click option on the `do` and `chat` commands, writing through via `configure(allow_net=True)`.

### Pattern 8: `PermissionGate.check` net-check insertion

**What:** Net-check fires BEFORE mode-tier in `_check_impl`. Requires access to `runtime.allow_net` and `tool_entry.is_network`.

```python
# Source: voss/harness/permissions.py — _check_impl extended
def _check_impl(self, tool_name: str, args: dict, *,
                is_mutating: bool = False,
                is_network: bool = False) -> tuple[bool, str]:
    # 0. Project-policy deny (unchanged)
    if self.project_policy is not None:
        if tool_name in self.project_policy.tool_policy.deny:
            return False, "denied by .voss/permissions.yml"

    # 0.5 Network gate — fires before mode-tier, emits NO telemetry on denial
    if is_network:
        from voss_runtime._config import get_config
        if not get_config().allow_net:
            return False, (
                "net disabled: set tools.allow_net = true in harness.toml or pass --allow-net"
            )

    # 1. Mode-tier (unchanged from today)
    allowed, why = mode_allows(self.mode, tool_name, is_mutating)
    ...
```

**Caller site (agent loop tool dispatch):** Pass `is_network=entry.is_network` from `ToolEntry`.

### Anti-Patterns to Avoid

- **Parsing MCP newline-delimited JSON with `readline()` without a timeout:** Subprocess may hang. Always wrap in `asyncio.wait_for(..., timeout=30.0)`.
- **Per-call `httpx.AsyncClient()`:** Loses connection pooling; anti-pattern per httpx docs. Use the lazy singleton on `NetSession`.
- **Writing `print()` or anything to stdout from the MCP server subprocess:** MCP protocol uses stdout for JSON-RPC; any extra output corrupts the stream.
- **Registering two `atexit` handlers (one for MCP, one for NetSession):** Use the single `lifecycle.py` hook for both — avoids ordering bugs.
- **Importing `mcp` Python SDK:** The SDK is an external dep; SPEC forbids new external deps. Implement the JSON-RPC framing directly with asyncio.subprocess.
- **Checking `is_network` by tool name prefix:** Fragile for MCP namespaced tools like `filesystem__read_file`. Use the stored `ToolEntry.is_network` field.
- **Sending `tools/call` before `initialized` notification is sent:** Protocol violation per spec lifecycle ordering.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client pooling | Custom connection manager | `httpx.AsyncClient` (already vendored) | Connection reuse, timeout, redirect handling built in |
| URL query string stripping | String split/replace on `?` | `urllib.parse.urlparse` + `urlunparse` | Handles encoded chars, edge cases (no query, fragment only) |
| JSON-RPC message framing | Custom binary framing | Newline-delimited JSON (`json.dumps + "\n"`, `readline`) | MCP spec mandates this exact framing |
| Token replenishment math | Leaky bucket / sliding window | Standard token bucket with `time.monotonic` | Token bucket is well-specified and deterministic-clock-testable |
| YAML loading | Custom parser | `yaml.safe_load` (pyyaml) | PyYAML is already a project dependency for `.voss/` config files |

**Key insight:** All four "don't hand-roll" items have either a stdlib solution or an already-vendored library. The MCP client is the exception — the MCP Python SDK is external, so raw asyncio.subprocess + json IS the right implementation for this project's constraints.

---

## Runtime State Inventory

Not applicable — T3 is a greenfield feature phase. No rename/refactor/migration involved.

---

## Common Pitfalls

### Pitfall 1: MCP subprocess stdout corruption via logging

**What goes wrong:** Any `print()` statement or logger that writes to stdout inside an MCP server subprocess will corrupt the JSON-RPC protocol stream. The client receives garbled JSON and the entire session crashes.

**Why it happens:** MCP uses stdout for protocol messages. The client reads lines and tries to parse each as JSON.

**How to avoid:** Redirect all subprocess stderr to a pipe and optionally log it via `telemetry.emit`. Never write to stdout outside of MCP protocol messages. In the CI fixture, verify that `npx -y @modelcontextprotocol/server-filesystem` does not write logging to stdout.

**Warning signs:** `json.JSONDecodeError` on the first readline from the subprocess.

### Pitfall 2: `initialized` notification forgotten

**What goes wrong:** Sending `tools/list` before `notifications/initialized` violates the lifecycle spec. Some MCP servers will silently ignore it; others will return an error or hang.

**Why it happens:** The three-step handshake (initialize → server response → initialized notification) is easy to collapse to two steps.

**How to avoid:** Make the handshake a fixed sequence in `McpClient._handshake()` with no branching. Write a unit test that asserts all three messages are sent in order using a mock transport.

**Warning signs:** `tools/list` returns an empty list or times out on the real server.

### Pitfall 3: httpx `follow_redirects=False` default

**What goes wrong:** `httpx.AsyncClient` defaults to `follow_redirects=False`. A `web_fetch` call to a URL that redirects (e.g., `http://` → `https://`, or a short URL) silently returns a 301/302 response body instead of following.

**Why it happens:** httpx changed the default from requests (which followed redirects by default). D-deferred section allows following redirects.

**How to avoid:** Construct `NetSession._client` with `follow_redirects=True, max_redirects=5` as shown in the code pattern above. This is locked (deferred section says planner picks this).

**Warning signs:** `web_fetch` returns a short HTML `<html><head><meta http-equiv="refresh"...>` page instead of the actual content.

### Pitfall 4: MCP tool name mismatch between fixture and real server

**What goes wrong:** The server-filesystem 2026.1.14 package uses `read_text_file` as the canonical read tool name, not `read_file`. Tests that assert for `filesystem__read_file` will fail.

**Why it happens:** The server tool names are determined by the pinned npm package, not by the SPEC. The SPEC example in NET-03 uses `filesystem__read_file` as a placeholder.

**How to avoid:** In the CI integration job, first run `voss mcp list` and capture the actual tool names. The NET-03 acceptance criteria fixture should call `tools/list` against the mock and assert the returned names match exactly. Do not hard-code `read_file` — check `read_text_file` against the 2026.1.14 server.

**Warning signs:** `filesystem__read_file` not found in toolset after server registration.

### Pitfall 5: `allow_net=False` path accidentally opens a socket

**What goes wrong:** If the `is_network` check is in `_check_impl` but the tool body also short-circuits independently (per D-08 `net=None`), a coding error could cause a tool body to run the real HTTP call even when `allow_net=False`.

**Why it happens:** Two denial paths: gate-level and tool-body-level. If they're not consistently wired, one can bypass the other.

**How to avoid:** The gate-level check (D-10) is the security invariant. The tool-body check (D-08, `net=None`) is a defensive belt-and-suspenders. The CI zero-socket test (NET-05 AC-f via MockTransport) is the definitive proof. Run this test in CI with `allow_net=False` and verify `transport.calls == 0`.

**Warning signs:** MockTransport call count > 0 when `allow_net=False`.

### Pitfall 6: TOML `[net.rate_limits]` nested section regex

**What goes wrong:** The existing regex pattern in `config.py` matches `[section]` blocks by scanning to the next `[`. The `[net.rate_limits]` block has a dot in the section name. The regex `^\[net\.rate_limits\]` requires escaping the dot.

**Why it happens:** `re.compile(r"^\[net.rate_limits\][^\[]*", re.MULTILINE)` — the unescaped dot matches any character. Use `r"^\[net\.rate_limits\]"`.

**How to avoid:** Test the regex against a fixture TOML file with adjacent sections before shipping.

**Warning signs:** Config parser matches the wrong section and returns incorrect rate limits.

### Pitfall 7: Per-session bucket state not reset between tests

**What goes wrong:** `TokenBucket` instances are created per `NetSession` (per `voss` invocation). In tests, if `NetSession` is a module-level singleton, token state persists between test cases and makes rate-limit tests order-dependent.

**Why it happens:** Class-level or module-level bucket registry shared across test instances.

**How to avoid:** Create a fresh `NetSession` (and thus fresh `TokenBucket` instances) in each test fixture. Use `pytest` fixtures with function scope.

**Warning signs:** Test order matters; rate limit tests pass alone but fail in the full suite.

---

## Code Examples

### Complete MCP handshake + tools/list (stdlib only)

```python
# Source: [ASSUMED] — derived from MCP spec (VERIFIED) + asyncio.subprocess (stdlib)
import asyncio, json, subprocess

async def _handshake_and_list_tools(proc) -> list[dict]:
    """Run initialize → initialized → tools/list. Returns raw tool list."""

    async def _write(msg: dict) -> None:
        data = json.dumps(msg, separators=(",", ":")) + "\n"
        proc.stdin.write(data.encode("utf-8"))
        await proc.stdin.drain()

    async def _read() -> dict:
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=30.0)
        return json.loads(line.decode("utf-8"))

    # Step 1: initialize
    await _write({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "voss-harness", "version": "0.2"}
        }
    })
    init_resp = await _read()
    # Verify server acknowledged protocol version
    assert init_resp.get("result", {}).get("protocolVersion") == "2025-11-25"

    # Step 2: initialized notification (no response expected)
    await _write({"jsonrpc": "2.0", "method": "notifications/initialized"})

    # Step 3: tools/list
    await _write({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools_resp = await _read()
    return tools_resp.get("result", {}).get("tools", [])
```

### `ToolEntry` extension with `is_network`

```python
# Source: voss/harness/tools.py — additive extension (D-09)
@dataclass(frozen=True)
class ToolEntry:
    descriptor: ToolDescriptor
    is_mutating: bool
    is_network: bool = False  # new field; default=False preserves all existing call sites

    # existing properties: name, description, parameters, invoke, invoke_dict unchanged
```

### `make_toolset` extension with `net` kwarg

```python
# Source: voss/harness/tools.py — additive extension (D-08)
def make_toolset(cwd: Path, *, net: "NetSession | None" = None) -> dict[str, ToolEntry]:
    # ... existing tools unchanged ...

    @tool(name="web_fetch", description="Fetch a URL via HTTP GET. Requires --allow-net.")
    async def web_fetch(url: str, timeout_s: float = 30.0) -> str:
        if net is None:
            return "<error: net disabled: set tools.allow_net = true in harness.toml or pass --allow-net>"
        return await net.fetch(url, timeout_s=timeout_s)

    # ... web_search similarly ...

    result = {
        # ... existing entries unchanged ...
        "web_fetch": ToolEntry(descriptor=web_fetch, is_mutating=False, is_network=True),
        "web_search": ToolEntry(descriptor=web_search, is_mutating=False, is_network=True),
    }
    # MCP tools added by registry.py at server registration time (not here)
    return result
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MCP HTTP+SSE transport | Streamable HTTP or stdio | 2025-11-25 spec | Stdio is preferred for local subprocesses; HTTP+SSE deprecated |
| `response_format` for tool annotations | `annotations.destructiveHint` sub-object | 2024-11-05+ | Distinct `annotations` object in Tool descriptor; not top-level field |
| httpx default follows redirects | `follow_redirects=False` (must opt in) | httpx ~0.20 | Must explicitly pass `follow_redirects=True` in AsyncClient constructor |
| MCP `readOnlyHint` as primary mutation signal | `destructiveHint` for explicit mutation, `readOnlyHint` for read classification | 2025-11-25 | Both fields present; use `destructiveHint` to set `is_mutating`, `readOnlyHint` for read classification |

**Deprecated/outdated:**

- `HTTP+SSE` MCP transport: replaced by Streamable HTTP in 2025-11-25 spec. voss uses stdio, which is unaffected.
- MCP `toolSchema` field: renamed to `inputSchema` in current spec. Use `inputSchema`.

---

## Open Questions (RESOLVED)

1. **pyyaml dependency presence**
   **RESOLVED:** PATTERNS.md confirms cognition.py:21 imports `yaml`; T3-01 Task 2 verifies pyproject.toml main-deps inclusion of pyyaml as part of Wave 0 scaffolding.
   - What we know: `.voss/mcp.yml` loader requires YAML parsing; the project uses `.voss/` YAML files (constraints.yml, permissions.yml, validation.yml)
   - What's unclear: Whether `pyyaml` is already in `pyproject.toml` dependencies or only in dev deps
   - Recommendation: `grep pyyaml /Users/benjaminmarks/Projects/Voss/pyproject.toml` before Wave 0. If absent, add to main deps.

2. **Exact tool names in server-filesystem 2026.1.14**
   **RESOLVED:** T3-09 Task 1 is a blocking-human checkpoint that pins the exact read-tool name by calling `tools/list` against the pinned `@modelcontextprotocol/server-filesystem` npm dist; the resolved value is recorded as `READ_TOOL_NAME` and substituted into the CI workflow before merge.
   - What we know: README for the servers repo lists `read_text_file` (not `read_file`). NET-03 acceptance criteria uses `filesystem__read_file` as placeholder.
   - What's unclear: Whether the 2026.1.14 npm dist uses `read_text_file` or a different alias.
   - Recommendation: In Wave 0 or the CI job, run `npx -y @modelcontextprotocol/server-filesystem@2026.1.14 /tmp 2>/dev/null & sleep 2 && echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}' | nc -q1 localhost <port>` — or simpler: run the integration test first, capture `tools/list` output, update test fixture. The planner should add a Wave 0 task to pin the actual tool names.

3. **`PermissionGate.check` signature change scope**
   **RESOLVED:** T3-02 Task 2 audits all `.check(` call sites via `grep -rn "\.check(" voss/harness/`; the signature extension is additive (new kwarg `is_network: bool = False` with safe default) — every existing caller continues to compile and pass without modification, and T3-05 wires `is_network=entry.is_network` at the agent-loop dispatch site.
   - What we know: Today `check(tool_name, args, *, is_mutating)`. T3 needs `is_network` too.
   - What's unclear: Whether callers pass `is_mutating` positionally or as kwarg; need to check all call sites.
   - Recommendation: Grep for `gate.check(` across the codebase before extending the signature. The call sites in `agent.py` must pass `is_network=entry.is_network`.

4. **`.voss/mcp.yml` vs `harness.toml`**
   **RESOLVED:** CONTEXT.md D-04 locks `.voss/mcp.yml` as the MCP server registry; the loader reads `{cwd}/.voss/mcp.yml` and the file is project-scoped (consistent with `.voss/permissions.yml`).
   - What we know: D-04 says `.voss/mcp.yml` is the schema. The existing TOML config lives at `~/.config/voss/config.toml`.
   - What's unclear: Is `.voss/mcp.yml` project-scoped (lives in the repo) or global? CONTEXT.md says project-scoped (`.voss/` is the project cognition directory per COG-03).
   - Recommendation: Project-scoped. The loader reads `{cwd}/.voss/mcp.yml`. This is consistent with `.voss/permissions.yml`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.x | All | ✓ | 3.x (project-managed) | — |
| httpx | web_fetch, web_search | ✓ | 0.28.1 | — |
| pyyaml | mcp/config.py | ? | unknown — verify | If absent: add to pyproject.toml deps |
| Node.js / npx | CI integration job only | ? | unknown — CI-only | CI must install Node |
| `BRAVE_SEARCH_API_KEY` env var | web_search | ? | env-only | Tool returns disabled-error envelope |

**Missing dependencies with no fallback:**

- Node.js/npx: required only for the CI integration job. The planner must add a CI setup step (`actions/setup-node@v4`) or verify Node is available on the CI runner. This does NOT block local development or unit tests.

**Missing dependencies with fallback:**

- `BRAVE_SEARCH_API_KEY`: absent → `web_search` returns `<error: web_search disabled: set BRAVE_SEARCH_API_KEY env var>`. All unit tests mock the Brave HTTP call; no live key needed for tests.
- pyyaml: if absent from main deps, unit tests that load `.voss/mcp.yml` will fail with ImportError. Wave 0 must verify and add if needed.

---

## Validation Architecture

> `nyquist_validation: true` in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths = ["tests"] |
| Quick run command | `pytest tests/harness/test_rate_limit.py tests/harness/test_net_telemetry.py -x` |
| Full suite command | `pytest tests/harness/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NET-01a | `web_fetch` registers with `is_network=True` | unit | `pytest tests/harness/test_web_fetch.py::test_registration -x` | ❌ Wave 0 |
| NET-01b | `web_fetch` without `allow_net` returns disabled-error | unit | `pytest tests/harness/test_web_fetch.py::test_allow_net_gate -x` | ❌ Wave 0 |
| NET-01c | 2 MB httpx-mocked response truncates at 1,048,576 bytes | unit | `pytest tests/harness/test_web_fetch.py::test_truncation -x` | ❌ Wave 0 |
| NET-01d | `timeout_s=200` clamps to 120 + RuntimeWarning | unit | `pytest tests/harness/test_web_fetch.py::test_timeout_clamp -x` | ❌ Wave 0 |
| NET-01e | HTTP 4xx/5xx returns `<error: http {status}: {reason}>` | unit | `pytest tests/harness/test_web_fetch.py::test_http_errors -x` | ❌ Wave 0 |
| NET-02a | `web_search` without key returns disabled-error | unit | `pytest tests/harness/test_web_search.py::test_no_key -x` | ❌ Wave 0 |
| NET-02b | Brave-mocked happy path renders 10 results in stable order | unit | `pytest tests/harness/test_web_search.py::test_mocked_results -x` | ❌ Wave 0 |
| NET-02c | `count=50` clamps to 20 + RuntimeWarning | unit | `pytest tests/harness/test_web_search.py::test_count_clamp -x` | ❌ Wave 0 |
| NET-02d | Brave HTTP 429 with Retry-After returns rate-limit envelope | unit | `pytest tests/harness/test_web_search.py::test_429_handling -x` | ❌ Wave 0 |
| NET-03a | `.voss/mcp.yml` loader parses fixture McpServerConfig | unit | `pytest tests/harness/mcp/test_mcp_config.py -x` | ❌ Wave 0 |
| NET-03b | Mock server launches + registers namespaced tools | unit | `pytest tests/harness/mcp/test_mcp_client.py::test_lazy_launch -x` | ❌ Wave 0 |
| NET-03c | SIGTERM reap on session exit | unit | `pytest tests/harness/mcp/test_mcp_client.py::test_sigterm_reap -x` | ❌ Wave 0 |
| NET-03d | CI: `voss mcp call filesystem read_text_file path=./README.md` returns content | integration | CI job `mcp-integration` | ❌ Wave 0 (CI config) |
| NET-04a | No `mcp` block → all MCP tools `is_mutating=False` | unit | `pytest tests/harness/mcp/test_mcp_scope.py::test_default_plan_scope -x` | ❌ Wave 0 |
| NET-04b | `mcp: {filesystem: edit}` → write_file `is_mutating=True` | unit | `pytest tests/harness/mcp/test_mcp_scope.py::test_edit_scope -x` | ❌ Wave 0 |
| NET-04c | `write_file` at plan scope returns `<error: denied by mcp scope: ...>` | unit | `pytest tests/harness/mcp/test_mcp_scope.py::test_scope_denial -x` | ❌ Wave 0 |
| NET-04d | `mode=auto` + `mcp scope=plan` still denies mutating tools | unit | `pytest tests/harness/mcp/test_mcp_scope.py::test_auto_does_not_override_scope -x` | ❌ Wave 0 |
| NET-05a | `RuntimeConfig().allow_net == False` | unit | `pytest tests/harness/test_allow_net.py::test_default_false -x` | ❌ Wave 0 |
| NET-05b | `[tools] allow_net = true` in TOML → loader returns True | unit | `pytest tests/harness/test_allow_net.py::test_toml_true -x` | ❌ Wave 0 |
| NET-05c | CLI `--allow-net` overrides config-file `false` | unit | `pytest tests/harness/test_allow_net.py::test_cli_override -x` | ❌ Wave 0 |
| NET-05d | `--allow-net=false` overrides config-file `true` | unit | `pytest tests/harness/test_allow_net.py::test_cli_explicit_false -x` | ❌ Wave 0 |
| NET-05e | Gate `(False, "net disabled: ...")` before prompt logic | unit | `pytest tests/harness/test_allow_net.py::test_gate_before_prompt -x` | ❌ Wave 0 |
| NET-05f | Zero outbound sockets when allow_net=False (MockTransport) | integration | `pytest tests/harness/test_allow_net.py::test_zero_socket_invariant -x` | ❌ Wave 0 |
| NET-06a | `redact_url("https://x.com/p?k=v#f")` == `"https://x.com/p"` | unit | `pytest tests/harness/test_net_telemetry.py::test_redact_url_strips -x` | ❌ Wave 0 |
| NET-06b | `redact_url("https://x.com/p")` no-op | unit | `pytest tests/harness/test_net_telemetry.py::test_redact_url_noop -x` | ❌ Wave 0 |
| NET-06c | `web_fetch` emits exactly one `net.request` + one `net.response` | unit | `pytest tests/harness/test_net_telemetry.py::test_event_emission -x` | ❌ Wave 0 |
| NET-06d | MCP stdio call emits `mcp.request`/`mcp.response` (not `net.*`) | unit | `pytest tests/harness/test_net_telemetry.py::test_mcp_events -x` | ❌ Wave 0 |
| NET-06e | RunRecord round-trip preserves both event types | unit | `pytest tests/harness/test_net_telemetry.py::test_run_record_roundtrip -x` | ❌ Wave 0 |
| NET-07a | `TokenBucket(60,60)` permits 60 calls then errors on 61st | unit | `pytest tests/harness/test_rate_limit.py::test_bucket_exhaustion -x` | ❌ Wave 0 |
| NET-07b | 1s monotonic advance replenishes 1 token | unit | `pytest tests/harness/test_rate_limit.py::test_replenish -x` | ❌ Wave 0 |
| NET-07c | TOML `web_fetch = "60/min"` overrides default | unit | `pytest tests/harness/test_rate_limit.py::test_toml_override_string -x` | ❌ Wave 0 |
| NET-07d | TOML `web_fetch = {rate = 60, burst = 120}` parses table form | unit | `pytest tests/harness/test_rate_limit.py::test_toml_override_table -x` | ❌ Wave 0 |
| NET-07e | MCP tool calls do NOT pass through bucket | unit | `pytest tests/harness/test_rate_limit.py::test_mcp_bypasses_bucket -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/harness/test_rate_limit.py tests/harness/test_net_telemetry.py -x --tb=short`
- **Per wave merge:** `pytest tests/harness/ -x --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`: `pytest tests/ -x`

### Wave 0 Gaps

- [ ] `tests/harness/test_web_fetch.py` — NET-01 acceptance cases (5 tests)
- [ ] `tests/harness/test_web_search.py` — NET-02 acceptance cases (4 tests)
- [ ] `tests/harness/mcp/__init__.py` — make mcp a test package
- [ ] `tests/harness/mcp/test_mcp_config.py` — NET-03 config loader
- [ ] `tests/harness/mcp/test_mcp_client.py` — NET-03 subprocess mock + handshake
- [ ] `tests/harness/mcp/test_mcp_scope.py` — NET-04 permission scope
- [ ] `tests/harness/test_allow_net.py` — NET-05 gate integration + zero-socket
- [ ] `tests/harness/test_net_telemetry.py` — NET-06 redact_url + events
- [ ] `tests/harness/test_rate_limit.py` — NET-07 TokenBucket unit tests
- [ ] `.github/workflows/mcp-integration.yml` — CI integration job for NET-03d
- [ ] Verify `pyyaml` in `pyproject.toml` main deps

---

## Security Domain

> `security_enforcement` not set to false — section required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No — no user auth on these tool surfaces | — |
| V3 Session Management | No — tools are per-session stateless | — |
| V4 Access Control | Yes — `allow_net` gate + MCP scope | `PermissionGate.check` net-check; `PermissionsConfig.mcp` scope |
| V5 Input Validation | Yes — URL validation, count clamp, timeout clamp | `urllib.parse.urlparse` for URL; min/max clamp on numeric inputs |
| V6 Cryptography | No — BRAVE_SEARCH_API_KEY is env-only; no key derivation | env-only secret convention |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via `web_fetch` with internal URLs | Tampering / Info Disclosure | Network off by default (`allow_net=False`); gate-level denial before socket opens |
| API key leakage in telemetry | Info Disclosure | `redact_url` strips query string (where keys often appear); `redact_tool_args` masks `token`/`api_key` substrings |
| MCP server process injection via `command` field in mcp.yml | Tampering | `${VAR}` interpolation limited to env vars; `{cwd}` is `Path.cwd()` — no shell execution; command is `argv` list (not string, no shell expansion) |
| MCP subprocess environment leakage | Info Disclosure | Per-server `env` allowlist in D-04; when set, subprocess starts with empty env + only listed vars |
| BRAVE_SEARCH_API_KEY stored in config file | Info Disclosure | Env-only convention from `auth.py`; config loader does not read `BRAVE_SEARCH_API_KEY` from TOML — env-only |
| web_fetch 1 MB truncation bypass | DoS | Truncation at exactly byte 1,048,576 is enforced in tool body before returning; cap is hardcoded, not configurable |
| MCP tool denial via `is_mutating` misclassification | Elevation of Privilege | Default `destructiveHint` absent → `is_mutating=True` (safe fallback); safe-by-default, not permissive-by-default |

---

## Sources

### Primary (HIGH confidence — verified via live tool or official docs)

- [MCP Specification 2025-11-25 — Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) — stdio framing (newline-delimited JSON-RPC, UTF-8, one message per line)
- [MCP Specification 2025-11-25 — Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle) — initialize/initialized/operation sequence; shutdown SIGTERM pattern
- [MCP Specification 2025-11-25 — Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) — tools/list request + response shape; tools/call shape; ToolAnnotations fields
- [MCP ToolAnnotations destructiveHint](https://chatforest.com/guides/mcp-tool-annotations-explained/) — confirmed boolean optional fields: readOnlyHint, destructiveHint, idempotentHint, openWorldHint
- [Brave Search API — Get Started](https://api-dashboard.search.brave.com/app/documentation/web-search/get-started) — endpoint URL, X-Subscription-Token, query params
- [Brave Search API — Responses](https://api-dashboard.search.brave.com/app/documentation/web-search/responses) — web.results[].{title, url, description} shape
- [httpx 0.28.1 — AsyncClient constructor](https://www.python-httpx.org/api/) — introspected live via `inspect.signature`; all defaults verified
- [@modelcontextprotocol/server-filesystem npm](https://www.npmjs.com/package/@modelcontextprotocol/server-filesystem) — version 2026.1.14 verified via `npm view`
- [server-filesystem README](https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/README.md) — tool names and ToolAnnotations table

### Secondary (MEDIUM confidence — official sources, web-verified)

- [httpx AsyncClient API reference](https://www.python-httpx.org/api/) — parameter names confirmed
- [Token bucket algorithm pattern](https://oneuptime.com/blog/post/2026-01-22-token-bucket-rate-limiting-python/view) — standard algorithm; stdlib `time.monotonic` usage confirmed

### Tertiary (LOW confidence / ASSUMED — flagged inline)

- Raw asyncio subprocess JSON-RPC framing code patterns — derived from spec + stdlib; marked `[ASSUMED]` in Code Examples
- `redact_url` implementation — stdlib urllib.parse; logic is straightforward; marked `[ASSUMED]`
- TokenBucket implementation — standard algorithm; marked `[ASSUMED]`
- httpx MockTransport test pattern — marked `[ASSUMED]`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | asyncio.subprocess write/read pattern: `proc.stdin.write(line.encode()) + drain()`, `proc.stdout.readline()` | Code Examples | Wrong async API → code fails at runtime. Mitigate: confirmed pattern mirrors tools.py `_shell_capture` shape |
| A2 | `redact_url` using `urlparse._replace()` strips userinfo cleanly | Code Examples | Userinfo not stripped → API key in `user:pass@host` form leaks to telemetry. Mitigate: write explicit test assertion |
| A3 | TokenBucket using `time.monotonic` is deterministic-clock-mockable via monkeypatch | Code Examples | Tests are non-deterministic if `time.monotonic` cannot be patched module-locally. Mitigate: use `monkeypatch.setattr("voss.harness.rate_limit.time.monotonic", ...)` |
| A4 | `pyyaml` is already in project main dependencies | Environment | ImportError in mcp/config.py on install. Mitigate: Wave 0 check |
| A5 | server-filesystem 2026.1.14 tool names include `read_text_file` (not `read_file`) | Common Pitfalls | Test assertions fail; CI integration broken. Mitigate: Wave 0 runs actual `tools/list` |
| A6 | httpx `MockTransport.handle_async_request` is the correct intercept interface for call counting | Code Examples | Zero-socket test doesn't intercept calls. Mitigate: check httpx.MockTransport API at implementation time |

**All `[ASSUMED]` tags above represent implementation patterns rather than protocol facts. Protocol facts (MCP spec, Brave API, httpx defaults) are verified via official sources.**

---

## Metadata

**Confidence breakdown:**
- MCP protocol: HIGH — verified against official 2025-11-25 spec
- Brave API: HIGH — verified against official Brave dashboard docs + endpoint URL confirmed
- httpx.AsyncClient: HIGH — live introspection of installed 0.28.1
- server-filesystem version/tools: MEDIUM — version via npm registry; tool names via README (may differ in actual package dist)
- Token bucket algorithm: MEDIUM — standard algorithm; implementation is [ASSUMED]
- redact_url: MEDIUM — stdlib urllib.parse; implementation is [ASSUMED]

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (30 days; MCP spec is stable; Brave API endpoint is stable; npm package may update)
