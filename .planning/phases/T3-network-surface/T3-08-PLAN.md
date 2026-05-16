---
phase: T3-network-surface
plan: 08
type: execute
wave: 4
depends_on: [T3-07]
files_modified:
  - voss/harness/cli.py
  - tests/harness/test_cli_mcp.py
autonomous: true
requirements: [NET-03]
must_haves:
  truths:
    - "voss/harness/cli.py adds a click.group('mcp') with two subcommands: voss mcp list and voss mcp call"
    - "voss mcp list with no .voss/mcp.yml prints '<no MCP servers configured>' and exits 0"
    - "voss mcp list with a populated .voss/mcp.yml prints each server's name, command, and advertised tool names"
    - "voss mcp list --json emits a JSON object with shape {servers: [{name, command, tools}]}"
    - "voss mcp call <server> <tool> [--arg key=value]... invokes McpClient.call_tool directly, bypassing PermissionGate (per D-13 — developer tool)"
    - "voss mcp call --arg parses JSON-looking values (true, false, 42, [\"a\",\"b\"], null) as JSON; non-JSON-parseable values fall back to raw string per D-14"
    - "voss mcp call exits 0 on success, 1 on protocol/transport error, 2 on server-side tool error"
    - "Registered in the main click group alongside other voss subcommands (do, chat, edit, etc.)"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "mcp_group click group + mcp_list_cmd + mcp_call_cmd; registered via the main group's add_command"
      contains: "@click.group(\"mcp\")"
    - path: "tests/harness/test_cli_mcp.py"
      provides: "click CliRunner tests covering: no-yml exit 0, populated-yml pretty output, --json shape, --arg JSON parsing, --arg string fallback, exit codes"
      contains: "def test_mcp_list_no_config"
  key_links:
    - from: "voss/harness/cli.py:mcp_list_cmd"
      to: "voss/harness/mcp.load_mcp_config + McpClient.list_tools"
      via: "load_mcp_config(cwd) → if None: print sentinel and exit 0; else iterate servers, ensure_launched each, list_tools, format"
      pattern: "load_mcp_config|list_tools"
    - from: "voss/harness/cli.py:mcp_call_cmd"
      to: "voss/harness/mcp.McpClient.call_tool"
      via: "build args dict from --arg pairs (JSON-parse with string fallback) → call_tool(server, tool, args) → print result.content[0].text → exit per result.isError"
      pattern: "call_tool"
---

<objective>
Add the `voss mcp {list,call}` CLI surface (D-13). Thin click group consuming the McpClient surface T3-07 ships. `voss mcp call` bypasses PermissionGate because it's an explicit developer/debug tool — invocation is bare and direct, mirroring the existing `voss check` pattern. `--arg key=value` parses values as JSON when they look JSON-shaped (true/false/numbers/arrays/null) with string fallback per D-14.

Purpose: Surface the MCP subsystem T3-07 ships to the user. Two acceptance bullets from T3-SPEC fall here:
- "`voss mcp list` with no `.voss/mcp.yml` exits 0 with `<no MCP servers configured>`"
- "`voss mcp list` with a populated `.voss/mcp.yml` prints each server's name + advertised tool names"

These were placed as separate plan items because the CLI surface touches only cli.py and has zero overlap with T3-07's mcp/ package — they can ship in parallel after Wave 2 completes (Wave 4 alongside T3-06 which touches different files).

Output: ~120 lines of click-decorated functions in cli.py; ~100 lines of CliRunner tests in tests/harness/test_cli_mcp.py.
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
@.planning/phases/T3-network-surface/T3-07-PLAN.md
@voss/harness/cli.py
@voss/harness/mcp/__init__.py
@voss/harness/mcp/client.py
</context>

<interfaces>
T3-PATTERNS section "voss/harness/cli.py (extend — `mcp` group + `--allow-net` flag)" locks the click group pattern (lines 487-510 of T3-PATTERNS). Mirror EXACTLY:

```
@click.group("mcp")
def mcp_group() -> None:
    """Inspect and debug MCP server connections."""


@mcp_group.command("list")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="Emit machine-readable JSON.")
def mcp_list_cmd(cwd_str: str, json_mode: bool) -> None:
    """List configured MCP servers and their advertised tools."""
    from pathlib import Path
    import json as json_lib
    from voss.harness.mcp import load_mcp_config, McpClient, McpConfigError
    cwd = Path(cwd_str).resolve()
    try:
        config = load_mcp_config(cwd)
    except McpConfigError as e:
        click.echo(f"<error: mcp config: {e}>", err=True)
        raise click.exceptions.Exit(1)
    if config is None or not config.servers:
        if json_mode:
            click.echo(json_lib.dumps({"servers": []}))
        else:
            click.echo("<no MCP servers configured>")
        return  # exit 0
    client = McpClient(config); client.set_cwd(cwd)
    import asyncio
    async def _populate():
        for name in config.servers:
            try:
                await client.ensure_launched(name)
            except Exception as ex:
                click.echo(f"<warning: {name} launch failed: {ex}>", err=True)
    asyncio.run(_populate())
    servers_payload = []
    for name, server in config.servers.items():
        tools = client._tools_cache.get(name, [])
        servers_payload.append({
            "name": name,
            "command": server.command + server.args,
            "tools": [t["name"] for t in tools],
        })
    if json_mode:
        click.echo(json_lib.dumps({"servers": servers_payload}, indent=2))
    else:
        for s in servers_payload:
            click.echo(f"{s['name']}:")
            click.echo(f"  command: {' '.join(s['command'])}")
            click.echo(f"  tools: {', '.join(s['tools']) if s['tools'] else '<none discovered>'}")
            click.echo("")
    # Note: do NOT explicitly reap subprocesses here — lifecycle.atexit handles it.


@mcp_group.command("call")
@click.argument("server")
@click.argument("tool_name")
@click.option("--arg", "args_kvs", multiple=True, help="key=value argument (repeatable). Values parsed as JSON when JSON-shaped; raw string fallback.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def mcp_call_cmd(server: str, tool_name: str, args_kvs: tuple[str, ...], cwd_str: str) -> None:
    """Call an MCP tool directly. Bypasses PermissionGate (developer tool)."""
    from pathlib import Path
    import json as json_lib
    from voss.harness.mcp import load_mcp_config, McpClient, McpConfigError
    cwd = Path(cwd_str).resolve()
    try:
        config = load_mcp_config(cwd)
    except McpConfigError as e:
        click.echo(f"<error: mcp config: {e}>", err=True)
        raise click.exceptions.Exit(1)
    if config is None or server not in (config.servers if config else {}):
        click.echo(f"<error: unknown server: {server!r}>", err=True)
        raise click.exceptions.Exit(1)
    # Parse --arg pairs
    args_dict: dict = {}
    for kv in args_kvs:
        if "=" not in kv:
            click.echo(f"<error: invalid --arg {kv!r}: expected key=value>", err=True)
            raise click.exceptions.Exit(1)
        key, raw_val = kv.split("=", 1)
        try:
            args_dict[key] = json_lib.loads(raw_val)  # try JSON parse
        except (json_lib.JSONDecodeError, ValueError):
            args_dict[key] = raw_val  # fallback to raw string
    client = McpClient(config); client.set_cwd(cwd)
    import asyncio
    async def _invoke():
        try:
            return await client.call_tool(server, tool_name, args_dict)
        except Exception as ex:
            return {"isError": True, "content": [{"type": "text", "text": f"<error: mcp transport: {ex}>"}], "__transport_error": True}
    result = asyncio.run(_invoke())
    if result.get("__transport_error"):
        click.echo(result["content"][0]["text"], err=True)
        raise click.exceptions.Exit(1)
    content = result.get("content", [])
    if content:
        for c in content:
            if c.get("type") == "text":
                click.echo(c.get("text", ""))
    if result.get("isError"):
        raise click.exceptions.Exit(2)
    # exit 0 implicit
```

Registration: at the bottom of cli.py, the existing click group adds commands. Locate the spot (`grep -n "do_cmd," voss/harness/cli.py` — line 1861 from grep earlier). Add `mcp_group,` to the add_command list. If the structure is `main.add_command(do_cmd)` then add `main.add_command(mcp_group)`.

D-14 JSON-parse-with-fallback details:
- `--arg path=./README.md` → not JSON-shaped (no quotes around the string) → falls back to string `"./README.md"`. Note: `json.loads("./README.md")` raises JSONDecodeError, so the fallback fires correctly.
- `--arg count=10` → json.loads("10") → 10 (int).
- `--arg verbose=true` → json.loads("true") → True (bool).
- `--arg names=["a","b"]` → json.loads('["a","b"]') → list. WARNING: shell quoting — actual command line will need quotes around the JSON. `voss mcp call x y --arg 'names=["a","b"]'` works.
- `--arg note=hello world` — argparse-style splitting won't work; click treats each --arg as one token. `voss mcp call x y --arg "note=hello world"` works as expected (quoted single token).

CliRunner pattern (from click.testing). Tests don't need a real MCP server for list when no .voss/mcp.yml exists. For populated cases, use the same MOCK_SERVER_SRC pattern from T3-07 Task 2.

For `voss mcp call` tests, the simplest path is: use the same mock server, exercise the full path (CLI → load_mcp_config → McpClient → mock subprocess → result print). This is integration-style but the mock server is in-tree Python.
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add voss mcp {list,call} click group to cli.py + register in main + smoke import test</name>
  <files>voss/harness/cli.py, tests/harness/test_cli_mcp.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-03 — Boundaries section names the two subcommands; Acceptance Criteria checklist items for voss mcp list)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-13 — CLI surface shape; D-14 — --arg JSON parsing)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (section "voss/harness/cli.py (extend)" — exact click group decorator pattern)
    - voss/harness/cli.py (locate the @click.command list near the bottom — `grep -n "@click.command\|do_cmd,\|@click.group" voss/harness/cli.py | tail -30`; the add_command registration site at line 1861)
    - voss/harness/mcp/__init__.py (T3-07 — re-exports)
    - voss/harness/mcp/client.py (T3-07 — McpClient.call_tool signature)
    - tests/harness/test_cli.py if it exists (for CliRunner pattern — `grep -n "CliRunner\|from click.testing" tests/harness/test_cli.py | head -10`)
  </read_first>
  <action>
    Edit voss/harness/cli.py:
    - Locate the imports section at top. Verify `import click` is present (it is — confirmed via cli.py line 21 grep showing the import).
    - Locate the existing `@click.command("X")` definitions near the bottom (last is around line 1774 `@click.command("eval")`). Add the mcp_group + mcp_list_cmd + mcp_call_cmd block per the interfaces section AFTER the eval_cmd definition but BEFORE the bottom group registration.
    - Locate the bottom group registration. The structure should be something like `main = click.Group(); main.add_command(do_cmd); ...` — `grep -nE "main\.add_command|main = click" voss/harness/cli.py`. Add `main.add_command(mcp_group)` in the same block. Alternative: if the main group is defined via `@click.group` decorator with explicit `commands={}`, find the dict and add `"mcp": mcp_group`.
    - The mcp_list_cmd and mcp_call_cmd bodies are exactly per the interfaces section. Pay special attention to:
      - Exception handling: McpConfigError → exit 1 with stderr; unknown server → exit 1; success → exit 0; server-side isError → exit 2.
      - asyncio.run is the synchronous-boundary pattern; if pytest collection triggers any event-loop conflict, the test fixture must reset state.
      - --json mode in mcp_list_cmd emits `{"servers": [...]}` even when servers is empty (empty list).
      - Pretty mode emits per-server block + blank line between blocks.

    Create tests/harness/test_cli_mcp.py:

    Imports: `import json as json_lib, subprocess, sys, textwrap, pytest; from pathlib import Path; from click.testing import CliRunner; from voss.harness.cli import mcp_group, mcp_list_cmd, mcp_call_cmd`. (mcp_group, mcp_list_cmd, mcp_call_cmd must be importable from cli.py — module-level names.)

    Helper for tests that need a real mock MCP server subprocess (lift from T3-07 Task 2):
    ```
    MOCK_SERVER_SRC = textwrap.dedent('''...''')  # same as T3-07

    def write_mcp_yml(cwd: Path, server_script: Path) -> None:
        (cwd / ".voss").mkdir(exist_ok=True)
        (cwd / ".voss" / "mcp.yml").write_text(textwrap.dedent(f"""
            servers:
              mock:
                command: [{sys.executable!r}, {str(server_script)!r}]
                timeout_s: 30.0
        """))
    ```

    Tests:

    - `def test_mcp_list_no_config(tmp_path)`: CliRunner. invoke `mcp_list_cmd` with `--cwd <tmp_path>` (no .voss/mcp.yml present). Assert result.exit_code == 0 and `"<no MCP servers configured>" in result.output`.

    - `def test_mcp_list_no_config_json(tmp_path)`: invoke `mcp_list_cmd --json --cwd <tmp_path>`. Assert exit_code == 0; parse stdout as JSON; assert == `{"servers": []}`.

    - `def test_mcp_list_with_servers(tmp_path)`: write MOCK_SERVER_SRC + mcp.yml. invoke `mcp_list_cmd --cwd <tmp_path>`. Assert exit_code == 0. Assert "mock:" appears in output (server name); assert "read_text_file" appears in output (tool name from mock); assert "write_file" appears.

    - `def test_mcp_list_json_shape(tmp_path)`: same setup. invoke `mcp_list_cmd --json --cwd <tmp_path>`. Parse stdout as JSON. Assert structure: `data["servers"]` is a list of length 1; `data["servers"][0]["name"] == "mock"`; `data["servers"][0]["tools"]` contains "read_text_file" and "write_file"; `data["servers"][0]["command"]` is a list of strings.

    - `def test_mcp_call_success(tmp_path)`: same setup. invoke `mcp_call_cmd ["mock", "read_text_file", "--arg", "path=./README.md", "--cwd", str(tmp_path)]`. Assert exit_code == 0; assert "mock-result" in result.output (the mock returns this content text).

    - `def test_mcp_call_unknown_server(tmp_path)`: same setup. invoke with server="nonexistent". Assert exit_code == 1; assert "<error: unknown server" in result.output (or stderr).

    - `def test_arg_json_parsing()`: this is a parser-only unit test — doesn't need MCP. Build the parse logic standalone (or reach into mcp_call_cmd's parse path). SIMPLER: write the parse logic into a small module-level helper `_parse_arg_kvs(args_kvs: tuple[str, ...]) -> dict` and test it directly:
      - `_parse_arg_kvs(("count=10",)) == {"count": 10}` (int)
      - `_parse_arg_kvs(("verbose=true",)) == {"verbose": True}` (bool)
      - `_parse_arg_kvs(('path="./README.md"',)) == {"path": "./README.md"}` (quoted string → JSON string)
      - `_parse_arg_kvs(("path=./README.md",)) == {"path": "./README.md"}` (bare string fallback)
      - `_parse_arg_kvs(('items=["a","b"]',)) == {"items": ["a", "b"]}` (list)
      - `_parse_arg_kvs(("null_val=null",)) == {"null_val": None}` (null)
      EXTRACT the parse loop into a helper `_parse_arg_kvs` defined at module scope in cli.py (so it's importable + testable). Update mcp_call_cmd to call it.

    - `def test_mcp_call_invalid_arg_format(tmp_path)`: invoke `mcp_call_cmd ["mock", "x", "--arg", "no_equals_sign"]`. Assert exit_code == 1; assert "expected key=value" in output.

    PYTEST-ASYNC NOTE: these tests use CliRunner which is sync. mcp_list_cmd and mcp_call_cmd contain `asyncio.run(...)` internally. CliRunner.invoke captures stdout/stderr cleanly. No pytest-asyncio decorator needed.

    Test cleanup: each test should call `lifecycle.reset_for_tests()` in a fixture so MCP subprocess state doesn't leak across tests. Use `@pytest.fixture(autouse=True)` at top.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_cli_mcp.py -x -q 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "^@click\.group\(.mcp.\)|^def mcp_group" voss/harness/cli.py | wc -l` returns >= 2
    - source assertion: `grep -nE "@mcp_group\.command\(.list.\)|@mcp_group\.command\(.call.\)" voss/harness/cli.py | wc -l` returns 2
    - source assertion: `grep -nE "<no MCP servers configured>" voss/harness/cli.py` returns 1 match (exact sentinel string)
    - source assertion: `grep -nE "def _parse_arg_kvs" voss/harness/cli.py` returns 1 match (helper extracted for testability)
    - registration: `grep -nE "add_command\(mcp_group\)|\"mcp\":\s*mcp_group" voss/harness/cli.py` returns 1 match
    - import smoke: `python -c "from voss.harness.cli import mcp_group, mcp_list_cmd, mcp_call_cmd, _parse_arg_kvs; print('OK')"` prints OK
    - help smoke: `python -c "from click.testing import CliRunner; from voss.harness.cli import mcp_group; r = CliRunner().invoke(mcp_group, ['--help']); print('list' in r.output and 'call' in r.output)"` prints `True`
    - behavior: all 8 tests pass (test_mcp_list_no_config, test_mcp_list_no_config_json, test_mcp_list_with_servers, test_mcp_list_json_shape, test_mcp_call_success, test_mcp_call_unknown_server, test_arg_json_parsing, test_mcp_call_invalid_arg_format)
    - regression: `uv run pytest tests/harness/test_cli.py tests/harness/mcp/ tests/harness/test_cli_mcp.py -x -q` exits 0
  </acceptance_criteria>
  <done>voss/harness/cli.py exports mcp_group (click.group), mcp_list_cmd, mcp_call_cmd, _parse_arg_kvs; both subcommands registered with main click group; voss mcp list with no config emits sentinel and exits 0; --json mode emits well-formed JSON; voss mcp call parses --arg with JSON+string fallback per D-14; exits 0/1/2 per result class; 8 CliRunner tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI invocation → MCP subprocess (no PermissionGate) | `voss mcp call` is a developer/debug surface per D-13. It explicitly bypasses PermissionGate. Trust model: the user invoking from CLI has full local authority; this is not an agent-driven path. |
| --arg JSON parsing | User-provided strings may be malformed JSON; json.loads errors must not crash. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T3-08-01 | Elevation | voss mcp call bypasses PermissionGate, executes destructive MCP tool | accept | D-13 explicit decision — this is a developer-tool surface, equivalent to running `npx @mcp/server` directly. User authored the mcp.yml. No agent-loop path uses this. Documented in the command --help string. |
| T-T3-08-02 | DoS | --arg with invalid format (no `=`) crashes CLI | mitigate | _parse_arg_kvs splits on first `=`; missing-`=` emits user-facing error + exit 1 (test_mcp_call_invalid_arg_format proves) |
| T-T3-08-03 | Tampering | --arg JSON parse exception bypasses fallback | mitigate | json.loads raises only JSONDecodeError; caught explicitly; falls back to raw string. No other exception types possible from `json.loads` on a string input. |
| T-T3-05 (reaffirm) | DoS | MCP subprocesses launched by mcp_list_cmd / mcp_call_cmd leak | mitigate | lifecycle.atexit handles reap globally; both commands rely on this without manual cleanup |
</threat_model>

<verification>
- `uv run pytest tests/harness/test_cli_mcp.py -x -q` exits 0 (8 tests pass)
- `voss mcp --help` (via CliRunner) shows both `list` and `call` subcommands
- `voss mcp list --cwd /tmp/empty` (where no mcp.yml exists) prints `<no MCP servers configured>` and exits 0
- `_parse_arg_kvs(("count=10","verbose=true","path=./README.md")) == {"count": 10, "verbose": True, "path": "./README.md"}` (mixed JSON + string fallback)
- `grep -cE "@click.group.\.mcp.\)|@mcp_group.command" voss/harness/cli.py` returns >= 3
</verification>

<success_criteria>
- voss mcp list / call subcommands registered under voss main click group
- mcp list outputs pretty by default + machine-readable via --json
- mcp call parses --arg key=value with JSON+string fallback per D-14
- Exit codes 0/1/2 distinguish success / protocol error / server-side tool error
- 8 CliRunner tests cover happy + sad paths
- No PermissionGate involvement in mcp call (D-13 dev-tool decision)
</success_criteria>

<output>
Create `.planning/phases/T3-network-surface/T3-08-SUMMARY.md` when done: report mcp_group line range; show example pretty output and --json output captured from CliRunner; show _parse_arg_kvs test matrix; pytest output for the 8 tests; note that T3-09 will USE `voss mcp call filesystem read_text_file path=./README.md` in CI against the real npm reference server.
</output>
