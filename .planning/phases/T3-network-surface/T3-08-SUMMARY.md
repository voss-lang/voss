# T3-08 Summary

Date: 2026-05-17

## CLI Surface

`voss/harness/cli.py` now exposes the MCP debug CLI:

- `mcp_group`: `voss/harness/cli.py:1968`
- `mcp list`: `voss/harness/cli.py:1973`
- `mcp call`: `voss/harness/cli.py:2031`
- `_parse_arg_kvs`: `voss/harness/cli.py:1950`
- main registration: `voss/harness/cli.py:2170`

`voss mcp call` bypasses `PermissionGate` by design and calls `McpClient.call_tool` directly.

## Example Output

No config:

```text
$ voss mcp list --cwd /tmp/empty
<no MCP servers configured>
```

No config JSON:

```json
{"servers": []}
```

Pretty output with a mock server:

```text
mock:
  command: /path/to/python -u /tmp/mock_server.py
  tools: read_text_file, write_file
```

JSON output with a mock server:

```json
{
  "servers": [
    {
      "name": "mock",
      "command": ["/path/to/python", "-u", "/tmp/mock_server.py"],
      "tools": ["read_text_file", "write_file"]
    }
  ]
}
```

## Argument Parsing

`_parse_arg_kvs` accepts repeated `--arg key=value` entries and parses JSON values with raw-string fallback:

| Input | Parsed |
|---|---|
| `count=10` | `{"count": 10}` |
| `verbose=true` | `{"verbose": True}` |
| `path="./README.md"` | `{"path": "./README.md"}` |
| `path=./README.md` | `{"path": "./README.md"}` |
| `items=["a","b"]` | `{"items": ["a", "b"]}` |
| `null_val=null` | `{"null_val": None}` |

Invalid entries without `=` exit 1 with `expected key=value`.

## Verification

```text
$ uv run pytest tests/harness/test_cli_mcp.py -x -q
..........                                                               [100%]
```

```text
$ uv run pytest tests/harness/test_cli.py tests/harness/mcp/ tests/harness/test_cli_mcp.py -x -q
.....................................                                    [100%]
```

Additional checks:

- `uv run python -m py_compile voss/harness/cli.py tests/harness/test_cli_mcp.py` passed.
- Source assertions for `@click.group("mcp")`, `mcp list`, `mcp call`, `_parse_arg_kvs`, and `AGENT_COMMANDS` registration passed.
- `mcp_group --help` lists both `list` and `call`.

## Next Plan

T3-09 can use:

```text
voss mcp call filesystem read_text_file --arg path=./README.md
```

against the pinned npm reference filesystem server in CI. The real tool names should be confirmed there against `tools/list`.
