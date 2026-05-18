---
phase: M12-mcp-bridge-caps-01c
plan: 02
type: execute
wave: 2
depends_on: [M12-01]
files_modified:
  - voss/harness/mcp/server_tools.py
  - tests/harness/mcp/test_mcp_server_tools.py
autonomous: true
requirements: [MCP-03, MCP-04, MCP-05]

must_haves:
  truths:
    - "`voss/harness/mcp/server_tools.py` exports `build_tool_descriptors(make_toolset_result, skill_registry, exposure: McpServerExposureConfig) -> list[dict]` that returns ONE MCP tool descriptor per advertised tool with keys `name`, `description`, `inputSchema`, and `annotations.destructiveHint`"
    - "`destructiveHint` is taken VERBATIM from the source: `ToolEntry.is_mutating` for low-level tools and `SkillEntry.mutating` for skills (D-02c)"
    - "Default `exposed_tools=\"*\"` resolves to EXACTLY 6 tool names: `fs_read`, `fs_glob`, `fs_grep`, `voss_check`, `git_status`, `git_diff` (ROADMAP M12 set)"
    - "Default `exposed_skills=\"*\"` resolves to EXACTLY the 7 skill ids from `default_skill_registry().ids()`: `add-test`, `analyze`, `audit-cognition`, `port-py-to-voss`, `rename-symbol`, `summarize-diff`, `voss-lint-as-skill`"
    - "`build_tool_dispatch(tools, skill_dispatch, gate)` returns an async callable that (a) calls `gate.check(name, args, is_mutating=<from registries>)` first, (b) on deny returns a `CallToolResult` with `isError=True` and `content=[{type:\"text\", text: <gate reason>}]`, (c) on allow dispatches to the tool or skill, (d) catches all exceptions and converts them to `isError=True` envelopes"
    - "An explicit `exposed_tools` list with a name NOT in `make_toolset_result` raises `McpConfigError(f\"unknown tool: {name}\")` at build time — never silently dropped"
    - "An explicit `exposed_skills` list with an id NOT in `skill_registry.ids()` raises `McpConfigError(f\"unknown skill: {id}\")` at build time"
  artifacts:
    - path: "voss/harness/mcp/server_tools.py"
      provides: "tool-descriptor builder + tools/call dispatcher with gate enforcement for the MCP server"
      contains: "def build_tool_descriptors"
      min_lines: 90
    - path: "tests/harness/mcp/test_mcp_server_tools.py"
      provides: "advertisement + dispatch + plan-mode-deny + unknown-tool + error-envelope tests"
      contains: "def test_default_surface_advertises_six_low_level_and_seven_skills"
      min_lines: 80
  key_links:
    - from: "voss/harness/mcp/server_tools.py"
      to: "voss/harness/tools.py:444"
      via: "iterate make_toolset result; read `ToolEntry.is_mutating` and `ToolEntry.descriptor.parameters` for inputSchema"
      pattern: "ToolEntry"
    - from: "voss/harness/mcp/server_tools.py"
      to: "voss/harness/skill_registry.py:11"
      via: "iterate `default_skill_registry().entries()`; read `SkillEntry.id`, `.description`, `.mutating`"
      pattern: "SkillEntry"
    - from: "voss/harness/mcp/server_tools.py"
      to: "voss/harness/permissions.py:172"
      via: "gate.check(tool_name, args, is_mutating=<from registry>) BEFORE every dispatch; respect the (allowed, reason) tuple"
      pattern: "gate\\.check\\("
---

<objective>
Build the tool-surface and dispatch layer for the MCP server: turn
`make_toolset(cwd)` + `default_skill_registry()` into the 13 advertised MCP
tool descriptors (`tools/list`), and route `tools/call` through
`PermissionGate.check` to either the underlying tool's `invoke(**args)` or the
skill bridge supplied by M12-03.

This plan implements D-02 (curated surface), D-02c (`destructiveHint =
is_mutating` verbatim), and the inbound half of D-03 (server `PermissionGate`
enforcement). It also implements MCP-04 (the mapping rule) and MCP-05 (gate
dispatch with `denied by mode plan` envelope). It does NOT call the actual
skill handlers — that bridge is M12-03 — it accepts a `skill_dispatch` callable
injected by the caller. M12-04 wires the bridge in at CLI level.

Parallel-safe with M12-03 (Wave 2): different files, both depend only on
M12-01.
</objective>

<context>
@.planning/phases/M12-mcp-bridge-caps-01c/M12-CONTEXT.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-PLAN-OUTLINE.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-01-server-scaffold-PLAN.md

Read first:
- `voss/harness/tools.py:77,99,109,250,343,444-465` — `make_toolset` signature,
  `ToolEntry` shape (`descriptor.name`, `.description`, `.parameters`,
  `is_mutating`, `is_network`), the curated 6-tool default surface lines.
- `voss/harness/skill_registry.py` (full file) — `SkillEntry(id, description,
  handler, mutating)`, `default_skill_registry()`, `SkillRegistry.entries()`.
- `voss/harness/permissions.py:172-260` — `PermissionGate.check(tool_name,
  args, *, is_mutating, is_network) -> tuple[bool, str]` and `mode_allows`
  semantics (plan denies all mutating; edit denies shell only; auto allows).
- `voss/harness/mcp/registry.py:24,37,66` — T3 client-side
  `register_mcp_tools` for the SYMMETRIC mapping. Inbound there:
  `destructiveHint -> is_mutating`. Outbound here: `is_mutating ->
  destructiveHint`. Mirror the convention.
- `voss/harness/mcp/config.py` (post-M12-01) — `McpServerExposureConfig`
  schema.
- MCP 2025-11-25 tool descriptor shape: `{name: str, description: str,
  inputSchema: dict, annotations: {destructiveHint: bool, ...}}`. Other
  annotation keys (`readOnlyHint`, `idempotentHint`, `openWorldHint`) are
  OUT OF SCOPE — only `destructiveHint` is advertised in v0.1.
</context>

<threat_model>
| ID | Threat | Mitigation |
|---|---|---|
| T-M12-02-01 | Mutating tool slips through plan mode (block-on-high) | The dispatcher calls `gate.check(name, args, is_mutating=<from registry>)` BEFORE any tool/skill invocation. `is_mutating` is read from `ToolEntry.is_mutating` (low-level) or `SkillEntry.mutating` (skill). On deny, returns `CallToolResult` with `isError=True`; the underlying tool/skill is never invoked. The test in Task 3 constructs a `PermissionGate(mode="plan")` and asserts every mutating skill (`add-test`, `analyze`, `rename-symbol`, `port-py-to-voss`) is denied with `denied by mode plan`. |
| T-M12-02-02 | `exposed_tools` opt-in lets an operator expose `shell_run`/`fs_write` accidentally | The default `"*"` resolves to ONLY the 6 ROADMAP-safe tools. Naming `shell_run` etc. in YAML opts in deliberately; the gate still enforces mode-tier. The risk is intentional opt-in, not silent broadening. |
| T-M12-02-03 | Tool with a typo'd name in YAML silently disappears from `tools/list` | Build-time validation: an unknown name in `exposed_tools` or `exposed_skills` raises `McpConfigError`. Operators see the error at server boot, not silent absence. |
| T-M12-02-04 | Tool exception escapes JSON-RPC framing and crashes the loop | The dispatcher wraps every `await entry.invoke(**args)` in `try/except Exception`; failure returns `CallToolResult` with `isError=True, content=[{type:"text", text:str(exc)}]`. Telemetry response event is emitted at `"warning"` level. |
| T-M12-02-05 | Network tool exposed by `exposed_tools` opt-in bypasses `allow_net` | The gate's `_check_impl` already handles `is_network=True` via the `allow_net` config gate (T3-02). This plan passes `is_network=entry.is_network` through to `gate.check`; no new bypass. |

Out-of-scope-here: skill execution (M12-03). CLI wiring (M12-04). End-to-end
subprocess test (M12-05).
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add `voss/harness/mcp/server_tools.py` with `build_tool_descriptors` + default-set resolvers</name>
  <read_first>
    voss/harness/tools.py (lines 77-100, 444-466 — `make_toolset` + ToolEntry shape; specifically `entry.descriptor.name`, `.description`, `.parameters`, `.is_mutating`, `.is_network`)
    voss/harness/skill_registry.py (full file — `SkillEntry` fields)
    voss/harness/mcp/config.py (post-M12-01 — `McpServerExposureConfig`)
    voss/harness/mcp/registry.py (lines 37-65 — inbound `_make_mcp_descriptor` shape for symmetry)
    voss/harness/mcp/server_tools.py (file being created — confirm it does not exist)
  </read_first>
  <action>
    Create `voss/harness/mcp/server_tools.py`.

    Module constants (LITERAL — these are MCP-03 contract):
    ```
    DEFAULT_LOW_LEVEL_TOOLS = (
        "fs_read", "fs_glob", "fs_grep",
        "voss_check", "git_status", "git_diff",
    )
    ```

    Imports: `from __future__ import annotations`, `from typing import Any,
    Awaitable, Callable, Mapping, Sequence`,
    `from voss.harness.mcp.config import McpServerExposureConfig,
    McpConfigError`. Forward-declare `ToolEntry` and `SkillEntry` as TYPE
    references only (avoid circular imports — use `if TYPE_CHECKING`).

    Public function `def resolve_tool_names(exposure: McpServerExposureConfig | None,
    available_tools: Mapping[str, Any]) -> list[str]:`
    - If `exposure is None` or `exposure.exposed_tools == "*"`: return list of
      `DEFAULT_LOW_LEVEL_TOOLS` that EXIST in `available_tools` (filtered;
      missing entries warned but NOT errored — `make_toolset` may omit a name
      based on env).
    - Else: iterate the explicit list, raise `McpConfigError(f"unknown tool:
      {name}")` for any name not in `available_tools`. Preserve list order.

    Public function `def resolve_skill_ids(exposure: McpServerExposureConfig | None,
    skill_registry: Any) -> list[str]:`
    - If `exposure is None` or `exposure.exposed_skills == "*"`: return
      `skill_registry.ids()` verbatim (sorted by `SkillRegistry.ids`).
    - Else: iterate explicit list, raise `McpConfigError(f"unknown skill: {id}")`
      for any id not in `skill_registry.ids()`.

    Public function `def build_tool_descriptors(tools: Mapping[str, Any],
    skill_registry: Any, exposure: McpServerExposureConfig | None,
    ) -> list[dict]:`
    - For each tool name from `resolve_tool_names`:
      `entry = tools[name]`. Build `{"name": entry.descriptor.name,
      "description": entry.description, "inputSchema": entry.parameters,
      "annotations": {"destructiveHint": bool(entry.is_mutating)}}`.
    - For each skill id from `resolve_skill_ids`:
      `entry = skill_registry.get(id)`. Build `{"name": entry.id, "description":
      entry.description, "inputSchema": {"type": "object", "properties":
      {"args": {"type": "array", "items": {"type": "string"}}},
      "required": []}, "annotations": {"destructiveHint": bool(entry.mutating)}}`.
      (Skills take a single optional `args: list[str]` positional list — the
      `SkillHandler` contract `Callable[[Any, list[str]], None]`.)
    - Return list with tools first then skills (deterministic order).

    Do NOT execute any tool or skill in this module. Do NOT import
    `make_toolset` (caller passes it in) — keeps the module synchronously
    importable and trivially test-stubbable.
  </action>
  <verify>
    <automated>python3 -c "import ast; ast.parse(open('voss/harness/mcp/server_tools.py').read()); print('ast ok')"</automated>
    <automated>python3 -c "from voss.harness.mcp.server_tools import DEFAULT_LOW_LEVEL_TOOLS, resolve_tool_names, resolve_skill_ids, build_tool_descriptors; assert DEFAULT_LOW_LEVEL_TOOLS == ('fs_read','fs_glob','fs_grep','voss_check','git_status','git_diff'); print('constants ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/mcp/server_tools.py` parses
    - `DEFAULT_LOW_LEVEL_TOOLS` is exactly the 6-tuple `("fs_read","fs_glob","fs_grep","voss_check","git_status","git_diff")` — literal verification by `grep -F`
    - `build_tool_descriptors` produces descriptors with keys `name`, `description`, `inputSchema`, `annotations.destructiveHint`
    - Module imports only `typing` + `voss.harness.mcp.config`; no circular imports of `tools.py` or `skill_registry.py` at module top
  </acceptance_criteria>
  <done>Descriptor builder + name resolvers ready, decoupled from concrete tool/skill modules.</done>
</task>

<task type="auto">
  <name>Task 2: Add `build_tool_dispatch` to `server_tools.py` — gate-enforced async dispatcher</name>
  <read_first>
    voss/harness/mcp/server_tools.py (Task 1 output — extend, do not rewrite)
    voss/harness/permissions.py (lines 172-260 — `PermissionGate.check` return shape + mode_allows behavior)
    voss/harness/tools.py (lines 51-55 — `ToolEntry.invoke` async signature)
  </read_first>
  <action>
    Add to `voss/harness/mcp/server_tools.py`:

    `def build_tool_dispatch(tools: Mapping[str, Any], skill_registry: Any,
    skill_dispatch: Callable[[str, list[str]], Awaitable[str]] | None, gate: Any,
    ) -> Callable[[str, dict[str, Any]], Awaitable[dict]]:`

    Returns an async function `async def dispatch(name: str, args: dict[str, Any])
    -> dict:` with this exact behavior:

    1. Look up `name`:
       - If `name in tools`: target = ("tool", tools[name]).
       - Elif `skill_registry.get(name) is not None`: target = ("skill", skill_registry.get(name)).
       - Else: return `{"content": [{"type": "text", "text": f"unknown tool: {name}"}], "isError": True}`.
    2. Determine `is_mutating` + `is_network`:
       - tool path: `entry.is_mutating`, `entry.is_network` (from `ToolEntry`).
       - skill path: `entry.mutating`, `False` (skills do not declare network).
    3. Call `allowed, reason = gate.check(name, args, is_mutating=is_mutating,
       is_network=is_network)`. If `not allowed`: return
       `{"content": [{"type": "text", "text": reason}], "isError": True}`. Do
       NOT invoke the underlying tool/skill.
    4. On allow:
       - tool path: `try: result = await entry.invoke(**args); return
         {"content": [{"type": "text", "text": str(result)}], "isError":
         False}`. Catch `Exception as exc` → `return {"content": [{"type":
         "text", "text": f"<error: {exc}>"}], "isError": True}`.
       - skill path: if `skill_dispatch is None`, return `{"content":
         [{"type": "text", "text": "skill dispatch not wired (M12-03)"}],
         "isError": True}`. Else `try: text = await skill_dispatch(name,
         args.get("args", []) or []); return {"content": [{"type": "text",
         "text": text}], "isError": False}`. Catch `Exception as exc` → same
         error envelope as tool path.

    The `skill_dispatch` injectable lets M12-03 own the actual skill execution
    (with its own ctx construction, stdout capture, cost handling) without
    coupling this plan to it.
  </action>
  <verify>
    <automated>python3 -c "import inspect; from voss.harness.mcp.server_tools import build_tool_dispatch; sig=inspect.signature(build_tool_dispatch); params=list(sig.parameters); assert params==['tools','skill_registry','skill_dispatch','gate'], params; print('sig ok')"</automated>
    <automated>python3 -c "import re; s=open('voss/harness/mcp/server_tools.py').read(); body='\n'.join(l for l in s.splitlines() if not l.lstrip().startswith('#')); assert re.search(r'gate\\.check\\(\\s*name', body), 'gate.check call missing'; assert 'isError' in body and 'content' in body; print('dispatch ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `build_tool_dispatch(tools, skill_registry, skill_dispatch, gate)` exists with that exact 4-arg signature
    - The returned async callable calls `gate.check(name, args, is_mutating=..., is_network=...)` BEFORE invoking any tool or skill
    - Denied calls return `{"isError": True, "content": [{"type":"text","text": <reason>}]}` with the gate's `reason` string verbatim
    - Tool/skill exceptions are caught and returned as `isError=True` envelopes — they do NOT propagate
    - When `skill_dispatch is None`, calling a skill name returns an `isError=True` envelope (M12-04 will wire the real bridge)
  </acceptance_criteria>
  <done>Gate-enforced dispatcher ready; tools invoke directly, skills route through the injected bridge.</done>
</task>

<task type="auto">
  <name>Task 3: Add `tests/harness/mcp/test_mcp_server_tools.py` covering advertisement, mapping, deny, errors</name>
  <read_first>
    voss/harness/mcp/server_tools.py (Tasks 1 & 2)
    voss/harness/tools.py (lines 444-466 — for assertion of default-set membership)
    voss/harness/skill_registry.py (post-T7 — the 7 skill ids assertion target)
    voss/harness/permissions.py (constructor signature for tests)
  </read_first>
  <action>
    Create `tests/harness/mcp/test_mcp_server_tools.py`. Use `pytest`,
    `asyncio_mode = "auto"`.

    Tests:

    1. `def test_default_surface_advertises_six_low_level_and_seven_skills(tmp_path)`:
       - `from voss.harness.tools import make_toolset; tools =
         make_toolset(tmp_path)`
       - `from voss.harness.skill_registry import default_skill_registry; reg =
         default_skill_registry()`
       - `descs = build_tool_descriptors(tools, reg, None)`
       - Assert names contain ALL of the 6 low-level set and ALL of the 7
         skill ids. Assert total count == 13.

    2. `def test_destructive_hint_mirrors_is_mutating(tmp_path)`:
       - Build default descriptors (as above).
       - For each descriptor: cross-check `annotations.destructiveHint` against
         the source flag. For low-level: `tools[name].is_mutating`. For skill:
         `reg.get(name).mutating`. Assert exact equality for all 13. Result:
         9 `destructiveHint=False` (6 low-level + voss-lint-as-skill +
         summarize-diff + audit-cognition), 4 `True` (analyze, rename-symbol,
         add-test, port-py-to-voss).

    3. `def test_unknown_tool_or_skill_raises_mcp_config_error(tmp_path)`:
       - `from voss.harness.mcp.config import McpServerExposureConfig,
         McpConfigError`
       - `exp = McpServerExposureConfig(exposed_tools=["fs_read","does_not_exist"])`
       - Build the descriptors → expect `pytest.raises(McpConfigError, match="unknown tool: does_not_exist")`.
       - Same for skill.

    4. `async def test_dispatch_plan_mode_denies_every_mutating_skill(tmp_path)`:
       - `from voss.harness.permissions import PermissionGate`
       - `gate = PermissionGate(mode="plan")`
       - Build dispatch with `skill_dispatch = AsyncMock(return_value="should not be called")` (or a sentinel).
       - For each of `analyze`, `rename-symbol`, `add-test`, `port-py-to-voss`:
         `res = await dispatch(name, {"args": []})`. Assert `res["isError"]
         is True` and `res["content"][0]["text"] == "denied by mode plan"`.
       - Assert `skill_dispatch` was NEVER awaited (call count 0).

    5. `async def test_dispatch_auto_mode_runs_read_only_tool(tmp_path, monkeypatch)`:
       - Create a dummy file in `tmp_path` so `fs_read` succeeds.
       - `gate = PermissionGate(auto_yes=True)`
       - Build dispatch (skill_dispatch=None — not exercised).
       - `res = await dispatch("fs_read", {"path": "<the dummy file>"})`.
         Assert `res["isError"] is False` and the content text equals the
         file's contents.

    6. `async def test_dispatch_skill_returns_unwired_error_when_dispatch_is_none(tmp_path)`:
       - Build dispatch with `skill_dispatch=None`, `gate=PermissionGate(auto_yes=True)`.
       - `res = await dispatch("voss-lint-as-skill", {"args": ["."]})`.
       - Assert `res["isError"] is True` and `"skill dispatch not wired"` in `res["content"][0]["text"]`.

    7. `async def test_dispatch_tool_exception_converts_to_iserror_envelope(tmp_path)`:
       - Build dispatch.
       - Call `await dispatch("fs_read", {"path": "no/such/file.txt"})` — fs_read returns an error string, which is allowed by the tool itself; assert `res["isError"] is False` and the text starts with `"<error: not found:"` (this is how fs_read reports its own error; the dispatcher does NOT promote it to isError unless an exception was raised). To genuinely trigger the exception path: monkeypatch one tool entry's `invoke` to raise `RuntimeError("boom")`, then assert `isError=True` and `"boom"` in the content text.

    8. `def test_unknown_call_returns_unknown_tool_envelope(tmp_path)`:
       - Build dispatch.
       - `res = asyncio.run(dispatch("nope", {}))`. Assert
         `res["isError"] is True` and `"unknown tool: nope"` in text.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/mcp/test_mcp_server_tools.py</automated>
    <automated>python3 -m pytest -q tests/harness/mcp/</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/mcp/test_mcp_server_tools.py` contains all 8 named tests
    - All 8 tests pass: `python3 -m pytest -q tests/harness/mcp/test_mcp_server_tools.py` exits 0
    - Full pre-existing mcp suite still passes: `python3 -m pytest -q tests/harness/mcp/` exits 0
    - The plan-mode deny test asserts `denied by mode plan` for ALL FOUR mutating skills (`analyze`, `rename-symbol`, `add-test`, `port-py-to-voss`)
    - The default-surface test asserts EXACTLY 13 descriptors (6 low-level + 7 skills)
  </acceptance_criteria>
  <done>Eight tests prove the 13-tool advertisement + gate-enforced dispatch + error envelopes + opt-in error handling.</done>
</task>

</tasks>

<verification>
```bash
cd /Users/benjaminmarks/Projects/Voss

# 1. Module + tests
python3 -m pytest -q tests/harness/mcp/test_mcp_server_tools.py
python3 -m pytest -q tests/harness/mcp/

# 2. Default 6-tool constant is exact
python3 -c "from voss.harness.mcp.server_tools import DEFAULT_LOW_LEVEL_TOOLS; assert DEFAULT_LOW_LEVEL_TOOLS == ('fs_read','fs_glob','fs_grep','voss_check','git_status','git_diff')"

# 3. Server module is unmodified (file-disjoint from M12-03)
git diff --stat voss/harness/mcp/server.py voss/harness/mcp/__init__.py voss/harness/mcp/config.py | grep -qE '\S' && echo "FAIL: M12-01 files touched (forbidden in M12-02)" || echo "OK: M12-01 files untouched"

# 4. The Wave-2-parallel sibling file (server_skills.py, owned by M12-03) is unmodified
test -e voss/harness/mcp/server_skills.py && (git diff --stat voss/harness/mcp/server_skills.py | grep -qE '\S' && echo "FAIL: M12-03 file edited" || echo "OK: M12-03 file untouched") || echo "OK: M12-03 file does not exist yet (Wave 2 sibling)"

# 5. Whitespace
git diff --check
```
</verification>

<success_criteria>
- `voss/harness/mcp/server_tools.py` ships `build_tool_descriptors`, `build_tool_dispatch`, `resolve_tool_names`, `resolve_skill_ids`, `DEFAULT_LOW_LEVEL_TOOLS`.
- Default surface = exactly 13 descriptors (6 low-level + 7 skills); `destructiveHint = is_mutating` verbatim.
- `tools/call` dispatcher always calls `gate.check` first; plan-mode denies all 4 mutating skills with `denied by mode plan`; tool exceptions are wrapped as `isError=True` envelopes; unknown names return `unknown tool: <name>` envelopes.
- Unknown names in explicit `exposed_tools`/`exposed_skills` raise `McpConfigError` at build time.
- 8 tests in `tests/harness/mcp/test_mcp_server_tools.py` green; full mcp suite green.
- Wave-2 file-disjointness: this plan does not edit `voss/harness/mcp/server.py`, `voss/harness/mcp/__init__.py`, `voss/harness/mcp/config.py` (M12-01), or `voss/harness/mcp/server_skills.py` (M12-03).
- `git diff --check` clean.
</success_criteria>

<output>
Create `.planning/phases/M12-mcp-bridge-caps-01c/M12-02-SUMMARY.md` when done.
</output>
