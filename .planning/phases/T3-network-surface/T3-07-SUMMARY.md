# T3-07 Summary

Date: 2026-05-17

## MCP Package Layout

`voss/harness/mcp/` now contains the T3-07 stdio MCP client package:

| File | Lines | Purpose |
|---|---:|---|
| `__init__.py` | 38 | Public re-exports for config, client, and registry APIs |
| `config.py` | 71 | `.voss/mcp.yml` schema, loader, `${VAR}` and `{cwd}` substitution |
| `client.py` | 263 | stdio JSON-RPC client, launch lifecycle, handshake, `tools/list`, `tools/call`, telemetry |
| `registry.py` | 87 | MCP tool descriptor adapter into namespaced `ToolEntry` records |

## Handshake

The client follows the RESEARCH Pattern 1 / MCP 2025-11-25 sequence:

1. Send `initialize` with protocol version `2025-11-25`.
2. Read the server initialize response and warn, not fail, on protocol mismatch.
3. Send `notifications/initialized`.
4. Send `tools/list` and cache the advertised tools for registration.

`McpClient.ensure_launched` registers a subprocess with `lifecycle.register_subprocess` only after the handshake and `tools/list` succeed.

## Tool Registration

`register_mcp_tools(config, permissions_mcp, mcp_client)` wraps cached MCP tools as:

- namespaced keys: `{server}__{tool}`
- `is_network=True`
- `is_mutating=False` under plan scope
- `is_mutating=annotations.destructiveHint` under edit/auto scope, with absent `destructiveHint` defaulting to `True`

The invoke closure enforces MCP scope directly: a destructive tool under plan scope returns:

```text
<error: denied by mcp scope: filesystem at plan, requires edit>
```

## make_toolset Decision

`make_toolset` remains synchronous. For MCP merge, it uses `asyncio.run` only when no event loop is already running, which matches the current click/REPL harness construction path. If called from inside a running event loop, it skips MCP merge and emits `mcp.boot_error` telemetry instead of attempting an illegal nested event loop.

This keeps the public `make_toolset` signature stable for T3-07. A future async bootstrap helper can replace this if a production call site needs MCP discovery from an async context.

## Verification

```text
$ uv run pytest tests/harness/mcp/ -x -q
.............                                                            [100%]
```

```text
$ uv run pytest tests/harness/ -k "mcp or lifecycle or web_fetch or web_search or allow_net or rate_limit or telemetry" -x -q
......................................................................   [100%]
```

```text
$ uv run pytest tests/harness/test_cognition_schemas.py tests/harness/test_cognition.py -x -q
...............s.........                                                [100%]
```

Additional checks:

- `grep -c "pytest.skip" tests/harness/mcp/test_mcp_config.py tests/harness/mcp/test_mcp_client.py tests/harness/mcp/test_mcp_scope.py` returned zero skips in each file.
- `uv run python -m py_compile` passed for MCP package files, `cognition_schemas.py`, `tools.py`, and MCP tests.
- `git diff --check` passed.
- Import smoke passed: `from voss.harness.mcp import register_mcp_tools, McpClient, McpConfig, McpServerConfig, load_mcp_config, McpConfigError`.

## Next Plans

T3-08 can reuse `McpClient.list_tools` and `McpClient.call_tool` directly for the `voss mcp` CLI surface. T3-09 should run `tools/list` against the pinned npm reference filesystem server to lock the real advertised tool names.
