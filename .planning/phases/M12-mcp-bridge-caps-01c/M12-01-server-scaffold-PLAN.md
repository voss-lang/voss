---
phase: M12-mcp-bridge-caps-01c
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/mcp/server.py
  - voss/harness/mcp/config.py
  - voss/harness/mcp/__init__.py
  - tests/harness/mcp/test_mcp_server_scaffold.py
autonomous: true
requirements: [MCP-01, MCP-02, MCP-06, MCP-07]

must_haves:
  truths:
    - "`voss/harness/mcp/server.py` exposes a `McpServer` class with an async `serve_stdio(stdin, stdout, *, mode)` entry that reads JSON-RPC lines, completes the 2025-11-25 handshake (`initialize` → `notifications/initialized`), responds to `tools/list` and `tools/call`, and exits cleanly on stdin EOF"
    - "`server.py` defines and uses ONLY the constant `_PROTOCOL_VERSION` already declared in `voss/harness/mcp/client.py:28` — the version string is not redeclared (one source of truth)"
    - "Every incoming `tools/call` emits exactly one `mcp.server.request` telemetry event BEFORE dispatch and one `mcp.server.response` event AFTER, with redacted args (reusing `telemetry.redact_tool_args`)"
    - "`McpServerExposureConfig` is added to `voss/harness/mcp/config.py` with fields `name: str | None`, `exposed_tools: list[str] | Literal[\"*\"] = \"*\"`, `exposed_skills: list[str] | Literal[\"*\"] = \"*\"`, `extra=\"forbid\"`"
    - "`McpConfig` gains an OPTIONAL `server: McpServerExposureConfig | None = None` field; the existing `servers:` (plural, outbound) loader is unchanged and all existing T3-07 mcp tests still pass"
    - "Stdin EOF returns from `serve_stdio` cleanly (no exception), and a `tools/call` whose tool name does not exist returns a JSON-RPC error `{code: -32601, message: \"tool not found: <name>\"}` instead of crashing"
  artifacts:
    - path: "voss/harness/mcp/server.py"
      provides: "stdio MCP 2025-11-25 server class + handshake + telemetry helpers"
      contains: "class McpServer"
      min_lines: 90
    - path: "voss/harness/mcp/config.py"
      provides: "extended schema: McpServerExposureConfig + McpConfig.server field"
      contains: "class McpServerExposureConfig"
    - path: "voss/harness/mcp/__init__.py"
      provides: "public re-exports of McpServer + McpServerExposureConfig"
      contains: "McpServerExposureConfig"
    - path: "tests/harness/mcp/test_mcp_server_scaffold.py"
      provides: "handshake roundtrip + tools/list shape + stdin-EOF clean exit + tool-not-found error envelope tests, all using in-memory async StringIO streams"
      contains: "async def test_handshake_roundtrip"
      min_lines: 80
  key_links:
    - from: "voss/harness/mcp/server.py"
      to: "voss/harness/mcp/client.py:28"
      via: "import _PROTOCOL_VERSION (one constant; do NOT redeclare)"
      pattern: "from voss\\.harness\\.mcp\\.client import _PROTOCOL_VERSION"
    - from: "voss/harness/mcp/server.py"
      to: "voss/harness/telemetry.py:190"
      via: "telemetry.emit(\"mcp.server.request\"/\"mcp.server.response\", ..., data=...)"
      pattern: "telemetry\\.emit\\(\\s*\"mcp\\.server\\."
    - from: "voss/harness/mcp/server.py"
      to: "voss/harness/telemetry.py:105"
      via: "telemetry.redact_tool_args(args) on every dispatched call (same redaction policy as client side)"
      pattern: "redact_tool_args\\("
    - from: "voss/harness/mcp/config.py"
      to: "voss/harness/mcp/config.py:27"
      via: "extend existing McpConfig; do NOT touch McpServerConfig (singular, outbound — T3 contract)"
      pattern: "class McpConfig\\(BaseModel\\):"
---

<objective>
Land the server-side scaffold for the MCP bridge: stdio JSON-RPC transport,
2025-11-25 handshake, `tools/list` placeholder, `tools/call` placeholder with
telemetry, error envelopes, plus the `.voss/mcp.yml` `server:` schema (and its
public re-exports). Pure transport + schema. No tool advertisement (M12-02
owns), no skill bridge (M12-03), no CLI command (M12-04). Lays the foundation
every later wave plugs into.

D-04 (telemetry-only audit) is established here: the events emit unconditionally
per `tools/call`. D-01 (stdio-only) is established here: there is no HTTP code
path even as a TODO. The protocol version is the single constant
`client.py:_PROTOCOL_VERSION = "2025-11-25"` — imported, never duplicated.
</objective>

<context>
@.planning/phases/M12-mcp-bridge-caps-01c/M12-CONTEXT.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-PLAN-OUTLINE.md

Read first:
- `voss/harness/mcp/client.py` (lines 28-end) — line-framed JSON-RPC writer,
  telemetry helpers, `_PROTOCOL_VERSION` constant, handshake structure to
  mirror in reverse.
- `voss/harness/mcp/config.py` (full file) — pydantic schema with
  `extra="forbid"`. Extend, don't rewrite.
- `voss/harness/mcp/__init__.py` (full file) — lazy `__getattr__` pattern for
  re-exports.
- `voss/harness/telemetry.py:105,133,190` — `redact_tool_args`, `redact_url`,
  `emit(event, level, *, data)` signatures.
- `tests/harness/mcp/test_mcp_config.py` and `test_mcp_client.py` — shape of
  existing tests; mirror their style for the new scaffold test.

Anthropic `mcp` Python SDK is importable (`python3 -c "import mcp"` succeeds)
but is NOT used here. The scaffold mirrors `client.py` line-framing for
symmetry and to keep the server inside the same telemetry envelope. If a later
plan finds a blocker, swap in the SDK then; today the cost is one ~120-line
module, the benefit is zero drift from the client side.
</context>

<threat_model>
Primary risk: the server reads from untrusted stdin (an external MCP host).
Concrete threats and mitigations in this plan:

| ID | Threat | Mitigation |
|---|---|---|
| T-M12-01-01 | Unbounded line read OOMs the process | Cap each JSON-RPC line at 1 MiB (`asyncio.StreamReader.readline(limit=...)` or manual check). Lines longer than the cap respond with error `-32700 parse error: line too long` and continue. |
| T-M12-01-02 | Malformed JSON crashes the server | Every `json.loads` is wrapped; failure → JSON-RPC error `-32700 parse error: <reason>`; serve loop continues. |
| T-M12-01-03 | Unknown method name crashes the dispatch | Method dispatch is a `match` / dict lookup with a default-arm returning JSON-RPC `-32601 method not found: <name>`. |
| T-M12-01-04 | Secrets leaked via telemetry args | Reuse `telemetry.redact_tool_args` verbatim — same redaction list as T3-07 client side. |
| T-M12-01-05 | Stdin EOF leaves the server hanging | Detect `b""` / EOF on readline and `return` from the serve loop cleanly. The acceptance test in this plan asserts this. |

Out-of-scope-here (covered by later plans): `tools/call` permission gate is
M12-02's responsibility (not yet wired). Skill execution and `CallToolResult`
content shape are M12-03. Subprocess CLI lifecycle is M12-04.

No new dependencies. No filesystem writes from the server. No network surface.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Extend `voss/harness/mcp/config.py` with `McpServerExposureConfig` + `McpConfig.server` field</name>
  <read_first>
    voss/harness/mcp/config.py (full file — extend, do not rewrite)
    .planning/phases/M12-mcp-bridge-caps-01c/M12-CONTEXT.md (D-03 `server:` block schema)
  </read_first>
  <action>
    Add `McpServerExposureConfig(BaseModel)` to `voss/harness/mcp/config.py`
    BELOW the existing `McpServerConfig` and ABOVE `McpConfig`:

    Fields:
    - `name: str | None = None` — advertised server name in `initialize`
      response. None means auto-default to `"voss"`.
    - `exposed_tools: list[str] | Literal["*"] = "*"` — either the literal
      string `"*"` (resolves to the curated 6-tool default in M12-02) or an
      explicit list of `make_toolset` keys.
    - `exposed_skills: list[str] | Literal["*"] = "*"` — same shape for the
      7-skill default surface.

    `model_config = STRICT` (the existing `extra="forbid"` dict). Use
    `typing.Literal` and import from `typing` at module top.

    Then modify `McpConfig`:
    - Add field `server: McpServerExposureConfig | None = None`.
    - Keep `servers: dict[str, McpServerConfig] = Field(default_factory=dict)`
      EXACTLY as is (T3 outbound contract).

    Do NOT touch `load_mcp_config` semantics or signatures. `load_mcp_config`
    returns `McpConfig | None`; the new `server` key in YAML must round-trip
    through the existing loader because pydantic `BaseModel.model_validate`
    handles it automatically.
  </action>
  <verify>
    <automated>python3 -c "from voss.harness.mcp.config import McpServerExposureConfig, McpConfig; c = McpConfig.model_validate({'server': {'name': 'voss'}}); assert c.server is not None and c.server.name == 'voss' and c.server.exposed_tools == '*' and c.server.exposed_skills == '*'; c2 = McpConfig.model_validate({}); assert c2.server is None; c3 = McpConfig.model_validate({'server': {'exposed_tools': ['fs_read','fs_glob']}}); assert c3.server.exposed_tools == ['fs_read','fs_glob']; print('config ok')"</automated>
    <automated>python3 -c "from voss.harness.mcp.config import McpConfig; from pydantic import ValidationError; ok=False; ok = (lambda: __import__('pydantic').ValidationError)()
import pydantic
try:
    McpConfig.model_validate({'server': {'unknown': 'x'}})
    raise AssertionError('extra=forbid was lost')
except pydantic.ValidationError:
    print('extra=forbid ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/mcp/config.py` contains `class McpServerExposureConfig(BaseModel):`
    - `McpConfig` has the new field `server: McpServerExposureConfig | None = None`
    - Existing `McpServerConfig` (singular, outbound) is byte-unchanged
    - Validating a YAML with an unknown key under `server:` raises `pydantic.ValidationError` (`extra="forbid"` preserved)
    - All existing tests in `tests/harness/mcp/test_mcp_config.py` still pass: `python3 -m pytest -q tests/harness/mcp/test_mcp_config.py` exits 0
  </acceptance_criteria>
  <done>Schema extended; pydantic round-trips the new `server:` block; existing outbound tests untouched.</done>
</task>

<task type="auto">
  <name>Task 2: Add `voss/harness/mcp/server.py` with stdio handshake + dispatcher + telemetry</name>
  <read_first>
    voss/harness/mcp/client.py (full file — mirror the framing, telemetry shape, protocol-version reuse)
    voss/harness/telemetry.py (lines 105-200 — `redact_tool_args`, `emit` signature)
    voss/harness/mcp/server.py (file being created — confirm it does not exist)
  </read_first>
  <action>
    Create `voss/harness/mcp/server.py`.

    Imports:
    - `from __future__ import annotations`
    - `import asyncio`, `import json`, `import sys`, `import time`
    - `from typing import Any, Awaitable, Callable, Mapping`
    - `from voss.harness import telemetry`
    - `from voss.harness.mcp.client import _PROTOCOL_VERSION` (SINGLE source
      of truth; do NOT redeclare)

    Module-level helpers (mirror client.py:29-34):
    - `def _emit_mcp_server_request(data: dict[str, Any]) -> None:` →
      `telemetry.emit("mcp.server.request", "info", data=data)`
    - `def _emit_mcp_server_response(level: str, data: dict[str, Any]) -> None:` →
      `telemetry.emit("mcp.server.response", level, data=data)`

    `LINE_LIMIT_BYTES = 1_048_576` module constant (1 MiB; T-M12-01-01).

    Define `class McpServer`:

    ```
    class McpServer:
        def __init__(
            self,
            *,
            name: str,
            tool_descriptors: list[Mapping[str, Any]],
            dispatch: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
        ) -> None:
    ```

    - `name`: advertised server name (the `serverInfo.name` in `initialize`
      response).
    - `tool_descriptors`: list of MCP tool spec dicts as advertised by
      `tools/list`. M12-02 builds this; the scaffold accepts an empty list.
    - `dispatch`: async callable that takes `(tool_name, args)` and returns the
      MCP `tools/call` result body (`{"content": [...], "isError": bool}`).
      Raising an exception inside `dispatch` is caught and converted to a
      JSON-RPC error response (T-M12-01-03). M12-02 supplies the real
      dispatcher; the scaffold's test passes a minimal stub.

    Public async method `async def serve_stdio(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:`. The serve loop:

    1. Read one line via `reader.readline()`. If the result is `b""` → EOF → `return` (T-M12-01-05).
    2. Reject if the line exceeds `LINE_LIMIT_BYTES` (T-M12-01-01) → write a parse-error response with `id=null`.
    3. `try: msg = json.loads(line)` else → write `-32700 parse error: <reason>` response (T-M12-01-02).
    4. Dispatch by `msg["method"]`:
       - `"initialize"` → reply with `{"jsonrpc":"2.0","id":<id>,"result":{"protocolVersion":_PROTOCOL_VERSION,"capabilities":{"tools":{}},"serverInfo":{"name":self._name,"version":"0.1.0"}}}`.
       - `"notifications/initialized"` → notifications carry no `id` and need no response; do nothing.
       - `"tools/list"` → reply with `{"jsonrpc":"2.0","id":<id>,"result":{"tools":self._tool_descriptors}}`.
       - `"tools/call"` → extract `name` and `arguments` from `msg["params"]`. Emit `mcp.server.request` event with `{"name": name, "args": telemetry.redact_tool_args(dict(args)), "mode": <pulled from a future M12-04 ctx — pass `None` here>}`. Record `start = time.monotonic()`. Try `result = await self._dispatch(name, args)`. On exception OR `result.get("isError")`, emit `mcp.server.response` at level `"warning"` with `{"name": name, "elapsed_ms": int((time.monotonic()-start)*1000), "ok": False, "error": <error text>}`; reply with JSON-RPC error envelope or the tool-error result per MCP spec (use a tool-error `CallToolResult` with `isError=true`). On success, emit `mcp.server.response` at level `"info"` with `{"name": name, "elapsed_ms": ..., "ok": True, "content_len": len(result.get("content", []))}`. Reply with `{"jsonrpc":"2.0","id":<id>,"result":result}`.
       - default → reply `{"jsonrpc":"2.0","id":<id>,"error":{"code":-32601,"message":f"method not found: {method}"}}` (T-M12-01-03).
    5. After every response, `writer.write(<line>+b"\n")` and `await writer.drain()`.
    6. Loop back to step 1 until EOF.

    Helper `def _json_rpc_error(*, id: Any, code: int, message: str) -> bytes:` returns the encoded line.

    DO NOT call any tool or skill in this plan — `dispatch` is a callable
    INJECTED by M12-02. The scaffold ONLY routes JSON-RPC ↔ `dispatch`. The
    scaffold knows nothing about `PermissionGate`, `make_toolset`, or
    `SkillEntry`.
  </action>
  <verify>
    <automated>python3 -c "import ast; ast.parse(open('voss/harness/mcp/server.py').read()); print('ast ok')"</automated>
    <automated>python3 -c "from voss.harness.mcp.server import McpServer, _PROTOCOL_VERSION, _emit_mcp_server_request, _emit_mcp_server_response, LINE_LIMIT_BYTES; assert _PROTOCOL_VERSION == '2025-11-25'; assert LINE_LIMIT_BYTES == 1_048_576; print('ok')"</automated>
    <automated>python3 -c "import re; s=open('voss/harness/mcp/server.py').read(); body='\n'.join(l for l in s.splitlines() if not l.lstrip().startswith('#') and not l.strip().startswith('\"\"\"')); assert '_PROTOCOL_VERSION = ' not in body, 'protocol version redeclared — must import from client.py'; assert 'fs_write' not in body and 'fs_edit' not in body and 'PermissionGate' not in body, 'scaffold must not couple to tool surface or gate (M12-02/04 own those)'; print('decoupled ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/mcp/server.py` parses
    - Module imports `_PROTOCOL_VERSION` from `voss.harness.mcp.client` and does not redeclare it
    - `class McpServer` has `__init__(self, *, name, tool_descriptors, dispatch)` and `async def serve_stdio(self, reader, writer)`
    - `_emit_mcp_server_request` and `_emit_mcp_server_response` both call `telemetry.emit` with event names `mcp.server.request` and `mcp.server.response` respectively
    - `redact_tool_args` is invoked on `tools/call` args before emitting the request event
    - Module contains no reference to `PermissionGate`, `make_toolset`, `SkillEntry`, `fs_write`, `fs_edit` (those are M12-02/03 surfaces)
  </acceptance_criteria>
  <done>Scaffold parses, decoupled from later-wave surfaces, telemetry events named correctly, protocol version is the single shared constant.</done>
</task>

<task type="auto">
  <name>Task 3: Re-export `McpServer` + `McpServerExposureConfig` from `voss/harness/mcp/__init__.py`</name>
  <read_first>
    voss/harness/mcp/__init__.py (full file — follow the existing lazy `__getattr__` pattern)
  </read_first>
  <action>
    Edit `voss/harness/mcp/__init__.py`:

    1. Add `McpServerExposureConfig` to the eager imports near the top
       (it lives in the already-imported `voss.harness.mcp.config` module, so
       it goes in the same import block as `McpServerConfig`, `McpConfig`,
       etc.).
    2. Add `"McpServerExposureConfig"` and `"McpServer"` to `__all__`.
    3. Extend the lazy `__getattr__` to lazy-load `McpServer`:
       ```python
       if name == "McpServer":
           from voss.harness.mcp.server import McpServer
           return McpServer
       ```
       Keep the existing `McpClient` and `register_mcp_tools` lazy entries
       byte-identical.

    Do NOT eagerly import `voss.harness.mcp.server` — keeping it lazy avoids
    pulling the server module into every harness boot.
  </action>
  <verify>
    <automated>python3 -c "from voss.harness.mcp import McpServer, McpServerExposureConfig, McpClient, McpConfig; print('all four ok')"</automated>
    <automated>python3 -c "import voss.harness.mcp as m; assert 'McpServer' in m.__all__ and 'McpServerExposureConfig' in m.__all__; print('__all__ ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `from voss.harness.mcp import McpServer` succeeds
    - `from voss.harness.mcp import McpServerExposureConfig` succeeds
    - `"McpServer"` and `"McpServerExposureConfig"` both present in `voss.harness.mcp.__all__`
    - Pre-existing re-exports (`McpClient`, `register_mcp_tools`, `McpServerConfig`, `McpConfig`, `load_mcp_config`, `substitute_server`, `McpConfigError`) still importable
  </acceptance_criteria>
  <done>Public surface extended additively; client-side imports untouched.</done>
</task>

<task type="auto">
  <name>Task 4: Add `tests/harness/mcp/test_mcp_server_scaffold.py` with in-memory handshake + dispatch tests</name>
  <read_first>
    voss/harness/mcp/server.py (Task 2 output — the surface under test)
    tests/harness/mcp/test_mcp_client.py (existing test style + in-memory stream pattern)
    voss/harness/telemetry.py (lines 55-200 — for capturing events via the recorder helper used in T3 tests)
  </read_first>
  <action>
    Create `tests/harness/mcp/test_mcp_server_scaffold.py`. Use `pytest`,
    `pytest.mark.asyncio` (or the existing `asyncio_mode = "auto"` from
    `pyproject.toml [tool.pytest.ini_options]`). Build an in-memory pair of
    `asyncio.StreamReader` + a buffer-backed `StreamWriter` (or use
    `asyncio.StreamReader.feed_data` + a mock writer that captures
    `.write`/`.drain`).

    Tests (each ~10-25 lines):

    1. `async def test_handshake_roundtrip()` — feed an `initialize` line with
       protocolVersion=`"2025-11-25"`, capabilities=`{}`, clientInfo=
       `{"name":"t","version":"0"}`. Then EOF. Assert the writer received
       exactly one JSON-RPC response with `result.protocolVersion ==
       "2025-11-25"` and `result.serverInfo.name == "voss-test"` (server is
       constructed with `name="voss-test"`).

    2. `async def test_tools_list_returns_descriptors()` — construct the
       server with `tool_descriptors=[{"name":"fs_read","description":"x",
       "inputSchema":{"type":"object","properties":{}}}]`. Feed `initialize`
       then `tools/list` then EOF. Assert the second response is
       `result={"tools":[<that descriptor>]}`.

    3. `async def test_tools_call_dispatches_and_emits_telemetry(monkeypatch)`
       — stub `voss.harness.telemetry.emit` (via monkeypatch) to append
       `(event, level, data)` tuples to a list. Stub `dispatch` as an async
       function that returns `{"content":[{"type":"text","text":"ok"}],
       "isError":False}`. Feed `initialize` then a `tools/call` for tool
       name `"x"` with args `{"a":1}` then EOF. Assert the emitted events
       include exactly one `mcp.server.request` (level `"info"`) and one
       `mcp.server.response` (level `"info"`, `ok=True`). Assert the
       response on the wire is the dispatch result wrapped in JSON-RPC.

    4. `async def test_tool_not_found_returns_method_error()` — construct the
       server with `dispatch` raising AssertionError if called. Feed
       `initialize` then `tools/call` for unknown method routing — actually
       this is `"unknown/method"` to hit the method-not-found branch
       (T-M12-01-03). Assert response is `{error:{code:-32601, message:
       contains "method not found"}}`.

    5. `async def test_parse_error_does_not_kill_loop()` — feed
       `initialize` (ok) then a literal non-JSON line `b"not-json\n"` then
       a well-formed `tools/list` then EOF. Assert: response 1 is the
       initialize result; response 2 is a parse error (`code=-32700`);
       response 3 is the tools/list result. The serve loop survived.

    6. `async def test_eof_returns_cleanly()` — feed nothing and close the
       reader. Assert `serve_stdio` returns within 0.5s without raising
       (T-M12-01-05).

    Mark async tests with `@pytest.mark.asyncio` if `asyncio_mode = "auto"` is
    not enough; mirror whatever the existing `test_mcp_client.py` uses.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/mcp/test_mcp_server_scaffold.py</automated>
    <automated>python3 -m pytest -q tests/harness/mcp/  # full mcp suite still passes (T3-07 regression guard)</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/mcp/test_mcp_server_scaffold.py` contains all 6 named async tests
    - All 6 tests pass: `python3 -m pytest -q tests/harness/mcp/test_mcp_server_scaffold.py` exits 0
    - The full pre-existing `tests/harness/mcp/` suite still passes: `python3 -m pytest -q tests/harness/mcp/` exits 0
    - The handshake-roundtrip test asserts `protocolVersion == "2025-11-25"` literally
    - The telemetry-emit test captures exactly one `mcp.server.request` AND exactly one `mcp.server.response` per `tools/call`
  </acceptance_criteria>
  <done>Six in-memory stdio tests prove the scaffold: handshake, tools/list, dispatch+telemetry, method-not-found, parse-error survival, EOF clean exit. T3-07 mcp tests still green.</done>
</task>

</tasks>

<verification>
Plan-level checks (run after all 4 tasks):

```bash
cd /Users/benjaminmarks/Projects/Voss

# 1. Schema + module surface
python3 -c "from voss.harness.mcp import McpServer, McpServerExposureConfig, McpConfig; c = McpConfig.model_validate({'server': {'exposed_tools': ['fs_read']}}); assert c.server.exposed_tools == ['fs_read']"

# 2. Protocol version is single source of truth (server.py does NOT redeclare it)
! grep -E "^_PROTOCOL_VERSION\s*=" voss/harness/mcp/server.py

# 3. Server module is decoupled from tool surface (M12-02/04 own those)
! grep -E "PermissionGate|make_toolset|SkillEntry|fs_write|fs_edit|skill_registry" voss/harness/mcp/server.py

# 4. Telemetry event names exact
grep -q 'mcp\.server\.request' voss/harness/mcp/server.py
grep -q 'mcp\.server\.response' voss/harness/mcp/server.py

# 5. The four owned tests + the full mcp suite are green
python3 -m pytest -q tests/harness/mcp/test_mcp_server_scaffold.py
python3 -m pytest -q tests/harness/mcp/

# 6. No whitespace damage
git diff --check
```
</verification>

<success_criteria>
- `voss/harness/mcp/server.py` exists, parses, exposes `McpServer` with `async def serve_stdio(self, reader, writer)`.
- Server module imports `_PROTOCOL_VERSION` from `client.py` (single constant) and contains no `PermissionGate`/`make_toolset`/`SkillEntry`/`fs_write`/`fs_edit` references.
- `McpServerExposureConfig` added to `voss/harness/mcp/config.py`; `McpConfig.server: McpServerExposureConfig | None = None`; `extra="forbid"` preserved everywhere.
- `voss/harness/mcp/__init__.py` re-exports `McpServer` (lazy) and `McpServerExposureConfig` (eager); existing T3 re-exports unchanged.
- `tests/harness/mcp/test_mcp_server_scaffold.py` 6/6 green; existing T3 mcp suite still green.
- Each `tools/call` emits exactly one `mcp.server.request` + one `mcp.server.response` telemetry event with redacted args.
- `git diff --check` clean.
</success_criteria>

<output>
Create `.planning/phases/M12-mcp-bridge-caps-01c/M12-01-SUMMARY.md` when done.
</output>
