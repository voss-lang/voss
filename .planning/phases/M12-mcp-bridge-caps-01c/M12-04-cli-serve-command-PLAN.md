---
phase: M12-mcp-bridge-caps-01c
plan: 04
type: execute
wave: 3
depends_on: [M12-01, M12-02, M12-03]
files_modified:
  - voss/harness/cli.py
  - tests/harness/mcp/test_mcp_serve_cli.py
autonomous: true
requirements: [MCP-01]

must_haves:
  truths:
    - "`voss mcp serve` is a new click subcommand under the existing `voss mcp` group (sibling to `list`/`call`) — `voss/harness/cli.py:2292` `@click.group(\"mcp\")` gains a third `@mcp_group.command(\"serve\")`"
    - "`--mode` is REQUIRED — no default; `voss mcp serve` with no `--mode` exits non-zero with `<error: --mode required (plan|edit|auto)>` on stderr (D-03 forcing function)"
    - "`--mode` accepts EXACTLY `plan|edit|auto`; any other value is rejected by click (`click.Choice(['plan','edit','auto'])`)"
    - "When invoked correctly, the serve command: (1) loads `.voss/mcp.yml` via `load_mcp_config(cwd)` and reads `config.server` (None → default `McpServerExposureConfig()`); (2) builds `tools = make_toolset(cwd)`; (3) gets `reg = default_skill_registry()`; (4) builds `descriptors = build_tool_descriptors(tools, reg, server_cfg)`; (5) builds `gate = PermissionGate(mode=<--mode>, auto_yes=True)`; (6) builds `skill_dispatch = make_skill_dispatch(cwd=cwd, provider=<server provider>, history=None, record=<SimpleNamespace>, renderer=PlainRenderer(), tools=tools, gate=gate, skill_registry=reg)`; (7) builds `dispatch = build_tool_dispatch(tools, reg, skill_dispatch, gate)`; (8) constructs `McpServer(name=<server name or 'voss'>, tool_descriptors=descriptors, dispatch=dispatch)`; (9) runs `asyncio.run(server.serve_stdio(reader, writer))` reading from stdin and writing to stdout"
    - "The serve loop's stdin/stdout are bound via `asyncio.StreamReader`/`StreamWriter` wrappers around `sys.stdin.buffer`/`sys.stdout.buffer` (NOT TextIOWrapper — the wire is bytes JSON-RPC lines)"
    - "Renderer is a NULL/plain renderer (no Rich Console) so renderer output does not corrupt the stdout JSON-RPC stream — see Threat T-M12-04-02"
    - "`--help` text documents D-05: 'Skills executed by this server use the server's configured LLM provider for cost. The calling host does not see the LLM cost.'"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "third command in the @mcp_group click group: `voss mcp serve --mode {plan|edit|auto} [--cwd PATH]`"
      contains: "mcp_group.command(\"serve\")"
    - path: "tests/harness/mcp/test_mcp_serve_cli.py"
      provides: "click CliRunner tests for argument parsing, --mode requirement, --mode rejection of invalid values, --help mentioning the cost-attribution note"
      contains: "def test_mode_required_when_omitted"
      min_lines: 60
  key_links:
    - from: "voss/harness/cli.py (new mcp_serve_cmd)"
      to: "voss/harness/mcp/server.py"
      via: "from voss.harness.mcp.server import McpServer; asyncio.run(server.serve_stdio(reader, writer))"
      pattern: "McpServer\\("
    - from: "voss/harness/cli.py (new mcp_serve_cmd)"
      to: "voss/harness/mcp/server_tools.py"
      via: "build_tool_descriptors + build_tool_dispatch"
      pattern: "build_tool_descriptors\\("
    - from: "voss/harness/cli.py (new mcp_serve_cmd)"
      to: "voss/harness/mcp/server_skills.py"
      via: "make_skill_dispatch supplies the dispatch callable injected into build_tool_dispatch"
      pattern: "make_skill_dispatch\\("
    - from: "voss/harness/cli.py (new mcp_serve_cmd)"
      to: "voss/harness/permissions.py:172"
      via: "PermissionGate(mode=<--mode>, auto_yes=True) constructed once for server lifetime"
      pattern: "PermissionGate\\(\\s*mode="
---

<objective>
Wire M12-01/02/03 surfaces into the `voss mcp` click group as a `voss mcp serve
--mode plan|edit|auto` foreground subcommand. Implements MCP-01 + the visible
half of D-03 (the no-default-mode forcing function). After this plan, an
operator can run `voss mcp serve --mode plan` and an MCP host can connect to
it as a subprocess and exchange real JSON-RPC over stdio.

This plan does NOT add an end-to-end stdio subprocess test — that's M12-05.
It only proves the click surface is correct.
</objective>

<context>
@.planning/phases/M12-mcp-bridge-caps-01c/M12-CONTEXT.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-PLAN-OUTLINE.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-01-server-scaffold-PLAN.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-02-tools-advertisement-dispatch-PLAN.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-03-skills-bridge-PLAN.md

Read first:
- `voss/harness/cli.py:2292-2480` — existing `@click.group("mcp")` definition,
  `mcp_list_cmd`, `mcp_call_cmd`. Style + option conventions to mirror.
- `voss/harness/permissions.py:145-180` — `PermissionGate` constructor +
  `mode` field (Literal["plan","edit","auto"]).
- `voss/harness/mcp/config.py:58` — `load_mcp_config(cwd) -> McpConfig | None`
  signature.
- `voss/harness/tools.py:77` — `make_toolset(cwd)` signature; pick a
  `provider=None` since this serve command does not own an LLM client itself
  (skill cost-attribution note is documentation, not enforcement — D-05).
- `voss/harness/render.py:60-130` — `make_renderer` and `PlainRenderer`. The
  serve command MUST use a renderer that does not write to stdout (renderer
  output collides with JSON-RPC frames).
</context>

<threat_model>
| ID | Threat | Mitigation |
|---|---|---|
| T-M12-04-01 | Operator runs `voss mcp serve` with no `--mode` and gets a default that's too permissive | `--mode` has no default; click raises `MissingOption` automatically. Add an explicit error message so the failure mode is clear in stderr. The smoke test asserts a non-zero exit with the right message. |
| T-M12-04-02 | Renderer prints status/banner/colors to stdout, corrupting JSON-RPC framing the host parses | Use a renderer that writes ONLY to stderr (a stderr-bound `PlainRenderer` or a true null renderer). MCP frames must be the only bytes on stdout. Document this constraint inline in the command body. |
| T-M12-04-03 | Operator runs `voss mcp serve --mode auto` accidentally and a remote host issues `fs_write` | The gate still enforces mode-tier per call; `auto` allows mutation, which is what the operator opted into. The forcing function (no default) is the safeguard at boot. No additional control. |
| T-M12-04-04 | `.voss/mcp.yml` is malformed and `load_mcp_config` raises | Wrap in `try/except McpConfigError`, print `<error: mcp config: {e}>` to stderr, exit non-zero (mirror existing `mcp_list_cmd`/`mcp_call_cmd` error handling at `cli.py:2310`/`2384`). |
| T-M12-04-05 | Bare-stdin EOF on launch keeps the process alive forever | `McpServer.serve_stdio` already returns on EOF (T-M12-01-05). The click wrapper calls `asyncio.run(...)` which returns when the coroutine returns, then exits. |

Out-of-scope: end-to-end subprocess roundtrip (M12-05). Multi-process
lifecycle / daemon mode (deferred). Network transport (deferred).
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add `voss mcp serve` click subcommand to `voss/harness/cli.py`</name>
  <read_first>
    voss/harness/cli.py (lines 2292-2480 — full existing mcp group; mirror style)
    voss/harness/mcp/__init__.py (post-M12-01 — confirm McpServer is re-exported)
    voss/harness/mcp/server.py (Task 2 of M12-01 — confirm McpServer signature + serve_stdio shape)
    voss/harness/mcp/server_tools.py (M12-02 — build_tool_descriptors + build_tool_dispatch)
    voss/harness/mcp/server_skills.py (M12-03 — make_skill_dispatch)
  </read_first>
  <action>
    Edit `voss/harness/cli.py`. Locate the existing `@mcp_group.command("call")`
    block. Immediately AFTER `mcp_call_cmd`'s closing (i.e. between the
    bottom of `mcp_call_cmd` and the next non-mcp `# -----`-style separator
    block), insert a new command.

    Imports needed (add to the top-of-file imports if not present; many of
    these are likely already imported elsewhere in cli.py — DEDUPE):
    - `import asyncio`, `import sys`, `import types`
    - `from voss.harness.mcp.config import load_mcp_config, McpConfigError,
      McpServerExposureConfig`
    - `from voss.harness.mcp.server import McpServer`
    - `from voss.harness.mcp.server_tools import build_tool_descriptors,
      build_tool_dispatch`
    - `from voss.harness.mcp.server_skills import make_skill_dispatch`
    - `from voss.harness.tools import make_toolset`
    - `from voss.harness.skill_registry import default_skill_registry`
    - `from voss.harness.permissions import PermissionGate`
    - `from voss.harness.render import PlainRenderer`

    Use whichever `make_renderer` factory the codebase already uses for non-TTY
    output (read `voss/harness/render.py:60-130` and prefer the existing
    factory; fall back to instantiating `PlainRenderer()` directly).

    New command:

    ```
    @mcp_group.command("serve")
    @click.option(
        "--mode",
        type=click.Choice(["plan", "edit", "auto"], case_sensitive=False),
        required=True,
        help=(
            "Permission mode for incoming MCP calls. REQUIRED — no default. "
            "plan denies all mutating tools; edit allows fs writes but denies "
            "shell; auto allows everything."
        ),
    )
    @click.option(
        "--cwd",
        "cwd_str",
        default=".",
        type=click.Path(file_okay=False),
        help="Project root the server operates against. Default: current dir.",
    )
    def mcp_serve_cmd(mode: str, cwd_str: str) -> None:
        """Run the Voss MCP server over stdio.

        Skills executed by this server use the SERVER's configured LLM
        provider. The calling MCP host does NOT see the LLM cost.
        """
        cwd = Path(cwd_str).resolve()
        try:
            cfg = load_mcp_config(cwd)
        except McpConfigError as e:
            click.echo(f"<error: mcp config: {e}>", err=True)
            sys.exit(1)
        server_cfg = cfg.server if cfg is not None else None
        if server_cfg is None:
            server_cfg = McpServerExposureConfig()

        tools = make_toolset(cwd)
        reg = default_skill_registry()
        try:
            descriptors = build_tool_descriptors(tools, reg, server_cfg)
        except McpConfigError as e:
            click.echo(f"<error: mcp config: {e}>", err=True)
            sys.exit(1)

        gate = PermissionGate(mode=mode, auto_yes=True)
        record = types.SimpleNamespace(model="mcp-server", id="mcp-serve")
        renderer = PlainRenderer()  # stderr-bound or no-op for JSON-RPC purity
        skill_dispatch = make_skill_dispatch(
            cwd=cwd,
            provider=None,        # M12 server does not own an LLM client; skill
                                  # paths that need a provider will surface that
                                  # in their own error envelope per gate result.
            history=None,
            record=record,
            renderer=renderer,
            tools=tools,
            gate=gate,
            skill_registry=reg,
        )
        dispatch = build_tool_dispatch(tools, reg, skill_dispatch, gate)
        server_name = (server_cfg.name or "voss") if server_cfg else "voss"
        server = McpServer(
            name=server_name, tool_descriptors=descriptors, dispatch=dispatch
        )

        async def _run() -> None:
            loop = asyncio.get_running_loop()
            reader = asyncio.StreamReader(loop=loop)
            protocol = asyncio.StreamReaderProtocol(reader, loop=loop)
            await loop.connect_read_pipe(lambda: protocol, sys.stdin.buffer)
            transport, _ = await loop.connect_write_pipe(
                asyncio.streams.FlowControlMixin, sys.stdout.buffer
            )
            writer = asyncio.StreamWriter(transport, _, None, loop)
            await server.serve_stdio(reader, writer)

        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            sys.exit(0)
    ```

    If `asyncio.streams.FlowControlMixin` is not stable across Python
    versions the codebase targets, the alternative is to use the helper from
    the Anthropic `mcp` Python SDK's stdio module instead (`mcp.server.stdio.
    stdio_server`). Pick the path that compiles and passes Task 2's tests.
    Document the choice in the task SUMMARY.

    The `PlainRenderer` constructor on this codebase writes to stdout by
    default; if so, replace it with a renderer that writes to stderr OR
    construct a no-op `SimpleNamespace` whose methods are all `lambda
    *a, **k: None`. The exact choice must be verified by reading
    `voss/harness/render.py`. The constraint is: **NOTHING the serve command
    writes goes to stdout except McpServer's JSON-RPC frames.**
  </action>
  <verify>
    <automated>python3 -c "import ast; ast.parse(open('voss/harness/cli.py').read()); print('cli.py parses')"</automated>
    <automated>python3 -c "from voss.harness.cli import mcp_group; assert 'serve' in [c.name for c in mcp_group.commands.values()], [c.name for c in mcp_group.commands.values()]; print('serve registered')"</automated>
    <automated>python3 -m voss.cli mcp serve --help 2>&1 | grep -q "REQUIRED"</automated>
    <automated>python3 -m voss.cli mcp serve --help 2>&1 | grep -qE "SERVER'?s configured LLM provider"</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/cli.py` parses
    - `voss mcp serve --help` succeeds and contains the substring `"REQUIRED"` (for `--mode`) and a phrase matching `SERVER'?s configured LLM provider` (D-05 cost-attribution note)
    - `voss mcp serve --help` lists `--mode` with choices `plan|edit|auto` and `--cwd` option
    - The command is registered as a sibling of `voss mcp list` and `voss mcp call`: `python3 -c "from voss.harness.cli import mcp_group; assert set(['list','call','serve']) <= set(mcp_group.commands.keys())"`
    - Invoking `python3 -m voss.cli mcp serve` with NO `--mode` exits non-zero
  </acceptance_criteria>
  <done>`voss mcp serve --mode {plan|edit|auto}` is a click command; `--mode` required; cost-attribution note in `--help`.</done>
</task>

<task type="auto">
  <name>Task 2: Add `tests/harness/mcp/test_mcp_serve_cli.py` covering CliRunner-level surface</name>
  <read_first>
    voss/harness/cli.py (Task 1 output — the new mcp_serve_cmd)
    tests/harness/mcp/test_mcp_config.py (existing CLI-level test style)
  </read_first>
  <action>
    Create `tests/harness/mcp/test_mcp_serve_cli.py`. Use `click.testing
    .CliRunner` (already used elsewhere in `tests/harness/`).

    Tests (all sync — CliRunner runs the click command in-process; do NOT
    actually invoke `serve_stdio`'s asyncio loop here — these are
    surface-level checks. End-to-end stdio roundtrip is M12-05):

    1. `def test_mode_required_when_omitted()`:
       - `runner = CliRunner()`
       - `result = runner.invoke(mcp_group, ["serve"])`
       - Assert `result.exit_code != 0`
       - Assert `"--mode" in result.output or "--mode" in (result.stderr or "")`
         (click puts the missing-option message in output depending on
         version)

    2. `def test_mode_rejects_invalid_value()`:
       - `result = runner.invoke(mcp_group, ["serve", "--mode", "yolo"])`
       - Assert `result.exit_code != 0`
       - Assert `"yolo" in result.output or "Invalid value" in result.output`

    3. `def test_help_documents_cost_attribution()`:
       - `result = runner.invoke(mcp_group, ["serve", "--help"])`
       - Assert `result.exit_code == 0`
       - Assert all three of these substrings appear: `"REQUIRED"` (in
         `--mode` help), `"plan"`, `"auto"`. AND a phrase matching
         `SERVER's configured LLM provider` or equivalent cost-attribution
         language.

    4. `def test_help_mentions_three_modes()`:
       - From the same `--help` output, assert all three of `plan`, `edit`,
         `auto` are mentioned.

    5. `def test_serve_is_sibling_of_list_and_call()`:
       - `from voss.harness.cli import mcp_group`
       - `assert set(['list','call','serve']) <= set(mcp_group.commands.keys())`

    6. `def test_malformed_mcp_yaml_exits_nonzero(tmp_path)`:
       - `(tmp_path / ".voss").mkdir()`
       - `(tmp_path / ".voss" / "mcp.yml").write_text("this is not yaml: [unclosed")`
       - `result = runner.invoke(mcp_group, ["serve", "--mode", "plan", "--cwd", str(tmp_path)])`
       - Assert `result.exit_code != 0`
       - Assert `"mcp config" in result.output or "mcp config" in (result.stderr or "")`

    Tests do NOT attempt to actually run the stdio server loop — that
    requires real stdin/stdout pipes and is M12-05's end-to-end concern.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/mcp/test_mcp_serve_cli.py</automated>
    <automated>python3 -m pytest -q tests/harness/mcp/</automated>
  </verify>
  <acceptance_criteria>
    - All 6 named tests in `tests/harness/mcp/test_mcp_serve_cli.py` pass
    - The `mode_required_when_omitted` test asserts a non-zero exit
    - The `help_documents_cost_attribution` test asserts the D-05 cost-attribution language is in `--help`
    - The `serve_is_sibling_of_list_and_call` test asserts the click group has all three commands
    - Full mcp suite (`tests/harness/mcp/`) still passes
  </acceptance_criteria>
  <done>CLI surface tests prove the command registration, the `--mode` forcing function, the cost-attribution `--help` text, the click group membership, and the YAML-malformed error path.</done>
</task>

</tasks>

<verification>
```bash
cd /Users/benjaminmarks/Projects/Voss

# 1. cli.py parses and the command is registered
python3 -c "from voss.harness.cli import mcp_group; assert set(['list','call','serve']) <= set(mcp_group.commands.keys())"

# 2. --help has the required keywords
python3 -m voss.cli mcp serve --help | grep -q "REQUIRED"
python3 -m voss.cli mcp serve --help | grep -qE "SERVER'?s configured LLM provider"

# 3. --mode required forcing function fires
python3 -m voss.cli mcp serve 2>&1 | grep -qE "(Missing option|--mode)" && echo OK

# 4. Tests green
python3 -m pytest -q tests/harness/mcp/test_mcp_serve_cli.py
python3 -m pytest -q tests/harness/mcp/

# 5. Whitespace
git diff --check
```
</verification>

<success_criteria>
- `voss/harness/cli.py` registers `mcp_serve_cmd` under `@mcp_group.command("serve")` as a sibling of `list`/`call`.
- `--mode` is REQUIRED (no default), accepts only `plan|edit|auto` (click.Choice).
- `--help` documents D-05 cost-attribution ("Skills executed by this server use the SERVER's configured LLM provider").
- Command body wires `load_mcp_config` → `build_tool_descriptors`/`build_tool_dispatch` → `make_skill_dispatch` → `McpServer.serve_stdio` over real stdio.
- 6 CliRunner-level tests green; full mcp suite green.
- Renderer choice keeps stdout free of non-JSON-RPC bytes (constraint stated; M12-05 verifies via subprocess).
- `git diff --check` clean.
</success_criteria>

<output>
Create `.planning/phases/M12-mcp-bridge-caps-01c/M12-04-SUMMARY.md` when done.
</output>
